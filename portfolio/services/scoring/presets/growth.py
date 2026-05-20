"""Slice 12 Part 2 — growth category scoring adapter (풀 구현).

포함 preset:
  - garp: PEG + EPS/Revenue 성장 (PRESET_METRICS core 3)
  - quality_growth: ROIC + 안정성 + 성장 (core 4)

PEG는 lower-is-better. 호출자가 정규화 시 inverse 적용 (peg_ratio → peg_score).
본 모듈은 정규화된 'peg_score' 키 가정.
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.services.scoring.preset_spec import PresetSpec


GROWTH_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="garp",
        category="growth",
        weights={
            "peg_ratio": 0.40,  # 정규화 시 inverse (lower-is-better)
            "eps_growth_yoy": 0.30,
            "revenue_growth_yoy": 0.30,
        },
        gate=None,
        description="GARP — PEG + growth 균형",
    ),
    PresetSpec(
        preset_id="quality_growth",
        category="growth",
        weights={
            "roic": 0.30,
            "roic_consistency_5y": 0.20,
            "revenue_growth_yoy": 0.25,
            "eps_growth_yoy": 0.25,
        },
        gate=None,
        description="Quality compounder — ROIC + 성장 균형",
    ),
]


class GrowthScoringEngine(ScoringEngineBase):
    """Growth category — garp + quality_growth."""

    category: ClassVar[str] = "growth"

    def score(self, metrics: dict[str, float]) -> dict[str, Any]:
        result: dict[str, float] = {}
        for spec in GROWTH_SPECS:
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
        return sorted({k for spec in GROWTH_SPECS for k in spec.weights})
