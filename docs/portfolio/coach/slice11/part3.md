# Slice 11 Part 3 작업 지시서

**작업명**: Prompt Builder (Base + 6 sub) + E1 Service 마이그레이션 + Smoke + #48 v3 자동 분기
**브랜치**: `slice11`
**선행 의존**: Slice 11 Part 2 종결 완료 (commit `975958f`, 회귀 550, IDENTICAL 7/7, #41 close)
**부채 처리**: Slice 10 #48 v3 첫 실측 검증 자연 분기 (예약 룰 수행)

---

## §0. Part 3 진입 baseline

| 항목         | 값                                                                               |
| ------------ | -------------------------------------------------------------------------------- |
| 회귀         | 550 (Part 2 종결 후)                                                             |
| 누적 비용    | $2.3775 / 임계 $4.00 (마진 41%)                                                  |
| 슬라이스 cap | $1.00 (Slice 9 도입, Part 3 smoke 예산 ~$0.015)                                  |
| IDENTICAL    | 7/7 (9슬라이스 누적)                                                             |
| LLM 호출     | 0/50 (Slice 11 누적)                                                             |
| 현재 브랜치  | `slice11` (Part 2 commit `975958f`)                                              |
| 자산         | Part 1 `commentary_input.py` + Part 2 `commentary_output.py` (Base + 6 sub 미러) |
| #48 처리     | Slice 10 close, Part 3 smoke 자연 분기 예약                                      |

---

## §1. Part 3 작업 범위

### 1.1 작업 목표

**3가지 동시 수행**:

1. **Prompt builder 모듈 신설** — `portfolio/services/coach/prompt_builder.py`
   - Base class: `PromptBuilderBase`
   - 6 sub class: `E1PromptBuilder` ~ `E6PromptBuilder`
   - Helper: system prompt, JSON schema injection, format helper
   - Registry: `PROMPT_BUILDER_CLASSES` dict (Part 1/2 미러)

2. **E1 service 마이그레이션** — 기존 E1 service의 prompt 코드를 builder 호출로 전환
   - **단독 마이그레이션** (E2~E6는 Part 4 이연)
   - 기존 service 외부 API 시그니처 변경 0 (내부만 진화)

3. **Smoke 1~2 케이스 LLM 실측** — E1만
   - haiku 1 케이스 + (선택) sonnet 1 케이스
   - **#48 v3 자동 분기**: count_tokens API 정의상 ±2% 보장 첫 실측 검증
   - schema fitting (Part 2 output schema validate) 작동성 확인

### 1.2 Prompt Builder 모듈 설계 (제안)

```python
# portfolio/services/coach/prompt_builder.py

from abc import abstractmethod
from typing import ClassVar
from pydantic import BaseModel
from portfolio.schemas.commentary_input import (
    CommentaryInputBase, E1Input, E2Input, E3Input, E4Input, E5Input, E6Input
)
from portfolio.schemas.commentary_output import (
    CommentaryOutputBase, E1Output, E2Output, E3Output, E4Output, E5Output, E6Output
)


class PromptBuilderBase:
    """공통 prompt builder. Base는 stateless 함수형으로 설계 (인스턴스 X)."""

    # sub class에서 정의
    entry_point: ClassVar[str] = ""  # "e1" ~ "e6"
    input_schema: ClassVar[type[CommentaryInputBase]] = CommentaryInputBase
    output_schema: ClassVar[type[CommentaryOutputBase]] = CommentaryOutputBase

    @classmethod
    @abstractmethod
    def build_user_prompt(cls, input_data: CommentaryInputBase) -> str:
        """진입점별 user prompt 생성. sub class에서 구현."""

    @classmethod
    def build_system_prompt(cls) -> str:
        """공통 system prompt — output schema JSON 형식 지시 포함."""
        schema_json = cls.output_schema.model_json_schema()
        return f"""You are a Korean investment portfolio coach...
응답은 반드시 다음 JSON schema를 준수해야 합니다:
{schema_json}
"""

    @classmethod
    def build_messages(cls, input_data: CommentaryInputBase) -> list[dict]:
        """LLM API 호출용 messages 배열 생성."""
        return [
            {"role": "system", "content": cls.build_system_prompt()},
            {"role": "user", "content": cls.build_user_prompt(input_data)},
        ]


class E1PromptBuilder(PromptBuilderBase):
    entry_point = "e1"
    input_schema = E1Input
    output_schema = E1Output

    @classmethod
    def build_user_prompt(cls, input_data: E1Input) -> str:
        # 기존 E1 service의 prompt 코드를 여기로 이동
        # Holding 5종 + GARP×15 metrics + preset context
        ...


# E2~E6 builder는 §1.3 마이그레이션 범위에 따라 스켈레톤만 (NotImplementedError raise) 또는 기존 prompt 보존


PROMPT_BUILDER_CLASSES: dict[str, type[PromptBuilderBase]] = {
    "e1": E1PromptBuilder,
    "e2": E2PromptBuilder,
    "e3": E3PromptBuilder,
    "e4": E4PromptBuilder,
    "e5": E5PromptBuilder,
    "e6": E6PromptBuilder,
}
```

**구현 룰**:

- Base는 stateless classmethod 기반 (인스턴스 X) — Part 1/2 schema의 frozen=True 미러
- `build_system_prompt`는 base에서 통합 (output schema JSON 자동 injection)
- `build_user_prompt`는 sub class별 구현 — 진입점별 데이터 구조 반영
- `build_messages`는 base에서 통합 — `[system, user]` 2개 메시지 배열 생성
- **E2~E6 sub builder는 스켈레톤만 작성** (`NotImplementedError("Part 4에서 마이그레이션 예정")` raise)
  - PROMPT_BUILDER_CLASSES dict는 6 entry 모두 채워 Part 1/2 미러 유지
  - 단위 테스트는 E1만 실측, E2~E6는 dict entry 존재 검증만

### 1.3 E1 Service 마이그레이션 룰

**대상**: 기존 E1 진입점 service (정확한 파일 경로는 §3 Step 1 인벤토리에서 확인)

- 후보: `portfolio/services/coach/e1_service.py` 또는 `portfolio/services/coach/holding_commentary_service.py`

**마이그레이션 룰**:

- 기존 service 함수의 **외부 시그니처 변경 0** (호출자 영향 0)
- 내부 prompt 생성 코드만 `E1PromptBuilder.build_messages(input_data)` 호출로 전환
- 기존 dict/string 기반 input → `E1Input` Pydantic 인스턴스 변환 (Part 1 schema 활용)
- LLM 응답 파싱 → `E1Output.model_validate_json(response)` (Part 2 schema 활용)
- ValidationError 발생 시 #41 재오픈 트리거 (§1.6 Fallback)

**E2~E6 service는 변경 0**.

### 1.4 Smoke 1~2 케이스 LLM 실측 설계

**케이스**:

| #   | 모델          | 입력                      | 비용 예상 | 목적                                              |
| --- | ------------- | ------------------------- | --------- | ------------------------------------------------- |
| 1   | haiku         | E1 / portfolio_a2 fixture | ~$0.005   | 메인 검증 (글쓰기 가설 5/5 정착, primary)         |
| 2   | sonnet (선택) | E1 / portfolio_a2 fixture | ~$0.010   | #48 v3 delta 모델별 측정 (선택, cap 마진 충분 시) |

**총 예상**: $0.005~0.015, slice cap $1.00 마진 99%+

**Smoke 단계 측정 항목**:

- LLM 응답이 Part 2 `E1Output` schema에 validate PASS (fitting 작동성)
- 응답 latency (참고)
- 실제 input_tokens / output_tokens (#48 v3 비교 baseline)
- count_tokens API 호출 → estimator 예측 토큰
- **delta = |actual - estimated| / actual** → KPI 임계 ±10% 적용 (count_tokens 명세상 ±2% 보장보다 보수적)

### 1.5 #48 v3 자동 분기 룰 (Slice 10 예약 수행)

**Slice 10 종결 시 예약된 룰** ("Slice 11 첫 LLM 호출 시 자연 분기"):

| 케이스    | 측정                                  | KPI 판정                                                           |
| --------- | ------------------------------------- | ------------------------------------------------------------------ |
| smoke N=1 | input_tokens delta 1건                | weak signal (Slice 7 H3 학습) → Part 4 매트릭스에서 재측정         |
| smoke N=2 | input_tokens delta 2건 (haiku/sonnet) | max_delta ≤10% → v3 PASS / >10% → keep_open + Slice 12 Step 0 후보 |

**측정 코드** (Step 5에서 실행):

```python
import anthropic
client = anthropic.Anthropic()

# 1. estimator 예측
from portfolio.services.coach.token_estimator import estimate_input_tokens  # v3
predicted = estimate_input_tokens(messages, model="claude-haiku-4-5-20251001")

# 2. count_tokens API 호출
counted = client.messages.count_tokens(
    model="claude-haiku-4-5-20251001",
    messages=messages,
).input_tokens

# 3. 실측 (LLM 호출 결과)
response = client.messages.create(...)
actual = response.usage.input_tokens

# 4. delta 계산
delta_predicted = abs(actual - predicted) / actual
delta_counted = abs(actual - counted) / actual  # 명세상 ≤2% 보장
```

**KPI 추가**:

- KPI 11: #48 v3 max_delta ≤10% (smoke N=2 시), N=1 시 weak signal 표기

### 1.6 Fallback 룰 (Part 3 한정)

| 트리거                                           | 대응                                                                                       |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| schema fitting 실패 (E1Output ValidationError)   | #41 재오픈 + sub class 보강 결정. Part 3 LLM 호출 중단, builder 단독 검증 후 Part 4 재시도 |
| 회귀 +14 초과 (예상 +6~10의 ±70% 마진 안전 상한) | Step 정지, builder 설계 재검토                                                             |
| IDENTICAL 7/7 깨짐                               | 즉시 `git revert`, 원인 진단                                                               |
| smoke 비용 $0.05 초과 (예상 $0.015의 333%)       | Step 5 정지, prompt 토큰 검토 + token_budgets 갱신 후 재진입                               |
| #48 v3 max_delta > 10%                           | 분석 dump, Slice 12 Step 0 후보 등록 (Part 3는 정상 종결, 부채만 등록)                     |
| Slice cap $1.00 도달 80% ($0.80)                 | 즉시 정지, Part 4/5 영향 분석                                                              |

---

## §2. 작업 환경 사전 확인

```bash
# 1. 브랜치 확인
git branch --show-current
# 기대값: slice11

# 2. Part 2 commit 확인
git log -1 --oneline
# 기대값: 975958f (...)

# 3. 회귀 baseline 확인
pytest portfolio/ tests/ -x -q 2>&1 | tail -5
# 기대값: 550 passed

# 4. Part 1/2 schema 모듈 import 검증
python -c "from portfolio.schemas.commentary_input import COMMENTARY_INPUT_CLASSES; print(len(COMMENTARY_INPUT_CLASSES))"
python -c "from portfolio.schemas.commentary_output import COMMENTARY_OUTPUT_CLASSES; print(len(COMMENTARY_OUTPUT_CLASSES))"
# 기대값: 6 / 6

# 5. E1 service 인벤토리
grep -rn "def.*generate.*commentary\|build.*prompt\|messages\s*=" portfolio/services/coach/ | grep -i "e1\|holding"

# 6. 기존 token_estimator 위치 확인
find portfolio/ -name "*token*estimator*" -o -name "*estimator*token*"

# 7. ANTHROPIC_API_KEY 확인 (smoke 호출용)
echo "API key set: $([ -n "$ANTHROPIC_API_KEY" ] && echo YES || echo NO)"
```

위 모든 명령 결과를 §10 회신에 dump 포함.

---

## §3. 작업 단계 (Step 1 ~ Step 8)

### Step 1: 호출자 인벤토리 + builder 설계 (20분)

**산출물**: `docs/portfolio/coach/slice11/part3_inventory.md`

- E1 service 위치 + 기존 prompt 코드 dump
- E2~E6 service 위치 (변경 없을 예정, 참고용)
- 기존 token estimator 위치 (#48 v3 검증용)
- Base + sub builder 인터페이스 매핑표

**KPI 1**: E1 service 파일 식별 PASS / 기존 prompt 코드 추출 PASS

### Step 2: prompt_builder.py 신설 (60분)

**산출물**: `portfolio/services/coach/prompt_builder.py`

- `PromptBuilderBase` (build_system_prompt, build_messages stateless classmethod)
- `E1PromptBuilder` 풀 구현 (기존 prompt 코드 이식)
- `E2PromptBuilder` ~ `E6PromptBuilder` 스켈레톤 (`build_user_prompt` 호출 시 `NotImplementedError("Part 4에서 마이그레이션 예정")` raise)
- `PROMPT_BUILDER_CLASSES` dict 6 entry

**구현 룰**:

- Base는 Part 1/2 schema 구조 미러
- stateless classmethod 패턴 (인스턴스 X)
- system prompt에 output schema JSON 자동 injection
- E1 user prompt는 기존 코드의 의미적 동치 보장 (output 동등성 확보)

**KPI 2**: 모듈 import 성공, PROMPT_BUILDER_CLASSES 6 entry 검증

```bash
python -c "
from portfolio.services.coach.prompt_builder import PROMPT_BUILDER_CLASSES, E1PromptBuilder
assert len(PROMPT_BUILDER_CLASSES) == 6
assert E1PromptBuilder.entry_point == 'e1'
print('OK')
"
```

### Step 3: E1 Service 마이그레이션 (40분)

**산출물**: 기존 E1 service 파일 (in-place 수정)

- 기존 prompt 생성 코드 → `E1PromptBuilder.build_messages(input_data)` 호출
- 입력 변환: 기존 dict/string → `E1Input` 인스턴스
- 응답 파싱: LLM 응답 → `E1Output.model_validate_json(response)`
- 외부 함수 시그니처 변경 0

**KPI 3**: E1 service 외부 API 호출자 (있다면) 영향 0

```bash
# E1 service의 public 함수 호출자 확인
grep -rn "from portfolio.services.coach.<e1_service_file> import" portfolio/ tests/
```

### Step 4: builder 단위 테스트 작성 (30분)

**산출물**: `tests/coach/test_prompt_builder.py` (8건)

1. `PromptBuilderBase`는 abstract — 직접 인스턴스화 시 build_user_prompt 호출 시 abstract error
2. `E1PromptBuilder.build_system_prompt()` JSON schema 포함
3. `E1PromptBuilder.build_user_prompt(e1_input)` 정상 작동 (portfolio_a2 fixture)
4. `E1PromptBuilder.build_messages()` system+user 2개 반환
5. `PROMPT_BUILDER_CLASSES` dict 6 entry, 키 정렬 검증
6. `E2PromptBuilder.build_user_prompt()` 호출 시 `NotImplementedError` raise (Part 4 예정 표시 확인)
7. PROMPT_BUILDER_CLASSES와 COMMENTARY_INPUT_CLASSES/COMMENTARY_OUTPUT_CLASSES 키 1:1 대응 검증
8. E1 user prompt 결정성 검증 (같은 input → 같은 output, stateless 확인)

**KPI 4**: 8/8 PASS

### Step 5: Smoke LLM 호출 + #48 v3 측정 (15분)

**산출물**:

- `docs/portfolio/coach/slice11/part3_smoke_dump.md` (LLM 호출 결과 + token delta 측정)

**실행 코드** (script `scripts/slice11_part3_smoke.py` 또는 ad-hoc):

```python
# 1. portfolio_a2 fixture 로드
from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input
e1_input = load_portfolio_a2_input("e1")

# 2. prompt 생성
from portfolio.services.coach.prompt_builder import E1PromptBuilder
messages = E1PromptBuilder.build_messages(e1_input)

# 3. estimator 예측 + count_tokens 호출 (#48 v3)
from portfolio.services.coach.token_estimator import estimate_input_tokens
import anthropic
client = anthropic.Anthropic()

predicted = estimate_input_tokens(messages, model="claude-haiku-4-5-20251001")
counted = client.messages.count_tokens(
    model="claude-haiku-4-5-20251001",
    messages=messages,
).input_tokens

# 4. 실측 LLM 호출 (Case 1: haiku)
response_haiku = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2000,
    messages=messages,
)
actual_haiku = response_haiku.usage.input_tokens

# 5. delta 계산
delta_predicted_haiku = abs(actual_haiku - predicted) / actual_haiku
delta_counted_haiku = abs(actual_haiku - counted) / actual_haiku

# 6. schema fitting 검증
from portfolio.schemas.commentary_output import E1Output
output = E1Output.model_validate_json(response_haiku.content[0].text)

# 7. Case 2 (sonnet, 선택) — slice cap 마진 확인 후 진행
# ... (haiku와 동일 패턴, model만 변경)
```

**측정 항목** dump:

- predicted / counted / actual (haiku, sonnet)
- delta_predicted / delta_counted
- output_tokens (haiku, sonnet)
- latency (참고)
- schema fitting PASS/FAIL
- LLM 응답 raw 텍스트 (Slice 11 #52 정책: dump 보존)

**KPI 5**: schema fitting PASS (E1Output validate 성공)
**KPI 6**: smoke 비용 ≤ $0.05 (Fallback 임계 333%)

### Step 6: 회귀 + IDENTICAL 검증 (10분)

```bash
# 6.1 신규 테스트 단독
pytest tests/coach/test_prompt_builder.py -v 2>&1 | tail -15

# 6.2 portfolio 전체 회귀
pytest portfolio/ tests/ -x -q 2>&1 | tail -5

# 6.3 IDENTICAL 7/7 검증
pytest portfolio/tests/test_static_integrity.py -v 2>&1 | tail -15

# 6.4 E1 service 회귀 (마이그레이션 영향 확인)
pytest portfolio/tests/test_e1_*.py portfolio/tests/test_holding_*.py -v 2>&1 | tail -20
```

**KPI 7**: 회귀 550 → 556~560 (+6~10) 또는 ±30% 마진 안 (+4~13)
**KPI 8**: IDENTICAL 7/7 유지
**KPI 9**: E1 service 회귀 마이그레이션 후 동등성 PASS

### Step 7: classifier 갱신 (10분)

신규 9건 분류:

- builder 단위 테스트 8건 → no-cost
- smoke 1건 → cost

**산출물**: `portfolio/tests/slice11/test_regression_classifier.py` 갱신

**KPI 10**: classifier deviation

- cost KPI ±30% 이내
- no-cost KPI ±50% 이내

### Step 8: KPI matrix + Part 3 종결 보고 (25분)

**산출물**:

- `docs/portfolio/coach/slice11/kpi_part3.md` (KPI 12건)
- `docs/portfolio/coach/slice11/part3_closing.md` (종결 보고)

---

## §4. KPI 매트릭스 (Part 3, 12건)

| #   | KPI                        | 측정값 | 기대값                         | PASS/FAIL |
| --- | -------------------------- | ------ | ------------------------------ | --------- |
| 1   | E1 service 파일 식별       | TBD    | 1건 식별, prompt 코드 추출     | TBD       |
| 2   | prompt_builder 모듈 import | TBD    | 6 entry, E1 entry_point="e1"   | TBD       |
| 3   | E1 service 호출자 영향     | TBD    | 영향 0 (외부 API 불변)         | TBD       |
| 4   | builder 단위 테스트        | TBD    | 8/8 PASS                       | TBD       |
| 5   | schema fitting             | TBD    | E1Output validate PASS         | TBD       |
| 6   | smoke 비용                 | TBD    | ≤ $0.05 (Fallback 임계)        | TBD       |
| 7   | 회귀 +Δ                    | TBD    | +6~10 (±30% = +4~13)           | TBD       |
| 8   | IDENTICAL                  | TBD    | 7/7 유지                       | TBD       |
| 9   | E1 service 회귀            | TBD    | 마이그레이션 후 PASS           | TBD       |
| 10  | classifier deviation       | TBD    | cost ±30%, no-cost ±50%        | TBD       |
| 11  | #48 v3 max_delta           | TBD    | ≤10% (N=2) / weak signal (N=1) | TBD       |
| 12  | 슬라이스 cap 마진          | TBD    | ≥ 80% ($0.80 미만 사용)        | TBD       |

---

## §5. 부채 처리 룰

### 5.1 #48 v3 (Slice 10 close, Part 3 자연 분기)

| 결과                 | 처리                                                                      |
| -------------------- | ------------------------------------------------------------------------- |
| max_delta ≤10% (N=2) | v3 정책 정착 확정, Slice 12+ 자연 활용                                    |
| max_delta ≤10% (N=1) | weak signal, Part 4 매트릭스에서 재측정 (N≥10), Slice 12 Step 0 후보 없음 |
| max_delta >10% (N≥1) | keep_open, Slice 12 Step 0 후보 등록 + 분석 dump                          |

### 5.2 #41 재오픈 가능성

| 트리거                 | 처리                                               |
| ---------------------- | -------------------------------------------------- |
| E1Output validate 실패 | #41 재오픈 + sub class 보강 결정 (Part 3 LLM 중단) |
| E1Output validate PASS | #41 close 유지 (Part 2 결정 그대로)                |

### 5.3 신규 부채 후보

| ID         | 내용                       | PS  | 트리거                                       |
| ---------- | -------------------------- | --- | -------------------------------------------- |
| #54 (후보) | builder 모듈 helper 분리   | 1.0 | 모듈 700+ lines 도달 시 (Slice 13+ 모니터링) |
| #55 (후보) | E2~E6 builder 마이그레이션 | -   | Part 4 작업 항목 (부채 아님, 정규 작업)      |

---

## §6. 회신 형식 (§10)

```
# Slice 11 Part 3 종결

## §1 baseline 확인
- 브랜치: slice11
- Part 2 commit: 975958f
- baseline 회귀: 550
- Part 1/2 schema 검증: 6/6, 6/6

## §2 인벤토리 (Step 1)
- E1 service 파일: ___
- 기존 prompt 코드 라인 수: ___
- token_estimator 위치: ___

## §3 prompt_builder 모듈 (Step 2)
- 라인 수: ___
- E1 풀 구현, E2~E6 스켈레톤
- PROMPT_BUILDER_CLASSES 6 entry 검증 PASS

## §4 E1 service 마이그레이션 (Step 3)
- 변경 파일: ___
- 외부 시그니처 변경: 0
- 호출자 영향: ___건 (예상 0)

## §5 builder 단위 테스트 (Step 4)
- 신규 8건: __/8 PASS

## §6 Smoke + #48 v3 (Step 5)
- 케이스: N=___
- haiku: predicted=___, counted=___, actual=___, delta_predicted=___%, delta_counted=___%
- sonnet (있다면): predicted=___, counted=___, actual=___, delta_predicted=___%, delta_counted=___%
- schema fitting: PASS/FAIL
- smoke 비용: $___
- LLM raw 응답 dump 위치: ___

## §7 회귀 (Step 6)
- 550 → ___ (+__)
- KPI 7 PASS/FAIL
- IDENTICAL 7/7 PASS/FAIL
- E1 service 회귀 PASS/FAIL

## §8 classifier (Step 7)
- 신규 9건 분류 + deviation

## §9 비용
- 단독: $___
- 누적: $2.3775 + $___ = $___
- slice cap: $___ / $1.00 (마진 ___%)

## §10 KPI matrix (12건)
| # | KPI | 측정값 | PASS/FAIL |
| 1 | ... | ... | ... |
(12건)

## §11 부채 처리
- #48 v3: PASS / weak signal / FAIL → 처리 결과
- #41: close 유지 / 재오픈

## §12 산출물 dump
- portfolio/services/coach/prompt_builder.py
- portfolio/services/coach/<e1_service> (수정)
- tests/coach/test_prompt_builder.py
- docs/portfolio/coach/slice11/part3_inventory.md
- docs/portfolio/coach/slice11/part3_smoke_dump.md
- docs/portfolio/coach/slice11/kpi_part3.md
- docs/portfolio/coach/slice11/part3_closing.md

## §13 커밋
- commit hash: ___
- commit message: "slice11 part3: prompt builder + e1 migration + smoke (#48 v3 ___)"

## §14 Part 4 진입 준비
- builder PRODUCTION READY (E1)
- E2~E6 마이그레이션 작업 항목 명시
- Part 4 scope: E2~E6 service 마이그레이션 + 풀 matrix (haiku/sonnet × 6 진입점 = 12 케이스) + manual eval 준비
- Slice cap 잔여: $___ ($1.00 - $___)
```

---

## §7. 예상 산출물 목록

| 영역         | 파일                                                    | 신규/수정           |
| ------------ | ------------------------------------------------------- | ------------------- |
| builder      | `portfolio/services/coach/prompt_builder.py`            | **신규**            |
| service      | `portfolio/services/coach/<e1_service>.py`              | **수정 (in-place)** |
| 테스트       | `tests/coach/test_prompt_builder.py`                    | **신규**            |
| classifier   | `portfolio/tests/slice11/test_regression_classifier.py` | 수정 (+1~2)         |
| smoke script | `scripts/slice11_part3_smoke.py` (선택)                 | 신규                |
| 문서         | `docs/portfolio/coach/slice11/part3_inventory.md`       | 신규                |
| 문서         | `docs/portfolio/coach/slice11/part3_smoke_dump.md`      | 신규                |
| 문서         | `docs/portfolio/coach/slice11/kpi_part3.md`             | 신규                |
| 문서         | `docs/portfolio/coach/slice11/part3_closing.md`         | 신규                |

---

## §8. 작업 시간 예상

| Step   | 작업                    | 시간        |
| ------ | ----------------------- | ----------- |
| 1      | 인벤토리 + builder 설계 | 20분        |
| 2      | prompt_builder.py 신설  | 60분        |
| 3      | E1 service 마이그레이션 | 40분        |
| 4      | builder 단위 테스트     | 30분        |
| 5      | smoke + #48 v3 측정     | 15분        |
| 6      | 회귀 + IDENTICAL        | 10분        |
| 7      | classifier 갱신         | 10분        |
| 8      | KPI + 종결 보고         | 25분        |
| **합** |                         | **~3h 30m** |

---

## §9. 작업 시작 신호

```bash
git status  # slice11 브랜치, clean 상태 확인
git log -1 --oneline  # 975958f 확인
pytest portfolio/ tests/ -x -q 2>&1 | tail -5  # 550 passed 확인
echo "API key set: $([ -n "$ANTHROPIC_API_KEY" ] && echo YES || echo NO)"
```

위 모든 명령 기대값 일치 시 Step 1 진입. 특히 **ANTHROPIC_API_KEY 미설정 시 Step 5 smoke 진행 불가 → 즉시 중단 후 보고**.

---

**END OF INSTRUCTIONS**
