"""
FRED Rate Limiter 설정 테스트

검증 항목:
  - RATE_LIMITS에 'fred' 등록 확인
  - REQUEST_DELAYS에 'fred' 등록 확인
  - get_rate_limiter('fred') 정상 반환
"""

from packages.shared.api_request.rate_limiter import (
    RATE_LIMITS,
    REQUEST_DELAYS,
    LimitType,
    get_rate_limiter,
)


class TestFredRateLimiterConfig:

    def test_fred_in_rate_limits(self):
        """RATE_LIMITS에 fred 등록됨"""
        assert "fred" in RATE_LIMITS

    def test_fred_per_minute_limit(self):
        """FRED: 분당 100회 제한"""
        assert RATE_LIMITS["fred"][LimitType.PER_MINUTE] == 100

    def test_fred_no_daily_limit(self):
        """FRED: 일일 제한 없음"""
        assert LimitType.PER_DAY not in RATE_LIMITS["fred"]

    def test_fred_request_delay(self):
        """FRED: 요청 간격 0.6초"""
        assert REQUEST_DELAYS["fred"] == 0.6

    def test_get_rate_limiter_returns_instance(self):
        """get_rate_limiter('fred') → RateLimiter 인스턴스"""
        limiter = get_rate_limiter("fred")
        assert limiter.provider == "fred"
        assert limiter.request_delay == 0.6

    def test_get_rate_limiter_status(self):
        """get_status() 정상 반환"""
        limiter = get_rate_limiter("fred")
        status = limiter.get_status()
        assert status["provider"] == "fred"
        assert "per_minute" in status["limits"]
        assert status["limits"]["per_minute"]["limit"] == 100
