# api_request/providers/factory.py
"""
Provider Factory

Feature Flag 기반으로 적절한 Provider를 선택하고 반환합니다.
Fallback 메커니즘을 지원하여 주 provider 실패 시 대체 provider 사용.
"""

import os
import logging
from enum import Enum
from typing import Optional, Dict, Type, List
from functools import lru_cache

from .base import StockDataProvider, ProviderResponse, ProviderError

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Provider 타입 열거형"""
    ALPHA_VANTAGE = "alpha_vantage"
    FMP = "fmp"


class EndpointType(Enum):
    """엔드포인트 타입 (Feature Flag 키)"""
    QUOTE = "quote"
    PROFILE = "profile"
    DAILY_PRICES = "daily_prices"
    WEEKLY_PRICES = "weekly_prices"
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    SEARCH = "search"
    SECTOR = "sector"


# 환경 변수 키 정의
ENV_KEYS = {
    EndpointType.QUOTE: "STOCK_PROVIDER_QUOTE",
    EndpointType.PROFILE: "STOCK_PROVIDER_PROFILE",
    EndpointType.DAILY_PRICES: "STOCK_PROVIDER_DAILY_PRICES",
    EndpointType.WEEKLY_PRICES: "STOCK_PROVIDER_WEEKLY_PRICES",
    EndpointType.BALANCE_SHEET: "STOCK_PROVIDER_BALANCE_SHEET",
    EndpointType.INCOME_STATEMENT: "STOCK_PROVIDER_INCOME_STATEMENT",
    EndpointType.CASH_FLOW: "STOCK_PROVIDER_CASH_FLOW",
    EndpointType.SEARCH: "STOCK_PROVIDER_SEARCH",
    EndpointType.SECTOR: "STOCK_PROVIDER_SECTOR",
}


# 기본 Provider 설정 (Phase 2 - Alpha Vantage 유지)
DEFAULT_PROVIDERS: Dict[EndpointType, ProviderType] = {
    EndpointType.QUOTE: ProviderType.ALPHA_VANTAGE,
    EndpointType.PROFILE: ProviderType.ALPHA_VANTAGE,
    EndpointType.DAILY_PRICES: ProviderType.ALPHA_VANTAGE,
    EndpointType.WEEKLY_PRICES: ProviderType.ALPHA_VANTAGE,
    EndpointType.BALANCE_SHEET: ProviderType.ALPHA_VANTAGE,
    EndpointType.INCOME_STATEMENT: ProviderType.ALPHA_VANTAGE,
    EndpointType.CASH_FLOW: ProviderType.ALPHA_VANTAGE,
    EndpointType.SEARCH: ProviderType.ALPHA_VANTAGE,
    EndpointType.SECTOR: ProviderType.ALPHA_VANTAGE,
}


# Fallback 체인 정의
FALLBACK_CHAIN: Dict[ProviderType, List[ProviderType]] = {
    ProviderType.ALPHA_VANTAGE: [ProviderType.FMP],
    ProviderType.FMP: [ProviderType.ALPHA_VANTAGE],
}


class ProviderFactory:
    """
    Provider 팩토리 클래스

    Feature Flag에 따라 적절한 Provider 인스턴스를 생성하고 반환합니다.
    싱글톤 패턴으로 Provider 인스턴스를 캐싱합니다.
    """

    _instances: Dict[ProviderType, StockDataProvider] = {}

    @classmethod
    def get_provider(
        cls,
        endpoint: EndpointType,
        force_provider: Optional[ProviderType] = None
    ) -> StockDataProvider:
        """
        엔드포인트에 맞는 Provider 반환

        Args:
            endpoint: 엔드포인트 타입
            force_provider: 강제로 사용할 provider (테스트용)

        Returns:
            StockDataProvider: 해당 엔드포인트의 Provider 인스턴스
        """
        if force_provider:
            provider_type = force_provider
        else:
            provider_type = cls._get_provider_type_for_endpoint(endpoint)

        return cls._get_or_create_provider(provider_type)

    @classmethod
    def _get_provider_type_for_endpoint(cls, endpoint: EndpointType) -> ProviderType:
        """
        환경 변수 또는 기본값에서 Provider 타입 결정

        Args:
            endpoint: 엔드포인트 타입

        Returns:
            ProviderType: 해당 엔드포인트의 Provider 타입
        """
        env_key = ENV_KEYS.get(endpoint)
        if env_key:
            env_value = os.getenv(env_key, "").lower()
            if env_value == "fmp":
                return ProviderType.FMP
            elif env_value == "alpha_vantage":
                return ProviderType.ALPHA_VANTAGE

        return DEFAULT_PROVIDERS.get(endpoint, ProviderType.ALPHA_VANTAGE)

    @classmethod
    def _get_or_create_provider(cls, provider_type: ProviderType) -> StockDataProvider:
        """
        Provider 인스턴스 가져오기 또는 생성

        Args:
            provider_type: Provider 타입

        Returns:
            StockDataProvider: Provider 인스턴스
        """
        if provider_type not in cls._instances:
            cls._instances[provider_type] = cls._create_provider(provider_type)

        return cls._instances[provider_type]

    @classmethod
    def _create_provider(cls, provider_type: ProviderType) -> StockDataProvider:
        """
        새 Provider 인스턴스 생성

        Args:
            provider_type: Provider 타입

        Returns:
            StockDataProvider: 새 Provider 인스턴스
        """
        if provider_type == ProviderType.ALPHA_VANTAGE:
            from .alphavantage import AlphaVantageProvider
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
            return AlphaVantageProvider(api_key=api_key)

        elif provider_type == ProviderType.FMP:
            from .fmp import FMPProvider
            api_key = os.getenv("FMP_API_KEY", "")
            return FMPProvider(api_key=api_key)

        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    @classmethod
    def get_fallback_providers(cls, provider_type: ProviderType) -> List[StockDataProvider]:
        """
        Fallback Provider 리스트 반환

        Args:
            provider_type: 현재 Provider 타입

        Returns:
            List[StockDataProvider]: Fallback provider 인스턴스 리스트
        """
        fallback_types = FALLBACK_CHAIN.get(provider_type, [])
        return [cls._get_or_create_provider(pt) for pt in fallback_types]

    @classmethod
    def clear_cache(cls) -> None:
        """캐시된 Provider 인스턴스 초기화"""
        cls._instances.clear()

    @classmethod
    def get_all_providers(cls) -> Dict[ProviderType, StockDataProvider]:
        """모든 활성화된 Provider 반환"""
        return cls._instances.copy()


def get_provider(
    endpoint: str,
    force_provider: Optional[str] = None
) -> StockDataProvider:
    """
    편의 함수: 문자열로 Provider 가져오기

    Args:
        endpoint: 엔드포인트 이름 (예: "quote", "profile")
        force_provider: 강제로 사용할 provider 이름

    Returns:
        StockDataProvider: Provider 인스턴스

    Example:
        provider = get_provider("quote")
        response = provider.get_quote("AAPL")
    """
    try:
        endpoint_type = EndpointType(endpoint.lower())
    except ValueError:
        logger.warning(f"Unknown endpoint: {endpoint}, using QUOTE as default")
        endpoint_type = EndpointType.QUOTE

    provider_type = None
    if force_provider:
        try:
            provider_type = ProviderType(force_provider.lower())
        except ValueError:
            logger.warning(f"Unknown provider: {force_provider}")

    return ProviderFactory.get_provider(endpoint_type, provider_type)


def call_with_fallback(
    endpoint: EndpointType,
    method_name: str,
    *args,
    **kwargs
) -> ProviderResponse:
    """
    Fallback 메커니즘을 적용한 Provider 호출

    주 Provider가 실패하면 Fallback Provider로 자동 전환합니다.

    Args:
        endpoint: 엔드포인트 타입
        method_name: 호출할 메서드 이름
        *args: 메서드 인자
        **kwargs: 메서드 키워드 인자

    Returns:
        ProviderResponse: Provider 응답

    Example:
        response = call_with_fallback(
            EndpointType.QUOTE,
            "get_quote",
            "AAPL"
        )
    """
    primary = ProviderFactory.get_provider(endpoint)
    providers = [primary] + ProviderFactory.get_fallback_providers(
        ProviderType(primary.PROVIDER_NAME)
    )

    last_error = None
    for provider in providers:
        try:
            method = getattr(provider, method_name)
            response = method(*args, **kwargs)

            if response.success:
                if provider != primary:
                    logger.info(
                        f"Fallback to {provider.PROVIDER_NAME} succeeded for {method_name}"
                    )
                return response

            # API 에러지만 다음 provider 시도
            last_error = response.error
            logger.warning(
                f"{provider.PROVIDER_NAME} failed for {method_name}: {response.error}"
            )

        except Exception as e:
            last_error = str(e)
            logger.error(
                f"{provider.PROVIDER_NAME} exception for {method_name}: {e}"
            )

    # 모든 provider 실패
    return ProviderResponse.error_response(
        error=f"All providers failed: {last_error}",
        provider="factory",
        error_code="ALL_PROVIDERS_FAILED"
    )


# 현재 설정 출력 (디버깅용)
def print_current_config() -> None:
    """현재 Provider 설정 출력"""
    print("\n=== Stock Provider Configuration ===")
    for endpoint in EndpointType:
        provider_type = ProviderFactory._get_provider_type_for_endpoint(endpoint)
        env_key = ENV_KEYS.get(endpoint, "N/A")
        env_value = os.getenv(env_key, "(not set)")
        print(f"  {endpoint.value:20s} -> {provider_type.value:15s} [{env_key}={env_value}]")
    print("=====================================\n")
