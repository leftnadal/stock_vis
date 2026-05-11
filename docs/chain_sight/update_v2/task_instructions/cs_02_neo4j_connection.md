# CS-0-2: Neo4j 연결 레이어 구현

> **작업 번호**: CS-0-2
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: Neo4j 연결 + 간단한 읽기/쓰기 테스트 통과
> **예상 소요**: 2~3시간
> **선행 조건**: CS-0-1 완료, Neo4j 서버 구동
> **산출물**: `chainsight/graph/repository.py`

---

## 구현

### GraphRepository Protocol + Neo4jGraphRepository

```python
# chainsight/graph/repository.py
from typing import Protocol, List, Dict, Any

class GraphRepository(Protocol):
    def get_node(self, ticker: str) -> Dict[str, Any]: ...
    def get_neighbors(self, ticker: str, depth: int = 1,
                      rel_types: List[str] | None = None) -> Dict: ...
    def upsert_node(self, label: str, properties: Dict) -> None: ...
    def upsert_edge(self, from_ticker: str, to_ticker: str,
                    rel_type: str, properties: Dict) -> None: ...
    def run_query(self, cypher: str, params: Dict) -> List[Dict]: ...

class Neo4jGraphRepository:
    """
    PID 기반 lazy initialization — Celery prefork 환경에서
    driver를 global singleton으로 캐싱하면 SIGSEGV 발생.
    """
    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        self._pid = None

    @property
    def driver(self):
        import os
        if self._driver is None or self._pid != os.getpid():
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._user, self._password))
            self._pid = os.getpid()
        return self._driver
```

### 설정

```python
# config/settings.py
NEO4J_URI = env('NEO4J_URI', default='bolt://localhost:7687')
NEO4J_USER = env('NEO4J_USER', default='neo4j')
NEO4J_PASSWORD = env('NEO4J_PASSWORD', default='password')
```

## 테스트

```python
# 연결 테스트
repo = Neo4jGraphRepository(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
result = repo.run_query("RETURN 1 AS n", {})
assert result[0]['n'] == 1

# 쓰기/읽기 테스트
repo.upsert_node("Stock", {"ticker": "TEST", "name": "Test Corp"})
node = repo.get_node("TEST")
assert node['ticker'] == "TEST"
repo.run_query("MATCH (s:Stock {ticker: 'TEST'}) DELETE s", {})
```

## 완료 기준

```
□ Neo4j 연결 성공
□ 읽기/쓰기 테스트 통과
□ Celery worker에서도 연결 안전 확인
```

→ **다음**: cs_03

**END OF DOCUMENT**
