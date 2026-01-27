#!/usr/bin/env python
"""
Stock Sync Service 테스트 스크립트

Usage:
    python scripts/test_stock_sync.py
"""

import os
import sys
import django

# Django 설정 초기화
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from stocks.services.stock_sync_service import StockSyncService
from stocks.services.rate_limiter import check_rate_limit
from stocks.models import Stock, DailyPrice
from django.utils import timezone


def print_section(title: str):
    """섹션 제목 출력"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def test_rate_limiter():
    """Rate Limiter 테스트"""
    print_section("1. Rate Limiter 테스트")

    can_call, usage = check_rate_limit('fmp')
    print(f"✓ FMP API 호출 가능 여부: {can_call}")
    print(f"  - 분당: {usage['minute']['used']}/{usage['minute']['limit']} (남음: {usage['minute']['remaining']})")
    print(f"  - 일일: {usage['day']['used']}/{usage['day']['limit']} (남음: {usage['day']['remaining']})")


def test_sync_overview():
    """Overview 동기화 테스트"""
    print_section("2. Overview 동기화 테스트")

    sync_service = StockSyncService()
    test_symbol = 'AAPL'

    print(f"\n[테스트 종목: {test_symbol}]")

    # DB 상태 확인
    stock = Stock.objects.filter(symbol=test_symbol).first()
    if stock:
        print(f"✓ DB에 이미 존재: {stock.stock_name} (업데이트: {stock.last_updated})")
    else:
        print(f"✗ DB에 없음 - 동기화 필요")

    # 신선도 확인
    freshness = sync_service.get_freshness(test_symbol, 'overview')
    print(f"✓ 데이터 신선도: {freshness}")

    # 동기화 필요 여부
    should_sync = sync_service.should_sync(test_symbol, 'overview')
    print(f"✓ 동기화 필요: {should_sync}")

    if should_sync:
        print(f"\n[동기화 실행 중...]")
        result = sync_service.sync_overview(test_symbol, force=False)

        if result.success:
            print(f"✓ 동기화 성공!")
            print(f"  - 소스: {result.source}")
            print(f"  - 시간: {result.synced_at}")
            if result.data:
                print(f"  - 데이터: {result.data}")
        else:
            print(f"✗ 동기화 실패: {result.error}")
    else:
        print(f"\n[동기화 건너뜀 - 데이터가 최신입니다]")

    # _meta 정보 확인
    print(f"\n[_meta 정보]")
    meta = sync_service.get_sync_meta(test_symbol, 'overview', 'db')
    for key, value in meta.items():
        print(f"  - {key}: {value}")


def test_sync_prices():
    """Price 동기화 테스트"""
    print_section("3. Price 동기화 테스트")

    sync_service = StockSyncService()
    test_symbol = 'AAPL'

    print(f"\n[테스트 종목: {test_symbol}]")

    # DB 가격 데이터 확인
    price_count = DailyPrice.objects.filter(stock__symbol=test_symbol).count()
    if price_count > 0:
        latest_price = DailyPrice.objects.filter(stock__symbol=test_symbol).order_by('-date').first()
        print(f"✓ DB에 가격 데이터 존재: {price_count}개 (최신: {latest_price.date})")
    else:
        print(f"✗ DB에 가격 데이터 없음 - 동기화 필요")

    # 신선도 확인
    freshness = sync_service.get_freshness(test_symbol, 'price')
    print(f"✓ 데이터 신선도: {freshness}")

    # 동기화 필요 여부
    should_sync = sync_service.should_sync(test_symbol, 'price')
    print(f"✓ 동기화 필요: {should_sync}")

    if should_sync:
        print(f"\n[동기화 실행 중... (최근 30일)]")
        result = sync_service.sync_prices(test_symbol, days=30, force=False)

        if result.success:
            print(f"✓ 동기화 성공!")
            print(f"  - 소스: {result.source}")
            print(f"  - 시간: {result.synced_at}")
            if result.data:
                print(f"  - 저장된 레코드: {result.data.get('records_saved', 0)}개")
        else:
            print(f"✗ 동기화 실패: {result.error}")
    else:
        print(f"\n[동기화 건너뜀 - 데이터가 최신입니다]")


def test_db_query():
    """DB 쿼리 테스트"""
    print_section("4. DB 쿼리 테스트")

    test_symbol = 'AAPL'

    # Stock 조회
    stock = Stock.objects.filter(symbol=test_symbol).first()
    if stock:
        print(f"✓ Stock 조회 성공:")
        print(f"  - 심볼: {stock.symbol}")
        print(f"  - 이름: {stock.stock_name}")
        print(f"  - 현재가: ${stock.real_time_price}")
        print(f"  - 변동: {stock.change_percent}")
        print(f"  - 시가총액: ${stock.market_capitalization:,.0f}" if stock.market_capitalization else "  - 시가총액: N/A")
    else:
        print(f"✗ Stock 조회 실패")

    # DailyPrice 조회 (최근 5일)
    prices = DailyPrice.objects.filter(stock__symbol=test_symbol).order_by('-date')[:5]
    if prices.exists():
        print(f"\n✓ DailyPrice 조회 성공 (최근 5일):")
        for price in prices:
            print(f"  - {price.date}: O=${price.open_price:.2f}, H=${price.high_price:.2f}, "
                  f"L=${price.low_price:.2f}, C=${price.close_price:.2f}, V={price.volume:,}")
    else:
        print(f"\n✗ DailyPrice 조회 실패")


def test_freshness_states():
    """Freshness 상태 테스트"""
    print_section("5. Freshness 상태 테스트")

    sync_service = StockSyncService()
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']

    print("\n데이터 타입별 신선도:")
    for symbol in test_symbols:
        print(f"\n[{symbol}]")
        for data_type in ['overview', 'price']:
            freshness = sync_service.get_freshness(symbol, data_type)
            should_sync = sync_service.should_sync(symbol, data_type)
            print(f"  - {data_type:10s}: {freshness:8s} (동기화 필요: {should_sync})")


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print(" Stock Sync Service 테스트 시작")
    print(" " + str(timezone.now()))
    print("=" * 60)

    try:
        # 1. Rate Limiter 테스트
        test_rate_limiter()

        # 2. Overview 동기화 테스트
        test_sync_overview()

        # 3. Price 동기화 테스트 (선택적)
        user_input = input("\n\nPrice 동기화 테스트를 진행하시겠습니까? (y/N): ")
        if user_input.lower() == 'y':
            test_sync_prices()

        # 4. DB 쿼리 테스트
        test_db_query()

        # 5. Freshness 상태 테스트
        test_freshness_states()

        print_section("테스트 완료")
        print("✓ 모든 테스트가 완료되었습니다.")

    except KeyboardInterrupt:
        print("\n\n[테스트 중단됨]")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
