# api_request/cache/decorators.py
"""
Provider Caching Decorators

Redis 기반 캐싱 레이어로 API 호출을 최소화합니다.
"""

import logging
import hashlib
import json
from functools import wraps
from typing import Optional, Callable, Any, Dict
from datetime import datetime

from django.core.cache import cache

logger = logging.getLogger(__name__)


# 캐시 TTL 설정 (초)
CACHE_TTL = {
    "quote": 300,          # 5분 - 실시간 시세
    "profile": 86400,      # 24시간 - 회사 프로필
    "daily_prices": 3600,  # 1시간 - 일별 가격
    "weekly_prices": 3600, # 1시간 - 주별 가격
    "balance_sheet": 604800,     # 7일 - 대차대조표
    "income_statement": 604800,  # 7일 - 손익계산서
    "cash_flow": 604800,         # 7일 - 현금흐름표
    "search": 1800,        # 30분 - 검색 결과
    "sector": 3600,        # 1시간 - 섹터 성과
}


def generate_cache_key(
    provider: str,
    method: str,
    *args,
    **kwargs
) -> str:
    """
    캐시 키 생성

    Args:
        provider: Provider 이름
        method: 메서드 이름
        *args: 메서드 인자
        **kwargs: 메서드 키워드 인자

    Returns:
        캐시 키 문자열
    """
    # 인자들을 직렬화 가능한 형태로 변환
    key_parts = [provider, method]

    for arg in args:
        if hasattr(arg, 'value'):  # Enum 처리
            key_parts.append(str(arg.value))
        else:
            key_parts.append(str(arg))

    for k, v in sorted(kwargs.items()):
        if hasattr(v, 'value'):
            key_parts.append(f"{k}={v.value}")
        else:
            key_parts.append(f"{k}={v}")

    # 해시로 키 길이 제한
    key_string = ":".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]

    return f"stock_provider:{provider}:{method}:{key_hash}"


def cached_provider_call(
    cache_type: str,
    timeout: Optional[int] = None
) -> Callable:
    """
    Provider 메서드 캐싱 데코레이터

    Args:
        cache_type: 캐시 타입 (quote, profile 등)
        timeout: 캐시 TTL (초), None이면 기본값 사용

    Example:
        @cached_provider_call(cache_type="quote")
        def get_quote(self, symbol: str) -> ProviderResponse:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            # 캐시 키 생성
            provider_name = getattr(self, 'PROVIDER_NAME', 'unknown')
            cache_key = generate_cache_key(
                provider_name,
                func.__name__,
                *args,
                **kwargs
            )

            # 캐시 조회
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")

                # ProviderResponse인 경우 cached 플래그 설정
                if hasattr(cached_result, 'cached'):
                    cached_result.cached = True

                return cached_result

            # 캐시 미스 - 실제 API 호출
            logger.debug(f"Cache miss: {cache_key}")
            result = func(self, *args, **kwargs)

            # 성공 응답만 캐시
            if hasattr(result, 'success') and result.success:
                ttl = timeout or CACHE_TTL.get(cache_type, 3600)
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

            return result

        return wrapper
    return decorator


def invalidate_cache(
    provider: str,
    method: str,
    *args,
    **kwargs
) -> bool:
    """
    특정 캐시 무효화

    Args:
        provider: Provider 이름
        method: 메서드 이름
        *args: 메서드 인자
        **kwargs: 메서드 키워드 인자

    Returns:
        삭제 성공 여부
    """
    cache_key = generate_cache_key(provider, method, *args, **kwargs)
    deleted = cache.delete(cache_key)
    logger.info(f"Cache invalidated: {cache_key} (deleted: {deleted})")
    return deleted


def invalidate_provider_cache(provider: str) -> int:
    """
    특정 Provider의 모든 캐시 무효화

    Args:
        provider: Provider 이름

    Returns:
        삭제된 키 수

    Note:
        Django 기본 캐시 백엔드에서는 패턴 삭제가 제한적입니다.
        Redis 백엔드 사용 시 SCAN 명령으로 개선 가능합니다.
    """
    # Django 기본 캐시에서는 전체 패턴 삭제가 어려움
    # Redis 사용 시 아래 코드 활성화
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        pattern = f"stock_provider:{provider}:*"
        keys = redis_conn.keys(pattern)
        if keys:
            redis_conn.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys for provider: {provider}")
            return len(keys)
    except ImportError:
        logger.warning("django_redis not available, cannot invalidate by pattern")
    except Exception as e:
        logger.error(f"Error invalidating cache for {provider}: {e}")

    return 0


def invalidate_symbol_cache(symbol: str) -> int:
    """
    특정 심볼의 모든 캐시 무효화

    Args:
        symbol: 주식 심볼

    Returns:
        삭제된 키 수
    """
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        pattern = f"stock_provider:*:*:{symbol.upper()}*"
        keys = redis_conn.keys(pattern)
        if keys:
            redis_conn.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys for symbol: {symbol}")
            return len(keys)
    except ImportError:
        logger.warning("django_redis not available, cannot invalidate by pattern")
    except Exception as e:
        logger.error(f"Error invalidating cache for {symbol}: {e}")

    return 0


class CacheStats:
    """캐시 통계 수집"""

    _hits = 0
    _misses = 0
    _last_reset = datetime.now()

    @classmethod
    def hit(cls) -> None:
        cls._hits += 1

    @classmethod
    def miss(cls) -> None:
        cls._misses += 1

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        total = cls._hits + cls._misses
        hit_rate = (cls._hits / total * 100) if total > 0 else 0

        return {
            "hits": cls._hits,
            "misses": cls._misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 2),
            "since": cls._last_reset.isoformat()
        }

    @classmethod
    def reset(cls) -> None:
        cls._hits = 0
        cls._misses = 0
        cls._last_reset = datetime.now()
