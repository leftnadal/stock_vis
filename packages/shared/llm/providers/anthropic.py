"""Anthropic provider — messages.create 래핑 (베이스 #1 패턴). 2nd provider."""

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

DEFAULT_MODEL = "claude-sonnet-4-5"


def _resolve_api_key() -> Optional[str]:
    from django.conf import settings

    return getattr(settings, "ANTHROPIC_API_KEY", None)


def _classify(exc: Exception) -> Exception:
    """Anthropic SDK 예외 → 코어 예외 계층 (베이스 #1 _classify_anthropic_error 미러)."""
    cls = type(exc).__name__
    if cls == "RateLimitError":
        return LLMRateLimitError(str(exc))
    if cls in ("APITimeoutError", "APIConnectionError"):
        return LLMTimeoutError(str(exc))
    if cls == "AuthenticationError":
        return LLMAuthError(str(exc))
    if cls in ("BadRequestError", "UnprocessableEntityError"):
        return LLMInvalidPromptError(str(exc))
    return exc


class AnthropicProvider:
    name = "anthropic"
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
        from anthropic import Anthropic

        api_key = _resolve_api_key()
        if not api_key:
            raise LLMAuthError("ANTHROPIC_API_KEY not configured")
        used_model = model or DEFAULT_MODEL
        started = time.time()
        try:
            client = Anthropic(api_key=api_key)
            # extra(top_p·stop_sequences 등) 먼저 → 명시 노브 우선.
            kwargs: dict = dict(extra or {})
            kwargs.update(
                {
                    "model": used_model,
                    # Anthropic messages.create는 max_tokens 필수 → None이면 2000 폴백.
                    "max_tokens": max_tokens if max_tokens is not None else 2000,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            if temperature is not None:
                kwargs["temperature"] = temperature
            # response_format: Anthropic은 response_mime_type 미지원 → 무시(provider 한계, 문서화).
            if system:
                kwargs["system"] = system
            response = client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc

        latency_ms = int((time.time() - started) * 1000)
        text = ""
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", "") or ""
                break
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMRawResponse(text, input_tokens, output_tokens, latency_ms)

    async def agenerate(
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
        """Anthropic async 미구현 — 슬라이스 ③ Anthropic 이관에서 AsyncAnthropic로 신설.

        ②b는 Gemini aio만 대상(aio Part 5곳 전부 Gemini). acomplete(provider='anthropic')는
        여기서 명시 차단(조용한 동기 폴백 금지).
        """
        raise NotImplementedError(
            "Anthropic async(agenerate)는 슬라이스 ③에서 구현 — ②b는 Gemini aio 전용."
        )

    async def astream(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
        extra: Optional[dict] = None,
    ):
        """Anthropic async streaming 미구현 — 슬라이스 ③에서 messages.stream(AsyncAnthropic)로 신설.

        ②b-stream은 Gemini 전용(#12 gemini_rag). ③ 예고: #8 adaptive(messages.stream async)가
        agenerate + astream 둘 다 요구 → ③ 범위 결정에 반영. 반복 시점 NotImplementedError.
        """
        raise NotImplementedError(
            "Anthropic astream은 슬라이스 ③에서 구현 — ②b-stream은 Gemini 전용."
        )
        yield  # 도달 불가 — async generator 표식(반복 시 위 raise 발생)
