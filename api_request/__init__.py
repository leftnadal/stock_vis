# api_request/__init__.py
"""
API Request Package

외부 API(Alpha Vantage, FMP)와의 통신 및 데이터 처리를 담당합니다.

주요 모듈:
- alphavantage_client: Alpha Vantage HTTP 클라이언트
- alphavantage_processor: 데이터 변환 처리
- alphavantage_service: 비즈니스 로직 및 DB 저장 (레거시)
- stock_service: Provider 추상화를 활용한 통합 서비스 (신규)
- providers/: Provider 추상화 레이어
- cache/: 캐싱 레이어
- rate_limiter: Rate Limiting

권장 사용법:
    from api_request.stock_service import get_stock_service, StockService

    service = get_stock_service()
    quote = service.get_quote('AAPL')
"""

# 편의를 위한 주요 클래스/함수 export
try:
    from .stock_service import StockService, get_stock_service
except ImportError:
    # Django 설정이 로드되지 않은 경우를 위한 fallback
    StockService = None
    get_stock_service = None

__all__ = [
    'StockService',
    'get_stock_service',
]
