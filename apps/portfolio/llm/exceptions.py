"""
LLM 호출 관련 예외 계층.

§1.2.1 폴백 트리거 분류:
  - 폴백 발동:  LLMRateLimitError, LLMTimeoutError
  - 폴백 안 함: LLMAuthError, LLMInvalidPromptError, LLMBudgetExceededError, 기타
"""

from __future__ import annotations

from typing import Literal, Optional

BudgetScope = Literal["instance", "slice"]


class LLMError(Exception):
    """LLM 호출 관련 모든 에러의 베이스."""


class LLMRateLimitError(LLMError):
    """Rate limit 초과 → 폴백 트리거."""


class LLMTimeoutError(LLMError):
    """타임아웃 → 폴백 트리거."""


class LLMAuthError(LLMError):
    """인증 에러 → raise (폴백 안 함)."""


class LLMInvalidPromptError(LLMError):
    """프롬프트/파라미터 잘못됨 (4xx) → raise (폴백 안 함)."""


class LLMBudgetExceededError(LLMError):
    """비용 가드 임계 도달 → raise (폴백 안 함).

    Slice 8 Part 1 #33: scope/count/limit 구조 인자 도입.
    backward-compat: message string 호출도 유지.

    Examples:
        # legacy
        raise LLMBudgetExceededError("Slice 3 budget exceeded: 50/50 calls")
        # Slice 8 (#33)
        raise LLMBudgetExceededError(scope="instance", count=51, limit=50)
    """

    def __init__(
        self,
        *args,
        scope: Optional[BudgetScope] = None,
        count: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        self.scope = scope
        self.count = count
        self.limit = limit
        if args:
            super().__init__(*args)
        elif scope is not None:
            super().__init__(f"LLM budget exceeded ({scope}): {count}/{limit}")
        else:
            super().__init__("LLM budget exceeded")


# Slice 8 Part 1 #33: 신규 호출자가 사용하는 alias.
# 지시서 §Step 0-1 "BudgetExceededError 정의" 충족.
BudgetExceededError = LLMBudgetExceededError
