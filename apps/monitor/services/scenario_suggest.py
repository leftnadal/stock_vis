"""L계열 가격 제안 + 정합 프리필 (TIMING-P2/P2.5, 읽기 전용).

빌더 4필드(진입·목표·손절·기한)를 서버측 1차 제시(3년 OHLC 클라 전송 금지). 진입=스윙 저점
(지지선)·손절=ATR×2·목표=스윙 고점(저항선)·기한=변동성 정합(coherence). 점수 파이프라인
무관 — 시나리오 파라미터 보조 제안일 뿐. 확정은 항상 사용자(3-B). 예측 아님(변동성 스케일링).
"""
import logging
from datetime import timedelta
from decimal import Decimal

from apps.monitor.services import coherence
from apps.monitor.services.technical import COMPUTE_LOOKBACK_DAYS
from packages.shared.stocks.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

# 스윙 저점(진입) 창 + ATR 손절 배수.
SWING_WINDOW = 20
ATR_PERIOD = 14
ATR_STOP_MULT = 2.0
# 스윙 고점(목표/저항) 창 — 진입 창과 대칭 개념, 기한 지평 근사 커버(~6개월 거래일).
RESISTANCE_WINDOW = 126
# 기한 후보 실패 시 고정 폴백(달력일).
FALLBACK_HORIZON_DAYS = 90
MIN_ROWS = ATR_PERIOD + 6


def _base_prices(symbol, as_of):
    """DailyPrice 로딩 + 진입/손절/목표 후보 산출. 부족 시 None 반환."""
    from packages.shared.stocks.models import DailyPrice

    from apps.monitor.services.scenario import latest_close

    since = as_of - timedelta(days=COMPUTE_LOOKBACK_DAYS)
    rows = list(
        DailyPrice.objects.filter(stock__symbol=symbol, date__gte=since, date__lte=as_of)
        .order_by("date")
        .values_list("high_price", "low_price", "close_price")
    )
    if len(rows) < MIN_ROWS:
        return None

    highs = [float(r[0]) for r in rows]
    lows = [float(r[1]) for r in rows]
    closes = [float(r[2]) for r in rows]

    close = latest_close(symbol, as_of=as_of) or closes[-1]
    support_low = min(lows[-SWING_WINDOW:])
    resistance_high = max(highs[-RESISTANCE_WINDOW:])
    atr_series = TechnicalIndicators.calculate_atr(highs, lows, closes, ATR_PERIOD)
    atr = next((v for v in reversed(atr_series) if v is not None), None)

    return {
        "close": round(close, 4),
        "support_low": round(support_low, 4),
        "resistance_high": round(resistance_high, 4),
        "atr": round(atr, 4) if atr is not None else None,
        "resistance_lookback": min(RESISTANCE_WINDOW, len(highs)),
    }


def suggest_scenario(symbol, as_of=None):
    """4필드 정합 프리필. 히스토리 부족 시 available=False.

    반환(기존 키 불변 + 추가): available·symbol·close·support_low·entry_suggest·atr·stop_suggest·
      target_suggest·horizon_days·deadline_suggest·rr_suggest·sigma·resistance_high·captions·
      omit(불변식 위반 시 사유)·basis.
    """
    from django.utils import timezone

    sym = symbol.upper()
    as_of = as_of or timezone.localdate()

    base = _base_prices(sym, as_of)
    if base is None:
        logger.info("scenario suggest: 히스토리 부족 symbol=%s", sym)
        return {"available": False, "symbol": sym}

    entry_suggest = base["support_low"]
    atr = base["atr"]
    stop_suggest = round(entry_suggest - ATR_STOP_MULT * atr, 4) if atr is not None else None
    target_suggest = base["resistance_high"]

    # 불변식 가드: stop < entry < target 위반 시 목표/기한 후보 생략(진입·손절만 제공).
    omit = None
    if stop_suggest is None:
        omit = "atr_unavailable"
    elif not (stop_suggest < entry_suggest < target_suggest):
        omit = "invariant_violation"  # 저항선이 진입 이하 등 — 목표/기한 생략

    sigma = coherence.daily_sigma(sym, as_of=as_of)
    horizon_days = None
    deadline_suggest = None
    rr_suggest = None
    if omit is None:
        horizon_days = coherence.horizon_for_target(entry_suggest, target_suggest, sigma)
        if horizon_days is None:
            horizon_days = FALLBACK_HORIZON_DAYS  # σ 부족 → 고정 폴백
            horizon_basis = "변동성 산출 불가 · 고정 90일"
        else:
            wk = round(horizon_days / 7)
            horizon_basis = f"변동성 기준 ~{wk}주 (σ={round(sigma, 4)})"
        deadline_suggest = (as_of + timedelta(days=horizon_days)).isoformat()
        rr_suggest = coherence.rr_ratio(entry_suggest, target_suggest, stop_suggest)
    else:
        horizon_basis = None

    return {
        "available": True,
        "symbol": sym,
        "close": base["close"],
        "support_low": base["support_low"],
        "resistance_high": base["resistance_high"],
        "atr": atr,
        "sigma": round(sigma, 6) if sigma is not None else None,
        "entry_suggest": entry_suggest,
        "stop_suggest": stop_suggest,
        "target_suggest": None if omit else target_suggest,
        "horizon_days": horizon_days,
        "deadline_suggest": deadline_suggest,
        "rr_suggest": rr_suggest,
        "omit": omit,
        "captions": {
            "entry": f"최근 {SWING_WINDOW}거래일 스윙 저점(지지선)",
            "stop": f"ATR({ATR_PERIOD}) {round(atr, 2) if atr else '—'}×{ATR_STOP_MULT:g}",
            "target": None if omit else f"최근 {base['resistance_lookback']}거래일 스윙 고점(저항선)",
            "deadline": horizon_basis,
        },
        "basis": (
            f"진입 {entry_suggest}(스윙 저점) · 손절 {stop_suggest}(ATR×{ATR_STOP_MULT:g}) · "
            f"목표 {target_suggest}(스윙 고점) · 기한 {horizon_basis or '—'}"
        ),
    }


def recompute_coherence(symbol, *, entry, target=None, deadline=None, stop=None, as_of=None):
    """사용자 확정값 → 나머지 정합 후보(자동 개서 아님, 힌트용). 예측 아님(변동성 스케일링).

    target 제공 → 기한 정합 / deadline 제공 → 목표 정합. R:R은 stop 있을 때 포함.
    반환: {sigma, coherent_deadline?, coherent_horizon_days?, coherent_target?, rr?, basis, note}
    """
    from django.utils import timezone

    sym = symbol.upper()
    as_of = as_of or timezone.localdate()
    sigma = coherence.daily_sigma(sym, as_of=as_of)

    out = {
        "symbol": sym,
        "sigma": round(sigma, 6) if sigma is not None else None,
        "note": "변동성 기준 정합 · 예측 아님",
    }

    entry_d = Decimal(str(entry))

    if target is not None:
        target_d = Decimal(str(target))
        hd = coherence.horizon_for_target(entry_d, target_d, sigma)
        if hd is not None:
            wk = round(hd / 7)
            out["coherent_horizon_days"] = hd
            out["coherent_deadline"] = (as_of + timedelta(days=hd)).isoformat()
            out["basis"] = f"목표 {target_d}이면 변동성 기준 ~{wk}주 (≈{round(hd / 30.4, 1)}개월)"
        else:
            out["basis"] = "정합 기한 산출 불가(변동성·가격 조건)"
        if stop is not None:
            out["rr"] = coherence.rr_ratio(entry_d, target_d, Decimal(str(stop)))

    elif deadline is not None:
        from datetime import date as _date

        d = deadline if isinstance(deadline, _date) else _date.fromisoformat(str(deadline))
        days = (d - as_of).days
        ct = coherence.target_for_horizon(entry_d, days, sigma)
        if ct is not None and days > 0:
            wk = round(days / 7)
            out["coherent_target"] = str(ct)
            out["basis"] = f"기한 ~{wk}주면 변동성 기준 목표 {ct}"
            if stop is not None:
                out["rr"] = coherence.rr_ratio(entry_d, ct, Decimal(str(stop)))
        else:
            out["basis"] = "정합 목표 산출 불가(변동성·기한 조건)"

    return out
