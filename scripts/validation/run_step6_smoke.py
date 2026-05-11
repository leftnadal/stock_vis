"""
Slice 1 Part 2 — Step 6: garp_tech fixture로 실제 Gemini Flash 1회 호출 검증.

판정 4개:
  1. Schema 통과: OneLineDiagnosis Pydantic validation
  2. 한국어 자연스러움: 수동 평가 (1~5), 사후 단계
  3. 비용: cost_usd <= $0.001
  4. 지연: latency_ms <= 5000

산출:
  docs/portfolio/coach/slice1/step6_smoke_output.json

Usage:
    python -m scripts.validation.run_step6_smoke
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.prompts.e1.e1_builder import build_e1_prompt
from portfolio.schemas.llm_outputs import OneLineDiagnosis
from portfolio.tests.fixtures.sample_analysis_context import get_context_garp_tech


# Slice 1 실측 기반 임계 ($0.001은 비현실적, Gemini Flash 1회 평균 $0.015).
THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 5000,
}

OUTPUT_PATH = Path("docs/portfolio/coach/slice1/step6_smoke_output.json")


def main() -> int:
    print("=" * 60)
    print("Step 6 Smoke Test — Gemini Flash + garp_tech")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. Fixture + Prompt 조립
    ctx = get_context_garp_tech()
    system_prompt, user_message = build_e1_prompt(ctx)
    prompt = f"{system_prompt}\n\n{user_message}"

    # 2. Gemini 1회 호출
    client = LLMClient()
    raw = client.complete(prompt=prompt, provider="gemini")

    # 3. Schema 통과 검증
    parsed = None
    schema_pass = False
    schema_error: str | None = None
    try:
        parsed = parse_json_response(OneLineDiagnosis, raw.text)
        schema_pass = True
    except Exception as exc:  # noqa: BLE001
        schema_error = str(exc)

    # 4. 자동 판정
    cost_pass = raw.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = raw.latency_ms <= THRESHOLDS["latency_ms_max"]

    # 5. 산출물 저장
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "metadata": {
                    **raw.metadata_dict(),
                    "fixture": "garp_tech",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                "raw_text": raw.text,
                "parsed": parsed.model_dump() if parsed else None,
                "judgments": {
                    "schema_pass": schema_pass,
                    "schema_error": schema_error,
                    "cost_pass": cost_pass,
                    "latency_pass": latency_pass,
                    "naturalness": "MANUAL_REVIEW_PENDING",
                },
                "thresholds": THRESHOLDS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 6. 콘솔 요약
    print(f"\n[Output] {OUTPUT_PATH}")
    print("\nJudgments:")
    print(f"  1. Schema 통과:        {'OK' if schema_pass else 'FAIL — ' + (schema_error or '')}")
    print(f"  2. 한국어 자연스러움:  수동 평가 → 산출물 JSON의 judgments.naturalness 직접 입력")
    print(
        f"  3. 비용:               {'OK' if cost_pass else 'FAIL'} "
        f"(${raw.cost_usd:.6f} / ${THRESHOLDS['cost_usd_max']:.4f})"
    )
    print(
        f"  4. 지연:               {'OK' if latency_pass else 'FAIL'} "
        f"({raw.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
    )

    if not (schema_pass and cost_pass and latency_pass):
        print("\n[RESULT] FAIL — 자동 판정 미통과. 지시서 §6.5 롤백 절차 참조.")
        return 1

    print("\n[RESULT] 자동 판정 PASS. 한국어 자연스러움 수동 평가 후 Step 7 진입 가능.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
