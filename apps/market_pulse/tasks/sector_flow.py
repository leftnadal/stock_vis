"""
Sector Flow Celery task (PR-G) — `mp_calc_sector_5min`.

소속: apps/market_pulse/tasks (app 레이어 Celery task).
역할: 평일 09:30~16:30 매 5분 — calculators.sector_flow로 11 GICS 섹터 ETF 상대강도·
  cross-dispersion 산출 → SectorFlowSnapshot upsert(long-format 11 row/cycle).
스케줄: Beat name `mp_calc_sector_5min`, crontab `*/5` 평일.
호출자: Celery Beat scheduler만.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.market_pulse.calculators import sector_flow as sector_calc

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.sector_flow.mp_calc_sector_5min",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=180,
    time_limit=240,
)
def mp_calc_sector_5min(self, **kwargs: Any) -> dict[str, Any]:
    try:
        snapshots = sector_calc.calculate()
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    leaders = sorted(snapshots, key=lambda s: s.rank_in_universe)[:3]
    laggards = sorted(snapshots, key=lambda s: s.rank_in_universe, reverse=True)[:3]
    return {
        "date": snapshots[0].date.isoformat() if snapshots else None,
        "rows_inserted": len(snapshots),
        "leaders": [
            {"symbol": s.market_index_id, "rel_strength": float(s.rel_strength)}
            for s in leaders
        ],
        "laggards": [
            {"symbol": s.market_index_id, "rel_strength": float(s.rel_strength)}
            for s in laggards
        ],
        "cross_dispersion": float(snapshots[0].cross_dispersion) if snapshots else 0,
        "rotation_index": float(snapshots[0].rotation_index) if snapshots else 0,
    }
