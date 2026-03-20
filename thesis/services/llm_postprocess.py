"""LLM Postprocessor: normalize → validate → merge (Phase A-Hardening)"""

import re
import logging

from thesis.services.builder_state import (
    CollectedData,
    IndicatorRecommendation,
    PremiseData,
    VALID_THESIS_TYPES,
)

logger = logging.getLogger(__name__)

# direction 한국어 → 영어 매핑
_DIRECTION_ALIASES = {
    '상승': 'bullish', '오름': 'bullish', 'bull': 'bullish',
    '하락': 'bearish', '내림': 'bearish', 'bear': 'bearish',
}

# direction/message 불일치 감지용 키워드
_BULLISH_KEYWORDS = {'상승', '오른다', '반등', '강세', '수혜', '긍정', '올라', '호재'}
_BEARISH_KEYWORDS = {'하락', '빠진다', '약세', '리스크', '부정', '떨어', '악재', '꺾인다'}


def normalize_llm_output(raw):
    """
    LLM 출력 정규화.

    - direction: 대소문자/한국어 정규화
    - thesis_type: str → list 변환, 유효값 필터링
    - premise title: 공백/특수문자 정리, 중복 제거
    - indicator_db_id: INDICATOR_CATALOG에 없으면 None으로 교정
    """
    if not isinstance(raw, dict):
        return raw

    # ── direction 정규화 ──
    direction = str(raw.get('direction', '')).strip().lower()
    direction = _DIRECTION_ALIASES.get(direction, direction)
    if direction not in ('bullish', 'bearish'):
        raw['direction'] = 'bearish'
    else:
        raw['direction'] = direction

    # ── thesis_type: str → list 변환 ──
    tt = raw.get('thesis_type', [])
    if isinstance(tt, str):
        parts = [t.strip().lower() for t in tt.replace('+', ',').split(',')]
        raw['thesis_type'] = parts
    elif isinstance(tt, list):
        raw['thesis_type'] = [str(t).strip().lower() for t in tt]

    # thesis_type 유효값만 필터링
    raw['thesis_type'] = [t for t in raw.get('thesis_type', []) if t in VALID_THESIS_TYPES]

    # ── premises 정리 ──
    premises = raw.get('premises', [])
    seen_titles = set()
    unique_premises = []
    for p in premises:
        if not isinstance(p, dict):
            continue
        # title 공백/특수문자 정리
        title = str(p.get('title', '')).strip()
        title = re.sub(r'\s+', ' ', title)  # 연속 공백 → 단일 공백
        title = title.strip('·•-–—*# ')  # 흔한 접두 특수문자 + 공백 제거
        if not title:
            continue
        p['title'] = title

        # description 정리
        desc = p.get('description', '')
        if isinstance(desc, str):
            p['description'] = desc.strip()

        # 중복 제거
        if title not in seen_titles:
            seen_titles.add(title)
            unique_premises.append(p)

    # ── indicator_db_id: CATALOG에 없으면 None 교정 ──
    from thesis.services.prompt_builder import get_indicator_by_id
    for p in unique_premises:
        for ind in p.get('recommended_indicators', []):
            db_id = ind.get('indicator_db_id')
            if db_id is not None and get_indicator_by_id(db_id) is None:
                logger.info(f"indicator_db_id {db_id} not in catalog, nullified")
                ind['indicator_db_id'] = None

    raw['premises'] = unique_premises

    # ── confidence 정규화 ──
    confidence = str(raw.get('confidence', 'medium')).strip().lower()
    if confidence not in ('high', 'medium', 'low'):
        raw['confidence'] = 'medium'
    else:
        raw['confidence'] = confidence

    # ── target 정리 ──
    target = raw.get('target', '')
    if isinstance(target, str):
        raw['target'] = target.strip()

    return raw


def validate_llm_output(raw):
    """
    LLM 출력 검증.

    Returns:
        (validated_data, warnings, errors)
        errors가 있으면 fallback 트리거.
    """
    warnings = []
    errors = []

    confidence = raw.get('confidence', 'medium')

    # low confidence: 질문 모드이므로 필수 필드 검증 완화
    if confidence == 'low':
        return raw, warnings, errors

    # direction 필수
    if not raw.get('direction'):
        errors.append('direction 누락')

    # target 필수
    if not raw.get('target'):
        errors.append('target 누락')

    # premises 최소 1개
    premises = raw.get('premises', [])
    if not premises:
        errors.append('premises 최소 1개 필요')

    # premises 5개 초과 시 자름
    if len(premises) > 5:
        raw['premises'] = premises[:5]
        warnings.append(f'premises {len(premises)}개 → 5개로 축소')

    # ── Hardening: direction/message 방향 불일치 감지 ──
    message = str(raw.get('message', ''))
    direction = raw.get('direction', '')
    if direction and message:
        msg_bullish = any(kw in message for kw in _BULLISH_KEYWORDS)
        msg_bearish = any(kw in message for kw in _BEARISH_KEYWORDS)
        if direction == 'bullish' and msg_bearish and not msg_bullish:
            warnings.append(f'direction({direction})과 message 톤 불일치 가능')
        elif direction == 'bearish' and msg_bullish and not msg_bearish:
            warnings.append(f'direction({direction})과 message 톤 불일치 가능')

    # ── Hardening: indicator 0개인 premise → warning ──
    for p in raw.get('premises', []):
        inds = p.get('recommended_indicators', [])
        if not inds:
            warnings.append(f'premise "{p.get("title", "")[:30]}" 에 추천 지표 없음')

    return raw, warnings, errors


def merge_to_collected(collected, validated):
    """
    검증된 LLM 출력을 CollectedData에 병합.

    Args:
        collected: CollectedData 또는 dict
        validated: normalize + validate를 거친 LLM 출력 dict

    Returns:
        CollectedData
    """
    if isinstance(collected, CollectedData):
        data = collected.model_dump()
    elif isinstance(collected, dict):
        data = collected.copy()
    else:
        data = {}

    # 단일 필드 병합 (None이 아닌 값만)
    for key in ('direction', 'target', 'target_type', 'title', 'timeframe', 'magnitude', 'sensitivity'):
        value = validated.get(key)
        if value is not None:
            data[key] = value

    # thesis_type: list 교체
    tt = validated.get('thesis_type')
    if tt:
        data['thesis_type'] = tt

    # premises: PremiseData 변환
    raw_premises = validated.get('premises', [])
    if raw_premises:
        premises = []
        for p in raw_premises:
            indicators = []
            for ind in p.get('recommended_indicators', []):
                indicators.append(IndicatorRecommendation(
                    indicator_db_id=ind.get('indicator_db_id'),
                    indicator_name=ind.get('indicator_name'),
                    why=ind.get('why', ''),
                    signal_type=ind.get('signal_type', 'coincident'),
                ))
            premises.append(PremiseData(
                title=p.get('title', ''),
                description=p.get('description', ''),
                recommended_indicators=indicators,
            ))
        data['premises'] = [p.model_dump() for p in premises]

    return CollectedData.model_validate(data)
