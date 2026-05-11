# CS-1-1: Stock 노드 벌크 로드

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 결과

- **Stock 노드**: 792개 (S&P 500 + TSM, FN 등 추가 종목) ✅
- 속성: ticker, name, sector, industry, market_cap 확인
- MERGE 기반 멱등 (중복 실행 안전)
- Management command: `load_stocks_to_neo4j`
- 서비스: `chainsight/services/neo4j_loader.py` → `load_stocks_to_neo4j()`

→ 다음: cs_12
