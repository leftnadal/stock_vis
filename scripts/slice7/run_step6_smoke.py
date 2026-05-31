"""Slice 7 Part 3 Step 6: smoke test (1 call, V1 tier1 × haiku) + #β2 1차 측정.

목표:
  - 4판정 (schema/completeness/cost/token) 전체 PASS
  - #β2 delta 측정 (prompt 포함 실측 input tokens 기반) → Step 7 budget 조정 신호

사용:
  poetry run python -m scripts.slice7.run_step6_smoke
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Django bootstrap 필요 (LLMClient 내부에서 settings 사용)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from apps.portfolio.llm.client import LLMClient  # noqa: E402
from apps.portfolio.llm.cost_guard import CostGuard  # noqa: E402
from apps.portfolio.llm.token_budgets import (  # noqa: E402
    ENTRYPOINT_TOKEN_BUDGETS,
    estimate_input_tokens,
)
from apps.portfolio.prompts.e4.builder import build_e4_prompt  # noqa: E402
from apps.portfolio.schemas.e4_conversation import (  # noqa: E402
    E4ConversationInput,
    E4ConversationOutput,
)
from apps.portfolio.services._llm_kwargs import resolve_provider_kwargs  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "apps/portfolio/tests/fixtures/e4_conversation/S01_V1_tier1.json"
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step6_smoke_result.json"
REPORT_PATH = ROOT / "docs/portfolio/coach/slice7/step6_smoke_result.md"

COST_THRESHOLD = 0.020
BUDGET_KEY = "e4_conversation_tier1"
PROVIDER_LABEL = "haiku"


def _strip_markdown_fence(text: str) -> str:
    """LLM이 ```json ... ``` fence를 붙인 경우 제거."""
    t = text.strip()
    if t.startswith("```"):
        # remove first line (```json or ```)
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


def main() -> int:
    CostGuard.get_instance().reset_slice("slice7_part3_step6", max_calls=5)

    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    inp = E4ConversationInput(**data["input"])

    prompt = build_e4_prompt(inp)
    prompt_chars = len(prompt)
    estimated_tokens = estimate_input_tokens(prompt)
    budget = ENTRYPOINT_TOKEN_BUDGETS[BUDGET_KEY]

    kwargs = resolve_provider_kwargs(PROVIDER_LABEL)
    client = LLMClient()
    t0 = time.time()
    response = client.complete(prompt=prompt, max_tokens=1000, **kwargs)
    latency_ms = int((time.time() - t0) * 1000)

    actual_input = response.input_tokens
    actual_output = response.output_tokens
    cost = response.cost_usd
    raw_text = response.text

    # 4판정
    try:
        cleaned = _strip_markdown_fence(raw_text)
        output = E4ConversationOutput.model_validate_json(cleaned)
        schema_pass = True
    except Exception as exc:
        output = None
        schema_pass = False
        schema_err = str(exc)
    else:
        schema_err = None

    completeness_pass = bool(
        schema_pass
        and output is not None
        and len(output.answer) >= 20
        and len(output.referenced_metrics) > 0
    )
    cost_pass = cost <= COST_THRESHOLD
    token_pass = actual_input <= budget
    all_pass = all((schema_pass, completeness_pass, cost_pass, token_pass))

    delta_pct = (
        (estimated_tokens - actual_input) / actual_input * 100 if actual_input else 0.0
    )

    result = {
        "smoke_4_judgment": {
            "schema": schema_pass,
            "completeness": completeness_pass,
            "cost": cost_pass,
            "token": token_pass,
            "all_pass": all_pass,
        },
        "schema_error": schema_err,
        "metrics": {
            "cost_usd": round(cost, 6),
            "cost_threshold": COST_THRESHOLD,
            "input_tokens_actual": actual_input,
            "output_tokens_actual": actual_output,
            "budget": budget,
            "latency_ms": latency_ms,
        },
        "beta2_first_measurement": {
            "prompt_chars": prompt_chars,
            "estimated_tokens": estimated_tokens,
            "actual_input_tokens": actual_input,
            "delta_pct": round(delta_pct, 2),
            "delta_abs_pct": round(abs(delta_pct), 2),
            "step7_budget_adjustment_needed": abs(delta_pct) > 50,
        },
        "fallback": response.fallback_from,
        "provider": response.provider,
        "model": response.model,
        "raw_text": raw_text,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 3 Step 6 — Smoke + #β2 1차 측정",
        "",
        "## 4판정",
        "",
        f"- schema:       {'✓ PASS' if schema_pass else '✗ FAIL'}"
        + (f" (err: {schema_err})" if schema_err else ""),
        f"- completeness: {'✓ PASS' if completeness_pass else '✗ FAIL'}",
        f"- cost:         {'✓ PASS' if cost_pass else '✗ FAIL'} "
        f"(${cost:.5f} / ${COST_THRESHOLD})",
        f"- token:        {'✓ PASS' if token_pass else '✗ FAIL'} "
        f"({actual_input} / {budget})",
        "",
        "## #β2 1차 측정 (Step 6 smoke)",
        "",
        f"- prompt chars: {prompt_chars}",
        f"- estimated tokens: {estimated_tokens}",
        f"- actual input tokens: {actual_input}",
        f"- delta: {delta_pct:+.2f}%",
        f"- Step 7 budget 조정 필요 (L4 분기): "
        f"{'YES' if abs(delta_pct) > 50 else 'NO'}",
        "",
        "## 메타",
        "",
        f"- latency: {latency_ms}ms / cost: ${cost:.5f}",
        f"- provider: {response.provider} / model: {response.model}",
        f"- fallback: {response.fallback_from}",
    ]
    REPORT_PATH.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"✓ smoke: {OUT_PATH}")
    print(f"  4판정 all_pass: {all_pass}")
    print(
        f"  #β2 delta: {delta_pct:+.2f}% → Step 7 budget "
        f"{'조정 (L4)' if abs(delta_pct) > 50 else '유지'}"
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
