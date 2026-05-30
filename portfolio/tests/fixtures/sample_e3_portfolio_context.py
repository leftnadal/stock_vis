"""Slice 6 Part 1 Step 1 — concentrated_portfolio 변형 5종 fixture.

지시서 §2.5 V1~V5 (5 카테고리 cover):
  V1 concentrated_balanced     (5h, 1 sector 50%, div .35) — GARP, growth alignment
  V2 concentrated_misfit       (5h, 1 sector 80%, div .15) — GARP, growth misalignment (special-ish)
  V3 concentrated_large        (10h, 2 sector 70%, div .25) — quality_factor (factor)
  V4 concentrated_value        (5h, value-tilted)            — buffett_quality_value (value)
  V5 concentrated_dividend     (7h, dividend-tilted)         — dividend_growth (income)

5 카테고리 cover: growth(V1) / value(V4) / income(V5) / factor(V3) / special(V2 misfit)
Slice 5 hybrid 7 패턴 mirror, concentrated 추가 차원 (sector 60%+ 집중)만 신설.

사용처:
  - Slice 6 Part 2 Step 6 smoke
  - Slice 6 Part 2 Step 7 token 측정 (sample_prompts → e3_portfolio P90)
  - Slice 6 Part 2 Step 8 14 calls 회고 (haiku 7 + sonnet 7)
"""

from __future__ import annotations

from typing import Any

# ============================================================
# preset 메타 (Slice 5 hybrid 7 mirror)
# ============================================================

PRESET_INTENT_MAP: dict[str, str] = {
    "garp": "합리적 가격 성장 (Growth At Reasonable Price)",
    "buffett_quality_value": "지속적 자본 수익성 + 합리적 가격",
    "dividend_growth": "배당 성장 + 안정 수익",
    "quality_factor": "자본 효율성 + 수익성 quality",
    "contrarian": "역발상 저평가 + 기초 펀더멘탈",
}


# ============================================================
# V1~V5 fixture (concentrated_portfolio 정의: holdings 5~10 + sector 60%+ 집중)
# ============================================================


def get_v1_concentrated_balanced() -> dict[str, Any]:
    """V1 — GARP × Tech 5종 50% 집중, 분산 0.35 (preset partial alignment).

    growth 카테고리. Slice 5 e3_baseline_garp_tech mirror + portfolio-level 차원 추가.
    """
    return {
        "fixture_id": "v1_concentrated_balanced",
        "fixture_group": "concentrated_baseline",
        "preset_id": "garp",
        "preset_category": "growth",
        "expected_alignment": "partial",
        "holdings": [
            {"ticker": "MSFT", "weight": 0.30, "sector": "Tech"},
            {"ticker": "NVDA", "weight": 0.20, "sector": "Tech"},
            {"ticker": "AAPL", "weight": 0.15, "sector": "Tech"},
            {"ticker": "GOOG", "weight": 0.20, "sector": "Tech"},
            {"ticker": "META", "weight": 0.15, "sector": "Tech"},
        ],
        "sector_concentration": "Tech 50%",
        "diversification_score": 0.35,
        "risk_concentration_score": 0.45,
        "core_metrics_summary": (
            "PEG=1.8 (boundary), EPS_growth=15% (above 10%), "
            "ROIC=18% (above 15%), revenue_growth=14%, "
            "PE=22, ROE=24%, FCF_yield=3.8%"
        ),
    }


def get_v2_concentrated_misfit() -> dict[str, Any]:
    """V2 — GARP × Tech 80% 극단 집중, 분산 0.15 (preset misalignment).

    growth misfit (special-ish 패턴 cover). Slice 5 e3_baseline_garp_misfit mirror.
    """
    return {
        "fixture_id": "v2_concentrated_misfit",
        "fixture_group": "concentrated_misfit",
        "preset_id": "garp",
        "preset_category": "growth",
        "expected_alignment": "misaligned",
        "holdings": [
            {"ticker": "TSLA", "weight": 0.40, "sector": "Tech"},
            {"ticker": "PLTR", "weight": 0.20, "sector": "Tech"},
            {"ticker": "SHOP", "weight": 0.20, "sector": "Tech"},
            {"ticker": "DDOG", "weight": 0.10, "sector": "Tech"},
            {"ticker": "SNOW", "weight": 0.10, "sector": "Tech"},
        ],
        "sector_concentration": "Tech 80%",
        "diversification_score": 0.15,
        "risk_concentration_score": 0.80,
        "core_metrics_summary": (
            "PEG=3.2 (well above 1.5), EPS_growth=4% (well below 10%), "
            "ROIC=6% (well below 15%), revenue_growth=12%, "
            "PE=65 (extreme), ROE=8%, FCF_yield=0.5%"
        ),
    }


def get_v3_concentrated_large() -> dict[str, Any]:
    """V3 — quality_factor × Tech+Healthcare 2 sector 70% 집중, 10 holdings.

    factor 카테고리. Slice 5 e3_baseline_garp_large mirror + factor preset.
    """
    return {
        "fixture_id": "v3_concentrated_large",
        "fixture_group": "concentrated_large",
        "preset_id": "quality_factor",
        "preset_category": "factor",
        "expected_alignment": "partial",
        "holdings": [
            {"ticker": "MSFT", "weight": 0.15, "sector": "Tech"},
            {"ticker": "AAPL", "weight": 0.12, "sector": "Tech"},
            {"ticker": "GOOG", "weight": 0.10, "sector": "Tech"},
            {"ticker": "JNJ", "weight": 0.12, "sector": "Healthcare"},
            {"ticker": "UNH", "weight": 0.10, "sector": "Healthcare"},
            {"ticker": "PFE", "weight": 0.08, "sector": "Healthcare"},
            {"ticker": "V", "weight": 0.08, "sector": "Tech"},
            {"ticker": "MA", "weight": 0.07, "sector": "Tech"},
            {"ticker": "ABT", "weight": 0.10, "sector": "Healthcare"},
            {"ticker": "TMO", "weight": 0.08, "sector": "Healthcare"},
        ],
        "sector_concentration": "Tech 52% + Healthcare 48% (top 2 sectors 100%, top 1=52%)",
        "diversification_score": 0.25,
        "risk_concentration_score": 0.40,
        "core_metrics_summary": (
            "ROIC=22% (above 15% factor 임계), gross_margin=58%, "
            "earnings_quality=0.85, FCF_yield=4.5%, "
            "EPS_stability_5y=0.92, debt_to_equity=0.35, ROA=12%"
        ),
    }


def get_v4_concentrated_value() -> dict[str, Any]:
    """V4 — buffett_quality_value × value-tilted 5 holdings 60% 집중.

    value 카테고리.
    """
    return {
        "fixture_id": "v4_concentrated_value",
        "fixture_group": "concentrated_value",
        "preset_id": "buffett_quality_value",
        "preset_category": "value",
        "expected_alignment": "aligned",
        "holdings": [
            {"ticker": "BRK.B", "weight": 0.30, "sector": "Financials"},
            {"ticker": "JPM", "weight": 0.20, "sector": "Financials"},
            {"ticker": "BAC", "weight": 0.15, "sector": "Financials"},
            {"ticker": "WFC", "weight": 0.15, "sector": "Financials"},
            {"ticker": "MS", "weight": 0.20, "sector": "Financials"},
        ],
        "sector_concentration": "Financials 100% (extreme)",
        "diversification_score": 0.20,
        "risk_concentration_score": 0.55,
        "core_metrics_summary": (
            "ROIC=16% (above 15%), PE=11 (below 15), PB=1.4, "
            "FCF_yield=7.5%, dividend_yield=2.8%, "
            "earnings_quality=0.78, debt_to_equity=0.65"
        ),
    }


def get_v5_concentrated_dividend() -> dict[str, Any]:
    """V5 — dividend_growth × Consumer Staples 60% 집중, 7 holdings.

    income 카테고리.
    """
    return {
        "fixture_id": "v5_concentrated_dividend",
        "fixture_group": "concentrated_dividend",
        "preset_id": "dividend_growth",
        "preset_category": "income",
        "expected_alignment": "aligned",
        "holdings": [
            {"ticker": "KO", "weight": 0.25, "sector": "Consumer Staples"},
            {"ticker": "PG", "weight": 0.18, "sector": "Consumer Staples"},
            {"ticker": "PEP", "weight": 0.15, "sector": "Consumer Staples"},
            {"ticker": "JNJ", "weight": 0.12, "sector": "Healthcare"},
            {"ticker": "MMM", "weight": 0.10, "sector": "Industrials"},
            {"ticker": "MO", "weight": 0.10, "sector": "Consumer Staples"},
            {"ticker": "CL", "weight": 0.10, "sector": "Consumer Staples"},
        ],
        "sector_concentration": "Consumer Staples 78%",
        "diversification_score": 0.30,
        "risk_concentration_score": 0.35,
        "core_metrics_summary": (
            "dividend_yield=3.8%, dividend_growth_5y=7.2%, payout_ratio=62%, "
            "EPS_growth=4.5%, ROIC=15%, FCF_coverage=1.8x, "
            "consecutive_dividend_years=25"
        ),
    }


# ============================================================
# 그룹 메타 + ALL_FIXTURES dict
# ============================================================

FIXTURE_GROUPS: dict[str, list[str]] = {
    "concentrated_baseline": [
        "v1_concentrated_balanced",
        "v2_concentrated_misfit",
    ],
    "concentrated_focused": [
        "v3_concentrated_large",
        "v4_concentrated_value",
        "v5_concentrated_dividend",
    ],
}


ALL_FIXTURES: dict[str, Any] = {
    "v1_concentrated_balanced": get_v1_concentrated_balanced,
    "v2_concentrated_misfit": get_v2_concentrated_misfit,
    "v3_concentrated_large": get_v3_concentrated_large,
    "v4_concentrated_value": get_v4_concentrated_value,
    "v5_concentrated_dividend": get_v5_concentrated_dividend,
}


def get_all_fixtures() -> list[dict[str, Any]]:
    """5 fixture 리스트 (테스트 parametrize용)."""
    return [fn() for fn in ALL_FIXTURES.values()]


def get_categories_covered() -> set[str]:
    """5 fixture가 cover하는 preset_category 집합."""
    return {f["preset_category"] for f in get_all_fixtures()}
