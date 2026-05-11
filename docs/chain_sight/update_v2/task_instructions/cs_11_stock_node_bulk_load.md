# CS-1-1: Stock 노드 벌크 로드

> **작업 번호**: CS-1-1
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: S&P 500 :Stock 노드 500개 Neo4j 적재
> **예상 소요**: 2~3시간
> **선행 조건**: CS-0-3 완료
> **산출물**: management command `load_stocks_to_neo4j`

---

## 데이터 소스

`stocks/Stock` 테이블에서 읽기 (ticker, name, sector, industry, market_cap).

## 구현

```python
# management command: load_stocks_to_neo4j
from chainsight.graph.repository import Neo4jGraphRepository

stocks = Stock.objects.filter(is_active=True)  # S&P 500 대상
for stock in stocks:
    repo.upsert_node("Stock", {
        "ticker": stock.symbol,
        "name": stock.name,
        "sector": stock.sector,
        "industry": stock.industry,
        "market_cap": stock.market_cap,
    })
```

⚠️ 벌크 로드 시 UNWIND 사용 권장 (개별 upsert 대비 ~10배 빠름).

## 완료 기준

```
□ :Stock 노드 ~500개 생성
□ MATCH (s:Stock) RETURN count(s)  → ~500
□ 각 노드에 ticker, name, sector, industry, market_cap 속성 확인
□ 중복 실행 시 데이터 덮어쓰기 (MERGE 사용)
```

→ **다음**: cs_12

**END OF DOCUMENT**
