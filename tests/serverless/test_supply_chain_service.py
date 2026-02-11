"""
Supply Chain Service Tests

Unit tests for supply chain synchronization service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import date

from serverless.services.supply_chain_service import (
    SupplyChainService,
    sync_supply_chain_for_symbol,
    get_supply_chain_for_symbol
)
from serverless.services.supply_chain_parser import SupplyChainRelation


@pytest.fixture
def service():
    """Create test service with mocked dependencies"""
    with patch('serverless.services.supply_chain_service.SECEdgarClient'):
        with patch('serverless.services.supply_chain_service.SupplyChainParser'):
            svc = SupplyChainService()
            yield svc


class TestSupplyChainService:
    """Supply Chain Service 테스트"""

    # ========================================
    # Sync Tests
    # ========================================

    @patch('serverless.services.supply_chain_service.cache')
    def test_sync_supply_chain_cache_hit(self, mock_cache, service):
        """캐시 히트 시 바로 반환"""
        cached_result = {
            'symbol': 'TSM',
            'status': 'success',
            'customers': [{'symbol': 'AAPL'}],
            'suppliers': [],
            'customer_count': 1,
            'supplier_count': 0
        }
        mock_cache.get.return_value = cached_result

        result = service.sync_supply_chain('TSM')

        assert result['cached'] is True
        assert result['customer_count'] == 1
        mock_cache.get.assert_called_once()

    @patch('serverless.services.supply_chain_service.cache')
    @patch.object(SupplyChainService, '_download_10k')
    @patch.object(SupplyChainService, '_save_relationships')
    @patch.object(SupplyChainService, '_sync_to_neo4j')
    def test_sync_supply_chain_success(
        self,
        mock_neo4j,
        mock_save,
        mock_download,
        mock_cache,
        service
    ):
        """동기화 성공 테스트"""
        mock_cache.get.return_value = None
        mock_download.return_value = """
        ITEM 1A. RISK FACTORS
        Apple Inc. accounted for 25% of our revenue.
        """

        # Mock parser
        mock_relation = SupplyChainRelation(
            source_symbol='TSM',
            target_name='Apple Inc.',
            target_symbol='AAPL',
            relation_type='customer',
            confidence='high',
            revenue_percent=25.0,
            evidence='Apple accounted for 25%'
        )
        service.parser.parse_10k = Mock(return_value=[mock_relation])
        service.edgar_client.extract_item_1a = Mock(return_value="Item 1A text")

        mock_save.return_value = 1
        mock_neo4j.return_value = 1

        result = service.sync_supply_chain('TSM')

        assert result['status'] == 'success'
        assert result['customer_count'] == 1
        assert result['supplier_count'] == 0
        assert result['cached'] is False

    @patch('serverless.services.supply_chain_service.cache')
    @patch.object(SupplyChainService, '_download_10k')
    def test_sync_supply_chain_no_10k(self, mock_download, mock_cache, service):
        """10-K 없음 테스트"""
        mock_cache.get.return_value = None
        mock_download.return_value = None

        result = service.sync_supply_chain('UNKNOWN')

        assert result['status'] == 'error'
        assert '10-K not found' in result.get('error', '')

    # ========================================
    # Batch Sync Tests
    # ========================================

    @patch.object(SupplyChainService, 'sync_supply_chain')
    def test_sync_batch_success(self, mock_sync, service):
        """배치 동기화 성공 테스트"""
        mock_sync.side_effect = [
            {'symbol': 'TSM', 'status': 'success', 'customer_count': 2, 'supplier_count': 1},
            {'symbol': 'NVDA', 'status': 'success', 'customer_count': 1, 'supplier_count': 2},
            {'symbol': 'AAPL', 'status': 'error', 'error': 'No 10-K'}
        ]

        result = service.sync_batch(['TSM', 'NVDA', 'AAPL'], delay=0)

        assert result['total'] == 3
        assert result['success'] == 2
        assert result['failed'] == 1
        assert 'AAPL' in result['failed_symbols']

    @patch.object(SupplyChainService, 'sync_supply_chain')
    def test_sync_batch_empty(self, mock_sync, service):
        """빈 배치 테스트"""
        result = service.sync_batch([], delay=0)

        assert result['total'] == 0
        assert result['success'] == 0

    # ========================================
    # Query Tests
    # ========================================

    @patch('serverless.services.supply_chain_service.cache')
    @patch('serverless.services.supply_chain_service.StockRelationship')
    def test_get_supply_chain_from_cache(self, mock_model, mock_cache, service):
        """캐시에서 공급망 조회"""
        mock_cache.get.return_value = {
            'customers': [{'symbol': 'AAPL'}],
            'suppliers': [{'symbol': 'ASML'}]
        }

        result = service.get_supply_chain('TSM')

        assert result['cached'] is True
        assert len(result['customers']) == 1
        assert len(result['suppliers']) == 1

    @patch('serverless.services.supply_chain_service.cache')
    @patch.object(SupplyChainService, '_get_relationships')
    def test_get_supply_chain_from_db(self, mock_get, mock_cache, service):
        """DB에서 공급망 조회"""
        mock_cache.get.return_value = None
        mock_get.side_effect = [
            [{'symbol': 'ASML', 'company_name': 'ASML Holdings'}],
            [{'symbol': 'AAPL', 'company_name': 'Apple Inc.'}]
        ]

        result = service.get_supply_chain('TSM')

        assert result['cached'] is False
        assert len(result['suppliers']) == 1
        assert len(result['customers']) == 1

    # ========================================
    # Strength Calculation Tests
    # ========================================

    def test_calculate_strength_high_confidence(self, service):
        """강도 계산 - 높은 신뢰도"""
        relation = SupplyChainRelation(
            source_symbol='TSM',
            target_name='Apple',
            target_symbol='AAPL',
            relation_type='customer',
            confidence='high',
            revenue_percent=25.0,
            evidence=''
        )

        strength = service._calculate_strength(relation)

        assert strength == Decimal('1.0')

    def test_calculate_strength_medium_confidence(self, service):
        """강도 계산 - 중간 신뢰도"""
        relation = SupplyChainRelation(
            source_symbol='TSM',
            target_name='Meta',
            target_symbol='META',
            relation_type='customer',
            confidence='medium',
            revenue_percent=None,
            evidence=''
        )

        strength = service._calculate_strength(relation)

        assert strength == Decimal('0.5')

    def test_calculate_strength_with_revenue_boost(self, service):
        """강도 계산 - 매출 비중 보너스"""
        relation = SupplyChainRelation(
            source_symbol='TSM',
            target_name='NVIDIA',
            target_symbol='NVDA',
            relation_type='customer',
            confidence='medium-high',
            revenue_percent=15.0,  # 10% 이상, 20% 미만
            evidence=''
        )

        strength = service._calculate_strength(relation)

        # medium-high (0.7) + revenue boost (0.05) = 0.75
        assert strength == Decimal('0.75')

    # ========================================
    # Cache Management Tests
    # ========================================

    @patch('serverless.services.supply_chain_service.cache')
    def test_clear_cache(self, mock_cache, service):
        """캐시 삭제 테스트"""
        mock_cache.delete.return_value = True

        result = service.clear_cache('TSM')

        assert result is True
        mock_cache.delete.assert_called_once_with('supply_chain:TSM')


class TestSaveRelationships:
    """관계 저장 테스트"""

    @pytest.fixture
    def service(self):
        with patch('serverless.services.supply_chain_service.SECEdgarClient'):
            with patch('serverless.services.supply_chain_service.SupplyChainParser'):
                return SupplyChainService()

    @pytest.mark.django_db
    def test_save_relationships_customer(self, service):
        """고객 관계 저장"""
        relations = [
            SupplyChainRelation(
                source_symbol='TSM',
                target_name='Apple Inc.',
                target_symbol='AAPL',
                relation_type='customer',
                confidence='high',
                revenue_percent=25.0,
                evidence='Apple accounted for 25%'
            )
        ]

        # Mock transaction and model
        with patch('serverless.services.supply_chain_service.StockRelationship') as mock_model:
            mock_model.objects.update_or_create.return_value = (Mock(), True)

            count = service._save_relationships('TSM', relations)

            assert count == 1
            mock_model.objects.update_or_create.assert_called_once()

            # Verify relationship_type is CUSTOMER_OF
            call_kwargs = mock_model.objects.update_or_create.call_args[1]
            assert call_kwargs.get('relationship_type') == 'CUSTOMER_OF'

    @pytest.mark.django_db
    def test_save_relationships_supplier(self, service):
        """공급사 관계 저장"""
        relations = [
            SupplyChainRelation(
                source_symbol='AAPL',
                target_name='TSMC',
                target_symbol='TSM',
                relation_type='supplier',
                confidence='medium-high',
                revenue_percent=None,
                evidence='We depend on TSMC'
            )
        ]

        with patch('serverless.services.supply_chain_service.StockRelationship') as mock_model:
            mock_model.objects.update_or_create.return_value = (Mock(), True)

            count = service._save_relationships('AAPL', relations)

            assert count == 1

            # Verify relationship_type is SUPPLIED_BY
            call_kwargs = mock_model.objects.update_or_create.call_args[1]
            assert call_kwargs.get('relationship_type') == 'SUPPLIED_BY'

    @pytest.mark.django_db
    def test_save_relationships_skip_unmatched(self, service):
        """티커 매칭 실패 시 스킵"""
        relations = [
            SupplyChainRelation(
                source_symbol='TSM',
                target_name='Unknown Company',
                target_symbol=None,  # No ticker match
                relation_type='customer',
                confidence='medium',
                revenue_percent=None,
                evidence='Some text'
            )
        ]

        with patch('serverless.services.supply_chain_service.StockRelationship') as mock_model:
            count = service._save_relationships('TSM', relations)

            assert count == 0
            mock_model.objects.update_or_create.assert_not_called()


class TestNeo4jSync:
    """Neo4j 동기화 테스트"""

    @pytest.fixture
    def service(self):
        with patch('serverless.services.supply_chain_service.SECEdgarClient'):
            with patch('serverless.services.supply_chain_service.SupplyChainParser'):
                return SupplyChainService()

    def test_sync_to_neo4j_success(self, service):
        """Neo4j 동기화 성공"""
        relations = [
            SupplyChainRelation(
                source_symbol='TSM',
                target_name='Apple',
                target_symbol='AAPL',
                relation_type='customer',
                confidence='high',
                revenue_percent=25,
                evidence='text'
            )
        ]

        # Patch where it's imported in the _sync_to_neo4j method
        with patch('serverless.services.neo4j_chain_sight_service.Neo4jChainSightService') as mock_neo4j:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_instance.create_stock_node.return_value = True
            mock_instance.create_relationship.return_value = True
            mock_neo4j.return_value = mock_instance

            count = service._sync_to_neo4j('TSM', relations)

            assert count == 1
            mock_instance.create_relationship.assert_called_once()

    def test_sync_to_neo4j_unavailable(self, service):
        """Neo4j 미사용 시 스킵"""
        relations = [
            SupplyChainRelation(
                source_symbol='TSM',
                target_name='Apple',
                target_symbol='AAPL',
                relation_type='customer',
                confidence='high',
                revenue_percent=25,
                evidence='text'
            )
        ]

        # Patch where it's imported in the _sync_to_neo4j method
        with patch('serverless.services.neo4j_chain_sight_service.Neo4jChainSightService') as mock_neo4j:
            mock_instance = Mock()
            mock_instance.is_available.return_value = False
            mock_neo4j.return_value = mock_instance

            count = service._sync_to_neo4j('TSM', relations)

            assert count == 0


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    @patch('serverless.services.supply_chain_service.SupplyChainService')
    def test_sync_supply_chain_for_symbol(self, mock_service_class):
        """sync_supply_chain_for_symbol 테스트"""
        mock_instance = Mock()
        mock_instance.sync_supply_chain.return_value = {'status': 'success'}
        mock_service_class.return_value = mock_instance

        result = sync_supply_chain_for_symbol('TSM')

        assert result['status'] == 'success'
        mock_instance.sync_supply_chain.assert_called_once_with('TSM')

    @patch('serverless.services.supply_chain_service.SupplyChainService')
    def test_get_supply_chain_for_symbol(self, mock_service_class):
        """get_supply_chain_for_symbol 테스트"""
        mock_instance = Mock()
        mock_instance.get_supply_chain.return_value = {'symbol': 'TSM'}
        mock_service_class.return_value = mock_instance

        result = get_supply_chain_for_symbol('TSM')

        assert result['symbol'] == 'TSM'
        mock_instance.get_supply_chain.assert_called_once_with('TSM')
