"""Slice 7 Part 4 §8: Stage 1 (haiku) 자동 판정.

Stage 1 평가 결과 (step9_5_eval_filled_v7.md)로:
  1. winner 신호 (haiku 단독, 기존 sonnet과 비교는 §10에서)
  2. 분포 폭 KPI (rubric §C.6, ≥ 3.0 필수)
  3. Stage 2 (sonnet) 진행 여부 자동 판정

판정 기준:
  - haiku label_mean ≥ 3.5 + 분포 폭 ≥ 3.0 → skip (winner 명확)
  - haiku label_mean < 3.0                  → proceed (sonnet 검증)
  - 3.0 ~ 3.5 또는 분포 폭 < 3.0           → proceed (안전 확보)

사용:
  poetry run python -m scripts.slice7.score_stage1
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILLED_PATH = ROOT / "docs/portfolio/coach/slice7/step9_5_eval_filled_v7.md"
KEY_PATH = ROOT / "docs/portfolio/coach/slice7/step9_4_eval_key_v7.json"
RAW_PATHS = {
    "slice5": ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
    "slice6": ROOT / "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
    "slice7": ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json",
}
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_6_stage1_verdict.json"
REPORT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_6_stage1_report.md"


EVAL_BLOCK = re.compile(
    r"##\s*Eval\s*#(\d+).*?naturalness:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?.*?insight:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?",
    re.DOTALL,
)


def parse_filled(text: str) -> dict[int, dict]:
    """Stage 1 섹션의 Eval # 블록만 파싱 (Stage 2 섹션 무시)."""
    # Stage 2 헤더 이전까지 자른다
    stage2_idx = text.find("# Stage 2")
    if stage2_idx > 0:
        text = text[:stage2_idx]
    results: dict[int, dict] = {}
    for match in EVAL_BLOCK.finditer(text):
        eid = int(match.group(1))
        try:
            nat = float(match.group(2))
            ins = float(match.group(3))
        except ValueError:
            continue
        results[eid] = {"naturalness": nat, "insight": ins}
    return results


def load_costs() -> dict:
    """(source_slice, idx) → cost_usd. slice5/6은 metadata.cost_usd 위치."""
    from scripts.slice7._common import entry_cost, load_raw

    costs: dict = {}
    for slice_name, path in RAW_PATHS.items():
        for i, e in enumerate(load_raw(path)):
            costs[(slice_name, i)] = entry_cost(e)
    return costs


def main() -> int:
    if not FILLED_PATH.exists():
        print(f"⚠ {FILLED_PATH} 미존재 — Stage 1 평가 (Phase C 사용자 작업) 먼저", file=sys.stderr)
        return 1
    if not KEY_PATH.exists():
        print(f"⚠ {KEY_PATH} 미존재 — prepare_manual_eval_v7 먼저", file=sys.stderr)
        return 1

    from portfolio.llm.eval_metrics import distribution_width_kpi

    parsed = parse_filled(FILLED_PATH.read_text(encoding="utf-8"))
    key_map = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    haiku_keys = key_map["haiku_stage1"]
    costs = load_costs()

    haiku_results: list[dict] = []
    all_scores: list[float] = []
    for eid, scores in parsed.items():
        meta = next((k for k in haiku_keys if k["eval_id"] == eid), None)
        if not meta:
            continue
        cost = costs.get((meta["source_slice"], meta["idx"]), 0)
        label_mean = (scores["naturalness"] + scores["insight"]) / 2
        efficiency = label_mean / cost if cost > 0 else 0
        haiku_results.append({
            "eval_id": eid,
            "source_slice": meta["source_slice"],
            "preset_id": meta["preset_id"],
            "tier": meta["tier"],
            "provider": meta["provider"],
            "naturalness": scores["naturalness"],
            "insight": scores["insight"],
            "label_mean": label_mean,
            "cost_usd": cost,
            "efficiency": efficiency,
        })
        all_scores.extend([scores["naturalness"], scores["insight"]])

    kpi = distribution_width_kpi(all_scores)

    label_means = [r["label_mean"] for r in haiku_results]
    avg_label = sum(label_means) / len(label_means) if label_means else 0

    by_slice: dict = {}
    for r in haiku_results:
        by_slice.setdefault(r["source_slice"], []).append(r["label_mean"])
    slice_avg = {s: sum(v) / len(v) for s, v in by_slice.items()}

    width = kpi.get("width", 0) if isinstance(kpi, dict) else 0
    if avg_label >= 3.5 and width >= 3:
        stage2_decision = "skip"
        stage2_reason = f"haiku label_mean {avg_label:.2f} ≥ 3.5 + 분포 폭 {width} ≥ 3"
    elif avg_label < 3.0:
        stage2_decision = "proceed"
        stage2_reason = f"haiku label_mean {avg_label:.2f} < 3.0 → sonnet 위닝 검증"
    else:
        stage2_decision = "proceed"
        stage2_reason = f"haiku label_mean {avg_label:.2f} / 분포 폭 {width} 애매 → 안전 확보"

    verdict = {
        "haiku_results": haiku_results,
        "avg_label_mean": round(avg_label, 4),
        "slice_avg_label_mean": {s: round(v, 4) for s, v in slice_avg.items()},
        "distribution_kpi": kpi,
        "stage2_decision": stage2_decision,
        "stage2_reason": stage2_reason,
        "rubric_c6_pass": bool(kpi.get("pass")) if isinstance(kpi, dict) else False,
    }
    OUT_PATH.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 4 Stage 1 Verdict\n",
        "## 집계",
        f"- haiku entries: {len(haiku_results)}",
        f"- avg label_mean: {avg_label:.4f}",
        f"- 분포 폭 (max-min): {width}",
        f"- 5점 비율: {kpi.get('five_ratio') if isinstance(kpi, dict) else '—'}",
        f"- 1점 사용: {kpi.get('one_count') if isinstance(kpi, dict) else '—'}건",
        f"- rubric §C.6 PASS: {verdict['rubric_c6_pass']}",
        "",
        "## Slice별 haiku label_mean",
    ]
    for s, avg in slice_avg.items():
        md.append(f"- {s}: {avg:.4f}")
    md.extend([
        "",
        "## Stage 2 판정",
        f"- **decision: {stage2_decision}**",
        f"- 사유: {stage2_reason}",
        "",
        "## #26 자연 close",
        f"- 분포 폭 KPI PASS: {verdict['rubric_c6_pass']}",
        f"- close 적격: {verdict['rubric_c6_pass']}",
    ])
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ verdict: {OUT_PATH}")
    print(f"  Stage 2 decision: {stage2_decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
