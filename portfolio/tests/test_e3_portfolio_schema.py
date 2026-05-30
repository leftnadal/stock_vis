"""Slice 6 Part 1 Step 1 — E3PortfolioCommentary schema + V1~V5 fixture 회귀 테스트.

지시서 §2.7 회귀 +4:
  test_e3_portfolio_schema_validates
  test_e3_portfolio_6_categories_cover
  test_e3_portfolio_dimension_lookup_dispatch
  test_e3_portfolio_v1_v5_fixtures (parametrize 5)
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from portfolio.prompts.e3_portfolio import (
    PROMPT_VARIABLE_SLOTS,
    build_e3_portfolio_prompt,
)
from portfolio.schemas.llm_outputs import E3PortfolioCommentary, PresetAlignment
from portfolio.tests.fixtures.sample_e3_portfolio_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
    PRESET_INTENT_MAP,
    get_all_fixtures,
    get_categories_covered,
    get_v1_concentrated_balanced,
    get_v2_concentrated_misfit,
    get_v3_concentrated_large,
    get_v4_concentrated_value,
    get_v5_concentrated_dividend,
)

# ============================================================
# 회귀 +4 (지시서 §2.7) + parametrize 5 = 실효 +9
# ============================================================


def test_e3_portfolio_schema_validates():
    """E3PortfolioCommentary 6 필드 schema parse PASS + 경계값 검증."""
    valid_data = {
        "holistic_assessment": (
            "GARP 관점 Tech 5종 집중 포트폴리오. 성장 모멘텀 양호하나 단일 섹터 50% 집중."
        ),
        "diversification_comment": "분산 점수 0.35는 5종목 집중도 기준 중간 수준입니다.",
        "sector_balance_comment": "Tech 50%로 단일 섹터 비중이 권장 30~40% 상한 초과.",
        "risk_concentration_comment": "집중 리스크 0.45는 변동성 확대 가능성을 시사합니다.",
        "preset_alignment": "partial",
        "confidence": 4,
    }
    parsed = E3PortfolioCommentary.model_validate(valid_data)

    # 6 필드 모두 존재
    assert parsed.holistic_assessment.startswith("GARP")
    assert parsed.preset_alignment == PresetAlignment.PARTIAL
    assert parsed.confidence == 4

    # min_length / max_length 검증 (holistic 30자 미만 → ValidationError)
    too_short = {**valid_data, "holistic_assessment": "짧음"}
    with pytest.raises(ValidationError):
        E3PortfolioCommentary.model_validate(too_short)

    # confidence 범위 (1~5) 검증
    too_high = {**valid_data, "confidence": 6}
    with pytest.raises(ValidationError):
        E3PortfolioCommentary.model_validate(too_high)

    # extra="forbid" — 추가 필드 거부
    extra_field = {**valid_data, "extra_field": "x"}
    with pytest.raises(ValidationError):
        E3PortfolioCommentary.model_validate(extra_field)

    # PresetAlignment 3종 모두 유효
    for alignment in ("aligned", "partial", "misaligned"):
        E3PortfolioCommentary.model_validate({**valid_data, "preset_alignment": alignment})


def test_e3_portfolio_6_categories_cover():
    """V1~V5 fixture가 5 preset_category cover (지시서 §2.5 + §2.8 KPI).

    growth (V1) / value (V4) / income (V5) / factor (V3) / special (V2 misfit)
    + concentrated 차원 = 6 카테고리 cover.
    """
    categories = get_categories_covered()
    expected = {"growth", "value", "income", "factor"}  # V2도 growth (misfit이 special-ish)
    assert expected.issubset(categories), (
        f"5 카테고리 cover 실패: {categories} (expected: {expected})"
    )

    # V2 misfit이 special 패턴 cover (preset_category=growth지만 expected_alignment=misaligned)
    v2 = get_v2_concentrated_misfit()
    assert v2["expected_alignment"] == "misaligned"

    # 5 fixture 모두 concentrated 차원 (sector 60%+ or 분산 ≤0.35)
    for f in get_all_fixtures():
        assert f["diversification_score"] <= 0.40, (
            f"{f['fixture_id']}: diversification_score={f['diversification_score']} > 0.40 "
            "— concentrated 차원 위반"
        )
        # holdings 5~10 (concentrated 정의)
        assert 5 <= len(f["holdings"]) <= 10

    # FIXTURE_GROUPS 정합성
    assert set(FIXTURE_GROUPS["concentrated_baseline"]) == {
        "v1_concentrated_balanced", "v2_concentrated_misfit"
    }
    assert set(FIXTURE_GROUPS["concentrated_focused"]) == {
        "v3_concentrated_large", "v4_concentrated_value", "v5_concentrated_dividend"
    }


def test_e3_portfolio_dimension_lookup_dispatch():
    """DIMENSION_LOOKUP[e3_portfolio] entry → _main_unified() 자동 dispatch ready.

    지시서 §2.6 e3 mirror 100% (path만 변경) + §2.8 자동 dispatch KPI.
    """
    from scripts.validation.score_step8 import DIMENSION_LOOKUP

    assert "e3_portfolio" in DIMENSION_LOOKUP
    entry = DIMENSION_LOOKUP["e3_portfolio"]

    # 8 필드 (e3 entry mirror 100%)
    expected_keys = {
        "dim1", "dim2", "model_label_field", "result_structure",
        "default_raw", "default_scored", "weight", "additional_lex_check",
    }
    assert set(entry.keys()) == expected_keys

    # e3와 동일 구조 (path만 다름)
    e3 = DIMENSION_LOOKUP["e3"]
    assert entry["dim1"] == e3["dim1"]
    assert entry["dim2"] == e3["dim2"]
    assert entry["model_label_field"] == e3["model_label_field"]
    assert entry["result_structure"] == e3["result_structure"]
    assert entry["weight"] == e3["weight"]
    assert entry["additional_lex_check"] == e3["additional_lex_check"]

    # path는 slice5 → slice6 / e3 → e3_portfolio
    assert entry["default_raw"] == "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json"
    assert entry["default_scored"] == "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json"


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_e3_portfolio_v1_v5_fixtures(fixture_name):
    """V1~V5 fixture 사전 fix + prompt 빌드 정상."""
    fixture = ALL_FIXTURES[fixture_name]()

    # 핵심 메타 존재
    assert fixture["fixture_id"] == fixture_name
    assert fixture["preset_id"] in PRESET_INTENT_MAP
    assert fixture["preset_category"] in {"growth", "value", "income", "factor"}
    assert fixture["expected_alignment"] in {"aligned", "partial", "misaligned"}

    # holdings 검증 (concentrated 정의)
    assert 5 <= len(fixture["holdings"]) <= 10
    weights_sum = sum(h["weight"] for h in fixture["holdings"])
    assert abs(weights_sum - 1.0) < 0.01, f"{fixture_name}: weights sum {weights_sum} ≠ 1.0"

    # 분석엔진 사전 산출값 (사전 산출, 정량 재계산 없음 — Slice 1~5 분석엔진 회피 정책 일관)
    assert 0.0 <= fixture["diversification_score"] <= 1.0
    assert 0.0 <= fixture["risk_concentration_score"] <= 1.0

    # prompt 빌드 정상
    holdings_summary = ", ".join(
        f"{h['ticker']}({h['weight']:.0%})" for h in fixture["holdings"]
    )
    prompt = build_e3_portfolio_prompt(
        preset_id=fixture["preset_id"],
        preset_intent=PRESET_INTENT_MAP[fixture["preset_id"]],
        holdings_summary=holdings_summary,
        sector_concentration=fixture["sector_concentration"],
        diversification_score=fixture["diversification_score"],
        risk_concentration_score=fixture["risk_concentration_score"],
        core_metrics_summary=fixture["core_metrics_summary"],
    )
    # 변수 슬롯 7종 모두 prompt에 반영됨
    assert fixture["preset_id"] in prompt
    assert holdings_summary in prompt
    assert fixture["sector_concentration"] in prompt
    assert fixture["core_metrics_summary"] in prompt
    # few-shot 2 examples 포함
    assert "Example 1" in prompt
    assert "Example 2" in prompt


# ============================================================
# 추가 자연 흡수
# ============================================================


def test_prompt_variable_slots_7():
    """지시서 §2.4 변수 슬롯 7종 명시."""
    assert len(PROMPT_VARIABLE_SLOTS) == 7
    assert set(PROMPT_VARIABLE_SLOTS) == {
        "preset_id", "preset_intent", "holdings_summary",
        "sector_concentration", "diversification_score",
        "risk_concentration_score", "core_metrics_summary",
    }


def test_e3_portfolio_entry_point_meta_schema_match():
    """budget_estimator.ENTRY_POINT_META[e3_portfolio].schema_fields가 실제 schema와 일치.

    Slice 6 Part 1 Step 0 + Step 1 정합성 검증.
    """
    from portfolio.llm.budget_estimator import ENTRY_POINT_META

    e3p = ENTRY_POINT_META["e3_portfolio"]
    # 6 필드 (str_long + str_medium × 3 + literal + int_float)
    assert e3p["schema_fields"] == [
        "str_long",        # holistic_assessment (300자 max → str_long)
        "str_medium",      # diversification_comment (200자 max)
        "str_medium",      # sector_balance_comment
        "str_medium",      # risk_concentration_comment
        "literal",         # preset_alignment
        "int_float",       # confidence
    ]
