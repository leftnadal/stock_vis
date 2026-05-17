"""Slice 9 Part 1 §4.1 — 분포 폭 측정 (KPI 11/#26).

rationale_records.json에서 rationale_score 분포 폭 (max - min) 측정.
KPI 11 기준: 분포 폭 ≥ 3.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PART1_DIR = REPO_ROOT / "docs/portfolio/coach/slice9/part1"


def main() -> int:
    rationale_path = PART1_DIR / "rationale_records.json"
    if not rationale_path.exists():
        print(f"❌ {rationale_path} 부재. Batch 실행 후 다시 시도.")
        return 1

    rationales = json.loads(rationale_path.read_text())

    auto_scores = [r["original_specificity_score"] for r in rationales]
    auto_dist = Counter(auto_scores)
    rationale_scores = [r["rationale_score"] for r in rationales]
    rationale_dist = Counter(rationale_scores)

    auto_width = (max(auto_scores) - min(auto_scores)) if auto_scores else 0
    rationale_width = (max(rationale_scores) - min(rationale_scores)) if rationale_scores else 0

    print(f"Auto specificity scores: {dict(sorted(auto_dist.items()))}, width={auto_width}")
    print(f"Rationale scores: {dict(sorted(rationale_dist.items()))}, width={rationale_width}")
    print(f"KPI 11 (분포 폭 ≥ 3): {'PASS' if rationale_width >= 3 else 'FAIL'}")

    summary = {
        "auto_scores_distribution": dict(sorted(auto_dist.items())),
        "rationale_scores_distribution": dict(sorted(rationale_dist.items())),
        "auto_width": auto_width,
        "rationale_width": rationale_width,
        "kpi11_pass": rationale_width >= 3,
    }
    out = PART1_DIR / "distribution_width.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"→ {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
