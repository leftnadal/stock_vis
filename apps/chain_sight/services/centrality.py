"""중심성 계산 서비스 (⑲ S3, S-C) — ⑱ 드라이런 analyze_graph.py 로직 승격.

RelationConfidence 전량 → 무방향 가중 그래프 → PageRank(허브) + betweenness(브리지).
Neo4j 불사용(PG + networkx in-memory). ⑱ 드라이런과 로직 동일성 유지:

- 페어 collapse: 무방향, 심볼쌍당 1엣지, weight = 그 쌍 행들의 max(truth_score, market_score)
  (⑱ analyze_graph.py `wt()`/`pair_weight` 동일 — 재현성 단일 소스).
- PageRank: weight 가중(truth 중심 — market 카테고리는 truth_score=0이라 peer 엣지 weight 지배).
- betweenness: 프로덕션 배치는 정확 계산(⑱ 드라이런의 k-샘플링 제거 — 555노드는 정확값도 수 초).
- 순위: 값 내림차순, 동점은 symbol 오름차순 tiebreak(결정론).

DB 미접촉 — 순수 계산(태스크가 저장). 드라이런 대조·단위 테스트가 이 함수를 직접 호출.
"""

import logging

import networkx as nx

logger = logging.getLogger(__name__)


def _edge_weight(truth_score, market_score):
    return max(truth_score or 0.0, market_score or 0.0)


def build_relation_graph(edge_rows):
    """RC 행 iterable[(symbol_a, symbol_b, truth_score, market_score)] → nx.Graph(무방향 collapse)."""
    pair_weight = {}
    for a, b, ts, ms in edge_rows:
        if a == b:
            continue
        key = (a, b) if a <= b else (b, a)
        w = _edge_weight(ts, ms)
        prev = pair_weight.get(key)
        if prev is None or w > prev:
            pair_weight[key] = w
    g = nx.Graph()
    for (a, b), w in pair_weight.items():
        g.add_edge(a, b, weight=w)
    return g


def _ranked(score_map):
    """{node: value} → {node: rank}(1=최상위, 동점은 symbol 오름차순)."""
    ordered = sorted(score_map.items(), key=lambda kv: (-kv[1], kv[0]))
    return {sym: i + 1 for i, (sym, _) in enumerate(ordered)}


def compute_centrality(edge_rows):
    """edge_rows → (rows, meta). rows=[{symbol,pagerank,betweenness,pagerank_rank,betweenness_rank}].

    DB 미접촉. edge_rows = iterable[(symbol_a, symbol_b, truth_score, market_score)].
    """
    g = build_relation_graph(edge_rows)
    n_nodes = g.number_of_nodes()
    n_edges = g.number_of_edges()
    if n_nodes == 0:
        return [], {"graph_nodes": 0, "graph_edges": 0}

    pr = nx.pagerank(g, weight="weight")
    bt = nx.betweenness_centrality(g, weight=None)  # 정확값(샘플링 없음)

    pr_rank = _ranked(pr)
    bt_rank = _ranked(bt)

    rows = [
        {
            "symbol": sym,
            "pagerank": pr[sym],
            "betweenness": bt[sym],
            "pagerank_rank": pr_rank[sym],
            "betweenness_rank": bt_rank[sym],
        }
        for sym in g.nodes()
    ]
    meta = {"graph_nodes": n_nodes, "graph_edges": n_edges}
    return rows, meta


def compute_centrality_from_db():
    """RelationConfidence 전량을 PG에서 읽어 compute_centrality 실행. (read-only 조회)"""
    from apps.chain_sight.models import RelationConfidence

    edge_rows = RelationConfidence.objects.values_list(
        "symbol_a", "symbol_b", "truth_score", "market_score"
    ).iterator()
    return compute_centrality(edge_rows)
