"""
LLMClient — Gemini Flash + Anthropic Sonnet 통합 wrapper.

§1 확정 결정 사항 반영:
  - LLMResponse Pydantic 컨테이너 반환
  - 1회 재시도 + 폴백 (RateLimit/Timeout만)
  - 비용 가드 (LLM_BUDGET_MAX_CALLS, 인스턴스별 카운트)
  - API 키: Django settings 경유

신 SDK 사용 (`google-genai`, `from google import genai`). 프로젝트 일관성에
맞춰 §4.2 자율 판단으로 채택.
"""

from __future__ import annotations

import time
from typing import Literal

from django.conf import settings

from packages.shared.llm import complete

from apps.portfolio.llm.exceptions import (
    LLMAuthError,
    LLMBudgetExceededError,
    LLMInvalidPromptError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from apps.portfolio.schemas.llm import LLMResponse

# Provider 단가 (USD per 1M tokens) — 2026-04 기준, 본인이 향후 수동 갱신
GEMINI_FLASH_INPUT_USD_PER_1M = 0.075
GEMINI_FLASH_OUTPUT_USD_PER_1M = 0.30
ANTHROPIC_SONNET_INPUT_USD_PER_1M = 3.0
ANTHROPIC_SONNET_OUTPUT_USD_PER_1M = 15.0
ANTHROPIC_HAIKU_INPUT_USD_PER_1M = 0.80
ANTHROPIC_HAIKU_OUTPUT_USD_PER_1M = 4.0

# 기본 모델명 (slice 1 part 2 사후 진단 결과 채택)
# - gemini-2.0-flash: free tier limit=0 (사용 불가). Slice 1 9/9 폴백 원인.
# - gemini-2.5-flash: free tier 정상 동작 확인 (2026-04-29 진단).
GEMINI_MODEL = "gemini-2.5-flash"
ANTHROPIC_MODEL = "claude-sonnet-4-5"
ANTHROPIC_SONNET_MODEL = "claude-sonnet-4-5"
ANTHROPIC_HAIKU_MODEL = "claude-haiku-4-5"

# Anthropic 모델별 단가 매핑 (model 문자열 → (input, output) 단가)
_ANTHROPIC_PRICING: dict[str, tuple[float, float]] = {
    ANTHROPIC_SONNET_MODEL: (
        ANTHROPIC_SONNET_INPUT_USD_PER_1M,
        ANTHROPIC_SONNET_OUTPUT_USD_PER_1M,
    ),
    ANTHROPIC_HAIKU_MODEL: (
        ANTHROPIC_HAIKU_INPUT_USD_PER_1M,
        ANTHROPIC_HAIKU_OUTPUT_USD_PER_1M,
    ),
}


def _classify_gemini_error(exc: Exception) -> Exception:
    """
    Gemini 신 SDK 예외를 통합 예외 계층으로 매핑.

    신 SDK는 google.genai.errors.* 클래스를 사용하지만 버전별로 시그니처가
    다를 수 있어, 클래스명/메시지 문자열 기반으로 1차 분류한다.
    """
    cls_name = type(exc).__name__.lower()
    msg = str(exc).lower()

    if (
        "ratelimit" in cls_name
        or "resourceexhausted" in cls_name
        or "quota" in msg
        or "rate limit" in msg
    ):
        return LLMRateLimitError(str(exc))
    if (
        "timeout" in cls_name
        or "deadlineexceeded" in cls_name
        or "timeout" in msg
        or "deadline" in msg
    ):
        return LLMTimeoutError(str(exc))
    if (
        "permission" in cls_name
        or "unauthenticated" in cls_name
        or "api key" in msg
        or "unauthorized" in msg
    ):
        return LLMAuthError(str(exc))
    if "invalidargument" in cls_name or "badrequest" in cls_name or "invalid" in msg:
        return LLMInvalidPromptError(str(exc))
    return exc


def _classify_anthropic_error(exc: Exception) -> Exception:
    """Anthropic SDK 예외를 통합 예외 계층으로 매핑."""
    # 클래스 임포트는 lazy (anthropic 버전 호환성). 매핑은 클래스명 기반.
    cls_name = type(exc).__name__

    if cls_name == "RateLimitError":
        return LLMRateLimitError(str(exc))
    if cls_name in ("APITimeoutError", "APIConnectionError"):
        return LLMTimeoutError(str(exc))
    if cls_name == "AuthenticationError":
        return LLMAuthError(str(exc))
    if cls_name in ("BadRequestError", "UnprocessableEntityError"):
        return LLMInvalidPromptError(str(exc))
    return exc


class LLMClient:
    """
    Gemini Flash + Anthropic Sonnet 통합 wrapper.

    - per-request 인스턴스화 권장 (singleton 금지, §3.1 자명 선언 #1).
    - 1회 재시도 + 폴백 (RateLimit/Timeout만, §1.2.1).
    - 비용 가드 (settings.LLM_BUDGET_MAX_CALLS, 인스턴스별, §1.2.3).
    - 응답: LLMResponse Pydantic.
    """

    def __init__(self) -> None:
        self._call_count: int = 0
        self._budget_max: int = settings.LLM_BUDGET_MAX_CALLS

    # ------------------------------------------------------------
    # public
    # ------------------------------------------------------------

    def complete(
        self,
        prompt: str,
        provider: Literal["gemini", "anthropic"] = "gemini",
        max_tokens: int = 2000,
        model: str | None = None,
        system: str | None = None,
        entry_point: str | None = None,
    ) -> LLMResponse:
        """
        LLM 호출. 폴백·가드 포함.

        Args:
            prompt: 유저 메시지. system이 None이면 시스템+유저 합쳐진 단일
                prompt 문자열로 취급 (기존 동작 유지).
            provider: "gemini" (기본) 또는 "anthropic" (Sonnet/Haiku 공통 라벨).
            max_tokens: 응답 최대 토큰.
            model: provider 내부 모델 변형 지정.
            system: (Slice 7 Part 4 #19) Anthropic system 인자로 별도 전달.
                None이면 기존 동작 (prompt 단일 문자열 그대로). Gemini는
                현재 system을 별도로 받지 않으므로 prompt 앞에 prepend.
            entry_point: (Slice 16 Step 0-A #68) 호출 진입점 식별자 ("e1"~"e6" 등).
                cost_ledger의 entry_point 컬럼에 그대로 기록. None이면 종전과 동일
                ledger 행에 null 기록 (backward-compat).

        Returns:
            LLMResponse (text + 메타데이터).

        Raises:
            LLMBudgetExceededError: 비용 가드 발동.
            LLMAuthError, LLMInvalidPromptError: 폴백 안 함, 호출자로 raise.
            LLMRateLimitError, LLMTimeoutError: 1차 + 폴백 모두 실패한 경우.
        """
        # 1. 비용 가드 — 인스턴스 카운터 + 글로벌 CostGuard 호출 전 차단.
        #    Slice 8 #33: guard.record_llm_call()로 두 카운터 +1 + 두 check 한 번에 처리.
        if self._call_count >= self._budget_max:
            raise LLMBudgetExceededError(
                f"호출 {self._call_count}회 도달, 가드 임계 {self._budget_max}"
            )
        from apps.portfolio.llm.cost_guard import CostGuard

        guard = CostGuard.get_instance()
        guard.record_llm_call()  # 두 카운터 ++ + per_instance/per_slice check

        # 2. 1차 시도 + 1회 재시도
        try:
            response = self._call_with_retry(
                provider, prompt, max_tokens, model, system
            )
        except (LLMRateLimitError, LLMTimeoutError):
            # 3. 폴백 시도 (반대 provider, 모델은 폴백 측 기본값)
            fallback_provider: Literal["gemini", "anthropic"] = (
                "anthropic" if provider == "gemini" else "gemini"
            )
            response = self._call_with_retry(
                fallback_provider, prompt, max_tokens, model=None, system=system
            )
            response.fallback_from = provider

        # 4. 글로벌 CostGuard 비용/모델 기록 (카운트는 step 1에서 이미 처리, 중복 방지)
        guard.record_response(cost_usd=response.cost_usd, model=response.model)

        # 5. cost ledger append (Slice 14 #63, append-only, 차단 동작 영향 없음).
        #    이중 방어: append_call 내부에서 흡수하지만, import/patch 실패 등 모든
        #    예외를 여기서도 한 번 더 차단 — ledger는 보조 장치, 본 흐름 보호 최우선.
        try:
            from apps.portfolio.llm.cost_ledger import append_call as _ledger_append

            _ledger_append(
                slice_id=guard.slice_id,
                entry_point=entry_point,  # Slice 16 #68: caller가 명시한 진입점 그대로 기록.
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
                fallback_from=response.fallback_from,
            )
        except Exception:  # noqa: BLE001 — 보조 장치, 본 흐름 보호 최우선.
            pass
        return response

    # ------------------------------------------------------------
    # internals
    # ------------------------------------------------------------

    def _call_with_retry(
        self,
        provider: Literal["gemini", "anthropic"],
        prompt: str,
        max_tokens: int,
        model: str | None,
        system: str | None = None,
    ) -> LLMResponse:
        """1회 재시도 포함 단일 provider 호출."""
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                return self._call(provider, prompt, max_tokens, model, system)
            except (LLMRateLimitError, LLMTimeoutError) as exc:
                last_exc = exc
                if attempt == 1:
                    raise
        # for-loop이 정상 종료되는 경로는 없지만 mypy 안심용.
        assert last_exc is not None
        raise last_exc

    def _call(
        self,
        provider: Literal["gemini", "anthropic"],
        prompt: str,
        max_tokens: int,
        model: str | None,
        system: str | None = None,
    ) -> LLMResponse:
        """단일 provider 호출 (1회). _call_count 증분."""
        self._call_count += 1
        start = time.time()
        if provider == "gemini":
            # Gemini는 system instruction을 SDK가 받지 않으므로 prompt 앞에 prepend.
            effective_prompt = f"{system}\n\n{prompt}" if system else prompt
            return self._call_gemini(effective_prompt, max_tokens, start)
        if provider == "anthropic":
            anthropic_model = model or ANTHROPIC_MODEL
            return self._call_anthropic(
                prompt, max_tokens, start, anthropic_model, system
            )
        raise LLMInvalidPromptError(f"Unknown provider: {provider}")

    def _call_gemini(
        self,
        prompt: str,
        max_tokens: int,
        start: float,
    ) -> LLMResponse:
        """Gemini Flash 호출 (신 SDK) — shared/llm complete() 경유(슬라이스 ④, IDENTICAL).

        config는 max_output_tokens 단일 노브(temperature/mime/system 미설정) → complete()가
        GenerateContentConfig(max_output_tokens=max_tokens) 동일 생성. 응답은 portfolio
        LLMResponse로 매핑하고 cost는 자체 단가 상수로 동일 계산(행위 보존). 예외는 complete()가
        분류한 LLMError를 _classify_gemini_error가 재매핑(클래스명 일치 → 동일 타입).
        """
        try:
            response = complete(
                prompt,
                provider="gemini",
                model=GEMINI_MODEL,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            raise _classify_gemini_error(exc) from exc

        text = getattr(response, "text", "") or ""
        input_tokens = int(getattr(response, "input_tokens", 0) or 0)
        output_tokens = int(getattr(response, "output_tokens", 0) or 0)
        cost_usd = (
            input_tokens / 1_000_000 * GEMINI_FLASH_INPUT_USD_PER_1M
            + output_tokens / 1_000_000 * GEMINI_FLASH_OUTPUT_USD_PER_1M
        )
        latency_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            text=text,
            provider="gemini",
            model=GEMINI_MODEL,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

    def _call_anthropic(
        self,
        prompt: str,
        max_tokens: int,
        start: float,
        model: str = ANTHROPIC_MODEL,
        system: str | None = None,
    ) -> LLMResponse:
        """Anthropic 호출. Sonnet/Haiku 등 model로 변형 지정.

        system: None이면 messages.create에 전달하지 않아 기존 동작 그대로
        (IDENTICAL hash KPI 보호). 명시되면 Anthropic SDK의 system 인자로
        별도 전달.

        슬라이스 ③a #2: 직접 `Anthropic().messages.create` → shared/llm `complete(provider="anthropic")`
        경유(코어 AnthropicProvider.generate 재사용, 신설 아님). wire IDENTICAL(model·max_tokens·
        messages·system[옵션] byte 동일, temperature/stop/tools 미주입 재도출 입증). 코어가 첫 text 블록
        추출 + usage 정규화(.input_tokens/.output_tokens) → cost는 자체 단가 상수로 동일 계산(행위 보존,
        _call_gemini 동형). 예외는 코어 분류 LLMError를 _classify_anthropic_error가 재매핑(클래스명 일치).
        """
        try:
            response = complete(
                prompt,
                provider="anthropic",
                model=model,
                max_tokens=max_tokens,
                system=system,
            )
        except Exception as exc:  # noqa: BLE001
            raise _classify_anthropic_error(exc) from exc

        text = getattr(response, "text", "") or ""
        input_tokens = int(getattr(response, "input_tokens", 0) or 0)
        output_tokens = int(getattr(response, "output_tokens", 0) or 0)
        # 모델별 단가 매핑. 미등록 모델은 Sonnet 단가 기본값.
        in_rate, out_rate = _ANTHROPIC_PRICING.get(
            model,
            (ANTHROPIC_SONNET_INPUT_USD_PER_1M, ANTHROPIC_SONNET_OUTPUT_USD_PER_1M),
        )
        cost_usd = (
            input_tokens / 1_000_000 * in_rate + output_tokens / 1_000_000 * out_rate
        )
        latency_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            text=text,
            provider="anthropic",
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
