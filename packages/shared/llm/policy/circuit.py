"""정책: circuit breaker 결합. circuit 인자 있을 때만 활성.

shared 토대 `get_circuit`(packages/shared/api_request/circuit_breaker) 재사용 — 베이스 #2 패턴.
이름별 CB 인스턴스가 failure_threshold/recovery/retry_attempts를 관리(tenacity 기반).
"""

from __future__ import annotations

from typing import Callable, TypeVar

from packages.shared.api_request.circuit_breaker import get_circuit

T = TypeVar("T")


def with_circuit(func: Callable[[], T], *, name: str) -> T:
    """func를 named circuit breaker로 감싸 호출."""
    cb = get_circuit(name)
    return cb.call(func)
