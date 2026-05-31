"""Expand API 서비스 — CS-6-6"""

from apps.chain_sight.graph import get_graph_repository

RELATION_PRIORITY = {
    "SUPPLIES_TO": 5,
    "COMPETES_WITH": 4,
    "HAS_THEME": 3,
    "PEER_OF": 2,
    "CO_MENTIONED": 1,
    "PRICE_CORRELATED": 0,
}


def find_expansion_candidates(source_ticker, excluded_tickers, limit=10):
    repo = get_graph_repository()
    rows = repo.run_query(
        """
        MATCH (src:Stock {ticker: $source})-[r]-(neighbor:Stock)
        WHERE neighbor.ticker <> $source
          AND NOT neighbor.ticker IN $excluded
          AND (r.status IN ['confirmed', 'probable'] OR type(r) = 'PEER_OF')
        WITH neighbor, r,
             type(r) AS rel_type,
             r.truth_score AS truth_score,
             r.status AS relation_status,
             r.relation_basis_summary AS basis_summary
        ORDER BY truth_score DESC NULLS LAST
        RETURN neighbor.ticker AS ticker,
               neighbor.name AS name,
               neighbor.sector AS sector,
               neighbor.heat_score AS heat_score,
               collect(DISTINCT {
                 rel_type: rel_type,
                 truth_score: truth_score,
                 status: relation_status,
                 basis_summary: basis_summary
               })[0] AS primary_relation,
               size(collect(DISTINCT rel_type)) AS relation_count
        LIMIT 100
        """,
        {"source": source_ticker, "excluded": excluded_tickers},
    )
    total_found = len(rows)
    candidates = []
    for row in rows:
        rel = row["primary_relation"]
        score = _compute_expansion_score(
            truth_score=rel.get("truth_score") or 0,
            heat_score=row.get("heat_score") or 0,
            rel_type=rel.get("rel_type") or "",
            relation_count=row.get("relation_count") or 1,
        )
        candidates.append(
            {
                "ticker": row["ticker"],
                "name": row.get("name") or row["ticker"],
                "sector": row.get("sector") or "",
                "relation_type": rel.get("rel_type"),
                "truth_score": rel.get("truth_score"),
                "relation_status": rel.get("status"),
                "heat_score": row.get("heat_score"),
                "basis_summary": rel.get("basis_summary") or "",
                "why_summary": _build_why_summary(rel, row),
                "_score": score,
            }
        )
    candidates.sort(key=lambda x: x["_score"], reverse=True)
    top = candidates[:limit]
    for c in top:
        del c["_score"]
    return {
        "source_ticker": source_ticker,
        "candidates": top,
        "total_found": total_found,
    }


def _compute_expansion_score(truth_score, heat_score, rel_type, relation_count):
    rel_priority = RELATION_PRIORITY.get(rel_type, 0)
    return (
        0.40 * (truth_score / 100.0)
        + 0.30 * heat_score
        + 0.20 * (rel_priority / 5.0)
        + 0.10 * min(relation_count / 3.0, 1.0)
    )


def _build_why_summary(relation, row):
    reasons = []
    status = relation.get("status")
    rel_type = relation.get("rel_type") or ""
    if status == "confirmed":
        reasons.append(f"{rel_type} 확인됨")
    elif status == "probable":
        reasons.append(f"{rel_type} 가능성 높음")
    if (row.get("heat_score") or 0) >= 0.6:
        reasons.append("높은 시장 관심도")
    if not reasons:
        reasons.append("관련 노드")
    return ", ".join(reasons)
