"""Slice 12 Part 1+2 — ScoringEngineBase 단위 테스트.

Slice 11 Part 1 base class 검증 패턴 미러 + Part 2 utility 보강.

테스트 항목 (10건):
Part 1 (3):
  1. ScoringEngineBase abstract 직접 인스턴스화 불가
  2. Pydantic config (frozen=True + extra=forbid)
  3. abstractmethod 등록 (score, required_metrics)
Part 2 (7):
  4. _apply_gate None → True
  5. _apply_gate gte pass
  6. _apply_gate gte fail
  7. _apply_gate lte pass/fail
  8. _apply_gate missing metric → False
  9. _weighted_sum 기본
  10. _weighted_sum 부재 지표 → 0
"""

from __future__ import annotations

import pytest

from portfolio.services.scoring.base import ScoringEngineBase


def test_abstract_cannot_instantiate():
    """ScoringEngineBase는 abstract → 직접 인스턴스화 시 TypeError."""
    with pytest.raises(TypeError):
        ScoringEngineBase()


def test_frozen_extra_forbid_config():
    """Pydantic config 검증 — frozen + extra=forbid."""
    assert ScoringEngineBase.model_config.get("frozen") is True
    assert ScoringEngineBase.model_config.get("extra") == "forbid"


def test_abstract_methods_defined():
    """abstract 메서드 등록 확인 — score / required_metrics."""
    assert "score" in ScoringEngineBase.__abstractmethods__
    assert "required_metrics" in ScoringEngineBase.__abstractmethods__


# ============================================================
# Part 2 utility (_apply_gate, _weighted_sum)
# ============================================================


def test_gate_none_passes():
    """gate=None → 항상 True."""
    assert ScoringEngineBase._apply_gate({"yield": 0.01}, None) is True


def test_gate_gte_pass():
    """gte (기본 op): value ≥ threshold → True."""
    gate = {"dividend_yield": 0.03, "_op": "gte"}
    assert ScoringEngineBase._apply_gate({"dividend_yield": 0.05}, gate) is True


def test_gate_gte_fail():
    """gte: value < threshold → False."""
    gate = {"dividend_yield": 0.03, "_op": "gte"}
    assert ScoringEngineBase._apply_gate({"dividend_yield": 0.02}, gate) is False


def test_gate_lte_pass_and_fail():
    """lte: value ≤ threshold → True / 초과 → False."""
    gate = {"beta": 1.2, "_op": "lte"}
    assert ScoringEngineBase._apply_gate({"beta": 1.0}, gate) is True
    assert ScoringEngineBase._apply_gate({"beta": 1.5}, gate) is False


def test_gate_missing_metric_fails():
    """지표 부재 시 미통과 (보수적 처리)."""
    gate = {"dividend_yield": 0.03, "_op": "gte"}
    assert ScoringEngineBase._apply_gate({"other_metric": 0.5}, gate) is False


def test_weighted_sum_basic():
    """기본 가중합."""
    metrics = {"a": 0.5, "b": 0.8}
    weights = {"a": 0.6, "b": 0.4}
    result = ScoringEngineBase._weighted_sum(metrics, weights)
    assert result == pytest.approx(0.5 * 0.6 + 0.8 * 0.4)


def test_weighted_sum_missing_metric_zero():
    """부재 지표는 0으로 처리."""
    metrics = {"a": 1.0}
    weights = {"a": 0.5, "b": 0.5}
    result = ScoringEngineBase._weighted_sum(metrics, weights)
    assert result == pytest.approx(0.5)
