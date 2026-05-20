"""Slice 12 Part 4 Step 1a — Blind A/B eval input 빌드.

Haiku (Part 3) + Sonnet (Part 4 Step 0) 30 commentary를 case별로 A/B 랜덤 배치.

Output:
  - docs/portfolio/coach/slice12/part4_blind_eval_input.json  (HTML 도구 입력)
  - docs/portfolio/coach/slice12/part4_blind_eval_truth.json  (평가 후 unmask용)

seed=42 고정 (Slice 11 Part 5 D2-A 패턴 재활용).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

HAIKU_RESULTS = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "part3_smoke_results.json"
SONNET_RESULTS = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "part4_sonnet_results.json"
INPUT_OUT = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "part4_blind_eval_input.json"
TRUTH_OUT = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "part4_blind_eval_truth.json"

SEED = 42


def build_eval_input() -> dict:
    """A/B 랜덤화된 30 commentary input + truth dump."""
    haiku_data = json.loads(HAIKU_RESULTS.read_text(encoding="utf-8"))
    sonnet_data = json.loads(SONNET_RESULTS.read_text(encoding="utf-8"))

    haiku_cases = {c["fixture"]: c for c in haiku_data["cases"]}
    sonnet_cases = {c["fixture"]: c for c in sonnet_data["cases"]}

    assert len(haiku_cases) == 15, f"haiku count: {len(haiku_cases)}"
    assert len(sonnet_cases) == 15, f"sonnet count: {len(sonnet_cases)}"
    assert set(haiku_cases) == set(sonnet_cases), "fixture mismatch"

    rng = random.Random(SEED)
    cases = []
    truth = []

    for fixture in sorted(haiku_cases.keys()):
        h = haiku_cases[fixture]
        s = sonnet_cases[fixture]

        if rng.random() < 0.5:
            commentary_a, model_a = h["commentary"], "haiku"
            commentary_b, model_b = s["commentary"], "sonnet"
        else:
            commentary_a, model_a = s["commentary"], "sonnet"
            commentary_b, model_b = h["commentary"], "haiku"

        is_gate = h["case_type"] == "gate" and (h["gate_triggered"] or s["gate_triggered"])
        cases.append({
            "fixture": fixture,
            "category": fixture.split("_")[0],
            "preset_id": h["preset_id"],
            "case_type": h["case_type"],
            "is_gate_case": is_gate,
            "commentary_a": commentary_a,
            "commentary_b": commentary_b,
        })
        truth.append({
            "fixture": fixture,
            "model_a": model_a,
            "model_b": model_b,
        })

    INPUT_OUT.parent.mkdir(parents=True, exist_ok=True)
    INPUT_OUT.write_text(
        json.dumps({"cases": cases, "seed": SEED}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    TRUTH_OUT.write_text(
        json.dumps({"truth": truth, "seed": SEED}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "n_cases": len(cases),
        "n_gate_cases": sum(1 for c in cases if c["is_gate_case"]),
        "haiku_a_count": sum(1 for t in truth if t["model_a"] == "haiku"),
        "sonnet_a_count": sum(1 for t in truth if t["model_a"] == "sonnet"),
    }
    return summary


if __name__ == "__main__":
    s = build_eval_input()
    print(f"Eval input built: {s['n_cases']} cases, "
          f"gate cases {s['n_gate_cases']}, "
          f"A=haiku {s['haiku_a_count']} / A=sonnet {s['sonnet_a_count']}")
    print(f"→ {INPUT_OUT.relative_to(REPO_ROOT)}")
    print(f"→ {TRUTH_OUT.relative_to(REPO_ROOT)} (truth, 평가 후 unmask)")
    sys.exit(0)
