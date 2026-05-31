"""
E3 입력 빌더.

Core + Supporting 지표만. Context 제외. Wallet 완전 배제.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from apps.portfolio.schemas import AnalysisContext


def build_e3_input(context: AnalysisContext) -> dict:
    """AnalysisContext → E3 입력 dict."""
    p = context.analysis_target_portfolio

    metrics: list[dict] = []
    for mr in p.core_metric_results + p.supporting_metric_results:
        metrics.append(
            {
                "metric_id": mr.metric_id,
                "metric_display_name": mr.metric_display_name,
                "tier": mr.tier.value,
                "value": float(mr.value) if mr.value is not None else None,
                "percentile": (
                    float(mr.percentile) if mr.percentile is not None else None
                ),
                "percentile_scope": mr.percentile_scope,
                "level_tag": mr.level_tag,
                "threshold_applied": (
                    float(mr.threshold_applied)
                    if mr.threshold_applied is not None
                    else None
                ),
                "passed_threshold": mr.passed_threshold,
            }
        )

    return {
        "preset_id": p.preset_id,
        "preset_name": p.preset_name,
        "preset_category": p.preset_category,
        "metrics": metrics,
    }
