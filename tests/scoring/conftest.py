"""Slice 12 Part 3 — scoring fixture loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture():
    """fixture name (확장자 제외) → dict 로더."""

    def _load(name: str) -> dict:
        with open(FIXTURE_DIR / f"{name}.json", encoding="utf-8") as f:
            return json.load(f)

    return _load


FIXTURE_NAMES = [
    "value_normal", "value_edge", "value_gate",
    "growth_normal", "growth_edge", "growth_gate",
    "income_normal", "income_edge", "income_gate",
    "factor_normal", "factor_edge", "factor_gate",
    "special_normal", "special_edge", "special_gate",
]
