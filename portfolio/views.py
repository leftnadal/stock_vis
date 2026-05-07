"""
Portfolio Coach Django views.

진입점:
  - GET  /api/coach/e1/garp/?provider=haiku            (Slice 1)
  - POST /api/coach/e5/adjustment/?provider=haiku      (Slice 2)
  - POST /api/coach/e2/diagnostic-card/?provider=haiku (Slice 3)
  - POST /api/coach/e6/comparison/?provider=haiku      (Slice 4)

순수 Django view + JsonResponse (DRF 미사용).
"""

from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from pydantic import ValidationError

from portfolio.llm import LLMBudgetExceededError, LLMError
from portfolio.schemas.llm import E2Request, E5Request, E6Request
from portfolio.services.e1_garp import run_e1_garp
from portfolio.services.e2_diagnostic_card import run_e2
from portfolio.services.e5_adjustment_parser import run_e5
from portfolio.services.e6_comparison import run_e6


# Slice 1 Decision: default provider = haiku (winner).
# "gemini"는 호환성 위해 허용하나 free tier에서 RateLimit 즉시 폴백 발생 가능.
_VALID_PROVIDERS = ("gemini", "anthropic", "sonnet", "haiku")


@require_GET
def coach_e1_garp(request: HttpRequest) -> JsonResponse:
    """
    GET /api/coach/e1/garp/?provider=haiku

    E1 한 줄 진단을 GARP 프리셋 + Mock fixture 기반으로 실행.
    provider 옵션: haiku (기본) | sonnet | anthropic (= sonnet) | gemini.
    """
    provider = request.GET.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return JsonResponse(
            {"error": f"Invalid provider: {provider!r}. Must be one of {list(_VALID_PROVIDERS)}."},
            status=400,
        )

    try:
        result = run_e1_garp(provider=provider)
    except LLMBudgetExceededError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except LLMError as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(result, status=200)


@csrf_exempt
@require_POST
def coach_e5_adjustment(request: HttpRequest) -> JsonResponse:
    """
    POST /api/coach/e5/adjustment/?provider=haiku

    body (JSON): {"analysis_context": {...}, "user_command": "...", "session_id": "..."}
    provider 옵션: haiku (기본) | sonnet | anthropic | gemini.

    응답:
      200 — {"response": E5Response, "metadata": LLMResponse.metadata_dict()}
      400 — invalid body or invalid provider
      429 — budget exceeded
      500 — LLM 호출 실패
    """
    provider = request.GET.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return JsonResponse(
            {
                "error": "invalid_provider",
                "detail": f"{provider!r} not in {list(_VALID_PROVIDERS)}",
            },
            status=400,
        )

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": f"json parse error: {exc}"},
            status=400,
        )

    try:
        e5_request = E5Request.model_validate(body)
    except ValidationError as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": str(exc)[:500]},
            status=400,
        )

    try:
        result = run_e5(e5_request, provider=provider)
    except LLMBudgetExceededError as exc:
        return JsonResponse(
            {"error": "budget_exceeded", "detail": str(exc)}, status=429
        )
    except LLMError as exc:
        return JsonResponse(
            {"error": "llm_invocation_failed", "detail": str(exc)[:300]},
            status=500,
        )
    except ValidationError as exc:
        # LLM 응답 schema 미일치
        return JsonResponse(
            {"error": "llm_response_schema_mismatch", "detail": str(exc)[:500]},
            status=500,
        )

    return JsonResponse(result, status=200, json_dumps_params={"ensure_ascii": False})


@csrf_exempt
@require_POST
def coach_e2_diagnostic_card(request: HttpRequest) -> JsonResponse:
    """
    POST /api/coach/e2/diagnostic-card/?provider=haiku

    body (JSON): {"analysis_context": {...}, "session_id": "..."}
    provider 옵션: haiku (기본 — D2.B 글쓰기) | sonnet | anthropic | gemini.

    응답:
      200 — {"response": E2Response, "metadata": LLMResponse.metadata_dict()}
      400 — invalid body or invalid provider
      429 — budget exceeded
      500 — LLM 호출 실패
    """
    provider = request.GET.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return JsonResponse(
            {
                "error": "invalid_provider",
                "detail": f"{provider!r} not in {list(_VALID_PROVIDERS)}",
            },
            status=400,
        )

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": f"json parse error: {exc}"},
            status=400,
        )

    try:
        e2_request = E2Request.model_validate(body)
    except ValidationError as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": str(exc)[:500]},
            status=400,
        )

    try:
        result = run_e2(e2_request, provider=provider)
    except LLMBudgetExceededError as exc:
        return JsonResponse(
            {"error": "budget_exceeded", "detail": str(exc)}, status=429
        )
    except LLMError as exc:
        return JsonResponse(
            {"error": "llm_invocation_failed", "detail": str(exc)[:300]},
            status=500,
        )
    except ValidationError as exc:
        return JsonResponse(
            {"error": "llm_response_schema_mismatch", "detail": str(exc)[:500]},
            status=500,
        )

    return JsonResponse(result, status=200, json_dumps_params={"ensure_ascii": False})


@csrf_exempt
@require_POST
def coach_e6_comparison(request: HttpRequest) -> JsonResponse:
    """
    POST /api/coach/e6/comparison/?provider=haiku

    body (JSON): {"analysis_context": {...}, "adjustments": [...], "user_intent": "..."}
    provider 옵션: haiku (기본 — D2.B 글쓰기) | sonnet | anthropic | gemini.

    응답:
      200 — {"response": E6ComparisonResponse, "metadata": LLMResponse.metadata_dict()}
      400 — invalid body or invalid provider
      429 — budget exceeded
      500 — LLM 호출 실패 / 응답 schema 불일치
    """
    provider = request.GET.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return JsonResponse(
            {
                "error": "invalid_provider",
                "detail": f"{provider!r} not in {list(_VALID_PROVIDERS)}",
            },
            status=400,
        )

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": f"json parse error: {exc}"},
            status=400,
        )

    try:
        e6_request = E6Request.model_validate(body)
    except ValidationError as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": str(exc)[:500]},
            status=400,
        )

    try:
        result = run_e6(e6_request, provider=provider)
    except LLMBudgetExceededError as exc:
        return JsonResponse(
            {"error": "budget_exceeded", "detail": str(exc)}, status=429
        )
    except LLMError as exc:
        return JsonResponse(
            {"error": "llm_invocation_failed", "detail": str(exc)[:300]},
            status=500,
        )
    except ValidationError as exc:
        return JsonResponse(
            {"error": "llm_response_schema_mismatch", "detail": str(exc)[:500]},
            status=500,
        )

    return JsonResponse(result, status=200, json_dumps_params={"ensure_ascii": False})
