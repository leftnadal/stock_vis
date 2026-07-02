"""슬라이스 ④ Part ①-aio EntityExtractor.extract 이관 — IDENTICAL.

aio 직접호출(client.aio.models.generate_content) → acomplete() 경유 후에도 하부 genai에 가던
GenerateContentConfig·contents·model byte 동일(max_output_tokens·temperature·thinking_budget,
system/mime 미설정) 검증. 출력 파싱 동일. 키 없으면 fallback 게이팅 보존.
"""

import pytest

from services.rag_analysis.services.entity_extractor import EntityExtractor


@pytest.fixture
def captured_aio(monkeypatch):
    """google.genai.Client patch — async aio.models.generate_content 캡처."""
    cap: dict = {}

    class _Usage:
        prompt_token_count = 3
        candidates_token_count = 7

    class _Resp:
        text = '{"stocks": ["AAPL"], "metrics": ["실적"], "concepts": [], "timeframe": null}'
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
async def test_entity_extractor_migration_identical(captured_aio, settings):
    settings.GEMINI_API_KEY = "fake-key"
    svc = EntityExtractor()
    assert svc._llm_enabled is True  # 게이팅 플래그 보존
    expected_contents = svc.EXTRACTION_PROMPT.format(question="AAPL 실적 어때?")

    result = await svc.extract("AAPL 실적 어때?")

    cfg = captured_aio["config"]
    assert cfg.max_output_tokens == 200
    assert cfg.temperature == 0.1
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_aio["model"] == "gemini-2.5-flash"
    assert captured_aio["contents"] == expected_contents
    # 출력 파싱 동일
    assert result["stocks"] == ["AAPL"]
    assert result["metrics"] == ["실적"]


def test_entity_extractor_no_key_fallback(settings):
    """키 없으면 fallback 모드(게이팅 보존, LLM 미호출)."""
    settings.GEMINI_API_KEY = None
    settings.GOOGLE_AI_API_KEY = None
    svc = EntityExtractor()
    assert svc._llm_enabled is False
