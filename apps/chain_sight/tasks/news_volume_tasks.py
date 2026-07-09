"""
C3 내러티브 볼륨 집계 태스크 (TH-10, 결정16=A) — 설계 앵커 §7.

- aggregate_theme_news_volume_task: 일간(heat 이전) — DailyNewsKeyword → ThemeNewsVolume
  테마×일자 mention_count 집계(멱등). 뉴스 파이프라인 후단.

공통: macOS fork 안전(#25), retry 관례, 명시 beat 등록(#28).
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="chainsight-aggregate-theme-news",
    bind=True,
    max_retries=3,
    soft_time_limit=600,
    time_limit=660,
)
def aggregate_theme_news_volume_task(self, days_back: int = 2):
    """일간 C3 집계 (§7). 최근 days_back 일 재집계(멱등, 지연 도착 키워드 흡수)."""
    from datetime import timedelta

    from django import db

    db.connections.close_all()  # macOS fork 안전 (Bug #25)

    from apps.chain_sight.services.c3_narrative_service import aggregate_theme_news_volume

    today = timezone.now().date()
    total = {"days": 0, "written": 0}
    try:
        for i in range(days_back):
            r = aggregate_theme_news_volume(target_date=today - timedelta(days=i))
            total["days"] += r["days"]
            total["written"] += r["written"]
    except Exception as exc:  # noqa: BLE001
        logger.error("aggregate_theme_news_volume_task 실패: %s", exc)
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))

    logger.info("C3 집계 완료: %s", total)
    return total
