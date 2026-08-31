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


def compute_centrality(edge_rows, want_degree=False, want_betweenness=True):
    """edge_rows → (rows, meta). rows=[{symbol,pagerank,pagerank_rank, [betweenness,betweenness_rank], [degree]}].

    DB 미접촉. edge_rows = iterable[(symbol_a, symbol_b, truth_score, market_score)].

    want_betweenness/want_degree = additive 옵션(기본 = ⑲ 원 동작 보존: betweenness 포함,
    degree 미포함). RC-C-1 backbone 어댑터는 want_betweenness=False·want_degree=True로
    호출해 582노드 부분그래프를 즉석 계산한다(betweenness 계산 생략 = 수십 ms).
    """
    g = build_relation_graph(edge_rows)
    n_nodes = g.number_of_nodes()
    n_edges = g.number_of_edges()
    if n_nodes == 0:
        return [], {"graph_nodes": 0, "graph_edges": 0}

    pr = nx.pagerank(g, weight="weight")
    pr_rank = _ranked(pr)

    bt = bt_rank = None
    if want_betweenness:
        bt = nx.betweenness_centrality(g, weight=None)  # 정확값(샘플링 없음)
        bt_rank = _ranked(bt)

    rows = []
    for sym in g.nodes():
        row = {
            "symbol": sym,
            "pagerank": pr[sym],
            "pagerank_rank": pr_rank[sym],
        }
        if want_betweenness:
            row["betweenness"] = bt[sym]
            row["betweenness_rank"] = bt_rank[sym]
        if want_degree:
            row["degree"] = g.degree(sym)
        rows.append(row)
    meta = {"graph_nodes": n_nodes, "graph_edges": n_edges}
    return rows, meta


def compute_centrality_from_db():
    """RelationConfidence 전량을 PG에서 읽어 compute_centrality 실행. (read-only 조회)"""
    from apps.chain_sight.models import RelationConfidence

    edge_rows = RelationConfidence.objects.values_list(
        "symbol_a", "symbol_b", "truth_score", "market_score"
    ).iterator()
    return compute_centrality(edge_rows)


# 활성 해자 기본 필터 (RC-C-1 D-RC-C1-STORAGE = compute-on-read).
BACKBONE_STATUS_ALLOW = ("confirmed", "probable")


def compute_backbone_centrality(status_allow=BACKBONE_STATUS_ALLOW):
    """활성 해자 부분그래프 중심성(compute-on-read 어댑터, ⑲ compute_centrality 재사용).

    입력 = RelationConfidence 중 relation_status∈{confirmed,probable} AND max(truth,market)>0
    엣지(self-loop 제외). PEER outlier 2행은 status='hidden'이라 필터에서 자연 제외된다
    (별도 제외 코드 불요 — 테스트로만 확인). PageRank(damping 0.85 = nx 기본) + degree.
    지속 모델·마이그레이션 없음(D-RC-C1-STORAGE 옵션 C). 반환 = (rows, meta), rows는
    pagerank 내림차순 정렬(동점 symbol 오름차순). betweenness 미계산(불요).
    """
    from apps.chain_sight.models import RelationConfidence

    qs = RelationConfidence.objects.filter(
        relation_status__in=status_allow
    ).values_list("symbol_a", "symbol_b", "truth_score", "market_score").iterator()
    # max>0 사전 배제: build_relation_graph가 0-weight 엣지를 만들지 않도록 어댑터에서 필터.
    edge_rows = (
        (a, b, ts, ms)
        for a, b, ts, ms in qs
        if a != b and max(ts or 0.0, ms or 0.0) > 0
    )
    rows, meta = compute_centrality(edge_rows, want_degree=True, want_betweenness=False)
    rows.sort(key=lambda r: (-r["pagerank"], r["symbol"]))
    return rows, meta
