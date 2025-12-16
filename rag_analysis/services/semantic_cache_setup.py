"""
Semantic Cache Setup - Neo4j 벡터 인덱스 설정

질문 임베딩을 저장할 Neo4j 벡터 인덱스를 생성합니다.
"""

import logging
from django.conf import settings
from .neo4j_driver import get_neo4j_driver

logger = logging.getLogger(__name__)


def setup_semantic_cache_index() -> bool:
    """
    Neo4j 벡터 인덱스 설정

    Creates:
        - AnalysisCache 노드용 벡터 인덱스 (384차원, cosine similarity)
        - 만료일 인덱스 (TTL 관리용)

    Returns:
        bool: 성공 여부
    """
    driver = get_neo4j_driver()

    if driver is None:
        logger.error("Neo4j driver not available. Cannot setup semantic cache.")
        return False

    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # 1. 벡터 인덱스 생성 (384차원 - MiniLM-L6-v2)
            session.run("""
                CREATE VECTOR INDEX analysis_question_embedding IF NOT EXISTS
                FOR (c:AnalysisCache)
                ON c.question_embedding
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 384,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """)
            logger.info("Vector index 'analysis_question_embedding' created/verified")

            # 2. 만료일 인덱스 생성 (TTL 쿼리 최적화)
            session.run("""
                CREATE INDEX analysis_cache_expires IF NOT EXISTS
                FOR (c:AnalysisCache)
                ON (c.expires_at)
            """)
            logger.info("Expiry index 'analysis_cache_expires' created/verified")

            # 3. 사용자 ID 인덱스 (선택적 사용자별 캐시)
            session.run("""
                CREATE INDEX analysis_cache_user IF NOT EXISTS
                FOR (c:AnalysisCache)
                ON (c.user_id)
            """)
            logger.info("User index 'analysis_cache_user' created/verified")

            # 4. 캐시 ID 유일성 제약
            session.run("""
                CREATE CONSTRAINT analysis_cache_id IF NOT EXISTS
                FOR (c:AnalysisCache)
                REQUIRE c.cache_id IS UNIQUE
            """)
            logger.info("Unique constraint 'analysis_cache_id' created/verified")

            return True

    except Exception as e:
        logger.error(f"Failed to setup semantic cache index: {e}")
        return False


def cleanup_expired_cache() -> int:
    """
    만료된 캐시 노드 삭제

    Returns:
        int: 삭제된 노드 수
    """
    driver = get_neo4j_driver()

    if driver is None:
        logger.warning("Neo4j driver not available. Cannot cleanup cache.")
        return 0

    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (c:AnalysisCache)
                WHERE c.expires_at < datetime()
                WITH c LIMIT 1000
                DETACH DELETE c
                RETURN count(*) as deleted_count
            """)

            record = result.single()
            deleted_count = record['deleted_count'] if record else 0

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired cache entries")

            return deleted_count

    except Exception as e:
        logger.error(f"Failed to cleanup expired cache: {e}")
        return 0


def get_cache_stats() -> dict:
    """
    캐시 통계 조회

    Returns:
        dict: {
            'total_entries': int,
            'active_entries': int,
            'expired_entries': int,
            'avg_similarity_score': float,
            'hit_rate_24h': float
        }
    """
    driver = get_neo4j_driver()

    if driver is None:
        return {
            'status': 'unavailable',
            'total_entries': 0,
            'active_entries': 0,
            'expired_entries': 0
        }

    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (c:AnalysisCache)
                WITH
                    count(c) as total,
                    sum(CASE WHEN c.expires_at > datetime() THEN 1 ELSE 0 END) as active,
                    sum(CASE WHEN c.expires_at <= datetime() THEN 1 ELSE 0 END) as expired,
                    avg(c.hit_count) as avg_hits
                RETURN total, active, expired, avg_hits
            """)

            record = result.single()

            if record:
                return {
                    'status': 'available',
                    'total_entries': record['total'] or 0,
                    'active_entries': record['active'] or 0,
                    'expired_entries': record['expired'] or 0,
                    'avg_hit_count': record['avg_hits'] or 0
                }

            return {
                'status': 'available',
                'total_entries': 0,
                'active_entries': 0,
                'expired_entries': 0,
                'avg_hit_count': 0
            }

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def drop_semantic_cache_index() -> bool:
    """
    시맨틱 캐시 인덱스 삭제 (테스트용)

    Returns:
        bool: 성공 여부
    """
    driver = get_neo4j_driver()

    if driver is None:
        return False

    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # 인덱스 삭제
            session.run("DROP INDEX analysis_question_embedding IF EXISTS")
            session.run("DROP INDEX analysis_cache_expires IF EXISTS")
            session.run("DROP INDEX analysis_cache_user IF EXISTS")
            session.run("DROP CONSTRAINT analysis_cache_id IF EXISTS")

            # 모든 캐시 노드 삭제
            session.run("MATCH (c:AnalysisCache) DETACH DELETE c")

            logger.info("Semantic cache index dropped")
            return True

    except Exception as e:
        logger.error(f"Failed to drop semantic cache index: {e}")
        return False
