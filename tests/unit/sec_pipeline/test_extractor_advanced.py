"""
GeminiExtractor 추가 단위 테스트.

기존 test_extractor.py에서 누락된 영역:
- _get_client lazy init / 캐싱
- 프롬프트에 paragraphs/symbol 주입 검증
- 비-JSON Exception 재발생
- empty response.text 처리

Gemini LLM 호출은 전부 mock. 실제 API 호출 절대 금지.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.sec_pipeline.extractor import GeminiExtractor


@pytest.fixture
def extractor():
    return GeminiExtractor()


def _mock_genai_response(text):
    response = MagicMock()
    response.text = text
    return response


# ---------------------------------------------------------------------------
# Tests: _get_client lazy init / 캐싱
# ---------------------------------------------------------------------------

class TestGetClientCaching:
    def test_client_cached_after_first_call(self, extractor):
        """동일 인스턴스에서 두 번 호출 시 client 1번만 생성."""
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = 'test-key'
            with patch('google.genai.Client') as mock_genai_client:
                mock_genai_client.return_value = MagicMock()
                c1 = extractor._get_client()
                c2 = extractor._get_client()
                assert c1 is c2
                # 한 번만 생성되어야 함
                assert mock_genai_client.call_count == 1

    def test_client_initialized_with_api_key(self, extractor):
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = 'real-key'
            with patch('google.genai.Client') as mock_genai_client:
                mock_genai_client.return_value = MagicMock()
                extractor._get_client()
                mock_genai_client.assert_called_once_with(api_key='real-key')


# ---------------------------------------------------------------------------
# Tests: extract_supply_chain — 프롬프트 검증 / 예외 재발생
# ---------------------------------------------------------------------------

class TestExtractSupplyChainAdvanced:
    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_paragraphs_joined_into_prompt(self, mock_get_client, extractor):
        """다수 paragraphs는 '---' 구분자로 join되어 프롬프트에 포함."""
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response(
            json.dumps({'relationships': []})
        )
        mock_get_client.return_value = client

        extractor.extract_supply_chain(
            'AAPL', 'Apple Inc.',
            ['First paragraph about TSMC.', 'Second paragraph about Samsung.']
        )
        # generate_content는 contents kwarg로 prompt를 받음
        call_kwargs = client.models.generate_content.call_args.kwargs
        prompt = call_kwargs['contents']
        assert 'AAPL' in prompt
        assert 'Apple Inc.' in prompt
        assert 'TSMC' in prompt
        assert 'Samsung' in prompt
        assert '---' in prompt

    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_non_json_exception_reraises(self, mock_get_client, extractor):
        """JSON 외 예외(예: API 오류)는 caller로 전파."""
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError('API down')
        mock_get_client.return_value = client

        with pytest.raises(RuntimeError, match='API down'):
            extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])


# ---------------------------------------------------------------------------
# Tests: extract_business_model — 추가 케이스
# ---------------------------------------------------------------------------

class TestExtractBusinessModelAdvanced:
    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_empty_response_text_returns_dict(self, mock_get_client, extractor):
        """response.text가 None이면 빈 dict 반환 ('{}' 파싱)."""
        response = MagicMock()
        response.text = None
        client = MagicMock()
        client.models.generate_content.return_value = response
        mock_get_client.return_value = client

        result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        # text=None → '{}' fallback → 빈 dict
        assert result == {}

    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_non_json_exception_reraises(self, mock_get_client, extractor):
        client = MagicMock()
        client.models.generate_content.side_effect = ConnectionError('timeout')
        mock_get_client.return_value = client

        with pytest.raises(ConnectionError):
            extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])

    @patch('services.sec_pipeline.extractor.GeminiExtractor._get_client')
    def test_full_5_field_response_preserved(self, mock_get_client, extractor):
        """5개 필드 응답이 그대로 전달되는지 확인."""
        result_json = json.dumps({
            'direct_customer_contact': {'value': 'direct', 'evidence_text': 'a', 'confidence': 0.9},
            'contract_model': {'value': 'subscription', 'evidence_text': 'b', 'confidence': 0.8},
            'recurring_revenue_signal': {'value': 'high', 'evidence_text': 'c', 'confidence': 0.7},
            'channel_dependency': {'value': 'low_dependency', 'evidence_text': 'd', 'confidence': 0.6},
            'customer_concentration': {'value': 'diversified', 'evidence_text': 'e', 'confidence': 0.5},
        })
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response(result_json)
        mock_get_client.return_value = client

        result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        assert set(result.keys()) == {
            'direct_customer_contact', 'contract_model',
            'recurring_revenue_signal', 'channel_dependency',
            'customer_concentration',
        }
        assert result['recurring_revenue_signal']['value'] == 'high'
