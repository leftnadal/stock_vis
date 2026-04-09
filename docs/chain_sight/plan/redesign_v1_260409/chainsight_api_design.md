# Chain Sight 마켓 뷰 API 설계서

> **버전**: v2.0  
> **작성일**: 2026-04-09  
> **상태**: 확정  
> **변경 이력**: v1.1 → v2.0 — 그래프+카드 연동형 탐색 허브에 맞춘 역할 재정의  
> **선행 문서**: chain_sight_seed_node_design.md, chain_sight_ui_ux_design.md

---

## 1. 개요

마켓 뷰(`/chainsight`)의 guided exploration 구조를 구동하는 4개 API.

| 엔드포인트                    | UI 역할                                                  | 호출 시점            |
| ----------------------------- | -------------------------------------------------------- | -------------------- |
| `GET /seeds/`                 | 섹터 바 + 시드 목록 + **섹터 진입 시 대표 카드**         | 페이지 진입 1회      |
| `GET /sector/{sector}/graph/` | 섹터 내 **그래프 구조 + 초기 맥락** 시각화               | 섹터 탭 시           |
| `GET /{symbol}/neighbors/`    | **그래프 중심 이동 + 관계 카드 패널** 렌더의 핵심 데이터 | 노드/카드 클릭 시    |
| `GET /signals/`               | **체인 스토리 피드** — 현재 chain 흐름 + 새 chain 추천   | 페이지 진입 + 스크롤 |

핵심 원칙:

- 이 API들은 "그래프만 그리기 위한 API"가 아니라 **그래프 + 카드 + 트레일 연동형 UI의 공통 데이터 소스**
- 특히 `neighbors`는 그래프 전환뿐 아니라 **관계 카드 패널 렌더용 핵심 API**
- 1차 구현에서 새 엔드포인트 추가 없음. 기존 API를 재정의하여 활용

### 기존 Deep dive API와의 관계

| 엔드포인트               | 용도                            | 사용 화면                                  |
| ------------------------ | ------------------------------- | ------------------------------------------ |
| `/{symbol}/graph/`       | depth 파라미터 지원 에고 그래프 | `/chainsight/[symbol]` deep dive workspace |
| `/{symbol}/suggestions/` | 프로파일 기반 추천              | `/chainsight/[symbol]` deep dive workspace |
| `/trace/`                | 두 종목 간 경로 추적            | `/chainsight/[symbol]` deep dive workspace |

Deep dive API는 마켓 뷰 주 흐름에서 사용하지 않으며, `/chainsight/[symbol]` 워크스페이스 전용.

Base URL: `/api/v1/chainsight/`

---

## 2. GET /api/v1/chainsight/seeds/

### 역할

오늘의 시드 + 섹터 요약. 페이지 진입 시 1회.

UI 활용:

- 섹터 버튼 바 렌더링 (sector_summary)
- **섹터 진입 시 대표 카드** 렌더링 (seeds를 섹터로 필터)
- 시드 노드 하이라이트 (그래프 내 bounce 여부)

### Request

```
GET /api/v1/chainsight/seeds/
```

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

### 필드 상세

**sector_summary[]** — 섹터 바 렌더용. Phase 1: seed_count DESC / Phase 2+: heat_total DESC.

| 필드       | 타입   | 설명                      |
| ---------- | ------ | ------------------------- |
| sector     | string | 섹터 key                  |
| pct_change | float  | 섹터 평균 수익률 (%)      |
| seed_count | int    | 시드 종목 수              |
| heat_total | float  | heat_score 합산 (Phase 2) |
| top_seed   | string | 가장 높은 시그널 종목     |

> Phase 2+ 에서 `sort_basis` 필드 추가 가능: `"seed_count"` 또는 `"heat_total"`

**seeds[]** — 대표 카드 + 시드 하이라이트용.

| 필드         | 타입     | 설명                |
| ------------ | -------- | ------------------- |
| symbol       | string   | ticker              |
| name         | string   | 종목명              |
| sector       | string   | 섹터                |
| industry     | string   | 산업                |
| market_cap   | int      | 시가총액            |
| daily_return | float    | 수익률 (%)          |
| volume_ratio | float    | 거래량 / SMA20      |
| seed_reasons | string[] | 시드 사유 코드      |
| seed_type    | string   | 대표 시드 타입      |
| signal_count | int      | 시드 소스 출현 횟수 |

**seed_reasons 코드:**
`price_top5`, `price_bottom5`, `volume_surge`, `sector_outlier`, `relation_upgrade`, `relation_downgrade`, `relation_new`, `comention_surge`

### 캐싱

`chainsight:seeds:{date}` / Redis / TTL: 다음 시드 계산까지

---

## 3. GET /api/v1/chainsight/sector/{sector}/graph/

### 역할

섹터 선택 시 **초기 구조와 맥락 시각화**. 단순 그래프 렌더용이 아니라, 섹터 내 관계 구조를 한눈에 파악하기 위한 맥락 데이터.

UI 활용:

- 그래프 캔버스 1차 렌더링 (노드 + 엣지)
- 관계 카드 패널은 이 시점에서는 **대표 시드 카드**(seeds API 기반)를 표시

### Request

```
GET /api/v1/chainsight/sector/{sector}/graph/?limit=12
```

| 파라미터             | 타입 | 기본값 | 설명              |
| -------------------- | ---- | ------ | ----------------- |
| limit                | int  | 12     | 종목 수 상한      |
| include_cross_sector | bool | false  | 타 섹터 연결 포함 |

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

### 필드 상세

**nodes[]**

| 필드      | 타입    | 설명                                  |
| --------- | ------- | ------------------------------------- |
| node_size | string  | "xl"/"lg"/"md"/"sm" — market cap 기반 |
| is_seed   | bool    | 오늘의 시드 여부 (bounce 판정)        |
| seed_type | string? | price/volume/relation/comention/null  |

**edges[]**

| 필드              | 타입   | 설명                                                                    |
| ----------------- | ------ | ----------------------------------------------------------------------- |
| type              | string | SUPPLIES_TO / COMPETES_WITH / PEER_OF / CO_MENTIONED / PRICE_CORRELATED |
| relation_category | string | "truth" / "market"                                                      |
| truth_score       | int?   | **Market 관계는 null**                                                  |
| market_score      | int?   | 시장 연관도                                                             |
| status            | string | confirmed / probable                                                    |

> 프론트 엣지 굵기: `truth_score ?? market_score ?? 1` (Market = 고정 1px)

### 데이터 소스

PostgreSQL (Stock market cap 정렬) + Neo4j (관계 조회). seeds 캐시에서 시드 정보 매핑.

### 캐싱

`chainsight:sector_graph:{sector}:{date}:{limit}` / 1시간 TTL

---

## 4. GET /api/v1/chainsight/{symbol}/neighbors/

### 역할

**마켓 뷰 탐색의 핵심 API.** 노드 클릭(또는 카드 CTA)에 의한 중심 이동 + 관계 카드 패널 렌더를 모두 이 API가 담당한다.

UI 활용:

- 그래프 중심 이동 시 새 이웃 노드/엣지 렌더링
- **관계 카드 패널의 카드 데이터** (관계 타입별 그룹, 정렬, CTA)
- 트레일 확장 (relation 정보)

### Request

```
GET /api/v1/chainsight/{symbol}/neighbors/?limit=8&rel_types=all&min_truth_score=35
```

| 파라미터        | 타입   | 기본값 | 설명                                         |
| --------------- | ------ | ------ | -------------------------------------------- |
| limit           | int    | 8      | 이웃 수 상한                                 |
| rel_types       | string | all    | 필터 (콤마 구분)                             |
| min_truth_score | int    | 35     | 최소 truth_score (Market 관계는 무조건 포함) |

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
			"is_seed": true,
			"seed_type": "volume",
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
			"is_seed": true,
			"seed_type": "price",
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
		{
			"source": "TSM",
			"target": "AMD",
			"type": "PEER_OF",
			"truth_score": 55
		}
	],
	"total_neighbor_count": 12,
	"returned_count": 8,
	"truncated": true
}
```

### 필드 상세

**neighbors[].relation**

| 필드               | 타입   | 설명                                      |
| ------------------ | ------ | ----------------------------------------- |
| type               | string | DB 저장 관계 타입                         |
| display_type       | string | 프론트 표시용 (**CUSTOMER_OF 파생 포함**) |
| direction          | string | inbound / outbound / bidirectional        |
| relation_category  | string | truth / market                            |
| truth_score        | int?   | **Market 관계는 null**                    |
| market_score       | int?   | 시장 연관도                               |
| status             | string | confirmed / probable                      |
| evidence_tier_best | string | tier1/tier2/tier3                         |

**display_type 파생 (CUSTOMER_OF):**

```
SUPPLIES_TO + direction=inbound  → display_type="SUPPLIES_TO"
SUPPLIES_TO + direction=outbound → display_type="CUSTOMER_OF"
기타 → display_type = type
```

**정렬:**

1. is_seed = true 우선
2. `(truth_score ?? market_score ?? 0)` DESC
3. market_cap DESC

**관계 카드 패널에서의 그룹핑:**
프론트에서 `display_type`을 기준으로 Suppliers / Competitors / Peers / Co-mentioned 그룹 분리.

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

### display_type 파생 로직 (View)

```python
@staticmethod
def _derive_display_type(rel_type, direction):
    if rel_type == 'SUPPLIES_TO' and direction == 'outbound':
        return 'CUSTOMER_OF'
    return rel_type
```

### 성능 요구

응답 < 200ms (p95). 사용자 탐색 핵심이므로 속도 중요.

### 캐싱

`chainsight:neighbors:{symbol}:{date}:{limit}:{rel_types}` / 30분 TTL

### 카드 설명 필드 확장 (2차)

1차에서는 프론트 템플릿으로 설명 조합. 2차에서 아래 필드 추가 검토:

```json
{
	"relation": {
		"relation_summary": "TSM이 NVDA에 반도체 패키징 공급",
		"why_now": "TSM 거래량 3.1배 급증 — capacity 이슈?",
		"insight_summary": "공급망 리스크 또는 수요 증가 시그널"
	}
}
```

추후 Phase에서 LLM 기반 생성 가능.

---

## 5. GET /api/v1/chainsight/signals/

### 역할

체인 스토리 피드 — **현재 관찰되는 chain 흐름 + 새로운 chain 시작점 추천**.

관계 카드(④)와의 구분:

- 관계 카드 = 현재 중심 기준 로컬 탐색 후보
- 체인 스토리 = 글로벌 chain flow + 새 chain discovery

### Request

```
GET /api/v1/chainsight/signals/?page=1&page_size=5&sector=
```

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
					"relation_to_next": "COMPETES_WITH",
					"relation_category": "truth",
					"relation_truth_score": 78,
					"relation_market_score": null
				},
				{
					"symbol": "AMD",
					"name": "Advanced Micro Devices",
					"daily_return": 4.1,
					"seed_type": "price",
					"relation_to_next": null,
					"relation_category": null,
					"relation_truth_score": null,
					"relation_market_score": null
				}
			],
			"trigger_summary": "TSM volume 3.1x surge, NVDA +7.2% price move"
		}
	]
}
```

### 필드

- `total_confidence`: `truth_score ?? market_score` fallback 평균
- `strength`: strong(>=70) / moderate(40~69) / weak(<40)
- `relation_category`: truth/market/null (마지막 노드)

### 체인 자동 구성

시드에서 출발 → 1-depth 이웃 중 시드 탐색 → depth 3까지 → total_confidence 정렬 → 카테고리 다양성(같은 카테고리 최대 2개)

### 캐싱

`chainsight:signals:{date}:{page}:{sector}` / 1시간 TTL

---

## 6. 에러 응답

모든 엔드포인트 공통.

| 코드 | 상황            | 응답                                               |
| ---- | --------------- | -------------------------------------------------- |
| 400  | 잘못된 파라미터 | `{"error": "invalid_parameter", "message": "..."}` |
| 404  | 종목/섹터 없음  | `{"error": "not_found", "message": "..."}`         |
| 503  | Neo4j 불가      | `{"error": "neo4j_unavailable", "message": "..."}` |

---

## 7. URL 등록

```python
# chainsight/api/urls.py
urlpatterns = [
    # 마켓 뷰 (신규)
    path('seeds/', views.SeedListView.as_view()),
    path('sector/<str:sector>/graph/', views.SectorGraphView.as_view()),
    path('<str:symbol>/neighbors/', views.NeighborGraphView.as_view()),
    path('signals/', views.SignalFeedView.as_view()),

    # Deep dive workspace (기존 CS-4)
    path('<str:symbol>/graph/', views.ChainSightGraphView.as_view()),
    path('<str:symbol>/suggestions/', views.ChainSightSuggestionView.as_view()),
    path('trace/', views.ChainSightTraceView.as_view()),
]
```

`sector/` prefix가 `<str:symbol>/` 보다 먼저 매칭되도록 순서 유지.

---

## 8. 필요 스키마 변경

| 모델                 | 변경                                           | Phase   | 비고                                             |
| -------------------- | ---------------------------------------------- | ------- | ------------------------------------------------ |
| RelationConfidence   | `previous_status` CharField(20)                | Phase 1 | 상태 전이 감지. Phase 3에서 히스토리 테이블 검토 |
| RelationConfidence   | `neo4j_dirty` BooleanField 확인                | Phase 1 | 기존 `synced_to_neo4j` → `neo4j_dirty` 패턴 반영 |
| SeedHeatScore (신규) | stock, date, heat_score, components, seed_rank | Phase 2 | —                                                |
| ChainSignal (선택)   | 체인 캐시 — 또는 Redis                         | Phase 1 | —                                                |

아키텍처 정합: 모든 모델 Layer 3(chainsight/). API 읽기 전용. 쓰기는 Celery 배치만. Market 관계 truth_score=null 유지. CUSTOMER_OF DB 저장 없음.

---

## 9. Celery Beat 연동

| 태스크                | 스케줄     | 후속 API         |
| --------------------- | ---------- | ---------------- |
| select_daily_seeds    | 매일 12:00 | seeds/, signals/ |
| calculate_heat_scores | 매일 11:30 | seeds/ (Phase 2) |

sector_graph, neighbors는 캐시 miss 시 실시간 계산.

---

## 10. 프론트엔드 훅 매핑

| 훅                       | API           | 키                                    |
| ------------------------ | ------------- | ------------------------------------- |
| `useSeedData()`          | seeds/        | `['chainsight', 'seeds']`             |
| `useSectorGraph(sector)` | sector graph/ | `['chainsight', 'sector', sector]`    |
| `useNeighbors(symbol)`   | neighbors/    | `['chainsight', 'neighbors', symbol]` |
| `useSignalFeed(page)`    | signals/      | `['chainsight', 'signals', page]`     |

`useNeighbors`는 그래프 전환 + 관계 카드 패널 렌더 모두에 사용. `staleTime: 5분` (탐색 중 빈번한 호출).
