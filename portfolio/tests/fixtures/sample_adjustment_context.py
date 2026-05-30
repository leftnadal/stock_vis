"""
Slice 2 Step 5 — E5 진입점 fixture: 분석 결과 + 자연어 명령 쌍.

Slice 1 GARP 분석 결과 (AnalysisContext Pydantic) 을 dict로 wrap해서
E5 입력 형식으로 변환.

v2 변경 (사용자 컨펌):
  - C3: COMMANDS dict 단일 진실 출처 — fixture 모두 COMMANDS 참조
  - I1: ambiguous → no_intent_chitchat 으로 의미 통합
        + unclear_amount 보조 fixture 신설

총 7개 fixture: clear_decrease / clear_multi / unclear_amount /
no_intent_question / no_intent_chitchat / remove / large.
"""

from __future__ import annotations

from typing import Any, Callable

from portfolio.schemas import AnalysisContext
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)

# COMMANDS는 모든 fixture가 참조하는 단일 진실 출처(SSoT).
COMMANDS: dict[str, str] = {
    "clear_decrease":     "TSLA 비중 좀 줄여줘. 너무 많은 것 같아.",
    "clear_multi":        "TSLA는 줄이고 NVDA는 좀 늘려줘.",
    "unclear_amount":     "TSLA 좀 줄여",
    "no_intent_question": "GARP 프리셋이 뭐야?",
    "no_intent_chitchat": "포트폴리오가 좀 불안한데 어떻게 할까?",
    "remove":             "PLTR은 빼버릴게.",
    "large_multi":        "변동성 큰 종목들 비중 좀 줄여줘. TSLA, PLTR, SHOP.",
}


def _wrap_context(ctx: AnalysisContext) -> dict[str, Any]:
    """
    AnalysisContext (Pydantic) → E5 입력 형태 dict.

    E5 service의 build_e5_prompt가 holdings/analysis_summary 등 dict 키를
    참조하므로 portfolio level 메타만 추출해서 평탄화.
    """
    p = ctx.analysis_target_portfolio
    return {
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
            "one_line_diagnosis": "GARP 적합도는 보통. TSLA, PLTR 변동성 우려.",
            "preset_id": p.preset_id,
            "preset_name": p.preset_name,
        },
        "preset_version": "v1.0",
    }


def _wrap_garp_tech_with_tsla() -> dict[str, Any]:
    """garp_tech 기반 + holdings의 가장 작은 weight 종목을 TSLA로 치환.

    Step 6에서 발견된 fixture-command 정합성 이슈 해소용 (refactor_backlog_slice2.md):
    user_command가 TSLA를 언급하므로 holdings에 TSLA가 존재해야 함.
    garp_tech 자체는 변경하지 않고 wrap 결과만 후처리.
    """
    ctx_dict = _wrap_context(get_context_garp_tech())
    least = min(ctx_dict["holdings"], key=lambda h: h["weight"])
    least["ticker"] = "TSLA"
    least["sector"] = "Consumer Discretionary"
    return ctx_dict


# ============================================================
# fixture 함수 — 각 함수는 (analysis_context dict, user_command, expected) 반환
# ============================================================


def get_e5_fixture_clear_decrease() -> dict[str, Any]:
    """단일 종목 명확 축소 명령 (Tech fixture + TSLA 보장)."""
    return {
        "analysis_context": _wrap_garp_tech_with_tsla(),
        "user_command": COMMANDS["clear_decrease"],
        "expected": {
            "adjustments_min_count": 1,
            "expected_tickers": {"TSLA"},
            "expected_actions": {"decrease"},
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_clear_multi() -> dict[str, Any]:
    """다중 종목 명확 명령 (Tech fixture + TSLA 보장)."""
    return {
        "analysis_context": _wrap_garp_tech_with_tsla(),
        "user_command": COMMANDS["clear_multi"],
        "expected": {
            "adjustments_min_count": 2,
            "expected_tickers": {"TSLA", "NVDA"},
            "expected_actions": {"decrease", "increase"},
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_unclear_amount() -> dict[str, Any]:
    """비중 수치 미명시 명령 — delta_weight=null 기대 (Tech fixture + TSLA 보장)."""
    return {
        "analysis_context": _wrap_garp_tech_with_tsla(),
        "user_command": COMMANDS["unclear_amount"],
        "expected": {
            "adjustments_min_count": 1,
            "expected_tickers": {"TSLA"},
            "expected_actions": {"decrease"},
            "delta_weight_required_null": True,
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_no_intent_question() -> dict[str, Any]:
    """질문 — no_actionable_intent=True 기대."""
    return {
        "analysis_context": _wrap_context(get_context_garp_tech()),
        "user_command": COMMANDS["no_intent_question"],
        "expected": {
            "adjustments_count": 0,
            "no_actionable_intent": True,
        },
    }


def get_e5_fixture_no_intent_chitchat() -> dict[str, Any]:
    """모호한 잡담/도움 요청 — no_actionable_intent=True 기대."""
    return {
        "analysis_context": _wrap_context(get_context_garp_misfit()),
        "user_command": COMMANDS["no_intent_chitchat"],
        "expected": {
            "adjustments_count": 0,
            "no_actionable_intent": True,
        },
    }


def get_e5_fixture_remove() -> dict[str, Any]:
    """종목 제거 명령 (action=remove)."""
    return {
        "analysis_context": _wrap_context(get_context_garp_large()),
        "user_command": COMMANDS["remove"],
        "expected": {
            "adjustments_min_count": 1,
            "expected_tickers": {"PLTR"},
            "expected_actions": {"remove"},
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_large() -> dict[str, Any]:
    """large fixture (종목 15) — 토큰 예산 검증용."""
    return {
        "analysis_context": _wrap_context(get_context_garp_large()),
        "user_command": COMMANDS["large_multi"],
        "expected": {
            "adjustments_min_count": 3,
            "expected_tickers": {"TSLA", "PLTR", "SHOP"},
            "expected_actions": {"decrease"},
            "no_actionable_intent": False,
        },
    }


ALL_FIXTURES: dict[str, Callable[[], dict[str, Any]]] = {
    "clear_decrease":     get_e5_fixture_clear_decrease,
    "clear_multi":        get_e5_fixture_clear_multi,
    "unclear_amount":     get_e5_fixture_unclear_amount,
    "no_intent_question": get_e5_fixture_no_intent_question,
    "no_intent_chitchat": get_e5_fixture_no_intent_chitchat,
    "remove":             get_e5_fixture_remove,
    "large_multi":        get_e5_fixture_large,
}
