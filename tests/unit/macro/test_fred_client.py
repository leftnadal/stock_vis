"""
FREDClient 단위 테스트

검증 항목:
  - API 키가 로그에 노출되지 않음
  - Transient 에러 (500, 502, 503, 504) → 최대 3회 재시도 후 실패
  - Permanent 에러 (401, 403, 404) → 즉시 raise, 재시도 없음
  - Rate Limiter 통합 (acquire 호출)
  - 정상 응답 파싱
"""

import logging
import pytest
from unittest.mock import patch, MagicMock

from macro.services.fred_client import FREDClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fred_client():
    """테스트용 FREDClient (API 키 하드코딩)"""
    with patch('macro.services.fred_client.get_rate_limiter') as mock_rl:
        mock_limiter = MagicMock()
        mock_limiter.acquire.return_value = True
        mock_rl.return_value = mock_limiter
        client = FREDClient(api_key='test_fred_key_secret_123')
        yield client


@pytest.fixture
def mock_rate_limiter():
    """Rate Limiter mock"""
    with patch('macro.services.fred_client.get_rate_limiter') as mock_rl:
        mock_limiter = MagicMock()
        mock_limiter.acquire.return_value = True
        mock_rl.return_value = mock_limiter
        yield mock_limiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code=200, json_data=None, text="error"):
    """Mock HTTP response"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    resp.raise_for_status.side_effect = (
        None if status_code == 200
        else Exception(f"HTTP {status_code}")
    )
    return resp


# ---------------------------------------------------------------------------
# Tests: API 키 로그 노출 차단
# ---------------------------------------------------------------------------

class TestApiKeyNotLeaked:
    """API 키가 로그 메시지에 절대 노출되지 않음을 검증"""

    @patch('macro.services.fred_client.requests.get')
    def test_api_key_not_in_error_log_on_http_error(self, mock_get, fred_client, caplog):
        """HTTP 에러 시 로그에 API 키 미포함"""
        mock_get.return_value = _mock_response(
            status_code=400,
            text="Bad request with api_key=test_fred_key_secret_123"
        )

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception):
                fred_client._make_request('series/observations', {'series_id': 'GDP'})

        for record in caplog.records:
            assert 'test_fred_key_secret_123' not in record.message

    @patch('macro.services.fred_client.requests.get')
    def test_api_key_not_in_error_log_on_request_exception(
        self, mock_get, fred_client, caplog
    ):
        """RequestException 시 로그에 API 키 미포함 (type(e).__name__만 로깅)"""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError(
            "Connection to https://api.stlouisfed.org/fred/series?api_key=test_fred_key_secret_123 failed"
        )

        with caplog.at_level(logging.ERROR):
            with pytest.raises(req.exceptions.ConnectionError):
                fred_client._make_request('series/observations', {'series_id': 'GDP'})

        for record in caplog.records:
            assert 'test_fred_key_secret_123' not in record.message

    @patch('macro.services.fred_client.requests.get')
    def test_response_text_truncated(self, mock_get, fred_client, caplog):
        """응답 텍스트가 200자로 truncate됨"""
        long_text = "x" * 500
        mock_get.return_value = _mock_response(status_code=422, text=long_text)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception):
                fred_client._make_request('series', {'series_id': 'GDP'})

        for record in caplog.records:
            if 'FRED API Error' in record.message:
                assert len(record.message) < 300


# ---------------------------------------------------------------------------
# Tests: 재시도 로직
# ---------------------------------------------------------------------------

class TestRetryLogic:
    """Transient 에러에 대한 재시도, Permanent 에러에 대한 즉시 실패"""

    @patch('macro.services.fred_client.time.sleep')
    @patch('macro.services.fred_client.requests.get')
    def test_transient_500_retries_3_times(self, mock_get, mock_sleep, fred_client):
        """500 에러 → 3회 시도 후 최종 실패"""
        mock_get.return_value = _mock_response(status_code=500)

        with pytest.raises(Exception):
            fred_client._make_request('series/observations', {'series_id': 'FEDFUNDS'})

        assert mock_get.call_count == 3

    @patch('macro.services.fred_client.time.sleep')
    @patch('macro.services.fred_client.requests.get')
    def test_transient_502_retries(self, mock_get, mock_sleep, fred_client):
        """502 에러도 재시도 대상"""
        mock_get.return_value = _mock_response(status_code=502)

        with pytest.raises(Exception):
            fred_client._make_request('series/observations', {'series_id': 'GDP'})

        assert mock_get.call_count == 3

    @patch('macro.services.fred_client.time.sleep')
    @patch('macro.services.fred_client.requests.get')
    def test_transient_recovers_on_second_attempt(self, mock_get, mock_sleep, fred_client):
        """첫 번째 500 → 두 번째 성공"""
        mock_get.side_effect = [
            _mock_response(status_code=500),
            _mock_response(status_code=200, json_data={'observations': []}),
        ]

        result = fred_client._make_request('series/observations', {'series_id': 'GDP'})
        assert result == {'observations': []}
        assert mock_get.call_count == 2

    @patch('macro.services.fred_client.time.sleep')
    @patch('macro.services.fred_client.requests.get')
    def test_exponential_backoff_delays(self, mock_get, mock_sleep, fred_client):
        """재시도 간 대기 시간: 2s, 4s"""
        mock_get.return_value = _mock_response(status_code=503)

        with pytest.raises(Exception):
            fred_client._make_request('series/observations', {'series_id': 'GDP'})

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert sleep_calls == [2, 4]

    @patch('macro.services.fred_client.requests.get')
    def test_permanent_401_no_retry(self, mock_get, fred_client):
        """401 → 즉시 실패, 재시도 없음"""
        mock_get.return_value = _mock_response(status_code=401)

        with pytest.raises(Exception):
            fred_client._make_request('series', {'series_id': 'GDP'})

        assert mock_get.call_count == 1

    @patch('macro.services.fred_client.requests.get')
    def test_permanent_403_no_retry(self, mock_get, fred_client):
        """403 → 즉시 실패"""
        mock_get.return_value = _mock_response(status_code=403)

        with pytest.raises(Exception):
            fred_client._make_request('series', {'series_id': 'GDP'})

        assert mock_get.call_count == 1

    @patch('macro.services.fred_client.requests.get')
    def test_permanent_404_no_retry(self, mock_get, fred_client):
        """404 → 즉시 실패"""
        mock_get.return_value = _mock_response(status_code=404)

        with pytest.raises(Exception):
            fred_client._make_request('series', {'series_id': 'INVALID'})

        assert mock_get.call_count == 1

    @patch('macro.services.fred_client.time.sleep')
    @patch('macro.services.fred_client.requests.get')
    def test_connection_error_retries(self, mock_get, mock_sleep, fred_client):
        """ConnectionError → 재시도"""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("conn refused")

        with pytest.raises(req.exceptions.ConnectionError):
            fred_client._make_request('series', {'series_id': 'GDP'})

        assert mock_get.call_count == 3


# ---------------------------------------------------------------------------
# Tests: Rate Limiter 통합
# ---------------------------------------------------------------------------

class TestRateLimiterIntegration:
    """Rate Limiter가 매 요청 전에 호출됨을 검증"""

    @patch('macro.services.fred_client.requests.get')
    def test_rate_limiter_acquire_called(self, mock_get, mock_rate_limiter):
        """정상 요청 시 acquire() 호출됨"""
        mock_get.return_value = _mock_response(
            status_code=200,
            json_data={'observations': [{'date': '2026-03-01', 'value': '5.33'}]}
        )

        client = FREDClient(api_key='test_key')
        client._make_request('series/observations', {'series_id': 'FEDFUNDS'})

        mock_rate_limiter.acquire.assert_called()

    @patch('macro.services.fred_client.time.sleep')
    @patch('macro.services.fred_client.requests.get')
    def test_rate_limiter_called_per_retry(self, mock_get, mock_sleep, mock_rate_limiter):
        """재시도마다 acquire() 호출됨"""
        mock_get.side_effect = [
            _mock_response(status_code=500),
            _mock_response(status_code=200, json_data={'observations': []}),
        ]

        client = FREDClient(api_key='test_key')
        client._make_request('series/observations', {'series_id': 'GDP'})

        assert mock_rate_limiter.acquire.call_count == 2


# ---------------------------------------------------------------------------
# Tests: 정상 응답
# ---------------------------------------------------------------------------

class TestSuccessfulRequests:

    @patch('macro.services.fred_client.requests.get')
    def test_get_latest_value(self, mock_get, fred_client):
        """최신 값 정상 조회"""
        mock_get.return_value = _mock_response(
            status_code=200,
            json_data={
                'observations': [
                    {'date': '2026-03-01', 'value': '5.33'}
                ]
            }
        )

        result = fred_client.get_latest_value('FEDFUNDS')

        assert result is not None
        assert result['value'] == 5.33
        assert result['date'] == '2026-03-01'
        assert result['series_id'] == 'FEDFUNDS'

    @patch('macro.services.fred_client.requests.get')
    def test_parse_value_dot(self, mock_get, fred_client):
        """'.' 값 → None"""
        mock_get.return_value = _mock_response(
            status_code=200,
            json_data={
                'observations': [{'date': '2026-03-01', 'value': '.'}]
            }
        )

        result = fred_client.get_latest_value('VIXCLS')
        assert result['value'] is None
