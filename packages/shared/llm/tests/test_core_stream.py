"""슬라이스 ②b-stream — astream() streaming async 코어 단위테스트.

핵심:
  (a) config byte 동일: astream이 generate_content_stream에 넘기는 GenerateContentConfig·contents·
      model이 sync generate와 **동일 조립**(_build_config_kwargs 단일 출처).
  (b) delta 청크 시퀀스 동등성: mock stream의 청크를 astream이 **원형·순서 그대로** yield(재청크·뭉개기 0).
  (c) gap fail-loud: streaming circuit/retry/fallback → NotImplementedError. anthropic astream → NotImplementedError.
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
@pytest.mark.parametrize("kw", [{"circuit": "c"}, {"retries": 1}, {"fallback": "anthropic"}])
async def test_stream_gap_params_raise(kw):
    """(c) streaming circuit/retry/fallback = 문서화된 gap → NotImplementedError(조용한 no-op 금지)."""
    with pytest.raises(NotImplementedError):
        async for _ in astream("x", provider="gemini", **kw):
            pass


@pytest.mark.asyncio
async def test_anthropic_astream_not_implemented():
    """anthropic astream은 ③까지 NotImplementedError(반복 시점)."""
    with pytest.raises(NotImplementedError):
        async for _ in astream("x", provider="anthropic"):
            pass
