"""
Slice 1 Part 2 — Step 8: 3 fixture × 3 model = 9회 실제 LLM 호출.

각 응답을 raw로 저장. 수동 평가(naturalness, insight) 후
score_step8 실행.

산출:
  docs/portfolio/coach/slice1/step8_3way_raw.json

Usage:
    python -m scripts.validation.run_step8_3way
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.llm import LLMClient
from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL
from portfolio.llm.parsers import parse_json_response
from portfolio.prompts.e1.e1_builder import build_e1_prompt
from portfolio.schemas.llm_outputs import OneLineDiagnosis
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)

# Provider 라벨 → (LLMClient.complete 인자: provider, model)
# §1.1: LLMResponse.provider Literal["gemini","anthropic"] 변경 금지.
# 따라서 sonnet/haiku는 anthropic + model 조합으로 구분.
PROVIDER_SPECS: dict[str, tuple[str, str | None]] = {
    "gemini": ("gemini", None),
    "sonnet": ("anthropic", ANTHROPIC_SONNET_MODEL),
    "haiku":  ("anthropic", ANTHROPIC_HAIKU_MODEL),
}

FIXTURES = {
    "garp_tech": get_context_garp_tech,
    "garp_misfit": get_context_garp_misfit,
    "garp_large": get_context_garp_large,
}

OUTPUT_PATH = Path("docs/portfolio/coach/slice1/step8_3way_raw.json")


def _assemble_prompt(ctx) -> str:
    system_prompt, user_message = build_e1_prompt(ctx)
    return f"{system_prompt}\n\n{user_message}"


def call_one(label: str, fixture_name: str, ctx_fn) -> dict:
    """단일 (label, fixture) 호출. error/schema/평가 슬롯 포함."""
    provider, model = PROVIDER_SPECS[label]
    ctx = ctx_fn()
    prompt = _assemble_prompt(ctx)
    client = LLMClient()
    try:
        raw = client.complete(prompt=prompt, provider=provider, model=model)
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "fixture": fixture_name,
            "error": f"{type(exc).__name__}: {exc}",
            "schema_pass": False,
            "naturalness": None,
            "insight": None,
        }

    # Schema 통과 검증 (마크다운 펜스 사전 제거)
    parsed = None
    schema_pass = False
    schema_error: str | None = None
    try:
        parsed = parse_json_response(OneLineDiagnosis, raw.text)
        schema_pass = True
    except Exception as exc:  # noqa: BLE001
        schema_error = str(exc)

    return {
        "label": label,
        **raw.metadata_dict(),
        "fixture": fixture_name,
        "raw_text": raw.text,
        "parsed": parsed.model_dump() if parsed else None,
        "schema_pass": schema_pass,
        "schema_error": schema_error,
        # 수동 평가 슬롯 — JSON 직접 수정으로 채움
        "naturalness": None,
        "insight": None,
        "error": None,
    }


def main() -> int:
    print("=" * 60)
    print("Step 8 — 3-way 회고 (3 fixture × 3 model = 9 calls)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results: list[dict] = []
    call_idx = 0
    for fixture_name, ctx_fn in FIXTURES.items():
        for label in PROVIDER_SPECS:
            call_idx += 1
            print(f"[{call_idx}/9] {label:<7} × {fixture_name:<12} ...", end=" ", flush=True)
            r = call_one(label, fixture_name, ctx_fn)
            results.append(r)
            if r.get("error"):
                print(f"ERROR: {r['error']}")
            else:
                print(
                    f"OK ({r['latency_ms']}ms, ${r['cost_usd']:.5f}, "
                    f"schema={'OK' if r['schema_pass'] else 'FAIL'})"
                )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_calls": len(results),
                    "errors": sum(1 for r in results if r.get("error")),
                    "total_cost_usd": sum(r.get("cost_usd") or 0 for r in results),
                },
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    total_cost = sum(r.get("cost_usd") or 0 for r in results)
    errors = sum(1 for r in results if r.get("error"))
    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"Total calls: {len(results)}, errors: {errors}, total cost: ${total_cost:.4f}")
    print(
        "\n다음 단계: 산출물 JSON의 각 entry에서 raw_text/parsed를 보고 "
        "naturalness, insight 필드를 1~5 정수로 직접 입력."
    )
    print("평가 완료 후: python -m scripts.validation.score_step8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
