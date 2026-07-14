"""
pytest 공통 fixtures

모든 테스트에서 사용 가능한 fixture 정의
"""

import json
import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


# ===== Fixture: 환경 변수 =====

# 격리 테스트 env(.env·실키 부재, 예: CI)에서도 FMP provider 인스턴스화가 되도록
# 더미 FMP_API_KEY를 보장한다(FMP-TESTDEBT env-독립화, 지시서⑮).
# - 실키가 있으면(dev/.env) 보존(setdefault/falsy-guard) → 실키 환경 회귀 무손상.
# - 라이브 호출은 각 테스트가 이미 mock(FMPClient·_request_* patch) → 더미로 충분,
#   라이브 FMP 호출 0.
# - "키부재→에러" 계약 테스트(예: test_fmp_weights::test_missing_api_key_raises)는
#   `settings`/`monkeypatch`로 키를 로컬 override(픽스처 setup 이후 테스트 본문이 후행) →
#   본 픽스처와 무충돌, 계약 그대로 검증됨.
_DUMMY_FMP_API_KEY = "test_dummy_fmp_key"


@pytest.fixture(autouse=True)
def _ensure_fmp_api_key(settings, monkeypatch):
    """FMP 키 부재 환경 격리용 더미 키 선주입(load_dotenv override 무관).

    두 읽기 경로 모두 커버: settings.FMP_API_KEY(serverless_client) +
    os.getenv(factory→provider 생성자). falsy(부재·빈문자열)일 때만 주입해 실키 보존.
    os.environ는 monkeypatch로 테스트 종료 시 자동 복원(세션 누수 없음).
    """
    if not getattr(settings, "FMP_API_KEY", None):
        settings.FMP_API_KEY = _DUMMY_FMP_API_KEY
    if not os.environ.get("FMP_API_KEY"):
        monkeypatch.setenv("FMP_API_KEY", _DUMMY_FMP_API_KEY)
    yield


@pytest.fixture
def env_fmp(monkeypatch):
    """FMP Provider 환경 변수"""
    monkeypatch.setenv('STOCK_DATA_PROVIDER', 'fmp')
    monkeypatch.setenv('FMP_API_KEY', 'test_fmp_key')
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
    from packages.shared.stocks.models import Stock

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
    from packages.shared.stocks.models import DailyPrice

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
    """각 테스트 후 캐시 초기화.

    SAFETY GUARD: cache.clear()는 django-redis 백엔드에서 FLUSHDB를 호출한다.
    운영 Redis DB=1에 실행되면 chainsight:seeds 등 모든 운영 캐시가 삭제된다.
    config/settings_test.py가 로드되어 LocMemCache로 격리되었는지 확인한다.
    """
    yield

    from django.conf import settings
    backend = settings.CACHES['default']['BACKEND']
    assert 'locmem' in backend.lower(), (
        f"cache.clear() blocked: non-LocMem backend detected ({backend}). "
        f"Run pytest with DJANGO_SETTINGS_MODULE=config.settings_test."
    )

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
