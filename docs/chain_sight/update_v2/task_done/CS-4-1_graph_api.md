# CS-4-1: 그래프 탐색 API

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 결과

- `GET /api/v1/chainsight/{symbol}/graph/?depth=1` → 200 ✅
- NVDA: nodes=90, edges=124
- CUSTOMER_OF 역방향 파생: `derived_type` 필드로 구현
- explanation: `relation_basis_summary` → edge 속성
- market_signals: `co_mention_count`, `price_correlation`

→ 다음: cs_42
