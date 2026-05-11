# CS-1-2: Sector/Industry 노드 + BELONGS_TO 관계

> **작업 번호**: CS-1-2
> **목표**: :Sector ~11개, :Industry ~70개, BELONGS_TO 관계 ~1,000개
> **예상 소요**: 2~3시간
> **선행 조건**: CS-1-1 완료
> **산출물**: `management/commands/load_sectors_to_neo4j.py`

---

## 구현

:Stock 노드의 sector/industry 속성에서 Cypher MERGE로 생성:

1. `MATCH (s:Stock) WITH DISTINCT s.sector → MERGE (sec:Sector {name})` + stock_count
2. `MATCH (s:Stock) WITH DISTINCT s.industry → MERGE (ind:Industry {name})` + sector_name, stock_count
3. `Stock -[:BELONGS_TO_SECTOR]-> Sector`
4. `Stock -[:BELONGS_TO_INDUSTRY]-> Industry`

커맨드: `load_sectors_to_neo4j --dry-run`

## 검증

```python
repo = get_graph_repository()
print(f"Sector: {repo.node_count('Sector')}")        # ~11
print(f"Industry: {repo.node_count('Industry')}")     # ~70
print(f"BTS: {repo.edge_count('BELONGS_TO_SECTOR')}")  # ~490
print(f"BTI: {repo.edge_count('BELONGS_TO_INDUSTRY')}") # ~485
```

## 완료 기준

```
□ :Sector ~11개, :Industry ~70개
□ BELONGS_TO 관계 ~1,000개
□ 고아 노드 없음
□ 멱등성 확인
```

→ **다음**: cs_13

**END OF DOCUMENT**
