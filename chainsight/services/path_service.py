from collections import Counter
from typing import Dict, List

from django.utils import timezone

from chainsight.graph import get_graph_repository
from packages.shared.stocks.models import Stock

RELATION_LABEL = {
    'SUPPLIES_TO': '공급망 중심',
    'COMPETES_WITH': '경쟁 관계',
    'PEER_OF': '동종업계',
    'HAS_THEME': '테마 연결',
    'CO_MENTIONED': '뉴스 연동',
    'PRICE_CORRELATED': '가격 동조',
}


def build_edge_snapshot(path_nodes: List[str]) -> List[Dict]:
    """인접 노드 쌍에 대해 Neo4j에서 관계 스냅샷을 조회."""
    if len(path_nodes) < 2:
        return []
    repo = get_graph_repository()
    snapshot = []
    for i in range(len(path_nodes) - 1):
        a, b = path_nodes[i], path_nodes[i + 1]
        result = repo.run_query(
            """
            MATCH (from:Stock {ticker: $a})-[r]-(to:Stock {ticker: $b})
            RETURN type(r) AS rel_type,
                   r.truth_score AS truth_score,
                   r.status AS status,
                   startNode(r).ticker AS start_ticker
            ORDER BY r.truth_score DESC NULLS LAST
            LIMIT 1
            """,
            {'a': a, 'b': b}
        )
        if result:
            row = result[0]
            snapshot.append({
                'from': row['start_ticker'],
                'to': b if row['start_ticker'] == a else a,
                'type': row['rel_type'],
                'truth_score': row['truth_score'],
                'status': row['status'],
            })
        else:
            snapshot.append({
                'from': a, 'to': b,
                'type': None, 'truth_score': None, 'status': 'hidden',
            })
    return snapshot


def build_path_signature(path_nodes: List[str], edge_snapshot: List[Dict]) -> str:
    """경로의 관계 유형과 섹터를 요약한 시그니처 문자열 생성."""
    rel_counts = Counter(
        edge['type'] for edge in edge_snapshot if edge.get('type')
    )
    if not rel_counts:
        rel_label = '관계 미확정'
    elif len(rel_counts) == 1:
        dominant = rel_counts.most_common(1)[0][0]
        rel_label = RELATION_LABEL.get(dominant, dominant)
    else:
        top_two = rel_counts.most_common(2)
        total = sum(rel_counts.values())
        if top_two[0][1] / total >= 0.6:
            rel_label = RELATION_LABEL.get(top_two[0][0], top_two[0][0])
        else:
            rel_label = '복합 체인'

    stocks = Stock.objects.filter(symbol__in=path_nodes).values_list('symbol', 'sector')
    sector_map = dict(stocks)
    sector_counts = Counter(
        sector_map.get(t) for t in path_nodes if sector_map.get(t)
    )
    if not sector_counts:
        sector_label = ''
    else:
        sector_label = sector_counts.most_common(1)[0][0]

    if sector_label:
        return f'{rel_label} · {sector_label}'
    return rel_label


def build_initial_why_now(path_nodes: List[str], edge_snapshot: List[Dict]) -> Dict:
    """초기 why_now 스냅샷 생성. 경로의 확인된 엣지 비율 기반 헤드라인."""
    strong_count = sum(
        1 for e in edge_snapshot
        if e.get('status') in ('confirmed', 'probable')
    )
    if strong_count == len(edge_snapshot) and strong_count > 0:
        headline = f'{len(path_nodes)}개 노드 전 구간 확인된 경로'
    elif strong_count >= len(edge_snapshot) * 0.6:
        headline = f'주요 구간 확인된 {len(path_nodes)}개 노드 경로'
    else:
        headline = f'{len(path_nodes)}개 노드 관찰 대상 경로'

    return {
        'headline': headline,
        'signals': [],
        'generated_at': timezone.now().isoformat(),
        'strong_edges': strong_count,
        'total_edges': len(edge_snapshot),
    }


# ─── Summary Path (CS-6-3) ──────────────────────

def generate_summary_path(path_nodes: List[str]) -> List[str]:
    """5+ 노드 경로를 3~4개 landmark로 압축. 4개 이하는 그대로."""
    if len(path_nodes) <= 4:
        return list(path_nodes)

    middle = path_nodes[1:-1]
    total = len(path_nodes)
    k = 1 if total <= 6 else 2

    scores = compute_landmark_scores(middle, path_nodes)

    top_k_indices = sorted(
        range(len(middle)),
        key=lambda i: scores[i],
        reverse=True,
    )[:k]
    top_k_indices.sort()

    selected_middle = [middle[i] for i in top_k_indices]
    return [path_nodes[0]] + selected_middle + [path_nodes[-1]]


def compute_landmark_scores(middle_nodes: List[str],
                             full_path: List[str]) -> List[float]:
    """중간 노드들의 landmark_score를 계산."""
    if not middle_nodes:
        return []

    centrality = _fetch_centrality(middle_nodes)

    pagerank_valid = any(
        centrality.get(n, {}).get('pagerank') is not None for n in middle_nodes
    )
    betweenness_valid = any(
        centrality.get(n, {}).get('betweenness') is not None for n in middle_nodes
    )

    if pagerank_valid and betweenness_valid:
        w = {'pagerank': 0.25, 'betweenness': 0.20, 'bridge': 0.30, 'sector': 0.25}
    elif pagerank_valid:
        w = {'pagerank': 0.25, 'betweenness': 0.0, 'bridge': 0.50, 'sector': 0.25}
    elif betweenness_valid:
        w = {'pagerank': 0.0, 'betweenness': 0.20, 'bridge': 0.55, 'sector': 0.25}
    else:
        w = {'pagerank': 0.0, 'betweenness': 0.0, 'bridge': 0.75, 'sector': 0.25}

    pagerank_ranks = _normalize_rank(
        {n: centrality.get(n, {}).get('pagerank') or 0 for n in middle_nodes}
    )
    betweenness_ranks = _normalize_rank(
        {n: centrality.get(n, {}).get('betweenness') or 0 for n in middle_nodes}
    )
    bridge_scores = _compute_bridge_scores(middle_nodes, full_path, centrality)
    sector_scores = _compute_sector_uniqueness(middle_nodes, full_path)

    scores = []
    for i, node in enumerate(middle_nodes):
        s = (
            w['pagerank'] * pagerank_ranks.get(node, 0)
            + w['betweenness'] * betweenness_ranks.get(node, 0)
            + w['bridge'] * bridge_scores[i]
            + w['sector'] * sector_scores[i]
        )
        scores.append(s)

    return scores


def _fetch_centrality(tickers: List[str]) -> Dict[str, Dict]:
    """Neo4j에서 pagerank_score, betweenness_score, degree 조회."""
    repo = get_graph_repository()
    rows = repo.run_query(
        """
        UNWIND $tickers AS t
        MATCH (s:Stock {ticker: t})
        OPTIONAL MATCH (s)-[r]-(other:Stock)
        RETURN s.ticker AS ticker,
               s.pagerank_score AS pagerank,
               s.betweenness_score AS betweenness,
               count(DISTINCT other) AS degree
        """,
        {'tickers': tickers}
    )
    return {
        row['ticker']: {
            'pagerank': row['pagerank'],
            'betweenness': row['betweenness'],
            'degree': row['degree'],
        }
        for row in rows
    }


def _normalize_rank(values: Dict[str, float]) -> Dict[str, float]:
    """값들을 0~1 percentile rank로 변환."""
    if not values:
        return {}
    sorted_items = sorted(values.items(), key=lambda x: x[1])
    n = len(sorted_items)
    return {
        ticker: (i / (n - 1)) if n > 1 else 1.0
        for i, (ticker, _) in enumerate(sorted_items)
    }


def _compute_bridge_scores(middle: List[str], full_path: List[str],
                            centrality: Dict[str, Dict]) -> List[float]:
    """bridge_score = 0.5 * position_weight + 0.5 * degree_weight"""
    scores = []
    total_middle = len(middle)
    degrees = {n: centrality.get(n, {}).get('degree', 0) for n in middle}
    max_degree = max(degrees.values()) if degrees else 1
    if max_degree == 0:
        max_degree = 1

    for i, node in enumerate(middle):
        if total_middle == 1:
            position_weight = 1.0
        else:
            center = (total_middle - 1) / 2
            position_weight = 1.0 - abs(i - center) / center
        degree_weight = degrees[node] / max_degree
        scores.append(0.5 * position_weight + 0.5 * degree_weight)

    return scores


def _compute_sector_uniqueness(middle: List[str],
                                full_path: List[str]) -> List[float]:
    """경로 내 섹터 다양성 기여도."""
    stocks = Stock.objects.filter(symbol__in=full_path).values_list('symbol', 'sector')
    sector_map = dict(stocks)
    path_sectors = [sector_map.get(t) for t in full_path if sector_map.get(t)]
    sector_counts = Counter(path_sectors)

    scores = []
    for node in middle:
        sector = sector_map.get(node)
        if sector is None:
            scores.append(0.5)
        else:
            scores.append(1.0 / sector_counts[sector])
    return scores
