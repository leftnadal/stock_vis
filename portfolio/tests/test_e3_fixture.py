"""E3 fixture 단위 테스트 (Slice 5 Step 5).

Hybrid 7 패턴 검증 + 5 카테고리 cover + E3Request schema 만족 + level_tag valid.
"""

from __future__ import annotations

import pytest

from portfolio.schemas.llm import E3Request
from portfolio.tests.fixtures.sample_metric_comment_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
    get_all_fixtures,
    get_baseline_fixtures,
    get_covered_categories,
    get_e3_fixture_focused_contrarian,
    get_focused_fixtures,
)

_VALID_LEVEL_TAGS = {"excellent", "good", "moderate", "weak", "critical"}


def test_all_fixtures_count():
    """7 fixture 정의 (baseline 3 + focused 4)."""
    assert len(ALL_FIXTURES) == 7


def test_baseline_count():
    """baseline 그룹 3개 (Slice 1 GARP 재활용)."""
    baseline = get_baseline_fixtures()
    assert len(baseline) == 3
    for fx in baseline:
        assert fx["fixture_group"] == "garp_baseline"
        assert fx["preset_id"] == "garp"


def test_focused_count():
    """focused 그룹 4개 (4 preset 신규)."""
    focused = get_focused_fixtures()
    assert len(focused) == 4
    for fx in focused:
        assert fx["fixture_group"] == "preset_focused"


def test_fixture_groups_meta_consistency():
    """FIXTURE_GROUPS 메타가 ALL_FIXTURES 키와 일치."""
    declared = set(FIXTURE_GROUPS["garp_baseline"]) | set(
        FIXTURE_GROUPS["preset_focused"]
    )
    assert declared == set(ALL_FIXTURES.keys())


def test_all_fixtures_satisfy_e3_request_schema():
    """모든 fixture가 E3Request schema 만족."""
    for fx in get_all_fixtures():
        req = E3Request(analysis_context=fx["analysis_context"])
        assert req.analysis_context is not None


@pytest.mark.parametrize("fixture_fn", list(ALL_FIXTURES.values()))
def test_fixture_metric_results_valid_level_tag(fixture_fn):
    """모든 metric의 level_tag ∈ {excellent, good, moderate, weak, critical}."""
    fx = fixture_fn()
    p = fx["analysis_context"]["analysis_target_portfolio"]
    for tier_key in (
        "core_metric_results",
        "supporting_metric_results",
        "context_metric_results",
    ):
        for m in p.get(tier_key, []):
            assert m["level_tag"] in _VALID_LEVEL_TAGS, (
                f"{fx['fixture_id']}: {m['metric_id']} level_tag={m['level_tag']!r} 부적절"
            )


@pytest.mark.parametrize("fixture_fn", list(ALL_FIXTURES.values()))
def test_fixture_percentile_in_range(fixture_fn):
    """percentile ∈ [0, 1] (None 허용)."""
    fx = fixture_fn()
    p = fx["analysis_context"]["analysis_target_portfolio"]
    for tier_key in (
        "core_metric_results",
        "supporting_metric_results",
    ):
        for m in p.get(tier_key, []):
            pct = m.get("percentile")
            if pct is None:
                continue
            assert 0.0 <= float(pct) <= 1.0


def test_covered_categories_5():
    """7 fixture가 5 카테고리(value/growth/income/factor/special) 모두 cover."""
    categories = get_covered_categories()
    expected = {"value", "growth", "income", "factor", "special"}
    assert categories == expected


def test_focused_buffett_value_category():
    """buffett fixture: preset_category=value + Buffett 메타."""
    from portfolio.tests.fixtures.sample_metric_comment_context import (
        get_e3_fixture_focused_buffett,
    )
    fx = get_e3_fixture_focused_buffett()
    assert fx["preset_category"] == "value"
    assert fx["preset_id"] == "buffett_quality_value"


def test_focused_dividend_growth_income_category():
    """dividend_growth fixture: preset_category=income."""
    from portfolio.tests.fixtures.sample_metric_comment_context import (
        get_e3_fixture_focused_dividend_growth,
    )
    fx = get_e3_fixture_focused_dividend_growth()
    assert fx["preset_category"] == "income"
    assert fx["preset_id"] == "dividend_growth"


def test_focused_contrarian_special_category():
    """contrarian fixture: preset_category=special."""
    fx = get_e3_fixture_focused_contrarian()
    assert fx["preset_category"] == "special"
    assert fx["preset_id"] == "contrarian"


def test_baseline_focused_grouping():
    """baseline 3 + focused 4 = 7 (hybrid 비율 정합)."""
    baseline = get_baseline_fixtures()
    focused = get_focused_fixtures()
    assert len(baseline) + len(focused) == 7
