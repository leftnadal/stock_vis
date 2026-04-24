"""
AnalysisContext — Tier 2.5 최상위 스키마.
E1~E6 모든 LLM 진입점에 공통으로 전달되는 현재 분석 컨텍스트.

PV3 필드명 규칙 (절대 변경 금지):
  - analysis_target_portfolio (NOT portfolio)
  - wallet_background        (NOT wallet)

설계 근거: coach-llm-design-v1.md §4-5 + §8-2 (PV3)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .diagnostic import DiagnosticCard
from .holding import HoldingSummary
from .metric_result import MetricResult, StrengthWeakness
from .return_breakdown import ReturnBreakdownWithTime


class AnalysisTargetPortfolioContext(BaseModel):
    """분석 대상 Portfolio (Wallet의 부분집합)에 대한 LLM 컨텍스트."""

    model_config = ConfigDict(extra="forbid")

    portfolio_id: str = Field(..., description="Portfolio UUID.")
    portfolio_name: str | None = Field(
        None,
        description="Portfolio 이름. 임시 그룹이면 None (save_type='temporary').",
    )
    preset_id: str = Field(..., description="적용된 프리셋 식별자 (예: 'garp').")
    preset_name: str = Field(..., description="프리셋 UI 이름.")
    preset_category: str = Field(
        ...,
        description="프리셋 카테고리 (value | growth | income | factor | special).",
    )
    save_type: str = Field(
        ...,
        description="'named' 또는 'temporary'.",
    )
    holdings_summary: list[HoldingSummary] = Field(
        ...,
        description="Portfolio에 포함된 종목 요약 리스트.",
    )
    holding_count: int = Field(..., ge=0, description="holdings_summary 길이.")
    core_metric_results: list[MetricResult] = Field(
        default_factory=list,
        description="Core tier 지표 결과.",
    )
    supporting_metric_results: list[MetricResult] = Field(
        default_factory=list,
        description="Supporting tier 지표 결과.",
    )
    context_metric_results: list[MetricResult] = Field(
        default_factory=list,
        description="Context tier 지표 결과.",
    )
    strengths: list[StrengthWeakness] = Field(
        default_factory=list,
        max_length=3,
        description="상위 3개 강점 지표.",
    )
    weaknesses: list[StrengthWeakness] = Field(
        default_factory=list,
        max_length=3,
        description="상위 3개 약점 지표.",
    )
    diagnostic_cards: list[DiagnosticCard] = Field(
        default_factory=list,
        max_length=3,
        description="E2 진단 카드 최대 3개.",
    )
    return_breakdown: ReturnBreakdownWithTime = Field(
        ...,
        description="Portfolio 수익률 breakdown (저장시점 + 현재).",
    )
    overrides_applied: dict | None = Field(
        None,
        description=(
            "E5/E6 조정 분석인 경우 적용된 overrides. "
            "예: {'metric_id': 'roic', 'new_threshold': 0.20}. "
            "원본 프리셋이면 None."
        ),
    )


class WalletBackgroundContext(BaseModel):
    """Wallet 배경 컨텍스트 — PV5 정책에 따라 진입점별 주입 정도가 다름."""

    model_config = ConfigDict(extra="forbid")

    wallet_id: str = Field(..., description="Wallet UUID.")
    total_holdings_count: int = Field(
        ...,
        ge=0,
        description="Wallet 내 WalletHolding 전체 개수.",
    )
    excluded_from_this_portfolio_count: int = Field(
        ...,
        ge=0,
        description="Wallet에 있지만 현재 Portfolio에 포함되지 않은 종목 수.",
    )
    sector_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="섹터명 → 비중 (0~1).",
    )
    industry_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="산업명 → 비중 (0~1).",
    )
    total_value_estimate: str = Field(
        ...,
        description="'high' | 'mid' | 'low' 버킷. 정확한 금액 노출 회피.",
    )
    return_breakdown: ReturnBreakdownWithTime = Field(
        ...,
        description="Wallet 전체 수익률 breakdown.",
    )
    historical_snapshots_available: int = Field(
        ...,
        ge=0,
        description="WalletSnapshot 개수 (A1 시계열 활용).",
    )
    notable_recent_changes: list[str] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "자연어 변화 요약 최대 5개. "
            "예: ['Tech 비중 40% → 55%', 'ABC 신규 편입']."
        ),
    )


class AnalysisContext(BaseModel):
    """
    Tier 2.5 최상위 스키마.
    모든 E1~E6 진입점에 공통으로 전달.

    PV3 규칙: `analysis_target_portfolio`, `wallet_background` 이름 고정.
    """

    model_config = ConfigDict(extra="forbid")

    analysis_target_portfolio: AnalysisTargetPortfolioContext = Field(
        ...,
        description="분석 대상 Portfolio. LLM이 '당신의 포트폴리오'로 지칭할 대상.",
    )
    wallet_background: WalletBackgroundContext = Field(
        ...,
        description="Wallet 전체 배경 컨텍스트. 대화에서 배경 대조용.",
    )
    # Phase 2 확장 슬롯 (MVP는 모두 None)
    watchlist_context: dict | None = Field(
        None,
        description="Phase 2 Watchlist 기능 연동 슬롯.",
    )
    monitoring_indicators_context: dict | None = Field(
        None,
        description="Phase 2 모니터링 지표 연동 슬롯.",
    )
    thesis_notes_context: dict | None = Field(
        None,
        description="Phase 2 Thesis 노트 연동 슬롯.",
    )
