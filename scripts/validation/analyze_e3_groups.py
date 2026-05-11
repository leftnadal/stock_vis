"""Slice 5 Part 2 Step 8 — E3 fixture 그룹별 비교 분석 (hybrid 7 검증).

baseline (garp_baseline 3) vs focused (preset_focused 4)의 모델별 점수 차이 측정.

Slice 4 analyze_e6_groups.py mirror ~95%. 차이:
  - 그룹 키: e5_baseline/e6_focused → garp_baseline/preset_focused (FIXTURE_GROUPS 일관)
  - 자료 #3 mirror — interpretation_guide 4매트릭스 동일

산출:
  docs/portfolio/coach/slice5/step8_2way_e3_group_analysis.json

Usage:
    python -m scripts.validation.analyze_e3_groups
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


SCORED_PATH = Path("docs/portfolio/coach/slice5/step8_2way_e3_scored.json")
OUTPUT_PATH = Path(
    "docs/portfolio/coach/slice5/step8_2way_e3_group_analysis.json"
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
    if not SCORED_PATH.exists():
        print(f"[ERROR] {SCORED_PATH} 없음. 먼저 score_step8.py --entrypoint e3 실행 필요.")
        return 1

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

    # hybrid 검증 (Slice 5 §8.7 mirror)
    hybrid_validation = {
        "context": (
            "baseline 그룹(garp_baseline 3)과 focused 그룹(preset_focused 4)의 "
            "점수 차이로 Slice 5 hybrid 결정 정당화 + 글쓰기 가설 5번째 외삽 검증."
        ),
        "interpretation_guide": {
            "small_diff": "두 그룹 점수 유사 (<10%) → preset 외삽 안전, 글쓰기 가설 일관.",
            "baseline_higher": (
                "GARP fixture가 평가 우수 → 다른 preset에서 글쓰기 품질 약화 "
                "(preset 외삽 위험)."
            ),
            "focused_higher": (
                "focused fixture가 평가 우수 → 다양한 preset이 오히려 더 나은 글쓰기 자극."
            ),
        },
    }

    # 자동 해석
    interpretations: list[str] = []
    for model in comparison:
        if (
            "garp_baseline" in comparison[model]
            and "preset_focused" in comparison[model]
        ):
            b = comparison[model]["garp_baseline"]["score_mean"]
            f = comparison[model]["preset_focused"]["score_mean"]
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
        "step": "step8_e3_group_analysis",
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
    assert loaded["step"] == "step8_e3_group_analysis"

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

    print("\n=== hybrid 7 검증 ===")
    for line in interpretations:
        print(f"  {line}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
