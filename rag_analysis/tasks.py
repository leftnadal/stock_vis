"""
Celery Tasks for RAG Analysis

Critical:
    - Idempotent: 중복 실행 시 안전
    - Neo4j 연결 실패 시에도 태스크는 성공 처리
"""

import logging
from celery import shared_task
from .services.neo4j_service import get_neo4j_service

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def sync_stock_to_neo4j(self, symbol: str, name: str, sector: str = None, industry: str = None):
    """
    종목 정보를 Neo4j에 동기화

    Args:
        symbol: 종목 심볼
        name: 회사명
        sector: 섹터
        industry: 업종

    Returns:
        {
            'status': 'success' | 'skipped' | 'failed',
            'symbol': str,
            'neo4j_available': bool,
            'error': None | str
        }

    Note:
        - Idempotent: MERGE를 사용하여 중복 생성 방지
        - Neo4j 연결 실패 시 'skipped' 반환 (재시도 없음)
    """
    neo4j_service = get_neo4j_service()

    # Neo4j 연결 확인
    if neo4j_service.driver is None:
        logger.warning(f"Neo4j unavailable - skipping sync for {symbol}")
        return {
            'status': 'skipped',
            'symbol': symbol,
            'neo4j_available': False,
            'error': 'neo4j_driver_not_available'
        }

    try:
        # Stock 노드 생성/업데이트
        success = neo4j_service.create_stock_node(
            symbol=symbol,
            name=name,
            sector=sector,
            industry=industry
        )

        if success:
            logger.info(f"Successfully synced {symbol} to Neo4j")
            return {
                'status': 'success',
                'symbol': symbol,
                'neo4j_available': True,
                'error': None
            }
        else:
            logger.error(f"Failed to sync {symbol} to Neo4j")
            return {
                'status': 'failed',
                'symbol': symbol,
                'neo4j_available': True,
                'error': 'create_node_failed'
            }

    except Exception as e:
        logger.error(f"Error syncing {symbol} to Neo4j: {e}")
        # 재시도 시도
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def delete_stock_from_neo4j(self, symbol: str):
    """
    종목을 Neo4j에서 삭제

    Args:
        symbol: 종목 심볼

    Returns:
        {
            'status': 'success' | 'skipped' | 'failed',
            'symbol': str,
            'neo4j_available': bool,
            'error': None | str
        }

    Note:
        - DETACH DELETE로 모든 관계 함께 삭제
        - Neo4j 연결 실패 시 'skipped' 반환
    """
    neo4j_service = get_neo4j_service()

    # Neo4j 연결 확인
    if neo4j_service.driver is None:
        logger.warning(f"Neo4j unavailable - skipping delete for {symbol}")
        return {
            'status': 'skipped',
            'symbol': symbol,
            'neo4j_available': False,
            'error': 'neo4j_driver_not_available'
        }

    try:
        # Stock 노드 삭제
        success = neo4j_service.delete_stock_node(symbol)

        if success:
            logger.info(f"Successfully deleted {symbol} from Neo4j")
            return {
                'status': 'success',
                'symbol': symbol,
                'neo4j_available': True,
                'error': None
            }
        else:
            logger.error(f"Failed to delete {symbol} from Neo4j")
            return {
                'status': 'failed',
                'symbol': symbol,
                'neo4j_available': True,
                'error': 'delete_node_failed'
            }

    except Exception as e:
        logger.error(f"Error deleting {symbol} from Neo4j: {e}")
        # 재시도 시도
        raise self.retry(exc=e)


@shared_task
def batch_sync_stocks_to_neo4j(stock_data_list: list):
    """
    여러 종목을 배치로 Neo4j에 동기화

    Args:
        stock_data_list: [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', ...},
            ...
        ]

    Returns:
        {
            'total': int,
            'success': int,
            'failed': int,
            'skipped': int,
            'results': [...]
        }

    Note:
        - 각 종목은 개별 태스크로 실행되지 않고 배치 처리
        - 100개 단위로 청킹하여 메모리 관리
    """
    import gc

    neo4j_service = get_neo4j_service()

    if neo4j_service.driver is None:
        logger.warning("Neo4j unavailable - skipping batch sync")
        return {
            'total': len(stock_data_list),
            'success': 0,
            'failed': 0,
            'skipped': len(stock_data_list),
            'results': [],
            'error': 'neo4j_driver_not_available'
        }

    results = {
        'total': len(stock_data_list),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'results': []
    }

    # 100개 단위로 청킹
    chunk_size = 100
    for i in range(0, len(stock_data_list), chunk_size):
        chunk = stock_data_list[i:i + chunk_size]

        for stock_data in chunk:
            try:
                success = neo4j_service.create_stock_node(
                    symbol=stock_data['symbol'],
                    name=stock_data['name'],
                    sector=stock_data.get('sector'),
                    industry=stock_data.get('industry'),
                    market_cap=stock_data.get('market_cap')
                )

                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1

            except Exception as e:
                logger.error(f"Error syncing {stock_data['symbol']}: {e}")
                results['failed'] += 1

        # 청크 처리 후 가비지 컬렉션
        gc.collect()
        logger.info(f"Processed {i + len(chunk)}/{len(stock_data_list)} stocks")

    logger.info(
        f"Batch sync completed: {results['success']} success, "
        f"{results['failed']} failed, {results['skipped']} skipped"
    )

    return results


@shared_task
def invalidate_graph_cache(symbol: str):
    """
    그래프 캐시 무효화

    Args:
        symbol: 종목 심볼

    Note:
        - Stock 모델 업데이트 시 자동 호출
        - 캐시 무효화 실패해도 에러 발생 안 함
    """
    from .services.cache import get_cache_service

    cache_service = get_cache_service()

    try:
        success = cache_service.invalidate_graph(symbol)
        if success:
            logger.info(f"Invalidated graph cache for {symbol}")
        else:
            logger.warning(f"Failed to invalidate graph cache for {symbol}")
        return {'status': 'success' if success else 'failed', 'symbol': symbol}

    except Exception as e:
        logger.error(f"Error invalidating graph cache for {symbol}: {e}")
        return {'status': 'error', 'symbol': symbol, 'error': str(e)}


@shared_task
def health_check_neo4j():
    """
    Neo4j 헬스체크 태스크

    Returns:
        {
            'status': 'healthy' | 'degraded' | 'unavailable',
            'connected': bool,
            'node_count': int | None,
            'relationship_count': int | None,
            'error': None | str
        }

    Note:
        - Celery Beat로 주기적 실행 (예: 5분마다)
        - 연결 상태 모니터링
    """
    neo4j_service = get_neo4j_service()

    try:
        health = neo4j_service.health_check()
        logger.info(f"Neo4j health check: {health['status']}")
        return health

    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return {
            'status': 'error',
            'connected': False,
            'error': str(e)
        }


# ============================================================
# Semantic Cache 태스크
# ============================================================

@shared_task
def cleanup_expired_semantic_cache():
    """
    만료된 시맨틱 캐시 정리

    Returns:
        {
            'status': 'success' | 'skipped' | 'error',
            'deleted_count': int,
            'error': None | str
        }

    Note:
        - Celery Beat로 매일 새벽 4시 실행
        - TTL(7일) 지난 캐시 노드 삭제
        - Neo4j 연결 실패 시 skipped 반환
    """
    try:
        from .services.semantic_cache_setup import cleanup_expired_cache

        deleted_count = cleanup_expired_cache()

        logger.info(f"Semantic cache cleanup: {deleted_count} entries deleted")
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'error': None
        }

    except ImportError as e:
        logger.warning(f"Semantic cache not available: {e}")
        return {
            'status': 'skipped',
            'deleted_count': 0,
            'error': 'semantic_cache_not_available'
        }

    except Exception as e:
        logger.error(f"Semantic cache cleanup failed: {e}")
        return {
            'status': 'error',
            'deleted_count': 0,
            'error': str(e)
        }


@shared_task
def warm_semantic_cache(limit: int = 50):
    """
    시맨틱 캐시 워밍 (자주 묻는 질문 사전 캐싱)

    Args:
        limit: 최대 워밍 수 (기본값: 50)

    Returns:
        {
            'status': 'success' | 'skipped' | 'error',
            'warmed_count': int,
            'failed_count': int,
            'skipped_count': int,
            'duration_seconds': float,
            'error': None | str
        }

    Note:
        - Celery Beat로 주 1회 실행 (일요일 새벽)
        - 인기 종목 × 자주 묻는 질문 조합으로 사전 캐싱
    """
    import asyncio

    try:
        from .services.cache_warmer import CacheWarmer

        warmer = CacheWarmer()

        # asyncio 이벤트 루프 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(warmer.warm_cache(limit=limit))
        finally:
            loop.close()

        logger.info(
            f"Semantic cache warming: {result.get('warmed_count', 0)} warmed, "
            f"{result.get('failed_count', 0)} failed"
        )

        return {
            'status': 'success',
            **result,
            'error': None
        }

    except ImportError as e:
        logger.warning(f"Cache warmer not available: {e}")
        return {
            'status': 'skipped',
            'warmed_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'duration_seconds': 0,
            'error': 'cache_warmer_not_available'
        }

    except Exception as e:
        logger.error(f"Semantic cache warming failed: {e}")
        return {
            'status': 'error',
            'warmed_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'duration_seconds': 0,
            'error': str(e)
        }


@shared_task
def invalidate_semantic_cache_for_symbol(symbol: str):
    """
    특정 종목의 시맨틱 캐시 무효화

    Args:
        symbol: 종목 심볼 (예: 'AAPL')

    Returns:
        {
            'status': 'success' | 'skipped' | 'error',
            'symbol': str,
            'deleted_count': int,
            'error': None | str
        }

    Note:
        - 종목 데이터 업데이트 시 호출
        - 실적 발표, 가격 급변 등 중요 이벤트 시 사용
    """
    import asyncio

    try:
        from .services.semantic_cache import get_semantic_cache

        cache = get_semantic_cache()

        # asyncio 이벤트 루프 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            deleted_count = loop.run_until_complete(
                cache.invalidate(symbol=symbol.upper())
            )
        finally:
            loop.close()

        if deleted_count > 0:
            logger.info(f"Invalidated {deleted_count} cache entries for {symbol}")
        else:
            logger.debug(f"No cache entries found for {symbol}")

        return {
            'status': 'success',
            'symbol': symbol.upper(),
            'deleted_count': deleted_count,
            'error': None
        }

    except ImportError as e:
        logger.warning(f"Semantic cache not available: {e}")
        return {
            'status': 'skipped',
            'symbol': symbol.upper(),
            'deleted_count': 0,
            'error': 'semantic_cache_not_available'
        }

    except Exception as e:
        logger.error(f"Semantic cache invalidation failed for {symbol}: {e}")
        return {
            'status': 'error',
            'symbol': symbol.upper(),
            'deleted_count': 0,
            'error': str(e)
        }


@shared_task
def get_semantic_cache_stats():
    """
    시맨틱 캐시 통계 조회

    Returns:
        {
            'status': 'available' | 'unavailable' | 'error',
            'total_entries': int,
            'active_entries': int,
            'expired_entries': int,
            'avg_hit_count': float,
            'error': None | str
        }

    Note:
        - 모니터링 대시보드용
        - 캐시 효율성 측정
    """
    try:
        from .services.semantic_cache_setup import get_cache_stats

        stats = get_cache_stats()
        logger.debug(f"Semantic cache stats: {stats}")
        return stats

    except ImportError as e:
        logger.warning(f"Semantic cache not available: {e}")
        return {
            'status': 'unavailable',
            'error': 'semantic_cache_not_available'
        }

    except Exception as e:
        logger.error(f"Failed to get semantic cache stats: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
