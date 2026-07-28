"""중심성 일간 배치 태스크 (⑲ S3, S-C).

RelationConfidence 그래프 → PageRank + betweenness → SymbolCentrality 일별 append.
Neo4j 불사용. 멱등(동일 as_of 재실행 = update_or_create 갱신, 중복 없음).
beat 등록은 DB-only(병진 수동, 이름 `chainsight-daily-centrality`) — dict 등록 금지(#28).
"""

import logging
import time

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, soft_time_limit=600, time_limit=660)
def compute_symbol_centrality(self, as_of=None):
    """RC 전량 중심성 → SymbolCentrality(as_of) 저장. as_of 미지정 시 오늘(UTC).

    Returns: {"as_of", "nodes", "edges", "saved", "elapsed_sec"}.
    """
    from apps.chain_sight.models import SymbolCentrality
    from apps.chain_sight.services.centrality import compute_centrality_from_db

    if as_of is None:
        as_of = timezone.now().date()

    t0 = time.time()
    rows, meta = compute_centrality_from_db()

    saved = 0
    for r in rows:
        SymbolCentrality.objects.update_or_create(
            symbol=r["symbol"],
            as_of=as_of,
            defaults={
                "pagerank": r["pagerank"],
                "betweenness": r["betweenness"],
                "pagerank_rank": r["pagerank_rank"],
                "betweenness_rank": r["betweenness_rank"],
                "graph_nodes": meta["graph_nodes"],
                "graph_edges": meta["graph_edges"],
            },
        )
        saved += 1

    elapsed = round(time.time() - t0, 2)
    if elapsed > 10:
        logger.warning(
            "compute_symbol_centrality 소요 %.2fs (>10s) — 그래프 규모 점검 필요 "
            "(⑱ 드라이런 baseline 3.92s)", elapsed
        )
    logger.info(
        "compute_symbol_centrality as_of=%s nodes=%d edges=%d saved=%d elapsed=%.2fs",
        as_of, meta["graph_nodes"], meta["graph_edges"], saved, elapsed
    )
    return {
        "as_of": str(as_of),
        "nodes": meta["graph_nodes"],
        "edges": meta["graph_edges"],
        "saved": saved,
        "elapsed_sec": elapsed,
    }
