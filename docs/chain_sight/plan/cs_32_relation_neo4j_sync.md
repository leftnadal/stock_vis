# CS-3-2: RelationConfidence → Neo4j 엣지 동기화

> **작업 번호**: CS-3-2
> **목표**: confirmed/probable Truth 관계 → Neo4j 엣지, Market 관계 → 보조 속성
> **예상 소요**: 1일
> **선행 조건**: CS-2-4 + CS-3-1 완료
> **산출물**: sync_relations_to_neo4j task

---

## 동기화 규칙 (로드맵 v1.3)

| 조건 | 동작 |
|------|------|
| Truth + confirmed/probable | Neo4j 엣지 MERGE |
| Truth + stale/hidden/weak (이전에 synced) | Neo4j 엣지 DELETE |
| Market (CO_MENTIONED, PRICE_CORRELATED) | 기존 엣지에 보조 속성 첨부 |

## ⚠️ 점검 결과 반영: CUSTOMER_OF 역방향 처리

이 task에서 SUPPLIES_TO 엣지를 동기화할 때, Neo4j에는 **SUPPLIES_TO 방향만** 저장한다.
CUSTOMER_OF는 CS-4-1 API에서 역방향 view로 파생한다 (로드맵 v1.3 규칙).

## 구현 핵심

```python
@shared_task
def sync_relations_to_neo4j():
    """Celery Beat: 주 1회 (일요일 06:00 — cs_25에서 등록 완료)"""
    # 1) confirmed/probable Truth → 엣지 MERGE + 속성
    # 2) stale/hidden/weak (synced=True) → 엣지 DELETE
    # 3) Market → 기존 엣지에 co_mention_count/price_correlation 속성 첨부
```

엣지 속성: confidence_status, truth_score, evidence_tier, basis_summary

## 완료 기준

```
□ confirmed/probable → Neo4j 엣지 생성
□ stale/hidden → Neo4j 엣지 삭제
□ Market 보조 속성 첨부
□ synced_to_neo4j 플래그 정상
```

→ **다음**: cs_33

**END OF DOCUMENT**
