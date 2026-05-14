# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-14
> **감사자**: Claude Code (read-only audit)
> **대상**: `docs/chain_sight/` 설계 문서군 vs `chainsight/` 앱 + `frontend/{app,components,hooks}/chainsight/` 구현
> **방법론**: 4개 설계 트랙(v1.3 roadmap / cs_5_frontend_design_v2 / redesign_v1_260409 Market View / update_v2 ROADMAP v1.4) 모두 cross-reference

---

## 요약 (구현률)

### 설계 트랙 식별

`docs/chain_sight/plan/` 내부는 4개 시간 축이 누적되어 있다.

| 트랙 | 시점 | 위치 | 관계 |
|------|------|------|------|
| **T1 (v1.3)** | 2026-04-02 | `plan/chain_sight_roadmap_v1.3.md` + `cs_00~cs_43.md` | 기반 (백엔드 CS-0~CS-4) |
| **T2 (FE v2)** | 2026-04-04 | `plan/cs_5_frontend_design_v2.md` | T1의 `cs_51~54.md`를 **부분 대체** (deep dive workspace 중심) |
| **T3 (Market View Redesign)** | 2026-04-09 | `plan/redesign_v1_260409/` 4개 문서 | T2의 진입 화면을 **재정의** (5-component market hub) |
| **T4 (v1.4)** | 2026-04-16 | `update_v2/ROADMAP_v1.4.md` + `update_v2/task_instructions/cs_61~73*` | T1~T3에 **Phase 6/7 Path Watchlist 추가** |

> **결론**: `redesign_v1_260409/`는 `cs_51~54`(T1 원안)와 `cs_5_frontend_design_v2`(T2)의 진입점 설계를 폐기/대체하나, **deep dive workspace 부분은 T2가 여전히 유효**. `cs_51~54` 자체는 T2에서 한 차례, T3에서 한 차례 더 대체되어 폐기 상태.

### 전체 구현률 (트랙별)

| 트랙 | 항목 수 | 완전(A) | 부분(B) | 미구현(C) | 폐기(D) | 구현률 |
|------|--------|---------|---------|----------|---------|--------|
| T1 v1.3 백엔드 (CS-0~CS-4) | 14 | 13 | 1 | 0 | 0 | **96%** |
| T2 FE v2 (deep dive) | 6 | 4 | 2 | 0 | 0 | **83%** |
| T3 Market View 5-component | 5 | 5 | 0 | 0 | 0 | **100%** |
| T4 v1.4 Path Watchlist (CS-6/CS-7) | 10 | 10 | 0 | 0 | 0 | **100%** |
| T1 v1.3 프론트 원안 (cs_51~54) | 4 | 0 | 0 | 0 | 4 | (폐기) |
| **종합** (폐기 제외) | **35** | **32** | **3** | **0** | **4** | **91%** |

### 핵심 관찰

1. **백엔드는 사실상 전 영역 구현 완료** — CS-3-3 GDS만 1회성 실행으로 처리되어 정기 재계산이 없음(부분 구현).
2. **프론트엔드는 두 진입점이 공존** — `/chainsight`(T3 Market View 5-component) + `/chainsight/[symbol]`(T2 deep dive workspace). 의도된 dual-entry이며 둘 다 살아있음.
3. **설계서와 응답 스키마 일부 mismatch** — `/signals/` 응답에서 design은 path 노드에 `seed_type`/`relation_to_next`/`daily_return`을 포함하나 실제 구현은 `symbol/name/sector`만 + 별도 `edges[]` 배열로 분리. 의미는 동일하나 필드 위치가 다름.
4. **종목 상세 Chain Sight 탭** — UI/UX 설계서(redesign_v1_260409)는 "탭 제거 → 딥링크"라고 명시했으나 실제 구현은 탭을 유지한 채 mini view + 딥링크 CTA를 제공. 의도된 절충안인지 deviation인지 불명.

---

## 문서별 상태 테이블

### T1: v1.3 백엔드 (Phase 0~4)

| 문서 | 코드 산출물 | 상태 | 비고 |
|------|------------|------|------|
| `cs_00_legacy_cleanup_api_test.md` | 레거시 제거 + `decisions/003_api_access_test.md` | A | T4(update_v2/task_done/CS-0-0)에서도 재확인 |
| `cs_01_migrations_verification.md` | `chainsight/migrations/0001~0008` | A | 8개 마이그레이션, audit P0 #9에서 `synced_to_neo4j` → `neo4j_dirty`로 통합 완료 |
| `cs_02_neo4j_connection.md` | `chainsight/graph/repository.py` (PID 기반 lazy init) | A | Celery prefork SIGSEGV 대응 적용됨 |
| `cs_03_neo4j_schema.md` | `chainsight/graph/schema.py` + `init_neo4j_schema` 커맨드 | A | constraints 4 + indexes 2 |
| `cs_11_stock_node_bulk_load.md` | `services/neo4j_loader.py::load_stocks_to_neo4j` + management cmd | A | |
| `cs_12_sector_industry.md` | `services/neo4j_loader.py::load_sectors_to_neo4j` | A | |
| `cs_13_peer_relations.md` | `tasks/peer_tasks.py::fetch_and_load_peers` | A | Finnhub + FMP 양쪽 지원 |
| `cs_21_tier_a_profile.md` (GrowthStage, CapitalDNA) | `tasks/profile_tasks.py` | A | calculate_all_profiles 통합 task 존재 |
| `cs_21b_sensitivity_profile.md` | `tasks/sensitivity_tasks.py` | A | FMP Revenue Segmentation 사용 |
| `cs_21c_insider_signal.md` | `tasks/insider_tasks.py` | A | Finnhub Insider 60 RPM 적용 |
| `cs_22_co_mention.md` | `tasks/relation_tasks.py::extract_co_mentions` | A | ChainNewsEvent도 함께 적재 |
| `cs_23_price_co_movement.md` | `tasks/relation_tasks.py::calculate_price_co_movement` | A | 90일 rolling correlation |
| `cs_24_relation_confidence.md` + `relation_confidence_design_v1.md` | `models/relation_discovery.py::RelationConfidence` v2.1 + `tasks/relation_tasks.py::update_relation_confidence`, `check_stale_and_decay` | A | 5단계 status, evidence_tier, evidence_sources JSONB, has_*_source bool 7개 모두 반영. `relation_basis_summary` 템플릿은 단순 형태(예: "Peer 관계 + 같은 산업", "뉴스 동시출현 N회") |
| `cs_25_chain_profile_aggregation.md` | `tasks/sync_tasks.py::aggregate_chain_profiles` | A | CategorySignal 통합 포함 |
| `cs_31_profile_neo4j_sync.md` | `tasks/sync_tasks.py::sync_profiles_to_neo4j` | A | neo4j_dirty 기반 Delta Sync |
| `cs_32_relation_neo4j_sync.md` | `services/neo4j_sync.py::sync_dirty_relations` + `tasks/sync_tasks.py::sync_relations_to_neo4j` + `tasks/neo4j_dirty_sync_tasks.py` | A | data_quality_3_fixes 시 RELATED_TO 하드코딩 → 동적 타입으로 교정 완료 |
| `cs_33_gds_algorithms.md` | (정기 Celery task 없음) | **B** | 1회성 실행 흔적만 존재 (`task_done/CS-3-3_gds_algorithms.md` 결과만), `gds_tasks.py` 또는 그에 준하는 정기 배치 코드는 부재. `path_service.py`는 Neo4j 노드의 `pagerank/betweenness` 속성을 읽기만 함 |
| `cs_41_graph_api.md` | `api/views.py::ChainSightGraphView` | A | `/api/v1/chainsight/{symbol}/graph/` |
| `cs_42_suggestion_api.md` | `api/views.py::ChainSightSuggestionView` | A | peers/same_industry/co_mentioned/same_sector 카테고리 |
| `cs_43_trace_api.md` | `api/views.py::ChainSightTraceView` | A | shortestPath, max_depth=5 |

### T2: cs_5_frontend_design_v2 (FE v2, 2026-04-04)

> deep dive workspace `/chainsight/[symbol]` 영역 — T3에서 진입점이 분리된 후에도 살아남음

| 요구사항 | 코드 산출물 | 상태 | 비고 |
|---------|------------|------|------|
| `/chainsight/[symbol]` 3-panel 전용 워크스페이스 | `frontend/app/chainsight/[symbol]/page.tsx` (370줄) | A | 좌 AI Guide / 중앙 ForceGraph2D / 우 NodeDetailPanel |
| GraphCanvas + 관계 타입 색상 6종 | `components/chainsight/GraphCanvas.tsx`, `graphStyles.ts`, `RelationLegend.tsx` | A | |
| NodeDetailPanel + CTA 4개 (가설 생성 / Watchlist / Validation / 여기서 탐색) | `components/chainsight/NodeDetailPanel.tsx` | **B** | "여기서 탐색", "Deep dive" 등 핵심 CTA는 존재. 일부 v2 설계의 외부 링크 라벨(↗️, 📊)은 단순화됨 |
| AIGuidePanel + CategoryCard | `components/chainsight/AIGuidePanel.tsx` | A | 카테고리 선택 → 그래프 필터링 |
| TracePanel + TracePathView | `components/chainsight/TracePathView.tsx` | A | from/to 입력 + 경로 하이라이트 |
| 종목 상세 미니 뷰 (CS-5-4) | `components/chainsight/GraphMiniView.tsx` + `app/stocks/[symbol]/page.tsx` 통합 | A | |
| 프로 기능: FilterPanel (관계 타입, depth) | `components/chainsight/FilterPanel.tsx` | A | |
| 프로 기능: 오버레이 (PER 히트맵, Centrality, Community) | (구현 흔적 없음) | **B** | v2 §6-2 정의만 존재. GDS 결과는 Neo4j 속성에 있으나 프론트에서 노드 시각화 토글로 노출 안 됨 |
| 프로 기능: 노드 비교 모드 (Ctrl+Click) | (구현 흔적 없음) | **B** | v2 §6-3. 우선순위 낮은 advanced 기능, 폐기 가능 영역 |
| 모바일 MobileCardList | `components/chainsight/MobileCardList.tsx` (202줄) | A | |
| WatchButton (v2 본문에는 없으나 T4에서 흡수) | `components/chainsight/WatchButton.tsx` | A | T4 CS-7-1과 동일 산출물 |

### T3: redesign_v1_260409 (Market View 5-component, 2026-04-09)

| 설계서 항목 | 코드 산출물 | 상태 | 비고 |
|------------|------------|------|------|
| **API** `GET /seeds/` (대표 시드 + 섹터 요약) | `api/views.py::SeedListView` + `services/seed_selection.py::build_sector_summary` + `SeedSnapshot` DB 영속화 + 3단 폴백 | A | `sector_summary`의 `heat_total`은 현재 0.0 고정(Phase 1: seed_count DESC 정렬만), `top_seed`는 구현됨 |
| **API** `GET /sector/{sector}/graph/` (overview graph) | `api/views.py::SectorGraphView` | A | node_size xl/lg/md/sm percentile 계산 포함 |
| **API** `GET /{symbol}/neighbors/` (마켓 뷰 탐색 핵심) | `api/views.py::NeighborGraphView` | A | display_type 파생, cross_edges 포함, CUSTOMER_OF 역방향 view 처리. `signal_count` 필드는 응답에 누락 (설계 §4 neighbors[].signal_count 명시) |
| **API** `GET /signals/` (글로벌 chain flow) | `api/views.py::SignalFeedView::_build_chain_signals` | A | 응답 형태: 설계는 `path: [{symbol, daily_return, seed_type, relation_to_next, ...}]` 단일 배열, 실제 코드는 `path: [{symbol, name, sector}]` + 별도 `edges: [{type, score}]` 분리. **의미 동등, 스키마 mismatch** |
| ① SectorBar | `components/chainsight/SectorBar.tsx` | A | 56줄, 수익률 색상, 가로 스크롤 |
| ② MarketGraphCanvas (overview/neighbor 분기) | `components/chainsight/MarketGraphCanvas.tsx` | A | 298줄, 시드 색상 구분 |
| ③ ExplorationTrail | `components/chainsight/ExplorationTrail.tsx` | A | 가로 스크롤 + undo |
| ④ RelationCardPanel (pre-focus/focused 분기) | `components/chainsight/RelationCardPanel.tsx` | A | 293줄, RELATION_TEMPLATES 1차 템플릿 포함 |
| ⑤ ChainStoryFeed (무한 스크롤) | `components/chainsight/ChainStoryFeed.tsx` | A | TanStack `useInfiniteQuery` + IntersectionObserver |
| `explorationStore` (Zustand) | `frontend/lib/stores/explorationStore.ts` | A | task_done summary에 등록됨 |
| `useMarketView` 4훅 | `frontend/hooks/useMarketView.ts` | A | useSeedData/useSectorGraph/useNeighbors/useSignalFeed |
| 페이지: `/chainsight/page.tsx` (5-component 조립) | `app/chainsight/page.tsx` | A | ?focus={symbol} 딥링크 처리 포함 |
| Header 메뉴 + 종목 상세 탭 제거 → 딥링크 | Header 추가됨 ✓ / 탭은 미제거 (mini view + CTA 형태로 유지) | **B** | UI/UX 설계 §11은 "탭 제거"였으나 실제는 탭 + GraphMiniView + "Chain Sight에서 보기" 링크. 사용성 보존 차원의 의도된 절충일 가능성 |
| Celery Beat `chainsight-seed-selection` (매일 13:00 UTC) | `config/celery.py:749`, `tasks/seed_tasks.py::run_seed_selection` | A | |
| Celery Beat `chainsight-neo4j-dirty-sync` (매주 일 04:30 UTC) | `config/celery.py:756`, `tasks/neo4j_dirty_sync_tasks.py` | A | `neo4j` 큐 라우팅 |

### T4: update_v2 v1.4 (Path Watchlist, Phase 6/7)

| 설계서 항목 | 코드 산출물 | 상태 | 비고 |
|------------|------------|------|------|
| **CS-6-1** SavedPath / PathAction 모델 | `chainsight/models/saved_path.py`, migration `0006_add_savedpath_pathaction.py` | A | UUID PK, status 4단계 |
| **CS-6-2** Watchlist CRUD API | `chainsight/views/watchlist_views.py::WatchlistViewSet` (router 등록) | A | POST/GET/DELETE + status 필터 |
| **CS-6-3** Summary path landmark 압축 | `chainsight/services/path_service.py::generate_summary_path` (pagerank/betweenness 활용) | A | GDS 결과 의존 — GDS 부재 시 fallback weight 사용 |
| **CS-6-4** Archive / Resolve action | `WatchlistViewSet.archive/resolve @action` | A | PathAction 기록 포함 |
| **CS-6-5** Recheck API 6단계 | `chainsight/services/recheck_service.py` + `WatchlistViewSet.recheck` | A | EdgeDiff dataclass, 2회+24h watching→active 전이 |
| **CS-6-6** Expand API | `chainsight/services/expand_service.py` + `WatchlistViewSet.expand` | A | RELATION_PRIORITY 정렬, heat_score 가중치 |
| **CS-6-7** Alternatives API | `chainsight/services/alternatives_service.py` + `WatchlistViewSet.alternatives` | A | 인접 노드 + relation_type 동일성 기반 |
| **CS-7-1** WatchButton | `frontend/components/chainsight/WatchButton.tsx` + ExplorationTrail 통합 | A | |
| **CS-7-2** Watchlist 카드 리스트 화면 | `frontend/app/chainsight/watchlist/page.tsx` + `PathCard.tsx` | A | status 필터, 빈 상태 UI |
| **CS-7-3** Full Path View + 액션 UX | `frontend/app/chainsight/watchlist/[id]/page.tsx` + `FullPathView.tsx` (349줄) | A | Recheck headline, Expand 후보, Alternatives 인라인 |
| **CS-4-4** Seed Node heat_score 배치 | `chainsight/tasks/seed_tasks.py::calculate_heat_scores` + Beat `chainsight-heat-score-daily` | A | 4-component 가중합 (price/volume/relation_change/news_activation) |

---

## 미구현 항목 상세

### 1. CS-3-3 GDS 정기 배치 — 부분 구현 (B)

**설계**: `cs_33_gds_algorithms.md`는 `chainsight/tasks/gds_tasks.py::run_gds_algorithms`을 정의. PageRank, Louvain, Betweenness를 Celery Beat로 주기 재계산. `task_done/CS-3-3_gds_algorithms.md`는 2026-04-03 1회 실행 결과(PageRank Top 5 등) 기록.

**현 상태**:
- `chainsight/tasks/` 내 `gds_tasks.py` **부재**
- `config/celery.py` Beat 스케줄에 GDS 항목 **없음**
- `chainsight/management/commands/`에 `run_gds_algorithms`류 커맨드 **없음**
- 결과 소비자는 존재: `chainsight/services/path_service.py:143~155`에서 `pagerank`, `betweenness` Neo4j 노드 속성을 읽어 landmark 점수 계산

**리스크**:
- 노드 추가/관계 갱신 후 PageRank/Community 값이 stale. 한 번 적재된 값이 그대로 노출됨
- summary path landmark 선정 정확도가 시간에 따라 저하

### 2. cs_5_frontend_design_v2 §6-2 노드 메트릭 오버레이 — 미구현 (B)

**설계**: PER 히트맵 / 시총 크기 / Centrality(PageRank) / Community(Louvain) 토글.

**현 상태**: `GraphCanvas.tsx`, `MarketGraphCanvas.tsx` 모두 섹터 색상 + 시드 색상 분기까지만 구현. 오버레이 토글 UI **없음**.

**의의**: "전문 투자자 기능"으로 명시된 advanced 기능. v2 설계 §11 (반영하지 않은 의견)에 가깝게 후순위 처리됨.

### 3. cs_5_frontend_design_v2 §6-3 노드 비교 모드 — 미구현 (B)

**설계**: 두 노드 Ctrl+Click → PER/ROE/Growth Stage/Capital DNA 등 병렬 표 + "두 종목 Trace" CTA.

**현 상태**: 미구현. 우선순위 가장 낮음.

### 4. T3 `/signals/` 응답 스키마 mismatch — 부분 구현 (B)

**설계** (`chainsight_api_design.md` §5):
```json
"path": [
  {"symbol": "...", "name": "...", "daily_return": 1.2, "seed_type": "volume",
   "relation_to_next": "SUPPLIES_TO", "relation_truth_score": 85,
   "relation_market_score": null, ...}
]
```

**구현** (`api/views.py::SignalFeedView::_build_chain_signals` lines 781~796):
```json
"path": [{"symbol", "name", "sector"}],
"edges": [{"type", "score"}]
```

**갭**:
- `daily_return`, `seed_type` 누락 → 프론트에서 chain card 표시 시 시드 정보 활용 불가
- `relation_to_next`가 path[]에서 분리되어 `edges[]`로 이동 — 의미는 동등하나 설계 스펙 불일치

### 5. T3 `/{symbol}/neighbors/` 응답 — 부분 구현 (B)

**설계** (`chainsight_api_design.md` §4):
- `neighbors[].signal_count` 필드 (시드 소스 출현 횟수)

**구현** (`api/views.py::NeighborGraphView` lines 556~577):
- `signal_count` 필드 **누락**. `seed_reasons` 배열만 포함.

**영향**: 카드 UI에서 signal badge 수치 표시 불가 → 프론트는 `seed_reasons.length`로 대체 가능하나 설계 의도와 다름.

### 6. T3 종목 상세 Chain Sight 탭 처리 — 의도된 절충 가능 (B)

**설계** (`chainsight_ui_ux_design.md` §11):
> `/stocks/[symbol]` → Chain Sight 탭 **제거**, 딥링크(`/chainsight?focus={symbol}`) 추가

**구현** (`frontend/app/stocks/[symbol]/page.tsx`):
- "Chain Sight (관계 탐색)" 탭 **유지** (line 84)
- 탭 내부에 `GraphMiniView` 미니 그래프 + "Chain Sight에서 보기" → `/chainsight?focus={symbol}` 링크 (line 450)

**판단**: T2 `cs_5_frontend_design_v2.md` §7 (종목 상세 미니 뷰)이 T3와 충돌. 실제 구현은 **T2를 따랐다**. 의도된 결정인지 redesign 적용 시 누락된 것인지 추가 확인 필요.

---

## 폐기/대체 항목

### D1. `cs_51_graph_visualization.md` — 폐기

- **이유**: T2 `cs_5_frontend_design_v2.md`가 "원안 (cs_51~54)" 대비 변경을 명시(§0 표). T3 `redesign_v1_260409`가 진입점을 다시 분리.
- **현 상태**: 산출물 파일명 `GraphView.tsx`은 존재하지 않음. 대신 `GraphCanvas.tsx`(T2 deep dive) + `MarketGraphCanvas.tsx`(T3 market view)로 분기.

### D2. `cs_52_ai_guide_ui.md` — 폐기

- **이유**: 동일. 산출물 파일명 `SuggestionCards.tsx`은 없으며 `AIGuidePanel.tsx`로 대체.
- **현 상태**: T2 deep dive workspace의 좌측 패널로 살아있음.

### D3. `cs_53_chain_trace_ui.md` — 폐기

- **이유**: T2/T3 모두에서 별도 진입점이 아닌 deep dive workspace 내부 기능으로 흡수.
- **현 상태**: `TracePathView.tsx`(105줄)로 구현. 좌측 AI Guide 패널 하단에 통합.

### D4. `cs_54_stock_detail_integration.md` — 폐기

- **이유**: T2 §7 (미니 뷰)이 1차 대체, T3 UI/UX §11 (탭 제거 → 딥링크)이 2차 대체.
- **현 상태**: 실제 구현은 위 **§6 갭**처럼 T2 안을 따름.

### D5. v1.3 부록 B의 ETF 모델 처리 (`# LEGACY_KEEP_UNTIL_DC2`) — 처리 완료

- **이유**: T1 v1.3에서 "DC-2 완료 시 제거" 조건부 보존. T4 v1.4 부속 보고서 `DC-2_etf_holdings_theme.md`에서 ETFProfile(21) + ETFHolding(4,915)을 `:Theme` 노드 + `HAS_THEME` 관계로 변환 완료.
- **현 상태**: `chainsight/management/commands/load_themes_to_neo4j.py` 존재. `serverless/`의 ETFProfile 등 모델은 보존(다른 서비스가 참조 — `references` 디렉토리에 명시).

### D6. `synced_to_neo4j` 필드 (단일 소스로 통합)

- **이유**: audit P0 #9 결정. 2026-04-29 기준.
- **현 상태**: 모든 모델에서 `neo4j_dirty` (의미 반전, True=동기화 필요) 단일 필드로 통일. 마이그레이션 `0008_unify_neo4j_flags.py` 완료. 본문 코드 주석에도 명시(`# audit P0 #9: synced_to_neo4j 제거, neo4j_dirty 단일 소스`).

---

## 부록: 디렉토리 ↔ task_done 교차 인덱스

`task_done/`은 두 위치에 분산:

| 위치 | 트랙 | 파일 수 |
|------|------|--------|
| `docs/chain_sight/task_done/CS-*.md` (1단 PR 시리즈) | T1 v1.3 백엔드 완료 보고 | 22 |
| `docs/chain_sight/task_done/chain_sight_redesign_V1/PR-*.md` | T3 Market View redesign 완료 보고 | 10 |
| `docs/chain_sight/update_v2/task_done/CS-*.md` + `cs_71_72_73_phase7_frontend.md` | T4 v1.4 (Phase 5~7 + 기존 항목 재확인) | 26 |

**상호 검증**:
- T1 `task_done/CS-3-3_gds_algorithms.md`는 1회 실행 결과만 기록 → 본 감사의 §1 부분 구현 분류와 일치
- T4 `update_v2/task_done/CS-5-5_market_view.md`는 "이미 구현됨" 명시 → T3에서 사실상 완성된 것 재확인
- T3 `task_done/chain_sight_redesign_V1/00_summary.md`의 "범위 밖(후속)" 목록(Heat Score, 전환 애니메이션, LLM chain title 등) 중 **Heat Score만 T4 CS-4-4로 구현 완료**. 나머지는 미해결로 잔존.

---

## 후속 권고 (감사 범위 외 — 참고용)

1. **CS-3-3 GDS 정기 배치 신규 작성** — `chainsight/tasks/gds_tasks.py` + Beat 등록(주 1회 권장)으로 PageRank/Louvain stale 방지
2. **`/signals/` 응답 스키마 정렬** — 설계서 §5에 맞춰 `path[]`에 `daily_return`, `seed_type`, `relation_to_next`를 합치거나, 설계서 자체를 현재 구현 형태로 업데이트
3. **`/{symbol}/neighbors/`의 `signal_count` 추가** — 1줄 패치(`'signal_count': len(ns_seed.get('seed_reasons', []))`)
4. **종목 상세 탭 처리 결정 확정** — T2/T3 사이의 모순을 `DECISIONS.md`에 명시(현 절충안 유지 vs 탭 제거)
5. **redesign_v1_260409/ vs cs_5_frontend_design_v2.md vs cs_51~54의 deprecation 표식** — 각 폐기 문서 상단에 "→ 대체: [...]" 명시해 후속 에이전트의 혼란 방지
