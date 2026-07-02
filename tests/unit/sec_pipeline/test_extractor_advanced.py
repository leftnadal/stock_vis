"""
GeminiExtractor 추가 단위 테스트.

기존 test_extractor.py에서 누락된 영역:
- _ensure_api_key 키 검증 (구 _get_client lazy init/캐싱 → 슬라이스 ④에서 의미 변경)
- 프롬프트에 paragraphs/symbol 주입 검증
- 비-JSON Exception 재발생
- empty response.text 처리

슬라이스 ④: genai 직접호출 → shared/llm complete() 경유로 이관됨. 따라서 mock seam도
`GeminiExtractor._get_client`(제거됨) → `google.genai.Client`(코어 provider가 생성)로 이동.

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
# Tests: _ensure_api_key (구 _get_client 키 검증 — 슬라이스 ④에서 rename)
# ---------------------------------------------------------------------------

class TestEnsureApiKey:
    def test_ensure_passes_with_key(self, extractor):
        """키가 설정되어 있으면 예외 없이 통과."""
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = 'test-key'
            # 예외가 발생하지 않으면 성공
            extractor._ensure_api_key()

    def test_ensure_raises_without_key(self, extractor):
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                extractor._ensure_api_key()


# ---------------------------------------------------------------------------
# Tests: extract_supply_chain — 프롬프트 검증 / 예외 재발생
# ---------------------------------------------------------------------------

class TestExtractSupplyChainAdvanced:
    def test_paragraphs_joined_into_prompt(self, extractor):
        """다수 paragraphs는 '---' 구분자로 join되어 프롬프트에 포함."""
        patcher = patch("google.genai.Client")
        mock_cls = patcher.start()
        mock_cls.return_value.models.generate_content.return_value = (
            _mock_genai_response(json.dumps({'relationships': []}))
        )
        try:
            extractor.extract_supply_chain(
                'AAPL', 'Apple Inc.',
                ['First paragraph about TSMC.', 'Second paragraph about Samsung.']
            )
            # generate_content는 contents kwarg로 prompt를 받음(빌더 불변)
            call = mock_cls.return_value.models.generate_content.call_args
            prompt = call.kwargs['contents']
            assert 'AAPL' in prompt
            assert 'Apple Inc.' in prompt
            assert 'TSMC' in prompt
            assert 'Samsung' in prompt
            assert '---' in prompt
            # config는 provider가 만든 GenerateContentConfig — json mime + temperature 보존,
            # max_output_tokens는 미설정(None).
            config = call.kwargs['config']
            assert config.response_mime_type == 'application/json'
            assert config.temperature == 0.1
            assert config.max_output_tokens is None
        finally:
            patcher.stop()

    def test_non_json_exception_reraises(self, extractor):
        """JSON 외 예외(예: API 오류)는 caller로 전파.

        complete()는 genai 예외를 코어 계층(LLMError 하위)으로 재분류한다. 'API down'은
        분류 규칙에 걸리지 않으므로(api key/invalid/timeout 등 키워드 없음) 원본 RuntimeError
        그대로 전파된다.
        """
        patcher = patch("google.genai.Client")
        mock_cls = patcher.start()
        mock_cls.return_value.models.generate_content.side_effect = RuntimeError('API down')
        try:
            with pytest.raises(RuntimeError, match='API down'):
                extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()


# ---------------------------------------------------------------------------
# Tests: extract_business_model — 추가 케이스
# ---------------------------------------------------------------------------

class TestExtractBusinessModelAdvanced:
    def test_empty_response_text_returns_dict(self, extractor):
        """response.text가 None이면 빈 dict 반환 ('{}' 파싱)."""
        patcher = _patch_genai_client(None)
        try:
            result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        # text=None → '{}' fallback → 빈 dict
        assert result == {}

    def test_non_json_exception_reraises(self, extractor):
        """비-JSON 예외는 caller로 전파.

        complete()는 genai 예외를 코어 계층으로 재분류한다. 'connection refused'는 분류
        키워드(timeout/deadline/quota/api key/invalid 등)에 걸리지 않으므로 원본
        ConnectionError 그대로 전파된다(의도: 예외 전파 보존).
        """
        patcher = patch("google.genai.Client")
        mock_cls = patcher.start()
        mock_cls.return_value.models.generate_content.side_effect = ConnectionError(
            'connection refused'
        )
        try:
            with pytest.raises(ConnectionError):
                extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()

    def test_full_5_field_response_preserved(self, extractor):
        """5개 필드 응답이 그대로 전달되는지 확인."""
        result_json = json.dumps({
            'direct_customer_contact': {'value': 'direct', 'evidence_text': 'a', 'confidence': 0.9},
            'contract_model': {'value': 'subscription', 'evidence_text': 'b', 'confidence': 0.8},
            'recurring_revenue_signal': {'value': 'high', 'evidence_text': 'c', 'confidence': 0.7},
            'channel_dependency': {'value': 'low_dependency', 'evidence_text': 'd', 'confidence': 0.6},
            'customer_concentration': {'value': 'diversified', 'evidence_text': 'e', 'confidence': 0.5},
        })
        patcher = _patch_genai_client(result_json)
        try:
            result = extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        assert set(result.keys()) == {
            'direct_customer_contact', 'contract_model',
            'recurring_revenue_signal', 'channel_dependency',
            'customer_concentration',
        }
        assert result['recurring_revenue_signal']['value'] == 'high'
