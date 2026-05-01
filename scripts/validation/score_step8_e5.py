"""
Slice 2 Part 2 Step 8 — E5 회고 점수 산출 (Q5.C — 신설 후 Step 9 일반화).

Slice 1 score_step8.py 패턴 mirror, 차원만 변경:
  naturalness/insight → intent_match/no_extra_changes

산식 (N2.B 동등 가중):
  - Lexicographic 1차 필터: schema=True ∧ intent_match≥3 ∧ no_extra_changes≥3
                            ∧ cost ≤ $0.020 ∧ latency ≤ 5000ms
  - Efficiency: sqrt(intent_match × no_extra_changes)  (Slice 1 sqrt(× 곱) mirror)
  - Fallback weights: schema/intent_match/no_extra/cost/lat = 0.25/0.25/0.25/0.15/0.10

Step 9에서 score_step8.py와 일반화 통합 예정.

Usage:
    python -m scripts.validation.score_step8_e5
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


THRESHOLDS = {
    "intent_match_min": 3,
    "no_extra_changes_min": 3,
    "cost_usd_max": 0.020,
    "latency_ms_max": 5000,
}

FALLBACK_WEIGHTS = {
    "schema": 0.25,
    "intent_match": 0.25,
    "no_extra_changes": 0.25,
    "cost": 0.15,
    "latency": 0.10,
}


def lexicographic_pass(judgments: dict, metadata: dict) -> tuple[bool, str]:
    """1차 필터. 통과 여부 + 실패 원인 (디버깅용)."""
    if not judgments.get("schema_pass"):
        return False, "schema_fail"
    intent = judgments.get("intent_match_manual")
    if intent is None:
        return False, "intent_match_manual_missing"
    if intent < THRESHOLDS["intent_match_min"]:
        return False, f"intent_match<{THRESHOLDS['intent_match_min']}"
    no_extra = judgments.get("no_extra_changes_manual")
    if no_extra is None:
        return False, "no_extra_changes_manual_missing"
    if no_extra < THRESHOLDS["no_extra_changes_min"]:
        return False, f"no_extra_changes<{THRESHOLDS['no_extra_changes_min']}"
    cost = metadata.get("cost_usd")
    if cost is None or cost > THRESHOLDS["cost_usd_max"]:
        return False, f"cost>{THRESHOLDS['cost_usd_max']}"
    latency = metadata.get("latency_ms")
    if latency is None or latency > THRESHOLDS["latency_ms_max"]:
        return False, f"latency>{THRESHOLDS['latency_ms_max']}"
    return True, "pass"


def efficiency_score(judgments: dict) -> float:
    """N2.B — sqrt(intent_match × no_extra_changes)."""
    intent = judgments.get("intent_match_manual") or 0
    no_extra = judgments.get("no_extra_changes_manual") or 0
    return math.sqrt(intent * no_extra)


def fallback_score(judgments: dict, metadata: dict) -> float:
    """가중 합산. lexicographic 통과 안 한 후보 비교용."""
    schema = 1.0 if judgments.get("schema_pass") else 0.0
    intent = ((judgments.get("intent_match_manual") or 0) - 1) / 4
    no_extra = ((judgments.get("no_extra_changes_manual") or 0) - 1) / 4
    cost = metadata.get("cost_usd") or 0
    lat = metadata.get("latency_ms") or 0
    cost_norm = max(0, 1 - (cost / THRESHOLDS["cost_usd_max"]))
    lat_norm = max(0, 1 - (lat / THRESHOLDS["latency_ms_max"]))
    return (
        FALLBACK_WEIGHTS["schema"] * schema
        + FALLBACK_WEIGHTS["intent_match"] * intent
        + FALLBACK_WEIGHTS["no_extra_changes"] * no_extra
        + FALLBACK_WEIGHTS["cost"] * cost_norm
        + FALLBACK_WEIGHTS["latency"] * lat_norm
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="docs/portfolio/coach/slice2/step8_2way_e5_raw.json",
    )
    parser.add_argument(
        "--output",
        default="docs/portfolio/coach/slice2/step8_2way_e5_scored.json",
    )
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))

    by_model: dict[str, list[dict]] = defaultdict(list)
    tradeoff_cases: list[dict] = []

    for r in raw["results"]:
        if "error" in r:
            continue
        judgments = r["judgments"]
        metadata = r.get("metadata") or {}
        passed, reason = lexicographic_pass(judgments, metadata)
        eff = efficiency_score(judgments)
        fb = fallback_score(judgments, metadata)
        scored = {
            "fixture": r["fixture"],
            "model_label": r["model_label"],
            "lex_pass": passed,
            "lex_fail_reason": None if passed else reason,
            "efficiency": round(eff, 4),
            "fallback": round(fb, 4),
            "raw_judgments": judgments,
            "raw_metadata": {
                "cost_usd": metadata.get("cost_usd"),
                "latency_ms": metadata.get("latency_ms"),
                "fallback_from": metadata.get("fallback_from"),
            },
        }
        by_model[r["model_label"]].append(scored)

        # N2 trade-off 모니터링 (|intent - no_extra| >= 2)
        intent = judgments.get("intent_match_manual")
        no_extra = judgments.get("no_extra_changes_manual")
        if (
            intent is not None
            and no_extra is not None
            and abs(intent - no_extra) >= 2
        ):
            tradeoff_cases.append({
                "fixture": r["fixture"],
                "model_label": r["model_label"],
                "intent_match": intent,
                "no_extra_changes": no_extra,
                "diff": intent - no_extra,
            })

    # 모델별 평균
    model_summary: dict[str, dict] = {}
    for label, scored_list in by_model.items():
        passed_list = [s for s in scored_list if s["lex_pass"]]
        n = len(scored_list)
        model_summary[label] = {
            "n_calls": n,
            "lex_pass_rate": round(len(passed_list) / n, 4) if n else 0.0,
            "label_means": {
                "intent_match": round(
                    sum(s["raw_judgments"].get("intent_match_manual") or 0
                        for s in scored_list) / n, 4,
                ) if n else 0.0,
                "no_extra_changes": round(
                    sum(s["raw_judgments"].get("no_extra_changes_manual") or 0
                        for s in scored_list) / n, 4,
                ) if n else 0.0,
            },
            "efficiency_mean": round(
                sum(s["efficiency"] for s in scored_list) / n, 4,
            ) if n else 0.0,
            "fallback_mean": round(
                sum(s["fallback"] for s in scored_list) / n, 4,
            ) if n else 0.0,
            "cost_total": round(
                sum(s["raw_metadata"].get("cost_usd") or 0 for s in scored_list), 4,
            ),
        }

    # winner: lex_pass_rate → efficiency_mean → fallback_mean 순
    sorted_models = sorted(
        model_summary.items(),
        key=lambda kv: (
            -kv[1]["lex_pass_rate"],
            -kv[1]["efficiency_mean"],
            -kv[1]["fallback_mean"],
        ),
    )
    winner_label = sorted_models[0][0] if sorted_models else None
    use_fallback = (
        sorted_models[0][1]["lex_pass_rate"] < 0.5 if sorted_models else False
    )

    n_total = len(raw["results"])
    tradeoff_freq = len(tradeoff_cases) / n_total if n_total else 0

    output = {
        "step": "step8_2way_e5_scored",
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": THRESHOLDS,
        "fallback_weights": FALLBACK_WEIGHTS,
        "by_fixture_model": dict(by_model),
        "model_summary": model_summary,
        "winner": winner_label,
        "use_fallback": use_fallback,
        "tradeoff_analysis": {
            "context": "N2.B — 동등 가중. raw 값 보존만, winner 결정에 영향 없음.",
            "tradeoff_cases": tradeoff_cases,
            "tradeoff_frequency": round(tradeoff_freq, 4),
            "monitoring_threshold": 0.30,
            "alert": tradeoff_freq > 0.30,
            "note": "30% 초과 시 Slice 3에서 가중치 룰 재검토 신호.",
        },
        "evaluation_dimensions": ["intent_match", "no_extra_changes"],
        "_meta_for_step9_generalization": {
            "context": "Step 9 score_step8 일반화 작업 시 입력 키",
            "dim1_key": "intent_match_manual",
            "dim2_key": "no_extra_changes_manual",
            "weight": 0.5,
        },
    }

    Path(args.output).write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 콘솔 표
    print("=" * 70)
    print("Step 8 — E5 Scoring Result")
    print("=" * 70)
    print(f"\n=== Per Model ===")
    print(
        f"{'Model':<8} {'n':>3} {'PassRate':>9} "
        f"{'Intent':>7} {'NoExtra':>8} {'Efficiency':>11} {'Fallback':>9} "
        f"{'CostTotal':>10}"
    )
    for label, m in sorted_models:
        print(
            f"{label:<8} {m['n_calls']:>3} {m['lex_pass_rate']:>9.2%} "
            f"{m['label_means']['intent_match']:>7.2f} "
            f"{m['label_means']['no_extra_changes']:>8.2f} "
            f"{m['efficiency_mean']:>11.4f} {m['fallback_mean']:>9.4f} "
            f"${m['cost_total']:>9.4f}"
        )

    print(f"\n[WINNER] {winner_label}")
    print(f"  use_fallback: {use_fallback}")
    print(
        f"  tradeoff_freq: {tradeoff_freq:.2%} "
        f"({'⚠️ ALERT' if tradeoff_freq > 0.30 else 'OK'})"
    )
    if tradeoff_cases:
        print(f"  tradeoff cases ({len(tradeoff_cases)}):")
        for tc in tradeoff_cases:
            print(
                f"    {tc['fixture']:<20} {tc['model_label']:<8} "
                f"intent={tc['intent_match']} no_extra={tc['no_extra_changes']} "
                f"diff={tc['diff']:+d}"
            )

    print(f"\n[Saved] {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
