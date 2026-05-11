# CS-0-2: Neo4j 연결 레이어 구현

> **작업 번호**: CS-0-2
> **목표**: GraphRepository 구현 + 읽기/쓰기 테스트 통과
> **예상 소요**: 2~3시간
> **선행 조건**: CS-0-1 완료, Neo4j 서버 구동
> **산출물**: `chainsight/graph/repository.py`, `chainsight/graph/__init__.py`, 테스트

---

## ⚠️ 로드맵 대비 변경 사항

로드맵 CS-0-2의 Protocol 시그니처를 아래와 같이 확장한다.
이 변경은 Phase 1 벌크 로드에 필수이므로 로드맵도 함께 업데이트할 것.

- `upsert_node(label, properties)` → `upsert_node(label, key_field, key_value, properties)` (MERGE에 key 필요)
- 추가 메서드: `bulk_upsert_nodes`, `bulk_upsert_edges`, `health_check`, `node_count`, `edge_count`, `close`

---

## 1. 설정

```python
# config/settings.py
NEO4J_URI = env('NEO4J_URI', default='bolt://localhost:7687')
NEO4J_USER = env('NEO4J_USER', default='neo4j')
NEO4J_PASSWORD = env('NEO4J_PASSWORD', default='password')
```

## 2. 디렉토리

```
chainsight/graph/
├── __init__.py       ← get_graph_repository() 팩토리
├── repository.py     ← Protocol + Neo4jGraphRepository
└── exceptions.py     ← GraphConnectionError, GraphQueryError
```

## 3. 핵심 구현

### repository.py

```python
class GraphRepository(Protocol):
    def get_node(self, ticker: str) -> Dict[str, Any] | None: ...
    def get_neighbors(self, ticker: str, depth: int = 1,
                      rel_types: List[str] | None = None) -> Dict: ...
    def upsert_node(self, label: str, key_field: str, key_value: str,
                    properties: Dict[str, Any]) -> None: ...
    def upsert_edge(self, from_ticker: str, to_ticker: str,
                    rel_type: str, properties: Dict[str, Any]) -> None: ...
    def bulk_upsert_nodes(self, label: str, key_field: str,
                          nodes_data: List[Dict]) -> int: ...
    def run_query(self, cypher: str, params: Dict | None = None) -> List[Dict]: ...
    def health_check(self) -> bool: ...
    def node_count(self, label: str = "Stock") -> int: ...
    def edge_count(self, rel_type: str | None = None) -> int: ...
    def close(self) -> None: ...

class Neo4jGraphRepository:
    """
    ⚠️ PID 기반 lazy initialization (Celery prefork fork 안전)
    """
    def __init__(self, uri, user, password):
        self._uri, self._user, self._password = uri, user, password
        self._driver, self._pid = None, None

    @property
    def driver(self):
        import os
        if self._driver is None or self._pid != os.getpid():
            from neo4j import GraphDatabase
            if self._driver: self._driver.close()
            self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            self._pid = os.getpid()
        return self._driver
```

### \_\_init\_\_.py

```python
_repository = None
def get_graph_repository():
    global _repository
    if _repository is None:
        from django.conf import settings
        from .repository import Neo4jGraphRepository
        _repository = Neo4jGraphRepository(
            settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    return _repository
```

## 4. 테스트 (Django shell)

```python
from chainsight.graph import get_graph_repository
repo = get_graph_repository()
print("Health:", repo.health_check())
repo.upsert_node("Stock", "ticker", "TEST001", {"name": "Test"})
print("Node:", repo.get_node("TEST001"))
repo.run_query("MATCH (n:Stock) WHERE n.ticker STARTS WITH 'TEST' DETACH DELETE n")
```

pytest: `chainsight/tests/test_graph_repository.py` 작성 (연결, CRUD, 벌크 테스트)

---

## 완료 기준

```
□ graph/ 디렉토리 3개 파일
□ settings.py + .env Neo4j 설정
□ 수동 테스트 통과 (health, upsert, get, delete)
□ pytest 전부 통과
```

→ **다음**: cs_03

**END OF DOCUMENT**
