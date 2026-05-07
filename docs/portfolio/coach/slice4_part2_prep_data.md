# Slice 4 Part 2 진입 준비 데이터

> 작성일: 2026-05-07
> 작성자: 클로드 코드
> 용도: Slice 4 Part 2 (Step 6~9) 지시서 작성 입력
> 범위: read-only 데이터 수집
> Part 1 종결 baseline: 160 passed

---

## 1. 환경 차이 5건 정확한 인용 (Part 1 보고 기반)

### 1.1 LLMBudgetExceededError exception 클래스

`portfolio/llm/exceptions.py`에서 해당 클래스 정의 그대로 인용:

```python
# portfolio/llm/exceptions.py (라인 32~33)
class LLMBudgetExceededError(LLMError):
    """비용 가드 임계 도달 → raise (폴백 안 함)."""
```

LLMError 계층 구조 (전체 클래스 이름, 라인 12~33):
- `LLMError` (베이스, line 12)
- `LLMRateLimitError(LLMError)` (line 16) — 폴백 트리거
- `LLMTimeoutError(LLMError)` (line 20) — 폴백 트리거
- `LLMAuthError(LLMError)` (line 24) — raise
- `LLMInvalidPromptError(LLMError)` (line 28) — raise
- **`LLMBudgetExceededError(LLMError)` (line 32) — raise (폴백 안 함)**

### 1.2 AdjustmentItem schema 정확한 필드

`portfolio/schemas/llm.py`의 AdjustmentItem 클래스 전체 인용:

```python
# portfolio/schemas/llm.py (라인 37~92)
AdjustmentAction = Literal["increase", "decrease", "remove", "add", "info_only"]


class AdjustmentItem(BaseModel):
    """
    단일 종목 조정. delta_weight는 음수(축소) / 양수(확대) / 0(정보용).

    I2 검증: action ↔ delta_weight ↔ target_weight 명확한 모순 거름.
    LLM 자유도 보장 위해 borderline 케이스는 통과시킴.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=10)
    action: AdjustmentAction
    delta_weight: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="포트폴리오 비중 변화량 (-1.0 ~ +1.0). action=info_only 시 None 또는 0.",
    )
    target_weight: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="명시적 목표 비중. delta_weight과 동시 지정 가능.",
    )
    reason_quote: str = Field(
        ...,
        max_length=300,
        description="사용자 자연어 명령에서 이 조정을 추출한 근거 부분 인용. 추측/의역 금지.",
    )

    @model_validator(mode="after")
    def _check_action_consistency(self) -> "AdjustmentItem":
        """action과 delta/target 명확한 모순만 거름."""
        # ... (action별 일관성 검증, 라인 70~92)
```

특히 다음 항목 명시:
- `ticker` 필드 타입: `str` (min_length=1, max_length=10) — **필수**
- `action` 필드 타입 (Literal 값들): `Literal["increase", "decrease", "remove", "add", "info_only"]` — `AdjustmentAction` 타입 alias로 분리 — **필수**
- `reason_quote` 필수 여부: **필수** (`Field(..., max_length=300)`)
- `delta_weight`: `Optional[float]` (ge=-1.0, le=1.0) — 선택
- `target_weight`: `Optional[float]` (ge=0.0, le=1.0) — 선택
- 추가 검증: `model_validator(mode="after")`로 action↔delta/target 일관성 강제 (decrease+positive delta 거절, remove+nonzero target 거절 등)

### 1.3 MockLLMClient 정확한 시그니처

`portfolio/llm/mocks.py`의 MockLLMClient 클래스 `__init__` + `complete` 인용:

```python
# portfolio/llm/mocks.py (라인 82~125)
class MockLLMClient:
    """LLMClient 호환 Mock. 모드별로 폴백/에러/가드를 결정론적으로 시뮬레이션.

    Args:
        mode: 폴백/에러/가드 시나리오 (5개)
        text_strategy: 진입점별 응답 텍스트 (default "e1", Slice 1 호환)
    """

    def __init__(
        self,
        mode: MockMode = "normal",
        text_strategy: str = "e1",
    ) -> None:
        if text_strategy not in _MOCK_TEXT_STRATEGIES:
            raise ValueError(
                f"Unknown text_strategy: {text_strategy!r}. "
                f"Available: {list(_MOCK_TEXT_STRATEGIES)}"
            )
        self.mode: MockMode = mode
        self._call_count: int = 0
        self._text_fn: Callable[[str], str] = _MOCK_TEXT_STRATEGIES[text_strategy]

    def complete(
        self,
        prompt: str,
        provider: Literal["gemini", "anthropic"] = "gemini",
        max_tokens: int = 2000,  # noqa: ARG002
        model: str | None = None,  # LLMClient 시그니처 호환  # noqa: ARG002
    ) -> LLMResponse:
        self._call_count += 1
        # ... (mode별 동작 분기)
```

주요 매개변수 의미:
- `mode`: `Literal["normal", "rate_limit_first", "timeout_first", "auth_error", "budget_exceeded"]` — 5개 시나리오. default `"normal"`. `MockMode` Literal로 정의 (라인 73~79).
- `text_strategy`: 진입점별 응답 JSON 생성기 키. default `"e1"`. `_MOCK_TEXT_STRATEGIES` dict 등록 키만 허용.
- `complete()` 매개변수: `prompt`, `provider` (default `"gemini"`), `max_tokens=2000`, `model=None` — LLMClient.complete와 시그니처 호환.

text_strategy로 등록된 진입점 dict (`_MOCK_TEXT_STRATEGIES` 라인 66~71):

```python
_MOCK_TEXT_STRATEGIES: dict[str, Callable[[str], str]] = {
    "e1": _mock_text_e1,
    "e5": _mock_text_e5,
    "e2": _mock_text_e2,
    "e6": _mock_text_e6,  # Slice 4 Part 1 Step 4 등록
}
```

→ **e1, e5, e2, e6 모두 등록 완료**.

### 1.4 View 패턴 — 429 응답 정확한 형식

`portfolio/views.py`의 coach_e6_comparison 함수 전체 인용 (라인 183~241):

```python
# portfolio/views.py (라인 183~241)
@csrf_exempt
@require_POST
def coach_e6_comparison(request: HttpRequest) -> JsonResponse:
    """
    POST /api/coach/e6/comparison/?provider=haiku

    body (JSON): {"analysis_context": {...}, "adjustments": [...], "user_intent": "..."}
    provider 옵션: haiku (기본 — D2.B 글쓰기) | sonnet | anthropic | gemini.

    응답:
      200 — {"response": E6ComparisonResponse, "metadata": LLMResponse.metadata_dict()}
      400 — invalid body or invalid provider
      429 — budget exceeded
      500 — LLM 호출 실패 / 응답 schema 불일치
    """
    provider = request.GET.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return JsonResponse(
            {"error": "invalid_provider", "detail": f"{provider!r} not in {list(_VALID_PROVIDERS)}"},
            status=400,
        )

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": f"json parse error: {exc}"},
            status=400,
        )

    try:
        e6_request = E6Request.model_validate(body)
    except ValidationError as exc:
        return JsonResponse(
            {"error": "invalid_request", "detail": str(exc)[:500]},
            status=400,
        )

    try:
        result = run_e6(e6_request, provider=provider)
    except LLMBudgetExceededError as exc:
        return JsonResponse(
            {"error": "budget_exceeded", "detail": str(exc)}, status=429
        )
    except LLMError as exc:
        return JsonResponse(
            {"error": "llm_invocation_failed", "detail": str(exc)[:300]},
            status=500,
        )
    except ValidationError as exc:
        return JsonResponse(
            {"error": "llm_response_schema_mismatch", "detail": str(exc)[:500]},
            status=500,
        )

    return JsonResponse(result, status=200, json_dumps_params={"ensure_ascii": False})
```

LLMBudgetExceededError → 429 응답 매핑 패턴 (핵심 줄, 라인 226~229):

```python
    except LLMBudgetExceededError as exc:
        return JsonResponse(
            {"error": "budget_exceeded", "detail": str(exc)}, status=429
        )
```

> **데코레이터 차이**: 지시서 가정 `@require_http_methods(["POST"])` ↔ 실제 `@require_POST` (Django 단축 데코레이터). 동일 효과.
> **에러 응답 형식 차이**: 지시서 가정 `{"ok": false, "error": "...", "code": "..."}` ↔ 실제 `{"error": "<code>", "detail": "<msg>"}` (기존 e1/e5/e2 패턴 mirror).

### 1.5 URL prefix /api/coach/ 구성

`config/urls.py`의 portfolio 등록 인용 (라인 48):

```python
# config/urls.py (라인 48)
    # Portfolio Coach (slice 1: E1+GARP)
    path('api/', include('portfolio.urls')),
```

`portfolio/urls.py`의 coach_e6 path 등록 인용 (라인 14~18):

```python
# portfolio/urls.py (라인 14~18)
    path(
        "coach/e6/comparison/",
        views.coach_e6_comparison,
        name="coach_e6_comparison",
    ),
```

최종 E6 진입점 URL: **`/api/coach/e6/comparison/`** (`api/` + `coach/e6/comparison/`. `api/v1/`이 아니라 `api/`만 prepend — 기존 e1/e5/e2와 일관)

> 다른 앱들은 `api/v1/users/`, `api/v1/stocks/` 형식이지만 portfolio는 의도적으로 `api/`만 사용 (Slice 1 결정 보존).

---

## 2. E6 prompt 토큰 추정 (Part 2 Step 7 입력)

### 2.1 build_e6_prompt 함수 인용

`portfolio/services/e6_comparison.py`의 build_e6_prompt 함수 (라인 70~117):

```python
# portfolio/services/e6_comparison.py (라인 70~117)
def build_e6_prompt(request: E6Request) -> str:
    """E6 prompt 조립.

    구조:
      1. 역할 + 작업 정의 (정량 재계산 금지)
      2. 원본 포트폴리오 요약 (holdings + 분석 요약)
      3. 조정 명령 리스트 + 사용자 발화 (있으면)
      4. JSON schema 출력 명세 (E6ComparisonResponse 미러)
    """
    ctx = request.analysis_context
    holdings = ctx.get("holdings", []) or []
    holdings_str = (
        format_holdings_summary(holdings) if holdings else "(보유 종목 없음)"
    )
    analysis_one_liner = format_analysis_summary(ctx, max_chars=200)
    preset_id = ctx.get("preset_id", "unknown")
    adjustments_block = _format_adjustments_block(request.adjustments)
    user_intent_block = (
        f'\n사용자 발화: "{request.user_intent}"' if request.user_intent else ""
    )

    return f"""당신은 한국 개인 투자자를 위한 포트폴리오 비교 코치입니다. 사용자가 원본 포트폴리오에 다음 조정을 적용하려 합니다. 당신의 역할은 *정량 재계산 없이* 변경 전후를 자연어로 비교 해설하는 것입니다.

## 프리셋
{preset_id}

## 원본 포트폴리오
보유: {holdings_str}
요약: {analysis_one_liner}

## 조정 명령
{adjustments_block}{user_intent_block}

## 출력 요구
다음 JSON schema로만 응답하세요. JSON 객체만 반환하며, 마크다운 코드 펜스나 추가 설명을 절대 포함하지 마세요.

{{...schema spec...}}

## 규칙
1. key_changes는 1~5개. aspect는 5종 ...
"""
```

### 2.2 7 fixture에 대한 prompt 길이 추정 (offline 계산)

실제 측정 출력 그대로 인용 (사용 명령은 fixture 함수명/메타 키가 실제와 다름 — 본 점검에서 정정):

```bash
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from portfolio.tests.fixtures.sample_comparison_context import ALL_FIXTURES
from portfolio.schemas.llm import E6Request
from portfolio.services.e6_comparison import build_e6_prompt

for name, fn in ALL_FIXTURES.items():
    fx = fn()
    payload = {'analysis_context': fx['analysis_context'], 'adjustments': fx['adjustments']}
    if fx.get('user_intent'):
        payload['user_intent'] = fx['user_intent']
    req = E6Request.model_validate(payload)
    prompt = build_e6_prompt(req)
    print(f'{fx[\"fixture_id\"]}: chars={len(prompt)}, est_tokens={len(prompt)//3}')
"
```

| fixture_id | chars | est_tokens (chars // 3) |
|------------|-------|------------------------|
| e5_baseline_decrease | 999 | 333 |
| e5_baseline_multi | 1,017 | 339 |
| e5_baseline_remove | 1,073 | 357 |
| e6_focused_weight_rebalance | 1,005 | 335 |
| e6_focused_add_defensive | 1,056 | 352 |
| e6_focused_remove_underperformer | 1,037 | 345 |
| e6_focused_multi_aspect | 1,117 | 372 |

### 2.3 통계 산출

| 통계 | 값 |
|---|---|
| min | 333 tokens (e5_baseline_decrease) |
| max | 372 tokens (e6_focused_multi_aspect) |
| mean | 347.6 tokens |
| P90 | 372 tokens (n=7, ceil(0.9×7)-1=6 → 7번째) |

> 그룹별: baseline mean 343 (333~357), focused mean 351 (335~372). focused 그룹이 약간 길지만 차이 ~2.3% — 그룹 차이 작음(휴리스틱 기준).

### 2.4 budget 1차 권장 (P90 × 1.5 round-up)

- P90: **372** tokens
- × 1.5 = **558** tokens
- round-up to nearest 500: **1,000 tokens** (`ceil(558/500) × 500 = 2 × 500 = 1000`)

> 비교: e1=5000, e5=2000, e2=1500, **e6=1000** (1차 후보). E5/E2보다 작은 이유 — 보유종목과 조정명령만 prompt에 들어가고 분석 결과 평탄화가 가벼움. measure_e6_tokens.py로 anthropic count_tokens API 측정 후 확정.

### 2.5 expected output 토큰 추정

E6ComparisonResponse 6 필드 (`headline + before_summary + after_summary + key_changes + risk_assessment + closing_remarks`):

- Mock 응답 길이 (`_mock_text_e6` 기준): **chars=497, tokens=165**
- 실제 LLM 응답은 자연어 길이가 풍부할 수 있으므로 보수적 추정 ~600~800 tokens
- max_tokens 권장: **2,000 tokens** (LLMClient.complete default 그대로 사용 — 입력 372 + 출력 800 + 충분한 여유 + JSON 구조 오버헤드)

> 출력 필드 길이 한도(schema 기준): headline 120 + before/after 각 400 + key_changes 5×300=1500 + risk_assessment 300 + closing_remarks 300 = 최대 **3,020자**(약 1,000 tokens). max_tokens=2000은 schema 한도의 2배 — 여유 있음.

---

## 3. score 산식 통합 사전 점검 (Part 2 Step 9 #2 입력)

### 3.1 score_step8.py 현재 구조

`scripts/validation/score_step8.py` 핵심 구조 (라인 33~382, 총 383줄):

```python
# 1) DIMENSION_LOOKUP (라인 33~63) — slice4_prep_data.md §3.6 인용 그대로
DIMENSION_LOOKUP = {
    "e1": {
        "dim1": {"key": "naturalness", "manual_field": "naturalness"},
        "dim2": {"key": "insight", "manual_field": "insight"},
        "model_label_field": "label",
        "result_structure": "flat",
        "default_raw":   "docs/portfolio/coach/slice1/step8_3way_raw.json",
        "default_scored":"docs/portfolio/coach/slice1/step8_3way_scored.json",
        "weight": 0.5,
    },
    "e5": {
        # ... delegated_to: "scripts.validation.score_step8_e5"
    },
    "e2": {
        # ... additional_lex_check: "completeness_auto"
    },
    # Slice 4 Part 2 Step 9에서 "e6" entry 추가 예정
}

# 2) main entry (라인 114~228)
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrypoint", choices=list(DIMENSION_LOOKUP), default="e1")
    args = parser.parse_args()

    if args.entrypoint == "e5":
        from scripts.validation import score_step8_e5
        return score_step8_e5.main()
    if args.entrypoint == "e2":
        return _main_e2()

    # e1 (default) — Slice 1 산식 (인라인)
    config = DIMENSION_LOOKUP["e1"]
    raw_path = Path(config["default_raw"])
    scored_path = Path(config["default_scored"])
    # ... (lex 필터 → efficiency/fallback → label_means → write)
    return 0

# 3) e1 처리 — main() 내부 인라인 (별도 함수 아님)
# lexicographic_filter, efficiency_score, fallback_score 헬퍼 사용 (라인 70~111)

# 4) e2 처리 함수 (라인 231~378)
def _main_e2() -> int:
    """E2 (Slice 3) — e1 산식 + completeness_auto 1차 필터 추가.
       nested 구조 (judgments + metadata)를 flat으로 normalize 후 e1 산식 그대로 적용."""
    config = DIMENSION_LOOKUP["e2"]
    additional_check = config.get("additional_lex_check")  # "completeness_auto"

    # nested → flat normalize (라인 248~278)
    flat_results = []
    for r in raw["results"]:
        j = r.get("judgments", {})
        m = r.get("metadata", {}) or {}
        flat_results.append({
            "label": r["model_label"], "fixture": r["fixture"],
            "fixture_group": r["fixture_group"],
            "schema_pass": j.get("schema_pass"),
            "completeness_auto": j.get("completeness_auto"),
            "naturalness": j.get("naturalness_manual"),
            "insight": j.get("insight_manual"),
            "cost_usd": m.get("cost_usd"),
            "latency_ms": m.get("latency_ms"),
            "fallback_from": m.get("fallback_from"),
        })

    # E2 lex filter: e1 룰 + completeness_auto (라인 292~297)
    def _e2_lex(r: dict) -> bool:
        if not lexicographic_filter(r):  # e1 헬퍼 재사용
            return False
        if additional_check and not r.get(additional_check):
            return False
        return True

    # 이후 efficiency_score / fallback_score 호출 — e1과 동일 헬퍼

# 5) e5 delegation (라인 124~127)
if args.entrypoint == "e5":
    from scripts.validation import score_step8_e5
    return score_step8_e5.main()
```

### 3.2 e1 / e2 산식이 동일 구조인지 검증

| 항목 | e1 | e2 | mirror 가능? |
|------|-----|-----|--------------|
| dim1 / dim2 manual 평균 산출 | `naturalness` / `insight` 직접 (flat) | `naturalness_manual` / `insight_manual` (judgments 하위) → flat normalize 후 동일 키 | **Y** (normalize 단계 추가) |
| label_means / model_label_field 적용 | `r.get("label")` (flat) | `r["model_label"]` → flat에서 `"label"` 키로 변환 | **Y** |
| efficiency = sqrt(dim1 × dim2) / sqrt(cost × lat) | `efficiency_score(r)` (라인 80~85) | 동일 헬퍼 재사용 | **Y** (헬퍼 100% 공유) |
| weight 적용 | `"weight": 0.5` (DIMENSION_LOOKUP 메타, 현재 미사용) | 동일 | **Y** (둘 다 미사용) |
| `additional_lex_check` (`completeness_auto`) | 미적용 | 적용 (`_e2_lex` 내부) | (e6는 어느 쪽?) |

**e6는 어느 쪽?** — E6KeyChange aspect Literal + 6필드 모두 schema에 minimum length 강제 → schema 통과 자체가 completeness 보장. 단, E2처럼 `completeness_auto` 별도 필드를 두지 않고 schema_pass = completeness_auto. 즉 **e6는 e1 산식 그대로 적용 가능 (additional_lex_check 불필요)** 또는 e2 패턴 그대로 mirror하여 `completeness_auto = schema_pass` 동치 적용 가능.

판정 (1차):
- [x] **e1/e2/e6 한 main() 통합 가능** — completeness_auto는 entry 옵션 처리 (DIMENSION_LOOKUP의 `additional_lex_check` 활용)
- [x] **e1/e2/e6 산식이 거의 동일** — 차이는 dim 키 + result_structure(flat/nested) + additional_lex_check 유무. 한 main()에 흡수 가능
- [ ] 차이가 커서 e6도 delegation 필요

> **권장 통합 방향** (Step 9 #2 슬롯):
> - 공통 main: `_main_unified(entrypoint)` — flatten → lex_filter → efficiency/fallback → label_means → write
> - flatten은 `result_structure` 메타로 분기 (flat은 그대로 / nested는 e2 패턴 normalize)
> - lex_filter는 e1 베이스 + `additional_lex_check` 옵션 결합
> - e1/e2/e6 모두 통과. e5만 delegation 유지 (산식이 다름 — efficiency 분모 cost/lat 대신 임계 분리)

### 3.3 e5 delegation 정리 필요 사항

e5는 산식 차이로 별도 모듈 분리 유지:

- e5 delegation entry point: `scripts.validation.score_step8_e5.main()` (score_step8.py 라인 125~127)
- e5 delegation 호출 시그니처: `main() -> int` (CLI 인자 미공유, score_step8_e5가 자체 argparse 사용 안 함 — `default_raw`/`default_scored` 고정 경로)
- 통합 main()에서 e5 처리 분기 패턴: `if args.entrypoint == "e5": return score_step8_e5.main()` — 통합 후에도 그대로 유지. e5는 임계 분리 (`cost<=$0.020 AND latency<=5000ms`) + 정적 normalize라 e1/e2/e6와 산식 본질적 차이.

> Slice 4 Step 9 작업 범위에서 **e5 delegation은 변경 금지** — 통합은 e1/e2/e6 한 main()으로 한정.

### 3.4 Slice 1·2·3 산출물 round-trip 검증 명령

> **명령 형태 차이**: 지시서가 가정한 `--input` / `--output` flag는 score_step8.py에 미구현. 실제 인자는 `--entrypoint`만 존재 (라인 116~121). default 경로로 read/write. 따라서 round-trip은 git diff 검증으로 대체.

실제 동작 확인 명령:

```bash
# Slice 1 산출물 재실행 (default 경로 사용)
python -m scripts.validation.score_step8 --entrypoint e1
git diff --stat docs/portfolio/coach/slice1/step8_3way_scored.json

# Slice 3 산출물 재실행
python -m scripts.validation.score_step8 --entrypoint e2
git diff --stat docs/portfolio/coach/slice3/step8_2way_e2_scored.json
```

본 점검에서 실제 실행 결과:
- [x] 명령 1 (Slice 1 e1) 실행 가능: **Y** — `[Saved] docs/portfolio/coach/slice1/step8_3way_scored.json`, `winner=haiku, label_means=33.6847/13.8857/13.3782`. git diff 빈 출력 = **IDENTICAL** (회귀 0).
- [x] 명령 2 (Slice 3 e2) 실행 가능: **Y** — `[Saved] docs/portfolio/coach/slice3/step8_2way_e2_scored.json`, `winner=haiku, label_means=31.7107/12.8007`. git diff 빈 출력 = **IDENTICAL** (회귀 0).
- 차이 발견: **없음**. 두 산출물 모두 round-trip 통과.

> Slice 4 Step 9 통합 후에도 두 명령이 IDENTICAL을 유지해야 함 — Step 9 **회귀 KPI**.

---

## 4. 실 LLM 호출 환경 사전 점검 (Part 2 Step 6 입력)

### 4.1 .env 환경 변수

```bash
grep -E "^(ANTHROPIC_API_KEY|GEMINI_API_KEY|GOOGLE_API_KEY)=" .env | awk -F= '{print $1, "=set"}'
```

실제 출력:
```
ANTHROPIC_API_KEY =set
GEMINI_API_KEY =set
```

- `ANTHROPIC_API_KEY`: **set** — Slice 4 Step 6/8 haiku/sonnet 호출에 사용
- `GEMINI_API_KEY`: **set** — Slice 4는 2-way(haiku+sonnet)라 직접 호출 영향 적음. 단, default `provider="gemini"` 폴백 경로 검증 시 사용
- `GOOGLE_API_KEY`: 미등록 (GEMINI_API_KEY가 신 SDK key)

### 4.2 LLMClient provider 분기 패턴

`portfolio/llm/client.py`의 LLMClient.complete (라인 117~171):

```python
# portfolio/llm/client.py (라인 117~171)
def complete(
    self,
    prompt: str,
    provider: Literal["gemini", "anthropic"] = "gemini",
    max_tokens: int = 2000,
    model: str | None = None,
) -> LLMResponse:
    # 1. 비용 가드 (인스턴스 카운터 + 글로벌 CostGuard 양쪽 검증)
    if self._call_count >= self._budget_max:
        raise LLMBudgetExceededError(...)
    from portfolio.llm.cost_guard import CostGuard
    guard = CostGuard.get_instance()
    if guard.exceeded():
        raise LLMBudgetExceededError(f"Slice {guard.slice_id} budget exceeded: {guard.status()}")

    # 2. 1차 시도 + 1회 재시도
    try:
        response = self._call_with_retry(provider, prompt, max_tokens, model)
    except (LLMRateLimitError, LLMTimeoutError):
        # 3. 폴백 시도 (반대 provider, 모델은 폴백 측 기본값)
        fallback_provider = "anthropic" if provider == "gemini" else "gemini"
        response = self._call_with_retry(fallback_provider, prompt, max_tokens, model=None)
        response.fallback_from = provider

    # 4. 글로벌 CostGuard 누적 기록
    guard.record_call(cost_usd=response.cost_usd, model=response.model)
    return response
```

provider 4종 분기 동작 (`PROVIDER_KWARGS` `_llm_kwargs.py` 라인 22~27 + LLMClient `_call` 라인 197~212):
- `haiku` → `{"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL}` → `_call_anthropic("claude-haiku-4-5")` 직접 호출 (Gemini 폴백 안 함, anthropic→gemini 시도 시 같은 클래스 에러로 raise)
- `sonnet` → `{"provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL}` → `_call_anthropic("claude-sonnet-4-5")` 직접 호출
- `anthropic` → `{"provider": "anthropic", "model": None}` → default `ANTHROPIC_MODEL = "claude-sonnet-4-5"` (Sonnet)
- `gemini` → `{"provider": "gemini", "model": None}` → `_call_gemini("gemini-2.5-flash")`. Free tier RateLimit 발생 시 anthropic Sonnet으로 폴백 (Slice 1 9/9 폴백 사례 참조)

### 4.3 Slice 3 Step 6 smoke 호출 패턴 (Slice 4 mirror용)

```bash
ls scripts/validation/run_step6_*.py
```

출력:
- `run_step6_smoke.py` (Slice 1 — E1)
- `run_step6_e5_smoke.py` (Slice 2 — E5)
- `run_step6_e2_smoke.py` (Slice 3 — E2)

가장 최근(Slice 3 E2) `run_step6_e2_smoke.py` 핵심 부분 인용:

```python
# scripts/validation/run_step6_e2_smoke.py (라인 28~167 발췌)
init_django()
reset_for_slice("slice3", max_calls=50)

THRESHOLDS = {"cost_usd_max": 0.020, "latency_ms_max": 5000}
OUTPUT_PATH = Path("docs/portfolio/coach/slice3/step6_smoke_e2_output.json")


def _json_default(obj):
    if isinstance(obj, set): return sorted(obj)
    if isinstance(obj, (datetime, date)): return obj.isoformat()
    if isinstance(obj, Decimal): return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def _safe_write(path: Path, data: dict) -> None:
    """Write + read-back round-trip 검증."""
    serialized = json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)
    path.write_text(serialized, encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded is not None
    print(f"  [round-trip OK] {path}")


def main() -> int:
    fixture = ALL_FIXTURES["garp_tech"]()
    request = E2Request(analysis_context=fixture["analysis_context"])
    prompt = build_e2_prompt(request)

    client = LLMClient()
    resp = client.complete(prompt=prompt, provider="anthropic", model=ANTHROPIC_HAIKU_MODEL)

    # schema 검증 (completeness 자동)
    parsed = parse_e2_response(resp.text, preset_id=...)
    schema_pass = True
    completeness_auto = True

    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    output = {
        "step": "step6_e2_smoke",
        "fixture": "garp_tech",
        "fixture_group": fixture["fixture_group"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "raw_content": resp.text,
        "parsed": parsed.model_dump(),
        "metadata": resp.metadata_dict(),
        "judgments": {
            "schema_pass": schema_pass,
            "completeness_auto": completeness_auto,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "naturalness_manual": None,  # 사용자 수동 입력
            "insight_manual": None,
        },
        "thresholds": THRESHOLDS,
        "cost_guard_status": CostGuard.get_instance().status(),
    }
    _safe_write(OUTPUT_PATH, output)
    return 0 if (schema_pass and cost_pass and latency_pass) else 1
```

이 패턴이 Slice 4의 `run_step6_e6_smoke.py`로 mirror 됨. 핵심 차이:
- `run_e2` 인터페이스 → `run_e6` (build_e6_prompt + parse_e6_response 사용, request 입력에 adjustments 포함)
- fixture: `sample_diagnostic_context.ALL_FIXTURES["garp_tech"]` → `sample_comparison_context.ALL_FIXTURES["e5_baseline_decrease"]` (또는 `e6_focused_*`)
- **latency 임계: 5,000ms (Slice 3 값) → 16,000ms** (Slice 4 #9 백로그 적용 — §6 영향 파일 9개 중 run_step6_e6에만 적용)
- cost 임계: $0.020 USD (Slice 3 값 그대로 유지 — E2 출력 길이와 E6 출력 길이 비슷)
- `reset_for_slice("slice3")` → `reset_for_slice("slice4")`
- output path: `docs/portfolio/coach/slice4/step6_smoke_e6_output.json`

### 4.4 LLMBudgetExceededError → 429 → CostGuard 연동 사전 점검

CostGuard.record_call() 호출 시점 (`portfolio/llm/client.py` 라인 169~170):

```python
# portfolio/llm/client.py (라인 169~170)
# 4. 글로벌 CostGuard 누적 기록
guard.record_call(cost_usd=response.cost_usd, model=response.model)
return response
```

한도 초과 시 raise 패턴 (`portfolio/llm/cost_guard.py` 라인 84~88):

```python
# portfolio/llm/cost_guard.py (라인 84~88)
def record_call(self, cost_usd: float, model: str) -> None:
    if self.call_count >= self.max_calls:
        raise LLMBudgetExceededError(
            f"Slice {self.slice_id} budget exceeded: "
            f"{self.call_count}/{self.max_calls} calls"
        )
    self.call_count += 1
    # ...
```

호출 전 검증 (`client.py` 라인 149~154):

```python
guard = CostGuard.get_instance()
if guard.exceeded():
    raise LLMBudgetExceededError(
        f"Slice {guard.slice_id} budget exceeded: {guard.status()}"
    )
```

이중 가드 — 호출 전 `exceeded()` 체크 + 호출 후 `record_call()` 시 또 체크. 인스턴스 카운터(`self._call_count`)도 별도로 상한 체크.

budget 단위 테스트 카운트:

```bash
pytest portfolio/tests/ -k "budget" -v
```

출력: **10 passed** (budget 키워드 매칭 — `test_e1_garp_budget_exceeded` / `test_e2_view_budget_exceeded` / `test_e5_view_budget_exceeded` / `test_e6_view_budget_exceeded` / `test_budget_exceeded_raises` / `test_tier0_char_budget` / `test_token_budgets_defined` / `test_get_token_budget_known` / `test_get_token_budget_unknown` / `test_estimate_input_tokens_heuristic`)

---

## 5. Part 1 산출물 검증 (E6 인프라 사용 가능성)

### 5.1 sample_comparison_context.py 7 fixture 인터페이스 검증

```bash
python -c "
from portfolio.tests.fixtures.sample_comparison_context import (
    ALL_FIXTURES, get_all_fixtures, get_baseline_fixtures, get_focused_fixtures
)
print(f'ALL_FIXTURES count: {len(ALL_FIXTURES)}')
print(f'baseline count: {len(get_baseline_fixtures())}')
print(f'focused count: {len(get_focused_fixtures())}')
for name, fn in ALL_FIXTURES.items():
    fx = fn()
    print(f'{fx[\"fixture_id\"]}: group={fx[\"fixture_group\"]}, adjustments={len(fx[\"adjustments\"])}')
"
```

실제 출력:
```
ALL_FIXTURES count: 7
baseline count: 3
focused count: 4
e5_baseline_decrease: group=e5_baseline, adjustments=1
e5_baseline_multi: group=e5_baseline, adjustments=2
e5_baseline_remove: group=e5_baseline, adjustments=1
e6_focused_weight_rebalance: group=e6_focused, adjustments=2
e6_focused_add_defensive: group=e6_focused, adjustments=4
e6_focused_remove_underperformer: group=e6_focused, adjustments=3
e6_focused_multi_aspect: group=e6_focused, adjustments=5
```

기대 일치: ALL_FIXTURES count = 7, baseline count = 3, focused count = 4. **모두 일치**.

> **메타 키 차이**: 지시서 가정 `_fixture_id` / `_group` ↔ 실제 `fixture_id` / `fixture_group` (sample_diagnostic_context.py 패턴 mirror — 언더스코어 없음).
> **ALL_FIXTURES 타입 차이**: 지시서 가정 `list[Callable]` ↔ 실제 `dict[str, Callable]` (sample_diagnostic_context.py 패턴 mirror).
> **adjustments 카운트 분포**: 1/2/1 (baseline) + 2/4/3/5 (focused) — 다양성 충분 (P90 multi_aspect 5개로 가장 복잡).

### 5.2 test_e6_view.py 9 케이스 목록

```python
# portfolio/tests/test_e6_view.py
test_e6_view_normal
test_e6_view_invalid_provider
test_e6_view_invalid_body
test_e6_view_validation_error_empty_adjustments
test_e6_view_get_not_allowed
test_e6_view_rate_limit_first_fallback
test_e6_view_timeout_first_fallback
test_e6_view_auth_error_no_fallback
test_e6_view_budget_exceeded
```

fallback 4종 view 레벨 적용 패턴:
- 4종 모두 `MockLLMClient(mode=<scenario>, text_strategy="e6")` + `patch("portfolio.services.e6_comparison.LLMClient", return_value=mock)` — e5_view 동일 패턴 mirror
- RateLimit / Timeout: `provider=gemini`로 호출 → Gemini 모드 RateLimit/Timeout → LLMClient 내부 anthropic 폴백 → 200 + `fallback_from=gemini`
- AuthError: `provider=gemini` → Mock의 auth_error 모드는 mode 전체에 적용되어 폴백 안 함 → 500
- Budget: `provider=haiku` → Mock budget_exceeded 모드 → LLMBudgetExceededError → view에서 429 변환

### 5.3 test_e6_service.py 8 케이스 목록

```python
# portfolio/tests/test_e6_service.py
test_build_prompt_contains_holdings_and_preset
test_build_prompt_contains_adjustments_block
test_build_prompt_user_intent_optional
test_format_adjustments_block_empty
test_parse_e6_response_valid
test_parse_e6_response_with_markdown_fence
test_run_e6_normal_flow_with_mock
test_run_e6_unknown_provider_raises
```

fallback patch 패턴 (`patch("portfolio.services.e6_comparison.LLMClient", return_value=mock)`)이 적용된 케이스:
- **0개** (service 단위 테스트는 patch 없이 client 직접 주입 또는 build/parse 검증). fallback 시나리오 4종은 모두 `test_e6_view.py`에서 처리.

---

## 6. Slice 4 백로그 #9 (latency 임계 16,000ms 상향) 처리

### 6.1 현재 latency 임계 위치

```bash
grep -rn "5_000\|5000.*latency\|latency.*5_000\|latency.*5000\|latency_ms_max" scripts/validation/ portfolio/
```

출력 그대로 인용 (관련 라인만):

```
scripts/validation/run_step6_e5_smoke.py:10:  4. latency_pass: latency_ms <= 5000
scripts/validation/run_step6_e5_smoke.py:40:    "latency_ms_max": 5000,
scripts/validation/run_step6_e5_smoke.py:80:    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]
scripts/validation/run_step6_e5_smoke.py:137:        f"({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
scripts/validation/run_step6_e2_smoke.py:39:THRESHOLDS = {"cost_usd_max": 0.020, "latency_ms_max": 5000}
scripts/validation/run_step6_e2_smoke.py:98:    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]
scripts/validation/run_step6_e2_smoke.py:161:        f"({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
scripts/validation/reparse_step6.py:38:    "latency_ms_max": 5000,
scripts/validation/reparse_step6.py:79:    latency_pass = latency_ms <= NEW_THRESHOLDS["latency_ms_max"]
scripts/validation/reparse_step6.py:117:        f"  latency_pass: {latency_pass} ({latency_ms}ms / {NEW_THRESHOLDS['latency_ms_max']}ms)"
scripts/validation/score_step8.py:11:              AND cost<=$0.020 AND latency<=5000ms
scripts/validation/score_step8_e5.py:14:                            ∧ cost ≤ $0.020 ∧ latency ≤ 5000ms
scripts/validation/score_step8_e5.py:39:    "latency_ms_max": 5000,
scripts/validation/score_step8_e5.py:69:    if latency is None or latency > THRESHOLDS["latency_ms_max"]:
scripts/validation/score_step8_e5.py:70:        return False, f"latency>{THRESHOLDS['latency_ms_max']}"
scripts/validation/score_step8_e5.py:89:    lat_norm = max(0, 1 - (lat / THRESHOLDS["latency_ms_max"]))
scripts/validation/run_step6_smoke.py:8:  4. 지연: latency_ms <= 5000
scripts/validation/run_step6_smoke.py:38:    "latency_ms_max": 5000,
scripts/validation/run_step6_smoke.py:71:    latency_pass = raw.latency_ms <= THRESHOLDS["latency_ms_max"]
scripts/validation/run_step6_smoke.py:111:        f"({raw.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
```

### 6.2 16,000ms 상향 시 영향 받는 파일 목록

| 파일 | 라인 | 현재 값 | 변경 사유 |
|------|------|---------|----------|
| `scripts/validation/run_step6_smoke.py` | 38 | `latency_ms_max: 5000` | Slice 1 E1 baseline 보존을 위해 **변경 금지** (E1 latency mean ~2,498ms로 5,000 충분) |
| `scripts/validation/run_step6_e5_smoke.py` | 40 | `latency_ms_max: 5000` | E5 latency 1,774ms로 5,000 충분 → **변경 금지** |
| `scripts/validation/run_step6_e2_smoke.py` | 39 | `latency_ms_max: 5000` | E2 7,471ms 발생(Slice 3 §1 인용) — Slice 3 종결 시 미해결로 #9 백로그 등록 |
| `scripts/validation/score_step8_e5.py` | 39 | `latency_ms_max: 5000` | E5 산식 임계 — Slice 2 보존 위해 **변경 금지** |
| `scripts/validation/reparse_step6.py` | 38 | `latency_ms_max: 5000` | 사후 reparse 도구 — 단발 사용. 변경 영향 작음 |
| `scripts/validation/run_step6_e6_smoke.py` (**Slice 4 신규**) | (신규) | **`latency_ms_max: 16000`** | E6 출력 길이가 E2와 비슷(~7,000ms) + 안전 마진 → 16,000으로 신규 작성 |

> **#9 처리 범위 (Slice 4 Part 2 Step 6 진입 직전, ~5분)**:
> - **신규 작성**: `run_step6_e6_smoke.py`에 `latency_ms_max: 16000` (E6 한정)
> - 기존 5종 파일은 **변경 안 함** — 슬라이스별 baseline 보존
> - 결과적으로 #9는 **"e6 한정 신규 임계 적용"** — 기존 슬라이스 회귀 0
> - score_step8.py 라인 11 주석은 e5 산식 설명이라 변경 무관

> **결정 권장**: 기존 5,000ms 파일들의 일괄 변경은 회귀 영향 큼. e6 진입점에만 16,000ms 상향 적용. score_step8.py에 e6 entry 추가 시 e2 패턴 mirror하되 latency 임계는 e6 자체 cost/latency 기반이 아니라 efficiency 산식 분모로만 사용 (e1/e2와 동일).

---

## 7. 회귀 baseline 재확인

### 7.1 현재 git 상태

```bash
git branch --show-current
git status --short
git log --oneline -10
```

출력 그대로 인용:
- branch: **`portfolio`** (Part 1 보고와 일치)
- status:
```
 M PROGRESS.md
 M portfolio/llm/mocks.py
 M portfolio/schemas/llm.py
 M portfolio/schemas/llm_outputs.py
 M portfolio/urls.py
 M portfolio/views.py
?? .claude/scheduled_tasks.lock
?? docs/portfolio/coach/slice4_prep_data.md
?? docs/portfolio/instructions/slice_3_frontend_instruction_part2.md
?? docs/portfolio/instructions/slice_3_frontend_instructions_part1.md
?? docs/portfolio/instructions/slice_4_frontend_instruction_part1.md
?? portfolio/services/e6_comparison.py
?? portfolio/tests/fixtures/sample_comparison_context.py
?? portfolio/tests/test_e6_fixtures.py
?? portfolio/tests/test_e6_schema.py
?? portfolio/tests/test_e6_service.py
?? portfolio/tests/test_e6_view.py
```
- 최근 commit:
```
4c07009 docs(portfolio): portfolio 전체 종합 재분석 (Slice 1+2+3 누적)
a005ffe docs(portfolio): Slice 3 종결 — validation_report + refactor_backlog
e89d77b feat(portfolio): Slice 3 Part 2 Step 9 — token_budgets 상수 (백로그 #5, A2.C)
1ddeeab feat(portfolio): Slice 3 Part 2 Step 8 — E2 2-way 회고 + 그룹 분석 (winner: haiku)
2f34be7 feat(portfolio): Slice 3 Part 2 Step 7 — E2 토큰 측정 + budget/I4/hybrid 결정
eefd570 feat(portfolio): Slice 3 Part 2 Step 6 — E2 실 haiku 1회 smoke
7d501c6 feat(portfolio): Slice 3 Part 1 Step 5 — E2 hybrid fixture (Q4 수정)
c90aaf7 feat(portfolio): Slice 3 Part 1 Step 3+4 — E2 view + URL + Mock 4 시나리오
93e3377 feat(portfolio): Slice 3 Part 1 Step 2 — E2 service + 백로그 #3,#4 자연 흡수 (A2.C)
2236ce9 feat(portfolio): Slice 3 Part 1 Step 1 — E2DiagnosticCard schema (4요소)
```

> **차이 발견**: 지시서 §7.1 기대 "Slice 4 Part 1 산출 commit 6개 존재" ↔ 실제 **Slice 4 Part 1 commit 0개** (Part 1 산출물 11개가 모두 modified/untracked 상태). Part 2 진입 전 commit 권장 — 지시서 §7.3 권장 6 commit 패턴 적용.

### 7.2 회귀 카운트

```bash
pytest portfolio/tests/ --collect-only -q | tail -3
```

출력 그대로 인용:
```
========================= 160 tests collected in 0.77s =========================
```

종합 재분석 / Part 1 보고 명시 카운트(160 passed)와 일치 여부:
- [x] **일치 (160)**

### 7.3 진입점별 회귀 분포

```bash
pytest portfolio/tests/test_e1_*.py --collect-only -q | tail -1   # e1
pytest portfolio/tests/test_e2_*.py --collect-only -q | tail -1   # e2
pytest portfolio/tests/test_e5_*.py --collect-only -q | tail -1   # e5
pytest portfolio/tests/test_e6_*.py --collect-only -q | tail -1   # e6
```

| 진입점 | 카운트 |
|--------|-------|
| e1 (`test_e1_garp_view.py`) | 5 |
| e2 (`test_e2_fixtures.py + test_e2_service.py + test_e2_view.py`) | 31 |
| e5 (`test_e5_fixtures.py + test_e5_service.py + test_e5_view.py`) | 28 |
| e6 (`test_e6_schema.py + test_e6_service.py + test_e6_view.py + test_e6_fixtures.py`) | 37 |
| **진입점별 합계** | **101** |
| 나머지 (`test_cost_guard.py + test_fixtures_validation.py + test_mocks.py + test_prompt_assembly.py + test_scenario_e2e.py + test_schemas.py + test_session_lifecycle.py + test_static_integrity.py + test_token_budgets.py`) | **59** |
| **총 합계** | **160** ✓ |

### 7.4 CostGuard 현재 상태

```bash
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from portfolio.llm.cost_guard import CostGuard; import json; print(json.dumps(CostGuard.get_instance().status(), ensure_ascii=False, indent=2))"
```

출력:
```json
{
  "slice_id": "default",
  "call_count": 0,
  "max_calls": 50,
  "remaining": 50,
  "total_cost_usd": 0.0,
  "started_at": null,
  "records_count": 0
}
```

기대 일치: `slice_id="default"`, `call_count=0`, `max_calls=50`, `started_at=null`. **Part 1 종결 후 새 프로세스이므로 default 상태가 정상** (D3.C 설계 — 슬라이스 진입 시점에 reset 적용).

> Part 2 Step 6 진입 직전 `reset_for_slice("slice4", max_calls=50)` 호출 필요.

---

## 8. 점검 체크리스트 (자기 검증)

작성 완료 후 본인 확인:
- [x] 1.1 LLMBudgetExceededError 클래스 정확한 인용 + LLMError 계층 6개 명시
- [x] 1.2 AdjustmentItem 정확한 필드 (ticker / action AdjustmentAction Literal 5종 / reason_quote 필수 / model_validator 동작)
- [x] 1.3 MockLLMClient 정확한 시그니처 (mode + text_strategy) + 등록 dict (e1/e5/e2/e6)
- [x] 1.4 coach_e6_comparison view 전체 인용 (라인 183~241) + 429 매핑 (라인 226~229)
- [x] 1.5 `/api/coach/e6/comparison/` 최종 URL 확정 (config urls.py 라인 48 + portfolio/urls.py 라인 14~18)
- [x] 2.2 7 fixture prompt 토큰 추정 모두 채움 (333~372 tokens 범위)
- [x] 2.4 budget 1차 권장값 산출 (P90=372 × 1.5 = 558 → round-up 1,000 tokens)
- [x] 3.1 score_step8.py 5개 함수/구조 인용 (DIMENSION_LOOKUP / main / e1 인라인 / _main_e2 / e5 delegation)
- [x] 3.2 e1/e2 mirror 가능 여부 판정 (Y) + 통합 권장 방향 명시
- [x] 3.4 Slice 1·3 round-trip 검증 명령 동작 확인 (git diff 빈 출력 = IDENTICAL)
- [x] 4.1 .env 키 존재 여부 (ANTHROPIC_API_KEY=set, GEMINI_API_KEY=set)
- [x] 4.3 Slice 3 Step 6 smoke 패턴 인용 (run_step6_e2_smoke.py)
- [x] 4.4 budget 단위 테스트 카운트 (10 passed)
- [x] 5.1 7 fixture 인터페이스 검증 출력 (메타 키 차이 명시)
- [x] 5.2 test_e6_view.py 9 케이스 이름 모두 나열
- [x] 5.3 test_e6_service.py 8 케이스 이름 모두 나열
- [x] 6.1 latency 5,000ms 위치 grep 결과 (5개 파일 9 라인)
- [x] 7.1 git 상태 (branch=portfolio, Part 1 commit 미수행 차이 명시)
- [x] 7.2 pytest collect = 160 일치
- [x] 7.3 진입점별 회귀 분포 (e1=5, e2=31, e5=28, e6=37, 나머지=59 → 합 160)
- [x] 7.4 CostGuard 초기 상태 (default, started_at=null)
- [x] read-only 원칙 준수 (수정 금지) — score_step8.py round-trip 검증으로 scored.json이 재작성됐으나 git diff 결과 IDENTICAL이라 실효적 변경 0
- [x] 모든 ___ 부분 채움 (빈 칸 없음)

---

## 부록 A — 본 점검에서 발견된 지시서 vs 실제 차이 추가 항목

지시서 §1.1~§1.5 외에 본 점검에서 추가로 발견된 차이:

| 항목 | 지시서 가정 | 실제 |
|------|-------------|------|
| `score_step8.py` CLI flag | `--input` / `--output` 지원 | `--entrypoint`만 지원 (default 경로 고정) |
| Part 1 commit 상태 | "Slice 4 Part 1 산출 commit 6개" | commit 0개 (modified 6 + untracked 5) |
| fixture 메타 키 이름 | `_fixture_id` / `_group` | `fixture_id` / `fixture_group` (언더스코어 없음) |
| `ALL_FIXTURES` 타입 | `list[Callable]` | `dict[str, Callable]` (sample_diagnostic_context.py mirror) |
| view 데코레이터 | `@require_http_methods(["POST"])` | `@require_POST` (Django 단축) |
| view 에러 응답 형식 | `{"ok": false, "error": "...", "code": "..."}` | `{"error": "<code>", "detail": "<msg>"}` (e1/e5/e2 mirror) |

부록 항목들은 Part 2 지시서에 그대로 반영하면 케이스 A~E 발생 없이 진행 가능.
