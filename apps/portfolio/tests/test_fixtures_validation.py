"""
Slice 1 Part 2 Step 7 — fixture 무결성 검증.

- weight 합 = 1.0
- holdings 수 정확
- garp_large 5/5/5 분포
- garp_misfit 모두 GARP 부정합 (PEG > 2.5 또는 ROIC < 8%)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.portfolio.tests.fixtures.sample_analysis_context import (
    garp_large_fit_distribution,
    get_context_dividend,
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)


@pytest.mark.parametrize(
    "loader",
    [
        get_context_garp_tech,
        get_context_garp_misfit,
        get_context_garp_large,
        get_context_dividend,
    ],
)
def test_fixture_holdings_weights_sum_to_one(loader):
    """모든 fixture의 holdings_summary weight 합이 1.0 ± 0.001."""
    ctx = loader()
    total = sum(h.weight for h in ctx.analysis_target_portfolio.holdings_summary)
    assert abs(total - Decimal("1.0")) < Decimal("0.001"), (
        f"{loader.__name__}: weight sum {total}"
    )


@pytest.mark.parametrize(
    "loader,expected",
    [
        (get_context_garp_tech, 5),
        (get_context_garp_misfit, 5),
        (get_context_garp_large, 15),
    ],
)
def test_fixture_holding_count_matches(loader, expected):
    """holdings_summary 길이와 holding_count 필드가 일치 + 기대값과 일치."""
    ctx = loader()
    p = ctx.analysis_target_portfolio
    assert len(p.holdings_summary) == expected
    assert p.holding_count == expected


def test_garp_large_distribution():
    """garp_large fit_class 분포 = 5/5/5."""
    dist = garp_large_fit_distribution()
    assert dist == {"fit": 5, "partial": 5, "misfit": 5}


def test_garp_misfit_core_metrics_indicate_misfit():
    """garp_misfit의 core 메트릭이 GARP 부정합 시그널."""
    ctx = get_context_garp_misfit()
    p = ctx.analysis_target_portfolio
    by_id = {m.metric_id: m for m in p.core_metric_results}
    # PEG는 임계값 미통과
    assert by_id["peg_ratio"].passed_threshold is False
    # EPS 성장률도 임계값 미통과
    assert by_id["eps_growth_yoy"].passed_threshold is False
    # 약점에 PEG 등재
    weakness_ids = {w.metric_id for w in p.weaknesses}
    assert "peg_ratio" in weakness_ids


def test_garp_large_preset_consistency():
    """garp_large 메트릭 ID 집합이 PRESET_METRICS['garp']의 metric_id와 일치."""
    from apps.portfolio.metrics.definitions.preset_metrics import PRESET_METRICS

    ctx = get_context_garp_large()
    p = ctx.analysis_target_portfolio
    fixture_ids = {
        m.metric_id
        for m in (
            p.core_metric_results
            + p.supporting_metric_results
            + p.context_metric_results
        )
    }
    preset_ids = {entry["metric_id"] for entry in PRESET_METRICS["garp"]}
    # garp_large는 GARP 프리셋의 모든 metric_id를 포함
    assert preset_ids.issubset(fixture_ids), (
        f"garp_large가 GARP 프리셋 metric을 누락: {preset_ids - fixture_ids}"
    )
