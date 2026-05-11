"""Slice 7 Part 3 Step 7.5: KPI 자동 검증 + IDENTICAL hash 유지 확인.

KPI 8 (Slice 1~6 일관):
  1. IDENTICAL hash (test_static_integrity 묶음)
  2. (위와 동일 — Slice 1 e1 + Slice 3 e2 보호)
  3. 호출 카운트 ≤ 50
  4. schema PASS rate = 100%
  5. completeness PASS rate = 100%
  6. fallback = 0건
  7. 단건 비용 임계 PASS
  8. 총 비용 ≤ $0.50

보조 KPI: provider별 cost·input·output 평균.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "docs/portfolio/coach/slice7/step7_matrix_raw.json"
METRICS_PATH = ROOT / "docs/portfolio/coach/slice7/step7_matrix_metrics.json"
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step7_5_kpi_report.md"

KPI_THRESHOLDS = {
    "call_count_max": 50,
    "schema_pass_rate": 1.0,
    "completeness_pass_rate": 1.0,
    "fallback_max": 0,
    "single_cost_max": 0.020,
    "total_cost_max": 0.50,
}


def check_identical_hash() -> tuple[bool, str]:
    r = subprocess.run(
        ["poetry", "run", "pytest", "-q", "portfolio/tests/test_static_integrity.py"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    out = r.stdout + "\n" + r.stderr
    return (r.returncode == 0 and "7 passed" in out, out)


def main() -> int:
    if not MATRIX_PATH.exists() or not METRICS_PATH.exists():
        print(f"✗ run scripts/slice7/run_step7_matrix.py first")
        return 1

    results = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    total = metrics["total_calls"]
    schema_pass = int(metrics["schema_pass"].split("/")[0])
    completeness_pass = int(metrics["completeness_pass"].split("/")[0])

    hash_pass, hash_output = check_identical_hash()

    kpis = {
        "1_slice1_e1_identical": hash_pass,
        "2_slice3_e2_identical": hash_pass,
        "3_call_count": total <= KPI_THRESHOLDS["call_count_max"],
        "4_schema_pass_rate": (
            (schema_pass / total if total else 0) >= KPI_THRESHOLDS["schema_pass_rate"]
        ),
        "5_completeness_pass_rate": (
            (completeness_pass / total if total else 0)
            >= KPI_THRESHOLDS["completeness_pass_rate"]
        ),
        "6_fallback_zero": metrics["fallback_count"] == 0,
        "7_single_cost_pass": metrics["max_single_cost"] <= KPI_THRESHOLDS["single_cost_max"],
        "8_total_cost_pass": metrics["total_cost"] <= KPI_THRESHOLDS["total_cost_max"],
    }
    all_pass = all(kpis.values())

    by_provider: dict[str, dict] = {}
    for r in results:
        prov = r.get("provider_meta") or r.get("provider")
        if not prov:
            continue
        d = by_provider.setdefault(
            prov, {"costs": [], "input_tokens": [], "output_tokens": []}
        )
        if "cost_usd" in r:
            d["costs"].append(r["cost_usd"])
            d["input_tokens"].append(r["input_tokens"])
            d["output_tokens"].append(r["output_tokens"])

    provider_stats = {}
    for prov, d in by_provider.items():
        n = len(d["costs"])
        if n == 0:
            continue
        provider_stats[prov] = {
            "n": n,
            "avg_cost": round(sum(d["costs"]) / n, 6),
            "avg_input": int(sum(d["input_tokens"]) / n),
            "avg_output": int(sum(d["output_tokens"]) / n),
        }

    md = [
        "# Slice 7 Part 3 Step 7.5 — KPI Report",
        "",
        f"## KPI 8/8: {'**PASS** ✓' if all_pass else '**FAIL** ✗'}",
        "",
    ]
    for k, v in kpis.items():
        md.append(f"- {k}: {'✓' if v else '✗'}")
    md.extend(["", "## 보조 KPI — Provider 통계", ""])
    md.append("| provider | n | avg_cost | avg_input | avg_output |")
    md.append("|---|---|---|---|---|")
    for prov, s in provider_stats.items():
        md.append(
            f"| {prov} | {s['n']} | ${s['avg_cost']} | {s['avg_input']} | {s['avg_output']} |"
        )

    OUT_PATH.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"✓ KPI report: {OUT_PATH}")
    print(f"  all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
