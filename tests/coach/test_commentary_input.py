"""Slice 11 Part 1 — CommentaryInputBase + 6 sub class + fixture mapping 검증.

KPI (Part 1 §6):
- CommentaryInputBase 4 필드 (portfolio_id/fetched_at/preset/entry_point) + holdings
- frozen + extra=forbid 동작
- 6 sub class (E1~E6) 정의 + discriminator 일관
- Holding 공통 type 1회 정의 + 6 sub class 재사용
- portfolio_a2 fixture → 6 schema validate 100%
- preset enum 5종 (income 포함)

테스트 10건.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from apps.portfolio.schemas.commentary_input import (
    COMMENTARY_INPUT_CLASSES,
    CommentaryInputBase,
    CommentaryInputE1,
    CommentaryInputE2,
    CommentaryInputE3,
    CommentaryInputE4,
    CommentaryInputE5,
    CommentaryInputE6,
    Holding,
)
from apps.portfolio.tests.fixtures.coach.loaders import (
    load_portfolio_a2_all_inputs,
    load_portfolio_a2_input,
    load_portfolio_a2_raw,
)


def _holding(ticker: str = "AAPL", weight: float = 1.0) -> Holding:
    return Holding(ticker=ticker, weight=weight)


def _e1_payload(**overrides) -> dict:
    base = {
        "portfolio_id": "pf_test",
        "fetched_at": datetime(2026, 5, 18, tzinfo=timezone.utc),
        "preset": "income",
        "holdings": [_holding()],
        "garp_metrics": {"AAPL": {"per": 20.0}},
    }
    base.update(overrides)
    return base


# ============================================================
# §1 Base
# ============================================================


def test_base_required_fields_and_preset_enum():
    """필수 필드 (portfolio_id/fetched_at/preset/holdings) + preset enum 5종.

    preset enum 5종: garp/focused/income/growth/factor (Slice 11 income 추가).
    """
    # 정상 instantiate
    inst = CommentaryInputE1(**_e1_payload())
    assert inst.portfolio_id == "pf_test"
    assert inst.preset == "income"
    assert inst.entry_point == "e1"
    # preset 5종 모두 허용
    for p in ("garp", "focused", "income", "growth", "factor"):
        ok = CommentaryInputE1(**_e1_payload(preset=p))
        assert ok.preset == p
    # 미등록 preset → ValidationError
    with pytest.raises(ValidationError):
        CommentaryInputE1(**_e1_payload(preset="invalid_preset"))


def test_base_frozen_immutability():
    """frozen=True → instantiate 후 필드 변경 불가."""
    inst = CommentaryInputE1(**_e1_payload())
    with pytest.raises(ValidationError):
        inst.portfolio_id = "changed"


def test_base_extra_forbid_rejects_unknown_fields():
    """extra='forbid' → 정의되지 않은 필드 거부 (schema drift 즉시 검출)."""
    with pytest.raises(ValidationError) as exc_info:
        CommentaryInputE1(**_e1_payload(unknown_field="x"))
    assert "extra" in str(exc_info.value).lower() or "forbid" in str(exc_info.value).lower()


# ============================================================
# §2 Holding + 6 sub class
# ============================================================


def test_holding_validates_weight_and_ticker():
    """Holding 공통 type — weight 0~1 / ticker 길이 / asset_class enum."""
    Holding(ticker="AAPL", weight=0.5)
    with pytest.raises(ValidationError):
        Holding(ticker="AAPL", weight=1.5)  # > 1.0
    with pytest.raises(ValidationError):
        Holding(ticker="AAPL", weight=-0.1)  # < 0
    with pytest.raises(ValidationError):
        Holding(ticker="", weight=0.5)  # empty ticker
    with pytest.raises(ValidationError):
        Holding(ticker="AAPL", weight=0.5, asset_class="invalid")  # enum


def test_six_sub_classes_instantiate_with_specific_fields():
    """E1~E6 모두 진입점별 특화 필드와 함께 instantiate PASS."""
    common = {
        "portfolio_id": "p",
        "fetched_at": datetime(2026, 5, 18, tzinfo=timezone.utc),
        "preset": "garp",
        "holdings": [_holding()],
    }
    e1 = CommentaryInputE1(**common, garp_metrics={"AAPL": {"per": 20}})
    assert e1.entry_point == "e1"

    e2 = CommentaryInputE2(**common, portfolio_return_1y=8.5, sector_allocation={"tech": 1.0})
    assert e2.entry_point == "e2"

    e3 = CommentaryInputE3(**common, concentration_metrics={"hhi": 0.5})
    assert e3.entry_point == "e3"

    e4 = CommentaryInputE4(**common, user_question="질문?")
    assert e4.entry_point == "e4" and e4.conversation_history == []

    e5 = CommentaryInputE5(**common, extraction_targets=["yield"])
    assert e5.entry_point == "e5" and e5.time_series_context is None

    e6 = CommentaryInputE6(**common, analysis_results={"AAPL": {"score": 8}})
    assert e6.entry_point == "e6"


def test_entry_point_discriminator_is_locked_literal():
    """각 sub class의 entry_point는 Literal로 고정 — 다른 값 거부."""
    # E1에 e1만 허용
    with pytest.raises(ValidationError):
        CommentaryInputE1(**_e1_payload(entry_point="e2"))


def test_mapping_registers_six_classes_with_shared_holding_type():
    """COMMENTARY_INPUT_CLASSES e1~e6 등록 + 모든 sub class가 동일 Holding type 재사용."""
    expected = {
        "e1": CommentaryInputE1, "e2": CommentaryInputE2, "e3": CommentaryInputE3,
        "e4": CommentaryInputE4, "e5": CommentaryInputE5, "e6": CommentaryInputE6,
    }
    assert COMMENTARY_INPUT_CLASSES == expected
    for cls in COMMENTARY_INPUT_CLASSES.values():
        assert "Holding" in str(cls.model_fields["holdings"].annotation), cls.__name__


# ============================================================
# §3 portfolio_a2 fixture 매핑
# ============================================================


def test_portfolio_a2_loads_to_six_sub_classes_with_time_series_e5():
    """KPI: portfolio_a2 fixture → 6 schema validate 100%. E5 TimeSeriesContext 동반."""
    inputs = load_portfolio_a2_all_inputs()
    assert set(inputs) == {"e1", "e2", "e3", "e4", "e5", "e6"}
    for ep, inp in inputs.items():
        assert inp.entry_point == ep
        assert inp.preset == "income"
        assert len(inp.holdings) == 5
        assert abs(sum(h.weight for h in inp.holdings) - 1.0) < 1e-6
    # E5는 TimeSeriesContext 채움
    e5 = inputs["e5"]
    assert e5.time_series_context is not None
    assert e5.time_series_context.window_4q is not None
    # 미등록 entry_point 로딩 시 KeyError
    with pytest.raises(KeyError):
        load_portfolio_a2_input("e99")
