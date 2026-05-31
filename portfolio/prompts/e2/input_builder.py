"""
E2 입력 빌더.

약점 각각에 대해 metric 상세 정보를 Core/Supporting/Context 결과에서 찾아 부착.
per_holding 상세 배열은 스키마에 없으므로 백엔드가 추후 주입할 수 있도록
빈 리스트 자리만 열어둔다.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from portfolio.schemas import AnalysisContext
from portfolio.schemas.metric_result import MetricResult


def _find_metric_detail(
    metric_id: str,
    *,
    core: list[MetricResult],
    supporting: list[MetricResult],
    context: list[MetricResult],
) -> MetricResult | None:
    for mr in core + supporting + context:
        if mr.metric_id == metric_id:
            return mr
    return None


def build_e2_input(context: AnalysisContext) -> dict:
    """AnalysisContext에서 E2용 입력 dict 생성 (약점 상세 포함)."""
    p = context.analysis_target_portfolio

    weaknesses_detail: list[dict] = []
    for weakness in p.weaknesses:
        detail = _find_metric_detail(
            weakness.metric_id,
            core=p.core_metric_results,
            supporting=p.supporting_metric_results,
            context=p.context_metric_results,
        )
        entry: dict = {
            "metric_id": weakness.metric_id,
            "metric_display_name": weakness.metric_display_name,
            "level_tag": weakness.level_tag,
            "reason_hint": weakness.reason_hint,
        }
        if detail is not None:
            entry.update(
                {
                    "tier": detail.tier.value,
                    "avg_value": float(detail.value)
                    if detail.value is not None
                    else None,
                    "percentile": float(detail.percentile)
                    if detail.percentile is not None
                    else None,
                    "percentile_scope": detail.percentile_scope,
                    "threshold_applied": (
                        float(detail.threshold_applied)
                        if detail.threshold_applied is not None
                        else None
                    ),
                    "passed_threshold": detail.passed_threshold,
                }
            )
        # per_holding 은 백엔드가 배열을 채워 넣기 전까지 빈 리스트
        entry.setdefault("per_holding", [])
        weaknesses_detail.append(entry)

    return {
        "analysis_target_portfolio": {
            "portfolio_name": p.portfolio_name,
            "preset_id": p.preset_id,
            "preset_name": p.preset_name,
            "preset_category": p.preset_category,
            "holding_count": p.holding_count,
            "weaknesses_detail": weaknesses_detail,
            "holdings_summary_light": [
                {
                    "symbol": h.stock_symbol,
                    "sector": h.sector,
                    "weight": float(h.weight),
                }
                for h in p.holdings_summary
            ],
        },
        "wallet_background": {
            "excluded_from_this_portfolio_count": (
                context.wallet_background.excluded_from_this_portfolio_count
            ),
        },
    }
