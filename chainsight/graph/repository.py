from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Protocol

from .exceptions import GraphConnectionError, GraphQueryError

logger = logging.getLogger(__name__)


class GraphRepository(Protocol):
    """그래프 DB 접근 인터페이스. 백엔드 교체 시 이 Protocol을 구현."""

    def get_node(self, ticker: str) -> Dict[str, Any] | None: ...
    def get_neighbors(self, ticker: str, depth: int = 1, rel_types: List[str] | None = None) -> Dict: ...
    def upsert_node(self, label: str, key_field: str, key_value: str, properties: Dict[str, Any]) -> None: ...
    def upsert_edge(self, from_ticker: str, to_ticker: str, rel_type: str, properties: Dict[str, Any]) -> None: ...
    def run_query(self, cypher: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]: ...
    def close(self) -> None: ...


class Neo4jGraphRepository:
    """
    실제 Neo4j 구현체.
    PID 기반 lazy initialization으로 Celery prefork fork 안전.
    """

    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        self._pid: int | None = None

    @property
    def driver(self):
        current_pid = os.getpid()
        if self._driver is None or self._pid != current_pid:
            try:
                from neo4j import GraphDatabase
                if self._driver is not None:
                    try:
                        self._driver.close()
                    except Exception:
                        pass
                self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
                self._pid = current_pid
                logger.debug(f"Neo4j driver created for PID {current_pid}")
            except Exception as e:
                raise GraphConnectionError(f"Neo4j 연결 실패: {e}") from e
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._pid = None

    def get_node(self, ticker: str) -> Dict[str, Any] | None:
        query = "MATCH (s:Stock {ticker: $ticker}) RETURN s {.*} AS node"
        results = self.run_query(query, {"ticker": ticker})
        return results[0]["node"] if results else None

    def get_neighbors(self, ticker: str, depth: int = 1, rel_types: List[str] | None = None) -> Dict[str, Any]:
        if rel_types:
            rel_filter = ":" + "|".join(rel_types)
        else:
            rel_filter = ""

        query = f"""
        MATCH (center:Stock {{ticker: $ticker}})
        OPTIONAL MATCH (center)-[r{rel_filter}]-(neighbor)
        RETURN center {{.*}} AS center_node,
               collect(DISTINCT neighbor {{.*}}) AS neighbors,
               collect(DISTINCT {{
                   from: startNode(r).ticker,
                   to: endNode(r).ticker,
                   type: type(r),
                   props: properties(r)
               }}) AS edges
        """
        results = self.run_query(query, {"ticker": ticker})
        if not results:
            return {"center": None, "nodes": [], "edges": []}

        row = results[0]
        return {
            "center": row["center_node"],
            "nodes": [row["center_node"]] + row["neighbors"],
            "edges": [e for e in row["edges"] if e.get("type")],
        }

    def upsert_node(self, label: str, key_field: str, key_value: str, properties: Dict[str, Any]) -> None:
        props_set = ", ".join(f"n.{k} = ${k}" for k in properties)
        query = f"MERGE (n:{label} {{{key_field}: $key_value}}) SET {props_set}"
        params = {"key_value": key_value, **properties}
        self.run_query(query, params)

    def upsert_edge(self, from_ticker: str, to_ticker: str, rel_type: str, properties: Dict[str, Any]) -> None:
        props_set = ", ".join(f"r.{k} = ${k}" for k in properties) if properties else ""
        set_clause = f"SET {props_set}" if props_set else ""
        query = f"""
        MATCH (a:Stock {{ticker: $from_ticker}})
        MATCH (b:Stock {{ticker: $to_ticker}})
        MERGE (a)-[r:{rel_type}]->(b)
        {set_clause}
        """
        params = {"from_ticker": from_ticker, "to_ticker": to_ticker, **properties}
        self.run_query(query, params)

    def bulk_upsert_nodes(self, label: str, key_field: str, nodes_data: List[Dict[str, Any]]) -> int:
        query = f"""
        UNWIND $batch AS row
        MERGE (n:{label} {{{key_field}: row.{key_field}}})
        SET n += row
        """
        self.run_query(query, {"batch": nodes_data})
        return len(nodes_data)

    def bulk_upsert_edges(self, rel_type: str, edges_data: List[Dict[str, Any]], from_key: str = "from_ticker", to_key: str = "to_ticker") -> int:
        query = f"""
        UNWIND $batch AS row
        MATCH (a:Stock {{ticker: row.{from_key}}})
        MATCH (b:Stock {{ticker: row.{to_key}}})
        MERGE (a)-[r:{rel_type}]->(b)
        """
        self.run_query(query, {"batch": edges_data})
        return len(edges_data)

    def run_query(self, cypher: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                result = session.run(cypher, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            raise GraphQueryError(f"Cypher 실행 실패: {e}\nQuery: {cypher}") from e

    def health_check(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    def node_count(self, label: str = "Stock") -> int:
        result = self.run_query(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        return result[0]["cnt"] if result else 0

    def edge_count(self, rel_type: str | None = None) -> int:
        if rel_type:
            result = self.run_query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS cnt")
        else:
            result = self.run_query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        return result[0]["cnt"] if result else 0
