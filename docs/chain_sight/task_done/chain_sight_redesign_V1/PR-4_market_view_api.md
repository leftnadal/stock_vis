# PR-4: 마켓 뷰 API 4종

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`

## 목표

마켓 뷰 UI를 구동하는 4개 REST API 엔드포인트 구현.

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `chainsight/api/views.py` | `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` 추가 |
| `chainsight/api/urls.py` | 마켓 뷰 URL 4종 추가 + 고정/동적 경로 순서 정리 |

## API 엔드포인트

| 메서드 | 경로 | 뷰 | 캐시 TTL |
|--------|------|-----|---------|
| GET | `/seeds/` | SeedListView | Redis (시드 task에서 설정) |
| GET | `/sector/{sector}/graph/` | SectorGraphView | 1시간 |
| GET | `/{symbol}/neighbors/` | NeighborGraphView | 30분 |
| GET | `/signals/` | SignalFeedView | 1시간 |

## 각 API 상세

### GET /seeds/
- Redis 캐시에서 읽기 전용 (시드 task가 데이터 생성)
- fallback: 오늘 → 어제 → 그제 순 탐색
- Neo4j 불필요 (503 위험 없음)

### GET /sector/{sector}/graph/?limit=12
- Neo4j에서 섹터 내 market_cap 상위 노드 + 관계 조회
- `node_size` 계산: market_cap 기준 percentile (xl/lg/md/sm)
- `is_seed`, `seed_type`, `seed_reasons`: Redis 시드 데이터와 매칭
- Stock 메타 bulk 조회 (N+1 방지)

### GET /{symbol}/neighbors/?limit=8&rel_types=all&min_truth_score=35
- 양방향 이웃 조회 (UNION 대신 undirected MATCH)
- `display_type` 파생: SUPPLIES_TO + outbound → CUSTOMER_OF
- 정렬: is_seed 우선 → score DESC → market_cap DESC
- `cross_edges`: 이웃 간 2차 관계 (그래프 렌더링용)
- 중복 이웃 제거 (seen set)

### GET /signals/?page=1&page_size=5&sector=
- 시드 페어 (같은 섹터) → Neo4j shortestPath (max hop 3)
- `total_confidence` = mean * 0.7 + min * 0.3 (최솟값 보정 평균)
- confidence < 30 제외
- strength: strong(≥70) / moderate(40~69) / weak(<40)
- `chain.id`: `chain_{date}_{seq:03d}`
- `root_sector` 포함 (FE 섹터 추론 불필요)

## URL 순서

```python
# 고정 경로 먼저
path('seeds/', ...)
path('sector/<str:sector>/graph/', ...)
path('signals/', ...)
path('trace/', ...)

# 동적 경로 뒤에
path('<str:symbol>/neighbors/', ...)
path('<str:symbol>/graph/', ...)
path('<str:symbol>/suggestions/', ...)
```

## 에러 응답

| 코드 | 상황 |
|------|------|
| 400 | 잘못된 파라미터 (limit < 1 등) |
| 404 | 종목/섹터 없음 |
| 503 | Neo4j 연결 실패 (GraphConnectionError) |
