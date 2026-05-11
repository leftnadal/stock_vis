# CS-1-1: Stock 노드 벌크 로드

> **완료일**: 2026-04-02

## 생성/수정된 파일

- chainsight/services.py (get_stock_data_for_neo4j, load_stocks_to_neo4j)
- chainsight/management/commands/load_stocks_to_neo4j.py

## 결과

- 로드 대상: 532개
- 성공: 532개, 실패: 0
- Neo4j :Stock 합계: 1,263개 (기존 731 + 신규 532, MERGE 중복 방지)

## 필드 매핑

- ticker ← Stock.symbol
- name ← Stock.stock_name
- sector ← Stock.sector
- industry ← Stock.industry
- market_cap ← Stock.market_capitalization
- exchange ← Stock.exchange

## 다음 작업

→ CS-1-2: Sector/Industry 노드 + BELONGS_TO 관계
