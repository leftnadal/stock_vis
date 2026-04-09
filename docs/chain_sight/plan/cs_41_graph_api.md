# CS-4-1: 그래프 탐색 API

> **작업 번호**: CS-4-1
> **목표**: GET /api/stocks/{symbol}/chainsight/graph/ — N-depth 그래프 탐색
> **예상 소요**: 1~2일
> **선행 조건**: Phase 3 완료
> **산출물**: `chainsight/views.py`, `chainsight/urls.py`

---

## API 명세

```
GET /api/stocks/{symbol}/chainsight/graph/?depth=1&rel_types=PEER_OF&min_confidence=probable
```

### Response

```json
{
    "center": { "ticker": "AAPL", "name": "...", "sector": "...", "pagerank_score": 0.02, ... },
    "nodes": [ ... ],
    "edges": [
        {
            "from": "AAPL", "to": "MSFT", "type": "PEER_OF",
            "confidence_status": "confirmed", "truth_score": 85.0,
            "basis_summary": "Peer relationship (finnhub,fmp)"
        }
    ],
    "meta": { "depth": 1, "node_count": 12, "edge_count": 18, "query_ms": 45 }
}
```

## ⚠️ 점검 결과 반영: CUSTOMER_OF 역방향 파생

로드맵 v1.3: "SUPPLIES_TO만 canonical, API에서 역방향 view로 CUSTOMER_OF 파생."

```python
# edges 후처리
for edge in edges:
    if edge["type"] == "SUPPLIES_TO":
        # 현재 symbol이 to(고객)인 경우 → 역방향 표시
        if edge["to"] == symbol:
            edge["derived_type"] = "CUSTOMER_OF"
            edge["display_label"] = f"{edge['from']}의 고객"
```

## ⚠️ 점검 결과 반영: M4 explanation + market_signals

로드맵 M4에서 언급한 필드 매핑:
- `explanation` = `basis_summary` (RelationConfidence.relation_basis_summary)
- `market_signals` = Market 관계 데이터 (co_mention_count, price_correlation)

edges에 포함:
```json
{
    "explanation": "Peer relationship (finnhub); Same industry (Consumer Electronics)",
    "market_signals": {
        "co_mention_count": 15,
        "price_correlation": 0.82
    }
}
```

## URL

```python
# chainsight/urls.py
path("stocks/<str:symbol>/chainsight/graph/", ChainSightGraphView.as_view(), name="graph"),
```

## 완료 기준

```
□ GET 200 응답, depth 1/2/3
□ CUSTOMER_OF 역방향 파생 동작
□ explanation + market_signals 포함
□ 응답 시간 3초 이내 (depth=1)
□ 404 for unknown symbol
```

→ **다음**: cs_42

**END OF DOCUMENT**
