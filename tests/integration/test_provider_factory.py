"""
Provider Factory Integration Tests

Provider 선택, Fallback, 캐싱 메커니즘 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal


class TestProviderFactoryBasic:
    """Provider Factory 기본 기능 테스트"""

    def test_factory_returns_provider(self):
        """
        Given: Provider Factory
        When: get_provider() 호출
        Then: StockDataProvider 인스턴스 반환
        """
        from api_request.providers.factory import ProviderFactory, EndpointType
        from api_request.providers.base import StockDataProvider

        provider = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider is not None
        assert isinstance(provider, StockDataProvider)

    def test_factory_caches_instances(self):
        """
        Given: Provider Factory
        When: 같은 타입으로 여러 번 호출
        Then: 동일 인스턴스 반환 (캐싱)
        """
        from api_request.providers.factory import ProviderFactory, EndpointType

        # 캐시 초기화
        ProviderFactory.clear_cache()

        provider1 = ProviderFactory.get_provider(EndpointType.QUOTE)
        provider2 = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider1 is provider2

    def test_factory_clear_cache(self):
        """
        Given: 캐시된 Provider
        When: clear_cache() 호출
        Then: 새 인스턴스 생성
        """
        from api_request.providers.factory import ProviderFactory, EndpointType

        provider1 = ProviderFactory.get_provider(EndpointType.QUOTE)
        ProviderFactory.clear_cache()
        provider2 = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider1 is not provider2


class TestProviderFactoryEnvConfig:
    """환경 변수 기반 Provider 선택 테스트"""

    def test_default_provider_is_alphavantage(self):
        """
        Given: 환경 변수 미설정
        When: Provider 요청
        Then: Alpha Vantage Provider 반환
        """
        from api_request.providers.factory import ProviderFactory, EndpointType

        ProviderFactory.clear_cache()

        provider = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider.PROVIDER_NAME == "alpha_vantage"

    def test_env_selects_fmp_provider(self, monkeypatch):
        """
        Given: STOCK_PROVIDER_QUOTE=fmp 설정
        When: Quote Provider 요청
        Then: FMP Provider 반환
        """
        from api_request.providers.factory import ProviderFactory, EndpointType

        monkeypatch.setenv("STOCK_PROVIDER_QUOTE", "fmp")
        monkeypatch.setenv("FMP_API_KEY", "test_key")
        ProviderFactory.clear_cache()

        provider = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider.PROVIDER_NAME == "fmp"

    def test_different_endpoints_different_providers(self, monkeypatch):
        """
        Given: Quote=alpha_vantage, Balance Sheet=fmp 설정
        When: 각 Provider 요청
        Then: 다른 Provider 반환
        """
        from api_request.providers.factory import ProviderFactory, EndpointType

        monkeypatch.setenv("STOCK_PROVIDER_QUOTE", "alpha_vantage")
        monkeypatch.setenv("STOCK_PROVIDER_BALANCE_SHEET", "fmp")
        monkeypatch.setenv("FMP_API_KEY", "test_key")
        ProviderFactory.clear_cache()

        quote_provider = ProviderFactory.get_provider(EndpointType.QUOTE)
        balance_provider = ProviderFactory.get_provider(EndpointType.BALANCE_SHEET)

        assert quote_provider.PROVIDER_NAME == "alpha_vantage"
        assert balance_provider.PROVIDER_NAME == "fmp"

    def test_force_provider_override(self, monkeypatch):
        """
        Given: 환경 변수 alpha_vantage 설정
        When: force_provider=FMP로 호출
        Then: FMP Provider 반환
        """
        from api_request.providers.factory import ProviderFactory, EndpointType, ProviderType

        monkeypatch.setenv("STOCK_PROVIDER_QUOTE", "alpha_vantage")
        monkeypatch.setenv("FMP_API_KEY", "test_key")
        ProviderFactory.clear_cache()

        provider = ProviderFactory.get_provider(
            EndpointType.QUOTE,
            force_provider=ProviderType.FMP
        )

        assert provider.PROVIDER_NAME == "fmp"


class TestProviderFactoryFallback:
    """Fallback 메커니즘 테스트"""

    def test_get_fallback_providers(self):
        """
        Given: Alpha Vantage Provider
        When: get_fallback_providers() 호출
        Then: FMP Provider 리스트 반환
        """
        from api_request.providers.factory import ProviderFactory, ProviderType

        ProviderFactory.clear_cache()

        fallbacks = ProviderFactory.get_fallback_providers(ProviderType.ALPHA_VANTAGE)

        assert len(fallbacks) == 1
        assert fallbacks[0].PROVIDER_NAME == "fmp"

    @patch('api_request.providers.alphavantage.AlphaVantageProvider.get_quote')
    @patch('api_request.providers.fmp.FMPProvider.get_quote')
    def test_fallback_on_primary_failure(self, mock_fmp_quote, mock_av_quote):
        """
        Given: Primary Provider 실패
        When: call_with_fallback() 호출
        Then: Fallback Provider로 자동 전환
        """
        from api_request.providers.factory import call_with_fallback, EndpointType, ProviderFactory
        from api_request.providers.base import ProviderResponse, NormalizedQuote

        ProviderFactory.clear_cache()

        # Alpha Vantage 실패 Mock
        mock_av_quote.return_value = ProviderResponse.error_response(
            error="Rate limit exceeded",
            provider="alpha_vantage",
            error_code="RATE_LIMIT"
        )

        # FMP 성공 Mock
        mock_fmp_quote.return_value = ProviderResponse.success_response(
            data=NormalizedQuote(
                symbol='AAPL',
                price=Decimal('150.25'),
                volume=50000000,
            ),
            provider='fmp'
        )

        result = call_with_fallback(EndpointType.QUOTE, 'get_quote', 'AAPL')

        assert result.success is True
        assert result.provider == 'fmp'

    @patch('api_request.providers.alphavantage.AlphaVantageProvider.get_quote')
    @patch('api_request.providers.fmp.FMPProvider.get_quote')
    def test_all_providers_fail(self, mock_fmp_quote, mock_av_quote):
        """
        Given: 모든 Provider 실패
        When: call_with_fallback() 호출
        Then: ALL_PROVIDERS_FAILED 에러 반환
        """
        from api_request.providers.factory import call_with_fallback, EndpointType, ProviderFactory
        from api_request.providers.base import ProviderResponse

        ProviderFactory.clear_cache()

        # 모든 Provider 실패 Mock
        mock_av_quote.return_value = ProviderResponse.error_response(
            error="Alpha Vantage error",
            provider="alpha_vantage"
        )
        mock_fmp_quote.return_value = ProviderResponse.error_response(
            error="FMP error",
            provider="fmp"
        )

        result = call_with_fallback(EndpointType.QUOTE, 'get_quote', 'AAPL')

        assert result.success is False
        assert result.error_code == "ALL_PROVIDERS_FAILED"

    @patch('api_request.providers.alphavantage.AlphaVantageProvider.get_quote')
    def test_primary_success_no_fallback(self, mock_av_quote):
        """
        Given: Primary Provider 성공
        When: call_with_fallback() 호출
        Then: Primary 결과 반환, Fallback 호출 안함
        """
        from api_request.providers.factory import call_with_fallback, EndpointType, ProviderFactory
        from api_request.providers.base import ProviderResponse, NormalizedQuote

        ProviderFactory.clear_cache()

        mock_av_quote.return_value = ProviderResponse.success_response(
            data=NormalizedQuote(
                symbol='AAPL',
                price=Decimal('150.25'),
                volume=50000000,
            ),
            provider='alpha_vantage'
        )

        result = call_with_fallback(EndpointType.QUOTE, 'get_quote', 'AAPL')

        assert result.success is True
        assert result.provider == 'alpha_vantage'


class TestConvenienceFunction:
    """get_provider 편의 함수 테스트"""

    def test_get_provider_string_endpoint(self):
        """
        Given: 문자열 endpoint
        When: get_provider() 호출
        Then: 올바른 Provider 반환
        """
        from api_request.providers.factory import get_provider, ProviderFactory

        ProviderFactory.clear_cache()

        provider = get_provider("quote")

        assert provider is not None
        assert provider.PROVIDER_NAME == "alpha_vantage"

    def test_get_provider_unknown_endpoint(self):
        """
        Given: 알 수 없는 endpoint
        When: get_provider() 호출
        Then: 기본값(QUOTE) Provider 반환
        """
        from api_request.providers.factory import get_provider, ProviderFactory

        ProviderFactory.clear_cache()

        provider = get_provider("unknown_endpoint")

        assert provider is not None  # 기본값으로 동작

    def test_get_provider_with_force(self, monkeypatch):
        """
        Given: force_provider 지정
        When: get_provider() 호출
        Then: 강제 지정된 Provider 반환
        """
        from api_request.providers.factory import get_provider, ProviderFactory

        monkeypatch.setenv("FMP_API_KEY", "test_key")
        ProviderFactory.clear_cache()

        provider = get_provider("quote", force_provider="fmp")

        assert provider.PROVIDER_NAME == "fmp"


class TestProviderFactoryAllProviders:
    """get_all_providers 테스트"""

    def test_get_all_providers_empty(self):
        """
        Given: 캐시 초기화
        When: get_all_providers() 호출
        Then: 빈 딕셔너리 반환
        """
        from api_request.providers.factory import ProviderFactory

        ProviderFactory.clear_cache()

        providers = ProviderFactory.get_all_providers()

        assert providers == {}

    def test_get_all_providers_with_cached(self):
        """
        Given: 여러 Provider 사용
        When: get_all_providers() 호출
        Then: 캐시된 Provider 딕셔너리 반환
        """
        from api_request.providers.factory import ProviderFactory, EndpointType, ProviderType

        ProviderFactory.clear_cache()

        ProviderFactory.get_provider(EndpointType.QUOTE)

        providers = ProviderFactory.get_all_providers()

        assert ProviderType.ALPHA_VANTAGE in providers


class TestEndpointTypes:
    """EndpointType 테스트"""

    def test_all_endpoint_types_have_env_keys(self):
        """
        Given: EndpointType 열거형
        When: ENV_KEYS 확인
        Then: 모든 타입에 환경 변수 키 존재
        """
        from api_request.providers.factory import EndpointType, ENV_KEYS

        for endpoint in EndpointType:
            assert endpoint in ENV_KEYS, f"Missing ENV_KEY for {endpoint}"

    def test_all_endpoint_types_have_defaults(self):
        """
        Given: EndpointType 열거형
        When: DEFAULT_PROVIDERS 확인
        Then: 모든 타입에 기본 Provider 존재
        """
        from api_request.providers.factory import EndpointType, DEFAULT_PROVIDERS

        for endpoint in EndpointType:
            assert endpoint in DEFAULT_PROVIDERS, f"Missing default for {endpoint}"


# ===== 마커 설정 =====
pytestmark = pytest.mark.integration
