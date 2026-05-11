# Slice 6 Part 1 v2 — 작업 지시서

> **버전**: v2 (사전 baseline 자료 반영)
> **시점**: Slice 5 종결 / Slice 6 Part 1 미실행
> **브랜치**: `portfolio`
> **누적 회귀**: 232 / 누적 광의 비용: $0.764
> **대상 진입점**: concentrated_portfolio E3 portfolio-level

---

## 0. 컨텍스트

Slice 6 = E3 진입점을 종목 단위 → portfolio 단위로 확장. Part 1 = 사전 설계 단계 (정적 분석, LLM 호출 0건).

**v1 → v2 핵심 보정**:

- e3_portfolio 잠정 budget: 2,500 → **9,500/10,000** (holdings 차원 추가)
- Schema: 4 필드 → **6 필드** (holistic + diversification + sector_balance + risk_concentration + preset_alignment + confidence)
- Prompt 변수: Core 7종 직접 → **도메인 추상화 7종** (분석엔진 사전 산출값 활용)
- 변형 5종: risk pattern → **preset 5 카테고리 cover** (Slice 5 hybrid 7 mirror)
- 분기 시나리오 E1~E4 처리 절차 통합

**진행 순서**: Step 0 → Step 1 (sequential, Step 1 schema 길이가 Step 0 baseline 의존)

---

## 1. Step 0 — #β2 Budget 추정 입출력 분리 모델

### 1.1 목적

e3 종목 +366% 편차(1차 추정 1,500 vs 실측 P90 4,359) 본질 해결. 입력/출력 토큰을 분리 추정해 어느 쪽이 ballooning됐는지 추적 가능한 일반화 모델 구축.

### 1.2 산출물

1. `app/portfolio/coach/budget_estimator.py` 신규 모듈
   - 함수: `estimate_budget_for_entrypoint(entrypoint: str, sample_prompts: list) -> dict`
   - 반환: `{"input": int, "output": int, "total": int, "total_with_buffer": int}`
2. `token_budgets.py` `ENTRY_POINT_META` dict 확장 (e3_portfolio placeholder 등록)
3. 회귀 테스트 +5 (`tests/portfolio/coach/test_budget_estimator.py`)
4. `docs/portfolio/coach/slice6/step0_budget_model.md` 결정 보존 (50줄 수준)

### 1.3 입력 추정기 (`InputTokenEstimator`)

- 기존 `token_budgets.estimate_input_tokens` 재사용 (#β1 closed, 평균 +2.9% 정상)
- 진입점 메타에서 prompt template path + 변수 슬롯 수 receive
- 5 진입점 실측 P90 데이터로 편차 ±15% 이내 검증

### 1.4 출력 추정기 (`OutputTokenEstimator`)

필드 타입별 baseline (한국어 1.5~2.5 char/token):

| 필드 타입             | 평균 토큰 | 사례                                   |
| --------------------- | --------- | -------------------------------------- |
| str_short (≤50자)     | 20~40     | E1.headline, E5.confidence note        |
| str_medium (51~200자) | 60~150    | E1.summary, E2 항목 코멘트             |
| str_long (insight)    | 100~250   | E2.weaknesses, E3.one_liner            |
| list[str] (3~5개)     | 100~300   | E2.strengths/weaknesses/actions        |
| Literal/enum          | 3~8       | E5.AdjustmentAction, E6.E6ChangeAspect |
| int/float             | 2~5       | confidence (1~5), delta_weight         |

- buffer: `total = (input + output) × 1.5` safety_factor
- round-up 500 단위

### 1.5 진입점 메타 dict (`ENTRY_POINT_META`)

```python
ENTRY_POINT_META = {
    "e1": {"prompt_path": ..., "var_slots": ..., "schema_fields": ...},
    "e5": {...},
    "e2": {...},
    "e6": {...},
    "e3": {...},
    "e3_portfolio": {  # Step 1 schema 확정 후 실값 대체
        "prompt_path": "app/portfolio/coach/prompts/e3_portfolio.txt",
        "var_slots": 7,
        "schema_fields": [...],  # B1 schema 6 필드
    },
}
```

### 1.6 5 진입점 backtest (핵심 검증)

| 진입점 | 등록 budget | 실측 P90  | 비고                                               |
| ------ | ----------- | --------- | -------------------------------------------------- |
| e1     | 5,000       | ~3,700    | 글쓰기 진입점, 1차 추정 적중                       |
| e5     | 2,000       | 756       | 추출, P90×1.5=1134→2000                            |
| e2     | 1,500       | 686       | 글쓰기, P90×1.5=1029→1500                          |
| e6     | 1,500       | 845       | 글쓰기, P90×1.5=1268→1500                          |
| **e3** | **7,000**   | **4,359** | **글쓰기, 1차 추정 1,500 대비 +366% (#β2 트리거)** |

→ **핵심**: e3에 새 모델 적용 시 ±20% 이내 추정 필요 (실패 시 분기 E1)

### 1.7 회귀 테스트 (+5)

```
test_estimate_budget_for_entrypoint_basic
test_estimate_budget_for_entrypoint_5_entrypoints_within_20pct
test_estimate_budget_for_entrypoint_round_up_500
test_estimate_budget_for_entrypoint_safety_factor_default
test_estimate_budget_for_entrypoint_unknown_entrypoint_raises
```

### 1.8 Acceptance Criteria

| 항목              | 기준                                |
| ----------------- | ----------------------------------- |
| 5 진입점 backtest | total 편차 ≤ ±20% (5건 모두)        |
| e3 핵심 검증      | 새 모델 추정 vs P90 4,359 ±20% 이내 |
| 입력 추정         | 5 진입점 input P90 vs 추정 ≤ ±15%   |
| 출력 추정         | 5 진입점 output P90 vs 추정 ≤ ±20%  |
| 회귀              | +5 PASS, 기존 232 영향 0건          |
| 비용              | $0 (정적 분석 + count_tokens API만) |

---

## 2. Step 1 — E3PortfolioCommentary Schema 설계

### 2.1 목적

portfolio-level commentary Pydantic schema 확정. Core 7종 + 분석엔진 사전 산출값 → portfolio 단위 진단 코멘트 인터페이스 정의. 매트릭스 변형 5종 명세 작성.

### 2.2 산출물

1. `app/portfolio/coach/schemas/e3_portfolio.py` Pydantic schema
2. `app/portfolio/coach/prompts/e3_portfolio.txt` prompt template
3. `tests/portfolio/coach/fixtures/v1_v5_concentrated.py` 변형 5종 fixture
4. `DIMENSION_LOOKUP[e3_portfolio]` entry 추가
5. 회귀 테스트 +4~8
6. `docs/portfolio/coach/slice6/portfolio_variants.md` (50줄 수준)

### 2.3 Pydantic schema (B1 baseline)

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class E3PortfolioCommentary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holistic_assessment: str = Field(
        ..., min_length=30, max_length=300,
        description="포트폴리오 전체 평가 2~3문장"
    )
    diversification_comment: str = Field(
        ..., min_length=20, max_length=200,
        description="분산 정도 한 줄 평가"
    )
    sector_balance_comment: str = Field(
        ..., min_length=20, max_length=200,
        description="섹터 균형 평가"
    )
    risk_concentration_comment: str = Field(
        ..., min_length=20, max_length=200,
        description="집중 리스크 평가"
    )
    preset_alignment: Literal["aligned", "partial", "misaligned"] = Field(
        ..., description="preset 의도 정합성"
    )
    confidence: int = Field(
        ..., ge=1, le=5,
        description="LLM 평가 자신도 1~5"
    )
```

**출력 토큰 추정**: 200 + 150 + 150 + 150 + 5 + 3 ≈ **660** → ×1.5 buffer ≈ 1,000
**총 budget**: input 9,500 + output 700 → ×1.5 = 10,500 → **잠정 10,500** (Step 0 backtest 결과로 reconciliation)

### 2.4 Prompt template 변수 슬롯 7종

```
{preset_id}              # preset 식별자
{preset_intent}          # preset 의도 (GARP=합리적 가격 성장 등)
{holdings_summary}       # 보유 종목 평탄화 요약
{sector_concentration}   # 섹터 집중도 (분석엔진 사전 산출)
{diversification_score}  # 분산 점수 (분석엔진)
{risk_concentration_score} # 집중 리스크 점수 (분석엔진)
{core_metrics_summary}   # Core 7종 raw 평탄화
```

- Slice 5 `build_e3_prompt` mirror + portfolio-level 차원 변경
- few-shot examples 2개: `concentrated_balanced` + `concentrated_misfit`
- preset_id별 의도 명시 (5 카테고리 cover 위해)

### 2.5 변형 5종 fixture (V1~V5)

`concentrated_portfolio` 정의: holdings 5~10 + 1~2 sector 60%+ 집중

| Case                      | holdings | sector top      | diversification | preset                | 카테고리              |
| ------------------------- | -------- | --------------- | --------------- | --------------------- | --------------------- |
| V1. concentrated_balanced | 5        | 50%             | 0.35            | GARP                  | growth — alignment    |
| V2. concentrated_misfit   | 5        | 80%             | 0.15            | GARP                  | growth — misalignment |
| V3. concentrated_large    | 10       | 70% (×2 sector) | 0.25            | quality_factor        | factor                |
| V4. concentrated_value    | 5        | value-tilted    | —               | buffett_quality_value | value                 |
| V5. concentrated_dividend | 7        | dividend-tilted | —               | dividend_growth       | income                |

→ **5 카테고리 cover**: growth / value / income / factor / special(V2 misfit이 contrarian-ish 패턴으로 cover)
→ Slice 5 hybrid 7 패턴 mirror, concentrated 추가 차원만 신설

### 2.6 DIMENSION_LOOKUP entry (Slice 5 e3 mirror 100%)

```python
"e3_portfolio": {
    "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
    "dim2": {"key": "insight", "manual_field": "insight_manual"},
    "model_label_field": "model_label",
    "result_structure": "nested",
    "default_raw":    "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
    "default_scored": "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json",
    "weight": 0.5,
    "additional_lex_check": "completeness_auto",
},
```

→ `_main_unified()` 변경 0줄. 자동 dispatch ready.

### 2.7 회귀 테스트 (+4~8)

```
test_e3_portfolio_schema_validates
test_e3_portfolio_6_categories_cover
test_e3_portfolio_dimension_lookup_dispatch
test_e3_portfolio_v1_v5_fixtures (parametrize 5)
```

### 2.8 Acceptance Criteria

| 항목          | 기준                                                                                                      |
| ------------- | --------------------------------------------------------------------------------------------------------- |
| schema 일관성 | 6 카테고리 cover 자동 검증 PASS (5 preset + concentrated 차원)                                            |
| Core 7종      | hhi/sector_hhi/top3/holding_count/beta/max_position/avg_corr 모두 prompt 변수로 매핑                      |
| 출력 schema   | 6 필드 (holistic + diversification + sector_balance + risk_concentration + preset_alignment + confidence) |
| 변형 5종      | V1~V5 fixture 사전 fix, 5 카테고리 cover                                                                  |
| 자동 dispatch | DIMENSION_LOOKUP entry → `_main_unified()` 변경 0줄 동작                                                  |
| 회귀          | +4~8 PASS, 기존 232+5=237 영향 0건                                                                        |
| 비용          | $0 (LLM 호출 0)                                                                                           |

---

## 3. 분기 시나리오 처리 절차

### E1 — Step 0 backtest 편차 >20%

- 입력/출력 어느 쪽 편차인지 컬럼별 식별
- `input 편차 ≫ output`: prompt 구조(system + few-shot) 반영 미흡 → input estimator에 system token 가중치 도입
- `output 편차 ≫ input`: schema 필드 길이 추정 미흡 → 1.4 baseline 재캘리브레이션
- **Step 0.5 보정 사이클**: safety_factor 1.5 → 2.0 또는 진입점별 가중치 도입

### E2 — e3_portfolio 추정 vs 잠정 9,500/10,000 편차 >30%

- `token_budgets["e3_portfolio"]` 재조정
- 동시에 schema 필드 길이 재검토 (B1 max_length 축소 검토)

### E3 — A3 baseline 어긋남 (예: str_long 추정 250 vs 실측 400)

- Step 1 schema 필드 타입 재분류 (str_long → str_xlong 신설 or max_length 명시)
- Part 2 prompt template 수정 trigger

### E4 — 6 카테고리 cover FAIL

- V6 추가 (e.g., `contrarian_concentrated`, special 카테고리 명시 보강)
- **Step 1.5 보정 사이클** (Part 2 진입 보류)

---

## 4. Part 1 종합 KPI

| 항목       | 목표                                           |
| ---------- | ---------------------------------------------- |
| 회귀 누적  | 232 → 240~245 (+8~13)                          |
| 비용 단독  | $0 (정적 분석, count_tokens API만)             |
| 누적 광의  | $0.764 → $0.764 (불변)                         |
| 신규 부채  | 0건 예상, 발생 시 ID + PS 명시                 |
| 부채 close | **#β2 close** (PS 3.0) → 누적 백로그 ~17 → ~16 |
| 소요 시간  | 1.5~2시간 (Step 0 30~45분 + Step 1 45~60분)    |

---

## 5. 회수 양식 (Step 0/1 실행 후)

```
[Slice 6 Part 1 완료 보고]

== Step 0 ==
A1. backtest 편차 표 (input_p90 fixed):
  e1: input_est=___, p90=3700, output_est=___, p90=___, total_dev=±__%
  e5: input_est=___, p90=756,  output_est=___, p90=___, total_dev=±__%
  e2: input_est=___, p90=686,  output_est=___, p90=___, total_dev=±__%
  e6: input_est=___, p90=845,  output_est=___, p90=___, total_dev=±__%
  e3: input_est=___, p90=4359, output_est=___, p90=___, total_dev=±__%
  → 핵심: e3가 1차 추정 1,500 대비 새 모델은 ±20% 이내인가? Y/N

A2. e3_portfolio 통합 추정:
  input=___, output=___, total_with_buffer=___
  → 잠정 9,500/10,000 대비 편차 ___%
  → >30% 시 E2 분기 trigger

A3. 필드 타입별 baseline 검증:
  str_short:  추정 20~40   vs 실측 ___
  str_medium: 추정 60~150  vs 실측 ___
  str_long:   추정 100~250 vs 실측 ___
  list_str:   추정 100~300 vs 실측 ___
  literal:    추정 3~8     vs 실측 ___
  int/float:  추정 2~5     vs 실측 ___
  → 어긋남 발견 시 E3 분기 trigger

A4. 회귀 신규 +___개 (목표 +5)

A5. 신규 부채: ___ (또는 "0건")

== Step 1 ==
B1. E3PortfolioCommentary 최종 schema:
  [Pydantic class 정의 그대로 첨부, 6 필드 검증]

B2. prompt template:
  [전체 텍스트 또는 변수 슬롯 7종 placeholder 위치]

B3. V1~V5 fixture (각 holdings/sector_concentration/diversification/preset_id):
  V1: ___
  V2: ___
  V3: ___
  V4: ___
  V5: ___

B4. DIMENSION_LOOKUP[e3_portfolio] entry:
  [1줄 entry, mirror 검증]

B5. 6 카테고리 schema 일관성: PASS / FAIL
  → FAIL 시 누락 카테고리 명시 (E4 분기 trigger)

== 종합 ==
- 누적 회귀: 232 → ___
- Part 1 단독 비용: $___
- 누적 광의: $0.764 → $___
- 기존 232 영향: ___건
- Part 1 소요 시간: Step 0 ___분 / Step 1 ___분
- 분기 시나리오 발동: E1 / E2 / E3 / E4 / 없음
```

---

## 6. 작업 흐름 (Claude Code용)

1. **Step 0 실행** (sequential)
   - `budget_estimator.py` 신규 작성
   - 입력/출력 추정기 구현
   - 5 진입점 backtest 실행
   - 회귀 +5 추가
   - **편차 ±20% 이내 확인 → 통과 시 Step 1, 실패 시 E1 분기**

2. **Step 1 실행** (Step 0 통과 후)
   - `e3_portfolio.py` schema + `e3_portfolio.txt` prompt
   - V1~V5 fixture 작성
   - `DIMENSION_LOOKUP` entry 추가
   - 6 카테고리 일관성 검증
   - 회귀 +4~8 추가
   - **6 카테고리 PASS → 통과, FAIL 시 E4 분기**

3. **결과 회수**
   - 위 5번 양식 그대로 채워서 보고
   - 분기 시나리오 발동 여부 명시

4. **commit 메시지 권장**
   - `feat(slice6/step0): add input/output split budget estimator (#β2 close)`
   - `feat(slice6/step1): add E3PortfolioCommentary schema + V1~V5 fixtures`
