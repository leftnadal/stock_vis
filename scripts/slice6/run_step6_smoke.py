"""Slice 6 Part 3 Step 6 — concentrated_portfolio E3 smoke test.

V1 × haiku × 1 call → 4판정 (schema/completeness/cost/token) PASS 검증.
Slice 5 run_step6_e3_smoke.py mirror + e3_portfolio reinforced mode.

D4 회피 가이드:
  - _json_default 핸들러
  - 산출물 round-trip 검증

Usage:
    python -m scripts.slice6.run_step6_smoke
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice6", max_calls=50)

from portfolio.llm import LLMClient
from portfolio.llm.cost_guard import CostGuard
from portfolio.prompts.e3_portfolio import build_e3_portfolio_prompt
from portfolio.services._llm_kwargs import PROVIDER_KWARGS
from portfolio.services.e3_portfolio_service import (
    parse_e3_portfolio_response,
)
from portfolio.tests.fixtures.sample_e3_portfolio_context import (
    PRESET_INTENT_MAP,
    get_v1_concentrated_balanced,
)

# Slice 6 Part 3 §1.3 + §1.4
THRESHOLDS = {
    "cost_usd_max": 0.020,       # 단건 비용 ≤ $0.020
    "output_tokens_max": 1_000,  # output ≤ 1,000 (buffer 1.5x 적용)
    "latency_ms_max": 16_000,    # Slice 4·5 e3 mirror
}

OUTPUT_JSON = Path("docs/portfolio/coach/slice6/step6_smoke_result.json")
OUTPUT_MD = Path("docs/portfolio/coach/slice6/step6_smoke_result.md")


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def _safe_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)
    path.write_text(serialized, encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded is not None, "Round-trip read returned None"
    print(f"  [round-trip OK] {path}")


def main() -> int:
    print("=" * 70)
    print("Slice 6 Part 3 Step 6 — E3 portfolio smoke (V1 × haiku, reinforced)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    fixture = get_v1_concentrated_balanced()
    holdings_summary = ", ".join(
        f"{h['ticker']}({h['weight']:.0%})" for h in fixture["holdings"]
    )

    # reinforced prompt (Part 2 Step A)
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
    print(f"[Prompt] chars={len(prompt)}")

    # LLM 호출 (haiku, real)
    client = LLMClient()
    resp = client.complete(prompt=prompt, **PROVIDER_KWARGS["haiku"])
    print(
        f"[LLM] provider={resp.provider} model={resp.model} "
        f"latency={resp.latency_ms}ms cost=${resp.cost_usd:.6f} "
        f"input_tokens={resp.input_tokens} output_tokens={resp.output_tokens} "
        f"fallback_from={resp.fallback_from}"
    )

    # 4판정
    parsed = None
    schema_pass = False
    schema_error: str | None = None
    parsed_dict = None
    completeness_pass = False
    try:
        parsed = parse_e3_portfolio_response(resp.text)
        schema_pass = True
        parsed_dict = parsed.model_dump()
        # completeness: 6 필드 모두 비공란 + 의미 있는 내용 (≥ min_length 만족 = parse 통과)
        completeness_pass = all(
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
        print(f"[schema_pass=False] {schema_error}")

    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    token_pass = resp.output_tokens <= THRESHOLDS["output_tokens_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    judgments = {
        "schema_pass": schema_pass,
        "schema_error": schema_error,
        "completeness_pass": completeness_pass,
        "cost_pass": cost_pass,
        "token_pass": token_pass,
        "latency_pass": latency_pass,  # 보조
    }

    output = {
        "step": "slice6_part3_step6_smoke",
        "fixture": fixture["fixture_id"],
        "fixture_group": fixture["fixture_group"],
        "preset_id": fixture["preset_id"],
        "preset_category": fixture["preset_category"],
        "model_label": "haiku",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "prompt_chars": len(prompt),
            "holdings_count": len(fixture["holdings"]),
            "preset_id": fixture["preset_id"],
        },
        "raw_content": resp.text,
        "parsed": parsed_dict,
        "metadata": resp.metadata_dict(),
        "judgments": judgments,
        "thresholds": THRESHOLDS,
        "status_summary": {
            "schema_pass": schema_pass,
            "completeness_pass": completeness_pass,
            "cost_pass": cost_pass,
            "token_pass": token_pass,
            "latency_pass": latency_pass,
            "four_judgment_all_pass": (
                schema_pass and completeness_pass and cost_pass and token_pass
            ),
        },
        "cost_guard_status": CostGuard.get_instance().status(),
    }

    _safe_write_json(OUTPUT_JSON, output)

    # Markdown 보고서
    md_lines = [
        "# Slice 6 Part 3 Step 6 — E3 Portfolio Smoke Test",
        "",
        f"> 실행: {output['executed_at']}",
        f"> Fixture: {fixture['fixture_id']} × haiku (reinforced mode)",
        "",
        "## 4 판정",
        "",
        "| 판정 | 결과 | 임계 대비 |",
        "|---|---|---|",
        f"| schema_pass | {'PASS ✓' if schema_pass else 'FAIL ✗'} | E3PortfolioCommentary 6 필드 |",
        f"| completeness_pass | {'PASS ✓' if completeness_pass else 'FAIL ✗'} | 모든 필드 비공란 |",
        f"| cost_pass | {'PASS ✓' if cost_pass else 'FAIL ✗'} | ${resp.cost_usd:.6f} / ${THRESHOLDS['cost_usd_max']:.4f} |",
        f"| token_pass | {'PASS ✓' if token_pass else 'FAIL ✗'} | output {resp.output_tokens} / {THRESHOLDS['output_tokens_max']} |",
        "",
        "## 메타데이터",
        "",
        f"- latency: {resp.latency_ms}ms (임계 {THRESHOLDS['latency_ms_max']}ms)",
        f"- input_tokens: {resp.input_tokens}",
        f"- output_tokens: {resp.output_tokens}",
        f"- fallback_from: {resp.fallback_from or 'None'}",
        f"- cost: ${resp.cost_usd:.6f}",
        "",
        "## 결과",
        "",
        f"- **4판정 전체 PASS**: {'✓' if output['status_summary']['four_judgment_all_pass'] else '✗ (G1 분기 발동)'}",
        "",
        "## CostGuard 상태",
        "",
        f"- slice_id: slice6",
        f"- call_count: {output['cost_guard_status']['call_count']}/{output['cost_guard_status']['max_calls']}",
        f"- 마진: {output['cost_guard_status']['remaining']}",
        f"- 누적 비용: ${output['cost_guard_status']['total_cost_usd']:.6f}",
    ]
    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  [saved] {OUTPUT_MD}")

    # 콘솔 요약
    print(f"\n[Result Summary]")
    print(f"  schema_pass:       {schema_pass}")
    print(f"  completeness_pass: {completeness_pass}")
    print(f"  cost_pass:         {cost_pass} (${resp.cost_usd:.5f} / ${THRESHOLDS['cost_usd_max']:.4f})")
    print(f"  token_pass:        {token_pass} ({resp.output_tokens} / {THRESHOLDS['output_tokens_max']})")
    print(f"  latency_pass:      {latency_pass} ({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)")
    print(f"  fallback_from:     {resp.fallback_from or 'None'}")
    print(
        f"\n  4판정 전체 PASS: "
        f"{'✓ (Step 7 진입 가능)' if output['status_summary']['four_judgment_all_pass'] else '✗ G1 분기 발동'}"
    )
    return 0 if output["status_summary"]["four_judgment_all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
