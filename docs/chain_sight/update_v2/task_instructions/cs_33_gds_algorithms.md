# CS-3-3: GDS 알고리즘 배치

> **작업 번호**: CS-3-3
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: pagerank, community_id, betweenness 노드 속성 생성
> **예상 소요**: 1~2일
> **선행 조건**: CS-3-2 완료
> **산출물**: `chainsight/tasks/gds_tasks.py`

---

## GDS 의존성

```
Neo4j GDS 플러그인 필요 (Community Edition에서 무료).
현재 MacBook self-hosted 환경에서는 문제없음.
프로덕션: GDS 포함 Docker 이미지 필요.
```

## 알고리즘 3개

### PageRank
```cypher
CALL gds.pageRank.write('stock-graph', { writeProperty: 'pagerank_score' })
```

### Community Detection (Louvain)
```cypher
CALL gds.louvain.write('stock-graph', { writeProperty: 'community_id' })
```

### Betweenness Centrality
```cypher
CALL gds.betweenness.write('stock-graph', { writeProperty: 'betweenness_score' })
```

## 완료 기준

```
□ :Stock 노드에 pagerank_score, community_id, betweenness_score 속성 생성
□ MATCH (s:Stock) WHERE s.pagerank_score IS NOT NULL RETURN count(s) → ~500
★ M3 달성: "Neo4j가 풍부해짐"
```

→ **다음**: cs_41 (Phase 4 시작)

**END OF DOCUMENT**
