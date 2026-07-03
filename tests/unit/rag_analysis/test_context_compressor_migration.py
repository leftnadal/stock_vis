"""슬라이스 ④ Part ①-aio ContextCompressor._compress_single 이관 — IDENTICAL (CB 존치).

aio 직접호출(cb.acall(client.aio.models.generate_content)) → cb.acall(acomplete) 옵션 A.
circuit breaker(gemini_compress 5/60)는 소비자단 존치(실 CB 통과), 감싸는 대상만 acomplete로 교체.
하부 genai config(max_output_tokens·temperature·thinking_budget)·contents·model byte 동일.
"""

import pytest

from services.rag_analysis.services.context_compressor import ContextCompressor


@pytest.fixture
def captured_aio(monkeypatch):
    cap: dict = {}

    class _Usage:
        prompt_token_count = 4
        candidates_token_count = 8

    class _Resp:
        text = "압축된 요약"
        usage_metadata = _Usage()

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
async def test_context_compressor_migration_identical(captured_aio, settings):
    settings.GEMINI_API_KEY = "fake-key"
    svc = ContextCompressor()
    assert svc._llm_enabled is True  # 게이팅 보존

    doc = {"id": "d1", "title": "AAPL", "content": "Apple earnings strong"}
    text = svc._get_document_text(doc)
    expected_contents = svc.COMPRESSION_PROMPT.format(question="질문?", document=text)

    result = await svc._compress_single(doc, "질문?")

    cfg = captured_aio["config"]
    assert cfg.max_output_tokens == 100  # MAX_TOKENS_PER_DOC
    assert cfg.temperature == 0.3
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_aio["model"] == "gemini-2.5-flash"
    assert captured_aio["contents"] == expected_contents  # CB 경유해도 contents 불변
    assert result["compressed"] == "압축된 요약"  # 출력 동일(.strip())
