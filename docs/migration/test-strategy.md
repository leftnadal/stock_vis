# FMP Migration Test Strategy

## 목차
1. [개요](#개요)
2. [테스트 범위 정의](#테스트-범위-정의)
3. [Mock 전략 및 Fixtures](#mock-전략-및-fixtures)
4. [데이터 검증 기준](#데이터-검증-기준)
5. [테스트 시나리오](#테스트-시나리오)
6. [CI/CD 통합](#cicd-통합)
7. [테스트 환경 구성](#테스트-환경-구성)
8. [커버리지 목표](#커버리지-목표)
9. [테스트 실행 가이드](#테스트-실행-가이드)

---

## 개요

### 목적
FMP API 마이그레이션의 안정성과 데이터 일관성을 보장하기 위한 포괄적인 테스트 전략을 수립합니다.

### 배경
- **현재 시스템**: Alpha Vantage API 사용
- **목표 시스템**: Financial Modeling Prep (FMP) API
- **아키텍처**: Provider 추상화 패턴 (architecture-design.md 참조)
- **테스트 프레임워크**: Django TestCase + pytest

### 핵심 원칙
1. **데이터 일관성**: Alpha Vantage와 FMP 간 데이터 동등성 보장
2. **무중단 전환**: Feature Flag 기반 점진적 마이그레이션 검증
3. **자동화 우선**: CI/CD 파이프라인 통합으로 회귀 방지
4. **성능 검증**: Rate Limiting 및 캐싱 동작 확인

---

## 테스트 범위 정의

### 1. Unit Tests (단위 테스트)

#### 1.1 FMP Client Layer
```
tests/unit/providers/fmp/
├── test_fmp_client.py           # HTTP 요청, Rate Limiting
├── test_fmp_processor.py        # 데이터 변환 로직
└── test_fmp_provider.py         # Provider 인터페이스 구현
```

**테스트 대상**:
- FMP API 각 엔드포인트 호출 메서드
- 응답 데이터 파싱 및 변환
- 에러 핸들링 (404, 429, 500 등)
- Rate Limiting 로직

**예시**:
```python
# tests/unit/providers/fmp/test_fmp_client.py

import pytest
from unittest.mock import Mock, patch
from API_request.providers.fmp.client import FMPClient
from API_request.exceptions import ProviderRateLimitError, ProviderAPIError

class TestFMPClient:
    @pytest.fixture
    def client(self):
        return FMPClient(api_key='test_key')

    @patch('requests.get')
    def test_get_quote_success(self, mock_get, client):
        """실시간 주가 조회 성공"""
        # Given
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "symbol": "AAPL",
            "price": 150.25,
            "changesPercentage": 1.69,
            "change": 2.50,
            "dayLow": 148.00,
            "dayHigh": 151.00,
            "yearHigh": 199.62,
            "yearLow": 124.17,
            "marketCap": 2500000000000,
            "priceAvg50": 145.32,
            "priceAvg200": 155.67,
            "volume": 50000000,
            "avgVolume": 55000000,
            "open": 149.50,
            "previousClose": 148.00,
            "eps": 6.11,
            "pe": 24.59,
            "earningsAnnouncement": "2025-01-30T12:00:00.000+0000",
            "sharesOutstanding": 16530000000,
            "timestamp": 1638360000
        }]
        mock_get.return_value = mock_response

        # When
        result = client.get_quote('AAPL')

        # Then
        assert result[0]['symbol'] == 'AAPL'
        assert result[0]['price'] == 150.25
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_rate_limit_error_429(self, mock_get, client):
        """Rate Limit 초과 시 에러 발생"""
        # Given
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "Error Message": "You have reached the 250 requests limit"
        }
        mock_get.return_value = mock_response

        # When/Then
        with pytest.raises(ProviderRateLimitError) as exc_info:
            client.get_quote('AAPL')

        assert "FMP" in str(exc_info.value)

    @patch('requests.get')
    def test_symbol_not_found_404(self, mock_get, client):
        """존재하지 않는 심볼"""
        # Given
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # When/Then
        with pytest.raises(ProviderAPIError):
            client.get_quote('INVALID')

    @patch('requests.get')
    def test_network_timeout(self, mock_get, client):
        """네트워크 타임아웃 처리"""
        # Given
        mock_get.side_effect = requests.exceptions.Timeout()

        # When/Then
        with pytest.raises(ProviderAPIError) as exc_info:
            client.get_quote('AAPL')

        assert "timeout" in str(exc_info.value).lower()
```

#### 1.2 FMP Processor Layer
```python
# tests/unit/providers/fmp/test_fmp_processor.py

import pytest
from datetime import date
from decimal import Decimal
from API_request.providers.fmp.processor import FMPProcessor

class TestFMPProcessor:
    @pytest.fixture
    def processor(self):
        return FMPProcessor()

    def test_process_quote_valid_data(self, processor):
        """실시간 주가 데이터 변환"""
        # Given
        raw_data = [{
            "symbol": "AAPL",
            "price": 150.25,
            "changesPercentage": 1.69,
            "change": 2.50,
            "dayLow": 148.00,
            "dayHigh": 151.00,
            "open": 149.50,
            "previousClose": 148.00,
            "volume": 50000000
        }]

        # When
        result = processor.process_quote(raw_data)

        # Then
        assert result['symbol'] == 'AAPL'
        assert result['real_time_price'] == Decimal('150.25')
        assert result['change_percent'] == "1.69%"
        assert result['open_price'] == Decimal('149.50')
        assert result['volume'] == 50000000

    def test_process_quote_missing_fields(self, processor):
        """필드 누락 시 안전 처리"""
        # Given
        raw_data = [{
            "symbol": "AAPL",
            "price": 150.25
            # 다른 필드 누락
        }]

        # When
        result = processor.process_quote(raw_data)

        # Then
        assert result['symbol'] == 'AAPL'
        assert result['real_time_price'] == Decimal('150.25')
        assert result['change'] == Decimal('0')  # 기본값
        assert result['volume'] == 0  # 기본값

    def test_process_quote_none_values(self, processor):
        """None 값 처리"""
        # Given
        raw_data = [{
            "symbol": "AAPL",
            "price": None,
            "change": None
        }]

        # When
        result = processor.process_quote(raw_data)

        # Then
        assert result['real_time_price'] == Decimal('0')
        assert result['change'] == Decimal('0')

    def test_process_balance_sheet(self, processor):
        """대차대조표 변환"""
        # Given
        raw_data = [{
            "date": "2024-09-30",
            "symbol": "AAPL",
            "period": "Q4",
            "calendarYear": "2024",
            "totalAssets": 364980000000,
            "totalLiabilities": 279414000000,
            "totalStockholdersEquity": 85566000000,
            "cashAndCashEquivalents": 29943000000
        }]

        # When
        result = processor.process_balance_sheet(raw_data)

        # Then
        assert len(result) == 1
        assert result[0]['reported_date'] == date(2024, 9, 30)
        assert result[0]['period_type'] == 'quarterly'
        assert result[0]['fiscal_year'] == 2024
        assert result[0]['fiscal_quarter'] == 'Q4'
        assert result[0]['total_assets'] == Decimal('364980000000')

    def test_process_historical_daily(self, processor):
        """일별 시세 변환"""
        # Given
        raw_data = {
            "symbol": "AAPL",
            "historical": [
                {
                    "date": "2025-12-07",
                    "open": 150.00,
                    "high": 152.00,
                    "low": 149.00,
                    "close": 151.50,
                    "volume": 60000000
                },
                {
                    "date": "2025-12-06",
                    "open": 148.50,
                    "high": 150.50,
                    "low": 148.00,
                    "close": 150.00,
                    "volume": 55000000
                }
            ]
        }

        # When
        result = processor.process_historical_daily(raw_data)

        # Then
        assert len(result) == 2
        assert result[0]['date'] == date(2025, 12, 7)
        assert result[0]['close_price'] == Decimal('151.50')
        assert result[0]['volume'] == 60000000
```

#### 1.3 Provider Factory
```python
# tests/unit/test_provider_factory.py

import pytest
from unittest.mock import patch
from API_request.provider_factory import ProviderFactory
from API_request.providers.alphavantage.provider import AlphaVantageProvider
from API_request.providers.fmp.provider import FMPProvider

class TestProviderFactory:
    def teardown_method(self):
        """각 테스트 후 싱글톤 캐시 초기화"""
        ProviderFactory.clear_cache()

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'alphavantage')
    @patch('django.conf.settings.ALPHA_VANTAGE_API_KEY', 'test_av_key')
    def test_get_default_provider_alphavantage(self):
        """기본 Provider: Alpha Vantage"""
        # When
        provider = ProviderFactory.get_provider()

        # Then
        assert isinstance(provider, AlphaVantageProvider)
        assert provider.get_provider_name() == 'AlphaVantage'

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'fmp')
    @patch('django.conf.settings.FMP_API_KEY', 'test_fmp_key')
    def test_get_default_provider_fmp(self):
        """기본 Provider: FMP"""
        # When
        provider = ProviderFactory.get_provider()

        # Then
        assert isinstance(provider, FMPProvider)
        assert provider.get_provider_name() == 'FMP'

    @patch('django.conf.settings.PROVIDER_OVERRIDES', {'quote': 'fmp'})
    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'alphavantage')
    @patch('django.conf.settings.FMP_API_KEY', 'test_fmp_key')
    @patch('django.conf.settings.ALPHA_VANTAGE_API_KEY', 'test_av_key')
    def test_endpoint_specific_override(self):
        """엔드포인트별 Provider 오버라이드"""
        # When
        default_provider = ProviderFactory.get_provider()
        quote_provider = ProviderFactory.get_provider(endpoint='quote')

        # Then
        assert default_provider.get_provider_name() == 'AlphaVantage'
        assert quote_provider.get_provider_name() == 'FMP'

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'invalid_provider')
    def test_invalid_provider_raises_error(self):
        """잘못된 Provider 이름 시 에러"""
        # When/Then
        with pytest.raises(ValueError) as exc_info:
            ProviderFactory.get_provider()

        assert "Unknown provider" in str(exc_info.value)

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'fmp')
    @patch('django.conf.settings.FMP_API_KEY', None)
    def test_missing_api_key_raises_error(self):
        """API 키 미설정 시 에러"""
        # When/Then
        with pytest.raises(ValueError) as exc_info:
            ProviderFactory.get_provider()

        assert "FMP_API_KEY not configured" in str(exc_info.value)

    @patch('django.conf.settings.ENABLE_PROVIDER_FALLBACK', True)
    @patch('django.conf.settings.FALLBACK_PROVIDER', 'alphavantage')
    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'fmp')
    @patch('django.conf.settings.ALPHA_VANTAGE_API_KEY', 'test_av_key')
    @patch('django.conf.settings.FMP_API_KEY', 'test_fmp_key')
    def test_fallback_provider_configuration(self):
        """Fallback Provider 설정 확인"""
        # When
        fallback = ProviderFactory.get_fallback_provider()

        # Then
        assert fallback.get_provider_name() == 'AlphaVantage'
```

---

### 2. Integration Tests (통합 테스트)

#### 2.1 Provider + Caching
```python
# tests/integration/test_cached_provider.py

import pytest
import time
from django.core.cache import cache
from API_request.providers.fmp.provider import FMPProvider
from API_request.cache.decorators import cached_provider_call

@pytest.mark.django_db
class TestCachedProviderCalls:

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """각 테스트 전 캐시 초기화"""
        cache.clear()
        yield
        cache.clear()

    @pytest.fixture
    def provider(self):
        return FMPProvider(api_key='test_key')

    def test_cache_hit_on_second_call(self, provider, mocker):
        """두 번째 호출 시 캐시 적중"""
        # Given
        mock_client = mocker.patch.object(provider.client, 'get_quote')
        mock_client.return_value = [{"symbol": "AAPL", "price": 150.25}]

        # When
        result1 = provider.get_quote('AAPL')  # 캐시 미스
        result2 = provider.get_quote('AAPL')  # 캐시 히트

        # Then
        assert result1 == result2
        mock_client.assert_called_once()  # API는 한 번만 호출

    def test_cache_timeout_expiration(self, provider, mocker):
        """캐시 타임아웃 만료 확인"""
        # Given
        mock_client = mocker.patch.object(provider.client, 'get_quote')
        mock_client.return_value = [{"symbol": "AAPL", "price": 150.25}]

        # When
        provider.get_quote('AAPL')  # 첫 호출 (캐시 저장, 1초 TTL)
        time.sleep(2)  # 캐시 만료 대기
        provider.get_quote('AAPL')  # 재호출 (캐시 미스)

        # Then
        assert mock_client.call_count == 2  # 두 번 호출됨

    def test_different_symbols_separate_cache(self, provider, mocker):
        """심볼별로 별도 캐시 키 사용"""
        # Given
        mock_client = mocker.patch.object(provider.client, 'get_quote')
        mock_client.side_effect = [
            [{"symbol": "AAPL", "price": 150.25}],
            [{"symbol": "MSFT", "price": 420.50}]
        ]

        # When
        aapl_result = provider.get_quote('AAPL')
        msft_result = provider.get_quote('MSFT')

        # Then
        assert aapl_result['symbol'] == 'AAPL'
        assert msft_result['symbol'] == 'MSFT'
        assert mock_client.call_count == 2
```

#### 2.2 StockService + Provider + Database
```python
# tests/integration/test_stock_service.py

import pytest
from django.test import TestCase, TransactionTestCase
from API_request.stock_service import StockService
from stocks.models import Stock, DailyPrice, BalanceSheet

@pytest.mark.django_db
class TestStockServiceIntegration(TransactionTestCase):

    def setUp(self):
        """각 테스트 전 데이터베이스 초기화"""
        Stock.objects.all().delete()
        self.service = StockService()

    def test_update_stock_data_creates_new_stock(self, mocker):
        """새 종목 생성 플로우 (Provider → DB)"""
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'market_capitalization': 2500000000000
        }
        mock_provider.get_quote.return_value = {
            'real_time_price': 150.25,
            'change': 2.50,
            'change_percent': '1.69%',
            'volume': 50000000
        }

        # When
        stock = self.service.update_stock_data('AAPL')

        # Then
        assert stock.symbol == 'AAPL'
        assert stock.stock_name == 'Apple Inc.'
        assert stock.real_time_price == 150.25
        assert Stock.objects.filter(symbol='AAPL').exists()

    def test_update_historical_prices_saves_daily_data(self, mocker):
        """일별 시세 저장 플로우"""
        # Given
        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')

        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_historical_daily.return_value = [
            {
                'date': date(2025, 12, 7),
                'open_price': 150.00,
                'high_price': 152.00,
                'low_price': 149.00,
                'close_price': 151.50,
                'volume': 60000000
            },
            {
                'date': date(2025, 12, 6),
                'open_price': 148.50,
                'high_price': 150.50,
                'low_price': 148.00,
                'close_price': 150.00,
                'volume': 55000000
            }
        ]

        # When
        results = self.service.update_historical_prices('AAPL', days=2)

        # Then
        assert results['daily'] == 2
        assert DailyPrice.objects.filter(stock=stock).count() == 2

        latest = DailyPrice.objects.filter(stock=stock).order_by('-date').first()
        assert latest.date == date(2025, 12, 7)
        assert latest.close_price == 151.50

    def test_update_financial_statements(self, mocker):
        """재무제표 저장 플로우"""
        # Given
        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')

        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_balance_sheet.return_value = [
            {
                'reported_date': date(2024, 9, 30),
                'period_type': 'quarterly',
                'fiscal_year': 2024,
                'fiscal_quarter': 'Q4',
                'total_assets': 364980000000,
                'total_liabilities': 279414000000,
                'total_equity': 85566000000
            }
        ]
        mock_provider.get_income_statement.return_value = []
        mock_provider.get_cash_flow.return_value = []

        # When
        results = self.service.update_financial_statements('AAPL')

        # Then
        assert results['balance_sheets'] == 1
        assert BalanceSheet.objects.filter(stock=stock).count() == 1

    def test_fallback_provider_on_primary_failure(self, mocker):
        """Primary Provider 실패 시 Fallback 동작"""
        # Given
        mock_primary = mocker.patch.object(self.service, 'provider')
        mock_primary.get_quote.side_effect = Exception("API Error")
        mock_primary.get_provider_name.return_value = "FMP"

        mock_fallback = mocker.MagicMock()
        mock_fallback.get_quote.return_value = {
            'symbol': 'AAPL',
            'real_time_price': 150.25
        }
        mock_fallback.get_provider_name.return_value = "AlphaVantage"

        self.service.fallback_provider = mock_fallback

        # When
        # _call_with_fallback은 private이므로 public 메서드 통해 테스트
        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        # update_stock_data 내부에서 _call_with_fallback 호출

        # Then
        mock_fallback.get_quote.assert_called_once_with('AAPL')
```

---

### 3. E2E Tests (종단 간 테스트)

#### 3.1 주요 사용자 시나리오
```python
# tests/e2e/test_stock_data_flow.py

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from API_request.stock_service import StockService
from users.models import Portfolio
from stocks.models import Stock, DailyPrice

User = get_user_model()

@pytest.mark.django_db
class TestStockDataE2E(TestCase):
    """
    실제 사용자 시나리오 기반 E2E 테스트
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = StockService()

    def test_user_adds_stock_to_portfolio_flow(self, mocker):
        """
        시나리오: 사용자가 포트폴리오에 종목 추가

        1. 종목 검색 → FMP API 호출
        2. 종목 데이터 수집 → Provider 호출
        3. 포트폴리오 저장 → DB 저장
        4. 차트 데이터 조회 → 캐싱 적용
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')

        # Step 1: 종목 검색
        mock_provider.search_stocks.return_value = [
            {
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'exchange': 'NASDAQ',
                'type': 'Stock'
            }
        ]

        # Step 2: 종목 데이터 수집
        mock_provider.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics'
        }
        mock_provider.get_quote.return_value = {
            'real_time_price': 150.25,
            'volume': 50000000
        }

        # When
        search_results = mock_provider.search_stocks('AAPL')
        stock = self.service.update_stock_data('AAPL')
        portfolio = Portfolio.objects.create(
            user=self.user,
            stock=stock,
            quantity=10,
            average_price=145.00
        )

        # Then
        assert search_results[0]['symbol'] == 'AAPL'
        assert stock.symbol == 'AAPL'
        assert portfolio.stock == stock
        assert portfolio.quantity == 10

    def test_chart_data_display_flow(self, mocker):
        """
        시나리오: 차트 데이터 조회

        1. 일별 시세 조회 → Provider 호출
        2. 캐싱 확인 → Redis/Memory Cache
        3. 프론트엔드 응답 → Serializer 변환
        """
        # Given
        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')

        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_historical_daily.return_value = [
            {
                'date': date(2025, 12, 7),
                'close_price': 151.50,
                'volume': 60000000
            }
        ]

        # When
        results = self.service.update_historical_prices('AAPL', days=1)

        # Then
        assert results['daily'] == 1
        daily_prices = DailyPrice.objects.filter(stock=stock)
        assert daily_prices.count() == 1
        assert daily_prices.first().close_price == 151.50

    def test_financial_data_update_flow(self, mocker):
        """
        시나리오: 재무제표 업데이트 (Celery Task)

        1. Celery Beat 스케줄링
        2. Provider 호출 (Balance Sheet, Income, Cash Flow)
        3. DB 저장 (Bulk Create/Update)
        """
        # Given
        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')

        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_balance_sheet.return_value = [
            {
                'reported_date': date(2024, 9, 30),
                'period_type': 'quarterly',
                'fiscal_year': 2024,
                'fiscal_quarter': 'Q4',
                'total_assets': 364980000000
            }
        ]
        mock_provider.get_income_statement.return_value = [
            {
                'reported_date': date(2024, 9, 30),
                'period_type': 'quarterly',
                'total_revenue': 94000000000,
                'net_income': 22000000000
            }
        ]
        mock_provider.get_cash_flow.return_value = [
            {
                'reported_date': date(2024, 9, 30),
                'period_type': 'quarterly',
                'operating_cashflow': 30000000000
            }
        ]

        # When
        results = self.service.update_financial_statements('AAPL')

        # Then
        assert results['balance_sheets'] == 1
        assert results['income_statements'] == 1
        assert results['cash_flows'] == 1
```

---

## Mock 전략 및 Fixtures

### 1. Fixtures 디렉토리 구조

```
tests/
├── fixtures/
│   ├── fmp/                          # FMP 응답 샘플
│   │   ├── quote_AAPL.json          # 실시간 주가
│   │   ├── profile_AAPL.json        # 회사 정보
│   │   ├── historical_daily_AAPL.json
│   │   ├── balance_sheet_AAPL.json
│   │   ├── income_statement_AAPL.json
│   │   ├── cash_flow_AAPL.json
│   │   └── search_apple.json        # 종목 검색
│   │
│   └── alphavantage/                 # Alpha Vantage 응답 (비교용)
│       ├── quote_AAPL.json
│       ├── overview_AAPL.json
│       └── ...
│
├── conftest.py                       # pytest 공통 fixture
└── unit/
    └── providers/
        └── fmp/
            └── test_fmp_client.py
```

### 2. Fixture 샘플

#### 2.1 FMP Quote Response
```json
// tests/fixtures/fmp/quote_AAPL.json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "price": 150.25,
    "changesPercentage": 1.69,
    "change": 2.50,
    "dayLow": 148.00,
    "dayHigh": 151.00,
    "yearHigh": 199.62,
    "yearLow": 124.17,
    "marketCap": 2500000000000,
    "priceAvg50": 145.32,
    "priceAvg200": 155.67,
    "volume": 50000000,
    "avgVolume": 55000000,
    "open": 149.50,
    "previousClose": 148.00,
    "eps": 6.11,
    "pe": 24.59,
    "earningsAnnouncement": "2025-01-30T12:00:00.000+0000",
    "sharesOutstanding": 16530000000,
    "timestamp": 1638360000
  }
]
```

#### 2.2 FMP Balance Sheet Response
```json
// tests/fixtures/fmp/balance_sheet_AAPL.json
[
  {
    "date": "2024-09-30",
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "cik": "0000320193",
    "fillingDate": "2024-11-01",
    "acceptedDate": "2024-11-01 06:01:36",
    "calendarYear": "2024",
    "period": "Q4",
    "cashAndCashEquivalents": 29943000000,
    "shortTermInvestments": 35228000000,
    "cashAndShortTermInvestments": 65171000000,
    "netReceivables": 65148000000,
    "inventory": 7286000000,
    "otherCurrentAssets": 14287000000,
    "totalCurrentAssets": 151892000000,
    "propertyPlantEquipmentNet": 45680000000,
    "goodwill": 0,
    "intangibleAssets": 0,
    "goodwillAndIntangibleAssets": 0,
    "longTermInvestments": 100544000000,
    "taxAssets": 0,
    "otherNonCurrentAssets": 66864000000,
    "totalNonCurrentAssets": 213088000000,
    "otherAssets": 0,
    "totalAssets": 364980000000,
    "accountPayables": 62611000000,
    "shortTermDebt": 9822000000,
    "taxPayables": 0,
    "deferredRevenue": 8249000000,
    "otherCurrentLiabilities": 65893000000,
    "totalCurrentLiabilities": 146575000000,
    "longTermDebt": 97207000000,
    "deferredRevenueNonCurrent": 0,
    "deferredTaxLiabilitiesNonCurrent": 0,
    "otherNonCurrentLiabilities": 35632000000,
    "totalNonCurrentLiabilities": 132839000000,
    "otherLiabilities": 0,
    "capitalLeaseObligations": 0,
    "totalLiabilities": 279414000000,
    "preferredStock": 0,
    "commonStock": 82080000000,
    "retainedEarnings": 19844000000,
    "accumulatedOtherComprehensiveIncomeLoss": -16358000000,
    "othertotalStockholdersEquity": 0,
    "totalStockholdersEquity": 85566000000,
    "totalEquity": 85566000000,
    "totalLiabilitiesAndStockholdersEquity": 364980000000,
    "minorityInterest": 0,
    "totalLiabilitiesAndTotalEquity": 364980000000,
    "totalInvestments": 135772000000,
    "totalDebt": 107029000000,
    "netDebt": 77086000000,
    "link": "https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-24-000123&xbrl_type=v",
    "finalLink": "https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-24-000123&xbrl_type=v"
  }
]
```

### 3. pytest-vcr 설정 (실제 API 응답 녹화)

```python
# tests/conftest.py

import pytest
import vcr
from pathlib import Path

# VCR 설정
@pytest.fixture(scope='module')
def vcr_config():
    return {
        'cassette_library_dir': str(Path(__file__).parent / 'fixtures' / 'vcr_cassettes'),
        'record_mode': 'once',  # 첫 호출만 녹화, 이후 재생
        'match_on': ['uri', 'method'],
        'filter_headers': ['authorization', 'apikey'],  # API 키 제거
    }

@pytest.fixture
def vcr_cassette_dir(request):
    """테스트별 cassette 디렉토리 자동 생성"""
    test_dir = Path(request.fspath).parent
    cassette_dir = test_dir / 'cassettes'
    cassette_dir.mkdir(exist_ok=True)
    return str(cassette_dir)
```

#### VCR 사용 예시
```python
# tests/integration/test_fmp_api_real.py

import pytest
import vcr
from API_request.providers.fmp.client import FMPClient

class TestFMPAPIReal:
    """
    실제 FMP API 호출 테스트 (VCR 녹화)

    주의: 실제 API 키 필요 (환경 변수 설정)
    첫 실행 시 API 호출 후 cassette 저장
    이후 재생만 수행
    """

    @pytest.fixture
    def client(self):
        return FMPClient(api_key=os.getenv('FMP_API_KEY'))

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/fmp_quote_AAPL.yaml')
    def test_get_quote_real_api(self, client):
        """실제 API 호출 (첫 실행만)"""
        # When
        result = client.get_quote('AAPL')

        # Then
        assert result[0]['symbol'] == 'AAPL'
        assert 'price' in result[0]
```

### 4. pytest-mock 활용

```python
# tests/conftest.py (계속)

import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_fmp_client(mocker):
    """FMP Client Mock"""
    mock_client = mocker.MagicMock()

    # 기본 응답 설정
    mock_client.get_quote.return_value = [
        {
            "symbol": "AAPL",
            "price": 150.25,
            "change": 2.50,
            "changesPercentage": 1.69
        }
    ]

    return mock_client

@pytest.fixture
def mock_provider_factory(mocker):
    """Provider Factory Mock"""
    mock_factory = mocker.patch('API_request.provider_factory.ProviderFactory')

    mock_provider = mocker.MagicMock()
    mock_provider.get_provider_name.return_value = 'FMP'
    mock_factory.get_provider.return_value = mock_provider

    return mock_factory

@pytest.fixture
def sample_stock_data():
    """테스트용 Stock 데이터"""
    return {
        'symbol': 'AAPL',
        'stock_name': 'Apple Inc.',
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'market_capitalization': 2500000000000,
        'real_time_price': 150.25
    }
```

---

## 데이터 검증 기준

### 1. 필수 필드 존재 여부

```python
# tests/validators.py

from typing import Dict, Any, List

class DataValidator:
    """Provider 응답 데이터 검증"""

    # 필수 필드 정의
    REQUIRED_FIELDS = {
        'quote': [
            'symbol', 'real_time_price', 'change', 'change_percent',
            'open_price', 'high_price', 'low_price', 'volume', 'previous_close'
        ],
        'company_profile': [
            'symbol', 'stock_name', 'sector', 'industry',
            'exchange', 'currency', 'market_capitalization'
        ],
        'daily_price': [
            'date', 'open_price', 'high_price', 'low_price',
            'close_price', 'volume'
        ],
        'balance_sheet': [
            'reported_date', 'period_type', 'fiscal_year', 'fiscal_quarter',
            'total_assets', 'total_liabilities', 'total_equity'
        ],
        'income_statement': [
            'reported_date', 'period_type', 'fiscal_year', 'fiscal_quarter',
            'total_revenue', 'net_income', 'gross_profit'
        ],
        'cash_flow': [
            'reported_date', 'period_type', 'fiscal_year', 'fiscal_quarter',
            'operating_cashflow', 'capital_expenditure', 'free_cash_flow'
        ]
    }

    @classmethod
    def validate_required_fields(cls, data: Dict[str, Any], data_type: str) -> List[str]:
        """
        필수 필드 누락 검증

        Returns:
            List[str]: 누락된 필드명 리스트
        """
        required = cls.REQUIRED_FIELDS.get(data_type, [])
        missing = [field for field in required if field not in data or data[field] is None]
        return missing

    @classmethod
    def validate_data_types(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """
        데이터 타입 검증

        Returns:
            Dict[str, str]: {필드명: 에러 메시지}
        """
        errors = {}

        # Decimal 필드
        decimal_fields = [
            'real_time_price', 'change', 'open_price', 'high_price', 'low_price',
            'close_price', 'market_capitalization', 'total_assets', 'total_liabilities'
        ]
        for field in decimal_fields:
            if field in data and not isinstance(data[field], (Decimal, int, float)):
                errors[field] = f"Expected Decimal/numeric, got {type(data[field])}"

        # Integer 필드
        integer_fields = ['volume', 'fiscal_year']
        for field in integer_fields:
            if field in data and not isinstance(data[field], int):
                try:
                    int(data[field])
                except (ValueError, TypeError):
                    errors[field] = f"Expected int, got {type(data[field])}"

        # Date 필드
        date_fields = ['date', 'reported_date', 'latest_quarter']
        for field in date_fields:
            if field in data and not isinstance(data[field], date):
                errors[field] = f"Expected date, got {type(data[field])}"

        return errors

    @classmethod
    def validate_value_ranges(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """
        값 범위 검증

        Returns:
            Dict[str, str]: {필드명: 에러 메시지}
        """
        errors = {}

        # 양수 검증
        positive_fields = [
            'real_time_price', 'open_price', 'high_price', 'low_price',
            'volume', 'market_capitalization', 'total_assets'
        ]
        for field in positive_fields:
            if field in data:
                value = data[field]
                if isinstance(value, (Decimal, int, float)) and value < 0:
                    errors[field] = f"Expected positive value, got {value}"

        # 퍼센트 범위 (-100% ~ +100%)
        percent_fields = ['change_percent', 'profit_margin', 'return_on_equity_ttm']
        for field in percent_fields:
            if field in data:
                value = data[field]
                # 문자열 형식 처리 (예: "1.69%")
                if isinstance(value, str):
                    value_str = value.replace('%', '').strip()
                    try:
                        numeric_value = float(value_str)
                        if not -100 <= numeric_value <= 1000:  # 일부 성장률은 100% 초과 가능
                            errors[field] = f"Percentage out of range: {value}"
                    except ValueError:
                        errors[field] = f"Invalid percentage format: {value}"

        return errors
```

### 2. Alpha Vantage vs FMP 데이터 일관성

```python
# tests/integration/test_provider_consistency.py

import pytest
from decimal import Decimal
from API_request.providers.alphavantage.provider import AlphaVantageProvider
from API_request.providers.fmp.provider import FMPProvider
from tests.validators import DataValidator

class TestProviderDataConsistency:
    """
    Alpha Vantage와 FMP 간 데이터 일관성 검증
    """

    TOLERANCE_PERCENT = 0.01  # 허용 오차: 1%

    @pytest.fixture
    def av_provider(self):
        return AlphaVantageProvider(api_key=os.getenv('ALPHA_VANTAGE_API_KEY'))

    @pytest.fixture
    def fmp_provider(self):
        return FMPProvider(api_key=os.getenv('FMP_API_KEY'))

    @pytest.mark.integration
    @vcr.use_cassette('tests/fixtures/vcr_cassettes/consistency_quote_AAPL.yaml')
    def test_quote_data_consistency(self, av_provider, fmp_provider):
        """실시간 주가 데이터 일관성"""
        symbol = 'AAPL'

        # When
        av_result = av_provider.get_quote(symbol)
        fmp_result = fmp_provider.get_quote(symbol)

        # Then: 필수 필드 검증
        av_missing = DataValidator.validate_required_fields(av_result, 'quote')
        fmp_missing = DataValidator.validate_required_fields(fmp_result, 'quote')

        assert not av_missing, f"Alpha Vantage missing fields: {av_missing}"
        assert not fmp_missing, f"FMP missing fields: {fmp_missing}"

        # Then: 필드명 일치 검증
        assert set(av_result.keys()) == set(fmp_result.keys()), \
            "Field names must match between providers"

        # Then: 가격 데이터 허용 오차 검증 (1% 이내)
        self._assert_within_tolerance(
            av_result['real_time_price'],
            fmp_result['real_time_price'],
            tolerance=self.TOLERANCE_PERCENT,
            field='real_time_price'
        )

        # Then: 거래량 비교 (실시간 데이터이므로 약간의 차이 허용)
        self._assert_within_tolerance(
            av_result['volume'],
            fmp_result['volume'],
            tolerance=0.05,  # 5% 허용
            field='volume'
        )

    @pytest.mark.integration
    @vcr.use_cassette('tests/fixtures/vcr_cassettes/consistency_balance_sheet_AAPL.yaml')
    def test_balance_sheet_consistency(self, av_provider, fmp_provider):
        """대차대조표 데이터 일관성"""
        symbol = 'AAPL'

        # When
        av_result = av_provider.get_balance_sheet(symbol, period='annual', limit=1)
        fmp_result = fmp_provider.get_balance_sheet(symbol, period='annual', limit=1)

        # Then: 같은 기간 데이터인지 확인
        assert av_result[0]['fiscal_year'] == fmp_result[0]['fiscal_year']
        assert av_result[0]['period_type'] == fmp_result[0]['period_type']

        # Then: 주요 지표 일치 검증 (1% 이내)
        self._assert_within_tolerance(
            av_result[0]['total_assets'],
            fmp_result[0]['total_assets'],
            tolerance=self.TOLERANCE_PERCENT,
            field='total_assets'
        )

        self._assert_within_tolerance(
            av_result[0]['total_liabilities'],
            fmp_result[0]['total_liabilities'],
            tolerance=self.TOLERANCE_PERCENT,
            field='total_liabilities'
        )

    def _assert_within_tolerance(
        self,
        av_value: Decimal,
        fmp_value: Decimal,
        tolerance: float,
        field: str
    ):
        """
        두 값이 허용 오차 내에 있는지 검증

        Args:
            av_value: Alpha Vantage 값
            fmp_value: FMP 값
            tolerance: 허용 오차 (비율, 예: 0.01 = 1%)
            field: 필드명 (에러 메시지용)
        """
        av_decimal = Decimal(str(av_value))
        fmp_decimal = Decimal(str(fmp_value))

        # 절대 차이
        diff = abs(av_decimal - fmp_decimal)

        # 상대 차이 (평균 대비)
        avg = (av_decimal + fmp_decimal) / 2
        if avg == 0:
            # 둘 다 0이면 통과
            return

        relative_diff = diff / avg

        assert relative_diff <= Decimal(str(tolerance)), \
            f"{field}: AV={av_value}, FMP={fmp_value}, " \
            f"diff={relative_diff:.2%} (tolerance={tolerance:.2%})"
```

### 3. 데이터 타입 및 범위 검증

```python
# tests/unit/test_data_validation.py

import pytest
from datetime import date
from decimal import Decimal
from tests.validators import DataValidator

class TestDataValidation:

    def test_validate_required_fields_all_present(self):
        """필수 필드 모두 존재"""
        # Given
        data = {
            'symbol': 'AAPL',
            'real_time_price': Decimal('150.25'),
            'change': Decimal('2.50'),
            'change_percent': '1.69%',
            'open_price': Decimal('149.50'),
            'high_price': Decimal('151.00'),
            'low_price': Decimal('148.00'),
            'volume': 50000000,
            'previous_close': Decimal('148.00')
        }

        # When
        missing = DataValidator.validate_required_fields(data, 'quote')

        # Then
        assert missing == []

    def test_validate_required_fields_missing(self):
        """필수 필드 누락"""
        # Given
        data = {
            'symbol': 'AAPL',
            'real_time_price': Decimal('150.25')
            # 다른 필드 누락
        }

        # When
        missing = DataValidator.validate_required_fields(data, 'quote')

        # Then
        assert 'change' in missing
        assert 'volume' in missing
        assert len(missing) > 0

    def test_validate_data_types_correct(self):
        """데이터 타입 정상"""
        # Given
        data = {
            'real_time_price': Decimal('150.25'),
            'volume': 50000000,
            'date': date(2025, 12, 7),
            'fiscal_year': 2024
        }

        # When
        errors = DataValidator.validate_data_types(data)

        # Then
        assert errors == {}

    def test_validate_data_types_incorrect(self):
        """데이터 타입 오류"""
        # Given
        data = {
            'real_time_price': "not a number",  # 잘못된 타입
            'volume': "50000000",  # 문자열
            'date': "2025-12-07"  # 문자열
        }

        # When
        errors = DataValidator.validate_data_types(data)

        # Then
        assert 'real_time_price' in errors
        # volume은 int로 변환 가능하므로 에러 없음
        assert 'date' in errors

    def test_validate_value_ranges_valid(self):
        """값 범위 정상"""
        # Given
        data = {
            'real_time_price': Decimal('150.25'),
            'volume': 50000000,
            'change_percent': '1.69%',
            'profit_margin': Decimal('0.25')
        }

        # When
        errors = DataValidator.validate_value_ranges(data)

        # Then
        assert errors == {}

    def test_validate_value_ranges_negative_price(self):
        """음수 가격 (비정상)"""
        # Given
        data = {
            'real_time_price': Decimal('-150.25'),
            'volume': -50000000
        }

        # When
        errors = DataValidator.validate_value_ranges(data)

        # Then
        assert 'real_time_price' in errors
        assert 'volume' in errors

    def test_validate_percentage_out_of_range(self):
        """퍼센트 범위 초과"""
        # Given
        data = {
            'change_percent': '10000%'  # 비정상적으로 큰 값
        }

        # When
        errors = DataValidator.validate_value_ranges(data)

        # Then
        assert 'change_percent' in errors
```

---

## 테스트 시나리오

### 1. 정상 케이스 (Happy Path)

```python
# tests/scenarios/test_happy_path.py

import pytest
from API_request.stock_service import StockService
from stocks.models import Stock, DailyPrice, BalanceSheet

@pytest.mark.django_db
class TestHappyPath:
    """
    정상 시나리오: 모든 것이 예상대로 동작
    """

    def setUp(self):
        self.service = StockService()

    def test_complete_stock_data_update(self, mocker):
        """
        종목 전체 데이터 업데이트 시나리오

        1. Company Profile 조회
        2. Real-time Quote 조회
        3. Historical Daily Prices (100일)
        4. Historical Weekly Prices (52주)
        5. Balance Sheet (5년)
        6. Income Statement (5년)
        7. Cash Flow (5년)
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')

        # Mock 응답 설정 (간략화)
        mock_provider.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.',
            'sector': 'Technology'
        }
        mock_provider.get_quote.return_value = {
            'real_time_price': 150.25
        }
        mock_provider.get_historical_daily.return_value = [
            {'date': date(2025, 12, 7), 'close_price': 151.50}
        ] * 100
        mock_provider.get_historical_weekly.return_value = [
            {'date': date(2025, 12, 7), 'close_price': 151.50}
        ] * 52
        mock_provider.get_balance_sheet.return_value = [
            {
                'reported_date': date(2024, 9, 30),
                'period_type': 'annual',
                'fiscal_year': 2024,
                'fiscal_quarter': None,
                'total_assets': 364980000000
            }
        ] * 5
        mock_provider.get_income_statement.return_value = [] * 5
        mock_provider.get_cash_flow.return_value = [] * 5

        # When
        stock = self.service.update_stock_data('AAPL')
        price_results = self.service.update_historical_prices('AAPL', days=100)
        financial_results = self.service.update_financial_statements('AAPL')

        # Then
        assert stock.symbol == 'AAPL'
        assert price_results['daily'] == 100
        assert price_results['weekly'] == 52
        assert financial_results['balance_sheets'] == 5

    def test_cached_data_reuse(self, mocker):
        """
        캐시 재사용 시나리오

        1. 첫 호출: API → DB 저장 → 캐시 저장
        2. 두 번째 호출: 캐시에서 반환 (API 호출 없음)
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_quote.return_value = {
            'symbol': 'AAPL',
            'real_time_price': 150.25
        }

        # When
        result1 = self.service.provider.get_quote('AAPL')  # 캐시 미스
        result2 = self.service.provider.get_quote('AAPL')  # 캐시 히트

        # Then
        assert result1 == result2
        mock_provider.get_quote.assert_called_once()  # API 한 번만 호출
```

### 2. 에러 케이스

```python
# tests/scenarios/test_error_cases.py

import pytest
from API_request.exceptions import (
    ProviderRateLimitError,
    ProviderAPIError,
    ProviderNotFoundError
)
from API_request.stock_service import StockService

@pytest.mark.django_db
class TestErrorCases:
    """
    에러 시나리오: 예외 상황 처리
    """

    def setUp(self):
        self.service = StockService()

    def test_rate_limit_429_error(self, mocker):
        """
        Rate Limit 초과 에러

        시나리오: FMP 무료 티어 250 calls/day 초과
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_quote.side_effect = ProviderRateLimitError(
            provider='FMP',
            message='You have reached the 250 requests limit',
            status_code=429
        )

        # When/Then
        with pytest.raises(ProviderRateLimitError):
            self.service.update_stock_data('AAPL')

    def test_symbol_not_found_404(self, mocker):
        """
        존재하지 않는 심볼

        시나리오: 사용자가 잘못된 심볼 입력
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_company_profile.side_effect = ProviderNotFoundError(
            "Symbol INVALID not found"
        )

        # When/Then
        with pytest.raises(ProviderNotFoundError):
            self.service.update_stock_data('INVALID')

    def test_network_timeout_error(self, mocker):
        """
        네트워크 타임아웃

        시나리오: FMP API 서버 응답 지연
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_quote.side_effect = ProviderAPIError(
            provider='FMP',
            message='Connection timeout',
            status_code=None
        )

        # When/Then
        with pytest.raises(ProviderAPIError):
            self.service.update_stock_data('AAPL')

    def test_invalid_api_response_format(self, mocker):
        """
        API 응답 형식 오류

        시나리오: FMP API가 예상과 다른 형식 반환
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_quote.return_value = {}  # 빈 응답

        # When
        stock = self.service.update_stock_data('AAPL')

        # Then
        # 빈 응답이어도 에러 발생하지 않고 기존 데이터 반환
        # (실제 구현에 따라 다를 수 있음)
        assert stock is not None

    def test_partial_data_available(self, mocker):
        """
        부분 데이터만 사용 가능

        시나리오: Profile은 성공, Quote는 실패
        """
        # Given
        mock_provider = mocker.patch.object(self.service, 'provider')
        mock_provider.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.'
        }
        mock_provider.get_quote.side_effect = Exception("Quote API Error")

        # When
        stock = self.service.update_stock_data('AAPL')

        # Then
        assert stock.symbol == 'AAPL'
        assert stock.stock_name == 'Apple Inc.'
        # real_time_price는 업데이트되지 않음
```

### 3. Fallback 케이스

```python
# tests/scenarios/test_fallback_cases.py

import pytest
from API_request.stock_service import StockService
from API_request.provider_factory import ProviderFactory

@pytest.mark.django_db
class TestFallbackCases:
    """
    Fallback 시나리오: Primary 실패 시 Fallback 동작
    """

    def setUp(self):
        self.service = StockService()

    @patch('django.conf.settings.ENABLE_PROVIDER_FALLBACK', True)
    @patch('django.conf.settings.FALLBACK_PROVIDER', 'alphavantage')
    def test_fallback_on_primary_failure(self, mocker):
        """
        Primary Provider 실패 시 Fallback 실행

        시나리오:
        1. FMP API 호출 실패 (Rate Limit)
        2. Alpha Vantage로 Fallback
        3. 데이터 정상 반환
        """
        # Given
        mock_primary = mocker.patch.object(self.service, 'provider')
        mock_primary.get_quote.side_effect = ProviderRateLimitError(
            provider='FMP',
            message='Rate limit exceeded'
        )
        mock_primary.get_provider_name.return_value = 'FMP'

        mock_fallback = mocker.MagicMock()
        mock_fallback.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.'
        }
        mock_fallback.get_quote.return_value = {
            'real_time_price': 150.25
        }
        mock_fallback.get_provider_name.return_value = 'AlphaVantage'

        self.service.fallback_provider = mock_fallback

        # When
        stock = self.service.update_stock_data('AAPL')

        # Then
        assert stock.symbol == 'AAPL'
        assert stock.real_time_price == 150.25
        mock_fallback.get_company_profile.assert_called_once()
        mock_fallback.get_quote.assert_called_once()

    @patch('django.conf.settings.ENABLE_PROVIDER_FALLBACK', True)
    def test_fallback_also_fails(self, mocker):
        """
        Primary와 Fallback 모두 실패

        시나리오:
        1. FMP 실패
        2. Alpha Vantage도 실패
        3. 최종 에러 발생
        """
        # Given
        mock_primary = mocker.patch.object(self.service, 'provider')
        mock_primary.get_quote.side_effect = Exception("FMP Error")

        mock_fallback = mocker.MagicMock()
        mock_fallback.get_quote.side_effect = Exception("Alpha Vantage Error")

        self.service.fallback_provider = mock_fallback

        # When/Then
        with pytest.raises(Exception):
            self.service.update_stock_data('AAPL')

    @patch('django.conf.settings.ENABLE_PROVIDER_FALLBACK', False)
    def test_no_fallback_when_disabled(self, mocker):
        """
        Fallback 비활성화 시 즉시 실패
        """
        # Given
        mock_primary = mocker.patch.object(self.service, 'provider')
        mock_primary.get_quote.side_effect = Exception("FMP Error")

        self.service.fallback_provider = None

        # When/Then
        with pytest.raises(Exception):
            self.service.update_stock_data('AAPL')
```

### 4. Feature Flag 전환 시나리오

```python
# tests/scenarios/test_feature_flag_migration.py

import pytest
from unittest.mock import patch
from API_request.provider_factory import ProviderFactory
from API_request.stock_service import StockService

class TestFeatureFlagMigration:
    """
    Feature Flag 기반 점진적 마이그레이션 시나리오
    """

    def teardown_method(self):
        ProviderFactory.clear_cache()

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'alphavantage')
    @patch('django.conf.settings.PROVIDER_OVERRIDES', {'quote': 'fmp'})
    def test_gradual_migration_quote_only(self):
        """
        단계 1: Quote만 FMP로 전환

        시나리오:
        - 기본: Alpha Vantage
        - Quote만: FMP
        """
        # When
        default_provider = ProviderFactory.get_provider()
        quote_provider = ProviderFactory.get_provider(endpoint='quote')

        # Then
        assert default_provider.get_provider_name() == 'AlphaVantage'
        assert quote_provider.get_provider_name() == 'FMP'

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'alphavantage')
    @patch('django.conf.settings.PROVIDER_OVERRIDES', {
        'quote': 'fmp',
        'company_profile': 'fmp',
        'balance_sheet': 'fmp'
    })
    def test_gradual_migration_multiple_endpoints(self):
        """
        단계 2: Quote, Profile, Balance Sheet FMP 전환
        """
        # When
        providers = {
            'default': ProviderFactory.get_provider(),
            'quote': ProviderFactory.get_provider(endpoint='quote'),
            'profile': ProviderFactory.get_provider(endpoint='company_profile'),
            'balance': ProviderFactory.get_provider(endpoint='balance_sheet'),
            'daily': ProviderFactory.get_provider(endpoint='historical_daily')
        }

        # Then
        assert providers['default'].get_provider_name() == 'AlphaVantage'
        assert providers['quote'].get_provider_name() == 'FMP'
        assert providers['profile'].get_provider_name() == 'FMP'
        assert providers['balance'].get_provider_name() == 'FMP'
        assert providers['daily'].get_provider_name() == 'AlphaVantage'

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'fmp')
    def test_complete_migration_to_fmp(self):
        """
        단계 3: 완전 전환 (모든 엔드포인트 FMP)
        """
        # When
        endpoints = [
            None, 'quote', 'company_profile', 'historical_daily',
            'balance_sheet', 'income_statement', 'cash_flow'
        ]
        providers = [ProviderFactory.get_provider(endpoint=ep) for ep in endpoints]

        # Then
        for provider in providers:
            assert provider.get_provider_name() == 'FMP'
```

---

## CI/CD 통합

### 1. GitHub Actions Workflow

```yaml
# .github/workflows/test-fmp-migration.yml

name: FMP Migration Tests

on:
  push:
    branches: [main, develop, feature/fmp-migration]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ['3.12']

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: stock_vis_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache Poetry dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cache/pypoetry
            .venv
          key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
          restore-keys: |
            ${{ runner.os }}-poetry-

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: |
          poetry install --with dev

      - name: Set up environment variables
        env:
          ALPHA_VANTAGE_API_KEY: ${{ secrets.ALPHA_VANTAGE_API_KEY }}
          FMP_API_KEY: ${{ secrets.FMP_API_KEY }}
        run: |
          echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/stock_vis_test" >> $GITHUB_ENV
          echo "REDIS_URL=redis://localhost:6379/0" >> $GITHUB_ENV
          echo "STOCK_DATA_PROVIDER=fmp" >> $GITHUB_ENV
          echo "ENABLE_PROVIDER_FALLBACK=true" >> $GITHUB_ENV
          echo "FALLBACK_PROVIDER=alphavantage" >> $GITHUB_ENV

      - name: Run database migrations
        run: |
          poetry run python manage.py migrate --noinput

      - name: Run linting (flake8)
        run: |
          poetry run flake8 API_request/ stocks/ users/ tests/

      - name: Run type checking (mypy)
        run: |
          poetry run mypy API_request/ stocks/ users/
        continue-on-error: true  # 타입 체크 실패 시 경고만

      - name: Run unit tests
        run: |
          poetry run pytest tests/unit/ \
            --cov=API_request \
            --cov=stocks \
            --cov=users \
            --cov-report=xml \
            --cov-report=html \
            --junitxml=test-results/junit-unit.xml \
            -v

      - name: Run integration tests
        run: |
          poetry run pytest tests/integration/ \
            --cov-append \
            --cov=API_request \
            --cov-report=xml \
            --junitxml=test-results/junit-integration.xml \
            -v

      - name: Run E2E tests
        run: |
          poetry run pytest tests/e2e/ \
            --cov-append \
            --cov=API_request \
            --cov-report=xml \
            --junitxml=test-results/junit-e2e.xml \
            -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

      - name: Generate coverage report
        run: |
          poetry run coverage report --fail-under=80
          poetry run coverage html

      - name: Upload coverage HTML
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: test-results/

  provider-consistency-test:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          poetry install

      - name: Run Provider Consistency Tests
        env:
          ALPHA_VANTAGE_API_KEY: ${{ secrets.ALPHA_VANTAGE_API_KEY }}
          FMP_API_KEY: ${{ secrets.FMP_API_KEY }}
        run: |
          poetry run pytest tests/integration/test_provider_consistency.py \
            -v \
            --tb=short

      - name: Upload consistency report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: consistency-report
          path: test-results/consistency-report.html
```

### 2. Pre-commit Hooks

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: poetry run pytest tests/unit/
        language: system
        pass_filenames: false
        always_run: true
```

### 3. Coverage 설정

```ini
# .coveragerc

[run]
source = API_request,stocks,users
omit =
    */migrations/*
    */tests/*
    */venv/*
    */__pycache__/*

[report]
precision = 2
show_missing = True
skip_covered = False

exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    pass

[html]
directory = htmlcov
```

---

## 테스트 환경 구성

### 1. pytest 설정

```ini
# pytest.ini

[pytest]
DJANGO_SETTINGS_MODULE = config.settings_test
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*

# 마커 정의
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (database, cache)
    e2e: End-to-end tests (full system)
    slow: Slow tests (API calls, long processing)
    provider_consistency: Provider data consistency tests

# 옵션
addopts =
    --verbose
    --strict-markers
    --tb=short
    --maxfail=5
    --reuse-db
    --nomigrations

# Coverage
testpaths = tests

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### 2. 테스트 전용 Django 설정

```python
# config/settings_test.py

from .settings import *

# 테스트 데이터베이스
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stock_vis_test',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# 빠른 테스트를 위한 비밀번호 해싱
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 캐시 (메모리 사용)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Celery (테스트 시 동기 실행)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 로깅 (콘솔 출력만)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Provider 설정 (환경 변수에서 오버라이드 가능)
STOCK_DATA_PROVIDER = os.getenv('STOCK_DATA_PROVIDER', 'fmp')
ENABLE_PROVIDER_FALLBACK = os.getenv('ENABLE_PROVIDER_FALLBACK', 'true').lower() == 'true'
FALLBACK_PROVIDER = os.getenv('FALLBACK_PROVIDER', 'alphavantage')

# 테스트 API 키 (실제 키는 환경 변수 사용)
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'test_av_key')
FMP_API_KEY = os.getenv('FMP_API_KEY', 'test_fmp_key')
```

### 3. conftest.py (pytest fixtures)

```python
# tests/conftest.py

import pytest
import os
import json
from pathlib import Path
from django.contrib.auth import get_user_model
from stocks.models import Stock, DailyPrice
from API_request.provider_factory import ProviderFactory

User = get_user_model()

# ===== Fixture: 테스트 데이터 로딩 =====

@pytest.fixture
def load_fixture():
    """JSON fixture 로딩 헬퍼"""
    def _load(filename):
        fixture_path = Path(__file__).parent / 'fixtures' / filename
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
    return Stock.objects.create(
        symbol='AAPL',
        stock_name='Apple Inc.',
        sector='Technology',
        industry='Consumer Electronics',
        exchange='NASDAQ',
        currency='USD',
        market_capitalization=2500000000000,
        real_time_price=150.25
    )

@pytest.fixture
@pytest.mark.django_db
def stock_with_prices(stock):
    """가격 데이터 포함 Stock"""
    from datetime import date, timedelta

    # 100일치 일별 가격 생성
    base_date = date(2025, 12, 7)
    for i in range(100):
        DailyPrice.objects.create(
            stock=stock,
            date=base_date - timedelta(days=i),
            open_price=150.00 + i * 0.1,
            high_price=152.00 + i * 0.1,
            low_price=148.00 + i * 0.1,
            close_price=151.00 + i * 0.1,
            volume=50000000 + i * 100000
        )

    return stock

# ===== Fixture: Provider Mocks =====

@pytest.fixture
def mock_fmp_client(mocker):
    """FMP Client Mock"""
    mock_client = mocker.MagicMock()

    # 기본 응답 설정
    mock_client.get_quote.return_value = [{
        "symbol": "AAPL",
        "price": 150.25,
        "change": 2.50,
        "changesPercentage": 1.69,
        "open": 149.50,
        "previousClose": 148.00,
        "volume": 50000000
    }]

    return mock_client

@pytest.fixture
def mock_provider(mocker):
    """Provider Mock (Factory 패턴)"""
    mock_provider = mocker.MagicMock()
    mock_provider.get_provider_name.return_value = 'FMP'

    # Factory Mock
    mocker.patch(
        'API_request.provider_factory.ProviderFactory.get_provider',
        return_value=mock_provider
    )

    return mock_provider

# ===== Fixture: Database Cleanup =====

@pytest.fixture(autouse=True)
@pytest.mark.django_db
def clear_database_cache():
    """각 테스트 후 캐시 및 데이터베이스 초기화"""
    yield

    # 캐시 초기화
    from django.core.cache import cache
    cache.clear()

    # Provider Factory 싱글톤 초기화
    ProviderFactory.clear_cache()

# ===== Fixture: Environment Variables =====

@pytest.fixture
def env_alphavantage(monkeypatch):
    """Alpha Vantage Provider 환경 변수"""
    monkeypatch.setenv('STOCK_DATA_PROVIDER', 'alphavantage')
    monkeypatch.setenv('ALPHA_VANTAGE_API_KEY', 'test_av_key')
    yield
    ProviderFactory.clear_cache()

@pytest.fixture
def env_fmp(monkeypatch):
    """FMP Provider 환경 변수"""
    monkeypatch.setenv('STOCK_DATA_PROVIDER', 'fmp')
    monkeypatch.setenv('FMP_API_KEY', 'test_fmp_key')
    yield
    ProviderFactory.clear_cache()

@pytest.fixture
def env_fallback_enabled(monkeypatch):
    """Fallback 활성화 환경 변수"""
    monkeypatch.setenv('ENABLE_PROVIDER_FALLBACK', 'true')
    monkeypatch.setenv('FALLBACK_PROVIDER', 'alphavantage')
    yield
```

---

## 커버리지 목표

### 1. 전체 커버리지 목표

| 계층 | 목표 커버리지 | 우선순위 | 비고 |
|-----|--------------|---------|------|
| **Provider 계층** | | | |
| `providers/base.py` | 100% | 높음 | 추상 인터페이스 |
| `providers/fmp/client.py` | 90% | 높음 | HTTP 요청 |
| `providers/fmp/processor.py` | 95% | 높음 | 데이터 변환 |
| `providers/fmp/provider.py` | 90% | 높음 | Provider 구현 |
| `providers/alphavantage/*` | 85% | 중간 | 레거시 코드 |
| **Factory & Service** | | | |
| `provider_factory.py` | 100% | 높음 | Feature Flag 로직 |
| `stock_service.py` | 85% | 높음 | 비즈니스 로직 |
| **Cache & Utils** | | | |
| `cache/base.py` | 100% | 중간 | 캐시 인터페이스 |
| `cache/redis_cache.py` | 80% | 중간 | Redis 구현 |
| `cache/decorators.py` | 85% | 중간 | 캐싱 데코레이터 |
| **Exception Handling** | | | |
| `exceptions.py` | 100% | 높음 | 예외 클래스 |
| **전체** | **80%+** | | |

### 2. 커버리지 측정 방법

```bash
# 전체 커버리지 측정
poetry run pytest --cov=API_request --cov=stocks --cov=users --cov-report=html

# 특정 모듈만
poetry run pytest --cov=API_request.providers.fmp --cov-report=term-missing

# 커버리지 80% 미만 시 실패
poetry run coverage report --fail-under=80

# HTML 리포트 생성
poetry run coverage html
open htmlcov/index.html
```

### 3. 커버리지 리포트 해석

```bash
# 예시 출력
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
API_request/__init__.py                       0      0   100%
API_request/provider_factory.py              45      2    96%   89-90
API_request/stock_service.py                120     15    88%   45, 67-70, 120-125
API_request/providers/base.py                 35      0   100%
API_request/providers/fmp/client.py           80      8    90%   145-150, 200
API_request/providers/fmp/processor.py        95      5    95%   220-225
API_request/providers/fmp/provider.py         70      7    90%   100, 150-155
-----------------------------------------------------------------------
TOTAL                                        445     37    92%
```

### 4. 커버리지 제외 항목

```python
# 커버리지에서 제외할 코드 패턴

def deprecated_function():
    """오래된 함수 (곧 제거 예정)"""
    pass  # pragma: no cover

def debug_only():
    if settings.DEBUG:  # pragma: no cover
        print("Debug mode")

def main():
    """스크립트 엔트리포인트"""
    if __name__ == '__main__':  # pragma: no cover
        run()
```

---

## 테스트 실행 가이드

### 1. 로컬 환경 테스트

```bash
# ===== 전체 테스트 실행 =====
poetry run pytest

# ===== 마커별 실행 =====
# Unit 테스트만
poetry run pytest -m unit

# Integration 테스트만
poetry run pytest -m integration

# E2E 테스트 제외
poetry run pytest -m "not e2e"

# 느린 테스트 제외
poetry run pytest -m "not slow"

# ===== 특정 파일/디렉토리 =====
# FMP Client 테스트만
poetry run pytest tests/unit/providers/fmp/test_fmp_client.py

# Provider 관련 테스트만
poetry run pytest tests/unit/providers/

# ===== 실패한 테스트만 재실행 =====
poetry run pytest --lf

# 마지막 실패 + 다음 N개
poetry run pytest --lf --ff

# ===== Verbose 모드 =====
poetry run pytest -v  # 상세 출력
poetry run pytest -vv  # 더 상세
poetry run pytest -vvv  # 가장 상세

# ===== 특정 테스트 실행 =====
# 클래스 단위
poetry run pytest tests/unit/test_provider_factory.py::TestProviderFactory

# 메서드 단위
poetry run pytest tests/unit/test_provider_factory.py::TestProviderFactory::test_get_default_provider_fmp

# ===== 병렬 실행 (pytest-xdist 필요) =====
poetry run pytest -n auto  # CPU 코어 수만큼 병렬
poetry run pytest -n 4  # 4개 워커

# ===== 커버리지와 함께 =====
poetry run pytest --cov=API_request --cov-report=html

# ===== 디버깅 =====
poetry run pytest --pdb  # 실패 시 pdb 진입
poetry run pytest --trace  # 즉시 pdb 진입
```

### 2. Docker 환경 테스트

```yaml
# docker-compose.test.yml

version: '3.9'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: stock_vis_test
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.test
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/stock_vis_test
      REDIS_URL: redis://redis:6379/0
      ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY}
      FMP_API_KEY: ${FMP_API_KEY}
    volumes:
      - .:/app
      - ./test-results:/app/test-results
    command: >
      sh -c "
        poetry run python manage.py migrate --noinput &&
        poetry run pytest --cov=API_request --cov-report=xml --junitxml=test-results/junit.xml
      "
```

```bash
# Docker로 테스트 실행
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# 결과 확인
cat test-results/junit.xml
```

### 3. CI/CD 환경 테스트

```bash
# GitHub Actions에서 실행되는 명령어와 동일하게 로컬에서 실행

# 1. 데이터베이스 마이그레이션
poetry run python manage.py migrate --noinput

# 2. Linting
poetry run flake8 API_request/ stocks/ users/ tests/

# 3. 타입 체크
poetry run mypy API_request/ stocks/ users/

# 4. Unit 테스트
poetry run pytest tests/unit/ \
  --cov=API_request \
  --cov-report=xml \
  --junitxml=test-results/junit-unit.xml

# 5. Integration 테스트
poetry run pytest tests/integration/ \
  --cov-append \
  --cov=API_request \
  --cov-report=xml \
  --junitxml=test-results/junit-integration.xml

# 6. E2E 테스트
poetry run pytest tests/e2e/ \
  --cov-append \
  --cov=API_request \
  --cov-report=xml \
  --junitxml=test-results/junit-e2e.xml

# 7. 커버리지 확인 (80% 미만 시 실패)
poetry run coverage report --fail-under=80
```

### 4. 테스트 디버깅 팁

```bash
# ===== 실패 원인 파악 =====
# 전체 트레이스백 출력
poetry run pytest --tb=long

# 짧은 트레이스백
poetry run pytest --tb=short

# 한 줄 요약
poetry run pytest --tb=line

# ===== 로그 출력 =====
# 모든 로그 출력
poetry run pytest -s  # --capture=no

# 실패한 테스트 로그만
poetry run pytest --log-cli-level=INFO

# ===== 특정 경고 무시 =====
poetry run pytest -W ignore::DeprecationWarning

# ===== 테스트 타임아웃 =====
poetry run pytest --timeout=10  # 10초 타임아웃

# ===== 실패 즉시 중단 =====
poetry run pytest -x  # 첫 실패 시 중단
poetry run pytest --maxfail=3  # 3번 실패 시 중단

# ===== HTML 리포트 생성 =====
poetry run pytest --html=test-results/report.html --self-contained-html
```

### 5. 성능 프로파일링

```bash
# 느린 테스트 찾기
poetry run pytest --durations=10  # 가장 느린 10개

# 모든 테스트 실행 시간
poetry run pytest --durations=0

# 프로파일링
poetry run pytest --profile
```

---

## 결론 및 다음 단계

### 핵심 전략 요약

1. **3계층 테스트**: Unit → Integration → E2E
2. **Mock 우선**: VCR + pytest-mock으로 외부 의존성 제거
3. **데이터 일관성**: Alpha Vantage vs FMP 비교 검증
4. **점진적 마이그레이션**: Feature Flag 기반 엔드포인트별 전환
5. **CI/CD 자동화**: GitHub Actions + Coverage 80% 목표

### 다음 단계

#### Phase 1: 테스트 인프라 구축 (1주)
- [ ] `tests/` 디렉토리 구조 생성
- [ ] `conftest.py` fixture 작성
- [ ] FMP API 응답 fixtures 수집 (VCR 사용)
- [ ] pytest 설정 파일 작성 (`pytest.ini`, `.coveragerc`)
- [ ] GitHub Actions 워크플로우 작성

#### Phase 2: Unit 테스트 작성 (1주)
- [ ] FMP Client 테스트 (HTTP 요청, 에러 핸들링)
- [ ] FMP Processor 테스트 (데이터 변환)
- [ ] FMP Provider 테스트 (인터페이스 구현)
- [ ] Provider Factory 테스트 (Feature Flag)
- [ ] DataValidator 테스트 (검증 로직)

#### Phase 3: Integration 테스트 작성 (1주)
- [ ] StockService + Provider + DB 통합
- [ ] 캐싱 동작 테스트
- [ ] Fallback 메커니즘 테스트
- [ ] Provider 일관성 테스트 (Alpha Vantage vs FMP)

#### Phase 4: E2E 테스트 및 CI/CD (1주)
- [ ] 주요 사용자 시나리오 테스트
- [ ] GitHub Actions 워크플로우 통합
- [ ] Coverage 리포트 자동화
- [ ] Pre-commit hooks 설정

### 성공 기준

- ✅ 전체 테스트 커버리지 80% 이상
- ✅ 모든 CI/CD 파이프라인 통과
- ✅ Alpha Vantage vs FMP 데이터 일치 (1% 이내 오차)
- ✅ 1000+ 테스트 케이스 실행 시간 5분 이내
- ✅ 0개의 flaky 테스트

### 리스크 및 대응

| 리스크 | 대응 방안 |
|-------|----------|
| FMP API Rate Limit 초과 | VCR cassette 사용, 실제 API 호출 최소화 |
| 데이터 불일치 | 허용 오차 1% 설정, 이상치 자동 보고 |
| 테스트 실행 시간 증가 | 병렬 실행 (pytest-xdist), 캐시 활용 |
| CI/CD 파이프라인 실패 | 로컬 환경에서 동일 명령어 재현 가능하도록 문서화 |

---

**작성자**: @qa-architect
**날짜**: 2025-12-08
**버전**: 1.0
