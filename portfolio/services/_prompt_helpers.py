"""Prompt builder 공통 헬퍼.

Slice 2 백로그 #4 — _format_analysis_summary 등 진입점 무관 헬퍼 분리.
Slice 3 Step 2에서 자연 흡수.
"""

from __future__ import annotations

from typing import Any


def format_holdings_summary(holdings: list[dict]) -> str:
    """Holdings 리스트 → 'TICKER(weight%)' 컴마 구분 문자열.

    예: "MSFT(30%), TSLA(20%), NVDA(50%)"
    """
    parts: list[str] = []
    for h in holdings:
        ticker = h.get("ticker") or h.get("stock_symbol") or "?"
        try:
            w = float(h.get("weight", 0))
            parts.append(f"{ticker}({w:.0%})")
        except (TypeError, ValueError):
            parts.append(f"{ticker}(?)")
    return ", ".join(parts)


def format_analysis_summary(ctx: dict[str, Any], max_chars: int = 200) -> str:
    """AnalysisContext에서 한 줄 진단 요약 추출.

    Slice 2 I4 모니터링 — 200자 truncate 유지 (Slice 2 max util 15.12%).
    Slice 3 Step 7 측정 후 조정 가능.
    """
    summary = ctx.get("analysis_summary", {}) or {}
    one_line = summary.get("one_line_diagnosis") or "분석 결과 없음"
    return str(one_line)[:max_chars]


def format_metrics_table(metrics: dict[str, Any]) -> str:
    """주요 지표 → markdown 표.

    예:
        | Metric | Value |
        |---|---|
        | P/E | 12.50 |
        | ROE | 0.18 |
    """
    if not metrics:
        return "(지표 데이터 없음)"
    lines = ["| Metric | Value |", "|---|---|"]
    for key, value in metrics.items():
        if isinstance(value, dict):
            v = value.get("value")
            display = f"{v:.4f}" if isinstance(v, float) else str(v)
        elif isinstance(value, float):
            display = f"{value:.4f}"
        else:
            display = str(value)
        lines.append(f"| {key} | {display} |")
    return "\n".join(lines)
