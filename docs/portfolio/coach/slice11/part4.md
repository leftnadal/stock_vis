# Slice 11 Part 4 작업 지시서

**작업명**: E2~E6 신규 Coach Service + 24 케이스 매트릭스 + #48 v3 자동 측정 (N=26 강 신호)
**브랜치**: `slice11`
**선행 의존**: Slice 11 Part 3 종결 완료 (commit `4789cc8`, 회귀 559, IDENTICAL 7/7, #48 v3 max_delta 0.0% 정착, #41 close)
**부채 처리**: Slice 10 #48 (Part 3 정착 후 N=26으로 견고화) / Part 3 잠재 #41 재오픈 트리거 모니터링

---

## §0. Part 4 진입 baseline

| 항목             | 값                                                                                     |
| ---------------- | -------------------------------------------------------------------------------------- |
| 회귀             | 559 (Part 3 종결 후)                                                                   |
| 누적 비용        | $2.4065 / 임계 $4.00 (마진 39.8%)                                                      |
| Slice cap        | $0.0290 / $1.00 사용 (마진 97.1%)                                                      |
| IDENTICAL        | 7/7 (9슬라이스 누적)                                                                   |
| LLM 호출         | 2/50 (Slice 11 누적)                                                                   |
| 현재 브랜치      | `slice11` (Part 3 commit `4789cc8`)                                                    |
| 자산             | Part 1/2/3: input + output schema + E1 prompt builder + E1 coach service + #48 v3 정착 |
| Part 3 실측 단가 | haiku/sonnet 각 ~$0.0145 (E1, input 1807 토큰)                                         |

---

## §1. Part 4 작업 범위

### 1.1 작업 목표 (5가지 동시 수행)

1. **Production 인벤토리 (Step 1)** — E2~E6 진입점의 기존 production endpoint 사용 여부 표 작성 (참고 데이터)

2. **E2~E6 Prompt Builder 풀 구현** — Part 3 E1 패턴 미러
   - `E2PromptBuilder` ~ `E6PromptBuilder` 5건 풀 구현
   - 기존 스켈레톤 (`NotImplementedError("Part 4에서 마이그레이션 예정")`) 제거

3. **E2~E6 신규 Coach Service** — Part 3 `run_e1_coach` 패턴 미러
   - `run_e2_coach` ~ `run_e6_coach` 5건 신규
   - 기존 production endpoint (있다면) **무변경** (frontend 보호)

4. **24 케이스 풀 매트릭스 LLM 실측**
   - **6 진입점 × 2 모델 × 2 반복 = 24 케이스**
   - 모든 케이스에 #48 v3 delta 자동 측정 (N=26 누적, Part 3 N=2 포함)
   - 모든 케이스 schema fitting 검증
   - 매트릭스 dump JSON 보존 (Part 5 manual eval 입력)

5. **#48 v3 견고화 + #41 재오픈 모니터링**

### 1.2 Prompt Builder 구현 룰 (E2~E6)

각 sub builder의 `build_user_prompt` 구현:

- `input_schema` 사용 (E2Input ~ E6Input, Part 1 정착)
- `output_schema` 사용 (E2Output ~ E6Output, Part 2 정착)
- 기존 service의 prompt 코드를 의미적 동치로 이식 (Step 1 인벤토리 결과 활용)

**진입점별 특이사항**:

| 진입점                | 데이터 구조                                | 특이사항                                   |
| --------------------- | ------------------------------------------ | ------------------------------------------ |
| E2 매수 후보          | 후보 종목 + GARP 메트릭                    | quoted_metrics 사용 (Part 2 output schema) |
| E3 포트폴리오 집중도  | hhi/sector_hhi/top3 등 portfolio-level 7종 | action_items + risk_flags 사용             |
| E4 대화 Q&A           | Tier 1~3 단순/표준/심화                    | base만 사용 (action_items/risk_flags 없음) |
| E5 수익률 시계열 해설 | TimeSeriesContext (Slice 8 #27)            | action_items + quoted_metrics 사용         |
| E6 ETF 분석           | ETF 기본 정보 + Income preset              | risk_flags + quoted_metrics 사용           |

### 1.3 E2~E6 Service 마이그레이션 룰

**대상**: 각 진입점별 `portfolio/services/coach/e{N}_service.py` (Step 1 인벤토리에서 확정)

**A1 패턴 적용**:

- 신규 함수 `run_e{N}_coach(input_data: E{N}Input) -> E{N}Output` 추가
- 기존 production 함수 (있다면) **무변경**
- 입력: `E{N}Input` Pydantic 인스턴스
- 출력: `E{N}Output` (Part 2 schema validate)
- 내부에서 `E{N}PromptBuilder.build_messages(input_data)` 호출 → LLM → `E{N}Output.model_validate_json(response)`
- schema 비대칭 발견 시 Part 3 OneLineDiagnosis vs E1Output 패턴 그대로 적용

**E1과의 차이**:

- E1은 이미 Part 3에서 `run_e1_coach` 작성됨 — **변경 없음**, 패턴 참조만

### 1.4 24 케이스 매트릭스 설계

#### 케이스 구성

```
6 진입점 (E1~E6) × 2 모델 (haiku, sonnet) × 2 반복 (#1, #2) = 24 케이스
```

#### Fixture

모든 케이스는 `portfolio_a2` fixture 사용 (Part 1 정착)

- E1: portfolio_a2.inputs.e1
- E2: portfolio_a2.inputs.e2
- E3: portfolio_a2.inputs.e3
- E4: portfolio_a2.inputs.e4
- E5: portfolio_a2.inputs.e5 (TimeSeriesContext 포함)
- E6: portfolio_a2.inputs.e6

#### 측정 항목 (케이스별)

| 항목                     | 측정 방법                                              |
| ------------------------ | ------------------------------------------------------ |
| input_tokens (predicted) | `estimate_input_tokens()` (v3 estimator)               |
| input_tokens (counted)   | `client.messages.count_tokens()` (Anthropic API, 무료) |
| input_tokens (actual)    | `response.usage.input_tokens`                          |
| output_tokens            | `response.usage.output_tokens`                         |
| delta_predicted          | `\|actual - predicted\| / actual`                      |
| delta_counted            | `\|actual - counted\| / actual`                        |
| cost_usd                 | LLMClient 메타데이터                                   |
| latency_ms               | LLMClient 메타데이터                                   |
| schema_fitting           | `E{N}Output.model_validate_json()` PASS/FAIL           |
| response_text            | raw 응답 텍스트 (Slice 11 #52 정책 dump)               |
| naturalness              | (Part 5 manual eval, Part 4에서는 측정 없음)           |
| insight                  | (Part 5 manual eval, Part 4에서는 측정 없음)           |

#### 비용 예상

| 항목                                 | 값                                                 |
| ------------------------------------ | -------------------------------------------------- |
| Part 3 실측 단가 (haiku/sonnet 평균) | ~$0.0145                                           |
| 24 케이스 예상                       | $0.0145 × 24 = $0.348                              |
| **누적 cap 예상**                    | $0.0290 + $0.348 = **$0.377**                      |
| **cap 마진**                         | $1.00 - $0.377 = **62.3%**                         |
| 누적 임계 예상                       | $2.4065 + $0.348 = $2.755 (임계 $4.00, 마진 31.1%) |

#### 24 케이스 실행 순서 (단계적 risk-on)

| 배치           | 케이스                                 | 비용 누적 | cap 마진 | 조건부 정지                        |
| -------------- | -------------------------------------- | --------- | -------- | ---------------------------------- |
| Batch 1        | E1~E6 × haiku × #1 (6)                 | $0.087    | 91%      | 정상                               |
| Batch 2        | E1~E6 × sonnet × #1 (6)                | $0.174    | 83%      | 정상                               |
| Batch 3        | E1~E6 × haiku × #2 (6)                 | $0.261    | 74%      | 정상                               |
| Batch 4        | E1~E6 × sonnet × #2 (6)                | $0.348    | 65%      | 정상                               |
| **Fallback A** | cap 마진 70% 도달 시 (대략 Batch 3 끝) | -         | -        | **즉시 정지 + 부분 매트릭스 종결** |
| **Fallback B** | cap 마진 60% 도달 시 (Batch 4 진행 중) | -         | -        | **즉시 정지, Step 5 종결**         |

### 1.5 #48 v3 자동 측정 룰

**케이스별 자동 측정** (Step 5에서 매트릭스 루프 내부):

```python
for case in cases:
    # 1. estimator 예측
    predicted = estimate_input_tokens(messages, model=case.model)
    # 2. count_tokens API
    counted = client.messages.count_tokens(model=case.model, messages=messages).input_tokens
    # 3. LLM 호출
    response = client.messages.create(...)
    actual = response.usage.input_tokens
    # 4. delta
    case.delta_predicted = abs(actual - predicted) / actual
    case.delta_counted = abs(actual - counted) / actual
```

**N=26 누적 (Part 3 N=2 + Part 4 N=24) 판정 룰**:

| 판정            | 조건                                         | 처리                                     |
| --------------- | -------------------------------------------- | ---------------------------------------- |
| **견고화 PASS** | max_delta ≤ 2% (count_tokens 명세 보장 한도) | v3 정착 완전 견고화, Slice 12+ 자연 활용 |
| **PASS (보수)** | max_delta ≤ 10% (Part 3 임계)                | v3 정착 유지, weak signal 케이스 dump    |
| **FAIL**        | max_delta > 10%                              | #48 재오픈, Slice 12 Step 0 후보 등록    |

### 1.6 Fallback 룰 (Part 4 한정, B2 24 케이스 보수 강화)

| 트리거                                                   | 대응                                                                        |
| -------------------------------------------------------- | --------------------------------------------------------------------------- |
| **Slice cap 70% 도달 ($0.30 사용)**                      | 즉시 매트릭스 중단, 측정된 케이스만으로 Part 4 종결 (KPI 14 부분 PASS 표기) |
| **Slice cap 80% 도달 ($0.80 사용)**                      | 비상 정지, Step 5 종결 + 부채 등록                                          |
| 단일 케이스 비용 $0.05 초과 (Part 3 실측 $0.0145의 345%) | 해당 케이스 dump, 다음 케이스 진행 (전체 중단 X)                            |
| 24 케이스 총 비용 $0.50 초과 (예상 $0.348의 144%)        | 즉시 정지, prompt 토큰 검토                                                 |
| 회귀 +50 초과 (예상 +25~40의 ±70% 상한)                  | Step 정지, 5건 service 패턴 재검토                                          |
| IDENTICAL 7/7 깨짐                                       | 즉시 `git revert`, 원인 진단                                                |
| schema fitting 실패 (E2~E6 sub class ValidationError)    | 해당 sub class 보강, #41 재오픈 + Part 4 keep_open + Slice 12 Step 0 후보   |
| #48 v3 max_delta > 10% (단일 케이스)                     | dump, 매트릭스 계속, 종결 시 keep_open 검토                                 |
| haiku/sonnet 응답 latency > 60s                          | 케이스 dump, 다음 진행                                                      |

---

## §2. 작업 환경 사전 확인

```bash
# 1. 브랜치 확인
git branch --show-current
# 기대값: slice11

# 2. Part 3 commit 확인
git log -1 --oneline
# 기대값: 4789cc8 (...)

# 3. 회귀 baseline 확인
pytest portfolio/ tests/ -x -q 2>&1 | tail -5
# 기대값: 559 passed

# 4. Part 1/2/3 자산 검증
python -c "
from portfolio.schemas.commentary_input import COMMENTARY_INPUT_CLASSES
from portfolio.schemas.commentary_output import COMMENTARY_OUTPUT_CLASSES
from portfolio.services.coach.prompt_builder import PROMPT_BUILDER_CLASSES
assert len(COMMENTARY_INPUT_CLASSES) == 6
assert len(COMMENTARY_OUTPUT_CLASSES) == 6
assert len(PROMPT_BUILDER_CLASSES) == 6
print('Part 1/2/3 자산 PASS')
"

# 5. Part 3 E1 coach service 검증
python -c "
from portfolio.services.coach.e1_service import run_e1_coach
print('run_e1_coach OK')
"

# 6. ANTHROPIC_API_KEY 확인
echo "API key set: $([ -n "$ANTHROPIC_API_KEY" ] && echo YES || echo NO)"

# 7. Slice 11 누적 LLM 호출 확인 (CostGuard 잔여 슬롯)
python -c "
from portfolio.services.coach.cost_guard import CostGuard
print(f'LLM 잔여: 48/50')  # Part 3 후 2 사용
"
```

위 모든 명령 결과를 §10 회신에 dump 포함. **API_KEY 미설정 시 즉시 중단 보고**.

---

## §3. 작업 단계 (Step 1 ~ Step 8)

### Step 1: Production 인벤토리 + E2~E6 service 식별 (25분)

**산출물**: `docs/portfolio/coach/slice11/part4_inventory.md`

**작업**:

1. E2~E6 진입점별 기존 service 파일 경로 식별
2. 기존 production endpoint (URL 또는 함수명) 사용 여부 표 작성
3. 기존 service의 prompt 생성 코드 dump (E2~E6 builder 이식 참고용)
4. 기존 input/output 데이터 구조 vs Part 1/2 schema 비교

**표 양식**:

| 진입점 | service 파일    | production 함수 | production endpoint    | frontend 사용 | schema 비대칭                |
| ------ | --------------- | --------------- | ---------------------- | ------------- | ---------------------------- |
| E1     | `e1_service.py` | `run_e1_garp`   | (예시) `/api/coach/e1` | 사용중        | OneLineDiagnosis vs E1Output |
| E2     | TBD             | TBD             | TBD                    | TBD           | TBD                          |
| ...    | ...             | ...             | ...                    | ...           | ...                          |

**KPI 1**: 5 진입점 모두 service 파일 식별 + production 사용 여부 표 완성

### Step 2: E2~E6 Prompt Builder 풀 구현 (90분)

**산출물**: `portfolio/services/coach/prompt_builder.py` 수정 (E2~E6 스켈레톤 → 풀 구현)

**구현 룰**:

- Part 3 E1PromptBuilder 패턴 그대로 (`entry_point`, `input_schema`, `output_schema`, `build_user_prompt`)
- Step 1 인벤토리의 기존 prompt 코드를 의미적 동치로 이식
- `NotImplementedError` 제거
- 진입점별 데이터 구조 반영 (§1.2 표 참고)

**구현 순서 권장** (단순 → 복잡):

1. E4 (대화 Q&A, base만 사용) — 30분
2. E2 (매수 후보, quoted_metrics) — 30분
3. E3 (포트폴리오 집중도, action+risk) — 30분
4. E5 (시계열, TimeSeriesContext) — 30분
5. E6 (ETF, risk+quoted) — 30분

> **합산 150분 예상, 패턴 자산 활용 시 90분 압축 목표**

**KPI 2**: 5 builder 모두 `NotImplementedError` 제거 + portfolio_a2 fixture로 `build_user_prompt` 정상 호출

```bash
python -c "
from portfolio.services.coach.prompt_builder import PROMPT_BUILDER_CLASSES
from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input
for entry in ['e2', 'e3', 'e4', 'e5', 'e6']:
    builder_cls = PROMPT_BUILDER_CLASSES[entry]
    input_data = load_portfolio_a2_input(entry)
    messages = builder_cls.build_messages(input_data)
    assert len(messages) == 2
    print(f'{entry}: OK ({len(messages[1][\"content\"])} chars user prompt)')
"
```

### Step 3: E2~E6 신규 Coach Service 작성 (60분)

**산출물**: 각 진입점 service 파일에 `run_e{N}_coach` 추가 (5개 파일)

**구현 패턴** (Part 3 `run_e1_coach` 미러):

```python
# portfolio/services/coach/e{N}_service.py

from portfolio.schemas.commentary_input import E{N}Input
from portfolio.schemas.commentary_output import E{N}Output
from portfolio.services.coach.prompt_builder import E{N}PromptBuilder
from portfolio.services.coach.llm_client import LLMClient


def run_e{N}_coach(
    input_data: E{N}Input,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 2000,
) -> tuple[E{N}Output, dict]:
    """E{N} 진입점 coach service. 기존 production 함수는 무변경.

    Returns:
        (output, metadata) — metadata includes provider/model/latency_ms/
        input_tokens/output_tokens/cost_usd/fallback_from (LLMClient 메타데이터)
    """
    messages = E{N}PromptBuilder.build_messages(input_data)
    client = LLMClient()
    response, metadata = client.create_with_metadata(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )
    output = E{N}Output.model_validate_json(response)
    return output, metadata
```

**KPI 3**: 5 service 함수 모두 import 성공 + 기존 production 함수 무변경 확인

```bash
python -c "
for n in [2, 3, 4, 5, 6]:
    exec(f'from portfolio.services.coach.e{n}_service import run_e{n}_coach')
    print(f'run_e{n}_coach: OK')
"

# 기존 production 함수 무변경 검증 (회귀)
pytest portfolio/tests/test_e*_service.py -v 2>&1 | tail -30
```

### Step 4: Builder + Service 단위 테스트 (30분)

**산출물**: `tests/coach/test_prompt_builder.py` 확장 + `tests/coach/test_coach_services.py` 신규

**테스트 케이스** (총 12건):

`test_prompt_builder.py` 확장 (5건):

- E2 builder `build_messages` portfolio_a2 정상
- E3 builder `build_messages` portfolio_a2 정상
- E4 builder `build_messages` portfolio_a2 정상 (base만 사용)
- E5 builder `build_messages` portfolio_a2 정상 (TimeSeriesContext 포함)
- E6 builder `build_messages` portfolio_a2 정상

`test_coach_services.py` 신규 (7건):

- E1 `run_e1_coach` import (Part 3 자산 확인)
- E2 `run_e2_coach` import 성공
- E3 `run_e3_coach` import 성공
- E4 `run_e4_coach` import 성공
- E5 `run_e5_coach` import 성공
- E6 `run_e6_coach` import 성공
- 6 service 함수 시그니처 일관성 (`(input, model, max_tokens) → (output, metadata)`)

> **단위 테스트는 LLM 호출 없음** — mock 또는 import + 시그니처 검증만

**KPI 4**: 신규 12건 PASS

### Step 5: 24 케이스 풀 매트릭스 실행 (45분)

**산출물**:

- `scripts/slice11_part4_matrix.py` (매트릭스 실행 스크립트)
- `docs/portfolio/coach/slice11/part4_matrix_dump.md` (모든 케이스 dump)
- `docs/portfolio/coach/slice11/part4_matrix.json` (구조화된 데이터, Part 5 manual eval 입력)

**실행 흐름** (단계적 risk-on):

```python
# scripts/slice11_part4_matrix.py
import json
from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input
from portfolio.services.coach import e1_service, e2_service, e3_service, e4_service, e5_service, e6_service
from portfolio.services.coach.cost_guard import CostGuard

SERVICES = {
    "e1": e1_service.run_e1_coach,
    "e2": e2_service.run_e2_coach,
    "e3": e3_service.run_e3_coach,
    "e4": e4_service.run_e4_coach,
    "e5": e5_service.run_e5_coach,
    "e6": e6_service.run_e6_coach,
}

MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-4-5-20251001"]
REPEATS = 2

cost_guard = CostGuard.get_instance()
results = []

# Batch 순서: E1~E6 × haiku × #1 → E1~E6 × sonnet × #1 → E1~E6 × haiku × #2 → E1~E6 × sonnet × #2
for repeat in [1, 2]:
    for model in MODELS:
        for entry in ["e1", "e2", "e3", "e4", "e5", "e6"]:
            # Fallback A: cap 마진 70% 도달 ($0.30 사용) 시 중단
            if cost_guard.current_spent >= 0.30:
                print(f"Fallback A 발동: cap 마진 70% 도달, 중단")
                break

            input_data = load_portfolio_a2_input(entry)
            service_fn = SERVICES[entry]

            # #48 v3 측정
            from portfolio.services.coach.prompt_builder import PROMPT_BUILDER_CLASSES
            from portfolio.services.coach.token_estimator import estimate_input_tokens
            import anthropic

            builder_cls = PROMPT_BUILDER_CLASSES[entry]
            messages = builder_cls.build_messages(input_data)
            predicted = estimate_input_tokens(messages, model=model)
            anthropic_client = anthropic.Anthropic()
            counted = anthropic_client.messages.count_tokens(model=model, messages=messages).input_tokens

            try:
                output, metadata = service_fn(input_data, model=model, max_tokens=2000)
                actual = metadata["input_tokens"]
                delta_predicted = abs(actual - predicted) / actual
                delta_counted = abs(actual - counted) / actual
                fitting_pass = True
            except Exception as e:
                output = None
                metadata = {"error": str(e)}
                actual = None
                delta_predicted = None
                delta_counted = None
                fitting_pass = False

            result = {
                "entry": entry,
                "model": model,
                "repeat": repeat,
                "predicted": predicted,
                "counted": counted,
                "actual": actual,
                "output_tokens": metadata.get("output_tokens"),
                "delta_predicted": delta_predicted,
                "delta_counted": delta_counted,
                "cost_usd": metadata.get("cost_usd"),
                "latency_ms": metadata.get("latency_ms"),
                "fitting_pass": fitting_pass,
                "response_text": output.model_dump_json() if output else None,
                "error": metadata.get("error"),
            }
            results.append(result)
            print(f"{entry}/{model[:20]}/#{repeat}: actual={actual} delta_pred={delta_predicted} cost=${metadata.get('cost_usd', 0):.4f} fitting={fitting_pass}")

# dump
with open("docs/portfolio/coach/slice11/part4_matrix.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
```

**KPI 5**: 매트릭스 실행 정상 종료 (Fallback 미발동 또는 부분 매트릭스 표기)
**KPI 6**: schema fitting PASS 비율 ≥ 23/24 (95.8%, 1건 실패 허용)
**KPI 7**: 매트릭스 총 비용 ≤ $0.50 (Fallback 임계 144%)
**KPI 8**: 슬라이스 cap 사용 ≤ $0.80 (마진 ≥ 20%)
**KPI 9**: #48 v3 max_delta 측정 (N=26 누적)

### Step 6: 회귀 + IDENTICAL 검증 (15분)

```bash
# 6.1 신규 단위 테스트
pytest tests/coach/test_prompt_builder.py tests/coach/test_coach_services.py -v 2>&1 | tail -25

# 6.2 portfolio 전체 회귀
pytest portfolio/ tests/ -x -q 2>&1 | tail -5

# 6.3 IDENTICAL 7/7 검증
pytest portfolio/tests/test_static_integrity.py -v 2>&1 | tail -15

# 6.4 E2~E6 기존 service 회귀 (production 함수 무변경 확인)
pytest portfolio/tests/test_e2_*.py portfolio/tests/test_e3_*.py portfolio/tests/test_e4_*.py portfolio/tests/test_e5_*.py portfolio/tests/test_e6_*.py -v 2>&1 | tail -30
```

**KPI 10**: 회귀 559 → 584~599 (+25~40) 또는 ±30% 마진 [+17, +52]
**KPI 11**: IDENTICAL 7/7 유지
**KPI 12**: E2~E6 production 회귀 PASS (마이그레이션 영향 0)

### Step 7: classifier 갱신 (15분)

**산출물**: `portfolio/tests/slice11/test_regression_classifier.py` 갱신

신규 분류:

- 단위 테스트 12건 → no-cost
- 매트릭스 24 케이스 → cost (단 회귀 테스트로는 카운트 X, 매트릭스 결과만 검증)

**KPI 13**: classifier deviation

- cost KPI ±30% 이내
- no-cost KPI ±50% 이내

### Step 8: KPI matrix + Part 4 종결 보고 (25분)

**산출물**:

- `docs/portfolio/coach/slice11/kpi_part4.md` (KPI 16건)
- `docs/portfolio/coach/slice11/part4_closing.md` (종결 보고)

**Part 4 종결 보고 추가 항목**:

- #48 v3 N=26 누적 판정 (견고화 PASS / 보수 PASS / FAIL)
- #41 처리 상태 (close 유지 / 재오픈)
- Part 5 manual eval 준비도 (24 케이스 dump JSON ready)
- winner 판정 (자동 단계, 비용 efficiency만 — naturalness/insight는 Part 5 manual eval 후)
- 글쓰기 가설 7/7 잠정 (자동 단계, Part 5 manual eval 후 확정)

---

## §4. KPI 매트릭스 (Part 4, 16건)

| #   | KPI                   | 측정값 | 기대값                                 | PASS/FAIL |
| --- | --------------------- | ------ | -------------------------------------- | --------- |
| 1   | Production 인벤토리   | TBD    | 5 진입점 표 완성                       | TBD       |
| 2   | E2~E6 builder 구현    | TBD    | 5/5 NotImplementedError 제거           | TBD       |
| 3   | E2~E6 service 신규    | TBD    | 5 함수 import + production 무변경      | TBD       |
| 4   | 신규 단위 테스트      | TBD    | 12/12 PASS                             | TBD       |
| 5   | 매트릭스 실행         | TBD    | 24 케이스 또는 Fallback 부분           | TBD       |
| 6   | schema fitting        | TBD    | ≥ 23/24 (95.8%)                        | TBD       |
| 7   | 매트릭스 비용         | TBD    | ≤ $0.50                                | TBD       |
| 8   | slice cap 사용        | TBD    | ≤ $0.80 (마진 ≥ 20%)                   | TBD       |
| 9   | #48 v3 max_delta      | TBD    | ≤ 2% (견고화) / ≤ 10% (보수)           | TBD       |
| 10  | 회귀 +Δ               | TBD    | +25~40 (±30% = +17~52)                 | TBD       |
| 11  | IDENTICAL             | TBD    | 7/7 유지                               | TBD       |
| 12  | E2~E6 production 회귀 | TBD    | 무변경 (마이그레이션 영향 0)           | TBD       |
| 13  | classifier deviation  | TBD    | cost ±30%, no-cost ±50%                | TBD       |
| 14  | 누적 cap              | TBD    | ≤ $0.80                                | TBD       |
| 15  | 누적 임계             | TBD    | ≤ $4.00                                | TBD       |
| 16  | Part 5 준비도         | TBD    | matrix.json + manual eval rubric ready | TBD       |

---

## §5. 부채 처리 룰

### 5.1 #48 v3 (Slice 10 close, Part 3 N=2 정착, Part 4 N=26 견고화)

| 결과                                    | 처리                                                   |
| --------------------------------------- | ------------------------------------------------------ |
| max_delta ≤ 2% (count_tokens 명세 한도) | **견고화 PASS** — Slice 12+ 자연 활용, 부채 완전 종결  |
| 2% < max_delta ≤ 10%                    | 보수 PASS — Slice 12 모니터링, 부채 종결 유지          |
| max_delta > 10%                         | **FAIL** — #48 재오픈, Slice 12 Step 0 후보, 분석 dump |

### 5.2 #41 재오픈 모니터링

| 트리거                            | 처리                                                     |
| --------------------------------- | -------------------------------------------------------- |
| E2~E6 Output ValidationError 발생 | #41 재오픈, 해당 sub class 보강, Slice 12 Step 0 후보    |
| 24/24 fitting PASS                | #41 close 유지 (Part 2 결정 그대로)                      |
| 23/24 (1건 fitting 실패)          | dump + 분석, #41 keep_open 1 part (Part 5에서 패턴 분석) |

### 5.3 신규 부채 후보

| ID         | 내용                                    | PS  | 트리거                                                             |
| ---------- | --------------------------------------- | --- | ------------------------------------------------------------------ |
| #54 (후보) | builder 모듈 helper 분리                | 1.0 | 모듈 700+ lines 도달 시 (Slice 13+ 모니터링)                       |
| #55 (후보) | 기존 production endpoint 통합/deprecate | 3.0 | Slice 13+ frontend 통합 시점 결정                                  |
| #56 (후보) | output_token estimator 작성             | 1.5 | Part 4 output_tokens 데이터 누적 후 모델링 (Slice 12+ Step 0 후보) |

---

## §6. 회신 형식 (§10)

```
# Slice 11 Part 4 종결

## §1 baseline 확인
- 브랜치: slice11
- Part 3 commit: 4789cc8
- baseline 회귀: 559
- Part 1/2/3 자산 검증: 6/6/6 PASS
- API key: YES/NO

## §2 Production 인벤토리 (Step 1)
[5 진입점 표]

## §3 E2~E6 Builder 풀 구현 (Step 2)
- 구현 5/5 완료
- 모듈 라인 수: ___
- portfolio_a2 fixture build_messages 검증: 5/5 PASS

## §4 E2~E6 신규 Coach Service (Step 3)
- run_e2_coach ~ run_e6_coach: 5/5 신규
- production 함수 무변경: PASS
- 호출자 영향: 0

## §5 단위 테스트 (Step 4)
- 신규 12건: __/12 PASS

## §6 매트릭스 실행 (Step 5)
- 케이스 실행: __/24 (Fallback 발동 시 ___ 표기)
- schema fitting: __/24
- 매트릭스 비용: $___
- 매트릭스 결과 요약:
  | 진입점 | model | repeat | actual | delta_pred | cost | fitting |
  | ... | ... | ... | ... | ... | ... | ... |
  (24행 또는 부분)

## §7 #48 v3 N=26 판정
- max_delta_predicted: ___%
- max_delta_counted: ___%
- 판정: 견고화 PASS / 보수 PASS / FAIL
- 처리: ___

## §8 회귀 (Step 6)
- 559 → ___ (+__)
- KPI 10 PASS/FAIL
- IDENTICAL 7/7 PASS/FAIL
- E2~E6 production 회귀: PASS/FAIL

## §9 classifier (Step 7)
- 신규 분류 + deviation

## §10 비용
- Part 4 단독: $___
- 누적: $2.4065 + $___ = $___
- slice cap: $___ / $1.00 (마진 ___%)
- 임계 마진: ___% / $4.00

## §11 KPI matrix (16건)
| # | KPI | 측정값 | PASS/FAIL |
| 1 | ... | ... | ... |
(16건)

## §12 부채 처리
- #48 v3 N=26: 견고화 PASS / 보수 PASS / FAIL → 처리
- #41: close 유지 / 재오픈
- 신규 부채 후보: #54/#55/#56 (해당 시)

## §13 산출물 dump
- portfolio/services/coach/prompt_builder.py (E2~E6 풀 구현)
- portfolio/services/coach/e{2,3,4,5,6}_service.py (run_e*_coach 추가)
- tests/coach/test_prompt_builder.py (확장)
- tests/coach/test_coach_services.py (신규)
- scripts/slice11_part4_matrix.py
- docs/portfolio/coach/slice11/part4_inventory.md
- docs/portfolio/coach/slice11/part4_matrix_dump.md
- docs/portfolio/coach/slice11/part4_matrix.json
- docs/portfolio/coach/slice11/kpi_part4.md
- docs/portfolio/coach/slice11/part4_closing.md

## §14 커밋
- commit hash: ___
- commit message: "slice11 part4: e2~e6 coach services + 24-case matrix + v3 n=26"

## §15 Part 5 진입 준비
- Part 4 자산 PRODUCTION READY: builder 6/6, service 6/6, matrix.json 24 케이스
- Part 5 scope: 24 케이스 manual eval (naturalness + insight 2축, rubric 표준화)
- Slice cap 잔여: $___ ($1.00 - $___)
- 임계 마진: ___% (Part 5는 LLM 0 예상, 영향 최소)
- winner 자동 판정 (efficiency 기준): haiku/sonnet 격차 ___%
- 글쓰기 가설 7/7 잠정 / 확정 보류 (Part 5 manual eval 후)
```

---

## §7. 예상 산출물 목록

| 영역       | 파일                                                    | 신규/수정                    |
| ---------- | ------------------------------------------------------- | ---------------------------- |
| builder    | `portfolio/services/coach/prompt_builder.py`            | **수정 (E2~E6 풀 구현)**     |
| service    | `portfolio/services/coach/e2_service.py`                | **수정 (run_e2_coach 추가)** |
| service    | `portfolio/services/coach/e3_service.py`                | **수정**                     |
| service    | `portfolio/services/coach/e4_service.py`                | **수정**                     |
| service    | `portfolio/services/coach/e5_service.py`                | **수정**                     |
| service    | `portfolio/services/coach/e6_service.py`                | **수정**                     |
| 테스트     | `tests/coach/test_prompt_builder.py`                    | 수정 (확장 +5)               |
| 테스트     | `tests/coach/test_coach_services.py`                    | **신규 (7건)**               |
| classifier | `portfolio/tests/slice11/test_regression_classifier.py` | 수정                         |
| script     | `scripts/slice11_part4_matrix.py`                       | **신규**                     |
| 문서       | `docs/portfolio/coach/slice11/part4_inventory.md`       | 신규                         |
| 문서       | `docs/portfolio/coach/slice11/part4_matrix_dump.md`     | 신규                         |
| 문서       | `docs/portfolio/coach/slice11/part4_matrix.json`        | 신규                         |
| 문서       | `docs/portfolio/coach/slice11/kpi_part4.md`             | 신규                         |
| 문서       | `docs/portfolio/coach/slice11/part4_closing.md`         | 신규                         |

---

## §8. 작업 시간 예상

| Step   | 작업                               | 시간       |
| ------ | ---------------------------------- | ---------- |
| 1      | Production 인벤토리 + service 식별 | 25분       |
| 2      | E2~E6 builder 풀 구현              | 90분       |
| 3      | E2~E6 신규 coach service           | 60분       |
| 4      | builder + service 단위 테스트      | 30분       |
| 5      | 24 케이스 매트릭스 실행            | 45분       |
| 6      | 회귀 + IDENTICAL                   | 15분       |
| 7      | classifier 갱신                    | 15분       |
| 8      | KPI + 종결 보고                    | 25분       |
| **합** |                                    | **~5h 5m** |

---

## §9. 작업 시작 신호

```bash
git status  # slice11 브랜치, clean
git log -1 --oneline  # 4789cc8 확인
pytest portfolio/ tests/ -x -q 2>&1 | tail -5  # 559 passed
echo "API key: $([ -n "$ANTHROPIC_API_KEY" ] && echo YES || echo NO)"

# Part 1/2/3 자산 검증
python -c "
from portfolio.schemas.commentary_input import COMMENTARY_INPUT_CLASSES
from portfolio.schemas.commentary_output import COMMENTARY_OUTPUT_CLASSES
from portfolio.services.coach.prompt_builder import PROMPT_BUILDER_CLASSES
from portfolio.services.coach.e1_service import run_e1_coach
assert len(COMMENTARY_INPUT_CLASSES) == 6
assert len(COMMENTARY_OUTPUT_CLASSES) == 6
assert len(PROMPT_BUILDER_CLASSES) == 6
print('자산 검증 PASS')
"
```

위 모든 명령 기대값 일치 시 Step 1 진입. **API_KEY 미설정 시 즉시 중단 보고** (Step 5 매트릭스 실행 불가).

---

**END OF INSTRUCTIONS**
