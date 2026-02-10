"""
Stock Screener API Views

FMP API를 통한 조건별 종목 검색 제공
- 시가총액, 베타, 거래량, 섹터 등 다양한 필터 지원
- 사전 정의된 스크리너 (대형주, 고배당주 등)
- Enhanced 필터 지원 (PE, ROE, EPS Growth 등)
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.utils import timezone

from .services.fmp_screener import FMPScreenerService
from .serializers_screener import (
    ScreenedStockSerializer,
    ScreenerRequestSerializer,
    ScreenerResponseSerializer
)
from serverless.services.enhanced_screener_service import EnhancedScreenerService

logger = logging.getLogger(__name__)


class StockScreenerView(APIView):
    """
    종목 스크리너 API

    GET /api/v1/stocks/screener/

    Query Parameters:
        - market_cap_more_than: 최소 시가총액 (USD)
        - market_cap_lower_than: 최대 시가총액 (USD)
        - price_more_than: 최소 주가 (USD)
        - price_lower_than: 최대 주가 (USD)
        - beta_more_than: 최소 베타
        - beta_lower_than: 최대 베타
        - volume_more_than: 최소 거래량
        - volume_lower_than: 최대 거래량
        - dividend_more_than: 최소 배당률 (%)
        - dividend_lower_than: 최대 배당률 (%)
        - is_etf: ETF 여부 (true/false)
        - is_actively_trading: 활성 거래 종목만 (true/false, 기본값: true)
        - sector: 섹터 필터 (예: Technology, Healthcare)
        - industry: 산업 필터
        - exchange: 거래소 필터 (NYSE, NASDAQ, AMEX 등)
        - limit: 반환할 종목 수 (기본값: 100, 최대: 1000)

    Response:
        {
            "stocks": [...],
            "total_count": 150,
            "filters_applied": {...}
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """조건별 종목 검색"""
        # Query Parameters 검증
        serializer = ScreenerRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        params = serializer.validated_data

        # Enhanced 필터 감지
        enhanced_service = EnhancedScreenerService()
        enhanced_filters = self._extract_enhanced_filters(params)
        is_enhanced = bool(enhanced_filters)

        if is_enhanced:
            # Enhanced 스크리너 사용 (PE/ROE/EPS Growth 등 지원)
            filters = self._build_enhanced_filters(params)
            result = enhanced_service.screen_enhanced(
                filters=filters,
                limit=params.get('limit', 100)
            )
            stocks = result.get('results', [])

            # Serializer로 데이터 포맷팅
            serializer_data = ScreenedStockSerializer(stocks, many=True)

            username = request.user.username if request.user.is_authenticated else 'anonymous'
            logger.info(
                f"Enhanced Screener API 호출 (user: {username}, is_enhanced: True, results: {len(stocks)})"
            )

            return Response({
                "success": True,
                "data": {
                    "stocks": serializer_data.data,
                    "total_count": result.get('count', len(stocks)),
                    "filters_applied": result.get('filters_applied', {}),
                },
                "meta": {
                    "timestamp": timezone.now(),
                    "is_enhanced": True,
                    "total_before_filter": result.get('total_before_filter', 0),
                }
            })

        # 기존 FMP Service 사용 (Instant 프리셋)
        service = FMPScreenerService()
        stocks = service.screen_stocks(
            market_cap_more_than=params.get('market_cap_more_than'),
            market_cap_lower_than=params.get('market_cap_lower_than'),
            price_more_than=params.get('price_more_than'),
            price_lower_than=params.get('price_lower_than'),
            beta_more_than=params.get('beta_more_than'),
            beta_lower_than=params.get('beta_lower_than'),
            volume_more_than=params.get('volume_more_than'),
            volume_lower_than=params.get('volume_lower_than'),
            dividend_more_than=params.get('dividend_more_than'),
            dividend_lower_than=params.get('dividend_lower_than'),
            is_etf=params.get('is_etf'),
            is_actively_trading=params.get('is_actively_trading', True),
            sector=params.get('sector'),
            industry=params.get('industry'),
            exchange=params.get('exchange'),
            limit=params.get('limit', 100)
        )

        # Quote 데이터로 변동률 등 추가 정보 병합
        stocks = service.enrich_with_quotes(stocks)

        # 클라이언트 필터 적용 (change_percent)
        stocks = self._apply_client_filters(stocks, params)

        # 응답 데이터 구성
        response_data = {
            "stocks": stocks,
            "total_count": len(stocks),
            "filters_applied": {k: v for k, v in params.items() if v is not None}
        }

        # Serializer로 데이터 포맷팅
        response_serializer = ScreenerResponseSerializer(response_data)

        username = request.user.username if request.user.is_authenticated else 'anonymous'
        logger.info(
            f"Stock Screener API 호출 성공 (user: {username}, filters: {len(params)}, results: {len(stocks)})"
        )

        return Response({
            "success": True,
            "data": response_serializer.data,
            "meta": {
                "timestamp": timezone.now(),
                "is_enhanced": False,
            }
        })

    def _extract_enhanced_filters(self, params: dict) -> dict:
        """Enhanced 필터 추출"""
        enhanced_keys = {
            'pe_ratio_min', 'pe_ratio_max',
            'roe_min', 'roe_max',
            'eps_growth_min', 'eps_growth_max',
            'revenue_growth_min', 'revenue_growth_max',
            'debt_equity_max',
            'current_ratio_min',
            'rsi_min', 'rsi_max',
        }
        return {k: v for k, v in params.items() if k in enhanced_keys and v is not None}

    def _build_enhanced_filters(self, params: dict) -> dict:
        """Enhanced 스크리너용 필터 구성"""
        filters = {}

        # FMP 직접 지원 필터 매핑
        fmp_mapping = {
            'market_cap_more_than': 'market_cap_min',
            'market_cap_lower_than': 'market_cap_max',
            'price_more_than': 'price_min',
            'price_lower_than': 'price_max',
            'beta_more_than': 'beta_min',
            'beta_lower_than': 'beta_max',
            'volume_more_than': 'volume_min',
            'volume_lower_than': 'volume_max',
            'dividend_more_than': 'dividend_min',
            'dividend_lower_than': 'dividend_max',
            'sector': 'sector',
            'exchange': 'exchange',
            'is_etf': 'is_etf',
            'is_actively_trading': 'is_actively_trading',
        }

        for param_key, filter_key in fmp_mapping.items():
            if params.get(param_key) is not None:
                filters[filter_key] = params[param_key]

        # Enhanced 필터 직접 추가
        enhanced_keys = [
            'pe_ratio_min', 'pe_ratio_max',
            'roe_min', 'roe_max',
            'eps_growth_min', 'eps_growth_max',
            'revenue_growth_min', 'revenue_growth_max',
            'debt_equity_max',
            'current_ratio_min',
            'rsi_min', 'rsi_max',
            'change_percent_min', 'change_percent_max',
        ]

        for key in enhanced_keys:
            if params.get(key) is not None:
                filters[key] = params[key]

        return filters

    def _apply_client_filters(self, stocks: list, params: dict) -> list:
        """클라이언트 사이드 필터 적용 (change_percent)"""
        change_min = params.get('change_percent_min')
        change_max = params.get('change_percent_max')

        if change_min is None and change_max is None:
            return stocks

        result = []
        for stock in stocks:
            change_pct = stock.get('changesPercentage')
            if change_pct is None:
                continue

            try:
                change_pct = float(change_pct)
                if change_min is not None and change_pct < change_min:
                    continue
                if change_max is not None and change_pct > change_max:
                    continue
                result.append(stock)
            except (ValueError, TypeError):
                continue

        return result


class LargeCapStocksView(APIView):
    """
    대형주 스크리너 API

    GET /api/v1/stocks/screener/large-cap/

    Query Parameters:
        - limit: 반환할 종목 수 (기본값: 50)

    Response:
        시가총액 100억 달러 이상 종목 리스트
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """대형주 조회"""
        try:
            limit = int(request.query_params.get('limit', 50))
            limit = min(max(1, limit), 1000)
        except ValueError:
            return Response(
                {"error": "limit는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPScreenerService()
        stocks = service.get_large_cap_stocks(limit=limit)

        # Serializer로 데이터 포맷팅
        serializer = ScreenedStockSerializer(stocks, many=True)

        username = request.user.username if request.user.is_authenticated else 'anonymous'
        logger.info(
            f"Large Cap Stocks API 호출 성공 (user: {username}, results: {len(stocks)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "filter": "market_cap > $10B",
                "count": len(stocks),
                "timestamp": timezone.now()
            }
        })


class HighDividendStocksView(APIView):
    """
    고배당주 스크리너 API

    GET /api/v1/stocks/screener/high-dividend/

    Query Parameters:
        - min_dividend: 최소 배당률 (%, 기본값: 3.0)
        - limit: 반환할 종목 수 (기본값: 50)

    Response:
        고배당 종목 리스트
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """고배당주 조회"""
        try:
            min_dividend = float(request.query_params.get('min_dividend', 3.0))
            limit = int(request.query_params.get('limit', 50))
            limit = min(max(1, limit), 1000)
        except ValueError:
            return Response(
                {"error": "파라미터 형식이 올바르지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPScreenerService()
        stocks = service.get_high_dividend_stocks(min_dividend=min_dividend, limit=limit)

        # Serializer로 데이터 포맷팅
        serializer = ScreenedStockSerializer(stocks, many=True)

        logger.info(
            f"High Dividend Stocks API 호출 성공 (user: {request.user.username}, results: {len(stocks)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "filter": f"dividend_yield >= {min_dividend}%",
                "count": len(stocks),
                "timestamp": timezone.now()
            }
        })


class SectorStocksView(APIView):
    """
    섹터별 종목 스크리너 API

    GET /api/v1/stocks/screener/sector/{sector}/

    Path Parameters:
        - sector: 섹터명 (예: Technology, Healthcare, Financials)

    Query Parameters:
        - limit: 반환할 종목 수 (기본값: 100)

    Response:
        해당 섹터 종목 리스트
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, sector):
        """섹터별 종목 조회"""
        try:
            limit = int(request.query_params.get('limit', 100))
            limit = min(max(1, limit), 1000)
        except ValueError:
            return Response(
                {"error": "limit는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPScreenerService()
        stocks = service.get_sector_stocks(sector=sector, limit=limit)

        if not stocks:
            return Response(
                {"error": f"섹터 '{sector}'의 종목을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = ScreenedStockSerializer(stocks, many=True)

        logger.info(
            f"Sector Stocks API 호출 성공 (user: {request.user.username}, sector: {sector}, results: {len(stocks)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "sector": sector,
                "count": len(stocks),
                "timestamp": timezone.now()
            }
        })


class LowBetaStocksView(APIView):
    """
    저변동성 종목 스크리너 API

    GET /api/v1/stocks/screener/low-beta/

    Query Parameters:
        - max_beta: 최대 베타 (기본값: 0.8)
        - limit: 반환할 종목 수 (기본값: 50)

    Response:
        저변동성 종목 리스트
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """저변동성 종목 조회"""
        try:
            max_beta = float(request.query_params.get('max_beta', 0.8))
            limit = int(request.query_params.get('limit', 50))
            limit = min(max(1, limit), 1000)
        except ValueError:
            return Response(
                {"error": "파라미터 형식이 올바르지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPScreenerService()
        stocks = service.get_low_beta_stocks(max_beta=max_beta, limit=limit)

        # Serializer로 데이터 포맷팅
        serializer = ScreenedStockSerializer(stocks, many=True)

        logger.info(
            f"Low Beta Stocks API 호출 성공 (user: {request.user.username}, results: {len(stocks)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "filter": f"beta < {max_beta}",
                "count": len(stocks),
                "timestamp": timezone.now()
            }
        })


class ExchangeStocksView(APIView):
    """
    거래소별 종목 스크리너 API

    GET /api/v1/stocks/screener/exchange/{exchange}/

    Path Parameters:
        - exchange: 거래소 코드 (NYSE, NASDAQ, AMEX 등)

    Query Parameters:
        - limit: 반환할 종목 수 (기본값: 100)

    Response:
        해당 거래소 종목 리스트
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, exchange):
        """거래소별 종목 조회"""
        try:
            limit = int(request.query_params.get('limit', 100))
            limit = min(max(1, limit), 1000)
        except ValueError:
            return Response(
                {"error": "limit는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FMP Service 호출
        service = FMPScreenerService()
        stocks = service.get_exchange_stocks(exchange=exchange, limit=limit)

        if not stocks:
            return Response(
                {"error": f"거래소 '{exchange}'의 종목을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializer로 데이터 포맷팅
        serializer = ScreenedStockSerializer(stocks, many=True)

        logger.info(
            f"Exchange Stocks API 호출 성공 (user: {request.user.username}, exchange: {exchange}, results: {len(stocks)})"
        )

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {
                "exchange": exchange.upper(),
                "count": len(stocks),
                "timestamp": timezone.now()
            }
        })
