"""S계열 타이밍 지표 산출 + 스코어링 dispatch (TIMING-P1, D-TIMING-DECISIONS-5 ①-A).

기존 EODSignal ingest 경로(ingest.py)와 **불변 공존** — 이 모듈은 catalog `compute_key`를
가진 S계열 지표만 담당한다. 소스 = DailyPrice(3년 OHLC, P0 실측), 계산 = shared
`TechnicalIndicators`(순수함수 재사용). indicator_scorer(robust-Z)·aggregator·state_machine
코드는 무접촉 — bounded 스코어링만 dispatch에서 우회한다.
"""
import logging
from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.monitor.catalog import catalog_entry
from apps.monitor.models import IndicatorReading
from apps.monitor.services.indicator_scorer import score_indicator_from_model
from packages.shared.stocks.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

# 산출용 DailyPrice 조회 폭(달력일) — 최장창 지표(252 거래일 모멘텀·52주) + 스코어 윈도우(60)
# 여유 확보. 3년 보존이라 넉넉히 당기고, 저장은 트레일링 STORE_POINTS만.
COMPUTE_LOOKBACK_DAYS = 500
# 산출 시계열 중 저장(upsert)하는 트레일링 유효 포인트 수 — scorer 기본 window 60 + 버퍼.
STORE_POINTS = 120

# bounded 지표의 원시값 자연 범위 ([lo, hi] → [-1, 1] 선형).
BOUNDED_RANGE = {
    "high_52w_proximity": (0.0, 1.0),
    "rsi14": (0.0, 100.0),
}


# ── 시계열 산출 (순수 함수, DailyPrice 행 소비) ────────────────────────────────

def compute_technical_series(compute_key, dates, opens, highs, lows, closes, volumes):
    """compute_key별 파생 시계열 → [(date, value)] (계산 가능한 날만, 시간순).

    dates/closes 등은 날짜 오름차순 정렬 가정. TechnicalIndicators(shared) 재사용.
    """
    n = len(closes)
    out = []

    if compute_key == "sma200_gap":
        sma = TechnicalIndicators.calculate_sma(closes, 200)
        for i in range(n):
            if sma[i] and sma[i] != 0:
                out.append((dates[i], (closes[i] - sma[i]) / sma[i] * 100.0))

    elif compute_key == "momentum_12_1":
        # 12-1 모멘텀: (1개월 전 종가 / 12개월 전 종가 - 1). 거래일 근사 21/252.
        for i in range(n):
            if i >= 252 and closes[i - 252]:
                out.append((dates[i], (closes[i - 21] / closes[i - 252] - 1.0) * 100.0))

    elif compute_key == "high_52w_proximity":
        for i in range(n):
            if i >= 251:
                hi = max(highs[i - 251 : i + 1])
                if hi:
                    out.append((dates[i], closes[i] / hi))

    elif compute_key == "volume_ratio":
        for i in range(n):
            if i >= 19:
                window = volumes[i - 19 : i + 1]
                avg = sum(window) / len(window)
                if avg:
                    out.append((dates[i], volumes[i] / avg))

    elif compute_key == "macd_histogram":
        macd = TechnicalIndicators.calculate_macd(closes)
        hist = macd["histogram"]
        for i in range(n):
            if hist[i] is not None:
                out.append((dates[i], float(hist[i])))

    elif compute_key == "rsi14":
        rsi = TechnicalIndicators.calculate_rsi(closes, 14)
        for i in range(n):
            if rsi[i] is not None:
                out.append((dates[i], float(rsi[i])))

    else:
        raise ValueError(f"미지의 compute_key: {compute_key}")

    return out


def _asof_dt(d):
    """DailyPrice.date → 판독 시점 datetime(자정, aware). ingest.py와 동일 정규화."""
    return timezone.make_aware(datetime.combine(d, time.min))


def ingest_technical_for_indicator(indicator, as_of_date=None, store_points=STORE_POINTS):
    """S계열 지표 하나에 DailyPrice 산출 시계열 upsert. 반환 = 결과 dict.

    catalog `compute_key`가 없는 지표(기존 EODSignal 3종·custom)는 skip — ingest.py 소관.
    """
    from packages.shared.stocks.models import DailyPrice, Stock

    result = {
        "indicator_id": str(indicator.id),
        "symbol": indicator.monitor.target_ref,
        "source_key": indicator.source_key,
        "ingested": 0,
        "status": "ok",
    }

    if indicator.monitor.scope != "stock":
        result["status"] = "skip_non_stock"
        return result

    entry = catalog_entry("stock", indicator.source_key) if indicator.source_key else None
    compute_key = (entry or {}).get("compute_key")
    if not compute_key:
        result["status"] = "skip_not_technical"
        return result

    symbol = indicator.monitor.target_ref.upper()
    as_of = as_of_date or timezone.localdate()
    since = as_of - timedelta(days=COMPUTE_LOOKBACK_DAYS)

    rows = list(
        DailyPrice.objects.filter(
            stock__symbol=symbol, date__gte=since, date__lte=as_of
        ).order_by("date").values_list(
            "date", "open_price", "high_price", "low_price", "close_price", "volume"
        )
    )
    if not rows:
        result["status"] = (
            "skip_unknown_symbol"
            if not Stock.objects.filter(symbol=symbol).exists()
            else "no_data_in_range"
        )
        logger.warning("technical ingest: DailyPrice 없음 symbol=%s (%s)", symbol, result["status"])
        return result

    dates = [r[0] for r in rows]
    highs = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    closes = [float(r[4]) for r in rows]
    volumes = [float(r[5]) for r in rows]
    opens = [float(r[1]) for r in rows]

    series = compute_technical_series(
        compute_key, dates, opens, highs, lows, closes, volumes
    )
    if not series:
        # 히스토리 부족(요구 행수 미달) — reading 미생성 + 사유 로그(백필 불요, P0 실측 519종목 757행).
        result["status"] = "insufficient_history"
        logger.info(
            "technical ingest: 히스토리 부족 symbol=%s key=%s rows=%d (요구 미달)",
            symbol, compute_key, len(rows),
        )
        return result

    for d, value in series[-store_points:]:
        IndicatorReading.objects.update_or_create(
            indicator=indicator,
            asof=_asof_dt(d),
            defaults={"value": float(value), "validation_status": "ok"},
        )
        result["ingested"] += 1

    logger.info(
        "technical ingest 완료: indicator=%s symbol=%s key=%s ingested=%d",
        indicator.id, symbol, compute_key, result["ingested"],
    )
    return result


def ingest_technical_for_monitor(monitor, as_of_date=None, store_points=STORE_POINTS):
    """모니터의 active S계열 지표 전부 산출·upsert. 개별 실패 격리."""
    results = []
    for ind in monitor.indicators.filter(is_active=True):
        try:
            results.append(
                ingest_technical_for_indicator(
                    ind, as_of_date=as_of_date, store_points=store_points
                )
            )
        except Exception:  # noqa: BLE001 — 배치 격리
            logger.exception("technical ingest 실패: indicator=%s", ind.id)
    return results


# ── 스코어링 dispatch (bounded 우회, 나머지는 기존 robust-Z 통과) ──────────────

def bounded_linear_score(value, compute_key, support_direction):
    """유계 지표 원시값 → [-1, 1] 선형 매핑 (D-TIMING-DECISIONS-5 ①-A).

    robust-Z 대신 자연 범위 [lo, hi]를 [-1, 1]로 선형 사상. support_direction 반영.
    """
    lo, hi = BOUNDED_RANGE[compute_key]
    span = hi - lo
    s = 2.0 * (value - lo) / span - 1.0 if span else 0.0
    s = max(-1.0, min(1.0, s))
    if support_direction == "negative":
        s = -s
    return round(s, 4)


def score_indicator_dispatch(indicator, as_of_date=None):
    """지표 스코어 라우팅 — bounded는 선형 매핑, 그 외는 기존 score_indicator_from_model.

    비-bounded(기존 3종·custom·zscore S계열)는 **완전히 동일 경로**로 통과(행위보존).
    is_paused·override_score는 어느 모드든 기존 함수가 처리하도록 먼저 위임.
    """
    if indicator.is_paused or indicator.override_score is not None:
        return score_indicator_from_model(indicator, as_of_date=as_of_date)

    entry = catalog_entry("stock", indicator.source_key) if indicator.source_key else None
    if not entry or entry.get("scoring_mode") != "bounded":
        return score_indicator_from_model(indicator, as_of_date=as_of_date)

    # bounded: 최신 판독값을 선형 매핑
    qs = indicator.readings.filter(
        validation_status__in=["ok", "extreme_jump_allowed"]
    )
    if as_of_date:
        qs = qs.filter(asof__date__lte=as_of_date)
    latest = qs.order_by("-asof").values_list("value", flat=True).first()
    if latest is None:
        return {
            "score": 0.0, "raw_z": 0.0, "is_extreme_vol": False,
            "effective_window": 0, "is_neutral_mad": False, "is_sufficient": False,
        }
    score = bounded_linear_score(
        float(latest), entry["compute_key"], indicator.support_direction
    )
    return {
        "score": score, "raw_z": 0.0, "is_extreme_vol": False,
        "effective_window": 1, "is_neutral_mad": False, "is_sufficient": True,
        "scoring_mode": "bounded",
    }
