"""슬라이스 ④ parse_filter_with_llm 이관 — IDENTICAL.

genai 직접호출 → complete() 경유 후에도 GenerateContentConfig byte 동일
(response_mime_type·temperature·thinking_budget, max_output_tokens 미설정) 검증. contents/model 동일.
키 누락 시 graceful error 반환(현행 보존)도 확인.
"""

import pytest

from services.validation.services.llm_peer_filter import (
    FILTER_PARSING_PROMPT,
    parse_filter_with_llm,
)


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = '{"market_cap_min": 1000000000}'

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


def test_llm_peer_filter_migration_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"
    expected_prompt = FILTER_PARSING_PROMPT.format(
        user_input="대형주만", symbol="AAPL", sector="Technology"
    )

    result = parse_filter_with_llm("대형주만", "AAPL", "Technology")

    cfg = captured_gemini["config"]
    assert cfg.response_mime_type == "application/json"  # response_format="json" 매핑
    assert cfg.temperature == 0.1
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "max_output_tokens", None) is None  # 미설정(Gemini 폴백 없음)
    assert getattr(cfg, "system_instruction", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_prompt
    assert result == {"market_cap_min": 1000000000}  # json.loads 동일


def test_llm_peer_filter_missing_key_graceful(settings):
    """키 누락 시 graceful error dict 반환(현행 보존, raise 아님)."""
    settings.GEMINI_API_KEY = None
    result = parse_filter_with_llm("대형주만", "AAPL", "Technology")
    assert result == {"error": "GEMINI_API_KEY not configured"}
