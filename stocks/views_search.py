"""
종목 검색 및 자동완성 API 뷰
Alpha Vantage Symbol Search API를 활용
"""
import logging
import os
import time
from typing import Optional

import requests
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock

logger = logging.getLogger(__name__)


class SymbolSearchView(APIView):
    """Alpha Vantage API를 통한 종목 검색"""

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

        # Alpha Vantage API 호출
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return Response(
                {'error': 'API 키가 설정되지 않았습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'SYMBOL_SEARCH',
            'keywords': keywords,
            'apikey': api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 에러 체크
            if 'Error Message' in data:
                return Response(
                    {'error': 'Invalid API request'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if 'Note' in data:
                return Response(
                    {'error': 'API rate limit reached. Please try again later.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 결과 파싱
            matches = data.get('bestMatches', [])
            results = []

            for match in matches[:10]:  # 최대 10개 결과
                # US 주식만 필터링 (선택사항)
                if match.get('4. region') == 'United States':
                    results.append({
                        'symbol': match.get('1. symbol'),
                        'name': match.get('2. name'),
                        'type': match.get('3. type'),
                        'region': match.get('4. region'),
                        'market_open': match.get('5. marketOpen'),
                        'market_close': match.get('6. marketClose'),
                        'timezone': match.get('7. timezone'),
                        'currency': match.get('8. currency'),
                        'match_score': float(match.get('9. matchScore', 0))
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

        except requests.exceptions.RequestException as e:
            return Response(
                {'error': f'API 요청 실패: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
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

        # Alpha Vantage API 호출 (GLOBAL_QUOTE)
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return Response(
                {'error': 'API 키가 설정되지 않았습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 에러 체크
            if 'Error Message' in data:
                return Response(
                    {'valid': False, 'error': 'Invalid symbol'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if 'Note' in data:
                return Response(
                    {'error': 'API rate limit reached. Please try again later.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            quote = data.get('Global Quote', {})

            if not quote or not quote.get('01. symbol'):
                return Response(
                    {'valid': False, 'error': 'Symbol not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 결과 포맷팅
            result = {
                'valid': True,
                'symbol': quote.get('01. symbol'),
                'price': float(quote.get('05. price', 0)),
                'change': float(quote.get('09. change', 0)),
                'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                'volume': int(quote.get('06. volume', 0)),
                'latest_trading_day': quote.get('07. latest trading day')
            }

            # 10분간 캐시
            cache.set(cache_key, result, 600)

            return Response(result)

        except requests.exceptions.RequestException as e:
            return Response(
                {'error': f'API 요청 실패: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
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
        logger.info(f"Stock {symbol} already exists in database")
        return stock
    except Stock.DoesNotExist:
        logger.info(f"Stock {symbol} not found in database, fetching from API")

    # Alpha Vantage API로 종목 정보 조회
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        logger.error("ALPHA_VANTAGE_API_KEY not set")
        return None

    # GLOBAL_QUOTE API로 유효성 검증
    url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': api_key
    }

    try:
        logger.info(f"Fetching GLOBAL_QUOTE for {symbol}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 에러 체크
        if 'Error Message' in data:
            logger.error(f"Alpha Vantage error for {symbol}: {data.get('Error Message')}")
            return None

        if 'Note' in data:
            logger.error(f"Alpha Vantage rate limit for {symbol}: {data.get('Note')}")
            return None

        quote = data.get('Global Quote', {})

        if not quote or not quote.get('01. symbol'):
            logger.error(f"No quote data found for {symbol}")
            return None

        logger.info(f"Got quote data for {symbol}: price={quote.get('05. price')}")

        # Rate limit 대응을 위해 잠시 대기
        time.sleep(12)  # Alpha Vantage 무료 티어는 5 calls/min

        # COMPANY_OVERVIEW API로 회사 정보 조회
        overview_params = {
            'function': 'OVERVIEW',
            'symbol': symbol,
            'apikey': api_key
        }

        company_name = symbol  # 기본값

        try:
            logger.info(f"Fetching OVERVIEW for {symbol}")
            overview_response = requests.get(url, params=overview_params, timeout=10)
            overview_response.raise_for_status()
            overview_data = overview_response.json()

            if 'Name' in overview_data:
                company_name = overview_data['Name']
                logger.info(f"Got company name for {symbol}: {company_name}")
            else:
                logger.warning(f"No company name in overview for {symbol}")
        except Exception as e:
            logger.warning(f"Failed to get overview for {symbol}: {e}")
            # Overview 조회 실패 시 SYMBOL_SEARCH로 시도
            time.sleep(12)  # Rate limit 대응

            search_params = {
                'function': 'SYMBOL_SEARCH',
                'keywords': symbol,
                'apikey': api_key
            }

            try:
                logger.info(f"Fetching SYMBOL_SEARCH for {symbol}")
                search_response = requests.get(url, params=search_params, timeout=10)
                search_response.raise_for_status()
                search_data = search_response.json()

                matches = search_data.get('bestMatches', [])
                for match in matches:
                    if match.get('1. symbol') == symbol:
                        company_name = match.get('2. name', symbol)
                        logger.info(f"Got company name from search for {symbol}: {company_name}")
                        break
            except Exception as e:
                logger.warning(f"Failed to search for {symbol}: {e}")

        # Stock 객체 생성
        try:
            stock = Stock.objects.create(
                symbol=symbol,
                stock_name=company_name,
                real_time_price=float(quote.get('05. price', 0)),
                change=float(quote.get('09. change', 0)),
                change_percent=quote.get('10. change percent', '0%')  # 필드명 수정: change_percentage -> change_percent
            )
            logger.info(f"Created new stock {symbol} in database")
            return stock
        except Exception as e:
            logger.error(f"Failed to create stock {symbol} in database: {e}")
            return None

    except Exception as e:
        logger.error(f"Error validating/creating stock {symbol}: {e}")
        return None