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
    StreamDelta,
    StreamFinal,
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


def _build_stream_kwargs(
    *,
    prompt: str,
    model: Optional[str],
    system: Optional[str],
    max_tokens: Optional[int],
    temperature: Optional[float],
    extra: Optional[dict],
) -> dict:
    """messages.stream/create 공통 kwargs 조립 (§핀4 #8 파라미터 집합 그대로).

    extra 먼저 → 명시 노브 우선. temperature/system은 값 있을 때만(#8 직접호출 동형).
    max_tokens None이면 2000 폴백(create와 동일). response_format은 Anthropic 미지원 → 무시.
    """
    kwargs: dict = dict(extra or {})
    kwargs.update(
        {
            "model": model or DEFAULT_MODEL,
            "max_tokens": max_tokens if max_tokens is not None else 2000,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    if temperature is not None:
        kwargs["temperature"] = temperature
    if system:
        kwargs["system"] = system
    return kwargs


class _AnthropicStreamAdapter:
    """messages.stream(async context manager)을 코어 astream 계약(StreamDelta*+StreamFinal)으로 변환.

    §핀5 어댑터: 셋업(cm.__aenter__=요청 전송)은 aopen_stream이 이미 완료(CB 대상 경계) →
    이 어댑터는 순회만 담당. text_stream(str) → StreamDelta, 종료 후 get_final_message().usage →
    StreamFinal. finally에서 cm.__aexit__로 연결 반드시 해제(누수 방지). SDK 예외는 코어 계층 분류.
    """

    def __init__(self, cm, stream):
        self._cm = cm
        self._stream = stream

    async def __aiter__(self):
        try:
            async for text in self._stream.text_stream:
                yield StreamDelta(text=text)
            final = await self._stream.get_final_message()
            usage = getattr(final, "usage", None)
            yield StreamFinal(
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            )
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc
        finally:
            await self._cm.__aexit__(None, None, None)


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
        """비동기 스트림 **셋업만** (슬라이스 ③b) — AsyncAnthropic.messages.stream 컨텍스트 진입.

        §핀5: gemini aopen_stream(await→iterator)과 동형 브리지 — messages.stream(async with)의
        `cm.__aenter__()`(요청 전송 = 스트림 오픈)를 **셋업 경계**로 삼아 여기서 await(코어 astream
        circuit=이 이 coroutine만 awith_circuit으로 감쌈, gemini 동형). 순회는 반환 어댑터가 담당.
        조립은 generate와 동일 `_build_stream_kwargs` 경유. SDK 예외는 코어 계층 분류.
        """
        from anthropic import AsyncAnthropic

        api_key = _resolve_api_key()
        if not api_key:
            raise LLMAuthError("ANTHROPIC_API_KEY not configured")
        kwargs = _build_stream_kwargs(
            prompt=prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            extra=extra,
        )
        try:
            client = AsyncAnthropic(api_key=api_key)
            cm = client.messages.stream(**kwargs)
            stream = await cm.__aenter__()  # ← 셋업(요청 전송) = CB 대상 경계
        except Exception as exc:  # noqa: BLE001 — SDK 예외를 코어 계층으로 분류 후 재전파
            raise _classify(exc) from exc
        return _AnthropicStreamAdapter(cm, stream)

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
        """비동기 스트리밍 (슬라이스 ③b) — aopen_stream 셋업 후 어댑터 순회 위임.

        StreamDelta*(텍스트 증분) + 종단 StreamFinal(usage) yield. 조립은 aopen_stream(동일
        `_build_stream_kwargs`) 경유. circuit=None 경로(코어가 prov.astream 직접 호출, #8)에서 셋업+
        순회 융합; circuit 경로는 코어가 aopen_stream만 CB로 감싸고 어댑터를 CB 바깥에서 순회.
        """
        adapter = await self.aopen_stream(
            prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            extra=extra,
        )
        async for delta in adapter:
            yield delta
