"""
Market Pulse 공용 Gemini 클라이언트 — 동기 호출 plumbing 단일출처 (Brief에서 추출).

소속: apps/market_pulse/llm (app 레이어 LLM 호출 공용 모듈).
역할: genai 동기 Client 빌드 + circuit breaker(`gemini`) 결합 + usage/latency 추출.
  소비처(briefing/, 후속 translation/)는 system_instruction·contents만 주입해 재사용 — 복제 0.
의존: packages.shared.api_request.circuit_breaker (CB `gemini`), google.genai 동기 클라이언트.
주의: Celery 안 호출 — **반드시 동기 API**(Bug #8: async genai.Client는 worker fork 충돌).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from django.conf import settings

from packages.shared.api_request.circuit_breaker import get_circuit

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class LLMRawResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def resolve_api_key() -> str | None:
    return getattr(settings, "GOOGLE_AI_API_KEY", None) or getattr(
        settings, "GEMINI_API_KEY", None
    )


def build_client():
    from google import genai as genai_module

    api_key = resolve_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY/GOOGLE_AI_API_KEY not configured")
    return genai_module.Client(api_key=api_key)


def generate_content(
    *, system_instruction: str, contents: list, model: str = DEFAULT_MODEL
) -> LLMRawResponse:
    """동기 generate_content 호출 + usage/latency 추출. 프롬프트는 호출부가 조립."""
    client = build_client()
    started = time.time()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={"system_instruction": system_instruction},
    )
    latency_ms = int((time.time() - started) * 1000)
    text = getattr(response, "text", "") or ""
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    return LLMRawResponse(text, prompt_tokens, completion_tokens, latency_ms)


def generate_with_circuit(
    *, system_instruction: str, contents: list, model: str = DEFAULT_MODEL
) -> LLMRawResponse:
    """circuit breaker(`gemini`)로 감싼 동기 호출. retry/backoff/open 처리는 CB가 담당."""
    cb = get_circuit("gemini")
    return cb.call(
        generate_content,
        system_instruction=system_instruction,
        contents=contents,
        model=model,
    )
