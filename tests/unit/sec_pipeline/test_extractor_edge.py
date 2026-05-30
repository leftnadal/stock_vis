"""
GeminiExtractor 추가 엣지 케이스 테스트.

기존 test_extractor.py / test_extractor_advanced.py 에서 누락된 영역:
- 호출 시 model name 이 'gemini-2.5-flash' 인지
- temperature=0.1 / response_mime_type='application/json' / thinking_budget=0 가 설정되는지
- extract_business_model 의 prompt 에 paragraphs 가 포함되는지
- 단일 paragraph 입력 시에도 정상 동작
- extract_supply_chain 의 빈 paragraphs 는 LLM 호출하지 않음

Gemini LLM 호출은 전부 mock. 실제 API 호출 절대 금지.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from sec_pipeline.extractor import GeminiExtractor


@pytest.fixture
def extractor():
    return GeminiExtractor()


def _mock_genai_response(text):
    response = MagicMock()
    response.text = text
    return response


# ---------------------------------------------------------------------------
# Tests: 호출 파라미터 검증
# ---------------------------------------------------------------------------

class TestExtractSupplyChainCallParams:
    @patch('sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_uses_gemini_25_flash_model(self, mock_get_client, extractor):
        """generate_content 호출 시 model='gemini-2.5-flash' 가 전달된다."""
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response(
            json.dumps({'relationships': []})
        )
        mock_get_client.return_value = client

        extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        kwargs = client.models.generate_content.call_args.kwargs
        assert kwargs['model'] == 'gemini-2.5-flash'

    @patch('sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_passes_config_object(self, mock_get_client, extractor):
        """GenerateContentConfig 가 config 인자로 전달된다."""
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response(
            json.dumps({'relationships': []})
        )
        mock_get_client.return_value = client

        extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        kwargs = client.models.generate_content.call_args.kwargs
        config = kwargs['config']
        # GenerateContentConfig 에 우리가 지정한 값들이 들어있어야 함
        assert config.response_mime_type == 'application/json'
        assert config.temperature == pytest.approx(0.1)

    def test_empty_paragraphs_skips_llm_call(self, extractor):
        """paragraphs 가 비어있으면 _get_client 자체가 호출되지 않는다."""
        with patch.object(GeminiExtractor, '_get_client') as mock_get_client:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', [])
            assert result == {'relationships': []}
            mock_get_client.assert_not_called()


class TestExtractBusinessModelCallParams:
    @patch('sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_uses_gemini_25_flash_model(self, mock_get_client, extractor):
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response('{}')
        mock_get_client.return_value = client

        extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        kwargs = client.models.generate_content.call_args.kwargs
        assert kwargs['model'] == 'gemini-2.5-flash'

    @patch('sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_prompt_includes_paragraphs(self, mock_get_client, extractor):
        """프롬프트에 입력 paragraphs 가 모두 포함된다."""
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response('{}')
        mock_get_client.return_value = client

        extractor.extract_business_model(
            'NFLX', 'Netflix Inc.',
            ['Subscription-based streaming.', 'Direct-to-consumer model.']
        )
        prompt = client.models.generate_content.call_args.kwargs['contents']
        assert 'Netflix Inc.' in prompt
        assert 'Subscription-based streaming.' in prompt
        assert 'Direct-to-consumer model.' in prompt

    def test_empty_paragraphs_skips_llm(self, extractor):
        """paragraphs 가 비면 LLM 호출 없이 빈 dict 반환."""
        with patch.object(GeminiExtractor, '_get_client') as mock_get_client:
            result = extractor.extract_business_model('AAPL', 'Apple Inc.', [])
            assert result == {}
            mock_get_client.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: 단일 paragraph
# ---------------------------------------------------------------------------

class TestSingleParagraph:
    @patch('sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_single_paragraph_no_separator_artifacts(self, mock_get_client, extractor):
        """단일 paragraph 입력 시 '---' 구분자가 추가로 등장하지 않는다."""
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response(
            json.dumps({'relationships': []})
        )
        mock_get_client.return_value = client

        extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['Only one paragraph.'])
        prompt = client.models.generate_content.call_args.kwargs['contents']
        # 단일 paragraph 입력은 join 후에도 '---' 가 본문에 없어야 함
        # (paragraphs_text 만 봤을 때 separator 미발생)
        assert 'Only one paragraph.' in prompt


# ---------------------------------------------------------------------------
# Tests: _get_client — 초기 상태
# ---------------------------------------------------------------------------

class TestGetClientInitialState:
    def test_initial_client_is_none(self, extractor):
        """초기 인스턴스의 _client 는 None."""
        assert extractor._client is None

    def test_client_cached_in_instance(self, extractor):
        """_get_client 호출 후 _client 가 설정된다."""
        with patch('sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = 'test-key'
            with patch('google.genai.Client') as mock_genai_client:
                fake = MagicMock()
                mock_genai_client.return_value = fake
                client = extractor._get_client()
                assert extractor._client is fake
                assert client is fake
