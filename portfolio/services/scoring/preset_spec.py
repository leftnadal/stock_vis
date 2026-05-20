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
