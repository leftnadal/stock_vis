# CS-3-2: RelationConfidence → Neo4j 엣지 동기화

> **작업 번호**: CS-3-2
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: confirmed 또는 probable만 엣지 생성
> **예상 소요**: 1~2일
> **선행 조건**: CS-3-1 완료
> **산출물**: sync task

---

## 동기화 규칙

- **Truth 관계**: confirmed 또는 probable → Neo4j 엣지 생성
- **Market 관계**: 보조 속성으로 첨부 (별도 엣지 아님)
- hidden/weak/stale → Neo4j에 엣지 생성하지 않음 (기존 엣지가 있으면 삭제)

## 구현

```python
@shared_task
def sync_relations_to_neo4j():
    relations = RelationConfidence.objects.filter(
        synced_to_neo4j=False,
        relation_category='truth',
        relation_status__in=['confirmed', 'probable']
    )
    for rel in relations:
        repo.upsert_edge(rel.symbol_a, rel.symbol_b, rel.relation_type, {
            "truth_score": rel.truth_score,
            "status": rel.relation_status,
            "basis_summary": rel.relation_basis_summary,
        })
        rel.synced_to_neo4j = True
        rel.save(update_fields=['synced_to_neo4j'])
```

## 완료 기준

```
□ confirmed/probable 관계만 Neo4j 엣지 생성
□ hidden/weak/stale 관계는 엣지 미생성 (삭제)
□ Market 관계는 보조 속성으로만 처리
```

→ **다음**: cs_33

**END OF DOCUMENT**
