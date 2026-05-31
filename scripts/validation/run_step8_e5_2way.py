"""
Slice 2 Part 2 Step 8 — E5 2-way 회고 (haiku + sonnet, gemini 제외).

7 fixture × 2 model = 14 호출. 비용 가드: 18 → 32 / 50.

산출:
  docs/portfolio/coach/slice2/step8_2way_e5_raw.json

수동 평가 입력 필요 (N1.A — JSON 직접 편집):
  results[].judgments.intent_match_manual (1~5)
  results[].judgments.no_extra_changes_manual (1~5)

Usage:
    python -m scripts.validation.run_step8_e5_2way
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from apps.portfolio.llm import LLMClient
from apps.portfolio.llm.client import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL
from apps.portfolio.llm.parsers import parse_json_response
from apps.portfolio.schemas.llm import E5Request, E5Response
from apps.portfolio.services.e5_adjustment_parser import build_e5_prompt
from apps.portfolio.tests.fixtures.sample_adjustment_context import ALL_FIXTURES

PROVIDERS = [
    {"label": "haiku", "provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    {"label": "sonnet", "provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL},
]


# 평가 가이드 (산출물에 인라인 — N1.C)
EVALUATION_GUIDE = {
    "intent_match": {
        "5": "모든 종목 + 액션 정확. 누락 없음.",
        "4": "핵심 정확. 사소한 누락 (예: target_weight null 미처리).",
        "3": "일부 누락 또는 추가 변경 있으나 핵심 의도 OK.",
        "2": "절반 이상 누락 또는 잘못된 액션.",
        "1": "의도 완전 빗나감.",
    },
    "no_extra_changes": {
        "5": "추가 변경 없음.",
        "4": "1개 종목 추가 변경 (사소함).",
        "3": "2~3개 종목 추가 변경.",
        "2": "4개 종목 추가 변경.",
        "1": "5개 이상 추가 변경 (의도 왜곡 수준).",
    },
}


OUTPUT_PATH = Path("docs/portfolio/coach/slice2/step8_2way_e5_raw.json")


def _json_default(obj):
    """set 등 직렬화 불가 객체 처리. fixture.expected에 set 사용."""
    if isinstance(obj, set):
        return sorted(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable: {obj!r}")


def main() -> int:
    print("=" * 60)
    print("Step 8 — E5 2-way 회고 (7 fixture × 2 model = 14 calls)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    client = LLMClient()
    results: list[dict] = []
    call_idx = 0

    for fixture_name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E5Request(
            analysis_context=fixture["analysis_context"],
            user_command=fixture["user_command"],
        )
        prompt = build_e5_prompt(request)

        for prov in PROVIDERS:
            call_idx += 1
            label = prov["label"]
            print(f"[{call_idx:>2}/14] {fixture_name:<20} × {label:<7}", end=" ", flush=True)
            try:
                resp = client.complete(
                    prompt=prompt,
                    provider=prov["provider"],
                    model=prov["model"],
                )
                # schema 검증 (마크다운 펜스 사전 제거)
                parsed = None
                schema_pass = False
                schema_error: str | None = None
                parsed_dict = None
                try:
                    parsed = parse_json_response(E5Response, resp.text)
                    schema_pass = True
                    parsed_dict = parsed.model_dump()
                except Exception as exc:  # noqa: BLE001
                    schema_error = f"{type(exc).__name__}: {str(exc)[:200]}"

                results.append({
                    "fixture": fixture_name,
                    "model_label": label,
                    "raw_content": resp.text,
                    "parsed": parsed_dict,
                    "metadata": resp.metadata_dict(),
                    "judgments": {
                        "schema_pass": schema_pass,
                        "schema_error": schema_error,
                        "intent_match_manual": None,
                        "no_extra_changes_manual": None,
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
                    "model_label": label,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                    "metadata": {},
                    "expected": fixture.get("expected", {}),
                    "judgments": {
                        "schema_pass": False,
                        "schema_error": str(exc)[:200],
                        "intent_match_manual": None,
                        "no_extra_changes_manual": None,
                    },
                })
                print(f"ERROR: {type(exc).__name__}: {exc}")

    # 비용 합계
    total_cost = sum(
        r.get("metadata", {}).get("cost_usd", 0) or 0 for r in results
    )
    fallback_count = sum(
        1 for r in results
        if r.get("metadata", {}).get("fallback_from") is not None
    )
    schema_pass_count = sum(
        1 for r in results if r["judgments"]["schema_pass"]
    )

    output = {
        "step": "step8_2way_e5_raw",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "matrix_size": {
            "fixtures": len(ALL_FIXTURES),
            "models": len(PROVIDERS),
            "total_calls": len(results),
        },
        "providers": [
            {"label": p["label"], "model": p["model"]} for p in PROVIDERS
        ],
        "results": results,
        "summary": {
            "total_calls": len(results),
            "total_cost_usd": round(total_cost, 4),
            "fallback_count": fallback_count,
            "schema_pass_count": schema_pass_count,
        },
        "evaluation_guide": EVALUATION_GUIDE,
        "manual_eval_required": [
            "results[].judgments.intent_match_manual (1~5 정수)",
            "results[].judgments.no_extra_changes_manual (1~5 정수)",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )

    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"  total calls:        {len(results)}")
    print(f"  schema_pass:        {schema_pass_count}/{len(results)}")
    print(f"  total cost:         ${total_cost:.4f}")
    print(f"  fallback count:     {fallback_count}/{len(results)}")
    print()
    print("⚠️  다음 필드를 수동 입력 후 score_step8_e5 실행:")
    print("    - results[].judgments.intent_match_manual (1~5)")
    print("    - results[].judgments.no_extra_changes_manual (1~5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
