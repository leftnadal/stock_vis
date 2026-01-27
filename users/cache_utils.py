import logging
from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

# 캐시 로거 설정
cache_logger = logging.getLogger('users.cache')


class WatchlistCache:
    """
    ## Watchlist 데이터 캐싱 클래스
    # - 사용자별 캐시 키 전략 (user_id 포함)
    # - 실시간 가격 데이터 짧은 캐싱 (60초 TTL)
    # - 캐시 무효화: 종목 추가/삭제/수정 시
    """

    # 캐시 타입별 TTL 설정 (초)
    CACHE_TTL = {
        'watchlist_list': 300,      # 5분 - 사용자의 Watchlist 목록
        'watchlist_detail': 300,    # 5분 - 특정 Watchlist 상세 (종목 제외)
        'watchlist_stocks': 60,     # 1분 - Watchlist 종목 + 실시간 가격
    }

    @staticmethod
    def _make_cache_key(cache_type, user_id, **params):
        """
        ## 사용자별 캐시 키 생성
        # - 사용자 ID 포함 (필수)
        # - 추가 파라미터 포함 (선택)
        #
        # 예시:
        #   watchlist:list:user_123
        #   watchlist:stocks:user_123:wl_456
        """
        # 기본 키 생성
        base_key = f"watchlist:{cache_type}:user_{user_id}"

        # 추가 파라미터 포함
        if params:
            param_str = ':'.join(f"{k}_{v}" for k, v in sorted(params.items()))
            base_key = f"{base_key}:{param_str}"

        return base_key

    @staticmethod
    def get_watchlist_list(user_id):
        """
        ## Watchlist 목록 캐시 조회
        # - 사용자의 모든 Watchlist 목록
        """
        cache_key = WatchlistCache._make_cache_key('list', user_id)
        cached_data = cache.get(cache_key)

        if cached_data:
            cache_logger.info(f"Cache HIT: watchlist_list for user {user_id}")
        else:
            cache_logger.info(f"Cache MISS: watchlist_list for user {user_id}")

        return cached_data

    @staticmethod
    def set_watchlist_list(user_id, data, timeout=None):
        """
        ## Watchlist 목록 캐시 저장
        """
        if timeout is None:
            timeout = WatchlistCache.CACHE_TTL['watchlist_list']

        cache_key = WatchlistCache._make_cache_key('list', user_id)
        cache.set(cache_key, data, timeout)
        cache_logger.info(f"Cache SET: watchlist_list for user {user_id}, TTL={timeout}s")

    @staticmethod
    def get_watchlist_stocks(user_id, watchlist_id):
        """
        ## Watchlist 종목 데이터 캐시 조회 (실시간 가격 포함)
        # - 가장 자주 사용되는 엔드포인트
        # - 실시간 가격 포함이므로 짧은 캐싱 (60초)
        """
        cache_key = WatchlistCache._make_cache_key('stocks', user_id, wl=watchlist_id)
        cached_data = cache.get(cache_key)

        if cached_data:
            cache_logger.info(f"Cache HIT: watchlist_stocks for user {user_id}, watchlist {watchlist_id}")
        else:
            cache_logger.info(f"Cache MISS: watchlist_stocks for user {user_id}, watchlist {watchlist_id}")

        return cached_data

    @staticmethod
    def set_watchlist_stocks(user_id, watchlist_id, data, timeout=None):
        """
        ## Watchlist 종목 데이터 캐시 저장
        """
        if timeout is None:
            timeout = WatchlistCache.CACHE_TTL['watchlist_stocks']

        cache_key = WatchlistCache._make_cache_key('stocks', user_id, wl=watchlist_id)
        cache.set(cache_key, data, timeout)
        cache_logger.info(f"Cache SET: watchlist_stocks for user {user_id}, watchlist {watchlist_id}, TTL={timeout}s")

    @staticmethod
    def invalidate_watchlist_list(user_id):
        """
        ## Watchlist 목록 캐시 무효화
        # - Watchlist 생성/삭제 시 호출
        """
        cache_key = WatchlistCache._make_cache_key('list', user_id)
        cache.delete(cache_key)
        cache_logger.info(f"Cache INVALIDATED: watchlist_list for user {user_id}")

    @staticmethod
    def invalidate_watchlist_stocks(user_id, watchlist_id):
        """
        ## Watchlist 종목 데이터 캐시 무효화
        # - 종목 추가/삭제/수정 시 호출
        """
        cache_key = WatchlistCache._make_cache_key('stocks', user_id, wl=watchlist_id)
        cache.delete(cache_key)
        cache_logger.info(f"Cache INVALIDATED: watchlist_stocks for user {user_id}, watchlist {watchlist_id}")

    @staticmethod
    def invalidate_all_user_watchlists(user_id):
        """
        ## 사용자의 모든 Watchlist 캐시 무효화
        # - 큰 변경사항이 있을 때 사용 (예: 전체 데이터 새로고침)
        #
        # 주의: cache.delete_pattern()은 Redis 전용 메서드
        # 기본 Django 캐시 백엔드에서는 개별 삭제 필요
        """
        try:
            # Redis 백엔드인 경우
            pattern = f"watchlist:*:user_{user_id}*"
            if hasattr(cache, 'delete_pattern'):
                deleted_count = cache.delete_pattern(pattern)
                cache_logger.info(f"Cache INVALIDATED (pattern): {deleted_count} keys for user {user_id}")
            else:
                # 기본 백엔드: 주요 캐시만 삭제
                WatchlistCache.invalidate_watchlist_list(user_id)
                cache_logger.warning(f"Pattern delete not supported, invalidated list cache only for user {user_id}")
        except Exception as e:
            cache_logger.error(f"Cache invalidation error for user {user_id}: {e}")


def watchlist_cached_api(cache_type='stocks', timeout=None):
    """
    ## Watchlist API에 캐싱을 적용하는 데코레이터
    # - 자동으로 사용자별 캐싱 적용
    # - 캐시 히트/미스 처리 자동화
    #
    # 사용 예시:
    #     @watchlist_cached_api(cache_type='stocks', timeout=60)
    #     def get(self, request, pk):
    #         ...
    """
    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            user_id = request.user.id

            # pk가 있으면 watchlist_id로 사용
            watchlist_id = kwargs.get('pk')

            # 캐시 조회
            if cache_type == 'stocks' and watchlist_id:
                cached_data = WatchlistCache.get_watchlist_stocks(user_id, watchlist_id)
            elif cache_type == 'list':
                cached_data = WatchlistCache.get_watchlist_list(user_id)
            else:
                cached_data = None

            # 캐시 히트
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)

            # 캐시 미스 - 원본 함수 실행
            response = func(self, request, *args, **kwargs)

            # 성공적인 응답이면 캐시에 저장
            if response.status_code == status.HTTP_200_OK:
                if cache_type == 'stocks' and watchlist_id:
                    WatchlistCache.set_watchlist_stocks(user_id, watchlist_id, response.data, timeout)
                elif cache_type == 'list':
                    WatchlistCache.set_watchlist_list(user_id, response.data, timeout)

            return response

        return wrapper
    return decorator
