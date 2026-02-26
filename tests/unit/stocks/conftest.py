"""
EOD Dashboard 테스트 공통 fixtures

stocks/eod_signal_calculator, eod_pipeline, eod_ingest, eod_api 테스트에서 공유.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta
from decimal import Decimal


# ───────────────────────────────────────────────
# DataFrame fixtures
# ───────────────────────────────────────────────

@pytest.fixture
def target_date():
    """테스트 기준 날짜"""
    return date(2026, 2, 25)


@pytest.fixture
def sample_price_df(target_date):
    """
    5개 종목 x 60거래일 샘플 가격 데이터.

    Columns: symbol, date, open, high, low, close, volume,
             sector, industry, market_cap
    """
    symbols = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'SPY']
    dates = pd.date_range(end=target_date, periods=60, freq='B')

    base_prices = {
        'AAPL': 180.0,
        'NVDA': 140.0,
        'MSFT': 400.0,
        'TSLA': 250.0,
        'SPY':  500.0,
    }

    rows = []
    np.random.seed(42)
    for symbol in symbols:
        base = base_prices[symbol]
        prices = base + np.cumsum(np.random.randn(60) * 2)
        for i, d in enumerate(dates):
            close = max(float(prices[i]), 10.0)
            rows.append({
                'symbol':     symbol,
                'date':       d.date(),
                'open':       close * 0.99,
                'high':       close * 1.02,
                'low':        close * 0.97,
                'close':      close,
                'volume':     int(np.random.uniform(5_000_000, 200_000_000)),
                'sector':     'Technology' if symbol != 'SPY' else '',
                'industry':   'Consumer Electronics' if symbol == 'AAPL' else '',
                'market_cap': int(base * 1e9),
            })

    return pd.DataFrame(rows)


@pytest.fixture
def calculator():
    """EODSignalCalculator 인스턴스"""
    from stocks.services.eod_signal_calculator import EODSignalCalculator
    return EODSignalCalculator()


@pytest.fixture
def tagger():
    """EODSignalTagger 인스턴스"""
    from stocks.services.eod_signal_tagger import EODSignalTagger
    return EODSignalTagger()


# ───────────────────────────────────────────────
# DB 모델 fixtures
# ───────────────────────────────────────────────

@pytest.fixture
def stock_aapl(db):
    """AAPL Stock 모델"""
    from stocks.models import Stock
    return Stock.objects.create(
        symbol='AAPL',
        stock_name='Apple Inc.',
        sector='Technology',
        industry='Consumer Electronics',
        exchange='NASDAQ',
        market_capitalization=Decimal('3000000000000'),
    )


@pytest.fixture
def stock_nvda(db):
    """NVDA Stock 모델"""
    from stocks.models import Stock
    return Stock.objects.create(
        symbol='NVDA',
        stock_name='NVIDIA Corporation',
        sector='Technology',
        industry='Semiconductors',
        exchange='NASDAQ',
        market_capitalization=Decimal('2000000000000'),
    )


@pytest.fixture
def stock_spy(db):
    """SPY Stock 모델"""
    from stocks.models import Stock
    return Stock.objects.create(
        symbol='SPY',
        stock_name='SPDR S&P 500 ETF Trust',
        sector='',
        industry='',
        exchange='NYSE',
    )


@pytest.fixture
def sp500_constituents(db, stock_aapl, stock_nvda, stock_spy):
    """활성 S&P500 구성 종목 3개"""
    from stocks.models import SP500Constituent
    constituents = []
    for stock in [stock_aapl, stock_nvda, stock_spy]:
        constituents.append(
            SP500Constituent.objects.create(
                symbol=stock.symbol,
                company_name=stock.stock_name,
                sector=stock.sector or '',
                is_active=True,
            )
        )
    return constituents


@pytest.fixture
def daily_prices_60d(db, stock_aapl, stock_nvda, stock_spy, target_date):
    """
    3개 종목 x 60거래일 DailyPrice 레코드.

    AAPL/NVDA는 꾸준히 상승, SPY는 target_date 기준 일반 흐름.
    """
    from stocks.models import DailyPrice

    stock_map = {
        'AAPL': (stock_aapl, 180.0),
        'NVDA': (stock_nvda, 140.0),
        'SPY':  (stock_spy,  500.0),
    }

    dates = pd.date_range(end=target_date, periods=60, freq='B')
    np.random.seed(42)
    created = []

    for symbol, (stock_obj, base) in stock_map.items():
        prices = base + np.cumsum(np.random.randn(60) * 1.5)
        for i, d in enumerate(dates):
            close = max(float(prices[i]), 10.0)
            created.append(DailyPrice(
                stock=stock_obj,
                date=d.date(),
                open_price=Decimal(str(round(close * 0.99, 4))),
                high_price=Decimal(str(round(close * 1.02, 4))),
                low_price=Decimal(str(round(close * 0.97, 4))),
                close_price=Decimal(str(round(close, 4))),
                volume=int(np.random.uniform(5_000_000, 100_000_000)),
            ))

    DailyPrice.objects.bulk_create(created)
    return created


@pytest.fixture
def pipeline_log_success(db, target_date):
    """status=success PipelineLog"""
    from django.utils import timezone
    from stocks.models import PipelineLog

    return PipelineLog.objects.create(
        date=target_date,
        status='success',
        stages={
            'ingest': {'count': 500, 'degrade_mode': False},
            'calculate': {'duration_s': 12.3},
            'tag': {'count': 450},
            'enrich': {'count': 450},
            'persist': {'upserted': 450},
        },
        ingest_quality={
            'total_received': 500,
            'vs_prev_day_pct': 100.0,
            'sector_null_pct': 1.0,
            'volume_zero_pct': 0.5,
            'degrade_mode': False,
        },
        total_duration_seconds=45.0,
        started_at=timezone.now(),
        completed_at=timezone.now(),
    )


@pytest.fixture
def snapshot(db, target_date):
    """EODDashboardSnapshot"""
    from django.utils import timezone
    from stocks.models import EODDashboardSnapshot

    return EODDashboardSnapshot.objects.create(
        date=target_date,
        json_data={
            'date': str(target_date),
            'stocks': [
                {
                    'stock_id': 'AAPL',
                    'signals': [{'id': 'V1', 'category': 'volume'}],
                    'signal_count': 1,
                    'close': 182.5,
                    'change_pct': 2.1,
                }
            ],
            'summary': {'total_stocks': 1, 'total_signals': 1},
        },
        total_signals=1,
        total_stocks=1,
        signal_distribution={'V1': 1},
        generated_at=timezone.now(),
        pipeline_duration_seconds=45.0,
    )
