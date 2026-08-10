"""CS-P1A Slice1: update_relation_confidence 재조립 회귀.

P2-1 회귀 방지: Neo4j 미의존 완주 + co_mention 착지 + price/peer 은퇴 + 기존 무접촉.
"""
import pytest

from apps.chain_sight.models import CoMentionEdge, RelationConfidence
from apps.chain_sight.tasks.relation_tasks import update_relation_confidence


@pytest.mark.django_db
def test_co_mention_lands_without_neo4j():
    # get_graph_repository mock 없이 호출 = Neo4j 미의존 입증(구 GraphQueryError 전체실패 회귀 방지)
    CoMentionEdge.objects.create(symbol_a="AAA", symbol_b="BBB", co_mention_count=12)
    CoMentionEdge.objects.create(symbol_a="CCC", symbol_b="DDD", co_mention_count=6)
    CoMentionEdge.objects.create(symbol_a="EEE", symbol_b="FFF", co_mention_count=3)
    CoMentionEdge.objects.create(symbol_a="GGG", symbol_b="HHH", co_mention_count=1)  # <2 미착지

    result = update_relation_confidence()

    com = RelationConfidence.objects.filter(relation_type="CO_MENTIONED")
    assert com.count() == 3
    assert result["created"] == 3
    # Slice2: 신규 CO_MENTIONED = evidence 계층
    assert set(com.values_list("serving_layer", flat=True)) == {"evidence"}
    # 임계 밴드 보존(count>=10 confirmed / >=5 probable / >=2 weak)
    assert com.get(symbol_a="AAA", symbol_b="BBB").relation_status == "confirmed"
    assert com.get(symbol_a="AAA", symbol_b="BBB").market_score == 85
    assert com.get(symbol_a="CCC", symbol_b="DDD").relation_status == "probable"
    assert com.get(symbol_a="EEE", symbol_b="FFF").relation_status == "weak"
    # count<2 미착지
    assert not RelationConfidence.objects.filter(symbol_a="GGG").exists()


@pytest.mark.django_db
def test_peer_and_price_landing_retired():
    # price/peer 착지 은퇴: co_mention만 생성, PEER_OF/PRICE_CORRELATED 신규 0
    CoMentionEdge.objects.create(symbol_a="AAA", symbol_b="BBB", co_mention_count=5)
    update_relation_confidence()
    assert RelationConfidence.objects.filter(relation_type="PEER_OF").count() == 0
    assert RelationConfidence.objects.filter(relation_type="PRICE_CORRELATED").count() == 0


@pytest.mark.django_db
def test_existing_records_untouched():
    # OUT 스코프: 기존 PEER_OF/PRICE 레코드 status·score 무접촉
    peer = RelationConfidence.objects.create(
        symbol_a="XXX", symbol_b="YYY", relation_type="PEER_OF",
        relation_status="stale", truth_score=85,
    )
    price = RelationConfidence.objects.create(
        symbol_a="XXX", symbol_b="ZZZ", relation_type="PRICE_CORRELATED",
        relation_status="confirmed", market_score=85,
    )
    CoMentionEdge.objects.create(symbol_a="AAA", symbol_b="BBB", co_mention_count=5)
    update_relation_confidence()
    peer.refresh_from_db()
    price.refresh_from_db()
    assert peer.relation_status == "stale"
    assert price.relation_status == "confirmed"


@pytest.mark.django_db
def test_existing_co_mention_updates_not_duplicates():
    # 재실행 시 기존 CO_MENTIONED 갱신(created 아님) — last_observed 갱신 경로 보존
    CoMentionEdge.objects.create(symbol_a="AAA", symbol_b="BBB", co_mention_count=5)
    update_relation_confidence()
    r2 = update_relation_confidence()
    assert r2["created"] == 0
    assert r2["updated"] == 1
    assert RelationConfidence.objects.filter(relation_type="CO_MENTIONED").count() == 1
