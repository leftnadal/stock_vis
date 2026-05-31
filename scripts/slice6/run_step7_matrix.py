"""Slice 6 Part 3 Step 7 — concentrated_portfolio E3 매트릭스 10 cases.

V1~V5 × {haiku, sonnet} = 10 LLM 호출 → raw 응답 수집 → KPI 측정값 dump.
Slice 5 run_step8_e3_2way.py mirror + e3_portfolio reinforced.

산출:
  docs/portfolio/coach/slice6/step7_matrix_raw.json
  docs/portfolio/coach/slice6/step7_matrix_metrics.json
  docs/portfolio/coach/slice6/step7_matrix_report.md

CostGuard 멱등 reset: step 6에서 1콜 누적된 상태에 +10 = 11/50 (마진 39).

Usage:
    python -m scripts.slice6.run_step7_matrix
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
# 멱등 reset — step 6 누적 카운트 보존 (max=50)
reset_for_slice("slice6", max_calls=50)

from apps.portfolio.llm import LLMClient
from apps.portfolio.llm.client import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL
from apps.portfolio.llm.cost_guard import CostGuard
from apps.portfolio.prompts.e3_portfolio import build_e3_portfolio_prompt
from apps.portfolio.services.e3_portfolio_service import (
    parse_e3_portfolio_response,
)
from apps.portfolio.tests.fixtures.sample_e3_portfolio_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
    PRESET_INTENT_MAP,
)

PROVIDERS = [
    {"label": "haiku", "provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    {"label": "sonnet", "provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL},
]


EVALUATION_GUIDE = {
    "naturalness": {
        "5": "한국어 자연스러움 우수, portfolio commentary 톤 매끄러움",
        "4": "자연스러우나 일부 어색 표현",
        "3": "이해 가능하나 약간 기계적",
        "2": "어색 표현 다수",
        "1": "이해 어려움 / 비문법적",
    },
    "insight": {
        "5": "preset 의도 + 분산/섹터/리스크를 비자명한 통찰로 종합, portfolio-level 함의 명확",
        "4": "기본 평가 + 일부 통찰 (preset 맥락 활용)",
        "3": "수치/태그 표면 반복만",
        "2": "단순 나열에 가까움",
        "1": "portfolio 해석 부재",
    },
    "completeness_auto": "schema parse 성공 + 6 필드 모두 비공란 시 자동 True",
}

RAW_PATH = Path("docs/portfolio/coach/slice6/step7_matrix_raw.json")
METRICS_PATH = Path("docs/portfolio/coach/slice6/step7_matrix_metrics.json")
REPORT_PATH = Path("docs/portfolio/coach/slice6/step7_matrix_report.md")

# Slice 6 Part 3 §2.4 / §2.5 단건 비용 임계
COST_THRESHOLDS = {"haiku_per_call": 0.010, "sonnet_per_call": 0.030, "total_max": 0.150}


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def main() -> int:
    print("=" * 70)
    print("Slice 6 Part 3 Step 7 — E3 portfolio 매트릭스 10 cases")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    client = LLMClient()
    results: list[dict] = []
    call_idx = 0

    for fixture_name, getter in ALL_FIXTURES.items():
        fixture = getter()
        holdings_summary = ", ".join(
            f"{h['ticker']}({h['weight']:.0%})" for h in fixture["holdings"]
        )
        prompt = build_e3_portfolio_prompt(
            preset_id=fixture["preset_id"],
            preset_intent=PRESET_INTENT_MAP[fixture["preset_id"]],
            holdings_summary=holdings_summary,
            sector_concentration=fixture["sector_concentration"],
            diversification_score=fixture["diversification_score"],
            risk_concentration_score=fixture["risk_concentration_score"],
            core_metrics_summary=fixture["core_metrics_summary"],
            analysis_context=fixture,
        )

        for prov in PROVIDERS:
            call_idx += 1
            label = prov["label"]
            print(
                f"[{call_idx:>2}/10] {fixture_name:<35} × {label:<7}",
                end=" ",
                flush=True,
            )
            try:
                resp = client.complete(
                    prompt=prompt, provider=prov["provider"], model=prov["model"]
                )
                parsed = None
                schema_pass = False
                schema_error: str | None = None
                parsed_dict = None
                completeness_auto = False
                try:
                    parsed = parse_e3_portfolio_response(resp.text)
                    schema_pass = True
                    parsed_dict = parsed.model_dump()
                    completeness_auto = all(
                        parsed_dict.get(f)
                        for f in (
                            "holistic_assessment",
                            "diversification_comment",
                            "sector_balance_comment",
                            "risk_concentration_comment",
                            "preset_alignment",
                        )
                    ) and 1 <= parsed_dict.get("confidence", 0) <= 5
                except Exception as exc:  # noqa: BLE001
                    schema_error = f"{type(exc).__name__}: {str(exc)[:300]}"

                results.append({
                    "fixture": fixture_name,
                    "fixture_id": fixture["fixture_id"],
                    "fixture_group": fixture["fixture_group"],
                    "preset_id": fixture["preset_id"],
                    "preset_category": fixture["preset_category"],
                    "expected_alignment": fixture["expected_alignment"],
                    "model_label": label,
                    "raw_content": resp.text,
                    "parsed": parsed_dict,
                    "metadata": resp.metadata_dict(),
                    "judgments": {
                        "schema_pass": schema_pass,
                        "schema_error": schema_error,
                        "completeness_auto": completeness_auto,
                        "preset_alignment_llm": parsed_dict.get("preset_alignment") if parsed_dict else None,
                        "preset_alignment_matches_expected": (
                            parsed_dict.get("preset_alignment") == fixture["expected_alignment"]
                            if parsed_dict else False
                        ),
                        "naturalness_manual": None,
                        "insight_manual": None,
                    },
                })
                print(
                    f"OK ({resp.latency_ms}ms, ${resp.cost_usd:.5f}, "
                    f"out={resp.output_tokens}, schema={'OK' if schema_pass else 'FAIL'}, "
                    f"align={parsed_dict.get('preset_alignment') if parsed_dict else '?'})"
                )
            except Exception as exc:  # noqa: BLE001
                results.append({
                    "fixture": fixture_name,
                    "fixture_id": fixture["fixture_id"],
                    "fixture_group": fixture["fixture_group"],
                    "preset_id": fixture["preset_id"],
                    "preset_category": fixture["preset_category"],
                    "expected_alignment": fixture["expected_alignment"],
                    "model_label": label,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                    "metadata": {},
                    "judgments": {
                        "schema_pass": False,
                        "schema_error": str(exc)[:200],
                        "completeness_auto": False,
                        "preset_alignment_llm": None,
                        "preset_alignment_matches_expected": False,
                        "naturalness_manual": None,
                        "insight_manual": None,
                    },
                })
                print(f"ERROR: {type(exc).__name__}: {exc}")

    # 합계
    total_cost = sum((r.get("metadata") or {}).get("cost_usd", 0) or 0 for r in results)
    fallback_count = sum(
        1 for r in results
        if (r.get("metadata") or {}).get("fallback_from") is not None
    )
    schema_pass_count = sum(1 for r in results if r["judgments"]["schema_pass"])
    completeness_count = sum(1 for r in results if r["judgments"]["completeness_auto"])
    latencies = [
        (r.get("metadata") or {}).get("latency_ms", 0)
        for r in results
        if (r.get("metadata") or {}).get("latency_ms")
    ]
    input_tokens_list = [
        (r.get("metadata") or {}).get("input_tokens", 0)
        for r in results
        if (r.get("metadata") or {}).get("input_tokens")
    ]
    output_tokens_list = [
        (r.get("metadata") or {}).get("output_tokens", 0)
        for r in results
        if (r.get("metadata") or {}).get("output_tokens")
    ]
    haiku_costs = [
        (r.get("metadata") or {}).get("cost_usd", 0) for r in results
        if r["model_label"] == "haiku" and (r.get("metadata") or {}).get("cost_usd")
    ]
    sonnet_costs = [
        (r.get("metadata") or {}).get("cost_usd", 0) for r in results
        if r["model_label"] == "sonnet" and (r.get("metadata") or {}).get("cost_usd")
    ]
    max_haiku_cost = max(haiku_costs) if haiku_costs else 0
    max_sonnet_cost = max(sonnet_costs) if sonnet_costs else 0

    # 단건 비용 PASS
    cost_per_call_pass = (
        max_haiku_cost <= COST_THRESHOLDS["haiku_per_call"]
        and max_sonnet_cost <= COST_THRESHOLDS["sonnet_per_call"]
    )
    total_cost_pass = total_cost <= COST_THRESHOLDS["total_max"]

    def _stats(xs: list) -> dict:
        if not xs:
            return {"min": 0, "max": 0, "mean": 0, "p90": 0}
        s = sorted(xs)
        n = len(s)
        return {
            "min": int(s[0]),
            "max": int(s[-1]),
            "mean": int(sum(s) / n),
            "p90": int(s[min(n - 1, int(0.9 * n))]),
        }

    raw_output = {
        "step": "slice6_part3_step7_matrix_raw",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "matrix_size": {
            "fixtures": len(ALL_FIXTURES),
            "models": len(PROVIDERS),
            "total_calls": len(results),
        },
        "providers": [{"label": p["label"], "model": p["model"]} for p in PROVIDERS],
        "fixture_groups": FIXTURE_GROUPS,
        "results": results,
        "summary": {
            "total_calls": len(results),
            "total_cost_usd": round(total_cost, 6),
            "fallback_count": fallback_count,
            "schema_pass_count": schema_pass_count,
            "completeness_auto_count": completeness_count,
            "latency_max_ms": max(latencies) if latencies else 0,
            "latency_p90_ms": sorted(latencies)[int(len(latencies) * 0.9)] if latencies else 0,
        },
        "evaluation_guide": EVALUATION_GUIDE,
        "manual_eval_required": [
            "results[].judgments.naturalness_manual (1~5)",
            "results[].judgments.insight_manual (1~5)",
        ],
        "cost_guard_status_at_end": CostGuard.get_instance().status(),
    }

    # Metrics (자동 측정) — Step 7.5 score_step7_5.py 입력 자료
    metrics_output = {
        "step": "slice6_part3_step7_matrix_metrics",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "kpi_basic": {
            "total_calls": len(results),
            "schema_pass": f"{schema_pass_count}/{len(results)}",
            "completeness_auto": f"{completeness_count}/{len(results)}",
            "fallback": fallback_count,
            "total_cost_usd": round(total_cost, 6),
            "max_haiku_cost": round(max_haiku_cost, 6),
            "max_sonnet_cost": round(max_sonnet_cost, 6),
            "cost_per_call_pass": cost_per_call_pass,
            "total_cost_pass": total_cost_pass,
        },
        "token_stats": {
            "input": _stats(input_tokens_list),
            "output": _stats(output_tokens_list),
            "budget_e3_portfolio": 7_000,
        },
        "latency_stats": _stats(latencies),
        "preset_alignment_analysis": [
            {
                "fixture": r["fixture"],
                "expected": r["expected_alignment"],
                "haiku_llm": next(
                    (x["judgments"]["preset_alignment_llm"] for x in results
                     if x["fixture"] == r["fixture"] and x["model_label"] == "haiku"),
                    None,
                ),
                "sonnet_llm": next(
                    (x["judgments"]["preset_alignment_llm"] for x in results
                     if x["fixture"] == r["fixture"] and x["model_label"] == "sonnet"),
                    None,
                ),
            }
            for r in results
            if r["model_label"] == "haiku"  # 5건만
        ],
        "cost_breakdown": {
            "haiku_total": round(sum(haiku_costs), 6),
            "sonnet_total": round(sum(sonnet_costs), 6),
            "haiku_count": len(haiku_costs),
            "sonnet_count": len(sonnet_costs),
        },
    }

    # 저장
    for path, data in ((RAW_PATH, raw_output), (METRICS_PATH, metrics_output)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded is not None
        print(f"  [saved] {path}")

    # Markdown 보고서
    md_lines = [
        "# Slice 6 Part 3 Step 7 — 매트릭스 10 cases 결과",
        "",
        f"> 실행: {raw_output['executed_at']}",
        f"> 매트릭스: 5 fixture × 2 model = 10 cases",
        "",
        "## 합계",
        "",
        f"- 총 호출: {len(results)}/10",
        f"- schema PASS: {schema_pass_count}/{len(results)}",
        f"- completeness PASS: {completeness_count}/{len(results)}",
        f"- fallback: {fallback_count}",
        f"- 총 비용: ${total_cost:.6f}",
        f"- max haiku cost: ${max_haiku_cost:.6f} / max sonnet cost: ${max_sonnet_cost:.6f}",
        f"- cost_per_call_pass: {'✓' if cost_per_call_pass else '✗'}",
        f"- total_cost_pass: {'✓' if total_cost_pass else '✗'}",
        "",
        "## case별 결과",
        "",
        "| # | fixture | model | schema | comp | output_tokens | cost | latency | preset_alignment LLM | vs expected |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        meta = r.get("metadata") or {}
        align = r["judgments"]["preset_alignment_llm"] or "?"
        match = r["judgments"]["preset_alignment_matches_expected"]
        match_str = "✓" if match else f"≠ ({r['expected_alignment']})"
        schema_str = "✓" if r["judgments"]["schema_pass"] else "✗"
        comp_str = "✓" if r["judgments"]["completeness_auto"] else "✗"
        md_lines.append(
            f"| {i} | {r['fixture']} | {r['model_label']} | "
            f"{schema_str} | {comp_str} | "
            f"{meta.get('output_tokens', '?')} | "
            f"${meta.get('cost_usd', 0):.5f} | "
            f"{meta.get('latency_ms', '?')}ms | "
            f"{align} | {match_str} |"
        )

    md_lines.extend([
        "",
        "## CostGuard",
        "",
        f"- call_count: {raw_output['cost_guard_status_at_end']['call_count']}/{raw_output['cost_guard_status_at_end']['max_calls']}",
        f"- 마진: {raw_output['cost_guard_status_at_end']['remaining']}",
        f"- 누적 비용: ${raw_output['cost_guard_status_at_end']['total_cost_usd']:.6f}",
    ])
    REPORT_PATH.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  [saved] {REPORT_PATH}")

    # 콘솔 요약
    print(f"\n[Result Summary]")
    print(f"  total calls:           {len(results)}/10")
    print(f"  schema PASS:           {schema_pass_count}/{len(results)}")
    print(f"  completeness PASS:     {completeness_count}/{len(results)}")
    print(f"  fallback:              {fallback_count}/{len(results)}")
    print(f"  total cost:            ${total_cost:.6f} / ${COST_THRESHOLDS['total_max']:.4f}")
    print(f"  max haiku cost:        ${max_haiku_cost:.6f} / ${COST_THRESHOLDS['haiku_per_call']:.4f}")
    print(f"  max sonnet cost:       ${max_sonnet_cost:.6f} / ${COST_THRESHOLDS['sonnet_per_call']:.4f}")
    print(f"  cost_per_call_pass:    {cost_per_call_pass}")
    print(f"  total_cost_pass:       {total_cost_pass}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
