# Chain Sight 마켓 뷰 API 설계서

> **버전**: v2.1 FINAL  
> **작성일**: 2026-04-10  
> **상태**: 확정 — 구현 진행 가능  
> **변경 이력**: v2.0 → v2.1 — neighbors 필드 보강, 역할 재서술, 용어 통일  
> **선행 문서**: chain_sight_seed_node_design.md, chain_sight_ui_ux_design.md

---

## 1. 개요

마켓 뷰의 guided exploration 구조를 구동하는 4개 API. 새 엔드포인트 추가 없이 기존 4개를 재사용한다.

| 엔드포인트                    | UI 역할                                                            | 호출 시점         |
| ----------------------------- | ------------------------------------------------------------------ | ----------------- |
| `GET /seeds/`                 | ① 섹터 바 + ④ **대표 시드 카드** (global preload → 섹터 필터 렌더) | 페이지 진입 1회   |
| `GET /sector/{sector}/graph/` | ② **overview graph** — 탐색 시작점을 고르기 위한 섹터 구조 파악    | 섹터 탭 시        |
| `GET /{symbol}/neighbors/`    | ② 중심 이동 + ④ **관계 카드 패널** 렌더의 핵심 데이터              | 노드/카드 클릭 시 |
| `GET /signals/`               | ⑤ **체인 스토리 피드** — 글로벌 chain flow + 새 chain 추천         | 진입 + 스크롤     |

핵심:

- 이 API들은 "그래프만 그리기 위한 API"가 아니라 **그래프 + 카드 + 트레일 연동형 UI의 공통 데이터 소스**
- `neighbors`는 그래프 전환뿐 아니라 **관계 카드 패널(④) 렌더용 핵심 API**

### Deep dive workspace API (별도)

| 엔드포인트               | 화면                                         |
| ------------------------ | -------------------------------------------- |
| `/{symbol}/graph/`       | Deep dive workspace (`/chainsight/[symbol]`) |
| `/{symbol}/suggestions/` | Deep dive workspace                          |
| `/trace/`                | Deep dive workspace                          |

마켓 뷰 주 흐름에서 사용하지 않음.

Base URL: `/api/v1/chainsight/`

---

## 2. GET /seeds/

### 역할

오늘의 시드 전체 + 섹터 요약. **global preload source**.

- 페이지 진입 시 전체 `seeds` preload
- 섹터 선택 후 프론트가 해당 sector로 filter하여 **대표 시드 카드** 표시

### Response 200

```json
{
	"date": "2026-04-09",
	"total_seeds": 18,
	"sector_summary": [
		{
			"sector": "Technology",
			"sector_display": "Technology",
			"pct_change": 1.8,
			"seed_count": 7,
			"heat_total": 84.2,
			"top_seed": "NVDA"
		}
	],
	"seeds": [
		{
			"symbol": "NVDA",
			"name": "NVIDIA Corp",
			"sector": "Technology",
			"industry": "Semiconductors",
			"market_cap": 2800000000000,
			"daily_return": 7.2,
			"volume_ratio": 3.1,
			"seed_reasons": ["price_top5", "volume_surge"],
			"seed_type": "price",
			"signal_count": 2
		}
	]
}
```

### sector_summary 정렬

- Phase 1: `seed_count DESC`
- Phase 2+: `heat_total DESC`
- 향후 `sort_basis` 필드 추가 가능

### seed_reasons 코드

`price_top5`, `price_bottom5`, `volume_surge`, `sector_outlier`, `relation_upgrade`, `relation_downgrade`, `relation_new`, `comention_surge`

### 캐싱

`chainsight:seeds:{date}` / Redis / TTL: 다음 시드 계산까지

---

## 3. GET /sector/{sector}/graph/

### 역할

섹터 선택 시 **overview graph**. 단순 초기 그래프가 아니라 **탐색 시작점을 고르기 위한 섹터 내 관계 구조 파악**이 목적.

이 단계에서 관계 카드 패널(④)은 overview graph가 아닌 `seeds/`의 **대표 시드 카드**를 표시한다. 중심 노드 기반 본격 탐색은 `neighbors/` 이후.

### Request

```
GET /api/v1/chainsight/sector/{sector}/graph/?limit=12
```

### Response 200

```json
{
	"sector": "Technology",
	"node_count": 10,
	"edge_count": 14,
	"nodes": [
		{
			"symbol": "NVDA",
			"name": "NVIDIA Corp",
			"sector": "Technology",
			"industry": "Semiconductors",
			"market_cap": 2800000000000,
			"daily_return": 7.2,
			"volume_ratio": 3.1,
			"is_seed": true,
			"seed_type": "price",
			"seed_reasons": ["price_top5", "volume_surge"],
			"node_size": "lg"
		}
	],
	"edges": [
		{
			"source": "NVDA",
			"target": "TSM",
			"type": "SUPPLIES_TO",
			"relation_category": "truth",
			"truth_score": 85,
			"market_score": 72,
			"status": "confirmed"
		},
		{
			"source": "NVDA",
			"target": "AMD",
			"type": "CO_MENTIONED",
			"relation_category": "market",
			"truth_score": null,
			"market_score": 45,
			"status": "probable"
		}
	]
}
```

### 필드

**edges[]**

| 필드              | 타입   | 설명                                                                    |
| ----------------- | ------ | ----------------------------------------------------------------------- |
| type              | string | SUPPLIES_TO / COMPETES_WITH / PEER_OF / CO_MENTIONED / PRICE_CORRELATED |
| relation_category | string | "truth" / "market"                                                      |
| truth_score       | int?   | **Market 관계는 null**                                                  |
| market_score      | int?   |                                                                         |
| status            | string | confirmed / probable                                                    |

**node_size**: xl(상위10%) / lg(10~30%) / md(30~60%) / sm(나머지)

> 프론트 엣지 굵기: `truth_score != null ? scale(truth_score) : 1`

### 캐싱

`chainsight:sector_graph:{sector}:{date}:{limit}` / 1시간

---

## 4. GET /{symbol}/neighbors/

### 역할

**마켓 뷰 탐색의 핵심 API.** 중심 이동 + 관계 카드 패널 렌더를 모두 담당한다.

### Request

```
GET /api/v1/chainsight/{symbol}/neighbors/?limit=8&rel_types=all&min_truth_score=35
```

### Response 200

```json
{
	"center": {
		"symbol": "NVDA",
		"name": "NVIDIA Corp",
		"sector": "Technology",
		"industry": "Semiconductors",
		"market_cap": 2800000000000,
		"daily_return": 7.2,
		"volume_ratio": 3.1,
		"is_seed": true,
		"seed_type": "price",
		"seed_reasons": ["price_top5", "volume_surge"]
	},
	"neighbors": [
		{
			"symbol": "TSM",
			"name": "Taiwan Semiconductor",
			"sector": "Technology",
			"industry": "Semiconductors",
			"market_cap": 800000000000,
			"daily_return": 1.2,
			"volume_ratio": 3.1,
			"is_seed": true,
			"seed_type": "volume",
			"seed_reasons": ["volume_surge"],
			"signal_count": 1,
			"relation": {
				"type": "SUPPLIES_TO",
				"display_type": "SUPPLIES_TO",
				"direction": "inbound",
				"relation_category": "truth",
				"truth_score": 85,
				"market_score": 72,
				"status": "confirmed",
				"evidence_tier_best": "tier1"
			}
		},
		{
			"symbol": "AMD",
			"name": "Advanced Micro Devices",
			"sector": "Technology",
			"industry": "Semiconductors",
			"market_cap": 250000000000,
			"daily_return": 4.1,
			"volume_ratio": 1.8,
			"is_seed": true,
			"seed_type": "price",
			"seed_reasons": ["price_top5"],
			"signal_count": 1,
			"relation": {
				"type": "COMPETES_WITH",
				"display_type": "COMPETES_WITH",
				"direction": "outbound",
				"relation_category": "truth",
				"truth_score": 78,
				"market_score": 65,
				"status": "confirmed",
				"evidence_tier_best": "tier2"
			}
		}
	],
	"cross_edges": [
		{ "source": "TSM", "target": "AMD", "type": "PEER_OF", "truth_score": 55 }
	],
	"total_neighbor_count": 12,
	"returned_count": 8,
	"truncated": true
}
```

### 필드 상세

**center** — 중심 노드. `volume_ratio`, `seed_reasons` 포함.

**neighbors[]** — 1차 응답에 카드 UI를 위해 아래 필드 포함:

| 필드         | 타입     | 설명                | 카드 UI 용도 |
| ------------ | -------- | ------------------- | ------------ |
| volume_ratio | float    | 거래량 / SMA20      | why now 조합 |
| seed_reasons | string[] | 시드 사유 코드      | signal badge |
| signal_count | int      | 시드 소스 출현 횟수 | 중요도 표시  |

**neighbors[].relation**

| 필드               | 타입   | 설명                                      |
| ------------------ | ------ | ----------------------------------------- |
| type               | string | DB 관계 타입                              |
| display_type       | string | 프론트 표시용 (**CUSTOMER_OF 파생 포함**) |
| direction          | string | inbound / outbound / bidirectional        |
| relation_category  | string | truth / market                            |
| truth_score        | int?   | **Market = null**                         |
| market_score       | int?   |                                           |
| status             | string | confirmed / probable                      |
| evidence_tier_best | string | tier1 / tier2 / tier3                     |

**display_type 파생:**

```
SUPPLIES_TO + direction=outbound → "CUSTOMER_OF"
기타 → type 그대로
```

**관계 카드 그룹핑:** 프론트에서 `display_type` 기준으로 Supply chain / Competitors / Peers / Co-mentioned 분리. CUSTOMER_OF는 Supply chain 그룹 내 badge.

**정렬:**

1. is_seed = true 우선
2. `(truth_score ?? market_score ?? 0)` DESC
3. market_cap DESC

### Neo4j 쿼리

```cypher
MATCH (center:Stock {ticker: $symbol})-[r]->(neighbor:Stock)
WHERE type(r) IN $rel_types
  AND r.status IN ['confirmed', 'probable']
  AND (r.truth_score >= $min_truth_score OR r.truth_score IS NULL)
RETURN neighbor.ticker, type(r), r.truth_score, r.market_score,
       r.status, r.evidence_tier_best, 'outbound' as direction
UNION
MATCH (neighbor:Stock)-[r]->(center:Stock {ticker: $symbol})
WHERE type(r) IN $rel_types
  AND r.status IN ['confirmed', 'probable']
  AND (r.truth_score >= $min_truth_score OR r.truth_score IS NULL)
RETURN neighbor.ticker, type(r), r.truth_score, r.market_score,
       r.status, r.evidence_tier_best, 'inbound' as direction
```

### display_type 파생 (View)

```python
@staticmethod
def _derive_display_type(rel_type, direction):
    if rel_type == 'SUPPLIES_TO' and direction == 'outbound':
        return 'CUSTOMER_OF'
    return rel_type
```

### 성능

< 200ms (p95). 탐색 핵심이므로 속도 중요.

### 캐싱

`chainsight:neighbors:{symbol}:{date}:{limit}:{rel_types}` / 30분

### 2차 필드 확장 (향후)

```json
{
	"relation": {
		"relation_summary": "TSM이 NVDA에 반도체 패키징 공급",
		"why_now": "TSM 거래량 3.1배 급증",
		"insight_summary": "공급망 리스크 또는 수요 증가 시그널"
	}
}
```

추후 LLM 기반 생성 가능.

---

## 5. GET /signals/

### 역할

**글로벌 chain flow + 새 chain 추천.** 현재 중심 노드/탐색 상태와 무관한 global feed.

관계 카드 패널(④)과의 구분:

- ④ = 현재 center 기준 로컬 탐색
- ⑤ = 시장 전체 chain flow + discovery

> 현재 트레일 해석 기능은 이번 버전 미포함. Future enhancement.

### Response 200

```json
{
	"date": "2026-04-09",
	"page": 1,
	"page_size": 5,
	"total_count": 12,
	"has_next": true,
	"chains": [
		{
			"id": "chain_20260409_001",
			"title": "Semiconductor supply chain reaction",
			"category": "Semiconductors",
			"root_sector": "Technology",
			"strength": "strong",
			"total_confidence": 76.5,
			"path": [
				{
					"symbol": "TSM",
					"name": "Taiwan Semiconductor",
					"daily_return": 1.2,
					"seed_type": "volume",
					"relation_to_next": "SUPPLIES_TO",
					"relation_category": "truth",
					"relation_truth_score": 85,
					"relation_market_score": null
				},
				{
					"symbol": "NVDA",
					"name": "NVIDIA Corp",
					"daily_return": 7.2,
					"seed_type": "price",
					"relation_to_next": null,
					"relation_category": null,
					"relation_truth_score": null,
					"relation_market_score": null
				}
			],
			"trigger_summary": "TSM volume 3.1x surge, NVDA +7.2%"
		}
	]
}
```

- `total_confidence`: `truth_score ?? market_score` fallback 평균
- `strength`: strong(>=70) / moderate(40~69) / weak(<40)

### 캐싱

`chainsight:signals:{date}:{page}:{sector}` / 1시간

---

## 6. 에러 응답

| 코드 | 상황            |
| ---- | --------------- |
| 400  | 잘못된 파라미터 |
| 404  | 종목/섹터 없음  |
| 503  | Neo4j 불가      |

---

## 7. URL 등록

```python
urlpatterns = [
    # 마켓 뷰
    path('seeds/', views.SeedListView.as_view()),
    path('sector/<str:sector>/graph/', views.SectorGraphView.as_view()),
    path('<str:symbol>/neighbors/', views.NeighborGraphView.as_view()),
    path('signals/', views.SignalFeedView.as_view()),
    # Deep dive workspace
    path('<str:symbol>/graph/', views.ChainSightGraphView.as_view()),
    path('<str:symbol>/suggestions/', views.ChainSightSuggestionView.as_view()),
    path('trace/', views.ChainSightTraceView.as_view()),
]
```

---

## 8. 스키마 변경

| 모델                 | 변경                                           | Phase   |
| -------------------- | ---------------------------------------------- | ------- |
| RelationConfidence   | `previous_status` CharField(20)                | Phase 1 |
| RelationConfidence   | `neo4j_dirty` 확인                             | Phase 1 |
| SeedHeatScore (신규) | stock, date, heat_score, components, seed_rank | Phase 2 |

Layer 3(chainsight/). API 읽기 전용. CUSTOMER_OF DB 저장 없음. Market truth_score=null 유지.

---

## 9. 프론트엔드 훅

| 훅                       | API           | staleTime |
| ------------------------ | ------------- | --------- |
| `useSeedData()`          | seeds/        | 30분      |
| `useSectorGraph(sector)` | sector graph/ | 30분      |
| `useNeighbors(symbol)`   | neighbors/    | 5분       |
| `useSignalFeed(page)`    | signals/      | 30분      |

### 상태 전이 흐름 요약

```
페이지 진입 → useSeedData() → 섹터 바 렌더
섹터 탭 → useSectorGraph(sector) → ② overview graph + ④ 대표 시드 카드 (seeds 필터) + ③ trail 초기화
노드/카드 클릭 → useNeighbors(symbol) → ② 중심 이동 + ③ 트레일 확장 + ④ 관계 카드
체인 카드 클릭 → useNeighbors(chain[0].symbol) → ② chain highlight + ③ 새 트레일 시작 + ④ 관계 카드
```
