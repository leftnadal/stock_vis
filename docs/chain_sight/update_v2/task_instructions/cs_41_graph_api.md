# CS-4-1: 그래프 탐색 API

> **작업 번호**: CS-4-1
> **로드맵 버전**: v1.4 (is_watched 필드 추가)
> **목표**: depth 파라미터로 N-depth 조회, nodes+edges 응답
> **예상 소요**: 2~3일
> **선행 조건**: Phase 3 완료
> **산출물**: `GET /api/stocks/{symbol}/chainsight/graph/`

---

## 엔드포인트

```
GET /api/stocks/{symbol}/chainsight/graph/
  Query params: depth=1 (기본), rel_types=PEER_OF,SUPPLIES_TO (필터)
  Response:
  {
    "center": "NVDA",
    "nodes": [
      { "ticker": "NVDA", "name": "NVIDIA", "sector": "Technology",
        "pagerank_score": 0.85, "community_id": 3,
        "growth_stage": "growth" }
    ],
    "edges": [
      { "from": "NVDA", "to": "TSM", "type": "SUPPLIES_TO",
        "truth_score": 85, "status": "confirmed",
        "explanation": "FMP/Finnhub peers + Supply Chain Tier 1 증거",
        "market_signals": { "co_mention_count": 45, "price_correlation": 0.72 } }
    ],
    "paths": [
      { "path": ["NVDA", "TSM", "ASML"],
        "is_watched": true,
        "watched_path_id": "uuid-here" }
    ]
  }
```

## v1.4 추가사항

### CUSTOMER_OF 역방향 파생
SUPPLIES_TO 엣지를 발견하면 반대 방향에 CUSTOMER_OF 라벨 추가:
```python
if edge['type'] == 'SUPPLIES_TO':
    # from→to 방향이면 "공급" 라벨
    # to→from 방향이면 "고객 관계" 라벨 (CUSTOMER_OF)
    edge['reverse_label'] = 'CUSTOMER_OF'
```

### explanation + market_signals 매핑
- `explanation` = RelationConfidence.relation_basis_summary
- `market_signals` = { co_mention_count, price_correlation } (Market 관계 데이터)

### is_watched 필드 (v1.4 신규)
```python
# N+1 방지: 사용자의 전체 saved_path를 prefetch
watched_paths = SavedPath.objects.filter(
    user=request.user, status__in=['watching', 'active']
).values_list('full_path', 'id')

# 메모리에서 path 매칭
watched_set = {tuple(p): id for p, id in watched_paths}
for path in response_paths:
    key = tuple(path['path'])
    path['is_watched'] = key in watched_set
    path['watched_path_id'] = str(watched_set.get(key)) if key in watched_set else None
```

## 완료 기준

```
□ depth=1 조회 → nodes+edges 응답
□ depth=2 조회 → 2-hop 포함
□ CUSTOMER_OF 역방향 파생 동작
□ explanation, market_signals 필드 포함
□ is_watched, watched_path_id 필드 포함 (N+1 없음)
□ 성능: 50노드 이내, 100 paths LIMIT
```

→ **다음**: cs_42

**END OF DOCUMENT**
