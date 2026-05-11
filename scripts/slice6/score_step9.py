"""Slice 6 Part 4 Step 9.3 — Manual eval 결과 파싱 + 자동 분기 처리.

step9_2_eval_filled.md → step9_3_scored.json + step9_3_report.md

- naturalness/insight 평점 추출
- blind 해제 (eval_key.json 매핑)
- efficiency 계산 (label_mean / cost) — Slice 1·3·4·5 일관
- winner 판정 (haiku vs sonnet, efficiency 우위)
- 글쓰기 가설 5/5 정착 검증 (S1·S3·S4·S5·S6 모두 haiku winner)
- G6 자동 분기 (V4 vs V5)
- preset 외삽 robustness (haiku insight 그룹차 vs Slice 5 0.50 baseline)

Usage:
    python -m scripts.slice6.score_step9
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from scripts.validation._setup import init_django

init_django()


FILLED_PATH = Path("docs/portfolio/coach/slice6/step9_2_eval_filled.md")
KEY_PATH = Path("docs/portfolio/coach/slice6/step9_1_eval_key.json")
RAW_PATH = Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json")
SCORED_PATH = Path("docs/portfolio/coach/slice6/step9_3_scored.json")
REPORT_PATH = Path("docs/portfolio/coach/slice6/step9_3_report.md")


EVAL_BLOCK = re.compile(
    r"##\s*Eval\s*#(\d+).*?"
    r"naturalness:\s*\[\s*(\d+(?:\.\d+)?)\s*\].*?"
    r"insight:\s*\[\s*(\d+(?:\.\d+)?)\s*\]",
    re.DOTALL,
)


def parse_eval_form(text: str) -> dict[str, dict[str, float]]:
    """eval_form 파싱 → {eval_id: {naturalness, insight}}"""
    results: dict[str, dict[str, float]] = {}
    for m in EVAL_BLOCK.finditer(text):
        eid = m.group(1)
        nat = float(m.group(2))
        ins = float(m.group(3))
        if not (1 <= nat <= 5):
            raise ValueError(f"naturalness out of range at eval #{eid}: {nat}")
        if not (1 <= ins <= 5):
            raise ValueError(f"insight out of range at eval #{eid}: {ins}")
        results[eid] = {"naturalness": nat, "insight": ins}
    return results


def load_costs(raw_path: Path) -> dict[int, float]:
    """raw.json results[i].metadata.cost_usd → {orig_idx: cost}"""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    return {
        i: (r.get("metadata") or {}).get("cost_usd", 0.0)
        for i, r in enumerate(raw["results"])
    }


def main() -> int:
    if not FILLED_PATH.exists():
        print(f"[ERROR] {FILLED_PATH} 미존재. Step 9.2 (사용자 평가) 완료 필요.")
        return 1

    filled_text = FILLED_PATH.read_text(encoding="utf-8")
    key_map = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    costs = load_costs(RAW_PATH)

    parsed = parse_eval_form(filled_text)
    if len(parsed) != 10:
        raise AssertionError(f"expected 10 evals, got {len(parsed)}: {list(parsed.keys())}")

    # blind 해제 + 비용 결합
    entries: list[dict] = []
    for eid, scores in parsed.items():
        meta = key_map[eid]
        orig_idx = meta["original_idx"]
        provider = meta["provider"]            # haiku / sonnet
        preset_id = meta["preset_id"]
        v_label = meta["v_label"]              # V1~V5
        cost = costs[orig_idx]
        label_mean = (scores["naturalness"] + scores["insight"]) / 2
        efficiency = label_mean / cost if cost > 0 else 0.0
        entries.append({
            "eval_id": int(eid),
            "original_idx": orig_idx,
            "provider": provider,
            "preset_id": preset_id,
            "v_label": v_label,
            "fixture": meta["fixture"],
            "expected_alignment": meta["expected_alignment"],
            "naturalness": scores["naturalness"],
            "insight": scores["insight"],
            "label_mean": round(label_mean, 4),
            "cost_usd": round(cost, 6),
            "efficiency": round(efficiency, 2),
        })

    # provider별 집계
    by_provider: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_provider[e["provider"]].append(e)

    provider_stats: dict[str, dict] = {}
    for prov, es in by_provider.items():
        label_means = [e["label_mean"] for e in es]
        costs_list = [e["cost_usd"] for e in es]
        effs = [e["efficiency"] for e in es]
        provider_stats[prov] = {
            "n": len(es),
            "label_mean_avg": round(sum(label_means) / len(label_means), 4),
            "cost_avg": round(sum(costs_list) / len(costs_list), 6),
            "efficiency_avg": round(sum(effs) / len(effs), 2),
            "naturalness_avg": round(sum(e["naturalness"] for e in es) / len(es), 4),
            "insight_avg": round(sum(e["insight"] for e in es) / len(es), 4),
        }

    # winner 판정 (efficiency 우위)
    haiku_eff = provider_stats.get("haiku", {}).get("efficiency_avg", 0.0)
    sonnet_eff = provider_stats.get("sonnet", {}).get("efficiency_avg", 0.0)
    winner = "haiku" if haiku_eff > sonnet_eff else "sonnet"
    if sonnet_eff > 0 and haiku_eff > 0:
        eff_gap_pct = round((haiku_eff - sonnet_eff) / sonnet_eff * 100, 2)
    else:
        eff_gap_pct = None

    # 글쓰기 가설 5/5 정착 검증
    # S1 E1 / S3 E2 / S4 E6 / S5 E3 모두 haiku winner. S6 e3_portfolio도 haiku면 5/5 정착.
    hypothesis_5_of_5 = winner == "haiku"

    # G6 자동 분기 (V4 vs V5)
    v4_label = [e["label_mean"] for e in entries if e["v_label"] == "V4"]
    v5_label = [e["label_mean"] for e in entries if e["v_label"] == "V5"]
    v4_avg = sum(v4_label) / len(v4_label) if v4_label else None
    v5_avg = sum(v5_label) / len(v5_label) if v5_label else None

    if v4_avg is not None and v5_avg is not None:
        if v4_avg >= v5_avg:
            g6_resolution = "fixture_update"
            g6_action = (
                f"V4 label_mean {v4_avg:.4f} ≥ V5 {v5_avg:.4f} → "
                f"LLM partial 평가가 합리적. V4 fixture expected_alignment "
                f"aligned → partial 수정."
            )
            g6_debt_delta = -1
        else:
            g6_resolution = "fixture_keep_with_debt"
            g6_action = (
                f"V4 label_mean {v4_avg:.4f} < V5 {v5_avg:.4f} → "
                f"Buffett 스타일 차별성 약함. fixture 유지 + prompt 튜닝 "
                f"신규 부채 #23 등록 (PS 2.0)."
            )
            g6_debt_delta = +1
    else:
        g6_resolution = "indeterminate"
        g6_action = "V4 or V5 entries 누락. eval_form 재확인 필요."
        g6_debt_delta = 0

    # preset 외삽 robustness (haiku, Slice 5 비교)
    haiku_entries = by_provider.get("haiku", [])
    haiku_by_preset: dict[str, list[float]] = defaultdict(list)
    for e in haiku_entries:
        haiku_by_preset[e["v_label"]].append(e["insight"])
    haiku_insight_means = {p: sum(v) / len(v) for p, v in haiku_by_preset.items()}
    if haiku_insight_means:
        max_i = max(haiku_insight_means.values())
        min_i = min(haiku_insight_means.values())
        haiku_insight_gap = round(max_i - min_i, 4)
    else:
        haiku_insight_gap = None
    robust_safe = haiku_insight_gap is not None and haiku_insight_gap <= 0.50

    # 결과 저장
    result = {
        "step": "slice6_part4_step9_3_scored",
        "entries": entries,
        "provider_stats": provider_stats,
        "winner": winner,
        "winner_efficiency_gap_pct": eff_gap_pct,
        "writing_hypothesis_5_of_5": hypothesis_5_of_5,
        "g6_resolution": g6_resolution,
        "g6_action": g6_action,
        "g6_debt_delta": g6_debt_delta,
        "g6_v4_label_mean": round(v4_avg, 4) if v4_avg is not None else None,
        "g6_v5_label_mean": round(v5_avg, 4) if v5_avg is not None else None,
        "preset_extrapolation_haiku_insight_gap": haiku_insight_gap,
        "preset_extrapolation_safe": robust_safe,
        "preset_extrapolation_slice5_baseline": 0.50,
        "haiku_insight_means_by_v": haiku_insight_means,
    }
    SCORED_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 리포트
    md = [
        "# Slice 6 Part 4 Step 9.3 — Manual Eval 결과 보고",
        "",
        "## Provider 집계",
        "",
        "| provider | n | label_mean | cost_avg | efficiency | naturalness | insight |",
        "|---|---|---|---|---|---|---|",
    ]
    for prov, st in provider_stats.items():
        md.append(
            f"| {prov} | {st['n']} | {st['label_mean_avg']} | ${st['cost_avg']} | "
            f"{st['efficiency_avg']} | {st['naturalness_avg']} | {st['insight_avg']} |"
        )

    md.extend([
        "",
        "## Winner 판정",
        "",
        f"- **winner**: **{winner}** (efficiency gap = {eff_gap_pct}%)",
        f"- **글쓰기 가설 5/5 정착**: {'PASS ✓' if hypothesis_5_of_5 else 'FAIL ✗ (H2 분기, sonnet winner)'}",
        "",
        "## G6 (V4 alignment) 자동 분기",
        "",
        f"- **resolution**: **{g6_resolution}**",
        f"- action: {g6_action}",
        f"- 부채 변화량: {g6_debt_delta:+d}",
        f"- V4 label_mean: {result['g6_v4_label_mean']}",
        f"- V5 label_mean: {result['g6_v5_label_mean']}",
        "",
        "## Preset 외삽 robustness (haiku, Slice 5 비교)",
        "",
        f"- haiku insight 그룹차: **{haiku_insight_gap}** (Slice 5 baseline ≤ 0.50)",
        f"- 판정: {'SAFE ✓' if robust_safe else 'WARN ⚠ (H3 분기)'}",
        f"- haiku V별 insight 평균: {haiku_insight_means}",
        "",
        "## 개별 평가 (eval_id 순)",
        "",
        "| eval_id | V | preset | provider | nat | ins | label_mean | cost | efficiency |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for e in sorted(entries, key=lambda x: x["eval_id"]):
        md.append(
            f"| {e['eval_id']} | {e['v_label']} | {e['preset_id']} | {e['provider']} | "
            f"{e['naturalness']} | {e['insight']} | {e['label_mean']} | "
            f"${e['cost_usd']} | {e['efficiency']} |"
        )

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ scored: {SCORED_PATH}")
    print(f"✓ report: {REPORT_PATH}")
    print()
    print(f"  winner:               {winner} (efficiency gap {eff_gap_pct}%)")
    print(f"  hypothesis 5/5:       {hypothesis_5_of_5}")
    print(f"  G6 resolution:        {g6_resolution} (debt delta {g6_debt_delta:+d})")
    print(f"  extrapolation gap:    {haiku_insight_gap} ({'SAFE' if robust_safe else 'WARN'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
