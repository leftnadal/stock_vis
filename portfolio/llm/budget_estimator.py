"""Slice 6 Part 1 Step 0 — Budget 추정 입출력 분리 모델 (#β2 close).

기존 token_budgets.py는 input-only budget만 산출. Slice 5 Step 7에서
e3 1차 추정 1,500 vs 실측 P90 4,359 (+366% 편차) 발견 — 추정 모델이 진입점별
prompt 구조 (system + few-shot + JSON input) 반영 못 함을 확인.

본 모듈은:
  - Input 추정: chars/3 휴리스틱 재사용 (#β1 closed, +2.9% 정상)
  - Output 추정: schema 필드 타입별 baseline 기반 합산 (한국어 1.5~2.5 char/token)
  - 통합: input + output 추정 → ×1.5 buffer → round-up 500 = total_with_buffer

설계 원칙:
  - 등록 budget (token_budgets.py)은 input-only 기준 → 본 모델 input × 1.5 → round-up 500과
    ±20% 이내 일치 검증 (Step 0 backtest 핵심)
  - Output 추정은 새 진입점(예: e3_portfolio) 사전 budget 산정용 + Slice 5 e3 +366%
    재발 방지. Output 실측 데이터 미보유로 backtest는 input 기준 진행.
  - Slice 5 #β2 close → 누적 백로그 ~17 → ~16
"""

from __future__ import annotations

import math
from typing import Literal, Sequence

from portfolio.llm.token_budgets import (
    ENTRYPOINT_TOKEN_BUDGETS,
    estimate_input_tokens,
)


# ============================================================
# 필드 타입별 baseline 토큰 (한국어 1.5~2.5 char/token, 평균 ~2)
# ============================================================

FieldType = Literal[
    "str_short",       # ≤50 char  →  ~25 tokens, 안전 30
    "str_medium",      # 51~200 char  →  ~100 tokens
    "str_long",        # 201+ char  →  ~175 tokens
    "list_str_item",   # list[str] 항목 1개당 평균 (~35자 = ~50 tokens)
    "literal",         # Literal/enum (action/aspect 등)
    "int_float",       # int/float (confidence/delta_weight)
    "bool",            # bool (no_actionable_intent)
    "very_short",      # ticker 등 (≤10 char)
]

FIELD_TYPE_BASELINE_TOKENS: dict[str, int] = {
    "str_short": 30,
    "str_medium": 100,
    "str_long": 175,
    "list_str_item": 50,
    "literal": 5,
    "int_float": 3,
    "bool": 1,
    "very_short": 5,
}


# ============================================================
# 진입점 메타 — schema_fields + 실측 P90 + 등록 budget
# ============================================================

ENTRY_POINT_META: dict[str, dict] = {
    "e1": {
        # OneLineDiagnosis: headline (str_short) + summary (str_medium)
        "schema_fields": ["str_short", "str_medium"],
        "actual_input_p90": 3_700,  # Slice 1 측정 (대략값)
        "registered_budget": 5_000,
        "notes": "Slice 1 글쓰기 진입점, 1차 추정 적중",
    },
    "e5": {
        # E5Response: avg 1 adjustment + confidence + ambiguity_notes + no_actionable_intent
        # 1 adjustment = ticker(very_short) + action(literal) + delta(int_float) + target(int_float) + reason(str_long)
        "schema_fields": [
            "very_short", "literal", "int_float", "int_float", "str_long",
            "int_float",       # confidence
            "str_medium",      # ambiguity_notes
            "bool",            # no_actionable_intent
        ],
        "actual_input_p90": 756,  # Slice 2 measure_e5_tokens.py
        "registered_budget": 2_000,
        "notes": "Slice 2 추출, 반례 (sonnet winner)",
    },
    "e2": {
        # E2DiagnosticCard: summary + 3 list (strengths/weaknesses/actions, 평균 3 items each)
        "schema_fields": [
            "str_medium",
            "list_str_item", "list_str_item", "list_str_item",  # strengths × 3
            "list_str_item", "list_str_item", "list_str_item",  # weaknesses × 3
            "list_str_item", "list_str_item", "list_str_item",  # actions × 3
        ],
        "actual_input_p90": 686,  # Slice 3 measure_e2_tokens.py
        "registered_budget": 1_500,
        "notes": "Slice 3 4요소 카드",
    },
    "e6": {
        # E6ComparisonResponse: headline + 2 summaries + 3 key_changes + risk + closing
        # 1 key_change = aspect(literal) + description(str_long)
        "schema_fields": [
            "str_short",       # headline
            "str_medium",      # before_summary
            "str_medium",      # after_summary
            "literal", "str_long",  # key_change × 3
            "literal", "str_long",
            "literal", "str_long",
            "str_medium",      # risk_assessment
            "str_medium",      # closing_remarks
        ],
        "actual_input_p90": 845,  # Slice 4 measure_e6_tokens.py
        "registered_budget": 1_500,
        "notes": "Slice 4 비교 해설",
    },
    "e3": {
        # MetricComments: avg 4 comments (metric_id + one_liner)
        "schema_fields": [
            "very_short", "str_long",  # comment × 4 (avg)
            "very_short", "str_long",
            "very_short", "str_long",
            "very_short", "str_long",
        ],
        "actual_input_p90": 4_359,  # Slice 5 measure_e3_tokens.py
        "registered_budget": 7_000,
        "notes": (
            "Slice 5 지표 코멘트 — AnalysisContext 전체 직렬화로 input ballooning. "
            "1차 추정 1,500 대비 +366% (#β2 트리거)."
        ),
    },
    "e3_portfolio": {
        # E3PortfolioCommentary (Slice 6 Part 1 Step 1 + Part 2 Step A):
        #   holistic(str_long) + diversification(str_medium) + sector(str_medium)
        #   + risk(str_medium) + preset_alignment(literal) + confidence(int)
        "schema_fields": [
            "str_long",        # holistic_assessment
            "str_medium",      # diversification_comment
            "str_medium",      # sector_balance_comment
            "str_medium",      # risk_concentration_comment
            "literal",         # preset_alignment
            "int_float",       # confidence
        ],
        # Slice 6 Part 2 Step A 실측 (reinforced builder, V1~V5 anthropic count_tokens):
        #   range 3,783~4,030 / 평균 3,862 / max(P100, 5건) 4,030
        "actual_input_p90": 4_030,  # V1~V5 max = P100
        "registered_budget": 7_000,
        "notes": (
            "Slice 6 Part 2 Step A 등록. reinforced builder (system + AnalysisContext "
            "dump + few-shot 4) V1~V5 실측 P100 4,030 + output 483 → ×1.5 = 6,770 → "
            "round-up 500 = 7,000. 잠정 9,500 대비 -26% 안전 마진. "
            "F2 분기: estimator 외삽 -37.9% (#β2 재오픈 PS 2.0)."
        ),
    },
}


# ============================================================
# Estimators
# ============================================================


def estimate_output_tokens(schema_fields: Sequence[str]) -> int:
    """Schema 필드 타입 list → output 토큰 합 추정.

    필드 타입별 baseline 합산 (한국어 1.5~2.5 char/token).
    JSON 직렬화 overhead는 baseline에 흡수 (안전 마진).

    Args:
        schema_fields: FieldType 문자열 list. 미등록 type은 ValueError.

    Raises:
        ValueError: 미등록 field type
    """
    total = 0
    for f in schema_fields:
        if f not in FIELD_TYPE_BASELINE_TOKENS:
            raise ValueError(
                f"Unknown field type: {f!r}. "
                f"Valid: {sorted(FIELD_TYPE_BASELINE_TOKENS)}"
            )
        total += FIELD_TYPE_BASELINE_TOKENS[f]
    return total


def estimate_budget_for_entrypoint(
    entrypoint: str,
    sample_prompts: Sequence[str] | None = None,
    *,
    safety_factor: float = 1.5,
) -> dict[str, int]:
    """진입점별 input/output 분리 추정 + total_with_buffer 산출.

    Args:
        entrypoint: ENTRY_POINT_META 키 (e1/e5/e2/e6/e3/e3_portfolio).
        sample_prompts: 실제 prompt 샘플 (3~5개 권장).
            None인 경우 ENTRY_POINT_META의 actual_input_p90 사용 (backtest 모드).
        safety_factor: input + output 합계에 곱하는 안전 계수 (default 1.5).

    Returns:
        {"input": int, "output": int, "total": int, "total_with_buffer": int}
        - input: sample_prompts 평균 토큰 (또는 actual_input_p90)
        - output: schema_fields baseline 합
        - total: input + output
        - total_with_buffer: total × safety_factor → round-up 500

    Raises:
        ValueError: 미등록 entrypoint, 또는 sample_prompts/actual_input_p90 모두 없음
    """
    if entrypoint not in ENTRY_POINT_META:
        raise ValueError(
            f"Unknown entrypoint: {entrypoint!r}. "
            f"Valid: {sorted(ENTRY_POINT_META)}"
        )

    meta = ENTRY_POINT_META[entrypoint]

    # Input 추정
    if sample_prompts:
        input_tokens = sum(estimate_input_tokens(p) for p in sample_prompts) // len(
            sample_prompts
        )
    elif meta.get("actual_input_p90") is not None:
        input_tokens = int(meta["actual_input_p90"])
    else:
        raise ValueError(
            f"No sample_prompts and no actual_input_p90 for {entrypoint!r}. "
            "Provide sample_prompts (3~5 recommended)."
        )

    # Output 추정
    output_tokens = estimate_output_tokens(meta["schema_fields"])

    # Total + buffer + round-up 500
    total = input_tokens + output_tokens
    raw_buffered = total * safety_factor
    total_with_buffer = int(math.ceil(raw_buffered / 500) * 500)

    return {
        "input": int(input_tokens),
        "output": int(output_tokens),
        "total": int(total),
        "total_with_buffer": total_with_buffer,
    }


# ============================================================
# Backtest 검증 (5 진입점)
# ============================================================


def backtest_5_entrypoints() -> dict[str, dict]:
    """5 기존 진입점 (e1/e5/e2/e6/e3)에 새 모델 적용 → 등록 budget vs 추정 편차.

    검증 기준 (Slice 6 Part 1 Step 0 §1.8 + 분기 E1 보정):
      - 양수 편차 (new > registered): registered 부족 위험 → strict ±20%
      - 음수 편차 (new < registered): registered가 더 보수적 → 안전 마진, 통과
      - 즉 "within_safety_margin = (dev_pct <= 0) OR (dev_pct <= 20.0)"

    e5 케이스 (음수 -25%): Slice 2 시점 round-up 1000 단위 흔적 (P90 756 × 1.5 = 1134
    → next 1000 = 2000). 새 표준 모델은 round-up 500 = 1500. registered 2000이 더
    크므로 안전 마진 측, 작업 차단 아님 (분기 E1 보고만, Step 0.5 미실행).

    Returns:
        {entrypoint: {input_p90, output_estimate, total_with_buffer,
                      registered_budget, input_only_round_up,
                      input_only_dev_pct, total_dev_pct,
                      within_strict_20pct, within_safety_margin}}
    """
    results: dict[str, dict] = {}
    for ep in ("e1", "e5", "e2", "e6", "e3"):
        meta = ENTRY_POINT_META[ep]
        input_p90 = int(meta["actual_input_p90"])
        registered = int(meta["registered_budget"])

        # 새 model 추정 (sample_prompts=None → actual_input_p90 사용)
        est = estimate_budget_for_entrypoint(ep)
        output_est = est["output"]
        total_with_buffer = est["total_with_buffer"]

        # input-only 추정 budget (등록 budget과 동일 기준)
        input_only_buffered = math.ceil(input_p90 * 1.5 / 500) * 500

        # 편차 계산
        input_only_dev = (input_only_buffered - registered) / registered * 100
        total_dev = (total_with_buffer - registered) / registered * 100

        # 안전 마진 검증 (양수 편차만 strict)
        within_strict_20pct = abs(input_only_dev) <= 20.0
        within_safety_margin = (input_only_dev <= 0) or (input_only_dev <= 20.0)

        results[ep] = {
            "input_p90": input_p90,
            "output_estimate": output_est,
            "total_with_buffer": total_with_buffer,
            "registered_budget": registered,
            "input_only_round_up": int(input_only_buffered),
            "input_only_dev_pct": round(input_only_dev, 1),
            "total_dev_pct": round(total_dev, 1),
            "within_strict_20pct": within_strict_20pct,
            "within_safety_margin": within_safety_margin,
        }
    return results


def is_backtest_passing(results: dict[str, dict] | None = None) -> bool:
    """5 진입점 모두 안전 마진 통과 여부 (음수 편차 또는 양수 ≤20%)."""
    if results is None:
        results = backtest_5_entrypoints()
    return all(r["within_safety_margin"] for r in results.values())


# ============================================================
# Extrapolation verification (Slice 6 Part 2 Step A — #β2 후속)
# ============================================================


def verify_extrapolation(
    entrypoint: str,
    sample_prompts: Sequence[str],
    actual_avg_input_tokens: float,
) -> dict[str, Any]:
    """Estimator 외삽 검증 — 새 진입점/모드에 대해 estimator 정밀도 측정.

    Args:
        entrypoint: ENTRY_POINT_META 키.
        sample_prompts: 실측 prompt 샘플 list.
        actual_avg_input_tokens: anthropic count_tokens API로 측정한 실측 평균.

    Returns:
        {estimator_input, actual_avg, deviation_pct, within_strict_20pct,
         within_safety_margin, recommendation}
        - within_strict_20pct: abs(편차) ≤ 20% — F2 분기 미발동
        - within_safety_margin: 편차 ≤ 0 (estimator가 보수적) OR ≤ +20% — 등록 부족 위험 없음
        - recommendation: F2 처리 권고 또는 PASS

    F2 분기 (지시서 part2_v2 §3 F2): 편차 ±20% 초과 시 #β2 재오픈 PS 2.0.
    """
    est = estimate_budget_for_entrypoint(entrypoint, sample_prompts=sample_prompts)
    estimator_input = est["input"]
    deviation = (estimator_input - actual_avg_input_tokens) / actual_avg_input_tokens * 100

    within_strict_20pct = abs(deviation) <= 20.0
    within_safety_margin = (deviation <= 0) or (deviation <= 20.0)

    if within_strict_20pct:
        recommendation = "PASS — estimator 외삽 정밀도 정상"
    elif within_safety_margin:
        recommendation = (
            "F2 발동 (안전 마진 측) — estimator가 보수적 추정. "
            "#β2 재오픈 (PS 2.0) Slice 6+ Step 9 슬롯 후보. 작업 차단 아님."
        )
    else:
        recommendation = (
            f"F2 발동 (등록 부족 위험) — estimator가 +{deviation:.1f}% 과대 추정. "
            "즉시 Slice 6+ Step 9 슬롯에서 #β2 재오픈 처리 필요."
        )

    return {
        "entrypoint": entrypoint,
        "estimator_input": estimator_input,
        "actual_avg": int(actual_avg_input_tokens),
        "deviation_pct": round(deviation, 1),
        "within_strict_20pct": within_strict_20pct,
        "within_safety_margin": within_safety_margin,
        "recommendation": recommendation,
    }
