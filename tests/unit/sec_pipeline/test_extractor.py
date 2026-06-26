"""
GeminiExtractor 단위 테스트.

Gemini LLM 호출은 전부 mock. 실제 API 호출 절대 금지.

슬라이스 ④: genai 직접호출 → shared/llm complete() 경유로 이관됨. 따라서 mock seam도
`GeminiExtractor._get_client`(제거됨) → `google.genai.Client`(코어 provider가 생성)로 이동.
파싱·에러 처리 검증 의도는 그대로(행위 보존).
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


@pytest.fixture(autouse=True)
def _gemini_key(settings):
    # complete()의 gemini provider + extractor._ensure_api_key 둘 다 키 필요.
    settings.GEMINI_API_KEY = "fake-key"


def _mock_genai_response(text):
    response = MagicMock()
    response.text = text
    response.usage_metadata = None  # 코어 provider 토큰 추출(int) 안전
    return response


def _patch_genai_client(text):
    """google.genai.Client를 patch해 generate_content가 주어진 text를 반환하도록.

    complete() → gemini provider → genai.Client(api_key).models.generate_content 경로를 가로챈다.
    """
    patcher = patch("google.genai.Client")
    mock_cls = patcher.start()
    mock_cls.return_value.models.generate_content.return_value = _mock_genai_response(text)
    return patcher


# ---------------------------------------------------------------------------
# Tests: extract_supply_chain
# ---------------------------------------------------------------------------

class TestExtractSupplyChain:
    def test_successful_extraction(self, extractor):
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
        patcher = _patch_genai_client(result_json)
        try:
            result = extractor.extract_supply_chain(
                'AAPL', 'Apple Inc.',
                ['TSMC manufactures chips for Apple.']
            )
        finally:
            patcher.stop()
        assert 'relationships' in result
        assert len(result['relationships']) == 1
        assert result['relationships'][0]['target_company'] == 'TSMC'

    def test_empty_paragraphs(self, extractor):
        result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', [])
        assert result == {'relationships': []}

    def test_json_parse_error(self, extractor):
        patcher = _patch_genai_client('not valid json{{{')
        try:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['Some text'])
        finally:
            patcher.stop()
        assert result['relationships'] == []
        assert 'error' in result

    def test_missing_relationships_key(self, extractor):
        patcher = _patch_genai_client('{"data": []}')
        try:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        assert result == {'relationships': []}

    def test_empty_response_text(self, extractor):
        patcher = _patch_genai_client(None)
        try:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        assert result == {'relationships': []}


# ---------------------------------------------------------------------------
# Tests: extract_business_model
# ---------------------------------------------------------------------------

class TestExtractBusinessModel:
    def test_successful_extraction(self, extractor):
        result_json = json.dumps({
            'direct_customer_contact': {
                'value': 'direct', 'evidence_text': 'sells directly', 'confidence': 0.8
            },
            'contract_model': {
                'value': 'subscription', 'evidence_text': 'SaaS model', 'confidence': 0.7
            },
        })
        patcher = _patch_genai_client(result_json)
        try:
            result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        assert 'direct_customer_contact' in result
        assert result['direct_customer_contact']['value'] == 'direct'

    def test_empty_paragraphs(self, extractor):
        result = extractor.extract_business_model('AAPL', 'Apple Inc.', [])
        assert result == {}

    def test_json_error(self, extractor):
        patcher = _patch_genai_client('bad json')
        try:
            result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        assert 'error' in result


# ---------------------------------------------------------------------------
# Tests: _ensure_api_key (구 _get_client 키 검증 — 슬라이스 ④에서 rename)
# ---------------------------------------------------------------------------

class TestEnsureApiKey:
    def test_no_api_key_raises(self, extractor):
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                extractor._ensure_api_key()
