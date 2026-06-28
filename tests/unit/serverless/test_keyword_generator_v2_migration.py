"""슬라이스 ④ Part ①-aio EnhancedKeywordGenerator (_call_llm_batch·_call_llm_single) 이관 — IDENTICAL.

aio 직접호출 2개 → acomplete(). 하부 genai config(system_instruction·max_output_tokens·temperature·
thinking_budget)·contents·model byte 동일. batch=MAX_TOKENS(8000), single=2000 분기 보존.
sync 래퍼 generate_keywords_sync_v2(asyncio.run)는 존치(이제 acomplete 구동).
"""

import pytest

from services.serverless.services.keyword_generator_v2 import EnhancedKeywordGenerator


@pytest.fixture
def captured_aio(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = '["키워드"]'

    class _AioModels:
        async def generate_content(self, *, model, contents, config):
            cap["model"] = model
            cap["contents"] = contents
            cap["config"] = config
            return _Resp()

    class _Aio:
        def __init__(self):
            self.models = _AioModels()

    class _Client:
        def __init__(self, api_key=None):
            self.aio = _Aio()

    import google.genai as real_genai

    monkeypatch.setattr(real_genai, "Client", _Client)
    return cap


@pytest.mark.asyncio
async def test_call_llm_batch_migration_identical(captured_aio, settings, monkeypatch):
    settings.GEMINI_API_KEY = "fake-key"
    svc = EnhancedKeywordGenerator()
    monkeypatch.setattr(svc.prompt_builder, "get_system_prompt", lambda mt: "SYS")
    monkeypatch.setattr(svc.prompt_builder, "build_batch_prompt", lambda c, mt: "BATCH_USER")

    await svc._call_llm_batch([{}], "gainers")

    cfg = captured_aio["config"]
    assert cfg.system_instruction == "SYS"
    assert cfg.max_output_tokens == 8000  # MAX_TOKENS (배치)
    assert cfg.temperature == 0.3
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_aio["model"] == "gemini-2.5-flash"
    assert captured_aio["contents"] == "BATCH_USER"


@pytest.mark.asyncio
async def test_call_llm_single_migration_identical(captured_aio, settings, monkeypatch):
    settings.GEMINI_API_KEY = "fake-key"
    svc = EnhancedKeywordGenerator()
    monkeypatch.setattr(svc.prompt_builder, "get_system_prompt", lambda mt: "SYS")
    monkeypatch.setattr(svc.prompt_builder, "build_user_prompt", lambda c: "SINGLE_USER")

    await svc._call_llm_single({}, "gainers")

    cfg = captured_aio["config"]
    assert cfg.system_instruction == "SYS"
    assert cfg.max_output_tokens == 2000  # 단일 종목 분기 보존
    assert cfg.temperature == 0.3
    assert cfg.thinking_config.thinking_budget == 0
    assert captured_aio["model"] == "gemini-2.5-flash"
    assert captured_aio["contents"] == "SINGLE_USER"
