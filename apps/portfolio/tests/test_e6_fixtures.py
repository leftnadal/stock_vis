"""E6 fixture 단위 테스트 (Slice 4 Step 5).

Hybrid 7 패턴 검증 + E6Request schema 만족 + 메타 일관성.
"""

from __future__ import annotations

import pytest

from apps.portfolio.schemas.llm import E6Request
from apps.portfolio.tests.fixtures.sample_comparison_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
    get_all_fixtures,
    get_baseline_fixtures,
    get_e6_fixture_focused_multi_aspect,
    get_focused_fixtures,
)


def test_all_fixtures_count():
    """7개 fixture 정의."""
    assert len(ALL_FIXTURES) == 7


def test_baseline_count():
    """baseline 그룹 3개 (Slice 2 재활용)."""
    baseline = get_baseline_fixtures()
    assert len(baseline) == 3
    for fx in baseline:
        assert fx["fixture_group"] == "e5_baseline"


def test_focused_count():
    """focused 그룹 4개 (Slice 4 신규)."""
    focused = get_focused_fixtures()
    assert len(focused) == 4
    for fx in focused:
        assert fx["fixture_group"] == "e6_focused"


def test_fixture_groups_meta_consistency():
    """FIXTURE_GROUPS 메타가 ALL_FIXTURES 키와 일치."""
    declared = set(FIXTURE_GROUPS["e5_baseline"]) | set(FIXTURE_GROUPS["e6_focused"])
    assert declared == set(ALL_FIXTURES.keys())


@pytest.mark.parametrize("fixture_fn", list(ALL_FIXTURES.values()))
def test_fixture_satisfies_e6_request_schema(fixture_fn):
    """모든 fixture는 E6Request schema를 만족."""
    fx = fixture_fn()
    payload = {
        "analysis_context": fx["analysis_context"],
        "adjustments": fx["adjustments"],
    }
    if fx.get("user_intent"):
        payload["user_intent"] = fx["user_intent"]
    req = E6Request.model_validate(payload)
    assert len(req.adjustments) >= 1
    # ticker / action / reason_quote 필수
    for adj in req.adjustments:
        assert adj.ticker
        assert adj.action in {"increase", "decrease", "remove", "add", "info_only"}
        assert adj.reason_quote


def test_fixture_ids_unique():
    """fixture_id 중복 없음."""
    ids = [fx["fixture_id"] for fx in get_all_fixtures()]
    assert len(set(ids)) == len(ids)


def test_focused_multi_aspect_complexity():
    """e6_focused_multi_aspect 은 5개 이상 adjustment."""
    fx = get_e6_fixture_focused_multi_aspect()
    assert len(fx["adjustments"]) >= 5
    # 4개 액션 모두 등장 (remove/decrease/increase/add)
    actions = {adj["action"] for adj in fx["adjustments"]}
    assert {"remove", "decrease", "increase", "add"}.issubset(actions)


def test_baseline_uses_slice2_user_command_as_intent():
    """baseline fixture의 user_intent가 Slice 2 user_command 그대로 들어옴."""
    baseline = get_baseline_fixtures()
    for fx in baseline:
        assert fx.get("user_intent")  # None 아님
        assert isinstance(fx["user_intent"], str)


def test_all_fixtures_have_holdings():
    """모든 fixture에 holdings 존재 — E6 prompt 작성에 필요."""
    for fx in get_all_fixtures():
        holdings = fx["analysis_context"].get("holdings")
        assert holdings, f"{fx['fixture_id']} has empty holdings"
