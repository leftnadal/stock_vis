"""Slice 12 Part 2 Step 5.1 — PresetSpec validator 단위 테스트 (7건)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from portfolio.services.scoring.preset_spec import PresetSpec


def test_valid_spec():
    """정상 spec 생성 PASS."""
    spec = PresetSpec(
        preset_id="value_test",
        category="value",
        weights={"roic": 0.5, "roe": 0.5},
    )
    assert spec.preset_id == "value_test"
    assert spec.category == "value"
    assert spec.gate is None


def test_weights_sum_not_one():
    """weights 합 0.97 → ValidationError."""
    with pytest.raises(ValidationError, match="weights sum"):
        PresetSpec(
            preset_id="bad",
            category="value",
            weights={"roic": 0.5, "roe": 0.47},
        )


def test_weights_sum_one_with_tolerance():
    """1.0001 → PASS (±0.001 허용)."""
    spec = PresetSpec(
        preset_id="ok",
        category="value",
        weights={"roic": 0.5001, "roe": 0.5},
    )
    assert spec.preset_id == "ok"


def test_negative_weight():
    """음수 가중치 → ValidationError."""
    with pytest.raises(ValidationError, match="non-negative"):
        PresetSpec(
            preset_id="bad",
            category="value",
            weights={"roic": 1.1, "roe": -0.1},
        )


def test_invalid_category():
    """미등록 카테고리 → ValidationError."""
    with pytest.raises(ValidationError):
        PresetSpec(
            preset_id="bad",
            category="unknown",  # type: ignore[arg-type]
            weights={"roic": 1.0},
        )


def test_frozen():
    """frozen=True — 인스턴스 수정 불가."""
    spec = PresetSpec(
        preset_id="frozen",
        category="value",
        weights={"roic": 1.0},
    )
    with pytest.raises(ValidationError):
        spec.preset_id = "modified"  # type: ignore[misc]


def test_extra_forbid():
    """extra="forbid" — 미정의 필드 → ValidationError."""
    with pytest.raises(ValidationError):
        PresetSpec(
            preset_id="bad",
            category="value",
            weights={"roic": 1.0},
            unknown_field="x",  # type: ignore[call-arg]
        )


def test_valid_gate_gte():
    """정상 gate (gte 기본)."""
    spec = PresetSpec(
        preset_id="income_test",
        category="income",
        weights={"dividend_yield": 1.0},
        gate={"dividend_yield": 0.03, "_op": "gte"},
    )
    assert spec.gate == {"dividend_yield": 0.03, "_op": "gte"}


def test_invalid_gate_op():
    """gate _op 미등록 값 → ValidationError."""
    with pytest.raises(ValidationError, match="gate _op"):
        PresetSpec(
            preset_id="bad",
            category="value",
            weights={"roic": 1.0},
            gate={"roic": 0.1, "_op": "between"},
        )


def test_gate_without_metric_raises():
    """gate에 metric 키 없이 _op만 있으면 → ValidationError."""
    with pytest.raises(ValidationError, match="at least one metric"):
        PresetSpec(
            preset_id="bad",
            category="value",
            weights={"roic": 1.0},
            gate={"_op": "gte"},
        )
