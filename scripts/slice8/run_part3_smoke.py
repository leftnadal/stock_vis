"""Slice 8 Part 3 §3 — Step 6 smoke: Haiku 1 call (baseline).

목적:
  - V2 prompt builder가 실제 LLM API에서 정상 동작
  - 단건 비용 < $0.03 (haiku 임계)
  - 답변 길이 ≥ 200자, action_items ≥ 1건
  - patterns score ≥ 3 (구체성 충족 신호)

사용:
  poetry run python scripts/slice8/run_part3_smoke.py

산출:
  docs/portfolio/coach/slice8/part3/step6_smoke_result.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Django setup (LLMClient는 django settings 사용)
import django

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from portfolio.llm.client import LLMClient  # noqa: E402
from portfolio.llm.cost_guard import CostGuard  # noqa: E402
from portfolio.prompts.e4.builder import build_e4_prompt_v2  # noqa: E402
from portfolio.schemas.e4_conversation import E4ConversationInput  # noqa: E402
from portfolio.tests.slice8.helpers.specificity_count import count_patterns  # noqa: E402

FIXTURE_PATH = ROOT / "portfolio/tests/fixtures/e4_conversation/S01_V1_tier1.json"
OUTPUT_PATH = ROOT / "docs/portfolio/coach/slice8/part3/step6_smoke_result.json"

# 임계
PER_CALL_HAIKU_USD = 0.03
ANSWER_MIN_LENGTH = 200
SCORE_MIN = 3


def main() -> int:
    # 1. CostGuard reset (Slice 8 #33: PER_INSTANCE=50/PER_SLICE=100)
    guard = CostGuard.get_instance()
    guard.reset_slice("slice8_part3_smoke", max_calls=10)

    # 2. fixture 로드
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    inp = E4ConversationInput.model_validate(fixture["input"])

    # 3. V2 prompt 생성
    system = __import__(
        "portfolio.prompts.e4.builder", fromlist=["build_v2_system_prompt"]
    ).build_v2_system_prompt()
    user = __import__(
        "portfolio.prompts.e4.builder", fromlist=["build_e4_user_prompt"]
    ).build_e4_user_prompt(inp)

    # 4. LLM 호출 (Haiku)
    client = LLMClient()
    response = client.complete(
        prompt=user,
        provider="anthropic",
        model="claude-haiku-4-5",
        max_tokens=2000,
        system=system,
    )

    # 5. 응답 파싱 (LLM 응답 text → E4ConversationOutput)
    # LLM은 JSON 형식으로 응답하도록 system prompt에 명시. 파싱 시도.
    answer_text = response.text
    try:
        parsed_raw = json.loads(answer_text)
    except json.JSONDecodeError:
        # 마크다운 펜스 제거 시도
        cleaned = answer_text.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:-1])
        try:
            parsed_raw = json.loads(cleaned)
        except json.JSONDecodeError as e:
            parsed_raw = {"parse_error": str(e), "raw_text": answer_text}

    # 6. patterns score (commentary 본문에 적용)
    answer_body = parsed_raw.get("answer", "") if isinstance(parsed_raw, dict) else ""
    patterns_score = count_patterns(answer_body)

    # 7. 4판정
    cost_pass = response.cost_usd <= PER_CALL_HAIKU_USD
    length_pass = len(answer_body) >= ANSWER_MIN_LENGTH
    actions_pass = (
        isinstance(parsed_raw, dict)
        and len(parsed_raw.get("action_items", []) or []) >= 1
    )
    score_pass = patterns_score >= SCORE_MIN

    result = {
        "scenario_id": fixture["scenario_id"],
        "model": response.model,
        "provider": response.provider,
        "cost_usd": response.cost_usd,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
        "raw_text": answer_text,
        "parsed": parsed_raw,
        "answer_length": len(answer_body),
        "patterns_score": patterns_score,
        "kpi_4판정": {
            "cost_pass": cost_pass,
            "length_pass": length_pass,
            "actions_pass": actions_pass,
            "score_pass": score_pass,
        },
        "all_pass": all([cost_pass, length_pass, actions_pass, score_pass]),
        "thresholds": {
            "per_call_haiku_usd": PER_CALL_HAIKU_USD,
            "answer_min_length": ANSWER_MIN_LENGTH,
            "score_min": SCORE_MIN,
        },
        "cumulative": guard.status(),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 8. 콘솔 요약
    print(f"=== Step 6 smoke result ===")
    print(f"scenario: {fixture['scenario_id']} ({fixture['description']})")
    print(f"model: {response.model}")
    print(f"cost: ${response.cost_usd:.6f} (임계 ${PER_CALL_HAIKU_USD})")
    print(f"answer_length: {len(answer_body)} (임계 ≥ {ANSWER_MIN_LENGTH})")
    print(
        f"action_items: {len(parsed_raw.get('action_items', []) or []) if isinstance(parsed_raw, dict) else 0}"
    )
    print(f"patterns_score: {patterns_score}/5 (임계 ≥ {SCORE_MIN})")
    print(f"all_pass: {result['all_pass']}")
    print(f"output: {OUTPUT_PATH.relative_to(ROOT)}")

    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
