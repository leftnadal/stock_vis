"""Slice 5 Part 2 Step 7 — E3 prompt 토큰 측정 (오프라인, generation 비용 0).

Hybrid 7 fixture 토큰 분포 + group 비교 (baseline GARP 3 + focused 4).

Slice 4 measure_e6_tokens.py mirror ~95% (지시서 §7.2).
차이:
  - fixture set: ALL_FIXTURES (E3 hybrid 7) → baseline + focused 그룹
  - request: E6Request → E3Request (analysis_context only)
  - prompt builder: build_e6_prompt → build_e3_prompt (service wrapper, AnalysisContext 입력)
  - INITIAL_BUDGET: 1500 (Q3, Part 1 §4.2.4 1차 추정)

#β1 자연 검증 절차 (지시서 §7.3):
  - 모든 fixture delta_pct 평균 ±20% 이내 → 휴리스틱 정상, #β1 closed
  - 평균 +30% 이상 → chars/3 → chars/2.5 보정
  - 평균 +50% 이상 → chars/3 → chars/2.6 보정 (Slice 4 e6 P90/measured 비율 인용)

Usage:
    python -m scripts.validation.measure_e3_tokens
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
from apps.portfolio.schemas import AnalysisContext
from apps.portfolio.schemas.llm import E3Request
from apps.portfolio.services.e3_metric_comment import build_e3_prompt
from apps.portfolio.tests.fixtures.sample_metric_comment_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
)

INITIAL_BUDGET = 1500  # Q3, Part 1 §4.2.4 1차 추정 (E2와 동일 가정 — 글쓰기 + multi metric)
PRIOR_ESTIMATE = 1000  # Part 1 chars/3 휴리스틱 baseline (E6 mirror)

OUTPUT_PATH = Path("docs/portfolio/coach/slice5/step7_e3_tokens.json")


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
    print("Slice 5 Step 7 — E3 prompt 토큰 측정 (7 fixtures × anthropic count_tokens)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results: list[dict] = []

    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E3Request(analysis_context=fixture["analysis_context"])
        context = AnalysisContext.model_validate(request.analysis_context)
        prompt = build_e3_prompt(context)
        token_count = count_tokens_anthropic(prompt)
        utilization = token_count / INITIAL_BUDGET
        char_estimate = len(prompt) // 3

        result = {
            "fixture": name,
            "fixture_id": fixture["fixture_id"],
            "fixture_group": fixture["fixture_group"],
            "preset_id": fixture["preset_id"],
            "preset_category": fixture["preset_category"],
            "prompt_chars": len(prompt),
            "char_estimate_tokens": char_estimate,
            "actual_input_tokens": token_count,
            "delta_pct_vs_estimate": round(
                (char_estimate - token_count) / token_count * 100, 1
            )
            if token_count
            else 0,  # estimate 가 actual 대비 +/-% (#β1 자연 검증)
            "budget": INITIAL_BUDGET,
            "utilization": round(utilization, 4),
            "holdings_count": len(
                fixture["analysis_context"]
                .get("analysis_target_portfolio", {})
                .get("holdings", [])
            ),
        }
        results.append(result)
        print(
            f"  {name:<35} group={fixture['fixture_group']:<15} "
            f"chars={len(prompt):>5}  tokens={token_count:>4}  "
            f"util={utilization:.2%}  Δest={result['delta_pct_vs_estimate']:+.1f}%"
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

    # #β1 자연 검증 — 평균 delta_pct
    delta_pcts = [r["delta_pct_vs_estimate"] for r in results]
    delta_mean = round(sum(delta_pcts) / len(delta_pcts), 1)
    if abs(delta_mean) <= 20:
        beta1_decision = "closed_no_correction"
        beta1_recommendation = "휴리스틱 정상 (chars/3) — 보정 불필요"
    elif delta_mean >= 50:
        beta1_decision = "correct_to_chars_div_2_6"
        beta1_recommendation = "chars/3 → chars/2.6 (Slice 4 e6 P90/measured 비율 인용)"
    elif delta_mean >= 30:
        beta1_decision = "correct_to_chars_div_2_5"
        beta1_recommendation = "chars/3 → chars/2.5 보정"
    else:
        beta1_decision = "monitor"
        beta1_recommendation = "20~30% 편차 — 모니터링, 추가 슬라이스 자료 누적 시 재평가"

    output = {
        "step": "step7_e3_token_measurement",
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
            "decision_rule_recommendation": (
                f"P90={p90} × 1.5 = {p90_x_1_5:.0f} → round-up 500 = {budget_proposed}"
            ),
        },
        "compared_to_existing_budgets": {
            "e1": 5000,
            "e5": 2000,
            "e2": 1500,
            "e6": 1500,
            "e3_proposed": budget_proposed,
        },
        "beta1_natural_verification": {
            "context": "#β1 — chars/3 휴리스틱 vs anthropic count_tokens 실측 delta_pct (Slice 4 Step 7 +50% 편차 교훈)",
            "fixture_delta_pcts": delta_pcts,
            "mean_delta_pct": delta_mean,
            "decision": beta1_decision,
            "recommendation": beta1_recommendation,
        },
        "max_utilization_observed": round(max_util, 4),
        "group_comparison_note": (
            "baseline (garp_baseline 3) vs focused (preset_focused 4) 토큰 차이 — "
            "Slice 5 hybrid 7 결정 정당성. 차이 작으면 preset 다양성 비용 영향 미미."
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
    print(
        f"  baseline group mean: "
        f"{group_stats.get('garp_baseline', {}).get('mean')}"
    )
    print(
        f"  focused group mean:  "
        f"{group_stats.get('preset_focused', {}).get('mean')}"
    )
    print(f"  max utilization:     {max_util:.2%}")
    print(f"\n  #β1 mean delta_pct:  {delta_mean:+.1f}%  → {beta1_decision}")
    print(f"  #β1 recommendation:  {beta1_recommendation}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
