"""
사용자 관련 유틸리티 함수
"""
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def get_alphavantage_service():
    """AlphaVantage 서비스 인스턴스를 반환합니다."""
    import sys

    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY environment variable not set")

    # API request 경로 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    api_request_path = os.path.join(project_root, 'API request')

    if api_request_path not in sys.path:
        sys.path.insert(0, api_request_path)

    from alphavantage_service import AlphaVantageService
    return AlphaVantageService(api_key)


def ensure_complete_stock_data(symbol: str) -> dict:
    """
    주식 데이터의 완전성을 확인하고, 누락된 데이터만 수집합니다.

    이 함수는 포트폴리오에 주식이 추가될 때 호출되어:
    1. 데이터베이스에서 기존 데이터 확인
    2. 누락된 데이터만 API에서 수집
    3. 결과 반환

    Args:
        symbol: 주식 심볼

    Returns:
        결과 정보가 담긴 딕셔너리
    """
    from stocks.models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement

    symbol = symbol.upper()

    result = {
        'success': False,
        'partial': False,
        'symbol': symbol,
        'summary': {},
        'missing': [],
        'fetched': [],
        'errors': []
    }

    try:
        service = get_alphavantage_service()
    except Exception as e:
        result['errors'].append(f"Failed to initialize service: {str(e)}")
        return result

    # 1. 주식 기본 정보 확인
    try:
        stock = Stock.objects.get(symbol=symbol)
        result['summary']['stock'] = 'exists'
        logger.info(f"Stock {symbol} already exists: {stock.stock_name}")
    except Stock.DoesNotExist:
        result['missing'].append('stock')
        try:
            logger.info(f"Fetching stock overview for {symbol}")
            stock = service.update_stock_data(symbol)
            result['fetched'].append('stock')
            result['summary']['stock'] = 'fetched'
            logger.info(f"Successfully fetched stock overview for {symbol}")
            time.sleep(12)  # Rate limiting
        except Exception as e:
            result['errors'].append(f"Failed to fetch stock: {str(e)}")
            return result

    # 2. 가격 데이터 확인
    daily_count = DailyPrice.objects.filter(stock=stock).count()
    weekly_count = WeeklyPrice.objects.filter(stock=stock).count()

    if daily_count < 30 or weekly_count < 10:
        result['missing'].append('prices')
        try:
            logger.info(f"Fetching price data for {symbol} (daily: {daily_count}, weekly: {weekly_count})")
            price_result = service.update_historical_prices(symbol, days=730)
            result['fetched'].append('prices')
            result['summary']['prices'] = {
                'daily': price_result.get('daily_prices', 0),
                'weekly': price_result.get('weekly_prices', 0)
            }
            logger.info(f"Successfully fetched price data for {symbol}")
            time.sleep(12)  # Rate limiting
        except Exception as e:
            result['errors'].append(f"Failed to fetch prices: {str(e)}")
    else:
        result['summary']['prices'] = {'daily': daily_count, 'weekly': weekly_count}
        logger.info(f"Price data exists for {symbol} (daily: {daily_count}, weekly: {weekly_count})")

    # 3. 재무제표 확인
    bs_count = BalanceSheet.objects.filter(stock=stock).count()
    is_count = IncomeStatement.objects.filter(stock=stock).count()
    cf_count = CashFlowStatement.objects.filter(stock=stock).count()

    if bs_count == 0 or is_count == 0 or cf_count == 0:
        result['missing'].append('financial_statements')
        try:
            logger.info(f"Fetching financial statements for {symbol} (BS: {bs_count}, IS: {is_count}, CF: {cf_count})")
            financial_result = service.update_financial_statements(symbol)
            result['fetched'].append('financial_statements')
            result['summary']['financial'] = {
                'balance_sheets': financial_result.get('balance_sheets', 0),
                'income_statements': financial_result.get('income_statements', 0),
                'cash_flows': financial_result.get('cash_flows', 0)
            }
            logger.info(f"Successfully fetched financial statements for {symbol}")
        except Exception as e:
            result['errors'].append(f"Failed to fetch financial statements: {str(e)}")
    else:
        result['summary']['financial'] = {
            'balance_sheets': bs_count,
            'income_statements': is_count,
            'cash_flows': cf_count
        }
        logger.info(f"Financial data exists for {symbol} (BS: {bs_count}, IS: {is_count}, CF: {cf_count})")

    # 결과 판정
    if not result['errors']:
        result['success'] = True
    elif result['fetched']:
        result['partial'] = True

    return result


def fetch_stock_data_sync(symbol: str) -> dict:
    """
    주식 데이터를 동기적으로 수집하고 저장합니다.

    포트폴리오에 주식이 추가될 때 호출되어:
    1. 기본 주식 정보 (Overview)
    2. 최근 가격 데이터 (일간, 주간)
    3. 재무제표 데이터 (대차대조표, 손익계산서, 현금흐름표)
    를 자동으로 수집하고 저장합니다.

    Args:
        symbol: 주식 심볼

    Returns:
        성공/실패 정보가 담긴 딕셔너리
    """
    results = {
        'success': False,
        'symbol': symbol,
        'data': {},
        'errors': []
    }

    try:
        # API 키 확인
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            error_msg = "ALPHA_VANTAGE_API_KEY environment variable not set"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results

        # AlphaVantage 서비스 초기화
        import sys
        import time

        # 더 안전한 경로 처리
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        api_request_path = os.path.join(project_root, 'API request')

        if api_request_path not in sys.path:
            sys.path.insert(0, api_request_path)

        try:
            from alphavantage_service import AlphaVantageService
        except ImportError as e:
            error_msg = f"Failed to import AlphaVantageService: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results

        service = AlphaVantageService(api_key)

        # 1. 기본 주식 정보 업데이트
        try:
            logger.info(f"Fetching stock overview for {symbol}")
            stock = service.update_stock_data(symbol)
            results['data']['stock'] = {
                'symbol': stock.symbol,
                'name': stock.stock_name,
                'updated': True
            }
            logger.info(f"Successfully updated overview for {symbol}")
        except Exception as e:
            error_msg = f"Failed to update stock data: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        # Rate limiting을 위한 대기
        time.sleep(12)

        # 2. 가격 데이터 업데이트 - 최근 2년 데이터
        try:
            logger.info(f"Fetching historical prices for {symbol}")
            # 일간 데이터: 최근 2년 (730일)
            price_results = service.update_historical_prices(symbol, days=730)
            results['data']['prices'] = price_results
            logger.info(f"Successfully updated price data for {symbol}")
        except Exception as e:
            error_msg = f"Failed to update price data: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        # Rate limiting을 위한 대기
        time.sleep(12)

        # 3. 주간 가격 데이터는 이미 update_historical_prices에서 처리됨
        # (update_historical_prices 메서드가 일간과 주간 데이터를 모두 가져옴)
        # 따라서 별도로 호출할 필요 없음

        # 4. 재무제표 데이터 업데이트
        try:
            logger.info(f"Fetching financial statements for {symbol}")
            financial_results = service.update_financial_statements(symbol)
            results['data']['financial'] = financial_results
            logger.info(f"Successfully updated financial statements for {symbol}")
        except Exception as e:
            error_msg = f"Failed to update financial statements: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        # 전체 프로세스 성공 여부
        if not results['errors']:
            results['success'] = True
            logger.info(f"Successfully fetched all data for {symbol}")
        else:
            logger.warning(f"Partially fetched data for {symbol} with errors: {results['errors']}")

    except Exception as e:
        error_msg = f"Unexpected error during data fetch: {str(e)}"
        logger.error(error_msg)
        results['errors'].append(error_msg)

    return results


def update_portfolio_stock_data(user_id: int) -> dict:
    """
    특정 사용자의 포트폴리오에 있는 모든 주식 데이터를 업데이트합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        업데이트 결과 딕셔너리
    """
    from users.models import Portfolio

    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'stocks': []
    }

    try:
        portfolios = Portfolio.objects.filter(user_id=user_id).select_related('stock')
        results['total'] = portfolios.count()

        for portfolio in portfolios:
            stock_result = fetch_stock_data_sync(portfolio.stock.symbol)

            if stock_result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1

            results['stocks'].append({
                'symbol': portfolio.stock.symbol,
                'success': stock_result['success'],
                'errors': stock_result.get('errors', [])
            })

            # Rate limiting을 위한 대기 (API 제한 고려)
            import time
            time.sleep(12)

    except Exception as e:
        logger.error(f"Failed to update portfolio stocks for user {user_id}: {e}")

    return results


def fetch_stock_data_background(symbol: str) -> None:
    """
    백그라운드에서 주식 데이터를 수집합니다.
    포트폴리오 추가 후 별도 스레드에서 실행됩니다.

    Args:
        symbol: 주식 심볼
    """
    import django
    django.setup()

    from stocks.models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement

    symbol = symbol.upper()
    logger.info(f"[Background] Starting data fetch for {symbol}")

    try:
        service = get_alphavantage_service()
    except Exception as e:
        logger.error(f"[Background] Failed to initialize service for {symbol}: {e}")
        return

    # 1. 주식 기본 정보 확인/업데이트
    try:
        stock = Stock.objects.get(symbol=symbol)
        logger.info(f"[Background] Stock {symbol} exists, updating...")
        service.update_stock_data(symbol)
        time.sleep(12)
    except Stock.DoesNotExist:
        logger.error(f"[Background] Stock {symbol} not found")
        return
    except Exception as e:
        logger.error(f"[Background] Error updating stock info for {symbol}: {e}")

    # 2. 가격 데이터 수집
    try:
        daily_count = DailyPrice.objects.filter(stock=stock).count()
        weekly_count = WeeklyPrice.objects.filter(stock=stock).count()

        if daily_count < 30 or weekly_count < 10:
            logger.info(f"[Background] Fetching price data for {symbol}")
            service.update_historical_prices(symbol, days=730)
            time.sleep(12)
        else:
            logger.info(f"[Background] Price data exists for {symbol}")
    except Exception as e:
        logger.error(f"[Background] Error fetching prices for {symbol}: {e}")

    # 3. 재무제표 수집
    try:
        bs_count = BalanceSheet.objects.filter(stock=stock).count()
        is_count = IncomeStatement.objects.filter(stock=stock).count()
        cf_count = CashFlowStatement.objects.filter(stock=stock).count()

        if bs_count == 0 or is_count == 0 or cf_count == 0:
            logger.info(f"[Background] Fetching financial statements for {symbol}")
            service.update_financial_statements(symbol)
        else:
            logger.info(f"[Background] Financial data exists for {symbol}")
    except Exception as e:
        logger.error(f"[Background] Error fetching financial statements for {symbol}: {e}")

    logger.info(f"[Background] Completed data fetch for {symbol}")


def get_stock_data_status(symbol: str) -> dict:
    """
    주식 데이터 수집 상태를 반환합니다.
    프론트엔드에서 폴링으로 호출합니다.

    Args:
        symbol: 주식 심볼

    Returns:
        데이터 상태 딕셔너리
    """
    from stocks.models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement

    symbol = symbol.upper()

    result = {
        'symbol': symbol,
        'stock_exists': False,
        'has_overview': False,
        'has_prices': False,
        'has_financial': False,
        'is_complete': False,
        'details': {
            'daily_prices': 0,
            'weekly_prices': 0,
            'balance_sheets': 0,
            'income_statements': 0,
            'cash_flows': 0
        }
    }

    try:
        stock = Stock.objects.get(symbol=symbol)
        result['stock_exists'] = True
        result['has_overview'] = bool(stock.stock_name and stock.real_time_price)

        # 가격 데이터 확인
        daily_count = DailyPrice.objects.filter(stock=stock).count()
        weekly_count = WeeklyPrice.objects.filter(stock=stock).count()
        result['details']['daily_prices'] = daily_count
        result['details']['weekly_prices'] = weekly_count
        result['has_prices'] = daily_count >= 30 or weekly_count >= 10

        # 재무제표 확인
        bs_count = BalanceSheet.objects.filter(stock=stock).count()
        is_count = IncomeStatement.objects.filter(stock=stock).count()
        cf_count = CashFlowStatement.objects.filter(stock=stock).count()
        result['details']['balance_sheets'] = bs_count
        result['details']['income_statements'] = is_count
        result['details']['cash_flows'] = cf_count
        result['has_financial'] = bs_count > 0 and is_count > 0

        # 완전성 판단
        result['is_complete'] = (
            result['has_overview'] and
            result['has_prices'] and
            result['has_financial']
        )

    except Stock.DoesNotExist:
        pass

    return result