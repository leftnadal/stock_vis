"""지표 판독 이식 (MON-P2-INGEST): source_key별 EODSignal → IndicatorReading.

EODSignal(shared)은 **읽기 전용**(단방향 유지) — 여기서 쓰기·수집 변경 없음.
stock scope 카탈로그 3종만 대상. 멱등(update_or_create on (indicator, asof)).

백필 길이 N (게이트 확정, 근거=indicator_scorer 코드):
  - scorer 기본 z-score window = 60 (거래일, indicator_scorer.py:30)
  - 최소 충분치 = 5 관측 (effective_window < 5 → is_sufficient False, :53)
  → BACKFILL_DAYS = 120 (달력일). 120일 ≈ 85 거래일 > 기본 window 60(+버퍼) ≥ 5.
    거래일이 아닌 달력일 기준이라 휴장일 갭에도 window 관측치를 안정 확보.
  신규 모니터 = N일 백필, 이후 증분(같은 커맨드 재실행 시 upsert로 신규분만 추가).
"""
import logging
from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.monitor.models import IndicatorReading

logger = logging.getLogger(__name__)

BACKFILL_DAYS = 120  # 근거: 위 docstring (scorer window 60 + 버퍼, min 5)

# source_key → EODSignal 필드 (읽기 전용 소비)
INGEST_FIELD_BY_KEY = {
    "eod_composite": "composite_score",
    "change_percent": "change_percent",
    "dollar_volume": "dollar_volume",
}


def _asof_dt(d):
    """EODSignal.date(DateField) → 판독 시점 datetime(그날 자정, aware). 하루 1행 정규화."""
    return timezone.make_aware(datetime.combine(d, time.min))


def ingest_readings_for_indicator(indicator, backfill_days=BACKFILL_DAYS, as_of_date=None):
    """지표 하나에 EODSignal 백필. 반환 = 이식 결과 dict."""
    from packages.shared.stocks.models import EODSignal, Stock

    result = {
        "indicator_id": str(indicator.id),
        "symbol": indicator.monitor.target_ref,
        "source_key": indicator.source_key,
        "ingested": 0,
        "skipped_null": 0,
        "status": "ok",
    }

    # stock scope + 매핑 있는 source_key만
    if indicator.monitor.scope != "stock":
        result["status"] = "skip_non_stock"
        logger.info("ingest skip(비-stock scope): monitor=%s", indicator.monitor_id)
        return result
    field = INGEST_FIELD_BY_KEY.get(indicator.source_key)
    if not field:
        result["status"] = "skip_no_source"
        logger.info(
            "ingest skip(소스 미매핑): indicator=%s key=%r", indicator.id, indicator.source_key
        )
        return result

    symbol = indicator.monitor.target_ref.upper()
    as_of = as_of_date or timezone.localdate()
    since = as_of - timedelta(days=backfill_days)

    rows = list(
        EODSignal.objects.filter(
            stock__symbol=symbol, date__gte=since, date__lte=as_of
        ).order_by("date")
    )

    if not rows:
        # 결측 구분: 종목 미등록(미수집) vs 등록됐으나 범위 내 데이터 없음(휴장/미수집)
        if not Stock.objects.filter(symbol=symbol).exists():
            result["status"] = "skip_unknown_symbol"
            logger.warning("ingest skip(종목 미등록=미수집): symbol=%s", symbol)
        else:
            result["status"] = "no_data_in_range"
            logger.warning(
                "ingest: EODSignal 없음(범위 %s~%s, 휴장/미수집): symbol=%s", since, as_of, symbol
            )
        return result

    for eod in rows:
        value = getattr(eod, field, None)
        if value is None:
            result["skipped_null"] += 1
            continue
        IndicatorReading.objects.update_or_create(
            indicator=indicator,
            asof=_asof_dt(eod.date),
            defaults={"value": float(value), "validation_status": "ok"},
        )
        result["ingested"] += 1

    logger.info(
        "ingest 완료: indicator=%s symbol=%s field=%s ingested=%d skipped_null=%d",
        indicator.id, symbol, field, result["ingested"], result["skipped_null"],
    )
    return result


def ingest_readings_for_monitor(monitor, backfill_days=BACKFILL_DAYS, as_of_date=None):
    """모니터의 active 지표 전부 이식."""
    results = []
    for ind in monitor.indicators.filter(is_active=True):
        try:
            results.append(
                ingest_readings_for_indicator(ind, backfill_days=backfill_days, as_of_date=as_of_date)
            )
        except Exception:  # noqa: BLE001 — 배치 격리
            logger.exception("ingest 실패: indicator=%s", ind.id)
    return results
