"""
Mock LLMClient — 5케이스 결정론적 시뮬레이션 + 진입점별 text strategy.

§7.1: LLMClient 인터페이스 호환. mode별 동작:
  - "normal":            정상 (Gemini 첫 시도 성공)
  - "rate_limit_first":  Gemini RateLimit → Anthropic 폴백 성공
  - "timeout_first":     Gemini Timeout    → Anthropic 폴백 성공
  - "auth_error":        Gemini AuthError → 폴백 안 함, raise
  - "budget_exceeded":   호출 즉시 LLMBudgetExceededError

text_strategy 옵션 (Slice 2 Step 0.5 도입):
  - "e1": OneLineDiagnosis JSON (default — Slice 1 호환)
  - "e5": E5Response JSON (Slice 2 Part 1)
  Slice 3 진입 시 진입점별로 추가.
"""

from __future__ import annotations

import json
from typing import Callable, Literal

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
_MOCK_TEXT_E1 = json.dumps(_MOCK_DIAGNOSIS, ensure_ascii=False)


def _mock_text_e1(prompt: str) -> str:  # noqa: ARG001
    """E1 진입점: OneLineDiagnosis schema 통과 JSON."""
    return _MOCK_TEXT_E1


def _mock_text_e5(prompt: str) -> str:  # noqa: ARG001
    """E5 진입점: E5Response schema 통과 JSON (TSLA decrease 단일 항목)."""
    return (
        '{"adjustments":[{"ticker":"TSLA","action":"decrease",'
        '"delta_weight":-0.05,"target_weight":null,'
        '"reason_quote":"TSLA 줄여줘"}],'
        '"confidence":4,"ambiguity_notes":null,'
        '"no_actionable_intent":false}'
    )


_MOCK_TEXT_STRATEGIES: dict[str, Callable[[str], str]] = {
    "e1": _mock_text_e1,
    "e5": _mock_text_e5,
}


MockMode = Literal[
    "normal",
    "rate_limit_first",
    "timeout_first",
    "auth_error",
    "budget_exceeded",
]


class MockLLMClient:
    """LLMClient 호환 Mock. 모드별로 폴백/에러/가드를 결정론적으로 시뮬레이션.

    Args:
        mode: 폴백/에러/가드 시나리오 (5개)
        text_strategy: 진입점별 응답 텍스트 (default "e1", Slice 1 호환)
    """

    def __init__(
        self,
        mode: MockMode = "normal",
        text_strategy: str = "e1",
    ) -> None:
        if text_strategy not in _MOCK_TEXT_STRATEGIES:
            raise ValueError(
                f"Unknown text_strategy: {text_strategy!r}. "
                f"Available: {list(_MOCK_TEXT_STRATEGIES)}"
            )
        self.mode: MockMode = mode
        self._call_count: int = 0
        self._text_fn: Callable[[str], str] = _MOCK_TEXT_STRATEGIES[text_strategy]

    def complete(
        self,
        prompt: str,
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
            return self._mock_response(prompt, provider="anthropic", fallback_from="gemini")

        # normal — 또는 anthropic 직접 호출
        return self._mock_response(prompt, provider=provider, fallback_from=None)

    # ------------------------------------------------------------

    def _mock_response(
        self,
        prompt: str,
        provider: Literal["gemini", "anthropic"],
        fallback_from: Literal["gemini", "anthropic"] | None,
    ) -> LLMResponse:
        return LLMResponse(
            text=self._text_fn(prompt),
            provider=provider,
            model=f"mock-{provider}",
            latency_ms=100,
            input_tokens=500,
            output_tokens=50,
            cost_usd=0.001,
            fallback_from=fallback_from,
        )
