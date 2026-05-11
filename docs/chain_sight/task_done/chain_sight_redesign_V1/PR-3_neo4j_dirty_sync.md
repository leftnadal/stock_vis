# PR-3: Neo4j Dirty Sync 개선

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`

## 목표

`neo4j_dirty` 플래그 기반 Neo4j 동기화 패턴으로 전환. 변경된 RelationConfidence만 선택적 동기화.

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `chainsight/services/neo4j_sync.py` | `sync_dirty_relations()` 서비스 |
| `chainsight/tasks/neo4j_dirty_sync_tasks.py` | `run_neo4j_dirty_sync` Celery task |

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `config/celery.py` | `chainsight-neo4j-dirty-sync` beat 등록 (매주 일 04:30) + task route (neo4j queue) |

## 동기화 로직

| 상태 | 동작 |
|------|------|
| `confirmed`, `probable` | 엣지 upsert (`repo.upsert_edge()`) |
| `hidden`, `weak`, `stale` | 엣지 삭제 (Cypher DELETE) |

## 핵심 규약

1. **undirected 관계 정규화**: `PEER_OF`, `COMPETES_WITH`, `CO_MENTIONED`, `PRICE_CORRELATED`는 `normalize_pair()` 적용 (symbol_a < symbol_b)
2. **queryset.update() 사용**: sync 후 `neo4j_dirty=False` 설정 시 `save()` 호출 금지 (dirty가 다시 True로 덮어씌워지므로)
3. **iterator(chunk_size=100)**: 메모리 효율적 대량 처리
4. **개별 에러 처리**: 한 레코드 실패해도 나머지 계속 처리

## Celery Beat 스케줄

```python
'chainsight-neo4j-dirty-sync': {
    'task': 'chainsight-neo4j-dirty-sync',
    'schedule': crontab(hour=4, minute=30, day_of_week=0),  # 매주 일요일
    'options': {'expires': 3600, 'queue': 'neo4j'}
}
```
