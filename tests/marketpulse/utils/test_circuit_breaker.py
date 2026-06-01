"""Tests for marketpulse.utils.circuit_breaker."""
from __future__ import annotations

import time

import pytest
from django.core.cache import cache

from packages.shared.api_request.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    get_circuit,
)


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    from packages.shared.api_request import circuit_breaker as cb_mod
    cb_mod._REGISTRY.clear()
    yield
    cache.clear()
    cb_mod._REGISTRY.clear()


class TestBasics:
    def test_call_success(self):
        cb = CircuitBreaker('t', retry_attempts=1)
        assert cb.call(lambda: 42) == 42
        assert cb.get_state() == CircuitState.CLOSED

    def test_get_circuit_singleton(self):
        a = get_circuit('foo')
        b = get_circuit('foo')
        assert a is b


class TestStateTransitions:
    def test_5_failures_open(self):
        cb = CircuitBreaker('o5', failure_threshold=5, retry_attempts=1)
        for _ in range(5):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        assert cb.get_state() == CircuitState.OPEN

    def test_open_blocks_calls(self):
        cb = CircuitBreaker('blk', failure_threshold=2, retry_attempts=1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: 'unreached')

    def test_open_to_half_open(self):
        cb = CircuitBreaker('rec', failure_threshold=2, recovery_seconds=1, retry_attempts=1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        cache.set('cb:opened_at:rec', time.time() - 5, timeout=None)
        assert cb.get_state() == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker('hok', failure_threshold=2, recovery_seconds=1, retry_attempts=1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        cache.set('cb:opened_at:hok', time.time() - 5, timeout=None)
        assert cb.call(lambda: 'ok') == 'ok'
        assert cb.get_state() == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker('hf', failure_threshold=2, recovery_seconds=1, retry_attempts=1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        cache.set('cb:opened_at:hf', time.time() - 5, timeout=None)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError('y')))
        assert cb.get_state() == CircuitState.OPEN

    def test_reset(self):
        cb = CircuitBreaker('rst', failure_threshold=2, retry_attempts=1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        assert cb.get_state() == CircuitState.OPEN
        cb.reset()
        assert cb.get_state() == CircuitState.CLOSED


class TestSuccessResetsCount:
    def test_partial_failure_then_success(self):
        cb = CircuitBreaker('p', failure_threshold=5, retry_attempts=1)
        for _ in range(4):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        assert cache.get('cb:fail_count:p') == 4
        cb.call(lambda: 'ok')
        assert cache.get('cb:fail_count:p') == 0
        assert cb.get_state() == CircuitState.CLOSED


class TestRetryWrapper:
    def test_retries_then_succeeds(self):
        cb = CircuitBreaker('rt', retry_attempts=3)
        calls = {'n': 0}

        def flaky():
            calls['n'] += 1
            if calls['n'] < 3:
                raise RuntimeError('transient')
            return 'ok'

        assert cb.call(flaky) == 'ok'
        assert cb.get_state() == CircuitState.CLOSED

    def test_retries_exhausted_one_failure(self):
        cb = CircuitBreaker('rf', failure_threshold=5, retry_attempts=2)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError('boom')))
        assert cache.get('cb:fail_count:rf') == 1
