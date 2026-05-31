"""
Chain Sight 서비스 — Neo4j 데이터 로드/동기화
"""

import logging
import time
from typing import Any, Dict, List, Tuple

import requests
from django.conf import settings

from chainsight.graph import get_graph_repository
from chainsight.utils import normalize_pair
from packages.shared.stocks.models import Stock

logger = logging.getLogger(__name__)

# Stock 모델 → Neo4j :Stock 노드 매핑
STOCK_FIELD_MAP = {
    "ticker": "symbol",
    "name": "stock_name",
    "sector": "sector",
    "industry": "industry",
    "market_cap": "market_capitalization",
    "exchange": "exchange",
}


# ── CS-1-1: Stock 노드 ──


def get_stock_data_for_neo4j(queryset=None) -> List[Dict[str, Any]]:
    if queryset is None:
        queryset = Stock.objects.all()
    django_fields = list(STOCK_FIELD_MAP.values())
    stocks = queryset.values(*django_fields)
    nodes = []
    for s in stocks:
        node = {}
        for neo4j_key, django_key in STOCK_FIELD_MAP.items():
            value = s.get(django_key)
            if value is not None:
                if neo4j_key == "market_cap":
                    node[neo4j_key] = float(value)
                else:
                    node[neo4j_key] = str(value) if value else ""
        if node.get("ticker"):
            nodes.append(node)
    return nodes


def load_stocks_to_neo4j(queryset=None, batch_size: int = 100) -> Dict[str, Any]:
    repo = get_graph_repository()
    nodes = get_stock_data_for_neo4j(queryset)
    result = {"total": len(nodes), "loaded": 0, "errors": 0, "batches": 0}
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i : i + batch_size]
        try:
            repo.bulk_upsert_nodes("Stock", "ticker", batch)
            result["loaded"] += len(batch)
            result["batches"] += 1
        except Exception as e:
            result["errors"] += len(batch)
            logger.error(f"Stock batch 실패: {e}")
    result["neo4j_total"] = repo.node_count("Stock")
    return result


# ── CS-1-2: Sector/Industry 노드 + BELONGS_TO ──


def load_sectors_to_neo4j() -> Dict[str, Any]:
    repo = get_graph_repository()
    result = {
        "sectors_created": 0,
        "industries_created": 0,
        "belongs_to_sector": 0,
        "belongs_to_industry": 0,
        "errors": [],
    }

    try:
        r = repo.run_query("""
            MATCH (s:Stock) WHERE s.sector IS NOT NULL AND s.sector <> ''
            WITH DISTINCT s.sector AS sector_name, count(s) AS stock_count
            MERGE (sec:Sector {name: sector_name}) SET sec.stock_count = stock_count
            RETURN count(sec) AS cnt
        """)
        result["sectors_created"] = r[0]["cnt"] if r else 0
    except Exception as e:
        result["errors"].append(str(e))

    try:
        r = repo.run_query("""
            MATCH (s:Stock) WHERE s.industry IS NOT NULL AND s.industry <> ''
            WITH DISTINCT s.industry AS industry_name, s.sector AS sector_name, count(s) AS stock_count
            MERGE (ind:Industry {name: industry_name}) SET ind.sector_name = sector_name, ind.stock_count = stock_count
            RETURN count(ind) AS cnt
        """)
        result["industries_created"] = r[0]["cnt"] if r else 0
    except Exception as e:
        result["errors"].append(str(e))

    try:
        r = repo.run_query("""
            MATCH (s:Stock), (sec:Sector) WHERE s.sector IS NOT NULL AND s.sector = sec.name
            MERGE (s)-[:BELONGS_TO_SECTOR]->(sec) RETURN count(*) AS cnt
        """)
        result["belongs_to_sector"] = r[0]["cnt"] if r else 0
    except Exception as e:
        result["errors"].append(str(e))

    try:
        r = repo.run_query("""
            MATCH (s:Stock), (ind:Industry) WHERE s.industry IS NOT NULL AND s.industry = ind.name
            MERGE (s)-[:BELONGS_TO_INDUSTRY]->(ind) RETURN count(*) AS cnt
        """)
        result["belongs_to_industry"] = r[0]["cnt"] if r else 0
    except Exception as e:
        result["errors"].append(str(e))

    return result


# ── CS-1-3: Peer 관계 ──


def fetch_finnhub_peers(symbol: str) -> List[str]:
    url = "https://finnhub.io/api/v1/stock/peers"
    params = {"symbol": symbol, "token": settings.FINNHUB_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return [p for p in r.json() if p != symbol]
    except Exception:
        pass
    return []


def fetch_fmp_peers(symbol: str) -> List[str]:
    url = "https://financialmodelingprep.com/stable/stock-peers"
    params = {"symbol": symbol, "apikey": settings.FMP_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                return [
                    d["symbol"]
                    for d in data
                    if d.get("symbol") and d["symbol"] != symbol
                ]
    except Exception:
        pass
    return []


def collect_all_peers(
    symbols: List[str], use_fmp: bool = False, finnhub_delay: float = 1.1
) -> Dict[str, Any]:
    pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    stats = {
        "symbols_processed": 0,
        "finnhub_success": 0,
        "fmp_success": 0,
        "finnhub_fail": 0,
        "fmp_fail": 0,
        "total_pairs": 0,
    }

    for i, symbol in enumerate(symbols):
        stats["symbols_processed"] += 1

        fp = fetch_finnhub_peers(symbol)
        if fp:
            stats["finnhub_success"] += 1
            for peer in fp:
                pair = normalize_pair(symbol, peer)
                if pair not in pairs:
                    pairs[pair] = {"source": "finnhub"}
                elif "finnhub" not in pairs[pair]["source"]:
                    pairs[pair]["source"] += ",finnhub"
        else:
            stats["finnhub_fail"] += 1

        time.sleep(finnhub_delay)

        if use_fmp:
            fmp = fetch_fmp_peers(symbol)
            if fmp:
                stats["fmp_success"] += 1
                for peer in fmp:
                    pair = normalize_pair(symbol, peer)
                    if pair not in pairs:
                        pairs[pair] = {"source": "fmp"}
                    elif "fmp" not in pairs[pair]["source"]:
                        pairs[pair]["source"] += ",fmp"
            else:
                stats["fmp_fail"] += 1
            time.sleep(0.3)

        if (i + 1) % 50 == 0:
            logger.info(f"Peer 수집: {i + 1}/{len(symbols)}, pairs: {len(pairs)}")

    stats["total_pairs"] = len(pairs)
    return {"pairs": pairs, "stats": stats}


def load_peers_to_neo4j(
    pairs: Dict[Tuple[str, str], Dict[str, Any]], batch_size: int = 200
) -> Dict[str, Any]:
    repo = get_graph_repository()
    result = {"loaded": 0, "errors": 0}

    edges = [
        {"from_ticker": a, "to_ticker": b, "source": p.get("source", "")}
        for (a, b), p in pairs.items()
    ]

    for i in range(0, len(edges), batch_size):
        batch = edges[i : i + batch_size]
        try:
            repo.run_query(
                """
                UNWIND $batch AS row
                MATCH (a:Stock {ticker: row.from_ticker})
                MATCH (b:Stock {ticker: row.to_ticker})
                MERGE (a)-[r:PEER_OF]-(b)
                SET r.source = row.source
            """,
                {"batch": batch},
            )
            result["loaded"] += len(batch)
        except Exception as e:
            result["errors"] += len(batch)
            logger.error(f"PEER_OF batch 실패: {e}")

    result["neo4j_total"] = repo.edge_count("PEER_OF")
    return result
