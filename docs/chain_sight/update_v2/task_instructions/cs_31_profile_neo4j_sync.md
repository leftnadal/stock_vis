# CS-3-1: ChainProfile → Neo4j 속성 동기화

> **작업 번호**: CS-3-1
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: :Stock 노드에 프로파일 속성 반영
> **예상 소요**: 1~2일
> **선행 조건**: CS-2-5 완료
> **산출물**: sync task

---

## 동기화 전략: Delta Sync

```
식별 기준: CompanyChainProfile.neo4j_synced == False
주기: 주 1회 (Celery Beat — CS-2-5에서 등록 완료)
실패 처리: 실패 건 로깅 + 다음 주기에 재시도
```

## 구현

```python
@shared_task
def sync_profiles_to_neo4j():
    profiles = CompanyChainProfile.objects.filter(neo4j_synced=False)
    for profile in profiles:
        repo.upsert_node("Stock", {
            "ticker": profile.symbol,
            "growth_stage": profile.growth_stage,
            "sensitivity_vector": [...],
            "capital_dna": [...],
            # 30개 score 필드
        })
        profile.neo4j_synced = True
        profile.neo4j_synced_at = timezone.now()
        profile.save(update_fields=['neo4j_synced', 'neo4j_synced_at'])
```

## 완료 기준

```
□ neo4j_synced=False인 프로파일 → Neo4j 반영
□ 동기화 후 neo4j_synced=True, neo4j_synced_at 기록
□ 실패 건 로깅 확인
```

→ **다음**: cs_32

**END OF DOCUMENT**
