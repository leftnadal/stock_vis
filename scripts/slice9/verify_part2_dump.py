"""Slice 9 Part 2 §4 — manual eval dump 정합성 자동 검증.

8 체크: cases.json 존재 + 26 entries + 필수 필드 + case_id 중복 / manual null /
        eval_page.html 존재 / HTML 내 26 case_id embed / rubric.md / instructions.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / "docs/portfolio/coach/slice9/part2/manual_eval"

EXPECTED_CASE_IDS = [
    f"S{i:02d}_{m}"
    for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14)
    for m in ("haiku", "sonnet")
]


def main() -> int:
    checks: list[tuple[str, bool]] = []

    # Check 1~4: cases.json
    cases_path = BASE / "cases.json"
    if not cases_path.exists():
        checks.append(("cases.json 존재", False))
        cases = []
    else:
        checks.append(("cases.json 존재", True))
        cases = json.loads(cases_path.read_text())
        checks.append(("cases.json 26 entries", len(cases) == 26))

        required_fields = [
            "case_id",
            "case_name",
            "commentary",
            "action_items",
            "rationale_text",
            "manual_naturalness",
            "manual_insight",
        ]
        all_have_fields = all(all(f in c for f in required_fields) for c in cases)
        checks.append(("cases.json 필수 필드 모두 존재", all_have_fields))

        ids = [c["case_id"] for c in cases]
        checks.append(("case_id 중복 없음", len(set(ids)) == len(ids)))

        all_null = all(
            c["manual_naturalness"] is None and c["manual_insight"] is None
            for c in cases
        )
        checks.append(("manual slots 초기값 None", all_null))

    # Check 5~6: eval_page.html
    html_path = BASE / "eval_page.html"
    checks.append(("eval_page.html 존재", html_path.exists()))

    if html_path.exists():
        html_content = html_path.read_text(encoding="utf-8")
        all_embed = all(f'"{cid}"' in html_content for cid in EXPECTED_CASE_IDS)
        checks.append(("HTML 26 case_id 모두 embed", all_embed))

    # Check 7: rubric.md
    rubric_path = BASE / "rubric.md"
    checks.append(("rubric.md 존재", rubric_path.exists()))

    # Check 8: instructions.md
    inst_path = BASE / "instructions.md"
    checks.append(("instructions.md 존재", inst_path.exists()))

    # 출력
    print("=" * 60)
    print("Slice 9 Part 2 — Manual Eval Dump 정합성 검증")
    print("=" * 60)
    all_pass = True
    for name, result in checks:
        verdict = "✓ PASS" if result else "✗ FAIL"
        if not result:
            all_pass = False
        print(f"{name}: {verdict}")
    print("=" * 60)
    print(f"전체 판정: {'✓ ALL PASS' if all_pass else '✗ FAIL 존재'} ({sum(1 for _, r in checks if r)}/{len(checks)})")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
