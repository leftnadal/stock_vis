"""Slice 3 Part 2 Step 7 — E2 prompt 토큰 측정 (오프라인, generation 비용 0).

7개 fixture별 input prompt 토큰 분포 + fixture 그룹 비교 (Q4 hybrid 검증).

Usage:
    python -m scripts.validation.measure_e2_tokens
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice3", max_calls=50)

from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL
from portfolio.schemas.llm import E2Request
from portfolio.services.e2_diagnostic_card import build_e2_prompt
from portfolio.tests.fixtures.sample_diagnostic_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
)


INITIAL_BUDGET = 5000  # E1과 동일 가정 (글쓰기 작업)

OUTPUT_PATH = Path("docs/portfolio/coach/slice3/step7_e2_token_measurement.json")


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
    print("Step 7 — E2 prompt 토큰 측정 (7 fixtures × anthropic count_tokens)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results: list[dict] = []

    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E2Request(analysis_context=fixture["analysis_context"])
        prompt = build_e2_prompt(request)
        token_count = count_tokens_anthropic(prompt)
        utilization = token_count / INITIAL_BUDGET

        result = {
            "fixture": name,
            "fixture_group": fixture["fixture_group"],
            "prompt_chars": len(prompt),
            "input_tokens": token_count,
            "budget": INITIAL_BUDGET,
            "utilization": round(utilization, 4),
            "holdings_count": len(fixture["analysis_context"].get("holdings", [])),
        }
        results.append(result)
        print(
            f"  {name:<22} group={fixture['fixture_group']:<18} "
            f"chars={len(prompt):>5}  tokens={token_count:>5}  "
            f"util={utilization:.2%}  holdings={result['holdings_count']}"
        )

    # 전체 통계
    tokens_all = sorted(r["input_tokens"] for r in results)
    n = len(tokens_all)
    stats_all = {
        "min": tokens_all[0],
        "max": tokens_all[-1],
        "mean": round(sum(tokens_all) / n, 1),
        "p50": tokens_all[n // 2],
        "p90": tokens_all[int(n * 0.9)],
    }

    # 그룹별 통계
    group_stats: dict[str, dict] = {}
    for group_name, group_fixtures in FIXTURE_GROUPS.items():
        group_tokens = [
            r["input_tokens"] for r in results if r["fixture"] in group_fixtures
        ]
        if not group_tokens:
            continue
        group_stats[group_name] = {
            "min": min(group_tokens),
            "max": max(group_tokens),
            "mean": round(sum(group_tokens) / len(group_tokens), 1),
            "fixture_count": len(group_tokens),
        }

    recommended_budget = int(stats_all["p90"] * 1.5)
    max_util = max(r["utilization"] for r in results)

    output = {
        "step": "step7_e2_token_measurement",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "stats_all": stats_all,
        "stats_by_group": group_stats,
        "initial_budget": INITIAL_BUDGET,
        "recommended_budget": recommended_budget,
        "decision_guide": {
            "if_recommended_lower_than_2500": "E2_TOKEN_BUDGET = 2500. Step 9 #5와 결합.",
            "if_2500_to_4000": "E2 budget = 4000. E1과 분리.",
            "if_higher_than_4000": "E1 budget 5000 유지. prompt 압축 검토.",
        },
        "i4_monitoring": {
            "context": "Slice 2 I4 — analysis_summary 200자 truncate 효과",
            "max_utilization_observed": max_util,
            "recommendation": (
                "max < 30% → 200자 유지. 30~70% → 모니터링. > 70% → 100자 압축."
            ),
        },
        "group_comparison_note": (
            "baseline (garp 3개) vs focused (e2 신규 4개) 토큰 차이 — "
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
    print(f"  token range (all):  {stats_all['min']} ~ {stats_all['max']}")
    print(f"  P90:                {stats_all['p90']}")
    print(f"  recommended budget: {recommended_budget}")
    print(f"  baseline group mean: {group_stats.get('slice1_baseline', {}).get('mean')}")
    print(f"  focused group mean:  {group_stats.get('e2_focused', {}).get('mean')}")
    print(f"  max utilization:     {max_util:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
