#!/usr/bin/env python
"""
포트폴리오에 추가된 모든 주식의 데이터를 완벽하게 가져오는 스크립트
- 모든 주식에 대해 일관되게 작동
- 재무제표 데이터를 확실하게 가져옴
"""

import os
import sys
import time

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# api_request 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
api_request_path = os.path.join(current_dir, 'api_request')
if api_request_path not in sys.path:
    sys.path.insert(0, api_request_path)

from alphavantage_service import AlphaVantageService
from stocks.models import Stock, BalanceSheet, IncomeStatement, CashFlowStatement
from users.models import Portfolio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_complete_stock_data(symbol):
    """
    주식 하나에 대한 모든 데이터를 완전히 가져옴
    """
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', 'RD2NHGDU2IJWIVDI')
    service = AlphaVantageService(api_key=api_key)

    print(f"\n{'='*60}")
    print(f"Fetching complete data for {symbol}")
    print(f"{'='*60}")

    results = {
        'symbol': symbol,
        'overview': False,
        'daily_prices': False,
        'weekly_prices': False,
        'balance_sheets': 0,
        'income_statements': 0,
        'cash_flows': 0,
        'errors': []
    }

    try:
        # 1. Overview (기본 정보)
        print(f"1. Fetching overview for {symbol}...")
        try:
            stock = service.update_stock_data(symbol)
            results['overview'] = True
            print(f"   ✅ Overview: {stock.stock_name}")
        except Exception as e:
            print(f"   ❌ Overview failed: {e}")
            results['errors'].append(f"Overview: {e}")

        # Rate limiting
        time.sleep(12)

        # 2. 가격 데이터
        print(f"2. Fetching price data for {symbol}...")
        try:
            price_result = service.update_historical_prices(symbol)
            if price_result:
                results['daily_prices'] = price_result.get('daily_prices', 0)
                results['weekly_prices'] = price_result.get('weekly_prices', 0)
                print(f"   ✅ Daily Prices: {results['daily_prices']} records")
                print(f"   ✅ Weekly Prices: {results['weekly_prices']} records")
            else:
                print(f"   ⚠️ Price data not returned")
        except Exception as e:
            print(f"   ❌ Price data failed: {e}")
            results['errors'].append(f"Prices: {e}")

        # Rate limiting
        time.sleep(12)

        # 3. 재무제표 - 가장 중요한 부분
        print(f"3. Fetching financial statements for {symbol}...")
        try:
            financial_result = service.update_financial_statements(symbol)
            if financial_result:
                results['balance_sheets'] = financial_result.get('balance_sheets', 0)
                results['income_statements'] = financial_result.get('income_statements', 0)
                results['cash_flows'] = financial_result.get('cash_flows', 0)

                print(f"   ✅ Balance Sheets: {results['balance_sheets']} records")
                print(f"   ✅ Income Statements: {results['income_statements']} records")
                print(f"   ✅ Cash Flows: {results['cash_flows']} records")

                # 재무제표가 없으면 경고
                if results['balance_sheets'] == 0:
                    print(f"   ⚠️ WARNING: No balance sheet data!")
                if results['income_statements'] == 0:
                    print(f"   ⚠️ WARNING: No income statement data!")
                if results['cash_flows'] == 0:
                    print(f"   ⚠️ WARNING: No cash flow data!")
            else:
                print(f"   ⚠️ Financial data not returned")
        except Exception as e:
            print(f"   ❌ Financial statements failed: {e}")
            results['errors'].append(f"Financial: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        results['errors'].append(f"Unexpected: {e}")

    # 최종 결과 요약
    print(f"\n📊 Summary for {symbol}:")
    print(f"   Overview: {'✅' if results['overview'] else '❌'}")
    print(f"   Daily Prices: {results['daily_prices']} records")
    print(f"   Weekly Prices: {results['weekly_prices']} records")
    print(f"   Balance Sheets: {results['balance_sheets']} records")
    print(f"   Income Statements: {results['income_statements']} records")
    print(f"   Cash Flows: {results['cash_flows']} records")

    if results['errors']:
        print(f"   ⚠️ Errors: {', '.join(results['errors'])}")

    return results


def update_all_portfolio_stocks():
    """
    모든 포트폴리오 주식의 데이터를 업데이트
    """
    print("\n" + "="*60)
    print("UPDATING ALL PORTFOLIO STOCKS")
    print("="*60)

    # 포트폴리오에 있는 모든 유니크한 주식 심볼
    symbols = Portfolio.objects.values_list('stock__symbol', flat=True).distinct()

    print(f"Found {len(symbols)} unique stocks in portfolios: {', '.join(symbols)}")

    all_results = []

    for symbol in symbols:
        result = fetch_complete_stock_data(symbol)
        all_results.append(result)

        # Rate limiting between stocks
        if symbol != list(symbols)[-1]:  # Not the last one
            print("\n⏳ Waiting 12 seconds for rate limiting...")
            time.sleep(12)

    # 최종 보고서
    print("\n" + "="*60)
    print("FINAL REPORT")
    print("="*60)

    success_count = 0
    partial_count = 0
    failed_count = 0

    for result in all_results:
        if not result['errors']:
            if (result['balance_sheets'] > 0 and
                result['income_statements'] > 0 and
                result['cash_flows'] > 0):
                success_count += 1
                print(f"✅ {result['symbol']}: Complete data")
            else:
                partial_count += 1
                print(f"⚠️ {result['symbol']}: Partial data (missing financial statements)")
        else:
            failed_count += 1
            print(f"❌ {result['symbol']}: Failed - {result['errors']}")

    print(f"\nTotal: {len(all_results)} stocks")
    print(f"  ✅ Complete: {success_count}")
    print(f"  ⚠️ Partial: {partial_count}")
    print(f"  ❌ Failed: {failed_count}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 특정 주식만 업데이트
        symbol = sys.argv[1].upper()
        fetch_complete_stock_data(symbol)
    else:
        # 모든 포트폴리오 주식 업데이트
        update_all_portfolio_stocks()