"""
Neo4j 온톨로지 스키마 정의.
이 파일이 Chain Sight Neo4j 스키마의 single source of truth이다.
"""

import logging

logger = logging.getLogger(__name__)

CONSTRAINTS = [
    {"name": "stock_ticker", "cypher": "CREATE CONSTRAINT stock_ticker IF NOT EXISTS FOR (s:Stock) REQUIRE s.ticker IS UNIQUE", "description": ":Stock ticker 유니크"},
    {"name": "sector_name", "cypher": "CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE", "description": ":Sector name 유니크"},
    {"name": "industry_name", "cypher": "CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (i:Industry) REQUIRE i.name IS UNIQUE", "description": ":Industry name 유니크"},
    {"name": "theme_name", "cypher": "CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE", "description": ":Theme name 유니크 (DC-2 이후)"},
]

INDEXES = [
    {"name": "stock_sector", "cypher": "CREATE INDEX stock_sector IF NOT EXISTS FOR (s:Stock) ON (s.sector)", "description": ":Stock 섹터별 필터링"},
    {"name": "stock_community", "cypher": "CREATE INDEX stock_community IF NOT EXISTS FOR (s:Stock) ON (s.community_id)", "description": ":Stock GDS 커뮤니티 조회"},
    {"name": "stock_market_cap", "cypher": "CREATE INDEX stock_market_cap IF NOT EXISTS FOR (s:Stock) ON (s.market_cap)", "description": ":Stock 시가총액 정렬"},
    {"name": "stock_industry", "cypher": "CREATE INDEX stock_industry IF NOT EXISTS FOR (s:Stock) ON (s.industry)", "description": ":Stock 산업별 필터링"},
]


def initialize_schema(graph_repo) -> dict:
    """Neo4j에 모든 constraint + index 생성. 멱등."""
    result = {"constraints_applied": 0, "indexes_applied": 0, "errors": []}

    for c in CONSTRAINTS:
        try:
            graph_repo.run_query(c["cypher"])
            result["constraints_applied"] += 1
            logger.info(f"Constraint OK: {c['name']}")
        except Exception as e:
            result["errors"].append(f"Constraint FAIL: {c['name']} — {e}")
            logger.error(f"Constraint FAIL: {c['name']} — {e}")

    for idx in INDEXES:
        try:
            graph_repo.run_query(idx["cypher"])
            result["indexes_applied"] += 1
            logger.info(f"Index OK: {idx['name']}")
        except Exception as e:
            result["errors"].append(f"Index FAIL: {idx['name']} — {e}")
            logger.error(f"Index FAIL: {idx['name']} — {e}")

    return result


def verify_schema(graph_repo) -> dict:
    """현재 Neo4j 스키마와 기대 스키마 대조."""
    existing_constraints = graph_repo.run_query("SHOW CONSTRAINTS")
    existing_names = {c.get("name", "") for c in existing_constraints}
    expected_c = {c["name"] for c in CONSTRAINTS}

    existing_indexes = graph_repo.run_query("SHOW INDEXES")
    existing_idx = {idx.get("name", "") for idx in existing_indexes}
    expected_i = {idx["name"] for idx in INDEXES}

    return {
        "constraints": {"expected": len(CONSTRAINTS), "found": sorted(expected_c & existing_names), "missing": sorted(expected_c - existing_names)},
        "indexes": {"expected": len(INDEXES), "found": sorted(expected_i & existing_idx), "missing": sorted(expected_i - existing_idx)},
    }
