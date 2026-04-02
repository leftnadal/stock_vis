# CS-0-2: Neo4j 연결 레이어 구현

> **작업 번호**: CS-0-2
> **목표**: Neo4j와 안전하게 통신하는 GraphRepository 구현 + 읽기/쓰기 테스트 통과
> **예상 소요**: 2~3시간
> **선행 조건**: CS-0-1 완료, Neo4j 서버 구동 중
> **산출물**: `chainsight/graph/repository.py`, `chainsight/graph/__init__.py`, 테스트 파일, 설정 추가

---

## 배경

Chain Sight의 모든 그래프 연산은 Neo4j를 통해 수행된다.
이 작업에서는 Django ↔ Neo4j 통신 레이어를 구현한다.

핵심 제약:

- Celery prefork 환경에서 driver를 global singleton으로 캐싱하면 **SIGSEGV 발생** (이전 분석 완료)
- 따라서 **PID 기반 lazy initialization**으로 fork 안전하게 처리

---

## 1. 사전 확인

### Neo4j 서버 구동 확인

```bash
# 방법 1: cypher-shell
cypher-shell -u neo4j -p password "RETURN 1 AS test"

# 방법 2: Python
python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
d.verify_connectivity()
print('Neo4j 연결 OK')
d.close()
"
```

### neo4j-driver 패키지 확인

```bash
pip show neo4j
# 없으면:
pip install neo4j
```

---

## 2. Django 설정 추가

`config/settings.py` (또는 프로젝트 설정 파일)에 추가:

```python
# === Neo4j ===
NEO4J_URI = env('NEO4J_URI', default='bolt://localhost:7687')
NEO4J_USER = env('NEO4J_USER', default='neo4j')
NEO4J_PASSWORD = env('NEO4J_PASSWORD', default='password')
```

`.env` 파일에도 추가:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

## 3. 디렉토리 구조 생성

```
chainsight/
├── graph/
│   ├── __init__.py          ← get_graph_repository() 팩토리 함수
│   ├── repository.py        ← Protocol + Neo4jGraphRepository 구현
│   └── exceptions.py        ← 그래프 관련 예외 클래스
├── models.py
├── services.py
├── utils.py
└── ...
```

```bash
mkdir -p chainsight/graph
touch chainsight/graph/__init__.py
touch chainsight/graph/repository.py
touch chainsight/graph/exceptions.py
```

---

## 4. 구현

### 4-1. exceptions.py

```python
# chainsight/graph/exceptions.py

class GraphConnectionError(Exception):
    """Neo4j 연결 실패"""
    pass

class GraphQueryError(Exception):
    """Cypher 쿼리 실행 실패"""
    pass
```

### 4-2. repository.py

```python
# chainsight/graph/repository.py

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Protocol

from .exceptions import GraphConnectionError, GraphQueryError

logger = logging.getLogger(__name__)


class GraphRepository(Protocol):
    """
    그래프 DB 접근 인터페이스.
    백엔드 교체 시 이 Protocol을 구현하면 된다.
    """

    def get_node(self, ticker: str) -> Dict[str, Any] | None:
        """ticker로 :Stock 노드 조회"""
        ...

    def get_neighbors(
        self,
        ticker: str,
        depth: int = 1,
        rel_types: List[str] | None = None,
    ) -> Dict[str, Any]:
        """ticker 기준 N-depth 이웃 조회. nodes + edges 반환."""
        ...

    def upsert_node(self, label: str, key_field: str, key_value: str, properties: Dict[str, Any]) -> None:
        """노드 MERGE (없으면 생성, 있으면 업데이트)"""
        ...

    def upsert_edge(
        self,
        from_ticker: str,
        to_ticker: str,
        rel_type: str,
        properties: Dict[str, Any],
    ) -> None:
        """관계 MERGE"""
        ...

    def run_query(self, cypher: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """임의 Cypher 실행"""
        ...

    def close(self) -> None:
        """연결 종료"""
        ...


class Neo4jGraphRepository:
    """
    실제 Neo4j 구현체.

    ⚠️ Celery prefork 환경에서 driver를 global singleton으로
    캐싱하면 SIGSEGV 발생 (이전에 분석 완료).
    PID 기반 lazy initialization으로 fork 안전하게 처리.
    """

    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        self._pid: int | None = None

    @property
    def driver(self):
        """PID가 바뀌면 (fork 후) 새 driver를 생성한다."""
        current_pid = os.getpid()
        if self._driver is None or self._pid != current_pid:
            try:
                from neo4j import GraphDatabase
                if self._driver is not None:
                    try:
                        self._driver.close()
                    except Exception:
                        pass
                self._driver = GraphDatabase.driver(
                    self._uri, auth=(self._user, self._password)
                )
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

    # ------------------------------------------------------------------
    # 노드 조회
    # ------------------------------------------------------------------

    def get_node(self, ticker: str) -> Dict[str, Any] | None:
        query = """
        MATCH (s:Stock {ticker: $ticker})
        RETURN s {.*} AS node
        """
        results = self.run_query(query, {"ticker": ticker})
        return results[0]["node"] if results else None

    def get_neighbors(
        self,
        ticker: str,
        depth: int = 1,
        rel_types: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        N-depth 이웃 노드 + 관계를 반환한다.

        Returns:
            {
                "center": { ... },
                "nodes": [ { ... }, ... ],
                "edges": [ { "from": "AAPL", "to": "MSFT", "type": "PEER_OF", ... }, ... ]
            }
        """
        # 관계 타입 필터
        if rel_types:
            rel_filter = ":" + "|".join(rel_types)
        else:
            rel_filter = ""

        query = f"""
        MATCH (center:Stock {{ticker: $ticker}})
        CALL apoc.path.subgraphAll(center, {{
            maxLevel: $depth,
            relationshipFilter: '{rel_filter}'
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """

        # apoc이 없을 경우를 대비한 fallback (depth=1 only)
        fallback_query = f"""
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

        try:
            results = self.run_query(query, {"ticker": ticker, "depth": depth})
            # apoc 결과 파싱
            if results:
                nodes_raw = results[0].get("nodes", [])
                rels_raw = results[0].get("relationships", [])
                nodes = [dict(n) for n in nodes_raw]
                edges = []
                for r in rels_raw:
                    edges.append({
                        "from": r.start_node["ticker"],
                        "to": r.end_node["ticker"],
                        "type": r.type,
                        **dict(r),
                    })
                center = next((n for n in nodes if n.get("ticker") == ticker), None)
                return {"center": center, "nodes": nodes, "edges": edges}
        except GraphQueryError:
            # apoc 미설치 시 fallback
            if depth > 1:
                logger.warning("APOC 미설치. depth=1 fallback 사용.")

        # fallback 실행
        results = self.run_query(fallback_query, {"ticker": ticker})
        if not results:
            return {"center": None, "nodes": [], "edges": []}

        row = results[0]
        return {
            "center": row["center_node"],
            "nodes": [row["center_node"]] + row["neighbors"],
            "edges": [e for e in row["edges"] if e.get("type")],
        }

    # ------------------------------------------------------------------
    # 노드/엣지 UPSERT
    # ------------------------------------------------------------------

    def upsert_node(self, label: str, key_field: str, key_value: str, properties: Dict[str, Any]) -> None:
        """
        MERGE로 노드를 upsert한다.
        예: upsert_node("Stock", "ticker", "AAPL", {"name": "Apple Inc.", ...})
        """
        props_set = ", ".join(f"n.{k} = ${k}" for k in properties)
        query = f"""
        MERGE (n:{label} {{{key_field}: $key_value}})
        SET {props_set}
        """
        params = {"key_value": key_value, **properties}
        self.run_query(query, params)

    def upsert_edge(
        self,
        from_ticker: str,
        to_ticker: str,
        rel_type: str,
        properties: Dict[str, Any],
    ) -> None:
        """
        두 :Stock 노드 사이에 관계를 MERGE한다.
        예: upsert_edge("AAPL", "MSFT", "PEER_OF", {"source": "finnhub"})
        """
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

    # ------------------------------------------------------------------
    # 벌크 UPSERT (Phase 1에서 사용)
    # ------------------------------------------------------------------

    def bulk_upsert_nodes(self, label: str, key_field: str, nodes_data: List[Dict[str, Any]]) -> int:
        """
        UNWIND로 노드를 벌크 upsert한다.
        nodes_data의 각 dict에 key_field가 포함되어야 한다.
        Returns: 처리된 노드 수
        """
        query = f"""
        UNWIND $batch AS row
        MERGE (n:{label} {{{key_field}: row.{key_field}}})
        SET n += row
        """
        self.run_query(query, {"batch": nodes_data})
        return len(nodes_data)

    def bulk_upsert_edges(
        self,
        rel_type: str,
        edges_data: List[Dict[str, Any]],
        from_key: str = "from_ticker",
        to_key: str = "to_ticker",
    ) -> int:
        """
        UNWIND로 관계를 벌크 upsert한다.
        edges_data의 각 dict에 from_key, to_key가 포함되어야 한다.
        Returns: 처리된 엣지 수
        """
        query = f"""
        UNWIND $batch AS row
        MATCH (a:Stock {{ticker: row.{from_key}}})
        MATCH (b:Stock {{ticker: row.{to_key}}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += apoc.map.removeKeys(row, ['{from_key}', '{to_key}'])
        """
        # apoc 없는 환경 fallback
        fallback_query = f"""
        UNWIND $batch AS row
        MATCH (a:Stock {{ticker: row.{from_key}}})
        MATCH (b:Stock {{ticker: row.{to_key}}})
        MERGE (a)-[r:{rel_type}]->(b)
        """
        try:
            self.run_query(query, {"batch": edges_data})
        except GraphQueryError:
            logger.warning("APOC 미설치. 벌크 엣지에서 속성 설정 생략.")
            self.run_query(fallback_query, {"batch": edges_data})
        return len(edges_data)

    # ------------------------------------------------------------------
    # 범용 쿼리
    # ------------------------------------------------------------------

    def run_query(self, cypher: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """임의 Cypher 실행. 결과를 List[Dict]로 반환."""
        try:
            with self.driver.session() as session:
                result = session.run(cypher, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            raise GraphQueryError(f"Cypher 실행 실패: {e}\nQuery: {cypher}") from e

    # ------------------------------------------------------------------
    # 유틸
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Neo4j 연결 상태 확인"""
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    def node_count(self, label: str = "Stock") -> int:
        """특정 라벨의 노드 수 반환"""
        result = self.run_query(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        return result[0]["cnt"] if result else 0

    def edge_count(self, rel_type: str | None = None) -> int:
        """관계 수 반환. rel_type 지정 시 해당 타입만."""
        if rel_type:
            result = self.run_query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS cnt")
        else:
            result = self.run_query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        return result[0]["cnt"] if result else 0
```

### 4-3. \_\_init\_\_.py (팩토리 함수)

```python
# chainsight/graph/__init__.py

from __future__ import annotations

_repository = None


def get_graph_repository():
    """
    GraphRepository 싱글턴 팩토리.
    ⚠️ PID 기반 driver 재생성은 Neo4jGraphRepository 내부에서 처리하므로
    이 레벨에서는 단순 싱글턴으로 충분하다.
    """
    global _repository
    if _repository is None:
        from django.conf import settings
        from .repository import Neo4jGraphRepository
        _repository = Neo4jGraphRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
        )
    return _repository
```

---

## 5. 테스트

### 5-1. 수동 테스트 (Django shell)

```bash
python manage.py shell
```

```python
from chainsight.graph import get_graph_repository

repo = get_graph_repository()

# 1) 연결 확인
print("Health:", repo.health_check())  # True

# 2) 쓰기 테스트 — 노드 생성
repo.upsert_node("Stock", "ticker", "TEST001", {
    "name": "Test Company",
    "sector": "Technology",
})
print("노드 생성 OK")

# 3) 읽기 테스트 — 노드 조회
node = repo.get_node("TEST001")
print("조회 결과:", node)
# → {'ticker': 'TEST001', 'name': 'Test Company', 'sector': 'Technology'}

# 4) 엣지 테스트 — 두 번째 노드 + 관계
repo.upsert_node("Stock", "ticker", "TEST002", {
    "name": "Test Company 2",
    "sector": "Technology",
})
repo.upsert_edge("TEST001", "TEST002", "PEER_OF", {"source": "test"})
print("엣지 생성 OK")

# 5) 이웃 조회 테스트
result = repo.get_neighbors("TEST001", depth=1)
print("이웃:", result)

# 6) 카운트 확인
print("Stock 노드 수:", repo.node_count("Stock"))
print("PEER_OF 수:", repo.edge_count("PEER_OF"))

# 7) 테스트 데이터 정리
repo.run_query("MATCH (n:Stock) WHERE n.ticker STARTS WITH 'TEST' DETACH DELETE n")
print("테스트 데이터 정리 OK")
print("정리 후 Stock 수:", repo.node_count("Stock"))  # 0
```

### 5-2. 자동 테스트 (pytest)

`chainsight/tests/test_graph_repository.py` 생성:

```python
# chainsight/tests/test_graph_repository.py

import pytest
from django.conf import settings
from chainsight.graph.repository import Neo4jGraphRepository
from chainsight.graph.exceptions import GraphConnectionError


@pytest.fixture
def repo():
    """테스트용 Neo4j repository. 테스트 후 정리."""
    r = Neo4jGraphRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )
    yield r
    # teardown: 테스트 노드 정리
    try:
        r.run_query("MATCH (n:Stock) WHERE n.ticker STARTS WITH 'TEST_' DETACH DELETE n")
    except Exception:
        pass
    r.close()


class TestNeo4jConnection:
    def test_health_check(self, repo):
        assert repo.health_check() is True

    def test_invalid_connection(self):
        bad_repo = Neo4jGraphRepository("bolt://localhost:9999", "no", "no")
        assert bad_repo.health_check() is False


class TestNodeOperations:
    def test_upsert_and_get_node(self, repo):
        repo.upsert_node("Stock", "ticker", "TEST_AAPL", {
            "name": "Apple Inc.",
            "sector": "Technology",
        })
        node = repo.get_node("TEST_AAPL")
        assert node is not None
        assert node["name"] == "Apple Inc."
        assert node["sector"] == "Technology"

    def test_get_nonexistent_node(self, repo):
        node = repo.get_node("TEST_NONEXISTENT")
        assert node is None

    def test_upsert_updates_existing(self, repo):
        repo.upsert_node("Stock", "ticker", "TEST_UPD", {"name": "Old Name"})
        repo.upsert_node("Stock", "ticker", "TEST_UPD", {"name": "New Name"})
        node = repo.get_node("TEST_UPD")
        assert node["name"] == "New Name"


class TestEdgeOperations:
    def test_upsert_and_query_edge(self, repo):
        repo.upsert_node("Stock", "ticker", "TEST_A", {"name": "A"})
        repo.upsert_node("Stock", "ticker", "TEST_B", {"name": "B"})
        repo.upsert_edge("TEST_A", "TEST_B", "PEER_OF", {"source": "test"})

        result = repo.run_query("""
            MATCH (a:Stock {ticker: 'TEST_A'})-[r:PEER_OF]->(b:Stock {ticker: 'TEST_B'})
            RETURN r.source AS source
        """)
        assert len(result) == 1
        assert result[0]["source"] == "test"

    def test_get_neighbors(self, repo):
        repo.upsert_node("Stock", "ticker", "TEST_C", {"name": "Center"})
        repo.upsert_node("Stock", "ticker", "TEST_N1", {"name": "Neighbor 1"})
        repo.upsert_node("Stock", "ticker", "TEST_N2", {"name": "Neighbor 2"})
        repo.upsert_edge("TEST_C", "TEST_N1", "PEER_OF", {})
        repo.upsert_edge("TEST_C", "TEST_N2", "PEER_OF", {})

        result = repo.get_neighbors("TEST_C", depth=1)
        assert result["center"] is not None
        # center + 2 neighbors
        assert len(result["nodes"]) >= 3
        assert len(result["edges"]) >= 2


class TestBulkOperations:
    def test_bulk_upsert_nodes(self, repo):
        nodes = [
            {"ticker": "TEST_B1", "name": "Bulk 1"},
            {"ticker": "TEST_B2", "name": "Bulk 2"},
            {"ticker": "TEST_B3", "name": "Bulk 3"},
        ]
        count = repo.bulk_upsert_nodes("Stock", "ticker", nodes)
        assert count == 3
        assert repo.get_node("TEST_B2") is not None


class TestUtilMethods:
    def test_node_count(self, repo):
        initial = repo.node_count("Stock")
        repo.upsert_node("Stock", "ticker", "TEST_CNT", {"name": "Count Test"})
        assert repo.node_count("Stock") == initial + 1
```

실행:

```bash
pytest chainsight/tests/test_graph_repository.py -v
```

---

## 완료 기준 체크리스트

```
□ chainsight/graph/ 디렉토리 생성 (3개 파일)
□ config/settings.py에 NEO4J_URI/USER/PASSWORD 추가
□ .env에 Neo4j 접속 정보 추가
□ Django shell 수동 테스트 7개 항목 전부 통과
□ pytest 자동 테스트 전부 통과
□ 테스트 데이터 정리 확인 (Neo4j에 TEST_ 노드 없음)
```

---

## 완료 기록 작성

`docs/chain_sight/task_done/CS-0-2_neo4j_driver.md` 작성:

```markdown
# CS-0-2: Neo4j 연결 레이어 구현

> **완료일**: 2026-04-XX
> **소요 시간**: XX시간

## 생성된 파일

- chainsight/graph/**init**.py
- chainsight/graph/repository.py
- chainsight/graph/exceptions.py
- chainsight/tests/test_graph_repository.py

## 설정 변경

- config/settings.py: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD 추가
- .env: Neo4j 접속 정보 추가

## 테스트 결과

- 수동 테스트: 7/7 통과
- pytest: X/X 통과

## 주요 설계 결정

- PID 기반 lazy driver 초기화 (Celery fork 안전)
- Protocol 기반 인터페이스 (백엔드 교체 가능)
- APOC 없는 환경 fallback 포함

## 발견된 이슈

- (있으면 기록)

## 다음 작업 연결

- CS-0-3: Neo4j 온톨로지 스키마 초기화
```

---

## 다음 작업

→ **CS-0-3**: Neo4j 온톨로지 스키마 초기화 (constraint + index + management command)

**END OF DOCUMENT**
