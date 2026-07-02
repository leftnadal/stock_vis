"""슬라이스 ④ #3 estimator_v3 count_tokens → 코어 util 이관 — wire IDENTICAL.

직접 Anthropic().messages.count_tokens → 코어 count_tokens(provider="anthropic").
messages(list)+system kwargs byte 동일(잉여키 0), .input_tokens int 반환 동일.
cache·fallback은 소비자(estimator) 소유(행위보존). SDK 예외 → fallback 트리거 보존.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.portfolio.measure import estimator_v3 as e3


@contextlib.contextmanager
def _anthropic(client):
    """코어 provider가 생성하는 anthropic.Anthropic을 mock으로 치환 + 키 해소."""
    with patch("anthropic.Anthropic", return_value=client), patch(
        "packages.shared.llm.providers.anthropic._resolve_api_key",
        return_value="fake-key",
    ):
        yield


def _client(input_tokens: int = 123, raise_exc: Exception | None = None) -> MagicMock:
    c = MagicMock()
    if raise_exc:
        c.messages.count_tokens.side_effect = raise_exc
    else:
        c.messages.count_tokens.return_value = SimpleNamespace(
            input_tokens=input_tokens
        )
    return c


@pytest.fixture(autouse=True)
def _reset():
    e3.reset_cache()
    yield
    e3.reset_cache()


def test_core_count_tokens_wire_and_return():
    """코어 count_tokens kwargs = 원본(model·messages·system, 잉여키 0) + .input_tokens int."""
    from packages.shared.llm import count_tokens

    c = _client(input_tokens=456)
    msgs = [{"role": "user", "content": "hi"}]
    with _anthropic(c):
        out = count_tokens(
            msgs, provider="anthropic", model="claude-haiku-4-5", system="sys"
        )
    assert out == 456
    kw = c.messages.count_tokens.call_args.kwargs
    assert kw == {"model": "claude-haiku-4-5", "messages": msgs, "system": "sys"}


def test_core_count_tokens_omits_system_when_none():
    """system=None이면 count_tokens kwargs에 'system' 키 없음(원본 동형, 잉여키 0)."""
    from packages.shared.llm import count_tokens

    c = _client(input_tokens=1)
    with _anthropic(c):
        count_tokens(
            [{"role": "user", "content": "x"}],
            provider="anthropic",
            model="claude-haiku-4-5",
        )
    kw = c.messages.count_tokens.call_args.kwargs
    assert set(kw) == {"model", "messages"}


def test_estimator_uses_core_and_caches():
    """estimator가 코어 경유 int 반환 + 동일 입력 cache hit(API 1회)."""
    c = _client(input_tokens=42)
    msgs = [{"role": "user", "content": "동일"}]
    with _anthropic(c):
        r1 = e3.estimate_input_tokens(msgs, system="s")
        r2 = e3.estimate_input_tokens(msgs, system="s")
    assert r1 == r2 == 42
    assert c.messages.count_tokens.call_count == 1
    assert e3.cache_stats()["size"] == 1


def test_estimator_fallback_on_exception(caplog):
    """API 예외(코어 분류) → v2 char/3 fallback + warn log(행위보존)."""
    c = _client(raise_exc=RuntimeError("rate limit"))
    with _anthropic(c):
        with caplog.at_level("WARNING"):
            result = e3.estimate_input_tokens(
                [{"role": "user", "content": "안녕하세요 한국어 텍스트"}], system=None
            )
    assert result > 0
    assert any("fallback to v2" in r.message for r in caplog.records)
