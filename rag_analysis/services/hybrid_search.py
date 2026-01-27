"""
Hybrid Search Service

Vector + BM25 + Graph 검색을 결합한 하이브리드 검색 서비스
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from .vector_search import VectorSearchService, get_vector_search_service
from .bm25_search import BM25SearchService, get_bm25_search_service
from .neo4j_service import Neo4jServiceLite, get_neo4j_service

logger = logging.getLogger(__name__)


@dataclass
class SearchWeights:
    """검색 점수 가중치"""
    vector: float = 0.4
    bm25: float = 0.3
    graph: float = 0.3

    def __post_init__(self):
        """가중치 합이 1.0인지 검증"""
        total = self.vector + self.bm25 + self.graph
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Search weights sum is {total}, not 1.0. Normalizing...")
            self.vector /= total
            self.bm25 /= total
            self.graph /= total


class MetadataFilterBuilder:
    """
    메타데이터 기반 필터링 빌더

    Example:
        >>> filter_builder = MetadataFilterBuilder()
        >>> filter_builder.add_symbol("AAPL").add_date_range("2024-01-01", "2024-12-31")
        >>> filtered_docs = filter_builder.apply(documents)
    """

    def __init__(self):
        self._filters = []

    def add_symbol(self, symbol: str) -> 'MetadataFilterBuilder':
        """특정 심볼로 필터링"""
        self._filters.append(lambda doc: doc.get('symbol', '').upper() == symbol.upper())
        return self

    def add_symbols(self, symbols: List[str]) -> 'MetadataFilterBuilder':
        """여러 심볼로 필터링"""
        symbols_upper = [s.upper() for s in symbols]
        self._filters.append(lambda doc: doc.get('symbol', '').upper() in symbols_upper)
        return self

    def add_date_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> 'MetadataFilterBuilder':
        """날짜 범위로 필터링 (ISO 형식: YYYY-MM-DD)"""
        def date_filter(doc):
            doc_date = doc.get('date', doc.get('created_at', ''))
            if not doc_date:
                return False
            if start_date and doc_date < start_date:
                return False
            if end_date and doc_date > end_date:
                return False
            return True

        self._filters.append(date_filter)
        return self

    def add_document_type(self, doc_type: str) -> 'MetadataFilterBuilder':
        """문서 타입으로 필터링 (e.g., 'financial', 'news', 'analysis')"""
        self._filters.append(lambda doc: doc.get('type', '') == doc_type)
        return self

    def add_custom(self, filter_func) -> 'MetadataFilterBuilder':
        """커스텀 필터 함수 추가"""
        self._filters.append(filter_func)
        return self

    def apply(self, documents: List[dict]) -> List[dict]:
        """필터 적용"""
        if not self._filters:
            return documents

        filtered = documents
        for filter_func in self._filters:
            filtered = [doc for doc in filtered if filter_func(doc)]

        logger.debug(f"Filtered {len(documents)} -> {len(filtered)} documents")
        return filtered


class HybridSearchService:
    """
    하이브리드 검색 서비스

    Features:
        - Vector search (의미 기반)
        - BM25 search (키워드 기반)
        - Graph search (관계 기반)
        - 가중치 기반 점수 통합
        - 메타데이터 필터링
    """

    def __init__(
        self,
        vector_service: Optional[VectorSearchService] = None,
        bm25_service: Optional[BM25SearchService] = None,
        neo4j_service: Optional[Neo4jServiceLite] = None,
        weights: Optional[SearchWeights] = None
    ):
        """
        Args:
            vector_service: 벡터 검색 서비스 (None이면 싱글톤 사용)
            bm25_service: BM25 검색 서비스 (None이면 새 인스턴스)
            neo4j_service: Neo4j 그래프 서비스 (None이면 싱글톤 사용)
            weights: 검색 가중치 (None이면 기본값)
        """
        self.vector_service = vector_service or get_vector_search_service()
        self.bm25_service = bm25_service or get_bm25_search_service()
        self.neo4j_service = neo4j_service or get_neo4j_service()
        self.weights = weights or SearchWeights()

    def search(
        self,
        query: str,
        documents: List[dict],
        top_k: int = 10,
        symbol: Optional[str] = None,
        metadata_filter: Optional[MetadataFilterBuilder] = None,
        use_graph: bool = True
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 수행

        Args:
            query: 검색 쿼리
            documents: 검색 대상 문서 리스트
            top_k: 반환할 최대 문서 수
            symbol: 관련 종목 심볼 (Graph 검색용, optional)
            metadata_filter: 메타데이터 필터 빌더
            use_graph: Graph 검색 사용 여부

        Returns:
            [
                {
                    'document': {...},
                    'score': 0.85,
                    'scores': {'vector': 0.9, 'bm25': 0.8, 'graph': 0.85}
                },
                ...
            ]
        """
        if not documents:
            logger.warning("No documents provided for hybrid search")
            return []

        # 1. 메타데이터 필터링
        filtered_docs = documents
        if metadata_filter:
            filtered_docs = metadata_filter.apply(documents)
            if not filtered_docs:
                logger.info("No documents after metadata filtering")
                return []

        # 2. Vector Search
        vector_results = self._vector_search(query, filtered_docs, top_k=top_k * 2)

        # 3. BM25 Search
        bm25_results = self._bm25_search(query, filtered_docs, top_k=top_k * 2)

        # 4. Graph Search (optional)
        graph_boost = {}
        if use_graph and symbol:
            graph_boost = self._graph_search(symbol, filtered_docs)

        # 5. 점수 통합
        integrated_results = self._integrate_scores(
            vector_results,
            bm25_results,
            graph_boost,
            top_k=top_k
        )

        logger.info(f"Hybrid search completed: {len(integrated_results)} results for '{query[:50]}...'")
        return integrated_results

    def _vector_search(
        self,
        query: str,
        documents: List[dict],
        top_k: int
    ) -> Dict[str, float]:
        """
        벡터 검색 수행

        Returns:
            {document_id: score}
        """
        try:
            results = self.vector_service.search(query, documents, top_k=top_k)
            scores = {}
            for doc, score in results:
                doc_id = self._get_doc_id(doc)
                scores[doc_id] = score
            logger.debug(f"Vector search: {len(scores)} results")
            return scores
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}", exc_info=True)
            return {}

    def _bm25_search(
        self,
        query: str,
        documents: List[dict],
        top_k: int
    ) -> Dict[str, float]:
        """
        BM25 검색 수행

        Returns:
            {document_id: score}
        """
        try:
            results = self.bm25_service.search(query, documents, top_k=top_k)
            scores = {}
            for doc, score in results:
                doc_id = self._get_doc_id(doc)
                scores[doc_id] = score
            logger.debug(f"BM25 search: {len(scores)} results")
            return scores
        except Exception as e:
            logger.error(f"BM25 search error: {str(e)}", exc_info=True)
            return {}

    def _graph_search(
        self,
        symbol: str,
        documents: List[dict]
    ) -> Dict[str, float]:
        """
        그래프 관계 기반 부스팅

        Args:
            symbol: 기준 종목 심볼
            documents: 문서 리스트

        Returns:
            {document_id: boost_score}
        """
        try:
            # Neo4j에서 관계 정보 조회
            relationships = self.neo4j_service.get_stock_relationships(symbol)

            if relationships['_meta']['source'] == 'fallback':
                logger.debug(f"Graph search unavailable for {symbol}")
                return {}

            # 관련 종목 심볼 추출
            related_symbols = set()
            for supply in relationships.get('supply_chain', []):
                related_symbols.add(supply['symbol'])
            for comp in relationships.get('competitors', []):
                related_symbols.add(comp['symbol'])
            for peer in relationships.get('sector_peers', []):
                related_symbols.add(peer['symbol'])

            # 문서와 매칭하여 부스트 점수 부여
            boost_scores = {}
            for doc in documents:
                doc_symbol = doc.get('symbol', '').upper()
                if doc_symbol in related_symbols:
                    doc_id = self._get_doc_id(doc)
                    # 관계 강도에 따라 부스트 (0.5 ~ 1.0)
                    boost_scores[doc_id] = 0.8

            logger.debug(f"Graph search: {len(boost_scores)} boosted documents for {symbol}")
            return boost_scores

        except Exception as e:
            logger.error(f"Graph search error: {str(e)}", exc_info=True)
            return {}

    def _integrate_scores(
        self,
        vector_scores: Dict[str, float],
        bm25_scores: Dict[str, float],
        graph_boost: Dict[str, float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        점수 통합 및 정규화

        Args:
            vector_scores: {doc_id: vector_score}
            bm25_scores: {doc_id: bm25_score}
            graph_boost: {doc_id: graph_boost}
            top_k: 반환할 최대 문서 수

        Returns:
            정렬된 결과 리스트
        """
        # 모든 문서 ID 수집
        all_doc_ids = set(vector_scores.keys()) | set(bm25_scores.keys()) | set(graph_boost.keys())

        if not all_doc_ids:
            return []

        # 점수 정규화 (0~1 범위로)
        vector_norm = self._normalize_scores(vector_scores)
        bm25_norm = self._normalize_scores(bm25_scores)
        graph_norm = self._normalize_scores(graph_boost)

        # 가중 합산
        integrated_scores = []
        for doc_id in all_doc_ids:
            v_score = vector_norm.get(doc_id, 0.0)
            b_score = bm25_norm.get(doc_id, 0.0)
            g_score = graph_norm.get(doc_id, 0.0)

            final_score = (
                self.weights.vector * v_score +
                self.weights.bm25 * b_score +
                self.weights.graph * g_score
            )

            integrated_scores.append({
                'doc_id': doc_id,
                'score': final_score,
                'scores': {
                    'vector': v_score,
                    'bm25': b_score,
                    'graph': g_score
                }
            })

        # 점수 기준 정렬
        integrated_scores.sort(key=lambda x: x['score'], reverse=True)

        # Top-K 선택
        return integrated_scores[:top_k]

    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        점수를 0~1 범위로 정규화 (Min-Max Normalization)

        Args:
            scores: {doc_id: raw_score}

        Returns:
            {doc_id: normalized_score}
        """
        if not scores:
            return {}

        values = list(scores.values())
        min_val = min(values)
        max_val = max(values)

        # 모든 값이 같으면 1.0으로 설정
        if max_val == min_val:
            return {k: 1.0 for k in scores.keys()}

        # Min-Max 정규화
        normalized = {}
        for doc_id, score in scores.items():
            normalized[doc_id] = (score - min_val) / (max_val - min_val)

        return normalized

    def _get_doc_id(self, doc: dict) -> str:
        """
        문서 고유 ID 생성

        Args:
            doc: 문서 딕셔너리

        Returns:
            문서 ID (예: 'AAPL_2024-01-15_balance_sheet')
        """
        # 우선순위: id > symbol+date+type > hash
        if 'id' in doc:
            return str(doc['id'])

        parts = []
        if 'symbol' in doc:
            parts.append(doc['symbol'].upper())
        if 'date' in doc or 'created_at' in doc:
            parts.append(doc.get('date', doc.get('created_at', '')))
        if 'type' in doc:
            parts.append(doc['type'])

        if parts:
            return '_'.join(parts)

        # Fallback: 문서 해시
        return str(hash(str(doc)))


def get_hybrid_search_service(
    weights: Optional[SearchWeights] = None
) -> HybridSearchService:
    """
    HybridSearchService 인스턴스 생성

    Args:
        weights: 검색 가중치 (None이면 기본값)

    Returns:
        HybridSearchService 인스턴스
    """
    return HybridSearchService(weights=weights)
