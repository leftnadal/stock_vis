"""
Concentration Celery task (PR-H) — `mp_calc_concentration_daily`.

소속: apps/market_pulse/tasks (app 레이어 Celery task).
역할: 평일 NY 17:15 — fetchers.fmp_weights로 SPY ETF holdings 가져온 뒤
  calculators.concentration로 top5/top10/HHI 산출 → ConcentrationSnapshot upsert.
스케줄: Beat name `mp_calc_concentration_daily`, crontab NY 17:15 평일.
주의: CB `fmp_etf`. FMP Starter quota 준수.
호출자: Celery Beat scheduler만.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.market_pulse.calculators import concentration as concentration_calc

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.concentration.mp_calc_concentration_daily",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    time_limit=180,
)
def mp_calc_concentration_daily(
    self, etf_symbol: str = "SPY", **kwargs: Any
) -> dict[str, Any]:
    etf_symbol = (etf_symbol or "SPY").upper()
    try:
        snapshot = concentration_calc.calculate_for_etf(etf_symbol)
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    return {
        "universe": snapshot.universe,
        "date": snapshot.date.isoformat(),
        "top5_weight": float(snapshot.top5_weight),
        "top10_weight": float(snapshot.top10_weight),
        "hhi": float(snapshot.hhi),
        "top_holdings": snapshot.top_holdings,
        "is_finalized": snapshot.is_finalized,
    }
