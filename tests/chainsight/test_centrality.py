"""중심성 배치 테스트 (⑲ S3, S-C).

- 서비스 compute_centrality: ⑱ 드라이런 로직(collapse weight=max(truth,market),
  PageRank 가중 + betweenness 정확) 재현 — 구조적 대조.
- 태스크 멱등(동일 as_of 재실행 = 갱신, 중복 없음).
- 조회 API /centrality/top/.
- ego 노드 rank 필드(스냅샷 있을 때 채워짐).
"""

from datetime import date

import pytest

from apps.chain_sight.models import RelationConfidence, SymbolCentrality
from apps.chain_sight.services.centrality import (
    build_relation_graph,
    compute_centrality,
)
from packages.shared.stocks.models import Stock


# ── 서비스 단위 (DB 무접촉) ──────────────────────────────────

# 그래프: A-B, B-C, A-C(삼각형) + A-D(펜던트) + D-E. A=허브, D=브리지(E→나머지).
FIXTURE_EDGES = [
    ("A", "B", 80.0, None),
    ("B", "C", 60.0, None),
    ("A", "C", 50.0, None),
    ("A", "D", 40.0, None),
    ("D", "E", 30.0, None),
]


class TestCentralityService:
    def test_graph_shape(self):
        g = build_relation_graph(FIXTURE_EDGES)
        assert g.number_of_nodes() == 5
        assert g.number_of_edges() == 5

    def test_collapse_max_weight_truth_or_market(self):
        """같은 쌍의 truth 엣지 + market 엣지 → collapse weight = max(truth, market)."""
        edges = [("A", "B", 80.0, None), ("A", "B", 0.0, 90.0)]  # PEER + PRICE
        g = build_relation_graph(edges)
        assert g.number_of_edges() == 1
        assert g["A"]["B"]["weight"] == 90.0  # market_score가 더 큼

    def test_skip_self_loops(self):
        g = build_relation_graph([("A", "A", 50.0, None), ("A", "B", 40.0, None)])
        assert g.number_of_nodes() == 2
        assert g.number_of_edges() == 1

    def test_ranks_are_permutation(self):
        rows, meta = compute_centrality(FIXTURE_EDGES)
        assert meta == {"graph_nodes": 5, "graph_edges": 5}
        pr_ranks = sorted(r["pagerank_rank"] for r in rows)
        bt_ranks = sorted(r["betweenness_rank"] for r in rows)
        assert pr_ranks == [1, 2, 3, 4, 5]
        assert bt_ranks == [1, 2, 3, 4, 5]

    def test_hub_and_bridge(self):
        """A=최고 허브(PageRank 1위), 브리지 구조에서 A·D가 betweenness 상위."""
        rows, _ = compute_centrality(FIXTURE_EDGES)
        by = {r["symbol"]: r for r in rows}
        assert by["A"]["pagerank_rank"] == 1
        # A는 {B,C}↔{D,E}, D는 {A,B,C}↔E 사이 브리지 → betweenness 상위 2
        assert {by["A"]["betweenness_rank"], by["D"]["betweenness_rank"]} == {1, 2}
        # 펜던트 말단 E와 삼각형 잔여 B,C는 betweenness 0(경로 경유 없음)
        assert by["E"]["betweenness"] == 0.0
        assert by["B"]["betweenness"] == 0.0

    def test_empty_graph(self):
        rows, meta = compute_centrality([])
        assert rows == []
        assert meta == {"graph_nodes": 0, "graph_edges": 0}


# ── 태스크 (DB) ──────────────────────────────────────────────

def _rc(a, b, rtype="PEER_OF", truth=50.0, market=None, category="truth"):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype,
        relation_category=category, truth_score=truth, market_score=market,
    )


@pytest.fixture
def rc_graph(db):
    _rc("A", "B", truth=80.0)
    _rc("B", "C", truth=60.0)
    _rc("A", "C", truth=50.0)
    _rc("A", "D", truth=40.0)
    _rc("D", "E", truth=30.0)
    return None


class TestCentralityTask:
    def test_saves_all_nodes(self, rc_graph):
        from apps.chain_sight.tasks.centrality_tasks import compute_symbol_centrality
        res = compute_symbol_centrality(as_of=date(2026, 7, 16))
        assert res["nodes"] == 5
        assert res["edges"] == 5
        assert res["saved"] == 5
        assert SymbolCentrality.objects.filter(as_of=date(2026, 7, 16)).count() == 5
        a = SymbolCentrality.objects.get(symbol="A", as_of=date(2026, 7, 16))
        assert a.pagerank_rank == 1
        assert a.graph_nodes == 5 and a.graph_edges == 5

    def test_idempotent_same_as_of(self, rc_graph):
        from apps.chain_sight.tasks.centrality_tasks import compute_symbol_centrality
        compute_symbol_centrality(as_of=date(2026, 7, 16))
        compute_symbol_centrality(as_of=date(2026, 7, 16))  # 재실행
        assert SymbolCentrality.objects.filter(as_of=date(2026, 7, 16)).count() == 5

    def test_append_new_as_of(self, rc_graph):
        """다른 as_of = 궤적 append(덮어쓰기 아님)."""
        from apps.chain_sight.tasks.centrality_tasks import compute_symbol_centrality
        compute_symbol_centrality(as_of=date(2026, 7, 16))
        compute_symbol_centrality(as_of=date(2026, 7, 17))
        assert SymbolCentrality.objects.filter(symbol="A").count() == 2


# ── 조회 API ─────────────────────────────────────────────────

@pytest.fixture
def auth_client(db, django_user_model):
    from rest_framework.test import APIClient
    u = django_user_model.objects.create_user(username="cen_u", password="x")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def centrality_snapshot(rc_graph):
    from apps.chain_sight.tasks.centrality_tasks import compute_symbol_centrality
    compute_symbol_centrality(as_of=date(2026, 7, 16))
    return None


class TestCentralityTopAPI:
    def test_top_pagerank_default(self, centrality_snapshot, auth_client):
        resp = auth_client.get("/api/v1/chainsight/centrality/top/")
        assert resp.status_code == 200
        d = resp.json()
        assert d["metric"] == "pagerank"
        assert d["results"][0]["symbol"] == "A"  # 허브 1위
        assert d["results"][0]["pagerank_rank"] == 1
        assert d["graph_size"] == {"nodes": 5, "edges": 5}

    def test_top_betweenness(self, centrality_snapshot, auth_client):
        resp = auth_client.get("/api/v1/chainsight/centrality/top/?metric=betweenness&n=2")
        d = resp.json()
        assert d["metric"] == "betweenness"
        assert len(d["results"]) == 2
        assert d["results"][0]["betweenness_rank"] == 1

    def test_invalid_metric_400(self, centrality_snapshot, auth_client):
        resp = auth_client.get("/api/v1/chainsight/centrality/top/?metric=bogus")
        assert resp.status_code == 400

    def test_empty_when_no_snapshot(self, db, auth_client):
        resp = auth_client.get("/api/v1/chainsight/centrality/top/")
        assert resp.status_code == 200
        assert resp.json()["results"] == []


# ── ego rank 필드 ────────────────────────────────────────────

class TestEgoRankFields:
    def test_ego_nodes_include_rank_when_snapshot_present(
        self, centrality_snapshot, auth_client
    ):
        for s in ["A", "B", "C", "D", "E"]:
            Stock.objects.get_or_create(
                symbol=s, defaults={"stock_name": f"{s} Inc.", "sector": "Technology"}
            )
        resp = auth_client.get("/api/v1/chainsight/ego/A/")
        d = resp.json()
        node_a = next(n for n in d["nodes"] if n["symbol"] == "A")
        assert node_a["pagerank_rank"] == 1
        assert node_a["betweenness_rank"] is not None
