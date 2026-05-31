"""
Slice 1 Part 2 — Step 8 후처리: raw_text를 robust parser로 재파싱.

기존 호출(step8_3way_raw.json)을 비용 0으로 재평가. naturalness/insight
입력값은 그대로 보존, schema_pass / parsed / schema_error만 갱신.

이유: 9회 호출 모두 LLM이 ```json ... ``` 마크다운 펜스로 감쌈 → 단순
model_validate_json은 실패. portfolio.llm.parsers.parse_json_response가
펜스 사전 제거 후 검증.

산출:
  docs/portfolio/coach/slice1/step8_3way_raw.json (in-place 갱신)

Usage:
    python -m scripts.validation.reparse_step8
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from apps.portfolio.llm.parsers import parse_json_response
from apps.portfolio.schemas.llm_outputs import OneLineDiagnosis

RAW_PATH = Path("docs/portfolio/coach/slice1/step8_3way_raw.json")


def main() -> int:
    if not RAW_PATH.exists():
        print(f"[ERROR] {RAW_PATH} 없음. run_step8_3way 먼저 실행.")
        return 1

    data = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    results = data.get("results", [])

    transitioned: list[str] = []  # FAIL → OK 전환 케이스
    still_fail: list[tuple[str, str]] = []
    no_text: list[str] = []

    for r in results:
        label = r.get("label", "?")
        fixture = r.get("fixture", "?")
        key = f"{label}×{fixture}"

        text = r.get("raw_text")
        if text is None:
            no_text.append(key)
            continue

        prev_pass = bool(r.get("schema_pass"))
        try:
            parsed = parse_json_response(OneLineDiagnosis, text)
        except Exception as exc:  # noqa: BLE001
            r["schema_pass"] = False
            r["schema_error"] = str(exc)
            r["parsed"] = None
            still_fail.append((key, str(exc).splitlines()[0]))
            continue

        r["schema_pass"] = True
        r["schema_error"] = None
        r["parsed"] = parsed.model_dump()
        if not prev_pass:
            transitioned.append(key)

    RAW_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = len(results)
    pass_count = sum(1 for r in results if r.get("schema_pass"))
    print("=" * 60)
    print("Step 8 reparse — robust parser (markdown fence strip)")
    print("=" * 60)
    print(f"\nResults: {pass_count}/{total} schema_pass")
    print(f"FAIL → OK 전환: {len(transitioned)}건")
    if transitioned:
        for k in transitioned:
            print(f"  + {k}")
    if still_fail:
        print(f"\n여전히 schema FAIL: {len(still_fail)}건")
        for k, msg in still_fail:
            print(f"  - {k}: {msg}")
    if no_text:
        print(f"\nraw_text 없음: {no_text}")

    print(f"\n[Saved] {RAW_PATH}")
    print("다음 단계: python -m scripts.validation.score_step8 (재실행)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
