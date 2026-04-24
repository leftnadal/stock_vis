"""
Mock AnalysisContext fixtures (Django 독립).

Pydantic Schema 만으로 구성. DB 접근 없음.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from portfolio.schemas import (
    AnalysisContext,
    AnalysisTargetPortfolioContext,
    CategoryBreakdown,
    ContributionItem,
    DiagnosticCard,
    HoldingSummary,
    MetricResult,
    MetricTier,
    ReturnBreakdown,
    ReturnBreakdownWithTime,
    ScopeType,
    Severity,
    StrengthWeakness,
    StructuralOrSingle,
    WalletBackgroundContext,
)


_NOW = datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc)


def _portfolio_return(total_return: str = "0.14") -> ReturnBreakdownWithTime:
    current = ReturnBreakdown(
        scope_type=ScopeType.PORTFOLIO,
        scope_id="11111111-1111-1111-1111-111111111111",
        calculated_at=_NOW,
        total_return=Decimal(total_return),
        total_value=Decimal("50000.00"),
        total_cost_basis=Decimal("43860.00"),
        by_sector=[
            CategoryBreakdown(
                name="Technology",
                weight=Decimal("1.00"),
                return_rate=Decimal(total_return),
                contribution_pp=Decimal(total_return),
            ),
        ],
        top_contributors=[
            ContributionItem(
                name="NVDA", weight=Decimal("0.30"),
                return_rate=Decimal("0.32"), contribution_pp=Decimal("0.096"),
            ),
        ],
        bottom_contributors=[
            ContributionItem(
                name="INTC", weight=Decimal("0.10"),
                return_rate=Decimal("-0.05"), contribution_pp=Decimal("-0.005"),
            ),
        ],
    )
    return ReturnBreakdownWithTime(at_save_time=None, current=current, delta_since_save=None)


def _wallet_return(total_return: str = "0.08") -> ReturnBreakdownWithTime:
    current = ReturnBreakdown(
        scope_type=ScopeType.WALLET,
        scope_id="22222222-2222-2222-2222-222222222222",
        calculated_at=_NOW,
        total_return=Decimal(total_return),
        total_value=Decimal("120000.00"),
        total_cost_basis=Decimal("111111.00"),
        by_sector=[
            CategoryBreakdown(
                name="Technology", weight=Decimal("0.55"),
                return_rate=Decimal("0.12"), contribution_pp=Decimal("0.066"),
            ),
            CategoryBreakdown(
                name="Healthcare", weight=Decimal("0.20"),
                return_rate=Decimal("0.06"), contribution_pp=Decimal("0.012"),
            ),
        ],
        top_contributors=[],
        bottom_contributors=[],
    )
    return ReturnBreakdownWithTime(at_save_time=None, current=current, delta_since_save=None)


def _holdings_tech() -> list[HoldingSummary]:
    return [
        HoldingSummary(
            holding_id=f"h-{i}", stock_symbol=sym, stock_name=name,
            sector="Technology", industry="Semiconductors" if sym in {"NVDA", "AMD", "INTC"} else "Software",
            shares=Decimal("10.0"),
            weight=Decimal(w), market_value=Decimal(mv),
            unrealized_return=Decimal(ur),
            investment_thesis=thesis,
        )
        for i, (sym, name, w, mv, ur, thesis) in enumerate([
            ("NVDA",  "NVIDIA",            "0.30", "15000", "0.32", "AI 인프라 수요"),
            ("MSFT",  "Microsoft",          "0.25", "12500", "0.18", "클라우드 지속 성장"),
            ("AAPL",  "Apple",              "0.20", "10000", "0.10", "서비스 수익 확대"),
            ("GOOGL", "Alphabet",           "0.15", "7500",  "0.12", "광고 안정 + AI"),
            ("INTC",  "Intel",              "0.10", "5000",  "-0.05", "턴어라운드 기대"),
        ])
    ]


def _core_metrics() -> list[MetricResult]:
    return [
        MetricResult(
            metric_id="roic", metric_display_name="투하자본수익률",
            tier=MetricTier.CORE, value=Decimal("0.18"),
            percentile=Decimal("0.82"), percentile_scope="industry",
            level_tag="good",
            threshold_applied=Decimal("0.15"), passed_threshold=True,
        ),
        MetricResult(
            metric_id="peg_ratio", metric_display_name="PEG 비율",
            tier=MetricTier.CORE, value=Decimal("2.80"),
            percentile=Decimal("0.15"), percentile_scope="industry",
            level_tag="weak",
            threshold_applied=Decimal("1.5"), passed_threshold=False,
        ),
    ]


def _supporting_metrics() -> list[MetricResult]:
    return [
        MetricResult(
            metric_id="revenue_growth_yoy", metric_display_name="매출 성장률(YoY)",
            tier=MetricTier.SUPPORTING, value=Decimal("0.18"),
            percentile=Decimal("0.70"), percentile_scope="industry",
            level_tag="good",
            threshold_applied=None, passed_threshold=None,
        ),
    ]


def _strengths() -> list[StrengthWeakness]:
    return [
        StrengthWeakness(
            metric_id="roic", metric_display_name="투하자본수익률",
            level_tag="good", rank_within_portfolio=1,
            reason_hint="5종목 중 4개가 산업 상위 25% 이내",
        ),
    ]


def _weaknesses() -> list[StrengthWeakness]:
    return [
        StrengthWeakness(
            metric_id="peg_ratio", metric_display_name="PEG 비율",
            level_tag="weak", rank_within_portfolio=1,
            reason_hint="평균 PEG 2.8, 프리셋 기준 1.5 상회",
        ),
    ]


def _diag_cards() -> list[DiagnosticCard]:
    return [
        DiagnosticCard(
            weakness_metric_id="peg_ratio",
            what_is_wrong="5개 종목 모두 PEG가 2.0 이상이며, 평균 PEG는 2.8입니다.",
            comparison_basis="비교 기준: GICS Semiconductors 산업 중앙값 (PEG 1.8) 및 프리셋 임계값 (PEG < 1.5).",
            why_it_matters="GARP 관점에서 성장 대비 높은 밸류에이션은 성장 둔화 시 조정 리스크로 직결됩니다.",
            caveat_or_exception="단, NVDA의 PEG 4.2가 평균을 끌어올린 측면이 있어 NVDA 제외 시 평균은 2.4로 완화됩니다.",
            severity=Severity.MEDIUM,
            structural_or_single=StructuralOrSingle.STRUCTURAL,
        ),
    ]


def get_context_garp_tech() -> AnalysisContext:
    """GARP + Tech 집중 포트폴리오 (PEG 약점)."""
    portfolio = AnalysisTargetPortfolioContext(
        portfolio_id="11111111-1111-1111-1111-111111111111",
        portfolio_name="Tech 성장주",
        preset_id="garp",
        preset_name="GARP",
        preset_category="growth",
        save_type="named",
        holdings_summary=_holdings_tech(),
        holding_count=5,
        core_metric_results=_core_metrics(),
        supporting_metric_results=_supporting_metrics(),
        context_metric_results=[],
        strengths=_strengths(),
        weaknesses=_weaknesses(),
        diagnostic_cards=_diag_cards(),
        return_breakdown=_portfolio_return(),
        overrides_applied=None,
    )
    wallet = WalletBackgroundContext(
        wallet_id="22222222-2222-2222-2222-222222222222",
        total_holdings_count=12,
        excluded_from_this_portfolio_count=7,
        sector_distribution={"Technology": 0.55, "Healthcare": 0.20, "Consumer": 0.25},
        industry_distribution={"Semiconductors": 0.30, "Software": 0.25},
        total_value_estimate="mid",
        return_breakdown=_wallet_return(),
        historical_snapshots_available=3,
        notable_recent_changes=["Tech 비중 40% → 55%", "ABC 신규 편입"],
    )
    return AnalysisContext(
        analysis_target_portfolio=portfolio,
        wallet_background=wallet,
    )


def get_context_garp_tech_with_roic_20() -> AnalysisContext:
    """ROIC 임계값 20% 상향된 조정본."""
    base = get_context_garp_tech()
    p = base.analysis_target_portfolio
    # Core metric 조정: threshold 0.15 → 0.20
    new_core = [
        mr.model_copy(update={"threshold_applied": Decimal("0.20"),
                              "passed_threshold": False, "level_tag": "moderate"})
        if mr.metric_id == "roic" else mr
        for mr in p.core_metric_results
    ]
    # 약점에 ROIC 추가 (INTC 단일 이상치)
    new_weak = list(p.weaknesses) + [
        StrengthWeakness(
            metric_id="roic", metric_display_name="투하자본수익률",
            level_tag="weak", rank_within_portfolio=2,
            reason_hint="INTC가 20% 미달, 나머지 4종목은 통과",
        ),
    ]
    new_cards = list(p.diagnostic_cards) + [
        DiagnosticCard(
            weakness_metric_id="roic",
            what_is_wrong="ROIC 20% 기준에서 5종목 중 1종목(INTC)이 미달합니다.",
            comparison_basis="비교 기준: 프리셋 조정 임계값 (ROIC >= 20%).",
            why_it_matters="Buffett 관점에서 상향된 ROIC 기준은 '지속적 자본 수익'의 엄격한 해석입니다.",
            caveat_or_exception="단일 이상치로 구조적 문제는 아닙니다.",
            severity=Severity.MEDIUM,
            structural_or_single=StructuralOrSingle.SINGLE_OUTLIER,
        ),
    ]
    adjusted_portfolio = p.model_copy(update={
        "core_metric_results": new_core,
        "weaknesses": new_weak,
        "diagnostic_cards": new_cards,
        "overrides_applied": {
            "metric_id": "roic",
            "old_threshold": 0.15,
            "new_threshold": 0.20,
        },
    })
    return base.model_copy(update={"analysis_target_portfolio": adjusted_portfolio})


def get_context_dividend() -> AnalysisContext:
    """Dividend Growth 포트폴리오 (배당 강점)."""
    holdings = [
        HoldingSummary(
            holding_id=f"h-div-{i}", stock_symbol=sym, stock_name=name,
            sector=sector, industry=industry,
            shares=Decimal("20.0"), weight=Decimal(w), market_value=Decimal(mv),
            unrealized_return=Decimal(ur), investment_thesis=None,
        )
        for i, (sym, name, sector, industry, w, mv, ur) in enumerate([
            ("JNJ", "Johnson & Johnson", "Healthcare", "Pharma", "0.20", "8000", "0.06"),
            ("PG",  "Procter & Gamble",  "Consumer Staples", "Household", "0.20", "8000", "0.05"),
            ("KO",  "Coca-Cola",          "Consumer Staples", "Beverages", "0.15", "6000", "0.04"),
            ("PEP", "PepsiCo",            "Consumer Staples", "Beverages", "0.15", "6000", "0.05"),
            ("WMT", "Walmart",            "Consumer Staples", "Retail",    "0.15", "6000", "0.08"),
            ("MMM", "3M",                 "Industrials",       "Conglomerate", "0.10", "4000", "0.02"),
            ("ABBV","AbbVie",             "Healthcare",        "Pharma",    "0.05", "2000", "0.11"),
        ])
    ]
    portfolio = AnalysisTargetPortfolioContext(
        portfolio_id="33333333-3333-3333-3333-333333333333",
        portfolio_name="배당 코어",
        preset_id="dividend_growth",
        preset_name="Dividend Growth",
        preset_category="income",
        save_type="named",
        holdings_summary=holdings,
        holding_count=7,
        core_metric_results=[
            MetricResult(
                metric_id="dividend_yield", metric_display_name="배당수익률",
                tier=MetricTier.CORE, value=Decimal("0.034"),
                percentile=Decimal("0.75"), percentile_scope="sector",
                level_tag="good",
                threshold_applied=Decimal("0.02"), passed_threshold=True,
            ),
        ],
        supporting_metric_results=[],
        context_metric_results=[],
        strengths=[
            StrengthWeakness(
                metric_id="dividend_yield", metric_display_name="배당수익률",
                level_tag="good", rank_within_portfolio=1,
                reason_hint="평균 3.4%, 섹터 중앙값 2.1%",
            ),
        ],
        weaknesses=[],
        diagnostic_cards=[],
        return_breakdown=_portfolio_return("0.07"),
        overrides_applied=None,
    )
    wallet = WalletBackgroundContext(
        wallet_id="44444444-4444-4444-4444-444444444444",
        total_holdings_count=15,
        excluded_from_this_portfolio_count=8,
        sector_distribution={"Consumer Staples": 0.50, "Healthcare": 0.25},
        industry_distribution={},
        total_value_estimate="mid",
        return_breakdown=_wallet_return("0.06"),
        historical_snapshots_available=1,
        notable_recent_changes=[],
    )
    return AnalysisContext(
        analysis_target_portfolio=portfolio,
        wallet_background=wallet,
    )
