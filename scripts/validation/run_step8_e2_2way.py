"""Slice 3 Part 2 Step 8 — E2 2-way 회고 (haiku + sonnet, A1.B 매트릭스).

7 fixture × 2 model = 14 calls. 비용 예상 ~$0.10.

D4 회피 가이드 적용:
  _json_default 핸들러 + round-trip 검증 의무

산출:
  docs/portfolio/coach/slice3/step8_2way_e2_raw.json
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice3", max_calls=50)

from portfolio.llm import LLMClient
from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL
from portfolio.llm.cost_guard import CostGuard
from portfolio.schemas.llm import E2Request
from portfolio.services.e2_diagnostic_card import build_e2_prompt, parse_e2_response
from portfolio.tests.fixtures.sample_diagnostic_context import (
    ALL_FIXTURES,
    FIXTURE_GROUPS,
)


PROVIDERS = [
    {"label": "haiku", "provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    {"label": "sonnet", "provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL},
]


EVALUATION_GUIDE = {
    "naturalness": {
        "5": "한국어 자연스러움 우수, 단순 수치 나열 없음",
        "4": "자연스러우나 일부 어색 표현",
        "3": "이해 가능하나 약간 기계적",
        "2": "어색 표현 다수",
        "1": "이해 어려움 / 비문법적",
    },
    "insight": {
        "5": "지표 너머 의미 있는 해석. 비자명한 패턴 발견",
        "4": "기본 해석 + 일부 통찰",
        "3": "지표 표면 해석만",
        "2": "단순 수치 나열에 가까움",
        "1": "분석 깊이 부재",
    },
    "completeness_auto": "schema 통과 시 자동 True",
}


OUTPUT_PATH = Path("docs/portfolio/coach/slice3/step8_2way_e2_raw.json")


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def main() -> int:
    print("=" * 60)
    print("Step 8 — E2 2-way 회고 (7 fixture × 2 model = 14 calls)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    client = LLMClient()
    results: list[dict] = []
    call_idx = 0

    for fixture_name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E2Request(analysis_context=fixture["analysis_context"])
        prompt = build_e2_prompt(request)

        for prov in PROVIDERS:
            call_idx += 1
            label = prov["label"]
            print(
                f"[{call_idx:>2}/14] {fixture_name:<20} × {label:<7}",
                end=" ",
                flush=True,
            )
            try:
                resp = client.complete(
                    prompt=prompt, provider=prov["provider"], model=prov["model"]
                )
                # schema + completeness 검증
                parsed = None
                schema_pass = False
                schema_error: str | None = None
                parsed_dict = None
                completeness_auto = False
                try:
                    parsed = parse_e2_response(
                        resp.text,
                        preset_id=request.analysis_context.get("preset_id", "garp"),
                    )
                    schema_pass = True
                    parsed_dict = parsed.model_dump()
                    completeness_auto = True
                except Exception as exc:  # noqa: BLE001
                    schema_error = f"{type(exc).__name__}: {str(exc)[:200]}"

                results.append({
                    "fixture": fixture_name,
                    "fixture_group": fixture["fixture_group"],
                    "model_label": label,
                    "raw_content": resp.text,
                    "parsed": parsed_dict,
                    "metadata": resp.metadata_dict(),
                    "judgments": {
                        "schema_pass": schema_pass,
                        "schema_error": schema_error,
                        "completeness_auto": completeness_auto,
                        "naturalness_manual": None,
                        "insight_manual": None,
                    },
                    "expected": fixture.get("expected", {}),
                })
                print(
                    f"OK ({resp.latency_ms}ms, ${resp.cost_usd:.5f}, "
                    f"schema={'OK' if schema_pass else 'FAIL'})"
                )
            except Exception as exc:  # noqa: BLE001
                results.append({
                    "fixture": fixture_name,
                    "fixture_group": fixture["fixture_group"],
                    "model_label": label,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                    "metadata": {},
                    "expected": fixture.get("expected", {}),
                    "judgments": {
                        "schema_pass": False,
                        "schema_error": str(exc)[:200],
                        "completeness_auto": False,
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
    latencies = [
        (r.get("metadata") or {}).get("latency_ms", 0)
        for r in results
        if (r.get("metadata") or {}).get("latency_ms")
    ]
    latency_max = max(latencies) if latencies else 0
    latency_p90 = sorted(latencies)[int(len(latencies) * 0.9)] if latencies else 0

    output = {
        "step": "step8_2way_e2_raw",
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
            "total_cost_usd": round(total_cost, 4),
            "fallback_count": fallback_count,
            "schema_pass_count": schema_pass_count,
            "latency_max_ms": latency_max,
            "latency_p90_ms": latency_p90,
        },
        "evaluation_guide": EVALUATION_GUIDE,
        "manual_eval_required": [
            "results[].judgments.naturalness_manual (1~5)",
            "results[].judgments.insight_manual (1~5)",
        ],
        "cost_guard_status_at_end": CostGuard.get_instance().status(),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(output, ensure_ascii=False, indent=2, default=_json_default)
    OUTPUT_PATH.write_text(serialized, encoding="utf-8")
    # Round-trip 검증 (D4)
    loaded = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert loaded["summary"]["total_calls"] == len(results), "Round-trip failed"
    print(f"  [round-trip OK] {OUTPUT_PATH}")

    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"  total calls:        {len(results)}")
    print(f"  schema_pass:        {schema_pass_count}/{len(results)}")
    print(f"  total cost:         ${total_cost:.4f}")
    print(f"  fallback count:     {fallback_count}/{len(results)}")
    print(f"  latency p90/max:    {latency_p90}ms / {latency_max}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
