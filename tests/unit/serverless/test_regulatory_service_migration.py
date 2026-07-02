"""슬라이스 ④ RegulatoryService.extract_regulatory_groups_llm 이관 — IDENTICAL (soft 편차).

원본 config는 dict{temperature,max_output_tokens}(thinking 없음). complete()의 GenerateContentConfig로
동일 필드 → genai가 dict↔config 동일 취급(wire 동일). 모델 gemini-2.0-flash-exp, contents=prompt(불변).
lazy 가용성 게이팅(_get_gemini_client truthy)도 보존.
"""

import pytest

from services.serverless.services.regulatory_service import RegulatoryService


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = "[]"

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


def test_regulatory_service_migration_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"
    svc = RegulatoryService()
    texts = [{"symbol": "NVDA", "text": "US-China export controls tighten"}]

    svc.extract_regulatory_groups_llm(texts)

    cfg = captured_gemini["config"]
    # dict{temperature,max_output_tokens} → GenerateContentConfig 동일 필드
    assert cfg.temperature == 0.3
    assert cfg.max_output_tokens == 2000
    assert getattr(cfg, "thinking_config", None) is None  # 원본 thinking 없음 보존
    assert getattr(cfg, "response_mime_type", None) is None
    assert getattr(cfg, "system_instruction", None) is None
    assert captured_gemini["model"] == "gemini-2.0-flash-exp"
    # contents=prompt(문자열, 빌더 불변) — 핵심 구조 보존 확인
    assert isinstance(captured_gemini["contents"], str)
    assert captured_gemini["contents"].startswith("You are a financial analyst")
    assert "NVDA" in captured_gemini["contents"]
