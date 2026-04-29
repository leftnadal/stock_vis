"""
Mock LLMClient — 5케이스 결정론적 시뮬레이션.

§7.1: LLMClient 인터페이스 호환. mode별 동작:
  - "normal":            정상 (Gemini 첫 시도 성공)
  - "rate_limit_first":  Gemini RateLimit → Anthropic 폴백 성공
  - "timeout_first":     Gemini Timeout    → Anthropic 폴백 성공
  - "auth_error":        Gemini AuthError → 폴백 안 함, raise
  - "budget_exceeded":   호출 즉시 LLMBudgetExceededError
"""

from __future__ import annotations

import json
from typing import Literal

from portfolio.llm.exceptions import (
    LLMAuthError,
    LLMBudgetExceededError,
)
from portfolio.schemas.llm import LLMResponse


# OneLineDiagnosis 스키마(headline 10~60자, summary 30~500자)를 통과하는 결정론적 Mock 응답.
_MOCK_DIAGNOSIS = {
    "headline": "GARP 적합도 양호, 밸류에이션 부담 일부",
    "summary": (
        "5개 종목 중 4개가 ROIC 산업 상위 25% 이내이며 EPS 성장도 견조합니다. "
        "다만 PEG 평균이 프리셋 기준 1.5를 상회해 성장 둔화 시 조정 리스크가 잠재합니다."
    ),
}
_MOCK_TEXT = json.dumps(_MOCK_DIAGNOSIS, ensure_ascii=False)


MockMode = Literal[
    "normal",
    "rate_limit_first",
    "timeout_first",
    "auth_error",
    "budget_exceeded",
]


class MockLLMClient:
    """LLMClient 호환 Mock. 모드별로 폴백/에러/가드를 결정론적으로 시뮬레이션."""

    def __init__(self, mode: MockMode = "normal") -> None:
        self.mode: MockMode = mode
        self._call_count: int = 0

    def complete(
        self,
        prompt: str,  # noqa: ARG002 (Mock은 prompt 사용 안 함)
        provider: Literal["gemini", "anthropic"] = "gemini",
        max_tokens: int = 2000,  # noqa: ARG002
        model: str | None = None,  # LLMClient 시그니처 호환 (Sonnet/Haiku 분기, Mock은 무시)  # noqa: ARG002
    ) -> LLMResponse:
        self._call_count += 1

        if self.mode == "budget_exceeded":
            raise LLMBudgetExceededError("Mock 가드 발동: budget_exceeded mode")

        if self.mode == "auth_error":
            raise LLMAuthError("Mock 인증 실패: auth_error mode")

        if self.mode in ("rate_limit_first", "timeout_first") and provider == "gemini":
            # 폴백 결과만 흉내 (실제 retry는 LLMClient가 담당, Mock에서는 결과만)
            return self._mock_response(provider="anthropic", fallback_from="gemini")

        # normal — 또는 anthropic 직접 호출
        return self._mock_response(provider=provider, fallback_from=None)

    # ------------------------------------------------------------

    def _mock_response(
        self,
        provider: Literal["gemini", "anthropic"],
        fallback_from: Literal["gemini", "anthropic"] | None,
    ) -> LLMResponse:
        return LLMResponse(
            text=_MOCK_TEXT,
            provider=provider,
            model=f"mock-{provider}",
            latency_ms=100,
            input_tokens=500,
            output_tokens=50,
            cost_usd=0.001,
            fallback_from=fallback_from,
        )
