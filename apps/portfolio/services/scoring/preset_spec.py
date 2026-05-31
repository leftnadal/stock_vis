"""Slice 12 Part 2 — PresetSpec Pydantic schema (D3-B).

Preset scoring 공식 정의 schema. Slice 11 Part 1 input/output schema 패턴 정합:
  - frozen=True, extra="forbid" → 런타임 typo·필드 drift 사전 차단
  - weights sum 1.0 ± 0.001 validator (런타임 합산 오류 차단)
  - category Literal 5종 (value/growth/income/factor/special)

D2-B: weighted_sum + threshold gate 혼합 패턴. gate는 선택적 필드.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

CategoryLiteral = Literal["value", "growth", "income", "factor", "special"]
GateOp = Literal["gte", "lte", "gt", "lt"]


class PresetSpec(BaseModel):
    """Preset scoring spec — weights + (선택) gate.

    Attributes:
        preset_id: 12 preset 중 하나 (예: "buffett_quality_value").
        category: 5 카테고리 중 하나.
        weights: 지표명 → 가중치. 합 1.0 ± 0.001, 모두 ≥ 0.
        gate: D2-B 임계 조건. {"metric": threshold, "_op": "gte|lte|gt|lt"} 또는 None.
        description: 사람 가독 설명.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    preset_id: str = Field(..., min_length=1)
    category: CategoryLiteral
    weights: dict[str, float] = Field(..., min_length=1)
    gate: Optional[dict[str, float | str]] = None
    # Slice 13 Step 0a #60: 3단 게이트 (ADDITIVE). 점수 경로 무손상 — pass/warn/fail
    # 결과는 commentary prompt context로만 흐른다. 기존 gate / _apply_gate / score=0
    # 로직과 완전 분리. None이면 평가 결과 항상 "pass".
    # 구조: {"metric": <name>, "fail_below": <float>, "warn_below": <float>, "_op": "gte"}
    # PLACEHOLDER: 경계값은 Slice 14 #61 calibration 대상.
    gate_tiers: Optional[dict[str, float | str]] = None
    description: str = ""

    @model_validator(mode="after")
    def _validate_weights(self) -> "PresetSpec":
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"weights sum must be 1.0 ± 0.001, got {total:.4f} "
                f"for preset {self.preset_id!r}"
            )
        if any(w < 0 for w in self.weights.values()):
            raise ValueError(
                f"weights must be non-negative for preset {self.preset_id!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_gate_op(self) -> "PresetSpec":
        if self.gate is None:
            return self
        op = self.gate.get("_op", "gte")
        if op not in ("gte", "lte", "gt", "lt"):
            raise ValueError(
                f"gate _op must be one of (gte,lte,gt,lt), got {op!r} "
                f"for preset {self.preset_id!r}"
            )
        # gate에 metric 키가 최소 1개 있어야 함 (_op 제외)
        metric_keys = [k for k in self.gate if not k.startswith("_")]
        if not metric_keys:
            raise ValueError(
                f"gate must have at least one metric threshold "
                f"for preset {self.preset_id!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_gate_tiers(self) -> "PresetSpec":
        """Slice 13 Step 0a #60: gate_tiers 구조 검증 (ADDITIVE).

        gate_tiers=None → skip. 정의 시:
        - "metric" 키 필수 (str)
        - "fail_below", "warn_below" 모두 float (warn_below > fail_below)
        - "_op"은 옵션, 기본 "gte" (gte일 때 fail_below < warn_below).
        """
        if self.gate_tiers is None:
            return self
        metric = self.gate_tiers.get("metric")
        if not isinstance(metric, str) or not metric:
            raise ValueError(
                f"gate_tiers.metric must be non-empty str for preset {self.preset_id!r}"
            )
        fail_below = self.gate_tiers.get("fail_below")
        warn_below = self.gate_tiers.get("warn_below")
        if not isinstance(fail_below, (int, float)) or not isinstance(
            warn_below, (int, float)
        ):
            raise ValueError(
                f"gate_tiers.fail_below and warn_below must be numeric "
                f"for preset {self.preset_id!r}"
            )
        op = self.gate_tiers.get("_op", "gte")
        if op not in ("gte", "lte", "gt", "lt"):
            raise ValueError(
                f"gate_tiers._op must be one of (gte,lte,gt,lt), got {op!r} "
                f"for preset {self.preset_id!r}"
            )
        # gte/gt: 값이 클수록 통과 → fail_below < warn_below 강제
        # lte/lt: 값이 작을수록 통과 → fail_below > warn_below 강제
        if op in ("gte", "gt") and fail_below >= warn_below:
            raise ValueError(
                f"gate_tiers: fail_below must be < warn_below for _op={op!r} "
                f"for preset {self.preset_id!r}"
            )
        if op in ("lte", "lt") and fail_below <= warn_below:
            raise ValueError(
                f"gate_tiers: fail_below must be > warn_below for _op={op!r} "
                f"for preset {self.preset_id!r}"
            )
        return self
