"""Slice 14 Step 0.5 — 게이트 가치 검증 probe (작업 2).

8 케이스 × haiku 3회 = 24 LLM 호출. gate_tiers=None 그대로(현 production).
출력 원문 전부 보존 → docs/portfolio/coach/slice14/gate_probe_outputs.json.

★ production 코드 변경 0. LLM 호출만.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from portfolio.llm import LLMClient  # noqa: E402
from portfolio.llm.cost_guard import CostGuard  # noqa: E402
from portfolio.schemas import (  # noqa: E402
    AnalysisContext,
    AnalysisTargetPortfolioContext,
    CategoryBreakdown,
    ContributionItem,
    HoldingSummary,
    MetricResult,
    MetricTier,
    ReturnBreakdown,
    ReturnBreakdownWithTime,
    ScopeType,
    StrengthWeakness,
    WalletBackgroundContext,
)
from portfolio.schemas.llm import E3Request  # noqa: E402
from portfolio.services.e3_metric_comment import run_e3  # noqa: E402

_NOW = datetime(2026, 5, 22, 10, 0, tzinfo=timezone.utc)


# ============================================================
# 케이스 정의 (gate_probe_cases.md와 동기)
# ============================================================

CASES: list[dict] = [
    {
        "case_id": 1,
        "preset_id": "buffett_quality_value",
        "preset_category": "value",
        "preset_name": "Buffett Quality Value",
        "risk_metric": "roic",
        "risk_metric_display": "투하자본수익률",
        "risk_value": Decimal("-0.08"),
        "risk_threshold": Decimal("0.15"),
        "normal_metrics": [
            ("roe", "ROE", Decimal("0.12"), Decimal("0.15")),
            ("roic_consistency_5y", "ROIC 일관성 5년", Decimal("0.55"), Decimal("0.50")),
            ("earnings_consistency_5y", "이익 일관성 5년", Decimal("0.50"), Decimal("0.50")),
        ],
        "risk_reason_hint": "ROIC -8%는 자본을 파괴하는 수준 (Buffett quality 정의 정면 위배)",
    },
    {
        "case_id": 2,
        "preset_id": "piotroski_f_score",
        "preset_category": "value",
        "preset_name": "Piotroski F-Score",
        "risk_metric": "f_score_total",
        "risk_metric_display": "Piotroski F-Score (0~9)",
        "risk_value": Decimal("1"),
        "risk_threshold": Decimal("7"),
        "normal_metrics": [],
        "risk_reason_hint": "9 중 1점 = 9개 재무 건전성 항목 중 1개만 통과 (F-Score 전략 기준 ≥7)",
    },
    {
        "case_id": 3,
        "preset_id": "garp",
        "preset_category": "growth",
        "preset_name": "GARP",
        "risk_metric": "eps_growth_yoy",
        "risk_metric_display": "EPS 성장률 (YoY)",
        "risk_value": Decimal("-0.35"),
        "risk_threshold": Decimal("0.10"),
        "normal_metrics": [
            ("peg_ratio", "PEG 비율", Decimal("1.50"), Decimal("1.50")),
            ("revenue_growth_yoy", "매출 성장률 (YoY)", Decimal("0.10"), Decimal("0.10")),
        ],
        "risk_reason_hint": "EPS -35% YoY = 역성장 (GARP의 'Growth' 전제 정면 위배)",
    },
    {
        "case_id": 4,
        "preset_id": "quality_growth",
        "preset_category": "growth",
        "preset_name": "Quality Growth",
        "risk_metric": "roic_consistency_5y",
        "risk_metric_display": "ROIC 일관성 5년",
        "risk_value": Decimal("0.10"),
        "risk_threshold": Decimal("0.50"),
        "normal_metrics": [
            ("roic", "ROIC", Decimal("0.16"), Decimal("0.15")),
            ("revenue_growth_yoy", "매출 성장률 (YoY)", Decimal("0.10"), Decimal("0.10")),
            ("eps_growth_yoy", "EPS 성장률 (YoY)", Decimal("0.12"), Decimal("0.10")),
        ],
        "risk_reason_hint": "ROIC 5년 일관성 10% = 수익성 변동 극심 (compounder 정의 불가)",
    },
    {
        "case_id": 5,
        "preset_id": "dividend_growth",
        "preset_category": "income",
        "preset_name": "Dividend Growth",
        "risk_metric": "dividend_yield",
        "risk_metric_display": "배당수익률",
        "risk_value": Decimal("0.001"),
        "risk_threshold": Decimal("0.02"),
        "normal_metrics": [
            ("dividend_growth_rate_5y", "배당 성장률 5년", Decimal("0.05"), Decimal("0.05")),
            ("dividend_growth_consistency_5y", "배당 일관성 5년", Decimal("0.60"), Decimal("0.50")),
        ],
        "risk_reason_hint": "yield 0.1% = preset gate 임계(2%)의 5%, income 분류 불가",
    },
    {
        "case_id": 6,
        "preset_id": "shareholder_yield",
        "preset_category": "income",
        "preset_name": "Shareholder Yield",
        "risk_metric": "shareholder_yield",
        "risk_metric_display": "순주주환원율",
        "risk_value": Decimal("-0.05"),
        "risk_threshold": Decimal("0.02"),
        "normal_metrics": [
            ("dividend_yield", "배당수익률", Decimal("0.025"), Decimal("0.02")),
            ("net_buyback_yield", "자사주매입 수익률", Decimal("0.01"), Decimal("0.01")),
            ("net_debt_reduction_rate", "부채감소율", Decimal("0.02"), Decimal("0.02")),
        ],
        "risk_reason_hint": "-5% = 발행 증가로 주주 희석 (shareholder yield 정의 정면 위배)",
    },
    {
        "case_id": 7,
        "preset_id": "low_volatility",
        "preset_category": "factor",
        "preset_name": "Low Volatility",
        "risk_metric": "beta",
        "risk_metric_display": "베타 (시장 민감도)",
        "risk_value": Decimal("1.8"),
        "risk_threshold": Decimal("1.2"),
        "normal_metrics": [
            ("volatility_1y", "변동성 1년", Decimal("0.18"), Decimal("0.20")),
            ("downside_deviation", "하방 편차", Decimal("0.12"), Decimal("0.15")),
            ("max_drawdown_1y", "최대 낙폭 1년", Decimal("-0.15"), Decimal("-0.20")),
            ("portfolio_volatility", "포트폴리오 변동성", Decimal("0.17"), Decimal("0.20")),
        ],
        "risk_reason_hint": "베타 1.8 = 시장보다 80% 변동적 (low volatility 정의 정면 위배, gate 1.2 lte의 1.5배)",
    },
    {
        "case_id": 8,
        "preset_id": "contrarian",
        "preset_category": "special",
        "preset_name": "Contrarian",
        "risk_metric": "pct_from_52w_high",
        "risk_metric_display": "52주 신고가 대비 등락률",
        "risk_value": Decimal("0.0"),
        "risk_threshold": Decimal("-0.20"),
        "normal_metrics": [
            ("pe_ratio", "PER", Decimal("10.0"), Decimal("15.0")),
            ("pb_ratio", "PBR", Decimal("1.2"), Decimal("1.5")),
            ("f_score_total", "Piotroski F-Score", Decimal("6"), Decimal("5")),
        ],
        "risk_reason_hint": "신고가 부근 = contrarian 매수 신호 전무 (모멘텀 영역, contrarian 정의 정면 위배)",
    },
]


# ============================================================
# AnalysisContext 합성
# ============================================================


def _holdings_synthetic(case: dict) -> list[HoldingSummary]:
    return [
        HoldingSummary(
            holding_id="probe-h-0",
            stock_symbol="RISKCASE",
            stock_name=f"Synthetic {case['preset_id']}",
            sector="Diversified",
            industry="Diversified",
            shares=Decimal("10.0"),
            weight=Decimal("1.00"),
            market_value=Decimal("10000"),
            unrealized_return=Decimal("0.00"),
            investment_thesis=case["risk_reason_hint"],
        )
    ]


def _core_metrics_synthetic(case: dict) -> list[MetricResult]:
    """위험 지표 1개 (critical) + 나머지 정상 Core 지표 (moderate)."""
    metrics: list[MetricResult] = [
        MetricResult(
            metric_id=case["risk_metric"],
            metric_display_name=case["risk_metric_display"],
            tier=MetricTier.CORE,
            value=case["risk_value"],
            percentile=Decimal("0.02"),
            percentile_scope="industry",
            level_tag="critical",
            threshold_applied=case["risk_threshold"],
            passed_threshold=False,
        )
    ]
    for mid, mname, mval, mthresh in case["normal_metrics"]:
        metrics.append(
            MetricResult(
                metric_id=mid,
                metric_display_name=mname,
                tier=MetricTier.CORE,
                value=mval,
                percentile=Decimal("0.50"),
                percentile_scope="industry",
                level_tag="moderate",
                threshold_applied=mthresh,
                passed_threshold=True,
            )
        )
    return metrics


def _weakness_synthetic(case: dict) -> list[StrengthWeakness]:
    return [
        StrengthWeakness(
            metric_id=case["risk_metric"],
            metric_display_name=case["risk_metric_display"],
            level_tag="critical",
            rank_within_portfolio=1,
            reason_hint=case["risk_reason_hint"],
        )
    ]


def _return_synthetic(scope_type: ScopeType, scope_id: str) -> ReturnBreakdownWithTime:
    current = ReturnBreakdown(
        scope_type=scope_type,
        scope_id=scope_id,
        calculated_at=_NOW,
        total_return=Decimal("0.00"),
        total_value=Decimal("10000.00"),
        total_cost_basis=Decimal("10000.00"),
        by_sector=[
            CategoryBreakdown(
                name="Diversified",
                weight=Decimal("1.00"),
                return_rate=Decimal("0.00"),
                contribution_pp=Decimal("0.00"),
            )
        ],
        top_contributors=[
            ContributionItem(
                name="RISKCASE",
                weight=Decimal("1.00"),
                return_rate=Decimal("0.00"),
                contribution_pp=Decimal("0.00"),
            )
        ],
        bottom_contributors=[],
    )
    return ReturnBreakdownWithTime(at_save_time=None, current=current, delta_since_save=None)


def build_context_for_case(case: dict) -> AnalysisContext:
    portfolio = AnalysisTargetPortfolioContext(
        portfolio_id="11111111-1111-1111-1111-111111111111",
        portfolio_name=f"probe_{case['preset_id']}",
        preset_id=case["preset_id"],
        preset_name=case["preset_name"],
        preset_category=case["preset_category"],
        save_type="named",
        holdings_summary=_holdings_synthetic(case),
        holding_count=1,
        core_metric_results=_core_metrics_synthetic(case),
        supporting_metric_results=[],
        context_metric_results=[],
        strengths=[],
        weaknesses=_weakness_synthetic(case),
        diagnostic_cards=[],
        return_breakdown=_return_synthetic(
            ScopeType.PORTFOLIO, "11111111-1111-1111-1111-111111111111"
        ),
        overrides_applied=None,
    )
    wallet = WalletBackgroundContext(
        wallet_id="22222222-2222-2222-2222-222222222222",
        total_holdings_count=1,
        excluded_from_this_portfolio_count=0,
        sector_distribution={"Diversified": 1.0},
        industry_distribution={"Diversified": 1.0},
        total_value_estimate="mid",
        return_breakdown=_return_synthetic(
            ScopeType.WALLET, "22222222-2222-2222-2222-222222222222"
        ),
        historical_snapshots_available=0,
        notable_recent_changes=[],
    )
    return AnalysisContext(
        analysis_target_portfolio=portfolio,
        wallet_background=wallet,
    )


# ============================================================
# probe 실행
# ============================================================


def run_probe(repeats: int = 3) -> list[dict]:
    guard = CostGuard.get_instance()
    guard.reset_slice("slice14", max_calls=100)
    client = LLMClient()
    results: list[dict] = []

    for case in CASES:
        ctx = build_context_for_case(case)
        request = E3Request(analysis_context=ctx.model_dump(mode="json"))
        for rep in range(1, repeats + 1):
            print(
                f"[probe] case={case['case_id']} ({case['preset_id']}) rep={rep}/{repeats}",
                flush=True,
            )
            try:
                out = run_e3(request, provider="haiku", client=client)
                results.append(
                    {
                        "case_id": case["case_id"],
                        "preset_id": case["preset_id"],
                        "category": case["preset_category"],
                        "risk_metric": case["risk_metric"],
                        "risk_value": str(case["risk_value"]),
                        "rep": rep,
                        "response": out["response"],
                        "metadata": out["metadata"],
                    }
                )
            except Exception as exc:  # noqa: BLE001 — 한 호출 실패 시 나머지 진행.
                print(f"  ERROR: {exc}", flush=True)
                results.append(
                    {
                        "case_id": case["case_id"],
                        "preset_id": case["preset_id"],
                        "category": case["preset_category"],
                        "risk_metric": case["risk_metric"],
                        "risk_value": str(case["risk_value"]),
                        "rep": rep,
                        "error": str(exc),
                    }
                )
    return results


def main() -> int:
    out_dir = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice14"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "gate_probe_outputs.json"
    results = run_probe(repeats=3)
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n{len(results)} 호출 완료 → {out_path}")
    total_cost = sum(
        r.get("metadata", {}).get("cost_usd", 0.0) for r in results if "metadata" in r
    )
    print(f"누적 비용: ${total_cost:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
