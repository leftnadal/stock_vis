"""E4 mock fixture round-trip 회귀 (Slice 7 Part 2 §3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from portfolio.schemas.e4_conversation import (
    E4ConversationInput,
    E4ConversationMetadata,
    E4ConversationOutput,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "e4_conversation"
ALL_FIXTURES = sorted(FIXTURE_DIR.glob("S*.json"))


# ===== Input round-trip =====


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_fixture_input_valid(fixture_path):
    """모든 fixture의 input이 schema validation 통과 (I2 trigger는 실패 기대)."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if data.get("trigger_case") == "I2":
        with pytest.raises(ValidationError):
            E4ConversationInput(**data["input"])
    else:
        inp = E4ConversationInput(**data["input"])
        assert inp.portfolio_id
        assert inp.tier in {1, 2, 3}


# ===== Output round-trip =====


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_fixture_expected_output_valid(fixture_path):
    """모든 fixture의 expected_output이 schema validation 통과 (null 허용)."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    expected_output = data.get("expected_output")
    if expected_output is None:
        # S13 (I2 trigger): output 자체가 None 허용
        return
    out = E4ConversationOutput(**expected_output)
    assert len(out.answer) >= 20


# ===== Metadata round-trip =====


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_fixture_expected_metadata_valid(fixture_path):
    """모든 fixture의 expected_metadata가 schema validation 통과."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    meta = data["expected_metadata"]
    m = E4ConversationMetadata(**meta)
    # trigger_case와 case_flags 일관성
    trigger = data.get("trigger_case")
    if trigger in {"I1", "I2", "I3", "I4"}:
        assert trigger in m.case_flags, f"{fixture_path.stem}: case_flags 누락"


# ===== Coverage =====


def test_fixture_count_15():
    """15 cases 정의대로 fixture 15건 존재."""
    assert len(ALL_FIXTURES) == 15, f"expected 15 fixtures, got {len(ALL_FIXTURES)}"


def test_fixture_preset_coverage():
    """V1~V5 5종 preset prefix 모두 cover."""
    prefixes = set()
    for fp in ALL_FIXTURES:
        data = json.loads(fp.read_text(encoding="utf-8"))
        prefixes.add(data["preset_id"].split("_")[0])
    assert prefixes >= {"V1", "V2", "V3", "V4", "V5"}, (
        f"missing preset prefixes: {prefixes}"
    )


def test_fixture_tier_coverage():
    """Tier 1·2·3 모두 cover."""
    tiers = set()
    for fp in ALL_FIXTURES:
        data = json.loads(fp.read_text(encoding="utf-8"))
        tiers.add(data["tier"])
    assert tiers == {1, 2, 3}, f"missing tiers: {tiers}"


def test_fixture_trigger_case_coverage():
    """분기 케이스 I1/I2/I4 cover."""
    triggers = set()
    for fp in ALL_FIXTURES:
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("trigger_case"):
            triggers.add(data["trigger_case"])
    for needed in ("I1", "I2", "I4"):
        assert needed in triggers, f"missing trigger {needed}; have {triggers}"


def test_fixture_low_confidence_present():
    """confidence=low 시나리오 1건 이상 cover (S15)."""
    found = False
    for fp in ALL_FIXTURES:
        data = json.loads(fp.read_text(encoding="utf-8"))
        out = data.get("expected_output")
        if out and out.get("confidence") == "low":
            found = True
            break
    assert found, "no fixture with confidence=low (S15 누락 추정)"


# ===== Tier별 budget key 일관성 =====


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_fixture_tier_matches_input_tier(fixture_path):
    """fixture top-level tier와 input.tier가 일치 (S13는 schema rejects라 input.tier만 검증)."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert data["tier"] == data["input"]["tier"]
