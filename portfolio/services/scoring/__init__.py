"""Slice 12 Part 1 — preset scoring registry.

Slice 11 Part 1 `COMMENTARY_INPUT_CLASSES` 패턴 미러 — 5 카테고리 dict 매핑.
"""

from __future__ import annotations

from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.services.scoring.presets.factor import FactorScoringEngine
from portfolio.services.scoring.presets.growth import GrowthScoringEngine
from portfolio.services.scoring.presets.income import IncomeScoringEngine
from portfolio.services.scoring.presets.special import SpecialScoringEngine
from portfolio.services.scoring.presets.value import ValueScoringEngine


PRESET_SCORERS: dict[str, type[ScoringEngineBase]] = {
    "value": ValueScoringEngine,
    "growth": GrowthScoringEngine,
    "income": IncomeScoringEngine,
    "factor": FactorScoringEngine,
    "special": SpecialScoringEngine,
}


def get_scorer(category: str) -> ScoringEngineBase:
    """카테고리명으로 scorer 인스턴스 반환.

    Args:
        category: "value" / "growth" / "income" / "factor" / "special"
                  (presets.py 카테고리, Slice 11 PresetType은 adapter에서 매핑).

    Returns:
        ScoringEngineBase 하위 인스턴스 (frozen Pydantic).

    Raises:
        KeyError: category가 PRESET_SCORERS에 없을 때.
    """
    cls = PRESET_SCORERS[category]
    return cls()


__all__ = [
    "PRESET_SCORERS",
    "ScoringEngineBase",
    "ValueScoringEngine",
    "GrowthScoringEngine",
    "IncomeScoringEngine",
    "FactorScoringEngine",
    "SpecialScoringEngine",
    "get_scorer",
]
