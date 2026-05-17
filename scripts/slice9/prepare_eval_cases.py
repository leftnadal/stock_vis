"""Slice 9 Part 2 §1 — manual eval용 cases.json 정리.

matrix_rationale_joined.json (26 entries)을 manual eval HTML 페이지에 최적화된 형식으로 변환.
지시서 §1.2 — joined.json의 parsed.{answer, action_items} 구조를 평탄화.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SRC = REPO_ROOT / "docs/portfolio/coach/slice9/part1/matrix_rationale_joined.json"
OUTPUT_DIR = REPO_ROOT / "docs/portfolio/coach/slice9/part2/manual_eval"

DEFAULT_QUESTION = "포트폴리오 평가"


def build_cases(joined: list[dict]) -> list[dict]:
    cases = []
    for entry in joined:
        parsed = entry.get("parsed") or {}
        action_items = parsed.get("action_items") or []
        cases.append(
            {
                "case_id": entry["case_id"],
                "case_name": entry["case_name"],
                "original_model": entry["original_model"],
                "question": entry.get("question") or DEFAULT_QUESTION,
                "commentary": entry["commentary"],
                "action_items": action_items,
                "rationale_text": entry["rationale_text"],
                "rationale_categories": entry.get("rationale_categories", []) or [],
                "rationale_score": entry["rationale_score"],
                "auto_specificity_score": entry.get("matrix_patterns_score", 0),
                "auto_specificity_detail": entry.get("rationale_specificity_detail", {}),
                # 평가 입력 슬롯 (사용자가 채울 자리)
                "manual_naturalness": None,  # 1~5
                "manual_insight": None,      # 1~5
                "manual_comment": "",
            }
        )
    return cases


def main() -> int:
    joined = json.loads(SRC.read_text())
    cases = build_cases(joined)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "cases.json"
    out.write_text(json.dumps(cases, ensure_ascii=False, indent=2))

    print(f"cases.json 정리 완료: {len(cases)} entries → {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
