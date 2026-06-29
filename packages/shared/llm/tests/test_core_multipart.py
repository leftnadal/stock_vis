"""슬라이스 ②c — complete() multipart contents 코어 통로 단위테스트 (소비처 0).

핵심:
  (a) 단일-str 경로 불변: str contents는 ②c 전과 동일하게 provider로 전달(평탄화·변형 0).
  (b) 멀티파트 wire 동등성: #19 형태(단일 Content(role=user) + 2 Part[SYS·user])를 complete()에
      넘기면 genai에 **그 구조 그대로** 전달(byte 동일) — concat 1파트와는 **다름**(회귀 방어).
  (c) escape는 str 전용: 멀티파트 + escape=True → NotImplementedError(조용한 변형 금지).
sync `complete()` 전용 — async/stream/anthropic 미변경(이번 범위 밖).
"""

from __future__ import annotations

import pytest

from packages.shared.llm import complete
from packages.shared.llm import providers as providers_mod
from packages.shared.llm.types import LLMRawResponse


class _FakeProvider:
    """호출 prompt 그대로 기록 — 코어 라우팅(변형 0) 검증용."""

    name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self):
        self.last = None
        self.calls = 0

    def generate(
        self,
        prompt,
        *,
        model,
        system,
        max_tokens,
        temperature=None,
        response_format=None,
        extra=None,
    ):
        self.calls += 1
        self.last = {"prompt": prompt, "model": model, "extra": extra}
        return LLMRawResponse("ok", 1, 2, 3)


@pytest.fixture
def patch_registry(monkeypatch):
    def _install(**provs):
        monkeypatch.setattr(providers_mod, "_REGISTRY", dict(provs))
        return provs

    return _install


def _mk_multipart():
    """#19 형태: 단일 Content(role=user) + 2 Part[SYS·user] (직접 생성자)."""
    from google.genai import types as gtypes

    return [
        gtypes.Content(
            role="user",
            parts=[
                gtypes.Part(text="SYSTEM_PROMPT_BODY"),
                gtypes.Part(text="USER_PROMPT_BODY"),
            ],
        )
    ]


# ── (a) 단일-str 경로 불변 ────────────────────────────────────────────────


def test_str_contents_unchanged_routing(patch_registry):
    """str contents는 변형 0으로 provider에 그대로(②c 전과 동일)."""
    fp = _FakeProvider()
    patch_registry(gemini=fp)

    complete("hello world")

    assert fp.last["prompt"] == "hello world"  # str 경로 불변
    assert isinstance(fp.last["prompt"], str)


# ── (b) 멀티파트 pass-through (코어 레벨) ──────────────────────────────────


def test_multipart_contents_passthrough_no_flatten(patch_registry):
    """멀티파트 contents는 코어가 변형 0으로 provider에 그대로(평탄화·concat·래핑 없음)."""
    fp = _FakeProvider()
    patch_registry(gemini=fp)

    contents = _mk_multipart()
    complete(contents, temperature=0.2, max_tokens=1500, response_format="json")

    assert fp.last["prompt"] is contents  # 동일 객체(pass-through, 변형 0)
    assert isinstance(fp.last["prompt"], list)
    assert len(fp.last["prompt"][0].parts) == 2  # 2파트 보존(concat 안 함)


# ── (b) 멀티파트 wire 동등성 (gemini.generate → genai) ─────────────────────


def _gemini_capture(monkeypatch):
    """genai.Client(sync) patch — generate_content가 받은 contents/config/model 캡처."""
    from packages.shared.llm.providers import gemini as gmod

    captured: dict = {}

    class _Usage:
        prompt_token_count = 1
        candidates_token_count = 2

    class _Resp:
        text = "{}"
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


def test_multipart_wire_byte_identical_and_differs_from_concat(monkeypatch):
    """#19 멀티파트가 genai에 byte 동일 전달 + concat 1파트와 다름 + config 동일 조립."""
    from google.genai import types as gtypes

    captured = _gemini_capture(monkeypatch)
    contents = _mk_multipart()

    complete(
        contents,
        provider="gemini",
        model="gemini-2.5-flash",
        temperature=0.2,
        max_tokens=1500,
        response_format="json",
        extra={"thinking_config": gtypes.ThinkingConfig(thinking_budget=0)},
    )

    sent = captured["contents"]
    # (b) genai에 넘어간 contents == 독립적으로 동일 형태 직접 빌드한 것(byte 동일 = 직접 호출 동형)
    assert sent == _mk_multipart()
    assert sent is contents  # 코어 변형 0
    # concat 1파트(평탄화)와는 다름 — 회귀 방어
    assert sent != "SYSTEM_PROMPT_BODY" + "USER_PROMPT_BODY"
    assert len(sent[0].parts) == 2

    # config 조립 동일(#19 노브): system_instruction 없음, mime/temperature/max/thinking
    cfg = captured["config"]
    assert cfg.temperature == 0.2
    assert cfg.max_output_tokens == 1500
    assert cfg.response_mime_type == "application/json"
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None
    assert captured["model"] == "gemini-2.5-flash"


def test_str_wire_unchanged_through_gemini(monkeypatch):
    """단일-str 경로: genai에 str 그대로 전달(②c 추가가 str wire 미파손)."""
    captured = _gemini_capture(monkeypatch)

    complete("plain prompt", provider="gemini")

    assert captured["contents"] == "plain prompt"
    assert isinstance(captured["contents"], str)


# ── (c) escape는 str 전용 ─────────────────────────────────────────────────


def test_multipart_with_escape_raises(patch_registry):
    """멀티파트 + escape=True → NotImplementedError(escape는 str 신뢰경계 전용)."""
    fp = _FakeProvider()
    patch_registry(gemini=fp)

    with pytest.raises(NotImplementedError):
        complete(_mk_multipart(), escape=True)
    assert fp.calls == 0  # 변형 시도 전 차단
