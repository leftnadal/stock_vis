"""Market Pulse v2 — News fetch task (PR-B)."""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone as django_timezone

from marketpulse.models.news import MarketPulseNews
from marketpulse.services import news_aggregator, news_classifier

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="marketpulse.tasks.news.mp_fetch_news_hourly",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=180,
    time_limit=240,
)
def mp_fetch_news_hourly(self, **kwargs: Any) -> dict[str, Any]:
    try:
        agg = news_aggregator.fetch_all(**kwargs)
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    items = agg["items"]
    sources_stats = agg["stats"]

    classified = []
    skipped = 0
    for item in items:
        result = news_classifier.classify(
            title=item.title,
            summary=item.summary,
            explicit_symbols=item.explicit_symbols,
        )
        if result is None:
            skipped += 1
            continue
        classified.append((news_aggregator.url_hash(item.url), result, item))

    after_quota = news_classifier.apply_quota(classified)

    by_cat: dict[str, int] = {}
    created_n = 0
    updated_n = 0
    with transaction.atomic():
        for url_hash, result, item in after_quota:
            obj, created = MarketPulseNews.objects.update_or_create(
                url_hash=url_hash,
                defaults={
                    "category": result.category,
                    "source": item.source,
                    "title": item.title[:500],
                    "summary": item.summary,
                    "url": item.url[:1024],
                    "image_url": (item.image_url or "")[:1024],
                    "publisher": (item.publisher or "")[:200],
                    "entities": {
                        "tickers": result.matched_symbols,
                        "sectors": [],
                        "topics": result.matched_keywords,
                    },
                    "published_at": item.published_at,
                },
            )
            if created:
                created_n += 1
            else:
                updated_n += 1
            by_cat[result.category] = by_cat.get(result.category, 0) + 1

    return {
        "fetched_total": len(items),
        "classified": len(classified),
        "after_quota": len(after_quota),
        "created": created_n,
        "updated": updated_n,
        "skipped_unclassified": skipped,
        "by_category": by_cat,
        "sources": sources_stats,
        "ran_at": django_timezone.now().isoformat(),
    }
