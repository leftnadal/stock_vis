"""
intraday 레짐 도메인 JSONField Pydantic v2 스키마 (PR-A2).

소속: apps/market_pulse/schemas (app 레이어 JSONField 검증).
역할: `RegimeSnapshot.inputs`·`fired_rules` JSONField의 14 매크로지표 + 발동 룰 검증.
주요 심볼:
  - IndicatorValue: 단일 지표(value, source, fetched_at)
  - IndicatorsSnapshot: 14 지표 묶음
  - MatchedCondition: 발동 룰 단위 (regime, atom 결과)
  - PendingTransition: 히스테리시스 후보(streak 누적 중)
소비처: regime/classifier.py·tasks/regime.py (intraday mp_calc_regime_15min) 저장 전 검증.
주의: 이 스키마는 **intraday 5단계 regime** 전용. packages/shared의 EOD VIX 3단계
  (DynamicRegimeCalculator)와는 별개 시스템(검증 대상 자체가 다름).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IndicatorValue(BaseModel):
    """14 거시 지표 중 1개 raw 값 + 메타데이터."""

    name: str = Field(description="지표 이름 (예: 'nfci', 'vix_level')")
    value: float | None = Field(default=None, description="null=데이터 누락")
    source: str = Field(description="원본 (예: 'FRED:NFCI')")
    fetched_at: str = Field(description="ISO datetime")


class IndicatorsSnapshot(BaseModel):
    """`RegimeSnapshot.inputs` — 14 지표 raw 값 + coverage."""

    indicators: list[IndicatorValue] = Field(default_factory=list)
    coverage_ratio: float = Field(ge=0.0, le=1.0, description="유효 지표 비율 (0~1)")


class MatchedCondition(BaseModel):
    """규칙 매칭 한 개 근거."""

    indicator: str
    threshold_expr: str = Field(description="비교식 (예: '>= 0', '< 30')")
    actual_value: float | None
    status: Literal["matched", "unmatched", "missing"]


class PendingTransition(BaseModel):
    """히스테리시스 후보 상태 (RegimeSnapshot.inputs.pending_transition 용)."""

    target: str = Field(description="후보 레짐 (예: 'CRISIS')")
    candidate_since: str = Field(description="ISO date")
    days_pending: int = Field(ge=0)
