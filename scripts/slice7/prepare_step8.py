"""Slice 7 Part 3 Step 8: Part 4 manual eval 입력 자료 준비.

Step 7 matrix raw → Part 4 평가용 entry 변환.
scored.json은 stub (Part 4에서 채움).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "docs/portfolio/coach/slice7/step7_matrix_raw.json"
OUT_RAW = ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json"
OUT_SCORED = ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_scored.json"
OUT_SUMMARY = ROOT / "docs/portfolio/coach/slice7/step7_5_summary.md"


def main() -> int:
    if not MATRIX_PATH.exists():
        print(f"✗ run scripts/slice7/run_step7_matrix.py first")
        return 1

    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    entries = []
    for r in matrix:
        if not r.get("schema_pass"):
            continue
        entries.append(
            {
                "scenario_id": r["scenario_id"],
                "preset_id": r["preset_id"],
                "tier": r["tier"],
                "provider": r.get("provider_meta") or r["provider"],
                "trigger_case": r.get("trigger_case"),
                "commentary": r["raw_content"],
                "cost_usd": r["cost_usd"],
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "latency_ms": r.get("latency_ms"),
            }
        )

    raw_payload = {"entries": entries, "total": len(entries)}
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    OUT_RAW.write_text(json.dumps(raw_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    scored_stub = {
        "entries": [
            {
                **e,
                "naturalness": None,
                "insight": None,
                "label_mean": None,
                "efficiency": None,
            }
            for e in entries
        ],
        "winner": None,
        "g_branches": [],
    }
    OUT_SCORED.write_text(
        json.dumps(scored_stub, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# Slice 7 Part 3 Step 8 Summary (Part 4 입력 가이드)",
        "",
        f"- 총 entries: {len(entries)}",
        f"- 매트릭스 raw: `{OUT_RAW.relative_to(ROOT)}`",
        f"- scored stub: `{OUT_SCORED.relative_to(ROOT)}`",
        "",
        "## Part 4 manual eval 작업 순서",
        "",
        "1. `prepare_manual_eval_v7.py` 실행 → eval_form_v7.md + eval_key_v7.json (seed=42)",
        "2. 병진 rubric 기반 평가 (rubric §C.6 분포 폭 KPI 자동 보고)",
        "3. `score_step9_v7.py` 실행 → winner + 글쓰기 가설 6/6 + 외삽 검증 + #26 자연 close 판정",
        "",
        "## DIMENSION_LOOKUP entry 추가 (Part 4 진입 시)",
        "",
        "`scripts/validation/score_step8.py` DIMENSION_LOOKUP에 `e4_conversation` 등록 필요.",
        "상세: `docs/portfolio/coach/slice7/step3_dimension_lookup_decision.md` §2.2",
    ]
    OUT_SUMMARY.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"✓ Step 8 raw: {OUT_RAW}")
    print(f"✓ Step 8 scored stub: {OUT_SCORED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
