"""Market Pulse v2 — Concentration Celery task (PR-H)."""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from marketpulse.calculators import concentration as concentration_calc

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="marketpulse.tasks.concentration.mp_calc_concentration_daily",
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
