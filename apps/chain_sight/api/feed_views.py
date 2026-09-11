"""R2-S2 + S3-1 — "오늘 시장의 이야기" 피드 API (GET only, 읽기 전용)."""

from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.services.market_story_feed import build_market_story_feed

_ET = ZoneInfo("America/New_York")
# 응답 캐시 TTL(초). S3-1 STEP 0-2: NewsEntity 재조회 p95 368ms(콜드) → 표시 카드 제목·
# evidence 조회 비용을 응답 단위로 캐싱. 일 단위 데이터라 15분이면 신선(#15 키 일관).
FEED_CACHE_TTL = 900


class MarketStoryFeedView(APIView):
    """GET /api/v1/chainsight/feed/ — 오늘 시장의 이야기 피드.

    카드 3유형(daily_spike 묶음·weekly_active·new_sec) + meta(헤더) + evidence.
    외부콜 0·prod write 0. 응답은 (limit, ET 날짜) 키로 캐시(FEED_CACHE_TTL).
    """

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 30))
        except (TypeError, ValueError):
            limit = 30
        limit = max(1, min(limit, 50))

        today_et = timezone.now().astimezone(_ET).date().isoformat()
        cache_key = f"chainsight:story_feed:v1:{limit}:{today_et}"
        payload = cache.get(cache_key)
        if payload is None:
            payload = build_market_story_feed(limit=limit)
            cache.set(cache_key, payload, FEED_CACHE_TTL)
        return Response(payload)
