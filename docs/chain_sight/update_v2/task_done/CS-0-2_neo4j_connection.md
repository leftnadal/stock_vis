# CS-0-2: Neo4j 연결 레이어 구현

> **완료일**: 2026-04-18
> **브랜치**: `tier1/code-quality-fixes`

## 상태: 이미 구현됨 — 검증 완료

`chainsight/graph/repository.py`가 이전 작업에서 이미 구현되어 있음. 지시서 요구사항 대비 검증 수행.

## 검증 결과

| # | 항목 | 결과 |
|---|------|------|
| 1 | Neo4j 연결 | ✅ `RETURN 1 AS n` → `[{'n': 1}]` |
| 2 | PID 기반 lazy init | ✅ `os.getpid()` 일치 확인 |
| 3 | 쓰기/읽기 | ✅ `upsert_node("TEST_CS02")` → `get_node("TEST_CS02")` → 정리 |
| 4 | GraphRepository Protocol | ✅ `get_node`, `get_neighbors`, `upsert_node`, `upsert_edge`, `run_query` |
| 5 | Neo4jGraphRepository | ✅ PID 기반 driver lazy init (Celery prefork 안전) |
| 6 | 설정 | ✅ `NEO4J_URI=bolt://localhost:7687`, `NEO4J_USER=neo4j` |

## Celery prefork 안전성

`Neo4jGraphRepository.driver` property가 `os.getpid()`를 체크하여 fork 후 새 프로세스에서 driver를 재생성. 기존 driver 객체가 fork되어 공유 소켓 문제(SIGSEGV)를 일으키는 것을 방지.

## 파일 구조

```
chainsight/graph/
├── __init__.py        — get_graph_repository() 싱글톤
├── repository.py      — GraphRepository Protocol + Neo4jGraphRepository
├── schema.py          — Neo4j 스키마 초기화
└── exceptions.py      — GraphConnectionError, GraphQueryError
```

## 완료 체크리스트

```
[x] Neo4j 연결 성공
[x] 읽기/쓰기 테스트 통과
[x] Celery worker에서도 연결 안전 확인 (PID 기반 lazy init)
```

→ **다음**: cs_03 (Neo4j 스키마)
