"""
Slice 2 Step 0.5 — Step 6 산출물 재처리 (LLM 호출 0).

Slice 1에서 도입된 robust parser(`portfolio.llm.parsers.parse_json_response`)와
갱신 임계($0.020)를 적용해 docs/portfolio/coach/slice1/step6_smoke_output.json의
judgments를 갱신.

naturalness는 사용자 수동 평가를 인자로 받음. 미입력 시 기존 값 보존.

Usage:
    # naturalness가 기억나면 인자로:
    python -m scripts.validation.reparse_step6 --naturalness 4

    # 그렇지 않으면 인자 없이 (기존 값 보존):
    python -m scripts.validation.reparse_step6
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.llm_outputs import OneLineDiagnosis


TARGET_PATH = Path("docs/portfolio/coach/slice1/step6_smoke_output.json")

NEW_THRESHOLDS = {
    "cost_usd_max": 0.020,  # Slice 1 회고에서 갱신 ($0.001 → $0.020)
    "latency_ms_max": 5000,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Step 6 산출물 재처리 (LLM 호출 없음)")
    parser.add_argument(
        "--naturalness",
        type=int,
        default=None,
        choices=[1, 2, 3, 4, 5],
        help="사용자 수동 평가 (1~5). 미입력 시 기존 값 보존.",
    )
    args = parser.parse_args()

    if not TARGET_PATH.exists():
        print(f"[ERROR] {TARGET_PATH} 없음. Step 6 먼저 실행 필요.")
        return 1

    data = json.loads(TARGET_PATH.read_text(encoding="utf-8"))

    # raw_text 또는 (Slice 1 v1) raw_content 키 모두 지원.
    raw = data.get("raw_text") or data.get("raw_content") or ""
    if not raw:
        print("[ERROR] raw_text/raw_content 비어있음. 재파싱 불가.")
        return 1

    # robust 파서 (마크다운 펜스 사전 제거)
    parsed = None
    schema_pass = False
    schema_error: str | None = None
    try:
        parsed = parse_json_response(OneLineDiagnosis, raw)
        schema_pass = True
    except Exception as exc:  # noqa: BLE001
        schema_error = f"{type(exc).__name__}: {str(exc)[:200]}"

    # 새 임계 적용
    cost_usd = data["metadata"].get("cost_usd", 0)
    latency_ms = data["metadata"].get("latency_ms", 0)
    cost_pass = cost_usd <= NEW_THRESHOLDS["cost_usd_max"]
    latency_pass = latency_ms <= NEW_THRESHOLDS["latency_ms_max"]

    # naturalness — 인자 우선, 없으면 기존 값 보존
    prev_nat = data.get("judgments", {}).get("naturalness")
    if args.naturalness is not None:
        naturalness: int | str | None = args.naturalness
    else:
        naturalness = prev_nat

    data["judgments"] = {
        "schema_pass": schema_pass,
        "schema_error": schema_error,
        "cost_pass": cost_pass,
        "latency_pass": latency_pass,
        "naturalness": naturalness,
    }
    data["thresholds"] = NEW_THRESHOLDS
    if parsed is not None:
        data["parsed"] = parsed.model_dump()

    data["reparse_metadata"] = {
        "reparsed_at": datetime.now(timezone.utc).isoformat(),
        "previous_thresholds_cost_usd_max": 0.001,
        "current_thresholds_cost_usd_max": NEW_THRESHOLDS["cost_usd_max"],
        "parser_module": "portfolio.llm.parsers.parse_json_response",
        "naturalness_arg_provided": args.naturalness is not None,
        "note": "raw_text 보존, judgments + thresholds + parsed만 갱신.",
    }

    TARGET_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] {TARGET_PATH} reparse 완료")
    print(f"  schema_pass:  {schema_pass}")
    print(
        f"  cost_pass:    {cost_pass} (${cost_usd:.5f} / ${NEW_THRESHOLDS['cost_usd_max']:.4f})"
    )
    print(
        f"  latency_pass: {latency_pass} ({latency_ms}ms / {NEW_THRESHOLDS['latency_ms_max']}ms)"
    )
    print(f"  naturalness:  {naturalness} (arg_provided={args.naturalness is not None})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
