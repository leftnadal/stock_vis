"""
Chain Sight Peer 수집 + Neo4j 로드 Celery 태스크.

사용법:
  fetch_and_load_peers.delay()               # Finnhub만
  fetch_and_load_peers.delay(use_fmp=True)   # Finnhub + FMP
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=3600,
    time_limit=3660,
)
def fetch_and_load_peers(self, use_fmp: bool = False):
    """전체 Peer 수집 + Neo4j 로드."""
    from apps.chain_sight.graph import get_graph_repository
    from apps.chain_sight.services import collect_all_peers, load_peers_to_neo4j

    repo = get_graph_repository()
    symbols = [
        r["ticker"]
        for r in repo.run_query(
            "MATCH (s:Stock) RETURN s.ticker AS ticker ORDER BY ticker"
        )
    ]
    logger.info(f"Peer 수집 대상: {len(symbols)}개 (use_fmp={use_fmp})")

    if not symbols:
        return {"error": "No stocks in Neo4j"}

    collection = collect_all_peers(symbols, use_fmp=use_fmp)
    load_result = load_peers_to_neo4j(collection["pairs"])

    logger.info(f"Peer 수집 완료: {collection['stats']}")
    logger.info(f"Neo4j 로드 완료: {load_result}")

    return {"collection_stats": collection["stats"], "load_result": load_result}
