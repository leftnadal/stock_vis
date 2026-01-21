"""
Fundamentals API Views

FMP API를 통한 기업 펀더멘털 데이터 제공
- Key Metrics: 핵심 재무 지표
- Ratios: 재무 비율
- DCF: Discounted Cash Flow 분석
- Rating: 투자 등급
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone

from .services.fmp_fundamentals import FMPFundamentalsService
from .serializers_fundamentals import (
    KeyMetricSerializer,
    RatioSerializer,
    DCFSerializer,
    RatingSerializer,
    AllFundamentalsSerializer
)

logger = logging.getLogger(__name__)


class KeyMetricsView(APIView):
    """
    핵심 재무 지표 API

    GET /api/v1/stocks/fundamentals/key-metrics/{symbol}/

    Query Parameters:
        - period: 'annual' (연간, 기본값) 또는 'quarter' (분기)
        - limit: 반환할 기간 수 (기본값: 5, 최대: 40)

    Response:
        [
            {
                "symbol": "AAPL",
                "date": "2023-12-31",
                "pe_ratio": 25.3,
                "pb_ratio": 5.2,
                "roe": 0.45,
                ...
            }
        ]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """핵심 재무 지표 조회"""
        # Query Parameters
        period = request.query_params.get('period', 'annual')
        if period not in ['annual', 'quarter']:
            return Response(
                {"error": "period는 'annual' 또는 'quarter'여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            limit = int(request.query_params.get('limit', 5))
            limit = min(max(1, limit), 40)
        except ValueError:
            return Response(
                {"error": "limit는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPFundamentalsService()
        data = service.get_key_metrics(symbol.upper(), period=period, limit=limit)

        if not data:
            return Response(
                {"error": f"종목 {symbol}의 데이터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = KeyMetricSerializer(data, many=True)

        logger.info(
            f"Key Metrics API 호출 성공 (user: {request.user.username}, symbol: {symbol}, period: {period})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "symbol": symbol.upper(),
                "period": period,
                "count": len(serializer.data),
                "timestamp": timezone.now()
            }
        })


class RatiosView(APIView):
    """
    재무 비율 API

    GET /api/v1/stocks/fundamentals/ratios/{symbol}/

    Query Parameters:
        - period: 'annual' (연간, 기본값) 또는 'quarter' (분기)
        - limit: 반환할 기간 수 (기본값: 5, 최대: 40)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """재무 비율 조회"""
        period = request.query_params.get('period', 'annual')
        if period not in ['annual', 'quarter']:
            return Response(
                {"error": "period는 'annual' 또는 'quarter'여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            limit = int(request.query_params.get('limit', 5))
            limit = min(max(1, limit), 40)
        except ValueError:
            return Response(
                {"error": "limit는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPFundamentalsService()
        data = service.get_ratios(symbol.upper(), period=period, limit=limit)

        if not data:
            return Response(
                {"error": f"종목 {symbol}의 데이터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = RatioSerializer(data, many=True)

        logger.info(
            f"Ratios API 호출 성공 (user: {request.user.username}, symbol: {symbol}, period: {period})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "symbol": symbol.upper(),
                "period": period,
                "count": len(serializer.data),
                "timestamp": timezone.now()
            }
        })


class DCFView(APIView):
    """
    DCF 분석 API

    GET /api/v1/stocks/fundamentals/dcf/{symbol}/

    Response:
        {
            "symbol": "AAPL",
            "dcf": 175.50,
            "stock_price": 150.25,
            "discount_percentage": 16.8,
            "recommendation": "Undervalued"
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """DCF 분석 조회"""
        # FMP Service 호출
        service = FMPFundamentalsService()
        data = service.get_dcf(symbol.upper())

        if not data:
            return Response(
                {"error": f"종목 {symbol}의 DCF 데이터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = DCFSerializer(data)

        logger.info(
            f"DCF API 호출 성공 (user: {request.user.username}, symbol: {symbol})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "symbol": symbol.upper(),
                "timestamp": timezone.now()
            }
        })


class RatingView(APIView):
    """
    투자 등급 API

    GET /api/v1/stocks/fundamentals/rating/{symbol}/

    Response:
        {
            "symbol": "AAPL",
            "rating": "A+",
            "rating_score": 4.8,
            "rating_recommendation": "Strong Buy"
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """투자 등급 조회"""
        # FMP Service 호출
        service = FMPFundamentalsService()
        data = service.get_rating(symbol.upper())

        if not data:
            return Response(
                {"error": f"종목 {symbol}의 Rating 데이터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = RatingSerializer(data)

        logger.info(
            f"Rating API 호출 성공 (user: {request.user.username}, symbol: {symbol})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "symbol": symbol.upper(),
                "timestamp": timezone.now()
            }
        })


class AllFundamentalsView(APIView):
    """
    전체 펀더멘털 데이터 API (한 번에 조회)

    GET /api/v1/stocks/fundamentals/all/{symbol}/

    Query Parameters:
        - period: 'annual' (연간, 기본값) 또는 'quarter' (분기)

    Response:
        {
            "key_metrics": [...],
            "ratios": [...],
            "dcf": {...},
            "rating": {...}
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """전체 펀더멘털 데이터 조회"""
        period = request.query_params.get('period', 'annual')
        if period not in ['annual', 'quarter']:
            return Response(
                {"error": "period는 'annual' 또는 'quarter'여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPFundamentalsService()
        data = service.get_all_fundamentals(symbol.upper(), period=period)

        # 빈 데이터 체크
        if not any([data['key_metrics'], data['ratios'], data['dcf'], data['rating']]):
            return Response(
                {"error": f"종목 {symbol}의 펀더멘털 데이터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = AllFundamentalsSerializer(data)

        logger.info(
            f"All Fundamentals API 호출 성공 (user: {request.user.username}, symbol: {symbol}, period: {period})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "symbol": symbol.upper(),
                "period": period,
                "timestamp": timezone.now()
            }
        })
