"""
Chain Sight Neo4j Dirty Sync — PR-3

neo4j_dirty=True인 RelationConfidence를 Neo4j에 동기화.
confirmed/probable → 엣지 upsert, hidden/weak/stale → 엣지 삭제.
"""

import logging

from django.utils import timezone

from chainsight.graph import get_graph_repository
from chainsight.models import RelationConfidence
from chainsight.utils import normalize_pair

logger = logging.getLogger(__name__)

# undirected 관계는 정규화된 방향(symbol_a < symbol_b)만 저장
UNDIRECTED_TYPES = {"PEER_OF", "COMPETES_WITH", "CO_MENTIONED", "PRICE_CORRELATED"}


def sync_dirty_relations() -> int:
    """neo4j_dirty=True인 RelationConfidence를 Neo4j에 동기화."""
    dirty_qs = RelationConfidence.objects.filter(neo4j_dirty=True)
    count = dirty_qs.count()
    if count == 0:
        logger.info("No dirty relations to sync")
        return 0

    repo = get_graph_repository()
    synced_pks = []

    for rc in dirty_qs.iterator(chunk_size=100):
        try:
            if rc.relation_status in ("confirmed", "probable"):
                _upsert_edge(repo, rc)
            elif rc.relation_category == "market" and rc.relation_status == "weak":
                # market 관계(CO_MENTIONED, PRICE_CORRELATED)는 weak도 동기화
                _upsert_edge(repo, rc)
            else:
                _delete_edge(repo, rc)
            synced_pks.append(rc.pk)
        except Exception as e:
            logger.error(f"Failed to sync relation {rc.pk}: {e}")

    # queryset.update() 사용 — save() 호출 금지 (dirty가 다시 True로 덮어씌워짐)
    # audit P0 #9: synced_to_neo4j 제거, neo4j_dirty 단일 소스
    if synced_pks:
        RelationConfidence.objects.filter(pk__in=synced_pks).update(
            neo4j_dirty=False,
            neo4j_synced_at=timezone.now(),
        )

    logger.info(
        f"Neo4j dirty sync complete: {len(synced_pks)}/{count} relations synced"
    )
    return len(synced_pks)


def _upsert_edge(repo, rc: RelationConfidence):
    """Neo4j에 관계 엣지 upsert."""
    # undirected 관계는 정규화 방향으로만 저장
    if rc.relation_type in UNDIRECTED_TYPES:
        sym_a, sym_b = normalize_pair(rc.symbol_a, rc.symbol_b)
    else:
        sym_a, sym_b = rc.symbol_a, rc.symbol_b

    props = {
        "truth_score": rc.truth_score,
        "status": rc.relation_status,
        "evidence_tier_best": rc.evidence_tier_best,
        "relation_category": rc.relation_category,
    }
    if rc.market_score is not None:
        props["market_score"] = rc.market_score

    repo.upsert_edge(sym_a, sym_b, rc.relation_type, props)


def _delete_edge(repo, rc: RelationConfidence):
    """Neo4j에서 관계 엣지 삭제."""
    if rc.relation_type in UNDIRECTED_TYPES:
        sym_a, sym_b = normalize_pair(rc.symbol_a, rc.symbol_b)
    else:
        sym_a, sym_b = rc.symbol_a, rc.symbol_b

    try:
        repo.run_query(
            """
            MATCH (a:Stock {ticker: $symbol_a})-[r]->(b:Stock {ticker: $symbol_b})
            WHERE type(r) = $rel_type
            DELETE r
        """,
            {"symbol_a": sym_a, "symbol_b": sym_b, "rel_type": rc.relation_type},
        )
    except Exception as e:
        logger.warning(f"Edge delete failed {sym_a}->{sym_b} [{rc.relation_type}]: {e}")
