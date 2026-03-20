"""LLM Postprocessor: normalize → validate → merge (Phase A-MVP)"""

import logging

from thesis.services.builder_state import (
    CollectedData,
    IndicatorRecommendation,
    PremiseData,
    VALID_THESIS_TYPES,
)

logger = logging.getLogger(__name__)


def normalize_llm_output(raw):
    """
    LLM 출력 정규화.

    - thesis_type: str → list 변환 ("earnings+chain" → ["earnings", "chain"])
    - premise title 중복 제거
    - direction 정규화
    """
    if not isinstance(raw, dict):
        return raw

    # thesis_type: str → list 변환
    tt = raw.get('thesis_type', [])
    if isinstance(tt, str):
        parts = [t.strip() for t in tt.replace('+', ',').split(',')]
        raw['thesis_type'] = parts

    # thesis_type 유효값만 필터링
    raw['thesis_type'] = [t for t in raw.get('thesis_type', []) if t in VALID_THESIS_TYPES]

    # premises 제목 중복 제거
    premises = raw.get('premises', [])
    seen_titles = set()
    unique_premises = []
    for p in premises:
        title = p.get('title', '')
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_premises.append(p)
    raw['premises'] = unique_premises

    # direction 정규화
    direction = raw.get('direction', '')
    if direction not in ('bullish', 'bearish'):
        raw['direction'] = 'bearish'

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
