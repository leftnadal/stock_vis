"""E4 prompt builder 회귀 (Slice 7 Part 3 §2)."""

from __future__ import annotations

import json
from pathlib import Path

from apps.portfolio.prompts.e4.builder import (
    SYSTEM_PROMPT,
    build_e4_messages,
    build_e4_prompt,
    build_e4_user_prompt,
    get_system_prompt,
)
from apps.portfolio.schemas.e4_conversation import E4ConversationInput

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "e4_conversation"


def _load_fixture(stem: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{stem}.json").read_text(encoding="utf-8"))


def test_system_prompt_non_empty():
    assert len(SYSTEM_PROMPT) > 100
    assert "JSON" in SYSTEM_PROMPT
    assert "referenced_metrics" in SYSTEM_PROMPT


def test_user_prompt_tier1_baseline():
    data = _load_fixture("S01_V1_tier1")
    inp = E4ConversationInput(**data["input"])
    prompt = build_e4_user_prompt(inp)
    assert "포트폴리오 정보" in prompt
    assert "현재 질문" in prompt
    assert "이전 대화" not in prompt
    assert data["input"]["current_user_question"] in prompt


def test_user_prompt_tier2_includes_history():
    data = _load_fixture("S02_V1_tier2")
    inp = E4ConversationInput(**data["input"])
    prompt = build_e4_user_prompt(inp)
    assert "이전 대화" in prompt
    assert "[사용자]" in prompt and "[어시스턴트]" in prompt


def test_user_prompt_i1_history_truncation():
    """S12: history 6 turn → max_history_turns=5 적용으로 5개로 truncate."""
    data = _load_fixture("S12_V1_tier2_overflow")
    inp = E4ConversationInput(**data["input"])
    prompt = build_e4_user_prompt(inp)
    history_lines = [
        line
        for line in prompt.split("\n")
        if line.startswith("[사용자]") or line.startswith("[어시스턴트]")
    ]
    assert len(history_lines) == 5, f"expected 5 lines, got {len(history_lines)}"


def test_full_prompt_includes_system_and_user():
    data = _load_fixture("S01_V1_tier1")
    inp = E4ConversationInput(**data["input"])
    full = build_e4_prompt(inp)
    assert SYSTEM_PROMPT in full
    assert "현재 질문" in full
    assert len(full) > len(SYSTEM_PROMPT) + 100


def test_messages_structure():
    data = _load_fixture("S01_V1_tier1")
    inp = E4ConversationInput(**data["input"])
    msgs = build_e4_messages(inp)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[0]["content"] == SYSTEM_PROMPT


def test_get_system_prompt_returns_const():
    assert get_system_prompt() == SYSTEM_PROMPT


def test_prompt_contains_metric_keys():
    """portfolio_metrics dict의 key가 prompt에 인용됨."""
    data = _load_fixture("S04_V2_tier1")
    inp = E4ConversationInput(**data["input"])
    prompt = build_e4_user_prompt(inp)
    for key in inp.portfolio_metrics:
        assert key in prompt, f"metric key '{key}' missing from prompt"
