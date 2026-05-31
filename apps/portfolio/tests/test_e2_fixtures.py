"""E2 fixture 검증 (Slice 3 Step 5 — Q4 hybrid)."""

from __future__ import annotations

import pytest

from portfolio.schemas.llm import E2Request
from portfolio.tests.fixtures.sample_diagnostic_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
)


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_e2_fixture_valid_request(fixture_name):
    """각 fixture가 E2Request로 검증 통과."""
    fixture = ALL_FIXTURES[fixture_name]()
    req = E2Request(analysis_context=fixture["analysis_context"])
    assert "holdings" in req.analysis_context
    assert "preset_id" in req.analysis_context


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_e2_fixture_has_expected_and_group(fixture_name):
    """각 fixture에 expected + fixture_group 존재."""
    fixture = ALL_FIXTURES[fixture_name]()
    assert "expected" in fixture, f"{fixture_name}: expected 누락"
    assert "fixture_group" in fixture
    assert fixture["fixture_group"] in FIXTURE_GROUPS


def test_e2_fixture_count():
    """7개 fixture (3 baseline + 4 focused)."""
    assert len(ALL_FIXTURES) == 7


def test_fixture_groups_completeness():
    """FIXTURE_GROUPS의 모든 fixture가 ALL_FIXTURES에 존재 + 역도 성립."""
    all_grouped = set()
    for group_fixtures in FIXTURE_GROUPS.values():
        all_grouped.update(group_fixtures)
    assert all_grouped == set(ALL_FIXTURES.keys())


def test_baseline_group_count():
    """Slice 1 baseline 그룹 = 3개."""
    assert len(FIXTURE_GROUPS["slice1_baseline"]) == 3


def test_focused_group_count():
    """E2 focused 그룹 = 4개."""
    assert len(FIXTURE_GROUPS["e2_focused"]) == 4
