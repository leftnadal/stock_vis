"""E3 (지표 코멘트, 한 줄 자연어) fixture — Slice 5 Step 5.

Hybrid 7 패턴 (Slice 1·3·4 mirror):
  - baseline 그룹 (3개): Slice 1 자산 GARP 재활용 (garp_tech / garp_misfit / garp_large)
  - focused 그룹 (4개): preset 다양성 검증 — value / income / factor / special 4 카테고리

5 카테고리 cover (지시서 §1.1):
  - value: buffett_quality_value (focused)
  - growth: garp (baseline 3개 모두)
  - income: dividend_growth (focused)
  - factor: quality_factor (focused)
  - special: contrarian (focused)

`concentrated_portfolio`는 백로그 #20 (Slice 6+ 별도 슬라이스) — 본 fixture에서 제외.

사용처:
  - Slice 5 Step 4 통합 테스트 보조
  - Slice 5 Part 2 Step 8 회고 (haiku 7 + sonnet 7 = 14 calls)
"""

from __future__ import annotations

from typing import Any

from portfolio.schemas import AnalysisContext
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)


# fixture 그룹 메타 (Step 8 회고 그룹 비교용)
FIXTURE_GROUPS: dict[str, list[str]] = {
    "garp_baseline": [
        "e3_baseline_garp_tech",
        "e3_baseline_garp_misfit",
        "e3_baseline_garp_large",
    ],
    "preset_focused": [
        "e3_focused_buffett",
        "e3_focused_dividend_growth",
        "e3_focused_quality_factor",
        "e3_focused_contrarian",
    ],
}


def _wrap(
    ctx: AnalysisContext,
    *,
    fixture_id: str,
    fixture_group: str,
    expected_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """AnalysisContext → E3 fixture dict (메타 + analysis_context dump)."""
    return {
        "fixture_id": fixture_id,
        "fixture_group": fixture_group,
        "analysis_context": ctx.model_dump(mode="json"),
        "preset_id": ctx.analysis_target_portfolio.preset_id,
        "preset_category": ctx.analysis_target_portfolio.preset_category,
        "expected_keywords": expected_keywords or [],
    }


def _retarget_preset(
    ctx: AnalysisContext,
    *,
    preset_id: str,
    preset_name: str,
    preset_category: str,
) -> AnalysisContext:
    """기존 AnalysisContext의 preset 메타만 변경 (metric_results는 그대로 유지).

    preset 다양성 검증 — 동일 metric에 대해 다른 preset 관점에서 코멘트 생성하는 패턴.
    Slice 5 핵심 가설: "GARP에서 학습한 평가 차원이 다른 preset에 외삽 가능한가?"
    """
    p = ctx.analysis_target_portfolio
    new_p = p.model_copy(
        update={
            "preset_id": preset_id,
            "preset_name": preset_name,
            "preset_category": preset_category,
        }
    )
    return ctx.model_copy(update={"analysis_target_portfolio": new_p})


# ============================================================
# baseline 그룹 (3개) — Slice 1 GARP 재활용
# ============================================================


def get_e3_fixture_baseline_garp_tech() -> dict[str, Any]:
    """GARP + Tech 집중 (Slice 1 garp_tech 재활용, 5 holdings)."""
    return _wrap(
        get_context_garp_tech(),
        fixture_id="e3_baseline_garp_tech",
        fixture_group="garp_baseline",
        expected_keywords=["GARP", "성장", "PEG"],
    )


def get_e3_fixture_baseline_garp_misfit() -> dict[str, Any]:
    """GARP misfit (Slice 1 garp_misfit 재활용)."""
    return _wrap(
        get_context_garp_misfit(),
        fixture_id="e3_baseline_garp_misfit",
        fixture_group="garp_baseline",
        expected_keywords=["GARP", "재검토"],
    )


def get_e3_fixture_baseline_garp_large() -> dict[str, Any]:
    """GARP + 15 holdings (Slice 1 garp_large 재활용 — 토큰 효과 검증용)."""
    return _wrap(
        get_context_garp_large(),
        fixture_id="e3_baseline_garp_large",
        fixture_group="garp_baseline",
        expected_keywords=["GARP", "분산"],
    )


# ============================================================
# focused 그룹 (4개) — 4 preset 신규 (5 카테고리 cover)
# ============================================================


def get_e3_fixture_focused_buffett() -> dict[str, Any]:
    """value 카테고리 — Buffett Quality Value preset 외삽."""
    base = get_context_garp_tech()
    ctx = _retarget_preset(
        base,
        preset_id="buffett_quality_value",
        preset_name="Buffett Quality Value",
        preset_category="value",
    )
    return _wrap(
        ctx,
        fixture_id="e3_focused_buffett",
        fixture_group="preset_focused",
        expected_keywords=["퀄리티", "ROIC", "안정"],
    )


def get_e3_fixture_focused_dividend_growth() -> dict[str, Any]:
    """income 카테고리 — Dividend Growth preset 외삽."""
    base = get_context_garp_tech()
    ctx = _retarget_preset(
        base,
        preset_id="dividend_growth",
        preset_name="Dividend Growth",
        preset_category="income",
    )
    return _wrap(
        ctx,
        fixture_id="e3_focused_dividend_growth",
        fixture_group="preset_focused",
        expected_keywords=["배당", "지속"],
    )


def get_e3_fixture_focused_quality_factor() -> dict[str, Any]:
    """factor 카테고리 — Quality Factor preset 외삽."""
    base = get_context_garp_tech()
    ctx = _retarget_preset(
        base,
        preset_id="quality_factor",
        preset_name="Quality Factor",
        preset_category="factor",
    )
    return _wrap(
        ctx,
        fixture_id="e3_focused_quality_factor",
        fixture_group="preset_focused",
        expected_keywords=["퀄리티", "수익성"],
    )


def get_e3_fixture_focused_contrarian() -> dict[str, Any]:
    """special 카테고리 — Contrarian preset 외삽 (pe_ratio 역방향)."""
    base = get_context_garp_tech()
    ctx = _retarget_preset(
        base,
        preset_id="contrarian",
        preset_name="Contrarian",
        preset_category="special",
    )
    return _wrap(
        ctx,
        fixture_id="e3_focused_contrarian",
        fixture_group="preset_focused",
        expected_keywords=["역발상", "저평가"],
    )


# ============================================================
# 헬퍼 — 전체 fixture dict
# ============================================================


ALL_FIXTURES: dict[str, Any] = {
    "e3_baseline_garp_tech": get_e3_fixture_baseline_garp_tech,
    "e3_baseline_garp_misfit": get_e3_fixture_baseline_garp_misfit,
    "e3_baseline_garp_large": get_e3_fixture_baseline_garp_large,
    "e3_focused_buffett": get_e3_fixture_focused_buffett,
    "e3_focused_dividend_growth": get_e3_fixture_focused_dividend_growth,
    "e3_focused_quality_factor": get_e3_fixture_focused_quality_factor,
    "e3_focused_contrarian": get_e3_fixture_focused_contrarian,
}


def get_all_fixtures() -> list[dict[str, Any]]:
    return [fn() for fn in ALL_FIXTURES.values()]


def get_baseline_fixtures() -> list[dict[str, Any]]:
    return [fn() for name, fn in ALL_FIXTURES.items() if name.startswith("e3_baseline")]


def get_focused_fixtures() -> list[dict[str, Any]]:
    return [fn() for name, fn in ALL_FIXTURES.items() if name.startswith("e3_focused")]


def get_covered_categories() -> set[str]:
    """5 카테고리 cover 검증용: 7 fixture의 preset_category 집합."""
    return {fn()["preset_category"] for fn in ALL_FIXTURES.values()}
