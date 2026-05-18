# Slice 11 Part 1 지시서 — 6 진입점 통합 input schema

> **Part 성격**: trio 5-Part β의 첫 진입점 작업 Part
> **작업 핵심**: A2(1 portfolio × E1~E6 종합)를 위한 통합 input schema 설계
> **예상**: 회귀 532 → 537~540 (+5~8) / 비용 $0 / LLM 0/50 / 시간 ~3시간

---

## 0. 사전 결정 (확정)

| 결정             | 채택                                                           | 핵심                                         |
| ---------------- | -------------------------------------------------------------- | -------------------------------------------- |
| D-1 schema 구조  | **a. 단일 모듈 base + 6 sub class** (가중합 4.625, 마진 1.4)   | Slice 8 H2 패턴 재사용 + #41 자연 close 정합 |
| D-2 fixture 정합 | **i. fixture → schema validate 직접 매핑** (4.10, tie-breaker) | Slice 8 #27 TimeSeriesContext 패턴 일관      |

**핵심 자산 재사용**:

- Slice 8 #27 `TimeSeriesContext` (`portfolio/schemas/commentary_input.py` 일부, 이미 존재) — Part 1에서 import 활용
- Slice 8 H2 `portfolio/schemas/commentary_output.py` 패턴 — Part 2에서 동일하게 적용 예정
- Slice 11 Step 0 `portfolio_a2.json` fixture (income preset, 1 ETF + 4 stocks)

⚠️ **scope 명확화**:

- Part 1 = **base + 6 sub class (e1~e6)만**
- e3_portfolio (Slice 6), e4_conversation (Slice 7) 같은 **변형 진입점은 제외** (Slice 12+ 자연 추가 시점)
- Part 2가 output schema 통합 — input/output 1:1 대응 유지

---

## §0 환경 점검 + Step 0 자산 확인

### 작업

1. **브랜치 + baseline 확인**

   ```bash
   git status  # slice11 브랜치 확인
   pytest portfolio/tests -q  # 회귀 532 baseline confirm
   ```

2. **Step 0 자산 검증**
   - `portfolio/schemas/commentary_input.py` 존재 + `TimeSeriesContext` 정의 확인 (Slice 8 #27 자산)
   - `portfolio/tests/fixtures/coach/portfolio_a2.json` 존재 + income preset 1 ETF + 4 stocks
   - `portfolio/measure/message_dumper.py` 존재 (Slice 11 Step 0 #52)

3. **기존 진입점 input 인터페이스 확인** (backward-compat 대상)
   - E1: `portfolio/coach/services/e1_*.py` 또는 유사 위치에서 입력 받는 함수/메서드
   - E2~E6: 동일 패턴
   - 어떤 dict/dataclass/Pydantic 모델을 입력으로 받는지 확인 → schema 매핑 정책 결정

### KPI

- 회귀 baseline 532 confirm
- `TimeSeriesContext` 정의 위치 명확

---

## §1 CommentaryInputBase 설계

### 작업

1. **`portfolio/schemas/commentary_input.py` 갱신** (TimeSeriesContext 기존 보존)

   **공통 base class 설계**:

   ```python
   from pydantic import BaseModel, Field
   from datetime import datetime
   from typing import Literal

   # 기존 TimeSeriesContext (Slice 8 #27) 보존
   class TimeSeriesContext(BaseModel):
       ...  # 기존 정의 유지

   # 신규 base
   class CommentaryInputBase(BaseModel):
       """6 진입점 공통 input base.

       모든 진입점 input은 이 base를 상속하고, 진입점별 특화 필드를 추가.
       """
       portfolio_id: str = Field(..., description="포트폴리오 식별자")
       fetched_at: datetime = Field(..., description="데이터 수집 시점 (snapshot)")
       preset: Literal["garp", "focused", "income", "growth", "factor"] = Field(
           ..., description="투자 스타일 preset"
       )
       entry_point: str = Field(..., description="진입점 식별 (e1~e6) - discriminator")

       model_config = {"frozen": True, "extra": "forbid"}
   ```

   **설계 원칙**:
   - **`frozen=True`**: input은 immutable (코칭 호출 후 변경 불가)
   - **`extra="forbid"`**: 정의되지 않은 필드 거부 (schema drift 즉시 검출)
   - **`entry_point` discriminator**: 향후 union 패턴 도입 시 활용
   - **preset enum**: Slice 11 신규 추가된 `income` 포함 (E6 mock fixture와 정합)

2. **단위 테스트** (`tests/coach/test_commentary_input.py` 신규)
   - base 필드 validation (필수/타입/enum)
   - `frozen=True` 동작 (immutability)
   - `extra="forbid"` 동작 (extra field rejection)
   - preset enum 정합성 (income 추가 확인)
   - 4~5건

### 산출물

- `portfolio/schemas/commentary_input.py` (갱신, base 추가)
- `tests/coach/test_commentary_input.py` (신규 4~5건)

### KPI

- `CommentaryInputBase` 정의 PASS
- frozen/extra=forbid 동작 PASS
- preset enum 5종 정합

---

## §2 6 sub class 정의 (E1~E6)

### 작업

1. **`portfolio/schemas/commentary_input.py` 6 sub class 추가**

   각 sub class는 `CommentaryInputBase` 상속 + 진입점별 특화 필드:

   ```python
   from typing import Literal

   class Holding(BaseModel):
       """포트폴리오 보유 종목 (공통 type)."""
       ticker: str
       weight: float  # 0.0 ~ 1.0
       sector: str | None = None

   class CommentaryInputE1(CommentaryInputBase):
       """E1 GARP 스코어링 input."""
       entry_point: Literal["e1"] = "e1"
       holdings: list[Holding]
       garp_metrics: dict[str, dict]  # {ticker: {per, peg, roe, ...}}

   class CommentaryInputE2(CommentaryInputBase):
       """E2 포트폴리오 종합 input."""
       entry_point: Literal["e2"] = "e2"
       holdings: list[Holding]
       portfolio_return_1y: float
       sector_allocation: dict[str, float]

   class CommentaryInputE3(CommentaryInputBase):
       """E3 concentrated_portfolio input."""
       entry_point: Literal["e3"] = "e3"
       holdings: list[Holding]
       concentration_metrics: dict  # hhi, top3_weight, etc.

   class CommentaryInputE4(CommentaryInputBase):
       """E4 대화 Q&A input."""
       entry_point: Literal["e4"] = "e4"
       holdings: list[Holding]
       user_question: str
       conversation_history: list[dict] = Field(default_factory=list)

   class CommentaryInputE5(CommentaryInputBase):
       """E5 추출 진입점 input."""
       entry_point: Literal["e5"] = "e5"
       holdings: list[Holding]
       extraction_targets: list[str]
       time_series_context: TimeSeriesContext | None = None

   class CommentaryInputE6(CommentaryInputBase):
       """E6 분석엔진 input."""
       entry_point: Literal["e6"] = "e6"
       holdings: list[Holding]
       analysis_results: dict[str, dict]  # {ticker: analysis_result}
   ```

   **설계 원칙**:
   - `Holding` 공통 type 1회 정의 (Slice 8 H2 ActionItem 패턴 응용)
   - 각 sub class의 `entry_point`는 Literal type (discriminator value 고정)
   - 진입점별 특화 필드는 코드베이스의 기존 input 구조 확인 후 fitting
   - `TimeSeriesContext`는 E5만 사용 (확장 필요 시 다른 sub class에 optional 추가)

   ⚠️ **코드베이스 검증 필요**: 각 sub class의 실제 필드는 기존 진입점 service의 input 구조를 확인 후 1:1 매칭. 위 정의는 골격만 — 코드 실제 fitting 시 조정 필요.

2. **단위 테스트** (`tests/coach/test_commentary_input.py` 추가)
   - 진입점별 instantiation PASS (E1~E6 각각)
   - `entry_point` discriminator value 일관성
   - `Holding` 공통 type 검증 (weight 범위 0~1)
   - sub class별 특화 필드 validation
   - 6~8건 추가 (총 10~13건)

### 산출물

- `portfolio/schemas/commentary_input.py` (갱신, 6 sub class + Holding)
- `tests/coach/test_commentary_input.py` (갱신, +6~8건)

### KPI

- 6 sub class 정의 PASS
- discriminator value 일관성 PASS
- Holding 공통 type 1회 정의

---

## §3 portfolio_a2 fixture → schema validate 매핑

### 작업

1. **`portfolio/tests/fixtures/coach/portfolio_a2.json` 갱신** (필요 시)
   - 기존 fixture가 6 진입점 input 모두를 포함하도록 확장
   - Step 0에서는 E6 mock만 포함 → Part 1에서 E1~E5 mock 데이터 추가
   - 각 진입점별 입력을 fixture의 sub key로 분리:

   ```json
   {
     "portfolio_id": "a2_income_001",
     "fetched_at": "2026-05-18T00:00:00Z",
     "preset": "income",
     "holdings": [
       {"ticker": "VYM", "weight": 0.40, "sector": "ETF"},
       {"ticker": "JNJ", "weight": 0.20, "sector": "Healthcare"},
       ...
     ],
     "inputs": {
       "e1": { "garp_metrics": {...} },
       "e2": { "portfolio_return_1y": 0.082, "sector_allocation": {...} },
       "e3": { "concentration_metrics": {...} },
       "e4": { "user_question": "이 포트폴리오의 배당 안정성은?", "conversation_history": [] },
       "e5": { "extraction_targets": [...], "time_series_context": {...} },
       "e6": { "analysis_results": {...} }
     }
   }
   ```

2. **fixture loader 함수** (`portfolio/tests/fixtures/coach/loaders.py` 신규 또는 기존에 추가)

   ```python
   def load_portfolio_a2_input(entry_point: str) -> CommentaryInputBase:
       """portfolio_a2 fixture를 sub class instance로 변환."""
       fixture_data = json.load(open("portfolio_a2.json"))
       common = {
           "portfolio_id": fixture_data["portfolio_id"],
           "fetched_at": fixture_data["fetched_at"],
           "preset": fixture_data["preset"],
       }
       holdings = fixture_data["holdings"]
       specific = fixture_data["inputs"][entry_point]

       sub_class_map = {
           "e1": CommentaryInputE1,
           "e2": CommentaryInputE2,
           ...
       }
       return sub_class_map[entry_point](
           **common,
           holdings=holdings,
           **specific,
       )
   ```

3. **단위 테스트** (`tests/coach/test_commentary_input.py` 추가)
   - portfolio_a2 fixture → 6 sub class validate PASS
   - 실패 케이스 (extra field, missing field, type mismatch)
   - 3~4건 (총 13~17건)

### 산출물

- `portfolio/tests/fixtures/coach/portfolio_a2.json` (갱신, 6 진입점 input 통합)
- `portfolio/tests/fixtures/coach/loaders.py` (신규 또는 갱신)
- `tests/coach/test_commentary_input.py` (갱신, +3~4건)

### KPI

- portfolio_a2 fixture → 6 sub class validate 100%
- loader 함수 6 진입점 모두 동작
- schema drift 즉시 검출 (extra field → FAIL)

---

## §4 회귀 분류 + Part 1 KPI 검증

### 작업

1. **회귀 분류기 갱신** (`portfolio/tests/helpers/regression_classifier.py`)
   - `schema` 카테고리 추가 (또는 기존 활용)
   - `tests/coach/test_commentary_input.py::*` → schema 카테고리

2. **`portfolio/tests/slice11/test_regression_classifier.py` 갱신** (+1 룰)
   - schema 카테고리 분류 정확도 검증

3. **KPI 매트릭스 검증** (자동)
   - `pytest portfolio/tests -q` → 회귀 +5~8 확인 (전체 537~540)
   - IDENTICAL hash 7/7 유지
   - 누적 비용 $2.3775 유지

### 산출물

- `portfolio/tests/helpers/regression_classifier.py` (갱신)
- `portfolio/tests/slice11/test_regression_classifier.py` (+1 룰)

### KPI

- 회귀 +5~8 (범위 충족)
- 분류 정확도 100%
- IDENTICAL 7/7 PASS

---

## §5 Part 1 종결 보고

### 작업

1. **`docs/portfolio/coach/slice11/part1_closing.md` 작성**
   - 회귀, IDENTICAL, 비용, LLM 호출
   - KPI 매트릭스 결과
   - **schema 모듈 구조** (base + 6 sub class + Holding)
   - **portfolio_a2 fixture 매핑 결과**
   - Slice 11 Part 2 진입 준비 상태 (output schema 통합)

2. **`docs/portfolio/coach/slice11/kpi_part1.md` 작성** (KPI 매트릭스 단독)

### 산출물

- `docs/portfolio/coach/slice11/part1_closing.md`
- `docs/portfolio/coach/slice11/kpi_part1.md`

---

## §6 KPI 매트릭스 (10건)

| #   | KPI                                                 | 임계                                                   | 측정                  |
| --- | --------------------------------------------------- | ------------------------------------------------------ | --------------------- |
| 1   | `CommentaryInputBase` 정의 PASS                     | 4 필드 (portfolio_id, fetched_at, preset, entry_point) | 단위 테스트           |
| 2   | frozen + extra=forbid 동작                          | PASS                                                   | 단위 테스트           |
| 3   | 6 sub class 정의 (E1~E6)                            | 6/6                                                    | grep + 단위 테스트    |
| 4   | discriminator value 일관성                          | entry_point Literal 6종                                | 단위 테스트           |
| 5   | `Holding` 공통 type 1회 정의                        | 1 정의 + 6 sub class 재사용                            | grep                  |
| 6   | portfolio_a2 fixture → 6 schema validate            | 100%                                                   | 단위 테스트           |
| 7   | preset enum 5종 (garp/focused/income/growth/factor) | PASS                                                   | 단위 테스트           |
| 8   | IDENTICAL hash 유지                                 | 7/7                                                    | test_static_integrity |
| 9   | 회귀 +5~8                                           | predicted ±30%(cost)/±50%(no-cost)                     | classifier            |
| 10  | 누적 비용 변화                                      | $0                                                     | CostGuard             |

---

## §7 Fallback 룰

| 트리거                                              | 조치                                                                                            |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| §1 기존 input 인터페이스가 dict 아닌 dataclass      | sub class에 `from_legacy()` classmethod 추가, backward-compat 보존                              |
| §2 진입점별 특화 필드가 코드베이스와 1:1 매핑 안 됨 | 골격 schema만 정의 + `extra="allow"` 일시 적용 → Part 3에서 prompt builder 작성 시 본격 fitting |
| §2 `TimeSeriesContext` 사용 범위 불명확             | E5만 적용 (기본값), 다른 sub class는 향후 optional 추가                                         |
| §3 portfolio_a2 fixture가 schema와 충돌             | fixture 갱신 우선 (schema가 source of truth)                                                    |
| 회귀 +8 초과                                        | sub class 1~2개를 Part 2로 분할 (e3/e6 같은 mock 의존 진입점 우선)                              |
| 누적 비용 $0 이상                                   | Part 1은 LLM 호출 0 → 발생 시 즉시 보고                                                         |

---

## §8 작업 순서 (recommend)

| §   | 작업                                            | 예상 시간 | 누적 |
| --- | ----------------------------------------------- | --------- | ---- |
| §0  | 환경 + Step 0 자산 + 기존 input 인터페이스 확인 | 15분      | 0:15 |
| §1  | CommentaryInputBase 설계 + 테스트               | 30분      | 0:45 |
| §2  | 6 sub class 정의 + 테스트                       | 1.5h      | 2:15 |
| §3  | portfolio_a2 fixture 매핑 + loader + 테스트     | 30분      | 2:45 |
| §4  | 회귀 분류 + KPI 검증                            | 15분      | 3:00 |
| §5  | 종결 보고                                       | 15분      | 3:15 |

**총 ~3시간 15분** (1세션 적정)

---

## §9 산출물 체크리스트 (8건)

### 신규 (4건)

- [ ] `tests/coach/test_commentary_input.py` (13~17건)
- [ ] `portfolio/tests/fixtures/coach/loaders.py` (또는 기존에 추가)
- [ ] `docs/portfolio/coach/slice11/kpi_part1.md`
- [ ] `docs/portfolio/coach/slice11/part1_closing.md`

### 갱신 (4건)

- [ ] `portfolio/schemas/commentary_input.py` (base + 6 sub class + Holding)
- [ ] `portfolio/tests/fixtures/coach/portfolio_a2.json` (6 진입점 input 통합)
- [ ] `portfolio/tests/helpers/regression_classifier.py` (schema 카테고리)
- [ ] `portfolio/tests/slice11/test_regression_classifier.py` (+1 룰)

---

## §10 회신 형식 (Claude Code → 사용자)

```
Slice 11 Part 1 종결 (6 진입점 통합 input schema).
- 회귀: 532 → ___ (+___)
- IDENTICAL: ___/7
- 비용 단독: $0 / 누적: $2.3775 (마진 41%)
- LLM 호출: 0/50
- KPI 10/10: ___ PASS, ___ FAIL
- schema 모듈: CommentaryInputBase + 6 sub class (E1~E6) + Holding
- portfolio_a2 fixture: 6 진입점 validate ___/6
- Fallback 발동: ___ (없음 / 어떤 §)

Slice 11 Part 2 진입 준비 상태: ___
#41 자연 close 예상 (Part 2 output schema 통합 작업 시)

git log --oneline (Step 0)..HEAD
[commit hashes]
```

manual 검증 필요 사항: 기존 진입점 service input과 schema 매핑 시 fitting 조정 발생 가능 — 발생 시 별도 섹션으로 명시.
