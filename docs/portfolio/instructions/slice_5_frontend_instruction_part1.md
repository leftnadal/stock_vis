# Slice 5 Part 1 작업 지시서 — E3 진입점 (preset 외삽 검증)

> 작성일: 2026-05-07
> 버전: v1.0
> 진입점: **E3 (지표 코멘트, MetricComment one-liner 자연어 생성)**
> 핵심 가치: ① 글쓰기 가설 5번째 외삽 검증 / ② preset 다양성 인터페이스 검증 / ③ 누적 비용 정합 부채 #γ1 정리
> Slice 4 Part 1 mirror 비율: ~95% (구조 동일, E3 schema·service·fixture 차이만 신규)

---

## §0. 참조 문서

| #   | 문서                                                                              | 용도                                               |
| --- | --------------------------------------------------------------------------------- | -------------------------------------------------- |
| 1   | `docs/portfolio/coach/slice4/slice4_part1_instructions.md`                        | mirror 대상 (~95%) — 모든 Step 구조의 1차 baseline |
| 2   | `docs/portfolio/coach/slice4/validation_report_slice4.md`                         | 회귀/비용/winner baseline                          |
| 3   | `docs/portfolio/coach/slice4/refactor_backlog_slice4.md`                          | 누적 백로그 → Slice 5 처리 추적                    |
| 4   | `docs/portfolio/coach/slice4/slice4_decisions.md` 부록 A·B·G                      | 누적 결정 표 + 잔존 부채                           |
| 5   | (이번 세션 산출) `slice5_decision_record.md` 6건 결정 + 2건 신규 백로그           | 본 지시서 결정 근거                                |
| 6   | (이번 세션 회수) Slice 5 자료 5종 보고                                            | 환경 차이 자동 변환 baseline                       |
| 7   | `portfolio/prompts/e3/` 4파일 (e3_builder, input_builder, instructions, examples) | E3 스켈레톤 (D-3)                                  |
| 8   | `portfolio/schemas/llm_outputs.py:65-87`                                          | MetricComment / MetricComments 스키마              |
| 9   | `portfolio/metrics/definitions/presets.py` (107줄) + `preset_metrics.py` (263줄)  | 12 preset 정의                                     |
| 10  | `portfolio/metrics/definitions/metrics.py`                                        | 57 지표 단일 진실 소스                             |

---

## §1. 목표

### §1.1 슬라이스 핵심 가치 (4종)

1. **E3 (지표 코멘트) 진입점 신규 구현**
   - 입력: `AnalysisContext` (preset_id + holdings + metrics)
   - 출력: `MetricComments {comments: list[MetricComment{metric_id, one_liner}]}` (one_liner 10~300자)
   - 진입점 본질: 종목별 metric 5단계 결과(excellent/good/moderate/weak/critical)를 1줄 자연어 코멘트로 변환
   - default provider = **haiku** (글쓰기 가설 4/4 정착 외삽, Slice 1·3·4 누적)

2. **글쓰기 가설 5번째 외삽 검증**
   - 누적: S1 E1 / S3 E2 / S4 E6 = haiku winner (4/4, 반례 S2 E5는 추출이라 일관)
   - S5 E3 = **5번째 글쓰기 진입점**. winner=haiku이면 5/5 정착 → preset 외삽 위험 해소
   - 반례 (winner=sonnet) 시 = 4/5 재평가 + Slice 6+ 추가 글쓰기 진입점 검증 필요 (케이스 F 처리)

3. **preset 다양성 인터페이스 검증**
   - 5 preset / 5 카테고리 균등 cover (자료 #2 기반):
     - **value**: buffett_quality_value
     - **growth**: garp (baseline, Slice 1 garp_large 재활용)
     - **income**: dividend_growth (Slice 1 dividend fixture 재활용 가능)
     - **factor**: quality_factor
     - **special**: contrarian
   - 검증 가설: "GARP에서 학습한 평가 차원이 다른 preset에 그대로 외삽 가능한가?"
   - 측정: insight 차원 그룹차 (Slice 3 0.67~0.83 경계 위험 재발 여부)

4. **누적 비용 정합 부채 #γ1 처리 (Step 0)**
   - 광의 단일 정책 채택
   - validation_report 1·2·3 §5 갱신 + `COST_POLICY.md` 신설
   - Slice 5 종결 시 누적 비용 baseline = $0.585 (광의)에서 시작

### §1.2 비범위 (Phase 2 / Slice 6+ 위임)

| 항목                                      | 위임                                                     |
| ----------------------------------------- | -------------------------------------------------------- |
| LLMClient.complete system 인자 추가       | 백로그 #19 (PS 2.0), Slice 6 Step 9 슬롯 후보            |
| concentrated_portfolio portfolio-level E3 | 백로그 #20 (PS 2.0), Slice 6+ 별도 슬라이스              |
| E2 keyword_match 룰 보완 (#10)            | Slice 6+ 이연                                            |
| E6 자동 평가 룰 정교화 (#15)              | Slice 5 Part 2 Step 8 회고 시 자연 흡수 가능성 별도 검토 |
| 분석 엔진 정량 재계산 (#12)               | Phase 2 위임                                             |
| #β1 (token 한국어 휴리스틱 보정)          | Slice 5 Part 2 Step 7 자연 검증 (결함 재발 시만 처리)    |

---

## §2. 사전 조건

### §2.1 git / 회귀 baseline

| 항목                            | 값                                                    |
| ------------------------------- | ----------------------------------------------------- |
| 브랜치                          | `portfolio`                                           |
| Slice 4 종결 단독 회귀          | **173 passed**                                        |
| origin rebase 합산 표시         | 296 passed (marketpulse v2 +123 포함)                 |
| Slice 5 Part 1 진입 시 baseline | 단독 173 passed                                       |
| Slice 5 Part 1 종결 예상 회귀   | **~210 passed** (단독, +37 가정 — Slice 4 +37 mirror) |

### §2.2 환경 차이 자동 변환 5건

자료 회수 #1~#5 발견 사항 기반.

| #   | 자료 발견                                                            | 자동 변환 처리                                                                                                          |
| --- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1   | `build_e3_prompt` → `(system, user)` tuple 반환 (Slice 1·3·4와 다름) | service에서 `system + "\n\n" + user` concat → 단일 prompt로 LLMClient.complete 호출 (백로그 #19로 영구 처리는 Slice 6+) |
| 2   | preset 12개 (concentrated_portfolio 추가)                            | concentrated 제외 11 preset 중 5 preset 선정 (5 카테고리 cover). concentrated는 백로그 #20                              |
| 3   | 지표 57개 (Type 1=39 / Type 2=13 / Type 3=5)                         | E3 build_e3_input은 산출 결과(MetricResult)만 받음 → 영향 없음                                                          |
| 4   | DIMENSION_LOOKUP 1줄 추가로 자동 dispatch                            | `_main_unified()` 변경 0줄 (Part 2 Step 8 e3 entry 추가만, 본 Part 1과 무관)                                            |
| 5   | cost_log.json 없음 (CostGuard 메모리만)                              | validation_report §5/§6을 사후 비용 로그로 채택. Step 0 #γ1에서 baseline 표 갱신                                        |

### §2.3 누적 부채 / 백로그 사전 등록

| #   | 부채                                         | Step 0 처리          | Step 7 자연 검증                                              |
| --- | -------------------------------------------- | -------------------- | ------------------------------------------------------------- |
| #γ1 | 누적 비용 광의/협의 정합 회복                | ✓ 본 Step 0에서 처리 | —                                                             |
| #β1 | token 한국어 휴리스틱 +50% 편차              | —                    | Part 2 Step 7에서 자연 검증, 재발 시 chars/3 → chars/2.5 보정 |
| #18 | score_step8_e5.py argparse --entrypoint 인자 | —                    | Slice 6+ 이연 (회귀 영향 0)                                   |

---

## §3. 스코프

### §3.1 Part 1 포함 (Step 0~5)

| Step            | 작업                                                                    | LLM 호출 | 회귀 변화 (예상)         |
| --------------- | ----------------------------------------------------------------------- | -------- | ------------------------ |
| 0               | #γ1 누적 비용 정합 부채 처리 (30분 한도)                                | 0        | 0                        |
| 1               | E3 schema (E3Request) + Mock 함수 (`_mock_text_e3`)                     | 0        | +5                       |
| 2               | service (`portfolio/services/e3_metric_comment.py`)                     | 0        | 0                        |
| 3               | view + URL (`coach_e3_metric_comment`, `/api/coach/e3/metric-comment/`) | 0        | 0                        |
| 4               | Mock 통합 테스트 (service 8 + view 9 = 17)                              | 0        | +17                      |
| 5               | hybrid 7 fixture (baseline GARP 3 + focused 4) + 단위 테스트 +12        | 0        | +15                      |
| **Part 1 합계** | —                                                                       | **0**    | **+37** (단독 173 → 210) |

### §3.2 Part 2 위임 (다음 세션)

- Step 6: Smoke (1 LLM call, fixture 선정 = baseline 1)
- Step 7: Token budget 측정 + `token_budgets.py` e3 등록 + #β1 자연 검증
- Step 8: 14 calls 회고 (haiku 7 + sonnet 7) + 그룹 분석 + e3 DIMENSION_LOOKUP entry
- Step 9: 백로그 #11 일반화 (`format_metrics_to_str` 통합 유틸, 30분 한도)
- validation_report (광의 단일 정책)
- refactor_backlog (Slice 4 → Slice 5 처리 결과)

### §3.3 Part 1 비포함 (재차 명시)

- Slice 1·3·4 IDENTICAL hash 검증 (Part 2 Step 9 도입 시점)
- 백로그 #19 (LLMClient system 인자), #20 (concentrated portfolio-level E3), #10 (E2 keyword_match)
- 분석 엔진 정량 재계산 (Phase 2)

---

## §4. Step별 작업

### §4.0 Step 0 — #γ1 누적 비용 정합 부채 처리 (30분 한도)

#### 4.0.1 작업 4건

**작업 A: validation_report_slice1.md §6 끝에 1줄 추가**

기존 §6 (Cost Guard) 표 다음에 다음 1줄 추가:

```markdown
> 광의 누적 비용 = $0.137 (Step 6 1차 + Step 6 재실행 + Step 8 + Gemini 진단). 이후 슬라이스도 광의 단일 정책 채택 (Slice 5 Step 0 #γ1 부채 처리, 2026-05-07).
```

**작업 B: validation_report_slice2.md §5 끝에 1줄 추가**

```markdown
> 광의 누적 비용 = $0.327 (S1 광의 $0.137 + S2 광의 $0.190, S2 1차 손실 14건 비용 포함). 광의 단일 정책 채택 (Slice 5 Step 0).
```

**작업 C: validation_report_slice3.md §5 끝에 1줄 추가**

```markdown
> 광의 누적 비용 = $0.428 (S2 광의 $0.327 + S3 $0.101). 광의 단일 정책 채택 (Slice 5 Step 0).
```

**작업 D: docs/portfolio/coach/COST_POLICY.md 신설**

전체 내용 (~25줄):

```markdown
# 누적 비용 산출 정책

> 작성: Slice 5 Step 0 (#γ1 부채 처리, 2026-05-07)
> 적용 대상: Slice 5 이후 모든 validation_report

## 단일 산출 정책

누적 비용은 **광의** 단일 정책으로 산출한다. 메인 4스텝(Step 6/7/8/9) 외 모든 LLM 호출 비용을 포함:

- 진단 호출 (Gemini 진단 등)
- 재실행 호출 (smoke 재실행 등)
- 1차 손실 호출 (Step 8 실패 후 재시도 시 1차 비용)
- 백로그 처리 호출 (Step 9 슬롯 작업 호출 등)

## 누적 baseline (Slice 1~4 광의)

| 시점         | 광의 누적 |
| ------------ | --------- |
| Slice 1 종결 | $0.137    |
| Slice 2 종결 | $0.327    |
| Slice 3 종결 | $0.428    |
| Slice 4 종결 | $0.585    |

## validation_report §5/§6 형식

- 표 제목: "광의 누적 비용"
- 메인 4스텝 비용은 _주석_(괄호)으로 1줄 표기 — 별도 표로 분리하지 않음
- 협의/광의 분리 표기 금지 (정의 일관성)

## 변경 이력

| 일자       | 변경                                                         |
| ---------- | ------------------------------------------------------------ |
| 2026-05-07 | 초안 작성. Slice 5 Step 0 #γ1 부채 처리. 광의 단일 정책 채택 |
```

#### 4.0.2 한도 초과 처리

- 30분 초과 시: 작업 D (COST_POLICY.md)는 _반드시_ 작성, 작업 A·B·C는 부분 적용 가능 (다음 슬라이스로 이연)
- Step 0 종결 시 시간 보고: `Step 0 종료 시각: __:__:__ (소요 __분)`

#### 4.0.3 LLM 호출 / 회귀 영향

- LLM 호출: **0건**
- 회귀 영향: **0건** (문서 수정만)

#### 4.0.4 검증

- 작업 A·B·C: 1줄 추가 후 git diff 확인 (변경 라인 수 = 슬라이스당 2~3줄)
- 작업 D: COST_POLICY.md 존재 + 누적 baseline 표 4개 행 작성

---

### §4.1 Step 1 — E3 schema + Mock 함수

Slice 4 Step 1 mirror ~85%. 차이: schema 본질(Request 구조), Mock 응답 형식.

#### 4.1.1 신규 파일/수정

| 파일                                | 작업   | 형태                                                                           |
| ----------------------------------- | ------ | ------------------------------------------------------------------------------ |
| `portfolio/schemas/llm_inputs.py`   | 수정   | `E3Request` 추가                                                               |
| `portfolio/schemas/llm_outputs.py`  | 확인만 | `MetricComment`/`MetricComments` 이미 정의 (라인 65-87, extra="forbid" 적용 ✓) |
| `portfolio/llm/mocks.py`            | 수정   | `_mock_text_e3` 추가                                                           |
| `portfolio/tests/test_e3_schema.py` | 신규   | 단위 테스트 5건                                                                |

#### 4.1.2 E3Request 정의 (E2Request mirror)

```python
# portfolio/schemas/llm_inputs.py에 추가

class E3Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_context: dict = Field(
        ...,
        description="AnalysisContext.model_dump() 결과. preset_id + holdings + metric_results 포함",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="LLM 호출 추적용 세션 ID",
    )

    @model_validator(mode="after")
    def validate_analysis_context(self) -> "E3Request":
        required_keys = {"preset_id", "holdings"}
        missing = required_keys - set(self.analysis_context.keys())
        if missing:
            raise ValueError(f"analysis_context missing required keys: {missing}")
        return self
```

#### 4.1.3 \_mock_text_e3 정의

```python
# portfolio/llm/mocks.py에 추가

def _mock_text_e3(prompt: str) -> str:
    """E3 진입점 Mock 응답.

    MetricComments schema 통과 JSON 반환.
    one_liner는 10~300자 범위 충족.
    metric_id는 prompt에서 추출 (없으면 default 'pe_ratio').
    """
    import re
    metric_ids = re.findall(r'"metric_id"\s*:\s*"([^"]+)"', prompt)
    if not metric_ids:
        metric_ids = ["pe_ratio", "roic", "revenue_growth"]

    comments = []
    for mid in metric_ids[:5]:  # 최대 5개
        comments.append({
            "metric_id": mid,
            "one_liner": (
                f"{mid} 지표는 동종 업계 대비 양호한 수준입니다. "
                "추가적인 모니터링이 권장됩니다."
            ),
        })

    return json.dumps({"comments": comments}, ensure_ascii=False)
```

#### 4.1.4 단위 테스트 5건

| #   | 테스트명                                | 검증                                                                |
| --- | --------------------------------------- | ------------------------------------------------------------------- |
| 1   | `test_e3_request_valid`                 | preset_id + holdings 포함 시 model_validate 성공                    |
| 2   | `test_e3_request_extra_forbidden`       | 추가 키 시 ValidationError                                          |
| 3   | `test_e3_request_missing_preset_id`     | preset_id 누락 시 ValidationError ("missing required keys")         |
| 4   | `test_mock_text_e3_returns_valid_json`  | `_mock_text_e3()` 출력이 `MetricComments` schema 통과               |
| 5   | `test_mock_text_e3_extracts_metric_ids` | prompt에 `"metric_id": "roic"` 포함 시 출력의 metric_id에 roic 포함 |

#### 4.1.5 LLM 호출 / 회귀 영향

- LLM 호출: 0건
- 회귀 영향: **+5** (단독 173 → 178)

---

### §4.2 Step 2 — service (e3_metric_comment.py)

Slice 4 Step 2 mirror ~80%. 차이: build_e3_prompt wrapper (system+user concat 처리).

#### 4.2.1 신규 파일

| 파일                                      | 작업 | 형태                                                       |
| ----------------------------------------- | ---- | ---------------------------------------------------------- |
| `portfolio/services/e3_metric_comment.py` | 신규 | `run_e3` + `build_e3_prompt` wrapper + `parse_e3_response` |

#### 4.2.2 핵심 인터페이스

```python
# portfolio/services/e3_metric_comment.py

from portfolio.prompts.e3.e3_builder import build_e3_prompt as _raw_build_e3_prompt
from portfolio.schemas.llm_inputs import E3Request
from portfolio.schemas.llm_outputs import MetricComments
from portfolio.schemas.analysis_context import AnalysisContext
from portfolio.llm.client import LLMClient
from portfolio.llm.parsers import strip_json_fences


def build_e3_prompt(context: AnalysisContext, prompt_version: str = "1.1") -> str:
    """LLMClient.complete 단일 prompt wrapper.

    raw build_e3_prompt가 (system, user) tuple 반환 → concat으로 단일 str 변환.
    Slice 6+ 백로그 #19 (LLMClient system 인자 추가) 처리 시 본 wrapper 제거.
    """
    system, user = _raw_build_e3_prompt(context, prompt_version=prompt_version)
    return f"{system}\n\n{user}"


def parse_e3_response(raw_text: str) -> MetricComments:
    """LLM raw text → MetricComments parse.

    JSON 펜스 제거 후 model_validate.
    """
    cleaned = strip_json_fences(raw_text)
    data = json.loads(cleaned)
    return MetricComments.model_validate(data)


def run_e3(
    request: E3Request,
    client: LLMClient,
    prompt_version: str = "1.1",
) -> tuple[MetricComments, dict]:
    """E3 진입점 메인 함수.

    Returns:
        (parsed_response, llm_metadata) 튜플.
        metadata: provider/model/latency_ms/input_tokens/output_tokens/cost_usd/fallback_from
    """
    context = AnalysisContext.model_validate(request.analysis_context)
    prompt = build_e3_prompt(context, prompt_version=prompt_version)
    raw_text, metadata = client.complete(
        prompt=prompt,
        max_tokens=1500,  # 1차 추정, Part 2 Step 7에서 실측 후 갱신
        entrypoint="e3",
    )
    parsed = parse_e3_response(raw_text)
    return parsed, metadata
```

#### 4.2.3 주의 사항 (자료 회수 발견 #1)

- `_raw_build_e3_prompt`이 `(system, user)` tuple 반환 → wrapper에서 concat
- 영구 처리는 Slice 6+ 백로그 #19 (LLMClient.complete system 인자 추가)
- 본 Slice 5에서 wrapper로 격리 → 백로그 #19 처리 시 wrapper 제거 + LLMClient 직접 system/user 전달로 전환

#### 4.2.4 max_tokens 1차 추정 = 1500

- 1차 추정 근거: Slice 4 #β1 교훈 (한국어 휴리스틱 +50% 편차) → 보수적 추정
- E3 출력 = 5 metric × one_liner 300자 max = 1,500자 ≈ 한국어 1,200 토큰 (×1.3 char/token 보수)
- Part 2 Step 7에서 P90 실측 후 `token_budgets.py["e3"]` 등록값 확정

#### 4.2.5 LLM 호출 / 회귀 영향

- LLM 호출: 0건
- 회귀 영향: 0건 (Step 4에서 통합 테스트로 검증)

---

### §4.3 Step 3 — view + URL

Slice 4 Step 3 mirror ~95%. 인터페이스 동일 (csrf_exempt + POST + JSON 응답 + 429 매핑).

#### 4.3.1 신규/수정 파일

| 파일                 | 작업 | 형태                                   |
| -------------------- | ---- | -------------------------------------- |
| `portfolio/views.py` | 수정 | `coach_e3_metric_comment` 추가         |
| `portfolio/urls.py`  | 수정 | `/api/coach/e3/metric-comment/` 라우팅 |

#### 4.3.2 view 정의

```python
# portfolio/views.py에 추가

@csrf_exempt
@require_POST
def coach_e3_metric_comment(request: HttpRequest) -> JsonResponse:
    """E3 진입점 view.

    Slice 1·3·4 동일 패턴 mirror.
    429 (CostGuard 한도 초과) 매핑 유지.
    """
    try:
        body = json.loads(request.body)
        e3_request = E3Request.model_validate(body)
    except (json.JSONDecodeError, ValidationError) as e:
        return JsonResponse({"error": "invalid_request", "detail": str(e)}, status=400)

    client = LLMClient()
    try:
        parsed, metadata = run_e3(e3_request, client=client)
    except CostGuardLimitExceeded:
        return JsonResponse({"error": "cost_guard_limit_exceeded"}, status=429)
    except Exception as e:
        return JsonResponse({"error": "llm_failure", "detail": str(e)}, status=500)

    return JsonResponse({
        "comments": [c.model_dump() for c in parsed.comments],
        "metadata": metadata,
    })
```

#### 4.3.3 URL 라우팅

```python
# portfolio/urls.py에 추가

path(
    "api/coach/e3/metric-comment/",
    views.coach_e3_metric_comment,
    name="coach_e3_metric_comment",
),
```

#### 4.3.4 LLM 호출 / 회귀 영향

- LLM 호출: 0건
- 회귀 영향: 0건 (Step 4에서 view 테스트로 검증)

---

### §4.4 Step 4 — Mock 통합 테스트

Slice 4 Step 4 mirror ~95%. 시나리오 5종 동일.

#### 4.4.1 신규 파일

| 파일                                 | 테스트 수 | 형태         |
| ------------------------------------ | --------- | ------------ |
| `portfolio/tests/test_e3_service.py` | 8         | service 단위 |
| `portfolio/tests/test_e3_view.py`    | 9         | view 통합    |

#### 4.4.2 service 테스트 8건

| #   | 테스트명                                 | 검증                                           |
| --- | ---------------------------------------- | ---------------------------------------------- |
| 1   | `test_run_e3_success_with_mock`          | Mock LLMClient → MetricComments 정상 parse     |
| 2   | `test_run_e3_returns_metadata`           | metadata에 provider/model/cost_usd 포함        |
| 3   | `test_build_e3_prompt_concat`            | wrapper가 system + "\n\n" + user 단일 str 반환 |
| 4   | `test_parse_e3_response_strips_fences`   | "`json\n{...}\n`" 형식도 parse 성공            |
| 5   | `test_parse_e3_response_invalid_json`    | parse 실패 시 JSONDecodeError raise            |
| 6   | `test_parse_e3_response_schema_mismatch` | comments 키 누락 시 ValidationError            |
| 7   | `test_run_e3_uses_haiku_default`         | LLMClient 호출 시 default provider="haiku"     |
| 8   | `test_run_e3_entrypoint_passed`          | LLMClient.complete에 entrypoint="e3" 전달      |

#### 4.4.3 view 테스트 9건

| #   | 테스트명                               | 검증                                                             |
| --- | -------------------------------------- | ---------------------------------------------------------------- |
| 1   | `test_view_post_success_with_mock`     | 200 + comments 응답                                              |
| 2   | `test_view_get_method_not_allowed`     | 405                                                              |
| 3   | `test_view_invalid_json_body`          | 400 + error="invalid_request"                                    |
| 4   | `test_view_missing_analysis_context`   | 400 (E3Request validation 실패)                                  |
| 5   | `test_view_extra_field_in_request`     | 400 (extra="forbid")                                             |
| 6   | `test_view_cost_guard_limit_429`       | CostGuardLimitExceeded → 429 + error="cost_guard_limit_exceeded" |
| 7   | `test_view_llm_failure_500`            | LLM 예외 → 500 + error="llm_failure"                             |
| 8   | `test_view_response_includes_metadata` | 응답 metadata 필드 존재                                          |
| 9   | `test_view_url_routing`                | reverse("coach_e3_metric_comment") 정상                          |

#### 4.4.4 Mock LLMClient mode

- Slice 4 동일 `mode="success" | "parse_fail" | "missing_field" | "cost_guard" | "llm_failure"` dict 매핑 활용
- 백로그 #7 (Mock mode dict 매핑) 자연 흡수 가능 — Slice 5에서 명시 정리는 안 함, Slice 6+ 이연

#### 4.4.5 LLM 호출 / 회귀 영향

- LLM 호출: 0건 (Mock 사용)
- 회귀 영향: **+17** (단독 178 → 195)

---

### §4.5 Step 5 — hybrid 7 fixture + 단위 테스트

Slice 4 Step 5 mirror ~70%. 차이: focused 4 preset 신규 (E6와 다른 preset 선정).

#### 4.5.1 fixture 구성

**baseline 3 (GARP, Slice 1 garp_large 재활용)**

| #   | fixture 이름                | preset | 재사용                                      | 비고                                                            |
| --- | --------------------------- | ------ | ------------------------------------------- | --------------------------------------------------------------- |
| 1   | `e3_baseline_garp_large`    | garp   | Slice 1 garp_large                          | 15 holdings, Core 5 + Sup 5 + Ctx 5 (E3 입력은 Core+Sup만 선택) |
| 2   | `e3_baseline_garp_medium`   | garp   | Slice 1 garp_medium                         | 8 holdings, Core 4 + Sup 3                                      |
| 3   | `e3_baseline_garp_dividend` | garp   | Slice 1 dividend fixture (income 일부 포함) | 5 holdings, dividend_yield 등                                   |

**focused 4 (preset 신규)**

| #   | fixture 이름                 | preset                | 카테고리 | holdings | 핵심 metric                                                |
| --- | ---------------------------- | --------------------- | -------- | -------- | ---------------------------------------------------------- |
| 4   | `e3_focused_buffett`         | buffett_quality_value | value    | 6~8      | roic, fcf_yield, debt_to_equity, gross_margin              |
| 5   | `e3_focused_dividend_growth` | dividend_growth       | income   | 5~7      | dividend_yield, dividend_growth_5y, payout_ratio           |
| 6   | `e3_focused_quality_factor`  | quality_factor        | factor   | 7~9      | roic, gross_margin, accrual_ratio                          |
| 7   | `e3_focused_contrarian`      | contrarian            | special  | 4~6      | pe_ratio (contrarian: higher_is_better override), pb_ratio |

#### 4.5.2 fixture 파일 위치

| 파일                                                        | 작업                                                                    |
| ----------------------------------------------------------- | ----------------------------------------------------------------------- |
| `portfolio/tests/fixtures/sample_metric_comment_context.py` | 신규. 7 fixture 함수 + Helper (`build_metric_results_for_fixture()` 등) |

#### 4.5.3 fixture 검증 단위 테스트 12건

| #   | 테스트명                                               | 검증                                                                  |
| --- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| 1   | `test_fixture_baseline_garp_large_15_holdings`         | 15 holdings + GARP preset_id                                          |
| 2   | `test_fixture_baseline_garp_medium_8_holdings`         | 8 holdings                                                            |
| 3   | `test_fixture_baseline_garp_dividend_5_holdings`       | 5 holdings + dividend 관련 metric 포함                                |
| 4   | `test_fixture_focused_buffett_value_category`          | preset_category="value" + roic 포함                                   |
| 5   | `test_fixture_focused_dividend_growth_income_category` | preset_category="income" + dividend_yield 포함                        |
| 6   | `test_fixture_focused_quality_factor_category`         | preset_category="factor"                                              |
| 7   | `test_fixture_focused_contrarian_special_category`     | preset_category="special" + pe_ratio direction_override 적용          |
| 8   | `test_all_fixtures_have_5_categories`                  | 7 fixture가 5 카테고리(value/growth/income/factor/special) 모두 cover |
| 9   | `test_fixture_metric_results_valid_level_tag`          | 모든 metric의 level_tag ∈ {excellent, good, moderate, weak, critical} |
| 10  | `test_fixture_percentile_in_range`                     | percentile ∈ [0, 1]                                                   |
| 11  | `test_fixture_round_trip_safe`                         | `_safe_write` round-trip 손실 0 (D4 가이드)                           |
| 12  | `test_baseline_focused_grouping`                       | baseline 3 + focused 4 = 7 (hybrid 비율 정합)                         |

#### 4.5.4 LLM 호출 / 회귀 영향

- LLM 호출: 0건
- 회귀 영향: **+15** (12 fixture 단위 + 3 helper, 단독 195 → 210)

#### 4.5.5 자료 회수 #2 활용

- 11 preset 검증: 자료 #2의 12 preset 중 concentrated 제외
- 5 카테고리 cover: 자료 #2 카테고리 분류(value 2/growth 2/income 2/factor 4/special 2) 기반
- preset_metrics 매핑: 자료 #2의 `get_metrics_for_tier(preset_id, tier)` helper 활용

---

## §5. 검증 지점

### §5.1 Step별 회귀 카운트 진행 표 (예상)

| 단계                                    | 추가 테스트 (단독) | 누적 (단독) | 비고                  |
| --------------------------------------- | ------------------ | ----------- | --------------------- |
| Slice 4 종결 baseline                   | —                  | 173         |                       |
| Step 0 (#γ1 부채 처리)                  | 0                  | 173         | 문서만                |
| Step 1 (E3 schema + Mock 함수)          | +5                 | 178         | E3Request 4 + Mock 1  |
| Step 2 (service)                        | 0                  | 178         | Step 4에서 통합 검증  |
| Step 3 (view + URL)                     | 0                  | 178         | Step 4에서 통합 검증  |
| Step 4 (Mock 통합 테스트)               | +17                | 195         | service 8 + view 9    |
| Step 5 (hybrid 7 fixture + 단위 테스트) | +15                | **210**     | fixture 12 + helper 3 |
| **Part 1 종결 예상**                    | —                  | **~210**    |                       |

목표: 단독 +37 (Slice 4 +37 mirror).

### §5.2 검증 판정 표

| #   | 검증 항목                                       | 임계                               | 자동/수동 |
| --- | ----------------------------------------------- | ---------------------------------- | --------- |
| 1   | Step 0 작업 4건 모두 적용                       | git diff에 4 파일 변경             | 자동      |
| 2   | COST_POLICY.md 신설 + 누적 baseline 표 4행      | 파일 존재 + 표 검증                | 자동      |
| 3   | E3Request extra="forbid" 적용                   | model_validate 실패 케이스         | 자동      |
| 4   | E3Request validator (preset_id + holdings 필수) | 누락 시 ValidationError            | 자동      |
| 5   | \_mock_text_e3 출력 schema 통과                 | MetricComments.model_validate 성공 | 자동      |
| 6   | build_e3_prompt wrapper concat 정상             | system + "\n\n" + user 형식        | 자동      |
| 7   | run_e3 default haiku 사용                       | LLMClient.complete 호출 인자 검증  | 자동      |
| 8   | view 200 + 4xx + 5xx 매핑                       | 9 시나리오 모두 통과               | 자동      |
| 9   | 7 fixture 5 카테고리 cover                      | preset_category 집합 = 5종         | 자동      |
| 10  | fixture 단위 테스트 12건                        | round-trip 손실 0                  | 자동      |
| 11  | 단독 회귀 +37 ±5                                | 210 ± 5 passed                     | 자동      |
| 12  | LLM 호출 0건 (Part 1 전체)                      | CostGuard records 0                | 자동      |
| 13  | git commit 분리 (Step 0~5 각각)                 | 6 commit                           | 수동      |

### §5.3 롤백 / 실패 시 처리

**케이스 A. Step 0 30분 한도 초과**

- COST_POLICY.md만 작성 + validation_report 갱신은 부분 적용
- 미완료 작업 = Slice 6 Step 0 부채로 이연 (백로그 신규 등록 불필요, COST_POLICY.md 정의 적용은 자동 진행)

**케이스 B. E3Request 모델 검증 실패 (Step 1)**

- 자료 회수 #1의 build_e3_prompt 시그니처와 충돌 시 발생
- 처리: `analysis_context: dict` 형태가 raw 정의와 다른지 확인 → 필요 시 `analysis_context: AnalysisContext` 직접 받는 형태로 schema 변경 결정 (사용자 에스컬레이션)

**케이스 C. \_mock_text_e3 schema 검증 실패 (Step 1)**

- one_liner min_length=10 또는 max_length=300 위반
- 처리: Mock 응답 길이 조정 (보수적으로 50~200자)

**케이스 D. build_e3_prompt wrapper 호출 실패 (Step 2)**

- raw build_e3_prompt 인자 시그니처가 자료 #1과 다름
- 처리: 자료 #1 인용된 시그니처(`context: AnalysisContext, prompt_version: str = "1.1"`) 검증 → 다르면 사용자 에스컬레이션

**케이스 E. fixture 작성 시 preset 매핑 실패 (Step 5)**

- 자료 #2의 `get_metrics_for_tier(preset_id, tier)` helper가 expected 결과 반환 안 함
- 처리: preset_metrics.py 263줄 직접 확인 → tier 매핑 수정 또는 fixture 단순화

**케이스 F. 회귀 +37 큰 편차 (±5 이상)**

- 단위 테스트 누락 또는 중복
- 처리: 누락 시 추가, 중복 시 통합. 케이스 F는 작업 차단 아님 (보고에 명시)

---

## §6. 권한 (Claude Code 균형 모드)

### §6.1 처방 영역 (반드시 지시서대로)

- E3Request 시그니처 (필드 + validator)
- build_e3_prompt wrapper concat 형식 (`system + "\n\n" + user`)
- run_e3 메타데이터 dict 키 (provider/model/latency_ms/input_tokens/output_tokens/cost_usd/fallback_from)
- view 응답 형식 ({"comments": [...], "metadata": {...}})
- view 4xx/5xx 매핑 (400/405/429/500)
- fixture 5 preset 선정 (garp/buffett/dividend_growth/quality_factor/contrarian) — 다른 preset 선정 금지
- Step 0 작업 4건 (validation_report 1·2·3 + COST_POLICY.md) — 다른 형식 변경 금지
- 글쓰기 가설 default = haiku

### §6.2 위임 영역 (Claude Code 판단)

- 변수명, 헬퍼 함수 분리, 로깅 형식
- Mock 응답 자연어 어조 (one_liner 본문)
- fixture holdings 종목 선정 (실제 종목 코드, 단 5 카테고리 cover만 보장)
- 단위 테스트 함수명 세부 표현
- COST_POLICY.md 변경 이력 표 형식 (단, 정책 정의는 처방대로)

### §6.3 금지 행위 (8건)

| #   | 금지                                                 | 사유                               |
| --- | ---------------------------------------------------- | ---------------------------------- |
| 1   | Slice 1·3·4 산출물(`step8_*_scored.json`) 변경       | Part 2 Step 9 IDENTICAL 보장       |
| 2   | `score_step8.py` 변경 (Part 2에서만 e3 entry 추가)   | Part 1 스코프 외                   |
| 3   | `token_budgets.py` 수정 (Part 2 Step 7)              | Part 1 스코프 외                   |
| 4   | LLM 실호출                                           | Part 1 LLM 호출 0건 정책           |
| 5   | concentrated_portfolio fixture 작성                  | 백로그 #20 위임                    |
| 6   | LLMClient.complete 시그니처 변경                     | 백로그 #19 위임, Slice 6+          |
| 7   | 분석 엔진 정량 재계산                                | Phase 2 위임                       |
| 8   | 광의/협의 분리 표기 (validation_report 신규 작성 시) | COST_POLICY.md 광의 단일 정책 위반 |

### §6.4 안전장치

- 작업 진행 중 환경 차이 발견 시(자료 #1~#5와 다른 사항): 즉시 사용자 에스컬레이션 (Claude Code report-only 패턴)
- Step 0 30분 한도 도달 시: 작업 D 완료 우선, 나머지 부분 적용
- 회귀 +37 ±5 편차 시: §5.3 케이스 F 처리

---

## §7. 산출물

### §7.1 신규 파일 (12건)

| 파일                                                                   | Step                                      |
| ---------------------------------------------------------------------- | ----------------------------------------- |
| `docs/portfolio/coach/COST_POLICY.md`                                  | 0                                         |
| `portfolio/services/e3_metric_comment.py`                              | 2                                         |
| `portfolio/tests/test_e3_schema.py`                                    | 1                                         |
| `portfolio/tests/test_e3_service.py`                                   | 4                                         |
| `portfolio/tests/test_e3_view.py`                                      | 4                                         |
| `portfolio/tests/fixtures/sample_metric_comment_context.py`            | 5                                         |
| `portfolio/tests/test_e3_fixture.py`                                   | 5                                         |
| `docs/portfolio/coach/slice5/slice5_part1_instructions.md`             | (본 지시서, 진입 시점에 이미 존재)        |
| `docs/portfolio/coach/slice5/slice5_part1_report.md`                   | Part 1 종결 시                            |
| `docs/portfolio/coach/slice5/slice5_decisions.md`                      | Part 1 진입 시 (이번 세션 결정 기록 보존) |
| `docs/portfolio/coach/slice5/decisions_record.md`                      | (선택) 이번 세션 6건 결정 보존            |
| (Part 2에서) `docs/portfolio/coach/slice5/validation_report_slice5.md` | Part 2                                    |

### §7.2 수정 파일 (5건)

| 파일                                                           | Step | 변경 내용                            |
| -------------------------------------------------------------- | ---- | ------------------------------------ |
| `portfolio/schemas/llm_inputs.py`                              | 1    | E3Request 추가                       |
| `portfolio/llm/mocks.py`                                       | 1    | \_mock_text_e3 추가                  |
| `portfolio/views.py`                                           | 3    | coach_e3_metric_comment 추가         |
| `portfolio/urls.py`                                            | 3    | /api/coach/e3/metric-comment/ 라우팅 |
| `docs/portfolio/coach/slice1/validation_report_slice1.md` (§6) | 0    | 광의 1줄 추가                        |
| `docs/portfolio/coach/slice2/validation_report_slice2.md` (§5) | 0    | 광의 1줄 추가                        |
| `docs/portfolio/coach/slice3/validation_report_slice3.md` (§5) | 0    | 광의 1줄 추가                        |

(실제 7건 중 §0 산출 4건 + 코드 4건 = 8건이지만 schemas/llm_inputs.py + mocks.py + views.py + urls.py = 4건이라 합계 12 신규 + 5 수정 = 17건 실제 변경)

### §7.3 git commit 정책

| Step | commit 메시지 형식                                                                             |
| ---- | ---------------------------------------------------------------------------------------------- |
| 0    | `[slice5] Step 0: #γ1 cost policy + validation_report 1·2·3 광의 누적 1줄 추가`                |
| 1    | `[slice5] Step 1: E3Request schema + _mock_text_e3 + 단위 테스트 5건`                          |
| 2    | `[slice5] Step 2: e3_metric_comment service (build_e3_prompt wrapper concat + run_e3 + parse)` |
| 3    | `[slice5] Step 3: coach_e3_metric_comment view + URL`                                          |
| 4    | `[slice5] Step 4: E3 Mock 통합 테스트 (service 8 + view 9)`                                    |
| 5    | `[slice5] Step 5: hybrid 7 fixture (GARP 3 재활용 + 4 preset focused) + 단위 테스트 12건`      |

총 6 commit, Step 단위 분리.

---

## §8. 완료 보고 포맷

Part 1 종결 시 사용자에게 다음 형식으로 보고:

```
# Slice 5 Part 1 완료 보고

## §A. 환경 정합성
- git branch: portfolio
- git commit 6건 (Step 0~5 분리)
- 회귀: 단독 173 → <단독 종결> passed (+<변화>, 목표 +37 ±5)
- LLM 호출: 0건 (Part 1 정책)
- 누적 비용 변화: 0 (Part 1 LLM 호출 없음)

## §B. Step별 진척

| Step | 산출물 | 회귀 변화 | 시간 |
|---|---|---|---|
| 0 | COST_POLICY.md + report 3 광의 1줄 | 0 | <분> |
| 1 | E3Request + _mock_text_e3 + 단위 5 | +5 | <분> |
| 2 | e3_metric_comment service | 0 | <분> |
| 3 | view + URL | 0 | <분> |
| 4 | Mock 통합 테스트 (service 8 + view 9) | +17 | <분> |
| 5 | hybrid 7 fixture + 단위 12 | +15 | <분> |

## §C. 신규/수정 파일 카운트
- 신규: <12 ± 1>
- 수정: <5 ± 1>
- 총 변경 라인 수: <X>

## §D. 환경 차이 자동 변환 결과
| # | 자료 발견 | 적용 결과 |
|---|---|---|
| 1 | (system, user) tuple → concat | <적용 / 케이스 발동> |
| 2 | 12 preset → concentrated 제외 11 | <적용> |
| 3 | 53 → 57 지표 | <영향 없음 확인> |
| 4 | DIMENSION_LOOKUP 1줄 dispatch | (Part 1 무관, Part 2에서 적용) |
| 5 | cost_log.json 없음 | Step 0에서 baseline 갱신 적용 |

## §E. 케이스 A~F 발생 여부
- A (Step 0 30분 한도 초과): 발생 / 미발생
- B (E3Request 모델 검증 실패): 발생 / 미발생
- C (_mock_text_e3 schema 검증 실패): 발생 / 미발생
- D (build_e3_prompt wrapper 호출 실패): 발생 / 미발생
- E (fixture preset 매핑 실패): 발생 / 미발생
- F (회귀 +37 ±5 큰 편차): 발생 / 미발생

## §F. Step 0 #γ1 처리 결과
- 작업 A (slice1 §6): 적용 / 부분 / 미적용
- 작업 B (slice2 §5): 적용 / 부분 / 미적용
- 작업 C (slice3 §5): 적용 / 부분 / 미적용
- 작업 D (COST_POLICY.md): 적용 / 미적용
- Step 0 소요시간: <분> / 30분

## §G. Slice 5 KPI (Part 1 시점)
- [ ] 회귀: 단독 +37 ±5
- [ ] LLM 호출: 0건
- [ ] 5 카테고리 cover (value/growth/income/factor/special): 7 fixture 검증
- [ ] D4 round-trip 위반: 0건
- [ ] git commit 분리: 6건
- [ ] Step 0 #γ1 처리: 4 작업 모두 적용 (또는 부분 사유)

## §H. Part 2 진입 준비도
- E3 service/view/Mock 인프라: <준비 완료 / 부분>
- hybrid 7 fixture: <준비 완료>
- Part 2 Step 6 진입 가능 여부: <Yes / 차단 사유>

## §I. Part 2 시점 결정 보류 항목
- Part 2 Step 7 token budget e3 1차 추정 = 1500 (한국어 보수 추정)
- Part 2 Step 8 winner 가설: haiku (글쓰기 가설 5번째 외삽) — Step 8 회고 결과로 검증
- Part 2 Step 9 슬롯: #11 일반화 (`format_metrics_to_str`) — 30분 한도
```

---

## §9. 변경 이력

### §9.1 본 지시서 변경 이력

| 일자       | 버전 | 변경 사항                                        |
| ---------- | ---- | ------------------------------------------------ |
| 2026-05-07 | v1.0 | 초안. Slice 5 Part 1 Step 0~5 + §5~§9 + 부록 A~F |

### §9.2 Slice 5 결정 변경 이력 (이번 세션 6건)

| 결정                      | 채택                                                         | 가중합    | 근거                                |
| ------------------------- | ------------------------------------------------------------ | --------- | ----------------------------------- |
| Q1+N3: 매트릭스 + fixture | hybrid 7 (GARP3 재활용 + 4 preset focused), 5 카테고리 cover | 4.40      | Slice 4 mirror + 통계 안정          |
| Q5: Step 9 슬롯           | #11 일반화 (`format_metrics_to_str`)                         | 4.80      | 자료 권장 + Slice 5 직결            |
| N1: (system, user) tuple  | service concat + 백로그 #19 등록                             | 4.55      | 회귀 위험 0 + 영구 가치 단계적 회복 |
| Q3: 평가 차원             | naturalness + insight + completeness 자동                    | 4.65      | 글쓰기 가설 5번째 외삽 정합성       |
| Q6: #γ1 처리              | 광의 단일 정책 + COST_POLICY.md 신설                         | 5.00      | 자료 권장 단일 진실 소스            |
| Q4-N2: preset 처리        | 11 preset (concentrated 제외) + 백로그 #20                   | 단순 확인 | 자료 권장 직접 채택                 |

---

## 부록 A — Slice 5 종결 결정 표 (Part 1 시점, Part 2 종결 시 갱신)

| 항목                       | 값 (Part 1 시점)                                                             | 값 (Part 2 종결 시 갱신)              |
| -------------------------- | ---------------------------------------------------------------------------- | ------------------------------------- |
| 진입점                     | E3 (지표 코멘트, preset 외삽 검증)                                           | (동일)                                |
| Default provider           | haiku (글쓰기 가설 4/4 정착 외삽)                                            | (Step 8 winner로 검증)                |
| Fixture 전략               | hybrid 7 (GARP 3 재활용 + 4 preset focused)                                  | (동일)                                |
| 평가 차원                  | naturalness / insight (manual) + completeness (자동)                         | (동일)                                |
| 5 preset 선정              | garp / buffett_quality_value / dividend_growth / quality_factor / contrarian | (동일)                                |
| 5 카테고리 cover           | value / growth / income / factor / special                                   | (동일)                                |
| Step 8 매트릭스            | 7 × 2 = 14 (haiku 7 + sonnet 7)                                              | (동일)                                |
| Step 9 슬롯 작업           | #11 metrics_table 일반화 (`format_metrics_to_str`)                           | (Part 2 종결 시 완료/이연 명시)       |
| Step 0 부채 처리           | #γ1 누적 비용 정합 (광의 단일 정책)                                          | (Part 1 종결 시 완료/부분 명시)       |
| (system, user) tuple 처리  | service concat (백로그 #19 Slice 6+)                                         | (동일)                                |
| concentrated_portfolio     | 제외 (백로그 #20 Slice 6+)                                                   | (동일)                                |
| Step 8 winner              | (Part 2 종결 시 기재)                                                        | <haiku / sonnet>                      |
| Lex pass rate              | (Part 2 종결 시 기재)                                                        | <haiku N/7 / sonnet N/7>              |
| 글쓰기 가설 외삽 검증      | (Part 2 종결 시 기재)                                                        | <5/5 정착 / 4/5 재평가>               |
| Token budget e3 등록값     | 1차 추정 1500                                                                | (Part 2 Step 7 P90 × 1.5 round-up)    |
| 누적 호출 (Slice 5)        | (Part 2 종결 시 기재)                                                        | <X> / 50                              |
| 누적 비용 (Slice 5 광의)   | (Part 2 종결 시 기재)                                                        | $<Y>                                  |
| 누적 비용 (Slice 1~5 광의) | $0.585 (Part 1 진입 시)                                                      | $0.585 + $<Slice 5>                   |
| 케이스 A~F 발동            | —                                                                            | (Part 2 종결 시 기재)                 |
| Slice 1·3·4 IDENTICAL hash | —                                                                            | (Part 2 Step 9 시점)                  |
| Slice 6 진입 결정          | Slice 5 종결 회고 시                                                         | (사용자 결정 — E4 또는 preset 일반화) |

---

## 부록 B — Slice 5 백로그 통합 표

### B.1 Slice 4 → Slice 5 처리 예정 (Part 2 슬롯)

| #   | 항목                                           | PS  | Slice 4 등록 | Slice 5 처리 예정              |
| --- | ---------------------------------------------- | --- | ------------ | ------------------------------ |
| 11  | metrics_table 일반화 (`format_metrics_to_str`) | 1.5 | 이연         | **Slice 5 Part 2 Step 9 슬롯** |

### B.2 Slice 5 Part 1 진입 시 신규 백로그 (이번 세션 결정)

| #   | 항목                                                             | PS  | 트리거                                             | 위임                     |
| --- | ---------------------------------------------------------------- | --- | -------------------------------------------------- | ------------------------ |
| 19  | LLMClient.complete system 인자 추가 + 4슬라이스 호출처 일괄 정비 | 2.0 | E3 (system, user) tuple → service concat 임시 처리 | Slice 6 Step 9 슬롯 후보 |
| 20  | concentrated_portfolio portfolio-level E3 별도 슬라이스          | 2.0 | Slice 5에서 concentrated 제외                      | Slice 6+ 별도 슬라이스   |

### B.3 Slice 6+ 이연 (Slice 4 신규 + Slice 4 잔여)

| #   | 항목                                            | PS  | 출처                                                                     |
| --- | ----------------------------------------------- | --- | ------------------------------------------------------------------------ |
| 5   | TOKEN_BUDGET LLMClient 통합 (잔여)              | 2.0 | Slice 3 신규                                                             |
| 6   | Step 8 raw output CSV 옵션                      | 1.0 | Slice 3 신규                                                             |
| 7   | Mock LLMClient mode dict 매핑                   | 1.0 | Slice 3 신규 (Slice 5 Step 4에서 자연 흡수 가능성, 명시 정리는 Slice 6+) |
| 8   | LLMClient entrypoint 인자 + 가드레일            | 2.5 | Slice 3 신규 (Slice 6 Step 9 슬롯 #19와 경합)                            |
| 10  | E2 keyword_match 룰 보완                        | 1.5 | Slice 3 신규 (E2 한정)                                                   |
| 13  | run*step6*\*.py 5종 latency 일괄 16,000ms 상향  | 1.0 | Slice 4 신규                                                             |
| 14  | score_step8.py CLI 인자 확장 (--input/--output) | 1.5 | Slice 4 신규                                                             |
| 15  | E6 자동 평가 룰 정교화                          | 1.5 | Slice 4 신규 (Slice 5 Part 2 Step 8 회고 시 자연 흡수 검토)              |
| 16  | E6 latency 24s 초과 sonnet 패턴 분석            | 1.0 | Slice 4 신규                                                             |
| 17  | auto_eval_e6.py 패턴 일반화                     | 2.0 | Slice 4 신규 (#10 E2와 통합)                                             |
| 18  | score_step8_e5.py argparse --entrypoint 인자    | 1.0 | Slice 4 검증 단계 발견                                                   |

### B.4 Phase 2 위임

| #   | 항목                | PS  | 출처                                         |
| --- | ------------------- | --- | -------------------------------------------- |
| 12  | E6 분석 엔진 재계산 | 5.0 | Slice 4 신규, 슬라이스 분리 가능성 별도 검토 |

### B.5 누적 백로그 합

- Slice 5 진입 시점: ~13건 → Slice 5 신규 #19, #20 추가 → ~15건
- Slice 5 Part 2 처리 (#11) → Slice 5 종결 시 ~14건
- PS 합 ~21.5 (대형 항목 #12 PS 5.0 제외 시 ~16.5)

---

## 부록 C — 회귀 카운트 진행 표 (Part 1 + Part 2 통합 예상)

| 단계                  | 추가 (단독) | 누적 (단독) | 비고                    |
| --------------------- | ----------- | ----------- | ----------------------- |
| Slice 4 종결          | —           | 173         | baseline                |
| Slice 5 Part 1 Step 0 | 0           | 173         | #γ1 부채                |
| Part 1 Step 1         | +5          | 178         | E3Request + Mock        |
| Part 1 Step 2         | 0           | 178         | service                 |
| Part 1 Step 3         | 0           | 178         | view + url              |
| Part 1 Step 4         | +17         | 195         | Mock 통합               |
| Part 1 Step 5         | +15         | **210**     | hybrid 7 fixture + 단위 |
| **Part 1 종결**       | —           | **210**     | (예상)                  |
| Part 2 Step 6         | 0           | 210         | smoke                   |
| Part 2 Step 7         | +3          | 213         | token_budgets 단위      |
| Part 2 Step 8         | 0           | 213         | 회고                    |
| Part 2 Step 9         | +5~10       | **218~223** | #11 일반화 단위         |
| **Slice 5 종결 예상** | —           | **218~223** |                         |

목표 Slice 5 종결 단독 +45~50 (Slice 1·2·3·4 누적 173 → ~220).

---

## 부록 D — 분석 엔진 의존성 회피 일관 적용 (Slice 1~5)

E3는 Slice 1·3·4와 동일하게 **분석 엔진 의존성 회피** 정책 일관 유지:

| 항목                                         | Slice 5 E3 적용                                                                  |
| -------------------------------------------- | -------------------------------------------------------------------------------- |
| E3 schema (Request/Response)                 | analysis_context: dict (이미 산출된 MetricResult만 받음, 정량 재계산 없음)       |
| build_e3_input                               | 자료 #1: Core + Supporting 지표만 (Context 제외, Wallet 배제) — 산출 결과 조회만 |
| Mock 응답 (`_mock_text_e3`)                  | 자연어 코멘트만 (one_liner 10~300자)                                             |
| fixture (`sample_metric_comment_context.py`) | 7개 모두 산출된 MetricResult 형태 (정량 재계산 미산출)                           |
| Part 2 Step 6/8 LLM 호출                     | LLM이 자연어 코멘트만 — 수치 검증 없음                                           |
| score_step8.py e3 entry                      | naturalness + insight + completeness 만 평가 (정량 차원 미사용)                  |

Phase 2 분석 엔진 슬라이스 추가 시:

- 백로그 #12 (E6 분석 엔진 재계산, PS 5.0)에 E3도 포함 가능 — preset별 외삽 모니터링 차원 추가
- 단독 슬라이스로 분리 가능 (자료 #4의 DIMENSION_LOOKUP 1줄 추가 패턴 활용)

---

## 부록 E — Slice 4 → Slice 5 mirror 비율 (Part 1)

| 항목                                                        | mirror 대상                                   | 비율                                 |
| ----------------------------------------------------------- | --------------------------------------------- | ------------------------------------ |
| Schema 추가 위치 (`portfolio/schemas/llm_inputs.py`)        | Slice 1·2·3·4                                 | 100%                                 |
| Service 인터페이스 (run*\*, build*_*prompt, parse*_)        | Slice 4 E6                                    | 90% (build\_\*\_prompt wrapper 차이) |
| View 인터페이스 (csrf_exempt + POST + JSON 응답 + 429 매핑) | Slice 1·2·3·4                                 | 100%                                 |
| Hybrid fixture (baseline + focused)                         | Slice 4 E6                                    | 100% (3 + 4 비율 동일)               |
| baseline 재활용 (Slice 1 자산)                              | Slice 4 (Slice 2 자산 재활용 패턴)            | 100% (GARP 3 재활용)                 |
| Mock LLMClient mode                                         | Slice 4                                       | 100%                                 |
| Step 0 30분 한도 부채 처리                                  | Slice 5 신규 패턴 (이전 슬라이스 Step 0 정착) | 신규                                 |

전체 Part 1 mirror 비율: **~95%** (Step 0 신규 + (system, user) wrapper 차이만 위임 영역).

자연어 / 결정 근거 / Mock 응답 본문은 위임.

---

## 부록 F — Slice 6 진입 결정 사전 안내 (Slice 5 종결 시 입력)

Slice 5 종결 회고 시 사용자 결정 자료. 본 부록은 frame만 제시, 정량 비교는 Slice 5 catalyst 충전 후 본격 분석.

### F.1 Slice 6 진입점 후보 비교 (frame)

| 후보                                                | 사전 등록 근거                         | 의존성                | 인지부하  | Slice 5 catalyst 충전 항목                                  |
| --------------------------------------------------- | -------------------------------------- | --------------------- | --------- | ----------------------------------------------------------- |
| **F.1.a E4 (대화 Q&A Tier 1~3)**                    | Coach 핵심 가치 + Phase 2 product 시연 | Tier 다층 (높음)      | 매우 높음 | Slice 5 글쓰기 가설 5/5 정착 시 Tier 2~3 default haiku 안전 |
| **F.1.b preset 일반화 (스코어링 엔진 일반화)**      | preset 인터페이스 검증 결과 활용       | 단독 (낮음)           | 중간      | Slice 5 5 preset 외삽 결과                                  |
| **F.1.c concentrated_portfolio E3 portfolio-level** | 백로그 #20 (PS 2.0)                    | 단독                  | 중간      | Slice 5 E3 패턴 정착                                        |
| **F.1.d LLMClient system 인자 통합**                | 백로그 #19 (PS 2.0)                    | 4슬라이스 호출처 정비 | 낮음      | 단독 슬라이스로는 너무 작음 — Step 9 슬롯에 적합            |

### F.2 Slice 6 진입점 결정 영향 자료

- **글쓰기 가설 5번째 외삽 검증 결과** (Slice 5 Part 2 Step 8 winner)
  - 5/5 정착 → E4 진입 안전 (Tier 2~3 default haiku)
  - 4/5 재평가 → 추가 글쓰기 진입점 검증 (preset 일반화 우선)
- **5 preset 외삽 insight 그룹차** (Slice 5 Part 2 Step 8 그룹 분석)
  - 그룹차 ≤ 0.50 → preset 일반화 안전
  - 그룹차 > 0.50 (Slice 3 위험 재발) → preset 일반화 보류, E4 우선

### F.3 Slice 6 Step 9 슬롯 후보 (백로그 ~14건 중)

| #   | 항목                                    | PS  | 자연 흡수 가능성                          |
| --- | --------------------------------------- | --- | ----------------------------------------- |
| 19  | LLMClient.complete system 인자 추가     | 2.0 | 슬라이스 6 진입점 따라 변동               |
| 8   | LLMClient entrypoint 인자 + 가드레일    | 2.5 | High                                      |
| 17  | auto_eval_e6.py 패턴 일반화 (E2와 통합) | 2.0 | E4 진입 시 자연 흡수                      |
| 5   | TOKEN_BUDGET LLMClient 통합 잔여        | 2.0 | Medium                                    |
| 14  | score_step8.py CLI 인자 확장            | 1.5 | High                                      |
| 15  | E6 자동 평가 룰 정교화                  | 1.5 | Slice 5 Part 2 Step 8 자연 흡수 시 closed |

### F.4 Slice 6 사전 결정 보존 권장 (slice6_decisions.md)

```markdown
# slice6_decisions.md

> 작성일: (Slice 5 종결 시점)

## 진입점 결정

- 1순위 후보: <E4 / preset 일반화 / concentrated E3>
- 근거: <Slice 5 winner / 그룹차 / Phase 2 가치>

## 진입점별 사전 결정

- E4 채택 시:
  - Tier 1~3 fixture 신규 인프라
  - default provider: Tier 1 추출=sonnet / Tier 2~3 글쓰기=haiku
  - Step 9 슬롯: #19 또는 #8
- preset 일반화 채택 시:
  - 스코어링 엔진 일반화 작업
  - Step 9 슬롯: #14 또는 #5
- concentrated E3 채택 시:
  - portfolio-level commentary schema 변경
  - Step 9 슬롯: #19

## 누적 결정 (Slice 1~5 보존)

- (Slice 1~5 결정 표 통합 — slice5_decisions.md 누적 결정 표 그대로)
```

### F.5 Slice 6 Step 0 부채 후보

- (Slice 5 종결 시점에서 잔여 부채 정리) — 매 슬라이스 Step 0 표준 패턴

---

## 부록 G — Step 0 #γ1 작업 명세 (확장)

본 부록은 Slice 5 Step 0의 4 작업을 정확한 형식으로 보존. 작업 진행 중 참조.

### G.1 작업 A: validation_report_slice1.md §6 끝 1줄 추가

**위치**: §6 (Cost Guard) 표 다음, §7 시작 전.

**추가 내용**:

```markdown
> **광의 누적 비용** = $0.137 (Step 6 1차 $0.0152 + Step 6 재실행 $0.0153 + Step 8 $0.1064 + Gemini 진단 ~$0.0005). 광의 단일 정책 채택 (Slice 5 Step 0 #γ1 부채 처리, 2026-05-07).
```

### G.2 작업 B: validation_report_slice2.md §5 끝 1줄 추가

**추가 내용**:

```markdown
> **광의 누적 비용** = $0.327 (Slice 1 광의 $0.137 + Slice 2 광의 $0.190). Slice 2 광의 = Step 6 $0.00135 + Step 8 1차 손실 14건 ~$0.04 + Step 8 2차 $0.0404 + Gemini 진단 ~$0.005 + Slice 1 진입 시 ~$0.10 보정. 광의 단일 정책 채택.
```

### G.3 작업 C: validation_report_slice3.md §5 끝 1줄 추가

**추가 내용**:

```markdown
> **광의 누적 비용** = $0.428 (Slice 2 광의 $0.327 + Slice 3 $0.101). 광의 단일 정책 채택.
```

### G.4 작업 D: COST_POLICY.md 신설

§4.0.1에 명시한 ~25줄 내용. 위치: `docs/portfolio/coach/COST_POLICY.md`.

### G.5 검증 체크리스트

| #   | 검증                                                                                                                                                                 |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | git diff에 4 파일 변경 확인                                                                                                                                          |
| 2   | COST_POLICY.md 누적 baseline 표 4행 ($0.137, $0.327, $0.428, $0.585)                                                                                                 |
| 3   | Slice 4 validation_report는 _변경 없음_ (광의 단일 정책 이미 부분 적용 — 단 협의/광의 분리 표기는 Slice 6+ Slice 4 보고서 갱신 시 정리, 본 Slice 5 Step 0 스코프 외) |
| 4   | Step 0 30분 한도 준수                                                                                                                                                |

---
