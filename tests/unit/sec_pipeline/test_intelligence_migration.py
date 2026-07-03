"""슬라이스 ④ PipelineIntelligenceReporter.generate_report 이관 — IDENTICAL.

genai 직접호출 → complete() 경유 후에도 GenerateContentConfig byte 동일
(response_mime_type·temperature·thinking_budget, max_output_tokens 미설정) 검증. contents/model 동일.
"""

import pytest

import services.sec_pipeline.intelligence as intel_mod
from services.sec_pipeline.intelligence import PipelineIntelligenceReporter


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


@pytest.mark.django_db
def test_intelligence_migration_identical(captured_gemini, settings, monkeypatch):
    settings.GEMINI_API_KEY = "fake-key"

    class _FakeCollector:
        def collect(self, hours_back):
            return {"x": "PROMPT_BODY"}

    monkeypatch.setattr(intel_mod, "PipelineDataCollector", _FakeCollector)
    monkeypatch.setattr(intel_mod, "PIPELINE_INTELLIGENCE_PROMPT", "{x}")

    svc = PipelineIntelligenceReporter()
    monkeypatch.setattr(svc, "_calculate_trend", lambda result: {})

    svc.generate_report(hours_back=24)

    cfg = captured_gemini["config"]
    assert cfg.response_mime_type == "application/json"  # response_format="json" 매핑
    assert cfg.temperature == 0.2
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "max_output_tokens", None) is None  # 미설정(Gemini 폴백 없음)
    assert getattr(cfg, "system_instruction", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == "PROMPT_BODY"  # PROMPT.format(**data) 불변
