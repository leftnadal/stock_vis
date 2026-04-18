# CS-2-4: RelationConfidence 종합 판정

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 결과

- **RelationConfidence 총 건수**: 10,738

### 상태 분포

| 상태 | 건수 | 비율 |
|------|------|------|
| confirmed | 2,028 | 18.9% |
| probable | 7,482 | 69.7% |
| weak | 1,228 | 11.4% |
| hidden | 0 | 0% |

### 타입 분포

| 관계 타입 | 건수 | 카테고리 |
|----------|------|---------|
| PEER_OF | 9,345 | truth |
| PRICE_CORRELATED | 1,162 | market |
| CO_MENTIONED | 227 | market |
| SUPPLIES_TO | 4 | truth (SEC pipeline) |

### 구현된 로직

- 증거 수집: peer, industry, news(co_mention), price(correlation)
- Tier 판정: 3+ sources=Tier1(confirmed/85), 2+=Tier2(probable/60), 1=Tier3(weak/35)
- Market 관계 (CO_MENTIONED, PRICE_CORRELATED): 독립 점수 기준 (count/corr 기반)
- stale decay: `check_stale_and_decay` (주간 토요일 04:00)
- 7개 bool 플래그: has_peer/industry/supply_chain/news/price/etf/llm_source

★ M2 달성: "관계 신뢰도 엔진 작동"

→ 다음: cs_25
