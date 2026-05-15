"""Slice 7 Part 4 §12: #19 LLMClient.complete `system` 인자 분리 회귀.

KPI: system=None일 때 기존 동작 그대로 (IDENTICAL hash 보호) +
system=str일 때 Anthropic SDK 호출에 system 인자 전달.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

from portfolio.llm.client import LLMClient


def test_complete_accepts_system_kwarg():
    """LLMClient.complete가 `system` 인자를 받는다 (Slice 7 #19)."""
    sig = inspect.signature(LLMClient.complete)
    assert "system" in sig.parameters
    # 기본값은 None — 기존 호출자 영향 없음
    assert sig.parameters["system"].default is None


def test_call_anthropic_omits_system_when_none():
    """system=None이면 SDK 호출 kwargs에 'system' 키 없음 (IDENTICAL hash 보호)."""
    client_instance = LLMClient()
    captured: dict = {}

    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="ok")]
    fake_response.usage = MagicMock(input_tokens=10, output_tokens=5)

    fake_sdk = MagicMock()
    fake_sdk.messages.create = MagicMock(side_effect=lambda **kw: (captured.update(kw), fake_response)[1])

    with patch("portfolio.llm.client.Anthropic", return_value=fake_sdk):
        client_instance._call_anthropic(
            prompt="user only",
            max_tokens=100,
            start=0.0,
            model="claude-haiku-4-5",
            system=None,
        )

    assert "system" not in captured  # 기존 동작
    assert captured["messages"] == [{"role": "user", "content": "user only"}]


def test_call_anthropic_passes_system_when_provided():
    """system=str이면 SDK 호출 kwargs에 system 인자 별도 전달."""
    client_instance = LLMClient()
    captured: dict = {}

    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="ok")]
    fake_response.usage = MagicMock(input_tokens=10, output_tokens=5)

    fake_sdk = MagicMock()
    fake_sdk.messages.create = MagicMock(side_effect=lambda **kw: (captured.update(kw), fake_response)[1])

    with patch("portfolio.llm.client.Anthropic", return_value=fake_sdk):
        client_instance._call_anthropic(
            prompt="user question",
            max_tokens=100,
            start=0.0,
            model="claude-haiku-4-5",
            system="You are a portfolio coach",
        )

    assert captured["system"] == "You are a portfolio coach"
    assert captured["messages"] == [{"role": "user", "content": "user question"}]


def test_call_propagates_system_through_layers():
    """_call(provider='anthropic', system=str) → _call_anthropic(system=str) 전달."""
    client_instance = LLMClient()
    captured: dict = {}

    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="ok")]
    fake_response.usage = MagicMock(input_tokens=10, output_tokens=5)

    fake_sdk = MagicMock()
    fake_sdk.messages.create = MagicMock(side_effect=lambda **kw: (captured.update(kw), fake_response)[1])

    with patch("portfolio.llm.client.Anthropic", return_value=fake_sdk):
        client_instance._call(
            provider="anthropic",
            prompt="user",
            max_tokens=100,
            model="claude-haiku-4-5",
            system="SYS",
        )

    assert captured["system"] == "SYS"
