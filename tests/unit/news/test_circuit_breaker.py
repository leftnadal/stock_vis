"""
Circuit Breaker 테스트

Redis 기반 Circuit Breaker의 열림/닫힘 시나리오를 검증합니다.
"""
import pytest
from unittest.mock import patch, MagicMock

from news.services.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    """CircuitBreaker 테스트"""

    @pytest.fixture
    def breaker(self):
        """기본 CircuitBreaker (threshold=5, timeout=300)"""
        return CircuitBreaker('test_provider', threshold=5, timeout=300)

    @pytest.fixture
    def breaker_low_threshold(self):
        """낮은 임계값 CircuitBreaker (threshold=2)"""
        return CircuitBreaker('test_low', threshold=2, timeout=60)

    @patch('news.services.circuit_breaker.cache')
    def test_initial_state_closed(self, mock_cache, breaker):
        """Given fresh breaker, When check, Then circuit is closed"""
        mock_cache.get.return_value = None
        assert breaker.is_open() is False

    @patch('news.services.circuit_breaker.cache')
    def test_is_open_when_key_exists(self, mock_cache, breaker):
        """Given circuit key exists, When check, Then circuit is open"""
        mock_cache.get.return_value = 1
        assert breaker.is_open() is True

    @patch('news.services.circuit_breaker.cache')
    def test_record_success_clears_failures(self, mock_cache, breaker):
        """Given breaker, When record_success, Then failures key deleted"""
        breaker.record_success()
        mock_cache.delete.assert_called_with('circuit:test_provider:failures')

    @patch('news.services.circuit_breaker.cache')
    def test_record_failure_increments(self, mock_cache, breaker):
        """Given breaker, When record_failure, Then failure count increases"""
        mock_cache.get.return_value = 2  # 기존 2회 실패
        breaker.record_failure()

        # 3으로 업데이트 (2+1)
        mock_cache.set.assert_called_once_with(
            'circuit:test_provider:failures', 3, timeout=600
        )

    @patch('news.services.circuit_breaker.cache')
    def test_circuit_opens_at_threshold(self, mock_cache, breaker_low_threshold):
        """Given failures at threshold, When record_failure, Then circuit opens"""
        mock_cache.get.return_value = 1  # 1회 실패 상태

        breaker_low_threshold.record_failure()  # 2회 → threshold 도달

        # circuit key 설정 확인 (is_open이 True가 되도록)
        calls = mock_cache.set.call_args_list
        circuit_set_calls = [c for c in calls if c[0][0] == 'circuit:test_low']
        assert len(circuit_set_calls) == 1
        assert circuit_set_calls[0][1]['timeout'] == 60  # timeout=60

    @patch('news.services.circuit_breaker.cache')
    def test_circuit_stays_closed_below_threshold(self, mock_cache, breaker):
        """Given failures below threshold, When record_failure, Then circuit stays closed"""
        mock_cache.get.return_value = 0  # 0회 실패

        breaker.record_failure()  # 1회 → threshold 미달

        # circuit key가 설정되지 않아야 함
        calls = mock_cache.set.call_args_list
        circuit_set_calls = [c for c in calls if c[0][0] == 'circuit:test_provider']
        assert len(circuit_set_calls) == 0

    @patch('news.services.circuit_breaker.cache')
    def test_reset_clears_all(self, mock_cache, breaker):
        """Given breaker, When reset, Then all keys deleted"""
        breaker.reset()
        mock_cache.delete.assert_any_call('circuit:test_provider')
        mock_cache.delete.assert_any_call('circuit:test_provider:failures')

    @patch('news.services.circuit_breaker.cache')
    def test_get_status(self, mock_cache, breaker):
        """Given breaker, When get_status, Then status dict 반환"""
        mock_cache.get.side_effect = [None, 3]  # is_open=False, failures=3

        status = breaker.get_status()
        assert status['provider'] == 'test_provider'
        assert status['is_open'] is False
        assert status['failures'] == 3
        assert status['threshold'] == 5
        assert status['timeout'] == 300

    @patch('news.services.circuit_breaker.cache')
    def test_record_failure_cache_error(self, mock_cache, breaker):
        """Given cache error, When record_failure, Then no crash (graceful)"""
        mock_cache.get.side_effect = Exception("Redis connection error")
        # Should not raise
        breaker.record_failure()

    @patch('news.services.circuit_breaker.cache')
    def test_record_success_cache_error(self, mock_cache, breaker):
        """Given cache error, When record_success, Then no crash (graceful)"""
        mock_cache.delete.side_effect = Exception("Redis connection error")
        # Should not raise
        breaker.record_success()


pytestmark = pytest.mark.unit
