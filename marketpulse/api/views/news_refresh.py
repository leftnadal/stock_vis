"""Market Pulse v2 — News Refresh endpoint (PR-J)."""
from __future__ import annotations

import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone as django_timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marketpulse.models.news import MarketPulseNews, NewsViewLog
from marketpulse.throttles import MarketPulseHourThrottle, MarketPulseUserThrottle

REFRESH_LIMIT = 6

CATEGORY_QUOTA = {
    MarketPulseNews.Category.MACRO: 2,
    MarketPulseNews.Category.SMART_MONEY: 2,
    MarketPulseNews.Category.MAG7: 2,
    MarketPulseNews.Category.SECTOR: 2,
    MarketPulseNews.Category.GEOPOLITICS: 1,
    MarketPulseNews.Category.INDEX: 1,
}


@extend_schema(
    summary='뉴스 6건 랜덤 픽 (24h user unique)',
    tags=['Market Pulse v2'],
    request=None,
    responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
)
class NewsRefreshView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def post(self, request, *args, **kwargs):
        user = request.user
        now = django_timezone.now()
        cutoff = now - timedelta(hours=24)
        viewed_date = django_timezone.localdate()

        seen_ids = set(
            NewsViewLog.objects.filter(user=user, viewed_date=viewed_date)
            .values_list('news_id', flat=True)
        )

        pool = list(
            MarketPulseNews.objects
            .filter(published_at__gte=cutoff)
            .exclude(pk__in=seen_ids)
            .order_by('-published_at')
        )

        picked: list[MarketPulseNews] = []
        counts: dict[str, int] = {cat: 0 for cat in CATEGORY_QUOTA}
        random.shuffle(pool)
        for n in pool:
            if len(picked) >= REFRESH_LIMIT:
                break
            cat_max = CATEGORY_QUOTA.get(n.category, 0)
            if counts.get(n.category, 0) >= cat_max:
                continue
            picked.append(n)
            counts[n.category] = counts.get(n.category, 0) + 1

        if len(picked) < REFRESH_LIMIT:
            for n in pool:
                if n in picked:
                    continue
                picked.append(n)
                if len(picked) >= REFRESH_LIMIT:
                    break

        with transaction.atomic():
            for n in picked:
                NewsViewLog.objects.get_or_create(user=user, news=n, viewed_date=viewed_date)
                n.mark_exposed()

        items = [
            {
                'id': n.pk, 'category': n.category, 'title': n.title,
                'summary': n.summary, 'url': n.url, 'publisher': n.publisher,
                'image_url': n.image_url,
                'published_at': n.published_at.isoformat(),
                'tickers': (n.entities or {}).get('tickers', []),
            }
            for n in picked
        ]
        return Response({
            '_meta': {
                'generated_at': now.isoformat(),
                'count': len(items),
                'pool_size': len(pool),
                'seen_count': len(seen_ids),
            },
            'items': items,
        })
