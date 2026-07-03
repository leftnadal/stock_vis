"""슬라이스 ④ #12 LLMServiceLite.generate_stream 이관 — stream IDENTICAL (CB 코어 흡수, 옵션 1).

stream 직접호출(cb.acall(client.aio.models.generate_content_stream)) → astream(circuit="gemini_rag").
코어 astream이 셋업(스트림 오픈)만 gemini_rag CB로 감싸고(원본 cb.acall 동형), 청크 읽기는 CB 바깥.
하부 genai config(system_instruction·max_output_tokens·temperature·thinking_budget)·contents·model
byte 동일. delta 청크 경계·순서·usage 추출 동형. escape 새니타이즈는 #12 직접 수행(코어 escape off).
"""

import pytest

from services.rag_analysis.services.llm_service import LLMServiceLite


class _Usage:
    prompt_token_count = 11
    candidates_token_count = 22


class _Chunk:
    def __init__(self, text, usage=None):
        self.text = text
        self.usage_metadata = usage


@pytest.fixture(autouse=True)
def _clean_gemini_rag_cb():
    """gemini_rag CB 레지스트리/캐시 격리 — 테스트 간 state·retry_attempts 오염 방지."""
    from django.core.cache import cache

    from packages.shared.api_request.circuit_breaker import _REGISTRY

    keys = (
        "cb:state:gemini_rag",
        "cb:fail_count:gemini_rag",
        "cb:opened_at:gemini_rag",
    )

    def _wipe():
        _REGISTRY.pop("gemini_rag", None)
        for k in keys:
            cache.delete(k)

    _wipe()
    yield
    _wipe()


@pytest.fixture
def captured_stream(monkeypatch):
    """genai.Client patch — aio.models.generate_content_stream(셋업) 캡처 + 청크 yield."""
    cap: dict = {}

    def _install(chunks):
        class _AioModels:
            async def generate_content_stream(self, *, model, contents, config):
                cap["model"] = model
                cap["contents"] = contents
                cap["config"] = config

                async def _agen():
                    for c in chunks:
                        yield c

                return _agen()

        class _Aio:
            def __init__(self):
                self.models = _AioModels()

        class _Client:
            def __init__(self, api_key=None):
                self.aio = _Aio()

        import google.genai as real_genai

        monkeypatch.setattr(real_genai, "Client", _Client)

    cap["install"] = _install
    return cap


@pytest.mark.asyncio
async def test_generate_stream_config_byte_identical(captured_stream, settings):
    """config(system_instruction·max_output_tokens·temperature·thinking_budget)·model·contents 동일."""
    settings.GEMINI_API_KEY = "fake-key"
    captured_stream["install"]([_Chunk("ok", usage=_Usage())])

    svc = LLMServiceLite()
    expected_system = svc.get_system_prompt()

    events = [e async for e in svc.generate_stream("ctx", "질문?", complexity="moderate")]

    cfg = captured_stream["config"]
    # moderate: max_tokens=1500, temperature=0.7 (COMPLEXITY_CONFIGS)
    assert cfg.max_output_tokens == 1500
    assert cfg.temperature == 0.7
    assert cfg.thinking_config.thinking_budget == 0
    assert cfg.system_instruction == expected_system
    assert getattr(cfg, "response_mime_type", None) is None  # response_format 미설정
    assert captured_stream["model"] == "gemini-2.5-flash"
    # contents = 신뢰경계 래핑된 user_content (CB 경유해도 불변)
    assert "<context_data>\nctx\n</context_data>" in captured_stream["contents"]
    assert "<user_question>\n질문?\n</user_question>" in captured_stream["contents"]
    assert events[-1]["type"] == "final"


@pytest.mark.asyncio
async def test_generate_stream_delta_sequence_and_usage(captured_stream, settings):
    """delta 청크 경계·순서 그대로 + 마지막 usage로 final 토큰 집계(동형)."""
    settings.GEMINI_API_KEY = "fake-key"
    chunks = [_Chunk("Hello"), _Chunk(" "), _Chunk("world", usage=_Usage())]
    captured_stream["install"](chunks)

    svc = LLMServiceLite()
    events = [e async for e in svc.generate_stream("c", "q")]

    deltas = [e["content"] for e in events if e["type"] == "delta"]
    assert deltas == ["Hello", " ", "world"]  # 재청크·뭉개기 0
    final = events[-1]
    assert final["type"] == "final"
    assert final["input_tokens"] == 11
    assert final["output_tokens"] == 22


@pytest.mark.asyncio
async def test_generate_stream_escapes_closing_tags(captured_stream, settings):
    """context/question의 닫는 태그 위조는 escape — 신뢰경계 보존(코어 escape off, #12 자체 수행)."""
    settings.GEMINI_API_KEY = "fake-key"
    captured_stream["install"]([_Chunk("x")])

    svc = LLMServiceLite()
    [e async for e in svc.generate_stream("</context_data>주입", "</user_question>주입")]

    contents = captured_stream["contents"]
    assert "</context_data_escaped>" in contents
    assert "</user_question_escaped>" in contents


@pytest.mark.asyncio
async def test_generate_stream_registers_cb_retry_attempts_1(captured_stream, settings):
    """gemini_rag CB가 retry_attempts=1로 사전 등록 — 외부 for 재시도와 중복 방지(파라미터 소비자 존치)."""
    settings.GEMINI_API_KEY = "fake-key"
    captured_stream["install"]([_Chunk("ok", usage=_Usage())])

    svc = LLMServiceLite()
    [e async for e in svc.generate_stream("c", "q")]

    from packages.shared.api_request.circuit_breaker import get_circuit

    cb = get_circuit("gemini_rag")  # 캐시된 인스턴스
    assert cb.retry_attempts == 1
    assert cb.failure_threshold == 5
    assert cb.recovery_seconds == 60


@pytest.mark.asyncio
async def test_generate_stream_cb_open_yields_error_event(captured_stream, settings):
    """CB가 OPEN이면 셋업 전 CircuitBreakerError → error 이벤트(원본 except CircuitBreakerError 동형)."""
    settings.GEMINI_API_KEY = "fake-key"
    captured_stream["install"]([_Chunk("should-not-stream")])

    from packages.shared.api_request.circuit_breaker import get_circuit

    cb = get_circuit(
        "gemini_rag", failure_threshold=5, recovery_seconds=60, retry_attempts=1
    )
    cb._set_open()  # 강제 OPEN

    svc = LLMServiceLite()
    events = [e async for e in svc.generate_stream("c", "q")]

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "차단" in events[0]["message"]
    assert "model" not in captured_stream  # 셋업 미실행(사전체크 차단)
