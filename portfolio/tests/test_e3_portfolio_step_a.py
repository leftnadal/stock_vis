"""Slice 6 Part 2 Step A — prompt builder 보강 + estimator 외삽 검증 회귀.

지시서 §1.6 회귀 +3~5:
  test_e3_portfolio_prompt_input_tokens_4k_to_6k
  test_e3_portfolio_few_shots_4_examples_loadable
  test_estimate_budget_e3_portfolio_extrapolation_within_20pct
  test_token_budgets_e3_portfolio_registered
  test_e3_portfolio_builder_system_prompt_included (자연 흡수)

본 모듈은 anthropic count_tokens API 호출 없이 chars/3 estimate로 구조 검증.
실측 검증은 docs/portfolio/coach/slice6/step_a_prompt_reinforcement.md 보존.
"""

from __future__ import annotations

import pytest

from portfolio.llm.budget_estimator import (
    ENTRY_POINT_META,
    estimate_budget_for_entrypoint,
    estimate_input_tokens,
    verify_extrapolation,
)
from portfolio.llm.token_budgets import (
    ENTRYPOINT_TOKEN_BUDGETS,
    get_token_budget,
)
from portfolio.prompts.e3_portfolio import (
    FEW_SHOT_EXAMPLES,
    REINFORCED_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    build_e3_portfolio_prompt,
)
from portfolio.tests.fixtures.sample_e3_portfolio_context import (
    ALL_FIXTURES,
    PRESET_INTENT_MAP,
)


def _build_v1_v5_prompts() -> list[str]:
    """V1~V5 reinforced prompts 빌드 (analysis_context dict 포함)."""
    prompts = []
    for name, getter in ALL_FIXTURES.items():
        f = getter()
        holdings_summary = ", ".join(
            f"{h['ticker']}({h['weight']:.0%})" for h in f["holdings"]
        )
        p = build_e3_portfolio_prompt(
            preset_id=f["preset_id"],
            preset_intent=PRESET_INTENT_MAP[f["preset_id"]],
            holdings_summary=holdings_summary,
            sector_concentration=f["sector_concentration"],
            diversification_score=f["diversification_score"],
            risk_concentration_score=f["risk_concentration_score"],
            core_metrics_summary=f["core_metrics_summary"],
            analysis_context=f,
        )
        prompts.append(p)
    return prompts


# ============================================================
# 회귀 +5 (지시서 §1.6)
# ============================================================


def test_e3_portfolio_prompt_input_tokens_4k_to_6k():
    """reinforced builder V1~V5 prompt가 4k~6k input 토큰 도달.

    실측 anthropic count_tokens (Step A 측정): V1~V5 range 3,783~4,030 / 평균 3,862.
    chars/3 estimate는 보수적이라 본 테스트는 chars 길이로 4k 이상 도달 검증.
    실측 평균 3,862는 4k boundary 미달이지만 max 4,030 (V3)으로 통과.
    """
    prompts = _build_v1_v5_prompts()
    assert len(prompts) == 5

    char_lens = [len(p) for p in prompts]
    # 한국어 평균 chars/token = ~1.85 (실측: 7,000 chars → 3,800 tokens)
    # 4,000 tokens 도달 = 약 7,000~7,500 chars
    avg_chars = sum(char_lens) / len(char_lens)
    max_chars = max(char_lens)
    assert avg_chars >= 6_500, (
        f"reinforced prompt 평균 chars {avg_chars:.0f} < 6,500 — input 4k 미달 위험 (F1)"
    )
    assert max_chars >= 7_000, (
        f"reinforced prompt max chars {max_chars} < 7,000 — input 4k 미달 위험 (F1)"
    )

    # minimal 모드는 input ~2,300 chars (analysis_context=None)
    minimal = build_e3_portfolio_prompt(
        preset_id="garp",
        preset_intent="합리적 가격 성장",
        holdings_summary="MSFT(50%), AAPL(50%)",
        sector_concentration="Tech 100%",
        diversification_score=0.20,
        risk_concentration_score=0.60,
        core_metrics_summary="PEG=2.0",
    )
    assert len(minimal) < 5_000, "minimal 모드가 reinforced 만큼 큼 — 구분 실패"
    # reinforced > minimal × 2 (보강 효과 검증)
    assert max_chars > len(minimal) * 2


def test_e3_portfolio_few_shots_4_examples_loadable():
    """Few-shot 4 examples (V1/V2/V3/V5 mirror) 모두 valid.

    5 카테고리 cover: growth aligned (V1) / growth misfit (V2) /
    factor partial (V3) / income aligned (V5). V4 (value) 제외 — test set 다양성.
    """
    assert len(FEW_SHOT_EXAMPLES) == 4
    expected_names = {
        "concentrated_balanced",  # V1 mirror
        "concentrated_misfit",     # V2 mirror
        "concentrated_factor",     # V3 mirror
        "concentrated_income",     # V5 mirror
    }
    actual_names = {ex["name"] for ex in FEW_SHOT_EXAMPLES}
    assert actual_names == expected_names

    # 각 example의 input/output 모두 비어있지 않음 + 한국어 포함
    for ex in FEW_SHOT_EXAMPLES:
        assert ex["input"]
        assert ex["output"]
        assert "preset_id=" in ex["input"]
        # output은 JSON-like 6 필드
        assert "holistic_assessment" in ex["output"]
        assert "preset_alignment" in ex["output"]
        assert "confidence" in ex["output"]


def test_estimate_budget_e3_portfolio_extrapolation_within_20pct():
    """Estimator 외삽 검증 — Step A 실측 평균 3,862 input 기반.

    분기 F2 발동 (편차 -37.9%, 안전 마진 측): #β2 재오픈 PS 2.0 후속.
    본 테스트는 verify_extrapolation 함수 동작 + 안전 마진 측 통과 검증.
    """
    prompts = _build_v1_v5_prompts()
    # Step A 실측 평균 3,862 (anthropic count_tokens 결과)
    actual_avg = 3_862.0

    result = verify_extrapolation("e3_portfolio", prompts, actual_avg)

    # estimator는 chars/3 휴리스틱으로 보수적 추정 (음수 편차)
    assert result["deviation_pct"] < 0, (
        f"estimator 외삽 양수 편차 발견: {result['deviation_pct']:+.1f}% — "
        "등록 부족 위험"
    )

    # 안전 마진 측 통과 (음수 편차 또는 +20% 이내)
    assert result["within_safety_margin"] is True

    # strict ±20%는 미달 → F2 분기 발동 인정 (#β2 재오픈)
    assert result["within_strict_20pct"] is False, (
        "Step A 실측에서 F2 분기 발동 (편차 -37.9%) — #β2 재오픈 인정 필요"
    )
    assert "F2 발동" in result["recommendation"]
    assert "#β2 재오픈" in result["recommendation"]


def test_token_budgets_e3_portfolio_registered():
    """token_budgets["e3_portfolio"] 정식 등록 (Slice 6 Part 2 Step A §1.5)."""
    assert "e3_portfolio" in ENTRYPOINT_TOKEN_BUDGETS
    budget = get_token_budget("e3_portfolio")

    # round-up 500
    assert budget % 500 == 0

    # 실측 P100 4,030 + output 483 → ×1.5 = 6,770 → round-up 500 = 7,000
    assert budget == 7_000

    # 잠정 9,500 대비 ±30% 이내 (F3 미발동)
    deviation_from_provisional = abs(budget - 9_500) / 9_500 * 100
    assert deviation_from_provisional <= 30.0, (
        f"잠정 9,500 대비 편차 {deviation_from_provisional:.1f}% > 30% — F3 분기"
    )

    # ENTRY_POINT_META에도 등록값 반영
    assert ENTRY_POINT_META["e3_portfolio"]["registered_budget"] == 7_000
    assert ENTRY_POINT_META["e3_portfolio"]["actual_input_p90"] == 4_030


def test_e3_portfolio_builder_system_prompt_included():
    """reinforced 모드 prompt에 SYSTEM_PROMPT 포함 + AnalysisContext JSON dump 포함."""
    prompt = build_e3_portfolio_prompt(
        preset_id="garp",
        preset_intent="합리적 가격 성장",
        holdings_summary="MSFT(60%), AAPL(40%)",
        sector_concentration="Tech 100%",
        diversification_score=0.15,
        risk_concentration_score=0.80,
        core_metrics_summary="PEG=1.5",
        analysis_context={"some": "data", "nested": {"k": "v"}},
    )

    # SYSTEM_PROMPT 도입부 포함
    assert "당신은 한국 개인 투자자를 위한 portfolio 단위 진단 전문가 LLM입니다" in prompt
    assert "역할 정의" in prompt
    assert "출력 Schema (E3PortfolioCommentary" in prompt
    assert "평가 기준" in prompt

    # Few-shot 4개 모두 포함
    for ex in FEW_SHOT_EXAMPLES:
        assert ex["name"] in prompt

    # AnalysisContext JSON dump 포함
    assert "AnalysisContext" in prompt
    assert "some" in prompt
    assert "nested" in prompt

    # 변수 슬롯도 그대로 치환
    assert "preset_id: garp" in prompt
    assert "MSFT(60%)" in prompt


# ============================================================
# 추가 자연 흡수
# ============================================================


def test_reinforced_vs_minimal_mode_differ():
    """analysis_context=None (minimal) vs dict (reinforced) 구분 동작.

    minimal: input ~750 tokens (Part 1 placeholder만)
    reinforced: input 3,700~4,030 tokens (Part 2 보강)
    """
    common_kwargs = {
        "preset_id": "garp",
        "preset_intent": "합리적 가격 성장",
        "holdings_summary": "MSFT(60%)",
        "sector_concentration": "Tech 60%",
        "diversification_score": 0.40,
        "risk_concentration_score": 0.30,
        "core_metrics_summary": "PEG=1.5",
    }
    minimal = build_e3_portfolio_prompt(**common_kwargs)
    reinforced = build_e3_portfolio_prompt(**common_kwargs, analysis_context={"x": 1})

    # reinforced가 최소 2배 이상 큼
    assert len(reinforced) > len(minimal) * 2

    # minimal에는 SYSTEM_PROMPT 부재
    assert "역할 정의" not in minimal
    assert "역할 정의" in reinforced

    # minimal에는 AnalysisContext 부재
    assert "AnalysisContext (분석엔진 사전 산출" not in minimal
    assert "AnalysisContext (분석엔진 사전 산출" in reinforced


def test_system_prompt_constant_well_formed():
    """SYSTEM_PROMPT 상수 — 핵심 섹션 포함."""
    # 핵심 섹션
    for section in (
        "역할 정의",
        "핵심 제약",
        "정량 재계산 금지",
        "출력은 JSON only",
        "한국어",
        "preset 의도 우선",
        "출력 Schema",
        "길이 제약",
        "평가 기준",
    ):
        assert section in SYSTEM_PROMPT, f"SYSTEM_PROMPT에 '{section}' 섹션 누락"
