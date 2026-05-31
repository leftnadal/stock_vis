"""
GeminiExtractor 단위 테스트.

Gemini LLM 호출은 전부 mock. 실제 API 호출 절대 금지.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.sec_pipeline.extractor import GeminiExtractor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def extractor():
    return GeminiExtractor()


def _mock_genai_response(text):
    response = MagicMock()
    response.text = text
    return response


# ---------------------------------------------------------------------------
# Tests: extract_supply_chain
# ---------------------------------------------------------------------------

class TestExtractSupplyChain:
    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_successful_extraction(self, mock_client, extractor):
        result_json = json.dumps({
            'relationships': [
                {
                    'target_company': 'TSMC',
                    'relationship_type': 'SUPPLIES_TO',
                    'evidence_text': 'TSMC manufactures chips for Apple',
                    'confidence': 0.9,
                },
            ]
        })
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response(result_json)
        mock_client.return_value = client

        result = extractor.extract_supply_chain(
            'AAPL', 'Apple Inc.',
            ['TSMC manufactures chips for Apple.']
        )
        assert 'relationships' in result
        assert len(result['relationships']) == 1
        assert result['relationships'][0]['target_company'] == 'TSMC'

    def test_empty_paragraphs(self, extractor):
        result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', [])
        assert result == {'relationships': []}

    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_json_parse_error(self, mock_client, extractor):
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response('not valid json{{{')
        mock_client.return_value = client

        result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['Some text'])
        assert result['relationships'] == []
        assert 'error' in result

    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_missing_relationships_key(self, mock_client, extractor):
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response('{"data": []}')
        mock_client.return_value = client

        result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        assert result == {'relationships': []}

    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_empty_response_text(self, mock_client, extractor):
        response = MagicMock()
        response.text = None
        client = MagicMock()
        client.models.generate_content.return_value = response
        mock_client.return_value = client

        result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        assert result == {'relationships': []}


# ---------------------------------------------------------------------------
# Tests: extract_business_model
# ---------------------------------------------------------------------------

class TestExtractBusinessModel:
    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_successful_extraction(self, mock_client, extractor):
        result_json = json.dumps({
            'direct_customer_contact': {
                'value': 'direct', 'evidence_text': 'sells directly', 'confidence': 0.8
            },
            'contract_model': {
                'value': 'subscription', 'evidence_text': 'SaaS model', 'confidence': 0.7
            },
        })
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response(result_json)
        mock_client.return_value = client

        result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        assert 'direct_customer_contact' in result
        assert result['direct_customer_contact']['value'] == 'direct'

    def test_empty_paragraphs(self, extractor):
        result = extractor.extract_business_model('AAPL', 'Apple Inc.', [])
        assert result == {}

    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_json_error(self, mock_client, extractor):
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response('bad json')
        mock_client.return_value = client

        result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        assert 'error' in result


# ---------------------------------------------------------------------------
# Tests: _get_client
# ---------------------------------------------------------------------------

class TestGetClient:
    def test_no_api_key_raises(self, extractor):
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                extractor._get_client()
