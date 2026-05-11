"""E4 conversation schema 회귀 (Slice 7 Part 2 §1)."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from portfolio.schemas.e4_conversation import (
    E4ConversationInput,
    E4ConversationMetadata,
    E4ConversationOutput,
    E4ConversationTurn,
)


# ===== Turn =====


def test_turn_valid():
    t = E4ConversationTurn(
        role="user",
        content="내 포트폴리오 집중도가 높아?",
        timestamp=datetime(2026, 5, 11, 10, 0, 0),
        turn_idx=0,
    )
    assert t.role == "user"
    assert t.turn_idx == 0


def test_turn_content_empty_rejected():
    with pytest.raises(ValidationError):
        E4ConversationTurn(
            role="user",
            content="",
            timestamp=datetime.now(),
            turn_idx=0,
        )


def test_turn_invalid_role_rejected():
    with pytest.raises(ValidationError):
        E4ConversationTurn(
            role="system",
            content="hi",
            timestamp=datetime.now(),
            turn_idx=0,
        )


def test_turn_frozen():
    t = E4ConversationTurn(
        role="user",
        content="hi",
        timestamp=datetime.now(),
        turn_idx=0,
    )
    with pytest.raises(ValidationError):
        t.role = "assistant"  # frozen


# ===== Input =====


def _base_input_kwargs():
    return dict(
        portfolio_id="p_001",
        preset_id="V1_garp",
        portfolio_metrics={
            "hhi_concentration": 0.45,
            "sector_hhi": 0.50,
            "top3_weight": 0.65,
            "holding_count": 5,
            "portfolio_beta": 1.10,
            "max_position_weight": 0.30,
            "avg_correlation": 0.40,
        },
        holdings_summary="Tech 50%, Healthcare 30%, Financials 20%. Top 3: AAPL/MSFT/NVDA.",
        current_user_question="내 포트폴리오 집중도가 높아?",
        tier=1,
        session_id="s_001",
    )


def test_input_tier1_no_history_ok():
    inp = E4ConversationInput(conversation_history=[], **_base_input_kwargs())
    assert inp.tier == 1
    assert inp.max_history_turns == 5


def test_input_tier2_empty_history_rejected():
    """I2 분기 사전 차단: tier=2/3 + history 비어있음 → ValueError."""
    kwargs = _base_input_kwargs()
    kwargs["tier"] = 2
    with pytest.raises(ValidationError) as exc:
        E4ConversationInput(conversation_history=[], **kwargs)
    assert "non-empty conversation_history" in str(exc.value)


def test_input_tier3_with_history_ok():
    history = [
        E4ConversationTurn(role="user", content="Q1", timestamp=datetime.now(), turn_idx=0),
        E4ConversationTurn(
            role="assistant",
            content="A1 답변 내용 (20자 이상 필요).",
            timestamp=datetime.now(),
            turn_idx=1,
        ),
    ]
    kwargs = _base_input_kwargs()
    kwargs["tier"] = 3
    inp = E4ConversationInput(conversation_history=history, **kwargs)
    assert len(inp.conversation_history) == 2


def test_input_max_history_turns_bounds():
    """max_history_turns 0~20 강제."""
    kwargs = _base_input_kwargs()
    with pytest.raises(ValidationError):
        E4ConversationInput(
            conversation_history=[],
            max_history_turns=21,
            **kwargs,
        )


# ===== Output =====


def _base_output_kwargs():
    return dict(
        answer="포트폴리오 hhi_concentration 0.45는 중간 집중도이며 분산 검토를 권장합니다.",
        referenced_metrics=["hhi_concentration", "sector_hhi"],
        follow_up_suggestions=["어떻게 분산하나요?", "추가 종목 추천"],
        confidence="medium",
    )


def test_output_valid():
    out = E4ConversationOutput(**_base_output_kwargs())
    assert out.confidence == "medium"
    assert len(out.referenced_metrics) == 2


def test_output_answer_too_short_rejected():
    kwargs = _base_output_kwargs()
    kwargs["answer"] = "짧음"
    with pytest.raises(ValidationError):
        E4ConversationOutput(**kwargs)


def test_output_referenced_metrics_non_snake_case_rejected():
    """I4 사전 체크: snake_case 위반."""
    kwargs = _base_output_kwargs()
    kwargs["referenced_metrics"] = ["HHI Concentration"]
    with pytest.raises(ValidationError) as exc:
        E4ConversationOutput(**kwargs)
    assert "snake_case" in str(exc.value)


def test_output_follow_up_max_3():
    kwargs = _base_output_kwargs()
    kwargs["follow_up_suggestions"] = ["q1", "q2", "q3", "q4"]
    with pytest.raises(ValidationError):
        E4ConversationOutput(**kwargs)


def test_output_confidence_low():
    kwargs = _base_output_kwargs()
    kwargs["confidence"] = "low"
    out = E4ConversationOutput(**kwargs)
    assert out.confidence == "low"


# ===== Metadata =====


def test_metadata_default_empty():
    m = E4ConversationMetadata()
    assert m.case_flags == []
    assert m.history_truncated is False
    assert m.tier_downgraded_from is None
    assert m.hallucinated_metrics == []


def test_metadata_i1_flag():
    m = E4ConversationMetadata(case_flags=["I1"], history_truncated=True)
    assert "I1" in m.case_flags
    assert m.history_truncated is True


def test_metadata_i2_downgrade_trace():
    m = E4ConversationMetadata(case_flags=["I2"], tier_downgraded_from=3)
    assert m.tier_downgraded_from == 3


def test_metadata_i4_hallucination_trace():
    m = E4ConversationMetadata(
        case_flags=["I4"],
        hallucinated_metrics=["nonexistent_metric"],
    )
    assert m.hallucinated_metrics == ["nonexistent_metric"]


# ===== token_budgets 연동 =====


def test_token_budgets_e4_tier1_2_3_registered():
    from portfolio.llm.token_budgets import ENTRYPOINT_TOKEN_BUDGETS, get_token_budget

    for key in ("e4_conversation_tier1", "e4_conversation_tier2", "e4_conversation_tier3"):
        assert key in ENTRYPOINT_TOKEN_BUDGETS
        assert get_token_budget(key) > 0

    # Tier가 올라갈수록 budget 증가
    t1 = get_token_budget("e4_conversation_tier1")
    t2 = get_token_budget("e4_conversation_tier2")
    t3 = get_token_budget("e4_conversation_tier3")
    assert t1 < t2 < t3
