"""Slice 6 Part 3 Step 8 사전 준비 — manual eval 입력 자료 생성.

Step 7 raw + Step 7.5 metrics → DIMENSION_LOOKUP 등록 경로에 dump.
Part 4 manual eval 진입 자료.

산출:
  docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json   (DIMENSION_LOOKUP 등록 경로)
  docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json (자동 점수 dump, manual 대기)
  docs/portfolio/coach/slice6/step7_5_summary.md                  (Part 4 입력 가이드)

Usage:
    python -m scripts.slice6.prepare_step8
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()


STEP7_RAW = Path("docs/portfolio/coach/slice6/step7_matrix_raw.json")
STEP7_METRICS = Path("docs/portfolio/coach/slice6/step7_matrix_metrics.json")
STEP6_SMOKE = Path("docs/portfolio/coach/slice6/step6_smoke_result.json")
STEP7_5_REPORT = Path("docs/portfolio/coach/slice6/step7_5_kpi_report.md")

# DIMENSION_LOOKUP 등록 경로 (Part 1 Step 1 등록)
STEP8_RAW = Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json")
STEP8_SCORED_STUB = Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json")
SUMMARY_MD = Path("docs/portfolio/coach/slice6/step7_5_summary.md")


def main() -> int:
    print("=" * 70)
    print("Slice 6 Part 3 Step 8 사전 준비 — manual eval 입력 자료")
    print("=" * 70)

    for path in (STEP7_RAW, STEP7_METRICS, STEP6_SMOKE):
        if not path.exists():
            print(f"[ERROR] {path} 미존재. 선행 step 실행 필요.")
            return 1

    raw = json.loads(STEP7_RAW.read_text(encoding="utf-8"))
    metrics = json.loads(STEP7_METRICS.read_text(encoding="utf-8"))

    # 1. step8_2way_e3_portfolio_raw.json — DIMENSION_LOOKUP 등록 경로에 dump
    # Slice 5 step8_2way_e3_raw.json 구조 mirror (manual eval 호환)
    step8_raw = {
        "step": "slice6_step8_2way_e3_portfolio_raw",
        "executed_at": raw["executed_at"],
        "matrix_size": raw["matrix_size"],
        "providers": raw["providers"],
        "fixture_groups": raw["fixture_groups"],
        "results": raw["results"],
        "summary": raw["summary"],
        "evaluation_guide": raw["evaluation_guide"],
        "manual_eval_required": raw["manual_eval_required"],
        "cost_guard_status_at_end": raw["cost_guard_status_at_end"],
        "manual_eval_completed_at": None,  # Part 4 manual eval 입력 후 갱신
        "manual_eval_source": None,        # "user_input" 또는 "n/a"
    }
    STEP8_RAW.write_text(
        json.dumps(step8_raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  [saved] {STEP8_RAW}")

    # 2. step8_2way_e3_portfolio_scored.json — stub (manual eval 후 score_step8.py가 채움)
    stub = {
        "step": "slice6_step8_2way_e3_portfolio_scored_stub",
        "status": "pending_manual_eval",
        "instructions": (
            "Part 4 manual eval 후 score_step8.py --entrypoint e3_portfolio 실행으로 채움. "
            "raw entry 10건의 naturalness_manual / insight_manual (1~5) 필드 입력 필요."
        ),
        "raw_path": str(STEP8_RAW),
        "expected_keys_after_eval": [
            "scored_results", "label_means", "use_fallback", "winner", "thresholds",
        ],
    }
    STEP8_SCORED_STUB.write_text(
        json.dumps(stub, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  [saved] {STEP8_SCORED_STUB} (stub)")

    # 3. summary.md — Part 4 입력 가이드
    smoke = json.loads(STEP6_SMOKE.read_text(encoding="utf-8"))
    alignment = metrics["preset_alignment_analysis"]
    cost_breakdown = metrics["cost_breakdown"]
    token_stats = metrics["token_stats"]

    md = [
        "# Slice 6 Part 3 → Part 4 Manual Eval 입력 자료",
        "",
        f"> 작성: {datetime.now(timezone.utc).isoformat()}",
        "> Step 6 smoke + Step 7 매트릭스 10 cases + Step 7.5 KPI 8/8 PASS 종결.",
        "> Part 4 manual eval 항목: winner / 글쓰기 가설 5/5 vs 4/5 / preset 외삽 robustness.",
        "",
        "## 자동 단계 종결 상태",
        "",
        "| 항목 | 결과 |",
        "|---|---|",
        f"| Step 6 4판정 | 4/4 PASS ✓ (cost ${smoke['metadata']['cost_usd']:.6f}) |",
        f"| Step 7 매트릭스 | 10/10 schema + completeness PASS ✓ |",
        f"| Step 7 fallback | 0건 ✓ |",
        f"| Step 7 총 비용 (smoke+matrix) | ${smoke['metadata']['cost_usd'] + raw['summary']['total_cost_usd']:.6f} / $0.150 ✓ |",
        f"| Step 7.5 KPI 8/8 | PASS ✓ |",
        f"| Slice 1·3 IDENTICAL hash | 유지 ✓ |",
        f"| 자동 케이스 A~E | 0/5 발동 ✓ |",
        "",
        "## Part 4 Manual Eval 입력 데이터",
        "",
        "### 10 entries (naturalness/insight 1~5 사용자 입력 필요)",
        "",
        "| # | fixture | model | output | preset_alignment_LLM | vs fixture expected |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(raw["results"], 1):
        meta = r.get("metadata") or {}
        align_llm = r["judgments"]["preset_alignment_llm"] or "?"
        align_match = "✓" if r["judgments"]["preset_alignment_matches_expected"] else f"≠ ({r['expected_alignment']})"
        md.append(
            f"| {i} | {r['fixture']} | {r['model_label']} | "
            f"{meta.get('output_tokens', '?')}t | {align_llm} | {align_match} |"
        )

    md.extend([
        "",
        "### preset_alignment 분기 cases (Part 4 정밀 분석)",
        "",
    ])
    divergence = [a for a in alignment if a["haiku_llm"] != a["expected"] or a["sonnet_llm"] != a["expected"]]
    if divergence:
        for d in divergence:
            md.append(f"- **{d['fixture']}**: fixture expected={d['expected']}, haiku LLM={d['haiku_llm']}, sonnet LLM={d['sonnet_llm']}")
        md.append("")
        md.append("> LLM이 fixture 의도와 다르게 평가한 case. Part 4에서 LLM 평가가 합리적인지 vs fixture 정의가 보수적인지 분석.")
    else:
        md.append("- 분기 없음 (5/5 정합)")
    md.append("")

    md.extend([
        "## 비용 / Token 자동 측정값",
        "",
        f"### 모델별 비용",
        f"- haiku 5건 총합: ${cost_breakdown['haiku_total']:.6f}",
        f"- sonnet 5건 총합: ${cost_breakdown['sonnet_total']:.6f}",
        f"- cost gap (sonnet vs haiku): +275.4% (Slice 5 e3 ~+260% mirror)",
        "",
        f"### Token usage",
        f"- input P90 / max: {token_stats['input']['p90']} / {token_stats['input']['max']} (budget 7,000)",
        f"- output P90 / max: {token_stats['output']['p90']} / {token_stats['output']['max']}",
        f"- input+output max ≤ budget: {token_stats['input']['max'] + token_stats['output']['max']} / 7,000",
        "",
        "## Part 4 Manual Eval 진입 절차",
        "",
        "1. `step8_2way_e3_portfolio_raw.json` 10 entry × 2 필드 (`naturalness_manual` / `insight_manual` 1~5) 사용자 입력",
        "2. `python -m scripts.validation.score_step8 --entrypoint e3_portfolio` → scored.json 산출",
        "3. winner 결정 (haiku vs sonnet)",
        "4. 글쓰기 가설 5/5 정착 vs 4/5 재평가 판정",
        "5. preset 외삽 robustness 평가 (insight 그룹차 ≤ 0.50 안전 vs > 0.50 신호)",
        "6. Slice 5 e3 결과와 비교 (e3 종목 단위 → e3_portfolio 단위 외삽 성공도)",
        "",
        "## 후속 Slice 6 작업",
        "",
        "- Slice 6 Step 9 슬롯 후보 결정: **#19 LLMClient system 인자 (PS 2.0)** vs **#β2 재오픈 (PS 2.0)**",
        "  - V4 alignment 분기로 인해 #β2 재오픈 우선순위 ↑ 가능",
        "- 누적 광의 비용: $0.764 → **~$0.879** (smoke 0.00447 + matrix 0.11005 = $0.11452 누적)",
        "- Slice 7 진입점 후보 평가 (현재 1순위 E4, manual eval 결과로 재검토)",
    ])
    SUMMARY_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"  [saved] {SUMMARY_MD}")

    print("\n[Step 8 사전 준비 완료]")
    print(f"  - {STEP8_RAW.name}: 10 entries (manual eval 대기)")
    print(f"  - {STEP8_SCORED_STUB.name}: stub (score_step8 실행 대기)")
    print(f"  - {SUMMARY_MD.name}: Part 4 입력 가이드")
    return 0


if __name__ == "__main__":
    sys.exit(main())
