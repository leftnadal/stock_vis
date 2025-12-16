"""
Reranker 테스트

CrossEncoderReranker와 RerankerWithThreshold의 기능을 검증합니다.
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from rag_analysis.services.reranker import (
    CrossEncoderReranker,
    RerankerWithThreshold,
    get_reranker
)


class TestCrossEncoderReranker:
    """CrossEncoderReranker 테스트"""

    @pytest.fixture
    def mock_cross_encoder(self):
        """Mock Cross-Encoder 모델"""
        with patch('rag_analysis.services.reranker.CrossEncoder') as mock:
            mock_model = MagicMock()
            mock.return_value = mock_model
            yield mock_model

    @pytest.fixture
    def reranker(self, mock_cross_encoder):
        """CrossEncoderReranker 인스턴스"""
        # 싱글톤 초기화 리셋
        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None
        return CrossEncoderReranker()

    @pytest.fixture
    def sample_documents(self):
        """샘플 문서 데이터"""
        return [
            (
                {'title': 'AAPL Q4 실적', 'content': 'Apple 4분기 실적 발표...', 'symbol': 'AAPL'},
                0.85,
                {'vector': 0.8, 'bm25': 0.9}
            ),
            (
                {'title': 'MSFT 클라우드', 'content': 'Microsoft Azure 성장...', 'symbol': 'MSFT'},
                0.75,
                {'vector': 0.7, 'bm25': 0.8}
            ),
            (
                {'title': 'NVDA GPU', 'content': 'NVIDIA AI 칩 수요...', 'symbol': 'NVDA'},
                0.65,
                {'vector': 0.6, 'bm25': 0.7}
            ),
        ]

    def test_initialization(self, reranker):
        """모델 초기화 검증"""
        assert reranker is not None
        assert reranker.model is not None
        assert reranker.MODEL_NAME == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def test_singleton_pattern(self, mock_cross_encoder):
        """싱글톤 패턴 동작 검증"""
        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

        reranker1 = CrossEncoderReranker()
        reranker2 = CrossEncoderReranker()

        assert reranker1 is reranker2
        assert reranker1.model is reranker2.model

    def test_rerank_basic(self, reranker, sample_documents, mock_cross_encoder):
        """기본 재순위화 동작"""
        # Mock 점수 설정 (NVDA > AAPL > MSFT 순서로)
        mock_scores = np.array([0.6, 0.4, 0.9])
        reranker.model.predict = MagicMock(return_value=mock_scores)

        # 실행
        result = reranker.rerank("NVDA AI 칩 분석", sample_documents, top_k=2)

        # 검증
        assert len(result) == 2
        assert result[0][0]['symbol'] == 'NVDA'  # 가장 높은 점수
        assert result[0][1] == 0.9
        assert result[1][0]['symbol'] == 'AAPL'  # 두 번째 점수
        assert result[1][1] == 0.6

    def test_rerank_with_breakdown_update(self, reranker, sample_documents, mock_cross_encoder):
        """breakdown에 rerank 점수 추가 검증"""
        mock_scores = np.array([0.8, 0.7, 0.6])
        reranker.model.predict = MagicMock(return_value=mock_scores)

        # top_k=2로 설정하여 rerank가 실행되도록 함 (문서 3개 > top_k 2)
        result = reranker.rerank("질문", sample_documents, top_k=2)

        # breakdown에 rerank 점수 포함 확인
        # 정렬 후 순서: 0번(0.8) > 1번(0.7) > 2번(0.6)
        assert 'rerank' in result[0][2]
        assert 'original_score' in result[0][2]
        assert 'vector' in result[0][2]  # 기존 breakdown 유지
        assert 'bm25' in result[0][2]
        # 첫 번째 문서는 원래 0.85 점수였고, rerank 후 0.8 점수
        assert result[0][2]['rerank'] == 0.8

    def test_rerank_empty_documents(self, reranker):
        """빈 문서 리스트 처리"""
        result = reranker.rerank("질문", [], top_k=3)
        assert result == []

    def test_rerank_less_than_topk(self, reranker, mock_cross_encoder):
        """문서 수가 top_k보다 적을 때"""
        docs = [
            ({'title': 'Doc1', 'content': 'Content1'}, 0.8, {}),
        ]

        result = reranker.rerank("질문", docs, top_k=3)
        assert result == docs  # 그대로 반환

    def test_rerank_prediction_error(self, reranker, sample_documents, mock_cross_encoder):
        """Cross-Encoder 예측 에러 처리"""
        reranker.model.predict = MagicMock(side_effect=Exception("Model error"))

        result = reranker.rerank("질문", sample_documents, top_k=2)

        # 에러 발생 시 원본 문서의 top_k 반환
        assert len(result) == 2
        assert result == sample_documents[:2]

    def test_get_document_text(self, reranker):
        """문서 텍스트 추출 로직"""
        # 제목 + 본문
        doc1 = {'title': 'Title', 'content': 'Content' * 100}
        text1 = reranker._get_document_text(doc1)
        assert 'Title' in text1
        assert 'Content' in text1
        assert len(text1) <= reranker.MAX_TEXT_LENGTH

        # 제목만
        doc2 = {'title': 'Only Title'}
        text2 = reranker._get_document_text(doc2)
        assert text2 == 'Only Title'

        # 본문만 (여러 필드 우선순위)
        doc3 = {'text': 'Text field', 'description': 'Description field'}
        text3 = reranker._get_document_text(doc3)
        assert text3 == 'Text field'  # text가 우선순위

        # 빈 문서
        doc4 = {}
        text4 = reranker._get_document_text(doc4)
        assert text4 == ''


class TestRerankerWithThreshold:
    """RerankerWithThreshold 테스트"""

    @pytest.fixture
    def mock_base_reranker(self):
        """Mock CrossEncoderReranker"""
        mock = MagicMock(spec=CrossEncoderReranker)
        return mock

    @pytest.fixture
    def threshold_reranker(self, mock_base_reranker):
        """RerankerWithThreshold 인스턴스"""
        return RerankerWithThreshold(mock_base_reranker, threshold=0.5)

    @pytest.fixture
    def sample_reranked_docs(self):
        """재순위화된 샘플 문서"""
        return [
            ({'symbol': 'AAPL'}, 0.9, {'rerank': 0.9}),
            ({'symbol': 'MSFT'}, 0.6, {'rerank': 0.6}),
            ({'symbol': 'NVDA'}, 0.4, {'rerank': 0.4}),  # 임계값 미달
            ({'symbol': 'TSLA'}, 0.3, {'rerank': 0.3}),  # 임계값 미달
        ]

    def test_threshold_filtering(self, threshold_reranker, mock_base_reranker, sample_reranked_docs):
        """임계값 필터링 동작"""
        mock_base_reranker.rerank.return_value = sample_reranked_docs

        result = threshold_reranker.rerank("질문", [], top_k=3, min_docs=1)

        # 0.5 이상만 선택
        assert len(result) == 2
        assert result[0][0]['symbol'] == 'AAPL'
        assert result[1][0]['symbol'] == 'MSFT'

    def test_min_docs_guarantee(self, threshold_reranker, mock_base_reranker, sample_reranked_docs):
        """최소 문서 수 보장"""
        mock_base_reranker.rerank.return_value = sample_reranked_docs

        # threshold=0.5인데 min_docs=3 요청
        result = threshold_reranker.rerank("질문", [], top_k=5, min_docs=3)

        # 임계값 미달이어도 상위 3개 반환
        assert len(result) == 3

    def test_top_k_selection(self, threshold_reranker, mock_base_reranker, sample_reranked_docs):
        """Top-K 선택"""
        mock_base_reranker.rerank.return_value = sample_reranked_docs

        result = threshold_reranker.rerank("질문", [], top_k=1, min_docs=1)

        # 필터링 후 상위 1개만
        assert len(result) == 1
        assert result[0][0]['symbol'] == 'AAPL'

    def test_threshold_clamping(self):
        """임계값 범위 제한"""
        mock_reranker = MagicMock()

        # 범위 초과
        reranker1 = RerankerWithThreshold(mock_reranker, threshold=1.5)
        assert reranker1.threshold == 1.0

        # 범위 미만
        reranker2 = RerankerWithThreshold(mock_reranker, threshold=-0.5)
        assert reranker2.threshold == 0.0


class TestGetReranker:
    """get_reranker 헬퍼 함수 테스트"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """각 테스트 전 싱글톤 초기화"""
        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

    @patch('rag_analysis.services.reranker.CrossEncoder')
    def test_get_basic_reranker(self, mock_cross_encoder):
        """기본 reranker 생성"""
        reranker = get_reranker(with_threshold=False)

        assert isinstance(reranker, CrossEncoderReranker)
        assert not isinstance(reranker, RerankerWithThreshold)

    @patch('rag_analysis.services.reranker.CrossEncoder')
    def test_get_threshold_reranker(self, mock_cross_encoder):
        """임계값 reranker 생성"""
        reranker = get_reranker(with_threshold=True, threshold=0.6)

        assert isinstance(reranker, RerankerWithThreshold)
        assert reranker.threshold == 0.6
