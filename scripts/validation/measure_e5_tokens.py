"""
Slice 2 Part 2 Step 7 — E5 prompt 토큰 측정 (오프라인, generation 비용 0).

7개 fixture별 input prompt 토큰 분포 + budget utilization 측정.
Anthropic count_tokens API는 input 토큰 계산 — generation 호출 아님.

산출:
  docs/portfolio/coach/slice2/step7_e5_token_measurement.json

I4 모니터링 (Part 1 v2):
  analysis_summary 200자 truncate가 토큰에 미치는 효과 측정.

Usage:
    python -m scripts.validation.measure_e5_tokens
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL
from portfolio.schemas.llm import E5Request
from portfolio.services.e5_adjustment_parser import build_e5_prompt
from portfolio.tests.fixtures.sample_adjustment_context import ALL_FIXTURES


# E5 budget 가정 (측정 후 갱신).
# E1 baseline 5,000 (Slice 1 갱신값). E5는 추출 작업이므로 더 작을 것으로 예상.
INITIAL_BUDGET = 5000

OUTPUT_PATH = Path("docs/portfolio/coach/slice2/step7_e5_token_measurement.json")


def count_tokens_anthropic(text: str) -> int:
    """Anthropic count_tokens API — input 토큰 계산. generation 비용 없음."""
    from anthropic import Anthropic

    client = Anthropic()
    resp = client.messages.count_tokens(
        model=ANTHROPIC_HAIKU_MODEL,
        messages=[{"role": "user", "content": text}],
    )
    return resp.input_tokens


def main() -> int:
    print("=" * 60)
    print("Step 7 — E5 prompt 토큰 측정 (7 fixtures × anthropic count_tokens)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results: list[dict] = []

    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E5Request(
            analysis_context=fixture["analysis_context"],
            user_command=fixture["user_command"],
        )
        prompt = build_e5_prompt(request)
        token_count = count_tokens_anthropic(prompt)
        utilization = token_count / INITIAL_BUDGET

        result = {
            "fixture": name,
            "prompt_chars": len(prompt),
            "input_tokens": token_count,
            "budget": INITIAL_BUDGET,
            "utilization": round(utilization, 4),
            "holdings_count": len(fixture["analysis_context"].get("holdings", [])),
            "command_chars": len(fixture["user_command"]),
        }
        results.append(result)
        print(
            f"  {name:<20} chars={result['prompt_chars']:>5}  "
            f"tokens={token_count:>5}  util={utilization:.2%}  "
            f"holdings={result['holdings_count']}"
        )

    # 통계
    tokens = sorted(r["input_tokens"] for r in results)
    n = len(tokens)
    stats = {
        "min": tokens[0],
        "max": tokens[-1],
        "mean": round(sum(tokens) / n, 1),
        "p50": tokens[n // 2],
        "p90": tokens[int(n * 0.9)],
    }

    # budget 권장값 (P90 × 1.5 안전 마진)
    recommended_budget = int(stats["p90"] * 1.5)

    output = {
        "step": "step7_e5_token_measurement",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "stats": stats,
        "initial_budget": INITIAL_BUDGET,
        "recommended_budget": recommended_budget,
        "budget_decision_required": True,
        "decision_guide": {
            "if_recommended_lower_than_initial": "budget 하향. E5 전용 budget 분리 검토.",
            "if_recommended_higher_than_initial": "budget 상향. E1과 통합 budget 검토.",
            "safe_zone": (
                "max utilization 70~85% 권장 (E5는 fixture 다양성 우선이라 50%여도 OK)."
            ),
        },
        "i4_monitoring": {
            "context": "Part 1 v2 I4 — analysis_summary 200자 truncate 효과 측정",
            "recommendation_rule": (
                "max utilization 30% 미만이면 200자→300자 상향 가능. "
                "70% 초과면 200자→100자 압축 검토."
            ),
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"  fixture count:      {len(results)}")
    print(f"  token range:        {stats['min']} ~ {stats['max']}")
    print(f"  P90 tokens:         {stats['p90']}")
    print(f"  recommended budget: {recommended_budget}")
    direction = "<" if recommended_budget < INITIAL_BUDGET else ">"
    print(f"  vs initial:         {recommended_budget} {direction} {INITIAL_BUDGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
