"""Slice 7 Part 4 §9: Stage 2 (sonnet) eval form 생성.

Stage 1 verdict가 'proceed'면 실행. Stage 1과 동일 로직, sonnet entries만 사용.
입력은 prepare_manual_eval_v7가 만든 step9_4_eval_form_v7.md의 Stage 2 섹션이
이미 있으므로, 이 스크립트는 별도 stage2 전용 form을 사용하지 않고 동일 파일을
연속 사용한다 (사용자는 §Stage 2 섹션에 평가만 추가).

본 스크립트는 진행 가능성만 확인하고 verdict를 출력한다.

사용:
  poetry run python -m scripts.slice7.prepare_stage2_form
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGE1_VERDICT = ROOT / "docs/portfolio/coach/slice7/step9_6_stage1_verdict.json"
EVAL_FORM = ROOT / "docs/portfolio/coach/slice7/step9_4_eval_form_v7.md"


def main() -> int:
    if not STAGE1_VERDICT.exists():
        print(f"⚠ {STAGE1_VERDICT} 미존재 — score_stage1 먼저 실행", file=sys.stderr)
        return 1
    verdict = json.loads(STAGE1_VERDICT.read_text(encoding="utf-8"))
    decision = verdict.get("stage2_decision")
    if decision == "skip":
        print(f"Stage 2 skip — 사유: {verdict.get('stage2_reason')}")
        print("Stage 2 평가 진행 불필요. score_final.py로 진행.")
        return 0
    print(f"Stage 2 proceed — 사유: {verdict.get('stage2_reason')}")
    print(f"평가 위치: {EVAL_FORM} 의 '# Stage 2 — sonnet 평가' 섹션")
    print("평가 완료 후: step9_7_sonnet_filled_v7.md (또는 동일 파일)에 저장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
