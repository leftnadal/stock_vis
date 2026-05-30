"""Slice 9 Part 1 §2 — Sonnet 26건 rationale batch 진행.

D2 batch 분할: 5건씩 6회 (마지막은 1건).
D3 단건 임계 자동 동시 적용: Sonnet < $0.10/건.
각 batch 종료 시 CostGuard cap 검증.

지시서 §1.1 코드 스켈레톤을 현재 코드베이스 인터페이스에 맞춰 적응:
- LLMClient(): no args. complete(prompt, provider="anthropic", model=..., system=..., max_tokens=...)
- estimate_input_tokens(prompt: str): 단일 인자, prompt = system + "\\n\\n" + user
- matrix_summary.json의 results 키에서 26 entries 로드
- E4PortfolioCommentary.parsed.answer를 commentary 본문으로 사용

사용:
    python scripts/slice9/run_part1_rationale_batch.py

실제 LLM API 호출 26회 + Sonnet 비용 $0.69 예상 (cap $1.00 마진 31%).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")

import django  # noqa: E402

django.setup()

from portfolio.llm.client import LLMClient  # noqa: E402
from portfolio.llm.cost_guard import (  # noqa: E402
    CostCapExceeded,
    CostGuard,
    CostThresholdExceeded,
)
from portfolio.llm.token_budgets import estimate_input_tokens  # noqa: E402
from portfolio.prompts.rationale.builder import build_rationale_prompt  # noqa: E402
from portfolio.schemas.rationale import RationaleBatch, RationaleRecord  # noqa: E402
from portfolio.tests.helpers.matrix_loader import (  # noqa: E402
    assign_case_ids,
    get_commentary,
    load_matrix_cases,
)
from portfolio.tests.slice8.helpers.specificity_count import (  # noqa: E402
    count_patterns,
    detail_patterns,
)

OUTPUT_DIR = REPO_ROOT / "docs/portfolio/coach/slice9/part1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 5
SONNET_MODEL = "claude-sonnet-4-5"  # 코드베이스 default (matrix와 시드 일치)
PER_CALL_THRESHOLD = 0.10  # D3 단건 임계
MAX_OUTPUT_TOKENS = 1024
RATE_LIMIT_SLEEP_SEC = 0.5

DEFAULT_QUESTION = "내 포트폴리오를 4요소 기준으로 평가해줘"

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """LLM 응답에서 JSON 객체 추출. 코드 펜스 우선, 없으면 직접 parse."""
    if not text:
        raise ValueError("응답 텍스트 비어있음")

    match = _JSON_FENCE.search(text)
    if match:
        return json.loads(match.group(1))

    # plain JSON 시도
    text_stripped = text.strip()
    # 첫 번째 { 부터 마지막 } 사이 추출
    start = text_stripped.find("{")
    end = text_stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text_stripped[start : end + 1])

    raise ValueError(f"JSON 추출 실패: {text[:200]}...")


def make_batches(cases: list[dict]) -> list[list[dict]]:
    """5건씩 batch 분할 (마지막은 1건)."""
    batches = []
    for i in range(0, len(cases), BATCH_SIZE):
        batches.append(cases[i : i + BATCH_SIZE])
    return batches


def run_one_case(
    case: dict,
    case_id: str,
    client: LLMClient,
    guard: CostGuard,
) -> RationaleRecord:
    """단일 case에 대해 rationale 생성."""
    commentary = get_commentary(case)
    specificity_score = count_patterns(commentary)
    specificity_detail = detail_patterns(commentary)

    system, user = build_rationale_prompt(
        case_name=case_id,
        original_commentary=commentary,
        original_question=DEFAULT_QUESTION,
        specificity_detail=specificity_detail,
    )

    # #β2 estimator 예측 (실측 비교용) — system + user 합쳐 단일 prompt 추정
    estimated = estimate_input_tokens(system + "\n\n" + user)

    response = client.complete(
        prompt=user,
        provider="anthropic",
        model=SONNET_MODEL,
        system=system,
        max_tokens=MAX_OUTPUT_TOKENS,
    )

    # D3 단건 임계 검증 (cost_guard.record_cost 호출 전)
    if response.cost_usd > PER_CALL_THRESHOLD:
        raise ValueError(
            f"{case_id} 단건 임계 위반: ${response.cost_usd:.4f} > ${PER_CALL_THRESHOLD}"
        )

    # CostGuard 기록 (cap/threshold 위반 시 raise)
    guard.record_cost(response.cost_usd)

    parsed = _extract_json(response.text)

    return RationaleRecord(
        case_id=case_id,
        case_name=case.get("case", case_id),
        original_model=case.get("model", "unknown"),
        rationale_model=SONNET_MODEL,
        original_commentary=commentary,
        original_specificity_score=specificity_score,
        original_specificity_detail=specificity_detail,
        rationale_text=str(parsed.get("rationale_text", "")),
        rationale_categories=list(parsed.get("rationale_categories", []) or []),
        rationale_score=int(parsed.get("rationale_score", 0)),
        cost_usd=response.cost_usd,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        estimated_input_tokens=estimated,
    )


def run_batches() -> None:
    cases = load_matrix_cases()
    case_ids = assign_case_ids(cases)
    batches = make_batches(cases)
    batch_ids = make_batches(case_ids)

    client = LLMClient()
    guard = CostGuard.get_instance()
    guard.reset_for_slice("slice9_part1")

    records: list[RationaleRecord] = []
    batch_logs: list[RationaleBatch] = []

    print(f"Slice 9 Part 1 batch 진행 시작 — {len(cases)} cases, {len(batches)} batches")
    print(f"Model: {SONNET_MODEL}")
    print(f"Cap: ${guard.cap_per_slice:.2f}, Threshold: ${guard.threshold:.2f}")
    print(f"Cumulative before: ${guard.cumulative_usd:.4f}")

    for batch_idx, (batch, ids) in enumerate(zip(batches, batch_ids), start=1):
        batch_start_cost = guard.slice_usd
        completed = 0
        aborted = False

        print(f"\n=== Batch {batch_idx}/{len(batches)} ({len(batch)} cases) ===")

        for case, case_id in zip(batch, ids):
            try:
                record = run_one_case(case, case_id, client, guard)
                records.append(record)
                completed += 1
                print(
                    f"  {case_id} ({record.original_model.replace('claude-','')}): "
                    f"score={record.rationale_score}, "
                    f"cost=${record.cost_usd:.4f}, "
                    f"slice_usd=${guard.slice_usd:.4f}"
                )
                time.sleep(RATE_LIMIT_SLEEP_SEC)
            except (CostCapExceeded, CostThresholdExceeded, ValueError) as e:
                print(f"  ❌ {case_id}: {e}")
                aborted = True
                break

        batch_log = RationaleBatch(
            batch_id=batch_idx,
            case_ids=ids,
            completed_count=completed,
            batch_cost_usd=guard.slice_usd - batch_start_cost,
            slice_cost_after_batch=guard.slice_usd,
            cap_warning_triggered=bool(guard.check_warnings()),
            aborted=aborted,
        )
        batch_logs.append(batch_log)

        warnings = guard.check_warnings()
        if warnings:
            for w in warnings:
                print(f"  ⚠ {w}")
            if guard.slice_usd >= guard.cap_warning:
                print(f"  ⚠ Cap 경고 도달 — 다음 batch 진입 전 사용자 확인 필요")

        if aborted:
            print(f"\n❌ Batch {batch_idx} 정지. 잔여 batch 건너뜀.")
            break

    # 저장
    (OUTPUT_DIR / "rationale_records.json").write_text(
        json.dumps([r.model_dump() for r in records], ensure_ascii=False, indent=2)
    )
    (OUTPUT_DIR / "batch_logs.json").write_text(
        json.dumps([b.model_dump() for b in batch_logs], ensure_ascii=False, indent=2)
    )

    print("\n=== 완료 ===")
    print(f"Total records: {len(records)}/{len(cases)}")
    print(f"Slice cost: ${guard.slice_usd:.4f} / cap ${guard.cap_per_slice:.2f}")
    print(f"Cumulative cost: ${guard.cumulative_usd:.4f} / threshold ${guard.threshold:.2f}")


if __name__ == "__main__":
    run_batches()
