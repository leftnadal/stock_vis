"""
E1 입력 빌더 — 풀 AnalysisContext에서 E1이 필요한 필드만 추출.

PV5(부분) 원칙: E1은 Wallet 정보를 최소로 주입. total_holdings_count +
excluded_from_this_portfolio_count 만 제공. metric_results/diagnostic_cards/
holdings_summary 상세는 제외 (토큰 효율).

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from apps.portfolio.schemas import AnalysisContext


def build_e1_input(context: AnalysisContext) -> dict:
    """AnalysisContext에서 E1용 간소 입력 dict 생성."""
    p = context.analysis_target_portfolio
    w = context.wallet_background

    return {
        "analysis_target_portfolio": {
            "portfolio_name": p.portfolio_name,
            "preset_id": p.preset_id,
            "preset_name": p.preset_name,
            "preset_category": p.preset_category,
            "holding_count": p.holding_count,
            "strengths": [
                {
                    "metric_id": s.metric_id,
                    "metric_display_name": s.metric_display_name,
                    "level_tag": s.level_tag,
                    "reason_hint": s.reason_hint,
                }
                for s in p.strengths
            ],
            "weaknesses": [
                {
                    "metric_id": wk.metric_id,
                    "metric_display_name": wk.metric_display_name,
                    "level_tag": wk.level_tag,
                    "reason_hint": wk.reason_hint,
                }
                for wk in p.weaknesses
            ],
            "portfolio_return_total": float(p.return_breakdown.current.total_return),
        },
        "wallet_background": {
            "total_holdings_count": w.total_holdings_count,
            "excluded_from_this_portfolio_count": w.excluded_from_this_portfolio_count,
        },
    }
