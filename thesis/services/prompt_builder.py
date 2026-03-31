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

    # ── 펀더멘털 (재무 체질 — validation/metrics 시스템) ──
    {'id': 60, 'name': '매출총이익률 (Gross Margin)', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'gross_margin'},
     'support_direction': 'positive'},
    {'id': 61, 'name': '순이익률 (Net Margin)', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'net_margin'},
     'support_direction': 'positive'},
    {'id': 62, 'name': 'ROIC (투하자본이익률)', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'roic'},
     'support_direction': 'positive'},
    {'id': 63, 'name': '유동비율 (Current Ratio)', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'current_ratio'},
     'support_direction': 'positive'},
    {'id': 64, 'name': '이자보상배율', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'interest_coverage'},
     'support_direction': 'positive'},
    {'id': 65, 'name': '순부채/EBITDA', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'net_debt_to_ebitda'},
     'support_direction': 'negative'},
    {'id': 66, 'name': 'FCF 마진', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'fcf_margin'},
     'support_direction': 'positive'},
    {'id': 67, 'name': 'EV/EBITDA', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'ev_to_ebitda'},
     'support_direction': 'negative'},
    {'id': 68, 'name': 'FCF 수익률', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'fcf_yield'},
     'support_direction': 'positive'},
    {'id': 69, 'name': '영업이익 성장률', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'operating_income_growth'},
     'support_direction': 'positive'},
    {'id': 70, 'name': '매출채권 회전일수 (DSO)', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'dso'},
     'support_direction': 'negative'},
    {'id': 71, 'name': '총자산회전율', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'asset_turnover'},
     'support_direction': 'positive'},
    {'id': 72, 'name': '발생액 비율 (Accruals)', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'accruals_ratio'},
     'support_direction': 'negative'},
    {'id': 73, 'name': '순주주수익률', 'category': 'fundamental',
     'data_source': 'metrics', 'data_params': {'metric_code': 'net_shareholder_yield'},
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

# 지표별 업데이트 주기 (프롬프트에 표시)
INDICATOR_FREQUENCY = {
    # 실시간/일간
    1: '일간', 2: '일간', 3: '일간', 4: '일간', 12: '일간', 13: '일간',
    14: '일간', 15: '일간', 16: '일간',
    20: '일간', 21: '일간', 22: '일간', 23: '일간', 24: '일간',
    25: '일간', 26: '일간',
    8: '일간', 9: '일간', 38: '일간', 39: '일간',
    10: '일간', 40: '일간', 41: '일간', 42: '일간', 43: '일간',
    44: '일간', 45: '일간', 46: '일간', 47: '일간',
    11: '일간',
    # 일간/주간 (금리)
    6: '주간', 7: '일간', 30: '일간', 37: '주간',
    # 월간
    31: '월간', 32: '월간', 33: '월간', 34: '분기', 35: '월간', 36: '월간',
    # 분기
    5: '분기', 50: '분기', 51: '분기', 52: '분기', 53: '분기',
    54: '분기', 55: '분기', 56: '분기', 57: '분기', 58: '분기',
    # 분기 (재무 체질 metrics)
    60: '분기', 61: '분기', 62: '분기', 63: '분기', 64: '분기',
    65: '분기', 66: '분기', 67: '분기', 68: '분기', 69: '분기',
    70: '분기', 71: '분기', 72: '분기', 73: '분기',
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
    """Indicator DB에서 PK + 업데이트 주기 포함 목록 생성."""
    lines = [
        "## 사용 가능한 지표",
        "",
        "**아래 목록에 있는 지표만 사용하세요. 목록에 없는 지표를 만들지 마세요.**",
        "indicator_db_id에는 괄호 안의 id 숫자를 반드시 사용하세요.",
        "각 지표 옆의 [일간/주간/월간/분기]는 데이터 업데이트 주기입니다.",
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
            freq = INDICATOR_FREQUENCY.get(ind['id'], '')
            freq_tag = f" [{freq}]" if freq else ""
            lines.append(f"  - {ind['name']}(id:{ind['id']}){freq_tag}")
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


# ──────────────────────────────────────────────
# Conversational Edit: 대화형 가설 수정 프롬프트
# ──────────────────────────────────────────────

def build_intent_classification_prompt(phase, collected):
    """사용자 메시지의 의도를 분류하는 프롬프트."""
    # 현재 가설 상태 요약
    ctx_parts = []
    # 가설 카드 컨텍스트 (선택 전)
    if collected.suggestions:
        titles = [f'{s.direction}: {s.title}' for s in collected.suggestions]
        ctx_parts.append(f'제시된 가설 카드: {" / ".join(titles)}')
    if collected.title:
        ctx_parts.append(f'가설: {collected.title}')
    if collected.direction:
        ctx_parts.append(f'방향: {collected.direction}')
    if collected.premises:
        premise_list = ', '.join(p.title for p in collected.premises)
        ctx_parts.append(f'전제({len(collected.premises)}개): {premise_list}')
    if collected.selected_indicator_ids:
        ctx_parts.append(f'지표: {len(collected.selected_indicator_ids)}개 선택됨')
    context = '\n'.join(ctx_parts) if ctx_parts else '(아직 가설 없음)'

    return f"""사용자가 투자 가설 빌더에서 메시지를 보냈습니다.
현재 단계: {phase}
{context}

사용자 메시지를 다음 중 하나로 분류하세요:
- "question": 질문이나 설명 요청 (예: "이 지표 왜 추천했어?", "bearish가 뭐야?", "이게 무슨 뜻이야?")
- "modify_premise": 전제 추가/삭제/변경 (예: "전제 하나 더 추가해줘", "환율 전제 빼줘")
- "modify_indicator": 지표 추가/삭제/변경 (예: "VIX 말고 다른 거", "금 지표 추가해줘")
- "modify_thesis": 가설 자체 변경 (예: "방향 바꿔볼까", "대상을 삼성전자로 바꿔줘")
- "proceed": 다음 단계 진행 (예: "좋아", "이대로 가자", "등록", "단기로")
- "restart": 처음부터 다시 (예: "다시 만들자", "처음부터")

JSON만 반환: {{"intent": "...", "detail": "추출된 핵심 내용"}}"""


def build_question_answer_prompt(collected, suggestions=None, source_news_id=None):
    """사용자 질문에 답변하기 위한 시스템 프롬프트."""
    ctx_parts = ['## 현재 가설 빌더 컨텍스트']

    # 뉴스 원문 컨텍스트
    if source_news_id:
        try:
            from news.models import NewsArticle
            article = NewsArticle.objects.filter(id=source_news_id).first()
            if article:
                ctx_parts.append(f'### 기반 뉴스')
                ctx_parts.append(f'- 제목: {article.title}')
                if hasattr(article, 'content') and article.content:
                    ctx_parts.append(f'- 내용 요약: {article.content[:300]}')
        except Exception:
            pass

    # 제안된 가설 카드 (선택 전이면 이 정보가 핵심)
    if suggestions:
        ctx_parts.append(f'### 현재 제시된 가설 카드 ({len(suggestions)}개)')
        for i, s in enumerate(suggestions):
            dir_label = {'bullish': '상승', 'bearish': '하락'}.get(s.direction, s.direction)
            ctx_parts.append(f'\n**가설 {i+1} ({dir_label})**: {s.title}')
            ctx_parts.append(f'요약: {s.summary}')
            if s.premises:
                for j, p in enumerate(s.premises, 1):
                    desc = f' — {p.description}' if p.description else ''
                    ctx_parts.append(f'  전제 {j}: {p.title}{desc}')

    # 확정된 가설 상태
    if collected.title:
        ctx_parts.append(f'\n### 사용자가 선택/수정한 가설')
        ctx_parts.append(f'- 제목: {collected.title}')
    if collected.direction:
        dir_label = {'bullish': '상승', 'bearish': '하락'}.get(collected.direction, collected.direction)
        ctx_parts.append(f'- 방향: {dir_label}')
    if collected.target:
        ctx_parts.append(f'- 대상: {collected.target}')
    if collected.premises:
        ctx_parts.append(f'- 전제 ({len(collected.premises)}개):')
        for i, p in enumerate(collected.premises, 1):
            desc = f' — {p.description}' if p.description else ''
            ctx_parts.append(f'  {i}. {p.title}{desc}')
            if p.recommended_indicators:
                for ind in p.recommended_indicators:
                    cat_ind = get_indicator_by_id(ind.indicator_db_id) if ind.indicator_db_id else None
                    name = cat_ind['name'] if cat_ind else (ind.indicator_name or '?')
                    ctx_parts.append(f'     → 지표: {name} ({ind.why})')
    context = '\n'.join(ctx_parts)

    return f"""당신은 친절한 투자 가설 빌더 어시스턴트입니다.
사용자가 가설을 만드는 중에 질문을 했습니다.

{context}

## 규칙
1. 한국어로 답변합니다.
2. 위 컨텍스트는 현재 대화 상황을 이해하기 위한 참고 자료입니다. **답변은 컨텍스트에 국한하지 말고 당신이 아는 모든 지식을 활용하세요.**
3. 시장 규모, 성장률, 기업 실적, 산업 동향 등을 물으면 당신이 아는 수치와 팩트를 구체적으로 제공합니다. "컨텍스트에 없다"고 회피하지 마세요.
4. 가설 카드에 나온 내용과 관련된 질문이면, 카드 내용 + 당신의 지식을 결합해서 답변합니다.
5. 전문 용어는 쉽게 풀어서 설명합니다.
6. 필요하면 "이 내용을 전제에 추가해볼까요?" 같은 제안도 합니다.
7. 답변 길이는 자유. 짧은 질문에는 2~3문장, 상세 질문에는 충분히 길게."""


def build_modify_premise_prompt(collected):
    """전제 수정용 시스템 프롬프트."""
    indicator_block = build_indicator_block()
    premises_desc = '\n'.join(
        f'{i}. {p.title}' for i, p in enumerate(collected.premises)
    ) if collected.premises else '(없음)'

    return f"""현재 가설의 전제 목록:
{premises_desc}

사용자가 전제를 수정하려고 합니다.
아래 JSON 형식으로만 응답하세요:

{{"action": "add" 또는 "remove",
 "premise_title": "전제 제목 (15~30자)",
 "premise_description": "전제를 뒷받침하는 구체적 근거 (1~2문장)",
 "target_index": 삭제 시 인덱스 번호 (0부터),
 "recommended_indicators": [
   {{"indicator_db_id": 숫자, "why": "이유 1문장", "signal_type": "leading|coincident|lagging"}}
 ],
 "message": "사용자에게 보여줄 대화 메시지 (1~2문장)"}}

{indicator_block}

**카탈로그에 있는 지표만 사용하세요. 목록에 없는 지표를 만들지 마세요.**"""


def build_modify_indicator_prompt(collected):
    """지표 수정용 시스템 프롬프트."""
    indicator_block = build_indicator_block()
    current_ids = collected.selected_indicator_ids
    current_names = []
    for db_id in current_ids:
        cat_ind = get_indicator_by_id(db_id)
        if cat_ind:
            current_names.append(f'- {cat_ind["name"]} (id:{db_id})')
    current_desc = '\n'.join(current_names) if current_names else '(없음)'

    return f"""현재 선택된 지표:
{current_desc}

사용자가 지표를 수정하려고 합니다.
아래 JSON 형식으로만 응답하세요:

{{"action": "add" 또는 "remove" 또는 "replace",
 "indicator_db_id": 추가/교체할 지표의 카탈로그 id,
 "remove_indicator_id": 삭제/교체 대상 id (remove/replace 시),
 "why": "추가/교체 이유 (1문장)",
 "message": "사용자에게 보여줄 대화 메시지 (1~2문장)"}}

{indicator_block}

**카탈로그에 있는 지표만 사용하세요.**"""


def call_gemini_light(system_prompt, user_message, history=None):
    """
    가벼운 Gemini 호출 (Structured Output 없이, 빠른 응답).

    Args:
        system_prompt: 시스템 프롬프트
        user_message: 현재 사용자 메시지
        history: 대화 이력 (최근 N개). list[ChatMessage] 또는 list[dict]
    """
    try:
        from google import genai
        from google.genai import types

        api_key = (
            getattr(settings, 'GOOGLE_AI_API_KEY', None)
            or getattr(settings, 'GEMINI_API_KEY', None)
        )
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)

        # 대화 이력 → Gemini contents 변환
        contents = []
        if history:
            for msg in history:
                role_val = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
                content_val = msg.content if hasattr(msg, 'content') else msg.get('content', '')
                gem_role = 'user' if role_val == 'user' else 'model'
                contents.append(
                    types.Content(role=gem_role, parts=[types.Part(text=content_val)])
                )
        # 현재 메시지 추가
        contents.append(
            types.Content(role='user', parts=[types.Part(text=user_message)])
        )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=500,
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=config,
        )

        return response.text if hasattr(response, 'text') and response.text else None

    except Exception as e:
        logger.exception(f"Gemini light call failed: {e}")
        return None


# ──────────────────────────────────────────────
# Suggestion Prompt (뉴스 이슈 → bullish/bearish 2개 가설)
# ──────────────────────────────────────────────

def build_suggestion_prompt(news_title, keyword='', summary='', sentiment='neutral'):
    """뉴스 이슈 기반 가설 제안 프롬프트 생성."""
    indicator_block = build_indicator_block()

    context_parts = [f'뉴스 제목: {news_title}']
    if keyword:
        context_parts.append(f'키워드: {keyword}')
    if summary:
        context_parts.append(f'요약: {summary}')
    if sentiment and sentiment != 'neutral':
        context_parts.append(f'센티먼트: {sentiment}')
    context = '\n'.join(context_parts)

    system_prompt = f"""당신은 투자 가설 설계 전문가입니다.

## 목표
아래 뉴스 이슈를 바탕으로, 같은 팩트를 다른 관점으로 해석한 **정확히 2개** 가설을 생성합니다.
- 1번: bullish (상승/긍정적 관점)
- 2번: bearish (하락/부정적 관점)

## 규칙
1. 한국어로 응답
2. title: 구체적인 가설 제목 (예: "Meta 규제 리스크는 과도한 우려, 광고 사업 견고" — 20~40자)
3. summary: 왜 그렇게 볼 수 있는지 근거와 논리를 포함한 설명 (2~3문장, 60~120자)
   - 단순 결론이 아니라 "어떤 팩트 → 어떤 해석 → 어떤 결론"의 논리 흐름을 담을 것
   - 예시: "EU 규제 강화에도 Meta의 일평균 사용자 32억 명은 줄지 않고 있으며, 광고 단가는 오히려 AI 타겟팅 고도화로 상승 중. 규제 벌금은 매출 대비 1~2% 수준으로 사업 모델 자체를 위협하기 어렵다."
4. 각 가설에 전제(premise) 2~3개를 포함
5. 전제 title: 핵심 주장 (15~30자, 예: "EU 벌금은 매출 대비 미미한 수준")
6. 전제 description: 그 전제를 뒷받침하는 구체적 근거와 데이터 (1~2문장)
   - 예시: "2024년 EU 벌금 총액 13억 유로는 Meta 연매출 1,500억 달러의 약 0.9%에 불과하며, 과거 벌금 부과 후에도 주가는 2주 내 회복했다."
7. 전제마다 추적할 지표의 indicator_db_id를 매핑하고, why에 "이 지표가 왜 이 전제를 검증하는 데 적합한지" 1문장으로 설명
   - ❌ "유가 관련" → ✅ "WTI 선물 가격이 배럴당 $80을 돌파하면 에너지 비용 상승이 현실화되는 신호"
8. target은 이슈와 가장 관련 있는 시장/종목/섹터
9. thesis_type은 가설 성격에 맞게 선택 (복수 가능)

## 지표 선택 원칙 (매우 중요)
- **카탈로그에 있는 지표만 사용**: 아래 목록에 없는 지표를 절대 만들지 마세요. "시장 점유율", "ARPU", "규제 비용" 같은 커스텀 지표는 금지합니다.
- **반드시 indicator_db_id를 사용**: 각 지표의 (id:숫자)를 recommended_indicators에 포함하세요.
- **업데이트 주기 균형 필수**: 일간 지표(주가, 환율, VIX 등) 최소 1개 + 필요 시 월간/분기 지표 혼합
- 분기 실적 지표(EPS, PER, ROE 등)만으로 전제를 구성하지 말 것 — 일간으로 추적 가능한 시장 지표를 우선 배치

## 핵심: 사용자가 두 카드를 비교해서 선택해야 합니다.
- 추상적이고 짧은 문구는 금지 (❌ "규제 영향 제한적", ❌ "강력한 사용자 기반")
- 구체적인 팩트, 수치, 논리를 포함할 것 (✅ "EU 벌금은 매출의 1% 미만으로 사업 위협 수준 아님")
- 두 가설이 같은 팩트를 정반대로 해석하는 구조가 이상적

{indicator_block}"""

    user_prompt = f"""다음 뉴스 이슈를 분석해서 bullish 1개 + bearish 1개 가설을 만들어주세요.
구체적인 수치와 논리적 근거를 포함해서 사용자가 어떤 가설이 더 설득력 있는지 판단할 수 있게 해주세요.

{context}"""

    return system_prompt, user_prompt


def get_suggestion_response_schema():
    """Suggestion Structured Output JSON 스키마."""
    suggestion_schema = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["bullish", "bearish"],
            },
            "title": {"type": "string"},
            "summary": {"type": "string"},
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
        "required": ["direction", "title", "summary", "target", "target_type",
                      "thesis_type", "premises"],
    }

    return {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "items": suggestion_schema,
            },
        },
        "required": ["suggestions"],
    }


def call_gemini_suggestions(system_prompt, user_prompt):
    """Gemini 호출: 가설 제안 (suggestion 전용 스키마)."""
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

        contents = [
            types.Content(role='user', parts=[types.Part(text=user_prompt)])
        ]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2000,
            temperature=0.4,
            response_mime_type="application/json",
            response_schema=get_suggestion_response_schema(),
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
        logger.exception(f"Gemini suggestion JSON parse failed: {e}")
        return None
    except Exception as e:
        logger.exception(f"Gemini suggestion call failed: {e}")
        return None
