"""
ContextCompressor / QuestionAwareCompressor 단위 테스트

Gemini API 호출은 mock, 폴백(truncate) 및 유틸 메서드는 실제 로직으로 검증합니다.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.rag_analysis.services.context_compressor import (
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

def _make_gemini_response(text):
    """shared/llm gemini provider가 _extract_raw로 읽을 수 있는 응답 mock.

    text + usage_metadata=None (코어 provider가 usage_metadata에서 int 토큰 추출 →
    None이면 `getattr(..., 0) or 0`으로 0 처리. MagicMock이면 int() TypeError).
    """
    resp = MagicMock()
    resp.text = text
    resp.usage_metadata = None
    return resp


class TestCompressWithGemini:
    """Gemini API를 mock한 compress() 테스트.

    슬라이스 ④ Part ①-aio: client.aio.models.generate_content 직접호출 →
    shared/llm acomplete() 경유. seam이 `self.client`(genai.Client) →
    `self._llm_enabled`(bool) + `google.genai.Client` patch로 바뀜.
    """

    def test_empty_documents(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor._llm_enabled = True
            result = _run(compressor.compress([], 'any question'))
            assert result == []

    def test_no_client_uses_fallback(self):
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor._llm_enabled = False
            docs = _make_documents(2)
            result = _run(compressor.compress(docs, 'question'))
            assert len(result) == 2
            for r in result:
                assert 'compressed' in r
                assert 'compression_ratio' in r

    def test_successful_compression(self, settings):
        settings.GEMINI_API_KEY = 'fake-key'
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor._llm_enabled = True

            resp = _make_gemini_response('  Compressed summary here  ')
            with patch('google.genai.Client') as mock_cls:
                mock_cls.return_value.aio.models.generate_content = AsyncMock(
                    return_value=resp
                )

                docs = _make_documents(1)
                result = _run(compressor.compress(docs, 'question'))
            assert len(result) == 1
            assert result[0]['compressed'] == 'Compressed summary here'

    def test_api_error_falls_back_to_truncate(self, settings):
        settings.GEMINI_API_KEY = 'fake-key'
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor._llm_enabled = True

            # generate_content가 raise → acomplete 내 provider._classify가 분류 후 re-raise.
            # 'API failed'는 어떤 분류 규칙에도 안 걸려 원본 RuntimeError 그대로 전파 →
            # context_compressor try/except가 잡고 gather(return_exceptions)가 폴백.
            with patch('google.genai.Client') as mock_cls:
                mock_cls.return_value.aio.models.generate_content = AsyncMock(
                    side_effect=RuntimeError('API failed')
                )

                docs = _make_documents(1)
                result = _run(compressor.compress(docs, 'q'))
            assert len(result) == 1
            # 폴백이므로 여전히 결과가 있어야 함
            assert 'compressed' in result[0]

    def test_batch_processing(self, settings):
        """MAX_CONCURRENT=5 배치 처리 확인"""
        settings.GEMINI_API_KEY = 'fake-key'
        with patch.object(ContextCompressor, '__init__', lambda self: None):
            compressor = ContextCompressor()
            compressor._llm_enabled = True
            compressor.MAX_CONCURRENT = 2  # 작은 배치 크기

            resp = _make_gemini_response('compressed')
            with patch('google.genai.Client') as mock_cls:
                gen = AsyncMock(return_value=resp)
                mock_cls.return_value.aio.models.generate_content = gen

                docs = _make_documents(5)
                result = _run(compressor.compress(docs, 'question'))
            assert len(result) == 5
            # 5개 문서 / batch_size 2 = 3 라운드 → generate_content 5번 호출
            assert gen.call_count == 5


# ---------------------------------------------------------------------------
# QuestionAwareCompressor
# ---------------------------------------------------------------------------

class TestQuestionAwareCompressor:
    """질문 맥락 기반 압축기"""

    def test_prompt_includes_question(self, settings):
        settings.GEMINI_API_KEY = 'fake-key'
        with patch.object(QuestionAwareCompressor, '__init__', lambda self: None):
            compressor = QuestionAwareCompressor()
            compressor._llm_enabled = True

            resp = _make_gemini_response('focused summary')
            with patch('google.genai.Client') as mock_cls:
                gen = AsyncMock(return_value=resp)
                mock_cls.return_value.aio.models.generate_content = gen

                doc = _make_doc(title='Earnings Report', content='Revenue was $94B')
                result = _run(compressor._compress_single(doc, 'AAPL 매출은?'))

                # generate_content 호출 시 question이 포함된 prompt(contents)인지 확인.
                # acomplete 경유 후에도 contents는 불변(byte 동일).
                call_args = gen.call_args
                contents = call_args.kwargs.get('contents', '')
                assert 'AAPL 매출은?' in contents
            assert result['compressed'] == 'focused summary'

    def test_inherits_fallback(self):
        with patch.object(QuestionAwareCompressor, '__init__', lambda self: None):
            compressor = QuestionAwareCompressor()
            compressor._llm_enabled = False
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
