"""
Finalize + Purge tasks (PR-O) — 일일 마감과 TTL 정리.

소속: apps/market_pulse/tasks (app 레이어 Celery tasks 운영).
역할:
  - mp_finalize_daily: 평일 NY 16:30 — 4 스냅샷 is_finalized=True + 캐시 무효화.
  - mp_purge_news_daily: 매일 NY 14:00 — 90일 초과 + is_exposed=False 뉴스 삭제(D5).
  - mp_purge_news_view_log_daily: 매일 NY 14:05 — 48h+ NewsViewLog 정리.
스케줄: 각 Beat name 동일, crontab 위 시각.
호출자: Celery Beat scheduler만.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone as django_timezone

from apps.market_pulse.api import cache as cache_keys
from apps.market_pulse.models.news import MarketPulseNews, NewsViewLog
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)

logger = logging.getLogger(__name__)


def _finalize_queryset(model, **filters) -> int:
    now = django_timezone.now()
    qs = model.objects.filter(is_finalized=False, **filters)
    return qs.update(is_finalized=True, finalized_at=now)


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.finalize.mp_finalize_daily",
    max_retries=3,
    default_retry_delay=120,
    soft_time_limit=120,
    time_limit=180,
)
def mp_finalize_daily(self, **kwargs: Any) -> dict[str, int]:
    today = django_timezone.localdate()
    try:
        regime_n = _finalize_queryset(RegimeSnapshot, date__lte=today)
        breadth_n = _finalize_queryset(BreadthSnapshot, date__lte=today)
        sector_n = _finalize_queryset(SectorFlowSnapshot, date__lte=today)
        conc_n = _finalize_queryset(ConcentrationSnapshot, date__lte=today)
        cache_keys.invalidate_all()
    except Exception as exc:
        countdown = 120 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    return {
        "regime_finalized": regime_n,
        "breadth_finalized": breadth_n,
        "sector_finalized": sector_n,
        "concentration_finalized": conc_n,
        "cache_invalidated": True,
    }


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.finalize.mp_purge_news_daily",
    max_retries=3,
    default_retry_delay=120,
    soft_time_limit=120,
    time_limit=180,
)
def mp_purge_news_daily(
    self, *, retention_days: int = 90, **kwargs: Any
) -> dict[str, int]:
    cutoff = django_timezone.now() - timedelta(days=retention_days)
    try:
        deleted, _ = MarketPulseNews.objects.filter(
            shown_on_layer0=False,
            published_at__lt=cutoff,
        ).delete()
    except Exception as exc:
        countdown = 120 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    return {"deleted": deleted, "retention_days": retention_days}


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.finalize.mp_purge_news_view_log_daily",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=60,
    time_limit=120,
)
def mp_purge_news_view_log_daily(
    self, *, retention_hours: int = 48, **kwargs: Any
) -> dict[str, int]:
    cutoff = django_timezone.now() - timedelta(hours=retention_hours)
    try:
        deleted, _ = NewsViewLog.objects.filter(viewed_at__lt=cutoff).delete()
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    return {"deleted": deleted, "retention_hours": retention_hours}
