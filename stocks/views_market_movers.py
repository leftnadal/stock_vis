"""
Market Movers API Views

FMP API를 통한 시장 주도 종목 데이터 제공
- 상승 TOP (gainers)
- 하락 TOP (losers)
- 거래량 TOP (actives)
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.utils import timezone

from .services.fmp_market_movers import FMPMarketMoversService
from .serializers_market_movers import MarketMoversResponseSerializer

logger = logging.getLogger(__name__)


class MarketMoversView(APIView):
    """
    Market Movers API

    GET /api/v1/stocks/market-movers/

    Query Parameters:
        - limit: 각 카테고리별 종목 수 (기본값: 10, 최대: 20)

    Response:
        {
            "gainers": [...],
            "losers": [...],
            "actives": [...],
            "cached_at": "2025-12-16T10:30:00",
            "last_updated": "2025-12-16T10:30:15"
        }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Market Movers 데이터 조회 (공개 API)"""
        # limit 파라미터 검증 (최대 20개)
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = min(max(1, limit), 20)  # 1 ~ 20 범위로 제한
        except ValueError:
            return Response(
                {"error": "limit 파라미터는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPMarketMoversService()
        data = service.get_all_movers(limit=limit)

        # 응답 생성 시간 추가
        data['last_updated'] = timezone.now()

        # Serializer로 데이터 검증 및 포맷팅
        serializer = MarketMoversResponseSerializer(data)

        user_info = request.user.username if request.user.is_authenticated else 'anonymous'
        logger.info(
            f"Market Movers API 호출 성공 (user: {user_info}, limit: {limit})"
        )

        return Response(serializer.data)
