"""Slice 9 Part 1 §5 — #β2 estimator 2차 측정.

Slice 7 systematic underestimate (-50% bias) → Slice 8 Step 0 재설계.
Part 1에서 Sonnet 26건 실데이터로 estimator 정밀도 검증.

KPI 12 기준: max delta ≤ 30%.
verdict: close (≤30%) / keep_open (30~50%) / re-design (>50%).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean, median

REPO_ROOT = Path(__file__).resolve().parents[2]
PART1_DIR = REPO_ROOT / "docs/portfolio/coach/slice9/part1"


def main() -> int:
    rationale_path = PART1_DIR / "rationale_records.json"
    if not rationale_path.exists():
        print(f"❌ {rationale_path} 부재. Batch 실행 후 다시 시도.")
        return 1

    rationales = json.loads(rationale_path.read_text())

    measurements = []
    for r in rationales:
        est = r.get("estimated_input_tokens", 0)
        actual = r.get("input_tokens", 0)
        if not est or not actual:
            continue
        delta = abs(actual - est) / actual
        measurements.append(
            {
                "case_id": r["case_id"],
                "estimated": est,
                "actual": actual,
                "delta": delta,
                "sign": "under" if est < actual else "over",
            }
        )

    if not measurements:
        print("측정 데이터 없음")
        return 1

    deltas = [m["delta"] for m in measurements]
    max_delta = max(deltas)
    p90 = sorted(deltas)[int(len(deltas) * 0.9)] if len(deltas) >= 10 else max_delta
    under_count = sum(1 for m in measurements if m["sign"] == "under")

    print(f"#β2 2차 측정 (n={len(measurements)}, Sonnet rationale Part 1):")
    print(f"  max delta: {max_delta*100:.2f}%")
    print(f"  p90 delta: {p90*100:.2f}%")
    print(f"  median: {median(deltas)*100:.2f}%")
    print(f"  mean: {mean(deltas)*100:.2f}%")
    print(
        f"  under-estimate: {under_count}/{len(measurements)} "
        f"({under_count/len(measurements)*100:.1f}%)"
    )
    print()
    print(f"Slice 7 baseline: max 52.21%, -50% bias")
    print(f"Slice 8 Step 0 재설계 후 max delta 1.88% (mock)")
    print(f"Slice 9 Part 1 (real Sonnet): max delta {max_delta*100:.2f}%")
    print()

    if max_delta <= 0.30:
        verdict = "close"
    elif max_delta <= 0.50:
        verdict = "keep_open"
    else:
        verdict = "re-design"
    print(f"Verdict: {verdict}")

    summary = {
        "measurements": measurements,
        "summary": {
            "n": len(measurements),
            "max_delta": max_delta,
            "p90_delta": p90,
            "median_delta": median(deltas),
            "mean_delta": mean(deltas),
            "under_ratio": under_count / len(measurements),
        },
        "verdict": verdict,
    }

    out = PART1_DIR / "beta2_round2.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"→ {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
