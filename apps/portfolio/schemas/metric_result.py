"""
MetricResult (Pydantic) — LLM에 전달할 지표 결과.
Django 모델 portfolio.models.MetricResult 와는 별개의 DTO.

설계 근거: coach-llm-design-v1.md §4-5

Slice 8 Part 1 Step 1 #27 추가: Optional[TimeSeriesContext] 시계열 필드
(기존 fixture는 None default로 backward-compat 유지).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from apps.portfolio.schemas.commentary_input import TimeSeriesContext


class MetricTier(StrEnum):
    """프리셋 내 지표의 중요도 계층."""

    CORE = "core"
    SUPPORTING = "supporting"
    CONTEXT = "context"


class MetricResult(BaseModel):
    """단일 지표의 계산 결과 + 해석 맥락."""

    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(..., description="지표 식별자 (예: 'roic').")
    metric_display_name: str = Field(
        ...,
        description="UI 표시용 이름 (예: '투하자본수익률').",
    )
    tier: MetricTier = Field(..., description="프리셋 내 계층.")
    value: Decimal | None = Field(
        None,
        description="원시 값. 결측치면 None.",
    )
    percentile: Decimal | None = Field(
        None,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="퍼센타일 (0~1). 전체 유니버스/섹터/산업 내 위치.",
    )
    percentile_scope: str = Field(
        "industry",
        description="percentile 산출 기준 (universe | sector | industry).",
    )
    level_tag: str = Field(
        ...,
        description="5단계 레벨 태그 (excellent | good | moderate | weak | critical).",
    )
    threshold_applied: Decimal | None = Field(
        None,
        description="프리셋에서 적용한 임계값. 조정(레벨 1)이 있으면 덮어쓴 값.",
    )
    passed_threshold: bool | None = Field(
        None,
        description="임계값 통과 여부. 임계값 개념이 없는 지표는 None.",
    )
    time_series: TimeSeriesContext | None = Field(
        None,
        description=(
            "Slice 8 #27: 4분기·12분기 시계열 컨텍스트. "
            "FMP 미가용 또는 시계열 부재 시 None (backward-compat)."
        ),
    )

    # Example:
    # {
    #   "metric_id": "roic",
    #   "metric_display_name": "투하자본수익률",
    #   "tier": "core",
    #   "value": "0.283",
    #   "percentile": "0.88",
    #   "percentile_scope": "industry",
    #   "level_tag": "excellent",
    #   "threshold_applied": "0.15",
    #   "passed_threshold": true
    # }


class StrengthWeakness(BaseModel):
    """Portfolio 내 강점/약점 상위 지표."""

    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(..., description="지표 식별자.")
    metric_display_name: str = Field(..., description="UI 표시용 이름.")
    level_tag: str = Field(
        ...,
        description="excellent | good | moderate | weak | critical.",
    )
    rank_within_portfolio: int = Field(
        ...,
        ge=1,
        description="Portfolio 내 순위 (1부터 시작, 1=가장 강점 또는 가장 약점).",
    )
    reason_hint: str = Field(
        ...,
        description="요약 (예: '산업 상위 5%', '임계값 미달 -30%').",
    )

    # Example:
    # {
    #   "metric_id": "roic",
    #   "metric_display_name": "투하자본수익률",
    #   "level_tag": "excellent",
    #   "rank_within_portfolio": 1,
    #   "reason_hint": "5개 종목 중 3개가 산업 상위 25% 이내"
    # }
