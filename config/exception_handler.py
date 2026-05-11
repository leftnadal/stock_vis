"""
DRF EXCEPTION_HANDLER — 응답 에러 envelope 표준화.

표준 형태: {detail, code?, errors?, status_code}

상세: docs/features/api_envelope/policy.md §4
"""
from __future__ import annotations

from typing import Any

from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_default_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]):
    response = drf_default_handler(exc, context)
    if response is None:
        return None

    payload: dict[str, Any] = {"status_code": response.status_code}
    detail_obj = response.data

    if isinstance(exc, ValidationError):
        if isinstance(detail_obj, dict):
            payload["detail"] = "Validation failed."
            payload["code"] = getattr(exc, "default_code", None) or "validation_error"
            payload["errors"] = detail_obj
        elif isinstance(detail_obj, list):
            payload["detail"] = "; ".join(str(m) for m in detail_obj) or "Validation failed."
            payload["code"] = getattr(exc, "default_code", None) or "validation_error"
        else:
            payload["detail"] = str(detail_obj)
            payload["code"] = getattr(exc, "default_code", None) or "validation_error"
    elif isinstance(detail_obj, dict) and "detail" in detail_obj:
        payload["detail"] = str(detail_obj["detail"])
        payload["code"] = (
            getattr(exc, "default_code", None)
            or getattr(detail_obj["detail"], "code", None)
            or "error"
        )
    elif isinstance(detail_obj, dict):
        payload["detail"] = "Error"
        payload["code"] = getattr(exc, "default_code", None) or "error"
        payload["errors"] = detail_obj
    else:
        payload["detail"] = str(detail_obj)
        payload["code"] = getattr(exc, "default_code", None) or "error"

    response.data = payload
    return response
