"""슬라이스 ④ keyword_extractor 이관 — 4노브 IDENTICAL 입증.

genai 직접호출(`self.client.models.generate_content`) → shared/llm `complete()` 경유로
바꾼 뒤에도, provider가 만드는 최종 `GenerateContentConfig`가 현행과 byte 동일
(system_instruction·max_output_tokens·temperature·thinking_budget, response_mime_type 미설정)
임을 genai 호출을 가로채 검증. contents/model 동일.
"""

import json

import pytest

from services.news.services.keyword_extractor import NewsKeywordExtractor


@pytest.fixture
def captured_gemini(monkeypatch):
    """provider의 genai.Client를 가로채 generate_content 인자(config 포함)를 캡처."""
    cap: dict = {}

    class _Usage:
        prompt_token_count = 5
        candidates_token_count = 10

    class _Resp:
        text = json.dumps([{"text": "NVDA 실적 기대", "sentiment": "positive"}])
        usage_metadata = _Usage()

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


def test_keyword_extractor_migration_4knob_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"  # __init__ 키 검증 + provider 해소
    svc = NewsKeywordExtractor()

    # 결정적 입력 — 이관 후에도 프롬프트 불변
    from datetime import date

    target_date = date(2026, 6, 25)
    news_data = [
        {
            "id": "1",
            "title": "NVIDIA beats earnings",
            "summary": "Strong AI chip demand drives revenue.",
            "source": "finnhub",
            "category": "earnings",
            "sentiment_score": 0.8,
            "symbols": ["NVDA"],
        }
    ]
    expected_system = svc._build_system_prompt()
    expected_user = svc._build_user_prompt(news_data, target_date)

    svc._call_llm(news_data, target_date)

    cfg = captured_gemini["config"]
    # ★ 4노브 + contents/model 이 현행 genai 호출과 byte 동일
    assert cfg.system_instruction == expected_system
    assert cfg.max_output_tokens == 6000  # MAX_OUTPUT_TOKENS
    assert cfg.temperature == 0.3  # TEMPERATURE
    assert cfg.thinking_config.thinking_budget == 0  # extra passthrough
    assert getattr(cfg, "response_mime_type", None) is None  # 현행 미설정 보존
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_user  # 프롬프트 불변
