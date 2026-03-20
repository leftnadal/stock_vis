"""Prompt Builder: LLM 빌더용 시스템 프롬프트 조립 + Gemini 호출 (Phase A-MVP)"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Static Indicator Catalog (MVP: hardcoded)
# 향후 DB 모델로 마이그레이션 가능
# ──────────────────────────────────────────────
INDICATOR_CATALOG = [
    # Market Data
    {'id': 1, 'name': '외국인 순매수 추이', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'metric': 'foreign_net_buy'},
     'support_direction': 'positive'},
    {'id': 2, 'name': '기관 순매수 추이', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'metric': 'institutional_net_buy'},
     'support_direction': 'positive'},
    {'id': 3, 'name': 'S&P 500', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^GSPC'},
     'support_direction': 'positive'},
    {'id': 4, 'name': 'KOSPI 지수', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^KS11'},
     'support_direction': 'positive'},
    {'id': 5, 'name': 'EPS 추이', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'metric': 'eps'},
     'support_direction': 'positive'},
    # Macro
    {'id': 6, 'name': '미국 기준금리 (Fed Funds Rate)', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'FEDFUNDS'},
     'support_direction': 'negative'},
    {'id': 7, 'name': '미국 10년 국채 금리', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'DGS10'},
     'support_direction': 'negative'},
    {'id': 8, 'name': 'VIX (공포지수)', 'category': 'macro',
     'data_source': 'fmp', 'data_params': {'symbol': '^VIX'},
     'support_direction': 'negative'},
    {'id': 9, 'name': '원/달러 환율', 'category': 'macro',
     'data_source': 'fmp', 'data_params': {'symbol': 'USDKRW'},
     'support_direction': 'negative'},
    # Technical
    {'id': 10, 'name': 'RSI (14일)', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'RSI', 'period': 14},
     'support_direction': 'positive'},
    # Sentiment
    {'id': 11, 'name': '뉴스 센티먼트', 'category': 'sentiment',
     'data_source': 'news_sentiment', 'data_params': {},
     'support_direction': 'positive'},
]

CATEGORY_LABELS = {
    'market_data': '시장 데이터',
    'macro': '거시경제',
    'technical': '기술적',
    'sentiment': '심리',
}

# ID → 지표 빠른 조회용
_INDICATOR_BY_ID = {ind['id']: ind for ind in INDICATOR_CATALOG}


# ──────────────────────────────────────────────
# Prompt Blocks
# ──────────────────────────────────────────────

def build_base_instruction():
    """역할 + 출력 규칙."""
    return """당신은 투자 가설 설계 전문가입니다.

## 역할
사용자가 한 줄로 던진 투자 아이디어를 분석해서, 체계적인 투자 가설로 구조화합니다.

## 출력 규칙
1. 한국어로 응답합니다.
2. 사용자 입력 한 번으로 가설 전체를 제안합니다 (One-shot Proposal).
3. 각 전제(premise)에 대해 추적할 지표를 추천하고, "왜(why)" 한 줄 이유를 붙입니다.
4. 확신도(confidence)를 판단합니다:
   - high: 대상, 방향, 근거가 명확
   - medium: 대부분 파악 가능하지만 일부 모호
   - low: 너무 모호하거나 추가 질문 필요
5. confidence가 low일 때는 가설을 제안하지 말고, 구체화 질문만 합니다.
   이때 premises는 빈 배열로 반환합니다.
6. message 필드에 사용자에게 보여줄 대화 메시지를 작성합니다.
   - high/medium: 가설 요약 + "어떠세요?" 식 확인
   - low: 구체적인 질문 1개"""


def build_type_guide_block():
    """5개 가설 유형 가이드."""
    return """## 가설 유형 가이드

다음 유형 중 해당하는 것을 모두 선택합니다 (복수 가능):

- **earnings**: 실적/매출/이익 기반 — "삼성전자 2분기 실적 반등"
- **flow**: 수급/자금 흐름 기반 — "외국인 순매수 전환"
- **macro**: 거시경제/금리/환율 기반 — "금리 인하 수혜"
- **chain**: 공급망/산업 연결 기반 — "엔비디아 공급망 수혜"
- **event**: 이벤트/정책/뉴스 기반 — "반도체 보조금 법안 통과"

하나 이상의 유형을 선택하세요."""


def build_indicator_block():
    """Indicator DB에서 PK 포함 목록 생성."""
    lines = [
        "## 사용 가능한 지표",
        "",
        "아래 목록에서 각 전제에 적합한 지표를 추천하세요.",
        "indicator_db_id에는 괄호 안의 id 숫자를 사용하세요.",
        "",
    ]

    by_category = {}
    for ind in INDICATOR_CATALOG:
        cat = ind['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(ind)

    for cat, label in CATEGORY_LABELS.items():
        inds = by_category.get(cat, [])
        if not inds:
            continue
        lines.append(f"[{label}]")
        for ind in inds:
            lines.append(f"  - {ind['name']}(id:{ind['id']})")
        lines.append("")

    return "\n".join(lines)


def build_system_prompt(state, flags):
    """flags 기반 블록 조합."""
    blocks = [build_base_instruction(), build_type_guide_block()]

    if flags.get('INDICATOR_CONTEXT_ENABLED'):
        blocks.append(build_indicator_block())

    # Phase B: Keyword Hint Enrichment
    if flags.get('KEYWORD_HINTS_ENABLED') and state:
        target = None
        if hasattr(state, 'collected') and hasattr(state.collected, 'target'):
            target = state.collected.target
        elif isinstance(state, dict):
            target = state.get('collected', {}).get('target')

        if target:
            from thesis.services.keyword_hint import collect_context_keywords, build_keyword_hint_block
            keywords = collect_context_keywords(target, flags)
            hint_block = build_keyword_hint_block(keywords)
            if hint_block:
                blocks.append(hint_block)

    return "\n\n".join(blocks)


# ──────────────────────────────────────────────
# Gemini Structured Output
# ──────────────────────────────────────────────

def get_gemini_response_schema():
    """Gemini Structured Output JSON 스키마."""
    return {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["bullish", "bearish"],
            },
            "target": {"type": "string"},
            "target_type": {
                "type": "string",
                "enum": ["index", "stock", "sector", "macro"],
            },
            "thesis_type": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["earnings", "flow", "macro", "chain", "event"],
                },
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "title": {"type": "string"},
            "message": {"type": "string"},
            "premises": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "recommended_indicators": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "indicator_db_id": {"type": "integer"},
                                    "why": {"type": "string"},
                                    "signal_type": {
                                        "type": "string",
                                        "enum": ["leading", "coincident", "lagging"],
                                    },
                                },
                                "required": ["indicator_db_id", "why"],
                            },
                        },
                    },
                    "required": ["title"],
                },
            },
        },
        "required": [
            "direction", "target", "target_type", "thesis_type",
            "confidence", "title", "message", "premises",
        ],
    }


def call_gemini(system_prompt, history):
    """
    Gemini 2.5 Flash 호출 (Structured Output).

    Args:
        system_prompt: 시스템 프롬프트
        history: list[dict] — {'role': 'user'|'assistant', 'content': str}

    Returns:
        dict (파싱된 JSON) or None (실패 시)
    """
    try:
        from google import genai
        from google.genai import types

        api_key = (
            getattr(settings, 'GOOGLE_AI_API_KEY', None)
            or getattr(settings, 'GEMINI_API_KEY', None)
        )
        if not api_key:
            logger.warning("Gemini API key not configured")
            return None

        client = genai.Client(api_key=api_key)

        # history → Gemini contents
        contents = []
        for msg in history:
            role = 'user' if msg.get('role') == 'user' else 'model'
            text = msg.get('content', '')
            contents.append(
                types.Content(role=role, parts=[types.Part(text=text)])
            )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2000,
            temperature=0.3,
            response_mime_type="application/json",
            response_schema=get_gemini_response_schema(),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=config,
        )

        text = response.text if hasattr(response, 'text') and response.text else ''
        if not text:
            return None

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.exception(f"Gemini JSON parse failed: {e}")
        return None
    except Exception as e:
        logger.exception(f"Gemini call failed: {e}")
        return None


def get_indicator_by_id(indicator_id):
    """INDICATOR_CATALOG에서 ID로 지표 조회."""
    return _INDICATOR_BY_ID.get(indicator_id, None)
