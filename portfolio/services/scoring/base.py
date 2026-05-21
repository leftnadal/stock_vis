"""Slice 12 Part 1-2 — preset scoring engine abstract base class.

Slice 11 Part 1 `CommentaryInputBase` 패턴 미러:
  - Pydantic v2 (frozen + extra=forbid)
  - 5 sub class per category (value/growth/income/factor/special)
  - Part 1: 스켈레톤 (NotImplementedError)
  - Part 2: 풀 구현 + utility (`_apply_gate`, `_weighted_sum`)

Part 2 signature 변경 (Part 1 inventory `score(input_data)` → `score(metrics)`):
  - 호출자는 미리 정규화된 metrics dict (지표명 → 0~1 정규값)을 전달
  - 정규화 책임은 호출자 (Part 3 smoke 단계 통합 시점)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, ConfigDict


class ScoringEngineBase(ABC, BaseModel):
    """Preset scoring engine abstract base.

    Sub class per category:
      - ValueScoringEngine (value)
      - GrowthScoringEngine (growth)
      - IncomeScoringEngine (income)
      - FactorScoringEngine (factor)
      - SpecialScoringEngine (special)

    설계 원칙 (Slice 11 Part 1 미러):
      - frozen=True: 인스턴스 immutable
      - extra="forbid": 의도하지 않은 필드 차단
      - @abstractmethod: sub class에서 score/required_metrics 구현 강제
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ClassVar — 카테고리 식별 (sub class에서 override)
    category: ClassVar[str] = ""

    @abstractmethod
    def score(self, metrics: dict[str, float]) -> dict[str, Any]:
        """카테고리별 scoring 로직.

        Args:
            metrics: 지표명 → 정규화된 값 (0~1) dict.
                     정규화 책임은 호출자 (Part 3 smoke 통합 시점).

        Returns:
            dict with:
              - preset_id별 점수 (0~100)
              - `_category_score`: 카테고리 평균 점수 (0~100)
        """

    @abstractmethod
    def required_metrics(self) -> list[str]:
        """이 카테고리 scoring이 필요로 하는 지표 키 목록 (전체 preset 합집합)."""

    # ============================================================
    # D2-B utility (Part 2 신규)
    # ============================================================

    @staticmethod
    def _apply_gate(
        metrics: dict[str, float],
        gate: Optional[dict[str, float | str]],
    ) -> bool:
        """D2-B: gate 임계 통과 여부 판정.

        gate=None → 항상 True.
        gate에 `_op` 키가 없으면 기본 "gte".
        지표 부재 시 미통과 (False).

        Args:
            metrics: 측정값 dict.
            gate: {"metric": threshold, "_op": "gte|lte|gt|lt"} 또는 None.

        Returns:
            True 통과 / False 미통과 (score=0 강제).
        """
        if gate is None:
            return True
        op = gate.get("_op", "gte")
        for key, threshold in gate.items():
            if key.startswith("_"):
                continue
            value = metrics.get(key)
            if value is None:
                return False
            if op == "gte" and value < threshold:
                return False
            if op == "lte" and value > threshold:
                return False
            if op == "gt" and value <= threshold:
                return False
            if op == "lt" and value >= threshold:
                return False
        return True

    @staticmethod
    def _evaluate_gate_tier(
        metrics: dict[str, float],
        gate_tiers: Optional[dict[str, float | str]],
    ) -> str:
        """Slice 13 Step 0a #60: 3단 게이트 평가 (ADDITIVE).

        ★ 점수 경로와 완전 분리. 결과는 commentary prompt context로만 사용.
        ★ 기존 `_apply_gate` 및 `score=0.0` 로직과 충돌 없음.

        gate_tiers=None → 항상 "pass" (기존 12 preset 동작 불변 보증).
        지표 부재 → "fail" (보수적, _apply_gate 동일 정책).

        Args:
            metrics: 측정값 dict.
            gate_tiers: {
                "metric": <name>,
                "fail_below": <float>,
                "warn_below": <float>,
                "_op": "gte|lte|gt|lt"  # 옵션, 기본 "gte"
            } 또는 None.

        Returns:
            "pass" | "warn" | "fail" — 점수에 영향 없음, prompt context 전용.
        """
        if gate_tiers is None:
            return "pass"
        metric_name = gate_tiers.get("metric")
        if not isinstance(metric_name, str):
            return "fail"
        value = metrics.get(metric_name)
        if value is None:
            return "fail"
        fail_below = gate_tiers.get("fail_below")
        warn_below = gate_tiers.get("warn_below")
        if not isinstance(fail_below, (int, float)) or not isinstance(
            warn_below, (int, float)
        ):
            return "fail"
        op = gate_tiers.get("_op", "gte")
        # gte/gt: 값이 클수록 좋음 (예: dividend_yield)
        if op in ("gte", "gt"):
            if value < fail_below:
                return "fail"
            if value < warn_below:
                return "warn"
            return "pass"
        # lte/lt: 값이 작을수록 좋음 (예: debt_ratio)
        if op in ("lte", "lt"):
            if value > fail_below:
                return "fail"
            if value > warn_below:
                return "warn"
            return "pass"
        return "fail"

    @staticmethod
    def _weighted_sum(
        metrics: dict[str, float],
        weights: dict[str, float],
    ) -> float:
        """D2-B: 가중합 계산.

        지표 부재 시 0으로 처리 (gate가 사전 차단 가정).
        정규화는 호출자 책임 (카테고리별 자유도).
        """
        return sum(
            metrics.get(name, 0.0) * weight
            for name, weight in weights.items()
        )

    @staticmethod
    def _normalize_to_0_100(raw: float) -> float:
        """가중합 결과(0~1 기대)를 0~100으로 정규화 + clip.

        지표값이 0~1 정규화 가정이므로 raw도 0~1. 100배 후 clip.
        """
        return max(0.0, min(100.0, raw * 100.0))
