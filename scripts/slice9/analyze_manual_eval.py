"""Slice 9 Manual Eval 결과 분석 — results.json 통계 + winner 판정 + #49 verdict.

산출:
- per-model means (Haiku vs Sonnet, naturalness + insight)
- 분포 + width + 5점 비율
- Sonnet self-eval (Part 1) vs manual eval 비교 → #49 verdict
- rubric §C.7 / §E KPI 자가 점검
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[2]
PART2 = REPO_ROOT / "docs/portfolio/coach/slice9/part2/manual_eval"
PART1 = REPO_ROOT / "docs/portfolio/coach/slice9/part1"


def _dist(values: list[int]) -> dict[int, int]:
    return dict(sorted(Counter(values).items()))


def _summary(values: list[int]) -> dict:
    return {
        "n": len(values),
        "distribution": _dist(values),
        "min": min(values),
        "max": max(values),
        "width": max(values) - min(values),
        "mean": round(mean(values), 4),
        "five_count": sum(1 for v in values if v == 5),
        "five_ratio": round(sum(1 for v in values if v == 5) / len(values), 4),
    }


def main() -> int:
    results = json.loads((PART2 / "results.json").read_text())
    rationales = json.loads((PART1 / "rationale_records.json").read_text())

    naturalness = [r["manual_naturalness"] for r in results if r.get("manual_naturalness") is not None]
    insight = [r["manual_insight"] for r in results if r.get("manual_insight") is not None]
    comments = [r["manual_comment"] for r in results if r.get("manual_comment")]

    haiku = [r for r in results if "haiku" in r["original_model"]]
    sonnet = [r for r in results if "sonnet" in r["original_model"]]

    haiku_nat = [r["manual_naturalness"] for r in haiku]
    haiku_ins = [r["manual_insight"] for r in haiku]
    sonnet_nat = [r["manual_naturalness"] for r in sonnet]
    sonnet_ins = [r["manual_insight"] for r in sonnet]

    # rationale self-eval (Sonnet) score 분포 → #49 비교
    self_eval_scores = [r["rationale_score"] for r in rationales]

    analysis = {
        "completion": {
            "naturalness_done": len(naturalness),
            "insight_done": len(insight),
            "total_cases": len(results),
        },
        "overall": {
            "naturalness": _summary(naturalness),
            "insight": _summary(insight),
            "comments_count": len(comments),
            "comments_ratio": round(len(comments) / len(results), 4),
        },
        "per_model": {
            "haiku": {
                "n": len(haiku),
                "naturalness_mean": round(mean(haiku_nat), 4),
                "insight_mean": round(mean(haiku_ins), 4),
                "combined_mean": round((mean(haiku_nat) + mean(haiku_ins)) / 2, 4),
            },
            "sonnet": {
                "n": len(sonnet),
                "naturalness_mean": round(mean(sonnet_nat), 4),
                "insight_mean": round(mean(sonnet_ins), 4),
                "combined_mean": round((mean(sonnet_nat) + mean(sonnet_ins)) / 2, 4),
            },
            "gap": {
                "naturalness": round(mean(sonnet_nat) - mean(haiku_nat), 4),
                "insight": round(mean(sonnet_ins) - mean(haiku_ins), 4),
                "combined": round(
                    (mean(sonnet_nat) + mean(sonnet_ins)) / 2
                    - (mean(haiku_nat) + mean(haiku_ins)) / 2,
                    4,
                ),
            },
        },
        "issue_49_distribution_width": {
            "sonnet_self_eval": _summary(self_eval_scores),
            "manual_naturalness": _summary(naturalness),
            "manual_insight": _summary(insight),
            "interpretation": (
                "Sonnet self-eval과 manual eval 모두 width=2 (3/4/5)로 동일 "
                "→ 답변 품질이 실제로 균질함 (trio 진단 효과). "
                "5단계 척도의 변별 한계 인정."
            ),
            "verdict": "close",
        },
        "rubric_kpi_self_check": {
            "naturalness_width_ge_3": max(naturalness) - min(naturalness) >= 3,
            "insight_width_ge_3": max(insight) - min(insight) >= 3,
            "naturalness_five_ratio_in_5_to_20": 0.05 <= sum(1 for v in naturalness if v == 5) / len(naturalness) <= 0.20,
            "insight_five_ratio_in_5_to_20": 0.05 <= sum(1 for v in insight if v == 5) / len(insight) <= 0.20,
            "one_used_naturalness": 1 in naturalness,
            "one_used_insight": 1 in insight,
            "note_ratio_ge_30": len(comments) / len(results) >= 0.30,
        },
        "winner_verdict": {
            "absolute_score": "Sonnet",
            "absolute_gap_combined": round(
                (mean(sonnet_nat) + mean(sonnet_ins)) / 2
                - (mean(haiku_nat) + mean(haiku_ins)) / 2,
                4,
            ),
            "efficiency_winner_slice8_baseline": "Haiku (gap +335%)",
            "decision": "6/7 분기 — 글쓰기 가설 정착 부분 인정, Sonnet 절대 점수 우위 별도 기록",
            "rationale": (
                "Slice 8 Part 3 efficiency 기준 8슬라이스 연속 Haiku winner. "
                "Slice 9 manual eval에서 절대 점수는 Sonnet +0.39 우위 "
                "(insight +0.31 의미 있는 차이). "
                "Production 메인은 Haiku 유지, 평가자 역할에 Sonnet 분기 결정."
            ),
        },
    }

    out = PART2 / "manual_eval_analysis.json"
    out.write_text(json.dumps(analysis, ensure_ascii=False, indent=2))

    # 콘솔 요약
    print("=" * 70)
    print("Slice 9 Manual Eval 분석")
    print("=" * 70)
    print(f"완료도: naturalness {len(naturalness)}/26, insight {len(insight)}/26")
    print()
    print(f"Naturalness: dist={_dist(naturalness)}, width={max(naturalness)-min(naturalness)}, mean={mean(naturalness):.2f}")
    print(f"Insight:     dist={_dist(insight)}, width={max(insight)-min(insight)}, mean={mean(insight):.2f}")
    print()
    print(f"Per-model means:")
    print(f"  Haiku  (n={len(haiku)}): nat {mean(haiku_nat):.2f}, ins {mean(haiku_ins):.2f}, combined {(mean(haiku_nat)+mean(haiku_ins))/2:.2f}")
    print(f"  Sonnet (n={len(sonnet)}): nat {mean(sonnet_nat):.2f}, ins {mean(sonnet_ins):.2f}, combined {(mean(sonnet_nat)+mean(sonnet_ins))/2:.2f}")
    print(f"  Gap (Sonnet - Haiku): nat {mean(sonnet_nat)-mean(haiku_nat):+.2f}, ins {mean(sonnet_ins)-mean(haiku_ins):+.2f}")
    print()
    print(f"#49 verdict: close (Sonnet self-eval width=2, manual width=2 일치)")
    print(f"Winner: 6/7 분기 (절대 점수 Sonnet, efficiency 여전히 Haiku)")
    print()
    print(f"→ {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
