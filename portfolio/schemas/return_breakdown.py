"""
ReturnBreakdown 스키마군 — 수익률 추적(RV1~RV4) 결과를 LLM에 전달.

설계 근거: return-tracking-design-v1.md §3-1, §4~5
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ScopeType(StrEnum):
    """수익률 breakdown의 스코프."""

    PORTFOLIO = "portfolio"
    WALLET = "wallet"


class ContributionItem(BaseModel):
    """기여도 단일 항목 (종목 또는 카테고리 리프)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="종목명 또는 카테고리명.")
    weight: Decimal = Field(..., description="비중 (0~1).")
    return_rate: Decimal = Field(..., description="해당 항목의 수익률.")
    contribution_pp: Decimal = Field(
        ...,
        description="전체 수익률에 대한 기여도 (percentage point).",
    )

    # Example:
    # {"name": "NVDA", "weight": "0.25", "return_rate": "0.32", "contribution_pp": "0.08"}


class CategoryBreakdown(BaseModel):
    """카테고리별 수익률 분해 (섹터/산업 등). 재귀 구조 지원."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ..., description="카테고리명 (예: 'Technology', 'Semiconductors')."
    )
    weight: Decimal = Field(..., description="전체 내 카테고리 비중 (0~1).")
    return_rate: Decimal = Field(..., description="카테고리 가중 평균 수익률.")
    contribution_pp: Decimal = Field(
        ...,
        description="전체 수익률에 대한 카테고리 기여도 (pp).",
    )
    children: list["CategoryBreakdown"] = Field(
        default_factory=list,
        description="하위 카테고리 (예: 섹터 → 산업).",
    )
    holdings: list[ContributionItem] = Field(
        default_factory=list,
        description="리프 레벨 종목 목록. children이 비어있을 때 의미.",
    )

    # Example (섹터 → 산업 → 종목 중첩):
    # {
    #   "name": "Technology", "weight": "0.6",
    #   "return_rate": "0.15", "contribution_pp": "0.09",
    #   "children": [{
    #     "name": "Semiconductors", "weight": "0.6",
    #     "return_rate": "0.22", "contribution_pp": "0.132",
    #     "children": [],
    #     "holdings": [{"name": "NVDA", "weight": "1.0",
    #                   "return_rate": "0.22", "contribution_pp": "0.22"}]
    #   }],
    #   "holdings": []
    # }


# Pydantic v2 재귀 참조 해결
CategoryBreakdown.model_rebuild()


class ReturnBreakdown(BaseModel):
    """특정 시점의 Portfolio 또는 Wallet 수익률 breakdown 스냅샷."""

    model_config = ConfigDict(extra="forbid")

    scope_type: ScopeType = Field(..., description="breakdown 대상 (portfolio/wallet).")
    scope_id: str = Field(
        ...,
        description="Portfolio UUID 또는 Wallet UUID (scope_type에 따라).",
    )
    calculated_at: datetime = Field(
        ...,
        description="계산 시점. ISO 8601 직렬화.",
    )
    total_return: Decimal = Field(..., description="전체 수익률 (-1 ~ ∞).")
    total_value: Decimal = Field(..., description="현재 평가금액.")
    total_cost_basis: Decimal = Field(..., description="총 원가 (매수 비용 합).")
    by_sector: list[CategoryBreakdown] = Field(
        default_factory=list,
        description="섹터별 수익률 분해. 필요 시 industry까지 nested.",
    )
    top_contributors: list[ContributionItem] = Field(
        default_factory=list,
        max_length=5,
        description="수익률 기여 상위 종목 (최대 5).",
    )
    bottom_contributors: list[ContributionItem] = Field(
        default_factory=list,
        max_length=5,
        description="수익률 기여 하위 종목 (최대 5).",
    )


class ReturnBreakdownWithTime(BaseModel):
    """시간 차원을 갖는 breakdown (RV4-b: 저장시점 + 현재 + 델타)."""

    model_config = ConfigDict(extra="forbid")

    at_save_time: ReturnBreakdown | None = Field(
        None,
        description="저장 시점 breakdown. Saved Analysis에만 존재. Temp면 None.",
    )
    current: ReturnBreakdown = Field(
        ...,
        description="현재 시점에서 재계산된 breakdown.",
    )
    delta_since_save: dict | None = Field(
        None,
        description=(
            "저장 시점 대비 변화. 예: "
            "{'total_return_change_pp': 0.03, 'period_days': 90}. "
            "at_save_time이 None이면 None."
        ),
    )

    # Example:
    # {
    #   "at_save_time": {...ReturnBreakdown...},
    #   "current":      {...ReturnBreakdown...},
    #   "delta_since_save": {"total_return_change_pp": 0.03, "period_days": 90}
    # }
