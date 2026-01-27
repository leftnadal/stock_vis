"""
Custom exceptions for the stocks app.
Provides standardized error handling with error codes and messages.
"""

from rest_framework import status
from rest_framework.response import Response


class StockAPIException(Exception):
    """Base exception for stock-related errors."""
    code = 'STOCK_ERROR'
    message = '주식 데이터 처리 중 오류가 발생했습니다.'
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    can_retry = True

    def __init__(self, message: str = None, details: dict = None):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_response(self) -> Response:
        """Convert exception to DRF Response."""
        return Response(
            {
                'error': {
                    'code': self.code,
                    'message': self.message,
                    'details': {
                        **self.details,
                        'can_retry': self.can_retry,
                    }
                }
            },
            status=self.status_code
        )


class StockNotFoundError(StockAPIException):
    """Raised when a stock cannot be found in DB or external APIs."""
    code = 'STOCK_NOT_FOUND'
    message = '요청한 종목을 찾을 수 없습니다.'
    status_code = status.HTTP_404_NOT_FOUND
    can_retry = True

    def __init__(self, symbol: str, tried_sources: list = None, message: str = None):
        details = {
            'symbol': symbol,
            'tried_sources': tried_sources or [],
        }
        super().__init__(
            message=message or f"종목 '{symbol}'을(를) 찾을 수 없습니다.",
            details=details
        )


class ExternalAPIError(StockAPIException):
    """Raised when external API calls fail."""
    code = 'EXTERNAL_API_ERROR'
    message = '외부 API 호출 중 오류가 발생했습니다.'
    status_code = status.HTTP_502_BAD_GATEWAY
    can_retry = True

    def __init__(self, api_name: str, original_error: str = None, message: str = None):
        details = {
            'api_name': api_name,
            'original_error': original_error,
        }
        super().__init__(
            message=message or f"{api_name} API 호출 중 오류가 발생했습니다.",
            details=details
        )


class RateLimitError(StockAPIException):
    """Raised when API rate limits are exceeded."""
    code = 'RATE_LIMIT_EXCEEDED'
    message = 'API 요청 한도를 초과했습니다.'
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    can_retry = True

    def __init__(self, api_name: str, reset_time: str = None, message: str = None):
        details = {
            'api_name': api_name,
            'reset_time': reset_time,
        }
        super().__init__(
            message=message or f"{api_name} API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            details=details
        )


class DataSyncError(StockAPIException):
    """Raised when data synchronization fails."""
    code = 'DATA_SYNC_ERROR'
    message = '데이터 동기화 중 오류가 발생했습니다.'
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    can_retry = True

    def __init__(self, symbol: str, data_type: str, original_error: str = None, message: str = None):
        details = {
            'symbol': symbol,
            'data_type': data_type,
            'original_error': original_error,
        }
        super().__init__(
            message=message or f"{symbol}의 {data_type} 데이터 동기화 중 오류가 발생했습니다.",
            details=details
        )


class InvalidParameterError(StockAPIException):
    """Raised when request parameters are invalid."""
    code = 'INVALID_PARAMETER'
    message = '잘못된 요청 파라미터입니다.'
    status_code = status.HTTP_400_BAD_REQUEST
    can_retry = False

    def __init__(self, parameter_name: str, provided_value: str = None, allowed_values: list = None, message: str = None):
        details = {
            'parameter_name': parameter_name,
            'provided_value': provided_value,
            'allowed_values': allowed_values,
        }
        super().__init__(
            message=message or f"잘못된 파라미터입니다: {parameter_name}",
            details=details
        )


class DataNotAvailableError(StockAPIException):
    """Raised when data exists but is not available (e.g., outdated)."""
    code = 'DATA_NOT_AVAILABLE'
    message = '데이터를 사용할 수 없습니다.'
    status_code = status.HTTP_404_NOT_FOUND
    can_retry = True

    def __init__(self, symbol: str, data_type: str, last_available: str = None, message: str = None):
        details = {
            'symbol': symbol,
            'data_type': data_type,
            'last_available': last_available,
        }
        super().__init__(
            message=message or f"{symbol}의 {data_type} 데이터를 사용할 수 없습니다.",
            details=details
        )
