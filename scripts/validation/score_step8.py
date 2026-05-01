"""
Slice 1 Part 2 — Step 8 점수 산출 (Slice 2 Step 9에서 entrypoint 일반화).

산식 (entrypoint별):
  e1 (Slice 1, 글쓰기 차원):
    1차 필터:  schema_pass=True AND naturalness>=3 AND insight>=3
    2차 efficiency:  sqrt(naturalness * insight) / sqrt(cost_usd * latency_s)
    Fallback: 0.25/0.25/0.25/0.15/0.10 (schema/n/i/cost_inv/lat_inv) — 동적 normalize
  e5 (Slice 2, 추출 차원):
    1차 필터:  schema_pass=True AND intent>=3 AND no_extra>=3
              AND cost<=$0.020 AND latency<=5000ms
    2차 efficiency:  sqrt(intent_match * no_extra_changes) — cost/lat은 임계로 분리
    Fallback: 동일 가중, 정적 normalize (THRESHOLDS 기반)
    → score_step8_e5.py로 위임 (Slice 3 진입 시 통합 가능)

Usage:
    python -m scripts.validation.score_step8                  # default e1 (Slice 1)
    python -m scripts.validation.score_step8 --entrypoint e5  # Slice 2 (delegate)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


# Slice 2 Step 9 일반화 — entrypoint별 메타데이터 단일 출처.
# 새 entrypoint 추가 시 (예: e2 진단 카드) 여기 한 곳만 갱신.
DIMENSION_LOOKUP = {
    "e1": {
        "dim1": {"key": "naturalness", "manual_field": "naturalness"},
        "dim2": {"key": "insight", "manual_field": "insight"},
        "model_label_field": "label",
        "result_structure": "flat",  # naturalness/insight 등이 result 최상위
        "default_raw": "docs/portfolio/coach/slice1/step8_3way_raw.json",
        "default_scored": "docs/portfolio/coach/slice1/step8_3way_scored.json",
        "weight": 0.5,
    },
    "e5": {
        "dim1": {"key": "intent_match", "manual_field": "intent_match_manual"},
        "dim2": {"key": "no_extra_changes", "manual_field": "no_extra_changes_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리
        "default_raw": "docs/portfolio/coach/slice2/step8_2way_e5_raw.json",
        "default_scored": "docs/portfolio/coach/slice2/step8_2way_e5_scored.json",
        "weight": 0.5,
        "delegated_to": "scripts.validation.score_step8_e5",
    },
}


RAW_PATH = Path(DIMENSION_LOOKUP["e1"]["default_raw"])
SCORED_PATH = Path(DIMENSION_LOOKUP["e1"]["default_scored"])


def lexicographic_filter(r: dict) -> bool:
    return (
        r.get("schema_pass") is True
        and isinstance(r.get("naturalness"), (int, float))
        and r["naturalness"] >= 3
        and isinstance(r.get("insight"), (int, float))
        and r["insight"] >= 3
    )


def efficiency_score(r: dict) -> float:
    n = r["naturalness"]
    i = r["insight"]
    c = max(r.get("cost_usd") or 1e-6, 1e-6)
    lat_s = max((r.get("latency_ms") or 1) / 1000.0, 1e-6)
    return math.sqrt(n * i) / math.sqrt(c * lat_s)


def fallback_score(r: dict, all_results: list[dict]) -> float:
    schema = 1.0 if r.get("schema_pass") else 0.0
    n_norm = (r.get("naturalness") or 0) / 5.0
    i_norm = (r.get("insight") or 0) / 5.0

    costs = [x["cost_usd"] for x in all_results if x.get("cost_usd") is not None]
    latencies = [x["latency_ms"] for x in all_results if x.get("latency_ms") is not None]
    if not costs or not latencies:
        return 0.0
    max_c, min_c = max(costs), min(costs)
    max_l, min_l = max(latencies), min(latencies)
    cost_v = r.get("cost_usd")
    lat_v = r.get("latency_ms")
    if cost_v is None or lat_v is None:
        return 0.0
    cost_inv = (max_c - cost_v) / (max_c - min_c) if max_c > min_c else 1.0
    lat_inv = (max_l - lat_v) / (max_l - min_l) if max_l > min_l else 1.0
    return (
        0.25 * schema
        + 0.25 * n_norm
        + 0.25 * i_norm
        + 0.15 * cost_inv
        + 0.10 * lat_inv
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entrypoint",
        choices=list(DIMENSION_LOOKUP),
        default="e1",
        help="평가 진입점 (default: e1 — Slice 1 호환). e5는 score_step8_e5에 위임.",
    )
    args = parser.parse_args()

    # e5 → score_step8_e5에 delegation (산식 차이로 인해 별도 모듈 유지)
    if args.entrypoint == "e5":
        from scripts.validation import score_step8_e5
        return score_step8_e5.main()

    # e1 (default) — Slice 1 산식
    config = DIMENSION_LOOKUP["e1"]
    raw_path = Path(config["default_raw"])
    scored_path = Path(config["default_scored"])

    if not raw_path.exists():
        print(f"[ERROR] {raw_path} 없음. run_step8_3way 먼저 실행.")
        return 1

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    results = raw["results"]

    # 수동 평가 누락 검증
    missing = [
        f"{r.get('label')}×{r.get('fixture')}"
        for r in results
        if not r.get("error")
        and (r.get("naturalness") is None or r.get("insight") is None)
    ]
    if missing:
        print(f"[ERROR] 다음 entry 수동 평가 미완료: {missing}")
        return 1

    passed = [r for r in results if lexicographic_filter(r)]
    use_fallback = len(passed) == 0

    print("=" * 60)
    print("Step 8 Scoring Result")
    print("=" * 60)
    print(f"\n1차 필터 통과: {len(passed)} / {len(results)}")
    print(f"Mode: {'FALLBACK' if use_fallback else 'EFFICIENCY'}")

    scored: list[dict] = []
    for r in results:
        if use_fallback:
            score = fallback_score(r, results)
            score_type = "fallback"
        elif lexicographic_filter(r):
            score = efficiency_score(r)
            score_type = "efficiency"
        else:
            score = None
            score_type = "filtered_out"
        scored.append({**r, "score": score, "score_type": score_type})

    # Per label (gemini/sonnet/haiku) 평균
    label_scores: dict[str, list[float]] = defaultdict(list)
    for r in scored:
        if r["score"] is not None:
            label_scores[r.get("label") or r.get("provider", "?")].append(r["score"])
    label_means: dict[str, float] = {
        label: sum(v) / len(v) for label, v in label_scores.items() if v
    }

    # 콘솔 표
    print("\n=== Per Call ===")
    print(
        f"{'Fixture':<14} {'Label':<8} {'Schema':>6} {'Nat':>4} {'Ins':>4} "
        f"{'Cost':>9} {'Lat(s)':>7} {'Score':>10} {'Type':<14}"
    )
    for r in scored:
        score_str = f"{r['score']:.2f}" if r["score"] is not None else "-"
        sch = "OK" if r.get("schema_pass") else "FAIL"
        cost = r.get("cost_usd") or 0
        lat_s = (r.get("latency_ms") or 0) / 1000
        nat = r.get("naturalness") if r.get("naturalness") is not None else "-"
        ins = r.get("insight") if r.get("insight") is not None else "-"
        print(
            f"{r.get('fixture',''):<14} {r.get('label',''):<8} "
            f"{sch:>6} {nat!s:>4} {ins!s:>4} "
            f"${cost:>7.5f} {lat_s:>7.2f} {score_str:>10} {r['score_type']:<14}"
        )

    print("\n=== Per Label (mean score) ===")
    winner = None
    for label, m in sorted(label_means.items(), key=lambda x: -x[1]):
        print(f"  {label:<8}: {m:.4f}  (n={len(label_scores[label])})")
    if label_means:
        winner = max(label_means.items(), key=lambda x: x[1])[0]
        print(f"\n[WINNER] {winner}")

    scored_path.write_text(
        json.dumps(
            {
                "scored_results": scored,
                "label_means": label_means,
                "use_fallback": use_fallback,
                "winner": winner,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n[Saved] {scored_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
