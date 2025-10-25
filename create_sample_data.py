"""
샘플 주식 데이터 생성 스크립트
"""
import os
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from stocks.models import Stock, DailyPrice

def create_sample_stocks():
    """샘플 주식 데이터 생성"""

    sample_stocks = [
        {
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.',
            'sector': 'Technology',
            'exchange': 'NASDAQ',
            'currency': 'USD',
            'asset_type': 'Common Stock',
            'real_time_price': Decimal('180.00'),
            'market_capitalization': Decimal('2800000000000'),  # 2.8T
            'description': 'Apple Inc. designs, manufactures, and markets consumer electronics and software.',
            'industry': 'Consumer Electronics',
        },
        {
            'symbol': 'GOOGL',
            'stock_name': 'Alphabet Inc.',
            'sector': 'Technology',
            'exchange': 'NASDAQ',
            'currency': 'USD',
            'asset_type': 'Common Stock',
            'real_time_price': Decimal('140.00'),
            'market_capitalization': Decimal('1700000000000'),  # 1.7T
            'description': 'Alphabet Inc. is a holding company that operates through Google and other subsidiaries.',
            'industry': 'Internet Content & Information',
        },
        {
            'symbol': 'MSFT',
            'stock_name': 'Microsoft Corporation',
            'sector': 'Technology',
            'exchange': 'NASDAQ',
            'currency': 'USD',
            'asset_type': 'Common Stock',
            'real_time_price': Decimal('380.00'),
            'market_capitalization': Decimal('2800000000000'),  # 2.8T
            'description': 'Microsoft Corporation develops and supports software, services, devices, and solutions.',
            'industry': 'Software - Infrastructure',
        },
        {
            'symbol': 'TSLA',
            'stock_name': 'Tesla Inc.',
            'sector': 'Automotive',
            'exchange': 'NASDAQ',
            'currency': 'USD',
            'asset_type': 'Common Stock',
            'real_time_price': Decimal('250.00'),
            'market_capitalization': Decimal('800000000000'),  # 800B
            'description': 'Tesla, Inc. designs, develops, manufactures, and sells electric vehicles and energy storage.',
            'industry': 'Auto Manufacturers',
        },
        {
            'symbol': 'NVDA',
            'stock_name': 'NVIDIA Corporation',
            'sector': 'Technology',
            'exchange': 'NASDAQ',
            'currency': 'USD',
            'asset_type': 'Common Stock',
            'real_time_price': Decimal('450.00'),
            'market_capitalization': Decimal('1100000000000'),  # 1.1T
            'description': 'NVIDIA Corporation provides graphics, computing and networking technologies.',
            'industry': 'Semiconductors',
        }
    ]

    created_stocks = []
    for stock_data in sample_stocks:
        stock, created = Stock.objects.update_or_create(
            symbol=stock_data['symbol'],
            defaults=stock_data
        )
        created_stocks.append(stock)
        if created:
            print(f"Created stock: {stock.symbol}")
        else:
            print(f"Updated stock: {stock.symbol}")

    return created_stocks

def create_sample_prices(stocks):
    """각 주식에 대한 샘플 일일 가격 데이터 생성"""

    today = datetime.now().date()

    for stock in stocks:
        base_price = float(stock.real_time_price)

        # 최근 30일간의 가격 데이터 생성
        for i in range(30):
            date = today - timedelta(days=i)

            # 랜덤 변동 (-5% ~ +5%)
            variation = random.uniform(0.95, 1.05)
            close_price = Decimal(str(round(base_price * variation, 2)))

            # 일중 변동
            high_price = close_price * Decimal('1.02')
            low_price = close_price * Decimal('0.98')
            open_price = close_price * Decimal(str(random.uniform(0.99, 1.01)))

            # 거래량 (랜덤)
            volume = random.randint(10000000, 50000000)

            DailyPrice.objects.update_or_create(
                stock=stock,
                date=date,
                defaults={
                    'open_price': open_price,
                    'high_price': high_price,
                    'low_price': low_price,
                    'close_price': close_price,
                    'volume': volume,
                    # adjusted_close는 모델에 없음
                }
            )

        print(f"Created 30 days of price data for {stock.symbol}")

if __name__ == '__main__':
    print("Creating sample stock data...")
    stocks = create_sample_stocks()
    print("\nCreating sample price data...")
    create_sample_prices(stocks)
    print("\nSample data creation completed!")