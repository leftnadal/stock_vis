"""E2 진입점 fixture — AnalysisContext (DiagnosticCard 입력, Slice 3 Step 5).

Q4 수정 (hybrid 결정):
  - slice1_baseline 그룹 (3개): garp_tech / garp_misfit / garp_large 재활용
  - e2_focused 그룹 (4개): clear_strengths / clear_weaknesses / balanced / extreme_risk

총 7개 fixture. fixture_group 메타로 Step 8 그룹 비교 분석에서 활용.
"""

from __future__ import annotations

from typing import Any

from portfolio.schemas import AnalysisContext
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)


# fixture 그룹 메타 (Step 8 회고에서 그룹 비교 분석)
FIXTURE_GROUPS: dict[str, list[str]] = {
    "slice1_baseline": ["garp_tech", "garp_misfit", "garp_large"],
    "e2_focused": [
        "e2_clear_strengths",
        "e2_clear_weaknesses",
        "e2_balanced",
        "e2_extreme_risk",
    ],
}


def _wrap_for_e2(ctx: AnalysisContext) -> dict[str, Any]:
    """AnalysisContext (Pydantic) → E2 입력 형태 dict.

    E2 service의 build_e2_prompt가 holdings/analysis_summary/metrics 등 dict 키를
    참조하므로 portfolio level 메타만 추출해서 평탄화.
    """
    p = ctx.analysis_target_portfolio
    return {
        "preset_id": p.preset_id,
        "holdings": [
            {
                "ticker": h.stock_symbol,
                "weight": float(h.weight),
                "sector": h.sector,
            }
            for h in p.holdings_summary
        ],
        "metrics": {
            m.metric_id: {
                "tier": m.tier.value,
                "value": float(m.value) if m.value is not None else None,
                "level_tag": m.level_tag,
            }
            for m in p.core_metric_results + p.supporting_metric_results
        },
        "analysis_summary": {
            "one_line_diagnosis": f"{p.preset_name} 적합도 분석 결과.",
            "preset_id": p.preset_id,
            "preset_name": p.preset_name,
        },
        "preset_version": "v1.0",
    }


# ============================================================
# Slice 1 baseline 그룹 (3개 재활용)
# ============================================================


def get_e2_fixture_garp_tech() -> dict[str, Any]:
    return {
        "fixture_group": "slice1_baseline",
        "analysis_context": _wrap_for_e2(get_context_garp_tech()),
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["GARP", "적합", "기술"],
        },
    }


def get_e2_fixture_garp_misfit() -> dict[str, Any]:
    return {
        "fixture_group": "slice1_baseline",
        "analysis_context": _wrap_for_e2(get_context_garp_misfit()),
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 2,
            "actions_min": 2,
            "summary_keywords_any": ["부적합", "MISFIT", "재검토", "약점"],
        },
    }


def get_e2_fixture_garp_large() -> dict[str, Any]:
    return {
        "fixture_group": "slice1_baseline",
        "analysis_context": _wrap_for_e2(get_context_garp_large()),
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["다각화", "분산", "포트폴리오"],
        },
    }


# ============================================================
# E2 focused 그룹 (4개 신규)
# ============================================================


def get_e2_fixture_clear_strengths() -> dict[str, Any]:
    """강점만 명확한 케이스."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "AAPL", "weight": 0.4, "sector": "Tech"},
                {"ticker": "MSFT", "weight": 0.6, "sector": "Tech"},
            ],
            "metrics": {
                "P/E": 18.5,
                "ROE": 0.32,
                "EarningsGrowth": 0.22,
                "Debt/Equity": 0.15,
            },
            "analysis_summary": {
                "one_line_diagnosis": "ROE 32%, 성장률 22%, 부채비율 15% — 모든 지표 우수.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 2,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["우수", "양호", "강점"],
        },
    }


def get_e2_fixture_clear_weaknesses() -> dict[str, Any]:
    """약점만 명확한 케이스."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "TSLA", "weight": 0.5, "sector": "Auto"},
                {"ticker": "PLTR", "weight": 0.5, "sector": "Tech"},
            ],
            "metrics": {
                "P/E": 95,
                "ROE": 0.05,
                "EarningsGrowth": -0.10,
                "Debt/Equity": 0.85,
            },
            "analysis_summary": {
                "one_line_diagnosis": "P/E 95, ROE 5%, 성장률 -10%, 부채비율 85% — 다중 약점.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 2,
            "actions_min": 2,
            "summary_keywords_any": ["부적합", "위험", "약점"],
        },
    }


def get_e2_fixture_balanced() -> dict[str, Any]:
    """4요소 균형 — naturalness 평가용."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.25, "sector": "Tech"},
                {"ticker": "JNJ", "weight": 0.25, "sector": "Healthcare"},
                {"ticker": "V", "weight": 0.25, "sector": "Financial"},
                {"ticker": "PG", "weight": 0.25, "sector": "Consumer"},
            ],
            "metrics": {
                "P/E": 22,
                "ROE": 0.18,
                "EarningsGrowth": 0.12,
                "Debt/Equity": 0.40,
            },
            "analysis_summary": {
                "one_line_diagnosis": "균형 잡힌 포트폴리오. 각 지표 평균 수준.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["균형", "안정", "적정"],
        },
    }


def get_e2_fixture_extreme_risk() -> dict[str, Any]:
    """집중 위험 — insight 평가용. 표면 지표는 양호하나 단일 종목 70% 집중."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "META", "weight": 0.7, "sector": "Tech"},
                {"ticker": "AMZN", "weight": 0.3, "sector": "Consumer"},
            ],
            "metrics": {
                "P/E": 25,
                "ROE": 0.20,
                "EarningsGrowth": 0.15,
                "Debt/Equity": 0.30,
                "Concentration": 0.70,
            },
            "analysis_summary": {
                "one_line_diagnosis": "지표는 양호하나 단일 종목 70% — 집중 위험 우려.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["집중", "위험", "분산"],
        },
    }


ALL_FIXTURES: dict[str, Any] = {
    "garp_tech": get_e2_fixture_garp_tech,
    "garp_misfit": get_e2_fixture_garp_misfit,
    "garp_large": get_e2_fixture_garp_large,
    "e2_clear_strengths": get_e2_fixture_clear_strengths,
    "e2_clear_weaknesses": get_e2_fixture_clear_weaknesses,
    "e2_balanced": get_e2_fixture_balanced,
    "e2_extreme_risk": get_e2_fixture_extreme_risk,
}
