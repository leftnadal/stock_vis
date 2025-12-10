"""
pytest 공통 fixtures

모든 테스트에서 사용 가능한 fixture 정의
"""

import pytest
import os
import json
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


# ===== Fixture: 환경 변수 =====

@pytest.fixture
def env_fmp(monkeypatch):
    """FMP Provider 환경 변수"""
    monkeypatch.setenv('STOCK_DATA_PROVIDER', 'fmp')
    monkeypatch.setenv('FMP_API_KEY', 'test_fmp_key')
    yield


@pytest.fixture
def env_alphavantage(monkeypatch):
    """Alpha Vantage Provider 환경 변수"""
    monkeypatch.setenv('STOCK_DATA_PROVIDER', 'alphavantage')
    monkeypatch.setenv('ALPHA_VANTAGE_API_KEY', 'test_av_key')
    yield


@pytest.fixture
def env_fallback_enabled(monkeypatch):
    """Fallback 활성화 환경 변수"""
    monkeypatch.setenv('ENABLE_PROVIDER_FALLBACK', 'true')
    monkeypatch.setenv('FALLBACK_PROVIDER', 'alphavantage')
    yield


# ===== Fixture: 테스트 데이터 로딩 =====

@pytest.fixture
def load_fixture():
    """JSON fixture 로딩 헬퍼"""
    def _load(filename):
        fixture_path = Path(__file__).parent / 'fixtures' / filename
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")
        with open(fixture_path) as f:
            return json.load(f)
    return _load


# ===== Fixture: 사용자 및 인증 =====

@pytest.fixture
@pytest.mark.django_db
def user():
    """테스트 사용자"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
@pytest.mark.django_db
def admin_user():
    """관리자 사용자"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


# ===== Fixture: Stock 모델 =====

@pytest.fixture
@pytest.mark.django_db
def stock():
    """기본 Stock 인스턴스"""
    from stocks.models import Stock

    return Stock.objects.create(
        symbol='AAPL',
        stock_name='Apple Inc.',
        sector='Technology',
        industry='Consumer Electronics',
        exchange='NASDAQ',
        currency='USD',
        market_capitalization=Decimal('2500000000000'),
        real_time_price=Decimal('150.25')
    )


@pytest.fixture
@pytest.mark.django_db
def stock_with_prices(stock):
    """가격 데이터 포함 Stock"""
    from stocks.models import DailyPrice

    # 100일치 일별 가격 생성
    base_date = date(2025, 12, 7)
    for i in range(100):
        DailyPrice.objects.create(
            stock=stock,
            date=base_date - timedelta(days=i),
            open_price=Decimal('150.00') + Decimal(i * 0.1),
            high_price=Decimal('152.00') + Decimal(i * 0.1),
            low_price=Decimal('148.00') + Decimal(i * 0.1),
            close_price=Decimal('151.00') + Decimal(i * 0.1),
            volume=50000000 + i * 100000
        )

    return stock


# ===== Fixture: Sample Data =====

@pytest.fixture
def sample_quote_data():
    """샘플 Quote 데이터 (FMP 형식)"""
    return [{
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 150.25,
        "changesPercentage": 1.69,
        "change": 2.50,
        "dayLow": 148.00,
        "dayHigh": 151.00,
        "open": 149.50,
        "previousClose": 148.00,
        "volume": 50000000,
        "timestamp": 1638360000
    }]


@pytest.fixture
def sample_profile_data():
    """샘플 Company Profile 데이터 (FMP 형식)"""
    return [{
        "symbol": "AAPL",
        "companyName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "exchange": "NASDAQ",
        "currency": "USD",
        "mktCap": 2500000000000,
        "description": "Apple Inc. designs, manufactures, and markets smartphones..."
    }]


@pytest.fixture
def sample_balance_sheet_data():
    """샘플 Balance Sheet 데이터 (FMP 형식)"""
    return [{
        "date": "2024-09-30",
        "symbol": "AAPL",
        "period": "Q4",
        "calendarYear": "2024",
        "totalAssets": 364980000000,
        "totalLiabilities": 279414000000,
        "totalStockholdersEquity": 85566000000,
        "cashAndCashEquivalents": 29943000000
    }]


# ===== Fixture: Database Cleanup =====

@pytest.fixture(autouse=True)
@pytest.mark.django_db
def clear_cache_after_test():
    """각 테스트 후 캐시 초기화"""
    yield

    # 캐시 초기화
    from django.core.cache import cache
    cache.clear()


# ===== Fixture: Provider Factory Reset =====

@pytest.fixture(autouse=True)
def reset_provider_factory():
    """각 테스트 후 Provider Factory 싱글톤 초기화"""
    yield

    # Provider Factory 초기화 (구현 후 활성화)
    # from API_request.provider_factory import ProviderFactory
    # ProviderFactory.clear_cache()
