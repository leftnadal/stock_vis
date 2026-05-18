# Slice 11 Part 2 작업 지시서

**작업명**: 6 진입점 통합 Output Schema (Base + 6 sub class, in-place 리팩토링)
**브랜치**: `slice11`
**선행 의존**: Slice 11 Part 1 종결 완료 (commit `ca272b0`, 회귀 541, IDENTICAL 7/7)
**부채 처리 타깃**: #41 output schema 통합 base (PS 2.5) → Part 2 종결 시 자연 close

---

## §0. Part 2 진입 baseline

| 항목         | 값                                                                                                          |
| ------------ | ----------------------------------------------------------------------------------------------------------- |
| 회귀         | 541 (Part 1 종결 후)                                                                                        |
| 누적 비용    | $2.3775 / 임계 $4.00 (마진 41%)                                                                             |
| 슬라이스 cap | $1.00 (Slice 9 도입)                                                                                        |
| IDENTICAL    | 7/7 (8슬라이스 누적)                                                                                        |
| LLM 호출     | 0/50 (Step 0 + Part 1 누적)                                                                                 |
| 현재 브랜치  | `slice11` (Part 1 commit `ca272b0`)                                                                         |
| 패턴 자산    | Part 1 `commentary_input.py` (Base + 6 sub + Holding + COMMENTARY_INPUT_CLASSES + frozen=True/extra=forbid) |

---

## §1. Part 2 작업 범위

### 1.1 작업 목표

`portfolio/schemas/commentary_output.py`를 Part 1과 같은 통합 base 패턴으로 **in-place 리팩토링**.

- Base class: `CommentaryOutputBase`
- 6 sub class: `E1Output`, `E2Output`, `E3Output`, `E4Output`, `E5Output`, `E6Output`
- Helper: `ActionItem` (base 모듈 안에 정의)
- Registry: `COMMENTARY_OUTPUT_CLASSES` dict (Part 1 `COMMENTARY_INPUT_CLASSES` 미러)

### 1.2 기존 → 신규 매핑표

기존 `commentary_output.py`의 7 schema 필드를 Base + sub class로 재구성한다.

| 기존 필드 (Slice 8 Part 2 도입)               | 위치       | 신규 위치                                          |
| --------------------------------------------- | ---------- | -------------------------------------------------- |
| `summary` (str)                               | E1~E6 공통 | **Base**                                           |
| `key_observations` (list[str])                | E1~E6 공통 | **Base**                                           |
| `action_items` (list[ActionItem])             | E1, E3, E5 | **각 sub class** (e1/e3/e5에만 포함)               |
| `risk_flags` (list[str])                      | E1, E3, E6 | **각 sub class** (e1/e3/e6에만 포함)               |
| `confidence` (Literal["high","medium","low"]) | E1~E6 공통 | **Base**                                           |
| `metrics_table` (str, deprecated wrapper)     | E1, E2     | **각 sub class** (e1/e2에만 포함, deprecated 유지) |
| `quoted_metrics` (dict)                       | E2, E5, E6 | **각 sub class** (e2/e5/e6에만 포함)               |

**원칙**:

- 6 진입점 전부 공통 필드 → Base
- 일부 진입점만 공통 필드 → 해당 sub class 각각에 포함 (DRY 깨지더라도 명시성 우선, Part 1 패턴 일관)
- `ActionItem`은 base 모듈 안에 정의 (`from portfolio.schemas.commentary_output import ActionItem` 가능)

### 1.3 schema 설정

Part 1과 동일:

```python
model_config = ConfigDict(frozen=True, extra="forbid")
```

### 1.4 신규 진입점별 schema 정의 (제안)

> 아래는 매핑표를 기준으로 한 sub class 골격 제안. 실제 구현 시 기존 `commentary_output.py` 내용과 1:1 fitting 후 확정.

```python
# Base
class CommentaryOutputBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    summary: str = Field(..., min_length=1)
    key_observations: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

# Helper (base 모듈 안에 정의)
class ActionItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    # (기존 commentary_output.py의 ActionItem 정의 그대로 흡수)

# Sub classes
class E1Output(CommentaryOutputBase):
    action_items: list[ActionItem] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    metrics_table: str = Field(default="", description="deprecated")  # #21 부채 유지

class E2Output(CommentaryOutputBase):
    quoted_metrics: dict[str, Any] = Field(default_factory=dict)
    metrics_table: str = Field(default="", description="deprecated")  # #21 부채 유지

class E3Output(CommentaryOutputBase):
    action_items: list[ActionItem] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)

class E4Output(CommentaryOutputBase):
    # Slice 7 E4 대화 Q&A: base만 사용 (action_items/risk_flags 불필요)
    pass

class E5Output(CommentaryOutputBase):
    action_items: list[ActionItem] = Field(default_factory=list)
    quoted_metrics: dict[str, Any] = Field(default_factory=dict)

class E6Output(CommentaryOutputBase):
    risk_flags: list[str] = Field(default_factory=list)
    quoted_metrics: dict[str, Any] = Field(default_factory=dict)

# Registry
COMMENTARY_OUTPUT_CLASSES: dict[str, type[CommentaryOutputBase]] = {
    "e1": E1Output,
    "e2": E2Output,
    "e3": E3Output,
    "e4": E4Output,
    "e5": E5Output,
    "e6": E6Output,
}
```

**구현 주의사항**:

- 기존 `commentary_output.py`에 있던 ActionItem 정의를 100% 그대로 흡수 (필드/제약 변경 금지)
- 기존 호출자가 `from portfolio.schemas.commentary_output import <기존 class 이름>` 형태로 import 했다면, 호환을 위해 **별칭(alias)** 가능 여부 §1.5에서 검토
- `summary` min_length=1은 기존 제약과 다를 수 있으니 기존 파일 보고 맞출 것

### 1.5 호환성 처리 (B1 in-place 룰)

기존 commentary_output.py를 import하는 호출자가 있다면 같은 commit에서 모두 갱신:

1. **호출자 인벤토리 작성** (§3 Step 1):
   - `grep -r "from portfolio.schemas.commentary_output import" portfolio/ tests/`
   - `grep -r "import portfolio.schemas.commentary_output" portfolio/ tests/`
   - 결과 목록을 dump (호출자 수가 5개 이하면 in-place + 호출자 갱신, 6개 이상이면 §1.6 Fallback)

2. **호출자 갱신**:
   - 기존 class 이름이 sub class 이름과 다르면 정확히 매핑하여 갱신
   - import 경로는 `from portfolio.schemas.commentary_output import ...` 그대로 유지

### 1.6 Fallback 룰 (Part 2 한정)

| 트리거                                                           | 대응                                                                                              |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 호출자 수 6개 이상                                               | B2 임시 전환: 기존 class를 sub class의 alias로 1 commit 유지, #41 keep_open, Slice 12 Step 0 후보 |
| 회귀 +12 초과 (예상 +5~7의 ±70% 마진)                            | Step 6 정지, schema 설계 재검토                                                                   |
| IDENTICAL 7/7 깨짐                                               | 즉시 `git revert`, 원인 진단 후 재진입                                                            |
| 기존 service에서 validation 깨짐 (Pydantic ValidationError 발생) | 해당 service의 호출 인자 dump + sub class 정의 재검토                                             |

---

## §2. 작업 환경 사전 확인

작업 시작 전 다음 명령으로 baseline 일치 검증:

```bash
# 1. 브랜치 확인
git branch --show-current
# 기대값: slice11

# 2. Part 1 commit 확인
git log -1 --oneline
# 기대값: ca272b0 (...)

# 3. 회귀 baseline 확인
pytest portfolio/ tests/ -x -q 2>&1 | tail -5
# 기대값: 541 passed

# 4. 기존 commentary_output.py 존재 확인
ls -la portfolio/schemas/commentary_output.py
cat portfolio/schemas/commentary_output.py | head -100

# 5. 호출자 인벤토리
grep -rn "from portfolio.schemas.commentary_output" portfolio/ tests/
grep -rn "import portfolio.schemas.commentary_output" portfolio/ tests/
```

위 모든 명령 결과를 §10 회신에 dump 포함.

---

## §3. 작업 단계 (Step 1 ~ Step 8)

### Step 1: 호출자 인벤토리 + 기존 schema dump (15분)

**산출물**:

- `docs/portfolio/coach/slice11/part2_caller_inventory.md`
  - 호출자 파일 목록 + import 형태
  - 기존 commentary_output.py 전체 내용 (참고용 dump)
  - 호출자 수 N건 → Fallback 트리거 여부 판단

**KPI 1**: 호출자 수 ≤ 5 → in-place 진행 / 6+ → §1.6 Fallback B2

### Step 2: 신규 schema 설계 + 매핑표 확정 (30분)

**산출물**:

- `docs/portfolio/coach/slice11/part2_schema_mapping.md`
  - 기존 7 필드 → Base/sub class 매핑표 (§1.2 보강)
  - ActionItem 정의 인용 (변경 없음 확인)
  - 기존 class 이름 vs 신규 class 이름 매핑

**KPI 2**: 매핑표 7 필드 + ActionItem 모두 신규 구조에 1:1 대응 (누락/추가 0)

### Step 3: portfolio/schemas/commentary_output.py 리팩토링 (45분)

**산출물**:

- `portfolio/schemas/commentary_output.py` 갱신 (Base + 6 sub + ActionItem + COMMENTARY_OUTPUT_CLASSES)
- 기존 7 필드 모두 신규 구조에 흡수

**구현 룰**:

- Part 1 `commentary_input.py` 구조 미러 (Base / sub class 순서, docstring 패턴, frozen=True/extra=forbid)
- ActionItem은 base 모듈 안에 정의 (`from portfolio.schemas.commentary_output import ActionItem` 가능)
- 기존 class 이름이 신규와 다르면 sub class에 alias 부여 가능 (e.g. `LegacyOutput = E1Output`) — 단 §1.5 호출자 갱신을 우선, alias는 #21 같은 deprecated wrapper 부채로 누적되지 않게 주의

**KPI 3**: pydantic import 정상, 모듈 import 성공 (`python -c "from portfolio.schemas.commentary_output import COMMENTARY_OUTPUT_CLASSES; print(len(COMMENTARY_OUTPUT_CLASSES))"` → 6)

### Step 4: 호출자 갱신 (20분)

**산출물**:

- Step 1 인벤토리의 모든 호출자 갱신 (in-place)

**KPI 4**: `grep` 으로 갱신 후 호출자가 신규 class 이름으로만 import 하는지 확인 (잔존 legacy import 0)

### Step 5: test_commentary_output.py 작성 (30분)

**산출물**:

- `tests/coach/test_commentary_output.py` (Part 1의 `test_commentary_input.py` 8건 미러)
  - Base class frozen 검증
  - 6 sub class 인스턴스 생성 + validate
  - extra="forbid" 위반 ValidationError 검증
  - ActionItem 단독 validate
  - COMMENTARY_OUTPUT_CLASSES dict 6개 항목 + 키 정렬 검증
  - portfolio_a2 fixture (있다면) 매핑 검증
  - confidence Literal 위반 검증
  - 기존 7 필드 모두 신규 구조에서 정상 작동 검증

**KPI 5**: 신규 테스트 8건 + 기존 commentary_output 관련 테스트 (있다면) 정상 작동

### Step 6: 회귀 smoke (10분)

```bash
# 6.1 신규 테스트만 단독 실행
pytest tests/coach/test_commentary_output.py -v 2>&1 | tail -20

# 6.2 portfolio 전체 회귀
pytest portfolio/ tests/ -x -q 2>&1 | tail -5

# 6.3 IDENTICAL 7/7 검증
pytest portfolio/tests/test_static_integrity.py -v 2>&1 | tail -15

# 6.4 regression classifier 분류
pytest portfolio/tests/slice11/test_regression_classifier.py -v 2>&1 | tail -10
```

**KPI 6**: 회귀 541 → 546~548 (+5~7) **또는** 회귀 격리 KPI ±30% 마진 (즉 ±2 = 544~550) 안에 들면 PASS
**KPI 7**: IDENTICAL 7/7 유지
**KPI 8**: 모든 신규 테스트 PASS

### Step 7: regression classifier 갱신 (10분)

신규 8건이 no-cost로 분류되는지 확인.

```bash
# Slice 11 regression classifier 갱신 (Step 0에서 작성)
# 신규 8건 + 기존 회귀 분류
```

**산출물**:

- `portfolio/tests/slice11/test_regression_classifier.py` 갱신 (필요 시 +1~2건)

**KPI 9**: 분류 deviation ±30% 이내 (cost KPI) / ±50% 이내 (no-cost KPI) — Slice 9 Step 0 E1 룰

### Step 8: KPI matrix + Part 2 종결 보고 (20분)

**산출물**:

- `docs/portfolio/coach/slice11/kpi_part2.md` (KPI 10건)
- `docs/portfolio/coach/slice11/part2_closing.md` (Part 2 종결 보고)

---

## §4. KPI 매트릭스 (Part 2)

| #   | KPI                     | 측정값 | 기대값                                      | PASS/FAIL |
| --- | ----------------------- | ------ | ------------------------------------------- | --------- |
| 1   | 호출자 인벤토리 N건     | TBD    | ≤ 5 (in-place)                              | TBD       |
| 2   | schema 매핑 완전성      | TBD    | 7 필드 + ActionItem 1:1                     | TBD       |
| 3   | 신규 schema 모듈 import | TBD    | 성공, dict 6개                              | TBD       |
| 4   | 호출자 갱신 완료        | TBD    | legacy import 0                             | TBD       |
| 5   | 신규 테스트 PASS        | TBD    | 8/8                                         | TBD       |
| 6   | 회귀 +Δ                 | TBD    | +5~7 (±30% = +3~10)                         | TBD       |
| 7   | IDENTICAL               | TBD    | 7/7 유지                                    | TBD       |
| 8   | 비용                    | $0     | $0 (LLM 호출 없음)                          | TBD       |
| 9   | classifier deviation    | TBD    | ±50% (no-cost)                              | TBD       |
| 10  | #41 close 조건          | TBD    | Base + 6 sub 완성 + 호출자 갱신 + 회귀 PASS | TBD       |

---

## §5. #41 부채 close 룰

**close 조건** (전부 충족 시):

1. KPI 1~10 모두 PASS
2. `portfolio/schemas/commentary_output.py`에 `CommentaryOutputBase` 정의 존재
3. `COMMENTARY_OUTPUT_CLASSES` dict 6 entry 존재
4. 호출자 갱신 완료 (legacy import 0)

**재오픈 트리거** (Part 3 prompt builder 작성 시점):

- service input과 본 schema 1:1 fitting 실패 시 (Pydantic ValidationError 발생)
- 신규 필드가 prompt builder 단계에서 발견되어 schema 보강 필요 시
- 재오픈 시 Slice 12 Step 0 후보로 자동 등록

**close 표기**:

- `part2_closing.md` §부채 처리 섹션에 "#41 close (자연 종결, Part 3 fitting 실패 시 재오픈)" 명시

---

## §6. 신규 부채 후보 (Part 2 종결 시 점검)

| ID         | 내용                                  | PS  | 트리거                                                               |
| ---------- | ------------------------------------- | --- | -------------------------------------------------------------------- |
| #54 (후보) | ActionItem helper 모듈 분리           | 1.0 | base 모듈 안 helper class 3개 이상 누적 시                           |
| #21 (기존) | metrics_table deprecated wrapper 제거 | 0.5 | output schema에 metrics_table 잔존 — Part 2에서 유지, Slice 13+ 후보 |
| #41 재오픈 | service fitting 실패 시               | 2.0 | Part 3 prompt builder 작성 중 발견                                   |

---

## §7. 회신 형식 (§10)

작업 완료 시 다음 형식으로 회신:

```
# Slice 11 Part 2 종결

## §1 baseline 확인
- 브랜치: slice11
- Part 1 commit: ca272b0
- baseline 회귀: 541
- 기존 commentary_output.py: (존재/없음, 라인 수)

## §2 호출자 인벤토리 (Step 1 결과)
- 호출자 수: N건
- 파일 목록: [...]
- Fallback 트리거: 발동/미발동

## §3 schema 매핑 (Step 2 결과)
- Base 필드: summary, key_observations, confidence
- E1 추가 필드: action_items, risk_flags, metrics_table
- E2 추가 필드: ...
- (이하 sub class별)
- ActionItem: 기존 정의 그대로 흡수 (변경 0)

## §4 호출자 갱신 (Step 4 결과)
- 갱신 호출자: N건
- legacy import 잔존: 0

## §5 회귀 (Step 6 결과)
- 541 → ___ (+__)
- KPI 6 PASS/FAIL
- IDENTICAL 7/7 PASS/FAIL

## §6 신규 테스트
- 신규 8건: __/8 PASS

## §7 비용
- 단독: $0
- 누적: $2.3775 유지

## §8 KPI matrix
| # | KPI | 측정값 | PASS/FAIL |
| 1 | ... | ... | ... |
(10건)

## §9 #41 처리
- close 조건 4건 충족 여부
- 최종 판정: close / keep_open

## §10 산출물 dump
- portfolio/schemas/commentary_output.py (신규 내용)
- tests/coach/test_commentary_output.py (신규)
- docs/portfolio/coach/slice11/part2_caller_inventory.md
- docs/portfolio/coach/slice11/part2_schema_mapping.md
- docs/portfolio/coach/slice11/kpi_part2.md
- docs/portfolio/coach/slice11/part2_closing.md

## §11 커밋
- commit hash: ___
- commit message: "slice11 part2: unified output schema (base + 6 sub class, #41 close)"

## §12 Part 3 진입 준비
- output schema PRODUCTION READY
- #41 처리 완료 (close / keep_open)
- 다음 작업: prompt builder (Part 1 input + Part 2 output schema 1:1 fitting)
```

---

## §8. 예상 산출물 목록

| 영역       | 파일                                                     | 신규/수정                    |
| ---------- | -------------------------------------------------------- | ---------------------------- |
| schema     | `portfolio/schemas/commentary_output.py`                 | **수정 (in-place 리팩토링)** |
| 테스트     | `tests/coach/test_commentary_output.py`                  | **신규**                     |
| 호출자     | (Step 1 인벤토리에 따라)                                 | 수정                         |
| classifier | `portfolio/tests/slice11/test_regression_classifier.py`  | 수정 (+1~2건)                |
| 문서       | `docs/portfolio/coach/slice11/part2_caller_inventory.md` | 신규                         |
| 문서       | `docs/portfolio/coach/slice11/part2_schema_mapping.md`   | 신규                         |
| 문서       | `docs/portfolio/coach/slice11/kpi_part2.md`              | 신규                         |
| 문서       | `docs/portfolio/coach/slice11/part2_closing.md`          | 신규                         |

---

## §9. 작업 시간 예상

| Step   | 작업                          | 시간       |
| ------ | ----------------------------- | ---------- |
| 1      | 호출자 인벤토리 + 기존 dump   | 15분       |
| 2      | schema 설계 + 매핑표          | 30분       |
| 3      | commentary_output.py 리팩토링 | 45분       |
| 4      | 호출자 갱신                   | 20분       |
| 5      | 신규 테스트 작성              | 30분       |
| 6      | 회귀 smoke                    | 10분       |
| 7      | classifier 갱신               | 10분       |
| 8      | KPI matrix + 종결 보고        | 20분       |
| **합** |                               | **~3시간** |

---

## §10. 작업 시작 신호

다음 명령으로 Step 1 시작:

```bash
git status  # slice11 브랜치, clean 상태 확인
git log -1 --oneline  # ca272b0 확인
pytest portfolio/ tests/ -x -q 2>&1 | tail -5  # 541 passed 확인
```

세 명령 모두 기대값 일치 시 Step 1 진입. 불일치 시 즉시 중단 후 보고.

---

**END OF INSTRUCTIONS**
