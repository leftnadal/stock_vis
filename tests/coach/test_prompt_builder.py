"""Slice 11 Part 3+4 — Prompt Builder 단위 테스트.

Part 3 (8 tests) + Part 4 확장 (+5 tests) = 12 tests.

테스트 항목 (Part 3, 일부 갱신):
1. Base.build_user_prompt abstract behavior (NotImplementedError)
2. E1 system prompt에 output schema JSON 포함
3. E1 user prompt가 portfolio_a2 fixture로 정상 생성
4. E1 build_messages = [system, user] 2개 반환
5. PROMPT_BUILDER_CLASSES dict 6 entry + Part 1/2 키 1:1 대응
6. (구) E2~E6 NotImplementedError — Part 4에서 의미 반전, **삭제**
7. E1 user prompt 결정성 (같은 input → 같은 output, stateless)
8. E1 ClassVar — entry_point/input_schema/output_schema 정합

Part 4 확장 (+5):
9. E2 builder build_messages portfolio_a2 정상 (sector_allocation 인용)
10. E3 builder build_messages portfolio_a2 정상 (concentration_metrics 인용)
11. E4 builder build_messages portfolio_a2 정상 (user_question 포함)
12. E5 builder build_messages portfolio_a2 정상 (time_series_context 포함)
13. E6 builder build_messages portfolio_a2 정상 (analysis_results 인용)
"""

from __future__ import annotations

import json

import pytest

from apps.portfolio.schemas.commentary_input import (
    COMMENTARY_INPUT_CLASSES,
    CommentaryInputE1,
    CommentaryInputE2,
    CommentaryInputE3,
    CommentaryInputE4,
    CommentaryInputE5,
    CommentaryInputE6,
)
from apps.portfolio.schemas.commentary_output import COMMENTARY_OUTPUT_CLASSES, E1Output
from apps.portfolio.services.coach.prompt_builder import (
    PROMPT_BUILDER_CLASSES,
    E1PromptBuilder,
    E2PromptBuilder,
    E3PromptBuilder,
    E4PromptBuilder,
    E5PromptBuilder,
    E6PromptBuilder,
    PromptBuilderBase,
)
from apps.portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input


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


# ============================================================
# Part 4 확장 — E2~E6 builder full implementation tests (+5)
# ============================================================


def test_e2_builder_builds_messages_with_sector_allocation():
    """E2 builder: portfolio_a2 fixture로 build_messages 정상, sector_allocation 인용."""
    inp = load_portfolio_a2_input("e2")
    assert isinstance(inp, CommentaryInputE2)
    msgs = E2PromptBuilder.build_messages(inp)
    assert len(msgs) == 2
    user = msgs[1]["content"]
    assert inp.portfolio_id in user
    assert "consumer_staples" in user  # sector_allocation 키 등장
    assert "8.2" in user  # portfolio_return_1y


def test_e3_builder_builds_messages_with_concentration_metrics():
    """E3 builder: hhi/top3_weight 등 concentration_metrics 인용."""
    inp = load_portfolio_a2_input("e3")
    assert isinstance(inp, CommentaryInputE3)
    msgs = E3PromptBuilder.build_messages(inp)
    user = msgs[1]["content"]
    assert "hhi" in user.lower()
    assert "top3" in user.lower() or "top3_weight" in user
    # system prompt에 action_items/risk_flags 슬롯 명시
    system = msgs[0]["content"]
    assert "action_items" in system
    assert "risk_flags" in system


def test_e4_builder_includes_user_question_only_base_fields():
    """E4 builder: user_question 포함, base만 사용 (action_items/risk_flags 슬롯 없음)."""
    inp = load_portfolio_a2_input("e4")
    assert isinstance(inp, CommentaryInputE4)
    msgs = E4PromptBuilder.build_messages(inp)
    user = msgs[1]["content"]
    assert inp.user_question in user
    # E4Output schema JSON properties는 base 3종만 (description 텍스트는 무관)
    system = msgs[0]["content"]
    schema_start = system.index("{")
    schema_json = json.loads(system[schema_start:])
    props = set(schema_json["properties"].keys())
    assert props == {"summary", "key_observations", "confidence"}, (
        f"E4 schema properties drift: {props}"
    )


def test_e5_builder_includes_time_series_context():
    """E5 builder: extraction_targets + time_series_context 포함."""
    inp = load_portfolio_a2_input("e5")
    assert isinstance(inp, CommentaryInputE5)
    msgs = E5PromptBuilder.build_messages(inp)
    user = msgs[1]["content"]
    # extraction_targets 키 일부 등장
    for tgt in inp.extraction_targets:
        assert tgt in user, f"extraction target {tgt} 누락"
    # time_series_context current/window_4q 값 등장 (3.45 / 3.30)
    assert "3.45" in user
    assert "3.30" in user


def test_e6_builder_includes_analysis_results():
    """E6 builder: 종목별 analysis_results 인용 (score/signals/notes)."""
    inp = load_portfolio_a2_input("e6")
    assert isinstance(inp, CommentaryInputE6)
    msgs = E6PromptBuilder.build_messages(inp)
    user = msgs[1]["content"]
    # 모든 종목 ticker가 analysis_results JSON에 등장
    for h in inp.holdings:
        assert h.ticker in user, f"{h.ticker} 누락"
    # signals 일부 등장
    assert "dividend_aristocrat" in user or "stable_yield" in user
