"""
API Rate Limiter Service

Redis 기반 Rate Limiting으로 외부 API 호출 제한을 관리합니다.
- FMP: 10 calls/minute, 250 calls/day
- Alpha Vantage: 5 calls/minute, 500 calls/day
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """Redis 기반 API Rate Limiter"""

    # API별 Rate Limit 설정
    LIMITS = {
        'fmp': {
            'per_minute': 10,
            'per_day': 250,
        },
        'alpha_vantage': {
            'per_minute': 5,
            'per_day': 500,
        },
        'yfinance': {
            'per_minute': 60,  # yfinance는 제한이 느슨함
            'per_day': 10000,
        },
    }

    # 캐시 키 패턴
    MINUTE_KEY = "rate_limit:{api}:minute:{minute}"
    DAY_KEY = "rate_limit:{api}:day:{date}"

    def __init__(self, api_name: str):
        """
        Args:
            api_name: API 이름 ('fmp', 'alpha_vantage', 'yfinance')
        """
        self.api_name = api_name.lower()
        if self.api_name not in self.LIMITS:
            raise ValueError(f"Unknown API: {api_name}. Supported: {list(self.LIMITS.keys())}")

        self.limits = self.LIMITS[self.api_name]

    def _get_minute_key(self) -> str:
        """현재 분 단위 키 생성"""
        now = timezone.now()
        minute = now.strftime('%Y%m%d%H%M')
        return self.MINUTE_KEY.format(api=self.api_name, minute=minute)

    def _get_day_key(self) -> str:
        """현재 일 단위 키 생성"""
        now = timezone.now()
        date = now.strftime('%Y%m%d')
        return self.DAY_KEY.format(api=self.api_name, date=date)

    def can_call(self) -> Tuple[bool, Optional[str]]:
        """
        API 호출 가능 여부 확인.

        Returns:
            (can_call, reason) - 호출 가능 여부와 불가 사유
        """
        minute_key = self._get_minute_key()
        day_key = self._get_day_key()

        # 분당 제한 확인
        minute_count = cache.get(minute_key, 0)
        if minute_count >= self.limits['per_minute']:
            return False, f"분당 제한 초과 ({minute_count}/{self.limits['per_minute']})"

        # 일일 제한 확인
        day_count = cache.get(day_key, 0)
        if day_count >= self.limits['per_day']:
            return False, f"일일 제한 초과 ({day_count}/{self.limits['per_day']})"

        return True, None

    def record_call(self) -> bool:
        """
        API 호출 기록.

        Returns:
            True if recorded successfully
        """
        minute_key = self._get_minute_key()
        day_key = self._get_day_key()

        try:
            # 분당 카운터 증가 (1분 후 만료)
            minute_count = cache.get(minute_key, 0)
            cache.set(minute_key, minute_count + 1, 60)

            # 일일 카운터 증가 (24시간 후 만료)
            day_count = cache.get(day_key, 0)
            cache.set(day_key, day_count + 1, 86400)

            logger.debug(f"Rate limit recorded for {self.api_name}: minute={minute_count + 1}, day={day_count + 1}")
            return True

        except Exception as e:
            logger.error(f"Failed to record rate limit for {self.api_name}: {e}")
            return False

    def get_usage(self) -> dict:
        """
        현재 사용량 조회.

        Returns:
            {
                'minute': {'used': int, 'limit': int},
                'day': {'used': int, 'limit': int},
                'can_call': bool
            }
        """
        minute_key = self._get_minute_key()
        day_key = self._get_day_key()

        minute_count = cache.get(minute_key, 0)
        day_count = cache.get(day_key, 0)

        can_call, _ = self.can_call()

        return {
            'api': self.api_name,
            'minute': {
                'used': minute_count,
                'limit': self.limits['per_minute'],
                'remaining': max(0, self.limits['per_minute'] - minute_count),
            },
            'day': {
                'used': day_count,
                'limit': self.limits['per_day'],
                'remaining': max(0, self.limits['per_day'] - day_count),
            },
            'can_call': can_call,
        }

    def get_reset_time(self) -> dict:
        """
        Rate Limit 초기화 시간 조회.

        Returns:
            {
                'minute_reset': datetime,
                'day_reset': datetime
            }
        """
        now = timezone.now()

        # 다음 분
        minute_reset = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)

        # 다음 날 (UTC 기준)
        day_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            'minute_reset': minute_reset.isoformat(),
            'day_reset': day_reset.isoformat(),
        }

    def wait_for_available(self, max_wait: int = 60) -> bool:
        """
        Rate Limit이 풀릴 때까지 대기.
        (Celery 태스크에서 사용 권장)

        Args:
            max_wait: 최대 대기 시간 (초)

        Returns:
            True if available within max_wait, False otherwise
        """
        import time

        start = timezone.now()
        while (timezone.now() - start).total_seconds() < max_wait:
            can_call, _ = self.can_call()
            if can_call:
                return True
            time.sleep(1)

        return False


class RateLimitedAPICall:
    """
    Rate Limiting이 적용된 API 호출을 위한 컨텍스트 매니저.

    Usage:
        with RateLimitedAPICall('fmp') as limiter:
            if limiter.can_proceed:
                # API 호출 실행
                response = make_api_call()
            else:
                # 제한 초과
                raise RateLimitError(...)
    """

    def __init__(self, api_name: str, auto_record: bool = True):
        self.limiter = APIRateLimiter(api_name)
        self.auto_record = auto_record
        self.can_proceed = False
        self.reason = None

    def __enter__(self):
        self.can_proceed, self.reason = self.limiter.can_call()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.can_proceed and self.auto_record and exc_type is None:
            self.limiter.record_call()
        return False


def check_rate_limit(api_name: str) -> Tuple[bool, dict]:
    """
    간단한 Rate Limit 체크 함수.

    Args:
        api_name: API 이름

    Returns:
        (can_call, usage_info)
    """
    try:
        limiter = APIRateLimiter(api_name)
        can_call, reason = limiter.can_call()
        usage = limiter.get_usage()
        usage['reason'] = reason
        return can_call, usage
    except ValueError as e:
        return False, {'error': str(e)}


def record_api_call(api_name: str) -> bool:
    """
    간단한 API 호출 기록 함수.

    Args:
        api_name: API 이름

    Returns:
        True if recorded successfully
    """
    try:
        limiter = APIRateLimiter(api_name)
        return limiter.record_call()
    except ValueError:
        return False
