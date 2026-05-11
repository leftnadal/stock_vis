# CS-1-3: Peer 관계 로드

> **작업 번호**: CS-1-3
> **목표**: PEER_OF 2,500~3,500개 → Phase 1 완료, M1 달성
> **예상 소요**: 3~5시간 (API 호출 포함)
> **선행 조건**: CS-1-2 완료 + CS-0-0 API 테스트 결과 참조
> **산출물**: Celery task, `management/commands/load_peers_to_neo4j.py`

---

## 전략

- **Finnhub Peers**: 주 소스 (무료, 확인됨). Rate limit 60/min → ~9분.
- **FMP Stock Peers**: CS-0-0 결과 200이면 보조 소스. 403이면 미사용.
- **undirected 정규화**: `normalize_pair()` 사용 (symbol_a < symbol_b).
- **source 속성**: "finnhub" / "fmp" / "finnhub,fmp" 기록.

## 구현

`chainsight/services.py`: `fetch_finnhub_peers()`, `fetch_fmp_peers()`, `collect_all_peers()`, `load_peers_to_neo4j()`
`chainsight/tasks/peer_tasks.py`: `fetch_and_load_peers` Celery task
커맨드: `load_peers_to_neo4j --use-fmp --limit 10 --dry-run --celery`

## Phase 1 완료 검증

```python
repo = get_graph_repository()
print(f"Stock: {repo.node_count('Stock')}")       # ~500
print(f"Sector: {repo.node_count('Sector')}")     # ~11
print(f"Industry: {repo.node_count('Industry')}")  # ~70
print(f"BTS: {repo.edge_count('BELONGS_TO_SECTOR')}")
print(f"BTI: {repo.edge_count('BELONGS_TO_INDUSTRY')}")
print(f"PEER_OF: {repo.edge_count('PEER_OF')}")   # ~2,500~3,500

# 파도타기 2-hop 테스트
trace = repo.run_query("""
    MATCH (s:Stock {ticker:'AAPL'})-[:PEER_OF]-(h1)-[:PEER_OF]-(h2)
    WHERE h2<>s RETURN DISTINCT h2.ticker LIMIT 20
""")
print(f"AAPL 2-hop: {len(trace)}개 도달")
```

## 완료 기준

```
□ PEER_OF 2,500~3,500개
□ 파도타기 2-hop 동작
□ 노드 ~580개, 관계 ~4,500개

★ M1 달성: "그래프에 데이터가 있음"
```

→ **다음**: cs_21

**END OF DOCUMENT**
