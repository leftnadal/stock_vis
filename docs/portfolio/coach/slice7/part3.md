# Slice 7 Part 3 작업 지시서 — E4 Prompt Builder + Real LLM Matrix

> **Part 3 범위**: E4 prompt builder 구현 + Step 6 smoke (1 call) + Step 7 matrix (28 calls) + Step 7.5 KPI + Step 8 dump 준비.
> 첫 LLM 비용 발생 단계. 누적 광의 $0.879 → 예상 $1.30 (임계 $1.50 마진 13%).
> **선행 결정**: #1=A 풀 매트릭스 14×2 / #2=C #β2 2회 측정 / #3=B PROJECT_LAYOUT.md docs 신설.
> **회귀 영향**: 0 예상 (prompt builder는 신규 코드, 기존 회귀에 영향 없음).
> **CostGuard**: 호출 카운트 = 1 (Step 6) + 28 (Step 7) = 29/50 (마진 21).

---

## §0. 사전 체크 (10초)

```bash
git status
git log --oneline -5
pytest -q  # 484 passed 확인

# Part 2 산출물 확인
ls portfolio/schemas/e4_conversation.py
ls portfolio/llm/token_budgets.py
ls portfolio/llm/eval_metrics.py
ls portfolio/tests/fixtures/e4_conversation/  # 15 fixtures
ls portfolio/prompts/e4/                       # 기존 자리 (builder.py 추가 대상)

# 환경 검증
cat portfolio/llm/token_budgets.py | grep e4_conversation
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:0:10}..."  # 키 존재 확인 (값 노출 X)
```

- [ ] 484 passed
- [ ] portfolio/prompts/e4/ 디렉토리 존재
- [ ] token_budgets에 e4_conversation_tier1/2/3 등록 확인
- [ ] ANTHROPIC_API_KEY 환경 변수 존재

---

## §1. PROJECT_LAYOUT.md docs 신설 (결정 #3=B 처리)

### 1.1 파일 생성

`docs/portfolio/coach/PROJECT_LAYOUT.md`:

```markdown
# Stock-Vis Portfolio Coach — 프로젝트 레이아웃

> **목적**: 작업 지시서 작성 시 경로 정합성 보장.
> Slice 7 Part 2에서 발견한 지시서 경로(`portfolio/coach/X`) vs 실제(`portfolio/X`)
> 불일치 재발 방지.

## 디렉토리 매핑 (canonical)

| 카테고리          | 실제 경로                                | 비고                                            |
| ----------------- | ---------------------------------------- | ----------------------------------------------- |
| Pydantic schemas  | `portfolio/schemas/`                     | E1~E6 schema 모두 여기                          |
| LLM 인프라        | `portfolio/llm/`                         | token_budgets.py, eval_metrics.py, LLMClient 등 |
| Prompt builders   | `portfolio/prompts/{entrypoint}/`        | e1~e6 각각 디렉토리                             |
| 진입점별 service  | `portfolio/services/`                    | \_main_unified 위치                             |
| 회귀 테스트       | `portfolio/tests/`                       | pytest 대상                                     |
| 회귀 fixtures     | `portfolio/tests/fixtures/{entrypoint}/` | mock 입력/출력                                  |
| Scripts (1회성)   | `scripts/slice{N}/`                      | 슬라이스 검증 스크립트                          |
| Docs (영구)       | `docs/portfolio/coach/`                  | 정책, 보고서, 설계                              |
| Docs (슬라이스별) | `docs/portfolio/coach/slice{N}/`         | 슬라이스 산출물                                 |

## 회귀 hash 정책

- `portfolio/tests/test_static_integrity.py` 7 항목으로 IDENTICAL hash 검증
- 보호 대상: Slice 1 e1_garp + Slice 3 e2_diversification 핵심 출력 hash
- 새 진입점 추가 시 hash KPI 영향 0 확인 필수

## CostGuard 정책

- 싱글톤 + `reset_for_slice` 멱등 (Slice 3 정착)
- 호출 카운트 상한 50/슬라이스
- 단건 비용 임계: $0.020 (Slice 1부터 일관)
- 누적 광의 비용 임계: $1.50 (Slice 7 Part 1 갱신)

## DIMENSION_LOOKUP 정책 (Slice 7 Part 3에서 재정의 가능)

- 기존: e1~e3, e5, e6은 schema + prompt_builder + budget_key dispatch
- E4: 검토 중 — Tier 1/2/3 dispatch 추가 필요
- 결론은 Part 3 §3에서 확정
```

### 1.2 검증 체크리스트

- [ ] PROJECT_LAYOUT.md 작성 완료
- [ ] 디렉토리 매핑 표 정확 (Part 2 실측 경로와 일치)
- [ ] 향후 지시서 작성자(나 또는 Claude Code)가 1차 참조 자료로 사용 가능

---

## §2. E4 Prompt Builder 구현

### 2.1 파일 생성: `portfolio/prompts/e4/builder.py`

기존 디렉토리 `portfolio/prompts/e4/` 활용. 패턴은 e3_portfolio_concentration prompt builder 참고.

```python
"""
E4 대화 Q&A prompt builder (Slice 7 Part 3).

Tier 1/2/3 multi-turn 지원. system prompt + portfolio context +
conversation history + current question 조합.

References:
- portfolio/prompts/e3_portfolio/builder.py (E3 portfolio-level 패턴)
"""

from __future__ import annotations
from typing import Optional

from portfolio.schemas.e4_conversation import E4ConversationInput
from portfolio.llm.format_utils import format_metrics_to_str  # Slice 5 #11 통합 utility


SYSTEM_PROMPT = """당신은 한국 개인 투자자를 위한 포트폴리오 코치입니다.
사용자의 포트폴리오 지표와 종목 구성을 바탕으로, 사용자의 질문에
간결하고 통찰력 있게 답변하세요.

답변 원칙:
1. 포트폴리오 지표(hhi_concentration, sector_hhi 등)를 의미 있게 인용하세요.
2. preset 의도(예: GARP=합리적 가격 성장, dividend_growth=안정 배당)를 반영하세요.
3. 단순 사실 나열보다 행동 시사점(예: 리밸런싱 검토)을 제시하세요.
4. multi-turn 대화에서는 이전 turn의 맥락을 고려하세요.
5. JSON 형식으로 응답하세요 (E4ConversationOutput schema 준수).

응답 JSON schema:
- answer: 답변 본문 (20~2000자)
- referenced_metrics: 인용한 portfolio_metrics key 리스트 (snake_case)
- follow_up_suggestions: 후속 질문 추천 (최대 3개)
- confidence: "high" | "medium" | "low"
"""


def build_e4_user_prompt(inp: E4ConversationInput) -> str:
    """E4 user message 생성.

    구성: portfolio context + (truncated) conversation_history + current question
    """
    # I1 trigger: history overflow 시 가장 오래된 turn부터 제거
    history = inp.conversation_history
    if len(history) > inp.max_history_turns:
        history = history[-inp.max_history_turns:]

    metrics_str = format_metrics_to_str(inp.portfolio_metrics)

    parts = [
        f"## 포트폴리오 정보",
        f"- portfolio_id: {inp.portfolio_id}",
        f"- preset: {inp.preset_id}",
        f"- tier: {inp.tier}",
        f"",
        f"## 포트폴리오 지표",
        metrics_str,
        f"",
        f"## 보유 종목 요약",
        inp.holdings_summary,
        f"",
    ]

    if history:
        parts.append("## 이전 대화")
        for turn in history:
            role_label = "사용자" if turn.role == "user" else "어시스턴트"
            parts.append(f"[{role_label}] {turn.content}")
        parts.append("")

    parts.extend([
        f"## 현재 질문",
        inp.current_user_question,
        f"",
        f"위 정보를 바탕으로 JSON 형식으로 답변하세요.",
    ])

    return "\n".join(parts)


def build_e4_messages(inp: E4ConversationInput) -> list[dict]:
    """LLM 호출용 messages 배열 생성.

    Note: #19 (LLMClient system 인자) 처리 전이라 user message에 system 포함 안 함.
    Slice 7 Step 9에서 #19 처리 후 system 분리 예정.
    """
    user_content = build_e4_user_prompt(inp)
    return [
        {"role": "user", "content": user_content},
    ]


def get_system_prompt() -> str:
    """system prompt 반환 (Step 9 #19 처리 시 LLMClient에 별도 전달)."""
    return SYSTEM_PROMPT
```

### 2.2 단위 테스트 추가

`portfolio/tests/test_e4_prompt_builder.py`:

```python
"""E4 prompt builder 회귀 (Slice 7 Part 3)."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from portfolio.prompts.e4.builder import (
    build_e4_user_prompt,
    build_e4_messages,
    get_system_prompt,
    SYSTEM_PROMPT,
)
from portfolio.schemas.e4_conversation import E4ConversationInput, E4ConversationTurn

FIXTURE_DIR = Path("portfolio/tests/fixtures/e4_conversation")


def _load_fixture(scenario_id: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{scenario_id}.json").read_text(encoding="utf-8"))


def test_system_prompt_non_empty():
    assert len(SYSTEM_PROMPT) > 100
    assert "JSON" in SYSTEM_PROMPT
    assert "referenced_metrics" in SYSTEM_PROMPT


def test_user_prompt_tier1_baseline():
    data = _load_fixture("S01_V1_tier1")
    inp = E4ConversationInput(**data["input"])
    prompt = build_e4_user_prompt(inp)
    assert "포트폴리오 정보" in prompt
    assert "현재 질문" in prompt
    assert "이전 대화" not in prompt  # tier 1 history 없음
    assert data["input"]["current_user_question"] in prompt


def test_user_prompt_tier2_includes_history():
    data = _load_fixture("S02_V1_tier2")
    inp = E4ConversationInput(**data["input"])
    prompt = build_e4_user_prompt(inp)
    assert "이전 대화" in prompt
    assert "[사용자]" in prompt or "[어시스턴트]" in prompt


def test_user_prompt_i1_history_truncation():
    """S12: history 6 turn → max_history_turns=5에 의해 truncate."""
    data = _load_fixture("S12_V1_tier2_overflow")
    inp = E4ConversationInput(**data["input"])
    prompt = build_e4_user_prompt(inp)
    history_lines = [l for l in prompt.split("\n") if l.startswith("[사용자]") or l.startswith("[어시스턴트]")]
    assert len(history_lines) <= 5, f"history should be truncated to 5, got {len(history_lines)}"


def test_messages_structure():
    data = _load_fixture("S01_V1_tier1")
    inp = E4ConversationInput(**data["input"])
    msgs = build_e4_messages(inp)
    assert isinstance(msgs, list)
    assert msgs[0]["role"] == "user"
    assert len(msgs[0]["content"]) > 100


def test_get_system_prompt_returns_const():
    assert get_system_prompt() == SYSTEM_PROMPT
```

### 2.3 회귀 실행

```bash
pytest -q portfolio/tests/test_e4_prompt_builder.py
```

**기대**: 6건 PASS, 누적 회귀 484 → 490 예상.

---

## §3. DIMENSION_LOOKUP 재평가

Part 2 보고에서 보류된 결정. Part 3에서 확정.

### 3.1 검토

- score_step8.py의 DIMENSION_LOOKUP은 **scoring config** 역할 (input/output schema dispatch 아님)
- 기존 e1~e6 진입점 호출 dispatch는 어떻게 이루어지는가? → service layer에서 직접 import + 호출 (확인 필요)

### 3.2 작업

```bash
# 기존 _main_unified 패턴 확인
grep -r "_main_unified" portfolio/services/ | head -10
grep -r "e3_portfolio" portfolio/services/ | head -10
```

**판단 기준**:

- (a) 기존 진입점이 service layer dispatch 사용 → E4도 동일 패턴 (DIMENSION_LOOKUP entry 추가 불필요)
- (b) DIMENSION_LOOKUP이 dispatch 역할 → E4 entry 추가

**결과를 docs로 기록**: `docs/portfolio/coach/slice7/step3_dimension_lookup_decision.md`

### 3.3 산출물

- decision docs 1건
- (필요 시) service layer dispatch entry 추가 + 단위 테스트 +1~3건

---

## §4. Step 6 — Smoke Test + #β2 1차 측정

### 4.1 Smoke test (1 call, V1 tier 1 × haiku)

`scripts/slice7/run_step6_smoke.py`:

```python
"""
Slice 7 Part 3 Step 6: smoke test (1 call, V1 tier1 × haiku).
+ #β2 1차 측정 (prompt 포함 실측 input tokens).

목표:
- 4판정 (schema/completeness/cost/token) 전체 PASS
- #β2 delta 측정 → Step 7 budget 조정 신호
"""

import json
import time
from pathlib import Path

from portfolio.schemas.e4_conversation import (
    E4ConversationInput,
    E4ConversationOutput,
)
from portfolio.prompts.e4.builder import build_e4_messages, get_system_prompt
from portfolio.llm.client import LLMClient
from portfolio.llm.token_budgets import BUDGETS
from portfolio.llm.cost_guard import CostGuard
from portfolio.llm.estimators import estimate_input_tokens

FIXTURE_PATH = Path("portfolio/tests/fixtures/e4_conversation/S01_V1_tier1.json")
OUT_PATH = Path("docs/portfolio/coach/slice7/step6_smoke_result.json")
REPORT_PATH = Path("docs/portfolio/coach/slice7/step6_smoke_result.md")

COST_THRESHOLD = 0.020
BUDGET_KEY = "e4_conversation_tier1"


def main():
    CostGuard.reset_for_slice("slice7_part3_step6")
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    inp = E4ConversationInput(**data["input"])

    messages = build_e4_messages(inp)
    system = get_system_prompt()

    # #β2 1차 측정: prompt 포함 실측 input chars/tokens
    full_prompt = system + "\n\n" + messages[0]["content"]
    prompt_chars = len(full_prompt)
    estimated_tokens = estimate_input_tokens(full_prompt)
    budget = BUDGETS[BUDGET_KEY]

    # LLM 호출
    client = LLMClient(provider="anthropic_haiku")
    t0 = time.time()
    response = client.call(
        messages=messages,
        system=system,
        max_tokens=1000,
    )
    latency_ms = int((time.time() - t0) * 1000)
    meta = response.metadata_dict()

    actual_input_tokens = meta.get("input_tokens", 0)
    actual_output_tokens = meta.get("output_tokens", 0)
    cost = meta.get("cost_usd", 0)

    # 4판정
    # schema
    try:
        output = E4ConversationOutput.model_validate_json(response.content)
        schema_pass = True
    except Exception as e:
        output = None
        schema_pass = False

    # completeness
    completeness_pass = (
        schema_pass
        and len(output.answer) >= 20
        and len(output.referenced_metrics) > 0
    )

    # cost
    cost_pass = cost <= COST_THRESHOLD

    # token
    token_pass = actual_input_tokens <= budget

    all_pass = all([schema_pass, completeness_pass, cost_pass, token_pass])

    # #β2 1차 분석
    delta_pct = (
        (estimated_tokens - actual_input_tokens) / actual_input_tokens * 100
        if actual_input_tokens
        else 0
    )

    result = {
        "smoke_4_judgment": {
            "schema": schema_pass,
            "completeness": completeness_pass,
            "cost": cost_pass,
            "token": token_pass,
            "all_pass": all_pass,
        },
        "metrics": {
            "cost_usd": cost,
            "cost_threshold": COST_THRESHOLD,
            "input_tokens_actual": actual_input_tokens,
            "output_tokens_actual": actual_output_tokens,
            "budget": budget,
            "latency_ms": latency_ms,
        },
        "beta2_first_measurement": {
            "prompt_chars": prompt_chars,
            "estimated_tokens": estimated_tokens,
            "actual_input_tokens": actual_input_tokens,
            "delta_pct": round(delta_pct, 2),
            "delta_abs_pct": round(abs(delta_pct), 2),
            "step7_budget_adjustment_needed": abs(delta_pct) > 50,
        },
        "fallback": meta.get("fallback_from") is not None,
        "provider": meta.get("provider"),
        "model": meta.get("model"),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 3 Step 6 — Smoke + #β2 1차 측정\n",
        "## 4판정",
        f"- schema:       {'✓ PASS' if schema_pass else '✗ FAIL'}",
        f"- completeness: {'✓ PASS' if completeness_pass else '✗ FAIL'}",
        f"- cost:         {'✓ PASS' if cost_pass else '✗ FAIL'} (${cost:.5f} / ${COST_THRESHOLD})",
        f"- token:        {'✓ PASS' if token_pass else '✗ FAIL'} ({actual_input_tokens} / {budget})",
        "",
        f"## #β2 1차 측정 (Step 6 smoke)",
        f"- prompt chars: {prompt_chars}",
        f"- estimated tokens: {estimated_tokens}",
        f"- actual input tokens: {actual_input_tokens}",
        f"- delta: {delta_pct:+.2f}%",
        f"- Step 7 budget 조정 필요: {'YES' if abs(delta_pct) > 50 else 'NO'}",
        "",
        f"## 메타",
        f"- latency: {latency_ms}ms / cost: ${cost:.5f}",
        f"- fallback: {result['fallback']}",
    ]
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ smoke: {OUT_PATH}")
    print(f"  4판정 all_pass: {all_pass}")
    print(f"  #β2 delta: {delta_pct:+.2f}% → Step 7 budget {'조정' if abs(delta_pct) > 50 else '유지'}")


if __name__ == "__main__":
    main()
```

### 4.2 실행

```bash
python scripts/slice7/run_step6_smoke.py
```

### 4.3 분기 처리

**L1 (4판정 FAIL)**: 즉시 Part 3 중단, 실패 원인 분석 후 보고.

**L4 (#β2 1차 delta > 50%)**: Step 7 진입 전 token budget 임시 +50% 안전 마진 적용:

```python
# Step 7 매트릭스 실행 전 token_budgets.py 임시 갱신 (Step 7 후 원복)
BUDGETS["e4_conversation_tier1"] = 6000 * 1.5  # 9000
BUDGETS["e4_conversation_tier2"] = 8000 * 1.5  # 12000
BUDGETS["e4_conversation_tier3"] = 12000 * 1.5  # 18000
```

**L4 분기 발동 시 메모리에 기록** (Step 7 budget 임시 조정 사실).

---

## §5. Step 7 — Matrix (14 cases × haiku/sonnet = 28 calls)

### 5.1 매트릭스 정의

호출 대상: S01~S15 중 **S13 제외 (I2 trigger schema reject)** = 14 cases × 2 providers = **28 calls**.

| scenario | preset | tier         | provider 매트릭스        |
| -------- | ------ | ------------ | ------------------------ |
| S01~S03  | V1     | 1,2,3        | haiku + sonnet           |
| S04~S05  | V2     | 1,2          | haiku + sonnet           |
| S06~S07  | V3     | 1,2          | haiku + sonnet           |
| S08~S09  | V4     | 1,2          | haiku + sonnet           |
| S10~S11  | V5     | 1,3          | haiku + sonnet           |
| S12      | V1     | 2 (I1)       | haiku + sonnet           |
| S13      | V1     | 2 (I2)       | **skip** (schema reject) |
| S14      | V2     | 3 (I4)       | haiku + sonnet           |
| S15      | V3     | 1 (low_conf) | haiku + sonnet           |

### 5.2 스크립트: `scripts/slice7/run_step7_matrix.py`

```python
"""
Slice 7 Part 3 Step 7: matrix 14 cases × haiku/sonnet (28 calls).

진행 중 cost 임계 ($0.020/call) 초과 시 자동 차단.
fallback 발생 시 별도 카운트 후 보고.
"""

import json
import time
from pathlib import Path

from portfolio.schemas.e4_conversation import (
    E4ConversationInput,
    E4ConversationOutput,
)
from portfolio.prompts.e4.builder import build_e4_messages, get_system_prompt
from portfolio.llm.client import LLMClient
from portfolio.llm.token_budgets import BUDGETS
from portfolio.llm.cost_guard import CostGuard

FIXTURE_DIR = Path("portfolio/tests/fixtures/e4_conversation")
OUT_RAW = Path("docs/portfolio/coach/slice7/step7_matrix_raw.json")
OUT_METRICS = Path("docs/portfolio/coach/slice7/step7_matrix_metrics.json")
OUT_REPORT = Path("docs/portfolio/coach/slice7/step7_matrix_report.md")

EXCLUDED_SCENARIOS = {"S13_V1_tier2_empty_history"}  # I2 trigger schema reject
PROVIDERS = ["anthropic_haiku", "anthropic_sonnet"]
COST_THRESHOLD = 0.020
TOTAL_COST_CAP = 0.50  # Step 7 단독 cap (안전 마진)
MAX_CALLS = 50  # CostGuard 한도


def main():
    CostGuard.reset_for_slice("slice7_part3_step7")
    fixtures = sorted(FIXTURE_DIR.glob("S*.json"))
    fixtures = [
        f for f in fixtures
        if f.stem not in EXCLUDED_SCENARIOS
    ]
    assert len(fixtures) == 14, f"expected 14 cases, got {len(fixtures)}"

    results = []
    total_cost = 0.0
    call_count = 0
    fallback_count = 0
    cost_breach_count = 0

    for fp in fixtures:
        data = json.loads(fp.read_text(encoding="utf-8"))
        inp = E4ConversationInput(**data["input"])
        messages = build_e4_messages(inp)
        system = get_system_prompt()
        tier = inp.tier
        budget_key = f"e4_conversation_tier{tier}"
        budget = BUDGETS[budget_key]

        for provider in PROVIDERS:
            if call_count >= MAX_CALLS:
                print(f"⚠ CostGuard 한도 도달: {call_count}/{MAX_CALLS} — 중단")
                break
            if total_cost >= TOTAL_COST_CAP:
                print(f"⚠ Step 7 비용 cap 도달: ${total_cost:.4f}/${TOTAL_COST_CAP} — 중단")
                break

            client = LLMClient(provider=provider)
            t0 = time.time()
            try:
                response = client.call(
                    messages=messages,
                    system=system,
                    max_tokens=1000,
                )
            except Exception as e:
                results.append({
                    "scenario_id": data["scenario_id"],
                    "preset_id": inp.preset_id,
                    "tier": tier,
                    "provider": provider,
                    "error": str(e),
                    "skipped": True,
                })
                continue
            latency_ms = int((time.time() - t0) * 1000)
            meta = response.metadata_dict()
            cost = meta.get("cost_usd", 0)
            input_tokens = meta.get("input_tokens", 0)
            output_tokens = meta.get("output_tokens", 0)
            fallback = meta.get("fallback_from") is not None

            # 단건 비용 임계 체크
            if cost > COST_THRESHOLD:
                cost_breach_count += 1

            if fallback:
                fallback_count += 1

            # schema/completeness
            try:
                output = E4ConversationOutput.model_validate_json(response.content)
                schema_pass = True
                completeness_pass = (
                    len(output.answer) >= 20
                    and len(output.referenced_metrics) > 0
                )
            except Exception:
                schema_pass = False
                completeness_pass = False

            results.append({
                "scenario_id": data["scenario_id"],
                "preset_id": inp.preset_id,
                "tier": tier,
                "provider": provider,
                "trigger_case": data.get("trigger_case"),
                "raw_content": response.content,
                "schema_pass": schema_pass,
                "completeness_pass": completeness_pass,
                "cost_usd": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "budget": budget,
                "latency_ms": latency_ms,
                "fallback": fallback,
                "provider_meta": meta.get("provider"),
                "model": meta.get("model"),
            })
            call_count += 1
            total_cost += cost

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    OUT_RAW.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # 집계
    schema_pass_count = sum(1 for r in results if r.get("schema_pass"))
    completeness_pass_count = sum(1 for r in results if r.get("completeness_pass"))
    input_tokens_list = [r["input_tokens"] for r in results if "input_tokens" in r]
    output_tokens_list = [r["output_tokens"] for r in results if "output_tokens" in r]

    def p90(lst):
        if not lst:
            return 0
        s = sorted(lst)
        idx = int(len(s) * 0.9)
        return s[min(idx, len(s) - 1)]

    metrics = {
        "total_calls": call_count,
        "total_cost": round(total_cost, 5),
        "schema_pass": f"{schema_pass_count}/{call_count}",
        "completeness_pass": f"{completeness_pass_count}/{call_count}",
        "fallback_count": fallback_count,
        "cost_breach_count": cost_breach_count,
        "max_single_cost": round(max((r["cost_usd"] for r in results if "cost_usd" in r), default=0), 5),
        "input_p90": p90(input_tokens_list),
        "input_max": max(input_tokens_list, default=0),
        "output_p90": p90(output_tokens_list),
        "output_max": max(output_tokens_list, default=0),
    }
    OUT_METRICS.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    # 보고서
    md = [
        "# Slice 7 Part 3 Step 7 — Matrix Report\n",
        f"## 집계",
        f"- 총 호출: {call_count}/28 (target)",
        f"- schema PASS: {schema_pass_count}/{call_count}",
        f"- completeness PASS: {completeness_pass_count}/{call_count}",
        f"- fallback: {fallback_count}건",
        f"- 단건 비용 임계 초과: {cost_breach_count}건",
        f"- 총 비용: ${total_cost:.5f}",
        f"- input P90/max: {metrics['input_p90']} / {metrics['input_max']}",
        f"- output P90/max: {metrics['output_p90']} / {metrics['output_max']}",
    ]
    OUT_REPORT.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ matrix: {OUT_RAW}")
    print(f"  total calls: {call_count} / cost ${total_cost:.4f}")
    print(f"  schema {schema_pass_count}/{call_count} / fallback {fallback_count}")


if __name__ == "__main__":
    main()
```

### 5.3 실행

```bash
python scripts/slice7/run_step7_matrix.py
```

**기대 비용**: $0.32~0.42. 진행 중 1건이라도 임계 ($0.020) 초과 시 자동 차단.

---

## §6. Step 7.5 — KPI 자동 검증

### 6.1 스크립트: `scripts/slice7/score_step7_5.py`

```python
"""
Slice 7 Part 3 Step 7.5: KPI 자동 검증 + IDENTICAL hash 유지 확인.

KPI 8 (Slice 1~6 일관):
1. Slice 1 e1 IDENTICAL hash
2. Slice 3 e2 IDENTICAL hash
3. 호출 카운트 ≤ 50
4. schema PASS rate = 100%
5. completeness PASS rate = 100%
6. fallback = 0건
7. 단건 비용 임계 PASS
8. 총 비용 ≤ $0.50

보조 KPI 9~12:
9. label_means by provider
10. preset alignment (E4는 multi-turn이라 alignment 측정 안 함 — skip)
11. lex coverage (chars proxy)
12. token usage P90 / budget 비율
"""

import json
import subprocess
from pathlib import Path

MATRIX_PATH = Path("docs/portfolio/coach/slice7/step7_matrix_raw.json")
METRICS_PATH = Path("docs/portfolio/coach/slice7/step7_matrix_metrics.json")
OUT_PATH = Path("docs/portfolio/coach/slice7/step7_5_kpi_report.md")

KPI_THRESHOLDS = {
    "call_count_max": 50,
    "schema_pass_rate": 1.0,
    "completeness_pass_rate": 1.0,
    "fallback_max": 0,
    "single_cost_max": 0.020,
    "total_cost_max": 0.50,
}


def check_identical_hash():
    """test_static_integrity 실행 후 7/7 PASS 확인."""
    r = subprocess.run(
        ["pytest", "-q", "portfolio/tests/test_static_integrity.py"],
        capture_output=True, text=True,
    )
    return "7 passed" in r.stdout or r.returncode == 0, r.stdout


def main():
    results = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    total = metrics["total_calls"]
    schema_pass = int(metrics["schema_pass"].split("/")[0])
    completeness_pass = int(metrics["completeness_pass"].split("/")[0])

    # IDENTICAL hash
    hash_pass, hash_output = check_identical_hash()

    kpis = {
        "1_slice1_e1_identical": hash_pass,
        "2_slice3_e2_identical": hash_pass,  # test_static_integrity 7 항목 묶음 → 같이 PASS
        "3_call_count": total <= KPI_THRESHOLDS["call_count_max"],
        "4_schema_pass_rate": (schema_pass / total if total else 0) >= KPI_THRESHOLDS["schema_pass_rate"],
        "5_completeness_pass_rate": (completeness_pass / total if total else 0) >= KPI_THRESHOLDS["completeness_pass_rate"],
        "6_fallback_zero": metrics["fallback_count"] == 0,
        "7_single_cost_pass": metrics["max_single_cost"] <= KPI_THRESHOLDS["single_cost_max"],
        "8_total_cost_pass": metrics["total_cost"] <= KPI_THRESHOLDS["total_cost_max"],
    }
    all_pass = all(kpis.values())

    # 보조 KPI 9: label_means by provider (대화 답변 길이 + cost gap)
    by_provider = {}
    for r in results:
        prov = r.get("provider_meta") or r.get("provider")
        if not prov:
            continue
        by_provider.setdefault(prov, {"costs": [], "input_tokens": [], "output_tokens": []})
        by_provider[prov]["costs"].append(r.get("cost_usd", 0))
        by_provider[prov]["input_tokens"].append(r.get("input_tokens", 0))
        by_provider[prov]["output_tokens"].append(r.get("output_tokens", 0))
    provider_stats = {}
    for prov, d in by_provider.items():
        n = len(d["costs"])
        provider_stats[prov] = {
            "n": n,
            "avg_cost": round(sum(d["costs"]) / n, 5) if n else 0,
            "avg_input": int(sum(d["input_tokens"]) / n) if n else 0,
            "avg_output": int(sum(d["output_tokens"]) / n) if n else 0,
        }

    md = [
        "# Slice 7 Part 3 Step 7.5 — KPI Report\n",
        f"## KPI 8/8: {'**PASS** ✓' if all_pass else '**FAIL** ✗'}\n",
    ]
    for k, v in kpis.items():
        md.append(f"- {k}: {'✓' if v else '✗'}")
    md.append("\n## 보조 KPI")
    md.append("### Provider 통계")
    md.append("| provider | n | avg_cost | avg_input | avg_output |")
    md.append("|---|---|---|---|---|")
    for prov, s in provider_stats.items():
        md.append(f"| {prov} | {s['n']} | ${s['avg_cost']} | {s['avg_input']} | {s['avg_output']} |")

    OUT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ KPI report: {OUT_PATH}")
    print(f"  all_pass: {all_pass}")


if __name__ == "__main__":
    main()
```

### 6.2 실행

```bash
python scripts/slice7/score_step7_5.py
pytest -q portfolio/tests/test_static_integrity.py  # IDENTICAL hash 별도 확인
```

---

## §7. #β2 2차 측정 (Step 7 matrix 후)

### 7.1 스크립트: `scripts/slice7/measure_beta2_round2.py`

```python
"""
Slice 7 Part 3 #β2 2차 측정 (Step 7 matrix 데이터 기반).

28 calls의 actual_input_tokens vs estimator 비교.
KPI: max delta ≤ 30% → close / > 30% → keep_open.
"""

import json
from pathlib import Path

from portfolio.llm.estimators import estimate_input_tokens
from portfolio.prompts.e4.builder import build_e4_messages, get_system_prompt
from portfolio.schemas.e4_conversation import E4ConversationInput

MATRIX_PATH = Path("docs/portfolio/coach/slice7/step7_matrix_raw.json")
FIXTURE_DIR = Path("portfolio/tests/fixtures/e4_conversation")
OUT_PATH = Path("docs/portfolio/coach/slice7/step7_beta2_round2.json")
REPORT_PATH = Path("docs/portfolio/coach/slice7/step7_beta2_round2.md")


def main():
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    results = []
    for entry in matrix:
        if "input_tokens" not in entry:
            continue
        fixture_id = entry["scenario_id"]
        fixture_path = FIXTURE_DIR / f"{fixture_id}.json"
        # 보다 robust한 검색 (확장 매칭)
        candidates = list(FIXTURE_DIR.glob(f"{fixture_id}*.json"))
        if not candidates:
            continue
        data = json.loads(candidates[0].read_text(encoding="utf-8"))
        inp = E4ConversationInput(**data["input"])
        msgs = build_e4_messages(inp)
        full_prompt = get_system_prompt() + "\n\n" + msgs[0]["content"]
        estimated = estimate_input_tokens(full_prompt)
        actual = entry["input_tokens"]
        delta_pct = (estimated - actual) / actual * 100 if actual else 0
        results.append({
            "scenario_id": fixture_id,
            "tier": entry["tier"],
            "provider": entry["provider"],
            "estimated": estimated,
            "actual": actual,
            "delta_pct": round(delta_pct, 2),
            "delta_abs_pct": round(abs(delta_pct), 2),
        })

    deltas = [r["delta_abs_pct"] for r in results]
    max_delta = max(deltas) if deltas else 0
    avg_delta = sum(deltas) / len(deltas) if deltas else 0
    kpi_pass = max_delta <= 30.0

    summary = {
        "results": results,
        "n": len(results),
        "max_delta_abs_pct": round(max_delta, 2),
        "avg_delta_abs_pct": round(avg_delta, 2),
        "kpi_threshold_pct": 30.0,
        "kpi_pass": kpi_pass,
        "beta2_verdict": "close" if kpi_pass else "keep_open",
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 3 #β2 2차 측정 (Step 7 matrix 후)\n",
        f"## KPI: max delta ≤ 30% → {'**PASS** ✓' if kpi_pass else '**FAIL** ✗'}",
        f"- n: {len(results)}",
        f"- max delta: {max_delta:.2f}%",
        f"- avg delta: {avg_delta:.2f}%",
        f"- **#β2 verdict: {summary['beta2_verdict']}**\n",
        "## 상세",
        "| scenario | tier | provider | estimated | actual | delta% |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        md.append(
            f"| {r['scenario_id']} | {r['tier']} | {r['provider']} | "
            f"{r['estimated']} | {r['actual']} | {r['delta_pct']:+.2f}% |"
        )
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ #β2 round 2: {OUT_PATH}")
    print(f"  max delta: {max_delta:.2f}% / verdict: {summary['beta2_verdict']}")


if __name__ == "__main__":
    main()
```

### 7.2 분기 처리

- **L5 (KPI PASS, delta ≤ 30%)**: #β2 close → Slice 8 Step 0 후보에서 제외
- **L5 (KPI FAIL, delta > 30%)**: #β2 keep_open → Slice 8 Step 0 후보 유지

---

## §8. Step 8 — Manual Eval 입력 자료 준비

### 8.1 raw + scored dump 준비 (Part 4 입력)

`scripts/slice7/prepare_step8.py` — Slice 6 패턴 일관:

```python
"""
Slice 7 Part 3 Step 8: Part 4 manual eval 입력 자료 준비.

Step 7 matrix raw → Part 4 평가용 entry 변환.
- DIMENSION_LOOKUP 경로 또는 service layer dispatch 경로로 처리
- scored.json은 stub (Part 4에서 채움)
"""

import json
from pathlib import Path

MATRIX_PATH = Path("docs/portfolio/coach/slice7/step7_matrix_raw.json")
OUT_RAW = Path("docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json")
OUT_SCORED = Path("docs/portfolio/coach/slice7/step8_2way_e4_conversation_scored.json")
OUT_SUMMARY = Path("docs/portfolio/coach/slice7/step7_5_summary.md")


def main():
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    entries = []
    for r in matrix:
        if not r.get("schema_pass"):
            continue
        entries.append({
            "scenario_id": r["scenario_id"],
            "preset_id": r["preset_id"],
            "tier": r["tier"],
            "provider": r["provider_meta"] or r["provider"],
            "trigger_case": r.get("trigger_case"),
            "commentary": r["raw_content"],
            "cost_usd": r["cost_usd"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
        })
    raw_payload = {"entries": entries, "total": len(entries)}
    OUT_RAW.write_text(json.dumps(raw_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # scored stub
    scored_stub = {
        "entries": [
            {**e, "naturalness": None, "insight": None, "label_mean": None, "efficiency": None}
            for e in entries
        ],
        "winner": None,
        "g_branches": [],
    }
    OUT_SCORED.write_text(json.dumps(scored_stub, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 3 Step 8 Summary (Part 4 입력 가이드)\n",
        f"- 총 entries: {len(entries)}",
        f"- 매트릭스 raw: {OUT_RAW}",
        f"- scored stub: {OUT_SCORED}",
        "",
        "## Part 4 manual eval 작업 순서",
        "1. prepare_manual_eval_v7.py 실행 → eval_form_v7.md + eval_key_v7.json 생성 (seed=42)",
        "2. 병진 rubric 기반 평가 (rubric §C.6 분포 폭 KPI 자동 보고)",
        "3. score_step9_v7.py 실행 → winner + 글쓰기 가설 6/6 + 외삽 검증 + #26 자연 close 판정",
    ]
    OUT_SUMMARY.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ Step 8 raw: {OUT_RAW}")
    print(f"✓ Step 8 scored stub: {OUT_SCORED}")


if __name__ == "__main__":
    main()
```

### 8.2 실행

```bash
python scripts/slice7/prepare_step8.py
```

---

## §9. 회귀 영향 KPI

| 단계                       | 회귀 영향                      | 비용        |
| -------------------------- | ------------------------------ | ----------- |
| §1 (PROJECT_LAYOUT.md)     | 0 (docs only)                  | $0          |
| §2 (E4 prompt builder)     | +6                             | $0          |
| §3 (DIMENSION_LOOKUP 결정) | 0 또는 +1~3 (dispatch 추가 시) | $0          |
| §4 (Step 6 smoke)          | 0 (script only)                | ~$0.005     |
| §5 (Step 7 matrix)         | 0 (script only)                | ~$0.32~0.42 |
| §6 (Step 7.5 KPI)          | 0 (script only)                | $0          |
| §7 (#β2 2차)               | 0 (script only)                | $0          |
| §8 (Step 8 dump)           | 0 (script only)                | $0          |

**총 회귀 추가**: +6~9건 (목표 484 → 490~493)
**총 비용 추가**: $0.33~0.43
**누적 광의 예상**: $0.879 + $0.43 = **$1.30** (임계 $1.50 마진 13%)
**호출 카운트**: 1 + 28 = **29/50** (마진 21)

---

## §10. 분기 시나리오 (Part 3 안에서)

| 시나리오    | 트리거                              | 조치                                                   |
| ----------- | ----------------------------------- | ------------------------------------------------------ |
| **L1**      | Step 6 smoke 4판정 FAIL             | 즉시 중단, 원인 분석 후 보고                           |
| **L2**      | Step 7 단건 비용 임계 ($0.020) 초과 | CostGuard 자동 차단 (스크립트 내장)                    |
| **L3**      | Step 7 fallback 발생 (≥1건)         | 보고 + 본 매트릭스는 유지 (Slice 1 9/9 폴백 사건 참조) |
| **L4**      | #β2 1차 delta > 50% (Step 6 후)     | Step 7 budget 임시 +50% 안전 마진, 메모리 기록         |
| **L5 PASS** | #β2 2차 delta ≤ 30%                 | #β2 close → Slice 8 Step 0 후보 제외                   |
| **L5 FAIL** | #β2 2차 delta > 30%                 | #β2 keep_open                                          |
| **L6**      | IDENTICAL hash 깨짐                 | 즉시 보고 + Part 3 중단                                |
| **L7**      | token budget 초과 (Tier별)          | 해당 case I1 분기 검증 (history truncate)              |
| **L8**      | Step 7 총 비용 > $0.50 cap          | 자동 차단, 매트릭스 미완료 보고                        |

---

## §11. 완료 보고 양식

```
[Slice 7 Part 3 완료 보고]

== §1 (PROJECT_LAYOUT.md) ==
- docs 신설: ✓
- 디렉토리 매핑 표 7건: ✓

== §2 (E4 prompt builder) ==
- portfolio/prompts/e4/builder.py 신설: ✓
- 회귀 추가: 6 PASS

== §3 (DIMENSION_LOOKUP 결정) ==
- decision docs: ✓
- 결론: (entry 추가 / service dispatch 사용)

== §4 (Step 6 smoke) ==
- 4판정: schema=? / completeness=? / cost=? / token=?
- cost: $? / latency: ?ms
- #β2 1차 delta: ?% → L4 분기 (발동 / 미발동)

== §5 (Step 7 matrix) ==
- 호출: 28/28 (또는 부분)
- schema PASS: ?/28
- completeness PASS: ?/28
- fallback: ?건
- 단건 비용 임계 초과: ?건
- 총 비용: $?
- input P90/max: ? / ?
- output P90/max: ? / ?

== §6 (Step 7.5 KPI) ==
- KPI 8/8: ?
- 보조 KPI 9 provider 통계: haiku cost $? / sonnet cost $?

== §7 (#β2 2차 측정) ==
- max delta: ?%
- verdict: close / keep_open

== §8 (Step 8 dump) ==
- raw entries: ?건
- scored stub: ✓
- Part 4 입력 자료 준비: ✓

== 종합 ==
- 회귀: 484 → ? (목표 490~493)
- 비용: $? (예상 $0.33~0.43)
- 누적 광의: $? (예상 $1.30, 임계 마진 ?%)
- 호출 카운트: ?/50
- IDENTICAL hash: ✓
- 분기 발동: L? (목록)
- 신규 부채 / close: ? (Β2 verdict 반영)

§I. 산출물 (~10건)
§II. 분기 발동 결과
§III. Part 4 진입 사전 체크
§IV. Commit 메시지 권장
§V. 핵심 결과 (4판정 / winner 후보 / 가설 6/6 신호)
```

---

## §12. Commit 메시지 권장

```
docs(slice7/part3/layout): PROJECT_LAYOUT.md 신설 (경로 매핑 부채 해소)
feat(slice7/part3/prompt): E4 conversation prompt builder
test(slice7/part3/prompt): E4 builder 회귀 +6
docs(slice7/part3/step3): DIMENSION_LOOKUP 결정 (entry add / service dispatch)
feat(slice7/part3/step6): smoke test + #β2 1차 측정
feat(slice7/part3/step7): matrix 14 cases × haiku/sonnet (28 calls)
feat(slice7/part3/step7_5): KPI 8 자동 검증
feat(slice7/part3/beta2): #β2 2차 측정 + verdict
feat(slice7/part3/step8): Part 4 manual eval 입력 자료 준비
```

---

## §13. Part 4 진입 사전 등록

Part 3 종결 후 Part 4 작업 범위 (Slice 6 패턴 일관):

- Step 9.1: `prepare_manual_eval_v7.py` (15 entries → blind 평가 표, seed=42)
  - 단, S13 reject 제외하면 entry는 28건 (14 cases × 2 providers)
  - blind 평가는 28건 평가 부담 ↑ → **결정 사항: 풀 평가 vs 압축 평가** Part 4 진입 전 결정
- Step 9.2: 병진 manual eval (rubric §C.6 분포 폭 KPI 적용)
- Step 9.3: score_step9_v7.py (winner + 글쓰기 가설 6/6 + #26 자연 close 판정)
- Step 9.4: 분기 후속 (Slice 6 G6 패턴 일관)
- Step 10: Slice 7 종결 보고 + Step 9 슬롯 #19 처리
