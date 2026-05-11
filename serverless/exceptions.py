"""serverless 도메인 APIException — envelope 표준 흡수.

기존 wrap 응답의 5xx 도메인 코드를 snake_case `default_code`로 보존.
4xx 에러는 DRF 표준 예외(NotFound/PermissionDenied/ValidationError 등)로 대체한다.

상세: docs/features/api_envelope/policy.md §3.2
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class GenerationFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Generation failed."
    default_code = "generation_failed"


class SyncFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Sync operation failed."
    default_code = "sync_failed"


class ScreenerError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Screener execution failed."
    default_code = "screener_error"


class InstitutionalError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Institutional data retrieval failed."
    default_code = "institutional_error"


class InstitutionalPeersError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Institutional peers retrieval failed."
    default_code = "institutional_peers_error"


class PatentError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Patent data retrieval failed."
    default_code = "patent_error"


class RegulatoryError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Regulatory data retrieval failed."
    default_code = "regulatory_error"


class ThesisGenerationFailed(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Thesis generation failed."
    default_code = "thesis_generation_failed"
