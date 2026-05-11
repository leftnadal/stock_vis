# CS-2-3: PriceCoMovement 계산

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 결과

- **PriceCoMovement**: 8,653건 ✅
- 90일 rolling correlation
- undirected 정규화 (symbol_a < symbol_b)
- Celery task: `calculate_price_co_movement` (주간 토요일 03:00)

→ 다음: cs_24
