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
                name="NVDA",
                weight=Decimal("0.30"),
                return_rate=Decimal("0.32"),
                contribution_pp=Decimal("0.096"),
            ),
        ],
        bottom_contributors=[
            ContributionItem(
                name="INTC",
                weight=Decimal("0.10"),
                return_rate=Decimal("-0.05"),
                contribution_pp=Decimal("-0.005"),
            ),
        ],
    )
    return ReturnBreakdownWithTime(
        at_save_time=None, current=current, delta_since_save=None
    )


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
                name="Technology",
                weight=Decimal("0.55"),
                return_rate=Decimal("0.12"),
                contribution_pp=Decimal("0.066"),
            ),
            CategoryBreakdown(
                name="Healthcare",
                weight=Decimal("0.20"),
                return_rate=Decimal("0.06"),
                contribution_pp=Decimal("0.012"),
            ),
        ],
        top_contributors=[],
        bottom_contributors=[],
    )
    return ReturnBreakdownWithTime(
        at_save_time=None, current=current, delta_since_save=None
    )


def _holdings_tech() -> list[HoldingSummary]:
    return [
        HoldingSummary(
            holding_id=f"h-{i}",
            stock_symbol=sym,
            stock_name=name,
            sector="Technology",
            industry="Semiconductors" if sym in {"NVDA", "AMD", "INTC"} else "Software",
            shares=Decimal("10.0"),
            weight=Decimal(w),
            market_value=Decimal(mv),
            unrealized_return=Decimal(ur),
            investment_thesis=thesis,
        )
        for i, (sym, name, w, mv, ur, thesis) in enumerate(
            [
                ("NVDA", "NVIDIA", "0.30", "15000", "0.32", "AI 인프라 수요"),
                ("MSFT", "Microsoft", "0.25", "12500", "0.18", "클라우드 지속 성장"),
                ("AAPL", "Apple", "0.20", "10000", "0.10", "서비스 수익 확대"),
                ("GOOGL", "Alphabet", "0.15", "7500", "0.12", "광고 안정 + AI"),
                ("INTC", "Intel", "0.10", "5000", "-0.05", "턴어라운드 기대"),
            ]
        )
    ]


def _core_metrics() -> list[MetricResult]:
    return [
        MetricResult(
            metric_id="roic",
            metric_display_name="투하자본수익률",
            tier=MetricTier.CORE,
            value=Decimal("0.18"),
            percentile=Decimal("0.82"),
            percentile_scope="industry",
            level_tag="good",
            threshold_applied=Decimal("0.15"),
            passed_threshold=True,
        ),
        MetricResult(
            metric_id="peg_ratio",
            metric_display_name="PEG 비율",
            tier=MetricTier.CORE,
            value=Decimal("2.80"),
            percentile=Decimal("0.15"),
            percentile_scope="industry",
            level_tag="weak",
            threshold_applied=Decimal("1.5"),
            passed_threshold=False,
        ),
    ]


def _supporting_metrics() -> list[MetricResult]:
    return [
        MetricResult(
            metric_id="revenue_growth_yoy",
            metric_display_name="매출 성장률(YoY)",
            tier=MetricTier.SUPPORTING,
            value=Decimal("0.18"),
            percentile=Decimal("0.70"),
            percentile_scope="industry",
            level_tag="good",
            threshold_applied=None,
            passed_threshold=None,
        ),
    ]


def _strengths() -> list[StrengthWeakness]:
    return [
        StrengthWeakness(
            metric_id="roic",
            metric_display_name="투하자본수익률",
            level_tag="good",
            rank_within_portfolio=1,
            reason_hint="5종목 중 4개가 산업 상위 25% 이내",
        ),
    ]


def _weaknesses() -> list[StrengthWeakness]:
    return [
        StrengthWeakness(
            metric_id="peg_ratio",
            metric_display_name="PEG 비율",
            level_tag="weak",
            rank_within_portfolio=1,
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
        mr.model_copy(
            update={
                "threshold_applied": Decimal("0.20"),
                "passed_threshold": False,
                "level_tag": "moderate",
            }
        )
        if mr.metric_id == "roic"
        else mr
        for mr in p.core_metric_results
    ]
    # 약점에 ROIC 추가 (INTC 단일 이상치)
    new_weak = list(p.weaknesses) + [
        StrengthWeakness(
            metric_id="roic",
            metric_display_name="투하자본수익률",
            level_tag="weak",
            rank_within_portfolio=2,
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
    adjusted_portfolio = p.model_copy(
        update={
            "core_metric_results": new_core,
            "weaknesses": new_weak,
            "diagnostic_cards": new_cards,
            "overrides_applied": {
                "metric_id": "roic",
                "old_threshold": 0.15,
                "new_threshold": 0.20,
            },
        }
    )
    return base.model_copy(update={"analysis_target_portfolio": adjusted_portfolio})


def get_context_dividend() -> AnalysisContext:
    """Dividend Growth 포트폴리오 (배당 강점)."""
    holdings = [
        HoldingSummary(
            holding_id=f"h-div-{i}",
            stock_symbol=sym,
            stock_name=name,
            sector=sector,
            industry=industry,
            shares=Decimal("20.0"),
            weight=Decimal(w),
            market_value=Decimal(mv),
            unrealized_return=Decimal(ur),
            investment_thesis=None,
        )
        for i, (sym, name, sector, industry, w, mv, ur) in enumerate(
            [
                (
                    "JNJ",
                    "Johnson & Johnson",
                    "Healthcare",
                    "Pharma",
                    "0.20",
                    "8000",
                    "0.06",
                ),
                (
                    "PG",
                    "Procter & Gamble",
                    "Consumer Staples",
                    "Household",
                    "0.20",
                    "8000",
                    "0.05",
                ),
                (
                    "KO",
                    "Coca-Cola",
                    "Consumer Staples",
                    "Beverages",
                    "0.15",
                    "6000",
                    "0.04",
                ),
                (
                    "PEP",
                    "PepsiCo",
                    "Consumer Staples",
                    "Beverages",
                    "0.15",
                    "6000",
                    "0.05",
                ),
                (
                    "WMT",
                    "Walmart",
                    "Consumer Staples",
                    "Retail",
                    "0.15",
                    "6000",
                    "0.08",
                ),
                ("MMM", "3M", "Industrials", "Conglomerate", "0.10", "4000", "0.02"),
                ("ABBV", "AbbVie", "Healthcare", "Pharma", "0.05", "2000", "0.11"),
            ]
        )
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
                metric_id="dividend_yield",
                metric_display_name="배당수익률",
                tier=MetricTier.CORE,
                value=Decimal("0.034"),
                percentile=Decimal("0.75"),
                percentile_scope="sector",
                level_tag="good",
                threshold_applied=Decimal("0.02"),
                passed_threshold=True,
            ),
        ],
        supporting_metric_results=[],
        context_metric_results=[],
        strengths=[
            StrengthWeakness(
                metric_id="dividend_yield",
                metric_display_name="배당수익률",
                level_tag="good",
                rank_within_portfolio=1,
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


# ============================================================
# GARP Misfit — 5종목, GARP 적합도 매우 낮음
# ============================================================


def _holdings_garp_misfit() -> list[HoldingSummary]:
    """5종목 모두 GARP 기준 미달 (PEG > 2.5, ROIC < 8% 등)."""
    return [
        HoldingSummary(
            holding_id=f"h-misfit-{i}",
            stock_symbol=sym,
            stock_name=name,
            sector=sector,
            industry=industry,
            shares=Decimal("10.0"),
            weight=Decimal(w),
            market_value=Decimal(mv),
            unrealized_return=Decimal(ur),
            investment_thesis=None,
        )
        for i, (sym, name, sector, industry, w, mv, ur) in enumerate(
            [
                (
                    "TSLA",
                    "Tesla",
                    "Consumer Discretionary",
                    "Auto",
                    "0.25",
                    "10000",
                    "-0.10",
                ),
                ("PLTR", "Palantir", "Technology", "Software", "0.20", "8000", "-0.05"),
                ("SHOP", "Shopify", "Technology", "E-commerce", "0.20", "8000", "0.02"),
                (
                    "ABNB",
                    "Airbnb",
                    "Consumer Discretionary",
                    "Travel",
                    "0.20",
                    "8000",
                    "-0.03",
                ),
                (
                    "RBLX",
                    "Roblox",
                    "Communication Services",
                    "Gaming",
                    "0.15",
                    "6000",
                    "-0.12",
                ),
            ]
        )
    ]


def get_context_garp_misfit() -> AnalysisContext:
    """
    GARP 프리셋 부정합 시나리오. 5종목 모두 PEG > 2.5 또는 ROIC < 8%.
    Coach E1이 약점 강조 + 보완 제안 톤으로 응답해야 하는 케이스.
    """
    portfolio = AnalysisTargetPortfolioContext(
        portfolio_id="55555555-5555-5555-5555-555555555555",
        portfolio_name="고성장 베팅",
        preset_id="garp",
        preset_name="GARP",
        preset_category="growth",
        save_type="named",
        holdings_summary=_holdings_garp_misfit(),
        holding_count=5,
        core_metric_results=[
            MetricResult(
                metric_id="peg_ratio",
                metric_display_name="PEG",
                tier=MetricTier.CORE,
                value=Decimal("3.20"),
                percentile=Decimal("0.08"),
                percentile_scope="industry",
                level_tag="critical",
                threshold_applied=Decimal("1.5"),
                passed_threshold=False,
            ),
            MetricResult(
                metric_id="eps_growth_yoy",
                metric_display_name="EPS 성장률 (YoY)",
                tier=MetricTier.CORE,
                value=Decimal("0.04"),
                percentile=Decimal("0.20"),
                percentile_scope="industry",
                level_tag="weak",
                threshold_applied=Decimal("0.10"),
                passed_threshold=False,
            ),
            MetricResult(
                metric_id="revenue_growth_yoy",
                metric_display_name="매출 성장률 (YoY)",
                tier=MetricTier.CORE,
                value=Decimal("0.12"),
                percentile=Decimal("0.55"),
                percentile_scope="industry",
                level_tag="moderate",
                threshold_applied=Decimal("0.08"),
                passed_threshold=True,
            ),
        ],
        supporting_metric_results=[
            MetricResult(
                metric_id="roic",
                metric_display_name="ROIC",
                tier=MetricTier.SUPPORTING,
                value=Decimal("0.06"),
                percentile=Decimal("0.18"),
                percentile_scope="industry",
                level_tag="weak",
                threshold_applied=Decimal("0.10"),
                passed_threshold=False,
            ),
            MetricResult(
                metric_id="pe_ratio",
                metric_display_name="PER",
                tier=MetricTier.SUPPORTING,
                value=Decimal("65.0"),
                percentile=Decimal("0.05"),
                percentile_scope="industry",
                level_tag="critical",
                threshold_applied=None,
                passed_threshold=None,
            ),
        ],
        context_metric_results=[
            MetricResult(
                metric_id="debt_to_equity",
                metric_display_name="부채비율",
                tier=MetricTier.CONTEXT,
                value=Decimal("0.45"),
                percentile=Decimal("0.60"),
                percentile_scope="industry",
                level_tag="moderate",
                threshold_applied=None,
                passed_threshold=None,
            ),
        ],
        strengths=[
            StrengthWeakness(
                metric_id="revenue_growth_yoy",
                metric_display_name="매출 성장률 (YoY)",
                level_tag="moderate",
                rank_within_portfolio=1,
                reason_hint="5종목 평균 12%로 임계값 8% 통과",
            ),
        ],
        weaknesses=[
            StrengthWeakness(
                metric_id="peg_ratio",
                metric_display_name="PEG",
                level_tag="critical",
                rank_within_portfolio=1,
                reason_hint="평균 3.20, 5종목 모두 임계값 1.5 미달",
            ),
            StrengthWeakness(
                metric_id="eps_growth_yoy",
                metric_display_name="EPS 성장률 (YoY)",
                level_tag="weak",
                rank_within_portfolio=2,
                reason_hint="평균 4%, 임계값 10% 미달",
            ),
            StrengthWeakness(
                metric_id="roic",
                metric_display_name="ROIC",
                level_tag="weak",
                rank_within_portfolio=3,
                reason_hint="평균 6%, 임계값 10% 미달",
            ),
        ],
        diagnostic_cards=[
            DiagnosticCard(
                weakness_metric_id="peg_ratio",
                what_is_wrong="5종목 모두 PEG가 2.5 이상이며 평균 PEG가 3.20입니다.",
                comparison_basis="비교 기준: 산업 중앙값 (PEG 1.8) 및 프리셋 임계값 (PEG < 1.5).",
                why_it_matters="GARP 관점에서 성장 대비 가격이 합리적인지가 핵심 판정인데, 현재 구성은 그 전제를 정면으로 위배합니다.",
                caveat_or_exception="5종목 모두 동일 패턴이라 단일 이상치가 아닌 구조적 이슈로 보입니다.",
                severity=Severity.HIGH,
                structural_or_single=StructuralOrSingle.STRUCTURAL,
            ),
        ],
        return_breakdown=_portfolio_return("-0.06"),
        overrides_applied=None,
    )
    wallet = WalletBackgroundContext(
        wallet_id="66666666-6666-6666-6666-666666666666",
        total_holdings_count=10,
        excluded_from_this_portfolio_count=5,
        sector_distribution={"Technology": 0.40, "Consumer Discretionary": 0.45},
        industry_distribution={"Software": 0.20, "Auto": 0.25, "E-commerce": 0.20},
        total_value_estimate="mid",
        return_breakdown=_wallet_return("-0.02"),
        historical_snapshots_available=2,
        notable_recent_changes=["TSLA 비중 15% → 25% (1개월)"],
    )
    return AnalysisContext(
        analysis_target_portfolio=portfolio,
        wallet_background=wallet,
    )


# ============================================================
# GARP Large — 15종목, 정합 5 / 부분 5 / 부정합 5 분포
# ============================================================

# (sym, name, sector, industry, weight, market_value, unrealized_return, fit_class)
# fit_class ∈ {"fit", "partial", "misfit"} — 분포 검증용 메타.
_GARP_LARGE_HOLDINGS_RAW: list[tuple[str, str, str, str, str, str, str, str]] = [
    # 정합 5종목 (PEG 0.8~1.3, EPS_growth > 10%, ROIC > 13%, weight 합 0.37)
    ("MSFT", "Microsoft", "Technology", "Software", "0.10", "5000", "0.18", "fit"),
    (
        "GOOGL",
        "Alphabet",
        "Communication Services",
        "Internet",
        "0.08",
        "4000",
        "0.12",
        "fit",
    ),
    (
        "V",
        "Visa",
        "Financial Services",
        "Credit Services",
        "0.07",
        "3500",
        "0.09",
        "fit",
    ),
    (
        "MA",
        "Mastercard",
        "Financial Services",
        "Credit Services",
        "0.06",
        "3000",
        "0.11",
        "fit",
    ),
    ("ADBE", "Adobe", "Technology", "Software", "0.06", "3000", "0.07", "fit"),
    # 부분 적합 5종목 (지표 일부 통과, weight 합 0.34)
    (
        "AAPL",
        "Apple",
        "Technology",
        "Consumer Electronics",
        "0.08",
        "4000",
        "0.05",
        "partial",
    ),
    (
        "AMZN",
        "Amazon",
        "Consumer Discretionary",
        "E-commerce",
        "0.07",
        "3500",
        "0.04",
        "partial",
    ),
    (
        "META",
        "Meta",
        "Communication Services",
        "Internet",
        "0.06",
        "3000",
        "0.10",
        "partial",
    ),
    (
        "AVGO",
        "Broadcom",
        "Technology",
        "Semiconductors",
        "0.06",
        "3000",
        "0.15",
        "partial",
    ),
    (
        "NVDA",
        "NVIDIA",
        "Technology",
        "Semiconductors",
        "0.07",
        "3500",
        "0.32",
        "partial",
    ),
    # 부정합 5종목 (PEG > 2.5 또는 ROIC < 8%, weight 합 0.29)
    (
        "TSLA",
        "Tesla",
        "Consumer Discretionary",
        "Auto",
        "0.05",
        "2500",
        "-0.10",
        "misfit",
    ),
    (
        "NFLX",
        "Netflix",
        "Communication Services",
        "Streaming",
        "0.05",
        "2500",
        "0.06",
        "misfit",
    ),
    ("CRM", "Salesforce", "Technology", "Software", "0.06", "3000", "0.04", "misfit"),
    ("PLTR", "Palantir", "Technology", "Software", "0.06", "3000", "-0.08", "misfit"),
    ("SHOP", "Shopify", "Technology", "E-commerce", "0.07", "3500", "0.02", "misfit"),
]


def garp_large_fit_distribution() -> dict[str, int]:
    """5/5/5 분포 검증용 (test_fixtures_validation에서 사용)."""
    counts: dict[str, int] = {"fit": 0, "partial": 0, "misfit": 0}
    for *_, fit_class in _GARP_LARGE_HOLDINGS_RAW:
        counts[fit_class] += 1
    return counts


def _holdings_garp_large() -> list[HoldingSummary]:
    return [
        HoldingSummary(
            holding_id=f"h-large-{i}",
            stock_symbol=sym,
            stock_name=name,
            sector=sector,
            industry=industry,
            shares=Decimal("10.0"),
            weight=Decimal(w),
            market_value=Decimal(mv),
            unrealized_return=Decimal(ur),
            investment_thesis=None,
        )
        for i, (sym, name, sector, industry, w, mv, ur, _fit) in enumerate(
            _GARP_LARGE_HOLDINGS_RAW
        )
    ]


def get_context_garp_large() -> AnalysisContext:
    """
    GARP 프리셋 + 종목 15개 large fixture.

    분포:
      - 정합 5종목 (PEG 0.8~1.3, EPS_growth > 10%, ROIC > 13%) — 강점 카드 후보
      - 부분 적합 5종목 (지표 일부 통과) — 보완 제안 후보
      - 부정합 5종목 (PEG > 2.5 또는 ROIC < 8%) — 약점/제외 제안 후보
    가중치 합 = 1.00.
    """
    portfolio = AnalysisTargetPortfolioContext(
        portfolio_id="77777777-7777-7777-7777-777777777777",
        portfolio_name="GARP 다양화 15",
        preset_id="garp",
        preset_name="GARP",
        preset_category="growth",
        save_type="named",
        holdings_summary=_holdings_garp_large(),
        holding_count=15,
        core_metric_results=[
            MetricResult(
                metric_id="peg_ratio",
                metric_display_name="PEG",
                tier=MetricTier.CORE,
                value=Decimal("1.85"),
                percentile=Decimal("0.45"),
                percentile_scope="industry",
                level_tag="moderate",
                threshold_applied=Decimal("1.5"),
                passed_threshold=False,
            ),
            MetricResult(
                metric_id="eps_growth_yoy",
                metric_display_name="EPS 성장률 (YoY)",
                tier=MetricTier.CORE,
                value=Decimal("0.13"),
                percentile=Decimal("0.62"),
                percentile_scope="industry",
                level_tag="good",
                threshold_applied=Decimal("0.10"),
                passed_threshold=True,
            ),
            MetricResult(
                metric_id="revenue_growth_yoy",
                metric_display_name="매출 성장률 (YoY)",
                tier=MetricTier.CORE,
                value=Decimal("0.11"),
                percentile=Decimal("0.58"),
                percentile_scope="industry",
                level_tag="good",
                threshold_applied=Decimal("0.08"),
                passed_threshold=True,
            ),
        ],
        supporting_metric_results=[
            MetricResult(
                metric_id="roic",
                metric_display_name="ROIC",
                tier=MetricTier.SUPPORTING,
                value=Decimal("0.14"),
                percentile=Decimal("0.65"),
                percentile_scope="industry",
                level_tag="good",
                threshold_applied=Decimal("0.10"),
                passed_threshold=True,
            ),
            MetricResult(
                metric_id="roe",
                metric_display_name="ROE",
                tier=MetricTier.SUPPORTING,
                value=Decimal("0.18"),
                percentile=Decimal("0.70"),
                percentile_scope="industry",
                level_tag="good",
                threshold_applied=None,
                passed_threshold=None,
            ),
            MetricResult(
                metric_id="pe_ratio",
                metric_display_name="PER",
                tier=MetricTier.SUPPORTING,
                value=Decimal("28.0"),
                percentile=Decimal("0.40"),
                percentile_scope="industry",
                level_tag="moderate",
                threshold_applied=None,
                passed_threshold=None,
            ),
            MetricResult(
                metric_id="revenue_growth_consistency_3y",
                metric_display_name="매출 성장 일관성 (3년)",
                tier=MetricTier.SUPPORTING,
                value=Decimal("0.72"),
                percentile=Decimal("0.55"),
                percentile_scope="industry",
                level_tag="moderate",
                threshold_applied=None,
                passed_threshold=None,
            ),
        ],
        context_metric_results=[
            MetricResult(
                metric_id="debt_to_equity",
                metric_display_name="부채비율",
                tier=MetricTier.CONTEXT,
                value=Decimal("0.55"),
                percentile=Decimal("0.50"),
                percentile_scope="industry",
                level_tag="moderate",
                threshold_applied=None,
                passed_threshold=None,
            ),
            MetricResult(
                metric_id="beta",
                metric_display_name="베타",
                tier=MetricTier.CONTEXT,
                value=Decimal("1.15"),
                percentile=Decimal("0.55"),
                percentile_scope="universe",
                level_tag="moderate",
                threshold_applied=None,
                passed_threshold=None,
            ),
            MetricResult(
                metric_id="market_cap",
                metric_display_name="시가총액",
                tier=MetricTier.CONTEXT,
                value=Decimal("450000000000"),
                percentile=Decimal("0.85"),
                percentile_scope="universe",
                level_tag="excellent",
                threshold_applied=None,
                passed_threshold=None,
            ),
        ],
        strengths=[
            StrengthWeakness(
                metric_id="eps_growth_yoy",
                metric_display_name="EPS 성장률 (YoY)",
                level_tag="good",
                rank_within_portfolio=1,
                reason_hint="15종목 평균 13%, 정합 5종목이 평균을 상향",
            ),
            StrengthWeakness(
                metric_id="roic",
                metric_display_name="ROIC",
                level_tag="good",
                rank_within_portfolio=2,
                reason_hint="평균 14%, 정합/부분 종목 10개가 임계값 통과",
            ),
        ],
        weaknesses=[
            StrengthWeakness(
                metric_id="peg_ratio",
                metric_display_name="PEG",
                level_tag="moderate",
                rank_within_portfolio=1,
                reason_hint="평균 1.85, 부정합 5종목이 평균을 끌어올림",
            ),
            StrengthWeakness(
                metric_id="pe_ratio",
                metric_display_name="PER",
                level_tag="moderate",
                rank_within_portfolio=2,
                reason_hint="평균 28, 일부 부정합 종목 50배 이상",
            ),
        ],
        diagnostic_cards=[
            DiagnosticCard(
                weakness_metric_id="peg_ratio",
                what_is_wrong="15종목 평균 PEG는 1.85로 프리셋 임계값 1.5를 상회합니다. 부정합 5종목 (TSLA, PLTR, SHOP 등)이 PEG 2.5 이상으로 평균을 끌어올렸습니다.",
                comparison_basis="비교 기준: 산업 중앙값 (PEG 1.8) 및 프리셋 임계값 (PEG < 1.5).",
                why_it_matters="GARP 관점에서 정합 5종목과 부분 5종목은 합리적 성장가에 있으나, 부정합 5종목이 묶음 전체의 GARP 적합도를 희석합니다.",
                caveat_or_exception="정합 5종목만 분리해서 보면 평균 PEG는 1.05로 양호합니다. 부정합 종목 분리 검토가 가능합니다.",
                severity=Severity.MEDIUM,
                structural_or_single=StructuralOrSingle.SINGLE_OUTLIER,
            ),
        ],
        return_breakdown=_portfolio_return("0.10"),
        overrides_applied=None,
    )
    wallet = WalletBackgroundContext(
        wallet_id="88888888-8888-8888-8888-888888888888",
        total_holdings_count=20,
        excluded_from_this_portfolio_count=5,
        sector_distribution={
            "Technology": 0.50,
            "Consumer Discretionary": 0.20,
            "Communication Services": 0.15,
            "Financial Services": 0.15,
        },
        industry_distribution={
            "Software": 0.25,
            "Semiconductors": 0.15,
            "E-commerce": 0.15,
            "Internet": 0.15,
        },
        total_value_estimate="high",
        return_breakdown=_wallet_return("0.09"),
        historical_snapshots_available=4,
        notable_recent_changes=[
            "Tech 비중 45% → 50% (3개월)",
            "TSLA 신규 편입",
            "AAPL 비중 12% → 8% (1개월)",
        ],
    )
    return AnalysisContext(
        analysis_target_portfolio=portfolio,
        wallet_background=wallet,
    )
