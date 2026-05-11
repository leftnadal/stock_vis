# CS-3-1: ChainProfile → Neo4j 속성 동기화

> **작업 번호**: CS-3-1
> **목표**: neo4j_synced=False인 ChainProfile → Neo4j :Stock 노드 속성 Delta Sync
> **예상 소요**: 1일
> **선행 조건**: CS-2-5 완료
> **산출물**: `chainsight/tasks/sync_tasks.py` (sync_profiles_to_neo4j)

---

## 동기화 전략

- 방식: Delta Sync (neo4j_synced == False만)
- 주기: 주 1회 (CS-2-5 집약 후, Celery Beat 05:30 — cs_25에서 등록 완료)
- 실패: 로깅 + 다음 주기 재시도 (neo4j_synced 그대로 False)

## 구현

```python
@shared_task
def sync_profiles_to_neo4j(batch_size=50):
    pending = CompanyChainProfile.objects.filter(neo4j_synced=False)
    for profile in pending.iterator():
        props = _profile_to_neo4j_props(profile)
        repo.run_query("MATCH (s:Stock {ticker:$t}) SET s += $p",
                       {"t": profile.symbol, "p": props})
        profile.neo4j_synced = True
        profile.neo4j_synced_at = timezone.now()
        profile.save(update_fields=["neo4j_synced", "neo4j_synced_at"])
```

## 검증

```python
node = repo.get_node("AAPL")
print(f"growth_stage: {node.get('growth_stage')}")
pending = CompanyChainProfile.objects.filter(neo4j_synced=False).count()
assert pending == 0
```

## 완료 기준

```
□ Delta Sync 동작 (False → True)
□ Neo4j :Stock 노드에 프로파일 속성 반영
□ 재실행 시 synced=True 스킵
```

→ **다음**: cs_32

**END OF DOCUMENT**
