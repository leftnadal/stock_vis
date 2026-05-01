"""
Slice 2 Part 2 Step 6 — E5 진입점 실 haiku 1회 호출 (smoke test).

clear_decrease fixture × haiku provider × 1회 호출로 baseline 측정.

판정 4개:
  1. schema_pass: E5Response Pydantic validation
  2. intent_match_manual: 1~5 수동 평가 (TSLA + decrease 매칭)
  3. cost_pass: cost_usd <= $0.020 (Slice 1 갱신 임계 동일)
  4. latency_pass: latency_ms <= 5000

산출:
  docs/portfolio/coach/slice2/step6_smoke_e5_output.json

Usage:
    python -m scripts.validation.run_step6_e5_smoke
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.llm import LLMClient
from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.llm import E5Request, E5Response
from portfolio.services.e5_adjustment_parser import build_e5_prompt
from portfolio.tests.fixtures.sample_adjustment_context import ALL_FIXTURES


THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 5000,
}

OUTPUT_PATH = Path("docs/portfolio/coach/slice2/step6_smoke_e5_output.json")


def main() -> int:
    fixture = ALL_FIXTURES["clear_decrease"]()
    request = E5Request(
        analysis_context=fixture["analysis_context"],
        user_command=fixture["user_command"],
    )
    prompt = build_e5_prompt(request)

    client = LLMClient()
    print("=" * 60)
    print("Step 6 — E5 smoke (clear_decrease × haiku)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    resp = client.complete(
        prompt=prompt,
        provider="anthropic",
        model=ANTHROPIC_HAIKU_MODEL,
    )

    # schema 검증 (마크다운 펜스 사전 제거)
    parsed: E5Response | None = None
    schema_pass = False
    schema_error: str | None = None
    parsed_dict = None
    try:
        parsed = parse_json_response(E5Response, resp.text)
        schema_pass = True
        parsed_dict = parsed.model_dump()
    except Exception as exc:  # noqa: BLE001
        schema_error = f"{type(exc).__name__}: {str(exc)[:300]}"

    # 임계 판정
    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    # 의도 매칭 가이드 (수동 평가 시 참조 — N1.C 인라인)
    intent_match_guide = {
        "5": "TSLA + decrease 모두 정확. 다른 종목/액션 추가 없음.",
        "4": "TSLA + decrease OK. 사소한 부수 변경(예: target_weight null 누락 등).",
        "3": "TSLA decrease는 있으나 추가 임의 변경 1~2개.",
        "2": "TSLA decrease 부분 매칭. 또는 임의 변경 3+개.",
        "1": "TSLA 또는 decrease 누락.",
    }

    output = {
        "step": "step6_e5_smoke",
        "fixture": "clear_decrease",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "user_command": request.user_command,
            "holdings_count": len(
                request.analysis_context.get("holdings", [])
            ),
        },
        "raw_content": resp.text,
        "parsed": parsed_dict,
        "metadata": resp.metadata_dict(),
        "judgments": {
            "schema_pass": schema_pass,
            "schema_error": schema_error,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "intent_match_manual": None,  # 수동 평가 입력 필요
        },
        "thresholds": THRESHOLDS,
        "evaluation_guide": {
            "intent_match": intent_match_guide,
        },
        "status_summary": {
            "schema_pass": schema_pass,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "manual_eval_required": "intent_match_manual",
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"  schema_pass:  {schema_pass}" + (f"  (error: {schema_error})" if schema_error else ""))
    print(
        f"  cost_pass:    {cost_pass} "
        f"(${resp.cost_usd:.5f} / ${THRESHOLDS['cost_usd_max']:.4f})"
    )
    print(
        f"  latency_pass: {latency_pass} "
        f"({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
    )
    print(f"  fallback_from: {resp.fallback_from}")
    print()
    print("⚠️  intent_match_manual 필드를 1~5로 직접 입력 필요.")
    print(f"    파일: {OUTPUT_PATH}")
    print("    가이드: output['evaluation_guide']['intent_match'] 참조")
    return 0 if (schema_pass and cost_pass and latency_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
