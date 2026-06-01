"""Thesis Builder: 대화형 가설 구조화 서비스 (설계 문서 2.3 + Phase A-MVP LLM 모드)"""

import json
import logging
import re
import uuid

from django.conf import settings

from packages.shared.api_request.circuit_breaker import CircuitBreakerError, get_circuit
from thesis.feature_flags import get_feature_flags
from thesis.models import HypothesisEvent, Thesis, ThesisIndicator, ThesisPremise
from thesis.services.builder_events import (
    EVENT_BUILDER_STARTED,
    EVENT_SUGGESTION_REQUEST_FAILED,
    EVENT_SUGGESTION_REQUEST_STARTED,
    EVENT_SUGGESTION_REQUEST_SUCCEEDED,
    EVENT_SUGGESTION_SELECTED,
    EVENT_SUGGESTION_TO_PRESET,
    log_event,
)
from thesis.services.builder_state import (
    MONITORING_PRESETS,
    BuilderPhase,
    ChatMessage,
    CollectedData,
    ConversationState,
    FallbackReason,
    IndicatorRecommendation,
    PremiseData,
    SuggestionData,
)
from thesis.services.indicator_matcher import (
    match_indicators_for_llm,
    match_indicators_for_premise,
)

logger = logging.getLogger(__name__)

# C-7: Guided Suggestion — low confidence 연속 시 제안할 인기 템플릿
POPULAR_TEMPLATES = [
    'AI 반도체 수요 증가로 관련주 상승',
    '금리 인하 기대감으로 부동산/REITs 반등',
    '원화 약세 지속으로 수출주 수혜',
    '고금리 장기화로 은행주 수혜',
]

# 방향 선택지
DIRECTION_CHOICES = [
    {'id': 'bullish', 'label': '계속 오른다'},
    {'id': 'bearish', 'label': '곧 꺾인다'},
    {'id': 'neutral', 'label': '잘 모르겠어'},
]

# 전제 카테고리 선택지
REASON_CHOICES = [
    {'id': 'election', 'label': '선거/정치 기대감 소멸', 'category': 'sentiment'},
    {'id': 'earnings', 'label': '기업 실적 부진', 'category': 'company'},
    {'id': 'foreign', 'label': '외국인 매도 전환', 'category': 'macro'},
    {'id': 'global', 'label': '글로벌 리스크', 'category': 'macro'},
    {'id': 'overheat', 'label': '과열/거품', 'category': 'sentiment'},
    {'id': 'supply', 'label': '수급 변화', 'category': 'market_data'},
    {'id': 'rate', 'label': '금리 변동', 'category': 'macro'},
    {'id': 'sector', 'label': '섹터 전환', 'category': 'sector'},
    {'id': 'custom', 'label': '다른 이유', 'type': 'text_input'},
]

TIMEFRAME_CHOICES = [
    {'id': 'short', 'label': '1개월 이내'},
    {'id': 'medium', 'label': '1~3개월'},
    {'id': 'half', 'label': '하반기 중'},
    {'id': 'year', 'label': '연말쯤'},
    {'id': 'skip', 'label': '모르겠어'},
]

MAGNITUDE_CHOICES = [
    {'id': 'mild', 'label': '살짝 조정'},
    {'id': 'moderate', 'label': '꽤 빠진다'},
    {'id': 'severe', 'label': '크게 빠진다'},
    {'id': 'skip', 'label': '모르겠어'},
]


def start_conversation(entry_source, source_news_id=None, user=None):
    """
    대화 시작. 첫 번째 메시지와 버튼 선택지 반환.
    """
    conv_id = str(uuid.uuid4())

    state = {
        'conv_id': conv_id,
        'entry_source': entry_source,
        'step': 1,
        'collected': {},
        'source_news_id': source_news_id,
    }

    if entry_source == 'news':
        if source_news_id:
            news_title = _get_news_title(source_news_id)
            state['collected']['news_title'] = news_title
            return {
                'conversation_state': state,
                'message': f'"{news_title}"\n이 흐름이 어떻게 될 것 같아요?',
                'buttons': DIRECTION_CHOICES,
                'selection_mode': 'single',
                'step': 1,
                'total_steps': 6,
            }
        return {
            'conversation_state': state,
            'message': '어떤 이슈에 대한 가설을 세울까요?',
            'buttons': [],
            'input_type': 'text',
            'step': 1,
            'total_steps': 6,
        }

    elif entry_source == 'free_input':
        return {
            'conversation_state': state,
            'message': '편하게 써주세요.\n한 줄이어도 좋고, 길게 써도 돼요.',
            'buttons': [],
            'input_type': 'text',
            'step': 1,
            'total_steps': 6,
        }

    return {
        'conversation_state': state,
        'message': '어떤 가설을 세울까요?',
        'buttons': [],
        'input_type': 'text',
        'step': 1,
        'total_steps': 6,
    }


def process_response(conversation_state, user_input, user=None):
    """
    사용자 선택/입력 처리 → 다음 단계 메시지 반환.
    """
    entry_source = conversation_state.get('entry_source', 'free_input')
    step = conversation_state.get('step', 1)
    collected = conversation_state.get('collected', {})

    if entry_source == 'news':
        return _process_news_path(conversation_state, step, collected, user_input, user)
    else:
        return _process_free_input_path(conversation_state, step, collected, user_input, user)


def _process_news_path(state, step, collected, user_input, user):
    """경로 1: 뉴스에서 시작."""

    if step == 1:
        # 방향 선택
        direction = user_input if isinstance(user_input, str) else user_input[0]
        collected['direction'] = direction
        state['collected'] = collected
        state['step'] = 2

        if direction == 'neutral':
            return {
                'conversation_state': state,
                'message': '양쪽 다 추적해볼까요?\n둘 다 만들어두면 비교하면서 볼 수 있어요.',
                'buttons': [
                    {'id': 'both', 'label': '둘 다 만들어줘'},
                    {'id': 'pick', 'label': '하나만 고를래'},
                ],
                'selection_mode': 'single',
                'step': 2,
                'total_steps': 6,
            }

        return {
            'conversation_state': state,
            'message': '왜 그렇게 생각하세요?\n여러 개 골라도 돼요.',
            'buttons': REASON_CHOICES,
            'selection_mode': 'multi',
            'step': 2,
            'total_steps': 6,
        }

    elif step == 2:
        action = user_input if isinstance(user_input, str) else user_input[0]

        # neutral 분기: both → bullish+bearish 2개 생성, pick → 방향 재선택
        if collected.get('direction') == 'neutral' and not collected.get('neutral_resolved'):
            if action == 'both':
                collected['create_counter_thesis'] = True
                collected['direction'] = 'bullish'
                collected['neutral_resolved'] = True
            elif action == 'pick':
                state['step'] = 1
                state['collected'] = collected
                return {
                    'conversation_state': state,
                    'message': '어떤 방향으로 갈 것 같아요?',
                    'buttons': [c for c in DIRECTION_CHOICES if c['id'] != 'neutral'],
                    'selection_mode': 'single',
                    'step': 1,
                    'total_steps': 6,
                }
            # both 선택 후 이유 선택 요청 (step 2 유지, neutral_resolved로 분기)
            state['collected'] = collected
            return {
                'conversation_state': state,
                'message': '왜 그렇게 생각하세요?\n여러 개 골라도 돼요.',
                'buttons': REASON_CHOICES,
                'selection_mode': 'multi',
                'step': 2,
                'total_steps': 6,
            }

        # 전제(이유) 선택
        reasons = user_input if isinstance(user_input, list) else [user_input]
        premises = _resolve_reasons(reasons)
        collected['premises'] = premises
        state['collected'] = collected
        state['step'] = 3

        return {
            'conversation_state': state,
            'message': '대략 언제쯤을 예상하세요?',
            'buttons': TIMEFRAME_CHOICES,
            'selection_mode': 'single',
            'step': 3,
            'total_steps': 6,
        }

    elif step == 3:
        # 시점 선택
        timeframe = user_input if isinstance(user_input, str) else user_input[0]
        collected['timeframe'] = timeframe if timeframe != 'skip' else ''
        state['collected'] = collected
        state['step'] = 4

        return {
            'conversation_state': state,
            'message': '강도는 어느 정도라고 생각하세요?',
            'buttons': MAGNITUDE_CHOICES,
            'selection_mode': 'single',
            'step': 4,
            'total_steps': 6,
        }

    elif step == 4:
        # 강도 선택
        magnitude = user_input if isinstance(user_input, str) else user_input[0]
        collected['magnitude'] = magnitude if magnitude != 'skip' else ''
        state['collected'] = collected
        state['step'] = 5

        # Gemini로 가설 구조화 + 지표 추천
        return _build_thesis_summary(state, collected, user)

    elif step == 5:
        # 확인 → 가설 생성
        action = user_input if isinstance(user_input, str) else user_input[0]

        if action == 'confirm':
            return _create_thesis(state, collected, user)
        elif action == 'modify':
            state['step'] = 2
            return {
                'conversation_state': state,
                'message': '어떤 부분을 수정할까요?',
                'buttons': REASON_CHOICES,
                'selection_mode': 'multi',
                'step': 2,
                'total_steps': 6,
            }

    return _default_response(state)


def _process_free_input_path(state, step, collected, user_input, user):
    """경로 2: 자유 입력."""

    if step == 1:
        # 자유 텍스트 → Gemini로 파싱
        text = user_input if isinstance(user_input, str) else str(user_input)
        collected['raw_text'] = text

        parsed = _parse_free_input(text)
        collected['parsed'] = parsed
        collected['direction'] = parsed.get('direction', 'bearish')
        collected['news_title'] = parsed.get('title', text[:50])
        state['collected'] = collected
        state['step'] = 2

        title = parsed.get('title', text[:50])
        direction_label = {'bullish': '상승', 'bearish': '하락', 'neutral': '중립'}.get(
            parsed.get('direction', 'bearish'), '하락'
        )

        premises_text = ''
        if parsed.get('premises'):
            for i, p in enumerate(parsed['premises'], 1):
                premises_text += f'\n    전제 {i}: {p}'

        return {
            'conversation_state': state,
            'message': f'정리해볼게요.\n\n    가설: {title}\n    방향: {direction_label}{premises_text}\n\n어때요?',
            'buttons': [
                {'id': 'confirm', 'label': '좋아, 이대로 가자'},
                {'id': 'modify', 'label': '수정할 부분 있어'},
                {'id': 'add_premise', 'label': '전제 추가할래'},
            ],
            'selection_mode': 'single',
            'step': 2,
            'total_steps': 6,
        }

    elif step == 2:
        action = user_input if isinstance(user_input, str) else user_input[0]

        if action == 'add_premise':
            state['step'] = 3
            return {
                'conversation_state': state,
                'message': '추가할 전제를 골라주세요.\n여러 개 골라도 돼요.',
                'buttons': REASON_CHOICES,
                'selection_mode': 'multi',
                'step': 3,
                'total_steps': 6,
            }
        elif action == 'modify':
            state['step'] = 1
            return {
                'conversation_state': state,
                'message': '다시 써주세요.',
                'buttons': [],
                'input_type': 'text',
                'step': 1,
                'total_steps': 6,
            }
        elif action == 'confirm':
            # 파싱된 전제가 있으면 활용
            parsed = collected.get('parsed', {})
            if parsed.get('premises'):
                collected['premises'] = [
                    {'content': p, 'category': 'custom'} for p in parsed['premises']
                ]
            state['collected'] = collected
            state['step'] = 4
            return {
                'conversation_state': state,
                'message': '대략 언제쯤을 예상하세요?',
                'buttons': TIMEFRAME_CHOICES,
                'selection_mode': 'single',
                'step': 4,
                'total_steps': 6,
            }

    elif step == 3:
        # 추가 전제 선택
        reasons = user_input if isinstance(user_input, list) else [user_input]
        new_premises = _resolve_reasons(reasons)
        existing = collected.get('premises', [])
        parsed = collected.get('parsed', {})
        if parsed.get('premises') and not existing:
            existing = [{'content': p, 'category': 'custom'} for p in parsed['premises']]
        collected['premises'] = existing + new_premises
        state['collected'] = collected
        state['step'] = 4

        return {
            'conversation_state': state,
            'message': '대략 언제쯤을 예상하세요?',
            'buttons': TIMEFRAME_CHOICES,
            'selection_mode': 'single',
            'step': 4,
            'total_steps': 6,
        }

    elif step == 4:
        timeframe = user_input if isinstance(user_input, str) else user_input[0]
        collected['timeframe'] = timeframe if timeframe != 'skip' else ''
        state['collected'] = collected
        state['step'] = 5

        return {
            'conversation_state': state,
            'message': '강도는 어느 정도라고 생각하세요?',
            'buttons': MAGNITUDE_CHOICES,
            'selection_mode': 'single',
            'step': 5,
            'total_steps': 6,
        }

    elif step == 5:
        magnitude = user_input if isinstance(user_input, str) else user_input[0]
        collected['magnitude'] = magnitude if magnitude != 'skip' else ''
        state['collected'] = collected
        state['step'] = 6

        return _build_thesis_summary(state, collected, user)

    elif step == 6:
        action = user_input if isinstance(user_input, str) else user_input[0]
        if action == 'confirm':
            return _create_thesis(state, collected, user)

    return _default_response(state)


def _resolve_reasons(reasons):
    """선택된 이유 ID 목록 → 전제 리스트로 변환."""
    reason_map = {r['id']: r for r in REASON_CHOICES}
    premises = []
    for r in reasons:
        if isinstance(r, dict):
            premises.append({
                'content': r.get('text', r.get('label', str(r))),
                'category': r.get('category', 'custom'),
            })
        elif r in reason_map:
            info = reason_map[r]
            premises.append({
                'content': info['label'],
                'category': info.get('category', 'custom'),
            })
        else:
            premises.append({
                'content': str(r),
                'category': 'custom',
            })
    return premises


def _parse_free_input(text):
    """Gemini로 자유 텍스트를 가설 구조로 파싱."""
    try:
        from google import genai
        from google.genai import types

        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            return _fallback_parse(text)

        client = genai.Client(api_key=api_key)

        # 프롬프트 인젝션 방지: 길이 제한 + 구분자 제거
        safe_text = text[:500].replace('```', '').replace('---', '').strip()

        prompt = f"""사용자가 투자 가설을 자유롭게 입력했어. 이걸 구조화해줘.

입력: "{safe_text}"

다음 JSON 형식으로만 반환해:
{{
  "title": "가설 제목 (짧게, 예: 'KOSPI 하락')",
  "direction": "bullish" | "bearish" | "neutral",
  "target": "대상 (예: 'KOSPI', '삼성전자', '2차전지 섹터')",
  "target_type": "index" | "stock" | "sector" | "macro",
  "thesis_type": "event" | "trend" | "comparison" | "divergence" | "custom",
  "premises": ["전제 1", "전제 2"]
}}

JSON만 반환해. 다른 텍스트 없이."""

        config = types.GenerateContentConfig(
            max_output_tokens=1000,
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        cb = get_circuit('gemini_thesis', failure_threshold=5, recovery_seconds=120)
        try:
            response = cb.call(
                client.models.generate_content,
                model='gemini-2.5-flash',
                contents=prompt,
                config=config,
            )
        except CircuitBreakerError as cb_exc:
            logger.warning(f"Gemini CB open (thesis): {cb_exc}")
            return _fallback_parse(text)

        response_text = response.text if hasattr(response, 'text') and response.text else ''
        if not response_text:
            return _fallback_parse(text)

        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return _fallback_parse(text)

        return json.loads(json_match.group())

    except Exception as e:
        logger.exception(f"Gemini parse failed: {e}")
        return _fallback_parse(text)


def _fallback_parse(text):
    """Gemini 실패 시 기본 파싱."""
    direction = 'bearish'
    if any(kw in text for kw in ['오른다', '상승', '반등', '올라', '오를']):
        direction = 'bullish'
    elif any(kw in text for kw in ['빠진다', '하락', '떨어', '꺾인다', '조정']):
        direction = 'bearish'

    return {
        'title': text[:50],
        'direction': direction,
        'target': '',
        'target_type': 'index',
        'thesis_type': 'custom',
        'premises': [text],
    }


def _build_thesis_summary(state, collected, user):
    """수집된 데이터로 가설 요약 + 지표 추천."""
    premises = collected.get('premises', [])
    direction = collected.get('direction', 'bearish')
    title = collected.get('news_title', collected.get('parsed', {}).get('title', ''))

    # 구조화 시도 (Gemini)
    if not title:
        title = _generate_title(premises, direction)

    # 각 전제에 대한 지표 추천
    recommended_indicators = []
    for premise in premises:
        content = premise.get('content', '') if isinstance(premise, dict) else str(premise)
        indicators = match_indicators_for_premise(content)
        recommended_indicators.extend(indicators)

    # 중복 제거
    seen = set()
    unique_indicators = []
    for ind in recommended_indicators:
        if ind['name'] not in seen:
            unique_indicators.append(ind)
            seen.add(ind['name'])

    collected['recommended_indicators'] = unique_indicators[:5]
    collected['title'] = title
    state['collected'] = collected

    # 마지막 확인 단계
    direction_label = {'bullish': '상승', 'bearish': '하락', 'neutral': '중립'}.get(direction, '')
    timeframe_label = _get_timeframe_label(collected.get('timeframe', ''))
    magnitude_label = _get_magnitude_label(collected.get('magnitude', ''))

    premises_text = ''
    for i, p in enumerate(premises, 1):
        content = p.get('content', '') if isinstance(p, dict) else str(p)
        premises_text += f'\n    · {content}'

    indicators_text = ''
    for ind in unique_indicators[:3]:
        indicators_text += f'\n    · {ind["name"]}'

    meta_parts = [f'{direction_label}']
    if timeframe_label:
        meta_parts.append(timeframe_label)
    if magnitude_label:
        meta_parts.append(magnitude_label)

    # step은 호출자가 이미 설정한 값을 유지 (news: 5, free_input: 6)
    # _build_thesis_summary에서 step을 변경하지 않음

    return {
        'conversation_state': state,
        'message': (
            f'가설 등록 준비 완료!\n\n'
            f'    가설: {title}\n'
            f'    {" | ".join(meta_parts)}\n\n'
            f'    전제:{premises_text}\n\n'
            f'    AI 추천 지표:{indicators_text}\n\n'
            f'    지표는 언제든 수정할 수 있어요.\n\n'
            f'어때요?'
        ),
        'buttons': [
            {'id': 'confirm', 'label': '좋아, 이대로 가자'},
            {'id': 'modify', 'label': '수정할 부분 있어'},
        ],
        'selection_mode': 'single',
        'step': state.get('step'),
        'total_steps': 6,
        'preview': {
            'title': title,
            'direction': direction,
            'premises': premises,
            'indicators': unique_indicators[:5],
        },
    }


def _create_thesis(state, collected, user):
    """실제 Thesis + Premise + Indicator 생성."""
    if not user:
        return {
            'conversation_state': state,
            'error': '로그인이 필요합니다.',
            'done': False,
        }

    direction = collected.get('direction', 'bearish')
    parsed = collected.get('parsed', {})
    title = collected.get('title', parsed.get('title', ''))
    target = parsed.get('target', collected.get('news_title', title))
    target_type = parsed.get('target_type', 'index')
    thesis_type = parsed.get('thesis_type', 'custom')

    timeframe_label = _get_timeframe_label(collected.get('timeframe', ''))
    magnitude_label = _get_magnitude_label(collected.get('magnitude', ''))

    thesis = Thesis.objects.create(
        user=user,
        title=title or target[:200],
        description=collected.get('raw_text', ''),
        direction=direction,
        target=target[:100],
        target_type=target_type,
        thesis_type=thesis_type,
        entry_source=state.get('entry_source', 'free_input'),
        expected_timeframe=timeframe_label,
        expected_magnitude=magnitude_label,
        source_news_id=state.get('source_news_id'),
        status='active',
    )

    # 전제 생성
    premises = collected.get('premises', [])
    created_premises = []
    for i, p in enumerate(premises):
        content = p.get('content', '') if isinstance(p, dict) else str(p)
        category = p.get('category', 'custom') if isinstance(p, dict) else 'custom'
        premise = ThesisPremise.objects.create(
            thesis=thesis,
            content=content,
            category=category,
            order=i,
        )
        created_premises.append(premise)

    # 추천 지표 자동 생성
    indicators = collected.get('recommended_indicators', [])
    created_indicators = []
    for ind in indicators:
        ti = ThesisIndicator.objects.create(
            thesis=thesis,
            name=ind['name'],
            indicator_type=ind.get('indicator_type', 'custom'),
            data_source=ind.get('data_source', 'manual'),
            data_params=ind.get('data_params', {}),
            support_direction=ind.get('support_direction', 'positive'),
            recommendation_reason=ind.get('reason', ''),
        )
        created_indicators.append(ti)

    # HypothesisEvent 기록
    try:
        HypothesisEvent.objects.create(
            user=user,
            thesis=thesis,
            event_type='thesis_created',
            event_data={
                'entry_source': state.get('entry_source'),
                'premise_count': len(created_premises),
                'indicator_count': len(created_indicators),
            },
        )
        # premise_added / indicator_added 이벤트 (InvestorDNA 집계에 필요)
        for premise in created_premises:
            HypothesisEvent.objects.create(
                user=user,
                thesis=thesis,
                event_type='premise_added',
                event_data={
                    'premise_id': str(premise.id),
                    'category': premise.category,
                },
            )
        for ti in created_indicators:
            HypothesisEvent.objects.create(
                user=user,
                thesis=thesis,
                event_type='ai_suggestion_accepted',
                event_data={
                    'indicator_id': str(ti.id),
                    'indicator_type': ti.indicator_type,
                    'data_source': ti.data_source,
                },
            )
    except Exception as e:
        logger.warning(f"Failed to record thesis_created event: {e}")

    # neutral → both 선택 시 반대 방향 가설도 생성
    counter_thesis_id = None
    if collected.get('create_counter_thesis'):
        counter_direction = 'bearish' if direction == 'bullish' else 'bullish'
        counter_thesis = Thesis.objects.create(
            user=user,
            title=title or target[:200],
            description=collected.get('raw_text', ''),
            direction=counter_direction,
            target=target[:100],
            target_type=target_type,
            thesis_type=thesis_type,
            entry_source=state.get('entry_source', 'free_input'),
            expected_timeframe=timeframe_label,
            expected_magnitude=magnitude_label,
            source_news_id=state.get('source_news_id'),
            status='active',
            copied_from=thesis,
        )
        # 전제/지표 복제
        for p in created_premises:
            ThesisPremise.objects.create(
                thesis=counter_thesis,
                content=p.content,
                category=p.category,
                order=p.order,
            )
        for ind in indicators:
            # 반대 방향이므로 support_direction 반전
            orig_dir = ind.get('support_direction', 'positive')
            flipped_dir = 'negative' if orig_dir == 'positive' else 'positive'
            ThesisIndicator.objects.create(
                thesis=counter_thesis,
                name=ind['name'],
                indicator_type=ind.get('indicator_type', 'custom'),
                data_source=ind.get('data_source', 'manual'),
                data_params=ind.get('data_params', {}),
                support_direction=flipped_dir,
                recommendation_reason=ind.get('reason', ''),
            )
        try:
            HypothesisEvent.objects.create(
                user=user,
                thesis=counter_thesis,
                event_type='thesis_created',
                event_data={
                    'entry_source': state.get('entry_source'),
                    'counter_of': str(thesis.id),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record counter thesis event: {e}")
        counter_thesis_id = str(counter_thesis.id)

    result = {
        'conversation_state': state,
        'thesis_id': str(thesis.id),
        'done': True,
        'message': '가설이 등록되었어요! 관제실에서 지표 변화를 추적할 수 있어요.',
    }
    if counter_thesis_id:
        result['counter_thesis_id'] = counter_thesis_id
        result['message'] = '양쪽 가설이 등록되었어요! 관제실에서 비교하며 추적할 수 있어요.'
    return result


def _get_news_title(news_id):
    """뉴스 기사 제목 조회."""
    try:
        from services.news.models import NewsArticle
        article = NewsArticle.objects.get(id=news_id)
        return article.title
    except Exception:
        return ''


def _generate_title(premises, direction):
    """전제 목록에서 가설 제목 생성."""
    if not premises:
        return '새 가설'
    first = premises[0]
    content = first.get('content', '') if isinstance(first, dict) else str(first)
    return content[:50]


def _get_timeframe_label(value):
    """timeframe ID → 라벨."""
    mapping = {r['id']: r['label'] for r in TIMEFRAME_CHOICES if r['id'] != 'skip'}
    return mapping.get(value, value or '')


def _get_magnitude_label(value):
    """magnitude ID → 라벨."""
    mapping = {r['id']: r['label'] for r in MAGNITUDE_CHOICES if r['id'] != 'skip'}
    return mapping.get(value, value or '')


def _default_response(state):
    """예상치 못한 단계에서의 기본 응답."""
    return {
        'conversation_state': state,
        'message': '다시 시작해볼까요?',
        'buttons': [],
        'step': state.get('step', 1),
        'total_steps': 6,
    }


# ──────────────────────────────────────────────
# LLM Mode
# ──────────────────────────────────────────────

def start_llm_conversation(entry_source, source_news_id=None):
    """LLM 모드 대화 시작. ConversationState 생성 → 초기 메시지 반환."""
    conv_id = str(uuid.uuid4())
    state = ConversationState(
        conv_id=conv_id,
        entry_source=entry_source,
        source_news_id=str(source_news_id) if source_news_id else None,
    )

    log_event(EVENT_BUILDER_STARTED, {
        'conv_id': conv_id,
        'entry_source': entry_source,
        'mode': 'llm',
    })

    if entry_source == 'news' and source_news_id:
        news_title = _get_news_title(source_news_id)
        return {
            'conversation_state': state.model_dump(),
            'message': f'"{news_title}" — 이 흐름에 대한 생각을 자유롭게 써주세요.',
            'buttons': [],
            'input_type': 'text',
            'phase': 'proposal',
        }

    return {
        'conversation_state': state.model_dump(),
        'message': '어떤 투자 아이디어가 있으세요?\n한 줄이면 충분해요.',
        'buttons': [],
        'input_type': 'text',
        'phase': 'proposal',
    }


def process_llm_turn(raw_state, user_input, user=None):
    """LLM 모드 턴 처리. phase 기반 분기."""
    try:
        state = ConversationState.model_validate(raw_state)
    except Exception as e:
        logger.exception(f"State validation failed: {e}")
        return _fallback_to_wizard(raw_state, user_input, FallbackReason.STATE_ERROR)

    # guided suggestion 버튼 클릭 → 해당 텍스트로 proposal
    text = user_input if isinstance(user_input, str) else str(user_input)
    if text == '__guided__':
        # label이 전송됨 (프론트에서 button.label을 user_input으로 전송)
        text = user_input

    # history에 사용자 메시지 추가
    state.history.append(ChatMessage(role='user', content=text))
    state.turn_count += 1

    # turn_count 방어 (무한 루프 방지)
    if state.turn_count > 20:
        return _fallback_to_wizard(state, text, FallbackReason.STATE_ERROR)

    phase = state.phase

    # suggestions phase: 카드 선택 또는 전제 multi-select 처리
    if phase == BuilderPhase.SUGGESTIONS.value:
        return _handle_suggestion_select(state, user_input, user)

    # fallback phase에서 사용자 선택 처리
    if phase == BuilderPhase.FALLBACK.value:
        return _handle_fallback_choice(state, text, user)

    if phase == BuilderPhase.PRESET.value:
        # 프리셋 버튼 입력이면 기존 로직
        if _detect_preset(text):
            return _handle_preset(state, text)
        # 자유 텍스트 → 대화형 처리
        return _handle_conversational_edit(state, text, user)

    elif phase == BuilderPhase.CONFIRM.value:
        if _is_confirm_intent(text):
            return _handle_confirm(state, user)
        elif _is_restart_intent(text):
            state.phase = BuilderPhase.PROPOSAL.value
            state.collected = CollectedData()
            state.history = []
            state.turn_count = 0
            return {
                'conversation_state': state.model_dump(),
                'message': '다시 시작할게요! 어떤 아이디어가 있으세요?',
                'buttons': [],
                'input_type': 'text',
                'phase': 'proposal',
            }
        # 자유 텍스트 → 대화형 처리
        return _handle_conversational_edit(state, text, user)
    else:
        # PROPOSAL (default)
        return _handle_proposal(state, text)


def _handle_proposal(state, user_input):
    """One-shot proposal: Gemini 호출 → normalize → validate → merge → match."""
    from thesis.services.builder_events import (
        EVENT_LLM_PARSE_FAILED,
        EVENT_PROPOSAL_GENERATED,
    )
    from thesis.services.llm_postprocess import (
        merge_to_collected,
        normalize_llm_output,
        validate_llm_output,
    )
    from thesis.services.prompt_builder import build_system_prompt, call_gemini

    flags = get_feature_flags()

    # 1. 시스템 프롬프트 빌드
    system_prompt = build_system_prompt(state, flags)

    # 2. Gemini 호출
    history_dicts = [{'role': m.role, 'content': m.content} for m in state.history]
    raw_output = call_gemini(system_prompt, history_dicts)

    if raw_output is None:
        return _fallback_to_wizard(state, user_input, FallbackReason.LLM_API_ERROR)

    # 3. normalize → validate
    normalized = normalize_llm_output(raw_output)
    validated, warnings, errors = validate_llm_output(normalized)

    if errors:
        log_event(EVENT_LLM_PARSE_FAILED, {
            'conv_id': state.conv_id,
            'errors': errors,
            'warnings': warnings,
        })
        return _fallback_to_wizard(state, user_input, FallbackReason.VALIDATION_ERROR)

    # 4. merge to collected
    state.collected = merge_to_collected(state.collected, validated)

    # 5. match indicators (PK → text 2단계)
    indicator_recommendations = match_indicators_for_llm(state.collected)

    # 5.1 매칭된 indicator_db_id를 collected에 저장 (사용자가 수정 가능)
    matched_ids = []
    for rec in indicator_recommendations:
        ind = rec.get('indicator', {})
        db_id = ind.get('id') if isinstance(ind, dict) else None
        if db_id:
            matched_ids.append(db_id)
    state.collected.selected_indicator_ids = matched_ids

    # 6. 응답 메시지
    confidence = validated.get('confidence', 'medium')
    message = validated.get('message', '')
    state.history.append(ChatMessage(role='assistant', content=message))

    # 7. confidence → phase 전이
    if confidence == 'low':
        state.phase = BuilderPhase.PROPOSAL.value

        # C-7: Guided Suggestion — low 2회 연속 시 인기 템플릿 제안
        guided_buttons = []
        if state.turn_count >= 2 and flags.get('GUIDED_SUGGESTION'):
            message += '\n\n이런 가설은 어떨까요?'
            guided_buttons = [
                {'id': '__guided__', 'label': t}
                for t in POPULAR_TEMPLATES
            ]
        elif state.turn_count >= 3:
            message += '\n\n예: "삼성전자 2분기 반등", "금리 인하 수혜주", "비만치료제 테마"'

        log_event(EVENT_PROPOSAL_GENERATED, {
            'conv_id': state.conv_id,
            'confidence': confidence,
            'premise_count': 0,
            'turn_count': state.turn_count,
        })

        return {
            'conversation_state': state.model_dump(),
            'message': message,
            'buttons': guided_buttons,
            'input_type': 'text',
            'confidence': confidence,
            'phase': 'proposal',
        }

    # high/medium → PRESET
    state.phase = BuilderPhase.PRESET.value

    log_event(EVENT_PROPOSAL_GENERATED, {
        'conv_id': state.conv_id,
        'confidence': confidence,
        'premise_count': len(validated.get('premises', [])),
        'turn_count': state.turn_count,
    })

    preset_buttons = [
        {'id': 'short', 'label': MONITORING_PRESETS['short']['label']},
        {'id': 'medium', 'label': MONITORING_PRESETS['medium']['label']},
        {'id': 'long', 'label': MONITORING_PRESETS['long']['label']},
    ]

    return {
        'conversation_state': state.model_dump(),
        'message': message,
        'buttons': preset_buttons,
        'selection_mode': 'single',
        'confidence': confidence,
        'needs_preset': True,
        'indicator_recommendations': indicator_recommendations,
        'phase': 'preset',
    }


def _handle_preset(state, user_input):
    """프리셋 선택 → timeframe/magnitude/sensitivity 설정 → CONFIRM."""
    from thesis.services.builder_events import EVENT_PRESET_SELECTED

    preset_key = _detect_preset(user_input)
    if not preset_key:
        preset_buttons = [
            {'id': 'short', 'label': MONITORING_PRESETS['short']['label']},
            {'id': 'medium', 'label': MONITORING_PRESETS['medium']['label']},
            {'id': 'long', 'label': MONITORING_PRESETS['long']['label']},
        ]
        return {
            'conversation_state': state.model_dump(),
            'message': '모니터링 기간을 선택해주세요.',
            'buttons': preset_buttons,
            'selection_mode': 'single',
            'needs_preset': True,
            'phase': 'preset',
        }

    preset = MONITORING_PRESETS[preset_key]
    state.collected.timeframe = preset['timeframe']
    state.collected.magnitude = preset['magnitude']
    state.collected.sensitivity = preset['sensitivity']
    state.phase = BuilderPhase.CONFIRM.value

    log_event(EVENT_PRESET_SELECTED, {
        'conv_id': state.conv_id,
        'preset': preset_key,
    })

    direction_label = {'bullish': '상승', 'bearish': '하락'}.get(
        state.collected.direction, ''
    )
    summary_parts = [
        f'가설: {state.collected.title or state.collected.target}',
        f'방향: {direction_label}',
        f'모니터링: {preset["label"]}',
    ]
    if state.collected.premises:
        summary_parts.append(f'전제: {len(state.collected.premises)}개')

    message = '등록 준비 완료!\n\n' + '\n'.join(f'    {p}' for p in summary_parts) + '\n\n등록할까요?'
    state.history.append(ChatMessage(role='assistant', content=message))

    return {
        'conversation_state': state.model_dump(),
        'message': message,
        'buttons': [
            {'id': 'confirm', 'label': '등록'},
            {'id': 'restart', 'label': '다시 만들기'},
        ],
        'selection_mode': 'single',
        'phase': 'confirm',
    }


def _handle_confirm(state, user):
    """등록 확인 → validate → DB 저장."""
    from thesis.services.builder_events import (
        EVENT_CONFIRM_CLICKED,
        EVENT_THESIS_CREATED,
    )

    log_event(EVENT_CONFIRM_CLICKED, {'conv_id': state.conv_id})

    collected = state.collected
    if not collected.direction or not collected.target or not collected.premises:
        return _fallback_to_wizard(state, '', FallbackReason.VALIDATION_ERROR)

    result = _create_thesis_from_llm(state, user)
    if 'error' in result:
        return result

    state.phase = BuilderPhase.COMPLETE.value

    log_event(EVENT_THESIS_CREATED, {
        'conv_id': state.conv_id,
        'thesis_id': result.get('thesis_id'),
    })

    return {
        'conversation_state': state.model_dump(),
        'message': '가설이 등록되었어요! 관제실에서 지표 변화를 추적할 수 있어요.',
        'thesis_id': result['thesis_id'],
        'is_complete': True,
        'done': True,
        'created_thesis': {
            'thesis_id': result['thesis_id'],
            'title': collected.title or collected.target,
            'dashboard_url': f'/thesis/{result["thesis_id"]}',
        },
        'phase': 'complete',
    }


def _create_thesis_from_llm(state, user):
    """LLM 모드에서 Thesis + Premise + Indicator 생성. 기존 _create_thesis() 래핑."""
    if not user:
        return {'error': '로그인이 필요합니다.', 'done': False}

    collected = state.collected
    from thesis.services.prompt_builder import get_indicator_by_id

    # thesis_type: list → DB 단일값 매핑
    thesis_type_raw = collected.thesis_type[0] if collected.thesis_type else 'custom'
    THESIS_TYPE_MAP = {
        'earnings': 'custom', 'flow': 'custom', 'macro': 'custom',
        'chain': 'custom', 'event': 'event',
    }
    db_thesis_type = THESIS_TYPE_MAP.get(thesis_type_raw, 'custom')

    thesis = Thesis.objects.create(
        user=user,
        title=(collected.title or collected.target or '')[:200],
        direction=collected.direction,
        target=(collected.target or '')[:100],
        target_type=collected.target_type or 'index',
        thesis_type=db_thesis_type,
        entry_source=state.entry_source,
        expected_timeframe=collected.timeframe or '',
        expected_magnitude=collected.magnitude or '',
        source_news_id=state.source_news_id,
        status='active',
    )

    # 전제 생성
    created_premises = []
    for i, p in enumerate(collected.premises):
        premise = ThesisPremise.objects.create(
            thesis=thesis,
            content=p.title,
            category='custom',
            order=i,
        )
        created_premises.append(premise)

    # 지표 생성 — selected_indicator_ids 우선, 없으면 premises에서 추출
    created_indicators = []
    indicator_ids_to_create = collected.selected_indicator_ids
    if not indicator_ids_to_create:
        for p in collected.premises:
            for rec in p.recommended_indicators:
                if rec.indicator_db_id:
                    indicator_ids_to_create.append(rec.indicator_db_id)

    # indicator_db_id → target_symbol / why 매핑 구축 (premises에서 추출)
    symbol_map = {}  # {db_id: 'META'}
    why_map = {}     # {db_id: '추천 이유'}
    for p in collected.premises:
        for rec in p.recommended_indicators:
            if rec.indicator_db_id:
                if rec.target_symbol:
                    symbol_map[rec.indicator_db_id] = rec.target_symbol
                if rec.why:
                    why_map.setdefault(rec.indicator_db_id, rec.why)

    seen_indicator_ids = set()
    for db_id in indicator_ids_to_create:
        if db_id not in seen_indicator_ids:
            cat_ind = get_indicator_by_id(db_id)
            if cat_ind:
                # data_params에 target_symbol 병합
                data_params = dict(cat_ind.get('data_params', {}))
                target_sym = symbol_map.get(db_id)
                if target_sym and 'symbol' not in data_params:
                    data_params['symbol'] = target_sym

                indicator_name = cat_ind['name']
                if target_sym:
                    indicator_name = f'{cat_ind["name"]} ({target_sym})'

                ti = ThesisIndicator.objects.create(
                    thesis=thesis,
                    name=indicator_name,
                    indicator_type=cat_ind.get('category', 'custom'),
                    data_source=cat_ind.get('data_source', 'manual'),
                    data_params=data_params,
                    support_direction=cat_ind.get('support_direction', 'positive'),
                    recommendation_reason=why_map.get(db_id, ''),
                )
                created_indicators.append(ti)
                seen_indicator_ids.add(db_id)

    # HypothesisEvent
    try:
        HypothesisEvent.objects.create(
            user=user,
            thesis=thesis,
            event_type='thesis_created',
            event_data={
                'entry_source': state.entry_source,
                'mode': 'llm',
                'premise_count': len(created_premises),
                'indicator_count': len(created_indicators),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to record thesis_created event: {e}")

    return {'thesis_id': str(thesis.id)}


def _handle_fallback_choice(state, user_input, user):
    """fallback phase에서 wizard/retry 선택 처리."""
    text = user_input.lower().strip()

    if text in ('retry', '다시 시도', '다시'):
        # LLM 재시도: phase를 proposal로 되돌리고 마지막 user 메시지로 재시도
        state.phase = BuilderPhase.PROPOSAL.value
        # history에서 마지막 user 메시지를 찾아서 재사용
        last_user_msg = ''
        for msg in reversed(state.history):
            if msg.role == 'user' and msg.content not in ('retry', '다시 시도', '다시'):
                last_user_msg = msg.content
                break
        if last_user_msg:
            return _handle_proposal(state, last_user_msg)
        # 원래 입력이 없으면 텍스트 입력 요청
        return {
            'conversation_state': state.model_dump(),
            'message': '다시 시도할게요! 어떤 아이디어가 있으세요?',
            'buttons': [],
            'input_type': 'text',
            'phase': 'proposal',
        }

    # wizard 선택 또는 기타 → wizard 전환
    return _switch_to_wizard(state)


def _switch_to_wizard(state):
    """LLM state → wizard state 변환 후 wizard 시작 응답."""
    entry_source = state.entry_source if hasattr(state, 'entry_source') else 'free_input'
    source_news_id = state.source_news_id if hasattr(state, 'source_news_id') else None
    conv_id = state.conv_id if hasattr(state, 'conv_id') else str(uuid.uuid4())

    wizard_state = {
        'conv_id': conv_id,
        'entry_source': entry_source,
        'step': 1,
        'collected': {},
        'source_news_id': source_news_id,
    }

    # wizard 시작 응답 (start_conversation과 동일)
    result = start_conversation(entry_source, source_news_id)
    result['conversation_state']['conv_id'] = conv_id
    return result


def _fallback_to_wizard(state, user_input, reason):
    """LLM 실패 시 fallback 선택 화면 반환."""
    from thesis.services.builder_events import EVENT_FALLBACK_TRIGGERED

    conv_id = state.conv_id if hasattr(state, 'conv_id') else state.get('conv_id', '')
    log_event(EVENT_FALLBACK_TRIGGERED, {
        'conv_id': conv_id,
        'reason': reason.value if isinstance(reason, FallbackReason) else str(reason),
    })

    # LLM state 유지 (retry 가능하도록)
    if hasattr(state, 'model_dump'):
        state.phase = BuilderPhase.FALLBACK.value
        response_state = state.model_dump()
    else:
        # dict state (state validation 실패 시)
        entry_source = state.get('entry_source', 'free_input') if isinstance(state, dict) else 'free_input'
        source_news_id = state.get('source_news_id') if isinstance(state, dict) else None
        response_state = {
            'conv_id': conv_id or str(uuid.uuid4()),
            'entry_source': entry_source,
            'mode': 'llm',
            'phase': 'fallback',
            'history': [],
            'collected': {},
            'turn_count': 0,
            'source_news_id': source_news_id,
        }

    return {
        'conversation_state': response_state,
        'message': 'AI 분석에 문제가 생겼어요.\n단계별로 진행하거나, 다시 시도할 수 있어요.',
        'buttons': [
            {'id': 'wizard', 'label': '단계별로 진행'},
            {'id': 'retry', 'label': '다시 시도'},
        ],
        'selection_mode': 'single',
        'phase': 'fallback',
        'fallback_reason': reason.value if isinstance(reason, FallbackReason) else str(reason),
    }


def _detect_preset(text):
    """사용자 입력에서 프리셋 키 탐지."""
    text_lower = text.lower().strip()
    if text_lower in ('short', '단기'):
        return 'short'
    elif text_lower in ('medium', '중기'):
        return 'medium'
    elif text_lower in ('long', '장기'):
        return 'long'
    return None


def _is_confirm_intent(text):
    """등록 의도 탐지."""
    return text.lower().strip() in ('confirm', '등록', '좋아', '네', '예', 'yes', 'ok')


def _is_restart_intent(text):
    """재시작 의도 탐지."""
    return text.lower().strip() in ('restart', '다시', '다시 만들기', '처음부터')


# ──────────────────────────────────────────────
# Conversational Edit (대화형 가설 수정)
# ──────────────────────────────────────────────

def _handle_conversational_edit(state, user_input, user):
    """
    PRESET/CONFIRM phase에서 자유 텍스트 입력 처리.
    1) Intent 분류 (Gemini light)
    2) Intent별 분기: question / modify_premise / modify_indicator / modify_thesis / proceed / restart
    """
    from thesis.services.prompt_builder import (
        build_intent_classification_prompt,
        call_gemini_light,
    )

    collected = state.collected

    # 최근 대화 이력 (마지막 8개 — 맥락 유지 + 토큰 절약)
    recent_history = state.history[-8:] if len(state.history) > 8 else list(state.history)

    # 1. Intent 분류 (이력 포함)
    intent_prompt = build_intent_classification_prompt(state.phase, collected)
    raw_intent = call_gemini_light(intent_prompt, user_input, history=recent_history)

    intent = 'question'  # default
    detail = user_input
    if raw_intent:
        try:
            import json as _json
            import re as _re
            json_match = _re.search(r'\{.*\}', raw_intent, _re.DOTALL)
            if json_match:
                parsed = _json.loads(json_match.group())
                intent = parsed.get('intent', 'question')
                detail = parsed.get('detail', user_input)
        except Exception:
            pass

    logger.info(f"Conversational edit: intent={intent}, detail={detail[:50]}")

    # 2. Intent별 처리
    if intent == 'proceed':
        return _handle_proceed_intent(state, detail, user)

    if intent == 'restart':
        state.phase = BuilderPhase.PROPOSAL.value
        state.collected = CollectedData()
        state.history = []
        state.turn_count = 0
        return {
            'conversation_state': state.model_dump(),
            'message': '다시 시작할게요! 어떤 아이디어가 있으세요?',
            'buttons': [],
            'input_type': 'text',
            'phase': 'proposal',
        }

    if intent == 'question':
        return _handle_question(state, user_input)

    if intent == 'modify_premise':
        return _handle_modify_premise(state, user_input)

    if intent == 'modify_indicator':
        return _handle_modify_indicator(state, user_input)

    if intent == 'modify_thesis':
        return _handle_modify_thesis(state, user_input)

    # fallback → 질문으로 처리
    return _handle_question(state, user_input)


def _handle_proceed_intent(state, detail, user):
    """proceed intent → 현재 phase에 맞는 진행 처리."""
    phase = state.phase
    if phase == BuilderPhase.PRESET.value:
        # 프리셋 감지 시도
        preset_key = _detect_preset(detail)
        if preset_key:
            return _handle_preset(state, preset_key)
        # "좋아", "이대로" 같은 경우 → medium 프리셋 기본 적용
        return _handle_preset(state, 'medium')
    elif phase == BuilderPhase.CONFIRM.value:
        return _handle_confirm(state, user)
    return _return_current_phase(state)


def _handle_question(state, user_input):
    """질문 → Gemini가 가설 카드 + 뉴스 + 대화 이력 맥락에서 답변."""
    from thesis.services.prompt_builder import (
        build_question_answer_prompt,
        call_gemini_light,
    )

    recent_history = state.history[-8:] if len(state.history) > 8 else list(state.history)

    # suggestions 데이터 + 뉴스 원문 전달
    suggestions = state.collected.suggestions if state.collected.suggestions else None
    source_news_id = state.source_news_id

    system_prompt = build_question_answer_prompt(
        state.collected,
        suggestions=suggestions,
        source_news_id=source_news_id,
    )
    answer = call_gemini_light(system_prompt, user_input, history=recent_history)

    if not answer:
        answer = '죄송해요, 답변을 생성하지 못했어요. 다시 질문해주세요.'

    state.history.append(ChatMessage(role='assistant', content=answer))

    return _return_current_phase(state, message=answer)


def _handle_modify_premise(state, user_input):
    """전제 추가/삭제 → Gemini가 delta JSON 생성 → collected/suggestions에 적용."""
    from thesis.services.indicator_matcher import match_indicators_for_llm
    from thesis.services.prompt_builder import (
        call_gemini_light,
        get_indicator_by_id,
    )

    # suggestions phase에서는 suggestion 카드의 전제 목록을 수정 대상으로 사용
    has_suggestions = bool(state.collected.suggestions)
    target_suggestion_idx = None

    if has_suggestions:
        # 사용자 입력에서 방향(상승/하락) 감지 → 해당 suggestion 찾기
        text_lower = user_input.lower()
        for idx, s in enumerate(state.collected.suggestions):
            if s.direction == 'bearish' and any(kw in text_lower for kw in ['하락', 'bearish', '부정', '리스크', '위축', '둔화']):
                target_suggestion_idx = idx
                break
            elif s.direction == 'bullish' and any(kw in text_lower for kw in ['상승', 'bullish', '긍정', '수혜', '성장']):
                target_suggestion_idx = idx
                break
        # 방향 키워드 없으면 마지막 suggestion (보통 bearish)
        if target_suggestion_idx is None:
            target_suggestion_idx = len(state.collected.suggestions) - 1

    # 수정 대상 전제 목록 결정
    if has_suggestions and target_suggestion_idx is not None:
        modify_target = state.collected.suggestions[target_suggestion_idx]
        current_premises_for_prompt = modify_target.premises
    else:
        current_premises_for_prompt = state.collected.premises

    # Gemini 호출 (수정 대상 전제 목록을 프롬프트에 포함)
    recent_history = state.history[-6:] if len(state.history) > 6 else list(state.history)

    # 프롬프트에 현재 전제 목록 직접 포함
    premises_desc = '\n'.join(
        f'{i}. {p.title}' for i, p in enumerate(current_premises_for_prompt)
    ) if current_premises_for_prompt else '(없음)'

    from thesis.services.prompt_builder import build_indicator_block
    indicator_block = build_indicator_block()
    system_prompt = f"""현재 가설의 전제 목록 (이미 존재하는 전제):
{premises_desc}

사용자가 전제를 수정하려고 합니다.
아래 JSON 형식으로만 응답하세요:

{{"action": "add" 또는 "remove" 또는 "none",
 "premise_title": "전제 제목 (15~30자)",
 "premise_description": "전제를 뒷받침하는 구체적 근거 (1~2문장)",
 "target_index": 삭제 시 인덱스 번호 (0부터),
 "recommended_indicators": [
   {{"indicator_db_id": 숫자, "why": "이유 1문장", "signal_type": "leading|coincident|lagging"}}
 ],
 "message": "사용자에게 보여줄 대화 메시지 (3~5문장). 반드시 아래 내용을 포함:
   1) 왜 이 전제를 추가/삭제하는지 (기존 전제와의 관계, 빠져있던 관점)
   2) 이 전제가 가설 전체에 어떤 의미를 더하는지
   3) 추천한 지표가 이 전제를 어떻게 검증하는지"}}

## 중복 방지 규칙 (매우 중요)
1. **위 전제 목록과 동일하거나 유사한 내용은 절대 추가하지 마세요.**
   - 같은 주제를 다른 표현으로 바꾸는 것도 중복입니다.
   - 예: "기업 실적 개선"이 이미 있으면 "기업 이익 증가"는 중복.
   - 예: "금리 인하 기대감"이 이미 있으면 "통화 완화 정책"은 중복.
2. **더 이상 의미 있는 새 전제를 추가할 수 없으면 action을 "none"으로 설정하고,
   message에 "충분한 근거가 마련된 것 같아요. 혹시 직접 추가하고 싶은 전제가 있으세요?"로 답하세요.**
3. 전제는 해당 가설의 방향(상승/하락)에 맞는 **구체적이고 차별화된 논거**여야 합니다.

{indicator_block}

**카탈로그에 있는 지표만 사용하세요. 목록에 없는 지표를 만들지 마세요.**
**당신이 아는 지식을 활용하여 구체적인 근거와 수치를 포함하세요.**"""

    raw = call_gemini_light(system_prompt, user_input, history=recent_history)

    if not raw:
        return _return_current_phase(state, message='전제 수정을 처리하지 못했어요. 다시 시도해주세요.')

    try:
        import json as _json
        import re as _re
        json_match = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if not json_match:
            raise ValueError('No JSON found')
        delta = _json.loads(json_match.group())
    except Exception:
        return _return_current_phase(state, message='전제 수정을 이해하지 못했어요. 좀 더 구체적으로 말씀해주세요.')

    action = delta.get('action', 'add')
    message = delta.get('message', '')

    # "none" → 더 추가할 전제가 없음
    if action == 'none':
        if not message:
            message = '충분한 근거가 마련된 것 같아요. 혹시 직접 추가하고 싶은 전제가 있으세요?'
        state.history.append(ChatMessage(role='assistant', content=message))
        return _return_current_phase(state, message=message)

    # 새 전제 생성
    new_premise = None
    if action == 'add':
        indicators = []
        for ind in delta.get('recommended_indicators', []):
            db_id = ind.get('indicator_db_id')
            if db_id and get_indicator_by_id(db_id):
                indicators.append(IndicatorRecommendation(
                    indicator_db_id=db_id,
                    why=ind.get('why', ''),
                    signal_type=ind.get('signal_type', 'coincident'),
                ))
        new_premise = PremiseData(
            title=delta.get('premise_title', ''),
            description=delta.get('premise_description', ''),
            recommended_indicators=indicators,
        )

    # 적용 대상 분기: suggestions 카드 vs collected.premises
    if has_suggestions and target_suggestion_idx is not None:
        target = state.collected.suggestions[target_suggestion_idx]
        if action == 'add' and new_premise:
            target.premises.append(new_premise)
            if not message:
                dir_label = {'bullish': '상승', 'bearish': '하락'}.get(target.direction, '')
                message = f'{dir_label} 가설에 전제 "{new_premise.title}"를 추가했어요.'
        elif action == 'remove':
            idx = delta.get('target_index')
            if idx is not None and 0 <= idx < len(target.premises):
                removed = target.premises.pop(idx)
                if not message:
                    message = f'전제 "{removed.title}"를 삭제했어요.'
    else:
        # 일반 모드: collected.premises 수정
        if action == 'add' and new_premise:
            state.collected.premises.append(new_premise)
            if not message:
                message = f'전제 "{new_premise.title}"를 추가했어요.'
        elif action == 'remove':
            idx = delta.get('target_index')
            if idx is not None and 0 <= idx < len(state.collected.premises):
                removed = state.collected.premises.pop(idx)
                if not message:
                    message = f'전제 "{removed.title}"를 삭제했어요.'
            else:
                return _return_current_phase(state, message='삭제할 전제를 찾지 못했어요.')

    # 지표 재매칭 (collected.premises가 있는 경우만)
    indicator_recommendations = None
    if state.collected.premises:
        indicator_recommendations = match_indicators_for_llm(state.collected)
        matched_ids = [
            rec['indicator']['id']
            for rec in indicator_recommendations
            if isinstance(rec.get('indicator'), dict) and rec['indicator'].get('id')
        ]
        state.collected.selected_indicator_ids = matched_ids

    state.history.append(ChatMessage(role='assistant', content=message))

    return _return_current_phase(
        state,
        message=message,
        indicator_recommendations=indicator_recommendations,
    )


def _handle_modify_indicator(state, user_input):
    """지표 추가/삭제/교체 → Gemini가 delta JSON 생성 → collected에 적용."""
    from thesis.services.prompt_builder import (
        build_modify_indicator_prompt,
        call_gemini_light,
        get_indicator_by_id,
    )

    recent_history = state.history[-6:] if len(state.history) > 6 else list(state.history)
    system_prompt = build_modify_indicator_prompt(state.collected)
    raw = call_gemini_light(system_prompt, user_input, history=recent_history)

    if not raw:
        return _return_current_phase(state, message='지표 수정을 처리하지 못했어요. 다시 시도해주세요.')

    try:
        import json as _json
        import re as _re
        json_match = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if not json_match:
            raise ValueError('No JSON found')
        delta = _json.loads(json_match.group())
    except Exception:
        return _return_current_phase(state, message='지표 수정을 이해하지 못했어요. 좀 더 구체적으로 말씀해주세요.')

    action = delta.get('action', 'add')
    message = delta.get('message', '')
    current_ids = list(state.collected.selected_indicator_ids)

    if action == 'add':
        db_id = delta.get('indicator_db_id')
        cat_ind = get_indicator_by_id(db_id) if db_id else None
        if cat_ind and db_id not in current_ids:
            current_ids.append(db_id)
            if not message:
                message = f'{cat_ind["name"]} 지표를 추가했어요.'
        elif not cat_ind:
            return _return_current_phase(state, message='카탈로그에 없는 지표예요. 다른 지표를 선택해주세요.')

    elif action == 'remove':
        remove_id = delta.get('remove_indicator_id')
        if remove_id and remove_id in current_ids:
            cat_ind = get_indicator_by_id(remove_id)
            current_ids.remove(remove_id)
            name = cat_ind['name'] if cat_ind else str(remove_id)
            if not message:
                message = f'{name} 지표를 삭제했어요.'

    elif action == 'replace':
        remove_id = delta.get('remove_indicator_id')
        add_id = delta.get('indicator_db_id')
        if remove_id in current_ids:
            current_ids.remove(remove_id)
        cat_ind = get_indicator_by_id(add_id) if add_id else None
        if cat_ind and add_id not in current_ids:
            current_ids.append(add_id)
            if not message:
                old = get_indicator_by_id(remove_id)
                old_name = old['name'] if old else str(remove_id)
                message = f'{old_name} → {cat_ind["name"]}로 교체했어요.'

    state.collected.selected_indicator_ids = current_ids
    state.history.append(ChatMessage(role='assistant', content=message))

    # indicator_recommendations 재구성
    from thesis.services.indicator_matcher import match_indicators_for_llm
    indicator_recommendations = match_indicators_for_llm(state.collected)

    return _return_current_phase(
        state,
        message=message,
        indicator_recommendations=indicator_recommendations,
    )


def _handle_modify_thesis(state, user_input):
    """가설 자체(방향/대상/제목) 변경 → 간단한 키워드 파싱."""
    text_lower = user_input.lower()
    message = ''

    if any(kw in text_lower for kw in ['bullish', '상승', '오른다', '올라']):
        state.collected.direction = 'bullish'
        message = '방향을 상승(bullish)으로 변경했어요.'
    elif any(kw in text_lower for kw in ['bearish', '하락', '내린다', '빠진다']):
        state.collected.direction = 'bearish'
        message = '방향을 하락(bearish)으로 변경했어요.'

    if not message:
        # Gemini에게 위임
        from thesis.services.prompt_builder import call_gemini_light
        prompt = f"""현재 가설: 제목="{state.collected.title}", 방향={state.collected.direction}, 대상={state.collected.target}
사용자 요청: "{user_input}"

변경할 필드와 값을 JSON으로 반환: {{"field": "title|direction|target", "new_value": "...", "message": "사용자에게 보여줄 메시지"}}"""
        raw = call_gemini_light(prompt, user_input)
        if raw:
            try:
                import json as _json
                import re as _re
                json_match = _re.search(r'\{.*\}', raw, _re.DOTALL)
                if json_match:
                    delta = _json.loads(json_match.group())
                    field = delta.get('field')
                    value = delta.get('new_value')
                    if field == 'title' and value:
                        state.collected.title = value
                    elif field == 'direction' and value in ('bullish', 'bearish'):
                        state.collected.direction = value
                    elif field == 'target' and value:
                        state.collected.target = value
                    message = delta.get('message', f'{field}을(를) 변경했어요.')
            except Exception:
                pass

    if not message:
        message = '변경 사항을 이해하지 못했어요. "방향 바꿔줘" 또는 "대상을 삼성전자로" 처럼 말씀해주세요.'

    state.history.append(ChatMessage(role='assistant', content=message))
    return _return_current_phase(state, message=message)


def _return_current_phase(state, message=None, indicator_recommendations=None):
    """현재 phase를 유지하면서 응답 반환 (대화형 수정 후)."""
    phase = state.phase

    # 기본 버튼 (현재 phase에 맞게)
    buttons = []
    selection_mode = 'single'
    needs_preset = False

    if phase == BuilderPhase.SUGGESTIONS.value:
        # suggestions phase에서는 버튼 없이 텍스트 입력만 유지
        pass
    elif phase == BuilderPhase.PRESET.value:
        buttons = [
            {'id': 'short', 'label': MONITORING_PRESETS['short']['label']},
            {'id': 'medium', 'label': MONITORING_PRESETS['medium']['label']},
            {'id': 'long', 'label': MONITORING_PRESETS['long']['label']},
        ]
        needs_preset = True
    elif phase == BuilderPhase.CONFIRM.value:
        buttons = [
            {'id': 'confirm', 'label': '등록'},
            {'id': 'restart', 'label': '다시 만들기'},
        ]

    result = {
        'conversation_state': state.model_dump(),
        'message': message or '',
        'buttons': buttons,
        'selection_mode': selection_mode,
        'phase': phase,
    }
    if needs_preset:
        result['needs_preset'] = True
    if indicator_recommendations is not None:
        result['indicator_recommendations'] = indicator_recommendations
    return result


# ──────────────────────────────────────────────
# Suggestion Mode (뉴스 이슈 → 자동 가설 2개 제안)
# ──────────────────────────────────────────────

def generate_suggestions(source_news_id, keyword='', summary='', sentiment='neutral'):
    """
    뉴스 이슈에서 bullish/bearish 가설 2개 자동 생성.

    Returns:
        dict: 통합 응답 shape (conversation_state, suggestions, phase, entry_mode)
    """
    import hashlib

    from django.core.cache import cache

    from thesis.services.llm_postprocess import (
        normalize_llm_output,
        validate_llm_output,
    )
    from thesis.services.prompt_builder import (
        build_suggestion_prompt,
        call_gemini_suggestions,
    )

    conv_id = str(uuid.uuid4())

    log_event(EVENT_SUGGESTION_REQUEST_STARTED, {
        'conv_id': conv_id,
        'source_news_id': str(source_news_id),
        'keyword': keyword,
    })

    # 1. 캐시 체크
    kw_hash = hashlib.md5((keyword or '').encode()).hexdigest()[:8]
    cache_key = f'thesis:suggest:{source_news_id}:{kw_hash}'
    cached = cache.get(cache_key)
    if cached:
        # 캐시 히트 → ConversationState 새로 생성 + 캐시된 suggestions 사용
        state = ConversationState(
            conv_id=conv_id,
            entry_source='news',
            phase=BuilderPhase.SUGGESTIONS.value,
            source_news_id=str(source_news_id),
        )
        state.collected.suggestions = [SuggestionData(**s) for s in cached]
        return {
            'conversation_state': state.model_dump(),
            'suggestions': cached,
            'phase': 'suggestions',
            'entry_mode': 'suggestions',
        }

    # 2. 뉴스 제목 조회
    news_title = _get_news_title(source_news_id)
    if not news_title:
        news_title = keyword or '뉴스 이슈'

    # 3. Gemini 호출
    system_prompt, user_prompt = build_suggestion_prompt(
        news_title, keyword, summary, sentiment,
    )
    raw_result = call_gemini_suggestions(system_prompt, user_prompt)

    if not raw_result or not raw_result.get('suggestions'):
        log_event(EVENT_SUGGESTION_REQUEST_FAILED, {
            'conv_id': conv_id,
            'reason': 'gemini_returned_none',
        })
        return None  # View에서 fallback 처리

    # 4. normalize + validate 각 suggestion 개별 적용
    valid_suggestions = []
    for raw_s in raw_result['suggestions']:
        normalized = normalize_llm_output(raw_s)
        validated, warnings, errors = validate_llm_output(normalized)
        if not errors:
            valid_suggestions.append(validated)

    if not valid_suggestions:
        log_event(EVENT_SUGGESTION_REQUEST_FAILED, {
            'conv_id': conv_id,
            'reason': 'all_suggestions_invalid',
        })
        return None

    # 5. SuggestionData로 변환 + 정확히 2개 보장
    suggestion_datas = []
    for vs in valid_suggestions[:2]:
        premises = []
        for p in vs.get('premises', []):
            indicators = []
            for ind in p.get('recommended_indicators', []):
                indicators.append({
                    'indicator_db_id': ind.get('indicator_db_id'),
                    'indicator_name': ind.get('indicator_name'),
                    'why': ind.get('why', ''),
                    'signal_type': ind.get('signal_type', 'coincident'),
                })
            premises.append({
                'title': p.get('title', ''),
                'description': p.get('description', ''),
                'recommended_indicators': indicators,
            })
        suggestion_datas.append({
            'direction': vs.get('direction', 'bullish'),
            'title': vs.get('title', ''),
            'summary': vs.get('message', vs.get('summary', '')),
            'target': vs.get('target', ''),
            'target_type': vs.get('target_type', 'index'),
            'thesis_type': vs.get('thesis_type', []),
            'premises': premises,
        })

    # 6. ConversationState 생성
    state = ConversationState(
        conv_id=conv_id,
        entry_source='news',
        phase=BuilderPhase.SUGGESTIONS.value,
        source_news_id=str(source_news_id),
    )
    state.collected.suggestions = [SuggestionData(**s) for s in suggestion_datas]

    # 7. 캐시 저장 (suggestions 배열만, TTL 10분)
    cache.set(cache_key, suggestion_datas, timeout=600)

    log_event(EVENT_SUGGESTION_REQUEST_SUCCEEDED, {
        'conv_id': conv_id,
        'suggestion_count': len(suggestion_datas),
    })

    return {
        'conversation_state': state.model_dump(),
        'suggestions': suggestion_datas,
        'phase': 'suggestions',
        'entry_mode': 'suggestions',
    }


def _handle_suggestion_select(state, user_input, user):
    """
    suggestions phase 2단계 처리:
      Step 1: select_suggestion:N → 전제 multi-select 표시
      Step 2: 전제 인덱스 리스트 → 선택된 전제로 지표 매칭 → PRESET
    """
    import re as _re

    from thesis.services.indicator_matcher import match_indicators_for_llm
    from thesis.services.llm_postprocess import merge_to_collected

    # ── Step 1: 카드 선택 → 전제 multi-select ──
    if isinstance(user_input, str):
        text = user_input.strip()
        match = _re.match(r'^select_suggestion:(\d+)$', text)
        if match:
            idx = int(match.group(1))
            suggestions = state.collected.suggestions
            if idx < 0 or idx >= len(suggestions):
                return {
                    'conversation_state': state.model_dump(),
                    'message': f'잘못된 선택입니다. 0~{len(suggestions)-1} 사이를 선택해주세요.',
                    'buttons': [],
                    'phase': 'suggestions',
                }

            selected = suggestions[idx]

            # 기본 정보 병합 (premises는 아직 확정 아님 — 사용자가 골라야 함)
            merge_data = {
                'direction': selected.direction,
                'target': selected.target,
                'target_type': selected.target_type,
                'title': selected.title,
                'thesis_type': selected.thesis_type,
            }
            state.collected = merge_to_collected(state.collected, merge_data)

            # 전제를 collected.premises에 임시 저장 (사용자 선택 대기)
            state.collected.premises = [
                PremiseData(
                    title=p.title,
                    description=p.description,
                    recommended_indicators=p.recommended_indicators,
                )
                for p in selected.premises
            ]

            log_event(EVENT_SUGGESTION_SELECTED, {
                'conv_id': state.conv_id,
                'direction': selected.direction,
                'index': idx,
            })

            # 전제를 multi-select 버튼으로 반환
            direction_label = {'bullish': '상승', 'bearish': '하락'}.get(selected.direction, '')
            buttons = [
                {'id': str(i), 'label': p.title, 'long_press_hint': bool(p.description)}
                for i, p in enumerate(selected.premises)
            ]
            long_press = {
                str(i): p.description
                for i, p in enumerate(selected.premises)
                if p.description
            }

            message = (
                f'"{selected.title}" ({direction_label}) 가설의 전제들이에요.\n'
                f'추적할 전제를 선택해주세요.'
            )
            state.history.append(ChatMessage(role='assistant', content=message))

            result = {
                'conversation_state': state.model_dump(),
                'message': message,
                'buttons': buttons,
                'selection_mode': 'multi',
                'phase': 'suggestions',
            }
            if long_press:
                result['long_press_explanations'] = long_press
            return result

        # select_suggestion:N 형식이 아닌 문자열 → 대화형 처리
        return _handle_conversational_edit(state, user_input, user)

    # ── Step 2: 전제 multi-select 확인 → 지표 매칭 → PRESET ──
    if isinstance(user_input, list):
        selected_indices = []
        for item in user_input:
            try:
                selected_indices.append(int(item))
            except (ValueError, TypeError):
                continue

        all_premises = state.collected.premises

        if not selected_indices:
            return {
                'conversation_state': state.model_dump(),
                'message': '최소 1개의 전제를 선택해주세요.',
                'buttons': [
                    {'id': str(i), 'label': p.title}
                    for i, p in enumerate(all_premises)
                ],
                'selection_mode': 'multi',
                'phase': 'suggestions',
            }

        # 선택된 전제만 유지
        kept_premises = [
            all_premises[i] for i in selected_indices
            if 0 <= i < len(all_premises)
        ]
        if not kept_premises:
            return {
                'conversation_state': state.model_dump(),
                'message': '최소 1개의 전제를 선택해주세요.',
                'buttons': [
                    {'id': str(i), 'label': p.title}
                    for i, p in enumerate(all_premises)
                ],
                'selection_mode': 'multi',
                'phase': 'suggestions',
            }

        state.collected.premises = kept_premises

        # validation
        try:
            CollectedData.model_validate(state.collected.model_dump())
        except Exception as e:
            logger.exception(f"CollectedData validation failed after premise selection: {e}")
            return {
                'conversation_state': state.model_dump(),
                'message': '전제 처리 중 오류가 발생했어요. 다시 시도해주세요.',
                'buttons': [],
                'phase': 'suggestions',
            }

        # 선택된 전제 기반 지표 정밀 매칭
        indicator_recommendations = match_indicators_for_llm(state.collected)
        matched_ids = []
        for rec in indicator_recommendations:
            ind = rec.get('indicator', {})
            db_id = ind.get('id') if isinstance(ind, dict) else None
            if db_id:
                matched_ids.append(db_id)
        state.collected.selected_indicator_ids = matched_ids

        # phase → PRESET
        state.phase = BuilderPhase.PRESET.value

        log_event(EVENT_SUGGESTION_TO_PRESET, {
            'conv_id': state.conv_id,
            'premise_count': len(kept_premises),
            'indicator_count': len(indicator_recommendations),
        })

        message = (
            f'전제 {len(kept_premises)}개를 선택했어요.\n'
            f'추천 지표 {len(indicator_recommendations)}개를 찾았어요.\n\n'
            f'모니터링 기간을 선택해주세요.'
        )
        state.history.append(ChatMessage(role='assistant', content=message))

        preset_buttons = [
            {'id': 'short', 'label': MONITORING_PRESETS['short']['label']},
            {'id': 'medium', 'label': MONITORING_PRESETS['medium']['label']},
            {'id': 'long', 'label': MONITORING_PRESETS['long']['label']},
        ]

        return {
            'conversation_state': state.model_dump(),
            'message': message,
            'buttons': preset_buttons,
            'selection_mode': 'single',
            'needs_preset': True,
            'indicator_recommendations': indicator_recommendations,
            'phase': 'preset',
        }

    # ── Fallback: 문자열도 리스트도 아닌 경우 → 대화형 처리 ──
    if isinstance(user_input, str):
        return _handle_conversational_edit(state, user_input, user)
    return _return_current_phase(state, message='가설 카드를 선택하거나 질문을 입력해주세요.')
