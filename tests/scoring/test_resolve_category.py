"""Slice 12 Part 3 — resolve_category + format_scores_for_prompt 단위 테스트."""

from __future__ import annotations

import pytest

from portfolio.services.scoring import (
    PRESET_ID_TO_CATEGORY,
    format_scores_for_prompt,
    resolve_category,
)


# ============================================================
# resolve_category — 12 preset_id 매핑
# ============================================================


def test_preset_id_to_category_has_12_entries():
    """12 preset 모두 등록 (presets.py 정합)."""
    assert len(PRESET_ID_TO_CATEGORY) == 12


@pytest.mark.parametrize("preset_id,category", [
    ("buffett_quality_value", "value"),
    ("piotroski_f_score", "value"),
    ("garp", "growth"),
    ("quality_growth", "growth"),
    ("dividend_growth", "income"),
    ("shareholder_yield", "income"),
    ("quality_factor", "factor"),
    ("low_volatility", "factor"),
    ("price_momentum", "factor"),
    ("multi_factor", "factor"),
    ("contrarian", "special"),
    ("concentrated_portfolio", "special"),
])
def test_resolve_category_mapping(preset_id, category):
    """12 preset_id → 카테고리 매핑 정합."""
    assert resolve_category(preset_id) == category


def test_resolve_category_unknown_raises():
    """미등록 preset_id → KeyError."""
    with pytest.raises(KeyError):
        resolve_category("unknown_preset")


# ============================================================
# format_scores_for_prompt
# ============================================================


def test_format_scores_normal():
    """정상 점수 → markdown bullet."""
    scores = {"p1": 50.5, "p2": 30.0, "_category_score": 40.25}
    out = format_scores_for_prompt(scores)
    assert "- p1: 50.50" in out
    assert "- p2: 30.00" in out
    assert "카테고리 평균: 40.25" in out


def test_format_scores_gate_triggered_marker():
    """gate 발동(0.0) → 명시적 마커."""
    scores = {"p1": 0.0, "p2": 50.0, "_category_score": 25.0}
    out = format_scores_for_prompt(scores)
    assert "(gate 미통과)" in out
    assert "- p1: 0.0 (gate 미통과)" in out


def test_format_scores_without_category_score():
    """`_category_score` 없으면 마지막 줄 생략."""
    scores = {"p1": 50.0}
    out = format_scores_for_prompt(scores)
    assert "카테고리 평균" not in out
    assert "- p1: 50.00" in out


def test_format_scores_underscore_keys_skipped():
    """underscore prefix 키는 별도 처리 (`_category_score`만 출력)."""
    scores = {"p1": 50.0, "_meta": 1.0, "_category_score": 50.0}
    out = format_scores_for_prompt(scores)
    assert "- _meta" not in out
    assert "카테고리 평균: 50.00" in out
