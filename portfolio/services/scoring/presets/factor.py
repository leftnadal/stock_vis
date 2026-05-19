"""Slice 12 Part 1 — factor category scoring adapter (스켈레톤).

카테고리: factor
포함 preset: quality_factor, low_volatility, price_momentum, multi_factor

Part 2: 5+ 팩터 합성 점수.
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.schemas.commentary_input import CommentaryInputBase
from portfolio.services.scoring.base import ScoringEngineBase


class FactorScoringEngine(ScoringEngineBase):
    """Factor category scoring engine."""

    category: ClassVar[str] = "factor"

    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 풀 구현 예정. "
            "factor 카테고리: 5+ 팩터 합성 (quality_factor, low_volatility, "
            "price_momentum, multi_factor)."
        )

    def required_metrics(self) -> list[str]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 PRESET_METRICS 기반 정의."
        )
