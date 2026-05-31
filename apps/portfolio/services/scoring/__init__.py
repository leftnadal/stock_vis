"""Slice 12 Part 1+3 — preset scoring registry + 호출자 통합 helpers.

Slice 11 Part 1 `COMMENTARY_INPUT_CLASSES` 패턴 미러 — 5 카테고리 dict 매핑.
Part 3: `resolve_category` + `format_scores_for_prompt` + 12 preset_id mapping 추가.
"""

from __future__ import annotations

from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.services.scoring.preset_spec import PresetSpec
from portfolio.services.scoring.presets.factor import FACTOR_SPECS, FactorScoringEngine
from portfolio.services.scoring.presets.growth import GROWTH_SPECS, GrowthScoringEngine
from portfolio.services.scoring.presets.income import INCOME_SPECS, IncomeScoringEngine
from portfolio.services.scoring.presets.special import (
    SPECIAL_SPECS,
    SpecialScoringEngine,
)
from portfolio.services.scoring.presets.value import VALUE_SPECS, ValueScoringEngine

PRESET_SCORERS: dict[str, type[ScoringEngineBase]] = {
    "value": ValueScoringEngine,
    "growth": GrowthScoringEngine,
    "income": IncomeScoringEngine,
    "factor": FactorScoringEngine,
    "special": SpecialScoringEngine,
}


# Slice 12 Part 3 — 12 preset_id → 5 카테고리 매핑.
# presets.py PRESETS dict의 category 값 기반. 새 preset 추가 시 본 dict 갱신 필수.
# (#61 후보: 자동화 — Slice 13+ PS 0.5)
PRESET_ID_TO_CATEGORY: dict[str, str] = {
    # value
    "buffett_quality_value": "value",
    "piotroski_f_score": "value",
    # growth
    "garp": "growth",
    "quality_growth": "growth",
    # income
    "dividend_growth": "income",
    "shareholder_yield": "income",
    # factor
    "quality_factor": "factor",
    "low_volatility": "factor",
    "price_momentum": "factor",
    "multi_factor": "factor",
    # special
    "contrarian": "special",
    "concentrated_portfolio": "special",
}


def get_scorer(category: str) -> ScoringEngineBase:
    """카테고리명으로 scorer 인스턴스 반환.

    Args:
        category: "value" / "growth" / "income" / "factor" / "special".

    Raises:
        KeyError: 미등록 category.
    """
    if category not in PRESET_SCORERS:
        raise KeyError(f"Unknown category: {category!r}")
    return PRESET_SCORERS[category]()


# Slice 13 Step 0a #60 — preset_id → PresetSpec lookup (gate_tiers 접근용).
_ALL_PRESET_SPECS: dict[str, PresetSpec] = {
    spec.preset_id: spec
    for specs in (
        VALUE_SPECS,
        GROWTH_SPECS,
        INCOME_SPECS,
        FACTOR_SPECS,
        SPECIAL_SPECS,
    )
    for spec in specs
}


def get_preset_spec(preset_id: str) -> PresetSpec:
    """preset_id → PresetSpec 인스턴스 반환 (Slice 13 Step 0a #60).

    gate_tiers 접근이 주 용도. ADDITIVE 점수 경로 무손상.

    Raises:
        KeyError: 미등록 preset_id.
    """
    if preset_id not in _ALL_PRESET_SPECS:
        raise KeyError(f"Unknown preset_id: {preset_id!r}")
    return _ALL_PRESET_SPECS[preset_id]


def resolve_category(preset_id: str) -> str:
    """12 preset_id → 5 카테고리 매핑.

    Args:
        preset_id: 12 preset 중 하나 (예: "buffett_quality_value").

    Returns:
        카테고리명 ("value" 등).

    Raises:
        KeyError: 미등록 preset_id.
    """
    if preset_id not in PRESET_ID_TO_CATEGORY:
        raise KeyError(f"Unknown preset_id: {preset_id!r}")
    return PRESET_ID_TO_CATEGORY[preset_id]


def format_scores_for_prompt(scores: dict[str, float]) -> str:
    """Score dict → LLM prompt 친화 문자열.

    Gate 발동(0점)은 명시적 표시. `_category_score`는 마지막 별도 줄.

    Args:
        scores: ScoringEngine.score() 반환 dict.

    Returns:
        markdown bullet 형식의 multi-line string.
    """
    lines: list[str] = []
    for key, value in scores.items():
        if key.startswith("_"):
            continue
        if value == 0.0:
            lines.append(f"- {key}: 0.0 (gate 미통과)")
        else:
            lines.append(f"- {key}: {value:.2f}")
    if "_category_score" in scores:
        lines.append("")
        lines.append(f"카테고리 평균: {scores['_category_score']:.2f}")
    return "\n".join(lines)


__all__ = [
    "PRESET_SCORERS",
    "PRESET_ID_TO_CATEGORY",
    "PresetSpec",
    "ScoringEngineBase",
    "ValueScoringEngine",
    "GrowthScoringEngine",
    "IncomeScoringEngine",
    "FactorScoringEngine",
    "SpecialScoringEngine",
    "get_scorer",
    "resolve_category",
    "get_preset_spec",
    "format_scores_for_prompt",
    "format_gate_tier_for_prompt",
]


def format_gate_tier_for_prompt(preset_id: str, tier: str) -> str:
    """Slice 13 Step 0a #60: gate tier 결과를 prompt 1줄로 포맷.

    ADDITIVE — prompt context 전용. 점수 영향 없음.
    """
    return f"## Gate Tier ({preset_id}): {tier}"
