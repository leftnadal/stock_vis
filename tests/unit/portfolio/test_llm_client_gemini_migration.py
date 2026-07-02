"""슬라이스 ④ LLMClient._call_gemini(Gemini 경로) 이관 — IDENTICAL.

genai 직접호출 → complete() 경유 후에도 GenerateContentConfig byte 동일
(max_output_tokens 단일 노브, temperature/mime/system 미설정). 반환 portfolio LLMResponse는
text·input/output_tokens·cost_usd(자체 단가 상수)·provider·model 동일.

이중-provider 파일: Anthropic 경로(_call_anthropic)는 Part ③ 몫 — 건드리지 않음.
"""

import time

import pytest

from apps.portfolio.llm.client import (
    GEMINI_FLASH_INPUT_USD_PER_1M,
    GEMINI_FLASH_OUTPUT_USD_PER_1M,
    GEMINI_MODEL,
    LLMClient,
)


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Usage:
        prompt_token_count = 100
        candidates_token_count = 200

    class _Resp:
        text = "포트폴리오 분석 결과"
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


def test_call_gemini_migration_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"
    svc = LLMClient()

    result = svc._call_gemini("PROMPT", max_tokens=512, start=time.time())

    cfg = captured_gemini["config"]
    # config = max_output_tokens 단일 노브(현행과 동일, 그 외 미설정)
    assert cfg.max_output_tokens == 512
    assert getattr(cfg, "temperature", None) is None
    assert getattr(cfg, "response_mime_type", None) is None
    assert getattr(cfg, "system_instruction", None) is None
    assert captured_gemini["model"] == GEMINI_MODEL
    assert captured_gemini["contents"] == "PROMPT"

    # 반환 portfolio LLMResponse — cost는 자체 단가 상수로 동일 계산
    assert result.text == "포트폴리오 분석 결과"
    assert result.provider == "gemini"
    assert result.model == GEMINI_MODEL
    assert result.input_tokens == 100
    assert result.output_tokens == 200
    expected_cost = (
        100 / 1_000_000 * GEMINI_FLASH_INPUT_USD_PER_1M
        + 200 / 1_000_000 * GEMINI_FLASH_OUTPUT_USD_PER_1M
    )
    assert result.cost_usd == expected_cost
