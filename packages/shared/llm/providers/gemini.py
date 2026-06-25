"""Gemini provider — genai 동기 Client 래핑 (베이스 #2 build_client 패턴). 우선 provider.

주의: 동기 API만(Bug #8: async genai.Client는 Celery worker fork 충돌).
"""

from __future__ import annotations

import time
from typing import Optional

from packages.shared.llm.types import (
    LLMAuthError,
    LLMInvalidPromptError,
    LLMRateLimitError,
    LLMRawResponse,
    LLMTimeoutError,
)

DEFAULT_MODEL = "gemini-2.5-flash"


def _resolve_api_key() -> Optional[str]:
    # 베이스 #2 resolve_api_key 패턴 (GOOGLE_AI_API_KEY 우선, GEMINI_API_KEY 폴백).
    from django.conf import settings

    return getattr(settings, "GOOGLE_AI_API_KEY", None) or getattr(
        settings, "GEMINI_API_KEY", None
    )


def _classify(exc: Exception) -> Exception:
    """genai 신 SDK 예외 → 코어 예외 계층 (베이스 #1 _classify_gemini_error 미러)."""
    cls = type(exc).__name__.lower()
    msg = str(exc).lower()
    if (
        "ratelimit" in cls
        or "resourceexhausted" in cls
        or "quota" in msg
        or "rate limit" in msg
    ):
        return LLMRateLimitError(str(exc))
    if (
        "timeout" in cls
        or "deadlineexceeded" in cls
        or "timeout" in msg
        or "deadline" in msg
    ):
        return LLMTimeoutError(str(exc))
    if (
        "permission" in cls
        or "unauthenticated" in cls
        or "api key" in msg
        or "unauthorized" in msg
    ):
        return LLMAuthError(str(exc))
    if "invalidargument" in cls or "badrequest" in cls or "invalid" in msg:
        return LLMInvalidPromptError(str(exc))
    return exc


class GeminiProvider:
    name = "gemini"
    default_model = DEFAULT_MODEL

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> LLMRawResponse:
        from google import genai
        from google.genai import types as gtypes

        api_key = _resolve_api_key()
        if not api_key:
            raise LLMAuthError("GEMINI_API_KEY/GOOGLE_AI_API_KEY not configured")
        used_model = model or DEFAULT_MODEL
        started = time.time()
        try:
            client = genai.Client(api_key=api_key)
            # extra(provider 고유: thinking_config·top_p 등) 먼저 → 명시 노브가 우선(덮어씀).
            config_kwargs: dict = dict(extra or {})
            if max_tokens is not None:  # None = 미설정(provider 기본) — 현행 재현
                config_kwargs["max_output_tokens"] = max_tokens
            if temperature is not None:
                config_kwargs["temperature"] = temperature
            if response_format == "json":
                config_kwargs["response_mime_type"] = "application/json"
            if system:
                config_kwargs["system_instruction"] = system
            response = client.models.generate_content(
                model=used_model,
                contents=prompt,
                config=gtypes.GenerateContentConfig(**config_kwargs),
            )
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc

        latency_ms = int((time.time() - started) * 1000)
        text = getattr(response, "text", "") or ""
        usage = getattr(response, "usage_metadata", None)
        input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        return LLMRawResponse(text, input_tokens, output_tokens, latency_ms)
