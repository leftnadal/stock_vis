"""L계열 가격 제안 (TIMING-P2 §3, 읽기 전용).

빌더에서 진입/손절가 후보를 서버측 산출(3년 OHLC 클라 전송 금지). DailyPrice + shared
`TechnicalIndicators`(ATR) 재사용. 점수 파이프라인 무관 — 시나리오 파라미터 보조 제안일 뿐
(D-TIMING-DECISIONS-5 L계열은 점수 미기여). 확정은 항상 사용자(3-B).
"""
import logging

from apps.monitor.services.technical import COMPUTE_LOOKBACK_DAYS
from packages.shared.stocks.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

# 스윙 저점 탐색 창(거래일) + ATR 손절 배수.
SWING_WINDOW = 20
ATR_PERIOD = 14
ATR_STOP_MULT = 2.0
# 제안 산출 최소 히스토리(ATR 14 + 여유).
MIN_ROWS = ATR_PERIOD + 6


def suggest_scenario(symbol, as_of=None):
    """종목의 진입(지지선)·손절(ATR×2) 후보 산출. 히스토리 부족 시 available=False.

    반환: {available, symbol, close, support_low, entry_suggest, atr, stop_suggest, basis}
    """
    from datetime import timedelta

    from django.utils import timezone

    from packages.shared.stocks.models import DailyPrice

    from apps.monitor.services.scenario import latest_close

    sym = symbol.upper()
    as_of = as_of or timezone.localdate()
    since = as_of - timedelta(days=COMPUTE_LOOKBACK_DAYS)

    rows = list(
        DailyPrice.objects.filter(stock__symbol=sym, date__gte=since, date__lte=as_of)
        .order_by("date")
        .values_list("high_price", "low_price", "close_price")
    )
    if len(rows) < MIN_ROWS:
        logger.info("scenario suggest: 히스토리 부족 symbol=%s rows=%d", sym, len(rows))
        return {"available": False, "symbol": sym}

    highs = [float(r[0]) for r in rows]
    lows = [float(r[1]) for r in rows]
    closes = [float(r[2]) for r in rows]

    close = latest_close(sym, as_of=as_of) or closes[-1]
    support_low = min(lows[-SWING_WINDOW:])  # 최근 스윙 저점 = 지지선 진입 후보

    atr_series = TechnicalIndicators.calculate_atr(highs, lows, closes, ATR_PERIOD)
    atr = next((v for v in reversed(atr_series) if v is not None), None)

    entry_suggest = round(support_low, 4)
    stop_suggest = round(support_low - ATR_STOP_MULT * atr, 4) if atr is not None else None

    return {
        "available": True,
        "symbol": sym,
        "close": round(close, 4),
        "support_low": round(support_low, 4),
        "entry_suggest": entry_suggest,
        "atr": round(atr, 4) if atr is not None else None,
        "stop_suggest": stop_suggest,
        "basis": (
            f"최근 {SWING_WINDOW}거래일 스윙 저점 {entry_suggest} 지지선 진입, "
            f"ATR({ATR_PERIOD}) {round(atr, 2) if atr else '—'}×{ATR_STOP_MULT:g} 손절 폭"
        ),
    }
