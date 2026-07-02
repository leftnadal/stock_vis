"""슬라이스 ④ RelationshipKeywordEnricher._generate_keywords 이관 — IDENTICAL (soft 편차).

원본 contents 단일 Content/단일 Part(SYS+prompt) → complete() concat 문자열(genai 정규화 wire 동일).
config 노브(max_output_tokens·temperature·thinking_budget) byte 동일, system_instruction 미설정 보존.
"""

import pytest

from services.serverless.services.relationship_keyword_enricher import (
    RelationshipKeywordEnricher,
)


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = '["공급망 의존", "매출 연동", "기술 협력"]'

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


def test_relationship_keyword_enricher_migration_identical(captured_gemini, settings, monkeypatch):
    settings.GEMINI_API_KEY = "fake-key"
    svc = RelationshipKeywordEnricher()
    monkeypatch.setattr(svc, "_build_prompt", lambda s, t, r: "BUILT_PROMPT")
    expected_contents = f"{svc.SYSTEM_PROMPT}\n\nBUILT_PROMPT"

    keywords = svc._generate_keywords("NVDA", "TSM", "supplier")

    cfg = captured_gemini["config"]
    assert cfg.max_output_tokens == 200
    assert cfg.temperature == 0.5
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None  # SYS는 user 본문에 합침(현행)
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_contents  # 단일파트 정규화 == concat
    assert keywords == ["공급망 의존", "매출 연동", "기술 협력"]
