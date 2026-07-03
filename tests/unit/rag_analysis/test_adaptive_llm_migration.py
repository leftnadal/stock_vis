"""슬라이스 ② #9 AdaptiveLLMService._generate_gemini_stream 이관 — 구→신 SDK wire IDENTICAL.

구SDK GenerativeModel(generation_config={max_output_tokens, temperature}, system_instruction)
.generate_content_async(prompt, stream=True) → 코어 astream(provider="gemini") 경유
(신SDK genai.Client.aio.models.generate_content_stream). 하부 GenerateContentConfig
(system_instruction·max_output_tokens·temperature)·contents·model byte 동일. delta 청크 경계·
순서·usage 추출 동형. CB·escape·extra(thinking) 미설정 = 구SDK 직접호출과 wire IDENTICAL.

#8(AsyncAnthropic messages.stream)은 무접촉(③ 대상) — 이 테스트는 gemini(#9) 경로만 검증.
"""

import pytest

from services.rag_analysis.services.adaptive_llm_service import AdaptiveLLMService


class _Usage:
    prompt_token_count = 33
    candidates_token_count = 44


class _Chunk:
    def __init__(self, text, usage=None):
        self.text = text
        self.usage_metadata = usage


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


def _make_service(settings):
    settings.GEMINI_API_KEY = "fake-key"
    return AdaptiveLLMService(provider="gemini", enable_cost_tracking=False)


@pytest.mark.asyncio
async def test_gemini_stream_config_byte_identical(captured_stream, settings):
    """하부 genai config(system_instruction·max_output_tokens·temperature)·model·contents 동일.

    구SDK는 thinking_config/response_format 미설정 → 신SDK도 동일하게 미설정(extra 없음).
    """
    captured_stream["install"]([_Chunk("ok", usage=_Usage())])
    svc = _make_service(settings)

    context, question = "삼성전자 컨텍스트 데이터", "전망은?"
    expected_config = svc.classifier.classify_and_configure(
        question, 0, len(context.split())
    )
    expected_depth = svc._get_depth_from_complexity(expected_config["complexity"])
    expected_system = svc._build_system_prompt(expected_depth)

    events = [e async for e in svc.generate_stream(context, question)]

    cfg = captured_stream["config"]
    assert cfg.max_output_tokens == expected_config["max_tokens"]
    assert cfg.temperature == expected_config["temperature"]
    assert cfg.system_instruction == expected_system
    # 구SDK 미설정 노브는 신SDK도 미설정 — wire IDENTICAL(추가 필드 0).
    assert getattr(cfg, "thinking_config", None) is None
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_stream["model"] == expected_config["model"]
    # contents = 구SDK가 보내던 단일 str 프롬프트 그대로(평탄화·래핑 0).
    assert captured_stream["contents"] == (
        f"## 컨텍스트\n{context}\n\n## 질문\n{question}\n\n## 분석"
    )
    assert events[-1]["type"] == "final"


@pytest.mark.asyncio
async def test_gemini_stream_delta_sequence_and_usage(captured_stream, settings):
    """delta 청크 경계·순서 그대로 + 마지막 usage로 final 토큰 집계(동형)."""
    chunks = [_Chunk("Hello"), _Chunk(" "), _Chunk("world", usage=_Usage())]
    captured_stream["install"](chunks)
    svc = _make_service(settings)

    events = [e async for e in svc.generate_stream("c", "q")]

    deltas = [e["content"] for e in events if e["type"] == "delta"]
    assert deltas == ["Hello", " ", "world"]  # 재청크·뭉개기 0

    final = events[-1]
    assert final["type"] == "final"
    assert final["content"] == "Hello world"
    assert final["input_tokens"] == 33
    assert final["output_tokens"] == 44
    assert "model" in final
    assert "complexity" in final


@pytest.mark.asyncio
async def test_gemini_stream_usage_fallback_estimate(captured_stream, settings):
    """usage_metadata 미제공 시 추정값 폴백 보존(원본 else 분기 동형)."""
    captured_stream["install"]([_Chunk("abc def ghi")])  # usage 없음
    svc = _make_service(settings)

    events = [e async for e in svc.generate_stream("ctx one two", "q?")]
    final = events[-1]
    assert final["type"] == "final"
    # 폴백 추정: output = len(full_response.split()) * 1.3 = 3 * 1.3 = 3.9 → int 3
    assert final["output_tokens"] == 3
    assert final["input_tokens"] > 0


@pytest.mark.asyncio
async def test_gemini_stream_error_yields_error_event(captured_stream, settings):
    """스트림 예외는 error 이벤트로 전파(원본 except Exception 동형)."""
    import google.genai as real_genai

    class _BoomModels:
        async def generate_content_stream(self, *, model, contents, config):
            raise RuntimeError("boom")

    class _BoomAio:
        def __init__(self):
            self.models = _BoomModels()

    class _BoomClient:
        def __init__(self, api_key=None):
            self.aio = _BoomAio()

    import pytest as _pytest

    monkeypatch = _pytest.MonkeyPatch()
    monkeypatch.setattr(real_genai, "Client", _BoomClient)
    try:
        svc = _make_service(settings)
        events = [e async for e in svc.generate_stream("c", "q")]
    finally:
        monkeypatch.undo()

    assert any(e["type"] == "error" for e in events)
