"""Slice 5 Part 2 Step 6 — E3 (지표 코멘트) 실 haiku 1회 smoke (D2.B + D4 가이드).

e3_baseline_garp_tech fixture × haiku × 1회 호출.

판정 4개 (Slice 5 Part 2 §1.1 #1):
  schema_pass (Pydantic) / completeness_pass (comments 1개 이상)
  cost_pass (≤ $0.020) / latency_pass (≤ 16,000ms — Slice 4 #9 e6 한정 → e3 동일 적용)

D4 회피 가이드 (Slice 2 1차 손실 재발 방지):
  - _json_default 핸들러 (set/Decimal/datetime)
  - 산출물 disk write 후 read-back round-trip 검증

Slice 4 (run_step6_e6_smoke.py)와의 핵심 차이:
  - run_e6 → E3 (build_e3_prompt + parse_e3_response)
  - fixture: ALL_FIXTURES["e5_baseline_decrease"] → ALL_FIXTURES["e3_baseline_garp_tech"]
  - schema: E6Request → E3Request (analysis_context only)
  - 판정 4개 (smoke 단계 manual naturalness/insight 제외 — Step 8에서 14 calls 회고로 평가)
  - reset_for_slice("slice4") → reset_for_slice("slice5")

환경 차이 적용 (Part 2 지시서 §2.2):
  - #6: portfolio.schemas.llm.E3Request (llm_inputs.py 미존재, llm.py 통합)
  - #7: PROVIDER_KWARGS["haiku"] (LLMClient entrypoint= 인자 미존재)
  - #8: LLMResponse.metadata_dict() (service tuple → 객체 시그니처)

Usage:
    python -m scripts.validation.run_step6_e3_smoke
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice5", max_calls=50)

from portfolio.llm import LLMClient
from portfolio.llm.cost_guard import CostGuard
from portfolio.schemas.llm import E3Request
from portfolio.services._llm_kwargs import PROVIDER_KWARGS  # 환경 차이 #7
from portfolio.services.e3_metric_comment import build_e3_prompt, parse_e3_response
from portfolio.tests.fixtures.sample_metric_comment_context import ALL_FIXTURES

THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 16000,  # Q2: Slice 4 #9 e6 한정 → e3 동일 적용
}

OUTPUT_PATH = Path("docs/portfolio/coach/slice5/step6_smoke_e3_output.json")


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
    print("Slice 5 Step 6 — E3 smoke (e3_baseline_garp_tech × haiku, D2.B)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    fixture_fn = ALL_FIXTURES["e3_baseline_garp_tech"]
    fixture = fixture_fn()
    request = E3Request(analysis_context=fixture["analysis_context"])
    # 환경 차이 #1: build_e3_prompt service wrapper가 (system, user) tuple → 단일 prompt concat
    from portfolio.schemas import AnalysisContext

    context = AnalysisContext.model_validate(request.analysis_context)
    prompt = build_e3_prompt(context)
    print(f"[Prompt] chars={len(prompt)}")

    client = LLMClient()
    resp = client.complete(prompt=prompt, **PROVIDER_KWARGS["haiku"])  # 환경 차이 #7
    print(
        f"[LLM] provider={resp.provider} model={resp.model} "
        f"latency={resp.latency_ms}ms cost=${resp.cost_usd:.6f} "
        f"fallback_from={resp.fallback_from}"
    )

    # 1. schema_pass — parse_e3_response 성공 여부
    parsed = None
    schema_pass = False
    schema_error: str | None = None
    parsed_dict = None
    completeness_pass = False
    try:
        parsed = parse_e3_response(resp.text)
        schema_pass = True
        parsed_dict = parsed.model_dump()
        # 2. completeness_pass — comments 1개 이상 (지시서 §6.2)
        completeness_pass = len(parsed.comments) >= 1
    except Exception as exc:  # noqa: BLE001
        schema_error = f"{type(exc).__name__}: {str(exc)[:300]}"
        print(f"[schema_pass=False] {schema_error}")

    # 3/4. cost / latency 임계
    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    output = {
        "step": "step6_e3_smoke",
        "fixture": "e3_baseline_garp_tech",
        "fixture_group": fixture["fixture_group"],
        "fixture_id": fixture["fixture_id"],
        "preset_id": fixture["preset_id"],
        "preset_category": fixture["preset_category"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "preset_id": fixture["preset_id"],
            "holdings_count": len(
                request.analysis_context.get("analysis_target_portfolio", {}).get(
                    "holdings", []
                )
            ),
            "metric_count": len(parsed.comments) if parsed else None,
        },
        "raw_content": resp.text,
        "parsed": parsed_dict,
        "metadata": resp.metadata_dict(),  # 환경 차이 #8
        "judgments": {
            "schema_pass": schema_pass,
            "schema_error": schema_error,
            "completeness_pass": completeness_pass,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
        },
        "thresholds": THRESHOLDS,
        "status_summary": {
            "schema_pass": schema_pass,
            "completeness_pass": completeness_pass,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "all_pass": schema_pass and completeness_pass and cost_pass and latency_pass,
        },
        "cost_guard_status": CostGuard.get_instance().status(),
    }

    _safe_write(OUTPUT_PATH, output)

    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"  schema_pass:       {schema_pass}")
    print(f"  completeness_pass: {completeness_pass} "
          f"(comments={len(parsed.comments) if parsed else 0})")
    print(
        f"  cost_pass:         {cost_pass} "
        f"(${resp.cost_usd:.5f} / ${THRESHOLDS['cost_usd_max']:.4f})"
    )
    print(
        f"  latency_pass:      {latency_pass} "
        f"({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
    )
    print(f"  fallback_from:     {resp.fallback_from}")
    return 0 if all([schema_pass, completeness_pass, cost_pass, latency_pass]) else 1


if __name__ == "__main__":
    sys.exit(main())
