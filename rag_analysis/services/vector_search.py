"""
Vector Search Service

sentence-transformers를 사용한 벡터 유사도 검색 서비스
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class VectorSearchService:
    """벡터 유사도 검색 서비스"""

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """싱글톤 패턴으로 모델 로딩"""
        if VectorSearchService._model is None:
            logger.info(f"Loading sentence-transformers model: {self.MODEL_NAME}")
            VectorSearchService._model = SentenceTransformer(self.MODEL_NAME)
            logger.info("Model loaded successfully")
        self.model = VectorSearchService._model

    def encode(self, text: str) -> np.ndarray:
        """
        단일 텍스트를 벡터로 인코딩

        Args:
            text: 인코딩할 텍스트

        Returns:
            numpy array 임베딩 벡터
        """
        if not text:
            logger.warning("Empty text provided for encoding")
            return np.zeros(384)  # all-MiniLM-L6-v2 차원

        return self.model.encode(text, convert_to_numpy=True)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        여러 텍스트를 배치로 인코딩

        Args:
            texts: 인코딩할 텍스트 리스트

        Returns:
            numpy array 임베딩 벡터들 (N x 384)
        """
        if not texts:
            logger.warning("Empty text list provided for batch encoding")
            return np.zeros((0, 384))

        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    def search(
        self,
        query: str,
        documents: List[dict],
        top_k: int = 20,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[dict, float]]:
        """
        벡터 유사도 검색

        Args:
            query: 검색 쿼리
            documents: 검색 대상 문서 리스트 (content 또는 text 필드 필요)
            top_k: 반환할 최대 문서 수
            score_threshold: 최소 유사도 임계값 (0~1)

        Returns:
            (문서, 유사도 점수) 튜플 리스트
        """
        if not documents:
            logger.warning("No documents provided for search")
            return []

        if not query:
            logger.warning("Empty query provided for search")
            return []

        try:
            # 쿼리 임베딩
            query_embedding = self.encode(query)

            # 문서 텍스트 추출
            doc_texts = []
            for d in documents:
                text = d.get('content', d.get('text', ''))
                if not text:
                    logger.debug(f"Empty text in document: {d.get('id', 'unknown')}")
                doc_texts.append(text)

            # 문서 임베딩
            doc_embeddings = self.encode_batch(doc_texts)

            # 코사인 유사도 계산
            # similarity = dot(A, B) / (norm(A) * norm(B))
            similarities = np.dot(doc_embeddings, query_embedding) / (
                np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_embedding) + 1e-9
            )

            # score_threshold 필터링
            if score_threshold is not None:
                valid_indices = np.where(similarities >= score_threshold)[0]
                similarities = similarities[valid_indices]
                documents = [documents[i] for i in valid_indices]

            # Top-K 추출
            if len(similarities) > top_k:
                top_indices = np.argsort(similarities)[::-1][:top_k]
            else:
                top_indices = np.argsort(similarities)[::-1]

            results = [(documents[idx], float(similarities[idx])) for idx in top_indices]

            logger.info(f"Vector search completed: {len(results)} results for query '{query[:50]}...'")
            return results

        except Exception as e:
            logger.error(f"Error during vector search: {str(e)}", exc_info=True)
            return []


def get_vector_search_service() -> VectorSearchService:
    """
    VectorSearchService 싱글톤 인스턴스 반환

    Returns:
        VectorSearchService 인스턴스
    """
    return VectorSearchService()
