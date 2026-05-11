# CS-3-3: GDS 알고리즘 배치

> **작업 번호**: CS-3-3
> **목표**: PageRank, Louvain Community, Betweenness Centrality → 노드 속성
> **예상 소요**: 1일
> **선행 조건**: CS-3-2 완료
> **산출물**: `chainsight/tasks/gds_tasks.py`

---

## GDS 의존성

⚠️ Neo4j GDS 별도 설치 필요 (Self-hosted Community: 무료. AuraDB Free: 미지원).

## 구현

```python
@shared_task
def run_gds_algorithms():
    # 0) 기존 projection 삭제
    # 1) graph.project('chainsight', 'Stock', {PEER_OF, BELONGS_TO_INDUSTRY, ...})
    # 2) gds.pageRank.write → pagerank_score
    # 3) gds.louvain.write → community_id
    # 4) gds.betweenness.write → betweenness_score
    # 5) projection 삭제
```

## 검증

```python
# PageRank Top 10
repo.run_query("MATCH (s:Stock) RETURN s.ticker, s.pagerank_score ORDER BY s.pagerank_score DESC LIMIT 10")
# Community 분포
repo.run_query("MATCH (s:Stock) RETURN s.community_id, count(s), collect(s.ticker)[..5] ORDER BY count(s) DESC LIMIT 10")
```

## 완료 기준

```
□ GDS 플러그인 설치 확인
□ pagerank_score, community_id, betweenness_score 노드 속성 반영
□ Top 10 합리성 확인

★ M3 달성: "Neo4j가 풍부해짐"
```

→ **다음**: cs_41

**END OF DOCUMENT**
