# CS-0-3: Neo4j 온톨로지 스키마 초기화

> **완료일**: 2026-04-02
> **소요 시간**: 20분

## 생성된 파일

- chainsight/graph/schema.py — CONSTRAINTS 4개, INDEXES 4개, initialize/verify 함수
- chainsight/management/__init__.py
- chainsight/management/commands/__init__.py
- chainsight/management/commands/init_neo4j_schema.py

## 스키마 현황

- Constraints: 4개 (stock_ticker, sector_name, industry_name, theme_name)
- Indexes: 4개 (stock_sector, stock_community, stock_market_cap, stock_industry)

## 테스트 결과

- Neo4j 연결 + 스키마 적용: Neo4j 서버 구동 후 `python manage.py init_neo4j_schema --verify`로 검증 예정

## Phase 0 완료 상태

- CS-0-0: ✅ 레거시 정리 + API 테스트 + RelationConfidence v2.1
- CS-0-1: ✅ Migrations 검증 (12개 테이블, 28개 컬럼)
- CS-0-2: ✅ Neo4j 연결 레이어 (PID 기반 fork 안전)
- CS-0-3: ✅ 온톨로지 스키마 (constraint + index + management command)

## 다음 작업 연결

→ Phase 1 (CS-1-1): Stock 노드 벌크 로드 — S&P 500 :Stock 노드 500개 적재
