"""Slice 11 Part 4 Step 5 — 24 케이스 풀 매트릭스 (#48 v3 N=26 견고화).

6 진입점 (E1~E6) × 2 모델 (haiku, sonnet) × 2 반복 (#1, #2) = 24 케이스.

각 케이스 측정:
  - estimator v3 예측 input_tokens
  - count_tokens API counted input_tokens
  - 실측 input_tokens (response.usage.input_tokens)
  - output_tokens / cost_usd / latency_ms
  - schema fitting (E{N}Output validate)
  - response_text raw (Slice 11 #52 정책)

배치 순서 (단계적 risk-on):
  Batch 1: E1~E6 × haiku × #1 → 누적 ~$0.087
  Batch 2: E1~E6 × sonnet × #1 → 누적 ~$0.174
  Batch 3: E1~E6 × haiku × #2 → 누적 ~$0.261
  Batch 4: E1~E6 × sonnet × #2 → 누적 ~$0.348

Fallback (§1.6):
  - slice cap 70% ($0.30): 즉시 중단, 부분 매트릭스 종결
  - slice cap 80% ($0.80): 비상 정지
  - 단일 케이스 > $0.05: 해당 케이스 dump, 계속
  - 총 비용 > $0.50: 즉시 정지
  - latency > 60s: 케이스 dump, 계속

Output:
  - docs/portfolio/coach/slice11/part4_matrix.json (구조화된 dump)
  - docs/portfolio/coach/slice11/part4_matrix_dump.md (가독성 dump)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import anthropic
from dotenv import load_dotenv

load_dotenv()

OUT_JSON = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice11" / "part4_matrix.json"
OUT_MD = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice11" / "part4_matrix_dump.md"

# 비용 임계 (§1.6)
SLICE_CAP_LIMIT_USD = 1.00
FALLBACK_A_TRIGGER = 0.30   # cap 70% — 부분 매트릭스 종결
FALLBACK_B_TRIGGER = 0.80   # cap 80% — 비상 정지
TOTAL_COST_HARD_STOP = 0.50  # 144% of expected $0.348
SINGLE_CASE_WARN = 0.05      # 단가 345% 초과 시 dump
LATENCY_WARN_MS = 60_000


def _model_label(model: str) -> str:
    """모델 ID → 짧은 라벨 (haiku / sonnet)."""
    if "haiku" in model:
        return "haiku"
    if "sonnet" in model:
        return "sonnet"
    return model


def _delta(actual: int, est: int) -> float:
    if actual <= 0:
        return 0.0
    return abs(actual - est) / actual * 100.0


def _model_rates(model: str) -> tuple[float, float]:
    if "haiku" in model:
        return 0.80e-6, 4.0e-6
    return 3.0e-6, 15.0e-6  # sonnet


def _run_case(entry: str, model: str, repeat: int, client: anthropic.Anthropic) -> dict:
    """단일 (entry, model, repeat) 케이스 실행 + 측정."""
    from portfolio.llm.parsers import parse_json_response
    from portfolio.measure.estimator_v3 import estimate_input_tokens, reset_cache
    from portfolio.schemas.commentary_output import COMMENTARY_OUTPUT_CLASSES
    from portfolio.services.coach.prompt_builder import PROMPT_BUILDER_CLASSES
    from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input

    reset_cache()

    inp = load_portfolio_a2_input(entry)
    builder_cls = PROMPT_BUILDER_CLASSES[entry]
    output_cls = COMMENTARY_OUTPUT_CLASSES[entry]

    messages = builder_cls.build_messages(inp)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]
    anth_messages = [{"role": "user", "content": user_prompt}]

    # 1. v3 estimator (count_tokens API + 캐시)
    predicted = estimate_input_tokens(
        anth_messages, system=system_prompt, model=model
    )

    # 2. 명시적 count_tokens (cache 비워서 강제 호출)
    reset_cache()
    counted_resp = client.messages.count_tokens(
        model=model, system=system_prompt, messages=anth_messages
    )
    counted = int(counted_resp.input_tokens)

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

    # 4. cost
    in_rate, out_rate = _model_rates(model)
    cost = actual * in_rate + output_tokens * out_rate

    # 5. schema fitting
    fitting_pass = False
    fitting_error = ""
    try:
        parse_json_response(output_cls, response_text)
        fitting_pass = True
    except Exception as e:  # noqa: BLE001
        fitting_error = f"{type(e).__name__}: {e}"

    return {
        "entry": entry,
        "model": model,
        "repeat": repeat,
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


def _matrix_order() -> list[tuple[str, str, int]]:
    """배치 순서 (§1.4): repeat → model → entry 순회."""
    ENTRIES = ["e1", "e2", "e3", "e4", "e5", "e6"]
    MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5"]
    order: list[tuple[str, str, int]] = []
    for repeat in (1, 2):
        for model in MODELS:
            for entry in ENTRIES:
                order.append((entry, model, repeat))
    return order


def main() -> int:
    print("=" * 70)
    print("Slice 11 Part 4 Step 5 — 24 케이스 매트릭스 (#48 v3 N=26)")
    print("=" * 70)

    client = anthropic.Anthropic()
    cases: list[dict] = []
    fallback_reason = ""
    total_cost = 0.0

    for entry, model, repeat in _matrix_order():
        # Fallback gate (pre-run)
        if total_cost >= FALLBACK_B_TRIGGER:
            fallback_reason = f"Fallback B: cap 80% 도달 (${total_cost:.4f})"
            print(f"\n[STOP] {fallback_reason}")
            break
        if total_cost >= FALLBACK_A_TRIGGER:
            fallback_reason = f"Fallback A: cap 70% 도달 (${total_cost:.4f})"
            print(f"\n[STOP] {fallback_reason}")
            break
        if total_cost >= TOTAL_COST_HARD_STOP:
            fallback_reason = f"총 비용 $0.50 초과 (${total_cost:.4f})"
            print(f"\n[STOP] {fallback_reason}")
            break

        tag = f"{entry}/{_model_label(model)}/#{repeat}"
        print(f"\n--- {tag} ---")
        try:
            result = _run_case(entry, model, repeat, client)
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL: {type(e).__name__}: {e}")
            cases.append({
                "entry": entry, "model": model, "repeat": repeat,
                "error": f"{type(e).__name__}: {e}",
                "schema_fitting_pass": False,
            })
            continue

        cases.append(result)
        total_cost += result["cost_usd"]

        for k in ("predicted_tokens", "counted_tokens", "actual_input_tokens",
                  "output_tokens", "delta_predicted_pct", "delta_counted_pct",
                  "latency_ms", "cost_usd", "schema_fitting_pass"):
            print(f"  {k}: {result[k]}")
        if result["schema_fitting_error"]:
            print(f"  schema_fitting_error: {result['schema_fitting_error']}")
        if result["cost_usd"] > SINGLE_CASE_WARN:
            print(f"  [WARN] 단일 케이스 비용 > ${SINGLE_CASE_WARN}")
        if result["latency_ms"] > LATENCY_WARN_MS:
            print(f"  [WARN] latency > {LATENCY_WARN_MS}ms")
        print(f"  누적 비용: ${total_cost:.4f}")

    _write_outputs(cases, total_cost, fallback_reason)

    print("\n" + "=" * 70)
    print(f"매트릭스 종료: {len(cases)}/24 케이스, 총 비용 ${total_cost:.4f}")
    if fallback_reason:
        print(f"중단 사유: {fallback_reason}")
    print(f"→ {OUT_JSON}")
    print(f"→ {OUT_MD}")
    return 0


def _write_outputs(cases: list[dict], total_cost: float, fallback_reason: str) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    successful = [c for c in cases if c.get("schema_fitting_pass")]
    fitting_failed = [c for c in cases if not c.get("schema_fitting_pass")]
    max_delta_predicted = max(
        (c.get("delta_predicted_pct", 0.0) for c in successful), default=0.0
    )
    max_delta_counted = max(
        (c.get("delta_counted_pct", 0.0) for c in successful), default=0.0
    )

    summary = {
        "n_cases_executed": len(cases),
        "n_cases_planned": 24,
        "n_fitting_pass": len(successful),
        "n_fitting_fail": len(fitting_failed),
        "total_cost_usd": round(total_cost, 6),
        "max_delta_predicted_pct": max_delta_predicted,
        "max_delta_counted_pct": max_delta_counted,
        "fallback_reason": fallback_reason,
        "slice_cap_used_pct": round(total_cost / SLICE_CAP_LIMIT_USD * 100, 2),
    }

    OUT_JSON.write_text(
        json.dumps({"summary": summary, "cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = _render_md(cases, summary)
    OUT_MD.write_text(md, encoding="utf-8")


def _render_md(cases: list[dict], summary: dict) -> str:
    lines = [
        "# Slice 11 Part 4 — 24 케이스 매트릭스 Dump (#48 v3 N=26)",
        "",
        "## §1. Summary",
        "",
        f"- 케이스 실행: **{summary['n_cases_executed']}/24**",
        f"- schema fitting PASS: **{summary['n_fitting_pass']}/{summary['n_cases_executed']}**",
        f"- 총 비용: **${summary['total_cost_usd']:.4f}** (cap $1.00, 사용 {summary['slice_cap_used_pct']}%)",
        f"- #48 v3 max_delta_predicted: **{summary['max_delta_predicted_pct']}%**",
        f"- #48 v3 max_delta_counted: **{summary['max_delta_counted_pct']}%** (count_tokens 명세 ≤ 2%)",
        f"- Fallback 발동: {summary['fallback_reason'] or '없음 (정상 종료)'}",
        "",
        "## §2. 케이스별 측정 표",
        "",
        "| # | entry | model | repeat | predicted | counted | actual | output | dlt_pred | dlt_cnt | latency_ms | cost | fitting |",
        "| - | ----- | ----- | ------ | --------- | ------- | ------ | ------ | -------- | ------- | ---------- | ---- | ------- |",
    ]
    for i, c in enumerate(cases, 1):
        if c.get("error") and "predicted_tokens" not in c:
            lines.append(
                f"| {i} | {c.get('entry','?')} | {c.get('model','?')[14:]} | #{c.get('repeat','?')} | "
                f"- | - | - | - | - | - | - | - | ERROR |"
            )
            continue
        lines.append(
            f"| {i} | {c['entry']} | {_model_label(c['model'])} | #{c['repeat']} | "
            f"{c['predicted_tokens']} | {c['counted_tokens']} | "
            f"{c['actual_input_tokens']} | {c['output_tokens']} | "
            f"{c['delta_predicted_pct']}% | {c['delta_counted_pct']}% | "
            f"{c['latency_ms']} | ${c['cost_usd']:.5f} | "
            f"{'PASS' if c['schema_fitting_pass'] else 'FAIL'} |"
        )

    lines += [
        "",
        "## §3. #48 v3 N=26 누적 판정",
        "",
    ]
    max_d = summary["max_delta_counted_pct"]
    if max_d <= 2.0:
        lines.append(f"- **견고화 PASS** (max_delta_counted = {max_d}% ≤ 2%, count_tokens 명세 한도)")
        lines.append("- Slice 12+ 자연 활용, #48 부채 완전 종결.")
    elif max_d <= 10.0:
        lines.append(f"- **보수 PASS** (2% < {max_d}% ≤ 10%)")
        lines.append("- v3 정착 유지, Slice 12 모니터링.")
    else:
        lines.append(f"- **FAIL** (max_delta_counted = {max_d}% > 10%)")
        lines.append("- #48 재오픈, Slice 12 Step 0 후보 등록.")

    lines += [
        "",
        "## §4. schema fitting 실패 케이스",
        "",
    ]
    failed = [c for c in cases if not c.get("schema_fitting_pass")]
    if failed:
        for c in failed:
            lines.append(f"### {c.get('entry')}/{c.get('model','?')[14:]}/#{c.get('repeat')}")
            lines.append("")
            lines.append(f"- error: `{c.get('schema_fitting_error') or c.get('error','-')}`")
            if c.get("response_text"):
                lines.append("")
                lines.append("```")
                lines.append(c["response_text"][:2000])
                lines.append("```")
            lines.append("")
    else:
        lines.append("- 없음 (모든 케이스 PASS)")

    lines += [
        "",
        "## §5. LLM 응답 raw 텍스트 (Slice 11 #52 정책)",
        "",
    ]
    for i, c in enumerate(cases, 1):
        if not c.get("response_text"):
            continue
        lines.append(f"### Case {i} — {c['entry']}/{c['model']}/#{c['repeat']}")
        lines.append("")
        lines.append("```json")
        lines.append(c["response_text"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
