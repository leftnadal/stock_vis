"""distribution_width_kpi 회귀 (Slice 7 Part 2 §4)."""

from __future__ import annotations

from portfolio.llm.eval_metrics import distribution_width_kpi


def test_empty_returns_fail():
    r = distribution_width_kpi([])
    assert r["pass"] is False
    assert r["width"] == 0


def test_full_range_passes():
    """1~5 전 범위 사용 + 5점 비율 적절 + 1점 1건 이상 → PASS."""
    scores = [1, 2, 3, 4, 5, 3, 4, 2, 3, 4]  # 10건, 5점 1/10=10%, 1점 1건
    r = distribution_width_kpi(scores)
    assert r["width"] == 4
    assert r["one_count"] == 1
    assert r["five_ratio"] == 0.1
    assert r["pass"] is True


def test_narrow_distribution_fails():
    """2~4 좁은 분포 — Slice 6 관찰 케이스 → FAIL."""
    scores = [3, 3, 4, 3, 4, 2, 3, 4, 3, 3]  # width=2
    r = distribution_width_kpi(scores)
    assert r["width"] == 2
    assert r["pass"] is False


def test_five_ratio_inflation_fails():
    """5점 비율 30% 초과 — 인플레이션 → FAIL (5_ratio > 20%)."""
    scores = [1, 5, 5, 5, 5, 3, 4, 2, 3, 4]  # 5점 4/10=40%
    r = distribution_width_kpi(scores)
    assert r["five_ratio"] == 0.4
    assert r["pass"] is False  # five_ratio 초과


def test_no_one_score_fails():
    """1점 사용 0건 → FAIL (양극단 미활용)."""
    scores = [2, 3, 4, 5, 3, 4, 2, 3, 4, 5]  # min=2
    r = distribution_width_kpi(scores)
    assert r["one_count"] == 0
    assert r["pass"] is False


def test_distribution_counter():
    """distribution dict가 Counter 결과와 일치."""
    scores = [1, 1, 2, 5, 5]
    r = distribution_width_kpi(scores)
    assert r["distribution"] == {1: 2, 2: 1, 5: 2}
