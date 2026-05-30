"""
ContextCompressor / QuestionAwareCompressor 단위 테스트

Gemini API 호출은 mock, 폴백(truncate) 및 유틸 메서드는 실제 로직으로 검증합니다.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_analysis.services.context_compressor import (
    ContextCompressor,
    QuestionAwareCompressor,
    get_context_compressor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """async 함수를 동기적으로 실행"""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_doc(title='Test Doc', content='Some long content here', **extra):
    """테스트 문서 생성"""
    doc = {'title': title, 'content': content}
    doc.update(extra)
    return doc


def _make_documents(n=3):
    """(doc, score, metadata) 튜플 리스트 생성"""
    return [
        (_make_doc(title=f'Doc {i}', content=f'Content for document {i}'), 0.9 - i * 0.1, {})
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# _estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    """토큰 수 추정"""

    def setup_method(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            self.compressor = ContextCompressor()

    def test_empty_string(self):
        assert self.compressor._estimate_tokens('') == 0

    def test_single_word(self):
        # 1 word * 1.5 = 1 (int)
        assert self.compressor._estimate_tokens('hello') == 1

    def test_multiple_words(self):
        text = 'one two three four'  # 4 words * 1.5 = 6
        assert self.compressor._estimate_tokens(text) == 6


# ---------------------------------------------------------------------------
# _get_document_text
# ---------------------------------------------------------------------------

class TestGetDocumentText:
    """문서 텍스트 추출"""

    def setup_method(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            self.compressor = ContextCompressor()

    def test_title_and_content(self):
        doc = {'title': 'My Title', 'content': 'My Content'}
        result = self.compressor._get_document_text(doc)
        assert result == 'My Title\nMy Content'

    def test_text_field_fallback(self):
        doc = {'text': 'Alt Content'}
        result = self.compressor._get_document_text(doc)
        assert result == 'Alt Content'

    def test_truncation_at_1000(self):
        doc = {'content': 'x' * 2000}
        result = self.compressor._get_document_text(doc)
        assert len(result) == 1000

    def test_empty_doc(self):
        result = self.compressor._get_document_text({})
        assert result == ''


# ---------------------------------------------------------------------------
# _generate_doc_id
# ---------------------------------------------------------------------------

class TestGenerateDocId:
    """문서 ID 생성"""

    def setup_method(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            self.compressor = ContextCompressor()

    def test_with_symbol_date_type(self):
        doc = {'symbol': 'aapl', 'date': '2024-01-01', 'type': 'financial'}
        result = self.compressor._generate_doc_id(doc)
        assert result == 'AAPL_2024-01-01_financial'

    def test_symbol_only(self):
        doc = {'symbol': 'msft'}
        result = self.compressor._generate_doc_id(doc)
        assert result == 'MSFT'

    def test_fallback_hash(self):
        doc = {'random_field': 'value'}
        result = self.compressor._generate_doc_id(doc)
        # hash 값이므로 숫자 문자열
        assert result  # non-empty


# ---------------------------------------------------------------------------
# _fallback_compress
# ---------------------------------------------------------------------------

class TestFallbackCompress:
    """폴백 truncate 압축"""

    def setup_method(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            self.compressor = ContextCompressor()

    def test_short_doc_unchanged(self):
        doc = {'title': 'Short', 'content': 'A few words only.', 'id': 'doc1'}
        result = self.compressor._fallback_compress(doc)
        assert result['original_id'] == 'doc1'
        assert result['title'] == 'Short'
        assert '...' not in result['compressed']

    def test_long_doc_truncated(self):
        long_content = ' '.join([f'word{i}' for i in range(200)])
        doc = {'content': long_content, 'id': 'long'}
        result = self.compressor._fallback_compress(doc)
        # 100 단어로 잘리고 ... 추가
        assert result['compressed'].endswith('...')
        word_count = len(result['compressed'].replace('...', '').split())
        assert word_count == 100

    def test_compression_ratio(self):
        doc = {'content': 'a b c d e', 'id': 'small'}
        result = self.compressor._fallback_compress(doc)
        assert 0 < result['compression_ratio'] <= 1.0
        assert result['original_tokens'] > 0
        assert result['compressed_tokens'] > 0


# ---------------------------------------------------------------------------
# compress (async, mocked Gemini)
# ---------------------------------------------------------------------------

class TestCompressWithGemini:
    """Gemini API를 mock한 compress() 테스트"""

    def test_empty_documents(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor.client = MagicMock()
            result = _run(compressor.compress([], 'any question'))
            assert result == []

    def test_no_client_uses_fallback(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor.client = None
            docs = _make_documents(2)
            result = _run(compressor.compress(docs, 'question'))
            assert len(result) == 2
            for r in result:
                assert 'compressed' in r
                assert 'compression_ratio' in r

    def test_successful_compression(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor.client = MagicMock()

            mock_response = MagicMock()
            mock_response.text = '  Compressed summary here  '
            compressor.client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )

            docs = _make_documents(1)
            result = _run(compressor.compress(docs, 'question'))
            assert len(result) == 1
            assert result[0]['compressed'] == 'Compressed summary here'

    def test_api_error_falls_back_to_truncate(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor.client = MagicMock()

            compressor.client.aio.models.generate_content = AsyncMock(
                side_effect=RuntimeError('API failed')
            )

            docs = _make_documents(1)
            result = _run(compressor.compress(docs, 'q'))
            assert len(result) == 1
            # 폴백이므로 여전히 결과가 있어야 함
            assert 'compressed' in result[0]

    def test_batch_processing(self):
        """MAX_CONCURRENT=5 배치 처리 확인"""
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor.client = MagicMock()
            compressor.MAX_CONCURRENT = 2  # 작은 배치 크기

            mock_response = MagicMock()
            mock_response.text = 'compressed'
            compressor.client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )

            docs = _make_documents(5)
            result = _run(compressor.compress(docs, 'question'))
            assert len(result) == 5
            # 5개 문서 / batch_size 2 = 3 라운드 → generate_content 5번 호출
            assert compressor.client.aio.models.generate_content.call_count == 5


# ---------------------------------------------------------------------------
# QuestionAwareCompressor
# ---------------------------------------------------------------------------

class TestQuestionAwareCompressor:
    """질문 맥락 기반 압축기"""

    def test_prompt_includes_question(self):
        with patch.object(QuestionAwareCompressor, '__init__', lambda self: None):
            compressor = QuestionAwareCompressor()
            compressor.client = MagicMock()

            mock_response = MagicMock()
            mock_response.text = 'focused summary'
            compressor.client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )

            doc = _make_doc(title='Earnings Report', content='Revenue was $94B')
            result = _run(compressor._compress_single(doc, 'AAPL 매출은?'))

            # generate_content 호출 시 question이 포함된 prompt인지 확인
            call_args = compressor.client.aio.models.generate_content.call_args
            prompt_text = call_args.kwargs.get('contents', call_args.args[0] if call_args.args else '')
            # contents kwarg로 전달
            contents = call_args[1].get('contents', '') if len(call_args) > 1 else ''
            assert result['compressed'] == 'focused summary'

    def test_inherits_fallback(self):
        with patch.object(QuestionAwareCompressor, '__init__', lambda self: None):
            compressor = QuestionAwareCompressor()
            compressor.client = None
            docs = _make_documents(1)
            result = _run(compressor.compress(docs, 'question'))
            assert len(result) == 1
            assert 'compressed' in result[0]


# ---------------------------------------------------------------------------
# get_context_compressor factory
# ---------------------------------------------------------------------------

class TestGetContextCompressor:
    """팩토리 함수"""

    def test_default_returns_base(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            with patch.object(QuestionAwareCompressor, '__init__', lambda self: None):
                compressor = get_context_compressor(question_aware=False)
                assert type(compressor) is ContextCompressor

    def test_question_aware_flag(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            with patch.object(QuestionAwareCompressor, '__init__', lambda self: None):
                compressor = get_context_compressor(question_aware=True)
                assert isinstance(compressor, QuestionAwareCompressor)
