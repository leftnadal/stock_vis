"""complete() — 27 소비처가 통과할 단일 LLM 진입점. 정책 형태 B(파라미터 토글, 기본 off).

★ 정책 적용 순서를 여기서 고정한다(소비처는 순서를 바꿀 수 없다 — B의 핵심 가치):

    escape → retry( circuit( provider.generate ) ) → cost

기본값 전부 off → 인자 없는 호출 = 순수 generate = 가장 얇은 현행 동작 재현(IDENTICAL).
  circuit=None  → CB 미적용 (현행 25곳 재현)
  escape=False  → 입력 직접 주입 (현행 재현)
  retries=0     → 재시도 없음 (현행 재현)
  cost_track=False → 기록 안 함 (현행 재현)
  fallback=None → 교차-provider 폴백 없음 (있을 때만 베이스 #1 폴백)
"""

from __future__ import annotations

from typing import Optional, Tuple

from packages.shared.llm.policy import cost as cost_policy
from packages.shared.llm.policy.circuit import with_circuit
from packages.shared.llm.policy.escape import escape_untrusted
from packages.shared.llm.policy.retry import with_retry
from packages.shared.llm.providers import get_provider
from packages.shared.llm.types import (
    LLMRateLimitError,
    LLMRawResponse,
    LLMResponse,
    LLMTimeoutError,
)


def complete(
    prompt: str,
    *,
    provider: str = "gemini",
    model: Optional[str] = None,
    system: Optional[str] = None,
    # ── 생성 config: 공통 노브(명시, provider-agnostic) ──
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[str] = None,
    # ── provider 고유 노브(extra, passthrough) — gemini: GenerateContentConfig에 merge ──
    extra: Optional[dict] = None,
    # ── 정책(슬라이스 ① 그대로, 기본 off) ──
    circuit: Optional[str] = None,
    escape: bool = False,
    retries: int = 0,
    cost_track: bool = False,
    fallback: Optional[str] = None,
) -> LLMResponse:
    """단일 LLM 진입점. 생성 config 배치 규칙:
      명시 노브(temperature·max_tokens·response_format) = 모든 provider 공통 생성 파라미터.
      extra(dict) = 그 provider 고유 노브(gemini thinking_config·top_p 등).
    모든 신규 노브 기본 None → 인자 없는 호출 = 슬라이스 ① 동작(노브 미설정, provider 기본).
    """
    # ── 정책 1: escape(신뢰경계) — escape=True일 때만 prompt 변환 ──────────
    effective_prompt = escape_untrusted(prompt) if escape else prompt

    def _run(prov_name: str, used_model: Optional[str]) -> Tuple[str, str, LLMRawResponse]:
        prov = get_provider(prov_name)

        def _gen() -> LLMRawResponse:
            return prov.generate(
                effective_prompt,
                model=used_model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
                extra=extra,
            )

        # ── 정책 2·3: retry( circuit( generate ) ) — 각각 인자 있을 때만 ──
        thunk = _gen
        if circuit is not None:
            inner = thunk
            thunk = lambda: with_circuit(inner, name=circuit)  # noqa: E731
        if retries > 0:
            raw = with_retry(thunk, retries=retries)
        else:
            raw = thunk()
        return prov.name, (used_model or prov.default_model), raw

    fallback_from: Optional[str] = None
    try:
        prov_name, resolved_model, raw = _run(provider, model)
    except (LLMRateLimitError, LLMTimeoutError):
        if not fallback:
            raise
        # 베이스 #1 폴백: 반대 provider, 모델은 폴백 측 기본값(model=None).
        fallback_from = provider
        prov_name, resolved_model, raw = _run(fallback, None)

    cost_usd = cost_policy.compute_cost(
        prov_name, resolved_model, raw.input_tokens, raw.output_tokens
    )

    # ── 정책 4: cost 기록 — cost_track=True일 때만 ───────────────────────
    if cost_track:
        cost_policy.record_cost(
            prov_name, resolved_model, raw.input_tokens, raw.output_tokens, cost_usd
        )

    return LLMResponse(
        text=raw.text,
        provider=prov_name,
        model=resolved_model,
        latency_ms=raw.latency_ms,
        input_tokens=raw.input_tokens,
        output_tokens=raw.output_tokens,
        cost_usd=cost_usd,
        fallback_from=fallback_from,
    )
