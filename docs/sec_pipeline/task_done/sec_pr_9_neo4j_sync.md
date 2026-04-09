# SEC-PR-9: sync_dirty_to_neo4j

> **완료일**: 2026-04-04

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `sec_pipeline/tasks.py` | sync_dirty_to_neo4j 추가 |

## 동기화 로직

```
Phase A: PG transaction (select_for_update, skip_locked)
  → dirty=True, target≠null인 evidence 최대 500건 lock + dict 복사

Phase B: Neo4j session
  → DELETE 기존 sec_10k origin edge (6개 known_types 전체)
  → CREATE 새 edge (dynamic type: SUPPLIES_TO, CUSTOMER_OF, etc.)

Phase C: PG update
  → 성공한 건 neo4j_dirty=False + neo4j_synced_at
```

## 설계 원칙 준수

| 원칙 | 준수 |
|------|------|
| MERGE 금지 | ✅ DELETE + CREATE 패턴 |
| RELATED_TO 고정 type 금지 | ✅ dynamic type (CUSTOMER_OF 등) |
| known_types에 RELATED_TO 포함 (레거시 정리) | ✅ |
| Phase 1 sole writer | ✅ |
| dirty flag만 (synced_to_neo4j 금지) | ✅ |
| Beat 1개 전제 + idempotent | ✅ select_for_update(skip_locked) |

## 테스트 결과

```
Dirty rows: 2 (NVDA→MU, PG→WMT)
Synced: 2/2

Neo4j 확인:
  PG -[CUSTOMER_OF]-> WMT (grade=high, source=sec_10k)
  NVDA -[CUSTOMER_OF]-> MU (grade=high, source=sec_10k)
```

## 다음 PR

→ SEC-PR-10: 관계 병합 + 미매칭 큐 처리
