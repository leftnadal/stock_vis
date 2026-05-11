"""
E6 입력 빌더.

두 AnalysisContext(원본 + 조정) 를 받아 LLM이 비교하기 쉬운 diff 요약으로 변환.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from portfolio.schemas import AnalysisContext
from portfolio.schemas.analysis_context import AnalysisTargetPortfolioContext


def _summarize(p: AnalysisTargetPortfolioContext) -> dict:
    return {
        "strengths": [
            {
                "metric_id": s.metric_id,
                "level_tag": s.level_tag,
                "reason_hint": s.reason_hint,
            }
            for s in p.strengths
        ],
        "weaknesses": [
            {
                "metric_id": w.metric_id,
                "level_tag": w.level_tag,
                "reason_hint": w.reason_hint,
            }
            for w in p.weaknesses
        ],
        "diagnostic_cards": [
            {
                "weakness_metric_id": c.weakness_metric_id,
                "severity": c.severity.value,
                "structural_or_single": c.structural_or_single.value,
            }
            for c in p.diagnostic_cards
        ],
        "total_return": float(p.return_breakdown.current.total_return),
    }


def build_e6_input(
    original_context: AnalysisContext,
    adjusted_context: AnalysisContext,
    applied_overrides: list[dict],
) -> dict:
    """원본 + 조정 AnalysisContext + 적용 overrides → E6용 입력 dict."""
    op = original_context.analysis_target_portfolio
    ap = adjusted_context.analysis_target_portfolio

    return {
        "preset_id": op.preset_id,
        "preset_name": op.preset_name,
        "original_summary": _summarize(op),
        "adjusted_summary": _summarize(ap),
        "applied_overrides": applied_overrides,
    }
