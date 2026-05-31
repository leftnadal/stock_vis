"""Slice 6 Part 2 Step B — E3 portfolio service 흐름 단위 테스트.

지시서 §2.6 회귀 +10~15:
  test_e3_portfolio_service_v1_haiku_mock_flow
  test_e3_portfolio_service_v1_sonnet_mock_flow
  ... (V1~V5 × haiku/sonnet 10건 parametrize)
  test_e3_portfolio_service_invalid_mock_raises_validation_error
  test_e3_portfolio_service_preset_alignment_enum_strict
  test_e3_portfolio_service_cost_guard_integration

서비스 흐름 4단계:
  1. build_e3_portfolio_prompt(context) → prompt
  2. load_mock_response(fixture_id, model_label) → raw text (mock)
  3. parse_e3_portfolio_response(raw) → E3PortfolioCommentary
  4. validate (Pydantic 자동 — parse 통과 = validate 통과)
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from apps.portfolio.llm.cost_guard import CostGuard
from apps.portfolio.schemas.llm_outputs import E3PortfolioCommentary, PresetAlignment
from apps.portfolio.services.e3_portfolio_service import (
    MOCK_FIXTURE_ROOT,
    load_mock_response,
    parse_e3_portfolio_response,
    run_e3_portfolio_with_mock,
)
from apps.portfolio.tests.fixtures.sample_e3_portfolio_context import (
    ALL_FIXTURES,
    PRESET_INTENT_MAP,
)

# ============================================================
# V1~V5 × haiku/sonnet parametrize 10건 (지시서 §2.6)
# ============================================================


# (fixture_id, model_label) 10건 = V1~V5 × {haiku, sonnet}
SERVICE_FLOW_CASES = [
    (fid, model) for fid in ALL_FIXTURES for model in ("haiku", "sonnet")
]


@pytest.mark.parametrize("fixture_id,model_label", SERVICE_FLOW_CASES)
def test_e3_portfolio_service_mock_flow(fixture_id, model_label):
    """V1~V5 × haiku/sonnet 10건 — 서비스 흐름 4단계 PASS.

    1. build_prompt
    2. invoke (mock)
    3. parse
    4. validate (자동 — parse 통과 = validate 통과, schema strict)
    """
    fixture = ALL_FIXTURES[fixture_id]()
    holdings_summary = ", ".join(
        f"{h['ticker']}({h['weight']:.0%})" for h in fixture["holdings"]
    )

    result = run_e3_portfolio_with_mock(
        fixture_id=fixture_id,
        model_label=model_label,
        preset_id=fixture["preset_id"],
        preset_intent=PRESET_INTENT_MAP[fixture["preset_id"]],
        holdings_summary=holdings_summary,
        sector_concentration=fixture["sector_concentration"],
        diversification_score=fixture["diversification_score"],
        risk_concentration_score=fixture["risk_concentration_score"],
        core_metrics_summary=fixture["core_metrics_summary"],
        analysis_context=fixture,
    )

    # Step 1: prompt 빌드 PASS
    assert result["prompt"]
    assert fixture["preset_id"] in result["prompt"]

    # Step 2: raw_response (mock) 로드 PASS
    assert result["raw_response"]
    parsed_json = json.loads(result["raw_response"])
    assert "holistic_assessment" in parsed_json

    # Step 3: parse PASS (E3PortfolioCommentary 6 필드 + Slice 8 #28 action_items)
    parsed = result["parsed"]
    assert set(parsed.keys()) == {
        "holistic_assessment",
        "diversification_comment",
        "sector_balance_comment",
        "risk_concentration_comment",
        "preset_alignment",
        "confidence",
        "action_items",  # Slice 8 Part 2 #28 추가 슬롯 (default [])
    }
    # Slice 8 #28: action_items backward-compat — fixture에 미존재 시 빈 리스트
    assert parsed["action_items"] == []

    # Step 4: validate — preset_alignment fixture expected_alignment 정합
    expected_alignment = fixture["expected_alignment"]
    assert parsed["preset_alignment"] == expected_alignment, (
        f"{fixture_id} × {model_label}: preset_alignment mismatch — "
        f"mock={parsed['preset_alignment']} vs fixture expected={expected_alignment}"
    )

    # confidence 1~5
    assert 1 <= parsed["confidence"] <= 5

    # 메타데이터 유지
    assert result["model_label"] == model_label
    assert result["fixture_id"] == fixture_id


# ============================================================
# 단위 검증 (지시서 §2.6 추가 검증 +3)
# ============================================================


def test_e3_portfolio_service_invalid_mock_raises_validation_error():
    """Schema 위반 mock → ValidationError (parse 단계 차단)."""
    # 6 필드 중 하나 누락
    bad_json = json.dumps(
        {
            "holistic_assessment": "x" * 50,
            "diversification_comment": "분산 점수 0.35는 적당한 수준입니다.",
            "sector_balance_comment": "Tech 50%는 의도된 집중입니다.",
            # risk_concentration_comment 누락
            "preset_alignment": "partial",
            "confidence": 3,
        }
    )
    with pytest.raises(ValidationError):
        parse_e3_portfolio_response(bad_json)

    # min_length 위반
    short_json = json.dumps(
        {
            "holistic_assessment": "짧음",  # 30자 미만
            "diversification_comment": "분산 점수 0.35는 적당한 수준입니다.",
            "sector_balance_comment": "Tech 50%는 의도된 집중입니다.",
            "risk_concentration_comment": "리스크 0.45는 중간 수준입니다.",
            "preset_alignment": "partial",
            "confidence": 3,
        }
    )
    with pytest.raises(ValidationError):
        parse_e3_portfolio_response(short_json)

    # confidence 범위 위반
    bad_conf = json.dumps(
        {
            "holistic_assessment": "x" * 50,
            "diversification_comment": "분산 점수 0.35는 적당한 수준입니다.",
            "sector_balance_comment": "Tech 50%는 의도된 집중입니다.",
            "risk_concentration_comment": "리스크 0.45는 중간 수준입니다.",
            "preset_alignment": "partial",
            "confidence": 6,  # 1~5 위반
        }
    )
    with pytest.raises(ValidationError):
        parse_e3_portfolio_response(bad_conf)


def test_e3_portfolio_service_preset_alignment_enum_strict():
    """preset_alignment Literal Enum 정합 — 5/5 fixture expected와 mock 일치.

    V1=partial / V2=misaligned / V3=partial / V4=aligned / V5=aligned
    (haiku/sonnet 동일 alignment).
    """
    expected_map = {
        "v1_concentrated_balanced": "partial",
        "v2_concentrated_misfit": "misaligned",
        "v3_concentrated_large": "partial",
        "v4_concentrated_value": "aligned",
        "v5_concentrated_dividend": "aligned",
    }
    for fid, expected in expected_map.items():
        for model in ("haiku", "sonnet"):
            raw = load_mock_response(fid, model)
            parsed = parse_e3_portfolio_response(raw)
            assert parsed.preset_alignment.value == expected, (
                f"{fid} × {model}: preset_alignment={parsed.preset_alignment} vs expected={expected}"
            )

    # PresetAlignment Enum 3종만 허용 (Literal 강제)
    invalid_json = json.dumps(
        {
            "holistic_assessment": "x" * 50,
            "diversification_comment": "분산 점수 0.35는 적당한 수준입니다.",
            "sector_balance_comment": "Tech 50%는 의도된 집중입니다.",
            "risk_concentration_comment": "리스크 0.45는 중간 수준입니다.",
            "preset_alignment": "unknown",  # Enum 외 값
            "confidence": 3,
        }
    )
    with pytest.raises(ValidationError):
        parse_e3_portfolio_response(invalid_json)


def test_e3_portfolio_service_cost_guard_integration():
    """CostGuard 통합 — reset_slice 멱등 동작 + mock 비용 카운팅 0."""
    guard = CostGuard.get_instance()
    guard.reset_slice("slice6_step_b_test", max_calls=50)

    # mock 단계에서는 LLM 호출 없음 → call_count 0 유지
    initial_count = guard.call_count
    initial_cost = guard.total_cost_usd

    fixture = ALL_FIXTURES["v1_concentrated_balanced"]()
    holdings_summary = ", ".join(
        f"{h['ticker']}({h['weight']:.0%})" for h in fixture["holdings"]
    )
    result = run_e3_portfolio_with_mock(
        fixture_id="v1_concentrated_balanced",
        model_label="haiku",
        preset_id=fixture["preset_id"],
        preset_intent=PRESET_INTENT_MAP[fixture["preset_id"]],
        holdings_summary=holdings_summary,
        sector_concentration=fixture["sector_concentration"],
        diversification_score=fixture["diversification_score"],
        risk_concentration_score=fixture["risk_concentration_score"],
        core_metrics_summary=fixture["core_metrics_summary"],
        analysis_context=fixture,
    )
    assert result["parsed"]

    # mock 단계 비용 0
    assert guard.call_count == initial_count
    assert guard.total_cost_usd == initial_cost

    # reset 멱등성
    guard.reset_slice("slice6_step_b_test", max_calls=50)
    assert guard.call_count == 0


# ============================================================
# 추가 자연 흡수 — load_mock_response 동작 검증
# ============================================================


def test_load_mock_response_unknown_fixture_raises():
    """미등록 fixture/model → FileNotFoundError / ValueError."""
    with pytest.raises(ValueError, match="Unknown model_label"):
        load_mock_response("v1_concentrated_balanced", "gemini")

    with pytest.raises(ValueError, match="Unknown fixture_id prefix"):
        load_mock_response("v99_nonexistent", "haiku")


def test_mock_fixture_count_is_10():
    """V1~V5 × haiku/sonnet = 정확히 10건."""
    files = sorted(MOCK_FIXTURE_ROOT.glob("*.json"))
    assert len(files) == 10
    expected_names = {
        f"v{i}_{m}.json" for i in range(1, 6) for m in ("haiku", "sonnet")
    }
    assert {f.name for f in files} == expected_names


def test_mock_responses_all_pydantic_valid():
    """10건 mock 모두 E3PortfolioCommentary schema parse PASS (F4 분기 미발동)."""
    for fid in ALL_FIXTURES:
        for model in ("haiku", "sonnet"):
            raw = load_mock_response(fid, model)
            parsed = parse_e3_portfolio_response(raw)
            assert isinstance(parsed, E3PortfolioCommentary)
            assert 1 <= parsed.confidence <= 5
            assert parsed.preset_alignment in (
                PresetAlignment.ALIGNED,
                PresetAlignment.PARTIAL,
                PresetAlignment.MISALIGNED,
            )
