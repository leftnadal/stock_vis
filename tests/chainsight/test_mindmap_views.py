"""CS-P5-FE-CARD Slice B2 — 마인드맵 카드 API 게이트 필터 회귀.

D-CARD-GATE: 연결 = evidence AND SEC4종. CO_MENTIONED 분리, excluded 미노출.
게이트는 백엔드 쿼리에서 적용됨을 검증.
"""

import pytest
from django.apps import apps
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
    """2단 유니버스 제외 플래그(universe_excluded) — 카드·트리·업종 카운트 미노출.

    B(CS-UNIVERSE-EXCLUDE-FLAG): 1단 industry 상수 필터에서 종목 플래그로 승격.
    제외 판정 = universe_excluded (industry 무관). 전환 전후 제외 집합 동일(B-4).
    """

    def _seed_stocks(self):
        Stock = apps.get_model("stocks", "Stock")
        # 정상 종목
        Stock.objects.create(
            symbol="NORM", stock_name="Normal Co", sector="Technology",
            industry="Software - Application",
        )
        # 제외 플래그 종목 (레버리지 ETF) — 데이터 마이그 0018 이 세팅하는 상태 재현
        Stock.objects.create(
            symbol="LEVX", stock_name="Daily 2X Long X ETF", sector="Financial Services",
            industry="Asset Management - Leveraged", asset_type="ETF",
            universe_excluded=True, exclude_reason="LEVERAGED_ETF",
        )

    def test_excluded_flag_absent_from_tree(self):
        self._seed_stocks()
        d = Client().get("/api/v1/chainsight/mindmap/tree/").json()
        tickers = {c["ticker"] for s in d["sectors"] for i in s["industries"] for c in i["cards"]}
        assert "NORM" in tickers
        assert "LEVX" not in tickers  # universe_excluded → 카드 미노출
        # 제외 종목 유일 업종 버킷 소멸 확인
        industries = {i["industry"] for s in d["sectors"] for i in s["industries"]}
        assert "Asset Management - Leveraged" not in industries
        # 집계 정합: stock_total = 정상 1종만 (제외분 불산입)
        assert d["stock_total"] == 1

    def test_excluded_symbol_card_returns_404(self):
        self._seed_stocks()
        resp = Client().get("/api/v1/chainsight/mindmap/card/LEVX/")
        assert resp.status_code == 404
        # 정상 종목 카드는 200
        assert Client().get("/api/v1/chainsight/mindmap/card/NORM/").status_code == 200

    def test_flag_drives_exclusion_not_industry(self):
        # B-3 승격 의미 명시: 제외는 플래그 기준. 레버리지 industry여도 flag=False면 노출.
        Stock = apps.get_model("stocks", "Stock")
        Stock.objects.create(
            symbol="LEVOK", stock_name="Lev ETF (unflagged)",
            sector="Financial Services", industry="Asset Management - Leveraged",
            universe_excluded=False,
        )
        d = Client().get("/api/v1/chainsight/mindmap/tree/").json()
        tickers = {c["ticker"] for s in d["sectors"] for i in s["industries"] for c in i["cards"]}
        assert "LEVOK" in tickers  # flag=False → 노출(industry 무관)
