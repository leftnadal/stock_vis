"""R2-S2 — "오늘 시장의 이야기" 피드 API (GET only, 읽기 전용)."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.services.market_story_feed import build_market_story_feed


class MarketStoryFeedView(APIView):
    """GET /api/v1/chainsight/feed/ — 오늘 시장의 이야기 피드.

    카드 3유형(daily_spike·weekly_active·new_sec) + 요약 + as_of. 외부콜 0·prod write 0.
    """

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 30))
        except (TypeError, ValueError):
            limit = 30
        limit = max(1, min(limit, 50))
        return Response(build_market_story_feed(limit=limit))
