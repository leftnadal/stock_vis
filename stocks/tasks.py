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
            from api_request.alphavantage_service import AlphaVantageService
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

        from api_request.alphavantage_service import AlphaVantageService
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
def aggregate_weekly_prices(target_week_end=None):
    """
    DailyPrice → WeeklyPrice DB 집계 (API 호출 없음)

    이미 수집된 DailyPrice 데이터를 ISO 주차 기준으로 WeeklyPrice로 변환.
    Beat 스케줄: 토요일 01:00 (금요일 EOD 동기화 이후)

    Args:
        target_week_end: 대상 주 금요일 날짜 (YYYY-MM-DD 문자열, 기본: 직전 금요일)
    """
    from datetime import date, timedelta
    from collections import defaultdict
    from django.db.models import Max, Min, Sum, Avg
    from .models import SP500Constituent

    try:
        today = date.today()

        if target_week_end:
            week_end = date.fromisoformat(target_week_end)
        else:
            # 직전 금요일 계산
            days_since_friday = (today.weekday() - 4) % 7
            if days_since_friday == 0 and today.weekday() != 4:
                days_since_friday = 7
            week_end = today - timedelta(days=days_since_friday)

        # 해당 주 월~금 범위
        week_start = week_end - timedelta(days=4)

        logger.info(f"Aggregating weekly prices for {week_start} ~ {week_end}")

        # S&P 500 활성 종목 기준
        sp500_symbols = list(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
        )

        if not sp500_symbols:
            return {'week_end': str(week_end), 'symbols_aggregated': 0, 'created': 0, 'updated': 0}

        # 해당 주간의 모든 DailyPrice 조회
        daily_prices = DailyPrice.objects.filter(
            stock__symbol__in=sp500_symbols,
            date__gte=week_start,
            date__lte=week_end,
        ).select_related('stock')

        # 종목별 그룹화
        symbol_prices = defaultdict(list)
        for dp in daily_prices:
            symbol_prices[dp.stock_id].append(dp)

        created = 0
        updated = 0

        for symbol, prices in symbol_prices.items():
            if not prices:
                continue

            prices_sorted = sorted(prices, key=lambda x: x.date)

            first_day = prices_sorted[0]
            last_day = prices_sorted[-1]

            defaults = {
                'open_price': first_day.open_price,
                'high_price': max(p.high_price for p in prices_sorted),
                'low_price': min(p.low_price for p in prices_sorted),
                'close_price': last_day.close_price,
                'volume': sum(p.volume for p in prices_sorted),
                'week_start_date': first_day.date,
                'week_end_date': last_day.date,
                'average_volume': sum(p.volume for p in prices_sorted) // len(prices_sorted),
            }

            try:
                stock = Stock.objects.get(symbol=symbol)
            except Stock.DoesNotExist:
                logger.warning(f"Stock {symbol} not found, skipping")
                continue

            _, was_created = WeeklyPrice.objects.update_or_create(
                stock=stock,
                date=last_day.date,
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        result = {
            'week_end': str(week_end),
            'symbols_aggregated': created + updated,
            'created': created,
            'updated': updated,
        }
        logger.info(f"Weekly aggregation complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Weekly aggregation failed: {e}")
        return f"Error: {e}"

@shared_task
def sync_sp500_financials(batch_size=101):
    """
    S&P 500 재무제표 순환 배치 업데이트 (FMP Provider 사용)

    S&P 500 전체를 5거래일에 1회전 완료.
    재무제표 없는 종목 우선 → 오래된 순 정렬 → 상위 batch_size 선택.

    Beat 스케줄: 평일 20:00 (EOD 동기화 이후)

    Args:
        batch_size: 1일 처리 종목 수 (기본: 101, 5일에 ~503개 커버)
    """
    from datetime import datetime
    from django.db.models import Max
    from .models import SP500Constituent, BalanceSheet

    try:
        sp500_symbols = list(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
        )

        if not sp500_symbols:
            return {'scheduled': 0, 'total_sp500': 0, 'oldest_update': None}

        # 각 심볼의 마지막 재무제표 업데이트 시각 조회
        last_updates = (
            BalanceSheet.objects
            .filter(stock__symbol__in=sp500_symbols)
            .values('stock__symbol')
            .annotate(last_update=Max('created_at'))
        )
        update_map = {row['stock__symbol']: row['last_update'] for row in last_updates}

        # 재무제표 없는 종목 우선, 그 다음 오래된 순
        never_updated = [s for s in sp500_symbols if s not in update_map]
        has_data = sorted(
            [s for s in sp500_symbols if s in update_map],
            key=lambda s: update_map[s],
        )
        priority_list = never_updated + has_data

        batch = priority_list[:batch_size]

        for symbol in batch:
            update_financials_with_provider.delay(symbol)

        oldest_update = str(update_map[has_data[0]]) if has_data else None

        result = {
            'scheduled': len(batch),
            'total_sp500': len(sp500_symbols),
            'never_updated': len(never_updated),
            'oldest_update': oldest_update,
        }
        logger.info(f"S&P 500 financials sync scheduled: {result}")
        return result

    except Exception as e:
        logger.error(f"S&P 500 financials sync failed: {e}")
        return f"Error: {e}"


@shared_task
def bulk_sync_sp500_financials():
    """
    S&P 500 재무제표 초기 대량 동기화 (수동 실행 전용)

    Beat 스케줄에 등록하지 않음. DB에 재무제표가 없는 종목을 모두 업데이트.
    countdown으로 2초 간격 분산 → FMP 분당 300 제한 내 안전하게 처리.

    수동 호출:
        from stocks.tasks import bulk_sync_sp500_financials
        bulk_sync_sp500_financials.delay()
    """
    from .models import SP500Constituent, BalanceSheet

    try:
        sp500_symbols = list(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
        )

        # 재무제표가 있는 종목 집합
        has_financials = set(
            BalanceSheet.objects
            .filter(stock__symbol__in=sp500_symbols)
            .values_list('stock__symbol', flat=True)
            .distinct()
        )

        missing = [s for s in sp500_symbols if s not in has_financials]

        for idx, symbol in enumerate(missing):
            update_financials_with_provider.apply_async(
                args=[symbol],
                countdown=idx * 2,  # 2초 간격으로 분산
            )

        result = {
            'total_sp500': len(sp500_symbols),
            'already_have_data': len(has_financials),
            'total_missing': len(missing),
            'scheduled': len(missing),
        }
        logger.info(f"Bulk S&P 500 financials sync scheduled: {result}")
        return result

    except Exception as e:
        logger.error(f"Bulk S&P 500 financials sync failed: {e}")
        return f"Error: {e}"

@shared_task
def update_single_financial_statement(symbol):
    """단일 종목 재무제표 업데이트"""
    try:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return f"API key not configured for {symbol}"

        from api_request.alphavantage_service import AlphaVantageService
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
        api_path = os.path.join(project_root, 'api_request')
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


# ============================================================
# StockService 기반 태스크 (Provider 추상화 사용)
# ============================================================

@shared_task(bind=True, max_retries=3)
def update_stock_with_provider(self, symbol, use_fallback=True):
    """
    Provider 추상화를 사용한 주식 데이터 업데이트

    StockService를 통해 Feature Flag에 따라 Alpha Vantage 또는 FMP 사용.
    Fallback 기능으로 주 provider 실패 시 대체 provider 자동 사용.

    Args:
        symbol: 주식 심볼
        use_fallback: Fallback 사용 여부 (기본: True)

    Returns:
        결과 문자열
    """
    try:
        from api_request.stock_service import get_stock_service

        service = get_stock_service()
        symbol = symbol.upper().strip()

        results = {
            'symbol': symbol,
            'stock_data': False,
            'prices': False,
            'financials': False,
        }

        # 1. 주식 기본 정보 업데이트
        try:
            logger.info(f"[Provider] Updating stock data for {symbol}")
            stock = service.update_stock_data(symbol)
            results['stock_data'] = True
            logger.info(f"[Provider] Stock data updated for {symbol}")
            time.sleep(12)  # Rate limiting
        except Exception as e:
            logger.error(f"[Provider] Failed to update stock data for {symbol}: {e}")

        # 2. 가격 데이터 업데이트
        try:
            logger.info(f"[Provider] Updating prices for {symbol}")
            price_result = service.update_historical_prices(symbol, days=730)
            results['prices'] = True
            logger.info(f"[Provider] Prices updated for {symbol}: {price_result}")
            time.sleep(12)
        except Exception as e:
            logger.error(f"[Provider] Failed to update prices for {symbol}: {e}")

        # 3. 재무제표 업데이트
        try:
            logger.info(f"[Provider] Updating financial statements for {symbol}")
            financial_result = service.update_financial_statements(symbol)
            results['financials'] = True
            logger.info(f"[Provider] Financials updated for {symbol}: {financial_result}")
        except Exception as e:
            logger.error(f"[Provider] Failed to update financials for {symbol}: {e}")

        # 캐시 무효화
        cache.delete(f'stock_quote_{symbol}')
        cache.delete(f'overview_{symbol}')
        cache.delete(f'chart_{symbol}_daily_1d')

        success_count = sum(1 for v in results.values() if v is True)
        return f"[Provider] Success: {success_count}/3 for {symbol}"

    except Exception as e:
        logger.error(f"[Provider] Task failed for {symbol}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def update_realtime_with_provider(symbols=None):
    """
    Provider를 사용한 실시간 가격 업데이트

    Args:
        symbols: 업데이트할 심볼 리스트 (없으면 포트폴리오 종목)

    Returns:
        결과 문자열
    """
    try:
        from api_request.stock_service import get_stock_service

        if not symbols:
            from users.models import Portfolio
            symbols = list(Portfolio.objects.values_list('stock__symbol', flat=True).distinct()[:10])

        if not symbols:
            return "[Provider] No symbols to update"

        service = get_stock_service()

        stats = {'updated': 0, 'cached': 0, 'errors': 0}

        for symbol in symbols:
            try:
                result = service.update_previous_close(symbol, force=False)

                if result['status'] == 'cached':
                    stats['cached'] += 1
                    logger.info(f"[Provider] Cached: {symbol}")
                elif result['status'] == 'updated':
                    stats['updated'] += 1
                    logger.info(f"[Provider] Updated: {symbol} @ ${result.get('price', 0):.2f}")
                    cache.delete(f'stock_quote_{symbol}')
                    if stats['updated'] < len(symbols):
                        time.sleep(12)
                else:
                    stats['errors'] += 1
                    logger.error(f"[Provider] Error: {symbol} - {result.get('message')}")

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"[Provider] Exception for {symbol}: {e}")

        return f"[Provider] Updated: {stats['updated']}, Cached: {stats['cached']}, Errors: {stats['errors']}"

    except Exception as e:
        logger.error(f"[Provider] Task failed: {e}")
        return f"[Provider] Error: {e}"


# ============================================================
# S&P 500 동기화 태스크
# ============================================================

@shared_task(bind=True, max_retries=3)
def sync_sp500_constituents(self):
    """
    S&P 500 구성 종목 동기화 (월 1회)

    FMP API에서 최신 S&P 500 구성 종목을 가져와 DB에 저장.
    없어진 종목은 is_active=False로 변경.
    """
    try:
        from stocks.services.sp500_service import SP500Service

        service = SP500Service()
        result = service.sync_constituents()

        logger.info(f"S&P 500 구성 종목 동기화 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"S&P 500 구성 종목 동기화 실패: {e}")
        raise self.retry(exc=e, countdown=300 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3, soft_time_limit=1800, time_limit=1860)
def sync_sp500_eod_prices(self, target_date=None):
    """
    S&P 500 전종목 EOD 가격 동기화 (매일 장 마감 후)

    Args:
        target_date: 대상 날짜 (YYYY-MM-DD 문자열, 기본: 오늘)
    """
    try:
        from stocks.services.sp500_eod_service import SP500EODService
        from datetime import date as date_type

        target = None
        if target_date:
            target = date_type.fromisoformat(target_date)

        service = SP500EODService()
        result = service.sync_eod_prices(target_date=target)

        logger.info(f"S&P 500 EOD 동기화 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"S&P 500 EOD 동기화 실패: {e}")
        raise self.retry(exc=e, countdown=300 * (self.request.retries + 1))


@shared_task
def update_financials_with_provider(symbol):
    """
    Provider를 사용한 재무제표 업데이트

    Args:
        symbol: 주식 심볼

    Returns:
        결과 문자열
    """
    try:
        from api_request.stock_service import get_stock_service

        service = get_stock_service()
        symbol = symbol.upper().strip()

        logger.info(f"[Provider] Updating financials for {symbol}")

        with transaction.atomic():
            result = service.update_financial_statements(symbol)

        logger.info(f"[Provider] Financials updated for {symbol}: {result}")
        return f"[Provider] Success: {symbol} - {result}"

    except Exception as e:
        logger.error(f"[Provider] Failed for {symbol}: {e}")
        return f"[Provider] Error: {symbol} - {e}"