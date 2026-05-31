"""Slice 12 Part 2 — income category scoring adapter (풀 구현, gate 필수).

포함 preset:
  - dividend_growth: dividend_yield + 5y growth rate + consistency
  - shareholder_yield: dividend + buyback + debt reduction 합산

D2-B gate: yield 임계 미달 시 score=0 강제 (income 본질 보호).
"""

from __future__ import annotations

from typing import Any, ClassVar

from apps.portfolio.services.scoring.base import ScoringEngineBase
from apps.portfolio.services.scoring.preset_spec import PresetSpec

INCOME_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="dividend_growth",
        category="income",
        weights={
            "dividend_yield": 0.40,
            "dividend_growth_rate_5y": 0.35,
            "dividend_growth_consistency_5y": 0.25,
        },
        gate={"dividend_yield": 0.02, "_op": "gte"},  # 2% 미만 컷
        description="Dividend growth — yield + 5y growth + 일관성",
    ),
    PresetSpec(
        preset_id="shareholder_yield",
        category="income",
        weights={
            "shareholder_yield": 0.40,
            "dividend_yield": 0.25,
            "net_buyback_yield": 0.20,
            "net_debt_reduction_rate": 0.15,
        },
        gate={"shareholder_yield": 0.02, "_op": "gte"},  # 총 주주환원 2% 미만 컷
        description="Shareholder yield — 배당 + 자사주 + 부채감소 합",
    ),
]


class IncomeScoringEngine(ScoringEngineBase):
    """Income category — dividend_growth + shareholder_yield (gate 필수)."""

    category: ClassVar[str] = "income"

    def score(self, metrics: dict[str, float]) -> dict[str, Any]:
        result: dict[str, float] = {}
        for spec in INCOME_SPECS:
            if not self._apply_gate(metrics, spec.gate):
                result[spec.preset_id] = 0.0
                continue
            raw = self._weighted_sum(metrics, spec.weights)
            result[spec.preset_id] = self._normalize_to_0_100(raw)
        preset_scores = [v for k, v in result.items() if not k.startswith("_")]
        result["_category_score"] = (
            sum(preset_scores) / len(preset_scores) if preset_scores else 0.0
        )
        return result

    def required_metrics(self) -> list[str]:
        return sorted({k for spec in INCOME_SPECS for k in spec.weights})
