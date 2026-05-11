# Slice 5 Part 2 작업 지시서 — E3 (Step 6~9 + report + backlog)

> 작성일: 2026-05-07
> 버전: v1.0
> 진입점: **E3 (지표 코멘트, MetricComment one-liner)**
> Part 1 종결 baseline: 단독 **219 passed** (목표 +37 ±5 대비 +9 초과 — fixture parametrize 14건 효과)
> Slice 4 Part 2 mirror 비율: ~95%

---

## §0. 참조 문서

| #   | 문서                                                                                       | 용도                                                |
| --- | ------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| 1   | `docs/portfolio/coach/slice4/slice4_part2_instructions.md`                                 | mirror 대상 (~95%) — 모든 Step 구조의 1차 baseline  |
| 2   | `docs/portfolio/coach/slice4/validation_report_slice4.md`                                  | report 6 섹션 형식 + 비용/회귀 baseline             |
| 3   | `docs/portfolio/coach/slice4/refactor_backlog_slice4.md`                                   | 백로그 처리 추적 형식                               |
| 4   | `docs/portfolio/coach/slice5/slice5_part1_instructions.md`                                 | 자동 변환 5건 baseline                              |
| 5   | `docs/portfolio/coach/slice5/slice5_part1_report.md`                                       | Part 1 종결 결과 + 추가 환경 차이 3건               |
| 6   | `docs/portfolio/coach/COST_POLICY.md` (신설, Slice 5 Step 0)                               | 광의 단일 정책 — Slice 5 validation_report부터 적용 |
| 7   | (이번 세션 회수) Slice 5 Part 2 자료 5종 보고                                              | Step 6~9 정확한 처방 baseline                       |
| 8   | (이번 세션 산출) Part 2 결정 사이클 7건 결정                                               | 본 지시서 결정 근거                                 |
| 9   | `scripts/validation/score_step8.py` \_main_unified() (Slice 4 Step 9 통합본, 라인 218~252) | Step 8 e3 entry 추가 위치                           |
| 10  | `portfolio/services/_prompt_helpers.py:39-60` (`format_metrics_table`)                     | Step 9 일반화 대상                                  |
| 11  | `portfolio/llm/token_budgets.py` (전체 45줄)                                               | Step 7 e3 등록 위치 + #β1 휴리스틱 검증 코드        |

---

## §1. 목표

### §1.1 슬라이스 핵심 가치 (5종)

1. **E3 진입점 실측 검증 (Step 6 smoke)**
   - fixture `e3_baseline_garp_tech` (5 holdings, 3 metrics)으로 1 LLM call
   - 4 판정 모두 PASS 목표: schema/completeness/cost(≤$0.020)/latency(≤16,000ms)

2. **E3 token budget 등록 (Step 7)**
   - 7 fixture P90 실측 → `token_budgets.py["e3"]` 등록값 확정
   - **#β1 자연 검증**: estimate_input_tokens chars/3 휴리스틱 vs 실측 delta_pct 측정 → +50% 편차 재발 시 chars/2.5로 보정 (Slice 4 Step 7 +50% 편차 교훈)

3. **글쓰기 가설 5번째 외삽 검증 (Step 8)**
   - 14 calls 매트릭스 = haiku 7 + sonnet 7 (gemini 제외, Slice 1 9/9 폴백 후 정책 일관)
   - winner=haiku 시 **5/5 정착** (S1 E1 + S3 E2 + S4 E6 + S5 E3 + 반례 S2 E5 일관) → preset 외삽 위험 영구 해소
   - winner=sonnet 시 **4/5 재평가** (케이스 F) → Slice 6+ 추가 글쓰기 진입점 검증 필요
   - 그룹 분석 4매트릭스: baseline (GARP 3) vs focused (4 preset) — naturalness/insight/score/cost·latency

4. **#11 metrics_table 일반화 (Step 9, 30분 한도)**
   - `format_metrics_table` → `format_metrics_to_str(data, format="markdown"|"json")` 일반화
   - E2 호출처 1줄 + E3 호출처 1줄 변경 + 단위 테스트 +3
   - **deprecated wrapper 유지** = 회귀 위험 0 + Slice 6+ 정리 (백로그 후보 #21)
   - **Slice 1·3 IDENTICAL hash 보장 KPI 일관 유지**:
     - Slice 1: `917fa3ef821426e88178456a1f70462f5ab9576e20f06a63d0a88c28fcc0f7b9`
     - Slice 3: `5594c6ab9291213bca7d3e98b3b221164575eb47c52a281248ddc616218cf3ba`

5. **Slice 5 첫 광의 단일 정책 적용 (validation_report)**
   - Step 0 #γ1 처리 후속 — Slice 5 validation_report §5는 광의 단일 정책으로 작성
   - 협의/광의 분리 표기 _금지_ (COST_POLICY.md 정책 위반)
   - 메인 4스텝 비용은 _주석_(괄호)으로 1줄 표기

### §1.2 비범위 (Phase 2 / Slice 6+ 위임)

| 항목                                         | 위임                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| LLMClient.complete system 인자 추가          | 백로그 #19 (PS 2.0), Slice 6 Step 9 슬롯 후보                          |
| concentrated_portfolio portfolio-level E3    | 백로그 #20 (PS 2.0), Slice 6+                                          |
| format_metrics_table deprecated wrapper 제거 | 백로그 후보 #21 (PS 0.5), Slice 6+                                     |
| LLMClient entrypoint 인자 + 가드레일         | 백로그 #8 (PS 2.5), Slice 6 Step 9 후보                                |
| 분석 엔진 정량 재계산                        | Phase 2 위임 (#12 PS 5.0)                                              |
| Slice 4 보고서 광의/협의 분리 표기 정리      | 보존 (Slice 4 작성 시점 정책 그대로 유지, COST_POLICY는 Slice 5+ 적용) |

---

## §2. 사전 조건

### §2.1 git / 회귀 baseline

| 항목                    | 값                                                                        |
| ----------------------- | ------------------------------------------------------------------------- |
| 브랜치                  | `portfolio` (push 완료, d134581..51c112e)                                 |
| Part 1 종결 단독 회귀   | **219 passed** (목표 +37 +9 초과 = 케이스 F, 작업 차단 아님)              |
| Part 1 종결 합산 표시   | 342 passed (origin rebase marketpulse v2 +123 포함)                       |
| Part 2 진입 시 baseline | 단독 219 passed                                                           |
| Part 2 종결 예상 회귀   | **단독 224~229 passed** (Step 7 +3 + Step 9 +5~10, 보수 +5~10 합산 = ~+8) |

### §2.2 환경 차이 자동 변환 8건

Part 1 지시서 §2.2 5건 + Part 1 실행에서 발견된 추가 3건:

| #                   | 자료 발견                                                                        | 자동 변환 처리                                                                      | Part 1·2 적용 시점                              |
| ------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------- |
| 1                   | `build_e3_prompt` (system, user) tuple 반환                                      | service `build_e3_prompt` wrapper에서 `system + "\n\n" + user` concat → 단일 prompt | Part 1 적용 ✓                                   |
| 2                   | preset 12개 (concentrated 추가)                                                  | concentrated 제외 11 preset, 5 preset 선정                                          | Part 1 적용 ✓                                   |
| 3                   | 지표 57개                                                                        | 영향 없음                                                                           | —                                               |
| 4                   | DIMENSION_LOOKUP 1줄 추가로 자동 dispatch                                        | `_main_unified()` 변경 0줄, e3 entry만 추가 (Step 8)                                | **Part 2 Step 8**                               |
| 5                   | cost_log.json 없음                                                               | validation_report §5 광의 단일 정책 (Slice 5+ 적용)                                 | Part 1 Step 0 ✓ + Part 2 validation_report 적용 |
| **6** (Part 1 발견) | `portfolio/schemas/llm_inputs.py` 미존재                                         | E3Request를 `portfolio/schemas/llm.py`에 추가 (E2/E5/E6 동일 위치)                  | Part 1 적용 ✓                                   |
| **7** (Part 1 발견) | LLMClient `entrypoint=` 인자 미존재 (백로그 #8)                                  | `PROVIDER_KWARGS` 사용 패턴, **Part 2 Step 6/8에서도 동일 적용**                    | **Part 2 Step 6, Step 8**                       |
| **8** (Part 1 발견) | service 시그니처 (text, metadata) tuple → `LLMResponse` 객체 + `metadata_dict()` | **Part 2 Step 6/8 LLM 호출 처리 시 `LLMResponse.metadata_dict()` 사용**             | **Part 2 Step 6, Step 8**                       |

### §2.3 누적 부채 / 백로그 사전 등록

| #   | 부채                            | Part 2 처리                                                                                                 |
| --- | ------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| #γ1 | 누적 비용 광의/협의 정합        | Part 1 Step 0 완료 ✓ — Part 2 validation_report에 광의 단일 정책 적용만 검증                                |
| #β1 | token 한국어 휴리스틱 +50% 편차 | **Part 2 Step 7 자연 검증** — 7 fixture estimate vs actual delta_pct 측정. 재발 시 chars/3 → chars/2.5 보정 |
| #18 | score_step8_e5.py argparse      | Slice 6+ 이연 (회귀 영향 0)                                                                                 |
| #19 | LLMClient system 인자           | Slice 6+ 이연                                                                                               |
| #20 | concentrated portfolio-level E3 | Slice 6+ 이연                                                                                               |

### §2.4 IDENTICAL hash baseline (Step 9 KPI)

자료 #5 인용 (Slice 5 Part 1 종결 직후 = Slice 4 Part 2 Step 9 baseline 동일):

| 산출물                                                  | sha256 hash                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------------ |
| `docs/portfolio/coach/slice1/step8_3way_scored.json`    | `917fa3ef821426e88178456a1f70462f5ab9576e20f06a63d0a88c28fcc0f7b9` |
| `docs/portfolio/coach/slice3/step8_2way_e2_scored.json` | `5594c6ab9291213bca7d3e98b3b221164575eb47c52a281248ddc616218cf3ba` |

→ **Step 9 통합 후 동일 hash 유지가 핵심 KPI**. 변경 시 즉시 git revert + 사용자 에스컬레이션 (케이스 D).

---

## §3. 스코프

### §3.1 Part 2 포함 (Step 6~9 + report + backlog)

| Step              | 작업                                                                                                   | LLM 호출               | 회귀 변화 (예상)               |
| ----------------- | ------------------------------------------------------------------------------------------------------ | ---------------------- | ------------------------------ |
| 6                 | E3 smoke (fixture=e3_baseline_garp_tech) + 4 판정 산출 + step6_smoke_e3_output.json                    | 1                      | 0                              |
| 7                 | 7 fixture token 측정 + e3 budget 등록 + #β1 자연 검증 + 단위 +3                                        | 0                      | +3                             |
| 8                 | 14 calls 회고 (haiku 7 + sonnet 7) + 그룹 분석 + DIMENSION_LOOKUP e3 entry + analyze_e3_groups.py 신규 | 14+재시도              | 0                              |
| 9                 | `format_metrics_to_str` 일반화 + E2/E3 호출처 변경 + 단위 +3 (30분 한도)                               | 0                      | +3                             |
| validation_report | 6 섹션 (광의 단일 정책 첫 적용)                                                                        | 0                      | 0                              |
| refactor_backlog  | Slice 4 7건 + Slice 5 신규 처리 결과                                                                   | 0                      | 0                              |
| **Part 2 합계**   | —                                                                                                      | **15** (재시도 0 가정) | **+6~13** (단독 219 → 225~232) |

### §3.2 Part 2 비포함 (재차 명시)

- LLMClient 시그니처 변경 (`entrypoint=` 인자, system 인자) — 백로그 #8, #19 위임
- format_metrics_table deprecated wrapper 제거 — 백로그 #21 후보 위임
- Slice 1·3 step8\_\*\_scored.json 변경 — IDENTICAL KPI 보장 (변경 금지)
- 분석 엔진 정량 재계산 — Phase 2 위임 (#12)

---

## §4. Step별 작업

### §4.6 Step 6 — E3 smoke (1 LLM call)

Slice 4 Step 6 mirror ~95%. fixture·임계만 차이.

#### 6.1 신규 파일

| 파일                                                     | 역할                                                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `scripts/validation/run_step6_e3_smoke.py`               | E3 smoke 실행 스크립트 (Slice 4 `run_step6_e6_smoke.py` mirror)                             |
| `docs/portfolio/coach/slice5/step6_smoke_e3_output.json` | smoke 산출물 (raw_content + parsed + metadata + judgments + thresholds + cost_guard_status) |

#### 6.2 핵심 코드 (Slice 4 mirror, 환경 차이 #7·#8 적용)

```python
# scripts/validation/run_step6_e3_smoke.py

from portfolio.llm import LLMClient
from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL, PROVIDER_KWARGS  # 환경 차이 #7
from portfolio.llm.cost_guard import CostGuard
from portfolio.schemas.llm import E3Request  # 환경 차이 #6 (llm.py 통합)
from portfolio.services.e3_metric_comment import build_e3_prompt, parse_e3_response, run_e3
from portfolio.tests.fixtures.sample_metric_comment_context import e3_baseline_garp_tech  # Q1 결정

THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 16000,  # Q2 결정 (Slice 4 #9 e6 한정 → e3 동일 적용)
}

OUTPUT_PATH = Path("docs/portfolio/coach/slice5/step6_smoke_e3_output.json")


def main() -> int:
    cost_guard = CostGuard(slice_id="slice5", limit=50, cost_limit_usd=0.20)
    fixture = e3_baseline_garp_tech()
    request = E3Request(analysis_context=fixture["analysis_context"])

    client = LLMClient(cost_guard=cost_guard)
    parsed, metadata = run_e3(request, client=client)  # 환경 차이 #8 (LLMResponse.metadata_dict() 내부)

    # 4 판정
    judgments = {
        "schema_pass": parsed is not None,
        "completeness_pass": len(parsed.comments) >= 1 if parsed else False,
        "cost_pass": metadata["cost_usd"] <= THRESHOLDS["cost_usd_max"],
        "latency_pass": metadata["latency_ms"] <= THRESHOLDS["latency_ms_max"],
    }

    output = {
        "fixture": "e3_baseline_garp_tech",
        "raw_content": metadata.get("raw_text", ""),
        "parsed": parsed.model_dump() if parsed else None,
        "metadata": metadata,
        "judgments": judgments,
        "thresholds": THRESHOLDS,
        "cost_guard_status": {
            "slice_id": "slice5",
            "call_count": cost_guard.call_count,
            "total_cost_usd": cost_guard.total_cost_usd,
        },
    }
    _safe_write(OUTPUT_PATH, output)  # round-trip 검증
    return 0 if all(judgments.values()) else 1
```

#### 6.3 fixture 선정 근거 (Q1 결정)

자료 #1 인용:

| fixture                   | holdings | core+sup metrics | 권장                          |
| ------------------------- | -------- | ---------------- | ----------------------------- |
| **e3_baseline_garp_tech** | **5**    | **2+1=3**        | **⭐ smoke 권장 (가장 단순)** |
| e3_baseline_garp_misfit   | 5        | 3+2=5            | —                             |
| e3_baseline_garp_large    | 15       | 3+4=7            | — (smoke로 무거움)            |
| focused 4종               | 5        | 2+1=3            | — (preset 다양성은 Step 8)    |

#### 6.4 임계 (Q2 결정)

- `cost_usd_max`: $0.020 (Slice 1~4 일관, COST_POLICY 정합)
- `latency_ms_max`: **16,000ms** (Slice 4 #9 e6 한정 → e3 동일 적용. E3 글쓰기 + multi metric 길이 반영)

#### 6.5 LLM 호출 / 회귀 영향

- LLM 호출: **1건** (Step 6 단독)
- 회귀 영향: 0건 (산출물만)
- 비용 예상: ~$0.005 (Slice 4 Step 6 $0.00437 mirror 추정)

---

### §4.7 Step 7 — Token budget 측정 + #β1 자연 검증

Slice 4 Step 7 mirror ~95%. 차이: #β1 검증 절차 명시.

#### 7.1 신규 / 수정 파일

| 파일                                                        | 작업                                                              |
| ----------------------------------------------------------- | ----------------------------------------------------------------- |
| `scripts/validation/measure_e3_tokens.py`                   | 신규 — 7 fixture P90 측정 (Slice 4 `measure_e6_tokens.py` mirror) |
| `docs/portfolio/coach/slice5/measure_e3_tokens_output.json` | 신규 — 측정 결과                                                  |
| `portfolio/llm/token_budgets.py`                            | 수정 — `e3` entry 1줄 추가                                        |
| `portfolio/tests/test_token_budgets.py`                     | 수정 — `e3` entry 단위 테스트 +3건                                |

#### 7.2 7 fixture token 측정 helper (Slice 4 mirror 100%)

```python
# scripts/validation/measure_e3_tokens.py

import math
from anthropic import Anthropic
from portfolio.llm.client import ANTHROPIC_HAIKU_MODEL
from portfolio.schemas.llm import E3Request
from portfolio.schemas.analysis_context import AnalysisContext
from portfolio.services.e3_metric_comment import build_e3_prompt
from portfolio.llm.token_budgets import estimate_input_tokens
from portfolio.tests.fixtures.sample_metric_comment_context import ALL_FIXTURES

def count_tokens_anthropic(text: str) -> int:
    """Anthropic count_tokens API — input 토큰 계산. generation 비용 0."""
    client = Anthropic()
    resp = client.messages.count_tokens(
        model=ANTHROPIC_HAIKU_MODEL,
        messages=[{"role": "user", "content": text}],
    )
    return resp.input_tokens

def main() -> int:
    results = []
    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E3Request(analysis_context=fixture["analysis_context"])
        context = AnalysisContext.model_validate(request.analysis_context)
        prompt = build_e3_prompt(context)  # service의 wrapper (system + "\n\n" + user concat)
        actual = count_tokens_anthropic(prompt)
        estimated = estimate_input_tokens(prompt)  # chars/3 휴리스틱
        delta_pct = (estimated - actual) / actual * 100 if actual else 0.0
        results.append({
            "fixture": name,
            "actual_tokens": actual,
            "estimated_chars_div_3": estimated,
            "delta_pct": delta_pct,  # #β1 자연 검증
            "char_count": len(prompt),
        })

    actuals = sorted(r["actual_tokens"] for r in results)
    n = len(actuals)
    p90_idx = math.ceil(0.9 * n) - 1
    p90 = actuals[p90_idx]
    mean = sum(actuals) / n
    budget_proposed = int(math.ceil(p90 * 1.5 / 500) * 500)  # round-up 500 단위
    # ... write output
```

#### 7.3 #β1 자연 검증 절차

자료 #2 인용 (`portfolio/llm/token_budgets.py:38-44` `estimate_input_tokens(prompt)` = `len(prompt) // 3`).

**검증 기준** (Slice 4 Step 7 +50% 편차 교훈):

- 모든 fixture의 `delta_pct` 평균이 **±20% 이내**: 휴리스틱 정상, 보정 불필요 → #β1 closed (validation_report §5에 1줄 기록)
- 평균 delta_pct가 **+30% 이상**: chars/3 → **chars/2.5** 보정 (편집 1줄)
- 평균 delta_pct가 **+50% 이상**: chars/3 → **chars/2.6** 보정 (Slice 4 e6 P90/measured 비율 인용)

**보정 시 추가 작업**:

1. `portfolio/llm/token_budgets.py:38-44` `estimate_input_tokens(prompt)` 본문 1줄 변경: `len(prompt) // 3` → `len(prompt) // 2.5` (또는 2.6)
2. test 추가 (한국어 100자 → 약 38~40 토큰 추정)
3. validation_report §5에 #β1 처리 결과 명시

#### 7.4 budget 결정 규칙

- `e3` 1차 추정 = 1500 (Q3, Part 1 지시서 §4.2.4)
- 실측 P90 × 1.5 → round-up 500 단위
- 1차 추정과 ±20% 이내면 1500 유지 권장 (round-up 안정성)
- 1차 추정 대비 +30% 이상이면 갱신값 등록

#### 7.5 token_budgets.py e3 entry 추가 (자료 #2 인용)

```python
# portfolio/llm/token_budgets.py

ENTRYPOINT_TOKEN_BUDGETS: dict[str, int] = {
    "e1": 5000,
    "e5": 2000,
    "e2": 1500,
    "e6": 1500,
    "e3": <P90_측정값_round-up>,  # Slice 5 Step 7 (P90 × 1.5 → round-up 500)
}
```

#### 7.6 단위 테스트 +3건

| #   | 테스트명                               | 검증                                            |
| --- | -------------------------------------- | ----------------------------------------------- |
| 1   | `test_e3_budget_registered`            | `get_token_budget("e3")` 정상 반환              |
| 2   | `test_e3_budget_round_up_500`          | 등록값 % 500 == 0                               |
| 3   | `test_e3_budget_within_estimate_range` | 1차 추정 1500 대비 ±50% 이내 (한국어 보수 추정) |

#### 7.7 LLM 호출 / 회귀 영향

- LLM 호출: 0건 (count_tokens API는 generation 비용 0, CostGuard 카운트 제외)
- 회귀 영향: **+3** (단독 219 → 222)

---

### §4.8 Step 8 — 14 calls 회고 + 그룹 분석 + DIMENSION_LOOKUP e3 entry

Slice 4 Step 8 mirror ~95%. 차이: e3 entry 추가 + analyze_e3_groups.py 신규.

#### 8.1 신규 / 수정 파일

| 파일                                                            | 작업                                                                           |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `scripts/validation/run_step8_2way_e3_retrospective.py`         | 신규 — 14 calls 매트릭스 (Slice 4 `run_step8_2way_e6_retrospective.py` mirror) |
| `docs/portfolio/coach/slice5/step8_2way_e3_raw.json`            | 신규 — 14 raw 결과 (manual 평가 입력 대기)                                     |
| `docs/portfolio/coach/slice5/step8_2way_e3_scored.json`         | 신규 — score 산출물 (winner / efficiency / lex_pass_rate)                      |
| `scripts/validation/analyze_e3_groups.py`                       | 신규 — 그룹 분석 (analyze_e2_groups.py mirror, 자료 #3)                        |
| `docs/portfolio/coach/slice5/step8_2way_e3_group_analysis.json` | 신규 — 4매트릭스 산출물                                                        |
| `scripts/validation/score_step8.py`                             | 수정 — `DIMENSION_LOOKUP["e3"]` entry 1줄 추가 (자료 #3 인용 형식 그대로)      |

#### 8.2 14 calls 매트릭스 (자료 #3 mirror)

| 차원     | 값                                       |
| -------- | ---------------------------------------- |
| 매트릭스 | 7 fixture × 2 model = 14 calls           |
| haiku    | 7 calls                                  |
| sonnet   | 7 calls                                  |
| gemini   | **제외** (Slice 1 9/9 폴백 후 정책 일관) |
| fixture  | hybrid 7 (baseline GARP 3 + focused 4)   |

#### 8.3 DIMENSION_LOOKUP e3 entry 추가 (자료 #3 인용 그대로)

```python
# scripts/validation/score_step8.py — DIMENSION_LOOKUP에 1줄 추가

"e3": {  # Slice 5 — e2/e6 패턴 mirror
    "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
    "dim2": {"key": "insight", "manual_field": "insight_manual"},
    "model_label_field": "model_label",
    "result_structure": "nested",
    "default_raw":   "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
    "default_scored":"docs/portfolio/coach/slice5/step8_2way_e3_scored.json",
    "weight": 0.5,
    "additional_lex_check": "completeness_auto",
},
```

→ **자동 dispatch**: `_main_unified()` 변경 0줄 (자료 #3 KPI 충족).

#### 8.4 analyze_e3_groups.py 신규 (자료 #3 mirror)

```python
# scripts/validation/analyze_e3_groups.py — analyze_e2_groups.py mirror 100%

SCORED_PATH = Path("docs/portfolio/coach/slice5/step8_2way_e3_scored.json")
OUTPUT_PATH = Path("docs/portfolio/coach/slice5/step8_2way_e3_group_analysis.json")

# fixture 그룹 정의 (hybrid 7 매핑)
FIXTURE_GROUPS = {
    "baseline": ["e3_baseline_garp_tech", "e3_baseline_garp_misfit", "e3_baseline_garp_large"],
    "focused": ["e3_focused_buffett", "e3_focused_dividend_growth", "e3_focused_quality_factor", "e3_focused_contrarian"],
}

# 4 매트릭스: model × group × {n, naturalness_mean, insight_mean, score_mean, cost_total_usd, latency_mean_ms}
```

#### 8.5 글쓰기 가설 외삽 검증 처리

Step 8 winner 결과별 처리:

| Winner     | 처리                                                                                                              | KPI                                |
| ---------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **haiku**  | **5/5 정착** ✓ — preset 외삽 위험 영구 해소. validation_report §4 명시                                            | 글쓰기 가설 외삽 검증 = 5/5        |
| **sonnet** | **케이스 F 발동** — 4/5 재평가. validation_report §4 가설 재평가 분석 추가. Slice 6+ 글쓰기 진입점 추가 검증 권장 | 글쓰기 가설 외삽 검증 = 4/5 재평가 |

→ 작업 차단 아님 (Slice 4 Step 8 케이스 F 처리 동일).

#### 8.6 efficiency / lex_pass_rate 검증 임계

Slice 4 Step 8 mirror:

| 항목                    | 임계                                 |
| ----------------------- | ------------------------------------ |
| efficiency 차이         | 두 모델 중 하나라도 ≥ 5% (동률 방지) |
| lex_pass_rate           | 두 모델 중 하나라도 ≥ 50%            |
| 각 fixture × model 결과 | manual 입력 후 score 산출 가능       |

#### 8.7 그룹 분석 4매트릭스 interpretation_guide

자료 #3 mirror:

- `small_diff` (<10%): 그룹간 차이 미미 → preset 외삽 안전
- `baseline_higher`: GARP fixture가 평가 우수 → 다른 preset에서 글쓰기 품질 약화 (preset 외삽 위험)
- `focused_higher`: focused fixture가 평가 우수 → 다양한 preset이 오히려 더 나은 글쓰기 자극

#### 8.8 LLM 호출 / 회귀 영향

- LLM 호출: **14건** (haiku 7 + sonnet 7) + 재시도 ~3 → **17/50 누적 마진 안전**
- 회귀 영향: 0건 (산출물만)
- 비용 예상: Slice 4 Step 8 ~$0.153 mirror → ~$0.15

---

### §4.9 Step 9 — `format_metrics_to_str` 일반화 (30분 한도)

Slice 4 Step 9 mirror ~70%. 차이: 작업 본질 (#11 metrics_table 일반화 vs #2 score 통합).

#### 9.1 작업 정의 (Q5=A 결정)

`format_metrics_table` (markdown 표, E2 전용) → `format_metrics_to_str(data, format="markdown"|"json")` 통합 utility.

자료 #4 인용 형식 그대로 채택. 시그니처 + 호출처 변경 영향도(2 호출처 × 1줄) 사전 검증 완료.

#### 9.2 신규 / 수정 파일

| 파일                                                 | 작업 | 형태                                                                                                                              |
| ---------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------- |
| `portfolio/services/_prompt_helpers.py`              | 수정 | `format_metrics_to_str` 신규 함수 + `format_metrics_table` deprecated wrapper                                                     |
| `portfolio/services/e2_diagnostic_card.py:41`        | 수정 | 호출처 1줄 변경                                                                                                                   |
| `portfolio/prompts/e3/e3_builder.py`                 | 수정 | `json.dumps(input_data, ensure_ascii=False, indent=2, default=str)` → `format_metrics_to_str(input_data, format="json")` 1줄 변경 |
| `portfolio/tests/test_prompt_helpers.py` (또는 동등) | 수정 | 단위 테스트 +3건                                                                                                                  |

#### 9.3 핵심 구현

```python
# portfolio/services/_prompt_helpers.py

import json
from typing import Any, Literal


def format_metrics_to_str(
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    format: Literal["markdown", "json"] = "markdown",
) -> str:
    """Metric 데이터를 prompt용 문자열로 직렬화.

    백로그 #11 일반화 (Slice 5 Part 2 Step 9, PS 1.5).

    - format="markdown": E2 dict[str, value] → markdown 표
    - format="json": E3 list[dict] → indented JSON (한국어 ensure_ascii=False)
    """
    if format == "markdown":
        return _format_markdown(data)
    elif format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    else:
        raise ValueError(f"Unknown format: {format}")


def _format_markdown(metrics: dict[str, Any]) -> str:
    """기존 format_metrics_table 본문 (자료 #4 인용)."""
    if not metrics:
        return "(지표 데이터 없음)"
    lines = ["| Metric | Value |", "|---|---|"]
    for key, value in metrics.items():
        if isinstance(value, dict):
            v = value.get("value")
            display = f"{v:.4f}" if isinstance(v, float) else str(v)
        elif isinstance(value, float):
            display = f"{value:.4f}"
        else:
            display = str(value)
        lines.append(f"| {key} | {display} |")
    return "\n".join(lines)


def format_metrics_table(metrics: dict[str, Any]) -> str:
    """[Deprecated] Slice 5 Part 2 (#11 일반화).

    호환성을 위해 유지. format_metrics_to_str(metrics, format='markdown') 호출 wrapper.
    Slice 6+ 백로그 #21로 제거 검토 (PS 0.5).
    """
    return format_metrics_to_str(metrics, format="markdown")
```

#### 9.4 호출처 변경 (각 1줄)

**E2 호출처** (`portfolio/services/e2_diagnostic_card.py:41`):

```python
# Before
metrics_str = format_metrics_table(ctx.get("metrics", {}))

# After
metrics_str = format_metrics_to_str(ctx.get("metrics", {}), format="markdown")
```

**E3 호출처** (`portfolio/prompts/e3/e3_builder.py` 내 dict 직렬화 부분):

```python
# Before
metrics_json = json.dumps(input_data, ensure_ascii=False, indent=2, default=str)

# After
from portfolio.services._prompt_helpers import format_metrics_to_str
metrics_json = format_metrics_to_str(input_data, format="json")
```

#### 9.5 단위 테스트 +3건

| #   | 테스트명                              | 검증                                                                   |
| --- | ------------------------------------- | ---------------------------------------------------------------------- |
| 1   | `test_format_metrics_to_str_markdown` | dict 입력 → markdown 표 출력 (기존 format_metrics_table 동일 결과)     |
| 2   | `test_format_metrics_to_str_json`     | list[dict] 입력 → indented JSON (ensure_ascii=False, default=str 적용) |
| 3   | `test_format_metrics_to_str_empty`    | 빈 입력 → markdown은 "(지표 데이터 없음)", json은 "[]" 또는 "{}"       |

추가 권장 (deprecated wrapper 회귀 검증):

- 기존 `format_metrics_table` 단위 테스트가 그대로 통과해야 함 (변경 없음)

#### 9.6 IDENTICAL hash 보장 절차 (KPI)

Step 9 작업 시작 *직전*과 _직후_ 양쪽에서 hash 검증:

```bash
# Step 9 작업 시작 직전
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json
# 결과를 /tmp/slice5_step9_baseline_e1.sha256, /tmp/slice5_step9_baseline_e2.sha256에 저장

# Step 9 작업 완료 직후
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json | diff - /tmp/slice5_step9_baseline_e1.sha256
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json | diff - /tmp/slice5_step9_baseline_e2.sha256
# 둘 다 출력 없음 (no diff) = IDENTICAL ✓
```

**예상**: 본 Step 9는 score_step8.py 미수정 + raw/scored JSON 미접촉. IDENTICAL 자동 보장.

검증 시 hash 차이 발견 시:

- 즉시 `git revert` (Step 9 commit 취소)
- 사용자 에스컬레이션 (긴급, 케이스 D)

#### 9.7 30분 한도 초과 처리 (케이스 E)

자료 #4 명시 "변경 영향도 = 2 호출처 × 1줄 = 작음" — 30분 한도 매우 안전. 단 만약 초과 시:

- format_metrics_to_str 신규 함수 + deprecated wrapper만 작성 (회귀 위험 0 보장)
- 호출처 변경 (E2/E3) 부분 적용 가능 (E2 우선)
- 단위 테스트 +3 부분 적용 (markdown 1건 우선)
- 미완료 분량 = Slice 6 Step 9 슬롯 후보로 이연

#### 9.8 LLM 호출 / 회귀 영향

- LLM 호출: 0건
- 회귀 영향: **+3** (단독 222 → 225)

---

### §4.10 validation_report (광의 단일 정책 첫 적용)

Slice 4 validation_report mirror ~95%. 차이: 광의 단일 정책 (협의/광의 분리 표기 _금지_).

#### 10.1 신규 파일

| 파일                                                      |
| --------------------------------------------------------- |
| `docs/portfolio/coach/slice5/validation_report_slice5.md` |

#### 10.2 6 섹션 구조 (Slice 4 mirror)

| 섹션                                            | 내용                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------- |
| §1 회귀 카운트 진행                             | Part 1 + Part 2 통합 표 (단독 173 → ~225~232)                             |
| §2 핵심 결과 (winner / 글쓰기 가설 / IDENTICAL) | Step 8 winner + 5/5 정착 또는 4/5 재평가 + Slice 1·3 IDENTICAL True/False |
| §3 그룹 분석 (4매트릭스)                        | analyze_e3_groups 산출 인용 + interpretation 명시                         |
| §4 케이스 A~F 발동                              | 6 케이스 발생 여부 + 처리 결과                                            |
| §5 누적 비용 (광의 단일 정책)                   | 본 슬라이스부터 광의 단일 적용                                            |
| §6 백로그 처리 결과                             | Slice 4 7건 + Slice 5 신규 처리 결과                                      |

#### 10.3 §5 비용 섹션 형식 (광의 단일, 자료 COST_POLICY 정합)

```markdown
## §5. 누적 비용 (광의 단일 정책, COST_POLICY.md 적용)

### Slice 5 비용

| 단계                                  | LLM 호출 | 비용        |
| ------------------------------------- | -------- | ----------- |
| Step 6 (smoke)                        | 1        | $<X>        |
| Step 7 (token 측정, count_tokens API) | 0        | 0           |
| Step 8 (회고 14 calls)                | 14       | $<Y>        |
| 재시도 (있을 경우)                    | <N>      | $<Z>        |
| **Slice 5 단독 광의**                 | <합계>   | **$<합계>** |

> 메인 4스텝 비용 = $<주석>. 광의는 재시도 / 진단 호출 모두 포함 (COST_POLICY 정의).

### 누적 (Slice 1~5 광의)

| 시점             | 광의 누적   |
| ---------------- | ----------- |
| Slice 1 종결     | $0.137      |
| Slice 2 종결     | $0.327      |
| Slice 3 종결     | $0.428      |
| Slice 4 종결     | $0.585      |
| **Slice 5 종결** | **$<합계>** |

#γ1 처리 결과: 광의 단일 정책 본 슬라이스부터 적용 ✓ (COST_POLICY.md 정합)
```

**금지 사항** (§6.4 안전장치):

- "협의 누적" 표 별도 작성 _금지_
- 광의/협의 분리 표기 _금지_
- 메인 4스텝 비용은 *주석 1줄*로만 (별도 표 X)

#### 10.4 #β1 처리 결과 명시 (§5에 1줄)

```markdown
> #β1 자연 검증 결과: estimate_input_tokens chars/3 휴리스틱 평균 delta_pct = ±<N>%. <보정 미실시 / chars/2.5 보정 적용 / chars/2.6 보정 적용>.
```

---

### §4.11 refactor_backlog (Slice 4 처리 결과 + Slice 5 신규)

Slice 4 mirror ~95%. 형식 동일.

#### 11.1 신규 파일

| 파일                                                     |
| -------------------------------------------------------- |
| `docs/portfolio/coach/slice5/refactor_backlog_slice5.md` |

#### 11.2 Slice 4 7건 처리 결과 표

| #   | 항목                                           | PS  | Slice 4 등록 | Slice 5 처리 결과                                                                  |
| --- | ---------------------------------------------- | --- | ------------ | ---------------------------------------------------------------------------------- |
| 11  | metrics_table 일반화                           | 1.5 | 이연         | **Slice 5 Step 9 완료** ✓ (`format_metrics_to_str` + deprecated wrapper)           |
| 5   | TOKEN_BUDGET LLMClient 통합 잔여               | 2.0 | 이연         | Slice 6+ 이연                                                                      |
| 6   | Step 8 raw output CSV 옵션                     | 1.0 | 이연         | Slice 6+ 이연                                                                      |
| 7   | Mock LLMClient mode dict 매핑                  | 1.0 | 이연         | Slice 6+ 이연                                                                      |
| 8   | LLMClient entrypoint 인자 + 가드레일           | 2.5 | 이연         | Slice 6+ Step 9 슬롯 후보                                                          |
| 10  | E2 keyword_match 룰 보완                       | 1.5 | 이연         | Slice 6+ 이연                                                                      |
| 13  | run*step6*\*.py 5종 latency 일괄 16,000ms 상향 | 1.0 | 이연         | Slice 6+ 이연 (run_step6_e3_smoke.py도 16,000ms 일관 적용으로 자연 흡수 부분 진행) |
| 14  | score_step8.py CLI 인자 확장                   | 1.5 | 이연         | Slice 6+ 이연                                                                      |
| 15  | E6 자동 평가 룰 정교화                         | 1.5 | 이연         | <Step 8 회고 시 자연 흡수 / 미흡수>                                                |
| 16  | E6 latency 24s 초과 sonnet 패턴 분석           | 1.0 | 이연         | Slice 6+ 이연                                                                      |
| 17  | auto_eval_e6.py 패턴 일반화                    | 2.0 | 이연         | Slice 6+ 이연                                                                      |
| 18  | score_step8_e5.py argparse                     | 1.0 | 이연         | Slice 6+ 이연                                                                      |

#### 11.3 Slice 5 신규 백로그

| #   | 항목                                                                            | PS  | 트리거                                                                  |
| --- | ------------------------------------------------------------------------------- | --- | ----------------------------------------------------------------------- |
| 19  | LLMClient.complete system 인자 추가 (default None) + 4슬라이스 호출처 일괄 정비 | 2.0 | E3 (system, user) tuple → service concat 임시. Slice 6 Step 9 슬롯 후보 |
| 20  | concentrated_portfolio portfolio-level E3 별도 슬라이스                         | 2.0 | Slice 5 concentrated 제외, Slice 6+ 별도 슬라이스                       |
| 21  | format_metrics_table deprecated wrapper 제거                                    | 0.5 | Slice 5 Step 9 후 호출처 통합 완료, Slice 6+ 정리                       |
| 22  | LLMResponse.metadata_dict() 표준 정착 검증                                      | 1.0 | 4 슬라이스 호출처 일관성 검증                                           |

#### 11.4 누적 백로그 합

- Slice 5 진입 시점: ~13건 (Slice 4 종결)
- Slice 5 신규: +4건 (#19/#20/#21/#22)
- Slice 5 처리: -1건 (#11 완료)
- **Slice 5 종결 누적**: **~16건** (PS 합 ~17.5, 대형 #12 PS 5.0 제외)

---

## §5. 검증 지점

### §5.1 Step별 회귀 카운트 진행 표 (예상)

| 단계                            | 추가 (단독) | 누적 (단독) | 비고                                       |
| ------------------------------- | ----------- | ----------- | ------------------------------------------ |
| Part 1 종결 baseline            | —           | 219         | (Part 1 +46, 케이스 F 발동분 포함)         |
| Step 6 (smoke 산출물)           | 0           | 219         | 산출물만                                   |
| Step 7 (token 측정 + 단위 +3)   | +3          | 222         | test_token_budgets 확장                    |
| Step 8 (회고 산출물 + e3 entry) | 0           | 222         | 산출물만                                   |
| Step 9 (#11 일반화 + 단위 +3)   | +3          | **225**     | format_metrics_to_str + deprecated wrapper |
| validation_report               | 0           | 225         | 산출물만                                   |
| refactor_backlog                | 0           | 225         | 산출물만                                   |

**Part 2 종결 예상 회귀: 225 ±5** (단독, Slice 1·2·3·4·5 누적 +52~57).

### §5.2 검증 판정 표

| #   | 검증 항목                             | 임계                                       | 자동/수동     |
| --- | ------------------------------------- | ------------------------------------------ | ------------- |
| 1   | Step 6 4 판정 모두 PASS               | schema/completeness/cost/latency 모두 True | 자동          |
| 2   | Step 7 budget 1차 추정 정확도         | ±20% 이내 (1500 유지 권장)                 | 자동          |
| 3   | Step 7 #β1 휴리스틱 검증              | 평균 delta_pct ≥ +30% 시 보정 적용         | 자동          |
| 4   | Step 8 lex_pass_rate                  | 두 모델 중 하나라도 ≥ 50%                  | 자동 + manual |
| 5   | Step 8 winner 결정                    | label_means 차이 ≥ 5% (둘 동률 방지)       | 자동          |
| 6   | Step 8 그룹 분석                      | 4매트릭스 모두 산출 + interpretation 적용  | 자동          |
| 7   | Step 8 글쓰기 가설 외삽               | 5/5 정착 또는 4/5 재평가 명시              | 자동          |
| 8   | **Step 9 Slice 1 e1 IDENTICAL**       | sha256 hash 동일 (`917fa3ef…0f7b9`)        | 자동 (KPI)    |
| 9   | **Step 9 Slice 3 e2 IDENTICAL**       | sha256 hash 동일 (`5594c6ab…f3ba`)         | 자동 (KPI)    |
| 10  | Step 9 시간 한도                      | ≤ 30분                                     | 수동          |
| 11  | CostGuard 한도 준수                   | call_count ≤ 50 (예상 15~17)               | 자동          |
| 12  | 누적 비용 임계                        | Slice 5 단독 ≤ $0.20                       | 자동          |
| 13  | 모든 산출물 round-trip                | \_safe_write로 검증                        | 자동          |
| 14  | validation_report 6 섹션 작성         | 섹션 수 ≥ 6                                | 수동          |
| 15  | validation_report 광의 단일 정책 적용 | "협의" 표 미포함, 광의 누적 표만           | 자동 (grep)   |
| 16  | refactor_backlog Slice 4·5 처리 결과  | Slice 4 7건 + Slice 5 신규 4건 추적        | 수동          |

### §5.3 롤백 / 실패 시 처리

**케이스 A. Step 6 schema_pass=False (parse 실패)**:

- raw_content 보존
- 사용자 에스컬레이션 — prompt 재설계 또는 schema 조정 결정 필요
- Step 7+ 진입 보류

**케이스 B. Step 6 latency > 16,000ms**:

- THRESHOLDS 재검토 (또는 sonnet 1회 호출로 재시도)
- 실패 지속 시 사용자 에스컬레이션 — fixture 변경 또는 prompt 단축

**케이스 C. Step 8 도중 호출 마진 부족 (CostGuard remaining < 5)**:

- 남은 호출 단계적 진행 (실패한 호출만 재시도)
- 마진 0 도달 시 Step 8 부분 종결 + 부분 manual 평가 + 부분 winner 판정

**케이스 D. Step 9 Slice 1 또는 Slice 3 IDENTICAL 깨짐**:

- **즉시 git revert** (Step 9 commit 취소)
- 사용자 에스컬레이션 (긴급)
- 본 Step 9는 score_step8.py 미수정 + raw/scored JSON 미접촉이므로 발생 가능성 매우 낮음. 발생 시 외부 요인 추적 필요

**케이스 E. Step 9 30분 한도 초과**:

- 진행분 git stash
- format_metrics_to_str + deprecated wrapper만 부분 적용 (회귀 위험 0 보장)
- 호출처 변경(E2/E3) 또는 단위 테스트 부분 적용 가능
- 미완료 분량 = Slice 6 Step 9 슬롯 후보로 이연

**케이스 F. Step 8 winner sonnet (글쓰기 가설 4/5 재평가)**:

- 가설 재평가 분석 추가 (validation_report §4에 명시)
- Slice 6+ 추가 글쓰기 진입점 검증 권장
- 작업 차단 조건 아님 — 결과 반영하여 진행

**케이스 G. (Slice 5 신규) Step 7 #β1 휴리스틱 +50% 편차 재발**:

- chars/3 → chars/2.5 (또는 chars/2.6) 보정 적용
- token_budgets.py:38-44 estimate_input_tokens 본문 1줄 변경
- validation_report §5에 보정 결과 명시
- Slice 4 Step 7 교훈 직접 적용 — 작업 차단 아님

---

## §6. 권한 (Claude Code 균형 모드)

### §6.1 처방 영역 (반드시 지시서대로)

- Step 6 fixture = `e3_baseline_garp_tech` (5 holdings, 3 metrics)
- Step 6 임계 = cost $0.020 / latency 16,000ms
- Step 7 #β1 자연 검증 절차 + 보정 임계 (±20% / +30% / +50%)
- Step 8 매트릭스 = 7 fixture × 2 model = 14 calls (gemini 제외)
- Step 8 DIMENSION_LOOKUP e3 entry 8 필드 (자료 #3 인용 그대로)
- Step 9 시그니처: `format_metrics_to_str(data, *, format: Literal["markdown", "json"]) -> str`
- Step 9 deprecated wrapper 유지 (`format_metrics_table` → `format_metrics_to_str(format="markdown")` 호출)
- Step 9 호출처 변경 = 정확히 2건 (E2 e2_diagnostic_card.py:41 + E3 e3_builder.py)
- validation_report 광의 단일 정책 (협의 표 작성 금지)
- COST_POLICY.md 정합 (광의 정의 일관 적용)
- 환경 차이 자동 변환 8건 (§2.2)
- Step 9 IDENTICAL hash baseline 사전·사후 검증

### §6.2 위임 영역 (Claude Code 판단)

- 변수명, 헬퍼 함수 분리, 로깅 형식
- analyze_e3_groups.py interpretation 임계 미세 조정 (자료 #3 mirror 기본)
- format_metrics_to_str 내부 분기 처리 방식
- 단위 테스트 함수명 세부 표현
- validation_report 섹션 본문 표현 (정책 정의는 처방대로)
- e3 budget 등록값 (실측 P90 × 1.5 기반 자동 산출)

### §6.3 금지 행위 (11건)

| #   | 금지                                                | 사유                                                        |
| --- | --------------------------------------------------- | ----------------------------------------------------------- |
| 1   | Slice 1 `step8_3way_scored.json` 변경               | IDENTICAL KPI 보장                                          |
| 2   | Slice 3 `step8_2way_e2_scored.json` 변경            | IDENTICAL KPI 보장                                          |
| 3   | Slice 4 `step8_2way_e6_scored.json` 변경            | Slice 4 산출물 보존                                         |
| 4   | Slice 1·3·4 raw json 변경                           | 산출물 baseline 보존                                        |
| 5   | Slice 4 step6*smoke*\*\_output.json 변경            | latency 임계 e6 한정 보존                                   |
| 6   | LLMClient.complete 시그니처 변경 (system 인자 추가) | 백로그 #19 위임                                             |
| 7   | LLMClient entrypoint= 인자 추가                     | 백로그 #8 위임                                              |
| 8   | format_metrics_table deprecated wrapper 제거        | 백로그 #21 위임 (Slice 6+)                                  |
| 9   | concentrated_portfolio fixture 추가                 | 백로그 #20 위임                                             |
| 10  | validation_report에 협의/광의 분리 표 작성          | COST_POLICY 정책 위반                                       |
| 11  | \_main_unified() 시그니처 또는 본문 변경            | DIMENSION_LOOKUP 1줄 추가만으로 자동 dispatch (자료 #3 KPI) |

### §6.4 안전장치 (Step 9 처방 비중 ↑)

- Step 9 시작 _직전_ IDENTICAL hash baseline 저장 (§4.9.6)
- Step 9 commit 분리: format_metrics_to_str 신규 + 호출처 2건 + 단위 테스트 — 4 sub-commit 가능
- Step 9 작업 시 score_step8.py 또는 raw/scored JSON 접근 금지
- 환경 차이 추가 발견 시 (자료 #1~#5와 다른 사항): 즉시 사용자 에스컬레이션 (Claude Code report-only 패턴)
- Step 7 #β1 결함 재발 시 즉시 보정 (사용자 에스컬레이션 불필요, 케이스 G 자동 처리)

---

## §7. 산출물

### §7.1 신규 파일 (12건)

| 파일                                                                                          | Step    |
| --------------------------------------------------------------------------------------------- | ------- |
| `scripts/validation/run_step6_e3_smoke.py`                                                    | 6       |
| `docs/portfolio/coach/slice5/step6_smoke_e3_output.json`                                      | 6       |
| `scripts/validation/measure_e3_tokens.py`                                                     | 7       |
| `docs/portfolio/coach/slice5/measure_e3_tokens_output.json`                                   | 7       |
| `scripts/validation/run_step8_2way_e3_retrospective.py`                                       | 8       |
| `docs/portfolio/coach/slice5/step8_2way_e3_raw.json`                                          | 8       |
| `docs/portfolio/coach/slice5/step8_2way_e3_scored.json`                                       | 8       |
| `scripts/validation/analyze_e3_groups.py`                                                     | 8       |
| `docs/portfolio/coach/slice5/step8_2way_e3_group_analysis.json`                               | 8       |
| `docs/portfolio/coach/slice5/validation_report_slice5.md`                                     | report  |
| `docs/portfolio/coach/slice5/refactor_backlog_slice5.md`                                      | backlog |
| `docs/portfolio/coach/slice5/slice5_part2_instructions.md` (본 지시서, 진입 시점에 이미 존재) | —       |

### §7.2 수정 파일 (4건)

| 파일                                                 | Step | 변경 내용                                                                |
| ---------------------------------------------------- | ---- | ------------------------------------------------------------------------ |
| `portfolio/llm/token_budgets.py`                     | 7    | `e3` entry 1줄 추가 (+ #β1 보정 시 estimate_input_tokens 본문 1줄)       |
| `portfolio/tests/test_token_budgets.py`              | 7    | e3 entry 단위 테스트 +3                                                  |
| `scripts/validation/score_step8.py`                  | 8    | `DIMENSION_LOOKUP["e3"]` entry 1줄 추가 (자료 #3 인용 그대로)            |
| `portfolio/services/_prompt_helpers.py`              | 9    | `format_metrics_to_str` 신규 + `format_metrics_table` deprecated wrapper |
| `portfolio/services/e2_diagnostic_card.py:41`        | 9    | 호출처 1줄 변경                                                          |
| `portfolio/prompts/e3/e3_builder.py`                 | 9    | 호출처 1줄 변경                                                          |
| `portfolio/tests/test_prompt_helpers.py` (또는 동등) | 9    | 단위 테스트 +3                                                           |

총 12 신규 + 7 수정 = 19 파일 변경 (Slice 4 Part 2와 유사 분량).

### §7.3 git commit 정책

| Step    | commit 메시지 형식                                                               |
| ------- | -------------------------------------------------------------------------------- |
| 6       | `[slice5] Step 6: E3 smoke (e3_baseline_garp_tech, latency 16k 임계)`            |
| 7       | `[slice5] Step 7: e3 token budget P90 등록 + #β1 자연 검증`                      |
| 8       | `[slice5] Step 8: 14 calls 회고 + DIMENSION_LOOKUP e3 entry + analyze_e3_groups` |
| 9       | `[slice5] Step 9: format_metrics_to_str 일반화 (#11) + E2/E3 호출처 + 단위 +3`   |
| report  | `[slice5] validation_report (광의 단일 정책 첫 적용)`                            |
| backlog | `[slice5] refactor_backlog (Slice 4 11건 + Slice 5 신규 #19~#22)`                |

총 6 commit, Step 단위 분리.

---

## §8. 완료 보고 포맷

Part 2 종결 시점 사용자에게 다음 형식으로 보고:

```
# Slice 5 Part 2 완료 보고 (Slice 5 종결)

## §A. 환경 정합성
- git branch / status / log
- 회귀 (단독): 219 → <225 ±5> passed (+<X>)
- CostGuard 종결 상태: slice_id="slice5", call_count=<X>, total_cost_usd=$<Y>

## §B. Step별 진척
| Step | 산출물 | LLM 호출 | 회귀 변화 | 시간 |
|---|---|---|---|---|
| 6 | smoke + 4 판정 | 1 | 0 | <분> |
| 7 | token + budget + 단위 +3 | 0 | +3 | <분> |
| 8 | 회고 + 그룹 + e3 entry | 14+재시도 | 0 | <분> |
| 9 | #11 일반화 + 단위 +3 | 0 | +3 | <분> |
| report + backlog | 산출물 | 0 | 0 | <분> |

## §C. 신규 / 수정 파일
- 신규 12 + 수정 7 (예상)

## §D. Step별 핵심 결과

### Step 6
- LLM: latency=<>ms, cost=$<>
- 4 판정: 모두 PASS (또는 실패 항목 명시)
- fallback_from: <None | 명시>

### Step 7
- 7 fixture 실측: P90=<>, mean=<>
- budget 결정: e3=<X> tokens
- 사전 추정 1500 정확도: ±<N>%
- #β1 자연 검증: estimate vs actual 평균 delta_pct = ±<N>%
- 보정 적용 여부: <보정 미실시 / chars/2.5 / chars/2.6>

### Step 8
- 14 calls 비용: $<X> (haiku $<Y> + sonnet $<Z>)
- lex_pass_rate: haiku <X>/7, sonnet <Y>/7
- label_means: haiku=<X>, sonnet=<Y>
- **Winner: <haiku | sonnet>**
- 그룹 분석 4매트릭스: <baseline vs focused interpretation>
- **글쓰기 가설 5번째 외삽 검증: <5/5 정착 | 4/5 재평가>**

### Step 9
- 통합 함수: format_metrics_to_str(data, format="markdown"|"json")
- deprecated wrapper: format_metrics_table → format_metrics_to_str 호출
- E2 호출처 변경: 적용 / 미적용
- E3 호출처 변경: 적용 / 미적용
- Slice 1 IDENTICAL: <확인 | revert 발생>
- Slice 3 IDENTICAL: <확인 | revert 발생>
- 시간: <분> / 30분 한도

## §E. 케이스 A~G 발생 여부
- A (Step 6 schema 실패): 발생 / 미발생
- B (Step 6 latency 초과): 발생 / 미발생
- C (Step 8 호출 마진 부족): 발생 / 미발생
- D (Step 9 IDENTICAL 깨짐): **반드시 미발생** (발생 시 즉시 revert 했어야 함)
- E (Step 9 30분 한도 초과): 발생 / 미발생
- F (winner sonnet, 가설 재평가): 발생 / 미발생
- G (Step 7 #β1 +50% 편차 재발): 발생 / 미발생

## §F. 누적 비용 (광의 단일 정책)
- Slice 1: $0.137 / Slice 2: $0.327 / Slice 3: $0.428 / Slice 4: $0.585 / **Slice 5: $<X>**
- Slice 5 단독: $<Slice 5 X> (메인 4스텝 비용 = $<주석>)
- COST_POLICY.md 광의 정의 정합: ✓

## §G. Slice 5 KPI
- [ ] 회귀: <225 ±5> passed (목표 ±5)
- [ ] LLM 호출 마진: <X>/50 (안전 ≥ 5)
- [ ] Step 9 IDENTICAL 검증: Slice 1 + Slice 3 모두 통과
- [ ] D4 round-trip 위반: 0건
- [ ] 글쓰기 가설 외삽 검증: 5/5 정착 또는 4/5 재평가 명시
- [ ] validation_report 6 섹션 작성 (광의 단일 정책)
- [ ] refactor_backlog Slice 4 7건 + Slice 5 신규 4건 처리 결과 추적
- [ ] CostGuard 누적: slice_id="slice5" + call_count 정상

## §H. Slice 6 진입 결정 자료
- 다음 슬라이스 진입점 후보:
  - E4 (대화 Q&A Tier 1~3) — Phase 2 product 시연 가치
  - preset 일반화 (스코어링 엔진 일반화) — Slice 5 5 preset 외삽 결과 활용
  - concentrated_portfolio E3 portfolio-level (#20)
  - LLMClient system 인자 통합 (#19) — 단독 슬라이스로는 작음
- 의존성 / 인프라 준비도 / 예상 매트릭스
- 권장: <글쓰기 가설 5/5 정착 시 E4 / 4/5 재평가 시 preset 일반화 우선>

## §I. Slice 6 사전 결정 보존 권장 (slice6_decisions.md)
- Slice 5 종결 시 사용자 결정 항목:
  1. Slice 6 진입점 (E4 / preset 일반화 / concentrated E3 / 기타)
  2. fixture 전략 (E4 채택 시 Tier별 / preset 일반화 시 매트릭스)
  3. Step 9 슬롯 작업 (백로그 #5/#8/#19 등 PS 순)
```

---

## §9. 변경 이력

### §9.1 본 지시서 변경 이력

| 일자       | 버전 | 변경 사항                                                                      |
| ---------- | ---- | ------------------------------------------------------------------------------ |
| 2026-05-07 | v1.0 | 초안 작성. Slice 5 Part 2 Step 6~9 + validation_report + refactor_backlog 통합 |

### §9.2 Slice 5 결정 변경 이력 (Part 1 + Part 2 통합)

Part 1 6건 + Part 2 7건 = 누적 13건:

| 일자                | 결정                        | 채택                                                   | 가중합    |
| ------------------- | --------------------------- | ------------------------------------------------------ | --------- |
| 2026-05-07 (Part 1) | Q1+N3 매트릭스              | hybrid 7 (GARP3 재활용 + 4 preset focused, 5 카테고리) | 4.40      |
| 2026-05-07 (Part 1) | Q5 Step 9 슬롯 (1차)        | #11 일반화 (`format_metrics_to_str`)                   | 4.80      |
| 2026-05-07 (Part 1) | N1 (system, user) tuple     | service concat + 백로그 #19 등록                       | 4.55      |
| 2026-05-07 (Part 1) | Q3 평가 차원                | naturalness + insight + completeness                   | 4.65      |
| 2026-05-07 (Part 1) | Q6 #γ1 처리                 | 광의 단일 정책 + COST_POLICY.md 신설                   | 5.00      |
| 2026-05-07 (Part 1) | Q4-N2 preset                | 11 preset (concentrated 제외) + 백로그 #20             | 단순 확인 |
| 2026-05-07 (Part 2) | Q5 Step 9 작업 형태         | A: 통합 + E2/E3 모두 변경 + deprecated wrapper         | 4.40      |
| 2026-05-07 (Part 2) | Q1 Step 6 fixture           | e3_baseline_garp_tech (자료 #1 권장)                   | 단순 확인 |
| 2026-05-07 (Part 2) | Q2 latency 임계             | 16,000ms (Slice 4 #9 mirror)                           | 단순 확인 |
| 2026-05-07 (Part 2) | Q3 budget 추정              | 1500 유지                                              | 단순 확인 |
| 2026-05-07 (Part 2) | Q4 Step 8 매트릭스          | hybrid 7 그대로                                        | 단순 확인 |
| 2026-05-07 (Part 2) | N1 환경 차이 3건 추가       | 자동 변환 적용 (8건 통합 명시)                         | 단순 확인 |
| 2026-05-07 (Part 2) | N2 Slice 4 보고서 광의 갱신 | 변경 없음                                              | 단순 확인 |

---

## 부록 A — Slice 5 종결 결정 표 (Part 2 종결 시 갱신)

| 항목                       | 값 (Part 1 시점)                                                             | 값 (Part 2 종결 시 갱신)                          |
| -------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------- |
| 진입점                     | E3 (지표 코멘트, preset 외삽 검증)                                           | (동일)                                            |
| Default provider           | haiku (글쓰기 가설 4/4 정착 외삽)                                            | (Step 8 winner로 검증)                            |
| Fixture 전략               | hybrid 7 (GARP 3 재활용 + 4 preset focused)                                  | (동일)                                            |
| 5 preset 선정              | garp / buffett_quality_value / dividend_growth / quality_factor / contrarian | (동일)                                            |
| 5 카테고리 cover           | value / growth / income / factor / special                                   | (동일)                                            |
| 평가 차원                  | naturalness / insight (manual) + completeness (자동)                         | (동일)                                            |
| Step 6 fixture             | e3_baseline_garp_tech                                                        | (동일)                                            |
| Step 6 임계                | cost $0.020 / latency 16,000ms                                               | (검증 결과 기재)                                  |
| Step 7 e3 budget           | 1차 추정 1500                                                                | <P90 × 1.5 round-up>                              |
| Step 7 #β1 처리            | 자연 검증 절차 명시                                                          | <보정 미실시 / chars/2.5 / chars/2.6>             |
| Step 8 매트릭스            | 7 × 2 = 14                                                                   | (동일)                                            |
| Step 8 winner              | (Part 2 종결 시 기재)                                                        | <haiku / sonnet>                                  |
| Step 8 lex pass rate       | (Part 2 종결 시 기재)                                                        | <haiku N/7 / sonnet N/7>                          |
| 글쓰기 가설 외삽 검증      | (Part 2 종결 시 기재)                                                        | <5/5 정착 / 4/5 재평가>                           |
| Step 9 작업                | #11 일반화 (`format_metrics_to_str` + deprecated wrapper)                    | (Part 2 종결 시 완료/이연 명시)                   |
| Step 0 #γ1 처리            | 광의 단일 정책                                                               | Part 1 완료 ✓, Part 2 validation_report 적용 검증 |
| (system, user) tuple       | service concat (백로그 #19 Slice 6+)                                         | (동일)                                            |
| concentrated_portfolio     | 제외 (백로그 #20)                                                            | (동일)                                            |
| 케이스 A~G 발동            | —                                                                            | (Part 2 종결 시 기재)                             |
| Slice 1·3 IDENTICAL hash   | baseline 명시                                                                | (Part 2 Step 9 후 검증)                           |
| 누적 호출 (Slice 5)        | (Part 2 종결 시 기재)                                                        | <X> / 50                                          |
| 누적 비용 (Slice 5 광의)   | (Part 2 종결 시 기재)                                                        | $<Y>                                              |
| 누적 비용 (Slice 1~5 광의) | $0.585 (진입 시)                                                             | $0.585 + $<Slice 5>                               |
| Slice 6 진입 결정          | Slice 5 종결 회고 시                                                         | (사용자 결정)                                     |

---

## 부록 B — Slice 5 백로그 통합 표

### B.1 Slice 4 11건의 Slice 5 처리 결과

| #   | 항목                                           | PS  | Slice 4 등록 | Slice 5 처리 결과                                          |
| --- | ---------------------------------------------- | --- | ------------ | ---------------------------------------------------------- |
| 11  | metrics_table 일반화 (`format_metrics_to_str`) | 1.5 | 이연         | **Slice 5 Step 9 완료** ✓                                  |
| 5   | TOKEN_BUDGET LLMClient 통합 잔여               | 2.0 | 이연         | Slice 6+                                                   |
| 6   | Step 8 raw output CSV 옵션                     | 1.0 | 이연         | Slice 6+                                                   |
| 7   | Mock LLMClient mode dict 매핑                  | 1.0 | 이연         | Slice 6+                                                   |
| 8   | LLMClient entrypoint 인자 + 가드레일           | 2.5 | 이연         | Slice 6+ Step 9 슬롯 후보                                  |
| 10  | E2 keyword_match 룰 보완                       | 1.5 | 이연         | Slice 6+                                                   |
| 13  | run*step6*\*.py 5종 latency 일괄 16,000ms 상향 | 1.0 | 이연         | run_step6_e3_smoke.py 자연 흡수 1건 + 기존 5 파일 Slice 6+ |
| 14  | score_step8.py CLI 인자 확장                   | 1.5 | 이연         | Slice 6+                                                   |
| 15  | E6 자동 평가 룰 정교화                         | 1.5 | 이연         | <Step 8 회고 자연 흡수 / 미흡수>                           |
| 16  | E6 latency 24s 초과 sonnet 패턴 분석           | 1.0 | 이연         | Slice 6+                                                   |
| 17  | auto_eval_e6.py 패턴 일반화                    | 2.0 | 이연         | Slice 6+                                                   |

**처리율**: Slice 4 11건 중 Slice 5 완료 1건 (#11) + 자연 흡수 부분 1건 (#13).

### B.2 Slice 5 신규 백로그 (Part 1 + Part 2)

| #   | 항목                                                    | PS  | 등록 시점         | 트리거                                        |
| --- | ------------------------------------------------------- | --- | ----------------- | --------------------------------------------- |
| 18  | score_step8_e5.py argparse --entrypoint 인자            | 1.0 | Slice 4 검증 단계 | exit 2 발생 (회귀 영향 0)                     |
| 19  | LLMClient.complete system 인자 추가 (default None)      | 2.0 | Slice 5 Part 1    | E3 (system, user) tuple → service concat 임시 |
| 20  | concentrated_portfolio portfolio-level E3 별도 슬라이스 | 2.0 | Slice 5 Part 1    | 5 preset에서 concentrated 제외                |
| 21  | format_metrics_table deprecated wrapper 제거            | 0.5 | Slice 5 Part 2    | Slice 5 Step 9 후 호출처 통합 완료            |
| 22  | LLMResponse.metadata_dict() 표준 정착 검증              | 1.0 | Slice 5 Part 2    | 4 슬라이스 호출처 일관성 검증                 |

### B.3 Phase 2 위임

| #   | 항목                | PS  | 출처                                         |
| --- | ------------------- | --- | -------------------------------------------- |
| 12  | E6 분석 엔진 재계산 | 5.0 | Slice 4 신규, 슬라이스 분리 가능성 별도 검토 |

### B.4 누적 백로그 합

- Slice 5 진입 시점: ~13건
- Slice 5 신규 (Part 1): #19, #20 (+2)
- Slice 5 신규 (Part 2): #21, #22 (+2)
- Slice 5 처리: #11 완료 (-1), #13 자연 흡수 부분 (계속 이연)
- **Slice 5 종결 누적**: **~16건** (PS 합 ~17.5, 대형 #12 PS 5.0 제외)

---

## 부록 C — 회귀 카운트 진행 표 (Part 1 + Part 2 통합)

| 단계                    | 추가 (단독) | 누적 (단독) | 비고                                                         |
| ----------------------- | ----------- | ----------- | ------------------------------------------------------------ |
| Slice 4 종결            | —           | 173         | baseline                                                     |
| Slice 5 Part 1 Step 0~5 | +46         | 219         | (목표 +37 +9 초과 = 케이스 F, fixture parametrize 14건 효과) |
| **Part 1 종결**         | —           | **219**     | (실측)                                                       |
| Part 2 Step 6           | 0           | 219         | smoke 산출물                                                 |
| Part 2 Step 7           | +3          | 222         | token_budgets 단위                                           |
| Part 2 Step 8           | 0           | 222         | 회고 산출물 + e3 entry                                       |
| Part 2 Step 9           | +3          | **225**     | format_metrics_to_str + 단위 +3                              |
| **Slice 5 종결 예상**   | —           | **225 ±5**  | (Slice 1·2·3·4·5 누적 +52~57)                                |

---

## 부록 D — 분석 엔진 의존성 회피 일관 적용 (Slice 1~5)

E3는 Slice 1·3·4와 동일하게 **분석 엔진 의존성 회피** 정책 일관 유지 (Part 1 → Part 2):

| 항목                         | Part 1                                                                     | Part 2                                                         |
| ---------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------- |
| E3 schema (Request/Response) | analysis_context: dict (이미 산출된 MetricResult만 받음, 정량 재계산 없음) | (동일 유지)                                                    |
| build_e3_input               | Core + Supporting 지표만 (Context 제외) — 산출 결과 조회만                 | (동일 유지)                                                    |
| Mock 응답                    | 자연어 코멘트만 (one_liner 10~300자)                                       | Step 6/8에서 그대로 활용                                       |
| fixture                      | 7개 모두 산출된 MetricResult 형태                                          | Step 7/8에서 그대로 활용                                       |
| Step 6/8 LLM 호출            | (Part 1에는 없음)                                                          | LLM이 자연어 코멘트만 — 수치 검증 없음                         |
| score_step8.py e3 entry      | (Part 1에는 없음)                                                          | naturalness + insight + completeness만 평가 (정량 차원 미사용) |
| validation_report            | (Part 1에는 없음)                                                          | §3 그룹 분석에서도 정량 비교 없음, 자연어 평가만               |

Phase 2 분석 엔진 슬라이스 추가 시:

- 백로그 #12 (E6 분석 엔진 재계산, PS 5.0)에 E3도 포함 가능 — preset별 외삽 모니터링 차원 추가
- 단독 슬라이스로 분리 가능 (DIMENSION_LOOKUP 1줄 추가 패턴 활용)

---

## 부록 E — Slice 4 → Slice 5 mirror 비율 (Part 2)

| 항목                                                | mirror 대상                                   | 비율                         |
| --------------------------------------------------- | --------------------------------------------- | ---------------------------- |
| Step 6 smoke 패턴 (`_json_default` + `_safe_write`) | Slice 4 Step 6 mirror                         | 100%                         |
| Step 7 token 측정 (count_tokens API + P90 × 1.5)    | Slice 4 Step 7 mirror                         | 100%                         |
| Step 7 #β1 자연 검증                                | 신규 (Slice 4 +50% 편차 교훈 적용)            | 신규                         |
| Step 8 회고 매트릭스 (7×2 = 14 calls + Gemini 제외) | Slice 4 Step 8 mirror                         | 100%                         |
| Step 8 그룹 분석 (4매트릭스 + interpretation_guide) | Slice 4 Step 8 mirror                         | 100%                         |
| Step 8 DIMENSION_LOOKUP entry 추가 (자동 dispatch)  | Slice 4 Step 9 #2 산식 통합                   | 100%                         |
| Step 9 일반화 패턴                                  | Slice 4 Step 9 패턴 (deprecated wrapper 추가) | 80% (작업 본질 다름)         |
| validation_report 6 섹션                            | Slice 4 mirror                                | 95% (광의 단일 정책 첫 적용) |
| refactor_backlog 형식                               | Slice 4 mirror                                | 100%                         |
| IDENTICAL KPI (Slice 1·3)                           | Slice 4 Step 9 KPI 일관                       | 100%                         |

전체 Part 2 mirror 비율: **~95%** (구조 모든 영역). 작업 본질·결정 근거·LLM 응답만 위임 영역.

---

## 부록 F — Slice 6 진입 결정 사전 안내 (Slice 5 종결 시 입력)

Slice 5 종결 시 사용자 결정 자료. 본 부록은 frame만 제시.

### F.1 Slice 6 진입점 후보 비교 (frame)

| 후보                                                | 사전 등록 근거                         | 의존성                | 인지부하  | Slice 5 catalyst 충전 항목                  |
| --------------------------------------------------- | -------------------------------------- | --------------------- | --------- | ------------------------------------------- |
| **F.1.a E4 (대화 Q&A Tier 1~3)**                    | Coach 핵심 가치 + Phase 2 product 시연 | Tier 다층 (높음)      | 매우 높음 | Slice 5 글쓰기 가설 5/5 정착 시 안전        |
| **F.1.b preset 일반화 (스코어링 엔진 일반화)**      | preset 인터페이스 검증 결과 활용       | 단독 (낮음)           | 중간      | Slice 5 5 preset 외삽 결과 + insight 그룹차 |
| **F.1.c concentrated_portfolio E3 portfolio-level** | 백로그 #20 (PS 2.0)                    | 단독                  | 중간      | Slice 5 E3 패턴 정착                        |
| **F.1.d LLMClient 통합 (#19 또는 #8)**              | 백로그 #19 / #8                        | 4슬라이스 호출처 정비 | 낮음      | 단독 슬라이스로는 작음 — Step 9 슬롯 적합   |

### F.2 Slice 6 진입점 결정 영향 자료

- **글쓰기 가설 5번째 외삽 검증 결과** (Slice 5 Part 2 Step 8 winner)
  - 5/5 정착 → E4 진입 안전 (Tier 2~3 default haiku)
  - 4/5 재평가 → preset 일반화 우선 + 추가 글쓰기 진입점 검증
- **5 preset 외삽 insight 그룹차** (Slice 5 Part 2 Step 8 그룹 분석)
  - 그룹차 ≤ 0.50 → preset 일반화 안전
  - 그룹차 > 0.50 (Slice 3 위험 재발) → preset 일반화 보류, E4 우선

### F.3 Slice 6 Step 9 슬롯 후보 (백로그 ~16건 중)

| #   | 항목                                    | PS  | 자연 흡수 가능성            |
| --- | --------------------------------------- | --- | --------------------------- |
| 19  | LLMClient system 인자 추가              | 2.0 | 슬라이스 6 진입점 따라 변동 |
| 8   | LLMClient entrypoint 인자 + 가드레일    | 2.5 | High                        |
| 17  | auto_eval_e6.py 패턴 일반화 (E2와 통합) | 2.0 | E4 진입 시 자연 흡수        |
| 5   | TOKEN_BUDGET LLMClient 통합 잔여        | 2.0 | Medium                      |

### F.4 Slice 6 사전 결정 보존 권장 (slice6_decisions.md frame)

```markdown
# slice6_decisions.md

> 작성일: (Slice 5 종결 시점)

## 진입점 결정

- 1순위 후보: <E4 / preset 일반화 / concentrated E3 / LLMClient 통합>
- 근거: <Slice 5 winner / 그룹차 / Phase 2 가치>

## 진입점별 사전 결정

- E4 채택 시:
  - Tier 1~3 fixture 신규 인프라
  - default provider: Tier 1 추출=sonnet / Tier 2~3 글쓰기=haiku
  - Step 9 슬롯: #19 또는 #8
- preset 일반화 채택 시:
  - 스코어링 엔진 일반화 작업
  - Step 9 슬롯: #8
- concentrated E3 채택 시:
  - portfolio-level commentary schema
  - Step 9 슬롯: #19

## 누적 결정 (Slice 1~5 보존)

- (Slice 1~5 결정 표 통합)
```

---

## 부록 G — Step 9 IDENTICAL hash 검증 절차 (확장)

본 부록은 Slice 5 Part 2 Step 9의 IDENTICAL KPI 검증 절차를 정확한 형식으로 보존.

### G.1 사전 baseline 저장 (Step 9 작업 _직전_)

```bash
mkdir -p /tmp/slice5_step9
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json | awk '{print $1}' > /tmp/slice5_step9/baseline_e1.sha256
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json | awk '{print $1}' > /tmp/slice5_step9/baseline_e2.sha256

# 기대값 (자료 #5 인용):
echo "917fa3ef821426e88178456a1f70462f5ab9576e20f06a63d0a88c28fcc0f7b9" | diff - /tmp/slice5_step9/baseline_e1.sha256
echo "5594c6ab9291213bca7d3e98b3b221164575eb47c52a281248ddc616218cf3ba" | diff - /tmp/slice5_step9/baseline_e2.sha256
# 둘 다 출력 없음 = 진입 baseline 정합 ✓
```

### G.2 사후 검증 (Step 9 작업 _직후_)

```bash
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json | awk '{print $1}' | diff - /tmp/slice5_step9/baseline_e1.sha256
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json | awk '{print $1}' | diff - /tmp/slice5_step9/baseline_e2.sha256
# 둘 다 출력 없음 (no diff) = IDENTICAL ✓
```

### G.3 hash 차이 발견 시

```bash
# 즉시 git revert (Step 9 commit 취소)
git log --oneline -1  # 최근 commit hash 확인
git revert --no-edit HEAD

# 사용자 에스컬레이션 — 케이스 D
# 본 Step 9는 score_step8.py 미수정 + raw/scored JSON 미접촉이므로
# hash 차이 발견 시 외부 요인 추적 필요 (다른 commit / 파일시스템 / encoding 등)
```

### G.4 작업 영역 분리 (안전장치)

Step 9 작업 시 _접근 금지_ 파일 (회귀 위험 0 보장):

- `scripts/validation/score_step8.py` (Step 8에서 e3 entry만 추가, Step 9에서는 미접촉)
- `docs/portfolio/coach/slice1/step8_3way_*.json` (Slice 1 산출물)
- `docs/portfolio/coach/slice3/step8_2way_e2_*.json` (Slice 3 산출물)
- `docs/portfolio/coach/slice4/step8_2way_e6_*.json` (Slice 4 산출물)

Step 9 작업 영역:

- `portfolio/services/_prompt_helpers.py` (신규 함수 + deprecated wrapper)
- `portfolio/services/e2_diagnostic_card.py:41` (1줄)
- `portfolio/prompts/e3/e3_builder.py` (1줄)
- `portfolio/tests/test_prompt_helpers.py` 또는 동등 (단위 테스트 +3)
