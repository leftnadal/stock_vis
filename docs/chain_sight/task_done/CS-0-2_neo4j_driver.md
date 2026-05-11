# CS-0-2: Neo4j 연결 레이어 구현

> **완료일**: 2026-04-02
> **소요 시간**: 30분

## 생성된 파일

- chainsight/graph/__init__.py — get_graph_repository() 팩토리
- chainsight/graph/repository.py — Neo4jGraphRepository (Protocol + 구현)
- chainsight/graph/exceptions.py — GraphConnectionError, GraphQueryError

## 설정 변경

- config/settings.py: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD 추가

## 주요 설계 결정

- PID 기반 lazy driver 초기화 (Celery fork 안전)
- Protocol 기반 인터페이스 (백엔드 교체 가능)
- bulk_upsert_nodes/edges: UNWIND 벌크 처리
- APOC 미설치 환경 fallback (get_neighbors depth=1 only)

## 테스트 결과

- Neo4j 서버 연결 테스트: CS-0-3에서 init_neo4j_schema 실행 시 확인 예정

## 다음 작업 연결

- CS-0-3: Neo4j 온톨로지 스키마 초기화
