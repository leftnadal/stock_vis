"""
Slice 2 Step 5 — E5 fixture 무결성 검증.

7 fixture × {Pydantic E5Request 통과, expected 필드 존재} = 14
+ 카운트 검증 + COMMANDS-fixture 일치 = 16
"""

from __future__ import annotations

import pytest

from apps.portfolio.schemas.llm import E5Request
from apps.portfolio.tests.fixtures.sample_adjustment_context import (
    ALL_FIXTURES,
    COMMANDS,
)


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES))
def test_e5_fixture_valid_request(fixture_name):
    """각 fixture가 E5Request 검증을 통과해야 함."""
    fixture = ALL_FIXTURES[fixture_name]()
    req = E5Request(
        analysis_context=fixture["analysis_context"],
        user_command=fixture["user_command"],
    )
    assert req.user_command
    assert "holdings" in req.analysis_context


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES))
def test_e5_fixture_has_expected_field(fixture_name):
    """각 fixture에 expected 필드 (회고 시 비교 기준) 존재."""
    fixture = ALL_FIXTURES[fixture_name]()
    assert "expected" in fixture, f"{fixture_name}: expected 누락"


def test_e5_fixture_count():
    """v2: 7 fixture (5 표준 + unclear_amount + large)."""
    assert len(ALL_FIXTURES) == 7


def test_commands_match_fixtures():
    """COMMANDS의 모든 키가 fixture에서 사용되고, fixture 명령은 COMMANDS에 존재."""
    used_commands: set[str] = set()
    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        cmd = fixture["user_command"]
        matched = [k for k, v in COMMANDS.items() if v == cmd]
        assert matched, f"fixture {name}이 COMMANDS에 없는 명령 사용: {cmd!r}"
        used_commands.update(matched)
    unused = set(COMMANDS) - used_commands
    assert not unused, f"COMMANDS에 정의됐지만 미사용: {unused}"
