"""
Tests for Neo4jChainSightService

Neo4j Chain Sight 온톨로지 서비스 테스트.
Neo4j 연결이 없어도 fallback 로직이 동작하는지 확인.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService


class TestNeo4jChainSightServiceBasic:
    """기본 기능 테스트 (Neo4j Mock 사용)"""

    def test_is_available_when_driver_is_none(self):
        """드라이버가 None일 때 is_available() False 반환"""
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=None):
            service = Neo4jChainSightService()
            assert service.is_available() is False

    def test_is_available_when_driver_exists(self):
        """드라이버가 있을 때 is_available() True 반환"""
        mock_driver = Mock()
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=mock_driver):
            service = Neo4jChainSightService()
            assert service.is_available() is True

    def test_create_stock_node_when_unavailable(self):
        """Neo4j 불가 시 create_stock_node() False 반환"""
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=None):
            service = Neo4jChainSightService()
            result = service.create_stock_node('NVDA', 'NVIDIA', 'Technology', 'Semiconductors', 1e12)
            assert result is False

    def test_create_relationship_when_unavailable(self):
        """Neo4j 불가 시 create_relationship() False 반환"""
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=None):
            service = Neo4jChainSightService()
            result = service.create_relationship('NVDA', 'AMD', 'PEER_OF', 0.85, 'fmp')
            assert result is False

    def test_create_relationship_invalid_type(self):
        """잘못된 관계 타입에서 False 반환"""
        mock_driver = Mock()
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=mock_driver):
            service = Neo4jChainSightService()
            result = service.create_relationship('NVDA', 'AMD', 'INVALID_TYPE', 0.85, 'fmp')
            assert result is False

    def test_get_related_stocks_when_unavailable(self):
        """Neo4j 불가 시 get_related_stocks() 빈 리스트 반환"""
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=None):
            service = Neo4jChainSightService()
            result = service.get_related_stocks('NVDA')
            assert result == []

    def test_get_n_depth_graph_when_unavailable(self):
        """Neo4j 불가 시 get_n_depth_graph() 빈 그래프 반환"""
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=None):
            service = Neo4jChainSightService()
            result = service.get_n_depth_graph('NVDA', depth=2)
            assert result == {"nodes": [], "edges": []}

    def test_get_statistics_when_unavailable(self):
        """Neo4j 불가 시 get_statistics() 빈 딕셔너리 반환"""
        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=None):
            service = Neo4jChainSightService()
            result = service.get_statistics()
            assert result == {}


class TestNeo4jChainSightServiceWithMockDriver:
    """Mock Driver를 사용한 테스트"""

    @pytest.fixture
    def mock_service(self):
        """Mock Neo4j driver가 있는 서비스"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = Mock(return_value=False)

        with patch('serverless.services.neo4j_chain_sight_service.get_neo4j_driver', return_value=mock_driver):
            service = Neo4jChainSightService()
            service._mock_session = mock_session
            yield service

    def test_create_stock_node_success(self, mock_service):
        """Stock 노드 생성 성공"""
        mock_result = Mock()
        mock_result.single.return_value = {'symbol': 'NVDA'}
        mock_service._mock_session.run.return_value = mock_result

        result = mock_service.create_stock_node('NVDA', 'NVIDIA', 'Technology', 'Semiconductors', 1e12)
        assert result is True

        # Cypher 쿼리 호출 확인
        mock_service._mock_session.run.assert_called_once()
        call_args = mock_service._mock_session.run.call_args
        assert 'MERGE (s:Stock {symbol: $symbol})' in call_args[0][0]

    def test_create_relationship_success(self, mock_service):
        """관계 생성 성공"""
        mock_result = Mock()
        mock_result.single.return_value = {'rel_type': 'PEER_OF'}
        mock_service._mock_session.run.return_value = mock_result

        result = mock_service.create_relationship(
            'NVDA', 'AMD', 'PEER_OF', 0.85, 'fmp',
            context={'source': 'test'}
        )
        assert result is True

    def test_create_indexes_success(self, mock_service):
        """인덱스 생성 성공"""
        result = mock_service.create_indexes()
        assert result is True

        # 3개 인덱스 생성 쿼리 호출 확인
        assert mock_service._mock_session.run.call_count == 3

    def test_get_related_stocks_success(self, mock_service):
        """관련 종목 조회 성공"""
        mock_records = [
            {
                'symbol': 'AMD',
                'name': 'AMD',
                'sector': 'Technology',
                'industry': 'Semiconductors',
                'market_cap': 200e9,
                'weight': 0.85,
                'relationship_type': 'PEER_OF',
                'source': 'fmp',
                'context_json': '{"test": true}'
            }
        ]
        mock_service._mock_session.run.return_value = mock_records

        result = mock_service.get_related_stocks('NVDA', rel_type='PEER_OF', limit=10)

        assert len(result) == 1
        assert result[0]['symbol'] == 'AMD'
        assert result[0]['weight'] == 0.85
        assert result[0]['context'] == {"test": True}


@pytest.mark.django_db
class TestNeo4jChainSightServiceIntegration:
    """통합 테스트 (실제 Neo4j 연결 필요)"""

    @pytest.fixture
    def service(self):
        """실제 Neo4j 연결 서비스"""
        service = Neo4jChainSightService()
        if not service.is_available():
            pytest.skip("Neo4j not available")
        return service

    def test_create_and_query_stock(self, service):
        """Stock 노드 생성 및 조회"""
        # 테스트 데이터 생성
        result = service.create_stock_node(
            'TEST_NVDA',
            'Test NVIDIA',
            'Technology',
            'Semiconductors',
            1e12
        )
        assert result is True

        # 조회 확인 (통계로)
        stats = service.get_statistics()
        assert stats.get('stock_nodes', 0) > 0

    def test_create_and_query_relationship(self, service):
        """관계 생성 및 조회"""
        # 테스트 노드 생성
        service.create_stock_node('TEST_A', 'Test A', 'Technology', 'Software', 1e9)
        service.create_stock_node('TEST_B', 'Test B', 'Technology', 'Software', 1e9)

        # 관계 생성
        result = service.create_relationship(
            'TEST_A', 'TEST_B', 'PEER_OF', 0.9, 'test',
            context={'test': True}
        )
        assert result is True

        # 관련 종목 조회
        related = service.get_related_stocks('TEST_A', rel_type='PEER_OF')
        symbols = [r['symbol'] for r in related]
        assert 'TEST_B' in symbols

    def test_n_depth_graph(self, service):
        """N-depth 그래프 조회"""
        # 테스트 데이터 생성
        service.create_stock_node('CENTER', 'Center Stock', 'Technology', 'Software', 1e9)
        service.create_stock_node('DEPTH1_A', 'Depth 1 A', 'Technology', 'Software', 1e9)
        service.create_stock_node('DEPTH1_B', 'Depth 1 B', 'Technology', 'Software', 1e9)

        service.create_relationship('CENTER', 'DEPTH1_A', 'PEER_OF', 0.8, 'test')
        service.create_relationship('CENTER', 'DEPTH1_B', 'SAME_INDUSTRY', 0.7, 'test')

        # 그래프 조회
        graph = service.get_n_depth_graph('CENTER', depth=1)

        assert len(graph['nodes']) > 0
        assert len(graph['edges']) > 0

        # 중심 노드 확인
        center_nodes = [n for n in graph['nodes'] if n['id'] == 'CENTER']
        assert len(center_nodes) == 1
        assert center_nodes[0]['group'] == 'center'

    def test_sync_from_postgres(self, service):
        """PostgreSQL에서 Neo4j로 동기화"""
        from serverless.models import StockRelationship

        # PostgreSQL에 테스트 데이터 있는지 확인
        if not StockRelationship.objects.exists():
            pytest.skip("No PostgreSQL relationships to sync")

        # 첫 번째 심볼로 동기화 테스트
        first_symbol = StockRelationship.objects.values_list(
            'source_symbol', flat=True
        ).first()

        result = service.sync_from_postgres(first_symbol)

        assert 'synced' in result
        assert 'failed' in result
        assert result['synced'] >= 0

    def test_statistics(self, service):
        """통계 조회"""
        stats = service.get_statistics()

        assert 'stock_nodes' in stats
        assert 'sector_nodes' in stats
        assert 'peer_of_relationships' in stats
        assert 'same_industry_relationships' in stats
        assert 'co_mentioned_relationships' in stats


class TestFallbackGraph:
    """PostgreSQL Fallback 그래프 테스트"""

    def test_fallback_graph_with_no_relationships(self):
        """관계가 없을 때 fallback 그래프"""
        from serverless.views import _get_fallback_graph

        with patch('serverless.models.StockRelationship') as mock_model:
            mock_model.objects.filter.return_value.order_by.return_value.__getitem__ = Mock(return_value=[])

            with patch('serverless.services.fmp_client.FMPClient') as mock_fmp:
                mock_fmp_instance = Mock()
                mock_fmp_instance.get_company_profile.return_value = {
                    'companyName': 'Test Company',
                    'sector': 'Technology'
                }
                mock_fmp.return_value = mock_fmp_instance

                graph = _get_fallback_graph('TEST', 1)

                assert len(graph['nodes']) >= 1  # 최소 중심 노드
                assert graph['nodes'][0]['group'] == 'center'

    def test_fallback_graph_with_relationships(self):
        """관계가 있을 때 fallback 그래프"""
        from serverless.views import _get_fallback_graph

        # Mock 관계 데이터
        mock_rel = Mock()
        mock_rel.target_symbol = 'TARGET'
        mock_rel.relationship_type = 'PEER_OF'
        mock_rel.strength = Decimal('0.85')
        mock_rel.context = {'sector': 'Technology'}

        with patch('serverless.models.StockRelationship') as mock_model:
            mock_qs = Mock()
            mock_qs.order_by.return_value.__getitem__ = Mock(return_value=[mock_rel])
            mock_model.objects.filter.return_value = mock_qs

            with patch('serverless.services.fmp_client.FMPClient') as mock_fmp:
                mock_fmp_instance = Mock()
                mock_fmp_instance.get_company_profile.return_value = {
                    'companyName': 'Test Company',
                    'sector': 'Technology'
                }
                mock_fmp.return_value = mock_fmp_instance

                graph = _get_fallback_graph('SOURCE', 1)

                assert len(graph['nodes']) >= 1
                # 중심 노드와 관련 노드가 있어야 함
                node_ids = [n['id'] for n in graph['nodes']]
                assert 'SOURCE' in node_ids
