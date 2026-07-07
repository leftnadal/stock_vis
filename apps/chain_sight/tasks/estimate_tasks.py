"""
C8 원장 스냅샷 배치 (TH-3) — snapshot_analyst_estimates_task.

설계서 theme_heat_design.md v1.2.1 §7: 주간(금 마감 후), **Cycle 1 첫 배포일부터 가동**
(콜드 스타트 시계를 최대한 앞당김). 유니버스 전종목 컨센서스를 주간 EstimateSnapshot 으로
적립 → 후속 슬라이스가 60일 diff 로 C8(리비전 괴리) 산출.

모집단 = UniverseSnapshot(배치 일자 동결) — 라이브 재조회 금지(drift 차단, TH-3 결정 2).
멱등 upsert. 성분별 try/except 격리. macOS fork 안전(Bug #25): fork 후 DB 재연결.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="chainsight-snapshot-analyst-estimates",
    bind=True,
    max_retries=3,
    soft_time_limit=3600,
    time_limit=3660,
)
def snapshot_analyst_estimates_task(self):
    """유니버스 전종목 애널리스트 컨센서스 주간 스냅샷 (§5.3 콜드 스타트 시계)."""
    from django import db

    db.connections.close_all()  # macOS fork 안전 (Bug #25)

    from apps.chain_sight.services.estimate_service import snapshot_estimates_for_symbols
    from apps.chain_sight.services.universe_snapshot import (
        get_or_create_universe_snapshot,
    )
    from packages.shared.api_request.providers.fmp.client import FMPClient

    snapshot_date = timezone.now().date()
    symbols, _snap, _diff = get_or_create_universe_snapshot(
        batch_date=snapshot_date, log_fn=logger.info
    )
    client = FMPClient(api_key=settings.FMP_API_KEY)

    try:
        result = snapshot_estimates_for_symbols(client, symbols, snapshot_date)
    except Exception as exc:  # noqa: BLE001
        logger.error("snapshot_analyst_estimates_task 실패: %s", exc)
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))

    logger.info("EstimateSnapshot 주간 스냅샷 완료 (%s): %s", snapshot_date, result)
    return result
