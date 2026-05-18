"""Slice 11 Part 1 §3 — portfolio_a2 fixture loader.

fixture (`portfolio_a2.json`)을 6 진입점 통합 input schema sub class instance로 변환.

D-2 결정: fixture → schema validate **직접 매핑** (legacy adapter 없음).
fixture 키와 schema 필드 1:1 대응. drift 발생 시 즉시 ValidationError.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from portfolio.schemas.commentary_input import (
    COMMENTARY_INPUT_CLASSES,
    CommentaryInputBase,
)

FIXTURE_DIR = Path(__file__).resolve().parent
PORTFOLIO_A2_PATH = FIXTURE_DIR / "portfolio_a2.json"


def load_portfolio_a2_raw(path: Path | None = None) -> dict[str, Any]:
    """portfolio_a2.json 원본 dict 로드."""
    target = path or PORTFOLIO_A2_PATH
    with open(target, encoding="utf-8") as fp:
        return json.load(fp)


def _base_kwargs(fixture: dict[str, Any]) -> dict[str, Any]:
    """fixture top-level → base 공통 필드 dict (portfolio_id/fetched_at/preset/holdings)."""
    return {
        "portfolio_id": fixture["portfolio_id"],
        "fetched_at": fixture["fetched_at"],
        "preset": fixture["preset"],
        "holdings": fixture["holdings"],
    }


def load_portfolio_a2_input(
    entry_point: str,
    path: Path | None = None,
) -> CommentaryInputBase:
    """portfolio_a2 fixture를 단일 진입점 sub class instance로 변환.

    Args:
        entry_point: "e1" ~ "e6".
        path: fixture 경로 override (테스트용).

    Raises:
        KeyError: 미등록 entry_point.
        pydantic.ValidationError: fixture가 schema와 불일치 (drift 검출).
    """
    if entry_point not in COMMENTARY_INPUT_CLASSES:
        raise KeyError(
            f"unknown entry_point: {entry_point!r}. "
            f"valid: {sorted(COMMENTARY_INPUT_CLASSES)}"
        )

    fixture = load_portfolio_a2_raw(path)
    common = _base_kwargs(fixture)
    specific = fixture["inputs"][entry_point]

    cls = COMMENTARY_INPUT_CLASSES[entry_point]
    return cls(**common, **specific)


def load_portfolio_a2_all_inputs(
    path: Path | None = None,
) -> dict[str, CommentaryInputBase]:
    """portfolio_a2 fixture를 6 진입점 sub class instance dict로 변환.

    Returns:
        {"e1": CommentaryInputE1, "e2": CommentaryInputE2, ...}
    """
    return {
        ep: load_portfolio_a2_input(ep, path)
        for ep in COMMENTARY_INPUT_CLASSES
    }
