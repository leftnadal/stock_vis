"""Slice 12 Part 2 — factor category scoring adapter (풀 구현, 4 preset).

포함 preset:
  - quality_factor: ROIC + ROE + 마진 + 안정성
  - low_volatility: 변동성 + 베타 + drawdown (gate: beta ≤ 1.2)
  - price_momentum: 12/6/3개월 수익 + relative strength
  - multi_factor: 5 composite (value/quality/growth/momentum/low_vol)

low_volatility에 gate 적용 (beta 1.2 초과 시 cut).
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.services.scoring.preset_spec import PresetSpec

FACTOR_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="quality_factor",
        category="factor",
        weights={
            "roic": 0.30,
            "roe": 0.25,
            "gross_margin": 0.20,
            "roe_stability_5y": 0.25,
        },
        gate=None,
        description="Quality factor — 수익성 + 안정성",
    ),
    PresetSpec(
        preset_id="low_volatility",
        category="factor",
        weights={
            "volatility_1y": 0.30,  # 정규화 시 inverse
            "beta": 0.20,            # 정규화 시 inverse
            "downside_deviation": 0.25,
            "max_drawdown_1y": 0.15,
            "portfolio_volatility": 0.10,
        },
        gate={"beta": 1.2, "_op": "lte"},  # 베타 1.2 초과 컷
        description="Low volatility — 변동성·베타 낮을수록 우수",
    ),
    PresetSpec(
        preset_id="price_momentum",
        category="factor",
        weights={
            "return_12m": 0.40,
            "return_6m": 0.25,
            "return_3m": 0.15,
            "relative_strength": 0.20,
        },
        gate=None,
        description="Price momentum — 12/6/3개월 수익 + RS",
    ),
    PresetSpec(
        preset_id="multi_factor",
        category="factor",
        weights={
            "composite_value": 0.20,
            "composite_quality": 0.20,
            "composite_growth": 0.20,
            "composite_momentum": 0.20,
            "composite_low_vol": 0.20,
        },
        gate=None,
        description="Multi-factor — 5 팩터 균등 합성",
    ),
]


class FactorScoringEngine(ScoringEngineBase):
    """Factor category — 4 preset (학술 팩터)."""

    category: ClassVar[str] = "factor"

    def score(self, metrics: dict[str, float]) -> dict[str, Any]:
        result: dict[str, float] = {}
        for spec in FACTOR_SPECS:
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
        return sorted({k for spec in FACTOR_SPECS for k in spec.weights})
