"""Indicator Matcher: 전제 텍스트 → 지표 추천 (설계 문서 5.2)"""

import json
import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)

# 키워드 룰 매칭 테이블
KEYWORD_RULES = [
    {
        'keywords': ['외국인', '외인', '순매수', '순매도', 'foreign'],
        'indicators': [{
            'name': '외국인 순매수 추이',
            'data_source': 'fmp',
            'data_params': {'metric': 'foreign_net_buy'},
            'indicator_type': 'market_data',
            'support_direction': 'positive',
            'reason': '외국인 투자자의 매매 동향은 시장 방향을 선행하는 핵심 지표입니다.',
        }],
    },
    {
        'keywords': ['금리', '연준', 'FOMC', 'fed', '기준금리', '금리인하', '금리인상'],
        'indicators': [
            {
                'name': '미국 기준금리 (Fed Funds Rate)',
                'data_source': 'fred',
                'data_params': {'series_id': 'FEDFUNDS'},
                'indicator_type': 'macro',
                'support_direction': 'negative',
                'reason': '기준금리 변동은 유동성과 할인율에 영향을 미칩니다.',
            },
            {
                'name': '미국 10년 국채 금리',
                'data_source': 'fred',
                'data_params': {'series_id': 'DGS10'},
                'indicator_type': 'macro',
                'support_direction': 'negative',
                'reason': '장기 금리는 시장 기대 인플레이션과 성장 전망을 반영합니다.',
            },
        ],
    },
    {
        'keywords': ['VIX', '공포', '변동성', '변동성지수', 'volatility'],
        'indicators': [{
            'name': 'VIX (공포지수)',
            'data_source': 'fmp',
            'data_params': {'symbol': '^VIX'},
            'indicator_type': 'macro',
            'support_direction': 'negative',
            'reason': 'VIX는 시장의 공포와 불확실성을 나타내는 대표적 지표입니다.',
        }],
    },
    {
        'keywords': ['환율', '달러', '원달러', 'USD', 'KRW', '원화'],
        'indicators': [{
            'name': '원/달러 환율',
            'data_source': 'fmp',
            'data_params': {'symbol': 'USDKRW'},
            'indicator_type': 'macro',
            'support_direction': 'negative',
            'reason': '환율 상승은 외국인 투자 매력도 감소와 수출 기업 수익성 변화를 의미합니다.',
        }],
    },
    {
        'keywords': ['RSI', 'MACD', '기술적', '과매수', '과매도', '이동평균', 'MA'],
        'indicators': [{
            'name': 'RSI (14일)',
            'data_source': 'fmp',
            'data_params': {'indicator': 'RSI', 'period': 14},
            'indicator_type': 'technical',
            'support_direction': 'positive',
            'reason': 'RSI는 단기 과매수/과매도 상태를 파악하는 기술적 지표입니다.',
        }],
    },
    {
        'keywords': ['센티먼트', '여론', '뉴스', '심리', '감성'],
        'indicators': [{
            'name': '뉴스 센티먼트',
            'data_source': 'news_sentiment',
            'data_params': {},
            'indicator_type': 'sentiment',
            'support_direction': 'positive',
            'reason': '뉴스 감성 분석은 시장 심리의 방향을 포착합니다.',
        }],
    },
    {
        'keywords': ['실적', 'EPS', '매출', '영업이익', '순이익', 'PER', 'earnings'],
        'indicators': [{
            'name': 'EPS 추이',
            'data_source': 'fmp',
            'data_params': {'metric': 'eps'},
            'indicator_type': 'market_data',
            'support_direction': 'positive',
            'reason': '기업 실적은 주가의 가장 근본적인 동력입니다.',
        }],
    },
    {
        'keywords': ['기관', '기관투자자', '연기금', '보험', '자산운용'],
        'indicators': [{
            'name': '기관 순매수 추이',
            'data_source': 'fmp',
            'data_params': {'metric': 'institutional_net_buy'},
            'indicator_type': 'market_data',
            'support_direction': 'positive',
            'reason': '기관투자자의 매매 패턴은 중장기 시장 방향을 시사합니다.',
        }],
    },
    {
        'keywords': ['S&P', 'S&P500', '나스닥', 'NASDAQ', '미국시장', '다우', 'DOW'],
        'indicators': [{
            'name': 'S&P 500',
            'data_source': 'fmp',
            'data_params': {'symbol': '^GSPC'},
            'indicator_type': 'market_data',
            'support_direction': 'positive',
            'reason': '미국 시장은 글로벌 위험선호도와 자금 흐름의 바로미터입니다.',
        }],
    },
    {
        'keywords': ['코스피', 'KOSPI', '종합주가지수'],
        'indicators': [{
            'name': 'KOSPI 지수',
            'data_source': 'fmp',
            'data_params': {'symbol': '^KS11'},
            'indicator_type': 'market_data',
            'support_direction': 'positive',
            'reason': 'KOSPI 지수는 한국 시장 전체의 방향을 보여주는 대표 지표입니다.',
        }],
    },
    {
        'keywords': ['선거', '정치', '정책', '대통령', '국회'],
        'indicators': [
            {
                'name': 'VIX (공포지수)',
                'data_source': 'fmp',
                'data_params': {'symbol': '^VIX'},
                'indicator_type': 'macro',
                'support_direction': 'negative',
                'reason': '정치적 불확실성은 시장 변동성 확대로 이어질 수 있습니다.',
            },
            {
                'name': 'KOSPI 지수',
                'data_source': 'fmp',
                'data_params': {'symbol': '^KS11'},
                'indicator_type': 'market_data',
                'support_direction': 'positive',
                'reason': '정치 이벤트의 시장 영향을 직접적으로 관측할 수 있습니다.',
            },
        ],
    },
]


def match_by_keywords(premise_text):
    """키워드 룰 매칭으로 지표 추천."""
    matched = []
    seen_names = set()
    text_lower = premise_text.lower()

    for rule in KEYWORD_RULES:
        for keyword in rule['keywords']:
            if keyword.lower() in text_lower or keyword in premise_text:
                for ind in rule['indicators']:
                    if ind['name'] not in seen_names:
                        matched.append(ind.copy())
                        seen_names.add(ind['name'])
                break

    return matched


def _sanitize_for_prompt(text, max_length=500):
    """프롬프트 인젝션 방지를 위한 사용자 입력 정제."""
    if not text:
        return ''
    # 길이 제한
    text = text[:max_length]
    # 프롬프트 구분자로 악용될 수 있는 패턴 제거
    text = text.replace('```', '').replace('---', '')
    return text.strip()


def match_by_gemini(premise_text, thesis=None):
    """Gemini 2.5 Flash로 지표 추천 (키워드 매칭 실패 시 fallback)."""
    try:
        from google import genai
        from google.genai import types

        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            logger.warning("Gemini API key not configured")
            return []

        client = genai.Client(api_key=api_key)

        safe_text = _sanitize_for_prompt(premise_text)
        thesis_context = ""
        if thesis:
            safe_title = _sanitize_for_prompt(thesis.title, max_length=100)
            safe_target = _sanitize_for_prompt(thesis.target, max_length=100)
            thesis_context = f"\n가설: {safe_title} ({thesis.get_direction_display()})\n대상: {safe_target}"

        prompt = f"""투자 전제: '{safe_text}'
{thesis_context}

이 전제를 측정할 수 있는 금융 지표 3~5개를 JSON 배열로 추천해줘.
각 항목은 다음 필드를 포함해야 해:
- name: 지표 이름 (한글)
- data_source: "fmp" | "fred" | "news_sentiment" | "manual"
- data_params: API 호출에 필요한 파라미터 (예: {{"symbol": "^VIX"}}, {{"series_id": "FEDFUNDS"}})
- indicator_type: "market_data" | "macro" | "technical" | "sentiment" | "custom"
- support_direction: "positive" (값이 오르면 전제 지지) | "negative" (값이 오르면 전제 반박)
- reason: 왜 이 지표가 이 전제를 측정하는 데 적합한지 (1줄)

JSON 배열만 반환해. 다른 텍스트 없이."""

        config = types.GenerateContentConfig(
            max_output_tokens=2000,
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config,
        )

        text = response.text if hasattr(response, 'text') and response.text else ''
        if not text:
            return []

        # JSON 추출
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if not json_match:
            return []

        indicators = json.loads(json_match.group())
        # 필수 필드 검증
        valid = []
        for ind in indicators:
            if all(k in ind for k in ('name', 'data_source', 'indicator_type', 'support_direction')):
                ind.setdefault('data_params', {})
                ind.setdefault('reason', '')
                valid.append(ind)

        return valid[:5]

    except Exception as e:
        logger.exception(f"Gemini indicator matching failed: {e}")
        return []


def match_indicators_for_premise(premise_text, thesis=None, user=None):
    """
    전제 텍스트 → 지표 추천 목록 반환.
    1. 키워드 룰 매칭 (빠름)
    2. 매칭 결과가 없으면 Gemini fallback
    """
    matched = match_by_keywords(premise_text)

    if not matched:
        matched = match_by_gemini(premise_text, thesis)

    return matched


def match_indicators_for_llm(collected):
    """
    LLM 빌더용 지표 매칭: PK 우선 2단계.

    1순위: indicator_db_id → INDICATOR_CATALOG 조회
    2순위: premise text → match_indicators_for_premise() fallback

    Args:
        collected: CollectedData (Pydantic model)

    Returns:
        list[dict] — {premise_title, indicator_name, why, signal_type, auto_matched, match_method, indicator}
    """
    from thesis.services.prompt_builder import get_indicator_by_id

    results = []
    seen_names = set()

    for premise in collected.premises:
        # 1순위: LLM이 추천한 indicator_db_id로 조회
        for rec in premise.recommended_indicators:
            if rec.indicator_db_id:
                cat_ind = get_indicator_by_id(rec.indicator_db_id)
                if cat_ind and cat_ind['name'] not in seen_names:
                    results.append({
                        'premise_title': premise.title,
                        'indicator': cat_ind,
                        'indicator_name': cat_ind['name'],
                        'why': rec.why,
                        'signal_type': rec.signal_type,
                        'auto_matched': True,
                        'match_method': 'pk',
                    })
                    seen_names.add(cat_ind['name'])

        # 2순위: PK 매칭 실패 시 키워드 룰 매칭만 사용
        # (match_by_gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외)
        pk_matched = any(
            rec.indicator_db_id and get_indicator_by_id(rec.indicator_db_id)
            for rec in premise.recommended_indicators
        )
        if not pk_matched:
            text_matches = match_by_keywords(premise.title)
            for ind in text_matches:
                if ind['name'] not in seen_names:
                    # 카탈로그에 존재하는 지표인지 최종 검증
                    catalog_entry = _find_in_catalog(ind['name'])
                    results.append({
                        'premise_title': premise.title,
                        'indicator': catalog_entry or ind,
                        'indicator_name': ind['name'],
                        'why': ind.get('reason', ''),
                        'signal_type': 'coincident',
                        'auto_matched': False,
                        'match_method': 'text',
                    })
                    seen_names.add(ind['name'])

    return results


def _find_in_catalog(name):
    """INDICATOR_CATALOG에서 이름으로 지표 검색."""
    from thesis.services.prompt_builder import INDICATOR_CATALOG
    for ind in INDICATOR_CATALOG:
        if ind['name'] == name:
            return ind
    return None
