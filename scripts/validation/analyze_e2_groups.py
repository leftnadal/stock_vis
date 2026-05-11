"""Step 8 — fixture 그룹별 비교 분석 (Q4 hybrid 검증).

baseline (garp 3) vs focused (e2 4)의 모델별 점수 차이 측정.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django

init_django()


SCORED_PATH = Path("docs/portfolio/coach/slice3/step8_2way_e2_scored.json")
OUTPUT_PATH = Path(
    "docs/portfolio/coach/slice3/step8_2way_e2_group_analysis.json"
)


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def main() -> int:
    scored = json.loads(SCORED_PATH.read_text(encoding="utf-8"))

    # 모델 × 그룹 집계
    by_model_group: dict[str, dict[str, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in scored["scored_results"]:
        if r.get("error"):
            continue
        group = r.get("fixture_group", "unknown")
        by_model_group[r["label"]][group].append({
            "naturalness": r.get("naturalness") or 0,
            "insight": r.get("insight") or 0,
            "score": r.get("score") or 0,
            "cost_usd": r.get("cost_usd") or 0,
            "latency_ms": r.get("latency_ms") or 0,
        })

    comparison: dict[str, dict] = {}
    for model in by_model_group:
        comparison[model] = {}
        for group in by_model_group[model]:
            items = by_model_group[model][group]
            n = len(items)
            comparison[model][group] = {
                "n": n,
                "naturalness_mean": round(
                    sum(i["naturalness"] for i in items) / n, 4
                ),
                "insight_mean": round(sum(i["insight"] for i in items) / n, 4),
                "score_mean": round(sum(i["score"] for i in items) / n, 4),
                "cost_total_usd": round(sum(i["cost_usd"] for i in items), 4),
                "latency_mean_ms": round(
                    sum(i["latency_ms"] for i in items) / n, 1
                ),
            }

    # Q4 hybrid 검증
    hybrid_validation = {
        "context": "baseline 그룹과 focused 그룹의 점수 차이로 hybrid 결정 정당화.",
        "interpretation_guide": {
            "small_diff": "두 그룹 점수 유사 → hybrid 결정 정당.",
            "baseline_higher": "baseline garp가 친숙 → focused는 도전적.",
            "focused_higher": "focused가 자연스러움 → E2 특화 fixture 효과.",
        },
    }

    # 자동 해석
    interpretations: list[str] = []
    for model in comparison:
        if "slice1_baseline" in comparison[model] and "e2_focused" in comparison[model]:
            b = comparison[model]["slice1_baseline"]["score_mean"]
            f = comparison[model]["e2_focused"]["score_mean"]
            diff_pct = abs(b - f) / b * 100 if b else 0
            if diff_pct < 10:
                verdict = f"small_diff ({diff_pct:.1f}%)"
            elif b > f:
                verdict = f"baseline_higher (+{(b-f)/b*100:.1f}%)"
            else:
                verdict = f"focused_higher (+{(f-b)/b*100:.1f}%)"
            interpretations.append(
                f"{model}: baseline={b:.2f} vs focused={f:.2f} → {verdict}"
            )

    output = {
        "step": "step8_e2_group_analysis",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "comparison": comparison,
        "hybrid_validation": hybrid_validation,
        "interpretations": interpretations,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    # Round-trip 검증 (D4)
    loaded = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert loaded["step"] == "step8_e2_group_analysis"

    print(f"[Saved] {OUTPUT_PATH}")
    for model, groups in comparison.items():
        print(f"\n{model}:")
        for group, stats in groups.items():
            print(
                f"  {group:<20} nat={stats['naturalness_mean']:.2f} "
                f"ins={stats['insight_mean']:.2f} score={stats['score_mean']:.2f} "
                f"cost=${stats['cost_total_usd']:.4f} "
                f"lat_avg={stats['latency_mean_ms']:.0f}ms"
            )

    print("\n=== Q4 hybrid 검증 ===")
    for line in interpretations:
        print(f"  {line}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
