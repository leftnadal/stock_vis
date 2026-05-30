"""Slice 6 Part 1 Step 0 — budget_estimator 단위 테스트.

회귀 테스트 +5 (지시서 §1.7):
  test_estimate_budget_for_entrypoint_basic
  test_estimate_budget_for_entrypoint_5_entrypoints_within_20pct
  test_estimate_budget_for_entrypoint_round_up_500
  test_estimate_budget_for_entrypoint_safety_factor_default
  test_estimate_budget_for_entrypoint_unknown_entrypoint_raises
"""

from __future__ import annotations

import pytest

from portfolio.llm.budget_estimator import (
    ENTRY_INSTRUCTION_BASELINE,
    ENTRY_OVERHEAD,
    ENTRY_POINT_META,
    FIELD_TYPE_BASELINE_TOKENS,
    SECTION_ESTIMATOR_FIT_DATA,
    _estimate_input_section,
    _estimate_instruction_section,
    _estimate_metric_section,
    backtest_5_entrypoints,
    backtest_section_estimator,
    estimate_budget_for_entrypoint,
    estimate_input_tokens_v2,
    estimate_output_tokens,
    is_backtest_passing,
    max_delta_pct,
)

# ============================================================
# 회귀 +5 (지시서 §1.7)
# ============================================================


def test_estimate_budget_for_entrypoint_basic():
    """기본 호출 — e3 진입점, sample_prompts None (actual_input_p90 사용)."""
    result = estimate_budget_for_entrypoint("e3")

    assert isinstance(result, dict)
    assert set(result.keys()) == {"input", "output", "total", "total_with_buffer"}

    # input = e3 actual_input_p90 = 4359
    assert result["input"] == 4_359
    # output = e3 schema_fields baseline 합 (4 comments × (very_short 5 + str_long 175) = 720)
    assert result["output"] == 720
    # total = 4359 + 720 = 5079
    assert result["total"] == 5_079
    # total_with_buffer = 5079 × 1.5 = 7618.5 → round-up 500 = 8000
    assert result["total_with_buffer"] == 8_000


def test_estimate_budget_for_entrypoint_5_entrypoints_within_20pct():
    """5 진입점 backtest — 안전 마진 통과 (음수 편차 또는 양수 ≤20%) 5건 모두 PASS.

    Slice 6 Part 1 Step 0 §1.8 + 분기 E1 보정 적용.
    양수 편차만 strict ±20% (registered 부족 위험만 검증).
    음수 편차는 registered가 더 보수적이므로 안전 마진 측 통과.
    """
    results = backtest_5_entrypoints()
    assert set(results.keys()) == {"e1", "e5", "e2", "e6", "e3"}

    failures = {ep: r for ep, r in results.items() if not r["within_safety_margin"]}
    assert not failures, (
        f"5 진입점 backtest 안전 마진 초과: "
        f"{ {ep: r['input_only_dev_pct'] for ep, r in failures.items()} }"
    )

    # e3 핵심 검증 — 1차 추정 1500 대비 +366% 편차 (#β2)가 새 모델로 ±20% 이내인지
    e3 = results["e3"]
    assert abs(e3["input_only_dev_pct"]) <= 20.0, (
        f"e3 #β2 검증 실패: input-only 편차 {e3['input_only_dev_pct']:+.1f}% > ±20%"
    )

    # 통합 helper 검증
    assert is_backtest_passing(results) is True

    # 분기 E1 발동 케이스 기록 — e5 음수 편차 (안전 마진, Step 0.5 미실행)
    e5 = results["e5"]
    assert e5["input_only_dev_pct"] < 0, (
        f"e5 분기 E1 음수 편차 예상: {e5['input_only_dev_pct']:+.1f}%"
    )
    assert e5["within_safety_margin"] is True
    # strict ±20% 기준으로는 불충족 (분기 E1 발동)
    assert e5["within_strict_20pct"] is False


def test_estimate_budget_for_entrypoint_round_up_500():
    """total_with_buffer는 항상 500 단위 round-up."""
    for ep in ("e1", "e5", "e2", "e6", "e3"):
        result = estimate_budget_for_entrypoint(ep)
        assert result["total_with_buffer"] % 500 == 0, (
            f"{ep}: total_with_buffer {result['total_with_buffer']} not multiple of 500"
        )

    # sample_prompts 명시 케이스도 round-up 500
    sample = "a" * 1500  # 약 500 tokens (chars/3)
    result = estimate_budget_for_entrypoint("e3", sample_prompts=[sample, sample, sample])
    assert result["total_with_buffer"] % 500 == 0


def test_estimate_budget_for_entrypoint_safety_factor_default():
    """safety_factor 기본값 1.5 — total × 1.5 → round-up 500."""
    # 단순한 sample 1개 (input estimate 직접 통제)
    sample = "a" * 300  # estimate_input_tokens = 100

    result_default = estimate_budget_for_entrypoint(
        "e1", sample_prompts=[sample]
    )
    # input=100, output (e1 schema_fields = str_short + str_medium = 30+100=130) = 130
    # total=230, ×1.5=345 → round-up 500 = 500
    assert result_default["input"] == 100
    assert result_default["output"] == 130
    assert result_default["total"] == 230
    assert result_default["total_with_buffer"] == 500

    # safety_factor=2.0 명시 케이스
    result_2x = estimate_budget_for_entrypoint(
        "e1", sample_prompts=[sample], safety_factor=2.0
    )
    # total=230, ×2.0=460 → round-up 500 = 500 (동일)
    # 더 큰 sample로 차이 확인
    big_sample = "a" * 1500  # 500 tokens
    result_default_big = estimate_budget_for_entrypoint(
        "e1", sample_prompts=[big_sample]
    )
    result_2x_big = estimate_budget_for_entrypoint(
        "e1", sample_prompts=[big_sample], safety_factor=2.0
    )
    # input=500, output=130, total=630
    # default: 630 × 1.5 = 945 → 1000
    # 2x: 630 × 2.0 = 1260 → 1500
    assert result_default_big["total_with_buffer"] == 1_000
    assert result_2x_big["total_with_buffer"] == 1_500


def test_estimate_budget_for_entrypoint_unknown_entrypoint_raises():
    """미등록 진입점 ValueError + 미등록 field type ValueError."""
    with pytest.raises(ValueError, match="Unknown entrypoint"):
        estimate_budget_for_entrypoint("e99_nonexistent")

    # estimate_output_tokens도 미등록 type 검증
    with pytest.raises(ValueError, match="Unknown field type"):
        estimate_output_tokens(["str_short", "invalid_type"])

    # 미등록 entrypoint + sample_prompts 모두 None → 명확한 에러
    # (Part 2 Step A 이후 e3_portfolio는 actual_input_p90=4030으로 등록되어
    #  더 이상 "No sample_prompts" 에러 트리거 불가. 임시 진입점 등록 없음 대신
    #  미등록 entrypoint로 동일 에러 경로 검증)
    with pytest.raises(ValueError, match="Unknown entrypoint"):
        estimate_budget_for_entrypoint("e_missing", sample_prompts=None)


# ============================================================
# 추가 헬퍼 검증 (자연 흡수)
# ============================================================


def test_field_type_baseline_tokens_complete():
    """8 field type baseline 모두 등록됨."""
    expected = {
        "str_short", "str_medium", "str_long",
        "list_str_item", "literal", "int_float", "bool", "very_short",
    }
    assert set(FIELD_TYPE_BASELINE_TOKENS.keys()) == expected
    assert all(v > 0 for v in FIELD_TYPE_BASELINE_TOKENS.values())


def test_entry_point_meta_has_5_existing_plus_e3_portfolio():
    """5 기존 + e3_portfolio (Part 2 Step A에서 실측 등록 완료) = 6 entries 모두 값 보유."""
    expected = {"e1", "e5", "e2", "e6", "e3", "e3_portfolio"}
    assert set(ENTRY_POINT_META.keys()) == expected

    # Part 2 Step A 이후: 6 entries 모두 actual_input_p90 + registered_budget 명시
    for ep in expected:
        meta = ENTRY_POINT_META[ep]
        assert meta["actual_input_p90"] is not None, f"{ep}: actual_input_p90 미등록"
        assert meta["registered_budget"] is not None, f"{ep}: registered_budget 미등록"
        assert meta["schema_fields"]

    # e3_portfolio 실측 등록값 검증 (Part 2 Step A)
    e3p = ENTRY_POINT_META["e3_portfolio"]
    assert e3p["actual_input_p90"] == 4_030  # V1~V5 max (5건)
    assert e3p["registered_budget"] == 7_000  # P100 + output 483 → ×1.5 → round-up 500


# ============================================================
# Slice 8 Part 1 Step 0-2 #β2 — 섹션 합산 estimator (3건)
# ============================================================


def test_estimator_section_decomposition():
    """세 섹션 함수가 각각 양수 반환 + 진입점별 instruction baseline 정합."""
    fixture = {
        "holdings": [{} for _ in range(5)],
        "portfolio_metrics": {f"m{i}": 0 for i in range(7)},
        "conversation_history": [{} for _ in range(2)],
        "time_series_metrics": ["pe", "peg", "roic"],
    }
    # input section: 5*35 + 3*30 + 2*200 = 175 + 90 + 400 = 665
    assert _estimate_input_section(fixture) == 665
    # metric section: 7 * 15 = 105
    assert _estimate_metric_section(fixture) == 105
    # instruction section: e4_conversation_tier1 → e4_conversation baseline 2700
    assert _estimate_instruction_section("e4_conversation_tier1") == 2_700
    assert _estimate_instruction_section("e4_conversation_tier3") == 2_700
    # e3는 baseline 1200
    assert _estimate_instruction_section("e3") == 1_200
    # 미등록 entry는 1000 default
    assert _estimate_instruction_section("e99_unknown") == 1_000

    # 모든 baseline + overhead 양수
    for entry, val in ENTRY_INSTRUCTION_BASELINE.items():
        assert val > 0, f"{entry}: instruction baseline 양수 위반"
    for entry, val in ENTRY_OVERHEAD.items():
        assert val > 0, f"{entry}: overhead 양수 위반"


def test_estimator_fit_max_delta_within_30pct():
    """5+ 슬라이스 fit data에 대해 max delta ≤ 30% (Slice 8 #β2 KPI)."""
    results = backtest_section_estimator()
    # 9건 fit data 모두 entry 등록 확인
    assert set(results.keys()) == {entry for entry, _, _ in SECTION_ESTIMATOR_FIT_DATA}

    # KPI: max |delta| ≤ 30%
    max_delta = max_delta_pct(results)
    assert max_delta <= 30.0, f"max delta {max_delta:.2f}% > 30% — #β2 KPI FAIL"

    # 모든 entry 30% 이내
    for entry, r in results.items():
        assert r["within_30pct"], (
            f"{entry}: delta {r['delta_pct']:+.2f}% 초과 (estimated {r['estimated']} vs actual {r['actual']})"
        )

    # 핵심: S5 e3 +290.6% bias 해소 검증
    assert abs(results["e3"]["delta_pct"]) <= 30.0
    # 핵심: S7 e4 -97% bias 해소 검증
    for tier in (1, 2, 3):
        assert abs(results[f"e4_conversation_tier{tier}"]["delta_pct"]) <= 30.0


def test_estimator_monotonic_in_input_size():
    """fixture input 크기 증가 시 추정값 단조증가 (sanity check)."""
    base = {"portfolio_metrics": {"m1": 0}}

    # holdings 증가
    h1 = estimate_input_tokens_v2("e4_conversation_tier1", {**base, "holdings": [{}]})
    h5 = estimate_input_tokens_v2("e4_conversation_tier1", {**base, "holdings": [{} for _ in range(5)]})
    h10 = estimate_input_tokens_v2("e4_conversation_tier1", {**base, "holdings": [{} for _ in range(10)]})
    assert h1 < h5 < h10

    # metrics 증가
    m1 = estimate_input_tokens_v2("e3", {"portfolio_metrics": {"m1": 0}})
    m5 = estimate_input_tokens_v2("e3", {"portfolio_metrics": {f"m{i}": 0 for i in range(5)}})
    m10 = estimate_input_tokens_v2("e3", {"portfolio_metrics": {f"m{i}": 0 for i in range(10)}})
    assert m1 < m5 < m10

    # history 증가
    base_e4 = {"holdings": [{} for _ in range(5)], "portfolio_metrics": {"m1": 0}}
    hist0 = estimate_input_tokens_v2("e4_conversation_tier1", {**base_e4, "conversation_history": []})
    hist1 = estimate_input_tokens_v2("e4_conversation_tier1", {**base_e4, "conversation_history": [{}]})
    hist5 = estimate_input_tokens_v2("e4_conversation_tier1", {**base_e4, "conversation_history": [{} for _ in range(5)]})
    assert hist0 < hist1 < hist5

    # tier overhead (history만 다르지 entry overhead도 다름) 양수
    tier1_h0 = estimate_input_tokens_v2("e4_conversation_tier1", base_e4)
    tier3_h0 = estimate_input_tokens_v2("e4_conversation_tier3", base_e4)
    assert tier1_h0 < tier3_h0  # tier3가 overhead 더 큼
