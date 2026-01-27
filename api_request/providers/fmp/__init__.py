# api_request/providers/fmp/__init__.py
"""
Financial Modeling Prep (FMP) Provider Package

FMP API를 사용하여 StockDataProvider 인터페이스를 구현합니다.
주요 장점: 재무제표, 회사 프로필에 강점
"""

from .provider import FMPProvider

__all__ = ['FMPProvider']
