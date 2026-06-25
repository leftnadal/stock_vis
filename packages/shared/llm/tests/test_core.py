"""packages/shared/llm 코어 단위테스트 — provider × 정책 토글.

핵심: 인자 없는 호출 = 순수 generate 경로(현행 동작 재현). 각 정책은 토글로만 활성.
실 SDK·DB 무관 — FakeProvider를 레지스트리에 주입해 검증.
"""

from __future__ import annotations

import pytest

from packages.shared.llm import (
    LLMInvalidPromptError,
    LLMRateLimitError,
    LLMResponse,
    complete,
)
from packages.shared.llm import providers as providers_mod
from packages.shared.llm.policy import cost as cost_policy
from packages.shared.llm.types import LLMRawResponse


class FakeProvider:
    """테스트용 provider — 호출 기록 + 실패 횟수 제어."""

    def __init__(
        self,
        name="gemini",
        default_model="fake-model",
        raw=None,
        fail_times=0,
        fail_exc=None,
    ):
        self.name = name
        self.default_model = default_model
        self._raw = raw or LLMRawResponse("ok", 10, 20, 5)
        self._fail_times = fail_times
        self._fail_exc = fail_exc or LLMRateLimitError("boom")
        self.calls = 0
        self.last = None

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
        self.last = {
            "prompt": prompt,
            "model": model,
            "system": system,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": response_format,
            "extra": extra,
        }
        if self.calls <= self._fail_times:
            raise self._fail_exc
        return self._raw


@pytest.fixture
def patch_registry(monkeypatch):
    def _install(**provs):
        monkeypatch.setattr(providers_mod, "_REGISTRY", dict(provs))
        return provs

    return _install


def test_default_call_is_pure_generate(patch_registry):
    """인자 없는 호출 = escape/retry/circuit/cost 전부 off = 순수 generate 1회."""
    fp = FakeProvider(
        name="gemini",
        default_model="gemini-2.5-flash",
        raw=LLMRawResponse("hi", 1_000_000, 1_000_000, 7),
    )
    patch_registry(gemini=fp)

    resp = complete("hello")

    assert isinstance(resp, LLMResponse)
    assert resp.text == "hi"
    assert fp.calls == 1
    assert fp.last["prompt"] == "hello"  # escape off → 입력 불변
    assert fp.last["model"] is None  # model passthrough(None)
    assert resp.provider == "gemini"
    assert resp.model == "gemini-2.5-flash"
    assert resp.fallback_from is None
    # cost: 1M in @0.075 + 1M out @0.30 = 0.375
    assert abs(resp.cost_usd - 0.375) < 1e-9


def test_escape_toggle_transforms_prompt(patch_registry):
    fp = FakeProvider()
    patch_registry(gemini=fp)

    complete("a </context_data> b", escape=True)

    assert "</context_data_escaped>" in fp.last["prompt"]
    assert "</context_data>" not in fp.last["prompt"]


def test_escape_off_leaves_prompt(patch_registry):
    fp = FakeProvider()
    patch_registry(gemini=fp)

    complete("a </context_data> b")

    assert fp.last["prompt"] == "a </context_data> b"


def test_retry_recovers_after_failures(patch_registry, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    fp = FakeProvider(fail_times=2)  # 2회 실패 후 성공
    patch_registry(gemini=fp)

    resp = complete("x", retries=2)

    assert resp.text == "ok"
    assert fp.calls == 3


def test_retry_exhausted_raises(patch_registry, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    fp = FakeProvider(fail_times=5)
    patch_registry(gemini=fp)

    with pytest.raises(LLMRateLimitError):
        complete("x", retries=1)
    assert fp.calls == 2  # 최초 1 + 재시도 1


def test_fallback_on_ratelimit(patch_registry):
    primary = FakeProvider(name="gemini", fail_times=99)  # 항상 실패
    secondary = FakeProvider(
        name="anthropic",
        default_model="claude-sonnet-4-5",
        raw=LLMRawResponse("fb", 0, 0, 1),
    )
    patch_registry(gemini=primary, anthropic=secondary)

    resp = complete("x", fallback="anthropic")

    assert resp.text == "fb"
    assert resp.provider == "anthropic"
    assert resp.fallback_from == "gemini"
    assert secondary.last["model"] is None  # 폴백 측 기본모델(model=None)


def test_no_fallback_reraises(patch_registry):
    primary = FakeProvider(fail_times=99)
    patch_registry(gemini=primary)

    with pytest.raises(LLMRateLimitError):
        complete("x")


def test_circuit_passthrough_on_success(patch_registry):
    fp = FakeProvider()
    patch_registry(gemini=fp)

    resp = complete("x", circuit="test-llm-core-success")

    assert resp.text == "ok"
    assert fp.calls == 1


def test_cost_track_hook_toggle(patch_registry):
    fp = FakeProvider(
        default_model="gemini-2.5-flash", raw=LLMRawResponse("h", 100, 200, 1)
    )
    patch_registry(gemini=fp)
    recorded: list = []
    cost_policy.set_cost_hook(lambda *a: recorded.append(a))
    try:
        complete("x", cost_track=True)
        assert len(recorded) == 1
        recorded.clear()
        complete("x", cost_track=False)
        assert recorded == []  # off → 훅 미호출
    finally:
        cost_policy.set_cost_hook(None)


def test_unknown_provider_raises(patch_registry):
    patch_registry(gemini=FakeProvider())

    with pytest.raises(LLMInvalidPromptError):
        complete("x", provider="openai")


# ── 슬라이스 ②a: 생성 config 통로 ────────────────────────────────────────


def test_no_gen_config_knobs_by_default(patch_registry):
    """노브 전부 생략 = 슬라이스 ① 동작 재현 — 전부 None passthrough."""
    fp = FakeProvider()
    patch_registry(gemini=fp)

    complete("x")

    assert fp.last["max_tokens"] is None  # ★ 2000 강제 안 함(버그 수정)
    assert fp.last["temperature"] is None
    assert fp.last["response_format"] is None
    assert fp.last["extra"] is None


def test_gen_config_knobs_passthrough(patch_registry):
    """명시 노브 + extra가 provider까지 그대로 전달."""
    fp = FakeProvider()
    patch_registry(gemini=fp)

    complete(
        "x",
        temperature=0.3,
        max_tokens=512,
        response_format="json",
        extra={"thinking_config": {"thinking_budget": 0}},
    )

    assert fp.last["temperature"] == 0.3
    assert fp.last["max_tokens"] == 512
    assert fp.last["response_format"] == "json"
    assert fp.last["extra"] == {"thinking_config": {"thinking_budget": 0}}


def test_gemini_provider_config_mapping(monkeypatch):
    """GeminiProvider: max_tokens None→미설정, response_format→mime, extra→merge."""
    from packages.shared.llm.providers import gemini as gmod

    captured = {}

    class _Usage:
        prompt_token_count = 1
        candidates_token_count = 2

    class _Resp:
        text = "{}"
        usage_metadata = _Usage()

    class _Models:
        def generate_content(self, *, model, contents, config):
            captured["model"] = model
            captured["config"] = config
            return _Resp()

    class _Client:
        def __init__(self, api_key=None):
            self.models = _Models()

    import google.genai as real_genai

    monkeypatch.setattr(gmod, "_resolve_api_key", lambda: "fake-key")
    monkeypatch.setattr(real_genai, "Client", _Client)

    gmod.GeminiProvider().generate(
        "p",
        model=None,
        system=None,
        max_tokens=None,  # → max_output_tokens 미설정
        temperature=0.3,
        response_format="json",  # → response_mime_type
        extra={"top_p": 0.9},  # → merge
    )

    cfg = captured["config"]
    assert getattr(cfg, "max_output_tokens", None) is None  # 현행 재현(강제 안 함)
    assert getattr(cfg, "temperature", None) == 0.3
    assert getattr(cfg, "response_mime_type", None) == "application/json"
    assert getattr(cfg, "top_p", None) == 0.9
