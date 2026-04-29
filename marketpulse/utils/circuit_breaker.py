"""Market Pulse v2 — Circuit Breaker (PR-B)."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from django.core.cache import cache
from tenacity import (
    Retrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class CircuitState:
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'


class CircuitBreakerError(Exception):
    def __init__(self, name: str, opened_at: float) -> None:
        super().__init__(f'circuit_breaker[{name}] OPEN (opened_at={opened_at})')
        self.name = name
        self.opened_at = opened_at


class CircuitBreaker:
    STATE_KEY = 'cb:state:{name}'
    FAIL_COUNT_KEY = 'cb:fail_count:{name}'
    OPENED_AT_KEY = 'cb:opened_at:{name}'

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_seconds: int = 60,
        retry_attempts: int = 3,
        retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.retry_attempts = retry_attempts
        self.retry_exceptions = retry_exceptions

    def _state_key(self) -> str: return self.STATE_KEY.format(name=self.name)
    def _fail_count_key(self) -> str: return self.FAIL_COUNT_KEY.format(name=self.name)
    def _opened_at_key(self) -> str: return self.OPENED_AT_KEY.format(name=self.name)

    def get_state(self) -> str:
        state = cache.get(self._state_key(), CircuitState.CLOSED)
        if state == CircuitState.OPEN:
            opened_at = cache.get(self._opened_at_key(), 0.0)
            if time.time() - float(opened_at) >= self.recovery_seconds:
                cache.set(self._state_key(), CircuitState.HALF_OPEN, timeout=None)
                return CircuitState.HALF_OPEN
        return state

    def _set_open(self) -> None:
        cache.set(self._state_key(), CircuitState.OPEN, timeout=None)
        cache.set(self._opened_at_key(), time.time(), timeout=None)
        cache.set(self._fail_count_key(), 0, timeout=None)
        logger.warning('circuit_breaker[%s] → OPEN', self.name)

    def _set_closed(self) -> None:
        cache.set(self._state_key(), CircuitState.CLOSED, timeout=None)
        cache.set(self._fail_count_key(), 0, timeout=None)
        cache.delete(self._opened_at_key())

    def reset(self) -> None:
        self._set_closed()

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        state = self.get_state()
        if state == CircuitState.OPEN:
            opened_at = cache.get(self._opened_at_key(), 0.0)
            raise CircuitBreakerError(self.name, float(opened_at))

        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self.retry_attempts),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                retry=retry_if_exception_type(self.retry_exceptions),
                reraise=True,
            ):
                with attempt:
                    result = func(*args, **kwargs)
        except RetryError as exc:
            self._record_failure()
            raise exc.last_attempt.exception() from exc
        except self.retry_exceptions as exc:
            self._record_failure()
            raise exc

        self._record_success()
        return result

    def _record_success(self) -> None:
        state = cache.get(self._state_key(), CircuitState.CLOSED)
        if state == CircuitState.HALF_OPEN:
            self._set_closed()
        else:
            cache.set(self._fail_count_key(), 0, timeout=None)

    def _record_failure(self) -> None:
        state = cache.get(self._state_key(), CircuitState.CLOSED)
        if state == CircuitState.HALF_OPEN:
            self._set_open()
            return
        added = cache.add(self._fail_count_key(), 1, timeout=None)
        if added:
            count = 1
        else:
            try:
                count = cache.incr(self._fail_count_key())
            except ValueError:
                cache.set(self._fail_count_key(), 1, timeout=None)
                count = 1
        if count >= self.failure_threshold:
            self._set_open()


_REGISTRY: dict[str, CircuitBreaker] = {}


def get_circuit(
    name: str,
    failure_threshold: int = 5,
    recovery_seconds: int = 60,
    retry_attempts: int = 3,
) -> CircuitBreaker:
    cb = _REGISTRY.get(name)
    if cb is None:
        cb = CircuitBreaker(name, failure_threshold, recovery_seconds, retry_attempts)
        _REGISTRY[name] = cb
    return cb
