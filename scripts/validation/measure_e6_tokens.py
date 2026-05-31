"""Slice 4 Part 2 Step 7 — E6 prompt 토큰 측정 (오프라인, generation 비용 0).

7개 fixture별 input prompt 토큰 분포 + fixture 그룹 비교 (Q4 hybrid 검증).

Slice 4 Part 1 §2.4 1차 추정값 (1,000 tokens) 검증 + budget 확정.

Usage:
    python -m scripts.validation.measure_e6_tokens
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from apps.portfolio.llm.client import ANTHROPIC_HAIKU_MODEL
from apps.portfolio.schemas.llm import E6Request
from apps.portfolio.services.e6_comparison import build_e6_prompt
from apps.portfolio.tests.fixtures.sample_comparison_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
)

INITIAL_BUDGET = 1500  # E2와 동일 가정 (글쓰기, 1차 추정 1,000~1,500 범위)
PRIOR_ESTIMATE = 1000  # Part 1 §2.4 chars/3 휴리스틱 추정값

OUTPUT_PATH = Path("docs/portfolio/coach/slice4/step7_e6_tokens.json")


def count_tokens_anthropic(text: str) -> int:
    """Anthropic count_tokens API — input 토큰 계산. generation 비용 없음."""
    from anthropic import Anthropic

    client = Anthropic()
    resp = client.messages.count_tokens(
        model=ANTHROPIC_HAIKU_MODEL,
        messages=[{"role": "user", "content": text}],
    )
    return resp.input_tokens


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def main() -> int:
    print("=" * 60)
    print("Slice 4 Step 7 — E6 prompt 토큰 측정 (7 fixtures × anthropic count_tokens)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results: list[dict] = []

    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        payload = {
            "analysis_context": fixture["analysis_context"],
            "adjustments": fixture["adjustments"],
        }
        if fixture.get("user_intent"):
            payload["user_intent"] = fixture["user_intent"]
        request = E6Request.model_validate(payload)
        prompt = build_e6_prompt(request)
        token_count = count_tokens_anthropic(prompt)
        utilization = token_count / INITIAL_BUDGET
        char_estimate = len(prompt) // 3

        result = {
            "fixture": name,
            "fixture_id": fixture["fixture_id"],
            "fixture_group": fixture["fixture_group"],
            "prompt_chars": len(prompt),
            "char_estimate_tokens": char_estimate,
            "actual_input_tokens": token_count,
            "delta_pct_vs_estimate": round(
                (token_count - char_estimate) / char_estimate * 100, 1
            )
            if char_estimate
            else 0,
            "budget": INITIAL_BUDGET,
            "utilization": round(utilization, 4),
            "holdings_count": len(fixture["analysis_context"].get("holdings", [])),
            "adjustments_count": len(fixture["adjustments"]),
        }
        results.append(result)
        print(
            f"  {name:<35} group={fixture['fixture_group']:<13} "
            f"chars={len(prompt):>5}  tokens={token_count:>4}  "
            f"util={utilization:.2%}  Δ={result['delta_pct_vs_estimate']:+.1f}%"
        )

    # 전체 통계
    tokens_all = sorted(r["actual_input_tokens"] for r in results)
    n = len(tokens_all)
    p90_idx = math.ceil(0.9 * n) - 1
    stats_all = {
        "min": tokens_all[0],
        "max": tokens_all[-1],
        "mean": round(sum(tokens_all) / n, 1),
        "p50": tokens_all[n // 2],
        "p90": tokens_all[p90_idx],
    }

    # 그룹별 통계
    group_stats: dict[str, dict] = {}
    for group_name, group_fixtures in FIXTURE_GROUPS.items():
        group_tokens = [
            r["actual_input_tokens"]
            for r in results
            if r["fixture"] in group_fixtures
        ]
        if not group_tokens:
            continue
        group_stats[group_name] = {
            "min": min(group_tokens),
            "max": max(group_tokens),
            "mean": round(sum(group_tokens) / len(group_tokens), 1),
            "fixture_count": len(group_tokens),
        }

    # Budget 결정 — P90 × 1.5 → round-up 500 단위
    p90 = stats_all["p90"]
    p90_x_1_5 = p90 * 1.5
    budget_proposed = int(math.ceil(p90_x_1_5 / 500) * 500)
    max_util = max(r["utilization"] for r in results)

    output = {
        "step": "step7_e6_token_measurement",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "stats_all": stats_all,
        "stats_by_group": group_stats,
        "initial_budget_assumption": INITIAL_BUDGET,
        "budget_decision": {
            "p90": p90,
            "p90_x_1_5": round(p90_x_1_5, 1),
            "round_up_500": budget_proposed,
            "prior_estimate_chars_div_3": PRIOR_ESTIMATE,
            "delta_from_prior_estimate_pct": round(
                (budget_proposed - PRIOR_ESTIMATE) / PRIOR_ESTIMATE * 100, 1
            ),
        },
        "compared_to_existing_budgets": {
            "e1": 5000,
            "e5": 2000,
            "e2": 1500,
            "e6_proposed": budget_proposed,
        },
        "i4_monitoring": {
            "context": "I4 — analysis_summary 200자 truncate 효과",
            "max_utilization_observed": round(max_util, 4),
            "recommendation": (
                "max < 30% → 200자 유지. 30~70% → 모니터링. > 70% → 100자 압축."
            ),
        },
        "group_comparison_note": (
            "baseline (e5_baseline 3) vs focused (e6_focused 4) 토큰 차이 — "
            "fixture 다양성이 비용에 미치는 영향. 큰 차이 없으면 hybrid 결정 정당."
        ),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(output, ensure_ascii=False, indent=2, default=_json_default)
    OUTPUT_PATH.write_text(serialized, encoding="utf-8")
    # Round-trip 검증 (D4)
    loaded = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert loaded["stats_all"]["max"] == stats_all["max"]

    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"  fixtures:           {len(results)}")
    print(f"  token range:        {stats_all['min']} ~ {stats_all['max']}")
    print(f"  mean:               {stats_all['mean']}")
    print(f"  P90:                {stats_all['p90']}")
    print(f"  P90 × 1.5:          {p90_x_1_5:.1f}")
    print(f"  budget (round-up 500): **{budget_proposed}**")
    print(
        f"  prior estimate (chars/3): {PRIOR_ESTIMATE} → "
        f"delta {output['budget_decision']['delta_from_prior_estimate_pct']:+.1f}%"
    )
    print(f"  baseline group mean: {group_stats.get('e5_baseline', {}).get('mean')}")
    print(f"  focused group mean:  {group_stats.get('e6_focused', {}).get('mean')}")
    print(f"  max utilization:     {max_util:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
