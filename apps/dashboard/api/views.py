"""dashboard BFF API — 뉴스 스트립(S1). [D-DASH-BFF · D-NEWSAXIS-CONTRACT]"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.services.strip_service import build_news_strip


class NewsStripView(APIView):
    """GET /api/dashboard/news-strip — 홈 상단 뉴스 축 응축 스트립.

    인증 필수(user 스코프 = 보유·관심 티어). 읽기 전용. 응답 실패·빈 데이터도 200
    (빈 items 배열) — FE 실패 격리와 짝.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = build_news_strip(request.user)
        return Response(data)
