# CS-3-2: RelationConfidence → Neo4j 엣지 동기화

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 결과

- confirmed/probable → 엣지 생성 ✅
- hidden/weak/stale → 엣지 미생성 (삭제) ✅
- dirty sync 패턴: `neo4j_dirty=True` → 동기화 → `False`
- 동적 엣지 타입: PEER_OF, SUPPLIES_TO, CO_MENTIONED, PRICE_CORRELATED ✅
- basis_summary 속성 포함 ✅

### Neo4j 엣지 현황

| 타입 | 건수 |
|------|------|
| PEER_OF | 12,180 |
| PRICE_CORRELATED | 1,162 |
| CO_MENTIONED | 195 |
| SUPPLIES_TO | 4 |

→ 다음: cs_33
