"""슬라이스 ②b-stream — astream() streaming async 코어 단위테스트.

핵심:
  (a) config byte 동일: astream이 generate_content_stream에 넘기는 GenerateContentConfig·contents·
      model이 sync generate와 **동일 조립**(_build_config_kwargs 단일 출처).
  (b) delta 청크 시퀀스 동등성: mock stream의 청크를 astream이 **원형·순서 그대로** yield(재청크·뭉개기 0).
  (c) gap fail-loud: streaming retry/fallback → NotImplementedError. anthropic astream(③b) → 정규화 델타 yield.
소비처 0 — 코어 신설만 검증.
"""

from __future__ import annotations

import pytest

from packages.shared.llm import astream


class _Usage:
    prompt_token_count = 11
    candidates_token_count = 22


class _Chunk:
    def __init__(self, text, usage=None):
        self.text = text
        self.usage_metadata = usage


def _dual_mock_client(cap, chunks, monkeypatch):
    """genai.Client patch — sync(.models.generate_content) + stream(.aio.models.generate_content_stream)."""
    from packages.shared.llm.providers import gemini as gmod

    class _Resp:
        text = "{}"
        usage_metadata = _Usage()

    class _SyncModels:
        def generate_content(self, *, model, contents, config):
            cap["sync"] = {"model": model, "contents": contents, "config": config}
            return _Resp()

    class _AioModels:
        async def generate_content_stream(self, *, model, contents, config):
            cap["stream"] = {"model": model, "contents": contents, "config": config}

            async def _agen():
                for c in chunks:
                    yield c

            return _agen()

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
@pytest.mark.parametrize("max_tokens", [None, 256])
async def test_stream_config_byte_identical_to_sync(monkeypatch, max_tokens):
    """(a) astream config == sync generate config (동일 _build_config_kwargs). max_tokens 두 변형."""
    from packages.shared.llm.providers import gemini as gmod

    cap: dict = {}
    _dual_mock_client(cap, [_Chunk("x")], monkeypatch)
    kwargs = dict(
        model=None,
        system="SYS",
        max_tokens=max_tokens,
        temperature=0.3,
        response_format="json",
        extra={"thinking_config": {"thinking_budget": 0}, "top_p": 0.9},
    )
    gmod.GeminiProvider().generate("PROMPT", **kwargs)
    async for _ in astream("PROMPT", provider="gemini", **kwargs):
        pass

    s, st = cap["sync"], cap["stream"]
    assert s["model"] == st["model"]
    assert s["contents"] == st["contents"] == "PROMPT"
    assert s["config"] == st["config"]  # GenerateContentConfig byte 동일
    expected_max = None if max_tokens is None else max_tokens
    assert getattr(st["config"], "max_output_tokens", None) == expected_max


@pytest.mark.asyncio
async def test_stream_delta_sequence_preserved(monkeypatch):
    """(b) 청크 경계·순서 그대로 yield — 재청크·버퍼링·뭉개기 0."""
    cap: dict = {}
    chunks = [_Chunk("Hello"), _Chunk(" "), _Chunk("world", usage=_Usage())]
    _dual_mock_client(cap, chunks, monkeypatch)

    out = []
    async for chunk in astream("p", provider="gemini"):
        out.append(chunk)

    assert out == chunks  # 동일 객체·동일 순서(증분 보존)
    assert [c.text for c in out] == ["Hello", " ", "world"]


@pytest.mark.asyncio
async def test_stream_cost_track_at_completion(monkeypatch):
    """cost_track=True면 스트림 완료 시점에 마지막 usage로 1회 집계."""
    from packages.shared.llm.policy import cost as cost_policy

    cap: dict = {}
    chunks = [_Chunk("a"), _Chunk("b", usage=_Usage())]
    _dual_mock_client(cap, chunks, monkeypatch)

    recorded: list = []
    cost_policy.set_cost_hook(lambda *a: recorded.append(a))
    try:
        async for _ in astream("p", provider="gemini", cost_track=True):
            pass
        assert len(recorded) == 1  # 완료 시점 1회
        recorded.clear()
        async for _ in astream("p", provider="gemini"):  # off
            pass
        assert recorded == []
    finally:
        cost_policy.set_cost_hook(None)


@pytest.mark.asyncio
@pytest.mark.parametrize("kw", [{"retries": 1}, {"fallback": "anthropic"}])
async def test_stream_gap_params_raise(kw):
    """(c) streaming retry/fallback = 문서화된 gap → NotImplementedError(조용한 no-op 금지).

    circuit은 슬라이스 ④에서 흡수됨(아래 circuit 테스트군) — 더 이상 gap 아님.
    """
    with pytest.raises(NotImplementedError):
        async for _ in astream("x", provider="gemini", **kw):
            pass


# ─── 슬라이스 ④: streaming circuit 흡수 (셋업만 CB, 청크 읽기는 CB 바깥) ───


@pytest.mark.asyncio
async def test_stream_circuit_success_yields_raw_chunks(monkeypatch):
    """circuit 설정 시 셋업을 CB로 감싸되 청크는 **원형 그대로** yield(재청크 0) + 셋업 실행됨."""
    cap: dict = {}
    chunks = [_Chunk("a"), _Chunk("b", usage=_Usage())]
    _dual_mock_client(cap, chunks, monkeypatch)

    out = []
    async for chunk in astream("p", provider="gemini", circuit="cb_ok_test"):
        out.append(chunk)

    assert out == chunks  # 동일 객체·동일 순서(증분 보존)
    assert cap["stream"]["contents"] == "p"  # 셋업이 CB 경유 후 실행됨


@pytest.mark.asyncio
async def test_stream_circuit_open_raises_before_setup(monkeypatch):
    """CB가 OPEN이면 셋업 전 CircuitBreakerError(사전체크) — #12 except CircuitBreakerError 동형."""
    from packages.shared.api_request.circuit_breaker import (
        CircuitBreakerError,
        get_circuit,
    )

    cap: dict = {}
    _dual_mock_client(cap, [_Chunk("x")], monkeypatch)
    cb = get_circuit("cb_open_test")
    cb._set_open()  # 강제 OPEN
    try:
        with pytest.raises(CircuitBreakerError):
            async for _ in astream("p", provider="gemini", circuit="cb_open_test"):
                pass
        assert "stream" not in cap  # 셋업 미실행(사전체크에서 차단)
    finally:
        cb.reset()


@pytest.mark.asyncio
async def test_stream_circuit_counts_setup_failure_not_iteration(monkeypatch):
    """셋업 실패만 CB 집계, 청크 읽기 실패는 미집계(#12 동형: cb.acall=셋업만 보호)."""
    from django.core.cache import cache

    from packages.shared.api_request.circuit_breaker import get_circuit
    from packages.shared.llm.providers import gemini as gmod

    # (1) 셋업 실패 → CB fail_count 증가 (retry_attempts=1 사전등록 — #12 동형, 빠름)
    async def _boom_open(self, prompt, **kw):
        raise RuntimeError("setup failed")

    monkeypatch.setattr(gmod.GeminiProvider, "aopen_stream", _boom_open)
    cb1 = get_circuit("cb_setup_fail_test", retry_attempts=1)
    cb1.reset()
    with pytest.raises(RuntimeError):
        async for _ in astream("p", provider="gemini", circuit="cb_setup_fail_test"):
            pass
    assert cache.get(cb1._fail_count_key()) == 1  # 셋업 실패 1건 집계
    cb1.reset()

    # (2) 셋업 성공 + 청크 읽기 실패 → CB fail_count 미증가(읽기는 CB 바깥)
    async def _ok_open_then_boom(self, prompt, **kw):
        async def _agen():
            yield _Chunk("a")
            raise RuntimeError("iteration failed")

        return _agen()

    monkeypatch.setattr(gmod.GeminiProvider, "aopen_stream", _ok_open_then_boom)
    cb2 = get_circuit("cb_iter_fail_test", retry_attempts=1)
    cb2.reset()
    with pytest.raises(RuntimeError):
        async for _ in astream("p", provider="gemini", circuit="cb_iter_fail_test"):
            pass
    assert cache.get(cb2._fail_count_key()) in (0, None)  # 청크 읽기 실패는 미집계
    cb2.reset()


@pytest.mark.asyncio
async def test_anthropic_astream_yields_normalized_delta(monkeypatch, settings):
    """anthropic astream(슬라이스 ③b) — StreamDelta*(text) + 종단 StreamFinal(usage) 정규화 yield.

    messages.stream(async with)을 provider 어댑터가 셋업/순회로 분해: text_stream→StreamDelta,
    get_final_message().usage→StreamFinal, __aexit__로 연결 해제.
    """
    settings.ANTHROPIC_API_KEY = "fake-key"
    from packages.shared.llm.types import StreamDelta, StreamFinal

    class _Stream:
        @property
        def text_stream(self):
            async def _g():
                for t in ["He", "llo"]:
                    yield t

            return _g()

        async def get_final_message(self):
            m = type("M", (), {})()
            m.usage = type("U", (), {"input_tokens": 7, "output_tokens": 9})()
            return m

    class _CM:
        async def __aenter__(self):
            return _Stream()

        async def __aexit__(self, *a):
            return None

    class _Msgs:
        def stream(self, **kw):
            return _CM()

    class _Client:
        def __init__(self, api_key=None):
            self.messages = _Msgs()

    import anthropic as real

    monkeypatch.setattr(real, "AsyncAnthropic", _Client)

    out = [c async for c in astream("x", provider="anthropic")]
    deltas = [c.text for c in out if isinstance(c, StreamDelta)]
    finals = [c for c in out if isinstance(c, StreamFinal)]
    assert deltas == ["He", "llo"]  # 재청크·뭉개기 0
    assert len(finals) == 1
    assert (finals[0].input_tokens, finals[0].output_tokens) == (7, 9)
