"""슬라이스 ④ KeywordGenerationService._call_llm_sync 이관 — IDENTICAL (soft 편차).

원본 contents는 단일 Content(role=user)/단일 Part(text=SYS+prompt). complete()에 concat 문자열을
전달하면 genai가 동일 구조로 정규화 → wire 동일. config 노브(max_output_tokens·temperature·
thinking_budget) byte 동일, system_instruction 미설정 보존. metadata 토큰수도 동일 값 보존.
"""

import pytest

from services.serverless.services.keyword_service import KeywordGenerationService


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Usage:
        prompt_token_count = 5
        candidates_token_count = 10

    class _Resp:
        text = '["AI 수요 증가", "실적 호조", "목표가 상향"]'
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


def test_keyword_service_migration_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"
    svc = KeywordGenerationService()
    expected_contents = f"{svc.SYSTEM_PROMPT}\n\nPROMPT"

    keywords, metadata = svc._call_llm_sync("PROMPT", max_retries=0)

    cfg = captured_gemini["config"]
    assert cfg.max_output_tokens == 1200
    assert cfg.temperature == 0.5
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None  # SYS는 user 본문에 합침(현행)
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_contents  # 단일파트 정규화 == concat
    # metadata 토큰수 = genai usage_metadata와 동일 값(코어 전달)
    assert metadata == {"input_tokens": 5, "output_tokens": 10}
    assert keywords == ["AI 수요 증가", "실적 호조", "목표가 상향"]
