"""Slice 7 Part 3 #β2 2차 측정 (Step 7 matrix 데이터 기반).

28 calls의 actual_input_tokens vs estimator(prompt 포함) 비교.
KPI: max delta ≤ 30% → close / > 30% → keep_open.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from portfolio.llm.token_budgets import estimate_input_tokens  # noqa: E402
from portfolio.prompts.e4.builder import build_e4_prompt  # noqa: E402
from portfolio.schemas.e4_conversation import E4ConversationInput  # noqa: E402

MATRIX_PATH = ROOT / "docs/portfolio/coach/slice7/step7_matrix_raw.json"
FIXTURE_DIR = ROOT / "portfolio/tests/fixtures/e4_conversation"
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step7_beta2_round2.json"
REPORT_PATH = ROOT / "docs/portfolio/coach/slice7/step7_beta2_round2.md"

KPI_THRESHOLD = 30.0


def main() -> int:
    if not MATRIX_PATH.exists():
        print(f"✗ run scripts/slice7/run_step7_matrix.py first")
        return 1

    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    # fixture 파일 prefix 매핑 (scenario_id → file stem)
    fixture_stems = {fp.stem.split("_")[0]: fp for fp in FIXTURE_DIR.glob("S*.json")}

    results: list[dict] = []
    for entry in matrix:
        if "input_tokens" not in entry:
            continue
        sid = entry["scenario_id"]  # 예: "S01"
        fp = fixture_stems.get(sid)
        if fp is None:
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        try:
            inp = E4ConversationInput(**data["input"])
        except Exception:
            # I2 trigger (S13) 등 schema reject
            continue
        prompt = build_e4_prompt(inp)
        estimated = estimate_input_tokens(prompt)
        actual = entry["input_tokens"]
        delta_pct = (estimated - actual) / actual * 100 if actual else 0.0
        results.append(
            {
                "scenario_id": sid,
                "tier": entry["tier"],
                "provider": entry["provider"],
                "estimated": estimated,
                "actual": actual,
                "delta_pct": round(delta_pct, 2),
                "delta_abs_pct": round(abs(delta_pct), 2),
            }
        )

    deltas = [r["delta_abs_pct"] for r in results]
    max_delta = max(deltas) if deltas else 0.0
    avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
    kpi_pass = max_delta <= KPI_THRESHOLD

    summary = {
        "results": results,
        "n": len(results),
        "max_delta_abs_pct": round(max_delta, 2),
        "avg_delta_abs_pct": round(avg_delta, 2),
        "kpi_threshold_pct": KPI_THRESHOLD,
        "kpi_pass": kpi_pass,
        "beta2_verdict": "close" if kpi_pass else "keep_open",
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 3 #β2 2차 측정 (Step 7 matrix 후)",
        "",
        f"## KPI: max delta ≤ {KPI_THRESHOLD:.0f}% → "
        f"{'**PASS** ✓' if kpi_pass else '**FAIL** ✗'}",
        "",
        f"- n: {len(results)}",
        f"- max delta: {max_delta:.2f}%",
        f"- avg delta: {avg_delta:.2f}%",
        f"- **#β2 verdict: {summary['beta2_verdict']}**",
        "",
        "## 상세",
        "",
        "| scenario | tier | provider | estimated | actual | delta% |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        md.append(
            f"| {r['scenario_id']} | {r['tier']} | {r['provider']} | "
            f"{r['estimated']} | {r['actual']} | {r['delta_pct']:+.2f}% |"
        )
    REPORT_PATH.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"✓ #β2 round 2: {OUT_PATH}")
    print(f"  max delta: {max_delta:.2f}% / verdict: {summary['beta2_verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
