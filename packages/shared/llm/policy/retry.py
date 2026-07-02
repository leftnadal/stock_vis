"""정책: 지수 백오프 재시도. retries>0일 때만 활성.

베이스 패턴(rag llm_service 재시도 루프 + 지연 테이블)을 지수 백오프로 일반화.
RateLimit/Timeout만 재시도(베이스 #1 폴백 트리거 분류와 일관) — Auth/Invalid는 즉시 raise.
"""

from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, TypeVar

from packages.shared.llm.types import LLMRateLimitError, LLMTimeoutError

T = TypeVar("T")

_RETRYABLE = (LLMRateLimitError, LLMTimeoutError)


def with_retry(func: Callable[[], T], *, retries: int, backoff_base: float = 0.5) -> T:
    """func를 최대 retries회 재시도. 지수 백오프 `backoff_base * 2**attempt`.

    retries=0이면 1회 호출(재시도 없음). retryable 외 예외는 즉시 전파.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return func()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == retries:
                raise
            time.sleep(backoff_base * (2 ** attempt))
    assert last_exc is not None  # 도달 불가 — mypy 안심용
    raise last_exc


async def awith_retry(
    func: Callable[[], Awaitable[T]], *, retries: int, backoff_base: float = 0.5
) -> T:
    """with_retry의 async 동형 (슬라이스 ②b). 백오프는 asyncio.sleep.

    동일 정책: retries=0이면 1회, retryable(RateLimit/Timeout)만 재시도, 그 외 즉시 전파.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await func()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == retries:
                raise
            await asyncio.sleep(backoff_base * (2 ** attempt))
    assert last_exc is not None  # 도달 불가
    raise last_exc
