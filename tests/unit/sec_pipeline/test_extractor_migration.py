"""슬라이스 ④ GeminiExtractor (extract_supply_chain·extract_business_model) 이관 — IDENTICAL.

genai 직접호출 2곳 → complete() 경유 후에도 GenerateContentConfig byte 동일
(response_mime_type·temperature·thinking_budget, max_output_tokens 미설정[Gemini라 폴백 없음]) 검증.
키 누락 시 조기 ValueError(현행 보존)도 확인.
"""

import pytest

from services.sec_pipeline.extractor import GeminiExtractor


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = "{}"

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


@pytest.mark.parametrize("method", ["extract_supply_chain", "extract_business_model"])
def test_sec_extractor_migration_identical(captured_gemini, settings, method):
    settings.GEMINI_API_KEY = "fake-key"
    svc = GeminiExtractor()

    getattr(svc, method)("NVDA", "NVIDIA Corp", ["paragraph about suppliers"])

    cfg = captured_gemini["config"]
    assert cfg.response_mime_type == "application/json"  # response_format="json" 매핑
    assert cfg.temperature == 0.1
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "max_output_tokens", None) is None  # 미설정(Gemini 폴백 없음)
    assert getattr(cfg, "system_instruction", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert isinstance(captured_gemini["contents"], str)  # contents=prompt 문자열(불변)


def test_sec_extractor_missing_key_raises(settings):
    """키 누락 시 조기 ValueError(현행 _get_client 동작 보존)."""
    settings.GEMINI_API_KEY = None
    svc = GeminiExtractor()
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        svc.extract_supply_chain("NVDA", "NVIDIA Corp", ["para"])
