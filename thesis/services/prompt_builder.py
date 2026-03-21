"""Prompt Builder: LLM 빌더용 시스템 프롬프트 조립 + Gemini 호출 (Phase A-MVP)"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Static Indicator Catalog (전체 확장)
# 향후 DB 모델로 마이그레이션 가능
# ──────────────────────────────────────────────
INDICATOR_CATALOG = [
    # ── 시장 데이터: 수급 ──
    {'id': 1, 'name': '외국인 순매수 추이', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'metric': 'foreign_net_buy'},
     'support_direction': 'positive'},
    {'id': 2, 'name': '기관 순매수 추이', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'metric': 'institutional_net_buy'},
     'support_direction': 'positive'},

    # ── 시장 데이터: 주요 지수 ──
    {'id': 3, 'name': 'S&P 500', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^GSPC'},
     'support_direction': 'positive'},
    {'id': 4, 'name': 'KOSPI 지수', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^KS11'},
     'support_direction': 'positive'},
    {'id': 12, 'name': 'NASDAQ', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^IXIC'},
     'support_direction': 'positive'},
    {'id': 13, 'name': '다우존스', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^DJI'},
     'support_direction': 'positive'},
    {'id': 14, 'name': '코스닥 지수', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^KQ11'},
     'support_direction': 'positive'},
    {'id': 15, 'name': '니케이 225', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^N225'},
     'support_direction': 'positive'},
    {'id': 16, 'name': '항셍 지수', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': '^HSI'},
     'support_direction': 'positive'},

    # ── 시장 데이터: 원자재/상품 ──
    {'id': 20, 'name': '금 (Gold)', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': 'GCUSD'},
     'support_direction': 'positive'},
    {'id': 21, 'name': '원유 (WTI)', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': 'CLUSD'},
     'support_direction': 'positive'},
    {'id': 22, 'name': '은 (Silver)', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': 'SIUSD'},
     'support_direction': 'positive'},
    {'id': 23, 'name': '구리 (Copper)', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': 'HGUSD'},
     'support_direction': 'positive'},
    {'id': 24, 'name': '천연가스', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': 'NGUSD'},
     'support_direction': 'positive'},

    # ── 시장 데이터: 암호화폐 ──
    {'id': 25, 'name': '비트코인 (BTC)', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': 'BTCUSD'},
     'support_direction': 'positive'},
    {'id': 26, 'name': '이더리움 (ETH)', 'category': 'market_data',
     'data_source': 'fmp', 'data_params': {'symbol': 'ETHUSD'},
     'support_direction': 'positive'},

    # ── 거시경제: 금리 ──
    {'id': 6, 'name': '미국 기준금리 (Fed Funds Rate)', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'FEDFUNDS'},
     'support_direction': 'negative'},
    {'id': 7, 'name': '미국 10년 국채 금리', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'DGS10'},
     'support_direction': 'negative'},
    {'id': 30, 'name': '미국 2년 국채 금리', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'DGS2'},
     'support_direction': 'negative'},
    {'id': 37, 'name': '30년 모기지 금리', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'MORTGAGE30US'},
     'support_direction': 'negative'},

    # ── 거시경제: 변동성/환율 ──
    {'id': 8, 'name': 'VIX (공포지수)', 'category': 'macro',
     'data_source': 'fmp', 'data_params': {'symbol': '^VIX'},
     'support_direction': 'negative'},
    {'id': 9, 'name': '원/달러 환율', 'category': 'macro',
     'data_source': 'fmp', 'data_params': {'symbol': 'USDKRW'},
     'support_direction': 'negative'},
    {'id': 38, 'name': '달러/유로 환율', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'DEXUSEU'},
     'support_direction': 'positive'},
    {'id': 39, 'name': '달러 인덱스 (DXY)', 'category': 'macro',
     'data_source': 'fmp', 'data_params': {'symbol': 'DX-Y.NYB'},
     'support_direction': 'negative'},

    # ── 거시경제: 고용/성장 ──
    {'id': 31, 'name': '실업률', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'UNRATE'},
     'support_direction': 'negative'},
    {'id': 32, 'name': '비농업 고용 (NFP)', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'PAYEMS'},
     'support_direction': 'positive'},
    {'id': 34, 'name': '실질 GDP', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'GDPC1'},
     'support_direction': 'positive'},
    {'id': 35, 'name': '산업생산지수', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'INDPRO'},
     'support_direction': 'positive'},

    # ── 거시경제: 물가/주택 ──
    {'id': 33, 'name': '소비자물가지수 (CPI)', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'CPIAUCSL'},
     'support_direction': 'negative'},
    {'id': 36, 'name': '주택착공건수', 'category': 'macro',
     'data_source': 'fred', 'data_params': {'series_id': 'HOUST'},
     'support_direction': 'positive'},

    # ── 기술적 지표 ──
    {'id': 10, 'name': 'RSI (14일)', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'RSI', 'period': 14},
     'support_direction': 'positive'},
    {'id': 40, 'name': 'MACD', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9},
     'support_direction': 'positive'},
    {'id': 41, 'name': '스토캐스틱 %K', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'stochastic', 'period': 14},
     'support_direction': 'positive'},
    {'id': 42, 'name': '볼린저 밴드 %B', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'bollinger', 'period': 20},
     'support_direction': 'positive'},
    {'id': 43, 'name': 'ATR (평균진폭)', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'ATR', 'period': 14},
     'support_direction': 'positive'},
    {'id': 44, 'name': 'OBV (거래량 누적)', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'OBV'},
     'support_direction': 'positive'},
    {'id': 45, 'name': 'SMA 50일', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'SMA', 'period': 50},
     'support_direction': 'positive'},
    {'id': 46, 'name': 'SMA 200일', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'SMA', 'period': 200},
     'support_direction': 'positive'},
    {'id': 47, 'name': 'EMA 12일', 'category': 'technical',
     'data_source': 'fmp', 'data_params': {'indicator': 'EMA', 'period': 12},
     'support_direction': 'positive'},

    # ── 펀더멘털 ──
    {'id': 5, 'name': 'EPS 추이', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'eps'},
     'support_direction': 'positive'},
    {'id': 50, 'name': 'PER (주가수익비율)', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'peRatioTTM'},
     'support_direction': 'negative'},
    {'id': 51, 'name': 'PBR (주가순자산비율)', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'pbRatioTTM'},
     'support_direction': 'negative'},
    {'id': 52, 'name': 'ROE (자기자본이익률)', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'returnOnEquityTTM'},
     'support_direction': 'positive'},
    {'id': 53, 'name': 'ROA (총자산이익률)', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'returnOnAssetsTTM'},
     'support_direction': 'positive'},
    {'id': 54, 'name': '부채비율 (Debt/Equity)', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'debtToEquityTTM'},
     'support_direction': 'negative'},
    {'id': 55, 'name': '잉여현금흐름 (FCF)', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'freeCashFlowTTM'},
     'support_direction': 'positive'},
    {'id': 56, 'name': '배당수익률', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'dividendYieldTTM'},
     'support_direction': 'positive'},
    {'id': 57, 'name': '영업이익률', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'operatingProfitMarginTTM'},
     'support_direction': 'positive'},
    {'id': 58, 'name': '매출성장률 (YoY)', 'category': 'fundamental',
     'data_source': 'fmp', 'data_params': {'metric': 'revenueGrowthYoY'},
     'support_direction': 'positive'},

    # ── 심리 ──
    {'id': 11, 'name': '뉴스 센티먼트', 'category': 'sentiment',
     'data_source': 'news_sentiment', 'data_params': {},
     'support_direction': 'positive'},
]

CATEGORY_LABELS = {
    'market_data': '시장 데이터',
    'macro': '거시경제',
    'technical': '기술적',
    'fundamental': '펀더멘털',
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
