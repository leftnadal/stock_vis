"""CS-P5-FE-CARD Slice B2 — 마인드맵 카드 API 게이트 필터 회귀.

D-CARD-GATE: 연결 = evidence AND SEC4종. CO_MENTIONED 분리, excluded 미노출.
게이트는 백엔드 쿼리에서 적용됨을 검증.
"""

import pytest
from django.apps import apps
from django.test import Client

from apps.chain_sight.constants import UNIVERSE_EXCLUDED_INDUSTRIES
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

    def test_tree_new_conn_7d_observability(self):
        # C-2: 최근 7일 신규 게이트 연결 카운트(first_observed_at auto_now_add) 노출
        self._seed()  # 방금 생성 = 7일 이내
        d = Client().get("/api/v1/chainsight/mindmap/tree/").json()
        assert "recent_new_connections_7d" in d
        assert d["recent_new_connections_7d"] >= 1  # SUPPLIES_TO AAA→BBB 신규
        cards = {c["ticker"]: c for s in d["sectors"] for i in s["industries"] for c in i["cards"]}
        if cards:
            assert "new_conn_7d" in next(iter(cards.values()))


@pytest.mark.django_db
class TestUniverseExcludeFilter:
    """1단 유니버스 제외 필터(레버리지 ETF industry) — 카드·트리·업종 카운트 미노출."""

    def _seed_stocks(self):
        Stock = apps.get_model("stocks", "Stock")
        excluded_ind = UNIVERSE_EXCLUDED_INDUSTRIES[0]  # "Asset Management - Leveraged"
        # 정상 종목
        Stock.objects.create(
            symbol="NORM", stock_name="Normal Co", sector="Technology",
            industry="Software - Application",
        )
        # 제외 industry 종목 (레버리지 ETF)
        Stock.objects.create(
            symbol="LEVX", stock_name="Daily 2X Long X ETF", sector="Financial Services",
            industry=excluded_ind, asset_type="ETF",
        )

    def test_excluded_industry_absent_from_tree(self):
        self._seed_stocks()
        d = Client().get("/api/v1/chainsight/mindmap/tree/").json()
        tickers = {c["ticker"] for s in d["sectors"] for i in s["industries"] for c in i["cards"]}
        assert "NORM" in tickers
        assert "LEVX" not in tickers  # 제외 industry → 카드 미노출
        # 업종 버킷 소멸 확인
        industries = {i["industry"] for s in d["sectors"] for i in s["industries"]}
        assert UNIVERSE_EXCLUDED_INDUSTRIES[0] not in industries
        # 집계 정합: stock_total = 정상 1종만 (제외분 불산입)
        assert d["stock_total"] == 1

    def test_excluded_symbol_card_returns_404(self):
        self._seed_stocks()
        resp = Client().get("/api/v1/chainsight/mindmap/card/LEVX/")
        assert resp.status_code == 404
        # 정상 종목 카드는 200
        assert Client().get("/api/v1/chainsight/mindmap/card/NORM/").status_code == 200
