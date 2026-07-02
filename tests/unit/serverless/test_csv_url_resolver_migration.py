"""슬라이스 ④ CSVURLResolver._find_csv_url_by_llm 이관 — 4노브 IDENTICAL.

genai 직접호출 → complete() 경유 후에도 GenerateContentConfig byte 동일
(system_instruction·max_output_tokens·temperature·thinking_budget) 검증. contents/model 동일.
genai.Client(피처 플래그) → self._llm_enabled 플래그로 게이팅 보존도 확인.
"""

import pytest

from services.serverless.services.csv_url_resolver import CSVURLResolver


@pytest.fixture
def captured_gemini(monkeypatch):
    cap: dict = {}

    class _Resp:
        text = "https://example.com/holdings.csv"

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


def test_csv_url_resolver_migration_4knob_identical(captured_gemini, settings, monkeypatch):
    settings.GEMINI_API_KEY = "fake-key"
    svc = CSVURLResolver()
    assert svc._llm_enabled is True  # 게이팅 플래그 보존(SDK + key)

    monkeypatch.setattr(svc, "_clean_html_for_llm", lambda html: "CLEAN_HTML")
    cfg_in = {"name": "SPDR", "base_url": "https://spdr.com"}

    # 결정적 프롬프트 — 현행 f-string 그대로 재구성
    expected_system = """당신은 웹페이지 HTML에서 CSV/XLSX 다운로드 링크를 찾는 전문가입니다.

규칙:
1. ETF Holdings 데이터를 다운로드할 수 있는 CSV 또는 XLSX 파일 링크를 찾으세요
2. href, data-url, data-download-url 등의 속성에서 URL을 찾으세요
3. 링크에 "holdings", "download", "csv", "xlsx" 등의 키워드가 포함된 것을 우선하세요
4. 정확히 하나의 URL만 반환하세요 (전체 URL, http로 시작)
5. URL을 찾을 수 없으면 "NOT_FOUND"만 반환하세요
6. 다른 설명 없이 URL만 반환하세요"""
    expected_user = f"""다음 HTML에서 XLK ETF의 Holdings CSV/XLSX 다운로드 링크를 찾아주세요.

운용사: SPDR
기본 URL: https://spdr.com

HTML (일부):
CLEAN_HTML

CSV/XLSX 다운로드 URL:"""

    result = svc._find_csv_url_by_llm("<html>", "XLK", "spdr", cfg_in)

    cfg = captured_gemini["config"]
    assert cfg.system_instruction == expected_system
    assert cfg.max_output_tokens == 1000  # LLM_MAX_TOKENS
    assert cfg.temperature == 0.1  # LLM_TEMPERATURE
    assert cfg.thinking_config.thinking_budget == 0
    assert getattr(cfg, "response_mime_type", None) is None
    assert captured_gemini["model"] == "gemini-2.5-flash"
    assert captured_gemini["contents"] == expected_user
    assert result == "https://example.com/holdings.csv"  # .strip() 동일
