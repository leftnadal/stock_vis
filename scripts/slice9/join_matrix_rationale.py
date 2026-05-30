"""Slice 9 Part 1 §3 — matrix + rationale_records join.

matrix_summary.json의 results 26 entries에 rationale_records.json을 case_id로 join.
Part 2 manual eval dump의 input 자료.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")

import django  # noqa: E402

django.setup()

from portfolio.tests.helpers.matrix_loader import (  # noqa: E402
    assign_case_ids,
    get_commentary,
    load_matrix_cases,
)

MATRIX_PART = REPO_ROOT / "docs/portfolio/coach/slice9/part1"
OUTPUT_PATH = MATRIX_PART / "matrix_rationale_joined.json"


def main() -> None:
    cases = load_matrix_cases()
    case_ids = assign_case_ids(cases)
    rationales = json.loads((MATRIX_PART / "rationale_records.json").read_text())
    rationales_by_id = {r["case_id"]: r for r in rationales}

    joined = []
    for case, case_id in zip(cases, case_ids):
        r = rationales_by_id.get(case_id)
        if not r:
            print(f"⚠ rationale missing for {case_id}")
            continue
        joined.append(
            {
                "case_id": case_id,
                "case_name": case.get("case"),
                "original_model": case.get("model"),
                "fixture_file": case.get("fixture_file"),
                "commentary": get_commentary(case),
                "parsed": case.get("parsed", {}),
                "matrix_4판정": case.get("kpi_4판정", {}),
                "matrix_cost_usd": case.get("cost_usd"),
                "matrix_patterns_score": case.get("patterns_score"),
                "rationale_text": r["rationale_text"],
                "rationale_categories": r["rationale_categories"],
                "rationale_score": r["rationale_score"],
                "rationale_cost_usd": r["cost_usd"],
                "rationale_specificity_detail": r["original_specificity_detail"],
            }
        )

    OUTPUT_PATH.write_text(json.dumps(joined, ensure_ascii=False, indent=2))
    print(f"Joined: {len(joined)} entries → {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
