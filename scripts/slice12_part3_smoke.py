"""Slice 12 Part 3 — Smoke matrix 15 케이스 (5 카테고리 × 3 case).

각 fixture (tests/scoring/fixtures/*.json) → e3_service.run_e3_coach 호출:
  - portfolio_a2 fixture를 input_data로 재사용 (Slice 11 Part 4 패턴)
  - fixture의 metrics dict → preset_id + metrics 인자 주입
  - LLM 호출 → E3Output + scores context 반환

측정:
  - schema_fitting (E3Output validate)
  - actual category score / gate_triggered
  - cost, latency, commentary
  - expected vs actual gate 일치 검증

Output:
  - docs/portfolio/coach/slice12/part3_smoke_results.json
  - docs/portfolio/coach/slice12/part3_smoke_dump.md
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")

import django  # noqa: E402

django.setup()

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

FIXTURE_DIR = REPO_ROOT / "tests" / "scoring" / "fixtures"
OUT_JSON = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "part3_smoke_results.json"
OUT_MD = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "part3_smoke_dump.md"

FIXTURE_NAMES = [
    "value_normal", "value_edge", "value_gate",
    "growth_normal", "growth_edge", "growth_gate",
    "income_normal", "income_edge", "income_gate",
    "factor_normal", "factor_edge", "factor_gate",
    "special_normal", "special_edge", "special_gate",
]

SLICE_CAP_HARD = 0.30  # Slice 12 Part 3 단독 cap


def _run_case(fixture_name: str) -> dict:
    """단일 fixture 케이스 실행."""
    from apps.portfolio.services.coach.e3_service import run_e3_coach
    from apps.portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input

    data = json.loads((FIXTURE_DIR / f"{fixture_name}.json").read_text(encoding="utf-8"))

    input_data = load_portfolio_a2_input("e3")  # portfolio_a2 E3 input 재사용

    t0 = time.time()
    try:
        result = run_e3_coach(
            input_data,
            provider="haiku",
            preset_id=data["preset_id"],
            metrics=data["metrics"],
        )
        latency_ms = int((time.time() - t0) * 1000)
        fitting_pass = True
        error = ""
    except Exception as e:  # noqa: BLE001
        latency_ms = int((time.time() - t0) * 1000)
        fitting_pass = False
        error = f"{type(e).__name__}: {str(e)[:300]}"
        result = {}

    scores = result.get("scores", {})
    meta = result.get("llm_metadata", {})
    category_score = scores.get("_category_score", -1.0)

    # Gate 발동 판정:
    # - 카테고리 score가 0.0이면 모든 preset이 gate cut (income/edge or income/gate 케이스)
    # - 또는 카테고리 안 일부 preset만 0.0인 경우 (factor low_volatility)
    preset_scores = [v for k, v in scores.items() if not k.startswith("_")]
    gate_triggered = any(v == 0.0 for v in preset_scores) if preset_scores else False
    expected_gate = data.get("expected_gate_triggered", False)

    commentary = ""
    if result.get("output"):
        summary = result["output"].get("summary", "")
        observations = result["output"].get("key_observations", [])
        commentary = summary + "\n" + "\n".join(f"- {o}" for o in observations)

    return {
        "fixture": fixture_name,
        "category": data["category"],
        "case_type": data["case_type"],
        "preset_id": data["preset_id"],
        "schema_fitting_pass": fitting_pass,
        "fitting_error": error,
        "scores": scores,
        "category_score": category_score,
        "gate_triggered": gate_triggered,
        "expected_gate_triggered": expected_gate,
        "gate_match": gate_triggered == expected_gate,
        "input_tokens": meta.get("input_tokens", 0),
        "output_tokens": meta.get("output_tokens", 0),
        "cost_usd": meta.get("cost_usd", 0.0),
        "latency_ms": latency_ms,
        "provider": meta.get("provider", ""),
        "model": meta.get("model", ""),
        "commentary": commentary,
    }


def main() -> int:
    print("=" * 70)
    print("Slice 12 Part 3 — Smoke matrix 15 case (5 카테고리 × 3 case)")
    print("=" * 70)

    cases: list[dict] = []
    total_cost = 0.0

    for name in FIXTURE_NAMES:
        if total_cost >= SLICE_CAP_HARD:
            print(f"\n[STOP] Slice cap {SLICE_CAP_HARD} 도달, 중단")
            break
        print(f"\n--- {name} ---")
        r = _run_case(name)
        cases.append(r)
        total_cost += r["cost_usd"]
        print(f"  fitting={r['schema_fitting_pass']} score={r['category_score']:.2f} "
              f"gate={r['gate_triggered']}(expected {r['expected_gate_triggered']}) "
              f"match={r['gate_match']}  cost=${r['cost_usd']:.5f}")
        if r["fitting_error"]:
            print(f"  ERR: {r['fitting_error']}")

    fitting_pass_n = sum(1 for c in cases if c["schema_fitting_pass"])
    gate_actual = sum(1 for c in cases if c["gate_triggered"])
    gate_match = sum(1 for c in cases if c["gate_match"])

    summary = {
        "n_cases_executed": len(cases),
        "n_cases_planned": 15,
        "n_fitting_pass": fitting_pass_n,
        "n_gate_triggered_actual": gate_actual,
        "n_gate_expected_match": gate_match,
        "total_cost_usd": round(total_cost, 6),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"summary": summary, "cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_lines = [
        "# Slice 12 Part 3 — Smoke Matrix Dump (15 case)",
        "",
        "## §1. Summary",
        "",
        f"- 케이스 실행: **{summary['n_cases_executed']}/15**",
        f"- schema fitting PASS: **{summary['n_fitting_pass']}/{summary['n_cases_executed']}**",
        f"- gate 발동 actual: **{summary['n_gate_triggered_actual']}**",
        f"- gate expected vs actual 일치: **{summary['n_gate_expected_match']}/{summary['n_cases_executed']}**",
        f"- 총 비용: **${summary['total_cost_usd']:.4f}**",
        "",
        "## §2. 케이스별 결과",
        "",
        "| # | fixture | preset | fit | category_score | gate(actual/expected) | cost | latency | summary 첫 줄 |",
        "| - | ------- | ------ | --- | -------------- | --------------------- | ---- | ------- | ------------- |",
    ]
    for i, c in enumerate(cases, 1):
        comm_head = c["commentary"].split("\n")[0][:60] if c["commentary"] else "-"
        md_lines.append(
            f"| {i} | {c['fixture']} | {c['preset_id']} | "
            f"{'P' if c['schema_fitting_pass'] else 'F'} | "
            f"{c['category_score']:.2f} | {c['gate_triggered']}/{c['expected_gate_triggered']} | "
            f"${c['cost_usd']:.5f} | {c['latency_ms']}ms | {comm_head} |"
        )

    md_lines += ["", "## §3. Gate 발동 케이스 commentary 발췌", ""]
    for c in cases:
        if c["gate_triggered"]:
            md_lines.append(f"### {c['fixture']} ({c['preset_id']})")
            md_lines.append("")
            md_lines.append("```")
            md_lines.append(c["commentary"][:600])
            md_lines.append("```")
            md_lines.append("")

    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"종료: {len(cases)}/15 case, fitting {fitting_pass_n}/{len(cases)}, "
          f"gate match {gate_match}/{len(cases)}, 총 비용 ${total_cost:.4f}")
    print(f"→ {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"→ {OUT_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
