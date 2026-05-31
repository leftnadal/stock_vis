"""Prompt builder 공통 헬퍼.

Slice 2 백로그 #4 — _format_analysis_summary 등 진입점 무관 헬퍼 분리.
Slice 3 Step 2에서 자연 흡수.
Slice 5 Part 2 Step 9 — 백로그 #11 일반화 (format_metrics_to_str).
"""

from __future__ import annotations

import json
from typing import Any, Literal


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


def format_metrics_to_str(
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    format: Literal["markdown", "json"] = "markdown",
) -> str:
    """Metric 데이터를 prompt용 문자열로 직렬화.

    백로그 #11 일반화 (Slice 5 Part 2 Step 9, PS 1.5).

    - format="markdown": E2 dict[str, value] → markdown 표
    - format="json":     E3 list[dict] / dict → indented JSON
                         (한국어 ensure_ascii=False, default=str fallback)
    """
    if format == "markdown":
        return _format_markdown(data)
    if format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    raise ValueError(f"Unknown format: {format!r}. Valid: 'markdown' | 'json'")


def _format_markdown(metrics: dict[str, Any]) -> str:
    """기존 format_metrics_table 본문 (자료 #4 인용).

    빈 dict / list / None 모두 "(지표 데이터 없음)" 반환.
    list 입력은 markdown 표 부적합 — empty 표시 (백로그 #11 PS 0.5 예외).
    """
    if not metrics or not isinstance(metrics, dict):
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


def format_metrics_table(metrics: dict[str, Any]) -> str:
    """[Deprecated — Slice 5 Part 2 Step 9 백로그 #11 일반화]

    호환성을 위해 유지. format_metrics_to_str(metrics, format='markdown') 호출 wrapper.
    Slice 6+ 백로그 #21로 제거 검토 (PS 0.5).

    예:
        | Metric | Value |
        |---|---|
        | P/E | 12.50 |
        | ROE | 0.18 |
    """
    return format_metrics_to_str(metrics, format="markdown")
