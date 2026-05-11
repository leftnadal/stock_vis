# CS-3-2: Relation → Neo4j 동기화

> **완료일**: 2026-04-03

## 생성/수정된 파일

- `chainsight/tasks/sync_tasks.py` (sync_relations_to_neo4j)

## 결과

- **1,631개** RELATED_TO edge 생성 (confirmed + probable 상태만)
- RelationConfidence 3,527건 중 status가 confirmed 또는 probable인 건만 동기화
- edge 속성: truth_score, market_score, evidence_tier_best, status

### Neo4j 관계 현황 (동기화 후)

| 관계 | 건수 | 원천 |
|------|------|------|
| PEER_OF | 8,350 | CS-1-3 |
| BELONGS_TO | 1,038 | CS-1-2 |
| RELATED_TO | 1,631 | CS-3-2 (이 작업) |

## 동기화 기준

```
status IN ('confirmed', 'probable') → Neo4j에 동기화
status IN ('hidden', 'weak', 'stale') → 동기화 제외
```

## 참고

- CS-3-1 (Profile sync)과 동시 완료, 하나의 task_done (CS-3-1)에 기록됨
- 이 문서는 누락된 개별 기록을 보완

## 다음 작업

→ CS-3-3: GDS 알고리즘 (PageRank, Louvain, Betweenness)
