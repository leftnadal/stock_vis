"""Slice 12 Part 1 — growth category scoring adapter (스켈레톤).

카테고리: growth
포함 preset: garp, quality_growth

Part 2: PEG + growth quality 점수.
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.schemas.commentary_input import CommentaryInputBase
from portfolio.services.scoring.base import ScoringEngineBase


class GrowthScoringEngine(ScoringEngineBase):
    """Growth category scoring engine."""

    category: ClassVar[str] = "growth"

    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 풀 구현 예정. "
            "growth 카테고리: PEG + growth quality (garp, quality_growth)."
        )

    def required_metrics(self) -> list[str]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 PRESET_METRICS 기반 정의."
        )
