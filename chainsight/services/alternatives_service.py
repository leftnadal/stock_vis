"""Alternatives API 서비스 — CS-6-7"""

from chainsight.graph import get_graph_repository


def find_alternatives(path_nodes, target_ticker, limit=10):
    if target_ticker not in path_nodes:
        raise ValueError(f'{target_ticker} not in path')

    idx = path_nodes.index(target_ticker)
    before = path_nodes[idx - 1] if idx > 0 else None
    after = path_nodes[idx + 1] if idx < len(path_nodes) - 1 else None

    if before is None and after is None:
        return {
            'target_ticker': target_ticker,
            'neighbor_constraints': {'before': None, 'after': None},
            'alternatives': [],
            'total_found': 0,
        }

    repo = get_graph_repository()
    before_rel = _fetch_relation(repo, before, target_ticker) if before else None
    after_rel = _fetch_relation(repo, target_ticker, after) if after else None

    alternatives = _query_alternatives(
        repo, target_ticker=target_ticker,
        before_ticker=before, before_rel_type=before_rel['rel_type'] if before_rel else None,
        after_ticker=after, after_rel_type=after_rel['rel_type'] if after_rel else None,
        excluded=path_nodes, limit=limit,
    )

    return {
        'target_ticker': target_ticker,
        'neighbor_constraints': {
            'before': {'ticker': before, 'relation_type': before_rel['rel_type']} if before_rel else None,
            'after': {'ticker': after, 'relation_type': after_rel['rel_type']} if after_rel else None,
        },
        'alternatives': alternatives,
        'total_found': len(alternatives),
    }


def _fetch_relation(repo, a, b):
    rows = repo.run_query(
        """
        MATCH (a:Stock {ticker: $a})-[r]-(b:Stock {ticker: $b})
        WHERE r.status IN ['confirmed', 'probable'] OR type(r) = 'PEER_OF'
        RETURN type(r) AS rel_type, r.truth_score AS truth_score, r.status AS status
        ORDER BY r.truth_score DESC NULLS LAST
        LIMIT 1
        """,
        {'a': a, 'b': b}
    )
    return rows[0] if rows else None


def _query_alternatives(repo, target_ticker, before_ticker, before_rel_type,
                         after_ticker, after_rel_type, excluded, limit):
    if before_ticker and after_ticker:
        return _query_both_sides(repo, target_ticker, before_ticker, before_rel_type,
                                  after_ticker, after_rel_type, excluded, limit)
    elif before_ticker:
        return _query_one_side(repo, before_ticker, before_rel_type, 'before', excluded, limit)
    elif after_ticker:
        return _query_one_side(repo, after_ticker, after_rel_type, 'after', excluded, limit)
    return []


def _query_both_sides(repo, target, before, before_rel, after, after_rel, excluded, limit):
    rows = repo.run_query(
        """
        MATCH (cand:Stock)-[r1]-(b:Stock {ticker: $before})
        WHERE type(r1) = $before_rel
          AND cand.ticker <> $target
          AND NOT cand.ticker IN $excluded
          AND (r1.status IN ['confirmed', 'probable'] OR type(r1) = 'PEER_OF')
        WITH cand, r1
        MATCH (cand)-[r2]-(a:Stock {ticker: $after})
        WHERE type(r2) = $after_rel
          AND (r2.status IN ['confirmed', 'probable'] OR type(r2) = 'PEER_OF')
        RETURN cand.ticker AS ticker,
               cand.name AS name,
               cand.sector AS sector,
               cand.industry AS industry,
               cand.heat_score AS heat_score,
               2 AS overlap,
               {rel_type: type(r1), truth_score: r1.truth_score, status: r1.status} AS rel_before,
               {rel_type: type(r2), truth_score: r2.truth_score, status: r2.status} AS rel_after
        ORDER BY r1.truth_score + r2.truth_score DESC NULLS LAST
        LIMIT $limit

        UNION

        MATCH (cand:Stock)-[r1]-(b:Stock {ticker: $before})
        WHERE type(r1) = $before_rel
          AND cand.ticker <> $target
          AND NOT cand.ticker IN $excluded
          AND (r1.status IN ['confirmed', 'probable'] OR type(r1) = 'PEER_OF')
          AND NOT EXISTS {
            MATCH (cand)-[r2]-(:Stock {ticker: $after})
            WHERE type(r2) = $after_rel
          }
        RETURN cand.ticker AS ticker,
               cand.name AS name,
               cand.sector AS sector,
               cand.industry AS industry,
               cand.heat_score AS heat_score,
               1 AS overlap,
               {rel_type: type(r1), truth_score: r1.truth_score, status: r1.status} AS rel_before,
               null AS rel_after
        ORDER BY r1.truth_score DESC NULLS LAST
        LIMIT $limit
        """,
        {'target': target, 'before': before, 'before_rel': before_rel,
         'after': after, 'after_rel': after_rel, 'excluded': excluded, 'limit': limit}
    )
    return [_format_alternative(row) for row in rows[:limit]]


def _query_one_side(repo, neighbor_ticker, rel_type, side, excluded, limit):
    rows = repo.run_query(
        """
        MATCH (cand:Stock)-[r]-(n:Stock {ticker: $neighbor})
        WHERE type(r) = $rel_type
          AND cand.ticker <> $neighbor
          AND NOT cand.ticker IN $excluded
          AND (r.status IN ['confirmed', 'probable'] OR type(r) = 'PEER_OF')
        RETURN cand.ticker AS ticker, cand.name AS name,
               cand.sector AS sector, cand.industry AS industry,
               cand.heat_score AS heat_score,
               r.truth_score AS truth_score, r.status AS status
        ORDER BY r.truth_score DESC NULLS LAST
        LIMIT $limit
        """,
        {'neighbor': neighbor_ticker, 'rel_type': rel_type, 'excluded': excluded, 'limit': limit}
    )
    results = []
    for row in rows:
        rel_info = {'rel_type': rel_type, 'truth_score': row.get('truth_score'), 'status': row.get('status')}
        results.append({
            'ticker': row['ticker'],
            'name': row.get('name') or row['ticker'],
            'sector': row.get('sector') or '',
            'industry': row.get('industry') or '',
            'overlap_count': 1,
            'relation_before': rel_info if side == 'before' else None,
            'relation_after': rel_info if side == 'after' else None,
            'why_summary': f'{side}쪽 노드와 같은 {rel_type} 관계',
        })
    return results


def _format_alternative(row):
    overlap = row.get('overlap', 0)
    rel_before = row.get('rel_before')
    rel_after = row.get('rel_after')
    if overlap == 2:
        why = '양옆 노드 모두와 같은 관계 유형 확인'
    elif rel_before:
        why = '앞쪽 노드와 같은 관계 유형'
    elif rel_after:
        why = '뒤쪽 노드와 같은 관계 유형'
    else:
        why = '관련 노드'
    return {
        'ticker': row['ticker'],
        'name': row.get('name') or row['ticker'],
        'sector': row.get('sector') or '',
        'industry': row.get('industry') or '',
        'overlap_count': overlap,
        'relation_before': rel_before,
        'relation_after': rel_after,
        'why_summary': why,
    }
