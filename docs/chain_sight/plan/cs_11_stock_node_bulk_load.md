# CS-1-1: Stock 노드 벌크 로드

> **작업 번호**: CS-1-1
> **목표**: PostgreSQL Stock → Neo4j :Stock 노드 ~500개
> **예상 소요**: 2~3시간
> **선행 조건**: Phase 0 완료
> **산출물**: `management/commands/load_stocks_to_neo4j.py`

---

## 1. 데이터 원천 확인

```python
from stocks.models import Stock
print(f"전체 종목: {Stock.objects.count()}")
sample = Stock.objects.first()
for f in ['symbol', 'name', 'sector', 'industry', 'market_cap', 'exchange']:
    print(f"  {f}: {hasattr(sample, f)} → {getattr(sample, f, 'N/A')}")
```

⚠️ 실제 필드명 확인 후 STOCK_FIELD_MAP 조정 (symbol vs ticker 등).

## 2. 노드 속성 매핑

| Neo4j | Django | 필수 |
|-------|--------|------|
| ticker | Stock.symbol | ✅ |
| name | Stock.name | ✅ |
| sector | Stock.sector | ✅ |
| industry | Stock.industry | ✅ |
| market_cap | Stock.market_cap | 선택 |
| exchange | Stock.exchange | 선택 |

Phase 2 이후 채워지는 속성: growth_stage, sensitivity_vector, capital_dna, pagerank_score, community_id

## 3. 구현

서비스: `chainsight/services.py` — `get_stock_data_for_neo4j()`, `load_stocks_to_neo4j(batch_size=100)`
커맨드: `load_stocks_to_neo4j --limit N --dry-run --exchange NYSE`

bulk_upsert_nodes (CS-0-2)를 배치 100개 단위로 사용.

## 4. 검증

```python
repo = get_graph_repository()
print(f"Stock: {repo.node_count('Stock')}")         # ~500
dup = repo.run_query("MATCH (s:Stock) WITH s.ticker AS t, count(*) AS c WHERE c>1 RETURN t,c")
assert len(dup) == 0
```

## 완료 기준

```
□ :Stock 노드 ~500개
□ 중복 ticker 없음
□ 필수 속성 null 최소화
```

→ **다음**: cs_12

**END OF DOCUMENT**
