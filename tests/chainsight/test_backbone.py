"""백본 뷰 테스트 (RC-C-1 슬라이스 1) — compute-on-read 어댑터 + /backbone/ API.

- 서비스 compute_backbone_centrality: status∈{confirmed,probable} 필터 · max>0/self-loop
  제외 · PEER outlier(status=hidden) 자연 제외 · want_degree · betweenness 미계산 · 빈 no-op.
- compute_centrality want_degree/want_betweenness 옵션(additive, ⑲ 기본 동작 보존).
- API /backbone/: 인증 필수 · 빈 상태 shape · θ 경계 · top_symbols/edges shape · computed_at/graph_size.

점수 스케일은 RC v3.0 [0,1] — θ = GRADE_CONFIRMED_MIN(0.85).
"""

import pytest
from django.core.cache import cache

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services.centrality import (
    compute_backbone_centrality,
    compute_centrality,
)
from apps.chain_sight.services.score_scale import GRADE_CONFIRMED_MIN


def _rc(a, b, status="confirmed", truth=0.9, market=None,
        category="truth", rtype="SUPPLIES_TO", evidence=3, streak=2):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype,
        relation_category=category, relation_status=status,
        truth_score=truth, market_score=market,
        evidence_count_total=evidence, evidence_streak=streak,
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


# ── compute_centrality 옵션 (additive, DB 무접촉) ────────────────

FIX = [("A", "B", 0.9, None), ("B", "C", 0.6, None), ("A", "C", 0.5, None),
       ("A", "D", 0.4, None), ("D", "E", 0.3, None)]


class TestCentralityOptions:
    def test_default_preserves_betweenness_no_degree(self):
        """기본 = ⑲ 원 동작: betweenness 포함, degree 미포함."""
        rows, _ = compute_centrality(FIX)
        r = rows[0]
        assert "betweenness" in r and "betweenness_rank" in r
        assert "degree" not in r

    def test_want_degree_adds_degree(self):
        rows, _ = compute_centrality(FIX, want_degree=True)
        by = {r["symbol"]: r for r in rows}
        assert by["A"]["degree"] == 3   # A-B, A-C, A-D
        assert by["E"]["degree"] == 1   # D-E

    def test_skip_betweenness(self):
        rows, _ = compute_centrality(FIX, want_degree=True, want_betweenness=False)
        r = rows[0]
        assert "betweenness" not in r and "betweenness_rank" not in r
        assert "pagerank" in r and "degree" in r


# ── compute_backbone_centrality (DB) ────────────────────────────

class TestBackboneService:
    def test_filters_confirmed_probable_only(self, db):
        _rc("A", "B", status="confirmed", truth=0.9)
        _rc("B", "C", status="probable", truth=0.6)
        _rc("C", "D", status="weak", truth=0.35)      # 제외
        _rc("D", "E", status="hidden", truth=0.5)     # 제외
        rows, meta = compute_backbone_centrality()
        syms = {r["symbol"] for r in rows}
        assert syms == {"A", "B", "C"}                # weak/hidden 노드 미포함
        assert meta["graph_nodes"] == 3
        assert meta["graph_edges"] == 2

    def test_peer_outlier_excluded_as_hidden(self, db):
        """PEER outlier 2행(status=hidden)은 status 필터로 자연 제외 — 별도 코드 불요."""
        _rc("A", "B", status="confirmed", truth=0.9)
        _rc("AAPL", "NVDA", status="hidden", truth=0.6, rtype="PEER")   # outlier 모사
        _rc("MSFT", "GOOGL", status="hidden", truth=0.5, rtype="PEER")  # outlier 모사
        rows, _ = compute_backbone_centrality()
        syms = {r["symbol"] for r in rows}
        assert syms == {"A", "B"}                     # PEER outlier 심볼 미포함

    def test_excludes_zero_weight_and_self_loop(self, db):
        _rc("A", "B", status="confirmed", truth=0.9)
        _rc("C", "D", status="confirmed", truth=0.0, market=0.0)  # max=0 제외
        # self-loop: 모델 save()가 SelfLoopError로 신규 차단(§0-4의 13행 = 가드 前 legacy).
        # 가드 우회 bulk_create로 legacy self-loop 모사 → 어댑터 a!=b 필터가 제외하는지 검증.
        RelationConfidence.objects.bulk_create([
            RelationConfidence(
                symbol_a="A", symbol_b="A", relation_type="SUPPLIES_TO",
                relation_category="truth", relation_status="confirmed",
                truth_score=0.9,
            )
        ])
        rows, meta = compute_backbone_centrality()
        assert {r["symbol"] for r in rows} == {"A", "B"}
        assert meta["graph_edges"] == 1

    def test_has_degree_no_betweenness(self, db):
        _rc("A", "B", status="confirmed", truth=0.9)
        _rc("A", "C", status="confirmed", truth=0.9)
        rows, _ = compute_backbone_centrality()
        a = next(r for r in rows if r["symbol"] == "A")
        assert a["degree"] == 2
        assert "betweenness" not in a

    def test_empty_no_op(self, db):
        _rc("A", "B", status="hidden", truth=0.9)  # confirmed/probable 없음
        rows, meta = compute_backbone_centrality()
        assert rows == []
        assert meta == {"graph_nodes": 0, "graph_edges": 0}

    def test_sorted_by_pagerank_desc(self, db):
        _rc("HUB", "B", status="confirmed", truth=0.9)
        _rc("HUB", "C", status="confirmed", truth=0.9)
        _rc("HUB", "D", status="confirmed", truth=0.9)
        _rc("B", "C", status="confirmed", truth=0.6)
        rows, _ = compute_backbone_centrality()
        assert rows[0]["symbol"] == "HUB"             # 최고 허브 1위
        prs = [r["pagerank"] for r in rows]
        assert prs == sorted(prs, reverse=True)


# ── /backbone/ API ──────────────────────────────────────────────

@pytest.fixture
def auth_client(db, django_user_model):
    from rest_framework.test import APIClient
    u = django_user_model.objects.create_user(username="bb_u", password="x")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


class TestBackboneAPI:
    URL = "/api/v1/chainsight/backbone/"

    def test_requires_auth(self, db):
        from rest_framework.test import APIClient
        resp = APIClient().get(self.URL)
        assert resp.status_code in (401, 403)

    def test_empty_state_shape(self, db, auth_client):
        _rc("A", "B", status="hidden", truth=0.9)  # 활성 해자 없음
        d = auth_client.get(self.URL).json()
        assert d["top_symbols"] == []
        assert d["edges"] == []
        assert d["graph_size"] == {"nodes": 0, "edges": 0}
        assert d["theta"] == GRADE_CONFIRMED_MIN
        assert "as_of" in d and "computed_at" in d

    def test_top_symbols_and_edge_shape(self, db, auth_client):
        _rc("A", "B", status="confirmed", truth=0.9, evidence=5, streak=3)
        _rc("B", "C", status="confirmed", truth=0.9)
        _rc("A", "C", status="confirmed", truth=0.9)
        d = auth_client.get(self.URL).json()
        assert set(d["top_symbols"][0].keys()) == {"symbol", "pagerank", "degree"}
        assert d["graph_size"] == {"nodes": 3, "edges": 3}
        e = d["edges"][0]
        assert set(e.keys()) == {
            "symbol_a", "symbol_b", "score", "category",
            "evidence_count", "observed_count", "trust",
        }

    def test_theta_boundary_edges(self, db, auth_client):
        # 삼각형 A-B-C confirmed + A-D probable(0.84 < θ). 엣지는 θ≥0.85만.
        _rc("A", "B", status="confirmed", truth=0.90)
        _rc("B", "C", status="confirmed", truth=0.90)
        _rc("A", "C", status="confirmed", truth=0.85)   # 경계 = 포함
        _rc("A", "D", status="probable", truth=0.84)    # < θ = 엣지 제외(D는 노드로는 존재)
        d = auth_client.get(self.URL + "?limit=10").json()
        pairs = {(e["symbol_a"], e["symbol_b"]) for e in d["edges"]}
        assert ("A", "C") in pairs                       # 0.85 포함
        assert ("A", "D") not in pairs                   # 0.84 제외
        assert all(e["score"] >= GRADE_CONFIRMED_MIN for e in d["edges"])

    def test_limit_param(self, db, auth_client):
        _rc("HUB", "B", status="confirmed", truth=0.9)
        _rc("HUB", "C", status="confirmed", truth=0.9)
        _rc("HUB", "D", status="confirmed", truth=0.9)
        d = auth_client.get(self.URL + "?limit=2").json()
        assert len(d["top_symbols"]) == 2

    def test_edge_field_mapping(self, db, auth_client):
        _rc("A", "B", status="confirmed", truth=0.9, category="truth",
            evidence=7, streak=4)
        d = auth_client.get(self.URL).json()
        e = next(x for x in d["edges"] if {x["symbol_a"], x["symbol_b"]} == {"A", "B"})
        assert e["score"] == 0.9
        assert e["category"] == "truth"
        assert e["evidence_count"] == 7      # evidence_count_total
        assert e["observed_count"] == 4      # evidence_streak
        assert e["trust"] == "confirmed"     # relation_status
