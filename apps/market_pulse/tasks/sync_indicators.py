"""
Yahoo Finance 보조 sync task — `mp_sync_yahoo_indicators_daily`.

소속: apps/market_pulse/tasks (app 레이어 Celery task).
역할: FRED 미지원 지표(CBOE VIX3M, ICE MOVE)를 yfinance로 보완. ^VIX3M, ^MOVE 일별
  종가를 EconomicIndicator(VIX3M/MOVE) + IndicatorValue에 idempotent 저장.
  다음 사이클 `mp_calc_regime_15min`에서 최신값 즉시 반영.
스케줄: Beat name `mp_sync_yahoo_indicators_daily`, crontab NY 17:35 평일.
Celery 정책 (Bug #8):
    동기 yfinance 호출 (LLM 아니지만 일관성 차원에서 동기 유지).
    yfinance 자체 retry 사용, 본 task는 idempotent하여 별도 CB 미적용.

매일 1회 (KST 06:35 = NY 17:35) 평일 후. NY 17:15 mp_calc_concentration_daily 직후 실행해
다음 KST 06:15 mp_generate_brief_daily가 최신 데이터로 동작.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)


SERIES_MAP = {
    "VIX3M": "^VIX3M",
    "MOVE": "^MOVE",
}


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.sync_indicators.mp_sync_yahoo_indicators_daily",
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=180,
    time_limit=240,
)
def mp_sync_yahoo_indicators_daily(
    self, *, period: str = "3mo", **kwargs: Any
) -> dict[str, Any]:
    """
    Yahoo Finance에서 VIX3M, MOVE를 EconomicIndicator로 sync.

    Args:
        period: yfinance period 문자열 (3mo / 6mo / 1y).

    Returns:
        {'series': {code: {ticker, fetched, saved}}, 'total_saved': int}
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        logger.exception("yfinance not available: %s", exc)
        raise

    from macro.models.indicators import EconomicIndicator, IndicatorValue

    summary: dict[str, dict[str, Any]] = {}
    total_saved = 0

    try:
        for code, ticker in SERIES_MAP.items():
            try:
                indicator = EconomicIndicator.objects.get(code=code)
            except EconomicIndicator.DoesNotExist:
                summary[code] = {"ticker": ticker, "error": "indicator_not_seeded"}
                continue

            try:
                df = yf.download(
                    ticker,
                    period=period,
                    interval="1d",
                    progress=False,
                    auto_adjust=False,
                )
            except Exception as exc:  # noqa: BLE001
                summary[code] = {"ticker": ticker, "error": str(exc)}
                continue

            if df is None or df.empty:
                summary[code] = {"ticker": ticker, "error": "empty"}
                continue

            saved = 0
            with transaction.atomic():
                for idx, row in df.iterrows():
                    obs_date = idx.date() if hasattr(idx, "date") else idx
                    close_val = row.get("Close")
                    if hasattr(close_val, "item"):
                        try:
                            close_val = close_val.item()
                        except Exception:  # noqa: BLE001
                            close_val = float(close_val)
                    if close_val is None:
                        continue
                    try:
                        value = Decimal(str(close_val))
                    except (InvalidOperation, ValueError):
                        continue
                    _, created = IndicatorValue.objects.update_or_create(
                        indicator=indicator,
                        date=obs_date,
                        defaults={"value": value},
                    )
                    if created:
                        saved += 1

            indicator.last_updated = django_timezone.now()
            indicator.save(update_fields=["last_updated"])
            total_saved += saved
            summary[code] = {"ticker": ticker, "fetched": len(df), "saved": saved}

    except Exception as exc:
        logger.exception("mp_sync_yahoo_indicators_daily failure: %s", exc)
        countdown = 300 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    return {
        "series": summary,
        "total_saved": total_saved,
        "period": period,
    }
