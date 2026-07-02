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

from typing import Optional, Tuple, Union

from packages.shared.llm.policy import cost as cost_policy
from packages.shared.llm.policy.circuit import awith_circuit, with_circuit
from packages.shared.llm.policy.escape import escape_untrusted
from packages.shared.llm.policy.retry import awith_retry, with_retry
from packages.shared.llm.providers import get_provider
from packages.shared.llm.types import (
    LLMRateLimitError,
    LLMRawResponse,
    LLMResponse,
    LLMTimeoutError,
    StreamFinal,
)


def complete(
    prompt: Union[str, list],
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

    contents 인터페이스(슬라이스 ②c): `prompt`가 `str`이면 기존 단일-str 경로(byte 불변).
    `str`이 아니면(예 list[Part]/[Content]) **멀티파트 경로** — 코어는 변형 0으로 provider에
    불투명 pass-through(평탄화·concat·래핑 없음 → genai wire byte 동일). sync `complete()` 전용
    (acomplete/astream/anthropic 미지원, 범위 밖). escape는 str 신뢰경계 전용.
    """
    # ── 정책 1: escape(신뢰경계) — escape=True일 때만 prompt 변환 ──────────
    # 단일-str 경로는 verbatim 보존. 멀티파트는 추가 분기로만 수용(평탄화 0).
    if isinstance(prompt, str):
        effective_prompt = escape_untrusted(prompt) if escape else prompt
    else:
        if escape:
            raise NotImplementedError(
                "multipart contents에 escape 미지원 — ②c 범위 밖(escape는 str 전용)."
            )
        effective_prompt = prompt

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

    return _finalize(prov_name, resolved_model, raw, fallback_from, cost_track=cost_track)


def _finalize(
    prov_name: str,
    resolved_model: str,
    raw: LLMRawResponse,
    fallback_from: Optional[str],
    *,
    cost_track: bool,
) -> LLMResponse:
    """cost 계산·기록 + LLMResponse 조립 — sync/async 후처리 단일 출처(복제 0)."""
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


async def acomplete(
    prompt: str,
    *,
    provider: str = "gemini",
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[str] = None,
    extra: Optional[dict] = None,
    circuit: Optional[str] = None,
    escape: bool = False,
    retries: int = 0,
    cost_track: bool = False,
    fallback: Optional[str] = None,
) -> LLMResponse:
    """complete()의 async 동형 (슬라이스 ②b) — aio provider 경로.

    시그니처·기본값(전부 off)·정책 순서(escape → retry(circuit(agenerate)) → cost)는 sync와 동형.
    provider 조립은 agenerate가 sync generate와 동일 헬퍼 경유 → 하부 config byte 동일.
    소비처 0으로 land — 이관은 후속 Part. (anthropic agenerate는 ③까지 NotImplementedError.)
    """
    # ── 정책 1: escape(신뢰경계) — sync와 동일 순수 변환 ──────────────────
    effective_prompt = escape_untrusted(prompt) if escape else prompt

    async def _run(prov_name: str, used_model: Optional[str]) -> Tuple[str, str, LLMRawResponse]:
        prov = get_provider(prov_name)

        async def _gen() -> LLMRawResponse:
            return await prov.agenerate(
                effective_prompt,
                model=used_model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
                extra=extra,
            )

        # ── 정책 2·3: retry( circuit( agenerate ) ) — 각각 인자 있을 때만 (async 동형) ──
        thunk = _gen
        if circuit is not None:
            inner = thunk
            thunk = lambda: awith_circuit(inner, name=circuit)  # noqa: E731
        if retries > 0:
            raw = await awith_retry(thunk, retries=retries)
        else:
            raw = await thunk()
        return prov.name, (used_model or prov.default_model), raw

    fallback_from: Optional[str] = None
    try:
        prov_name, resolved_model, raw = await _run(provider, model)
    except (LLMRateLimitError, LLMTimeoutError):
        if not fallback:
            raise
        fallback_from = provider
        prov_name, resolved_model, raw = await _run(fallback, None)

    return _finalize(prov_name, resolved_model, raw, fallback_from, cost_track=cost_track)


async def astream(
    prompt: str,
    *,
    provider: str = "gemini",
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[str] = None,
    extra: Optional[dict] = None,
    circuit: Optional[str] = None,
    escape: bool = False,
    retries: int = 0,
    cost_track: bool = False,
    fallback: Optional[str] = None,
):
    """스트리밍 async 진입점 (슬라이스 ②b-stream + 슬라이스 ④ streaming CB 흡수).

    조립은 generate/agenerate와 동일 헬퍼(provider 내부) → 하부 config byte 동일. 청크는 **원형 그대로**
    yield(재청크·뭉개기 0). escape(prompt) + cost(스트림 완료 시 집계) + circuit(셋업만 보호) 지원.

    circuit(슬라이스 ④): streaming CB — 셋업(스트림 오픈 = provider.aopen_stream)만 named CB로 감싼다
    (OPEN 사전체크 + 실패/성공 집계). 청크 iteration은 **CB 바깥**(원본 #12 `cb.acall(generate_content_stream)`
    동형 — 셋업만 보호, 청크 읽기 실패는 미집계, raw 전파). CB 파라미터(failure_threshold·retry_attempts 등)는
    `get_circuit` 레지스트리 소유 — 소비자가 사전 등록(#10 옵션 A: 파라미터 소비자 존치).

    문서화된 gap(억지 구현 금지): streaming retry/fallback은 코어 미흡수 — 설정 시 NotImplementedError로
    명시 차단(조용한 no-op 금지). anthropic astream/aopen_stream은 슬라이스 ③까지 NotImplementedError.
    """
    if retries > 0:
        raise NotImplementedError(
            "streaming retry는 코어 미흡수(gap) — 소비자 소유. ②b-stream."
        )
    if fallback is not None:
        raise NotImplementedError("streaming fallback 미지원(gap). ②b-stream.")

    # ── 정책 1: escape(신뢰경계) — non-stream과 동일 순수 변환 ────────────
    effective_prompt = escape_untrusted(prompt) if escape else prompt
    prov = get_provider(provider)

    # ── 정책 2: circuit — 셋업(스트림 오픈)만 CB 보호, 청크 읽기는 CB 바깥(#12 동형) ──
    # circuit=None: provider.astream 직접(셋업+iteration 융합, ②b-stream 동작).
    # circuit 설정: aopen_stream(셋업)만 awith_circuit으로 감싸 OPEN 사전체크·실패 집계 →
    # 반환된 raw iterator를 아래 단일 루프에서 CB 바깥으로 소비(읽기 실패 미집계, raw 전파).
    if circuit is not None:
        async def _open():
            return await prov.aopen_stream(
                effective_prompt,
                model=model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
                extra=extra,
            )

        stream = await awith_circuit(_open, name=circuit)
    else:
        stream = prov.astream(
            effective_prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            extra=extra,
        )

    last_input_tokens = 0
    last_output_tokens = 0
    async for chunk in stream:
        # cost 누적용 usage 추적 — 청크 변형 0(원형 그대로 통과).
        # gemini: raw 청크의 usage_metadata(#12 IDENTICAL, 경로 불변).
        usage = getattr(chunk, "usage_metadata", None)
        if usage is not None:
            last_input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
            last_output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        # anthropic(③b): 정규화 종단 StreamFinal에서 usage 흡수(gemini 청크는 해당 없음).
        elif isinstance(chunk, StreamFinal):
            last_input_tokens = chunk.input_tokens
            last_output_tokens = chunk.output_tokens
        yield chunk

    # ── 정책 4: cost 기록 — cost_track=True일 때만, 스트림 완료 시점 집계 ──
    if cost_track:
        resolved_model = model or prov.default_model
        cost_usd = cost_policy.compute_cost(
            prov.name, resolved_model, last_input_tokens, last_output_tokens
        )
        cost_policy.record_cost(
            prov.name, resolved_model, last_input_tokens, last_output_tokens, cost_usd
        )
