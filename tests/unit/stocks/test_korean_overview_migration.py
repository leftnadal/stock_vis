"""슬라이스 ② korean_overview 이관 — 4노브 IDENTICAL 입증.

genai 직접 호출 → shared/llm `complete()` 경유로 바꾼 뒤에도, provider가 만드는 최종
`GenerateContentConfig`가 현행과 byte 동일(temperature·response_mime_type·thinking_budget·
max_output_tokens 미설정)임을 genai 호출을 가로채 검증. 출력 파싱도 동일.
"""

import json

import pytest

from packages.shared.stocks.services.korean_overview_service import (
    KoreanOverviewService,
)


@pytest.fixture
def captured_gemini(monkeypatch):
    """provider의 genai.Client를 가로채 generate_content 인자(config 포함)를 캡처."""
    cap: dict = {}

    class _Usage:
        prompt_token_count = 5
        candidates_token_count = 10

    class _Resp:
        text = json.dumps(
            {
                "summary": "애플은 하드웨어와 서비스를 결합한 기업이다.",
                "business_model": "아이폰 중심 하드웨어 + 서비스 구독.",
                "competitive_edge": "생태계 락인과 브랜드 해자.",
                "risk_factors": "규제·중국 의존·경쟁 심화.",
            }
        )
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


@pytest.mark.django_db
def test_korean_overview_migration_4knob_identical(
    stock_aapl, captured_gemini, settings
):
    settings.GEMINI_API_KEY = "fake-key"  # __init__ 키 검증 + provider 해소
    svc = KoreanOverviewService()
    expected_prompt = svc._build_prompt(stock_aapl)  # 결정적 — 이관 후에도 불변

    result = svc.generate_for_stock("AAPL", force=True)

    cfg = captured_gemini["config"]
    # ★ 4노브 + contents/model 이 현행 genai 호출과 byte 동일
    assert cfg.temperature == 0.3
    assert cfg.response_mime_type == "application/json"  # response_format="json" 매핑
    assert cfg.thinking_config.thinking_budget == 0  # extra passthrough
    assert getattr(cfg, "max_output_tokens", None) is None  # 미설정(2000 강제 안 됨)
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_prompt  # 프롬프트 불변

    # 출력 파싱 동일 — json.loads(response.text) → DB 저장 결과
    assert result.summary == "애플은 하드웨어와 서비스를 결합한 기업이다."
    assert result.business_model == "아이폰 중심 하드웨어 + 서비스 구독."
    assert result.competitive_edge == "생태계 락인과 브랜드 해자."
    assert result.risk_factors == "규제·중국 의존·경쟁 심화."
    assert result.llm_model == "gemini-2.5-flash"
