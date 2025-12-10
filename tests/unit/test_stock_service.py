"""
StockService Unit Tests

Provider 추상화를 활용한 통합 서비스 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
from decimal import Decimal


class TestStockServiceInit:
    """StockService 초기화 테스트"""

    def test_get_stock_service_singleton(self):
        """
        Given: get_stock_service() 호출
        When: 여러 번 호출
        Then: 동일한 인스턴스 반환 (싱글톤)
        """
        from api_request.stock_service import get_stock_service

        service1 = get_stock_service()
        service2 = get_stock_service()

        assert service1 is service2

    def test_stock_service_class_init(self):
        """
        Given: StockService 클래스 직접 생성
        When: 인스턴스화
        Then: 정상 생성
        """
        from api_request.stock_service import StockService

        service = StockService()

        assert service is not None
        assert hasattr(service, '_factory')


class TestStockServiceProviderMethods:
    """StockService Provider 메서드 테스트 (Mock 사용)"""

    @pytest.fixture
    def mock_provider_response(self):
        """Mock ProviderResponse"""
        from api_request.providers.base import ProviderResponse, NormalizedQuote

        quote = NormalizedQuote(
            symbol='AAPL',
            price=Decimal('150.25'),
            open=Decimal('149.50'),
            high=Decimal('151.00'),
            low=Decimal('148.00'),
            volume=50000000,
            change=Decimal('2.50'),
            change_percent=Decimal('1.69'),
        )

        return ProviderResponse.success_response(
            data=quote,
            provider='alpha_vantage'
        )

    @patch('api_request.stock_service.call_with_fallback')
    def test_get_quote_success(self, mock_call, mock_provider_response):
        """
        Given: 정상 Provider 응답
        When: get_quote() 호출
        Then: ProviderResponse 반환
        """
        from api_request.stock_service import StockService

        mock_call.return_value = mock_provider_response
        service = StockService()

        result = service.get_quote('AAPL')

        assert result.success is True
        assert result.data.symbol == 'AAPL'
        assert result.data.price == Decimal('150.25')

    @patch('api_request.stock_service.call_with_fallback')
    def test_get_quote_normalizes_symbol(self, mock_call, mock_provider_response):
        """
        Given: 소문자 심볼 입력
        When: get_quote() 호출
        Then: 대문자로 변환하여 호출
        """
        from api_request.stock_service import StockService
        from api_request.providers.factory import EndpointType

        mock_call.return_value = mock_provider_response
        service = StockService()

        service.get_quote('aapl')

        mock_call.assert_called_once_with(EndpointType.QUOTE, 'get_quote', 'AAPL')

    @patch('api_request.stock_service.call_with_fallback')
    def test_get_company_profile(self, mock_call):
        """
        Given: Company Profile 요청
        When: get_company_profile() 호출
        Then: 정확한 EndpointType으로 호출
        """
        from api_request.stock_service import StockService
        from api_request.providers.factory import EndpointType
        from api_request.providers.base import ProviderResponse, NormalizedCompanyProfile

        profile = NormalizedCompanyProfile(
            symbol='AAPL',
            name='Apple Inc.',
            sector='Technology',
        )
        mock_call.return_value = ProviderResponse.success_response(
            data=profile,
            provider='alpha_vantage'
        )
        service = StockService()

        result = service.get_company_profile('AAPL')

        mock_call.assert_called_once_with(EndpointType.PROFILE, 'get_company_profile', 'AAPL')
        assert result.success is True
        assert result.data.name == 'Apple Inc.'


class TestStockServiceDBMethods:
    """StockService DB 저장 메서드 테스트"""

    @pytest.fixture
    def mock_provider_responses(self):
        """Provider 응답 Mock 세트"""
        from api_request.providers.base import (
            ProviderResponse, NormalizedCompanyProfile, NormalizedQuote, NormalizedPriceData
        )

        profile = NormalizedCompanyProfile(
            symbol='AAPL',
            name='Apple Inc.',
            sector='Technology',
            industry='Consumer Electronics',
            market_cap=Decimal('2500000000000'),
        )

        quote = NormalizedQuote(
            symbol='AAPL',
            price=Decimal('150.25'),
            open=Decimal('149.50'),
            high=Decimal('151.00'),
            low=Decimal('148.00'),
            volume=50000000,
        )

        daily_prices = [
            NormalizedPriceData(
                date=date(2025, 12, 7),
                open=Decimal('149.50'),
                high=Decimal('151.00'),
                low=Decimal('148.00'),
                close=Decimal('150.25'),
                volume=50000000,
            ),
        ]

        return {
            'profile': ProviderResponse.success_response(data=profile, provider='alpha_vantage'),
            'quote': ProviderResponse.success_response(data=quote, provider='alpha_vantage'),
            'daily': ProviderResponse.success_response(data=daily_prices, provider='alpha_vantage'),
        }

    @pytest.mark.django_db
    @patch('api_request.stock_service.call_with_fallback')
    def test_update_stock_data_creates_new(self, mock_call, mock_provider_responses):
        """
        Given: 존재하지 않는 심볼
        When: update_stock_data() 호출
        Then: 새 Stock 레코드 생성
        """
        from api_request.stock_service import StockService
        from stocks.models import Stock

        # Mock 설정
        def side_effect(endpoint, method, *args, **kwargs):
            if method == 'get_company_profile':
                return mock_provider_responses['profile']
            elif method == 'get_quote':
                return mock_provider_responses['quote']
            return mock_provider_responses['profile']

        mock_call.side_effect = side_effect

        service = StockService()
        stock = service.update_stock_data('AAPL')

        assert stock.symbol == 'AAPL'
        assert stock.stock_name == 'Apple Inc.'
        assert Stock.objects.filter(symbol='AAPL').exists()

    @pytest.mark.django_db
    @patch('api_request.stock_service.call_with_fallback')
    def test_update_stock_data_updates_existing(self, mock_call, stock, mock_provider_responses):
        """
        Given: 이미 존재하는 Stock
        When: update_stock_data() 호출
        Then: 기존 레코드 업데이트
        """
        from api_request.stock_service import StockService
        from stocks.models import Stock

        def side_effect(endpoint, method, *args, **kwargs):
            if method == 'get_company_profile':
                return mock_provider_responses['profile']
            elif method == 'get_quote':
                return mock_provider_responses['quote']
            return mock_provider_responses['profile']

        mock_call.side_effect = side_effect

        original_name = stock.stock_name
        service = StockService()

        updated_stock = service.update_stock_data('AAPL')

        assert Stock.objects.count() == 1  # 새로 생성되지 않음
        assert updated_stock.pk == stock.pk

    @pytest.mark.django_db
    @patch('api_request.stock_service.call_with_fallback')
    def test_update_historical_prices_saves_daily(self, mock_call, stock, mock_provider_responses):
        """
        Given: 가격 데이터 Provider 응답
        When: update_historical_prices() 호출
        Then: DailyPrice 레코드 저장
        """
        from api_request.stock_service import StockService
        from stocks.models import DailyPrice

        mock_call.return_value = mock_provider_responses['daily']

        service = StockService()
        result = service.update_historical_prices(stock)

        assert result['daily_prices'] == 1
        assert DailyPrice.objects.filter(stock=stock).exists()


class TestStockServiceUpdatePreviousClose:
    """update_previous_close 메서드 테스트"""

    @pytest.mark.django_db
    @patch('api_request.stock_service.call_with_fallback')
    def test_update_previous_close_creates_stock(self, mock_call):
        """
        Given: 존재하지 않는 심볼
        When: update_previous_close() 호출
        Then: Stock 생성 후 가격 업데이트
        """
        from api_request.stock_service import StockService
        from api_request.providers.base import ProviderResponse, NormalizedPriceData
        from stocks.models import Stock

        prices = [
            NormalizedPriceData(
                date=date(2025, 12, 6),
                close=Decimal('150.25'),
                open=Decimal('149.00'),
                high=Decimal('151.00'),
                low=Decimal('148.00'),
                volume=50000000,
            ),
            NormalizedPriceData(
                date=date(2025, 12, 5),
                close=Decimal('148.00'),
                open=Decimal('147.00'),
                high=Decimal('149.00'),
                low=Decimal('146.00'),
                volume=45000000,
            ),
        ]
        mock_call.return_value = ProviderResponse.success_response(
            data=prices, provider='alpha_vantage'
        )

        service = StockService()
        result = service.update_previous_close('NEWSTOCK')

        assert result['status'] == 'updated'
        assert result['price'] == 150.25
        assert Stock.objects.filter(symbol='NEWSTOCK').exists()

    @pytest.mark.django_db
    @patch('api_request.stock_service.call_with_fallback')
    def test_update_previous_close_cached_today(self, mock_call, stock):
        """
        Given: 오늘 이미 업데이트한 Stock
        When: update_previous_close(force=False) 호출
        Then: 캐시된 응답 반환, API 호출 안함
        """
        from api_request.stock_service import StockService
        from django.utils import timezone

        # Stock에 오늘 API 호출 기록 설정
        stock.last_api_call = timezone.now()
        stock.save()

        service = StockService()
        result = service.update_previous_close('AAPL', force=False)

        assert result['status'] == 'cached'
        mock_call.assert_not_called()

    @pytest.mark.django_db
    @patch('api_request.stock_service.call_with_fallback')
    def test_update_previous_close_force_update(self, mock_call, stock):
        """
        Given: 오늘 이미 업데이트한 Stock
        When: update_previous_close(force=True) 호출
        Then: 강제로 API 호출
        """
        from api_request.stock_service import StockService
        from api_request.providers.base import ProviderResponse, NormalizedPriceData
        from django.utils import timezone

        stock.last_api_call = timezone.now()
        stock.save()

        prices = [
            NormalizedPriceData(
                date=date(2025, 12, 6),
                close=Decimal('155.00'),
                open=Decimal('150.00'),
                high=Decimal('156.00'),
                low=Decimal('149.00'),
                volume=60000000,
            ),
        ]
        mock_call.return_value = ProviderResponse.success_response(
            data=prices, provider='alpha_vantage'
        )

        service = StockService()
        result = service.update_previous_close('AAPL', force=True)

        assert result['status'] == 'updated'
        mock_call.assert_called_once()


class TestStockServiceGetStockSummary:
    """get_stock_summary 메서드 테스트"""

    @pytest.mark.django_db
    def test_get_stock_summary_existing(self, stock_with_prices):
        """
        Given: 가격 데이터가 있는 Stock
        When: get_stock_summary() 호출
        Then: 데이터 카운트 포함 요약 반환
        """
        from api_request.stock_service import StockService

        service = StockService()
        summary = service.get_stock_summary('AAPL')

        assert summary['symbol'] == 'AAPL'
        assert summary['name'] == 'Apple Inc.'
        assert summary['data_counts']['daily_prices'] == 100

    @pytest.mark.django_db
    def test_get_stock_summary_not_found(self):
        """
        Given: 존재하지 않는 심볼
        When: get_stock_summary() 호출
        Then: 에러 반환
        """
        from api_request.stock_service import StockService

        service = StockService()
        summary = service.get_stock_summary('NONEXISTENT')

        assert 'error' in summary


class TestStockServiceProviderInfo:
    """get_provider_info 메서드 테스트"""

    def test_get_provider_info(self):
        """
        Given: StockService 인스턴스
        When: get_provider_info() 호출
        Then: Provider 설정 정보 반환
        """
        from api_request.stock_service import StockService

        service = StockService()
        info = service.get_provider_info()

        assert 'providers' in info
        assert 'fallback_enabled' in info
        assert 'cache_ttl' in info


# ===== 마커 설정 =====
pytestmark = pytest.mark.unit
