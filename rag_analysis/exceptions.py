"""rag_analysis 도메인 APIException — envelope 표준 흡수.

기존 wrap 응답의 도메인 코드(`CACHE_ERROR`, `COST_ERROR`, `HISTORY_ERROR`,
`STATS_ERROR`)를 snake_case `default_code`로 보존.

상세: docs/features/api_envelope/policy.md §3.2
"""
from rest_framework import status
from rest_framework.exceptions import APIException


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
