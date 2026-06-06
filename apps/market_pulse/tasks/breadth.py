"""
Breadth Celery task (PR-F) — `mp_calc_breadth_5min`.

소속: apps/market_pulse/tasks (app 레이어 Celery task).
역할: 평일 09:30~16:30 매 5분 — calculators.breadth로 advance/decline·52w high/low·
  AD-line 누적 산출 → BreadthSnapshot upsert.
스케줄: Beat name `mp_calc_breadth_5min`, crontab `*/5`.
호출자: Celery Beat scheduler만.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.market_pulse.calculators import breadth as breadth_calc

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.breadth.mp_calc_breadth_5min",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=180,
    time_limit=240,
)
def mp_calc_breadth_5min(self, universe: str = "SPY", **kwargs: Any) -> dict[str, Any]:
    universe = (universe or "SPY").upper()
    if universe != "SPY":
        return {"universe": universe, "status": "skipped_phase2"}

    try:
        snapshot = breadth_calc.calculate(universe=universe)
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    return {
        "universe": snapshot.universe,
        "date": snapshot.date.isoformat(),
        "advance": snapshot.advance_count,
        "decline": snapshot.decline_count,
        "unchanged": snapshot.unchanged_count,
        "total": snapshot.total_count,
        "new_high_52w": snapshot.new_high_52w,
        "new_low_52w": snapshot.new_low_52w,
        "ad_line": snapshot.ad_line,
        "ad_line_change": snapshot.ad_line_change,
        "is_finalized": snapshot.is_finalized,
    }
