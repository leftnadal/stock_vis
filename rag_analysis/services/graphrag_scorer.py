"""
GraphRAG Scorer

Cross-Encoder + Graph 관계 + 최신성 점수를 통합한 고급 스코어링 시스템
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from .reranker import CrossEncoderReranker
from .neo4j_service import Neo4jServiceLite, get_neo4j_service

logger = logging.getLogger(__name__)


@dataclass
class ScoringWeights:
    """스코어링 가중치"""
    rerank: float = 0.5      # Cross-Encoder 점수
    graph_rel: float = 0.3   # Graph 관계 점수
    recency: float = 0.2     # 최신성 점수

    def __post_init__(self):
        """가중치 합이 1.0인지 검증"""
        total = self.rerank + self.graph_rel + self.recency
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Scoring weights sum is {total}, not 1.0. Normalizing...")
            self.rerank /= total
            self.graph_rel /= total
            self.recency /= total


class GraphRAGScorer:
    """
    GraphRAG 통합 스코어러

    Features:
        - Cross-Encoder 재순위화 (의미 관련성)
        - Graph 관계 점수 (Neo4j 연결 강도)
        - 최신성 점수 (시간 가중치)
        - 가중 합산으로 최종 점수 계산

    Usage:
        >>> scorer = GraphRAGScorer()
        >>> scored = scorer.score(
        ...     question="AAPL 재무 분석",
        ...     documents=[(doc1, 0.8, {}), ...],
        ...     symbol="AAPL",
        ...     top_k=3
        ... )
    """

    def __init__(
        self,
        reranker: Optional[CrossEncoderReranker] = None,
        neo4j_service: Optional[Neo4jServiceLite] = None,
        weights: Optional[ScoringWeights] = None
    ):
        """
        Args:
            reranker: Cross-Encoder 재순위화 인스턴스 (None이면 새로 생성)
            neo4j_service: Neo4j 서비스 (None이면 싱글톤 사용)
            weights: 스코어링 가중치 (None이면 기본값)
        """
        self.reranker = reranker or CrossEncoderReranker()
        self.neo4j_service = neo4j_service or get_neo4j_service()
        self.weights = weights or ScoringWeights()

    def score(
        self,
        question: str,
        documents: List[Tuple[dict, float, dict]],
        symbol: Optional[str] = None,
        top_k: int = 3,
        use_graph: bool = True,
        use_recency: bool = True
    ) -> List[Tuple[dict, float, dict]]:
        """
        문서 통합 스코어링 및 재순위화

        Args:
            question: 사용자 질문
            documents: (document, score, breakdown) 튜플 리스트
            symbol: 기준 종목 심볼 (Graph 검색용, optional)
            top_k: 반환할 상위 개수
            use_graph: Graph 관계 점수 사용 여부
            use_recency: 최신성 점수 사용 여부

        Returns:
            최종 스코어링된 (document, final_score, breakdown) 튜플 리스트

        Example:
            >>> documents = [
            ...     ({'symbol': 'AAPL', 'date': '2024-01-15', 'content': '...'}, 0.8, {}),
            ...     ({'symbol': 'NVDA', 'date': '2024-01-10', 'content': '...'}, 0.7, {})
            ... ]
            >>> scored = scorer.score("AAPL 공급망 분석", documents, symbol="AAPL", top_k=1)
        """
        if not documents:
            logger.warning("No documents to score")
            return []

        # 1. Cross-Encoder 재순위화
        reranked = self.reranker.rerank(question, documents, top_k=len(documents))

        # 2. Graph 관계 점수 계산
        graph_scores = {}
        if use_graph and symbol:
            graph_scores = self._calculate_graph_scores(symbol, reranked)

        # 3. 최신성 점수 계산
        recency_scores = {}
        if use_recency:
            recency_scores = self._calculate_recency_scores(reranked)

        # 4. 점수 통합
        final_results = self._integrate_scores(
            reranked,
            graph_scores,
            recency_scores,
            top_k=top_k
        )

        logger.info(
            f"GraphRAG scoring completed: {len(final_results)} results, "
            f"top score: {final_results[0][1]:.3f}"
        )

        return final_results

    def _calculate_graph_scores(
        self,
        symbol: str,
        documents: List[Tuple[dict, float, dict]]
    ) -> Dict[str, float]:
        """
        Graph 관계 기반 점수 계산

        Args:
            symbol: 기준 종목 심볼
            documents: 문서 리스트

        Returns:
            {doc_index: graph_score} (0.0 ~ 1.0)

        Logic:
            - 동일 심볼: 1.0
            - Supply chain 관계: strength 값 (0.5 ~ 1.0)
            - Competitor 관계: overlap_score * 0.8
            - Sector peer 관계: 0.6
            - 무관계: 0.0
        """
        try:
            # Neo4j에서 관계 정보 조회
            relationships = self.neo4j_service.get_stock_relationships(symbol)

            if relationships['_meta']['source'] == 'fallback':
                logger.debug(f"Graph scoring unavailable for {symbol}")
                return {}

            # 관련 종목 심볼과 점수 매핑 구축
            related_scores = {}

            # Supply chain 관계
            for supply in relationships.get('supply_chain', []):
                related_symbol = supply['symbol'].upper()
                strength = supply.get('strength', 0.5)
                related_scores[related_symbol] = strength

            # Competitor 관계
            for comp in relationships.get('competitors', []):
                comp_symbol = comp['symbol'].upper()
                overlap = comp.get('overlap_score', 0.7)
                related_scores[comp_symbol] = overlap * 0.8  # 경쟁사는 약간 낮은 가중치

            # Sector peer 관계
            for peer in relationships.get('sector_peers', []):
                peer_symbol = peer['symbol'].upper()
                if peer_symbol not in related_scores:  # 중복 방지
                    related_scores[peer_symbol] = 0.6

            # 문서별 Graph 점수 계산
            graph_scores = {}
            for idx, (doc, _, _) in enumerate(documents):
                doc_symbol = doc.get('symbol', '').upper()

                if doc_symbol == symbol.upper():
                    # 동일 심볼: 최고 점수
                    graph_scores[str(idx)] = 1.0
                elif doc_symbol in related_scores:
                    # 관계 있는 심볼: 관계 강도 점수
                    graph_scores[str(idx)] = related_scores[doc_symbol]
                else:
                    # 무관계: 0점
                    graph_scores[str(idx)] = 0.0

            logger.debug(f"Graph scores calculated for {len(graph_scores)} documents")
            return graph_scores

        except Exception as e:
            logger.error(f"Graph scoring error: {str(e)}", exc_info=True)
            return {}

    def _calculate_recency_scores(
        self,
        documents: List[Tuple[dict, float, dict]]
    ) -> Dict[str, float]:
        """
        최신성 점수 계산

        Args:
            documents: 문서 리스트

        Returns:
            {doc_index: recency_score} (0.0 ~ 1.0)

        Logic:
            - 오늘: 1.0
            - 1주일 이내: 0.9
            - 1개월 이내: 0.7
            - 3개월 이내: 0.5
            - 1년 이내: 0.3
            - 1년 이상: 0.1
            - 날짜 없음: 0.5 (중립)
        """
        now = datetime.now()
        recency_scores = {}

        for idx, (doc, _, _) in enumerate(documents):
            # 날짜 추출 (여러 필드 시도)
            date_str = (
                doc.get('date') or
                doc.get('created_at') or
                doc.get('updated_at') or
                doc.get('fiscal_date_ending') or
                None
            )

            if not date_str:
                # 날짜 정보 없음: 중립 점수
                recency_scores[str(idx)] = 0.5
                continue

            try:
                # 날짜 파싱 (ISO 형식 가정: YYYY-MM-DD)
                doc_date = datetime.fromisoformat(date_str.split('T')[0])
                days_diff = (now - doc_date).days

                # 최신성 점수 계산
                if days_diff <= 0:
                    score = 1.0  # 오늘/미래
                elif days_diff <= 7:
                    score = 0.9  # 1주일 이내
                elif days_diff <= 30:
                    score = 0.7  # 1개월 이내
                elif days_diff <= 90:
                    score = 0.5  # 3개월 이내
                elif days_diff <= 365:
                    score = 0.3  # 1년 이내
                else:
                    score = 0.1  # 1년 이상

                recency_scores[str(idx)] = score

            except (ValueError, AttributeError) as e:
                logger.debug(f"Date parsing error for '{date_str}': {e}")
                recency_scores[str(idx)] = 0.5  # 파싱 실패: 중립

        logger.debug(f"Recency scores calculated for {len(recency_scores)} documents")
        return recency_scores

    def _integrate_scores(
        self,
        reranked: List[Tuple[dict, float, dict]],
        graph_scores: Dict[str, float],
        recency_scores: Dict[str, float],
        top_k: int
    ) -> List[Tuple[dict, float, dict]]:
        """
        점수 통합 및 최종 순위 결정

        Args:
            reranked: Cross-Encoder 재순위화 결과
            graph_scores: Graph 관계 점수
            recency_scores: 최신성 점수
            top_k: 반환할 최대 문서 수

        Returns:
            최종 스코어링된 문서 리스트
        """
        # Rerank 점수 정규화 (0~1 범위로)
        rerank_values = [score for _, score, _ in reranked]
        min_rerank = min(rerank_values) if rerank_values else 0.0
        max_rerank = max(rerank_values) if rerank_values else 1.0
        range_rerank = max_rerank - min_rerank if max_rerank != min_rerank else 1.0

        final_results = []

        for idx, (doc, rerank_score, breakdown) in enumerate(reranked):
            # 1. Rerank 점수 정규화
            norm_rerank = (rerank_score - min_rerank) / range_rerank

            # 2. Graph 점수 가져오기 (없으면 0.0)
            graph_score = graph_scores.get(str(idx), 0.0)

            # 3. Recency 점수 가져오기 (없으면 0.5)
            recency_score = recency_scores.get(str(idx), 0.5)

            # 4. 가중 합산
            final_score = (
                self.weights.rerank * norm_rerank +
                self.weights.graph_rel * graph_score +
                self.weights.recency * recency_score
            )

            # 5. Breakdown 업데이트
            breakdown_copy = breakdown.copy()
            breakdown_copy.update({
                'rerank_normalized': norm_rerank,
                'graph_relation': graph_score,
                'recency': recency_score,
                'final_score': final_score,
                'weights': {
                    'rerank': self.weights.rerank,
                    'graph_rel': self.weights.graph_rel,
                    'recency': self.weights.recency
                }
            })

            final_results.append((doc, final_score, breakdown_copy))

        # 최종 점수 기준 정렬
        final_results.sort(key=lambda x: x[1], reverse=True)

        return final_results[:top_k]


def get_graphrag_scorer(
    weights: Optional[ScoringWeights] = None
) -> GraphRAGScorer:
    """
    GraphRAGScorer 인스턴스 생성 헬퍼

    Args:
        weights: 스코어링 가중치 (None이면 기본값)

    Returns:
        GraphRAGScorer 인스턴스

    Example:
        >>> # 기본 가중치
        >>> scorer = get_graphrag_scorer()

        >>> # 커스텀 가중치
        >>> weights = ScoringWeights(rerank=0.6, graph_rel=0.2, recency=0.2)
        >>> scorer = get_graphrag_scorer(weights=weights)
    """
    return GraphRAGScorer(weights=weights)
