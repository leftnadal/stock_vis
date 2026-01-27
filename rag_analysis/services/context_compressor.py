"""
Context Compressor - Gemini Flash 기반 문서 압축

선별된 문서를 Gemini 2.5 Flash로 요약하여 토큰을 획기적으로 줄입니다.
"""

import asyncio
import logging
from typing import List, Tuple, Dict, Any, Optional

from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    컨텍스트 압축기 (Gemini Flash 기반)

    Features:
        - Gemini 2.5 Flash 사용 (빠르고 저렴)
        - 문서별 병렬 압축
        - 압축 실패 시 폴백 (truncate)
        - 압축률 추적
    """

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS_PER_DOC = 100
    MAX_CONCURRENT = 5  # 동시 압축 최대 개수

    COMPRESSION_PROMPT = """다음 문서를 핵심 정보만 남기고 50단어 이내로 압축하세요.
날짜, 수치, 고유명사는 반드시 포함하세요.

문서:
{document}

압축된 내용 (50단어 이내):"""

    def __init__(self):
        """Gemini API 클라이언트 초기화"""
        api_key = getattr(settings, 'GEMINI_API_KEY', None) or getattr(settings, 'GOOGLE_AI_API_KEY', None)

        if not api_key:
            logger.warning(
                "GEMINI_API_KEY not set. ContextCompressor will use fallback mode."
            )
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    async def compress(
        self,
        documents: List[Tuple[dict, float, dict]],
        question: str
    ) -> List[dict]:
        """
        문서 리스트 압축

        Args:
            documents: [(doc, score, metadata), ...]
            question: 사용자 질문 (미사용, QuestionAwareCompressor에서 사용)

        Returns:
            [
                {
                    'original_id': str,
                    'title': str,
                    'compressed': str,
                    'original_tokens': int,
                    'compressed_tokens': int,
                    'compression_ratio': float
                },
                ...
            ]
        """
        if not documents:
            logger.warning("No documents to compress")
            return []

        # API 키가 없으면 폴백 모드
        if not self.client:
            logger.info("Using fallback compression (truncate)")
            return [self._fallback_compress(doc) for doc, _, _ in documents]

        # 병렬 압축 (MAX_CONCURRENT 개씩)
        compressed_results = []

        for i in range(0, len(documents), self.MAX_CONCURRENT):
            batch = documents[i:i + self.MAX_CONCURRENT]
            tasks = [
                self._compress_single(doc, question)
                for doc, _, _ in batch
            ]

            # gather + return_exceptions로 에러 발생해도 계속 진행
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 에러 처리
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Compression failed for doc {i+idx}: {result}")
                    # 폴백 사용
                    doc = batch[idx][0]
                    compressed_results.append(self._fallback_compress(doc))
                else:
                    compressed_results.append(result)

        logger.info(f"Compressed {len(compressed_results)} documents")
        return compressed_results

    async def _compress_single(self, doc: dict, question: str) -> dict:
        """
        단일 문서 압축

        Args:
            doc: 문서 딕셔너리
            question: 사용자 질문 (기본 압축기에서는 미사용)

        Returns:
            압축 결과 딕셔너리
        """
        original_text = self._get_document_text(doc)
        original_tokens = self._estimate_tokens(original_text)

        try:
            config = types.GenerateContentConfig(
                max_output_tokens=self.MAX_TOKENS_PER_DOC,
                temperature=0.3,  # 낮은 온도로 일관된 압축
            )

            response = await self.client.aio.models.generate_content(
                model=self.MODEL,
                contents=self.COMPRESSION_PROMPT.format(document=original_text),
                config=config,
            )

            compressed_text = response.text.strip()
            compressed_tokens = self._estimate_tokens(compressed_text)

            return {
                'original_id': doc.get('id', self._generate_doc_id(doc)),
                'title': doc.get('title', ''),
                'compressed': compressed_text,
                'original_tokens': original_tokens,
                'compressed_tokens': compressed_tokens,
                'compression_ratio': compressed_tokens / max(original_tokens, 1)
            }

        except Exception as e:
            logger.error(f"Gemini API error during compression: {e}")
            raise

    def _get_document_text(self, doc: dict) -> str:
        """
        문서에서 텍스트 추출

        Args:
            doc: 문서 딕셔너리

        Returns:
            추출된 텍스트 (최대 1000자)
        """
        title = doc.get('title', '')
        content = doc.get('content', doc.get('text', ''))

        combined = f"{title}\n{content}" if title else content
        return combined[:1000]  # 1000자 제한

    def _fallback_compress(self, doc: dict) -> dict:
        """
        폴백: 단순 truncate

        Args:
            doc: 문서 딕셔너리

        Returns:
            압축 결과 (truncate)
        """
        text = self._get_document_text(doc)
        original_tokens = self._estimate_tokens(text)

        # 100 단어로 truncate
        words = text.split()[:100]
        compressed = ' '.join(words)
        if len(words) == 100:
            compressed += '...'

        compressed_tokens = self._estimate_tokens(compressed)

        return {
            'original_id': doc.get('id', self._generate_doc_id(doc)),
            'title': doc.get('title', ''),
            'compressed': compressed,
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            'compression_ratio': compressed_tokens / max(original_tokens, 1)
        }

    def _estimate_tokens(self, text: str) -> int:
        """
        토큰 수 추정 (간단한 어림법)

        Args:
            text: 텍스트

        Returns:
            추정 토큰 수 (영어 기준 1 토큰 ≈ 0.75 단어, 한글 기준 1 토큰 ≈ 0.5 단어)
        """
        # 공백 기준 단어 개수
        words = len(text.split())
        # 보수적 추정 (1 단어 = 1.5 토큰)
        return int(words * 1.5)

    def _generate_doc_id(self, doc: dict) -> str:
        """
        문서 ID 생성

        Args:
            doc: 문서 딕셔너리

        Returns:
            문서 ID
        """
        # symbol + date + type 조합
        parts = []
        if 'symbol' in doc:
            parts.append(doc['symbol'].upper())
        if 'date' in doc or 'created_at' in doc:
            parts.append(doc.get('date', doc.get('created_at', '')))
        if 'type' in doc:
            parts.append(doc['type'])

        if parts:
            return '_'.join(parts)

        # Fallback: 해시
        return str(hash(str(doc)))


class QuestionAwareCompressor(ContextCompressor):
    """
    질문 맥락을 고려한 압축기

    질문과 관련된 내용만 남기고 나머지는 제거하여 압축률을 높입니다.
    """

    COMPRESSION_PROMPT = """다음 문서를 질문과 관련된 핵심 정보만 남기고 50단어 이내로 압축하세요.
질문과 관련 없는 내용은 과감히 제거하세요.

질문: {question}

문서:
{document}

질문과 관련된 압축 내용 (50단어 이내):"""

    async def _compress_single(self, doc: dict, question: str) -> dict:
        """
        질문 기반 단일 문서 압축

        Args:
            doc: 문서 딕셔너리
            question: 사용자 질문

        Returns:
            압축 결과 딕셔너리
        """
        original_text = self._get_document_text(doc)
        original_tokens = self._estimate_tokens(original_text)

        try:
            config = types.GenerateContentConfig(
                max_output_tokens=self.MAX_TOKENS_PER_DOC,
                temperature=0.3,
            )

            response = await self.client.aio.models.generate_content(
                model=self.MODEL,
                contents=self.COMPRESSION_PROMPT.format(
                    question=question,
                    document=original_text
                ),
                config=config,
            )

            compressed_text = response.text.strip()
            compressed_tokens = self._estimate_tokens(compressed_text)

            return {
                'original_id': doc.get('id', self._generate_doc_id(doc)),
                'title': doc.get('title', ''),
                'compressed': compressed_text,
                'original_tokens': original_tokens,
                'compressed_tokens': compressed_tokens,
                'compression_ratio': compressed_tokens / max(original_tokens, 1)
            }

        except Exception as e:
            logger.error(f"Gemini API error during compression: {e}")
            raise


# 싱글톤 인스턴스 (선택적)
_compressor_instance = None


def get_context_compressor(question_aware: bool = False) -> ContextCompressor:
    """
    ContextCompressor 인스턴스 생성

    Args:
        question_aware: 질문 맥락 고려 여부

    Returns:
        ContextCompressor 또는 QuestionAwareCompressor
    """
    if question_aware:
        return QuestionAwareCompressor()
    else:
        return ContextCompressor()
