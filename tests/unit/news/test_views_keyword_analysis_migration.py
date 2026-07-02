"""슬라이스 ④ NewsViewSet._generate_keyword_analysis 이관 — 3노브 IDENTICAL.

genai 직접호출 → shared/llm `complete()` 경유 후에도 GenerateContentConfig가
현행과 byte 동일(max_output_tokens·temperature·thinking_budget, system/mime 미설정)임을
genai 호출을 가로채 검증. contents/model 동일.
"""

import pytest

from services.news.api.views import NewsViewSet


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Usage:
        prompt_token_count = 5
        candidates_token_count = 10

    class _Resp:
        text = "엔비디아 실적 기대가 시장을 끌어올린다."
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


def test_views_keyword_analysis_migration_3knob_identical(captured_gemini, settings):
    settings.GEMINI_API_KEY = "fake-key"
    articles = [
        {"title": "NVIDIA beats earnings", "source": "finnhub"},
        {"title": "AI chip demand surges", "source": "marketaux"},
    ]
    # 프롬프트는 결정적 — 현행 f-string 그대로 재구성
    titles = "\n".join(f"- {a['title']} ({a['source']})" for a in articles[:8])
    expected_prompt = f"""키워드: "AI 반도체" (감성: positive)

관련 뉴스 기사 제목:
{titles}

위 뉴스들을 종합하여 투자자 관점에서 핵심 요약을 3-4문장으로 작성하세요.
- 무슨 일이 일어나고 있는지
- 어떤 종목/섹터에 영향이 있는지
- 투자자가 주목해야 할 포인트

한국어로 작성하세요. JSON이 아닌 일반 텍스트로 응답하세요."""

    result = NewsViewSet()._generate_keyword_analysis("AI 반도체", "positive", articles)

    cfg = captured_gemini["config"]
    assert cfg.max_output_tokens == 500
    assert cfg.temperature == 0.3
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "system_instruction", None) is None  # 현행 미설정 보존
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_prompt
    assert result == "엔비디아 실적 기대가 시장을 끌어올린다."  # .strip() 동일
