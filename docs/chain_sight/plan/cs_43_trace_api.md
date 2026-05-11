# CS-4-3: 경로 탐색 API (Chain Trace)

> **작업 번호**: CS-4-3
> **목표**: GET /api/chainsight/trace/?from=X&to=Y — 두 종목 간 최단 경로
> **예상 소요**: 1일
> **선행 조건**: CS-4-1 완료
> **산출물**: views.py에 TraceView 추가

---

## API 명세

```
GET /api/chainsight/trace/?from=AAPL&to=TSLA&max_depth=5
```

### Response

```json
{
    "from": "AAPL", "to": "TSLA",
    "found": true, "path_length": 3,
    "path": [
        { "node": {"ticker":"AAPL","name":"Apple"}, "next_relation": {"type":"PEER_OF","basis_summary":"..."} },
        { "node": {"ticker":"MSFT","name":"Microsoft"}, "next_relation": {"type":"PEER_OF","basis_summary":"..."} },
        { "node": {"ticker":"TSLA","name":"Tesla"}, "next_relation": null }
    ],
    "alternative_paths": 2
}
```

## 구현

Neo4j `shortestPath` 사용:
```cypher
MATCH path = shortestPath((a:Stock {ticker:$from})-[*..5]-(b:Stock {ticker:$to}))
RETURN nodes(path), relationships(path)
```

## 완료 기준

```
□ 경로 있는 경우: path + 단계별 설명
□ 경로 없는 경우: found=false
□ 필수 파라미터 누락 시 400
□ 응답 시간 3초 이내

★ M4 달성: "API 완성"
```

→ **다음**: cs_51

**END OF DOCUMENT**
