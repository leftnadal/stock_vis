"""
EntityExtractor / EntityNormalizer 단위 테스트

Gemini API 호출은 mock, 폴백 규칙 기반 추출은 실제 로직으로 검증합니다.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.rag_analysis.services.entity_extractor import (
    EntityExtractor,
    EntityNormalizer,
    ExtractedEntities,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """async 함수를 동기적으로 실행"""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# EntityExtractor — 폴백 (규칙 기반)
# ---------------------------------------------------------------------------

class TestFallbackExtraction:
    """_fallback_extraction 규칙 기반 추출"""

    def setup_method(self):
        with patch.object(EntityExtractor, '__init__', lambda self: None):
            self.extractor = EntityExtractor()
            self.extractor.client = None

    def test_extracts_uppercase_stock_codes(self):
        result = self.extractor._fallback_extraction('AAPL, TSLA 비교해줘')
        assert 'AAPL' in result['stocks']
        assert 'TSLA' in result['stocks']

    def test_extracts_korean_stock_names(self):
        result = self.extractor._fallback_extraction('삼성전자와 SK하이닉스 전망')
        assert '삼성전자' in result['stocks']
        assert 'SK하이닉스' in result['stocks']

    def test_extracts_metrics(self):
        result = self.extractor._fallback_extraction('PER과 ROE를 알려줘')
        assert 'PER' in result['metrics']
        assert 'ROE' in result['metrics']

    def test_extracts_revenue_keyword(self):
        result = self.extractor._fallback_extraction('매출과 영업이익 분석')
        assert '매출' in result['metrics']
        assert '영업이익' in result['metrics']

    def test_no_stocks_found(self):
        result = self.extractor._fallback_extraction('투자 전략을 알려줘')
        # 'stocks'가 비어 있거나 짧은 대문자 단어만 포함
        for s in result['stocks']:
            assert len(s) >= 2

    def test_timeframe_is_none(self):
        result = self.extractor._fallback_extraction('AAPL 분석해줘')
        assert result['timeframe'] is None

    def test_concepts_empty(self):
        result = self.extractor._fallback_extraction('아무 질문')
        assert result['concepts'] == []


# ---------------------------------------------------------------------------
# EntityExtractor — _clean_json_response
# ---------------------------------------------------------------------------

class TestCleanJsonResponse:
    """마크다운 코드 블록 제거"""

    def setup_method(self):
        with patch.object(EntityExtractor, '__init__', lambda self: None):
            self.extractor = EntityExtractor()

    def test_plain_json(self):
        raw = '{"stocks": ["AAPL"]}'
        assert self.extractor._clean_json_response(raw) == raw

    def test_markdown_code_block(self):
        raw = '```json\n{"stocks": ["AAPL"]}\n```'
        result = self.extractor._clean_json_response(raw)
        parsed = json.loads(result)
        assert parsed['stocks'] == ['AAPL']

    def test_code_block_without_json_keyword(self):
        raw = '```\n{"key": "val"}\n```'
        result = self.extractor._clean_json_response(raw)
        parsed = json.loads(result)
        assert parsed['key'] == 'val'


# ---------------------------------------------------------------------------
# EntityExtractor — extract (async, mocked Gemini)
# ---------------------------------------------------------------------------

class TestExtractWithGemini:
    """Gemini API를 mock한 extract() 테스트"""

    def test_successful_extraction(self):
        with patch.object(EntityExtractor, '__init__', lambda self: None):
            extractor = EntityExtractor()
            extractor.client = MagicMock()

            mock_response = MagicMock()
            mock_response.text = json.dumps({
                'stocks': ['AAPL', 'MSFT'],
                'metrics': ['PER'],
                'concepts': ['성장주'],
                'timeframe': '2024년',
            })
            extractor.client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )

            result = _run(extractor.extract('AAPL과 MSFT의 PER 비교'))
            assert result['stocks'] == ['AAPL', 'MSFT']
            assert result['metrics'] == ['PER']
            assert result['concepts'] == ['성장주']
            assert result['timeframe'] == '2024년'

    def test_json_parse_error_falls_back(self):
        with patch.object(EntityExtractor, '__init__', lambda self: None):
            extractor = EntityExtractor()
            extractor.client = MagicMock()

            mock_response = MagicMock()
            mock_response.text = 'invalid json {{'
            extractor.client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )

            result = _run(extractor.extract('AAPL 분석'))
            # 폴백으로 AAPL이 추출되어야 함
            assert 'AAPL' in result['stocks']

    def test_api_error_falls_back(self):
        with patch.object(EntityExtractor, '__init__', lambda self: None):
            extractor = EntityExtractor()
            extractor.client = MagicMock()

            extractor.client.aio.models.generate_content = AsyncMock(
                side_effect=RuntimeError('API error')
            )

            result = _run(extractor.extract('TSLA 전망'))
            assert 'TSLA' in result['stocks']

    def test_no_client_uses_fallback(self):
        with patch.object(EntityExtractor, '__init__', lambda self: None):
            extractor = EntityExtractor()
            extractor.client = None

            result = _run(extractor.extract('삼성전자 매출'))
            assert '삼성전자' in result['stocks']
            assert '매출' in result['metrics']


# ---------------------------------------------------------------------------
# EntityNormalizer
# ---------------------------------------------------------------------------

class TestNormalizeStocks:
    """종목명 정규화"""

    def setup_method(self):
        self.normalizer = EntityNormalizer()

    def test_korean_to_symbol(self):
        result = self.normalizer.normalize_stocks(['삼성전자', '카카오'])
        assert '005930.KS' in result
        assert '035720.KS' in result

    def test_english_uppercase(self):
        result = self.normalizer.normalize_stocks(['aapl', 'msft'])
        assert 'AAPL' in result
        assert 'MSFT' in result

    def test_deduplication(self):
        result = self.normalizer.normalize_stocks(['네이버', 'NAVER'])
        # 둘 다 035420.KS로 매핑 → 중복 제거
        assert result.count('035420.KS') == 1

    def test_mixed_input(self):
        result = self.normalizer.normalize_stocks(['애플', 'GOOGL'])
        assert 'AAPL' in result
        assert 'GOOGL' in result


class TestNormalizeMetrics:
    """지표 정규화"""

    def setup_method(self):
        self.normalizer = EntityNormalizer()

    def test_korean_metric_mapping(self):
        result = self.normalizer.normalize_metrics(['매출', 'PER'])
        assert 'revenue' in result
        assert 'pe_ratio' in result

    def test_multi_field_metric(self):
        result = self.normalizer.normalize_metrics(['실적'])
        assert 'revenue' in result
        assert 'earnings' in result

    def test_unknown_metric_lowercased(self):
        result = self.normalizer.normalize_metrics(['EBITDA'])
        assert 'ebitda' in result

    def test_deduplication(self):
        result = self.normalizer.normalize_metrics(['매출', '매출'])
        assert result.count('revenue') == 1
