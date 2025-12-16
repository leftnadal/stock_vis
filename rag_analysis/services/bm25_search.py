"""
BM25 Search Service

rank_bm25를 사용한 키워드 기반 검색 서비스
"""

from rank_bm25 import BM25Okapi
from typing import List, Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)


class BM25SearchService:
    """BM25 키워드 검색 서비스"""

    def __init__(self):
        """BM25 인덱스 초기화"""
        self._index: Optional[BM25Okapi] = None
        self._documents: Optional[List[dict]] = None

    def _tokenize(self, text: str) -> List[str]:
        """
        텍스트 토큰화 (한글/영문/숫자 추출)

        Args:
            text: 토큰화할 텍스트

        Returns:
            토큰 리스트
        """
        if not text:
            return []

        # 한글, 영문, 숫자를 각각 추출
        # [가-힣]+: 한글 연속
        # [a-zA-Z]+: 영문 연속
        # [0-9]+: 숫자 연속
        tokens = re.findall(r'[가-힣]+|[a-zA-Z]+|[0-9]+', text.lower())
        return tokens

    def build_index(self, documents: List[dict]) -> None:
        """
        BM25 인덱스 구축

        Args:
            documents: 인덱싱할 문서 리스트
        """
        if not documents:
            logger.warning("No documents provided for indexing")
            self._index = None
            self._documents = None
            return

        try:
            self._documents = documents
            tokenized_docs = []

            for doc in documents:
                # 제목과 내용을 결합하여 토큰화
                text = doc.get('content', doc.get('text', ''))
                title = doc.get('title', '')
                combined = f"{title} {text}"
                tokens = self._tokenize(combined)
                tokenized_docs.append(tokens)

            # BM25 인덱스 생성
            self._index = BM25Okapi(tokenized_docs)
            logger.info(f"BM25 index built with {len(documents)} documents")

        except Exception as e:
            logger.error(f"Error building BM25 index: {str(e)}", exc_info=True)
            self._index = None
            self._documents = None

    def search(
        self,
        query: str,
        documents: Optional[List[dict]] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[dict, float]]:
        """
        BM25 검색 수행

        Args:
            query: 검색 쿼리
            documents: 검색 대상 문서 (None이면 기존 인덱스 사용)
            top_k: 반환할 최대 문서 수
            score_threshold: 최소 점수 임계값

        Returns:
            (문서, BM25 점수) 튜플 리스트
        """
        # 새 문서가 제공되면 인덱스 재구축
        if documents is not None:
            self.build_index(documents)

        # 인덱스가 없으면 빈 결과 반환
        if not self._index or not self._documents:
            logger.warning("No BM25 index available for search")
            return []

        if not query:
            logger.warning("Empty query provided for BM25 search")
            return []

        try:
            # 쿼리 토큰화
            query_tokens = self._tokenize(query)
            if not query_tokens:
                logger.warning(f"No tokens extracted from query: '{query}'")
                return []

            # BM25 점수 계산
            scores = self._index.get_scores(query_tokens)

            # score_threshold 필터링
            if score_threshold is not None:
                valid_indices = [i for i in range(len(scores)) if scores[i] >= score_threshold]
            else:
                # 점수가 0보다 큰 문서만 필터링
                valid_indices = [i for i in range(len(scores)) if scores[i] > 0]

            if not valid_indices:
                logger.info(f"No documents matched query: '{query}'")
                return []

            # 점수 기준 정렬
            sorted_indices = sorted(
                valid_indices,
                key=lambda i: scores[i],
                reverse=True
            )[:top_k]

            results = [
                (self._documents[idx], float(scores[idx]))
                for idx in sorted_indices
            ]

            logger.info(f"BM25 search completed: {len(results)} results for query '{query[:50]}...'")
            return results

        except Exception as e:
            logger.error(f"Error during BM25 search: {str(e)}", exc_info=True)
            return []

    def get_top_tokens(self, text: str, top_n: int = 10) -> List[str]:
        """
        텍스트에서 중요한 토큰 추출 (디버깅/분석용)

        Args:
            text: 분석할 텍스트
            top_n: 반환할 토큰 수

        Returns:
            중요 토큰 리스트
        """
        tokens = self._tokenize(text)
        # 빈도수 기반 정렬
        from collections import Counter
        token_counts = Counter(tokens)
        return [token for token, _ in token_counts.most_common(top_n)]


def get_bm25_search_service() -> BM25SearchService:
    """
    BM25SearchService 인스턴스 생성

    Returns:
        BM25SearchService 인스턴스
    """
    return BM25SearchService()
