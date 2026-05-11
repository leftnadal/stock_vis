"""Slice 4 Part 2 Step 6 — E6 (조정 후 비교 해설) 실 haiku 1회 smoke (D2.B + D4 가이드).

e5_baseline_decrease fixture × haiku × 1회 호출.

판정 6개:
  schema_pass (Pydantic) / completeness_auto (schema 통과 = True)
  naturalness (수동 1~5) / insight (수동 1~5)
  cost_pass (≤ $0.020) / latency_pass (≤ 16,000ms — Slice 4 #9 e6 한정)

D4 회피 가이드 (Slice 2 1차 손실 재발 방지):
  - _json_default 핸들러 (set/Decimal/datetime)
  - 산출물 disk write 후 read-back round-trip 검증

Slice 3 (run_step6_e2_smoke.py)와의 핵심 차이:
  - run_e2 → run_e6 (build_e6_prompt + parse_e6_response)
  - fixture: ALL_FIXTURES["garp_tech"] → ALL_FIXTURES["e5_baseline_decrease"]
  - latency 임계: 5,000ms → 16,000ms (Slice 4 #9 처리, e6 한정)
  - reset_for_slice("slice3") → reset_for_slice("slice4")

Usage:
    python -m scripts.validation.run_step6_e6_smoke
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice4", max_calls=50)

from portfolio.llm import LLMClient
from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL
from portfolio.llm.cost_guard import CostGuard
from portfolio.schemas.llm import E6Request
from portfolio.services.e6_comparison import build_e6_prompt, parse_e6_response
from portfolio.tests.fixtures.sample_comparison_context import ALL_FIXTURES


THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 16000,  # Slice 4 #9 — E6 한정 (E2 7,471ms + 안전 마진)
}

OUTPUT_PATH = Path("docs/portfolio/coach/slice4/step6_smoke_e6_output.json")


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
    print("Slice 4 Step 6 — E6 smoke (e5_baseline_decrease × haiku, D2.B)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    fixture_fn = ALL_FIXTURES["e5_baseline_decrease"]
    fixture = fixture_fn()
    payload = {
        "analysis_context": fixture["analysis_context"],
        "adjustments": fixture["adjustments"],
    }
    if fixture.get("user_intent"):
        payload["user_intent"] = fixture["user_intent"]
    request = E6Request.model_validate(payload)
    prompt = build_e6_prompt(request)
    print(f"[Prompt] chars={len(prompt)}")

    client = LLMClient()
    resp = client.complete(
        prompt=prompt, provider="anthropic", model=ANTHROPIC_HAIKU_MODEL
    )
    print(
        f"[LLM] provider={resp.provider} model={resp.model} "
        f"latency={resp.latency_ms}ms cost=${resp.cost_usd:.6f} "
        f"fallback_from={resp.fallback_from}"
    )

    # 1. schema_pass — parse_e6_response 성공 여부
    parsed = None
    schema_pass = False
    schema_error: str | None = None
    parsed_dict = None
    completeness_auto = False
    try:
        parsed = parse_e6_response(resp.text)
        schema_pass = True
        parsed_dict = parsed.model_dump()
        completeness_auto = True  # parse 성공 = 6 필드 minimum length 충족
    except Exception as exc:  # noqa: BLE001
        schema_error = f"{type(exc).__name__}: {str(exc)[:300]}"
        print(f"[schema_pass=False] {schema_error}")

    # 2. cost / latency 임계
    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    eval_guide = {
        "naturalness": {
            "5": "한국어 자연스러움 우수, 비교 해설 톤 매끄러움",
            "4": "자연스러우나 일부 어색 표현",
            "3": "이해 가능하나 약간 기계적",
            "2": "어색 표현 다수",
            "1": "이해 어려움 / 비문법적",
        },
        "insight": {
            "5": "before/after 차이를 비자명한 통찰로 연결, key_changes가 의미있음",
            "4": "기본 차이 분석 + 일부 통찰",
            "3": "수치/필드 표면 비교만",
            "2": "단순 나열에 가까움",
            "1": "비교 깊이 부재",
        },
    }

    output = {
        "step": "step6_e6_smoke",
        "fixture": "e5_baseline_decrease",
        "fixture_group": fixture["fixture_group"],
        "fixture_id": fixture["fixture_id"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "preset_id": request.analysis_context.get("preset_id"),
            "holdings_count": len(request.analysis_context.get("holdings", [])),
            "adjustments_count": len(request.adjustments),
            "user_intent": request.user_intent,
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
            "naturalness_manual": None,  # 사용자 수동 입력 자리
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
