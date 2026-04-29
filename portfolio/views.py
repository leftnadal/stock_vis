"""
Portfolio Coach Django views.

slice 1 전반부 — 단일 진입점:
  - GET /api/coach/e1/garp/?provider=gemini|anthropic

§6.4 자율 판단 금지: 순수 Django view + JsonResponse만 (DRF 미사용).
"""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from portfolio.llm import LLMBudgetExceededError, LLMError
from portfolio.services.e1_garp import run_e1_garp


_VALID_PROVIDERS = ("gemini", "anthropic")


@require_GET
def coach_e1_garp(request: HttpRequest) -> JsonResponse:
    """
    GET /api/coach/e1/garp/?provider=gemini

    E1 한 줄 진단을 GARP 프리셋 + Mock fixture 기반으로 실행.
    """
    provider = request.GET.get("provider", "gemini")
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
