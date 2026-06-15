"""
관심도 M1 배치 태스크 (CS-RD2).

Celery beat 등록 예시 (DatabaseScheduler 사용 시 PeriodicTask.objects.create로 등록):

    from django_celery_beat.models import PeriodicTask, CrontabSchedule
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="30", hour="22", day_of_week="1-5",  # 평일 22:30 UTC (07:30 KST+1)
        day_of_month="*", month_of_year="*",
        timezone="UTC",
    )
    PeriodicTask.objects.update_or_create(
        name="chainsight-attention-daily",
        defaults={
            "task": "chainsight-attention-daily",
            "crontab": schedule,
            "enabled": True,
        },
    )
"""

import logging

from celery import shared_task
from django.db.models import Max

from apps.chain_sight.services.attention_service import compute_attention_scores
from packages.shared.stocks.models import DailyPrice

logger = logging.getLogger(__name__)


@shared_task(
    name="chainsight-attention-daily",
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=600,
)
def compute_daily_attention():
    """
    최신 거래일 기준 관심도 M1 계산. 멱등 (upsert).

    Returns:
        dict: processed 종목 수, target_date
    """
    # 최신 거래일 = DailyPrice 테이블의 최대 date
    latest = DailyPrice.objects.aggregate(max_date=Max("date"))["max_date"]
    if not latest:
        logger.warning("compute_daily_attention: DailyPrice 데이터 없음")
        return {"processed": 0, "target_date": None}

    processed = compute_attention_scores(latest)
    logger.info("compute_daily_attention: date=%s, processed=%d", latest, processed)
    return {"processed": processed, "target_date": str(latest)}
