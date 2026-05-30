"""EOD Keyword Collector: EOD 시그널 → ContextKeyword 변환 (Phase B, PR-10)

규칙 기반 — EODSignal 모델의 signals JSONField에서 임계값 규칙으로 키워드 추출.
"""

import logging
from datetime import date, timedelta

from thesis.services.builder_events import log_event
from thesis.services.keyword_cache import ContextKeyword, save_keywords

logger = logging.getLogger(__name__)

# 시그널 ID → 키워드 매핑 규칙
SIGNAL_KEYWORD_MAP = {
    'T1_oversold': {'text': 'RSI 과매도 구간', 'role': 'signal'},
    'T1_overbought': {'text': 'RSI 과매수 구간', 'role': 'signal'},
    'V1': {'text': '거래량 급증', 'role': 'signal'},
    'PV1': {'text': '거래량-가격 효율 상승', 'role': 'support'},
    'PV2': {'text': '스마트머니 집적 징후', 'role': 'support'},
    'P5': {'text': '52주 신고가 돌파', 'role': 'support'},
    'P7': {'text': '저점 반등 신호', 'role': 'support'},
    'MA1_golden': {'text': '골든크로스 발생', 'role': 'support'},
    'MA1_dead': {'text': '데드크로스 발생', 'role': 'risk'},
    'S1': {'text': '섹터 내 상대 강세', 'role': 'support'},
    'S2': {'text': '섹터 내 상대 약세', 'role': 'risk'},
}


def extract_eod_keywords(target: str) -> list[ContextKeyword]:
    """
    EODSignal에서 target 종목의 최근 시그널을 키워드로 변환.
    target은 종목명 또는 symbol.
    """
    from packages.shared.stocks.models import EODSignal

    # target → symbol 변환
    symbol = _resolve_symbol(target)
    if not symbol:
        return []

    # 최근 3일 시그널 조회
    today = date.today()
    cutoff = today - timedelta(days=3)
    eod_signals = EODSignal.objects.filter(
        stock__symbol=symbol,
        date__gte=cutoff,
    ).order_by('-date').first()

    if not eod_signals or not eod_signals.signals:
        return []

    keywords = []
    seen = set()
    for sig in eod_signals.signals:
        sig_id = sig.get('id', '')

        # 직접 매핑
        if sig_id in SIGNAL_KEYWORD_MAP and sig_id not in seen:
            mapping = SIGNAL_KEYWORD_MAP[sig_id]
            keywords.append(ContextKeyword(
                text=mapping['text'],
                source='eod',
                role=mapping['role'],
            ))
            seen.add(sig_id)

        # RSI 특수 처리 (signal 데이터에서 RSI 값 추출)
        if sig_id == 'T1' and sig_id not in seen:
            direction = sig.get('direction', '')
            if direction == 'bearish':
                keywords.append(ContextKeyword(text='RSI 과매도 구간', source='eod', role='signal'))
            elif direction == 'bullish':
                keywords.append(ContextKeyword(text='RSI 과매수 구간', source='eod', role='signal'))
            seen.add(sig_id)

    return keywords[:5]


def _resolve_symbol(target: str) -> str | None:
    """종목명/symbol → symbol 변환."""
    from packages.shared.stocks.models import Stock
    stock = Stock.objects.filter(symbol__iexact=target).first()
    if stock:
        return stock.symbol
    stock = Stock.objects.filter(name__icontains=target).first()
    if stock:
        return stock.symbol
    return None


def collect_eod_keywords(target: str):
    """EOD 키워드 추출 + KeywordCache 저장."""
    try:
        keywords = extract_eod_keywords(target)
        save_keywords(target, 'eod', keywords)
        log_event('keyword_extracted', {
            'source': 'eod',
            'target': target,
            'count': len(keywords),
        })
    except Exception as e:
        log_event('keyword_extraction_failed', {
            'source': 'eod',
            'target': target,
            'error': str(e),
        })
        logger.exception(f"EOD keyword extraction failed for {target}: {e}")
