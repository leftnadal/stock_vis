"""
주도주 지표 배치 태스크 (CS-M2 Slice 3).

beat 등록은 관리 명령 `register_chainsight_beats`로 수행
(DatabaseScheduler 사용 시 config dict는 무시됨 — bug #28).
"""

import logging

from celery import shared_task
from django.db.models import Max

from apps.chain_sight.services.leadership_compute import compute_leadership_scores
from packages.shared.stocks.models import DailyPrice

logger = logging.getLogger(__name__)


@shared_task(
    name="chainsight-leadership-daily",
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=900,
)
def compute_daily_leadership():
    """
    최신 거래일 기준 주도주 지표 4종 계산. 멱등 (upsert).

    Returns:
        dict: rows 산출 행 수, as_of_date.
    """
    latest = DailyPrice.objects.aggregate(max_date=Max("date"))["max_date"]
    if not latest:
        logger.warning("compute_daily_leadership: DailyPrice 데이터 없음")
        return {"rows": 0, "as_of_date": None}

    rows = compute_leadership_scores(latest)
    logger.info("compute_daily_leadership: as_of=%s, rows=%d", latest, rows)
    return {"rows": rows, "as_of_date": str(latest)}
