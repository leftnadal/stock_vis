# api_request/providers/__init__.py
"""
Stock Data Provider Package

이 패키지는 다양한 주식 데이터 제공자(Alpha Vantage, FMP 등)를
추상화하여 일관된 인터페이스를 제공합니다.

Usage:
    from api_request.providers import get_provider

    provider = get_provider('quote')  # Feature flag에 따라 적절한 provider 반환
    quote = provider.get_quote('AAPL')
"""

from .base import StockDataProvider, ProviderResponse
from .factory import get_provider, ProviderType

__all__ = [
    'StockDataProvider',
    'ProviderResponse',
    'get_provider',
    'ProviderType',
]
