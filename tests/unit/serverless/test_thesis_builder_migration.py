"""슬라이스 ④ ThesisBuilder._call_llm_sync 이관 — 4노브 IDENTICAL.

genai 직접호출 → complete() 경유 후에도 GenerateContentConfig byte 동일
(system_instruction·max_output_tokens·temperature·thinking_budget, response_mime_type 미설정) 검증.
"""

import pytest

from services.serverless.services.thesis_builder import ThesisBuilder


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = "투자 테제 본문"

    class _Models:
        def generate_content(self, *, model, contents, config):
            cap["model"] = model
            cap["contents"] = contents
            cap["config"] = config
            return _Resp()

    class _Client:
        def __init__(self, api_key=None):
            self.models = _Models()

    import google.genai as real_genai

    monkeypatch.setattr(real_genai, "Client", _Client)
    return cap


def test_thesis_builder_migration_4knob_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"
    result = ThesisBuilder()._call_llm_sync("SYS_PROMPT", "USER_PROMPT")

    cfg = captured_gemini["config"]
    assert cfg.system_instruction == "SYS_PROMPT"
    assert cfg.max_output_tokens == 4000  # MAX_TOKENS
    assert cfg.temperature == 0.5  # TEMPERATURE
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "response_mime_type", None) is None  # 현행 미설정 보존(잘림 회피)
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == "USER_PROMPT"
    assert result == "투자 테제 본문"
