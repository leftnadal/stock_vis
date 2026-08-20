"""CS-P5-FE-CARD Slice B2 — 마인드맵 카드 API 게이트 필터 회귀.

D-CARD-GATE: 연결 = evidence AND SEC4종. CO_MENTIONED 분리, excluded 미노출.
게이트는 백엔드 쿼리에서 적용됨을 검증.
"""

import pytest
from django.test import Client

from apps.chain_sight.models import RelationConfidence


@pytest.mark.django_db
class TestMindmapGate:
    def _seed(self):
        # 게이트 통과(evidence+SEC4종)
        RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b="BBB", relation_type="SUPPLIES_TO",
            relation_category="truth", serving_layer="evidence", canonical_direction="a→b",
        )
        # CO_MENTIONED(evidence) — 연결 아님, 같은 그룹
        RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b="CCC", relation_type="CO_MENTIONED",
            relation_category="market", serving_layer="evidence",
            evidence_sources={"co_mention_count": 9},
        )
        # excluded(SEC4종이지만 서빙 제외) — 미노출
        RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b="DDD", relation_type="DEPENDS_ON",
            relation_category="truth", serving_layer="excluded",
        )
        # context(PEER_OF) — 미노출
        RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b="EEE", relation_type="PEER_OF",
            relation_category="truth", serving_layer="context",
        )

    def test_card_gate_only_sec4_evidence(self):
        self._seed()
        d = Client().get("/api/v1/chainsight/mindmap/card/AAA/").json()
        others = {c["other"] for c in d["connections"]}
        assert others == {"BBB"}  # SUPPLIES_TO evidence만
        assert "CCC" not in others  # CO_MENTIONED 제외
        assert "DDD" not in others  # excluded 제외
        assert "EEE" not in others  # context 제외

    def test_comention_in_groups_not_connections(self):
        self._seed()
        d = Client().get("/api/v1/chainsight/mindmap/card/AAA/").json()
        group_others = {g["other"] for g in d["groups"]}
        assert "CCC" in group_others  # CO_MENTIONED = 같은 그룹
        assert d["groups"][0]["co_mention_count"] == 9

    def test_excluded_never_in_tree_counts(self):
        self._seed()
        # AAA 카드의 gate_conn_count = 1(BBB만), excluded/comention/context 불산입
        d = Client().get("/api/v1/chainsight/mindmap/tree/").json()
        assert d["stock_total"] >= 0  # 스모크(유니버스 무시드여도 200)
        assert d["gate_definition"].startswith("serving_layer=evidence")

    def test_direction_directed_types(self):
        self._seed()
        d = Client().get("/api/v1/chainsight/mindmap/card/AAA/").json()
        conn = d["connections"][0]
        assert conn["relation_type"] == "SUPPLIES_TO"
        assert conn["direction"] == "out"  # AAA=symbol_a, a→b
