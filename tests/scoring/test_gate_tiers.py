"""Slice 13 Step 0a #60 — 3단 게이트 (gate_tiers, ADDITIVE) 단위 테스트.

설계 원칙:
  - 기존 `gate` / `_apply_gate` 로직 무손상 (점수 경로 분리)
  - gate_tiers=None → "pass" (기존 12 preset 동작 불변 보증)
  - "pass" | "warn" | "fail" 3분기 검증
  - prompt format helper 검증
"""

from __future__ import annotations

import pytest

from portfolio.services.scoring import (
    PRESET_ID_TO_CATEGORY,
    PresetSpec,
    ScoringEngineBase,
    format_gate_tier_for_prompt,
    get_preset_spec,
)


# ============================================================
# _evaluate_gate_tier 단위 (8건)
# ============================================================


def test_gate_tier_none_returns_pass():
    """gate_tiers=None → 항상 "pass" (기존 preset 불변 보증)."""
    assert ScoringEngineBase._evaluate_gate_tier({"x": 0.5}, None) == "pass"


def test_gate_tier_gte_pass():
    """gte: value ≥ warn_below → "pass"."""
    tiers = {
        "metric": "dividend_yield",
        "fail_below": 0.02,
        "warn_below": 0.03,
        "_op": "gte",
    }
    assert (
        ScoringEngineBase._evaluate_gate_tier({"dividend_yield": 0.05}, tiers)
        == "pass"
    )


def test_gate_tier_gte_warn():
    """gte: fail_below ≤ value < warn_below → "warn"."""
    tiers = {
        "metric": "dividend_yield",
        "fail_below": 0.02,
        "warn_below": 0.03,
        "_op": "gte",
    }
    assert (
        ScoringEngineBase._evaluate_gate_tier({"dividend_yield": 0.025}, tiers)
        == "warn"
    )


def test_gate_tier_gte_fail():
    """gte: value < fail_below → "fail"."""
    tiers = {
        "metric": "dividend_yield",
        "fail_below": 0.02,
        "warn_below": 0.03,
        "_op": "gte",
    }
    assert (
        ScoringEngineBase._evaluate_gate_tier({"dividend_yield": 0.01}, tiers)
        == "fail"
    )


def test_gate_tier_lte_three_branches():
    """lte: 값이 작을수록 좋음 (예: debt_ratio)."""
    tiers = {
        "metric": "debt_ratio",
        "fail_below": 0.7,   # 0.7 초과 → fail
        "warn_below": 0.5,   # 0.5 초과 → warn
        "_op": "lte",
    }
    assert ScoringEngineBase._evaluate_gate_tier({"debt_ratio": 0.3}, tiers) == "pass"
    assert ScoringEngineBase._evaluate_gate_tier({"debt_ratio": 0.6}, tiers) == "warn"
    assert ScoringEngineBase._evaluate_gate_tier({"debt_ratio": 0.8}, tiers) == "fail"


def test_gate_tier_missing_metric_returns_fail():
    """지표 부재 → "fail" (_apply_gate 동일 보수 정책)."""
    tiers = {
        "metric": "dividend_yield",
        "fail_below": 0.02,
        "warn_below": 0.03,
    }
    assert ScoringEngineBase._evaluate_gate_tier({"other": 0.5}, tiers) == "fail"


def test_gate_tier_default_op_is_gte():
    """_op 미지정 시 기본 "gte"."""
    tiers = {"metric": "x", "fail_below": 0.1, "warn_below": 0.2}
    assert ScoringEngineBase._evaluate_gate_tier({"x": 0.05}, tiers) == "fail"
    assert ScoringEngineBase._evaluate_gate_tier({"x": 0.15}, tiers) == "warn"
    assert ScoringEngineBase._evaluate_gate_tier({"x": 0.25}, tiers) == "pass"


def test_gate_tier_returns_str_type():
    """반환 타입은 항상 str (pass/warn/fail) — bool과 분리."""
    result = ScoringEngineBase._evaluate_gate_tier({}, None)
    assert isinstance(result, str)


# ============================================================
# PresetSpec validator (3건)
# ============================================================


def test_gate_tiers_validator_invalid_metric():
    """metric 미지정 시 ValueError."""
    with pytest.raises(ValueError, match="metric must be non-empty"):
        PresetSpec(
            preset_id="x",
            category="value",
            weights={"a": 1.0},
            gate_tiers={"fail_below": 0.1, "warn_below": 0.2},
        )


def test_gate_tiers_validator_gte_threshold_order():
    """gte _op: fail_below < warn_below 강제."""
    with pytest.raises(ValueError, match="fail_below must be <"):
        PresetSpec(
            preset_id="x",
            category="value",
            weights={"a": 1.0},
            gate_tiers={
                "metric": "x",
                "fail_below": 0.3,
                "warn_below": 0.2,  # gte인데 reverse
                "_op": "gte",
            },
        )


def test_gate_tiers_validator_lte_threshold_order():
    """lte _op: fail_below > warn_below 강제."""
    with pytest.raises(ValueError, match="fail_below must be >"):
        PresetSpec(
            preset_id="x",
            category="value",
            weights={"a": 1.0},
            gate_tiers={
                "metric": "debt",
                "fail_below": 0.2,
                "warn_below": 0.3,  # lte인데 reverse
                "_op": "lte",
            },
        )


# ============================================================
# 기존 12 preset 불변 보증 (1건 → 12 검증)
# ============================================================


def test_all_12_presets_have_gate_tiers_none():
    """기존 12 preset 모두 gate_tiers=None → 평가는 항상 "pass"."""
    for preset_id in PRESET_ID_TO_CATEGORY:
        spec = get_preset_spec(preset_id)
        assert spec.gate_tiers is None, (
            f"{preset_id}: gate_tiers must be None at Slice 13 entry "
            f"(Slice 14 #61 calibration 대상)"
        )
        # 어떤 metrics를 줘도 "pass" (점수 경로 무손상)
        assert (
            ScoringEngineBase._evaluate_gate_tier({}, spec.gate_tiers) == "pass"
        )


# ============================================================
# format_gate_tier_for_prompt (1건)
# ============================================================


def test_format_gate_tier_for_prompt_format():
    """prompt 1줄 포맷 확인."""
    out = format_gate_tier_for_prompt("dividend_growth", "warn")
    assert out == "## Gate Tier (dividend_growth): warn"
