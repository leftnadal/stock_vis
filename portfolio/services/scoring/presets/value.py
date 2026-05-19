"""Slice 12 Part 1 — value category scoring adapter (스켈레톤).

카테고리: value (presets.py 기준)
포함 preset: buffett_quality_value, piotroski_f_score

Part 1: 스켈레톤 (NotImplementedError raise).
Part 2: 풀 구현 (ROIC + 안정성 점수 등 카테고리별 logic).
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.schemas.commentary_input import CommentaryInputBase
from portfolio.services.scoring.base import ScoringEngineBase


class ValueScoringEngine(ScoringEngineBase):
    """Value category scoring engine."""

    category: ClassVar[str] = "value"

    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 풀 구현 예정. "
            "value 카테고리: ROIC + 안정성 점수 (buffett_quality_value, piotroski_f_score)."
        )

    def required_metrics(self) -> list[str]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 PRESET_METRICS 기반 정의."
        )
