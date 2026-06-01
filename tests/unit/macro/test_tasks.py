"""
Macro Celery Tasks 단위 테스트

검증 항목:
  - update_economic_indicators: exponential backoff 적용
"""

from unittest.mock import MagicMock, patch

import pytest


class TestUpdateEconomicIndicatorsRetry:
    """update_economic_indicators의 exponential backoff 검증"""

    def _run_with_retries(self, retries_count):
        """bind=True 태스크를 특정 retries 값으로 실행"""
        from apps.market_pulse.tasks.macro import update_economic_indicators

        task = update_economic_indicators
        mock_retry = MagicMock()

        with patch.object(task, 'retry', mock_retry):
            # Celery의 request context를 push하여 retries 설정
            task.push_request(retries=retries_count)
            try:
                with patch('apps.market_pulse.services.macro_service.MacroEconomicService',
                           side_effect=Exception("FRED down")):
                    with patch('apps.market_pulse.tasks.macro.cache'):
                        task.run()
            finally:
                task.pop_request()

        return mock_retry

    def test_exponential_backoff_first_retry(self):
        """첫 번째 재시도: countdown = 60 (60 * 2^0)"""
        mock_retry = self._run_with_retries(0)
        mock_retry.assert_called_once_with(countdown=60)

    def test_exponential_backoff_second_retry(self):
        """두 번째 재시도: countdown = 120 (60 * 2^1)"""
        mock_retry = self._run_with_retries(1)
        mock_retry.assert_called_once_with(countdown=120)

    def test_exponential_backoff_third_retry(self):
        """세 번째 재시도: countdown = 240 (60 * 2^2)"""
        mock_retry = self._run_with_retries(2)
        mock_retry.assert_called_once_with(countdown=240)
