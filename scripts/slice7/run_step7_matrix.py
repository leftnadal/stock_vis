"""Slice 7 Part 3 Step 7: matrix 14 cases × haiku/sonnet (28 calls).

진행 중 단건 cost 임계 ($0.020/call) 초과 시 cost_breach_count 증가 (자동 차단 X — 매트릭스 완주).
누적 Step 7 cost cap ($0.50) 초과 시 즉시 중단.

사용:
  poetry run python -m scripts.slice7.run_step7_matrix
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from apps.portfolio.llm.client import LLMClient  # noqa: E402
from apps.portfolio.llm.cost_guard import CostGuard  # noqa: E402
from apps.portfolio.llm.token_budgets import ENTRYPOINT_TOKEN_BUDGETS  # noqa: E402
from apps.portfolio.prompts.e4.builder import build_e4_prompt  # noqa: E402
from apps.portfolio.schemas.e4_conversation import (  # noqa: E402
    E4ConversationInput,
    E4ConversationOutput,
)
from apps.portfolio.services._llm_kwargs import resolve_provider_kwargs  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "portfolio/tests/fixtures/e4_conversation"
OUT_RAW = ROOT / "docs/portfolio/coach/slice7/step7_matrix_raw.json"
OUT_METRICS = ROOT / "docs/portfolio/coach/slice7/step7_matrix_metrics.json"
OUT_REPORT = ROOT / "docs/portfolio/coach/slice7/step7_matrix_report.md"

EXCLUDED_SCENARIOS = {"S13_V1_tier2_empty_history"}  # I2 trigger schema reject
PROVIDER_LABELS = ["haiku", "sonnet"]
COST_THRESHOLD = 0.020
TOTAL_COST_CAP = 0.50  # Step 7 단독 cap
MAX_CALLS = 50


def _strip_markdown_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


def _p90(lst: list[int]) -> int:
    if not lst:
        return 0
    s = sorted(lst)
    idx = int(len(s) * 0.9)
    return s[min(idx, len(s) - 1)]


def main() -> int:
    CostGuard.get_instance().reset_slice("slice7_part3_step7", max_calls=MAX_CALLS)

    fixtures = sorted(FIXTURE_DIR.glob("S*.json"))
    fixtures = [fp for fp in fixtures if fp.stem not in EXCLUDED_SCENARIOS]
    assert len(fixtures) == 14, f"expected 14 cases, got {len(fixtures)}"

    results: list[dict] = []
    total_cost = 0.0
    call_count = 0
    fallback_count = 0
    cost_breach_count = 0

    for fp in fixtures:
        data = json.loads(fp.read_text(encoding="utf-8"))
        inp = E4ConversationInput(**data["input"])
        prompt = build_e4_prompt(inp)
        tier = inp.tier
        budget_key = f"e4_conversation_tier{tier}"
        budget = ENTRYPOINT_TOKEN_BUDGETS[budget_key]

        for label in PROVIDER_LABELS:
            if total_cost >= TOTAL_COST_CAP:
                print(
                    f"⚠ Step 7 비용 cap 도달: ${total_cost:.4f}/${TOTAL_COST_CAP} — 중단"
                )
                break

            kwargs = resolve_provider_kwargs(label)
            client = LLMClient()
            t0 = time.time()
            try:
                response = client.complete(prompt=prompt, max_tokens=1000, **kwargs)
            except Exception as exc:
                results.append(
                    {
                        "scenario_id": data["scenario_id"],
                        "preset_id": inp.preset_id,
                        "tier": tier,
                        "provider": label,
                        "error": str(exc),
                        "skipped": True,
                    }
                )
                continue
            latency_ms = int((time.time() - t0) * 1000)

            cost = response.cost_usd
            input_tokens = response.input_tokens
            output_tokens = response.output_tokens
            fallback = response.fallback_from is not None

            if cost > COST_THRESHOLD:
                cost_breach_count += 1
            if fallback:
                fallback_count += 1

            cleaned = _strip_markdown_fence(response.text)
            try:
                output = E4ConversationOutput.model_validate_json(cleaned)
                schema_pass = True
                completeness_pass = bool(
                    len(output.answer) >= 20 and len(output.referenced_metrics) > 0
                )
            except Exception:
                schema_pass = False
                completeness_pass = False

            results.append(
                {
                    "scenario_id": data["scenario_id"],
                    "preset_id": inp.preset_id,
                    "tier": tier,
                    "provider": label,
                    "trigger_case": data.get("trigger_case"),
                    "raw_content": response.text,
                    "schema_pass": schema_pass,
                    "completeness_pass": completeness_pass,
                    "cost_usd": round(cost, 6),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "budget": budget,
                    "latency_ms": latency_ms,
                    "fallback": fallback,
                    "provider_meta": response.provider,
                    "model": response.model,
                }
            )
            call_count += 1
            total_cost += cost

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    OUT_RAW.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    schema_pass_count = sum(1 for r in results if r.get("schema_pass"))
    completeness_pass_count = sum(1 for r in results if r.get("completeness_pass"))
    input_tokens_list = [r["input_tokens"] for r in results if "input_tokens" in r]
    output_tokens_list = [r["output_tokens"] for r in results if "output_tokens" in r]

    metrics = {
        "total_calls": call_count,
        "total_cost": round(total_cost, 5),
        "schema_pass": f"{schema_pass_count}/{call_count}",
        "completeness_pass": f"{completeness_pass_count}/{call_count}",
        "fallback_count": fallback_count,
        "cost_breach_count": cost_breach_count,
        "max_single_cost": round(
            max((r["cost_usd"] for r in results if "cost_usd" in r), default=0), 5
        ),
        "input_p90": _p90(input_tokens_list),
        "input_max": max(input_tokens_list, default=0),
        "output_p90": _p90(output_tokens_list),
        "output_max": max(output_tokens_list, default=0),
    }
    OUT_METRICS.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 3 Step 7 — Matrix Report",
        "",
        "## 집계",
        "",
        f"- 총 호출: {call_count}/28 (target)",
        f"- schema PASS: {schema_pass_count}/{call_count}",
        f"- completeness PASS: {completeness_pass_count}/{call_count}",
        f"- fallback: {fallback_count}건",
        f"- 단건 비용 임계 초과: {cost_breach_count}건",
        f"- 총 비용: ${total_cost:.5f}",
        f"- input P90/max: {metrics['input_p90']} / {metrics['input_max']}",
        f"- output P90/max: {metrics['output_p90']} / {metrics['output_max']}",
    ]
    OUT_REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"✓ matrix: {OUT_RAW}")
    print(f"  total calls: {call_count} / cost ${total_cost:.4f}")
    print(f"  schema {schema_pass_count}/{call_count} / fallback {fallback_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
