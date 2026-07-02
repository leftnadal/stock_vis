"""packages/shared/llm — 통합 LLM 코어 공유 타입.

베이스 #1 portfolio `LLMResponse`(추상화) + 베이스 #2 market_pulse `LLMRawResponse`(정책)
정합 흡수. 소비처 0 — 슬라이스 ① 신설, 기존 27 소비처 무변경.

예외 계층 = `apps/portfolio/llm/exceptions.py` 미러(폴백 트리거 분류 일관):
  - 폴백/재시도 트리거: LLMRateLimitError, LLMTimeoutError
  - raise(폴백 안 함):  LLMAuthError, LLMInvalidPromptError, LLMBudgetExceededError
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class LLMError(Exception):
    """LLM 코어 모든 예외의 베이스."""


class LLMRateLimitError(LLMError):
    """Rate limit → 폴백/재시도 트리거."""


class LLMTimeoutError(LLMError):
    """타임아웃 → 폴백/재시도 트리거."""


class LLMAuthError(LLMError):
    """인증 에러 → raise (폴백 안 함)."""


class LLMInvalidPromptError(LLMError):
    """프롬프트/파라미터 4xx → raise (폴백 안 함)."""


class LLMBudgetExceededError(LLMError):
    """비용 가드 임계 → raise (폴백 안 함)."""


@dataclass(frozen=True)
class LLMRawResponse:
    """provider.generate() 원시 반환 — cost 미계산.

    베이스 #2 `LLMRawResponse` 미러(토큰명만 base #1과 정합: prompt→input, completion→output).
    """

    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


@dataclass(frozen=True)
class LLMResponse:
    """complete() 통합 반환.

    베이스 #1 `LLMResponse` 미러 — 단, 도메인 필드(action_items)는 제외해 순수 유지.
    """

    text: str
    provider: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    fallback_from: Optional[str] = None


@dataclass(frozen=True)
class StreamDelta:
    """astream() 정규화 텍스트 조각 (ADR-LLM-001, provider-무관).

    순회 중 0개 이상 yield. §핀1·§핀4 실측: #12(gemini)·#8(anthropic) 공통으로
    "텍스트 델타 1개"가 스트림 단위 → text 단일 필드로 표준화.
    """

    text: str


@dataclass(frozen=True)
class StreamFinal:
    """astream() 종단 usage (ADR-LLM-001, provider-무관).

    스트림 종료 시 정확히 1개 yield(마지막). gemini=마지막 청크 usage_metadata,
    anthropic=get_final_message().usage — 위치가 provider마다 다른 것을 코어/provider가
    흡수해 단일 모양으로 노출. cache_tokens는 캐시 히트 토큰(미제공 provider는 0).
    """

    input_tokens: int
    output_tokens: int
    cache_tokens: int = 0
