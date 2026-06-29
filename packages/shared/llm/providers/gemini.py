"""Gemini provider — genai Client 래핑 (베이스 #2 build_client 패턴). 우선 provider.

sync `generate`(client.models.generate_content) + async `agenerate`(client.aio.models.
generate_content, 슬라이스 ②b). config 조립·응답 추출은 단일 출처 헬퍼(_build_config_kwargs·
_extract_raw)를 둘 다 경유 — 분기는 dispatch(sync/aio)만, 조립 복제 0(drift 방지, 규약 10).

주의(Bug #8): sync 경로는 동기 API만. async 경로(aio)는 asyncio 이벤트 루프 컨텍스트 전용 —
Celery 동기 태스크에서는 sync `generate`를 쓴다(async genai.Client fork 충돌 회피).
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


def _build_config_kwargs(
    *,
    max_tokens: Optional[int],
    temperature: Optional[float],
    response_format: Optional[str],
    system: Optional[str],
    extra: Optional[dict],
) -> dict:
    """생성 config 조립 단일 출처 — sync/async 양쪽이 동일하게 경유(byte 동일 보장).

    extra(provider 고유: thinking_config·top_p 등) 먼저 → 명시 노브가 우선(덮어씀).
    None = 미설정(provider 기본) — 현행 동작 재현.
    """
    config_kwargs: dict = dict(extra or {})
    if max_tokens is not None:
        config_kwargs["max_output_tokens"] = max_tokens
    if temperature is not None:
        config_kwargs["temperature"] = temperature
    if response_format == "json":
        config_kwargs["response_mime_type"] = "application/json"
    if system:
        config_kwargs["system_instruction"] = system
    return config_kwargs


def _extract_raw(response, started: float) -> LLMRawResponse:
    """genai 응답 → LLMRawResponse 추출 단일 출처 — sync/async 동일."""
    latency_ms = int((time.time() - started) * 1000)
    text = getattr(response, "text", "") or ""
    usage = getattr(response, "usage_metadata", None)
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    return LLMRawResponse(text, input_tokens, output_tokens, latency_ms)


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
        """동기 생성 — client.models.generate_content."""
        from google import genai
        from google.genai import types as gtypes

        api_key = _resolve_api_key()
        if not api_key:
            raise LLMAuthError("GEMINI_API_KEY/GOOGLE_AI_API_KEY not configured")
        used_model = model or DEFAULT_MODEL
        config_kwargs = _build_config_kwargs(
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            system=system,
            extra=extra,
        )
        started = time.time()
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(  # ← sync dispatch
                model=used_model,
                contents=prompt,
                config=gtypes.GenerateContentConfig(**config_kwargs),
            )
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc

        return _extract_raw(response, started)

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
        """비동기 생성 — client.aio.models.generate_content (슬라이스 ②b).

        조립(config·contents·model)·추출은 sync `generate`와 동일 헬퍼 경유 →
        하부 GenerateContentConfig byte 동일. 분기는 dispatch(aio)만.
        """
        from google import genai
        from google.genai import types as gtypes

        api_key = _resolve_api_key()
        if not api_key:
            raise LLMAuthError("GEMINI_API_KEY/GOOGLE_AI_API_KEY not configured")
        used_model = model or DEFAULT_MODEL
        config_kwargs = _build_config_kwargs(
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            system=system,
            extra=extra,
        )
        started = time.time()
        try:
            client = genai.Client(api_key=api_key)
            response = await client.aio.models.generate_content(  # ← async dispatch
                model=used_model,
                contents=prompt,
                config=gtypes.GenerateContentConfig(**config_kwargs),
            )
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc

        return _extract_raw(response, started)

    async def aopen_stream(
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
        """비동기 스트림 **셋업만** — client.aio.models.generate_content_stream await
        (요청 전송 + 스트림 오픈) 후 SDK async iterator 반환. 청크 읽기는 호출자가 수행.

        circuit 경계 분리용(슬라이스 ④): 코어 astream(circuit=)이 이 셋업 coroutine만 CB로 감싸고
        (원본 #12 `cb.acall(generate_content_stream)`와 동형 — 셋업만 보호), 청크 iteration은 CB
        바깥에서 돈다. 조립(config·contents·model)은 generate/agenerate/astream과 동일
        `_build_config_kwargs` 경유 → 하부 GenerateContentConfig byte 동일. SDK 예외는 코어 계층 분류.
        """
        from google import genai
        from google.genai import types as gtypes

        api_key = _resolve_api_key()
        if not api_key:
            raise LLMAuthError("GEMINI_API_KEY/GOOGLE_AI_API_KEY not configured")
        used_model = model or DEFAULT_MODEL
        config_kwargs = _build_config_kwargs(
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            system=system,
            extra=extra,
        )
        try:
            client = genai.Client(api_key=api_key)
            return await client.aio.models.generate_content_stream(  # ← stream dispatch(셋업)
                model=used_model,
                contents=prompt,
                config=gtypes.GenerateContentConfig(**config_kwargs),
            )
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc

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
        """비동기 스트리밍 — aopen_stream 셋업 후 청크 **증분 yield**(재청크·버퍼링·뭉개기 0 —
        청크 경계·순서 그대로). 조립은 aopen_stream(동일 `_build_config_kwargs`) 경유 → config byte
        동일. SDK 예외는 코어 계층으로 분류 후 재전파.
        """
        stream = await self.aopen_stream(
            prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            extra=extra,
        )
        try:
            async for chunk in stream:
                yield chunk  # 원 청크 그대로(증분 보존)
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc
