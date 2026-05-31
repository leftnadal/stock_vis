"""rag_analysis 도메인 APIException — envelope 표준 흡수.

기존 wrap 응답의 도메인 코드를 snake_case `default_code`로 보존:
- 5xx: CacheError, CostError, HistoryError, StatsError
- 4xx 비즈니스: BasketFull, DuplicateItem, CapacityExceeded
- 503: CacheUnavailable

비즈니스 의미가 있는 4xx 코드는 ValidationError로 흡수하지 않고 도메인
예외로 유지 — 클라이언트가 status_code+detail이 아닌 code로 분기 가능.

상세: docs/features/api_envelope/policy.md §3.2
"""

from rest_framework import status
from rest_framework.exceptions import APIException

# ===== 5xx 도메인 예외 =====


class CacheError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Cache operation failed."
    default_code = "cache_error"


class CostError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Cost computation failed."
    default_code = "cost_error"


class HistoryError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "History retrieval failed."
    default_code = "history_error"


class StatsError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Stats query failed."
    default_code = "stats_error"


# ===== 4xx 비즈니스 도메인 예외 =====


class BasketFull(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "DataBasket is full."
    default_code = "basket_full"


class DuplicateItem(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Item already exists in basket."
    default_code = "duplicate_item"


class CapacityExceeded(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Capacity exceeded."
    default_code = "capacity_exceeded"


# ===== 5xx 서비스 가용성 =====


class CacheUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Semantic cache service is unavailable."
    default_code = "cache_unavailable"
