# CS-2-4: RelationConfidence 종합 판정

> **완료일**: 2026-04-03

## 생성/수정된 파일

- `chainsight/tasks/relation_tasks.py` (update_relation_confidence, check_stale_and_decay)

## 결과

- RelationConfidence 레코드: **3,527건**
- CoMentionEdge 744쌍 + PriceCoMovement 2,473쌍 → 종합 신뢰도 계산
- 3-tier 점수: truth_score, market_score, investment_relevance
- 5단계 상태 분류: hidden / weak / probable / confirmed / stale

### 상태 분포

| 상태 | 기준 | 비고 |
|------|------|------|
| confirmed | truth_score ≥ 0.8 | PEER_OF 기반 |
| probable | truth_score ≥ 0.5 | co-mention + price correlation |
| weak | truth_score ≥ 0.2 | 단일 소스 |
| hidden | truth_score < 0.2 | 추후 보강 필요 |
| stale | 90일 초과 미갱신 | decay 대상 |

### evidence_sources 활용

7개 boolean 필드:
- `has_peer_of`: Finnhub/FMP Peer 데이터
- `has_co_mention`: 뉴스 공동 언급
- `has_price_corr`: 가격 상관관계
- `has_supply_chain`, `has_etf_peer`, `has_institutional`, `has_llm_relation`

## 다음 작업

→ CS-2-5: CompanyChainProfile 집계
