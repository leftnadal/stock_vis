"""
이상 신호 룰별 evidence Pydantic v2 스키마 (PR-A2).

소속: apps/market_pulse/schemas (app 레이어 JSONField 검증).
역할: `AnomalySignalLog.inputs`·`threshold` JSONField의 4 Core 룰 evidence 구조 검증.
주요 심볼:
  - R02Evidence: concentration_extreme (top10_weight 임계 초과)
  - R04Evidence: vix_spike (vix_change_pct 급등)
  - R09Evidence: sector_extreme_z (섹터 rel_strength z-score 극단)
  - R12Evidence: dispersion_spike (cross-dispersion 급증)
소비처: tasks/anomaly.py의 mp_detect_anomaly_5min — evidence 저장 직전 검증.
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
