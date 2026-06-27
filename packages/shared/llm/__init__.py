"""packages/shared/llm — 통합 LLM 코어 (BOUNDARY-LLM 슬라이스 ①, 소비처 0).

공개 표면:
  complete(prompt, *, provider, model, system, max_tokens,
           circuit=None, escape=False, retries=0, cost_track=False, fallback=None) -> LLMResponse
  acomplete(...) — complete()의 async 동형 (슬라이스 ②b, Gemini aio 경로). 동일 시그니처.
  LLMResponse / LLMRawResponse / 예외 계층.

정책 형태 B(파라미터 토글, 기본 off) — 기본값 = 현행 동작 재현(IDENTICAL).
"""

from __future__ import annotations

from packages.shared.llm.core import acomplete, complete
from packages.shared.llm.types import (
    LLMAuthError,
    LLMBudgetExceededError,
    LLMError,
    LLMInvalidPromptError,
    LLMRateLimitError,
    LLMRawResponse,
    LLMResponse,
    LLMTimeoutError,
)

__all__ = [
    "complete",
    "acomplete",
    "LLMResponse",
    "LLMRawResponse",
    "LLMError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMAuthError",
    "LLMInvalidPromptError",
    "LLMBudgetExceededError",
]
