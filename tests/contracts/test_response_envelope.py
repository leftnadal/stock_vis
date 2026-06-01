"""
audit P0 #14 (PR-0) — custom_exception_handler 계약 테스트.

표준 에러 envelope: {detail, code?, errors?, status_code}.

DRF 표준 예외 + 도메인 APIException 서브클래스가 동일한 키 셋을 반환하는지 검증.
상세: docs/features/api_envelope/policy.md §4.2
"""
from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from services.rag_analysis.exceptions import CacheError
from services.serverless.exceptions import GenerationFailed, SyncFailed


def _make_view(exc_to_raise):
    """주어진 예외를 raise하는 최소 APIView를 생성."""

    class _RaisingView(APIView):
        permission_classes = [AllowAny]

        def get(self, request):
            raise exc_to_raise

    return _RaisingView.as_view()


def _invoke(exc):
    factory = APIRequestFactory()
    view = _make_view(exc)
    request = factory.get("/__test__/")
    response = view(request)
    response.render()
    return response


# ────────── DRF 표준 예외 ──────────

def test_not_found_envelope():
    resp = _invoke(NotFound("Stock not found"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    body = resp.data
    assert body["detail"] == "Stock not found"
    assert body["code"] == "not_found"
    assert body["status_code"] == 404
    assert "errors" not in body


def test_not_authenticated_envelope():
    resp = _invoke(NotAuthenticated())
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    body = resp.data
    assert body["code"] == "not_authenticated"
    assert body["status_code"] == 401
    assert isinstance(body["detail"], str)


def test_permission_denied_envelope():
    resp = _invoke(PermissionDenied("Admin only"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.data
    assert body["detail"] == "Admin only"
    assert body["code"] == "permission_denied"
    assert body["status_code"] == 403


def test_validation_error_field_dict():
    resp = _invoke(ValidationError({"email": ["required"], "password": ["too short"]}))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    body = resp.data
    assert body["code"] == "invalid"  # DRF default_code on ValidationError
    assert body["status_code"] == 400
    assert "errors" in body
    assert body["errors"]["email"] == ["required"]
    assert body["errors"]["password"] == ["too short"]
    assert body["detail"] == "Validation failed."


def test_validation_error_non_field_list():
    resp = _invoke(ValidationError(["Bad input one", "Bad input two"]))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    body = resp.data
    assert body["code"] == "invalid"
    assert body["status_code"] == 400
    assert "Bad input one" in body["detail"]
    assert "Bad input two" in body["detail"]


def test_throttled_envelope():
    resp = _invoke(Throttled(wait=30))
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    body = resp.data
    assert body["code"] == "throttled"
    assert body["status_code"] == 429
    assert "30" in body["detail"]


# ────────── 도메인 APIException 서브클래스 ──────────

def test_cache_error_envelope():
    resp = _invoke(CacheError("Redis connection refused"))
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    body = resp.data
    assert body["detail"] == "Redis connection refused"
    assert body["code"] == "cache_error"
    assert body["status_code"] == 500


def test_cache_error_default_detail():
    resp = _invoke(CacheError())
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    body = resp.data
    assert body["detail"] == "Cache operation failed."
    assert body["code"] == "cache_error"


def test_generation_failed_envelope():
    resp = _invoke(GenerationFailed("LLM timeout"))
    assert resp.status_code == 500
    body = resp.data
    assert body["detail"] == "LLM timeout"
    assert body["code"] == "generation_failed"
    assert body["status_code"] == 500


def test_sync_failed_envelope():
    resp = _invoke(SyncFailed())
    assert resp.status_code == 500
    body = resp.data
    assert body["code"] == "sync_failed"
    assert body["status_code"] == 500


# ────────── envelope 키 셋 일관성 ──────────

@pytest.mark.parametrize("exc", [
    NotFound("x"),
    NotAuthenticated(),
    PermissionDenied("y"),
    ValidationError(["z"]),
    Throttled(wait=10),
    CacheError("a"),
    GenerationFailed("b"),
    SyncFailed(),
])
def test_envelope_has_required_keys(exc):
    resp = _invoke(exc)
    body = resp.data
    assert {"detail", "code", "status_code"}.issubset(body.keys())
    assert isinstance(body["detail"], str)
    assert isinstance(body["code"], str)
    assert isinstance(body["status_code"], int)
