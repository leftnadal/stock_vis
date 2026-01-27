"""
GraphRAG Scorer 테스트

GraphRAGScorer의 통합 스코어링 기능을 검증합니다.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from rag_analysis.services.graphrag_scorer import (
    GraphRAGScorer,
    ScoringWeights,
    get_graphrag_scorer
)


class TestScoringWeights:
    """ScoringWeights 테스트"""

    def test_default_weights(self):
        """기본 가중치 검증"""
        weights = ScoringWeights()
        assert weights.rerank == 0.5
        assert weights.graph_rel == 0.3
        assert weights.recency == 0.2

    def test_custom_weights(self):
        """커스텀 가중치 설정"""
        weights = ScoringWeights(rerank=0.6, graph_rel=0.2, recency=0.2)
        assert weights.rerank == 0.6
        assert weights.graph_rel == 0.2
        assert weights.recency == 0.2

    def test_weight_normalization(self):
        """가중치 정규화 (합이 1.0이 아닐 때)"""
        weights = ScoringWeights(rerank=0.5, graph_rel=0.3, recency=0.1)
        # 합이 0.9이므로 정규화
        total = weights.rerank + weights.graph_rel + weights.recency
        assert abs(total - 1.0) < 0.01


class TestGraphRAGScorer:
    """GraphRAGScorer 테스트"""

    @pytest.fixture
    def mock_reranker(self):
        """Mock CrossEncoderReranker"""
        mock = MagicMock()
        mock.rerank.return_value = [
            ({'symbol': 'AAPL', 'date': '2024-01-15'}, 0.9, {'rerank': 0.9}),
            ({'symbol': 'NVDA', 'date': '2024-01-10'}, 0.7, {'rerank': 0.7}),
            ({'symbol': 'MSFT', 'date': '2023-12-20'}, 0.5, {'rerank': 0.5}),
        ]
        return mock

    @pytest.fixture
    def mock_neo4j_service(self):
        """Mock Neo4jServiceLite"""
        mock = MagicMock()
        mock.get_stock_relationships.return_value = {
            'symbol': 'AAPL',
            'supply_chain': [
                {'symbol': 'NVDA', 'strength': 0.8}
            ],
            'competitors': [
                {'symbol': 'MSFT', 'overlap_score': 0.7}
            ],
            'sector_peers': [],
            '_meta': {'source': 'neo4j', '_error': None}
        }
        return mock

    @pytest.fixture
    def scorer(self, mock_reranker, mock_neo4j_service):
        """GraphRAGScorer 인스턴스"""
        return GraphRAGScorer(
            reranker=mock_reranker,
            neo4j_service=mock_neo4j_service
        )

    @pytest.fixture
    def sample_documents(self):
        """샘플 문서"""
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        return [
            (
                {'symbol': 'AAPL', 'date': today, 'content': 'Apple 최신 실적...'},
                0.8,
                {}
            ),
            (
                {'symbol': 'NVDA', 'date': week_ago, 'content': 'NVIDIA GPU 성장...'},
                0.7,
                {}
            ),
            (
                {'symbol': 'MSFT', 'date': month_ago, 'content': 'Microsoft 클라우드...'},
                0.6,
                {}
            ),
        ]

    def test_initialization(self, scorer):
        """초기화 검증"""
        assert scorer is not None
        assert scorer.reranker is not None
        assert scorer.neo4j_service is not None
        assert scorer.weights.rerank == 0.5
        assert scorer.weights.graph_rel == 0.3
        assert scorer.weights.recency == 0.2

    def test_score_basic(self, scorer, sample_documents, mock_reranker):
        """기본 스코어링 동작"""
        result = scorer.score(
            question="AAPL 분석",
            documents=sample_documents,
            symbol="AAPL",
            top_k=3
        )

        # 결과 검증
        assert len(result) == 3
        assert result[0][1] > result[1][1] > result[2][1]  # 점수 내림차순

        # Breakdown 검증
        assert 'rerank_normalized' in result[0][2]
        assert 'graph_relation' in result[0][2]
        assert 'recency' in result[0][2]
        assert 'final_score' in result[0][2]

    def test_score_with_graph_disabled(self, scorer, sample_documents, mock_reranker):
        """Graph 점수 비활성화"""
        result = scorer.score(
            question="질문",
            documents=sample_documents,
            symbol="AAPL",
            top_k=3,
            use_graph=False
        )

        # Graph 점수가 모두 0.0이어야 함
        for _, _, breakdown in result:
            assert breakdown['graph_relation'] == 0.0

    def test_score_with_recency_disabled(self, scorer, sample_documents, mock_reranker):
        """최신성 점수 비활성화"""
        result = scorer.score(
            question="질문",
            documents=sample_documents,
            symbol="AAPL",
            top_k=3,
            use_recency=False
        )

        # Recency 점수가 모두 0.5 (중립)이어야 함
        for _, _, breakdown in result:
            assert breakdown['recency'] == 0.5

    def test_score_empty_documents(self, scorer):
        """빈 문서 리스트 처리"""
        result = scorer.score("질문", [], symbol="AAPL", top_k=3)
        assert result == []

    def test_calculate_graph_scores(self, scorer, mock_neo4j_service):
        """Graph 점수 계산"""
        documents = [
            ({'symbol': 'AAPL'}, 0.8, {}),  # 동일 심볼: 1.0
            ({'symbol': 'NVDA'}, 0.7, {}),  # Supply chain: 0.8
            ({'symbol': 'MSFT'}, 0.6, {}),  # Competitor: 0.7 * 0.8 = 0.56
            ({'symbol': 'TSLA'}, 0.5, {}),  # 무관계: 0.0
        ]

        graph_scores = scorer._calculate_graph_scores('AAPL', documents)

        # 점수 검증
        assert graph_scores['0'] == 1.0  # AAPL (동일)
        assert graph_scores['1'] == 0.8  # NVDA (supply chain)
        assert graph_scores['2'] == pytest.approx(0.56, abs=0.01)  # MSFT (competitor)
        assert graph_scores['3'] == 0.0  # TSLA (무관계)

    def test_calculate_graph_scores_neo4j_unavailable(self, scorer, mock_neo4j_service):
        """Neo4j 비활성화 시 Graph 점수"""
        mock_neo4j_service.get_stock_relationships.return_value = {
            'symbol': 'AAPL',
            '_meta': {'source': 'fallback', '_error': 'neo4j_unavailable'}
        }

        documents = [({'symbol': 'AAPL'}, 0.8, {})]
        graph_scores = scorer._calculate_graph_scores('AAPL', documents)

        assert graph_scores == {}  # 빈 딕셔너리

    def test_calculate_recency_scores(self, scorer):
        """최신성 점수 계산"""
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        quarter_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        two_years_ago = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

        documents = [
            ({'date': today}, 0.8, {}),
            ({'date': week_ago}, 0.7, {}),
            ({'date': month_ago}, 0.6, {}),
            ({'date': quarter_ago}, 0.5, {}),
            ({'date': year_ago}, 0.4, {}),
            ({'date': two_years_ago}, 0.3, {}),
            ({}, 0.2, {}),  # 날짜 없음
        ]

        recency_scores = scorer._calculate_recency_scores(documents)

        # 점수 검증
        assert recency_scores['0'] == 1.0  # 오늘
        assert recency_scores['1'] == 0.9  # 1주일 이내
        assert recency_scores['2'] == 0.7  # 1개월 이내
        assert recency_scores['3'] == 0.5  # 3개월 이내
        assert recency_scores['4'] == 0.3  # 1년 이내
        assert recency_scores['5'] == 0.1  # 1년 이상
        assert recency_scores['6'] == 0.5  # 날짜 없음 (중립)

    def test_calculate_recency_scores_invalid_date(self, scorer):
        """잘못된 날짜 형식 처리"""
        documents = [
            ({'date': 'invalid-date'}, 0.8, {}),
            ({'date': '2024-13-99'}, 0.7, {}),  # 잘못된 월/일
        ]

        recency_scores = scorer._calculate_recency_scores(documents)

        # 파싱 실패 시 중립 점수
        assert recency_scores['0'] == 0.5
        assert recency_scores['1'] == 0.5

    def test_integrate_scores(self, scorer, mock_reranker):
        """점수 통합 로직"""
        reranked = [
            ({'symbol': 'AAPL'}, 0.9, {}),
            ({'symbol': 'NVDA'}, 0.5, {}),
        ]

        graph_scores = {'0': 1.0, '1': 0.5}
        recency_scores = {'0': 1.0, '1': 0.7}

        result = scorer._integrate_scores(reranked, graph_scores, recency_scores, top_k=2)

        # AAPL이 최고 점수 (rerank + graph + recency 모두 높음)
        assert len(result) == 2
        assert result[0][0]['symbol'] == 'AAPL'
        assert result[0][2]['final_score'] > result[1][2]['final_score']

    def test_integrate_scores_normalization(self, scorer):
        """Rerank 점수 정규화 검증"""
        reranked = [
            ({'symbol': 'A'}, 10.0, {}),  # 큰 값
            ({'symbol': 'B'}, 5.0, {}),
            ({'symbol': 'C'}, 0.0, {}),
        ]

        result = scorer._integrate_scores(reranked, {}, {}, top_k=3)

        # 정규화된 rerank 점수 검증 (0~1 범위)
        assert 0.0 <= result[0][2]['rerank_normalized'] <= 1.0
        assert result[0][2]['rerank_normalized'] == 1.0  # 최대값
        assert result[2][2]['rerank_normalized'] == 0.0  # 최소값

    def test_integrate_scores_missing_graph_recency(self, scorer):
        """Graph/Recency 점수 누락 시 기본값 사용"""
        reranked = [({'symbol': 'AAPL'}, 0.9, {})]

        # Graph/Recency 점수 없음
        result = scorer._integrate_scores(reranked, {}, {}, top_k=1)

        # 기본값 확인
        assert result[0][2]['graph_relation'] == 0.0  # 기본값
        assert result[0][2]['recency'] == 0.5  # 기본값 (중립)


class TestGetGraphRAGScorer:
    """get_graphrag_scorer 헬퍼 함수 테스트"""

    @patch('rag_analysis.services.graphrag_scorer.CrossEncoderReranker')
    @patch('rag_analysis.services.graphrag_scorer.get_neo4j_service')
    def test_get_scorer_default(self, mock_neo4j, mock_reranker):
        """기본 scorer 생성"""
        scorer = get_graphrag_scorer()

        assert isinstance(scorer, GraphRAGScorer)
        assert scorer.weights.rerank == 0.5
        assert scorer.weights.graph_rel == 0.3
        assert scorer.weights.recency == 0.2

    @patch('rag_analysis.services.graphrag_scorer.CrossEncoderReranker')
    @patch('rag_analysis.services.graphrag_scorer.get_neo4j_service')
    def test_get_scorer_custom_weights(self, mock_neo4j, mock_reranker):
        """커스텀 가중치로 scorer 생성"""
        weights = ScoringWeights(rerank=0.6, graph_rel=0.2, recency=0.2)
        scorer = get_graphrag_scorer(weights=weights)

        assert scorer.weights.rerank == 0.6
        assert scorer.weights.graph_rel == 0.2
        assert scorer.weights.recency == 0.2


class TestGraphRAGScorerIntegration:
    """통합 시나리오 테스트"""

    @pytest.fixture
    def full_scorer(self):
        """실제 의존성을 사용하는 scorer (Mock 없음)"""
        # 실제 인스턴스 생성은 sentence-transformers 설치 필요
        # 여기서는 mock 사용
        mock_reranker = MagicMock()
        mock_neo4j = MagicMock()

        return GraphRAGScorer(
            reranker=mock_reranker,
            neo4j_service=mock_neo4j
        )

    def test_end_to_end_scoring(self, full_scorer):
        """End-to-End 스코어링 시나리오"""
        # Mock 설정
        full_scorer.reranker.rerank.return_value = [
            ({'symbol': 'AAPL', 'date': '2024-01-15'}, 0.9, {}),
            ({'symbol': 'NVDA', 'date': '2024-01-10'}, 0.7, {}),
        ]

        full_scorer.neo4j_service.get_stock_relationships.return_value = {
            'symbol': 'AAPL',
            'supply_chain': [{'symbol': 'NVDA', 'strength': 0.8}],
            'competitors': [],
            'sector_peers': [],
            '_meta': {'source': 'neo4j', '_error': None}
        }

        documents = [
            ({'symbol': 'AAPL', 'date': '2024-01-15'}, 0.8, {}),
            ({'symbol': 'NVDA', 'date': '2024-01-10'}, 0.7, {}),
        ]

        # 실행
        result = full_scorer.score(
            question="AAPL 공급망 분석",
            documents=documents,
            symbol="AAPL",
            top_k=2,
            use_graph=True,
            use_recency=True
        )

        # 검증
        assert len(result) == 2
        assert all('final_score' in breakdown for _, _, breakdown in result)
        assert all('weights' in breakdown for _, _, breakdown in result)
