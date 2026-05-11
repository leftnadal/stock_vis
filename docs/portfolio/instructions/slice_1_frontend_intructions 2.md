# 슬라이스 1 전반부 지시서: E1+GARP 백엔드 와이어링 (Step 1~5)

> 작성일: 2026-04-29
> 슬라이스: 1 (E1 한 줄 진단 + GARP 프리셋, Mock LLM 검증)
> 범위: Step 1~5 (결정론적 코드 작성 + Mock 통합 테스트)
> 후속: 슬라이스 1 후반부 지시서 (Step 6~9, 별도 세션에서 작성)

---

## §0. 참조 문서 + 사전 조건

### §0.1 참조 문서

작업 시작 전 다음 문서를 모두 읽고 컨텍스트 확보. 추측 금지, 실제 파일 view 결과 기준으로 작업.

| 문서                       | 절대 경로                                                                                     | 용도                                                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| D-0a                       | `/Users/byeongjinjeong/Desktop/stock_vis/docs/portfolio/instructions/d-0a-instructions.md`    | Django 모델 13개 정의                                                                                                   |
| D-0b                       | `/Users/byeongjinjeong/Desktop/stock_vis/docs/portfolio/instructions/d-0b-instructions.md`    | Pydantic 스키마 8개 (`schemas/llm_outputs.py` 포함)                                                                     |
| D-1                        | `/Users/byeongjinjeong/Desktop/stock_vis/docs/portfolio/instructions/d-1-instructions.md`     | Tier 0 시스템 프롬프트                                                                                                  |
| D-2                        | `/Users/byeongjinjeong/Desktop/stock_vis/docs/portfolio/instructions/d-2-instructions.md`     | E1 한 줄 진단 프롬프트                                                                                                  |
| presets.py                 | `/Users/byeongjinjeong/Desktop/stock_vis/portfolio/metrics/definitions/presets.py`            | GARP 프리셋 정의                                                                                                        |
| preset_metrics.py          | `/Users/byeongjinjeong/Desktop/stock_vis/portfolio/metrics/definitions/preset_metrics.py`     | GARP 지표 매핑                                                                                                          |
| sample_analysis_context.py | `/Users/byeongjinjeong/Desktop/stock_vis/portfolio/tests/fixtures/sample_analysis_context.py` | `get_context_garp_tech()` 등 Mock fixture 함수                                                                          |
| 기존 schemas/              | `/Users/byeongjinjeong/Desktop/stock_vis/portfolio/schemas/`                                  | Pydantic 스키마 8개 (analysis_context, diagnostic, holding, llm_outputs, metric_result, return_breakdown, user_profile) |
| 기존 prompts/e1/           | `/Users/byeongjinjeong/Desktop/stock_vis/portfolio/prompts/e1/`                               | E1 프롬프트 빌더 (재사용)                                                                                               |

### §0.2 사전 조건 (본인이 작업 시작 전 확인)

**다음 4가지가 모두 충족되어야 슬라이스 1 작업 시작 가능. 하나라도 미충족이면 즉시 본인에게 보고하고 중단.**

1. **브랜치**: `git branch --show-current` 결과가 `portfolio` 여야 함. 다른 브랜치이면 본인이 직접 `git checkout portfolio`로 전환 후 진행. Claude Code는 브랜치 전환 금지.
2. **테스트 기준선**: `pytest portfolio/tests/ -q` 결과가 `22 passed` 여야 함. 그 외(예: `21 passed, 1 failed`)이면 즉시 보고하고 중단.
3. **환경 변수**: `.env` 파일에 `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` 두 개 모두 존재. (값 노출 금지, 키 존재 여부만 확인.)
4. **의존성**: `anthropic`, `google-generativeai`, `pydantic` 패키지 설치 확인 (`pip show <package>` 또는 `poetry show <package>`).

위 4가지 모두 충족되면 §1로 진행.

---

## §1. 확정 결정 사항 블록 (변경 금지)

**아래 블록의 모든 결정 사항은 본 세션에서 본인과 합의된 결과. Claude Code는 절대 변경 금지. 변경이 필요하다고 판단되면 즉시 작업 중단하고 §10 에스컬레이션 포맷으로 본인에게 보고.**

### §1.1 메타데이터 컨테이너: Pydantic 모델 (`LLMResponse`)

`schemas/llm.py`에 다음 Pydantic 모델 신규 작성:

```python
from typing import Literal, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    text: str
    provider: Literal["gemini", "anthropic"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    fallback_from: Optional[Literal["gemini", "anthropic"]] = None
```

- `dict` 또는 `dataclass`로 변경 금지
- 필드 추가/제거 금지

### §1.2 재시도 후 동작: 폴백 provider

- 1차 시도 실패 → 1회 재시도
- 재시도도 실패 + 폴백 트리거 조건 충족 시 → 다른 provider로 폴백
- 폴백 트리거 조건은 §1.2.1 참조
- 폴백 응답에는 `fallback_from` 필드에 원래 시도 provider 명시

### §1.2.1 폴백 트리거 조건

**폴백 발동**: `LLMRateLimitError`, `LLMTimeoutError` 두 클래스만

**폴백 안 함 (raise)**: `LLMAuthError`, `LLMInvalidPromptError`, 기타 모든 에러

### §1.2.2 폴백 메타데이터: `fallback_from` 필드

- 정상 호출 시: `fallback_from = None`
- 폴백 발동 시: `fallback_from = "gemini"` (Gemini → Anthropic 폴백) 또는 `"anthropic"` (반대 방향)
- `provider` 필드는 항상 **최종 사용 provider**를 의미

### §1.2.3 비용 가드: 엄격 차단, 임계 50회

- 환경 변수 `LLM_BUDGET_MAX_CALLS` (기본값 50)
- `LLMClient` 인스턴스의 `_call_count`가 임계 도달 시 → `LLMBudgetExceededError` raise
- view 레이어에서 503 응답 + 명확한 에러 메시지

### §1.A API 키 로딩: Django settings

- `os.getenv()` 직접 호출 금지
- `django.conf.settings.ANTHROPIC_API_KEY`, `django.conf.settings.GEMINI_API_KEY`, `django.conf.settings.LLM_BUDGET_MAX_CALLS` 사용
- `config/settings.py`에 다음 섹션 추가:

```python
# === LLM Provider Settings ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_BUDGET_MAX_CALLS = int(os.getenv("LLM_BUDGET_MAX_CALLS", "50"))
```

### §1.5 Mock LLM 통합 테스트: 5케이스 심층 검증

§7에서 상세히 정의. 케이스 5개 모두 작성 필수.

---

## §2. Claude Code "다음 작업 5개" 카테고리 매핑 표

**Claude Code가 이전에 제안한 다음 작업 5개와 슬라이스 1 범위의 관계.**

| 카테고리                      | 슬라이스 1 포함 여부 | 슬라이스 1에서의 형태                                                                | 본격 작업 시점                        |
| ----------------------------- | -------------------- | ------------------------------------------------------------------------------------ | ------------------------------------- |
| 1. 실제 LLM 호출 테스트       | **부분 포함**        | E1+GARP 한 진입점만, Mock 위주 (실 호출은 후반부 9회)                                | 슬라이스 1 후반부 (별도 지시서)       |
| 2. 백엔드 API 엔드포인트      | **부분 포함**        | `GET /api/coach/e1/garp/` 단일 엔드포인트, **순수 Django view** (DRF 미적용)         | 후속 슬라이스 ("API 엔드포인트 추출") |
| 3. ReturnCalculator (RV1~RV4) | **미포함**           | 슬라이스 1 GARP 진입점은 fixture가 모든 입력 제공. ReturnCalculator 호출 없음        | 슬라이스별 점진 확장                  |
| 4. 프리셋 스코어링 엔진       | **미포함**           | Mock fixture(`get_context_garp_tech()`)가 strengths/weaknesses 미리 박혀 있음 → 우회 | "스코어링 엔진 일반화" 단계           |
| 5. 프론트엔드 Coach 채팅 UI   | **미포함**           | 슬라이스 1은 백엔드만. JsonResponse로 검증                                           | 마지막 단계 ("프론트엔드 연동")       |

**중요**: 위 표의 "본격 작업 시점" 컬럼이 슬라이스 1 외 작업이라는 것은 **자율 판단으로 미리 작성하지 않는다**는 의미. 예를 들어 4번 스코어링 엔진을 미리 만들지 말 것 — Mock fixture 사용으로 우회.

---

## §3. 자명 선언 + 작업 범위

### §3.1 자명 선언 (재논의 불필요)

1. **LLMClient 인스턴스화**: per-request (Django view마다 생성). singleton 금지.
2. **Provider SDK import**: eager (모듈 최상단 import). lazy import 금지.
3. **schema 파싱 책임 분리**: `LLMClient.complete()`는 `LLMResponse` 반환 (text + 메타데이터만). 진입점별 schema 파싱 (예: `OneLineDiagnosis`)은 service 레이어 책임.
4. **Provider 단가 상수 위치**: `portfolio/llm/client.py` 모듈 상수. 별도 모듈 분리 금지.
5. **토큰 카운트/비용 계산**: client 내부 메소드. provider별 응답에서 추출 (Gemini `usageMetadata`, Anthropic `usage`).
6. **fixture 사용 방식**: `from portfolio.tests.fixtures.sample_analysis_context import get_context_garp_tech` import 방식. JSON 파싱 금지.
7. **신규 디렉토리 생성**: `portfolio/llm/`, `portfolio/services/`, `portfolio/views.py`, `portfolio/urls.py` 모두 신규 생성. 기존에 없음.
8. **schemas/llm.py**: 신규 파일. `LLMResponse` 모델 정의.

### §3.2 작업 범위 (Step 1~5)

| Step | 작업                                              | 산출물                                                                                                               |
| ---- | ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 1    | LLMClient wrapper                                 | `portfolio/schemas/llm.py` + `portfolio/llm/exceptions.py` + `portfolio/llm/client.py` + `portfolio/llm/__init__.py` |
| 2    | services/e1_garp.py (비즈니스 로직 분리)          | `portfolio/services/__init__.py` + `portfolio/services/e1_garp.py`                                                   |
| 3    | Django view (`GET /api/coach/e1/garp/?provider=`) | `portfolio/views.py`                                                                                                 |
| 4    | URL 라우팅                                        | `portfolio/urls.py` + `config/urls.py` 수정                                                                          |
| 5    | Mock LLM client + 통합 테스트 5케이스             | `portfolio/llm/mocks.py` + `portfolio/tests/test_e1_garp_view.py`                                                    |

**테스트 통과 목표**: 22 → 27 (5케이스 추가). `pytest portfolio/tests/ -q` 결과 `27 passed` 확인.

### §3.3 작업 범위 외 (Claude Code 자율 판단 금지 항목)

- DRF (Django REST Framework) 도입 → 슬라이스 1은 순수 Django view + JsonResponse
- 프리셋 스코어링 엔진 (Mock fixture로 우회)
- ReturnCalculator (슬라이스 1 GARP 진입점에 불필요)
- 프론트엔드 코드 (백엔드 검증만)
- E2~E6 진입점 (E1만)
- 다른 프리셋 (GARP만)
- 실제 LLM 호출 (Mock으로 검증, 실 호출은 후반부 별도 지시서)

---

## §4. Step 1: LLMClient wrapper

### §4.1 산출물 4개 파일

#### 1) `portfolio/schemas/llm.py` (신규)

`LLMResponse` Pydantic 모델 정의 (§1.1 그대로).

#### 2) `portfolio/llm/__init__.py` (신규)

```python
from portfolio.llm.client import LLMClient
from portfolio.llm.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthError,
    LLMInvalidPromptError,
    LLMBudgetExceededError,
)

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMAuthError",
    "LLMInvalidPromptError",
    "LLMBudgetExceededError",
]
```

#### 3) `portfolio/llm/exceptions.py` (신규)

6개 예외 클래스 계층 구조:

```python
class LLMError(Exception):
    """LLM 호출 관련 모든 에러의 베이스."""

class LLMRateLimitError(LLMError):
    """Rate limit 초과 → 폴백 트리거."""

class LLMTimeoutError(LLMError):
    """타임아웃 → 폴백 트리거."""

class LLMAuthError(LLMError):
    """인증 에러 → raise (폴백 안 함)."""

class LLMInvalidPromptError(LLMError):
    """프롬프트/파라미터 잘못됨 (4xx) → raise."""

class LLMBudgetExceededError(LLMError):
    """비용 가드 임계 도달 → raise."""
```

#### 4) `portfolio/llm/client.py` (신규)

**LLMClient 핵심 책임**:

- Gemini Flash + Anthropic Sonnet 두 provider를 단일 `complete()` 메소드로 통합
- 1회 재시도 + 폴백 (RateLimit, Timeout만)
- 비용 가드 (인스턴스별 카운트)
- 토큰 카운트 + cost_usd 계산

**필수 구성 요소**:

```python
import time
from typing import Literal
from django.conf import settings
from anthropic import Anthropic
import google.generativeai as genai

from portfolio.schemas.llm import LLMResponse
from portfolio.llm.exceptions import (
    LLMError, LLMRateLimitError, LLMTimeoutError,
    LLMAuthError, LLMInvalidPromptError, LLMBudgetExceededError,
)

# Provider 단가 (USD per 1M tokens) — 2026-04 기준, 본인이 향후 수동 갱신
GEMINI_FLASH_INPUT_USD_PER_1M = 0.075
GEMINI_FLASH_OUTPUT_USD_PER_1M = 0.30
ANTHROPIC_SONNET_INPUT_USD_PER_1M = 3.0
ANTHROPIC_SONNET_OUTPUT_USD_PER_1M = 15.0

# 기본 모델명
GEMINI_MODEL = "gemini-2.0-flash"
ANTHROPIC_MODEL = "claude-sonnet-4-5"


class LLMClient:
    """
    Gemini Flash + Anthropic Sonnet 통합 wrapper.

    - 1회 재시도 + 폴백 (RateLimit/Timeout만)
    - 비용 가드 (LLM_BUDGET_MAX_CALLS, 인스턴스별)
    - 응답: LLMResponse (Pydantic)
    """

    def __init__(self):
        self._call_count = 0
        self._budget_max = settings.LLM_BUDGET_MAX_CALLS

    def complete(
        self,
        prompt: str,
        provider: Literal["gemini", "anthropic"] = "gemini",
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        LLM 호출. 폴백·가드 포함.

        Args:
            prompt: 시스템+유저 프롬프트 통합 문자열 (또는 provider별 메시지 형식)
            provider: "gemini" (기본) 또는 "anthropic"
            max_tokens: 응답 최대 토큰

        Returns:
            LLMResponse (text + 메타데이터)

        Raises:
            LLMBudgetExceededError: 비용 가드 발동
            LLMAuthError, LLMInvalidPromptError: 폴백 안 함, raise
            LLMError: 폴백도 실패한 경우
        """
        # 1. 비용 가드 먼저 검사
        if self._call_count >= self._budget_max:
            raise LLMBudgetExceededError(
                f"호출 {self._call_count}회 도달, 가드 임계 {self._budget_max}"
            )

        # 2. 1차 시도 + 1회 재시도
        try:
            return self._call_with_retry(provider, prompt, max_tokens)
        except (LLMRateLimitError, LLMTimeoutError) as e:
            # 3. 폴백
            fallback_provider = "anthropic" if provider == "gemini" else "gemini"
            response = self._call_with_retry(fallback_provider, prompt, max_tokens)
            response.fallback_from = provider
            return response
        # LLMAuthError, LLMInvalidPromptError 는 raise 그대로

    def _call_with_retry(self, provider, prompt, max_tokens) -> LLMResponse:
        """1회 재시도 포함 단일 provider 호출."""
        for attempt in range(2):
            try:
                return self._call(provider, prompt, max_tokens)
            except (LLMRateLimitError, LLMTimeoutError):
                if attempt == 1:
                    raise

    def _call(self, provider, prompt, max_tokens) -> LLMResponse:
        """단일 provider 호출. 1회만."""
        self._call_count += 1
        start = time.time()

        if provider == "gemini":
            return self._call_gemini(prompt, max_tokens, start)
        elif provider == "anthropic":
            return self._call_anthropic(prompt, max_tokens, start)
        else:
            raise LLMInvalidPromptError(f"Unknown provider: {provider}")

    def _call_gemini(self, prompt, max_tokens, start) -> LLMResponse:
        """Gemini Flash 호출. 응답 파싱 + cost 계산."""
        # 구체 구현은 자율 판단:
        # - genai.configure(api_key=settings.GEMINI_API_KEY)
        # - GenerativeModel(GEMINI_MODEL).generate_content(prompt)
        # - 응답.usage_metadata에서 prompt_token_count, candidates_token_count 추출
        # - cost = (input_tokens / 1_000_000) * GEMINI_FLASH_INPUT_USD_PER_1M + ...
        # - 에러 매핑:
        #     google.api_core.exceptions.ResourceExhausted → LLMRateLimitError
        #     google.api_core.exceptions.DeadlineExceeded → LLMTimeoutError
        #     google.api_core.exceptions.PermissionDenied / Unauthenticated → LLMAuthError
        #     google.api_core.exceptions.InvalidArgument → LLMInvalidPromptError
        ...

    def _call_anthropic(self, prompt, max_tokens, start) -> LLMResponse:
        """Anthropic Sonnet 호출. 응답 파싱 + cost 계산."""
        # 구체 구현은 자율 판단:
        # - Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        # - .messages.create(model=ANTHROPIC_MODEL, messages=[...], max_tokens=max_tokens)
        # - 응답.usage.input_tokens / output_tokens 추출
        # - 에러 매핑:
        #     anthropic.RateLimitError → LLMRateLimitError
        #     anthropic.APITimeoutError → LLMTimeoutError
        #     anthropic.AuthenticationError → LLMAuthError
        #     anthropic.BadRequestError → LLMInvalidPromptError
        ...
```

### §4.2 자율 판단 허용 영역 (Step 1)

다음은 본인이 명시하지 않은 디테일. Claude Code 자율 판단 허용:

- import 정리 순서 (stdlib → third-party → local)
- docstring 형식 (Google style, NumPy style 등 일관성만 유지)
- 내부 변수명
- 에러 메시지 한국어/영어 (한국어 권장하나 강제 아님)
- `_call_gemini` / `_call_anthropic` 내부 구체 구현

### §4.3 자율 판단 금지 영역 (Step 1)

- `LLMResponse` schema 변경 (필드 추가/제거 금지)
- `complete()` 메소드 시그니처 변경
- 폴백 트리거 조건 변경 (RateLimit + Timeout만)
- `fallback_from` 필드 사용 방식 변경
- 비용 가드 임계 검사 로직 변경
- API 키 로딩 방식 변경 (`os.getenv()` 직접 호출 금지)

---

## §5. Step 2: services/e1_garp.py (비즈니스 로직 분리)

### §5.1 산출물 2개 파일

#### 1) `portfolio/services/__init__.py` (신규)

빈 파일 또는 명시적 export:

```python
from portfolio.services.e1_garp import run_e1_garp

__all__ = ["run_e1_garp"]
```

#### 2) `portfolio/services/e1_garp.py` (신규)

**책임**: view에서 HTTP 코드 분리. 비즈니스 로직(프롬프트 빌드 → LLM 호출 → schema 파싱)만 담당.

```python
from typing import Literal
from portfolio.llm import LLMClient
from portfolio.schemas.llm import LLMResponse
from portfolio.schemas.llm_outputs import OneLineDiagnosis  # D-0b 산출물
from portfolio.tests.fixtures.sample_analysis_context import get_context_garp_tech
from portfolio.prompts.e1.e1_builder import build_e1_prompt  # D-2 산출물


def run_e1_garp(
    provider: Literal["gemini", "anthropic", "mock"] = "gemini",
    client: LLMClient | None = None,
) -> dict:
    """
    E1 한 줄 진단 + GARP 프리셋 종단 실행.

    1. Mock fixture에서 AnalysisContext 로드
    2. E1 프롬프트 빌드
    3. LLM 호출
    4. 응답 schema 파싱 (OneLineDiagnosis)
    5. {diagnosis, llm_metadata} dict 반환

    Args:
        provider: "gemini" (기본) / "anthropic" / "mock" (테스트용)
        client: LLMClient 인스턴스 (의존성 주입, 테스트 모킹용)

    Returns:
        dict: {
            "diagnosis": OneLineDiagnosis (Pydantic dump),
            "llm_metadata": LLMResponse 메타데이터 (text 제외),
        }
    """
    # 1. fixture 로드
    context = get_context_garp_tech()

    # 2. 프롬프트 빌드 (D-2 빌더 재사용)
    prompt = build_e1_prompt(context)

    # 3. LLM 호출
    if client is None:
        client = LLMClient()

    llm_response: LLMResponse = client.complete(prompt=prompt, provider=provider)

    # 4. schema 파싱
    diagnosis = OneLineDiagnosis.model_validate_json(llm_response.text)

    # 5. 응답 dict 구성
    return {
        "diagnosis": diagnosis.model_dump(),
        "llm_metadata": {
            "provider": llm_response.provider,
            "model": llm_response.model,
            "latency_ms": llm_response.latency_ms,
            "input_tokens": llm_response.input_tokens,
            "output_tokens": llm_response.output_tokens,
            "cost_usd": llm_response.cost_usd,
            "fallback_from": llm_response.fallback_from,
        },
    }
```

### §5.2 자율 판단 허용 영역 (Step 2)

- `OneLineDiagnosis` 실제 schema 필드명/위치 — D-0b 결과를 view 후 정확히 import
- `build_e1_prompt` 실제 함수명/시그니처 — D-2/`prompts/e1/e1_builder.py` view 후 정확히 import
- 응답 dict 구조 디테일 (단, `diagnosis` + `llm_metadata` 두 키는 유지)
- 에러 핸들링 (예: schema 파싱 실패 시 어떤 예외 raise할지)

### §5.3 자율 판단 금지 영역 (Step 2)

- `client` 파라미터 (의존성 주입) 제거 금지 — Mock 테스트의 핵심
- LLMClient 직접 호출 금지 (반드시 의존성 주입 받은 client 사용)
- `provider` 파라미터에 `"mock"` 추가 (Mock client 사용 시 사용)

---

## §6. Step 3 + Step 4: Django view + URL 라우팅

### §6.1 Step 3 산출물: `portfolio/views.py` (신규)

```python
import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from portfolio.llm import LLMBudgetExceededError, LLMError
from portfolio.services.e1_garp import run_e1_garp


@require_GET
def coach_e1_garp(request):
    """
    GET /api/coach/e1/garp/?provider=gemini

    E1 한 줄 진단 (GARP 프리셋 + Mock fixture).
    """
    provider = request.GET.get("provider", "gemini")

    if provider not in ("gemini", "anthropic"):
        return JsonResponse(
            {"error": f"Invalid provider: {provider}. Must be 'gemini' or 'anthropic'."},
            status=400,
        )

    try:
        result = run_e1_garp(provider=provider)
        return JsonResponse(result, status=200)
    except LLMBudgetExceededError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except LLMError as e:
        return JsonResponse({"error": str(e)}, status=500)
```

### §6.2 Step 4 산출물: URL 라우팅

#### 1) `portfolio/urls.py` (신규)

```python
from django.urls import path
from portfolio import views

app_name = "portfolio"

urlpatterns = [
    path("coach/e1/garp/", views.coach_e1_garp, name="coach_e1_garp"),
]
```

#### 2) `config/urls.py` 수정 (기존 파일)

기존 `urlpatterns`에 한 줄 추가 (정확한 위치는 자율 판단):

```python
from django.urls import include, path

urlpatterns = [
    # ... 기존 라인들 ...
    path("api/", include("portfolio.urls")),
]
```

**주의**: `config/urls.py`가 이미 다른 앱(macro, marketpulse 등)의 라우팅을 포함하고 있을 수 있음. 기존 라인 수정 금지, **추가만** 허용.

### §6.3 자율 판단 허용 영역 (Step 3+4)

- `coach_e1_garp` 함수 docstring
- 에러 메시지 문구 (한국어/영어)
- `provider` 검증 로직 디테일 (정규식, set 멤버십 등)
- `config/urls.py`에서 `path("api/", ...)` 추가 위치

### §6.4 자율 판단 금지 영역 (Step 3+4)

- DRF (`@api_view`, `Response`, `APIView`) 사용 금지 — 순수 Django view + JsonResponse만
- URL 패턴 변경 금지 (`/api/coach/e1/garp/` 그대로)
- HTTP 메소드 추가 금지 (GET만)
- `coach_e1_garp` 함수명 변경 금지

---

## §7. Step 5: Mock LLM 통합 테스트 (5케이스 심층 검증)

### §7.1 산출물 2개 파일

#### 1) `portfolio/llm/mocks.py` (신규)

**책임**: Mock LLMClient. 결정론적 응답 + 모드 분기로 폴백/에러/가드 모든 케이스 시뮬레이션.

```python
from typing import Literal
from portfolio.schemas.llm import LLMResponse
from portfolio.llm.exceptions import (
    LLMRateLimitError, LLMTimeoutError, LLMAuthError, LLMBudgetExceededError,
)


class MockLLMClient:
    """
    LLMClient 인터페이스 호환 Mock.

    모드별 동작:
    - "normal": 정상 응답 반환 (Gemini 첫 시도 성공)
    - "rate_limit_first": Gemini 2회 RateLimit → Anthropic 폴백 성공
    - "timeout_first": Gemini 2회 Timeout → Anthropic 폴백 성공
    - "auth_error": Gemini 첫 시도 AuthError (폴백 안 함, raise)
    - "budget_exceeded": 호출 시 즉시 LLMBudgetExceededError
    """

    def __init__(self, mode: Literal[
        "normal", "rate_limit_first", "timeout_first",
        "auth_error", "budget_exceeded"
    ] = "normal"):
        self.mode = mode
        self._call_count = 0

    def complete(self, prompt, provider="gemini", max_tokens=2000) -> LLMResponse:
        self._call_count += 1

        if self.mode == "budget_exceeded":
            raise LLMBudgetExceededError("Mock 가드 발동")

        if self.mode == "auth_error":
            raise LLMAuthError("Mock 인증 실패")

        if self.mode == "rate_limit_first" and provider == "gemini":
            # 폴백 시뮬레이션: Anthropic으로 전환
            return self._mock_response(provider="anthropic", fallback_from="gemini")

        if self.mode == "timeout_first" and provider == "gemini":
            return self._mock_response(provider="anthropic", fallback_from="gemini")

        # normal
        return self._mock_response(provider=provider, fallback_from=None)

    def _mock_response(self, provider, fallback_from) -> LLMResponse:
        """결정론적 Mock 응답. OneLineDiagnosis schema 통과 가능한 JSON 텍스트."""
        # OneLineDiagnosis 실제 schema에 맞춘 JSON 문자열
        # (D-0b의 schemas/llm_outputs.py를 view한 후 정확한 필드로 채울 것)
        mock_text = '{"diagnosis": "GARP 적합도 양호. 성장-가치 균형 유지.", ...}'

        return LLMResponse(
            text=mock_text,
            provider=provider,
            model="mock-" + provider,
            latency_ms=100,
            input_tokens=500,
            output_tokens=50,
            cost_usd=0.001,
            fallback_from=fallback_from,
        )
```

#### 2) `portfolio/tests/test_e1_garp_view.py` (신규)

**5케이스 심층 검증**:

```python
import pytest
from django.test import Client
from django.urls import reverse
from unittest.mock import patch
from portfolio.llm.mocks import MockLLMClient


@pytest.fixture
def django_client():
    return Client()


# ===== 케이스 1: 정상 호출 =====
@pytest.mark.django_db
def test_e1_garp_normal_call(django_client):
    """Gemini 정상 호출 → 200 + 응답 schema 통과."""
    mock = MockLLMClient(mode="normal")

    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 200
    data = response.json()

    # 응답 구조 검증
    assert "diagnosis" in data
    assert "llm_metadata" in data

    # 메타데이터 필드 검증
    metadata = data["llm_metadata"]
    assert metadata["provider"] == "gemini"
    assert metadata["fallback_from"] is None
    assert metadata["latency_ms"] >= 0
    assert metadata["input_tokens"] > 0
    assert metadata["output_tokens"] > 0
    assert metadata["cost_usd"] >= 0


# ===== 케이스 2: RateLimit → 폴백 =====
@pytest.mark.django_db
def test_e1_garp_rate_limit_fallback(django_client):
    """Gemini RateLimit 2회 → Anthropic 폴백 성공."""
    mock = MockLLMClient(mode="rate_limit_first")

    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 200
    metadata = response.json()["llm_metadata"]

    # 폴백 메타데이터 검증
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


# ===== 케이스 3: Timeout → 폴백 =====
@pytest.mark.django_db
def test_e1_garp_timeout_fallback(django_client):
    """Gemini Timeout 2회 → Anthropic 폴백 성공."""
    mock = MockLLMClient(mode="timeout_first")

    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 200
    metadata = response.json()["llm_metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


# ===== 케이스 4: AuthError → 폴백 안 함, 500 응답 =====
@pytest.mark.django_db
def test_e1_garp_auth_error_no_fallback(django_client):
    """AuthError는 폴백 안 함 → 500 응답."""
    mock = MockLLMClient(mode="auth_error")

    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 500
    assert "error" in response.json()


# ===== 케이스 5: 비용 가드 발동 → 503 응답 =====
@pytest.mark.django_db
def test_e1_garp_budget_exceeded(django_client):
    """비용 가드 임계 도달 → 503 응답."""
    mock = MockLLMClient(mode="budget_exceeded")

    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 503
    assert "error" in response.json()
```

### §7.2 자율 판단 허용 영역 (Step 5)

- Mock 응답의 `mock_text` 실제 JSON 내용 (단, `OneLineDiagnosis` schema 통과는 필수)
- 테스트 함수 docstring
- `patch` 경로 (다만 `portfolio.services.e1_garp.LLMClient` 가정)
- 추가 assertion (위에 명시된 검증 외에도 자율 추가 가능)

### §7.3 자율 판단 금지 영역 (Step 5)

- 5케이스 모두 작성 필수 (4케이스로 줄이기 금지)
- 케이스별 mode 변경 금지 (`normal`, `rate_limit_first`, `timeout_first`, `auth_error`, `budget_exceeded`)
- HTTP status code 변경 금지 (200/500/503)
- Mock 인스턴스화 외 실제 외부 API 호출 금지

### §7.4 테스트 회귀 검증

작업 완료 후 다음 명령으로 27 테스트 통과 확인:

```bash
pytest portfolio/tests/ -q
```

**예상 결과**: `27 passed in X.XXs` (기존 22 + 신규 5)

`27 passed`가 아니면 §10 에스컬레이션.

---

## §8. 판단 허용 범위 (전체 요약)

본 지시서의 자율 판단 허용/금지를 통합 정리.

### §8.1 자율 판단 허용 (디테일)

- import 정리 순서, docstring 형식
- 내부 변수명, 한국어/영어 에러 메시지
- 함수 내부 구체 구현 (단, 시그니처와 동작은 명시된 대로)
- 추가 assertion, 추가 docstring

### §8.2 자율 판단 금지 (구조 + 결정 사항)

- §1 "확정 결정 사항 블록" 모든 항목
- 파일 경로, 함수명, 클래스명, schema 필드
- HTTP 메소드, URL 패턴, status code
- DRF 도입, 다른 진입점/프리셋 추가, 실제 LLM 호출
- 작업 범위 외 항목 (§3.3 참조)

### §8.3 자율 판단 모호 영역 (즉시 에스컬레이션)

다음 상황은 자율 판단 금지 — 즉시 §10 에스컬레이션:

- D-0b의 `OneLineDiagnosis` schema 필드가 본 지시서 가정과 다른 경우
- D-2의 `build_e1_prompt` 함수 시그니처가 다른 경우
- `get_context_garp_tech()` 함수 반환 타입이 `AnalysisContext`가 아닌 경우
- 기존 22 테스트가 회귀 발생한 경우 (27 passed 외 결과)
- §1 결정 사항 변경이 필요하다고 판단되는 모든 상황

---

## §9. 완료 보고 포맷

작업 완료 시 다음 포맷으로 본인에게 보고.

### 보고 템플릿

```
# 슬라이스 1 전반부 작업 완료 보고

## 1. 산출물

| Step | 파일 경로 | 라인 수 | 비고 |
|---|---|---|---|
| 1 | portfolio/schemas/llm.py | XX | 신규 |
| 1 | portfolio/llm/__init__.py | XX | 신규 |
| 1 | portfolio/llm/exceptions.py | XX | 신규 |
| 1 | portfolio/llm/client.py | XX | 신규 |
| 2 | portfolio/services/__init__.py | XX | 신규 |
| 2 | portfolio/services/e1_garp.py | XX | 신규 |
| 3 | portfolio/views.py | XX | 신규 |
| 4 | portfolio/urls.py | XX | 신규 |
| 4 | config/urls.py | +1 라인 | 수정 |
| 5 | portfolio/llm/mocks.py | XX | 신규 |
| 5 | portfolio/tests/test_e1_garp_view.py | XX | 신규 |

## 2. 테스트 결과

```

$ pytest portfolio/tests/ -q
XX passed in X.XXs

```

기존 22 + 신규 5 = 27 passed 확인 ✅

## 3. 검증 체크리스트

- [ ] §1 확정 결정 사항 모두 반영
- [ ] §3.3 작업 범위 외 항목 작성하지 않음
- [ ] DRF 미사용 (순수 Django view)
- [ ] LLMResponse Pydantic 모델 그대로 사용
- [ ] fallback_from 필드 존재
- [ ] 비용 가드 (LLM_BUDGET_MAX_CALLS) Django settings 사용
- [ ] 5케이스 통합 테스트 모두 작성
- [ ] 기존 22 테스트 회귀 없음

## 4. 자율 판단 영역 요약

§8.1에서 자율 판단으로 결정한 사항 (있으면) 명시:
- 예: docstring 형식 = Google style
- 예: 에러 메시지 = 한국어
- 예: cost_usd 단가 상수는 `client.py` 모듈 최상단

## 5. 미해결 / 에스컬레이션 사항

(있으면 명시. 없으면 "없음")

## 6. Git 커밋 권장

```

git add portfolio/schemas/llm.py portfolio/llm/ portfolio/services/ portfolio/views.py portfolio/urls.py config/urls.py portfolio/tests/test_e1_garp_view.py
git commit -m "feat(portfolio): slice 1 frontend wiring (E1+GARP, Mock LLM verified)"

```

(아직 커밋하지 마. 본인이 변경 사항 review 후 커밋 결정.)
```

---

## §10. 에스컬레이션 포맷

다음 상황 발생 시 작업 즉시 중단하고 본인에게 보고. **임의 판단으로 진행 금지.**

### 에스컬레이션 트리거

1. §0.2 사전 조건 4가지 중 하나라도 미충족
2. §1 확정 결정 사항 변경이 필요하다고 판단되는 상황
3. 참조 문서(D-0b, D-2 등)와 본 지시서 가정 사이 충돌
4. 기존 22 테스트 회귀 발생
5. fixture/schema/builder의 실제 인터페이스가 본 지시서 가정과 다름
6. §3.3 작업 범위 외 항목을 추가해야 한다고 판단되는 상황
7. 30분 이상 막힌 모든 상황

### 보고 포맷

```
# 에스컬레이션: [한 줄 요약]

## 발생 위치
- Step: [1~5 중]
- 파일: [경로]
- 라인: [번호 또는 "전체"]

## 상황
[현재 상태 객관 기술]

## 본 지시서 가정 vs 실제
| 항목 | 본 지시서 가정 | 실제 |
|---|---|---|
| ... | ... | ... |

## 시도한 것
[있으면 기술]

## 본인 결정 필요 사안
[질문 형태로 명확히]

## 영향 범위
- Step X에 영향 / 슬라이스 1 전체 영향 / 슬라이스 2~6에도 영향

## 권장 옵션
- 옵션 A: [장단점]
- 옵션 B: [장단점]
- (필요시 옵션 C)
```

본인이 답변하면 그에 따라 진행. 답변 받기 전 자율 판단 금지.

---

## §11. 부록: 본 세션 결정 근거 요약

본 지시서의 §1 결정 사항이 어떤 근거로 정해졌는지 요약. Claude Code는 **참고용**으로만 활용. 결정 변경 권한 없음.

| 결정                    | 옵션                          | 가중 총점     | 추천 근거                                |
| ----------------------- | ----------------------------- | ------------- | ---------------------------------------- |
| 1.1 메타데이터 컨테이너 | Pydantic                      | 4.60          | D-0b 8개 schemas 일관성 + 타입 안전성    |
| 1.2 재시도 후 동작      | 폴백 provider                 | (사용자 선택) | 가용성 최대화                            |
| 1.2.1 폴백 트리거       | RateLimit + Timeout만         | 4.60          | 정확성 1위 (불필요 폴백 방지)            |
| 1.2.2 폴백 메타데이터   | fallback_from 필드            | 4.80          | Pydantic 패턴 일관성                     |
| 1.2.3 비용 가드         | 엄격 차단 (50회)              | 4.40          | 비용 통제 + 가용성 영향 미미             |
| 1.A API 키 로딩         | Django settings               | 4.75          | Django 일관성 + override_settings 테스트 |
| 2 지시서 범위           | 전반부 + 후반부 2개           | 4.80          | 옵션 C 하이브리드 정합                   |
| 3 자율도                | 균형 (구조 박음, 디테일 자율) | 4.40          | D-시리즈 검증 패턴                       |
| 4 매핑 표               | 지시서 내 명시                | 4.80          | Claude Code 자율 판단 차단               |
| 5 통합 테스트           | 심층 (5케이스)                | (사용자 선택) | 결정 1.2 모든 동작 결정론적 검증         |

---

**지시서 끝.**

작업 시작 전 §0.2 사전 조건 확인 → §1 결정 사항 숙지 → §4부터 순차 진행.

막힘 발생 시 §10 에스컬레이션 포맷으로 즉시 보고.
