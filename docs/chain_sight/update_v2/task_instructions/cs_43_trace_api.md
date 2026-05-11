# CS-4-3: 경로 탐색 API

> **작업 번호**: CS-4-3
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: 두 종목 간 최단 경로 반환
> **예상 소요**: 1~2일
> **선행 조건**: CS-4-2 완료
> **산출물**: `GET /api/chainsight/trace/`

---

## 엔드포인트

```
GET /api/chainsight/trace/?from=NVDA&to=SMCI
Response:
{
  "from": "NVDA", "to": "SMCI",
  "path": ["NVDA", "AMAT", "SMCI"],
  "steps": [
    { "from": "NVDA", "to": "AMAT", "type": "PEER_OF",
      "basis_summary": "Finnhub + FMP peers" },
    { "from": "AMAT", "to": "SMCI", "type": "SUPPLIES_TO",
      "basis_summary": "Supply Chain Tier 1" }
  ],
  "path_length": 2,
  "alternative_count": 3
}
```

## Neo4j Cypher

```cypher
MATCH path = shortestPath(
  (a:Stock {ticker: $from})-[*..5]-(b:Stock {ticker: $to})
)
RETURN path
```

## 완료 기준

```
□ 두 종목 간 최단 경로 반환
□ 단계별 관계 타입 + basis_summary 포함
□ 경로 없는 경우 안내 메시지
```

→ **다음**: cs_44 (Seed Node heat_score)

**END OF DOCUMENT**
