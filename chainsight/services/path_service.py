from collections import Counter
from typing import Dict, List

from django.utils import timezone

from chainsight.graph import get_graph_repository
from stocks.models import Stock

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
