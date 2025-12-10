# api_request/rate_limiter.py
"""
Rate Limiter

API 호출 빈도를 제한하고 일일 할당량을 관리합니다.
Redis 기반으로 분산 환경에서도 동작합니다.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from functools import wraps
from enum import Enum

from django.core.cache import cache

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Rate Limit 초과 예외"""
    def __init__(self, provider: str, limit_type: str, retry_after: int = 0):
        self.provider = provider
        self.limit_type = limit_type
        self.retry_after = retry_after
        message = f"{provider} {limit_type} rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)


class LimitType(Enum):
    """Rate Limit 타입"""
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"


# Provider별 Rate Limit 설정
RATE_LIMITS = {
    "alpha_vantage": {
        LimitType.PER_MINUTE: 5,
        LimitType.PER_DAY: 500,
    },
    "fmp": {
        LimitType.PER_MINUTE: 10,
        LimitType.PER_DAY: 250,
    }
}

# Request Delay 설정 (초)
REQUEST_DELAYS = {
    "alpha_vantage": 12.0,  # 분당 5회 = 12초 간격
    "fmp": 0.5,  # FMP는 더 관대
}


class RateLimiter:
    """
    API Rate Limiter

    Redis 기반 분산 Rate Limiting을 제공합니다.
    """

    CACHE_KEY_PREFIX = "rate_limit"

    def __init__(self, provider: str):
        """
        Args:
            provider: Provider 이름 (alpha_vantage, fmp)
        """
        self.provider = provider
        self.limits = RATE_LIMITS.get(provider, {})
        self.request_delay = REQUEST_DELAYS.get(provider, 1.0)
        self._last_request_time = 0

    def _get_cache_key(self, limit_type: LimitType) -> str:
        """캐시 키 생성"""
        return f"{self.CACHE_KEY_PREFIX}:{self.provider}:{limit_type.value}"

    def _get_window_seconds(self, limit_type: LimitType) -> int:
        """Rate Limit 윈도우 크기 (초)"""
        if limit_type == LimitType.PER_MINUTE:
            return 60
        elif limit_type == LimitType.PER_HOUR:
            return 3600
        elif limit_type == LimitType.PER_DAY:
            return 86400
        return 60

    def check_limit(self, limit_type: LimitType) -> bool:
        """
        Rate Limit 체크

        Args:
            limit_type: 체크할 limit 타입

        Returns:
            True if within limit, False if exceeded
        """
        limit = self.limits.get(limit_type)
        if limit is None:
            return True  # 설정된 limit 없음

        cache_key = self._get_cache_key(limit_type)
        current_count = cache.get(cache_key, 0)

        return current_count < limit

    def increment(self, limit_type: LimitType) -> int:
        """
        카운터 증가

        Args:
            limit_type: 증가할 limit 타입

        Returns:
            증가 후 카운트
        """
        cache_key = self._get_cache_key(limit_type)
        window = self._get_window_seconds(limit_type)

        try:
            # Redis 원자적 증가
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")

            pipe = redis_conn.pipeline()
            pipe.incr(cache_key)
            pipe.expire(cache_key, window)
            result = pipe.execute()
            return result[0]
        except ImportError:
            # Django 기본 캐시 fallback
            current = cache.get(cache_key, 0)
            new_count = current + 1
            cache.set(cache_key, new_count, window)
            return new_count
        except Exception as e:
            logger.warning(f"Rate limiter increment error: {e}")
            return 0

    def acquire(self) -> bool:
        """
        Rate Limit 획득 시도

        모든 limit 타입을 체크하고, 통과하면 카운터를 증가시킵니다.
        Request delay도 적용합니다.

        Returns:
            True if acquired, raises RateLimitExceeded if not
        """
        # 모든 limit 체크
        for limit_type in self.limits.keys():
            if not self.check_limit(limit_type):
                retry_after = self._get_retry_after(limit_type)
                raise RateLimitExceeded(self.provider, limit_type.value, retry_after)

        # Request delay 적용
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"{self.provider} rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        # 카운터 증가
        for limit_type in self.limits.keys():
            self.increment(limit_type)

        self._last_request_time = time.time()
        return True

    def _get_retry_after(self, limit_type: LimitType) -> int:
        """
        재시도 가능 시간 계산

        Args:
            limit_type: Limit 타입

        Returns:
            재시도까지 남은 시간 (초)
        """
        cache_key = self._get_cache_key(limit_type)

        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            ttl = redis_conn.ttl(cache_key)
            return max(0, ttl)
        except:
            # 기본값
            return self._get_window_seconds(limit_type)

    def get_status(self) -> Dict[str, Any]:
        """
        현재 Rate Limit 상태

        Returns:
            각 limit 타입별 현재 상태
        """
        status = {
            "provider": self.provider,
            "request_delay": self.request_delay,
            "limits": {}
        }

        for limit_type, limit in self.limits.items():
            cache_key = self._get_cache_key(limit_type)
            current = cache.get(cache_key, 0)
            status["limits"][limit_type.value] = {
                "current": current,
                "limit": limit,
                "remaining": max(0, limit - current),
                "reset_in": self._get_retry_after(limit_type)
            }

        return status

    def reset(self, limit_type: Optional[LimitType] = None) -> None:
        """
        카운터 리셋

        Args:
            limit_type: 리셋할 limit 타입 (None이면 모두 리셋)
        """
        types_to_reset = [limit_type] if limit_type else list(self.limits.keys())

        for lt in types_to_reset:
            cache_key = self._get_cache_key(lt)
            cache.delete(cache_key)
            logger.info(f"Reset rate limit counter: {cache_key}")


def rate_limited(provider: str):
    """
    Rate Limiting 데코레이터

    Args:
        provider: Provider 이름

    Example:
        @rate_limited("fmp")
        def get_quote(self, symbol: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = RateLimiter(provider)
            limiter.acquire()  # Rate limit 체크 및 대기
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Provider별 싱글톤 인스턴스
_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(provider: str) -> RateLimiter:
    """
    Provider별 Rate Limiter 인스턴스 반환

    Args:
        provider: Provider 이름

    Returns:
        RateLimiter 인스턴스
    """
    if provider not in _limiters:
        _limiters[provider] = RateLimiter(provider)
    return _limiters[provider]


def get_all_rate_limit_status() -> Dict[str, Any]:
    """
    모든 Provider의 Rate Limit 상태

    Returns:
        Provider별 상태 딕셔너리
    """
    return {
        provider: get_rate_limiter(provider).get_status()
        for provider in RATE_LIMITS.keys()
    }
