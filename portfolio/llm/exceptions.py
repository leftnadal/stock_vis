"""
LLM 호출 관련 예외 계층.

§1.2.1 폴백 트리거 분류:
  - 폴백 발동:  LLMRateLimitError, LLMTimeoutError
  - 폴백 안 함: LLMAuthError, LLMInvalidPromptError, LLMBudgetExceededError, 기타
"""

from __future__ import annotations


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
    """비용 가드 임계 도달 → raise (폴백 안 함)."""
