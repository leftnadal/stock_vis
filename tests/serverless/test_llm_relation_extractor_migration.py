"""슬라이스 ④ #19 LLMRelationExtractor._call_llm 이관 — multipart wire IDENTICAL.

직접호출 `client.models.generate_content(contents=[Content(2 Part)])` → `complete([멀티파트])`.
②c 불투명 pass-through라 contents 2파트(SYS·user)가 genai에 **byte 동일** 전달(평탄화·concat 0).
config(temperature 0.2·max 1500·mime json·thinking 0, system_instruction 없음)·model 동일 조립.
sync 전용. usage 추출 동형(input_tokens/output_tokens).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from services.serverless.services.llm_relation_extractor import LLMRelationExtractor


def _gemini_capture(monkeypatch):
    """google.genai.Client(sync) patch — generate_content가 받은 contents/config/model 캡처."""
    from packages.shared.llm.providers import gemini as gmod

    captured: dict = {}

    class _Usage:
        prompt_token_count = 123
        candidates_token_count = 45

    class _Resp:
        text = '{"relations": []}'
        usage_metadata = _Usage()

    class _Models:
        def generate_content(self, *, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return _Resp()

    class _Client:
        def __init__(self, api_key=None):
            self.models = _Models()

    import google.genai as real_genai

    monkeypatch.setattr(gmod, "_resolve_api_key", lambda: "fake-key")
    monkeypatch.setattr(real_genai, "Client", _Client)
    return captured


@pytest.fixture
def extractor(settings):
    """LLMRelationExtractor (의존 서비스 모킹, genai.Client 생성 없음)."""
    settings.GEMINI_API_KEY = "test-api-key"
    with patch(
        "services.serverless.services.llm_relation_extractor.get_pre_filter"
    ), patch("services.serverless.services.llm_relation_extractor.get_symbol_matcher"):
        return LLMRelationExtractor()


def test_call_llm_multipart_wire_identical(extractor, monkeypatch):
    """#19 2파트 contents가 genai에 byte 동일 전달 + concat과 다름 + config 동일 + usage 동형."""
    from google.genai import types as gtypes

    captured = _gemini_capture(monkeypatch)

    text = "Microsoft acquired Activision for $68.7B."
    result = extractor._call_llm(text)

    # 기대 user_prompt = 현행 _call_llm 템플릿 그대로 재현
    truncated = text[:5000] if len(text) > 5000 else text
    expected_user_prompt = f"""Extract corporate relationships from the following text:

---
{truncated}
---

Return only valid JSON with the extracted relations."""
    expected_contents = [
        gtypes.Content(
            role="user",
            parts=[
                gtypes.Part(text=LLMRelationExtractor.SYSTEM_PROMPT),
                gtypes.Part(text=expected_user_prompt),
            ],
        )
    ]

    # (c) contents wire byte 동일 — 2파트·순서(SYS·user) 보존, concat·평탄화 0
    sent = captured["contents"]
    assert sent == expected_contents
    assert len(sent[0].parts) == 2
    assert sent[0].role == "user"
    assert sent[0].parts[0].text == LLMRelationExtractor.SYSTEM_PROMPT
    assert sent[0].parts[1].text == expected_user_prompt
    assert sent != LLMRelationExtractor.SYSTEM_PROMPT + expected_user_prompt  # concat 아님

    # (b) config 동일 조립 — system_instruction 없음
    cfg = captured["config"]
    assert cfg.temperature == LLMRelationExtractor.TEMPERATURE  # 0.2
    assert cfg.max_output_tokens == LLMRelationExtractor.MAX_OUTPUT_TOKENS  # 1500
    assert cfg.response_mime_type == "application/json"
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None
    assert captured["model"] == LLMRelationExtractor.MODEL  # gemini-2.5-flash

    # 반환 dict 동형 (usage 추출 — input/output_tokens)
    assert result["text"] == '{"relations": []}'
    assert result["prompt_tokens"] == 123
    assert result["completion_tokens"] == 45


def test_call_llm_truncates_long_text(extractor, monkeypatch):
    """5000자 초과 텍스트는 truncate 보존(현행 동작) — user Part에 잘린 텍스트 반영."""
    captured = _gemini_capture(monkeypatch)

    long_text = "A" * 6000
    extractor._call_llm(long_text)

    user_part_text = captured["contents"][0].parts[1].text
    assert ("A" * 5000) in user_part_text
    assert ("A" * 5001) not in user_part_text  # 5000자에서 잘림
