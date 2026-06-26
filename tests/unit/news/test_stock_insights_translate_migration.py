"""슬라이스 ④ StockInsights._translate_keywords_to_korean 이관 — 3노브 IDENTICAL.

genai 직접호출 → complete() 경유 후에도 GenerateContentConfig byte 동일
(max_output_tokens·temperature·thinking_budget, system/mime 미설정) 검증. contents/model 동일.
"""

import pytest

from services.news.services.stock_insights import NewsBasedStockInsights


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = '["엔비디아 실적 상회"]'

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


def test_stock_insights_translate_migration_3knob_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"
    insights = [
        {"keyword_mentions": [{"keyword": "AI chip", "news_headline": "NVIDIA beats earnings"}]}
    ]
    unique_headlines = ["NVIDIA beats earnings"]
    numbered = "\n".join(f"{idx + 1}. {h}" for idx, h in enumerate(unique_headlines))
    expected_prompt = f"""다음 영문 뉴스 헤드라인을 각각 20자 이내의 한국어 키워드로 요약하세요.
투자자 관점에서 핵심 내용만 간결하게 "주어 + 동사" 구조로 작성하세요.
예: "Tesla Q1 deliveries beat" → "테슬라 1분기 인도량 상회"

{numbered}

정확히 {len(unique_headlines)}개의 한국어 키워드를 JSON 배열로만 응답하세요."""

    NewsBasedStockInsights()._translate_keywords_to_korean(insights)

    cfg = captured_gemini["config"]
    assert cfg.max_output_tokens == 500
    assert cfg.temperature == 0.2
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_prompt
    # in-place 적용도 동일 — 번역 결과가 매핑됨
    assert insights[0]["keyword_mentions"][0]["keyword"] == "엔비디아 실적 상회"
