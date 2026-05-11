"""Slice 7 Part 1 Step 0.2: H3 재측정 (rubric 적용 후 gap 검증).

Slice 6 manual eval raw 데이터(step9_2_eval_filled.md)에 manual_eval_rubric.md
기준을 적용한 재평가(step0_2_eval_filled_rubric.md)와 비교하여 H3 분기 진위 검증.

분기 자동 결정:
  - 재측정 결과 haiku insight gap ≤ 0.50 → H3 false alarm → #24 close, Slice 8 Step 0 변경
  - 재측정 결과 haiku insight gap > 0.50 → H3 진짜 신호 → #24 Slice 8 Step 0 유지

사용:
  python scripts/slice7/remeasure_h3_with_rubric.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ORIGINAL_PATH = ROOT / "docs/portfolio/coach/slice6/step9_2_eval_filled.md"
RUBRIC_PATH = ROOT / "docs/portfolio/coach/manual_eval_rubric.md"
KEY_PATH = ROOT / "docs/portfolio/coach/slice6/step9_1_eval_key.json"
RUBRIC_EVAL_PATH = ROOT / "docs/portfolio/coach/slice7/step0_2_eval_filled_rubric.md"
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step0_2_h3_remeasure.json"
REPORT_PATH = ROOT / "docs/portfolio/coach/slice7/step0_2_h3_remeasure_report.md"

# Eval 블록 파서: "## Eval #N (...)" + 이후 어딘가에 "- naturalness: [숫자]" / "- insight: [숫자]"
EVAL_HEADER = re.compile(r"##\s*Eval\s*#(\d+)", re.MULTILINE)
NATURALNESS = re.compile(r"naturalness:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?", re.IGNORECASE)
INSIGHT = re.compile(r"insight:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?", re.IGNORECASE)


def parse_evals(text: str) -> dict[str, dict[str, float]]:
    """Eval 블록별 (naturalness, insight) 추출.

    각 블록은 "## Eval #N"부터 다음 "## Eval #" 또는 문서 끝까지.
    빈 값([   ])은 None으로 기록하지 않고 누락 처리 (점수 미기재 = 평가 안 함).
    """
    results: dict[str, dict[str, float]] = {}
    headers = list(EVAL_HEADER.finditer(text))
    for idx, m in enumerate(headers):
        eid = m.group(1)
        start = m.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
        block = text[start:end]
        nat_m = NATURALNESS.search(block)
        ins_m = INSIGHT.search(block)
        if not nat_m or not ins_m:
            continue
        try:
            nat = float(nat_m.group(1))
            ins = float(ins_m.group(1))
        except (TypeError, ValueError):
            continue
        results[eid] = {"naturalness": nat, "insight": ins}
    return results


def stats(parsed: dict[str, dict[str, float]], key_map: dict, label: str) -> dict:
    """provider=haiku 필터로 preset별 insight 평균 + gap + 분포 산출."""
    by_preset: dict[str, list[float]] = defaultdict(list)
    distribution: dict[int, int] = defaultdict(int)
    for eid, scores in parsed.items():
        meta = key_map.get(eid)
        if meta is None:
            continue
        # provider 값은 step9_1_eval_key.json에서 "haiku" 또는 "sonnet"
        # (방어적: "anthropic_haiku" 표기도 허용)
        if meta.get("provider") not in {"haiku", "anthropic_haiku"}:
            continue
        by_preset[meta["preset_id"]].append(scores["insight"])
        for v in (scores["naturalness"], scores["insight"]):
            distribution[int(v)] += 1
    insight_means = {p: round(sum(v) / len(v), 4) for p, v in by_preset.items() if v}
    if insight_means:
        gap = round(max(insight_means.values()) - min(insight_means.values()), 4)
    else:
        gap = None
    return {
        "label": label,
        "insight_means_by_preset": insight_means,
        "insight_gap": gap,
        "distribution_1_to_5": dict(sorted(distribution.items())),
        "total_ratings": sum(distribution.values()),
    }


def dist_width(d: dict[int, int]) -> int:
    keys = [int(k) for k, v in d.items() if v > 0]
    return max(keys) - min(keys) if keys else 0


def main() -> int:
    if not ORIGINAL_PATH.exists():
        print(f"✗ {ORIGINAL_PATH} not found")
        return 1
    if not KEY_PATH.exists():
        print(f"✗ {KEY_PATH} not found")
        return 1

    key_map = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    original = parse_evals(ORIGINAL_PATH.read_text(encoding="utf-8"))

    if not RUBRIC_EVAL_PATH.exists():
        print(f"⚠ {RUBRIC_EVAL_PATH} not found — rubric 재평가 미실행")
        print("  → docs/portfolio/coach/slice7/step0_2_eval_form_rubric.md 작성 후 재실행")
        return 2

    rubric = parse_evals(RUBRIC_EVAL_PATH.read_text(encoding="utf-8"))

    s_orig = stats(original, key_map, "original")
    s_rub = stats(rubric, key_map, "rubric")

    BASELINE = 0.50
    orig_gap = s_orig["insight_gap"]
    rub_gap = s_rub["insight_gap"]

    if rub_gap is None:
        verdict = "indeterminate"
        action = "rubric 재평가 누락 — 재실행 필요"
        h3_status = "unresolved"
    elif rub_gap <= BASELINE:
        verdict = "h3_false_alarm"
        action = (
            f"rubric 재측정 gap {rub_gap} ≤ {BASELINE} → H3는 측정 도구 noise. "
            f"#24(preset 외삽 일반화 PS 2.5) close. Slice 8 Step 0 변경 필요."
        )
        h3_status = "closed_false_alarm"
    else:
        verdict = "h3_confirmed"
        action = (
            f"rubric 재측정 gap {rub_gap} > {BASELINE} → H3 진짜 신호. "
            f"#24(preset 외삽 일반화 PS 2.5) Slice 8 Step 0 유지."
        )
        h3_status = "confirmed_keep"

    orig_width = dist_width(s_orig["distribution_1_to_5"])
    rub_width = dist_width(s_rub["distribution_1_to_5"])
    rubric_effect = rub_width > orig_width

    result = {
        "original": s_orig,
        "rubric": s_rub,
        "baseline": BASELINE,
        "verdict": verdict,
        "action": action,
        "h3_status": h3_status,
        "distribution_width_original": orig_width,
        "distribution_width_rubric": rub_width,
        "rubric_widened_distribution": rubric_effect,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 1 Step 0.2 — H3 재측정 보고",
        "",
        "## 비교",
        "",
        "| 항목 | 기존 (rubric 없음) | 신규 (rubric 적용) |",
        "|---|---|---|",
        f"| haiku insight gap | {orig_gap} | {rub_gap} |",
        f"| 분포 폭 (max-min) | {orig_width} | {rub_width} |",
        f"| 총 평점 수 | {s_orig['total_ratings']} | {s_rub['total_ratings']} |",
        "",
        f"## 판정: **{verdict}**",
        "",
        f"- action: {action}",
        f"- H3 상태: {h3_status}",
        f"- rubric 효과 (분포 넓어짐): {rubric_effect}",
        "",
        "## preset별 insight 평균 (haiku only)",
        "",
        "| preset | original | rubric |",
        "|---|---|---|",
    ]
    presets = sorted(set(s_orig["insight_means_by_preset"]) | set(s_rub["insight_means_by_preset"]))
    for p in presets:
        ov = s_orig["insight_means_by_preset"].get(p, "—")
        rv = s_rub["insight_means_by_preset"].get(p, "—")
        md.append(f"| {p} | {ov} | {rv} |")
    REPORT_PATH.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"✓ result: {OUT_PATH}")
    print(f"✓ report: {REPORT_PATH}")
    print(f"  verdict: {verdict}")
    print(f"  gap: orig={orig_gap} → rubric={rub_gap}")
    print(f"  width: orig={orig_width} → rubric={rub_width}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
