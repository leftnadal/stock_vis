"""이상 신호 룰별 evidence Pydantic v2 스키마 (PR-A2).

`AnomalySignalLog.inputs` / `threshold` JSONField 검증용.
4 Core 룰: R02 concentration_extreme, R04 vix_spike,
            R09 sector_extreme_z, R12 dispersion_spike.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class R02Evidence(BaseModel):
    """concentration_extreme — 상위 5종목 기여도 극단."""

    universe: str = Field(description="대상 universe (예: 'SPY')")
    top5_contrib: float = Field(ge=0.0, le=1.0, description="상위 5종목 비중 (0~1)")
    top5_pct_1y: float = Field(ge=0.0, le=1.0, description="1년 백분위")
    threshold_pct: float = Field(default=0.85, ge=0.0, le=1.0)
    breadth_50ma: float = Field(description="50일 이평 위 비율 (보조)")


class R04Evidence(BaseModel):
    """vix_spike — VIX 급등."""

    vix_today: float = Field(ge=0.0)
    vix_yesterday: float = Field(ge=0.0)
    pct_change: float = Field(description="일간 변화율 (음수 가능)")
    vix_pct_1y: float = Field(ge=0.0, le=1.0)
    threshold_abs: float = Field(default=30.0, ge=0.0)
    threshold_pct: float = Field(default=0.80, ge=0.0, le=1.0)


class R09Evidence(BaseModel):
    """sector_extreme_z — 섹터 Z-score 극단."""

    sector_etf: str = Field(description="섹터 ETF 심볼 ('XLE', 'XLK' 등)")
    z_score_temporal: float = Field(description="자기 시계열 대비 Z-score")
    z_score_cross: float = Field(description="섹터 간 cross-sectional Z-score")
    threshold_z: float = Field(default=2.5, ge=0.0)
    direction: Literal["up", "down"] = Field(description="방향")


class R12Evidence(BaseModel):
    """dispersion_spike — 섹터 분산 극단."""

    dispersion_today: float = Field(ge=0.0)
    dispersion_pct_1y: float = Field(ge=0.0, le=1.0)
    threshold_pct: float = Field(default=0.85, ge=0.0, le=1.0)
