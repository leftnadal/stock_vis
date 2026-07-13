"""
Theme Heat API 뷰 (TH-15, 결정23B/24C) — 읽기 전용. 새 파일(기존 views.py 무수정).

E1 GET /api/v1/chainsight/theme-heat/          — 버튼바(테마 11종)
E2 GET /api/v1/chainsight/theme-heat/{theme}/  — 카드(단일 테마)

인증: IsAuthenticated (CS-CREDIT-CONSUME 대시보드 트랙 승계).
원장 조회만 — 재계산 없음(A1). 소비 차단은 blocked 구조로 값+사유 동봉(은닉 아님).
"""

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.services.heat_api_service import build_bar_items, build_card

logger = logging.getLogger(__name__)


@extend_schema(tags=["Chain Sight"], responses={200: OpenApiTypes.OBJECT})
class ThemeHeatBarView(APIView):
    """GET /api/v1/chainsight/theme-heat/ — 버튼바. computed(score desc)→accumulating(days desc)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = build_bar_items()
        return Response({"count": len(items), "themes": items})


@extend_schema(tags=["Chain Sight"], responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
class ThemeHeatCardView(APIView):
    """GET /api/v1/chainsight/theme-heat/{theme}/ — 카드. 미존재 테마 404."""

    permission_classes = [IsAuthenticated]

    def get(self, request, theme: str):
        card = build_card(theme)
        if card is None:
            return Response(
                {"error": f"테마 '{theme}'가 없습니다(sector HeatEntity 미존재)."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(card)
