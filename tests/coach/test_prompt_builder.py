"""Slice 11 Part 3 — Prompt Builder 단위 테스트 (Step 4).

KPI 4 — 8/8 PASS.

테스트 항목:
1. Base.build_user_prompt abstract behavior (NotImplementedError)
2. E1 system prompt에 output schema JSON 포함
3. E1 user prompt가 portfolio_a2 fixture로 정상 생성
4. E1 build_messages = [system, user] 2개 반환
5. PROMPT_BUILDER_CLASSES dict 6 entry + Part 1/2 키 1:1 대응
6. E2~E6 sub builder build_user_prompt → NotImplementedError (Part 4 예정)
7. E1 user prompt 결정성 (같은 input → 같은 output, stateless)
8. E1 ClassVar — entry_point/input_schema/output_schema 정합
"""

from __future__ import annotations

import json

import pytest

from portfolio.schemas.commentary_input import (
    COMMENTARY_INPUT_CLASSES,
    CommentaryInputE1,
)
from portfolio.schemas.commentary_output import COMMENTARY_OUTPUT_CLASSES, E1Output
from portfolio.services.coach.prompt_builder import (
    PROMPT_BUILDER_CLASSES,
    E1PromptBuilder,
    E2PromptBuilder,
    E3PromptBuilder,
    E4PromptBuilder,
    E5PromptBuilder,
    E6PromptBuilder,
    PromptBuilderBase,
)
from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input


@pytest.fixture(scope="module")
def e1_input() -> CommentaryInputE1:
    inp = load_portfolio_a2_input("e1")
    assert isinstance(inp, CommentaryInputE1)
    return inp


def test_base_build_user_prompt_raises_not_implemented():
    """Base는 abstract — build_user_prompt 호출 시 NotImplementedError."""
    with pytest.raises(NotImplementedError) as exc_info:
        PromptBuilderBase.build_user_prompt(input_data=None)
    assert "sub class" in str(exc_info.value).lower() or "구현" in str(exc_info.value)


def test_e1_system_prompt_includes_output_schema_json():
    """E1 system prompt에 E1Output JSON schema 명시."""
    system = E1PromptBuilder.build_system_prompt()
    # output schema의 키 필드가 system에 등장해야 함
    assert "summary" in system
    assert "confidence" in system
    assert "action_items" in system
    assert "metrics_table" in system
    # JSON schema 구조 (properties)
    assert "properties" in system


def test_e1_user_prompt_includes_portfolio_data(e1_input):
    """E1 user prompt에 portfolio_a2 fixture 데이터 반영."""
    user = E1PromptBuilder.build_user_prompt(e1_input)
    assert e1_input.portfolio_id in user
    assert "income" in user  # preset
    # 5종 holdings 모두 등장
    for h in e1_input.holdings:
        assert h.ticker in user, f"{h.ticker} 누락"
    # garp_metrics 일부 키 등장
    assert "per" in user.lower() or "PER" in user
    assert "roe" in user.lower() or "ROE" in user


def test_e1_build_messages_returns_two_messages(e1_input):
    """build_messages = [system, user] 2개 메시지."""
    msgs = E1PromptBuilder.build_messages(e1_input)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[0]["content"]  # 비어있지 않음
    assert msgs[1]["content"]


def test_prompt_builder_classes_registry_matches_part1_and_part2():
    """PROMPT_BUILDER_CLASSES dict 6 entry + Part 1/2 키 1:1 대응."""
    assert set(PROMPT_BUILDER_CLASSES) == {"e1", "e2", "e3", "e4", "e5", "e6"}
    assert set(PROMPT_BUILDER_CLASSES) == set(COMMENTARY_INPUT_CLASSES)
    assert set(PROMPT_BUILDER_CLASSES) == set(COMMENTARY_OUTPUT_CLASSES)
    # entry_point ClassVar 정합
    for ep, builder_cls in PROMPT_BUILDER_CLASSES.items():
        assert builder_cls.entry_point == ep, f"{builder_cls.__name__} mismatch"


def test_e2_to_e6_skeletons_raise_not_implemented(e1_input):
    """E2~E6 build_user_prompt → NotImplementedError (Part 4 메시지)."""
    for cls in (E2PromptBuilder, E3PromptBuilder, E4PromptBuilder,
                E5PromptBuilder, E6PromptBuilder):
        with pytest.raises(NotImplementedError) as exc_info:
            cls.build_user_prompt(input_data=e1_input)
        msg = str(exc_info.value)
        assert "Part 4" in msg


def test_e1_user_prompt_deterministic(e1_input):
    """E1 user prompt는 결정적 — 같은 input → 같은 output (stateless)."""
    p1 = E1PromptBuilder.build_user_prompt(e1_input)
    p2 = E1PromptBuilder.build_user_prompt(e1_input)
    assert p1 == p2


def test_e1_classvar_schema_alignment():
    """E1 ClassVar — entry_point/input_schema/output_schema 정합."""
    assert E1PromptBuilder.entry_point == "e1"
    assert E1PromptBuilder.input_schema is CommentaryInputE1
    assert E1PromptBuilder.output_schema is E1Output
