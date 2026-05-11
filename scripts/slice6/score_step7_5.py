"""Slice 6 Part 3 Step 7.5 — KPI 자동 검증 (8 + 보조 12) + 케이스 A~G.

Step 7 raw + metrics → KPI 8/8 PASS 판정 + IDENTICAL hash + 케이스 검증.
Slice 5 score_step8 패턴 mirror.

Usage:
    python -m scripts.slice6.score_step7_5
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

from scripts.validation._setup import init_django

init_django()


METRICS_PATH = Path("docs/portfolio/coach/slice6/step7_matrix_metrics.json")
RAW_PATH = Path("docs/portfolio/coach/slice6/step7_matrix_raw.json")
REPORT_PATH = Path("docs/portfolio/coach/slice6/step7_5_kpi_report.md")

# Slice 1/3 IDENTICAL hash baseline (Slice 5 Step 9 KPI 유지)
IDENTICAL_BASELINE = {
    "slice1_e1": "917fa3ef821426e88178456a1f70462f5ab9576e20f06a63d0a88c28fcc0f7b9",
    "slice3_e2": "5594c6ab9291213bca7d3e98b3b221164575eb47c52a281248ddc616218cf3ba",
}
IDENTICAL_PATHS = {
    "slice1_e1": Path("docs/portfolio/coach/slice1/step8_3way_scored.json"),
    "slice3_e2": Path("docs/portfolio/coach/slice3/step8_2way_e2_scored.json"),
}

# Slice 6 Part 3 §3.3 KPI 8
KPI_THRESHOLDS = {
    "total_calls": 11,  # smoke 1 + matrix 10
    "schema_required": 10,
    "completeness_required": 10,
    "fallback_max": 0,
    "haiku_cost_per_call": 0.010,
    "sonnet_cost_per_call": 0.030,
    "total_cost_max": 0.150,
    "max_calls_budget": 50,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    print("=" * 70)
    print("Slice 6 Part 3 Step 7.5 — KPI 자동 검증")
    print("=" * 70)

    if not METRICS_PATH.exists() or not RAW_PATH.exists():
        print(f"[ERROR] {METRICS_PATH} or {RAW_PATH} 미존재. Step 7 실행 필요.")
        return 1

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))

    # ====================================================================
    # KPI 8 — 핵심 (Slice 6 Part 3 §3.3)
    # ====================================================================
    kpi_basic = metrics["kpi_basic"]

    # 1. Slice 1 e1 IDENTICAL
    slice1_hash = _sha256(IDENTICAL_PATHS["slice1_e1"])
    kpi_1 = slice1_hash == IDENTICAL_BASELINE["slice1_e1"]

    # 2. Slice 3 e2 IDENTICAL
    slice3_hash = _sha256(IDENTICAL_PATHS["slice3_e2"])
    kpi_2 = slice3_hash == IDENTICAL_BASELINE["slice3_e2"]

    # 3. 호출 카운트 (smoke 1 + matrix 10 = 11)
    # CostGuard는 reset_for_slice로 step 7에서 리셋되므로 matrix만 카운트.
    # 실제 LLM 호출 총합 = smoke (Step 6) 1 + matrix (Step 7) 10 = 11
    cost_guard_status = raw["cost_guard_status_at_end"]
    smoke_path = Path("docs/portfolio/coach/slice6/step6_smoke_result.json")
    smoke_calls = 0
    if smoke_path.exists():
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        smoke_calls = smoke["cost_guard_status"]["call_count"]
    total_actual_calls = cost_guard_status["call_count"] + smoke_calls
    kpi_3 = total_actual_calls == KPI_THRESHOLDS["total_calls"]

    # 4. schema 10/10
    schema_count = int(kpi_basic["schema_pass"].split("/")[0])
    kpi_4 = schema_count == KPI_THRESHOLDS["schema_required"]

    # 5. completeness 10/10
    comp_count = int(kpi_basic["completeness_auto"].split("/")[0])
    kpi_5 = comp_count == KPI_THRESHOLDS["completeness_required"]

    # 6. fallback 0건
    kpi_6 = kpi_basic["fallback"] == KPI_THRESHOLDS["fallback_max"]

    # 7. 단건 비용 PASS
    kpi_7 = bool(kpi_basic["cost_per_call_pass"])

    # 8. 총 비용 PASS (smoke + matrix 합산)
    smoke_cost = 0.004470  # Step 6 측정값
    total_with_smoke = kpi_basic["total_cost_usd"] + smoke_cost
    kpi_8 = total_with_smoke <= KPI_THRESHOLDS["total_cost_max"]

    kpis_8 = {
        "1_slice1_e1_identical": kpi_1,
        "2_slice3_e2_identical": kpi_2,
        "3_call_count_11_of_50": kpi_3,
        "4_schema_10_of_10": kpi_4,
        "5_completeness_10_of_10": kpi_5,
        "6_fallback_zero": kpi_6,
        "7_cost_per_call_pass": kpi_7,
        "8_total_cost_pass": kpi_8,
    }
    kpi_8_pass = all(kpis_8.values())

    # ====================================================================
    # 보조 KPI 9~12 (Slice 6 Part 3 §3.4)
    # ====================================================================

    # 9. label_means 격차 (자동 측정만, 판정은 Part 4)
    haiku_costs = [
        (r.get("metadata") or {}).get("cost_usd", 0)
        for r in raw["results"] if r["model_label"] == "haiku"
    ]
    sonnet_costs = [
        (r.get("metadata") or {}).get("cost_usd", 0)
        for r in raw["results"] if r["model_label"] == "sonnet"
    ]
    haiku_outputs = [
        (r.get("metadata") or {}).get("output_tokens", 0)
        for r in raw["results"] if r["model_label"] == "haiku"
    ]
    sonnet_outputs = [
        (r.get("metadata") or {}).get("output_tokens", 0)
        for r in raw["results"] if r["model_label"] == "sonnet"
    ]
    kpi_9 = {
        "haiku_avg_cost": round(statistics.mean(haiku_costs), 6) if haiku_costs else 0,
        "sonnet_avg_cost": round(statistics.mean(sonnet_costs), 6) if sonnet_costs else 0,
        "haiku_avg_output_tokens": int(statistics.mean(haiku_outputs)) if haiku_outputs else 0,
        "sonnet_avg_output_tokens": int(statistics.mean(sonnet_outputs)) if sonnet_outputs else 0,
        "cost_gap_pct": round(
            (statistics.mean(sonnet_costs) - statistics.mean(haiku_costs))
            / statistics.mean(haiku_costs) * 100, 1
        ) if haiku_costs else 0,
        "note": "label_means efficiency 판정은 manual eval 후 (Part 4)",
    }

    # 10. preset 외삽 insight 그룹차 (preset_alignment_matches_expected 기준)
    alignment_analysis = metrics["preset_alignment_analysis"]
    haiku_matches = sum(
        1 for a in alignment_analysis
        if a["haiku_llm"] == a["expected"]
    )
    sonnet_matches = sum(
        1 for a in alignment_analysis
        if a["sonnet_llm"] == a["expected"]
    )
    # 단순 graph: alignment 정합률을 그룹차 proxy로 사용 (Part 4 manual eval에서 insight 측정)
    kpi_10 = {
        "haiku_alignment_matches": f"{haiku_matches}/{len(alignment_analysis)}",
        "sonnet_alignment_matches": f"{sonnet_matches}/{len(alignment_analysis)}",
        "alignment_divergence_cases": [
            {
                "fixture": a["fixture"],
                "expected": a["expected"],
                "haiku_llm": a["haiku_llm"],
                "sonnet_llm": a["sonnet_llm"],
            }
            for a in alignment_analysis
            if a["haiku_llm"] != a["expected"] or a["sonnet_llm"] != a["expected"]
        ],
        "note": "insight 그룹차 0.50 임계 판정은 manual eval 필요 (Part 4)",
    }

    # 11. lex coverage (chars 길이 기반 proxy)
    haiku_text_lens = [
        len(r.get("raw_content", "")) for r in raw["results"] if r["model_label"] == "haiku"
    ]
    sonnet_text_lens = [
        len(r.get("raw_content", "")) for r in raw["results"] if r["model_label"] == "sonnet"
    ]
    kpi_11 = {
        "haiku_avg_chars": int(statistics.mean(haiku_text_lens)) if haiku_text_lens else 0,
        "sonnet_avg_chars": int(statistics.mean(sonnet_text_lens)) if sonnet_text_lens else 0,
        "note": "lex coverage 어휘 다양성 판정은 manual eval (Part 4)",
    }

    # 12. token usage P90/max vs budget 7,000
    token_stats = metrics["token_stats"]
    kpi_12 = {
        "input_p90": token_stats["input"]["p90"],
        "input_max": token_stats["input"]["max"],
        "output_p90": token_stats["output"]["p90"],
        "output_max": token_stats["output"]["max"],
        "budget": token_stats["budget_e3_portfolio"],
        "input_within_budget": token_stats["input"]["max"] <= token_stats["budget_e3_portfolio"],
        "total_max_within_budget": (
            token_stats["input"]["max"] + token_stats["output"]["max"]
        ) <= token_stats["budget_e3_portfolio"],
    }

    # ====================================================================
    # 케이스 A~G 발동 검증 (Slice 6 Part 3 §3.5)
    # ====================================================================
    cases = {
        "A_schema_fail": (10 - schema_count) >= 1,
        "B_completeness_fail": (10 - comp_count) >= 1,
        "C_fallback_ge_1": kpi_basic["fallback"] >= 1,
        "D_single_cost_exceed": not kpi_basic["cost_per_call_pass"],
        "E_total_cost_exceed": not kpi_8,
        "F_label_means_anomaly": False,  # manual eval 필요 (Part 4)
        "G_preset_extrapolation_gt_50": False,  # manual eval 필요 (Part 4)
    }
    auto_cases_triggered = sum(
        1 for k, v in cases.items()
        if k.startswith(("A", "B", "C", "D", "E")) and v
    )

    # ====================================================================
    # 결과 종합
    # ====================================================================
    result = {
        "step": "slice6_part3_step7_5_kpi_verification",
        "kpis_8": kpis_8,
        "kpi_8_pass": kpi_8_pass,
        "auxiliary_kpis_9_to_12": {
            "9_label_means": kpi_9,
            "10_preset_extrapolation": kpi_10,
            "11_lex_coverage": kpi_11,
            "12_token_usage": kpi_12,
        },
        "cases_a_to_g": cases,
        "auto_cases_triggered_a_to_e": auto_cases_triggered,
        "manual_cases_pending_f_g": ["F (label_means)", "G (preset 외삽)"],
        "identical_hash_verification": {
            "slice1_e1": {"baseline": IDENTICAL_BASELINE["slice1_e1"], "actual": slice1_hash, "match": kpi_1},
            "slice3_e2": {"baseline": IDENTICAL_BASELINE["slice3_e2"], "actual": slice3_hash, "match": kpi_2},
        },
    }

    # Markdown 보고서
    md = ["# Slice 6 Part 3 Step 7.5 — KPI 자동 검증 보고서", ""]
    md.append(f"> 실행: 자동 검증 산출\n")

    md.append("## KPI 8/8 (핵심)\n")
    md.append("| # | KPI | 결과 |")
    md.append("|---|---|---|")
    labels = [
        ("1", "Slice 1 e1 IDENTICAL hash", kpi_1),
        ("2", "Slice 3 e2 IDENTICAL hash", kpi_2),
        ("3", f"호출 카운트 11/50 (smoke {smoke_calls} + matrix {cost_guard_status['call_count']} = {total_actual_calls})", kpi_3),
        ("4", f"schema 10/10 (실제 {schema_count}/10)", kpi_4),
        ("5", f"completeness 10/10 (실제 {comp_count}/10)", kpi_5),
        ("6", f"fallback 0건 (실제 {kpi_basic['fallback']})", kpi_6),
        ("7", "단건 비용 PASS (haiku ≤ $0.010, sonnet ≤ $0.030)", kpi_7),
        ("8", f"총 비용 PASS (smoke+matrix ${total_with_smoke:.6f} ≤ $0.150)", kpi_8),
    ]
    for num, label, ok in labels:
        md.append(f"| {num} | {label} | {'✓ PASS' if ok else '✗ FAIL'} |")
    md.append("")
    md.append(f"**KPI 8/8 전체 결과: {'8/8 PASS ✓' if kpi_8_pass else '일부 FAIL'}**\n")

    md.append("## 보조 KPI 9~12\n")
    md.append(f"### 9. label_means (cost/output 기반, manual eval은 Part 4)")
    md.append(f"- haiku avg cost: ${kpi_9['haiku_avg_cost']:.6f}, output {kpi_9['haiku_avg_output_tokens']} tokens")
    md.append(f"- sonnet avg cost: ${kpi_9['sonnet_avg_cost']:.6f}, output {kpi_9['sonnet_avg_output_tokens']} tokens")
    md.append(f"- cost gap (sonnet vs haiku): **+{kpi_9['cost_gap_pct']:.1f}%**\n")

    md.append(f"### 10. preset 외삽 (alignment proxy)")
    md.append(f"- haiku alignment matches: {kpi_10['haiku_alignment_matches']}")
    md.append(f"- sonnet alignment matches: {kpi_10['sonnet_alignment_matches']}")
    if kpi_10["alignment_divergence_cases"]:
        md.append(f"- 분기 cases:")
        for d in kpi_10["alignment_divergence_cases"]:
            md.append(f"  - {d['fixture']}: expected={d['expected']}, haiku={d['haiku_llm']}, sonnet={d['sonnet_llm']}")
    md.append("")

    md.append(f"### 11. lex coverage (chars proxy)")
    md.append(f"- haiku avg chars: {kpi_11['haiku_avg_chars']}")
    md.append(f"- sonnet avg chars: {kpi_11['sonnet_avg_chars']}\n")

    md.append(f"### 12. token usage vs budget {kpi_12['budget']}")
    md.append(f"- input P90/max: {kpi_12['input_p90']} / {kpi_12['input_max']}")
    md.append(f"- output P90/max: {kpi_12['output_p90']} / {kpi_12['output_max']}")
    md.append(f"- input within budget: {kpi_12['input_within_budget']}")
    md.append(f"- input+output_max within budget: {kpi_12['total_max_within_budget']}\n")

    md.append("## 케이스 A~G 발동\n")
    md.append("| 케이스 | 발동 | 처리 |")
    md.append("|---|---|---|")
    md.append(f"| A schema FAIL ≥ 1 | {'✗ 발동' if cases['A_schema_fail'] else '✓ 미발동'} | {'재시도' if cases['A_schema_fail'] else '-'} |")
    md.append(f"| B completeness FAIL ≥ 1 | {'✗ 발동' if cases['B_completeness_fail'] else '✓ 미발동'} | {'prompt 보강' if cases['B_completeness_fail'] else '-'} |")
    md.append(f"| C fallback ≥ 1 | {'✗ 발동' if cases['C_fallback_ge_1'] else '✓ 미발동'} | {'fallback_from 분석' if cases['C_fallback_ge_1'] else '-'} |")
    md.append(f"| D 단건 비용 초과 | {'✗ 발동' if cases['D_single_cost_exceed'] else '✓ 미발동'} | - |")
    md.append(f"| E 총 비용 초과 | {'✗ 발동' if cases['E_total_cost_exceed'] else '✓ 미발동'} | - |")
    md.append(f"| F label_means 비정상 | manual eval (Part 4) | - |")
    md.append(f"| G preset 외삽 > 0.50 | manual eval (Part 4) | - |")
    md.append(f"\n**자동 케이스 A~E: {auto_cases_triggered}/5 발동**\n")

    md.append("## IDENTICAL Hash KPI\n")
    md.append(f"- Slice 1 e1: `{slice1_hash[:16]}…` {'✓ IDENTICAL' if kpi_1 else '✗ FAIL'}")
    md.append(f"- Slice 3 e2: `{slice3_hash[:16]}…` {'✓ IDENTICAL' if kpi_2 else '✗ FAIL'}\n")

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"\n[saved] {REPORT_PATH}")

    # 콘솔 요약
    print(f"\n[KPI 8/8] {'PASS ✓' if kpi_8_pass else 'FAIL'}")
    for num, label, ok in labels:
        status = "✓" if ok else "✗"
        print(f"  {status} {num}. {label}")

    print(f"\n[자동 케이스 A~E] {auto_cases_triggered}/5 발동")
    if auto_cases_triggered:
        for k, v in cases.items():
            if v and k.startswith(("A", "B", "C", "D", "E")):
                print(f"  ✗ {k}")

    print(f"\n[보조 KPI 9~12]")
    print(f"  9. haiku ${kpi_9['haiku_avg_cost']:.6f} / sonnet ${kpi_9['sonnet_avg_cost']:.6f} (gap +{kpi_9['cost_gap_pct']:.1f}%)")
    print(f"  10. alignment haiku={kpi_10['haiku_alignment_matches']} / sonnet={kpi_10['sonnet_alignment_matches']}")
    if kpi_10["alignment_divergence_cases"]:
        print(f"      분기: {[d['fixture'] for d in kpi_10['alignment_divergence_cases']]}")
    print(f"  12. token input max {kpi_12['input_max']} / output max {kpi_12['output_max']} (budget {kpi_12['budget']})")
    return 0 if kpi_8_pass else 1


if __name__ == "__main__":
    sys.exit(main())
