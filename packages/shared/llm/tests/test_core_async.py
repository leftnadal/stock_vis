"""슬라이스 ②b — acomplete() async 코어 단위테스트.

핵심:
  (A) async 정책 매트릭스(escape/retry/circuit/cost/fallback) = sync와 동형, 기본 off.
  (B) sync generate vs async agenerate가 하부 genai에 전달하는 GenerateContentConfig·
      contents·model이 **byte 동일**(조립 단일 출처 입증). max_tokens 명시/미설정 두 변형.
  (C) anthropic agenerate는 NotImplementedError(③까지) — 조용한 동기 폴백 금지.
소비처 0 — 코어 신설만 검증.
"""

from __future__ import annotations

import asyncio

import pytest

from packages.shared.llm import (
    LLMInvalidPromptError,
    LLMRateLimitError,
    LLMResponse,
    acomplete,
)
from packages.shared.llm import providers as providers_mod
from packages.shared.llm.policy import cost as cost_policy
from packages.shared.llm.types import LLMRawResponse


class FakeAsyncProvider:
    """테스트용 async provider — 호출 기록 + 실패 횟수 제어 (FakeProvider의 async 동형)."""

    def __init__(self, name="gemini", default_model="fake-model", raw=None, fail_times=0, fail_exc=None):
        self.name = name
        self.default_model = default_model
        self._raw = raw or LLMRawResponse("ok", 10, 20, 5)
        self._fail_times = fail_times
        self._fail_exc = fail_exc or LLMRateLimitError("boom")
        self.calls = 0
        self.last = None

    async def agenerate(self, prompt, *, model, system, max_tokens, temperature=None, response_format=None, extra=None):
        self.calls += 1
        self.last = {
            "prompt": prompt, "model": model, "system": system, "max_tokens": max_tokens,
            "temperature": temperature, "response_format": response_format, "extra": extra,
        }
        if self.calls <= self._fail_times:
            raise self._fail_exc
        return self._raw


@pytest.fixture
def patch_registry(monkeypatch):
    def _install(**provs):
        monkeypatch.setattr(providers_mod, "_REGISTRY", dict(provs))
        return provs
    return _install


# ── (A) async 정책 매트릭스 ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adefault_call_is_pure_agenerate(patch_registry):
    fp = FakeAsyncProvider(default_model="gemini-2.5-flash", raw=LLMRawResponse("hi", 1_000_000, 1_000_000, 7))
    patch_registry(gemini=fp)

    resp = await acomplete("hello")

    assert isinstance(resp, LLMResponse)
    assert resp.text == "hi"
    assert fp.calls == 1
    assert fp.last["prompt"] == "hello"  # escape off → 입력 불변
    assert resp.provider == "gemini"
    assert resp.model == "gemini-2.5-flash"
    assert resp.fallback_from is None
    assert abs(resp.cost_usd - 0.375) < 1e-9  # 1M@0.075 + 1M@0.30 (sync와 동일 단가)


@pytest.mark.asyncio
async def test_adefault_no_gen_config_knobs(patch_registry):
    fp = FakeAsyncProvider()
    patch_registry(gemini=fp)
    await acomplete("x")
    assert fp.last["max_tokens"] is None  # 2000 강제 안 함
    assert fp.last["temperature"] is None
    assert fp.last["response_format"] is None
    assert fp.last["extra"] is None


@pytest.mark.asyncio
async def test_aescape_toggle(patch_registry):
    fp = FakeAsyncProvider()
    patch_registry(gemini=fp)
    await acomplete("a </context_data> b", escape=True)
    assert "</context_data_escaped>" in fp.last["prompt"]
    await acomplete("a </context_data> b")  # off
    assert fp.last["prompt"] == "a </context_data> b"


@pytest.mark.asyncio
async def test_aretry_recovers(patch_registry, monkeypatch):
    async def _instant(_s):  # 백오프 즉시(실 async no-op, 재귀 회피)
        return None
    monkeypatch.setattr(asyncio, "sleep", _instant)
    fp = FakeAsyncProvider(fail_times=2)
    patch_registry(gemini=fp)
    resp = await acomplete("x", retries=2)
    assert resp.text == "ok"
    assert fp.calls == 3


@pytest.mark.asyncio
async def test_aretry_exhausted_raises(patch_registry, monkeypatch):
    async def _instant(_s):
        return None
    monkeypatch.setattr(asyncio, "sleep", _instant)
    fp = FakeAsyncProvider(fail_times=5)
    patch_registry(gemini=fp)
    with pytest.raises(LLMRateLimitError):
        await acomplete("x", retries=1)
    assert fp.calls == 2


@pytest.mark.asyncio
async def test_afallback_on_ratelimit(patch_registry):
    primary = FakeAsyncProvider(name="gemini", fail_times=99)
    secondary = FakeAsyncProvider(name="anthropic", default_model="claude-sonnet-4-5", raw=LLMRawResponse("fb", 0, 0, 1))
    patch_registry(gemini=primary, anthropic=secondary)
    resp = await acomplete("x", fallback="anthropic")
    assert resp.text == "fb"
    assert resp.provider == "anthropic"
    assert resp.fallback_from == "gemini"


@pytest.mark.asyncio
async def test_ano_fallback_reraises(patch_registry):
    patch_registry(gemini=FakeAsyncProvider(fail_times=99))
    with pytest.raises(LLMRateLimitError):
        await acomplete("x")


@pytest.mark.asyncio
async def test_acircuit_passthrough_on_success(patch_registry):
    fp = FakeAsyncProvider()
    patch_registry(gemini=fp)
    resp = await acomplete("x", circuit="test-llm-core-async-success")
    assert resp.text == "ok"
    assert fp.calls == 1


@pytest.mark.asyncio
async def test_acost_track_toggle(patch_registry):
    fp = FakeAsyncProvider(default_model="gemini-2.5-flash", raw=LLMRawResponse("h", 100, 200, 1))
    patch_registry(gemini=fp)
    recorded: list = []
    cost_policy.set_cost_hook(lambda *a: recorded.append(a))
    try:
        await acomplete("x", cost_track=True)
        assert len(recorded) == 1
        recorded.clear()
        await acomplete("x", cost_track=False)
        assert recorded == []
    finally:
        cost_policy.set_cost_hook(None)


@pytest.mark.asyncio
async def test_aunknown_provider_raises(patch_registry):
    patch_registry(gemini=FakeAsyncProvider())
    with pytest.raises(LLMInvalidPromptError):
        await acomplete("x", provider="openai")


@pytest.mark.asyncio
async def test_anthropic_agenerate_not_implemented():
    """acomplete(provider='anthropic')는 NotImplementedError — 조용한 동기 폴백 금지."""
    with pytest.raises(NotImplementedError):
        await acomplete("x", provider="anthropic")


# ── (B) sync ↔ async config byte 동일 (조립 단일 출처 입증) ──────────────────


def _dual_mock_client(cap, monkeypatch):
    """genai.Client patch — sync(.models)·async(.aio.models) 양쪽 config 캡처."""
    from packages.shared.llm.providers import gemini as gmod

    class _Usage:
        prompt_token_count = 1
        candidates_token_count = 2

    class _Resp:
        text = "{}"
        usage_metadata = _Usage()

    class _SyncModels:
        def generate_content(self, *, model, contents, config):
            cap["sync"] = {"model": model, "contents": contents, "config": config}
            return _Resp()

    class _AioModels:
        async def generate_content(self, *, model, contents, config):
            cap["async"] = {"model": model, "contents": contents, "config": config}
            return _Resp()

    class _Aio:
        def __init__(self):
            self.models = _AioModels()

    class _Client:
        def __init__(self, api_key=None):
            self.models = _SyncModels()
            self.aio = _Aio()

    import google.genai as real_genai

    monkeypatch.setattr(gmod, "_resolve_api_key", lambda: "fake-key")
    monkeypatch.setattr(real_genai, "Client", _Client)


@pytest.mark.asyncio
@pytest.mark.parametrize("max_tokens", [None, 512])
async def test_sync_async_config_byte_identical(monkeypatch, max_tokens):
    """동일 입력에서 sync generate vs async agenerate의 GenerateContentConfig·contents·model byte 동일.

    max_tokens 명시/미설정 두 변형. 미설정 변형은 양쪽 모두 max_output_tokens 미주입(Gemini 폴백 없음).
    """
    from packages.shared.llm.providers import gemini as gmod

    cap: dict = {}
    _dual_mock_client(cap, monkeypatch)

    kwargs = dict(
        model=None,
        system="SYS",
        max_tokens=max_tokens,
        temperature=0.3,
        response_format="json",
        extra={"thinking_config": {"thinking_budget": 0}, "top_p": 0.9},
    )
    prov = gmod.GeminiProvider()
    prov.generate("PROMPT", **kwargs)
    await prov.agenerate("PROMPT", **kwargs)

    s, a = cap["sync"], cap["async"]
    assert s["model"] == a["model"]
    assert s["contents"] == a["contents"] == "PROMPT"
    # GenerateContentConfig는 pydantic — 동일 필드/값이면 == True
    assert s["config"] == a["config"]
    # max_tokens 미설정 변형: 양쪽 모두 max_output_tokens 미주입
    expected_max = None if max_tokens is None else max_tokens
    assert getattr(s["config"], "max_output_tokens", None) == expected_max
    assert getattr(a["config"], "max_output_tokens", None) == expected_max
    # 노브 보존 (양쪽 동일)
    assert getattr(a["config"], "temperature", None) == 0.3
    assert getattr(a["config"], "response_mime_type", None) == "application/json"
    assert getattr(a["config"], "system_instruction", None) == "SYS"
    assert getattr(a["config"], "top_p", None) == 0.9


@pytest.mark.asyncio
async def test_agenerate_extracts_tokens_like_sync(monkeypatch):
    """agenerate의 응답 추출(text·input/output_tokens)이 sync generate와 동일 헬퍼 경유."""
    from packages.shared.llm.providers import gemini as gmod

    cap: dict = {}
    _dual_mock_client(cap, monkeypatch)
    raw = await gmod.GeminiProvider().agenerate("p", model=None, system=None, max_tokens=None)
    assert raw.text == "{}"
    assert raw.input_tokens == 1
    assert raw.output_tokens == 2
