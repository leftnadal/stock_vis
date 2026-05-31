"""Slice 3 Part 2 Step 6 — E2 진입점 실 haiku 1회 smoke (D2.B + D4 가이드).

garp_tech fixture (slice1_baseline 그룹) × haiku × 1회 호출.

판정 6개:
  schema_pass (Pydantic) / completeness_auto (schema 통과 = True)
  naturalness (수동 1~5) / insight (수동 1~5)
  cost_pass (≤ $0.020) / latency_pass (≤ 5,000ms)

D4 회피 가이드 (Slice 2 1차 손실 재발 방지):
  - _json_default 핸들러 (set/Decimal/datetime)
  - 산출물 disk write 후 read-back round-trip 검증

Usage:
    python -m scripts.validation.run_step6_e2_smoke
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

from apps.portfolio.llm import LLMClient
from apps.portfolio.llm.client import ANTHROPIC_HAIKU_MODEL
from apps.portfolio.llm.cost_guard import CostGuard
from apps.portfolio.schemas.llm import E2Request
from apps.portfolio.services.e2_diagnostic_card import (
    build_e2_prompt,
    parse_e2_response,
)
from apps.portfolio.tests.fixtures.sample_diagnostic_context import ALL_FIXTURES

THRESHOLDS = {"cost_usd_max": 0.020, "latency_ms_max": 5000}

OUTPUT_PATH = Path("docs/portfolio/coach/slice3/step6_smoke_e2_output.json")


def _json_default(obj):
    """JSON 직렬화 안전망 — D4 회피 가이드."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def _safe_write(path: Path, data: dict) -> None:
    """Write + read-back round-trip 검증."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)
    path.write_text(serialized, encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded is not None, "Round-trip read returned None"
    print(f"  [round-trip OK] {path}")


def main() -> int:
    print("=" * 60)
    print("Step 6 — E2 smoke (garp_tech × haiku, D2.B)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    fixture = ALL_FIXTURES["garp_tech"]()
    request = E2Request(analysis_context=fixture["analysis_context"])
    prompt = build_e2_prompt(request)

    client = LLMClient()
    resp = client.complete(
        prompt=prompt, provider="anthropic", model=ANTHROPIC_HAIKU_MODEL
    )

    # schema 검증 (completeness 자동 통과 포함)
    parsed = None
    schema_pass = False
    schema_error: str | None = None
    parsed_dict = None
    completeness_auto = False
    try:
        parsed = parse_e2_response(
            resp.text, preset_id=request.analysis_context.get("preset_id", "garp")
        )
        schema_pass = True
        parsed_dict = parsed.model_dump()
        completeness_auto = True
    except Exception as exc:  # noqa: BLE001
        schema_error = f"{type(exc).__name__}: {str(exc)[:300]}"

    # 임계 판정
    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    eval_guide = {
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
    }

    output = {
        "step": "step6_e2_smoke",
        "fixture": "garp_tech",
        "fixture_group": fixture["fixture_group"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "preset_id": request.analysis_context.get("preset_id"),
            "holdings_count": len(request.analysis_context.get("holdings", [])),
        },
        "raw_content": resp.text,
        "parsed": parsed_dict,
        "metadata": resp.metadata_dict(),
        "judgments": {
            "schema_pass": schema_pass,
            "schema_error": schema_error,
            "completeness_auto": completeness_auto,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "naturalness_manual": None,
            "insight_manual": None,
        },
        "thresholds": THRESHOLDS,
        "evaluation_guide": eval_guide,
        "status_summary": {
            "schema_pass": schema_pass,
            "completeness_auto": completeness_auto,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "manual_eval_required": ["naturalness_manual", "insight_manual"],
        },
        "cost_guard_status": CostGuard.get_instance().status(),
    }

    _safe_write(OUTPUT_PATH, output)

    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"  schema_pass:       {schema_pass}")
    print(f"  completeness_auto: {completeness_auto}")
    print(
        f"  cost_pass:         {cost_pass} "
        f"(${resp.cost_usd:.5f} / ${THRESHOLDS['cost_usd_max']:.4f})"
    )
    print(
        f"  latency_pass:      {latency_pass} "
        f"({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
    )
    print(f"  fallback_from:     {resp.fallback_from}")
    print()
    print("⚠️  naturalness_manual + insight_manual 필드 1~5 직접 입력 필요.")
    return 0 if (schema_pass and cost_pass and latency_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
