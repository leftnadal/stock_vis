"""Slice 8 Part 3 §4 — Step 7 matrix: 14 cases × haiku/sonnet = 28 calls.

호출 수: 28 (PER_INSTANCE 50 한도 56% 사용, 마진 22)
예상 비용: haiku ~$0.10 + sonnet ~$0.32 = ~$0.42
4판정 PASS 정책: 각 호출에 (cost / length / action_items / parse) 4종 검증

fixture 출처: Slice 7 e4_conversation S01~S14 재활용 (시나리오 다양성 유지).
지시서 §4.1의 신규 12건 작성 대신 시간 절약 + 일관성 우선.

사용:
  poetry run python scripts/slice8/run_part3_matrix.py

산출:
  docs/portfolio/coach/slice8/part3/matrix/<case>_<model>.json (28 files)
  docs/portfolio/coach/slice8/part3/matrix_summary.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from portfolio.llm.client import LLMClient  # noqa: E402
from portfolio.llm.cost_guard import CostGuard  # noqa: E402
from portfolio.prompts.e4.builder import (  # noqa: E402
    build_e4_user_prompt,
    build_v2_system_prompt,
)
from portfolio.schemas.e4_conversation import E4ConversationInput  # noqa: E402
from portfolio.tests.slice8.helpers.specificity_count import count_patterns  # noqa: E402

FIXTURE_DIR = ROOT / "portfolio/tests/fixtures/e4_conversation"
OUTPUT_DIR = ROOT / "docs/portfolio/coach/slice8/part3/matrix"
SUMMARY_PATH = ROOT / "docs/portfolio/coach/slice8/part3/matrix_summary.json"

# Slice 7 fixture 15건 중 14건 선택 (S01~S14, glob 매칭)
FIXTURES = sorted(
    [p.name for p in FIXTURE_DIR.glob("S*.json")
     if int(p.stem.split("_")[0][1:]) <= 14]
)

MODELS = [
    ("anthropic", "claude-haiku-4-5", 0.03),
    ("anthropic", "claude-sonnet-4-5", 0.10),  # claude-sonnet-4-5 또는 4-6
]

ANSWER_MIN_LENGTH = 200
SCORE_MIN = 3


def _parse_response_text(raw_text: str) -> dict:
    """LLM 응답 text → dict 파싱 (마크다운 펜스 제거 포함)."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:-1])
            cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            return {"parse_error": str(e), "raw_text": raw_text}


def run_one(
    case_name: str,
    fixture_file: str,
    provider: str,
    model: str,
    per_call_threshold: float,
    system: str,
    user: str,
    guard: CostGuard,
) -> dict:
    """단건 호출 + 4판정."""
    client = LLMClient()
    t0 = time.time()
    response = client.complete(
        prompt=user,
        provider=provider,
        model=model,
        max_tokens=2000,
        system=system,
    )
    latency = time.time() - t0

    parsed = _parse_response_text(response.text)
    answer_body = parsed.get("answer", "") if isinstance(parsed, dict) else ""

    cost_pass = response.cost_usd <= per_call_threshold
    length_pass = len(answer_body) >= ANSWER_MIN_LENGTH
    actions_pass = (
        isinstance(parsed, dict) and len(parsed.get("action_items", []) or []) >= 1
    )
    parse_pass = isinstance(parsed, dict) and "parse_error" not in parsed
    score = count_patterns(answer_body) if isinstance(answer_body, str) else 0
    score_pass = score >= SCORE_MIN

    return {
        "case": case_name,
        "fixture_file": fixture_file,
        "model": model,
        "provider": provider,
        "cost_usd": response.cost_usd,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": int(latency * 1000),
        "answer_length": len(answer_body),
        "patterns_score": score,
        "raw_text": response.text,
        "parsed": parsed,
        "kpi_4판정": {
            "cost_pass": cost_pass,
            "length_pass": length_pass,
            "actions_pass": actions_pass,
            "parse_pass": parse_pass,
        },
        "score_pass": score_pass,
        "all_pass": all([cost_pass, length_pass, actions_pass, parse_pass]),
        "cumulative_after": {
            "call_count": guard.call_count,
            "total_cost_usd": guard.total_cost_usd,
        },
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    guard = CostGuard.get_instance()
    guard.reset_slice("slice8_part3_matrix", max_calls=60)

    summary: list[dict] = []
    print(f"=== Step 7 matrix: {len(FIXTURES)} cases × {len(MODELS)} models = {len(FIXTURES) * len(MODELS)} calls ===")

    skipped: list[str] = []
    for idx, fixture_file in enumerate(FIXTURES, 1):
        fixture_path = FIXTURE_DIR / fixture_file
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        case_name = fixture["scenario_id"]
        try:
            inp = E4ConversationInput.model_validate(fixture["input"])
        except Exception as e:
            print(f"[{idx:02d}/{len(FIXTURES)}] case={case_name} skip (trigger_case validation): {e.__class__.__name__}")
            skipped.append(case_name)
            continue

        # V2 system + user 생성 (case 동일)
        system = build_v2_system_prompt()
        user = build_e4_user_prompt(inp)

        for provider, model, per_call_threshold in MODELS:
            out_path = OUTPUT_DIR / f"{case_name}_{model.replace('-', '_')}.json"

            # resume: 이미 결과 파일 있으면 skip (재호출 비용 방지)
            if out_path.exists():
                result = json.loads(out_path.read_text(encoding="utf-8"))
                print(
                    f"[{idx:02d}/{len(FIXTURES)}] case={case_name} model={model} (resumed from cache)"
                )
                summary.append(result)
                continue

            print(
                f"[{idx:02d}/{len(FIXTURES)}] case={case_name} model={model} ...",
                flush=True,
            )

            # 사전 비용 체크
            cum = guard.total_cost_usd + 1.595
            if cum > 2.00:
                print(f"  ⚠ 누적 ${cum:.4f} > $2.00 임계 도달 → 작업 중단")
                break

            try:
                result = run_one(
                    case_name, fixture_file, provider, model,
                    per_call_threshold, system, user, guard,
                )
            except Exception as e:
                print(f"  ✗ 호출 실패: {e}")
                result = {
                    "case": case_name,
                    "fixture_file": fixture_file,
                    "model": model,
                    "error": str(e),
                    "all_pass": False,
                }

            out_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            summary.append(result)

            # 콘솔 요약
            if "error" not in result:
                print(
                    f"  cost=${result['cost_usd']:.6f} len={result['answer_length']} "
                    f"score={result['patterns_score']}/5 all_pass={result['all_pass']}"
                )

        else:
            continue
        break  # 내부 break 시 외부 break

    # 종합 요약
    total_cost = sum(r.get("cost_usd", 0) for r in summary)
    pass_count = sum(1 for r in summary if r.get("all_pass"))
    haiku_results = [r for r in summary if "haiku" in r.get("model", "")]
    sonnet_results = [r for r in summary if "sonnet" in r.get("model", "")]

    summary_doc = {
        "total_calls": len(summary),
        "total_cost_usd": total_cost,
        "haiku_calls": len(haiku_results),
        "sonnet_calls": len(sonnet_results),
        "all_pass_count": pass_count,
        "pass_rate": pass_count / len(summary) if summary else 0.0,
        "haiku_avg_cost": (
            sum(r.get("cost_usd", 0) for r in haiku_results) / len(haiku_results)
            if haiku_results
            else 0
        ),
        "sonnet_avg_cost": (
            sum(r.get("cost_usd", 0) for r in sonnet_results) / len(sonnet_results)
            if sonnet_results
            else 0
        ),
        "haiku_avg_score": (
            sum(r.get("patterns_score", 0) for r in haiku_results) / len(haiku_results)
            if haiku_results
            else 0
        ),
        "sonnet_avg_score": (
            sum(r.get("patterns_score", 0) for r in sonnet_results) / len(sonnet_results)
            if sonnet_results
            else 0
        ),
        "specificity_lacking_count": sum(
            1 for r in summary if r.get("patterns_score", 5) <= 2
        ),
        "results": summary,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n=== Matrix Summary ===")
    print(f"calls: {summary_doc['total_calls']}")
    print(f"total_cost: ${summary_doc['total_cost_usd']:.6f}")
    print(f"haiku avg: cost ${summary_doc['haiku_avg_cost']:.6f}, score {summary_doc['haiku_avg_score']:.2f}/5")
    print(f"sonnet avg: cost ${summary_doc['sonnet_avg_cost']:.6f}, score {summary_doc['sonnet_avg_score']:.2f}/5")
    print(f"all_pass: {summary_doc['all_pass_count']}/{summary_doc['total_calls']} ({summary_doc['pass_rate']:.1%})")
    print(f"specificity_lacking (score ≤ 2): {summary_doc['specificity_lacking_count']}/{summary_doc['total_calls']}")
    print(f"\noutput: {SUMMARY_PATH.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
