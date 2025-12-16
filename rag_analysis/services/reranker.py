"""
Cross-Encoder Reranker

검색 결과를 Cross-Encoder로 재순위화하여 가장 관련성 높은 Top-K를 선별합니다.
"""

from sentence_transformers import CrossEncoder
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Cross-Encoder 기반 재순위화

    Features:
        - MS MARCO 사전학습 모델 사용
        - 질문-문서 쌍의 관련성 점수 계산
        - 싱글톤 패턴으로 모델 재사용

    Usage:
        >>> reranker = CrossEncoderReranker()
        >>> documents = [(doc1, 0.8, {}), (doc2, 0.7, {})]
        >>> reranked = reranker.rerank("질문", documents, top_k=3)
    """

    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    MAX_TEXT_LENGTH = 1000  # Cross-Encoder는 최대 512 토큰 제한

    _instance = None
    _model = None

    def __new__(cls):
        """싱글톤 패턴: 모델 인스턴스 재사용"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Cross-Encoder 모델 초기화

        Note:
            - 최초 호출 시 모델 다운로드 (약 80MB)
            - 이후 호출은 캐시된 모델 재사용
        """
        if CrossEncoderReranker._model is None:
            logger.info(f"Loading Cross-Encoder model: {self.MODEL_NAME}")
            CrossEncoderReranker._model = CrossEncoder(self.MODEL_NAME)
            logger.info("Cross-Encoder model loaded successfully")
        self.model = CrossEncoderReranker._model

    def rerank(
        self,
        question: str,
        documents: List[Tuple[dict, float, dict]],
        top_k: int = 3
    ) -> List[Tuple[dict, float, dict]]:
        """
        문서 재순위화

        Args:
            question: 사용자 질문
            documents: (document, score, breakdown) 튜플 리스트
            top_k: 반환할 상위 개수

        Returns:
            재순위화된 (document, rerank_score, breakdown) 튜플 리스트

        Example:
            >>> documents = [
            ...     ({'title': 'Doc1', 'content': '...'}, 0.8, {}),
            ...     ({'title': 'Doc2', 'content': '...'}, 0.7, {})
            ... ]
            >>> reranked = reranker.rerank("AAPL 재무 분석", documents, top_k=1)
        """
        if not documents:
            logger.warning("No documents to rerank")
            return []

        # Top-K보다 적으면 그대로 반환
        if len(documents) <= top_k:
            logger.debug(f"Documents ({len(documents)}) <= top_k ({top_k}), returning all")
            return documents

        # Cross-Encoder 입력 준비
        pairs = []
        for doc, _, _ in documents:
            doc_text = self._get_document_text(doc)
            pairs.append([question, doc_text])

        # 관련성 점수 계산
        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            logger.error(f"Cross-Encoder prediction error: {str(e)}", exc_info=True)
            # 에러 발생 시 원본 문서 반환
            return documents[:top_k]

        # 점수와 함께 재정렬
        scored_docs = []
        for i, (doc, orig_score, breakdown) in enumerate(documents):
            rerank_score = float(scores[i])
            # breakdown에 rerank 점수 추가
            breakdown_copy = breakdown.copy()
            breakdown_copy['rerank'] = rerank_score
            breakdown_copy['original_score'] = orig_score
            scored_docs.append((doc, rerank_score, breakdown_copy))

        # 점수 기준 내림차순 정렬
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            f"Reranked {len(documents)} docs → top_k={top_k}, "
            f"top score: {scored_docs[0][1]:.3f}, "
            f"bottom score: {scored_docs[-1][1]:.3f}"
        )

        return scored_docs[:top_k]

    def _get_document_text(self, doc: dict) -> str:
        """
        문서에서 텍스트 추출

        Args:
            doc: 문서 딕셔너리

        Returns:
            결합된 텍스트 (title + content/text)

        Note:
            Cross-Encoder는 최대 512 토큰 제한이 있으므로
            MAX_TEXT_LENGTH로 텍스트 길이 제한
        """
        # 제목 추출
        title = doc.get('title', doc.get('name', ''))

        # 본문 추출 (여러 필드 우선순위)
        content = (
            doc.get('content') or
            doc.get('text') or
            doc.get('description') or
            doc.get('summary') or
            ''
        )

        # 제목과 본문 결합
        if title and content:
            combined = f"{title}\n{content}"
        elif title:
            combined = title
        else:
            combined = content

        # 길이 제한
        if len(combined) > self.MAX_TEXT_LENGTH:
            combined = combined[:self.MAX_TEXT_LENGTH]

        return combined


class RerankerWithThreshold:
    """
    임계값 기반 필터링 추가 Reranker

    Features:
        - Cross-Encoder 재순위화
        - 최소 점수 임계값 필터링
        - 최소 문서 수 보장

    Usage:
        >>> base_reranker = CrossEncoderReranker()
        >>> reranker = RerankerWithThreshold(base_reranker, threshold=0.5)
        >>> results = reranker.rerank("질문", documents, top_k=3, min_docs=1)
    """

    def __init__(
        self,
        reranker: CrossEncoderReranker,
        threshold: float = 0.5
    ):
        """
        Args:
            reranker: Cross-Encoder 재순위화 인스턴스
            threshold: 최소 점수 임계값 (0.0 ~ 1.0)
        """
        self.reranker = reranker
        self.threshold = threshold

        if not 0.0 <= threshold <= 1.0:
            logger.warning(f"Threshold {threshold} out of range [0, 1], clamping")
            self.threshold = max(0.0, min(1.0, threshold))

    def rerank(
        self,
        question: str,
        documents: List[Tuple[dict, float, dict]],
        top_k: int = 3,
        min_docs: int = 1
    ) -> List[Tuple[dict, float, dict]]:
        """
        임계값 기반 재순위화

        Args:
            question: 사용자 질문
            documents: (document, score, breakdown) 튜플 리스트
            top_k: 반환할 최대 문서 수
            min_docs: 최소 보장 문서 수 (임계값 미달이어도 반환)

        Returns:
            필터링 및 재순위화된 문서 리스트

        Logic:
            1. Cross-Encoder로 재순위화
            2. 임계값 이상 문서 필터링
            3. 필터링 결과가 min_docs 미만이면 상위 min_docs개 반환
            4. Top-K 선택
        """
        # 1. Cross-Encoder 재순위화 (모든 문서에 대해)
        reranked = self.reranker.rerank(question, documents, top_k=len(documents))

        # 2. 임계값 필터링
        filtered = [
            (doc, score, breakdown)
            for doc, score, breakdown in reranked
            if score >= self.threshold
        ]

        logger.debug(
            f"Threshold filtering: {len(reranked)} docs → "
            f"{len(filtered)} docs above {self.threshold}"
        )

        # 3. 최소 문서 수 보장
        if len(filtered) < min_docs:
            logger.info(
                f"Filtered docs ({len(filtered)}) < min_docs ({min_docs}), "
                f"using top {min_docs} from reranked results"
            )
            filtered = reranked[:min_docs]

        # 4. Top-K 선택
        return filtered[:top_k]


def get_reranker(with_threshold: bool = False, threshold: float = 0.5) -> CrossEncoderReranker:
    """
    Reranker 인스턴스 생성 헬퍼

    Args:
        with_threshold: 임계값 필터링 사용 여부
        threshold: 임계값 (with_threshold=True일 때만 사용)

    Returns:
        CrossEncoderReranker 또는 RerankerWithThreshold 인스턴스

    Example:
        >>> # 기본 reranker
        >>> reranker = get_reranker()

        >>> # 임계값 필터링 포함
        >>> reranker = get_reranker(with_threshold=True, threshold=0.6)
    """
    base_reranker = CrossEncoderReranker()

    if with_threshold:
        return RerankerWithThreshold(base_reranker, threshold=threshold)

    return base_reranker
