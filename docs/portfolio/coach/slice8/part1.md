# Slice 8 Part 1 최종 실행 지시서

> **Stock-Vis Portfolio Coach — LLM 진단 코멘트 파이프라인 input 보강 trio 통합 1단계**

---

## 메타 정보

| 항목           | 값                             |
| -------------- | ------------------------------ |
| 작성일         | 2026-05-16                     |
| 브랜치         | `portfolio`                    |
| docs 경로      | `docs/portfolio/coach/slice8/` |
| 확정 옵션      | A1 + B2 + C2                   |
| 비용 임계      | $2.00 (사전 경고 $1.60)        |
| Fallback 임계  | 회귀 +25                       |
| 누적 시작점    | 회귀 410 / 비용 $1.595         |
| 예상 회귀 증가 | +12 ~ +26                      |
| 예상 비용 증가 | $0 (LLM 호출 없음)             |

---

## 0. 컨텍스트

### Slice 7 종결 상태 (2026-05-15)

- 회귀 410 / 누적 $1.595 (구 임계 $1.50 -0.6% FAIL → 신 임계 $2.00 상향 처리)
- LLM budget 81/50 override 발생 → **#33 budget 분리 동기**
- rationale 75% "구체성 부족" 시스템 결함 확인 → **#27 input 보강 동기**
- #β2 max delta 52.21% systematic underestimate (-50% bias) → **estimator 재설계 동기**
- 분포 폭 2 < 3.0 → **#26 keep_open** (rubric 강화 필요)
- IDENTICAL 7/7 유지

### Slice 8 사전 결정 (D-1/D-2/D-3, 2026-05-15)

- **D-1:** 비용 임계 $1.50 → $2.00, CostGuard 80% 사전 경고 $1.60, Slice 9 재상향 트리거 $2.10
- **D-2 trio 통합:** Part1 #27 input → Part2 #28 schema → Part3 #29 prompt+matrix → Part4 manual eval
- **D-3 Step 0 묶음:** #26 rubric + #β2 estimator + #33 budget 분리 동시 처리
- 회귀 격리 KPI ±30%
- Fallback: Part 1 회귀 +25 초과 시 #28/#29 Slice 9 분리

### Part 1의 임무

Step 0 묶음을 안전하게 닫고 + #27 input 보강의 토대(schema)를 정의해서 + Part 2~4가 안정적으로 진입할 수 있는 활주로를 깐다. 비용은 0에 가깝게 유지.

---

## Step 0-1: #33 budget 분리 (PER_INSTANCE=50 / PER_SLICE=100)

### 목적

S7 LLM budget override(81/50) 재발 차단. 후속 Step 0-2/0-3 작업의 격리 안전망 확보.

### 대상 파일

- `portfolio/coach/cost_guard.py` (수정)
- `portfolio/coach/exceptions.py` (신규 또는 수정)
- `docs/portfolio/coach/COST_POLICY.md` (갱신)
- `tests/portfolio/coach/test_cost_guard.py` (신규/추가)

### 작업 상세

#### 1. `BudgetExceededError` 정의

```python
from typing import Literal

class BudgetExceededError(Exception):
    def __init__(self, scope: Literal["instance", "slice"], count: int, limit: int):
        self.scope = scope
        self.count = count
        self.limit = limit
        super().__init__(f"LLM budget exceeded ({scope}): {count}/{limit}")
```

#### 2. `CostGuard` 클래스 변경 (싱글톤 패턴 유지)

- 추가 속성:
  - `_per_instance_count: int = 0`
  - `_per_slice_count: int = 0`
  - `PER_INSTANCE_LIMIT: int = 50` (클래스 상수)
  - `PER_SLICE_LIMIT: int = 100` (클래스 상수)
- 추가 메서드:
  - `start_instance(self) -> None`: `_per_instance_count = 0`로 초기화
  - `check_per_instance(self) -> None`: 50 도달 시 `BudgetExceededError(scope="instance", ...)` raise
  - `check_per_slice(self) -> None`: 100 도달 시 `BudgetExceededError(scope="slice", ...)` raise
  - `record_llm_call(self) -> None`: 두 카운터 모두 +1 후 두 체크 호출
- `reset_for_slice` 멱등 패턴 유지하되 두 카운터 모두 0으로.

#### 3. 기존 호출 지점 마이그레이션

- 기존 `check()` 호출하는 모든 지점을 `record_llm_call()`로 치환.
- `record_llm_call`은 `LLMClient.call` 직전 1회만 호출되어야 함 (중복 카운트 방지).

#### 4. `COST_POLICY.md` §LLM budget 섹션 갱신

- 두 카운터 분리 정책 명문화
- S7 override 사례(81/50, Slice 7 Part 4) 부록 §Appendix A로 추가
- 임계 변경 이력: 50 단일 → PER_INSTANCE=50 / PER_SLICE=100 (Slice 8 발효)

#### 5. 신규 단위 테스트

- `test_cost_guard_per_instance_limit`: 50회 PASS, 51회 시 `BudgetExceededError(scope="instance")` raise
- `test_cost_guard_per_slice_limit`: 동일 패턴, 100/101
- `test_cost_guard_start_instance_resets_only_instance_counter`: slice counter 보존 확인
- `test_cost_guard_reset_for_slice_idempotent`: 두 카운터 0 + 멱등성
- `test_cost_guard_singleton_preserved`: 싱글톤 인스턴스 동일성

### KPI

- [ ] 회귀 격리 ±30% (예상 +3~7건)
- [ ] IDENTICAL hash 7/7 유지 (`test_static_integrity` PASS)
- [ ] 신규 단위 테스트 5건 모두 PASS
- [ ] 기존 회귀 테스트에서 LLM 호출 카운트 흐름 변경 없음

### 실패 시 처리

- IDENTICAL 위반: 즉시 중단, 호출 지점 마이그레이션 누락 점검
- 회귀 +7 초과: 호출 중복 카운팅 여부 점검

---

## Step 0-2: #β2 estimator 재설계

### 목적

S5(+366%) ~ S7(-52.21%) systematic bias 해소. max delta ≤ 30% 달성.

### 대상 파일

- `portfolio/coach/token_budgets.py` (수정)
- `tests/portfolio/coach/test_budget_estimator.py` (수정/추가)
- `docs/portfolio/coach/slice8/budget_estimator_v2.md` (신규, fit 보고서)

### 작업 상세

#### 1. 현행 estimator 진단 보고서 (`budget_estimator_v2.md` §1)

| 슬라이스 | 진입점       | 추정     | 실측 P90 | delta      |
| -------- | ------------ | -------- | -------- | ---------- |
| S5       | e3           | 1500     | 4359     | +290.6%    |
| S6       | e3_portfolio | (기록값) | 4030     | (기록값)   |
| S7       | Part 3 KPI   | (기록값) | (기록값) | max 52.21% |

- bias 패턴: 모두 systematic underestimate (단방향, -50% bias)

#### 2. 새 모델: 섹션 합산 추정기

```python
def estimate_input_tokens(entry: str, fixture: dict) -> int:
    input_tokens = _estimate_input_section(fixture)         # raw values + 시계열
    metric_tokens = _estimate_metric_section(fixture)       # metric 리스트
    instruction_tokens = _estimate_instruction_section(entry)  # 진입점별 상수
    overhead = _ENTRY_OVERHEAD[entry]                       # 진입점별 보정 상수
    return input_tokens + metric_tokens + instruction_tokens + overhead
```

#### 3. 보정 계수 fit

- 입력 데이터: S5/S6/S7 실측 `(entry, input_tokens_actual)` 튜플
- 단순 선형 회귀 (numpy 또는 수동 OLS) — **sklearn 의존성 추가 금지**
- `_ENTRY_OVERHEAD` 딕셔너리에 진입점별 상수 보관
- fit 결과를 `budget_estimator_v2.md` §2에 표로 기록

#### 4. 검증

- 5슬라이스 실측 데이터에 대해 새 estimator의 delta 계산
- max delta ≤ 30% 검증 → PASS / FAIL 명시

#### 5. 단위 테스트

- `test_estimator_section_decomposition`: 세 섹션 함수가 각각 양수 반환
- `test_estimator_fit_max_delta_within_30pct`: 5슬라이스 데이터에 대해 max delta ≤ 30%
- `test_estimator_monotonic_in_input_size`: input 크기 증가 시 추정값 단조증가

### KPI

- [ ] 회귀 격리 ±30% (예상 +2~5건, estimator는 격리 모듈)
- [ ] max delta ≤ 30% PASS
- [ ] IDENTICAL 7/7 유지

### 실패 시 처리 (KPI 미달)

- max delta > 30%: `#β2 keep_open` 유지, Slice 9 Step 0 재후보 등록
- **단, Part 1은 계속 진행** (estimator 재설계는 격리 작업이므로 다음 Step에 영향 없음)
- `budget_estimator_v2.md` §3에 미달 사유 분석 기록

---

## Step 0-3: #26 rubric 5→10단계 + 양극단 + 분포 폭 자동 게이트

### 목적

S7 manual eval "큰 차이 없음" 관찰 + 분포 폭 2 < 3.0 keep_open 해소. rubric 신호 변별력 강화.

### 대상 파일

- `docs/portfolio/coach/manual_eval_rubric.md` (대규모 갱신)

### 작업 상세

#### 1. 10단계 척도 재정의 (§A)

| 점수 | 정의        | 앵커                                              |
| ---- | ----------- | ------------------------------------------------- |
| 1    | 완전 부적합 | 지표 이름만 나열, raw values 없음, 시계열 부재    |
| 2-3  | 결함 명확   | raw 일부만, 시계열 부재                           |
| 4-5  | 부분 적합   | raw 충실, 시계열/벤치마크 부재                    |
| 6-7  | 기본 충족   | raw + 시계열 일부, 동종 비교 없음                 |
| 8-9  | 우수        | raw + 시계열 + 동종 비교                          |
| 10   | 완벽        | naturalness + insight 양축 만점, 사용자 맥락 포함 |

#### 2. 양극단 앵커 사례 (§B)

- **1점 앵커:** S7 Part 4의 실제 rationale 인용 (75% "구체성 부족" 패턴 사례)
- **10점 앵커:** 가상의 이상적 출력 예시 (raw + 4Q 시계열 변화율 + 동종 비교 + portfolio 맥락)

#### 3. KPI §C 분포 폭 자동 게이트 룰 명문화

- "manual eval 분포 폭 (max - min) ≥ 3.0 시 #26 자연 close"
- "< 3.0 시 keep_open 유지, Slice 9 Step 0 재후보 등록"
- "score 스크립트 출력에 분포 폭 자동 보고 포함" (Part 4 구현, Part 1은 룰 명문화만)

#### 4. 운영 노트 (§D)

- 10단계 전환 시 기존 5단계 평가와의 매핑 표:

| 기존 5단계 | 신규 10단계 |
| ---------- | ----------- |
| 1          | 1-2         |
| 2          | 3-4         |
| 3          | 5-6         |
| 4          | 7-8         |
| 5          | 9-10        |

- Slice 7까지의 manual eval 데이터는 5단계 그대로 유지 (**재평가 금지, 비용 보호**)

### KPI

- [ ] 회귀 0건 (docs only)
- [ ] rubric §C 분포 폭 자동 게이트 룰 명문화 PASS (텍스트 검증)

---

## Step 1: #27 input schema 정의 (B2 — raw + 시계열 1Q/4Q/12Q)

### 목적

S7 "rationale 75% 구체성 부족" 시스템 결함 해소. LLM input에 시계열 컨텍스트 주입 토대 마련.

### 대상 파일

- `portfolio/coach/schemas/commentary_input.py` (수정)
- `tests/portfolio/coach/test_commentary_input_schema.py` (수정/추가)

### 작업 상세

#### 1. `TimeSeriesContext` 모델 정의

```python
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel

class TimeSeriesContext(BaseModel):
    current: Decimal
    window_1q: Optional[Decimal] = None   # 1분기 전
    window_4q: Optional[Decimal] = None   # 4분기 전
    window_12q: Optional[Decimal] = None  # 12분기 전

    @property
    def delta_4q_pct(self) -> Optional[Decimal]:
        """4분기 변화율 (UI/LLM 표시용 helper)"""
        if self.window_4q is None or self.window_4q == 0:
            return None
        return (self.current - self.window_4q) / abs(self.window_4q) * 100
```

#### 2. 기존 metric 모델에 필드 추가 (backward-compat 유지)

- 모든 metric 모델에 `time_series: Optional[TimeSeriesContext] = None` 필드 추가
- 기존 fixture는 `None` 허용 → 기존 회귀 테스트 무영향 보장

#### 3. 단위 테스트

- `test_time_series_context_optional_fields`: None 허용 확인
- `test_time_series_context_delta_4q_pct`: 정상 계산 + 0 분모 None 반환
- `test_commentary_input_backward_compat`: 기존 fixture (time_series 없는) 로딩 PASS
- `test_commentary_input_with_time_series`: 신규 fixture (time_series 포함) 로딩 PASS

### KPI

- [ ] 회귀 격리 ±30% (예상 +5~10건)
- [ ] 기존 회귀 테스트 무영향 (backward-compat)
- [ ] IDENTICAL 7/7 유지

---

## Step 2: mock smoke 1~2건 (E3 concentrated_portfolio + E2)

### 목적

새 schema의 service layer 유효성 즉시 검증. Part 2 mock fixture 설계 기반 데이터 확보.

### 대상 파일

- `tests/portfolio/coach/slice8/test_input_v2_smoke.py` (신규)
- `tests/portfolio/coach/slice8/fixtures/e3_concentrated_v2.json` (신규)
- `tests/portfolio/coach/slice8/fixtures/e2_v2.json` (신규)

### 작업 상세

#### 1. fixture 작성

- E3 concentrated_portfolio entry 1건: 새 schema 형식, time_series 포함
- E2 entry 1건: 동일 패턴
- **LLM 호출 없음, schema 유효성만 검증**

#### 2. smoke 테스트

- `test_e3_concentrated_v2_schema_loads`: Pydantic 로딩 PASS
- `test_e3_concentrated_v2_time_series_populated`: time_series 필드 채워짐
- `test_e2_v2_schema_loads`: 동일 패턴
- `test_e2_v2_backward_compat`: time_series 일부 None 케이스도 로딩 PASS

#### 3. snapshot 비교

- fixture의 schema dump 결과를 snapshot으로 저장
- 향후 회귀 시 schema drift 감지

### KPI

- [ ] 회귀 +2~4건 (smoke 격리)
- [ ] $0 비용 유지 (LLM 호출 전혀 없음)
- [ ] IDENTICAL 7/7 유지

---

## Step 3: 누적 회귀 점검 및 Fallback 판정

### 자동 점검 스크립트

```bash
# 회귀 총량
pytest --collect-only -q | tail -1
# 예상: 410 + 12~26 = 422~436

# IDENTICAL hash
pytest tests/portfolio/coach/test_static_integrity.py -v

# 비용 누적
cat docs/portfolio/coach/slice8/cost_log.md
```

### 판정 룰

| 회귀 증가량 | 판정              | 다음 행동                                             |
| ----------- | ----------------- | ----------------------------------------------------- |
| +12 ~ +24   | 정상              | **Part 2 진입**                                       |
| +25         | 경계              | 사용자 확인 후 결정                                   |
| +26 이상    | **Fallback 발동** | #28/#29 Slice 9 분리, Slice 8은 Part 1 종료 후 마무리 |

### 비용 점검

- 누적 ≤ $1.60: 정상 (Part 1은 LLM 호출 0이므로 $1.595 유지 예상)
- $1.60 < 누적 ≤ $2.00: 사전 경고, Part 2 진입 전 비용 분석
- 누적 > $2.00: **모든 작업 중단**, Slice 9 재상향 트리거

---

## 산출물 체크리스트 (Part 1 종료 시)

| #   | 파일                                                    | 종류                                    |
| --- | ------------------------------------------------------- | --------------------------------------- |
| 1   | `portfolio/coach/cost_guard.py` v2                      | 코드 (PER_INSTANCE/PER_SLICE 분리)      |
| 2   | `portfolio/coach/exceptions.py`                         | 코드 (BudgetExceededError)              |
| 3   | `portfolio/coach/token_budgets.py` v2                   | 코드 (섹션 합산 estimator)              |
| 4   | `portfolio/coach/schemas/commentary_input.py` v2        | 코드 (TimeSeriesContext)                |
| 5   | `tests/portfolio/coach/test_cost_guard.py`              | 테스트 (5건)                            |
| 6   | `tests/portfolio/coach/test_budget_estimator.py`        | 테스트 (3건)                            |
| 7   | `tests/portfolio/coach/test_commentary_input_schema.py` | 테스트 (4건)                            |
| 8   | `tests/portfolio/coach/slice8/test_input_v2_smoke.py`   | 테스트 (4건 + fixture 2건)              |
| 9   | `docs/portfolio/coach/COST_POLICY.md`                   | docs (§LLM budget + §Appendix A)        |
| 10  | `docs/portfolio/coach/manual_eval_rubric.md` v2         | docs (10단계 + 양극단 + 분포 폭 게이트) |
| 11  | `docs/portfolio/coach/slice8/budget_estimator_v2.md`    | docs (fit 보고서)                       |
| 12  | `docs/portfolio/coach/slice8/part1_closing.md`          | docs (Part 1 종결 보고서)               |

---

## Part 1 종결 보고서 템플릿 (`part1_closing.md`)

```markdown
# Slice 8 Part 1 종결 보고서

## KPI 통과 현황

- [ ] 회귀: 410 → **_ (증가 +_**, Fallback 임계 +25 대비 \_\_\_%)
- [ ] IDENTICAL hash 7/7: PASS / FAIL
- [ ] #33 단위 테스트 5건: PASS / FAIL
- [ ] #β2 max delta: \_\_\_% (≤30% PASS / FAIL → keep_open)
- [ ] #27 backward-compat: PASS / FAIL
- [ ] smoke 4건: PASS / FAIL
- [ ] 비용: $1.595 → $**_ (사전 경고 $1.60 대비 _**%)

## 부채 처리 결과

- #33: closed / keep_open
- #β2: closed / keep_open (재시도 Slice 9 Step 0)
- #26: docs 갱신 완료, 분포 폭 자동 close는 Slice 8 Part 4에서 판정

## Part 2 진입 판정

- 회귀 증가량 **_ → _** (진입 / 분리)
- 비용 \_\_\_ → 안전 / 사전 경고 / 중단

## Slice 9 등록 항목 (있을 시)

- #β2 keep_open (max delta \_\_\_% > 30%)
- (기타)
```

---

## 실행 순서 요약

```
1. Step 0-1 (#33)        → 회귀 확인 → IDENTICAL 확인
2. Step 0-2 (#β2)        → max delta 확인 → 미달 시 keep_open 기록 후 진행
3. Step 0-3 (#26)        → docs 갱신
4. Step 1   (#27 schema) → 회귀 확인 → backward-compat 확인
5. Step 2   (smoke)      → 4건 PASS 확인
6. Step 3   (점검)        → Fallback 판정 → 종결 보고서 작성
```

각 Step 종료마다 회귀 누적 분량 확인, **+25 초과 시 즉시 사용자 보고**.

---

## Fallback 및 안전망 통합표

| 조건                    | 트리거                        | 처리                                           |
| ----------------------- | ----------------------------- | ---------------------------------------------- |
| Part 1 회귀 > +25       | `pytest --collect-only` count | #28/#29 Slice 9 분리, Part 2 진입 보류         |
| 누적 비용 > $1.60       | CostGuard 80% 사전 경고       | Part 2 진입 전 비용 분석 + Slice 9 재상향 검토 |
| #β2 max delta > 30%     | Step 0-2 KPI                  | #β2 keep_open + Slice 9 Step 0 재후보          |
| IDENTICAL hash 7/7 위반 | `test_static_integrity`       | 즉시 중단, 원인 분석                           |
| 누적 비용 > $2.00       | CostGuard 임계                | 모든 작업 중단, Slice 9 재상향 트리거 평가     |

---

## 결정 근거 (옵션 A1 + B2 + C2)

### 결정 A — Step 0 실행 순서: **A1 (#33 → #β2 → #26)**

- 가중합 **4.10** (마진 0.95)
- 격리 인프라(#33 budget 분리) 우선 정착 → 후속 작업의 호출 폭주가 PER_INSTANCE=50에서 자동 차단
- S7의 81/50 override 같은 사고가 Part 1 내부에서 원천 차단

### 결정 B — #27 보강 깊이: **B2 (raw + 시계열 1Q/4Q/12Q)**

- 가중합 **4.00** (마진 0.40)
- "구체성 부족" 결함의 핵심은 시계열 변화
- FMP API가 이미 시계열 제공 → 추가 데이터 페치 비용 0
- 모든 진입점(E1~E6) 공통 schema → 일관성

### 결정 C — Part 1 산출물 범위: **C2 (Step 0 + schema + smoke 1~2건)**

- 가중합 **4.00** (마진 0.50)
- Fallback 트리거(+25)를 Part 1에서 정직하게 가시화 → Part 2 진입 전 분리 결정 가능
- Slice 7 Part 1 패턴(산출물 8건 수준)과 일관

---

**문서 끝.** 이 지시서 그대로 Claude Code 환경에서 실행 시작. Part 1 종결 보고서 회수 후 Part 2 지시서 작성.
