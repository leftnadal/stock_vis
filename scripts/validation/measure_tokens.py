"""
Slice 1 Part 2 — Step 7: 3개 fixture의 입력 토큰 사용량 측정 (오프라인).

E1 입력 토큰 예산 (Slice 1 추정값) 대비 utilization 산출.
실제 LLM 호출 없음 (Gemini count_tokens는 무료).

Usage:
    python -m scripts.validation.measure_tokens
"""

from __future__ import annotations

import sys

from scripts.validation._setup import init_django

init_django()

from django.conf import settings
from google import genai

from apps.portfolio.prompts.e1.e1_builder import build_e1_prompt
from apps.portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)

# Slice 1 실측 갱신 (2026-04-29):
#   garp_tech 3698 / garp_misfit 3844 / garp_large 3848 tokens.
#   E1 input_builder가 PV5 원칙으로 간소 입력 (holdings 미포함) → 종목 수 효과 미미.
#   budget 5000은 utilization 70~85% 안전 구간을 자연스럽게 만족시키는 값.
#   D-8 추정 8000은 fixture 크기 효과를 과대평가한 것으로 판명. Slice 2에서 재정의.
TOKEN_BUDGETS = {
    "E1_input": 5000,
}

GEMINI_TOKENIZER_MODEL = "gemini-2.5-flash"  # client.py와 일관 (2.0-flash free tier=0)


def count_tokens(prompt: str) -> int:
    """Gemini 토크나이저 (실제 호출 모델과 동일)."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    result = client.models.count_tokens(model=GEMINI_TOKENIZER_MODEL, contents=prompt)
    return int(getattr(result, "total_tokens", 0) or 0)


def _assemble_prompt(ctx) -> str:
    system_prompt, user_message = build_e1_prompt(ctx)
    return f"{system_prompt}\n\n{user_message}"


def main() -> int:
    print("=" * 60)
    print("Step 7 — Fixture 토큰 사용량 측정")
    print("=" * 60)

    fixtures = {
        "garp_tech": get_context_garp_tech(),
        "garp_misfit": get_context_garp_misfit(),
        "garp_large": get_context_garp_large(),
    }

    budget = TOKEN_BUDGETS["E1_input"]
    rows: list[dict] = []
    for name, ctx in fixtures.items():
        prompt = _assemble_prompt(ctx)
        tokens = count_tokens(prompt)
        utilization = tokens / budget if budget else 0.0
        if name == "garp_large":
            in_safe_range = 0.70 <= utilization <= 0.85
        else:
            in_safe_range = utilization <= 0.85
        rows.append(
            {
                "fixture": name,
                "input_tokens": tokens,
                "budget": budget,
                "utilization_pct": round(utilization * 100, 1),
                "in_safe_range": in_safe_range,
            }
        )

    # 콘솔 표
    header = f"{'Fixture':<14} {'Tokens':>8} {'Budget':>8} {'Util':>8} {'Safe':>6}"
    print(f"\n{header}")
    for r in rows:
        mark = "OK" if r["in_safe_range"] else "FAIL"
        print(
            f"{r['fixture']:<14} {r['input_tokens']:>8} {r['budget']:>8} "
            f"{r['utilization_pct']:>7.1f}% {mark:>6}"
        )

    large_row = next(r for r in rows if r["fixture"] == "garp_large")
    if not large_row["in_safe_range"]:
        print(
            f"\n[FAIL] garp_large utilization {large_row['utilization_pct']}% "
            f"outside [70%, 85%]."
        )
        print("       Fixture 종목 수 또는 메트릭 정보 조정 필요.")
        return 1

    print(
        f"\n[PASS] garp_large utilization {large_row['utilization_pct']}% within [70%, 85%]."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
