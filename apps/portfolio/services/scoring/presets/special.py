"""Slice 12 Part 2 — special category scoring adapter (풀 구현).

포함 preset:
  - contrarian: 저PER/저PBR + 52w 고점 대비 하락 + F-score
  - concentrated_portfolio: HHI + 섹터 HHI + 상위 비중 + 보유 종목 수

direction_override (Slice 11 Part 1 inventory): contrarian은 pe_ratio higher-is-better
역발상 해석. 본 모듈은 호출자가 정규화 시 contrarian 해석 적용 가정.
"""

from __future__ import annotations

from typing import Any, ClassVar

from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.services.scoring.preset_spec import PresetSpec

SPECIAL_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="contrarian",
        category="special",
        weights={
            "pe_ratio": 0.25,  # contrarian direction_override
            "pb_ratio": 0.25,  # contrarian direction_override
            "pct_from_52w_high": 0.30,  # 하락폭 클수록 contrarian 매수 기회
            "f_score_total": 0.20,
        },
        gate=None,
        description="Contrarian — 시장 저평가 + 재무 건전성",
    ),
    PresetSpec(
        preset_id="concentrated_portfolio",
        category="special",
        weights={
            "hhi_concentration": 0.25,
            "sector_hhi": 0.20,
            "top3_weight": 0.15,
            "holding_count": 0.10,
            "portfolio_beta": 0.10,
            "max_position_weight": 0.10,
            "avg_correlation": 0.10,
        },
        gate=None,
        description="Concentrated — 집중도 + 상관관계 종합 진단",
    ),
]


class SpecialScoringEngine(ScoringEngineBase):
    """Special category — contrarian + concentrated_portfolio."""

    category: ClassVar[str] = "special"

    def score(self, metrics: dict[str, float]) -> dict[str, Any]:
        result: dict[str, float] = {}
        for spec in SPECIAL_SPECS:
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
        return sorted({k for spec in SPECIAL_SPECS for k in spec.weights})
