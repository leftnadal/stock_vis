"""PG 네이티브 ego 그래프 API 테스트 (⑰ S1-b).

시드 = RelationConfidence + RelationPairSnapshot + Stock 직접(theme_tags 무사용).
양방향 조회·limit 절단·궤적 join·빈 이웃·404 커버.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.chain_sight.models import RelationConfidence, RelationPairSnapshot
from apps.chain_sight.utils import normalize_pair
from packages.shared.stocks.models import Stock


def _stock(sym, sector="Technology"):
    return Stock.objects.create(symbol=sym, stock_name=f"{sym} Inc.", sector=sector)


def _rc(a, b, rtype="PEER_OF", truth=50.0, category="truth"):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype,
        relation_category=category, truth_score=truth,
    )


def _rps(a, b, period, truth_max):
    ca, cb = normalize_pair(a, b)
    return RelationPairSnapshot.objects.create(
        canonical_a=ca, canonical_b=cb, period=period,
        truth_max=truth_max, market_max=0.0,
        relevance_opp=0.0, relevance_risk=0.0,
    )


@pytest.fixture
def ego_data(db):
    for s in ["AAA", "BBB", "CCC", "DDD", "LONE"]:
        _stock(s)
    # AAA 중심: 양방향(AAA=symbol_a 2건 + AAA=symbol_b 1건)
    _rc("AAA", "BBB", "PEER_OF", 80.0)
    _rc("AAA", "CCC", "SUPPLIES_TO", 40.0, category="truth")
    _rc("DDD", "AAA", "COMPETES_WITH", 60.0)  # AAA가 symbol_b
    # 궤적: AAA-BBB 상승(3점)
    base = date(2026, 7, 1)
    for i, v in enumerate([50.0, 65.0, 80.0]):
        _rps("AAA", "BBB", base + timedelta(days=i), v)
    return None


@pytest.fixture
def auth_client(db, django_user_model):
    from rest_framework.test import APIClient
    u = django_user_model.objects.create_user(username="ego_u", password="x")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


class TestEgoGraphAPI:
    def test_bidirectional_1hop(self, ego_data, auth_client):
        """AAA가 symbol_a/symbol_b 어느 쪽이든 이웃으로 잡힌다."""
        resp = auth_client.get("/api/v1/chainsight/ego/AAA/")
        assert resp.status_code == 200
        d = resp.json()
        assert d["center"]["symbol"] == "AAA"
        targets = {e["target"] for e in d["edges"]}
        assert targets == {"BBB", "CCC", "DDD"}  # DDD=symbol_b 방향도 포함
        assert d["meta"]["total_edges"] == 3
        # source는 항상 center
        assert all(e["source"] == "AAA" for e in d["edges"])

    def test_sorted_by_truth_desc(self, ego_data, auth_client):
        resp = auth_client.get("/api/v1/chainsight/ego/AAA/")
        scores = [e["truth_score"] for e in resp.json()["edges"]]
        assert scores == sorted(scores, reverse=True)  # 80,60,40

    def test_min_score_filter(self, ego_data, auth_client):
        resp = auth_client.get("/api/v1/chainsight/ego/AAA/?min_score=50")
        d = resp.json()
        assert d["meta"]["total_edges"] == 2  # 80,60만
        assert all(e["truth_score"] >= 50 for e in d["edges"])

    def test_types_filter(self, ego_data, auth_client):
        resp = auth_client.get("/api/v1/chainsight/ego/AAA/?types=PEER_OF")
        d = resp.json()
        assert d["meta"]["total_edges"] == 1
        assert d["edges"][0]["relation_type"] == "PEER_OF"

    def test_limit_truncation(self, ego_data, auth_client):
        resp = auth_client.get("/api/v1/chainsight/ego/AAA/?limit=1")
        d = resp.json()
        assert d["meta"]["total_edges"] == 3  # 전체 카운트는 보존
        assert d["meta"]["returned"] == 1      # 절단
        assert d["edges"][0]["truth_score"] == 80.0  # 상위 1건

    def test_trajectory_join(self, ego_data, auth_client):
        """AAA-BBB 궤적(50→80 상승)이 trend에 실린다. N+1 없이."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as ctx:
            resp = auth_client.get("/api/v1/chainsight/ego/AAA/")
        bbb = next(e for e in resp.json()["edges"] if e["target"] == "BBB")
        assert bbb["trend"]["direction"] == "up"
        assert bbb["trend"]["delta"] == 30.0  # 80-50
        assert len(bbb["trend"]["points"]) == 3
        # N+1 방어: 쿼리 수가 이웃 수에 비례하지 않음(상수급)
        assert len(ctx.captured_queries) <= 8

    def test_empty_neighbors(self, ego_data, auth_client):
        """무관계 심볼 → 빈 엣지, 200."""
        resp = auth_client.get("/api/v1/chainsight/ego/LONE/")
        assert resp.status_code == 200
        d = resp.json()
        assert d["edges"] == []
        assert d["meta"]["total_edges"] == 0
        assert d["nodes"] == [{
            "symbol": "LONE", "name": "LONE Inc.", "sector": "Technology",
            "pagerank_rank": None, "betweenness_rank": None,  # ⑲ S3 additive, 스냅샷 부재 시 null
        }]

    def test_unknown_symbol_404(self, ego_data, auth_client):
        resp = auth_client.get("/api/v1/chainsight/ego/NOPE/")
        assert resp.status_code == 404


@pytest.fixture
def ego_cross_data(ego_data):
    """ego_data(AAA 이웃 BBB/CCC/DDD) 위에 이웃끼리의 cross 엣지 BBB↔CCC 추가."""
    _rc("BBB", "CCC", "PEER_OF", 70.0)
    return None


class TestEgoCrossEdges:
    """S2 (⑲ D②): include_cross_edges — 기본 false 바이트 불변 + true 정확성."""

    def test_default_false_is_additive(self, ego_cross_data, auth_client):
        """기본(파라미터 없음): cross_edges 키·meta.cross_edges_count 부재 = 응답 바이트 불변."""
        resp = auth_client.get("/api/v1/chainsight/ego/AAA/")
        d = resp.json()
        assert set(d.keys()) == {"center", "nodes", "edges", "meta"}
        assert "cross_edges" not in d
        assert set(d["meta"].keys()) == {"total_edges", "returned", "filtered_by"}
        assert "cross_edges_count" not in d["meta"]
        # 중심 엣지는 이웃끼리 링크(BBB-CCC)를 포함하지 않는다(center=AAA source만)
        assert all(e["source"] == "AAA" for e in d["edges"])

    def test_explicit_false_same_as_default(self, ego_cross_data, auth_client):
        base = auth_client.get("/api/v1/chainsight/ego/AAA/").json()
        off = auth_client.get(
            "/api/v1/chainsight/ego/AAA/?include_cross_edges=false"
        ).json()
        assert base == off

    def test_true_returns_cross_edges(self, ego_cross_data, auth_client):
        """true: 이웃 BBB↔CCC 사이 RC 엣지가 동일 스키마로 cross_edges에 실린다."""
        resp = auth_client.get(
            "/api/v1/chainsight/ego/AAA/?include_cross_edges=true"
        )
        d = resp.json()
        assert d["meta"]["cross_edges_count"] == 1
        ce = d["cross_edges"][0]
        assert {ce["source"], ce["target"]} == {"BBB", "CCC"}
        assert ce["relation_type"] == "PEER_OF"
        assert ce["truth_score"] == 70.0
        assert set(ce.keys()) == {"source", "target", "relation_type", "truth_score", "trend"}
        # 중심 엣지(edges)에는 여전히 cross가 섞이지 않는다
        assert all(e["source"] == "AAA" for e in d["edges"])
        assert d["meta"]["returned"] == len(d["edges"]) == 3

    def test_true_empty_when_no_neighbor_links(self, ego_data, auth_client):
        """이웃끼리 엣지가 없으면(ego_data만) cross_edges=[]."""
        resp = auth_client.get(
            "/api/v1/chainsight/ego/AAA/?include_cross_edges=true"
        )
        d = resp.json()
        assert d["cross_edges"] == []
        assert d["meta"]["cross_edges_count"] == 0

    def test_cross_edges_use_post_limit_neighbor_set(self, ego_cross_data, auth_client):
        """limit=1 → 이웃 {BBB}뿐 → cross(BBB-CCC) 성립 불가 → 빈 리스트(절단 후 집합 기준)."""
        resp = auth_client.get(
            "/api/v1/chainsight/ego/AAA/?include_cross_edges=true&limit=1"
        )
        d = resp.json()
        assert d["meta"]["returned"] == 1
        assert d["cross_edges"] == []

    def test_cross_edges_no_nplus1(self, ego_cross_data, auth_client):
        """cross 조회는 단일 양방향 쿼리 — 쿼리 수 상수급 유지."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            auth_client.get("/api/v1/chainsight/ego/AAA/?include_cross_edges=true")
        assert len(ctx.captured_queries) <= 9
