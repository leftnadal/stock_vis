"""
Chain Sight Neo4j Dirty Sync Celery Task — PR-3
"""

import logging

from celery import shared_task

from chainsight.services.neo4j_sync import sync_dirty_relations

logger = logging.getLogger(__name__)


@shared_task(name="chainsight-neo4j-dirty-sync", max_retries=2, default_retry_delay=60)
def run_neo4j_dirty_sync():
    """neo4j_dirty=True 레코드를 Neo4j에 동기화."""
    count = sync_dirty_relations()
    logger.info(f"Neo4j dirty sync task complete: {count} relations synced")
    return count
