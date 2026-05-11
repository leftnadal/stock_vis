# CS-4-2: 탐색 제안 API

> **작업 번호**: CS-4-2
> **목표**: GET /api/stocks/{symbol}/chainsight/suggestions/ — 카테고리별 탐색 제안
> **예상 소요**: 1일
> **선행 조건**: CS-4-1 완료
> **산출물**: views.py에 SuggestionView 추가

---

## Response

```json
{
    "symbol": "AAPL",
    "categories": [
        { "id": "peers", "label": "경쟁사", "count": 8, "rel_types": ["PEER_OF","COMPETES_WITH"],
          "top_tickers": ["MSFT","GOOG"], "strength": "strong" },
        { "id": "supply_chain", "label": "공급망", "count": 5, "rel_types": ["SUPPLIES_TO"],
          "top_tickers": ["TSMC","HON"], "strength": "strong" },
        { "id": "same_sector", "label": "같은 섹터", "count": 74,
          "rel_types": ["BELONGS_TO_SECTOR"], "top_tickers": ["NVDA","CRM"], "strength": "weak" },
        { "id": "co_mentioned", "label": "뉴스 동시출현", "count": 12,
          "rel_types": ["CO_MENTIONED"], "top_tickers": ["TSLA","META"], "strength": "signal" },
        { "id": "community", "label": "같은 클러스터", "count": 15,
          "rel_types": [], "top_tickers": ["..."], "strength": "moderate" }
    ]
}
```

## 카테고리 생성 로직

1. 경쟁사: PEER_OF + COMPETES_WITH (pagerank 정렬)
2. 공급망: SUPPLIES_TO 양방향
3. 같은 섹터: BELONGS_TO_SECTOR 역방향
4. 뉴스 동시출현: CoMentionEdge (count 정렬)
5. 같은 클러스터: community_id 매칭

## 완료 기준

```
□ 200 응답, 카테고리 2개 이상
□ top_tickers 실제 존재 확인
□ 응답 시간 1초 이내
```

→ **다음**: cs_43

**END OF DOCUMENT**
