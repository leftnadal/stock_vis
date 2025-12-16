"""
Django Signals for Stock Model Sync to Neo4j

Critical:
    - 비동기 처리: Celery 태스크로 실행 (blocking 없음)
    - Neo4j 실패 시에도 Django 트랜잭션 영향 없음
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from stocks.models import Stock
from .tasks import sync_stock_to_neo4j, delete_stock_from_neo4j, invalidate_graph_cache

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Stock)
def stock_saved_handler(sender, instance, created, **kwargs):
    """
    Stock 모델 저장 시 Neo4j 동기화

    Args:
        sender: Stock 모델 클래스
        instance: Stock 인스턴스
        created: 신규 생성 여부
        **kwargs: 추가 인자

    Note:
        - Celery 태스크로 비동기 처리
        - Neo4j 동기화 실패해도 Django 트랜잭션은 성공
        - 캐시 무효화도 함께 수행
    """
    try:
        # Neo4j 동기화 (비동기)
        sync_stock_to_neo4j.delay(
            symbol=instance.symbol,
            name=instance.stock_name or instance.symbol,
            sector=instance.sector,
            industry=instance.industry
        )

        # 그래프 캐시 무효화 (비동기)
        invalidate_graph_cache.delay(instance.symbol)

        action = "created" if created else "updated"
        logger.info(f"Stock {action}: {instance.symbol} - Neo4j sync queued")

    except Exception as e:
        # Signal handler에서 예외 발생해도 Django 트랜잭션 영향 없음
        logger.error(f"Error queueing Neo4j sync for {instance.symbol}: {e}")


@receiver(post_delete, sender=Stock)
def stock_deleted_handler(sender, instance, **kwargs):
    """
    Stock 모델 삭제 시 Neo4j에서도 삭제

    Args:
        sender: Stock 모델 클래스
        instance: Stock 인스턴스
        **kwargs: 추가 인자

    Note:
        - Celery 태스크로 비동기 처리
        - DETACH DELETE로 모든 관계 함께 삭제
    """
    try:
        # Neo4j에서 삭제 (비동기)
        delete_stock_from_neo4j.delay(symbol=instance.symbol)

        # 그래프 캐시 무효화 (비동기)
        invalidate_graph_cache.delay(instance.symbol)

        logger.info(f"Stock deleted: {instance.symbol} - Neo4j deletion queued")

    except Exception as e:
        # Signal handler에서 예외 발생해도 Django 트랜잭션 영향 없음
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
