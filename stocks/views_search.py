"""
종목 검색 및 자동완성 API 뷰
StockService Provider 추상화 사용 (FMP 기본)
"""
import logging
from typing import Optional

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock

logger = logging.getLogger(__name__)


class SymbolSearchView(APIView):
    """StockService를 통한 종목 검색"""

    def get(self, request):
        """
        종목 심볼 또는 회사명으로 검색

        Query Parameters:
            - keywords: 검색 키워드 (심볼 또는 회사명)
        """
        keywords = request.query_params.get('keywords', '').strip()

        if not keywords or len(keywords) < 2:
            return Response(
                {'error': '검색어는 최소 2글자 이상 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 캐시 확인
        cache_key = f"symbol_search_{keywords.lower()}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        try:
            from api_request.stock_service import get_stock_service

            service = get_stock_service()
            response = service.search_symbols(keywords)

            if not response.success:
                return Response(
                    {'error': f'검색 실패: {response.error}'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            results = []
            for idx, r in enumerate(response.data[:10]):
                # US 주식만 필터링 (exchange에 NYSE, NASDAQ, AMEX 포함)
                if r.exchange and any(
                    ex in r.exchange.upper()
                    for ex in ['NYSE', 'NASDAQ', 'AMEX']
                ):
                    results.append({
                        'symbol': r.symbol,
                        'name': r.name,
                        'type': r.type or 'Equity',
                        'region': r.exchange or 'United States',
                        'currency': r.currency or 'USD',
                        'match_score': 1.0 - (idx * 0.05),
                    })

            # 매치 스코어로 정렬
            results.sort(key=lambda x: x['match_score'], reverse=True)

            response_data = {
                'count': len(results),
                'results': results
            }

            # 5분간 캐시
            cache.set(cache_key, response_data, 300)

            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': f'서버 오류: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SymbolValidateView(APIView):
    """종목 심볼 유효성 검증 및 정보 조회"""

    def get(self, request, symbol):
        """
        특정 심볼의 유효성 검증 및 기본 정보 조회

        Path Parameters:
            - symbol: 종목 심볼
        """
        symbol = symbol.upper()

        # 캐시 확인
        cache_key = f"symbol_validate_{symbol}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        try:
            from api_request.stock_service import get_stock_service

            service = get_stock_service()
            response = service.get_quote(symbol)

            if not response.success:
                return Response(
                    {'valid': False, 'error': 'Symbol not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            quote = response.data

            result = {
                'valid': True,
                'symbol': quote.symbol,
                'price': float(quote.price) if quote.price else 0,
                'change': float(quote.change) if quote.change else 0,
                'change_percent': str(quote.change_percent) if quote.change_percent else '0',
                'volume': quote.volume or 0,
                'latest_trading_day': str(quote.latest_trading_day) if quote.latest_trading_day else None,
            }

            # 10분간 캐시
            cache.set(cache_key, result, 600)

            return Response(result)

        except Exception as e:
            return Response(
                {'error': f'서버 오류: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PopularSymbolsView(APIView):
    """인기 종목 리스트 제공"""

    def get(self, request):
        """
        자주 검색되는 인기 종목 리스트 반환
        """
        popular_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'type': 'Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'type': 'Technology'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'type': 'Technology'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'type': 'E-Commerce'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'type': 'Semiconductors'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'type': 'Social Media'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'type': 'Electric Vehicles'},
            {'symbol': 'BRK.B', 'name': 'Berkshire Hathaway Inc.', 'type': 'Conglomerate'},
            {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'type': 'Banking'},
            {'symbol': 'V', 'name': 'Visa Inc.', 'type': 'Financial Services'},
            {'symbol': 'IREN', 'name': 'Iris Energy Limited', 'type': 'Bitcoin Mining'},
            {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF', 'type': 'ETF'},
            {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'type': 'ETF'},
            {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'type': 'Semiconductors'},
            {'symbol': 'PLTR', 'name': 'Palantir Technologies', 'type': 'Software'},
        ]

        return Response({
            'count': len(popular_stocks),
            'results': popular_stocks
        })


def validate_and_create_stock(symbol: str) -> Optional[Stock]:
    """
    종목 심볼을 검증하고, 유효한 경우 Stock 객체를 생성 또는 반환

    Args:
        symbol: 종목 심볼 (예: 'AAPL')

    Returns:
        Stock 객체 또는 None (유효하지 않은 경우)
    """
    symbol = symbol.upper()

    # 이미 Stock이 존재하는지 확인
    try:
        stock = Stock.objects.get(symbol=symbol)
        return stock
    except Stock.DoesNotExist:
        pass

    try:
        from api_request.stock_service import get_stock_service

        service = get_stock_service()

        # 1. Quote로 유효성 검증
        quote_response = service.get_quote(symbol)
        if not quote_response.success:
            logger.error(f"Could not validate {symbol}: {quote_response.error}")
            return None

        quote = quote_response.data
        if not quote or not quote.symbol:
            return None

        # 2. Profile로 회사명 조회
        company_name = symbol
        profile_response = service.get_company_profile(symbol)
        if profile_response.success and profile_response.data:
            company_name = profile_response.data.name or symbol

        # 3. Stock 생성
        stock = Stock.objects.create(
            symbol=symbol,
            stock_name=company_name,
            real_time_price=float(quote.price) if quote.price else 0,
            change=float(quote.change) if quote.change else 0,
            change_percent=f"{quote.change_percent}%" if quote.change_percent else '0%',
        )
        return stock

    except Exception as e:
        logger.error(f"Error validating/creating stock {symbol}: {e}")
        return None
