"""
Redis 기반 Circuit Breaker — per provider

연속 실패 시 해당 provider를 일시 차단하여 cascading failure 방지.
"""

import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Redis 기반 Circuit Breaker"""

    def __init__(self, provider_name: str, threshold: int = 5, timeout: int = 300):
        """
        Args:
            provider_name: Provider 이름 (fmp, alpha_vantage 등)
            threshold: 연속 실패 임계값 (기본: 5회)
            timeout: 차단 시간 (기본: 300초 = 5분)
        """
        self.provider_name = provider_name
        self.key = f"circuit:{provider_name}"
        self.failures_key = f"circuit:{provider_name}:failures"
        self.threshold = threshold
        self.timeout = timeout

    def is_open(self) -> bool:
        """Circuit이 열려있는지 (차단 상태) 확인"""
        return cache.get(self.key) is not None

    def record_failure(self):
        """실패 기록 — threshold 도달 시 circuit open"""
        try:
            # Redis INCR 에뮬레이션
            current = cache.get(self.failures_key, 0)
            current += 1
            cache.set(self.failures_key, current, timeout=self.timeout * 2)

            if current >= self.threshold:
                cache.set(self.key, 1, timeout=self.timeout)
                logger.critical(
                    f"Circuit OPEN: {self.provider_name} "
                    f"({current} consecutive failures, blocking for {self.timeout}s)"
                )
        except Exception as e:
            logger.error(f"CircuitBreaker.record_failure error: {e}")

    def record_success(self):
        """성공 기록 — 실패 카운터 초기화"""
        try:
            cache.delete(self.failures_key)
        except Exception as e:
            logger.error(f"CircuitBreaker.record_success error: {e}")

    def reset(self):
        """수동 리셋 — circuit 닫기"""
        try:
            cache.delete(self.key)
            cache.delete(self.failures_key)
            logger.info(f"Circuit RESET: {self.provider_name}")
        except Exception as e:
            logger.error(f"CircuitBreaker.reset error: {e}")

    def get_status(self) -> dict:
        """현재 상태 조회"""
        return {
            'provider': self.provider_name,
            'is_open': self.is_open(),
            'failures': cache.get(self.failures_key, 0),
            'threshold': self.threshold,
            'timeout': self.timeout,
        }
