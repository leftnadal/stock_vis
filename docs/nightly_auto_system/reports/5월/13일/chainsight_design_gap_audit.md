# Chain Sight 설계 갭 감사

> 감사일: 2026-05-13
> 범위: `docs/chain_sight/plan/` (설계) ↔ `chainsight/` + `frontend/{app,components}/chainsight/` (구현)
> 방법: 읽기 전용 cross-reference (cs_00~54 + redesign_v1_260409/ + task_done/)

---

## 요약 (구현률)

| Phase | 설계 항목 | 완전(A) | 부분(B) | 미구현(C) | 폐기/대체(D) | 구현률 |
|-------|----------|---------|---------|-----------|--------------|--------|
| Phase 0 (인프라) | cs_00~03 (4) | 4 | 0 | 0 | 0 | **100%** |
| Phase 1 (데이터) | cs_11~13 (3) | 3 | 0 | 0 | 0 | **100%** |
| Phase 2 (프로파일/관계) | cs_21~25 + 21b/21c (7) | 7 | 0 | 0 | 0 | **100%** |
| Phase 3 (Neo4j Sync) | cs_31~33 (3) | 2 | 0 | **1 (cs_33 GDS)** | 0 | **67%** |
| Phase 4 (API) | cs_41~43 (3) | 3 | 0 | 0 | 0 | **100%** |
| Phase 5 (FE) | cs_51~54 + v2 (5) | 0 | 0 | 0 | **5 (Redesign V1으로 대체)** | **대체 100%** |
| Redesign V1 (마켓뷰) | PR-1~7 (7) | 7 | 0 | 0 | 0 | **100%** |
| 추가 (Watchlist) | SavedPath/PathAction | 1 | 0 | 0 | 0 | **100%** |

**전체 구현률: 약 93%** (32/34 설계 단위 완료, 1건 미구현 = GDS, 5건은 v1 → Redesign V1로 의도적 대체)

### 핵심 결론
- **Redesign V1**은 기존 `cs_*` 시리즈를 **폐기하지 않는다**. 백엔드(cs_00~43)는 그대로 사용 + 확장(neo4j_dirty 등). 프론트엔드 v1 명세(cs_51~54)만 마켓뷰 5컴포넌트 구조로 **재설계**됨.
- **단일 미구현 항목**은 `cs_33_gds_algorithms.md` (PageRank / Louvain / Betweenness Centrality). 노드 속성 일부(`stock_community` index)만 schema에 예약되어 있고 실제 GDS 호출 태스크는 존재하지 않음.
- Frontend `[symbol]` Deep Dive는 cs_51~54 의도(GraphCanvas/AIGuidePanel/NodeDetailPanel/MiniView)를 그대로 충족하며, `/chainsight` 메인 마켓뷰는 Redesign V1 5-패널(SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed)로 추가됨.

---

## 문서별 상태 테이블

### Phase 0: 인프라 (cs_00~03)

| 설계 문서 | 핵심 요구사항 | 구현 위치 | 상태 |
|-----------|---------------|-----------|------|
| cs_00_legacy_cleanup_api_test | serverless/frontend 잔재 제거, API 5종 테스트 | task_done/CS-0-0 + 기존 cs* 코드 모두 chainsight/로 통합 | **A** 완전 |
| cs_01_migrations_verification | Django 12개 테이블 + RelationConfidence v2.1 필드 | migrations/0001~0008 (8개), RelationConfidence 24개 필드 모두 존재 | **A** 완전 |
| cs_02_neo4j_connection | Neo4jGraphRepository (PID 기반 lazy init) | `chainsight/graph/repository.py` — health_check/upsert_node/get_neighbors/run_query 모두 존재 | **A** 완전 |
| cs_03_neo4j_schema | Constraint 4개 + Index 2개 멱등 생성 | `chainsight/graph/schema.py` + `init_neo4j_schema` 명령어 | **A** 완전 |

### Phase 1: 기초 데이터 (cs_11~13)

| 설계 문서 | 핵심 요구사항 | 구현 위치 | 상태 |
|-----------|---------------|-----------|------|
| cs_11_stock_node_bulk_load | ~500 :Stock 노드 벌크 적재 (STOCK_FIELD_MAP) | `services/neo4j_loader.py` + `load_stocks_to_neo4j` command | **A** 완전 |
| cs_12_sector_industry | :Sector 11 + :Industry 70 + BELONGS_TO ~1000 | `services/neo4j_loader.load_sectors_to_neo4j` + command | **A** 완전 |
| cs_13_peer_relations | PEER_OF 2.5K~3.5K (Finnhub + FMP) | `services/neo4j_loader.fetch_finnhub/fmp_peers + collect_all_peers` + `peer_tasks.py` | **A** 완전 |

### Phase 2: 프로파일 + 관계 (cs_21~25)

| 설계 문서 | 핵심 모델/태스크 | 구현 위치 | 상태 |
|-----------|------------------|-----------|------|
| cs_21_tier_a_profile | CompanyGrowthStage, CompanyCapitalDNA + calculate_all_profiles | `models/growth_stage.py`, `models/capital_dna.py`, `tasks/profile_tasks.py` | **A** 완전 |
| cs_21b_sensitivity_profile | CompanySensitivityProfile (rate/forex/regulation) | `models/sensitivity.py` + `tasks/sensitivity_tasks.py` | **A** 완전 |
| cs_21c_insider_signal | CompanyInsiderSignal (Finnhub P/S 거래코드) | `models/insider_signal.py` + `tasks/insider_tasks.py` | **A** 완전 |
| cs_22_co_mention | ChainNewsEvent, CoMentionEdge + extract_co_mentions | `models/news_event.py`, `models/relation_discovery.py`, `tasks/relation_tasks.py` | **A** 완전 |
| cs_23_price_co_movement | PriceCoMovement (90일 rolling corr, ≥0.5) | `models/relation_discovery.PriceCoMovement` + `tasks/relation_tasks.calculate_price_co_movement` | **A** 완전 |
| cs_24_relation_confidence | RelationConfidence v2.1 (24필드, 5상태, Tier3) | `models/relation_discovery.RelationConfidence` 모든 필드 존재. 0008 마이그레이션으로 플래그 통일 완료 | **A** 완전 |
| cs_25_chain_profile_aggregation | CompanyChainProfile + Celery Beat 8개 | `models/chain_profile.py` + `tasks/profile_tasks.aggregate_chain_profiles` + `config/celery.py` 스케줄 등록 (DB PeriodicTask 기반, drift 인지) | **A** 완전 |

### Phase 3: Neo4j 동기화 + GDS (cs_31~33)

| 설계 문서 | 핵심 요구사항 | 구현 위치 | 상태 |
|-----------|---------------|-----------|------|
| cs_31_profile_neo4j_sync | _profile_to_neo4j_props + sync_profiles_to_neo4j (delta) | `services/neo4j_sync.py` + `tasks/sync_tasks.py` (neo4j_dirty 기반) | **A** 완전 |
| cs_32_relation_neo4j_sync | confirmed/probable MERGE, stale/hidden DELETE | `services/neo4j_sync.sync_dirty_relations` (`tasks/neo4j_dirty_sync_tasks.py`) | **A** 완전 |
| cs_33_gds_algorithms | PageRank + Louvain + Betweenness 노드 속성 적재 (M3) | **미구현** — codebase 전반 grep 결과 `pageRank/louvain/betweenness/gds.` 호출 0건 (schema.py에 stock_community index만 예약) | **C** 미구현 |

### Phase 4: REST API (cs_41~43) + Redesign PR-4

| 설계 문서 | 엔드포인트 | 구현 위치 | 상태 |
|-----------|-----------|-----------|------|
| cs_41_graph_api | GET `/{symbol}/chainsight/graph/?depth=N` + CUSTOMER_OF 파생 | `api/views.ChainSightGraphView` (depth ≤3, derived_type="CUSTOMER_OF" L91) | **A** 완전 |
| cs_42_suggestion_api | GET `/{symbol}/chainsight/suggestions/` (5 카테고리) | `api/views.ChainSightSuggestionView` | **A** 완전 |
| cs_43_trace_api | GET `/chainsight/trace/?from=&to=&max_depth=5` | `api/views.ChainSightTraceView` (max_depth=5 cypher path) | **A** 완전 |
| Redesign PR-4 | seeds / sector / neighbors / signals (마켓뷰 4종) | `api/views.SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView` + `_display_type()` (L532 CUSTOMER_OF outbound 파생) | **A** 완전 |

### Phase 5: 프론트엔드 (cs_51~54, v2) — Redesign V1로 대체

| 설계 문서 (v1) | 의도된 컴포넌트 | Redesign V1 대응 구현 | 상태 |
|---------------|-----------------|----------------------|------|
| cs_51_graph_visualization | GraphView.tsx + GraphControls + NodeDetailPanel | `GraphCanvas.tsx` (`[symbol]`) + `MarketGraphCanvas.tsx` (마켓뷰) + `NodeDetailPanel.tsx` | **D** 대체 (의도 충족, 이름 변경) |
| cs_52_ai_guide_ui | SuggestionCards + CategoryCard | `AIGuidePanel.tsx` (`[symbol]`) + `RelationCardPanel.tsx` (마켓뷰) | **D** 대체 |
| cs_53_chain_trace_ui | TraceView + TracePathView | `TracePathView.tsx` + `FullPathView.tsx` | **D** 대체 (FullPathView로 확장) |
| cs_54_stock_detail_integration | ChainSightMiniView + `/chainsight/[symbol]` 전용 페이지 | `GraphMiniView.tsx` + `app/chainsight/[symbol]/page.tsx` 활성 | **D** 대체 (의도 충족) |
| cs_5_frontend_design_v2 | 3-panel (240/flex-1/320), 6색 관계, CTA 5종 | `[symbol]` 페이지에서 `AIGuidePanel`/`GraphCanvas`/`NodeDetailPanel` 3-panel + `graphStyles.RELATION_STYLES` 6색 + CTA 5종(가설/Watchlist/Validation/여기서탐색/경로찾기) | **D** 대체 (전부 충족) |

### Redesign V1 (PR-1~7) — 마켓뷰 신규

| PR | 산출물 | 구현 위치 | 상태 |
|----|--------|-----------|------|
| PR-1 schema migration | RelationConfidence.neo4j_dirty/previous_status, CompanyChainProfile.neo4j_synced | migration 0005 + 0008 (플래그 통일) | **A** 완전 |
| PR-2 seed selection | 5 시드 소스 + run_seed_selection (매일 12:00 UTC) | `services/seed_selection.py` + `tasks/seed_tasks.py` + `models/seed_snapshot.SeedSnapshot` | **A** 완전 |
| PR-3 dirty sync | sync_dirty_relations + 주1회 batch | `services/neo4j_sync.py` + `tasks/neo4j_dirty_sync_tasks.py` (neo4j queue) | **A** 완전 |
| PR-4 market view API | seeds/sector/neighbors/signals 4종 + CUSTOMER_OF display_type | `api/views.py` 4개 View 클래스 + `_display_type()` | **A** 완전 |
| PR-5 FE core UI | explorationStore + SectorBar + MarketGraphCanvas | `lib/stores/explorationStore.ts` + `components/chainsight/{SectorBar,MarketGraphCanvas}.tsx` | **A** 완전 |
| PR-6 trail + cards | ExplorationTrail + RelationCardPanel | `components/chainsight/{ExplorationTrail,RelationCardPanel}.tsx` | **A** 완전 |
| PR-7 chain story | ChainStoryFeed + 무한스크롤 | `components/chainsight/ChainStoryFeed.tsx` | **A** 완전 |

### 추가 구현 (설계서 외 후속 작업)

| 항목 | 구현 위치 | 비고 |
|------|-----------|------|
| SavedPath / PathAction (Watchlist) | `models/saved_path.py` + `views/watchlist_views.py` + `services/path_service.py`/`recheck_service.py`/`alternatives_service.py` | Redesign V1 이후 후속, DC-2와 별개 |
| `app/chainsight/watchlist/` 페이지 2개 | `frontend/app/chainsight/watchlist/{page,[id]/page}.tsx` + `PathCard.tsx` + `FullPathView.tsx` | Watchlist UX 전체 |
| `regenerate_summary_paths` command | `management/commands/regenerate_summary_paths.py` | 저장 경로 요약 재생성 |

---

## 미구현 항목 상세

### 1. cs_33_gds_algorithms (Phase 3, M3) — **C 미구현**

**설계 요구사항** (cs_33_gds_algorithms.md):
- `graph.project()` → GDS in-memory graph projection
- `gds.pageRank.write()` → `:Stock { pagerank_score }`
- `gds.louvain.write()` → `:Stock { community_id }`
- `gds.betweenness.write()` → `:Stock { betweenness_score }`
- Celery 태스크 `run_gds_algorithms()` (주 1회)
- DoD: 모든 :Stock 노드에 3개 속성 반영

**구현 현황**:
- `chainsight/` 전 디렉토리에서 `pageRank|louvain|betweenness|gds\.|run_gds` grep 결과: **0건** (path_service.py의 1건은 "path_signature"로 무관)
- `chainsight/graph/schema.py`에 `stock_community` index 선언만 예약 (실제 채워주는 코드 없음)
- `chainsight/services/`에 GDS 호출 서비스 없음
- `chainsight/tasks/`에 `run_gds_algorithms` 태스크 없음
- `config/celery.py` 스케줄에도 GDS 항목 없음

**영향**:
- Frontend `MarketGraphCanvas`에서 node centrality 기반 size 가중을 사용한다면 fallback 필요 (현재는 `market_cap` percentile 기반으로 대체 — Redesign PR-4 명세)
- `cs_5_frontend_design_v2`의 "Centrality 메트릭 오버레이" 프로 기능은 비활성 상태

**판단**: Redesign V1이 마켓뷰 경험에서 GDS 없이도 시드/시그널 기반 탐색을 우선시했기 때문에 우선순위가 낮아진 것으로 보임. 명시적 폐기 결정 문서는 발견되지 않음 → 현 시점에는 **보류된 미구현**으로 분류.

---

### 2. 미테스트 항목 (브라우저 검증)

`task_done/chain_sight_redesign_V1/browser_test_report.md`에 명시된 미테스트(미구현 아님):
- 섹터 재탭 → reset
- 체인 스토리 피드 (데이터 부족으로 테스트 미진행)
- 무한 스크롤 동작 (위와 동일)
- truth 관계 엣지 굵기 차등
- 시드 노드 bounce 애니메이션 (범위 밖)

→ 구현은 되어 있고 검증만 미수행 → 갭은 아니나 후속 QA 필요.

---

### 3. QA 검증서 비차단 개선 사항

`task_done/chain_sight_redesign_V1/qa_evaluator_review_01.md` 91% 통과 시 지적된 3건:
1. `chainsightService.ts`의 `fetch()`를 `authAxios`로 통일 (audit P0 #26 패턴)
2. `useInfiniteQuery`의 `pageParam` 명시적 타입 (`as number`)
3. `RelationCardPanel`에 에러 바운더리 또는 에러 상태 UI

→ 기능적 갭 아닌 코드 품질 개선 항목.

---

## 폐기/대체 항목

### Frontend v1 (cs_51~54, cs_5_frontend_design_v2) → Redesign V1으로 대체

**대체 근거**:
- `task_done/chain_sight_redesign_V1/00_summary.md`가 마켓뷰를 **신규 진입점**으로 정의 (Deep Dive와 별개)
- `[symbol]` Deep Dive 페이지는 cs_5_v2의 3-panel + 6색 + CTA 명세를 그대로 충족 → **의도 보존된 대체**
- `/chainsight` 메인은 Redesign 5-패널(SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed)로 **새로 설계됨**

**명세 매핑**:

| cs_v1 의도 | Redesign V1 구현 | 의도 충족? |
|-----------|------------------|-----------|
| GraphView (react-force-graph-2d, Spotlight, lazy expansion) | GraphCanvas + MarketGraphCanvas | ✓ |
| GraphControls (depth 전환, 섹터 색) | FilterPanel + RelationFilterChips | ✓ |
| NodeDetailPanel (CTA 5종) | NodeDetailPanel.tsx ([symbol] 우측) | ✓ |
| SuggestionCards / CategoryCard | AIGuidePanel ([symbol]) + RelationCardPanel (마켓뷰) | ✓ |
| TraceView (from/to 경로 + 단계 설명) | TracePathView + FullPathView | ✓ (FullPathView로 강화) |
| ChainSightMiniView (height=256, top6 ticker) | GraphMiniView.tsx | ✓ |
| 3-panel 레이아웃 (240/flex-1/320) | `[symbol]/page.tsx`의 AIGuide/Graph/NodeDetail | ✓ |
| 관계 6색 (`graphStyles.RELATION_STYLES`) | `components/chainsight/graphStyles.ts` | ✓ |
| 프로 기능 (필터 패널/메트릭 오버레이/비교) | FilterPanel ✓ / Centrality 오버레이 ✗ (GDS 미구현) / 비교 모드 ✗ | 부분 |

**미충족 (cs_v2 프로 기능)**:
- **메트릭 오버레이의 Centrality** — cs_33 GDS 미구현에 종속
- **노드 비교 모드** — 별도 컴포넌트 부재 (v2 명세에만 존재)

→ 두 항목 모두 v2의 "프로 기능" 영역으로, 마켓뷰 우선순위에 밀려 명시적으로 후속 처리됨.

---

### 미완료 후속 작업 (Redesign V1 자체 명시)

`00_summary.md`에 향후 작업으로 명시된 항목 — **갭 아닌 의식적 후속**:
1. 전환 애니메이션 (300ms ease-out, bounce)
2. Heat Score (Phase 2) — 6개 정규화 항목(가격/거래량/관계 변화/co-mention/뉴스/GDS 중심도)
3. LLM 기반 chain title/summary 생성
4. relation_summary / why_now / insight_summary 필드 확장
5. 모바일 card-first UI (현재 `MobileCardList.tsx`만 존재, 풀 모바일 UX는 미완)
6. **GDS** (Heat Score 의존성) — cs_33 미구현과 연결

---

## 검증 핵심 증거

| 검증 항목 | grep/Read 결과 |
|-----------|----------------|
| `neo4j_dirty` 통일 (audit P0 #9) | migrations/0008_unify_neo4j_flags.py 존재 |
| CUSTOMER_OF 파생 | api/views.py L91 (graph), L532-533 (neighbors) 둘 다 구현 |
| Celery Beat drift 인지 | config/celery.py L121-133 주석에 DatabaseScheduler 규약 명시 |
| GDS 미구현 | grep `pageRank|louvain|betweenness|gds\.` → 0건 |
| Watchlist 전체 | models/saved_path.py + views/watchlist_views.py + 3개 services + 2개 frontend 페이지 + PathCard.tsx |
| 마켓뷰 5컴포넌트 | components/chainsight/ 19개 컴포넌트 전수 확인 |

---

## 권장 후속 액션

1. **GDS 구현 결정 명확화**: cs_33을 정식 폐기할지, M3 후속으로 일정에 다시 올릴지 결정. Heat Score Phase 2 의존성 때문에 결정 지연 시 마켓뷰 신뢰도 신호 약화.
2. **cs_5_frontend_design_v2의 "노드 비교 모드"**: 명시적 폐기 or `docs/chain_sight/plan/remaining_work_plan.md`에 후속 등록 필요.
3. **QA 비차단 개선 3건** (chainsightService.ts authAxios 통일 등) 별도 PR로 정리.
4. **redesign_v1_260409/ 4개 문서**를 `cs_*` 시리즈와 cross-link하는 README/index 추가 권장 — 신규 인원이 v1 cs_* → Redesign V1 진화를 추적할 수 있도록.

---

*감사 완료 — 코드 수정 없음, 읽기 전용.*
