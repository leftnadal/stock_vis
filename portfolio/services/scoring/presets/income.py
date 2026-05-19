"""Slice 12 Part 1 — income category scoring adapter (스켈레톤).

카테고리: income
포함 preset: dividend_growth, shareholder_yield

Part 2: dividend yield + dividend growth 점수.
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.schemas.commentary_input import CommentaryInputBase
from portfolio.services.scoring.base import ScoringEngineBase


class IncomeScoringEngine(ScoringEngineBase):
    """Income category scoring engine."""

    category: ClassVar[str] = "income"

    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 풀 구현 예정. "
            "income 카테고리: dividend yield + 배당 성장 (dividend_growth, shareholder_yield)."
        )

    def required_metrics(self) -> list[str]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 PRESET_METRICS 기반 정의."
        )
