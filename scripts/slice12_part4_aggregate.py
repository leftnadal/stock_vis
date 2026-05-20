"""Slice 12 Part 4 Step 3 — 집계 + unmask + 가설 검증.

Input:
  - part4_blind_eval_input.json  (A/B 랜덤화 input)
  - part4_blind_eval_truth.json  (A=haiku|sonnet truth)
  - part4_blind_eval_output.json (병진 평가)
  - part3_smoke_results.json     (haiku cost/latency)
  - part4_sonnet_results.json    (sonnet cost/latency)

Output:
  - docs/portfolio/coach/slice12/part4_aggregate.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
S12 = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12"

INPUT = S12 / "part4_blind_eval_input.json"
TRUTH = S12 / "part4_blind_eval_truth.json"
OUTPUT = S12 / "part4_blind_eval_output.json"
HAIKU_RESULTS = S12 / "part3_smoke_results.json"
SONNET_RESULTS = S12 / "part4_sonnet_results.json"
REPORT = S12 / "part4_aggregate.json"


def aggregate() -> dict:
    input_data = json.loads(INPUT.read_text(encoding="utf-8"))
    truth_data = json.loads(TRUTH.read_text(encoding="utf-8"))
    output_data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    haiku_data = json.loads(HAIKU_RESULTS.read_text(encoding="utf-8"))
    sonnet_data = json.loads(SONNET_RESULTS.read_text(encoding="utf-8"))

    input_cases = {c["fixture"]: c for c in input_data["cases"]}
    truth_map = {t["fixture"]: t for t in truth_data["truth"]}
    eval_map = {e["fixture"]: e for e in output_data["evaluations"]}
    haiku_map = {c["fixture"]: c for c in haiku_data["cases"]}
    sonnet_map = {c["fixture"]: c for c in sonnet_data["cases"]}

    # ============================================================
    # Unmask: A/B → haiku/sonnet 매핑
    # ============================================================
    rows = []
    for fixture in sorted(truth_map.keys()):
        t = truth_map[fixture]
        e = eval_map.get(fixture, {})
        ic = input_cases[fixture]

        if t["model_a"] == "haiku":
            haiku_nat, sonnet_nat = e.get("nat_a"), e.get("nat_b")
            haiku_ins, sonnet_ins = e.get("ins_a"), e.get("ins_b")
            haiku_gc, sonnet_gc = e.get("gc_a"), e.get("gc_b")
        else:
            haiku_nat, sonnet_nat = e.get("nat_b"), e.get("nat_a")
            haiku_ins, sonnet_ins = e.get("ins_b"), e.get("ins_a")
            haiku_gc, sonnet_gc = e.get("gc_b"), e.get("gc_a")

        rows.append({
            "fixture": fixture,
            "case_type": ic["case_type"],
            "is_gate_case": ic["is_gate_case"],
            "haiku": {"nat": haiku_nat, "ins": haiku_ins, "gc": haiku_gc},
            "sonnet": {"nat": sonnet_nat, "ins": sonnet_ins, "gc": sonnet_gc},
        })

    # ============================================================
    # 모델별 평균
    # ============================================================
    haiku_nat_all = [r["haiku"]["nat"] for r in rows if r["haiku"]["nat"] is not None]
    haiku_ins_all = [r["haiku"]["ins"] for r in rows if r["haiku"]["ins"] is not None]
    sonnet_nat_all = [r["sonnet"]["nat"] for r in rows if r["sonnet"]["nat"] is not None]
    sonnet_ins_all = [r["sonnet"]["ins"] for r in rows if r["sonnet"]["ins"] is not None]

    # gc — (B) 30건 모두 (사용자 평가 전체) + (A) gate 2건만 부가
    haiku_gc_all = [r["haiku"]["gc"] for r in rows if r["haiku"]["gc"] is not None]
    sonnet_gc_all = [r["sonnet"]["gc"] for r in rows if r["sonnet"]["gc"] is not None]
    haiku_gc_gate_only = [r["haiku"]["gc"] for r in rows if r["is_gate_case"] and r["haiku"]["gc"] is not None]
    sonnet_gc_gate_only = [r["sonnet"]["gc"] for r in rows if r["is_gate_case"] and r["sonnet"]["gc"] is not None]

    haiku_means = {
        "nat": mean(haiku_nat_all),
        "ins": mean(haiku_ins_all),
        "gc_all": mean(haiku_gc_all),
        "gc_gate_only": mean(haiku_gc_gate_only) if haiku_gc_gate_only else None,
    }
    sonnet_means = {
        "nat": mean(sonnet_nat_all),
        "ins": mean(sonnet_ins_all),
        "gc_all": mean(sonnet_gc_all),
        "gc_gate_only": mean(sonnet_gc_gate_only) if sonnet_gc_gate_only else None,
    }

    # ============================================================
    # Case별 winner
    # ============================================================
    haiku_wins_nat = sum(1 for r in rows if r["haiku"]["nat"] > r["sonnet"]["nat"])
    sonnet_wins_nat = sum(1 for r in rows if r["sonnet"]["nat"] > r["haiku"]["nat"])
    nat_tie = sum(1 for r in rows if r["haiku"]["nat"] == r["sonnet"]["nat"])

    haiku_wins_ins = sum(1 for r in rows if r["haiku"]["ins"] > r["sonnet"]["ins"])
    sonnet_wins_ins = sum(1 for r in rows if r["sonnet"]["ins"] > r["haiku"]["ins"])
    ins_tie = sum(1 for r in rows if r["haiku"]["ins"] == r["sonnet"]["ins"])

    haiku_combined_wins = sum(
        1 for r in rows
        if (r["haiku"]["nat"] + r["haiku"]["ins"]) > (r["sonnet"]["nat"] + r["sonnet"]["ins"])
    )
    sonnet_combined_wins = sum(
        1 for r in rows
        if (r["sonnet"]["nat"] + r["sonnet"]["ins"]) > (r["haiku"]["nat"] + r["haiku"]["ins"])
    )
    combined_tie = len(rows) - haiku_combined_wins - sonnet_combined_wins

    # ============================================================
    # Cost / latency / efficiency
    # ============================================================
    haiku_cost = sum(haiku_map[f]["cost_usd"] for f in truth_map)
    sonnet_cost = sum(sonnet_map[f]["cost_usd"] for f in truth_map)
    haiku_lat = mean(haiku_map[f]["latency_ms"] for f in truth_map)
    sonnet_lat = mean(sonnet_map[f]["latency_ms"] for f in truth_map)

    haiku_quality = haiku_means["nat"] + haiku_means["ins"]
    sonnet_quality = sonnet_means["nat"] + sonnet_means["ins"]
    haiku_eff = haiku_quality / haiku_cost if haiku_cost > 0 else 0
    sonnet_eff = sonnet_quality / sonnet_cost if sonnet_cost > 0 else 0
    eff_gap_pct = ((haiku_eff - sonnet_eff) / sonnet_eff * 100) if sonnet_eff > 0 else 0

    # ============================================================
    # 분포 폭 (#26 재발 검증)
    # ============================================================
    nat_combined = haiku_nat_all + sonnet_nat_all
    ins_combined = haiku_ins_all + sonnet_ins_all
    nat_width = max(nat_combined) - min(nat_combined)
    ins_width = max(ins_combined) - min(ins_combined)
    width_26_status = "PASS" if (nat_width >= 3 and ins_width >= 3) else "RE_REGRESSION"

    # ============================================================
    # 가설 검증
    # ============================================================
    # 글쓰기 가설 8/8 정착:
    #   - haiku_combined_wins >= 8 (15 중 과반)
    #   - 또는 haiku_nat_wins >= 9 (압도)
    if haiku_combined_wins >= 8 or haiku_wins_nat >= 9:
        hypothesis_8th = "haiku"
        hypothesis_status = "8/8 정착"
    elif sonnet_combined_wins >= 8 or sonnet_wins_nat >= 9:
        hypothesis_8th = "sonnet"
        hypothesis_status = "7/8 (S12 반례)"
    else:
        hypothesis_8th = "tie"
        # tie인 경우 평균 비교
        if haiku_quality > sonnet_quality:
            hypothesis_8th = "haiku"
            hypothesis_status = "8/8 정착 (평균 우위)"
        elif sonnet_quality > haiku_quality:
            hypothesis_8th = "sonnet"
            hypothesis_status = "7/8 (S12 반례, 평균)"
        else:
            hypothesis_status = "동률 (8/8 정착 보류)"

    # #60 활성화: haiku gc 평균 (전체 30건 또는 gate 2건)
    gate_60_all = "active" if haiku_means["gc_all"] <= 3.0 else "hold"
    gate_60_gate_only = (
        "active" if (haiku_means["gc_gate_only"] is not None and haiku_means["gc_gate_only"] <= 3.0)
        else "hold"
    )

    report = {
        "rows": rows,
        "haiku_means": haiku_means,
        "sonnet_means": sonnet_means,
        "delta": {
            "nat": haiku_means["nat"] - sonnet_means["nat"],
            "ins": haiku_means["ins"] - sonnet_means["ins"],
            "gc_all": haiku_means["gc_all"] - sonnet_means["gc_all"],
        },
        "case_wins": {
            "haiku_nat_wins": haiku_wins_nat,
            "sonnet_nat_wins": sonnet_wins_nat,
            "nat_tie": nat_tie,
            "haiku_ins_wins": haiku_wins_ins,
            "sonnet_ins_wins": sonnet_wins_ins,
            "ins_tie": ins_tie,
            "haiku_combined_wins": haiku_combined_wins,
            "sonnet_combined_wins": sonnet_combined_wins,
            "combined_tie": combined_tie,
            "total_cases": len(rows),
        },
        "cost": {
            "haiku_total": round(haiku_cost, 6),
            "sonnet_total": round(sonnet_cost, 6),
            "ratio_sonnet_to_haiku": round(sonnet_cost / haiku_cost, 2) if haiku_cost > 0 else 0,
        },
        "latency": {
            "haiku_avg_ms": round(haiku_lat, 0),
            "sonnet_avg_ms": round(sonnet_lat, 0),
            "ratio_sonnet_to_haiku": round(sonnet_lat / haiku_lat, 2) if haiku_lat > 0 else 0,
        },
        "efficiency": {
            "haiku_quality_per_dollar": round(haiku_eff, 1),
            "sonnet_quality_per_dollar": round(sonnet_eff, 1),
            "gap_pct": round(eff_gap_pct, 1),
        },
        "writing_hypothesis": {
            "slice_winner": hypothesis_8th,
            "cumulative_status": hypothesis_status,
            "haiku_combined_wins": haiku_combined_wins,
            "threshold": "haiku_combined_wins >= 8 OR haiku_nat_wins >= 9",
        },
        "debt_60_gate_aware_prompt": {
            "decision_all_30": gate_60_all,
            "decision_gate_only_2": gate_60_gate_only,
            "haiku_gc_mean_all": round(haiku_means["gc_all"], 2),
            "haiku_gc_mean_gate_only": (
                round(haiku_means["gc_gate_only"], 2)
                if haiku_means["gc_gate_only"] is not None else None
            ),
            "threshold": "haiku_gc_mean <= 3.0 → active",
        },
        "debt_26_distribution_width": {
            "status": width_26_status,
            "nat_width": nat_width,
            "ins_width": ins_width,
            "threshold": "nat/ins width >= 3 → close 유지",
        },
    }

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _print_report(r: dict) -> None:
    print("=" * 70)
    print("Slice 12 Part 4 Step 3 — Aggregate")
    print("=" * 70)
    print()
    print("== Model means ==")
    print(f"haiku  : nat={r['haiku_means']['nat']:.2f}  ins={r['haiku_means']['ins']:.2f}  "
          f"gc_all={r['haiku_means']['gc_all']:.2f}  gc_gate={r['haiku_means']['gc_gate_only']}")
    print(f"sonnet : nat={r['sonnet_means']['nat']:.2f}  ins={r['sonnet_means']['ins']:.2f}  "
          f"gc_all={r['sonnet_means']['gc_all']:.2f}  gc_gate={r['sonnet_means']['gc_gate_only']}")
    print(f"delta  : nat={r['delta']['nat']:+.2f}  ins={r['delta']['ins']:+.2f}  "
          f"gc_all={r['delta']['gc_all']:+.2f}")
    print()
    print("== Case wins (haiku/sonnet/tie) ==")
    cw = r["case_wins"]
    print(f"  nat      : {cw['haiku_nat_wins']}/{cw['sonnet_nat_wins']}/{cw['nat_tie']}")
    print(f"  ins      : {cw['haiku_ins_wins']}/{cw['sonnet_ins_wins']}/{cw['ins_tie']}")
    print(f"  combined : {cw['haiku_combined_wins']}/{cw['sonnet_combined_wins']}/{cw['combined_tie']}")
    print()
    print(f"== Cost ==")
    print(f"  haiku  ${r['cost']['haiku_total']:.4f}  /  sonnet ${r['cost']['sonnet_total']:.4f}  "
          f"(ratio {r['cost']['ratio_sonnet_to_haiku']}×)")
    print(f"== Latency ==")
    print(f"  haiku {r['latency']['haiku_avg_ms']:.0f}ms  /  sonnet {r['latency']['sonnet_avg_ms']:.0f}ms  "
          f"(ratio {r['latency']['ratio_sonnet_to_haiku']}×)")
    print(f"== Efficiency (quality / cost) ==")
    print(f"  haiku {r['efficiency']['haiku_quality_per_dollar']:.0f}  /  "
          f"sonnet {r['efficiency']['sonnet_quality_per_dollar']:.0f}  "
          f"(gap {r['efficiency']['gap_pct']:+.0f}%)")
    print()
    print("== Writing hypothesis ==")
    wh = r["writing_hypothesis"]
    print(f"  slice winner: {wh['slice_winner']}")
    print(f"  cumulative: {wh['cumulative_status']}")
    print()
    print("== #60 gate-aware prompt ==")
    d60 = r["debt_60_gate_aware_prompt"]
    print(f"  decision (all 30): {d60['decision_all_30']}  (haiku gc mean {d60['haiku_gc_mean_all']})")
    print(f"  decision (gate only 2): {d60['decision_gate_only_2']}  "
          f"(haiku gc mean {d60['haiku_gc_mean_gate_only']})")
    print()
    print("== #26 distribution width ==")
    d26 = r["debt_26_distribution_width"]
    print(f"  status: {d26['status']}  (nat width {d26['nat_width']}, ins width {d26['ins_width']})")
    print()
    print(f"→ {REPORT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    r = aggregate()
    _print_report(r)
    sys.exit(0)
