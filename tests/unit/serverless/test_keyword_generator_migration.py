"""슬라이스 ④ Part ①-aio KeywordGeneratorService (_call_llm aio + _call_llm_sync sync) 이관 — IDENTICAL.

단일 client를 sync+aio가 공유했으므로 통째 이관: aio→acomplete(), sync→complete().
양쪽이 _llm_kwargs() 단일 출처를 공유 → 두 경로의 GenerateContentConfig byte 동일.
하부 genai config(system_instruction·max_output_tokens·temperature·thinking_budget)·contents·model 동일.
"""

import pytest

from services.serverless.services.keyword_generator import KeywordGeneratorService


@pytest.fixture
def captured_dual(monkeypatch):
    """genai.Client patch — sync(.models)·async(.aio.models) 양쪽 캡처."""
    cap: dict = {}

    class _Resp:
        text = '["키워드"]'

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

    monkeypatch.setattr(real_genai, "Client", _Client)
    return cap


def _assert_config(c):
    assert c.system_instruction == "SYS"
    assert c.max_output_tokens == 8000  # MAX_TOKENS
    assert c.temperature == 0.3
    assert c.thinking_config.thinking_budget == 0
    assert getattr(c, "response_mime_type", None) is None


@pytest.mark.asyncio
async def test_keyword_generator_sync_aio_identical(captured_dual, settings, monkeypatch):
    settings.GEMINI_API_KEY = "fake-key"
    svc = KeywordGeneratorService()
    monkeypatch.setattr(svc.prompt_builder, "get_system_prompt", lambda: "SYS")

    await svc._call_llm("USER")  # aio → acomplete()
    svc._call_llm_sync("USER")  # sync → complete()

    s, a = captured_dual["sync"], captured_dual["async"]
    _assert_config(s["config"])
    _assert_config(a["config"])
    assert s["config"] == a["config"]  # 두 경로 config byte 동일(단일 출처 _llm_kwargs)
    assert s["model"] == a["model"] == "gemini-2.5-flash"
    assert s["contents"] == a["contents"] == "USER"
