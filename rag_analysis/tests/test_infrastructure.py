"""
Infrastructure Component Tests

Tests for:
- Neo4j driver (lazy connection)
- Neo4j service (queries)
- Cache service
- Celery tasks
- Django signals
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from stocks.models import Stock


class Neo4jDriverTests(TestCase):
    """
    Neo4j Driver Tests
    """

    @patch('rag_analysis.services.neo4j_driver.GraphDatabase')
    def test_lazy_connection_success(self, mock_gdb):
        """첫 호출 시 연결 시도"""
        from rag_analysis.services.neo4j_driver import get_neo4j_driver, reset_connection

        # Reset state
        reset_connection()

        # Mock driver
        mock_driver = Mock()
        mock_driver.verify_connectivity.return_value = None
        mock_gdb.driver.return_value = mock_driver

        # First call - should connect
        driver = get_neo4j_driver()
        self.assertIsNotNone(driver)
        mock_gdb.driver.assert_called_once()

        # Second call - should use cached driver
        driver2 = get_neo4j_driver()
        self.assertEqual(driver, driver2)
        mock_gdb.driver.assert_called_once()  # Still only called once

    @patch('rag_analysis.services.neo4j_driver.GraphDatabase')
    def test_connection_failure_returns_none(self, mock_gdb):
        """연결 실패 시 None 반환 (앱은 계속 실행)"""
        from rag_analysis.services.neo4j_driver import get_neo4j_driver, reset_connection

        # Reset state
        reset_connection()

        # Mock connection failure
        mock_gdb.driver.side_effect = Exception("Connection failed")

        # Should return None, not raise
        driver = get_neo4j_driver()
        self.assertIsNone(driver)


class Neo4jServiceTests(TestCase):
    """
    Neo4j Service Tests
    """

    def test_fallback_when_driver_unavailable(self):
        """Neo4j 연결 실패 시 fallback 데이터 반환"""
        from rag_analysis.services.neo4j_service import Neo4jServiceLite

        # Mock driver as None
        service = Neo4jServiceLite()
        service.driver = None

        # Should return empty relationships with fallback status
        result = service.get_stock_relationships('AAPL')

        self.assertEqual(result['symbol'], 'AAPL')
        self.assertEqual(result['supply_chain'], [])
        self.assertEqual(result['competitors'], [])
        self.assertEqual(result['sector_peers'], [])
        self.assertEqual(result['_meta']['source'], 'fallback')
        self.assertIsNotNone(result['_meta']['_error'])

    @patch('rag_analysis.services.neo4j_service.get_neo4j_driver')
    def test_health_check_unavailable(self, mock_get_driver):
        """Neo4j 연결 불가 시 health check"""
        from rag_analysis.services.neo4j_service import Neo4jServiceLite

        mock_get_driver.return_value = None

        service = Neo4jServiceLite()
        health = service.health_check()

        self.assertEqual(health['status'], 'unavailable')
        self.assertFalse(health['connected'])
        self.assertIsNone(health['node_count'])


class CacheServiceTests(TestCase):
    """
    Cache Service Tests
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_graph_context_cache(self):
        """그래프 컨텍스트 캐싱"""
        from rag_analysis.services.cache import get_cache_service

        cache_service = get_cache_service()

        test_data = {
            'symbol': 'AAPL',
            'supply_chain': [{'symbol': 'NVDA', 'strength': 0.8}],
            'competitors': []
        }

        # Set
        success = cache_service.set_graph_context('AAPL', test_data)
        self.assertTrue(success)

        # Get
        cached = cache_service.get_graph_context('AAPL')
        self.assertIsNotNone(cached)
        self.assertEqual(cached['symbol'], 'AAPL')

        # Invalidate
        success = cache_service.invalidate_graph('AAPL')
        self.assertTrue(success)

        # Should be empty now
        cached = cache_service.get_graph_context('AAPL')
        self.assertIsNone(cached)

    def test_llm_response_cache(self):
        """LLM 응답 캐싱"""
        from rag_analysis.services.cache import get_cache_service

        cache_service = get_cache_service()

        prompt = "What is the revenue trend for AAPL?"
        response = "Apple's revenue has been growing steadily..."

        # Set
        success = cache_service.set_llm_response(prompt, response)
        self.assertTrue(success)

        # Get
        cached = cache_service.get_llm_response(prompt)
        self.assertEqual(cached, response)


class CeleryTaskTests(TestCase):
    """
    Celery Task Tests
    """

    @patch('rag_analysis.tasks.get_neo4j_service')
    def test_sync_task_when_neo4j_unavailable(self, mock_get_service):
        """Neo4j 연결 불가 시 태스크는 'skipped' 반환"""
        from rag_analysis.tasks import sync_stock_to_neo4j

        # Mock service with driver=None
        mock_service = Mock()
        mock_service.driver = None
        mock_get_service.return_value = mock_service

        # Execute task
        result = sync_stock_to_neo4j('AAPL', 'Apple Inc.', 'Technology')

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['symbol'], 'AAPL')
        self.assertFalse(result['neo4j_available'])

    @patch('rag_analysis.tasks.get_neo4j_service')
    def test_delete_task_success(self, mock_get_service):
        """Neo4j 삭제 태스크 성공"""
        from rag_analysis.tasks import delete_stock_from_neo4j

        # Mock service
        mock_service = Mock()
        mock_service.driver = Mock()
        mock_service.delete_stock_node.return_value = True
        mock_get_service.return_value = mock_service

        # Execute task
        result = delete_stock_from_neo4j('AAPL')

        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['neo4j_available'])
        mock_service.delete_stock_node.assert_called_once_with('AAPL')


class SignalTests(TestCase):
    """
    Django Signal Tests
    """

    @patch('rag_analysis.signals.sync_stock_to_neo4j')
    @patch('rag_analysis.signals.invalidate_graph_cache')
    def test_stock_saved_triggers_sync(self, mock_invalidate, mock_sync):
        """Stock 저장 시 Neo4j 동기화 태스크 큐잉"""
        # Create stock
        stock = Stock.objects.create(
            symbol='TEST',
            stock_name='Test Inc.',
            sector='Technology'
        )

        # Signal should trigger async tasks
        mock_sync.delay.assert_called_once()
        mock_invalidate.delay.assert_called_once_with('TEST')

    @patch('rag_analysis.signals.delete_stock_from_neo4j')
    @patch('rag_analysis.signals.invalidate_graph_cache')
    def test_stock_deleted_triggers_neo4j_delete(self, mock_invalidate, mock_delete):
        """Stock 삭제 시 Neo4j 삭제 태스크 큐잉"""
        # Create and delete stock
        stock = Stock.objects.create(symbol='TEST', stock_name='Test Inc.')
        stock_symbol = stock.symbol
        stock.delete()

        # Signal should trigger delete task
        mock_delete.delay.assert_called_once_with(symbol=stock_symbol)
        mock_invalidate.delay.assert_called()


class IntegrationTests(TestCase):
    """
    Integration Tests (without actual Neo4j)
    """

    def test_app_starts_without_neo4j(self):
        """Neo4j 없이 앱 시작 가능"""
        from rag_analysis.services import get_neo4j_service, get_cache_service

        # Services should be importable
        neo4j_service = get_neo4j_service()
        cache_service = get_cache_service()

        self.assertIsNotNone(neo4j_service)
        self.assertIsNotNone(cache_service)

    def test_tasks_are_registered(self):
        """Celery 태스크 등록 확인"""
        from rag_analysis.tasks import (
            sync_stock_to_neo4j,
            delete_stock_from_neo4j,
            health_check_neo4j,
            batch_sync_stocks_to_neo4j,
            invalidate_graph_cache
        )

        # All tasks should have names
        self.assertEqual(sync_stock_to_neo4j.name, 'rag_analysis.tasks.sync_stock_to_neo4j')
        self.assertEqual(delete_stock_from_neo4j.name, 'rag_analysis.tasks.delete_stock_from_neo4j')
        self.assertEqual(health_check_neo4j.name, 'rag_analysis.tasks.health_check_neo4j')
        self.assertEqual(batch_sync_stocks_to_neo4j.name, 'rag_analysis.tasks.batch_sync_stocks_to_neo4j')
        self.assertEqual(invalidate_graph_cache.name, 'rag_analysis.tasks.invalidate_graph_cache')
