"""Slice 7 Part 4 §10: 통합 efficiency winner + Slice 5/6 재판정 + Slice 7 winner.

Stage 1 + Stage 2 (있다면) 데이터로:
  1. 통합 efficiency winner (Slice 1·3·4·5·6 패턴 일관)
  2. Slice 5 재판정 vs 기존 step8 scored 비교
  3. Slice 6 재판정 vs 기존 step8 scored 비교
  4. Slice 7 winner 확정
  5. Tier별 보조 분석 (Slice 7 전용)
  6. 글쓰기 가설 5/5 vs 6/6 판정
  7. Slice 1·3·4 진행 여부 자동 결정

사용:
  poetry run python -m scripts.slice7.score_final
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGE1_PATH = ROOT / "docs/portfolio/coach/slice7/step9_6_stage1_verdict.json"
FILLED_PATH = ROOT / "docs/portfolio/coach/slice7/step9_5_eval_filled_v7.md"
KEY_PATH = ROOT / "docs/portfolio/coach/slice7/step9_4_eval_key_v7.json"
EXISTING_RESULTS = {
    "slice5": ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_scored.json",
    "slice6": ROOT / "docs/portfolio/coach/slice6/step9_3_scored.json",
}
RAW_PATHS = {
    "slice5": ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
    "slice6": ROOT / "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
    "slice7": ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json",
}
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_9_final_verdict.json"
REPORT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_9_final_report.md"


EVAL_BLOCK = re.compile(
    r"##\s*Eval\s*#(\d+).*?naturalness:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?.*?insight:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?",
    re.DOTALL,
)


def parse_section(text: str, section_header: str, next_section_header: str | None) -> dict[int, dict]:
    """특정 Stage 섹션의 Eval # 블록만 파싱."""
    start = text.find(section_header)
    if start < 0:
        return {}
    if next_section_header:
        end = text.find(next_section_header, start + len(section_header))
        if end > 0:
            text = text[start:end]
        else:
            text = text[start:]
    else:
        text = text[start:]
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
    from scripts.slice7._common import entry_cost, load_raw

    costs: dict = {}
    for slice_name, path in RAW_PATHS.items():
        for i, e in enumerate(load_raw(path)):
            costs[(slice_name, i)] = entry_cost(e)
    return costs


def normalize_provider(p: str | None) -> str:
    if not p:
        return "unknown"
    pl = str(p).lower()
    if "haiku" in pl:
        return "haiku"
    if "sonnet" in pl:
        return "sonnet"
    return pl


def determine_winner_by_slice(entries: list[dict]) -> dict:
    by_slice_provider: dict = {}
    for e in entries:
        key = (e["source_slice"], normalize_provider(e.get("provider")))
        by_slice_provider.setdefault(key, []).append(e)
    result: dict = {}
    for (slice_name, provider), es in by_slice_provider.items():
        label_means = [x["label_mean"] for x in es]
        costs = [x["cost_usd"] for x in es]
        avg_label = sum(label_means) / len(label_means) if label_means else 0
        avg_cost = sum(costs) / len(costs) if costs else 0
        efficiency = avg_label / avg_cost if avg_cost else 0
        result.setdefault(slice_name, {})[provider] = {
            "n": len(es),
            "avg_label_mean": round(avg_label, 4),
            "avg_cost": round(avg_cost, 6),
            "efficiency": round(efficiency, 2),
        }
    return result


def main() -> int:
    if not STAGE1_PATH.exists():
        print(f"⚠ {STAGE1_PATH} 미존재 — score_stage1 먼저", file=sys.stderr)
        return 1
    if not FILLED_PATH.exists() or not KEY_PATH.exists():
        print("⚠ eval_filled 또는 eval_key 미존재", file=sys.stderr)
        return 1

    stage1 = json.loads(STAGE1_PATH.read_text(encoding="utf-8"))
    haiku_entries = stage1["haiku_results"]

    key_map = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    sonnet_keys = key_map.get("sonnet_stage2", [])
    costs = load_costs()

    # Stage 2 파싱 (있다면)
    sonnet_entries: list[dict] = []
    if stage1.get("stage2_decision") == "proceed":
        filled_text = FILLED_PATH.read_text(encoding="utf-8")
        stage2_parsed = parse_section(filled_text, "# Stage 2", None)
        for eid, scores in stage2_parsed.items():
            meta = next((k for k in sonnet_keys if k["eval_id"] == eid), None)
            if not meta:
                continue
            cost = costs.get((meta["source_slice"], meta["idx"]), 0)
            label_mean = (scores["naturalness"] + scores["insight"]) / 2
            efficiency = label_mean / cost if cost > 0 else 0
            sonnet_entries.append({
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

    all_entries = haiku_entries + sonnet_entries
    slice_winners = determine_winner_by_slice(all_entries)

    # winner 판정 (Slice별)
    winners_by_slice: dict = {}
    for slice_name, providers in slice_winners.items():
        h = providers.get("haiku")
        s = providers.get("sonnet")
        if h and s:
            winner = "haiku" if h["efficiency"] > s["efficiency"] else "sonnet"
            gap_pct = round((h["efficiency"] - s["efficiency"]) / s["efficiency"] * 100, 2) if s["efficiency"] else None
            winners_by_slice[slice_name] = {
                "winner": winner,
                "haiku_efficiency": h["efficiency"],
                "sonnet_efficiency": s["efficiency"],
                "efficiency_gap_pct": gap_pct,
            }
        elif h and not s:
            winners_by_slice[slice_name] = {
                "winner": "stage1_only_haiku",
                "haiku_efficiency": h["efficiency"],
            }
        elif s and not h:
            winners_by_slice[slice_name] = {
                "winner": "stage2_only_sonnet",
                "sonnet_efficiency": s["efficiency"],
            }

    # 기존 winner 비교
    winner_changes: dict = {}
    for slice_name, existing_path in EXISTING_RESULTS.items():
        if not existing_path.exists():
            continue
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        old_winner = existing.get("winner") or existing.get("winner_label") or "unknown"
        new_winner = winners_by_slice.get(slice_name, {}).get("winner", "unknown")
        winner_changes[slice_name] = {
            "old": old_winner,
            "new": new_winner,
            "changed": old_winner != new_winner,
        }

    # 글쓰기 가설 판정
    s5 = winners_by_slice.get("slice5", {}).get("winner", "unknown")
    s6 = winners_by_slice.get("slice6", {}).get("winner", "unknown")
    s7 = winners_by_slice.get("slice7", {}).get("winner", "unknown")
    haiku_3 = [s5, s6, s7].count("haiku")
    if haiku_3 == 3:
        hypothesis_status = "6_of_6_pending_slice1_3_4_verification"
        slice134_proceed = False
    elif haiku_3 < 3:
        hypothesis_status = "broken_winner_changed"
        slice134_proceed = True
    else:
        hypothesis_status = "indeterminate"
        slice134_proceed = True

    # Tier별 보조 (Slice 7 전용)
    tier_analysis: dict = {}
    s7_entries = [e for e in all_entries if e["source_slice"] == "slice7"]
    for tier in [1, 2, 3]:
        t_entries = [e for e in s7_entries if e.get("tier") == tier]
        if not t_entries:
            continue
        haiku_t = [e for e in t_entries if normalize_provider(e.get("provider")) == "haiku"]
        sonnet_t = [e for e in t_entries if normalize_provider(e.get("provider")) == "sonnet"]
        tier_analysis[f"tier_{tier}"] = {
            "haiku_n": len(haiku_t),
            "haiku_avg_label": round(sum(e["label_mean"] for e in haiku_t) / len(haiku_t), 4) if haiku_t else None,
            "sonnet_n": len(sonnet_t),
            "sonnet_avg_label": round(sum(e["label_mean"] for e in sonnet_t) / len(sonnet_t), 4) if sonnet_t else None,
            "n_total": len(t_entries),
            "weak_signal_warning": len(t_entries) < 6,
        }

    distribution_kpi = stage1.get("distribution_kpi", {})
    rubric_c6_pass = bool(distribution_kpi.get("pass")) if isinstance(distribution_kpi, dict) else False

    final = {
        "stage2_executed": bool(sonnet_entries),
        "winners_by_slice": winners_by_slice,
        "winner_changes": winner_changes,
        "hypothesis_status": hypothesis_status,
        "slice134_recheck_proceed": slice134_proceed,
        "tier_analysis_slice7": tier_analysis,
        "rubric_c6_distribution_pass": rubric_c6_pass,
        "rubric_26_close_action": "close" if rubric_c6_pass else "keep_open",
    }
    OUT_PATH.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# Slice 7 Part 4 Final Verdict\n", "## 통합 Winner"]
    for slice_name, w in winners_by_slice.items():
        md.append(
            f"- {slice_name}: **{w['winner']}** "
            f"(haiku eff {w.get('haiku_efficiency', '—')} / sonnet eff {w.get('sonnet_efficiency', '—')}, "
            f"gap {w.get('efficiency_gap_pct', '—')}%)"
        )

    md.append("\n## Slice 5/6 Winner 변경 분석")
    for slice_name, change in winner_changes.items():
        marker = "⚠ 변경" if change["changed"] else "✓ 유지"
        md.append(f"- {slice_name}: {change['old']} → {change['new']} {marker}")

    md.append("\n## 글쓰기 가설")
    md.append(f"- 상태: **{hypothesis_status}**")
    md.append(f"- Slice 1·3·4 재검토 진행: **{slice134_proceed}**")

    md.append("\n## Tier별 분석 (Slice 7)")
    for tier, t in tier_analysis.items():
        warn = " ⚠ weak signal" if t["weak_signal_warning"] else ""
        md.append(
            f"- {tier} (n={t['n_total']}{warn}): "
            f"haiku label {t.get('haiku_avg_label')} / sonnet label {t.get('sonnet_avg_label')}"
        )

    md.append("\n## #26 자연 close")
    md.append(f"- 분포 폭 KPI PASS: {rubric_c6_pass}")
    md.append(f"- #26 action: **{final['rubric_26_close_action']}**")

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ final verdict: {OUT_PATH}")
    print(f"  hypothesis: {hypothesis_status}")
    print(f"  Slice 1·3·4 proceed: {slice134_proceed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
