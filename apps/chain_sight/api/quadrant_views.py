"""DSS-QUADRANT 섹터 사분면 read-only API (QUAD-IMPL-1 Slice 1).

GET /api/v1/chainsight/theme-heat/quadrant/ — 11 섹터 사분면 payload.
계산은 서비스(sector_quadrant.build_quadrant)로 분리·뷰는 얇게. DB 쓰기 0.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.services.sector_quadrant import build_quadrant


@extend_schema(tags=["Chain Sight"], responses={200: OpenApiTypes.OBJECT})
class SectorQuadrantView(APIView):
    """GET /api/v1/chainsight/theme-heat/quadrant/ — 섹터 사분면(Heat×수요 breadth)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_quadrant())
