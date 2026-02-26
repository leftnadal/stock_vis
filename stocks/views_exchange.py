"""
Exchange Quotes API Views

FMP API를 통한 실시간 시세 정보 제공
- Index Quotes: 주요 지수 시세
- Stock Quote: 개별 종목 시세
- Batch Quotes: 여러 종목 일괄 조회
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone

from .services.fmp_exchange_quotes import FMPExchangeQuotesService
from .serializers_exchange import (
    QuoteSerializer,
    IndexQuoteSerializer,
    MajorIndicesSerializer,
    SectorPerformanceSerializer,
    BatchQuotesResponseSerializer
)

logger = logging.getLogger(__name__)


class IndexQuotesView(APIView):
    """
    주요 지수 시세 API

    GET /api/v1/stocks/quotes/index/

    Response:
        주요 지수 ETF 리스트 (SPY, QQQ, DIA, IWM)
        [
            {
                "symbol": "SPY",
                "name": "SPDR S&P 500 ETF Trust",
                "price": 4500.25,
                "change": 25.30,
                "changes_percentage": 0.56,
                ...
            }
        ]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """주요 지수 시세 조회"""
        # FMP Service 호출
        service = FMPExchangeQuotesService()
        data = service.get_index_quotes()

        if not data:
            return Response(
                {"error": "지수 시세 데이터를 가져올 수 없습니다."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Serializer로 데이터 포맷팅
        serializer = IndexQuoteSerializer(data, many=True)

        logger.info(
            f"Index Quotes API 호출 성공 (user: {request.user.username}, count: {len(data)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "count": len(serializer.data),
                "timestamp": timezone.now()
            }
        })


class StockQuoteView(APIView):
    """
    개별 종목 실시간 시세 API

    GET /api/v1/stocks/quotes/{symbol}/

    Response:
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 175.50,
            "change": 2.30,
            "changes_percentage": 1.33,
            "volume": 50000000,
            "market_cap": 2800000000000,
            ...
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """개별 종목 시세 조회"""
        # FMP Service 호출
        service = FMPExchangeQuotesService()
        data = service.get_quote(symbol.upper())

        if not data:
            return Response(
                {"error": f"종목 {symbol}의 시세 데이터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = QuoteSerializer(data)

        logger.info(
            f"Stock Quote API 호출 성공 (user: {request.user.username}, symbol: {symbol})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "symbol": symbol.upper(),
                "timestamp": timezone.now()
            }
        })


class BatchQuotesView(APIView):
    """
    여러 종목 일괄 시세 API

    POST /api/v1/stocks/quotes/batch/

    Request Body:
        {
            "symbols": ["AAPL", "MSFT", "GOOGL"]
        }

    Response:
        {
            "quotes": [...],
            "total_count": 3,
            "timestamp": "2025-12-17T10:30:00"
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """여러 종목 일괄 시세 조회"""
        # Request Body 검증
        symbols = request.data.get('symbols', [])

        if not isinstance(symbols, list):
            return Response(
                {"error": "symbols는 배열이어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not symbols:
            return Response(
                {"error": "최소 1개 이상의 심볼이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(symbols) > 100:
            return Response(
                {"error": "최대 100개까지만 조회 가능합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPExchangeQuotesService()
        data = service.get_batch_quotes(symbols)

        if not data:
            return Response(
                {"error": "시세 데이터를 가져올 수 없습니다."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # 응답 데이터 구성
        response_data = {
            "quotes": data,
            "total_count": len(data),
            "timestamp": timezone.now()
        }

        # Serializer로 데이터 포맷팅
        serializer = BatchQuotesResponseSerializer(response_data)

        logger.info(
            f"Batch Quotes API 호출 성공 (user: {request.user.username}, symbols: {len(symbols)}, results: {len(data)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "requested_count": len(symbols),
                "returned_count": len(data)
            }
        })


class MajorIndicesView(APIView):
    """
    주요 3대 지수 API

    GET /api/v1/stocks/quotes/major-indices/

    Response:
        {
            "sp500": {...},
            "nasdaq": {...},
            "dow_jones": {...}
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """주요 3대 지수 조회 (S&P 500, NASDAQ, Dow Jones)"""
        # FMP Service 호출
        service = FMPExchangeQuotesService()
        data = service.get_major_indices()

        if not data:
            return Response(
                {"error": "주요 지수 데이터를 가져올 수 없습니다."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Serializer로 데이터 포맷팅
        serializer = MajorIndicesSerializer(data)

        logger.info(
            f"Major Indices API 호출 성공 (user: {request.user.username})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "timestamp": timezone.now()
            }
        })


class SectorPerformanceView(APIView):
    """
    섹터 성과 API

    GET /api/v1/stocks/quotes/sector-performance/

    Response:
        섹터 ETF 시세 리스트 (XLK, XLF, XLV 등)
        [
            {
                "symbol": "XLK",
                "name": "Technology Select Sector SPDR Fund",
                "price": 175.50,
                "change": 2.30,
                "changes_percentage": 1.33,
                ...
            }
        ]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """섹터 성과 조회 (섹터 ETF 기반)"""
        # FMP Service 호출
        service = FMPExchangeQuotesService()
        data = service.get_sector_performance()

        if not data:
            return Response(
                {"error": "섹터 성과 데이터를 가져올 수 없습니다."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Serializer로 데이터 포맷팅
        response_data = {"sectors": data}
        serializer = SectorPerformanceSerializer(response_data)

        logger.info(
            f"Sector Performance API 호출 성공 (user: {request.user.username}, count: {len(data)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "count": len(data),
                "timestamp": timezone.now()
            }
        })
