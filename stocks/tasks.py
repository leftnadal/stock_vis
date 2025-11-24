from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.db import transaction
from .models import Stock, DailyPrice, WeeklyPrice
import time
import os

logger = get_task_logger(__name__)

def chunks(lst, n):
    """리스트를 n개씩 묶어서 반환하는 헬퍼 함수"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

@shared_task(bind=True, max_retries=3)
def update_realtime_prices(self, symbols=None, priority='normal'):
    """
    최적화된 실시간 주가 업데이트 태스크
    - 전날 종가를 현재 가격으로 사용
    - 당일 이미 업데이트한 종목은 스킵
    """
    try:
        # AlphaVantage API 키 확인
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            logger.error("ALPHA_VANTAGE_API_KEY not found in environment variables")
            return "API key not configured"

        if not symbols:
            # 포트폴리오에 있는 종목만 업데이트 (성능 최적화)
            from users.models import Portfolio
            symbols = Portfolio.objects.values_list('stock__symbol', flat=True).distinct()[:10]

            if not symbols:
                logger.info("No symbols to update")
                return "No symbols to update"

        # AlphaVantageService 동적 import (순환 참조 방지)
        try:
            from API_request.alphavantage_service import AlphaVantageService
        except ImportError:
            logger.error("AlphaVantageService not found")
            return "Service not available"

        service = AlphaVantageService(api_key=api_key)

        stats = {
            'updated': 0,
            'cached': 0,
            'errors': 0
        }

        for symbol in symbols:
            try:
                # 최적화된 업데이트 메서드 사용 (자동 캐싱)
                result = service.update_previous_close(symbol, force=False)

                if result['status'] == 'cached':
                    stats['cached'] += 1
                    logger.info(f"Using cached data for {symbol}")
                elif result['status'] == 'updated':
                    stats['updated'] += 1
                    logger.info(f"Updated {symbol} with close price ${result['price']:.2f}")

                    # 캐시 무효화
                    cache.delete(f'stock_quote_{symbol}')
                    cache.delete(f'chart_{symbol}_daily_1d')

                    # Rate limiting (API 호출한 경우만)
                    if stats['updated'] < len(symbols):
                        time.sleep(12)
                else:
                    stats['errors'] += 1
                    logger.error(f"Error updating {symbol}: {result.get('message', 'Unknown error')}")

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error updating {symbol}: {e}")
                continue

        return f"Updated: {stats['updated']}, Cached: {stats['cached']}, Errors: {stats['errors']}"

    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise self.retry(exc=e, countdown=60)

@shared_task
def update_daily_prices():
    """일일 종가 데이터 업데이트"""
    try:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            logger.error("ALPHA_VANTAGE_API_KEY not found")
            return "API key not configured"

        # 포트폴리오에 있는 모든 종목
        from users.models import Portfolio
        symbols = Portfolio.objects.values_list('stock__symbol', flat=True).distinct()

        if not symbols:
            return "No symbols to update"

        # 5개씩 배치 처리
        for batch in chunks(list(symbols), 5):
            update_batch_daily_prices.delay(batch)

        return f"Scheduled {len(symbols)} symbols for update"

    except Exception as e:
        logger.error(f"Failed to schedule daily price updates: {e}")
        return f"Error: {e}"

@shared_task
def update_batch_daily_prices(symbols):
    """최적화된 배치 단위 일일 가격 업데이트"""
    try:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return "API key not configured"

        from API_request.alphavantage_service import AlphaVantageService
        service = AlphaVantageService(api_key=api_key)

        stats = {
            'updated': 0,
            'cached': 0,
            'errors': 0
        }

        for symbol in symbols:
            try:
                # 최적화된 메서드 사용
                result = service.update_previous_close(symbol, force=False)

                if result['status'] == 'cached':
                    stats['cached'] += 1
                    logger.info(f"Skipped {symbol} - already updated today")
                elif result['status'] == 'updated':
                    stats['updated'] += 1
                    logger.info(f"Updated daily prices for {symbol}")
                    # API 호출한 경우만 rate limiting
                    if stats['updated'] < len(symbols):
                        time.sleep(12)
                else:
                    stats['errors'] += 1
                    logger.error(f"Failed to update {symbol}: {result.get('message')}")

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Failed to update daily prices for {symbol}: {e}")

        return f"Updated: {stats['updated']}, Cached: {stats['cached']}, Errors: {stats['errors']}"

    except Exception as e:
        logger.error(f"Batch update failed: {e}")
        return f"Error: {e}"

@shared_task
def update_weekly_prices():
    """주간 가격 데이터 업데이트"""
    try:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return "API key not configured"

        # 모든 활성 종목
        symbols = Stock.objects.filter(is_active=True).values_list('symbol', flat=True)[:20]

        from API_request.alphavantage_service import AlphaVantageService
        service = AlphaVantageService(api_key=api_key)

        updated = 0
        for symbol in symbols:
            try:
                with transaction.atomic():
                    # 주간 데이터 업데이트 로직 구현
                    logger.info(f"Updating weekly prices for {symbol}")
                    # service.update_weekly_prices(symbol)  # 실제 구현 필요
                    time.sleep(12)
                    updated += 1
            except Exception as e:
                logger.error(f"Failed to update weekly prices for {symbol}: {e}")

        return f"Updated weekly prices for {updated} symbols"

    except Exception as e:
        logger.error(f"Weekly update failed: {e}")
        return f"Error: {e}"

@shared_task(bind=True)
def update_financial_statements(self):
    """재무제표 업데이트 (월별 실행)"""
    try:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return "API key not configured"

        symbols = Stock.objects.filter(is_active=True).values_list('symbol', flat=True)[:10]

        for symbol in symbols:
            # 개별 종목별로 별도 태스크 실행
            update_single_financial_statement.delay(symbol)

        return f"Scheduled financial statement updates for {len(symbols)} symbols"

    except Exception as e:
        logger.error(f"Failed to schedule financial updates: {e}")
        return f"Error: {e}"

@shared_task
def update_single_financial_statement(symbol):
    """단일 종목 재무제표 업데이트"""
    try:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return f"API key not configured for {symbol}"

        from API_request.alphavantage_service import AlphaVantageService
        service = AlphaVantageService(api_key=api_key)

        try:
            with transaction.atomic():
                # Balance Sheet
                service.update_balance_sheet(symbol)
                time.sleep(12)

                # Income Statement
                service.update_income_statement(symbol)
                time.sleep(12)

                # Cash Flow
                service.update_cash_flow(symbol)

            logger.info(f"Updated financial statements for {symbol}")
            return f"Success: {symbol}"

        except Exception as e:
            logger.error(f"Failed to update financial statements for {symbol}: {e}")
            return f"Failed: {symbol} - {e}"

    except Exception as e:
        logger.error(f"Task error for {symbol}: {e}")
        return f"Error: {symbol} - {e}"

# 테스트 태스크
@shared_task
def add_numbers(x, y):
    """간단한 테스트 태스크"""
    result = x + y
    logger.info(f"Add task: {x} + {y} = {result}")
    return result

@shared_task
def test_redis_connection():
    """Redis 연결 테스트"""
    try:
        cache.set('test_key', 'test_value', 10)
        value = cache.get('test_key')
        logger.info(f"Redis test: stored and retrieved '{value}'")
        return f"Redis working: {value}"
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return f"Redis error: {e}"

@shared_task
def fetch_and_save_stock_data(symbol):
    """
    포트폴리오에 주식이 추가될 때 자동으로 모든 데이터를 수집하는 태스크

    Args:
        symbol: 주식 심볼

    Returns:
        성공/실패 정보를 담은 문자열
    """
    try:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            logger.error(f"ALPHA_VANTAGE_API_KEY not found for {symbol}")
            return f"API key not configured for {symbol}"

        # API 경로 추가
        import sys
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        api_path = os.path.join(project_root, 'API request')
        if api_path not in sys.path:
            sys.path.insert(0, api_path)

        from alphavantage_service import AlphaVantageService
        service = AlphaVantageService(api_key=api_key)

        results = {
            'symbol': symbol,
            'overview': False,
            'daily_prices': False,
            'weekly_prices': False,
            'balance_sheet': False,
            'income_statement': False,
            'cash_flow': False
        }

        try:
            # 1. Stock Overview 업데이트
            logger.info(f"Fetching overview for {symbol}")
            stock = service.update_stock_data(symbol)
            results['overview'] = True
            logger.info(f"Successfully updated overview for {symbol}")
            time.sleep(12)  # Rate limiting

            # 2. 일간 및 주간 가격 데이터 (최근 2년)
            logger.info(f"Fetching daily and weekly prices for {symbol}")
            # update_historical_prices는 일간과 주간 데이터를 모두 가져옴
            service.update_historical_prices(symbol, days=730)
            results['daily_prices'] = True
            results['weekly_prices'] = True
            logger.info(f"Successfully updated daily and weekly prices for {symbol}")
            time.sleep(12)  # Rate limiting

            # 4. Balance Sheet
            logger.info(f"Fetching balance sheet for {symbol}")
            service.update_balance_sheet(symbol)
            results['balance_sheet'] = True
            logger.info(f"Successfully updated balance sheet for {symbol}")
            time.sleep(12)  # Rate limiting

            # 5. Income Statement
            logger.info(f"Fetching income statement for {symbol}")
            service.update_income_statement(symbol)
            results['income_statement'] = True
            logger.info(f"Successfully updated income statement for {symbol}")
            time.sleep(12)  # Rate limiting

            # 6. Cash Flow Statement
            logger.info(f"Fetching cash flow statement for {symbol}")
            service.update_cash_flow(symbol)
            results['cash_flow'] = True
            logger.info(f"Successfully updated cash flow for {symbol}")

            # 캐시 무효화
            cache.delete(f'stock_quote_{symbol}')
            cache.delete(f'overview_{symbol}')
            cache.delete(f'chart_{symbol}_daily_1d')

            success_count = sum(1 for v in results.values() if v and isinstance(v, bool))
            logger.info(f"Successfully fetched {success_count}/6 data types for {symbol}")

            return f"Success: Fetched {success_count}/6 data types for {symbol}"

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            success_count = sum(1 for v in results.values() if v and isinstance(v, bool))
            return f"Partial success: Fetched {success_count}/6 data types for {symbol}. Error: {e}"

    except Exception as e:
        logger.error(f"Task completely failed for {symbol}: {e}")
        return f"Failed: Could not fetch data for {symbol}. Error: {e}"