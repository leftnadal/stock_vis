"""
Neo4j Driver Singleton with Lazy Connection

Critical: Neo4j가 꺼져 있어도 Django가 죽지 않도록 lazy initialization 구현
"""

import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from django.conf import settings

logger = logging.getLogger(__name__)

# Global driver instance (초기화는 첫 사용 시)
_driver: Optional[Driver] = None
_connection_attempted = False


def get_neo4j_driver() -> Optional[Driver]:
    """
    Neo4j driver를 반환 (Lazy Singleton)

    Returns:
        Driver instance or None if connection failed

    Note:
        - 첫 호출 시 연결 시도
        - 연결 실패 시 None 반환 (앱은 계속 실행)
        - 이후 호출 시 캐시된 driver 반환
    """
    global _driver, _connection_attempted

    if _driver is not None:
        return _driver

    if _connection_attempted:
        # 이미 연결 시도했으나 실패한 경우
        return None

    _connection_attempted = True

    try:
        uri = settings.NEO4J_URI
        username = settings.NEO4J_USERNAME
        password = settings.NEO4J_PASSWORD

        logger.info(f"Attempting Neo4j connection to {uri}")

        _driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            max_connection_lifetime=settings.NEO4J_CONNECTION_POOL.get('max_connection_lifetime', 3600),
            max_connection_pool_size=settings.NEO4J_CONNECTION_POOL.get('max_connection_pool_size', 50),
            connection_acquisition_timeout=settings.NEO4J_CONNECTION_POOL.get('connection_acquisition_timeout', 60),
        )

        # 연결 확인
        _driver.verify_connectivity()
        logger.info("Neo4j connection established successfully")

        return _driver

    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        logger.warning("Application will continue without Neo4j graph features")
        _driver = None
        return None


def close_neo4j_driver():
    """
    Neo4j driver 연결 종료

    Note:
        - Django shutdown 시 호출됨 (AppConfig.ready)
    """
    global _driver
    if _driver is not None:
        try:
            _driver.close()
            logger.info("Neo4j driver closed successfully")
        except Exception as e:
            logger.error(f"Error closing Neo4j driver: {e}")
        finally:
            _driver = None


def reset_connection():
    """
    연결 재시도를 위한 상태 리셋

    Note:
        - 테스트 또는 수동 재연결 시 사용
    """
    global _driver, _connection_attempted
    close_neo4j_driver()
    _connection_attempted = False
    logger.info("Neo4j connection state reset")
