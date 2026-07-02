"""슬라이스 ④ NewsDeepAnalyzer._analyze_single 이관 — 4노브 IDENTICAL.

genai 직접호출 → complete() 경유 후에도 GenerateContentConfig byte 동일
(system_instruction·max_output_tokens[tier별 분기]·temperature·thinking_budget) 검증.
프롬프트 빌더는 결정적이라 고정 문자열로 패치, tier=B → max_output_tokens=4000 분기 보존 확인.
"""

import pytest

from services.news.services.news_deep_analyzer import NewsDeepAnalyzer


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


@pytest.mark.parametrize("tier,expected_max", [("A", 2000), ("B", 4000), ("C", 6000)])
def test_news_deep_analyzer_migration_identical(captured_gemini, settings, monkeypatch, tier, expected_max):
    settings.GEMINI_API_KEY = "fake-key"
    svc = NewsDeepAnalyzer()
    monkeypatch.setattr(svc, "_build_prompt", lambda article, t: "USER_PROMPT")
    monkeypatch.setattr(svc, "_build_system_prompt", lambda t: "SYS_PROMPT")
    monkeypatch.setattr(svc, "_parse_response", lambda raw, t: None)  # validate 경로 회피

    svc._analyze_single(article=object(), tier=tier)

    cfg = captured_gemini["config"]
    assert cfg.system_instruction == "SYS_PROMPT"
    assert cfg.max_output_tokens == expected_max  # tier별 분기 보존
    assert cfg.temperature == 0.3
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == "USER_PROMPT"
