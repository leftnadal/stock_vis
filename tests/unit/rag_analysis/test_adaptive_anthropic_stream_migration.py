"""슬라이스 ③b #8 AdaptiveLLMService._generate_claude_stream 이관 — anthropic stream IDENTICAL.

직접 AsyncAnthropic.messages.stream(async with + text_stream + get_final_message) →
코어 astream(provider="anthropic")(정규화 델타 StreamDelta/StreamFinal) + shim.
IDENTICAL 대상(§핀4): delta str 시퀀스·순서, 종단 usage(input/output_tokens), dict 봉투
({type:delta/final}) byte 동일. wire: messages·model·max_tokens·temperature·system 동일.
어댑터 __aexit__ 호출(연결 누수 방지)도 검증. circuit=None(원본 CB 없음, 행위보존).
"""

import pytest

from services.rag_analysis.services.adaptive_llm_service import AdaptiveLLMService
from services.rag_analysis.services.complexity_classifier import QuestionComplexity


class _Usage:
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class _FinalMessage:
    def __init__(self, i, o):
        self.usage = _Usage(i, o)


class _FakeStream:
    """AsyncAnthropic messages.stream 진입 결과 — text_stream + get_final_message."""

    def __init__(self, chunks, usage):
        self._chunks = chunks
        self._usage = usage

    @property
    def text_stream(self):
        async def _gen():
            for c in self._chunks:
                yield c

        return _gen()

    async def get_final_message(self):
        return _FinalMessage(*self._usage)


class _FakeCM:
    """async context manager (messages.stream 반환) — __aenter__/__aexit__ 추적."""

    def __init__(self, stream, flags):
        self._stream = stream
        self._flags = flags

    async def __aenter__(self):
        self._flags["entered"] = True
        return self._stream

    async def __aexit__(self, *a):
        self._flags["exited"] = True
        return None


@pytest.fixture
def captured_anthropic(monkeypatch):
    """anthropic.AsyncAnthropic patch — messages.stream(kwargs) 캡처 + fake 스트림."""
    cap: dict = {"flags": {}}

    def _install(chunks, usage):
        stream = _FakeStream(chunks, usage)

        class _FakeMessages:
            def stream(self, **kwargs):
                cap["kwargs"] = kwargs
                return _FakeCM(stream, cap["flags"])

        class _FakeAsyncAnthropic:
            def __init__(self, api_key=None):
                cap["api_key"] = api_key
                self.messages = _FakeMessages()

        import anthropic as real

        monkeypatch.setattr(real, "AsyncAnthropic", _FakeAsyncAnthropic)

    cap["install"] = _install
    return cap


def _config():
    return {
        "model": "claude-sonnet-4-5",
        "max_tokens": 1000,
        "temperature": 0.7,
        "complexity": QuestionComplexity.MODERATE,
    }


def _make_service(settings):
    settings.ANTHROPIC_API_KEY = "fake-key"
    return AdaptiveLLMService(provider="claude", enable_cost_tracking=False)


@pytest.mark.asyncio
async def test_claude_stream_delta_sequence_and_usage(captured_anthropic, settings):
    """delta str 시퀀스·순서 그대로 + 종단 usage로 final 집계(원본 동형)."""
    captured_anthropic["install"](["안녕", "하세요", " 분석"], usage=(31, 42))
    svc = _make_service(settings)

    events = [
        e
        async for e in svc._generate_claude_stream("SYS", "ctx", "q?", _config())
    ]

    deltas = [e["content"] for e in events if e["type"] == "delta"]
    assert deltas == ["안녕", "하세요", " 분석"]  # 재청크·뭉개기 0

    final = events[-1]
    assert final["type"] == "final"
    assert final["content"] == "안녕하세요 분석"
    assert final["input_tokens"] == 31
    assert final["output_tokens"] == 42
    assert final["model"] == "claude-sonnet-4-5"
    assert final["complexity"] == "moderate"


@pytest.mark.asyncio
async def test_claude_stream_wire_identical(captured_anthropic, settings):
    """messages.stream kwargs = 원본 #8 직접호출과 byte 동일(model·max_tokens·temperature·system·messages)."""
    captured_anthropic["install"](["x"], usage=(1, 1))
    svc = _make_service(settings)

    ctx, q = "컨텍스트본문", "질문본문"
    [e async for e in svc._generate_claude_stream("SYS_P", ctx, q, _config())]

    kw = captured_anthropic["kwargs"]
    assert kw["model"] == "claude-sonnet-4-5"
    assert kw["max_tokens"] == 1000
    assert kw["temperature"] == 0.7
    assert kw["system"] == "SYS_P"
    # 원본 user_message 조립 그대로(단일 user 메시지)
    expected_user = f"## 컨텍스트\n{ctx}\n\n## 질문\n{q}\n\n## 분석"
    assert kw["messages"] == [{"role": "user", "content": expected_user}]
    # #8 미전달 노브 미주입(잉여키 0)
    assert set(kw) == {"model", "max_tokens", "temperature", "system", "messages"}


@pytest.mark.asyncio
async def test_claude_stream_closes_context(captured_anthropic, settings):
    """어댑터가 __aenter__(셋업)·__aexit__(연결 해제)를 모두 호출(누수 방지)."""
    captured_anthropic["install"](["a", "b"], usage=(5, 6))
    svc = _make_service(settings)

    [e async for e in svc._generate_claude_stream("SYS", "c", "q", _config())]

    assert captured_anthropic["flags"].get("entered") is True
    assert captured_anthropic["flags"].get("exited") is True


@pytest.mark.asyncio
async def test_claude_stream_unavailable_when_no_key(settings):
    """ANTHROPIC_API_KEY 없으면 error 이벤트(가드 보존)."""
    settings.ANTHROPIC_API_KEY = ""
    svc = AdaptiveLLMService(provider="claude", enable_cost_tracking=False)

    events = [
        e async for e in svc._generate_claude_stream("SYS", "c", "q", _config())
    ]
    assert len(events) == 1
    assert events[0]["type"] == "error"
