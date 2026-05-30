"""Slice 12 Part 2 — value category scoring adapter (풀 구현).

카테고리: value
포함 preset (Slice 11 Part 1 inventory 기준):
  - buffett_quality_value: ROIC + ROE + 안정성 (core 4)
  - piotroski_f_score: F-score 단일 (core 1)

PRESET_METRICS의 core 메트릭을 균등 가중. 가중치 합 1.0 ± 0.001.
gate 없음 (value 진입 임계 별도 미설정).
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.services.scoring.preset_spec import PresetSpec

VALUE_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="buffett_quality_value",
        category="value",
        weights={
            "roic": 0.30,
            "roe": 0.25,
            "roic_consistency_5y": 0.25,
            "earnings_consistency_5y": 0.20,
        },
        gate=None,
        description="Warren Buffett quality value — ROIC + 안정성",
    ),
    PresetSpec(
        preset_id="piotroski_f_score",
        category="value",
        weights={"f_score_total": 1.0},
        gate=None,
        description="Piotroski F-Score 9 항목 합",
    ),
]


class ValueScoringEngine(ScoringEngineBase):
    """Value category scoring engine — buffett_quality_value + piotroski_f_score."""

    category: ClassVar[str] = "value"

    def score(self, metrics: dict[str, float]) -> dict[str, Any]:
        result: dict[str, float] = {}
        for spec in VALUE_SPECS:
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
        return sorted({k for spec in VALUE_SPECS for k in spec.weights})
