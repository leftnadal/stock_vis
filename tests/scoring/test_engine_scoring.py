"""Slice 12 Part 2 Step 5.3 — 5 카테고리 score() 동작 검증.

각 카테고리:
  - 정상 metrics → 0~100 범위 + `_category_score` 평균 일치
  - gate 발동 (income/low_volatility) → score=0
  - 모든 preset 출력 + clip 동작
"""

from __future__ import annotations

import pytest

from portfolio.services.scoring import get_scorer
from portfolio.services.scoring.presets.factor import FACTOR_SPECS
from portfolio.services.scoring.presets.growth import GROWTH_SPECS
from portfolio.services.scoring.presets.income import INCOME_SPECS
from portfolio.services.scoring.presets.special import SPECIAL_SPECS
from portfolio.services.scoring.presets.value import VALUE_SPECS

SPEC_LISTS = {
    "value": VALUE_SPECS,
    "growth": GROWTH_SPECS,
    "income": INCOME_SPECS,
    "factor": FACTOR_SPECS,
    "special": SPECIAL_SPECS,
}


@pytest.mark.parametrize("category", list(SPEC_LISTS.keys()))
def test_score_output_in_0_100_range(category):
    """모든 preset score 및 _category_score는 0~100 범위 (clip)."""
    scorer = get_scorer(category)
    # 모든 required metric을 0.5로 채움 (gate 통과 보장 위해 dividend_yield/shareholder_yield는 0.5)
    metrics = {m: 0.5 for m in scorer.required_metrics()}
    out = scorer.score(metrics)
    for preset_id, score in out.items():
        assert 0.0 <= score <= 100.0, (
            f"{category}/{preset_id} out of range: {score}"
        )


@pytest.mark.parametrize("category", list(SPEC_LISTS.keys()))
def test_score_includes_all_presets_plus_category_score(category):
    """각 카테고리 출력은 카테고리 내 모든 preset_id + `_category_score`."""
    scorer = get_scorer(category)
    metrics = {m: 0.5 for m in scorer.required_metrics()}
    out = scorer.score(metrics)
    expected_preset_ids = {spec.preset_id for spec in SPEC_LISTS[category]}
    actual_preset_ids = {k for k in out if not k.startswith("_")}
    assert actual_preset_ids == expected_preset_ids
    assert "_category_score" in out


@pytest.mark.parametrize("category", list(SPEC_LISTS.keys()))
def test_category_score_equals_preset_mean(category):
    """`_category_score` = preset_id별 score 평균."""
    scorer = get_scorer(category)
    metrics = {m: 0.5 for m in scorer.required_metrics()}
    out = scorer.score(metrics)
    preset_scores = [v for k, v in out.items() if not k.startswith("_")]
    expected = sum(preset_scores) / len(preset_scores)
    assert out["_category_score"] == pytest.approx(expected)


# ============================================================
# Gate 발동 (income, factor/low_volatility)
# ============================================================


def test_income_gate_cuts_when_yield_below_threshold():
    """income: dividend_yield 0.01 < 0.02 → dividend_growth=0, shareholder_yield=0."""
    scorer = get_scorer("income")
    out = scorer.score({
        "dividend_yield": 0.01,
        "dividend_growth_rate_5y": 0.9,
        "dividend_growth_consistency_5y": 0.9,
        "shareholder_yield": 0.01,  # < 0.02 → cut
        "net_buyback_yield": 0.05,
        "net_debt_reduction_rate": 0.05,
    })
    assert out["dividend_growth"] == 0.0
    assert out["shareholder_yield"] == 0.0
    assert out["_category_score"] == 0.0


def test_income_gate_passes_when_yield_above_threshold():
    """income: yield 0.05 ≥ 0.02 → 가중합 정상 계산."""
    scorer = get_scorer("income")
    out = scorer.score({
        "dividend_yield": 0.05,
        "dividend_growth_rate_5y": 0.8,
        "dividend_growth_consistency_5y": 0.9,
        "shareholder_yield": 0.06,
        "net_buyback_yield": 0.03,
        "net_debt_reduction_rate": 0.02,
    })
    assert out["dividend_growth"] > 0.0
    assert out["shareholder_yield"] > 0.0


def test_factor_low_volatility_gate_cuts_high_beta():
    """factor: low_volatility — beta 1.5 > 1.2 → low_volatility=0."""
    scorer = get_scorer("factor")
    metrics = {m: 0.5 for m in scorer.required_metrics()}
    metrics["beta"] = 1.5  # gate cut
    out = scorer.score(metrics)
    assert out["low_volatility"] == 0.0
    # 다른 factor preset은 영향 없음
    assert out["quality_factor"] > 0.0
    assert out["price_momentum"] > 0.0
    assert out["multi_factor"] > 0.0


def test_factor_low_volatility_gate_passes_low_beta():
    """factor: beta 0.8 ≤ 1.2 → low_volatility 정상."""
    scorer = get_scorer("factor")
    metrics = {m: 0.5 for m in scorer.required_metrics()}
    metrics["beta"] = 0.8
    out = scorer.score(metrics)
    assert out["low_volatility"] > 0.0
