"""Slice 11 Part 3 Step 5 — E1 smoke + #48 v3 자동 분기.

A2 통합 진입점 E1 commentary를 portfolio_a2 fixture로 실측 호출.
haiku + sonnet 2 케이스 (slice cap $1.00 마진 98.5%+).

측정:
  - estimator v3 예측 (in-memory)
  - count_tokens API (정의상 ±2%)
  - actual (LLM 응답 usage)
  - delta_predicted / delta_counted

Output:
  - console summary
  - docs/portfolio/coach/slice11/part3_smoke_dump.md
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DUMP_PATH = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice11" / "part3_smoke_dump.md"


def _delta(actual: int, est: int) -> float:
    if actual <= 0:
        return 0.0
    return abs(actual - est) / actual * 100


def _run_case(model: str) -> dict:
    """단일 모델 케이스 실행 + 측정."""
    from portfolio.measure.estimator_v3 import estimate_input_tokens, reset_cache
    from portfolio.schemas.commentary_output import E1Output
    from portfolio.services.coach.prompt_builder import E1PromptBuilder
    from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input

    reset_cache()  # 케이스별 격리

    inp = load_portfolio_a2_input("e1")
    messages = E1PromptBuilder.build_messages(inp)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    # Anthropic 형식 — system은 별도 인자
    anth_messages = [{"role": "user", "content": user_prompt}]

    client = anthropic.Anthropic()

    # 1. v3 estimator (count_tokens API 활용)
    predicted = estimate_input_tokens(anth_messages, system=system_prompt, model=model)

    # 2. 별도 count_tokens 직접 호출 (cache hit이지만 명시적 호출용)
    reset_cache()  # cache 비워서 강제 API 호출
    counted_response = client.messages.count_tokens(
        model=model, system=system_prompt, messages=anth_messages
    )
    counted = int(counted_response.input_tokens)

    # 3. 실측 LLM 호출
    t0 = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system_prompt,
        messages=anth_messages,
    )
    latency_ms = int((time.time() - t0) * 1000)
    actual = int(response.usage.input_tokens)
    output_tokens = int(response.usage.output_tokens)
    response_text = "".join(b.text for b in response.content if hasattr(b, "text"))

    # 4. cost 계산 (단가 portfolio/llm/client.py 동일)
    if "haiku" in model:
        in_rate, out_rate = 0.80e-6, 4.0e-6
    else:  # sonnet
        in_rate, out_rate = 3.0e-6, 15.0e-6
    cost = actual * in_rate + output_tokens * out_rate

    # 5. schema fitting (Part 2 E1Output validate)
    fitting_pass = False
    fitting_error = ""
    try:
        # parse_json_response가 markdown fence 제거 처리
        from portfolio.llm.parsers import parse_json_response

        E1Output_parsed = parse_json_response(E1Output, response_text)
        fitting_pass = True
        fitting_error = ""
    except Exception as e:  # noqa: BLE001
        fitting_error = f"{type(e).__name__}: {e}"

    return {
        "model": model,
        "predicted_tokens": predicted,
        "counted_tokens": counted,
        "actual_input_tokens": actual,
        "output_tokens": output_tokens,
        "delta_predicted_pct": round(_delta(actual, predicted), 2),
        "delta_counted_pct": round(_delta(actual, counted), 2),
        "latency_ms": latency_ms,
        "cost_usd": round(cost, 6),
        "schema_fitting_pass": fitting_pass,
        "schema_fitting_error": fitting_error,
        "response_text": response_text,
    }


def main() -> int:
    print("=" * 60)
    print("Slice 11 Part 3 Step 5 — E1 smoke + #48 v3 측정")
    print("=" * 60)

    cases = []
    for model in ("claude-haiku-4-5", "claude-sonnet-4-5"):
        print(f"\n--- {model} ---")
        try:
            result = _run_case(model)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {type(e).__name__}: {e}")
            return 2
        cases.append(result)
        for k in ("predicted_tokens", "counted_tokens", "actual_input_tokens",
                  "output_tokens", "delta_predicted_pct", "delta_counted_pct",
                  "latency_ms", "cost_usd", "schema_fitting_pass"):
            print(f"  {k}: {result[k]}")
        if result["schema_fitting_error"]:
            print(f"  schema_fitting_error: {result['schema_fitting_error']}")

    total_cost = sum(c["cost_usd"] for c in cases)
    max_delta_counted = max(c["delta_counted_pct"] for c in cases)
    all_fitting = all(c["schema_fitting_pass"] for c in cases)

    print("\n=== Summary ===")
    print(f"N = {len(cases)}")
    print(f"max delta_counted_pct = {max_delta_counted}%")
    print(f"all schema fitting PASS = {all_fitting}")
    print(f"total cost = ${total_cost:.4f}")

    DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUMP_PATH.write_text(_render_md(cases, total_cost, max_delta_counted, all_fitting),
                         encoding="utf-8")
    print(f"\ndump → {DUMP_PATH}")
    return 0


def _render_md(cases: list[dict], total_cost: float, max_delta_counted: float,
               all_fitting: bool) -> str:
    lines = [
        "# Slice 11 Part 3 Step 5 — Smoke Dump (#48 v3 자동 분기)",
        "",
        f"- N = {len(cases)}",
        f"- max delta_counted_pct = **{max_delta_counted}%** (count_tokens API 명세 ≤ 2%)",
        f"- all schema fitting PASS: **{all_fitting}**",
        f"- total cost: **${total_cost:.4f}** (cap $1.00 마진 {(1.0 - total_cost) * 100:.1f}%)",
        "",
        "## 1. 케이스별 측정",
        "",
        "| # | model | predicted | counted | actual | output | delta_predicted | delta_counted | latency_ms | cost | fitting |",
        "| - | ----- | --------- | ------- | ------ | ------ | --------------- | ------------- | ---------- | ---- | ------- |",
    ]
    for i, c in enumerate(cases, 1):
        lines.append(
            f"| {i} | {c['model']} | {c['predicted_tokens']} | {c['counted_tokens']} | "
            f"{c['actual_input_tokens']} | {c['output_tokens']} | {c['delta_predicted_pct']}% | "
            f"{c['delta_counted_pct']}% | {c['latency_ms']} | ${c['cost_usd']:.5f} | "
            f"{'PASS' if c['schema_fitting_pass'] else 'FAIL'} |"
        )

    lines += [
        "",
        "## 2. #48 v3 KPI 판정",
        "",
        "| KPI                       | 임계        | 측정              | 판정 |",
        "| ------------------------- | ----------- | ----------------- | ---- |",
        f"| max_delta_counted (count_tokens 정확성) | ≤ 2% | {max_delta_counted}% | "
        f"{'PASS' if max_delta_counted <= 2.0 else 'FAIL'} |",
        f"| schema fitting (E1Output validate)      | 모든 케이스 | "
        f"{'all PASS' if all_fitting else 'FAIL 존재'} | "
        f"{'PASS' if all_fitting else 'FAIL'} |",
        f"| smoke cost                              | ≤ $0.05 | ${total_cost:.4f} | "
        f"{'PASS' if total_cost <= 0.05 else 'FAIL'} |",
        "",
        "## 3. 부채 처리 (Slice 10 #48 예약 룰)",
        "",
    ]
    if max_delta_counted <= 10.0 and len(cases) >= 2:
        lines.append("- **v3 정책 정착 확정** (max_delta ≤ 10%, N=2). Slice 12+ 자연 활용.")
    elif max_delta_counted <= 10.0:
        lines.append("- weak signal (N=1, max_delta ≤ 10%). Part 4 매트릭스 재측정.")
    else:
        lines.append(f"- max_delta > 10% ({max_delta_counted}%) — keep_open, Slice 12 Step 0 후보 등록.")

    lines += ["", "## 4. LLM 응답 raw 텍스트 (Slice 11 #52 정책)", ""]
    for i, c in enumerate(cases, 1):
        lines.append(f"### Case {i} — {c['model']}")
        lines.append("")
        lines.append("```")
        lines.append(c["response_text"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
