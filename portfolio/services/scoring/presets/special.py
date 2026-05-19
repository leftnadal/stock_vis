"""Slice 12 Part 1 — special category scoring adapter (스켈레톤).

카테고리: special
포함 preset: contrarian, concentrated_portfolio

Part 2: 집중도 + contrarian 점수.
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.schemas.commentary_input import CommentaryInputBase
from portfolio.services.scoring.base import ScoringEngineBase


class SpecialScoringEngine(ScoringEngineBase):
    """Special category scoring engine."""

    category: ClassVar[str] = "special"

    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 풀 구현 예정. "
            "special 카테고리: 집중도 + contrarian (concentrated_portfolio, contrarian)."
        )

    def required_metrics(self) -> list[str]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 PRESET_METRICS 기반 정의."
        )
