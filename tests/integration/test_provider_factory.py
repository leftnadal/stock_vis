"""
Provider Factory Integration Tests

Provider 선택, Fallback, 캐싱 메커니즘 테스트
"""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestProviderFactoryBasic:
    """Provider Factory 기본 기능 테스트"""

    def test_factory_returns_provider(self):
        """
        Given: Provider Factory
        When: get_provider() 호출
        Then: StockDataProvider 인스턴스 반환
        """
        from packages.shared.api_request.providers.base import StockDataProvider
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
        )

        provider = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider is not None
        assert isinstance(provider, StockDataProvider)

    def test_factory_caches_instances(self):
        """
        Given: Provider Factory
        When: 같은 타입으로 여러 번 호출
        Then: 동일 인스턴스 반환 (캐싱)
        """
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
        )

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
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
        )

        provider1 = ProviderFactory.get_provider(EndpointType.QUOTE)
        ProviderFactory.clear_cache()
        provider2 = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider1 is not provider2


class TestProviderFactoryEnvConfig:
    """환경 변수 기반 Provider 선택 테스트"""

    def test_default_provider_is_fmp(self):
        """
        Given: 환경 변수 미설정
        When: Provider 요청
        Then: FMP Provider 반환 (기본 Provider가 FMP로 변경됨)
        """
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
        )

        ProviderFactory.clear_cache()

        provider = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider.PROVIDER_NAME == "fmp"

    def test_env_selects_fmp_provider(self, monkeypatch):
        """
        Given: STOCK_PROVIDER_QUOTE=fmp 설정
        When: Quote Provider 요청
        Then: FMP Provider 반환
        """
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
        )

        monkeypatch.setenv("STOCK_PROVIDER_QUOTE", "fmp")
        monkeypatch.setenv("FMP_API_KEY", "test_key")
        ProviderFactory.clear_cache()

        provider = ProviderFactory.get_provider(EndpointType.QUOTE)

        assert provider.PROVIDER_NAME == "fmp"


class TestProviderFactoryFallback:
    """Fallback 메커니즘 테스트 (현재 FMP 단독, fallback 체인 비어있음)."""

    def test_fmp_has_no_fallbacks(self):
        """
        Given: 현재 provider 구성에서 FMP만 활성
        When: FMP의 fallback 조회
        Then: 빈 리스트 (fallback 체인 없음)
        """
        from packages.shared.api_request.providers.factory import (
            ProviderFactory,
            ProviderType,
        )

        ProviderFactory.clear_cache()
        fallbacks = ProviderFactory.get_fallback_providers(ProviderType.FMP)
        assert fallbacks == []

    @patch('packages.shared.api_request.providers.fmp.FMPProvider.get_quote')
    def test_primary_failure_returns_all_failed(self, mock_fmp_quote):
        """
        Given: FMP 실패 + fallback 없음
        When: call_with_fallback() 호출
        Then: ALL_PROVIDERS_FAILED 에러 반환
        """
        from packages.shared.api_request.providers.base import ProviderResponse
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
            call_with_fallback,
        )

        ProviderFactory.clear_cache()
        mock_fmp_quote.return_value = ProviderResponse.error_response(
            error="FMP error", provider="fmp"
        )

        result = call_with_fallback(EndpointType.QUOTE, 'get_quote', 'AAPL')

        assert result.success is False
        assert result.error_code == "ALL_PROVIDERS_FAILED"

    @patch('packages.shared.api_request.providers.fmp.FMPProvider.get_quote')
    def test_primary_success_no_fallback(self, mock_fmp_quote):
        """
        Given: Primary Provider (FMP) 성공
        When: call_with_fallback() 호출
        Then: Primary 결과 반환, Fallback 호출 안함
        """
        from packages.shared.api_request.providers.base import (
            NormalizedQuote,
            ProviderResponse,
        )
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
            call_with_fallback,
        )

        ProviderFactory.clear_cache()

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


class TestConvenienceFunction:
    """get_provider 편의 함수 테스트"""

    def test_get_provider_string_endpoint(self):
        """
        Given: 문자열 endpoint
        When: get_provider() 호출
        Then: 올바른 Provider 반환 (기본값: FMP)
        """
        from packages.shared.api_request.providers.factory import (
            ProviderFactory,
            get_provider,
        )

        ProviderFactory.clear_cache()

        provider = get_provider("quote")

        assert provider is not None
        assert provider.PROVIDER_NAME == "fmp"

    def test_get_provider_unknown_endpoint(self):
        """
        Given: 알 수 없는 endpoint
        When: get_provider() 호출
        Then: 기본값(QUOTE) Provider 반환
        """
        from packages.shared.api_request.providers.factory import (
            ProviderFactory,
            get_provider,
        )

        ProviderFactory.clear_cache()

        provider = get_provider("unknown_endpoint")

        assert provider is not None  # 기본값으로 동작

    def test_get_provider_with_force(self, monkeypatch):
        """
        Given: force_provider 지정
        When: get_provider() 호출
        Then: 강제 지정된 Provider 반환
        """
        from packages.shared.api_request.providers.factory import (
            ProviderFactory,
            get_provider,
        )

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
        from packages.shared.api_request.providers.factory import ProviderFactory

        ProviderFactory.clear_cache()

        providers = ProviderFactory.get_all_providers()

        assert providers == {}

    def test_get_all_providers_with_cached(self):
        """
        Given: 여러 Provider 사용
        When: get_all_providers() 호출
        Then: 캐시된 Provider 딕셔너리 반환 (기본값: FMP)
        """
        from packages.shared.api_request.providers.factory import (
            EndpointType,
            ProviderFactory,
            ProviderType,
        )

        ProviderFactory.clear_cache()

        ProviderFactory.get_provider(EndpointType.QUOTE)

        providers = ProviderFactory.get_all_providers()

        assert ProviderType.FMP in providers


class TestEndpointTypes:
    """EndpointType 테스트"""

    def test_all_endpoint_types_have_env_keys(self):
        """
        Given: EndpointType 열거형
        When: ENV_KEYS 확인
        Then: 모든 타입에 환경 변수 키 존재
        """
        from packages.shared.api_request.providers.factory import ENV_KEYS, EndpointType

        for endpoint in EndpointType:
            assert endpoint in ENV_KEYS, f"Missing ENV_KEY for {endpoint}"

    def test_all_endpoint_types_have_defaults(self):
        """
        Given: EndpointType 열거형
        When: DEFAULT_PROVIDERS 확인
        Then: 모든 타입에 기본 Provider 존재
        """
        from packages.shared.api_request.providers.factory import (
            DEFAULT_PROVIDERS,
            EndpointType,
        )

        for endpoint in EndpointType:
            assert endpoint in DEFAULT_PROVIDERS, f"Missing default for {endpoint}"


# ===== 마커 설정 =====
pytestmark = pytest.mark.integration
