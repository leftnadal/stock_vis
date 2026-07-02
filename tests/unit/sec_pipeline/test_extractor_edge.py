"""
GeminiExtractor 추가 엣지 케이스 테스트.

기존 test_extractor.py / test_extractor_advanced.py 에서 누락된 영역:
- 호출 시 model name 이 'gemini-2.5-flash' 인지
- temperature=0.1 / response_mime_type='application/json' / thinking_config(thinking_budget=0) 가 설정되는지
- extract_business_model 의 prompt 에 paragraphs 가 포함되는지
- 단일 paragraph 입력 시에도 정상 동작
- extract_supply_chain 의 빈 paragraphs 는 LLM 호출하지 않음

슬라이스 ④: genai 직접호출 → shared/llm complete() 경유로 이관됨. 따라서 mock seam도
`GeminiExtractor._get_client`(제거됨) → `google.genai.Client`(코어 provider가 생성)로 이동.
호출 검증은 `mock_cls.return_value.models.generate_content.call_args` 로 한다.
max_output_tokens 는 미설정(extractor가 max_tokens 미지정) — provider 기본값 보존.

Gemini LLM 호출은 전부 mock. 실제 API 호출 절대 금지.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.sec_pipeline.extractor import GeminiExtractor


@pytest.fixture
def extractor():
    return GeminiExtractor()


@pytest.fixture(autouse=True)
def _gemini_key(settings):
    # complete()의 gemini provider + extractor._ensure_api_key 둘 다 키 필요.
    settings.GEMINI_API_KEY = "fake-key"


def _mock_genai_response(text):
    response = MagicMock()
    response.text = text
    response.usage_metadata = None  # 코어 provider 토큰 추출(int) 안전 — None 필수
    return response


def _patch_genai_client(text):
    """google.genai.Client를 patch해 generate_content가 주어진 text를 반환하도록.

    complete() → gemini provider → genai.Client(api_key).models.generate_content 경로를 가로챈다.
    반환된 patcher 의 `mock_cls.return_value.models.generate_content` 로 call_args 검사.
    """
    patcher = patch("google.genai.Client")
    mock_cls = patcher.start()
    mock_cls.return_value.models.generate_content.return_value = _mock_genai_response(text)
    return patcher, mock_cls


# ---------------------------------------------------------------------------
# Tests: 호출 파라미터 검증
# ---------------------------------------------------------------------------

class TestExtractSupplyChainCallParams:
    def test_uses_gemini_25_flash_model(self, extractor):
        """generate_content 호출 시 model='gemini-2.5-flash' 가 전달된다."""
        patcher, mock_cls = _patch_genai_client(json.dumps({'relationships': []}))
        try:
            extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        kwargs = mock_cls.return_value.models.generate_content.call_args.kwargs
        assert kwargs['model'] == 'gemini-2.5-flash'

    def test_passes_config_object(self, extractor):
        """GenerateContentConfig 가 config 인자로 전달되며 우리가 지정한 값들을 보존한다."""
        patcher, mock_cls = _patch_genai_client(json.dumps({'relationships': []}))
        try:
            extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        kwargs = mock_cls.return_value.models.generate_content.call_args.kwargs
        config = kwargs['config']
        # provider 가 만든 GenerateContentConfig 에 우리가 지정한 값들이 들어있어야 함
        assert config.response_mime_type == 'application/json'
        assert config.temperature == pytest.approx(0.1)
        # thinking_config(thinking_budget=0) 보존
        assert config.thinking_config is not None
        assert config.thinking_config.thinking_budget == 0
        # max_output_tokens 는 미설정(extractor가 max_tokens 미지정 → provider 기본)
        assert config.max_output_tokens is None

    def test_empty_paragraphs_skips_llm_call(self, extractor):
        """paragraphs 가 비어있으면 genai.Client 자체가 호출되지 않는다."""
        with patch('google.genai.Client') as mock_cls:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', [])
            assert result == {'relationships': []}
            mock_cls.assert_not_called()


class TestExtractBusinessModelCallParams:
    def test_uses_gemini_25_flash_model(self, extractor):
        patcher, mock_cls = _patch_genai_client('{}')
        try:
            extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        kwargs = mock_cls.return_value.models.generate_content.call_args.kwargs
        assert kwargs['model'] == 'gemini-2.5-flash'

    def test_prompt_includes_paragraphs(self, extractor):
        """프롬프트에 입력 paragraphs 가 모두 포함된다."""
        patcher, mock_cls = _patch_genai_client('{}')
        try:
            extractor.extract_business_model(
                'NFLX', 'Netflix Inc.',
                ['Subscription-based streaming.', 'Direct-to-consumer model.']
            )
        finally:
            patcher.stop()
        prompt = mock_cls.return_value.models.generate_content.call_args.kwargs['contents']
        assert 'Netflix Inc.' in prompt
        assert 'Subscription-based streaming.' in prompt
        assert 'Direct-to-consumer model.' in prompt

    def test_empty_paragraphs_skips_llm(self, extractor):
        """paragraphs 가 비면 LLM 호출 없이 빈 dict 반환."""
        with patch('google.genai.Client') as mock_cls:
            result = extractor.extract_business_model('AAPL', 'Apple Inc.', [])
            assert result == {}
            mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: 단일 paragraph
# ---------------------------------------------------------------------------

class TestSingleParagraph:
    def test_single_paragraph_no_separator_artifacts(self, extractor):
        """단일 paragraph 입력 시 '---' 구분자가 추가로 등장하지 않는다."""
        patcher, mock_cls = _patch_genai_client(json.dumps({'relationships': []}))
        try:
            extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['Only one paragraph.'])
        finally:
            patcher.stop()
        prompt = mock_cls.return_value.models.generate_content.call_args.kwargs['contents']
        # 단일 paragraph 입력은 join 후에도 '---' 가 본문에 없어야 함
        # (paragraphs_text 만 봤을 때 separator 미발생)
        assert 'Only one paragraph.' in prompt


# ---------------------------------------------------------------------------
# Tests: API 키 검증 (구 _get_client 초기상태 → 슬라이스 ④ _ensure_api_key)
# ---------------------------------------------------------------------------

class TestEnsureApiKey:
    def test_no_api_key_raises(self, extractor):
        """키 누락 시 _ensure_api_key 가 조기 ValueError (구 _get_client 동작 보존)."""
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                extractor._ensure_api_key()

    def test_api_key_present_passes(self, extractor):
        """키가 있으면 _ensure_api_key 가 통과(예외 없음)."""
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = 'test-key'
            extractor._ensure_api_key()  # 예외 없이 반환
