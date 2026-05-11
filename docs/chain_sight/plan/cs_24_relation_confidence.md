# CS-2-4: RelationConfidence 종합 판정

> **작업 번호**: CS-2-4
> **목표**: RELATION_CONFIDENCE.md 정책표 기반 모든 관계의 신뢰도 종합 판정
> **예상 소요**: 2~3일 (Phase 2 핵심)
> **선행 조건**: CS-2-2, CS-2-3, RELATION_CONFIDENCE.md
> **산출물**: update_relation_confidence + check_stale_and_decay tasks

---

## 판정 흐름

```
PEER_OF (Neo4j)           → has_peer_source
BELONGS_TO_INDUSTRY        → has_industry_source
SUPPLIES_TO (수동/Gemini)  → has_supply_chain_source
CoMentionEdge              → has_news_source
PriceCoMovement            → has_price_source
ETF (DC-2 이후)            → has_etf_source
LLM (DC-4 이후)            → has_llm_source
         ↓
RelationConfidence: tier + score + status + summary
```

## 증거 등급 + 상태 매핑

| Tier | 조건 | → 상태 | truth_score |
|------|------|--------|-------------|
| 1 | supply chain 공시 등 | confirmed | 85 |
| 2 | 2개+ 독립 소스 교차 | probable | 60 |
| 3 | 단일 소스/간접 증거 | weak | 35 |
| - | 증거 없음 | hidden | 15 |

## 구현 핵심

```python
@shared_task
def update_relation_confidence():
    """Celery Beat: 주 1회 (일요일 04:00). RELATION_CONFIDENCE.md 정책표 기반."""
    # 1) 모든 관계 후보 수집 (Neo4j PEER_OF + same industry + PG CoMention + PriceCorr)
    # 2) 각 후보: 증거 평가 → tier → status → truth_score → summary
    # 3) RelationConfidence upsert (synced_to_neo4j=False)

@shared_task
def check_stale_and_decay():
    """Celery Beat: 주 1회 (일요일 04:30). 하향 전이."""
    # confirmed (90일 미갱신) → stale
    # probable (60일) → weak
    # weak (30일) → hidden
```

relation_category: Market 관계(CO_MENTIONED, PRICE_CORRELATED)는 truth_score 비대상.
canonical_direction: undirected = "both", directed = "a→b".

## 완료 기준

```
□ RelationConfidence 적재 확인
□ 상태 분포: hidden / weak / probable / confirmed 확인
□ relation_basis_summary 텍스트 합리성
□ stale decay 동작 확인
```

→ **다음**: cs_25

**END OF DOCUMENT**
