"""
Django Signals for Stock Model Sync to Neo4j

Critical:
    - 비동기 처리: Celery 태스크로 실행 (blocking 없음)
    - Neo4j 실패 시에도 Django 트랜잭션 영향 없음
    - 배치 업데이트 시 동일 심볼 중복 태스크 방지 (Redis debounce)
"""

import logging
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from stocks.models import Stock
from .tasks import sync_stock_to_neo4j, delete_stock_from_neo4j, invalidate_graph_cache

logger = logging.getLogger(__name__)

# Debounce TTL: 동일 심볼에 대해 10초 내 중복 태스크 방지
_DEBOUNCE_TTL = 10


def _should_dispatch(action: str, symbol: str) -> bool:
    """Redis 기반 debounce — 동일 (action, symbol) 조합을 TTL 내 1회만 허용"""
    key = f'signal:debounce:{action}:{symbol}'
    if cache.get(key):
        return False
    cache.set(key, 1, _DEBOUNCE_TTL)
    return True


@receiver(post_save, sender=Stock)
def stock_saved_handler(sender, instance, created, **kwargs):
    """
    Stock 모델 저장 시 Neo4j 동기화

    Note:
        - Celery 태스크로 비동기 처리
        - Neo4j 동기화 실패해도 Django 트랜잭션은 성공
        - debounce: 배치 업데이트 시 동일 심볼 10초 내 중복 방지
    """
    try:
        symbol = instance.symbol

        if _should_dispatch('sync', symbol):
            sync_stock_to_neo4j.delay(
                symbol=symbol,
                name=instance.stock_name or symbol,
                sector=instance.sector,
                industry=instance.industry
            )
            invalidate_graph_cache.delay(symbol)
            action = "created" if created else "updated"
            logger.info(f"Stock {action}: {symbol} - Neo4j sync queued")
        else:
            logger.debug(f"Stock save debounced: {symbol}")

    except Exception as e:
        logger.error(f"Error queueing Neo4j sync for {instance.symbol}: {e}")


@receiver(post_delete, sender=Stock)
def stock_deleted_handler(sender, instance, **kwargs):
    """
    Stock 모델 삭제 시 Neo4j에서도 삭제

    Note:
        - 삭제는 debounce 없이 항상 실행 (되돌릴 수 없으므로)
    """
    try:
        delete_stock_from_neo4j.delay(symbol=instance.symbol)
        invalidate_graph_cache.delay(instance.symbol)
        logger.info(f"Stock deleted: {instance.symbol} - Neo4j deletion queued")

    except Exception as e:
        logger.error(f"Error queueing Neo4j deletion for {instance.symbol}: {e}")


# Optional: DailyPrice 업데이트 시 캐시 무효화
# from stocks.models import DailyPrice
#
# @receiver(post_save, sender=DailyPrice)
# def daily_price_saved_handler(sender, instance, created, **kwargs):
#     """
#     DailyPrice 업데이트 시 분석 캐시 무효화
#     """
#     try:
#         from .services.cache import get_cache_service
#         cache_service = get_cache_service()
#         cache_service.invalidate_analysis(instance.stock.symbol)
#         logger.debug(f"Analysis cache invalidated for {instance.stock.symbol}")
#     except Exception as e:
#         logger.error(f"Error invalidating analysis cache: {e}")
