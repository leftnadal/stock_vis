"""Slice 9 Part 1 #45 — KPI 12개 자동 검증.

Slice 9 #43/E1 KPI 매트릭스 v2:
- core 8 (회귀/IDENTICAL/단건/누적/cap/호출/4판정/winner)
- auxiliary 4 (회귀 9a/9b/trio/분포/estimator)

지시서 §4.2 — 현재 코드베이스 시그니처에 맞춰 적응.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")

import django  # noqa: E402

django.setup()

from apps.portfolio.tests.helpers.regression_classifier import (
    classify_regression,  # noqa: E402
)

PART1_DIR = REPO_ROOT / "docs/portfolio/coach/slice9/part1"
BASELINE_REGRESSION = 476  # Step 0 종결값
CUMULATIVE_BEFORE_PART1 = 2.0483
CAP_PER_SLICE = 1.00
THRESHOLD = 3.00


def _parse_pytest_count(stdout: str) -> int:
    """'X passed in Y.YYs' → X."""
    lines = [ln for ln in stdout.strip().split("\n") if ln.strip()]
    last = lines[-1] if lines else ""
    m = re.search(r"(\d+)\s+passed", last)
    return int(m.group(1)) if m else 0


def main() -> int:
    rationale_path = PART1_DIR / "rationale_records.json"
    if not rationale_path.exists():
        print(f"❌ {rationale_path} 부재. Batch 실행 후 다시 시도.")
        return 1

    rationales = json.loads(rationale_path.read_text())
    batch_logs_path = PART1_DIR / "batch_logs.json"
    batch_logs = json.loads(batch_logs_path.read_text()) if batch_logs_path.exists() else []

    kpis: dict[str, dict] = {}

    # ── Core KPI 8개 ──

    # KPI 1: 회귀 통과
    result = subprocess.run(
        ["pytest", "portfolio/tests", "-q"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    passed = _parse_pytest_count(result.stdout)
    actual_delta = passed - BASELINE_REGRESSION
    kpis["1_regression"] = {
        "value": f"{BASELINE_REGRESSION} → {passed} (+{actual_delta})",
        "pass": passed >= BASELINE_REGRESSION,
    }

    # KPI 2: IDENTICAL hash
    result = subprocess.run(
        ["pytest", "portfolio/tests/test_static_integrity.py", "-v"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    identical_pass = result.stdout.count("PASSED") >= 7
    kpis["2_identical_hash"] = {
        "value": "7/7 PASS" if identical_pass else "FAIL",
        "pass": identical_pass,
    }

    # KPI 3: 단건 cost (Sonnet < $0.10)
    sonnet_violations = sum(1 for r in rationales if r["cost_usd"] > 0.10)
    kpis["3_per_call_cost"] = {
        "value": f"violations={sonnet_violations}/{len(rationales)}",
        "pass": sonnet_violations == 0,
    }

    # KPI 4: 누적 cost
    total_part1_cost = sum(r["cost_usd"] for r in rationales)
    cumulative = CUMULATIVE_BEFORE_PART1 + total_part1_cost
    kpis["4_cumulative_cost"] = {
        "value": f"${cumulative:.4f} (threshold ${THRESHOLD})",
        "pass": cumulative <= THRESHOLD,
    }

    # KPI 5: 슬라이스 cap (Slice 9 #43 신규)
    slice_usd = total_part1_cost
    kpis["5_slice_cap"] = {
        "value": f"${slice_usd:.4f} / ${CAP_PER_SLICE} ({slice_usd*100:.1f}%)",
        "pass": slice_usd <= CAP_PER_SLICE,
    }

    # KPI 6: LLM 호출
    call_count = len(rationales)
    kpis["6_llm_calls"] = {
        "value": f"{call_count}/100",
        "pass": call_count <= 100,
    }

    # KPI 7: 4판정 PASS 비율 (rationale 자체)
    pass_count = sum(
        1
        for r in rationales
        if r["cost_usd"] <= 0.10
        and len(r["rationale_text"]) >= 100
        and 0 <= r["rationale_score"] <= 5
    )
    kpis["7_4판정_ratio"] = {
        "value": f"{pass_count}/{len(rationales)}",
        "pass": pass_count >= int(len(rationales) * 0.90),
    }

    # KPI 8: winner (Part 4 manual eval 후 확정)
    kpis["8_winner_hypothesis"] = {
        "value": "Part 4 manual eval 후 확정 (잠정 Haiku 6/6)",
        "pass": None,
    }

    # ── Auxiliary KPI 4개 ──

    # KPI 9a/9b: E1 분류 룰 적용
    part1_changed_paths = [
        "portfolio/schemas/rationale.py",
        "portfolio/prompts/rationale/builder.py",
        "portfolio/tests/helpers/matrix_loader.py",
        "portfolio/tests/slice9/test_rationale_schema.py",
        "portfolio/tests/slice9/test_rationale_builder.py",
        "portfolio/tests/slice9/test_verify_part1_kpi.py",
        "scripts/slice9/run_part1_rationale_batch.py",
        "scripts/slice9/verify_part1_kpi.py",
    ]
    classification = classify_regression(part1_changed_paths)

    cost_predicted = 9  # schema 4 + builder 2 + kpi 4 - 1 boundary
    if classification in ("cost", "mixed"):
        deviation = (
            abs(actual_delta - cost_predicted) / cost_predicted if cost_predicted else 1.0
        )
        kpis["9a_cost_regression"] = {
            "value": (
                f"classification={classification}, predicted={cost_predicted}, "
                f"actual={actual_delta}, dev={deviation*100:.1f}%"
            ),
            "pass": deviation <= 0.30,
        }
        kpis["9b_no_cost_regression"] = {
            "value": "Part 1은 cost 분류, N/A",
            "pass": None,
        }
    else:
        deviation = (
            abs(actual_delta - cost_predicted) / cost_predicted if cost_predicted else 1.0
        )
        kpis["9a_cost_regression"] = {
            "value": f"classification={classification}, N/A",
            "pass": None,
        }
        kpis["9b_no_cost_regression"] = {
            "value": f"predicted={cost_predicted}, actual={actual_delta}, dev={deviation*100:.1f}%",
            "pass": deviation <= 0.50,
        }

    # KPI 10: trio 진단 효과 (Slice 8 #29 재측정)
    insufficient = sum(1 for r in rationales if r["original_specificity_score"] <= 2)
    ratio = insufficient / len(rationales) if rationales else 0
    kpis["10_trio_diagnosis_effect"] = {
        "value": f"{insufficient}/{len(rationales)} ({ratio*100:.1f}%)",
        "pass": ratio < 0.30,
    }

    # KPI 11: 분포 폭 (#26)
    rationale_scores = [r["rationale_score"] for r in rationales]
    width = (max(rationale_scores) - min(rationale_scores)) if rationale_scores else 0
    kpis["11_distribution_width"] = {
        "value": f"width={width}",
        "pass": width >= 3,
    }

    # KPI 12: #β2 estimator 2차 측정
    deltas: list[float] = []
    for r in rationales:
        est = r.get("estimated_input_tokens", 0)
        actual = r.get("input_tokens", 0)
        if est and actual:
            deltas.append(abs(actual - est) / actual)
    max_delta = max(deltas) if deltas else 0
    kpis["12_beta2_estimator"] = {
        "value": f"max delta {max_delta*100:.2f}% (n={len(deltas)})",
        "pass": max_delta <= 0.30,
    }

    # 출력
    print("=" * 70)
    print("Slice 9 Part 1 — KPI 12개 자동 검증")
    print("=" * 70)
    all_pass = True
    for kpi_id, data in kpis.items():
        if data["pass"] is True:
            verdict = "✓ PASS"
        elif data["pass"] is False:
            verdict = "✗ FAIL"
            all_pass = False
        else:
            verdict = "⊘ N/A"
        print(f"{kpi_id}: {data['value']} → {verdict}")
    print("=" * 70)
    print(f"전체 판정: {'✓ ALL PASS' if all_pass else '⊘ FAIL/N/A 존재'}")

    out = PART1_DIR / "kpi_verification.json"
    out.write_text(json.dumps(kpis, ensure_ascii=False, indent=2))
    print(f"→ {out.relative_to(REPO_ROOT)}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
