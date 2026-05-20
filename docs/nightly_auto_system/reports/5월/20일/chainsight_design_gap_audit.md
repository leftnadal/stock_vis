# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-20
> **범위**: `docs/chain_sight/plan/` (v1.3 + redesign_v1) + `docs/chain_sight/update_v2/` (v1.4) ↔ `chainsight/` 백엔드 + `frontend/components/chainsight/` 프론트 코드 대조
> **방식**: 읽기 전용 감사. 코드 수정 없음.
> **선행 감사**: `docs/nightly_auto_system/reports/5월/19일/chainsight_design_gap_audit.md` (v1.3 기준 94%)
> **금일 차이점**: `docs/chain_sight/update_v2/` (ROADMAP v1.4) 가 최신 활성 설계임을 확인하고, Phase 6 (Path Watchlist 백엔드) + Phase 7 (Path Watchlist 프론트) + CS-4-4 (heat_score) 까지 포함해 재대조.

---

## 요약 (구현률)

| 카테고리 | 총 항목 | 완전 구현(A) | 부분 구현(B) | 미구현(C) | 폐기/대체(D) |
|----------|---------|------------|------------|----------|------------|
| Phase 0 인프라 (CS-0-0 ~ CS-0-3) | 4 | 4 | 0 | 0 | 0 |
| Phase 1 시드 로드 (CS-1-1 ~ CS-1-3) | 3 | 3 | 0 | 0 | 0 |
| Phase 2 파이프라인 (CS-2-1 ~ CS-2-5, +b/+c) | 7 | 7 | 0 | 0 | 0 |
| Phase 3 Neo4j Sync + GDS (CS-3-1 ~ CS-3-3) | 3 | 2 | 1 | 0 | 0 |
| Phase 4 REST API (CS-4-1 ~ CS-4-4) | 4 | 4 | 0 | 0 | 0 |
| 마켓 뷰 4종 API (redesign_v1) | 4 | 4 | 0 | 0 | 0 |
| Phase 5 Frontend (redesign_v1 PR-5~7 + CS-5-5/5-6) | 9 | 9 | 0 | 0 | 0 |
| Phase 5 Frontend (cs_51~54 원안) | 4 | — | — | — | 4 |
| Phase 5 Frontend (cs_5_frontend_design_v2) | 1 | — | — | — | 1 |
| Phase 6 Path Watchlist Backend (CS-6-1 ~ CS-6-7) | 7 | 7 | 0 | 0 | 0 |
| Phase 7 Path Watchlist Frontend (CS-7-1 ~ CS-7-3) | 3 | 3 | 0 | 0 | 0 |
| DC-2 ETF Theme | 1 | 1 | 0 | 0 | 0 |
| Celery Beat 일괄 등록 | 1 | 1 | 0 | 0 | 0 |
| **소계 (활성 설계 기준)** | **46** | **45** | **1** | **0** | **—** |
| 폐기된 설계 (별도 카운트) | 5 | — | — | — | 5 |

**핵심 결과**:
- 활성 설계서(ROADMAP v1.4 + redesign_v1 + PM_DESIGN v1.2) 대비 **구현률 약 98%** (45/46).
- 유일한 부분 구현(B): CS-3-3 GDS 자동화 (1회성 콘솔 실행으로 적재, 주간 배치 미구현). 5월 19일 감사와 동일.
- 미구현(C)은 0건.
- `plan/cs_51~54_*.md` 와 `plan/cs_5_frontend_design_v2.md` 는 모두 redesign_v1 + Phase 7 로 **완전히 대체**됨.

---

## 문서별 상태 테이블

### 1. Phase 0 — 인프라 (CS-0-0 ~ CS-0-3)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `plan/cs_00_legacy_cleanup_api_test.md` | `task_done/CS-0-0_legacy_cleanup_api_test.md` | serverless 제거 + decisions/003 | A |
| `plan/cs_01_migrations_verification.md` | `task_done/CS-0-1_migrations.md` | `chainsight/migrations/0001~0008` (8개) | A |
| `plan/cs_02_neo4j_connection.md` | `task_done/CS-0-2_neo4j_driver.md` | `chainsight/graph/repository.py`, `exceptions.py` | A |
| `plan/cs_03_neo4j_schema.md` | `task_done/CS-0-3_neo4j_schema.md` | `chainsight/graph/schema.py` + `init_neo4j_schema` command | A |

### 2. Phase 1 — 시드 로드 (CS-1-*)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `plan/cs_11_stock_node_bulk_load.md` | `CS-1-1_stock_nodes.md` | `chainsight/management/commands/load_stocks_to_neo4j.py` | A |
| `plan/cs_12_sector_industry.md` | `CS-1-2_sectors.md` | `chainsight/management/commands/load_sectors_to_neo4j.py` | A |
| `plan/cs_13_peer_relations.md` | `CS-1-3_peers.md` | `chainsight/tasks/peer_tasks.py::fetch_and_load_peers` + `chainsight/services/neo4j_loader.py` | A |

### 3. Phase 2 — 파생 데이터 계산 (CS-2-*)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `plan/cs_21_tier_a_profile.md` | `CS-2-1_tier_a_profiles.md` | `chainsight/tasks/profile_tasks.py::calculate_growth_stages, calculate_capital_dna`, `models/growth_stage.py`, `capital_dna.py` | A |
| `plan/cs_21b_sensitivity_profile.md` | `CS-2-1b_sensitivity_profile.md` | `chainsight/tasks/sensitivity_tasks.py`, `models/sensitivity.py` | A |
| `plan/cs_21c_insider_signal.md` | `CS-2-1c_insider_signal.md` | `chainsight/tasks/insider_tasks.py`, `models/insider_signal.py` | A |
| `plan/cs_22_co_mention.md` | `CS-2-2_co_mention.md` | `chainsight/tasks/relation_tasks.py::extract_co_mentions` | A |
| `plan/cs_23_price_co_movement.md` | `CS-2-3_price_co_movement.md` | `chainsight/tasks/relation_tasks.py::calculate_price_co_movement` | A |
| `plan/cs_24_relation_confidence.md` + `plan/relation_confidence_design_v1.md` | `CS-2-4_relation_confidence.md` | `chainsight/tasks/relation_tasks.py::update_relation_confidence, check_stale_and_decay` | A |
| `plan/cs_25_chain_profile_aggregation.md` | `CS-2-5_chain_profile_aggregation.md` | `chainsight/tasks/sync_tasks.py::aggregate_chain_profiles`, `models/chain_profile.py` | A |

### 4. Phase 3 — Neo4j 동기화 + GDS (CS-3-*)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `plan/cs_31_profile_neo4j_sync.md` | `CS-3-1_profile_sync.md` | `chainsight/tasks/sync_tasks.py::sync_profiles_to_neo4j` | A |
| `plan/cs_32_relation_neo4j_sync.md` | `CS-3-2_relation_neo4j_sync.md` | `chainsight/tasks/sync_tasks.py::sync_relations_to_neo4j` + `chainsight/services/neo4j_sync.py::sync_dirty_relations` (PR-3 dirty sync) | A |
| `plan/cs_33_gds_algorithms.md` | `CS-3-3_gds_algorithms.md` | **`chainsight/tasks/gds_tasks.py` 부재** — 1회성 콘솔 실행으로 `pagerank_score`/`community_id`/`betweenness_score` 노드 속성에 적재. `chainsight/services/path_service.py:143`에서 소비. | **B** |

### 5. Phase 4 — REST API (CS-4-*) + Market View

| 설계 문서 | 코드 위치 | 상태 |
|-----------|-----------|------|
| `plan/cs_41_graph_api.md` (Deep dive) | `chainsight/api/views.py::ChainSightGraphView` (`/<symbol>/graph/`) | A |
| `plan/cs_42_suggestion_api.md` | `chainsight/api/views.py::ChainSightSuggestionView` (`/<symbol>/suggestions/`) | A |
| `plan/cs_43_trace_api.md` | `chainsight/api/views.py::ChainSightTraceView` (`/trace/`) | A |
| `update_v2/task_instructions/cs_44_seed_node_heat_score.md` | `chainsight/tasks/seed_tasks.py::calculate_heat_scores` + Beat `chainsight-heat-score-daily` | A |
| `plan/redesign_v1_260409/chainsight_api_design.md` §2 `seeds/` | `chainsight/api/views.py::SeedListView` + 3단 폴백 (Redis → SeedSnapshot → async 복구) | A |
| 동 §3 `sector/{sector}/graph/` | `chainsight/api/views.py::SectorGraphView` | A |
| 동 §4 `{symbol}/neighbors/` | `chainsight/api/views.py::NeighborGraphView` (`_display_type` 파생: `SUPPLIES_TO` + outbound → `CUSTOMER_OF`) | A |
| 동 §5 `signals/` | `chainsight/api/views.py::SignalFeedView::_build_chain_signals` | A |

> URL 등록: `chainsight/api/urls.py` — 마켓 뷰 4종 + Deep dive 3종 + Watchlist 라우터 매핑. 고정 경로(`seeds/`, `sector/<>/graph/`, `signals/`, `trace/`)를 동적 경로(`<symbol>/...`)보다 앞에 배치.

### 6. Phase 5 — Frontend (활성 설계: redesign_v1 + cs_55/56)

| PR / task_done | 설계 문서 | 코드 위치 | 상태 |
|----------------|-----------|-----------|------|
| `task_done/chain_sight_redesign_V1/PR-1` (스키마 보완) | `redesign_v1/chainsight_api_design.md` §8 | `chainsight/migrations/0005_add_neo4j_dirty_previous_status.py` + `models/relation_discovery.py` (save 오버라이드) | A |
| `task_done/chain_sight_redesign_V1/PR-2` | `redesign_v1/chainsight_seed_node_design.md` | `chainsight/services/seed_selection.py`, `chainsight/tasks/seed_tasks.py::run_seed_selection` | A |
| `task_done/chain_sight_redesign_V1/PR-3` | `redesign_v1/chainsight_api_design.md` §8 + dirty sync | `chainsight/services/neo4j_sync.py`, `chainsight/tasks/neo4j_dirty_sync_tasks.py`, `migrations/0008_unify_neo4j_flags.py` | A |
| `task_done/chain_sight_redesign_V1/PR-4` | `redesign_v1/chainsight_api_design.md` §2~§5 | `chainsight/api/views.py` (4 view) + `urls.py` | A |
| `task_done/chain_sight_redesign_V1/PR-5` | `redesign_v1/chainsight_ui_ux_design.md` §4 ①② | `frontend/app/chainsight/page.tsx`, `lib/stores/explorationStore.ts`, `hooks/useMarketView.ts`, `components/chainsight/SectorBar.tsx`, `MarketGraphCanvas.tsx` | A |
| `task_done/chain_sight_redesign_V1/PR-6` | `redesign_v1/chainsight_ui_ux_design.md` §4 ③④ | `components/chainsight/ExplorationTrail.tsx`, `RelationCardPanel.tsx` (Empty/Pre-focus/Focused 3-state) | A |
| `task_done/chain_sight_redesign_V1/PR-7` | `redesign_v1/chainsight_ui_ux_design.md` §4 ⑤ | `components/chainsight/ChainStoryFeed.tsx` (useInfiniteQuery) | A |
| `update_v2/task_done/CS-5-5_market_view.md` | `update_v2/task_instructions/cs_55_market_view.md` | 마켓 뷰 3영역 레이아웃 (구현 완료 표기) | A |
| `update_v2/task_done/CS-5-6_seed_node.md` | `update_v2/task_instructions/cs_56_seed_node.md` | seed 노드 UI 적용 완료 표기 | A |

### 7. Phase 6 — Path Watchlist Backend (update_v2)

| 설계 문서 | 코드 위치 | 상태 |
|-----------|-----------|------|
| `update_v2/task_instructions/cs_61_saved_path_model.md` | `chainsight/models/saved_path.py::SavedPath, PathAction` + `migrations/0006_add_savedpath_pathaction.py` + `admin.py` | A |
| `update_v2/task_instructions/cs_62_watchlist_crud_api.md` | `chainsight/views/watchlist_views.py::WatchlistViewSet` + `serializers/path_watchlist.py` (List/Detail/Create) + router 등록 | A |
| `update_v2/task_instructions/cs_63_summary_path.md` | `chainsight/services/path_service.py` (landmark 압축) + `management/commands/regenerate_summary_paths.py` | A |
| `update_v2/task_instructions/cs_65_recheck_api.md` | `chainsight/services/recheck_service.py` (6단계) + Watchlist viewset action | A |
| `update_v2/task_instructions/cs_66_expand_api.md` | `chainsight/services/expand_service.py` (1-hop 확장 + 종합 점수) | A |
| `update_v2/task_instructions/cs_67_alternatives_api.md` | `chainsight/services/alternatives_service.py` (노드 대안 탐색) | A |
| `update_v2/task_done/cs_71_72_73_phase7_frontend.md` (회고용) | (Phase 6 커밋 SHA `1c62a16 → c6836bd` 7건 기록) | A |

### 8. Phase 7 — Path Watchlist Frontend (update_v2)

| 설계 문서 | 코드 위치 | 상태 |
|-----------|-----------|------|
| `update_v2/task_instructions/cs_71_watch_button.md` | `frontend/components/chainsight/WatchButton.tsx` + `ExplorationTrail.tsx` 통합 + `services/pathWatchlistService.ts` + `hooks/usePathWatchlist.ts` + `types/pathWatchlist.ts` | A |
| `update_v2/task_instructions/cs_72_watchlist_ui.md` | `frontend/app/chainsight/watchlist/...` (카드 리스트) | A |
| `update_v2/task_instructions/cs_73_full_path_view.md` | `frontend/components/chainsight/FullPathView.tsx` (액션 UX 포함) | A |

### 9. 기타 (DC-2, Celery Beat)

| 설계 / task_done | 코드 위치 | 상태 |
|------------------|-----------|------|
| `task_done/DC-2_etf_holdings_theme.md` | `chainsight/management/commands/load_themes_to_neo4j.py` (serverless ETFProfile/Holding 재활용 → Neo4j `:Theme` + `HAS_THEME`) | A |
| `task_done/celery_beat_registration.md` | `config/celery.py::beat_schedule` — `chainsight-*` 9개 (seed-selection/dirty-sync/heat-score/co-mention/profiles/price/relation-confidence/stale-decay/chain-profile) | A |

---

## 미구현 항목 상세

### (B) 부분 구현 — 1건

#### CS-3-3 GDS 알고리즘 배치 — 자동화 미완

- **설계 (`plan/cs_33_gds_algorithms.md`)**: `chainsight/tasks/gds_tasks.py` 에 `run_gds_algorithms` Celery task 로 PageRank/Louvain/Betweenness 주간 배치.
- **실제 상태**:
  - `chainsight/tasks/` 디렉토리 목록에 `gds_tasks.py` 가 **존재하지 않음** (`ls chainsight/tasks/` 확인).
  - `gds.pageRank`, `gds.louvain`, `gds.betweenness` 등의 Cypher 호출이 `chainsight/` 어디에도 없음 (grep 결과: `chainsight/graph/schema.py`, `chainsight/management/commands/regenerate_summary_paths.py`, `chainsight/services/path_service.py` 3개 — 모두 *읽기*만 수행).
  - `task_done/CS-3-3_gds_algorithms.md` 기준, GDS 2.13.2 를 Neo4j 콘솔에서 직접 실행해 `:Stock` 속성 `pagerank_score` / `community_id` / `betweenness_score` 를 1회성 적재. `chainsight/services/path_service.py:143`이 이 값을 소비하므로 데이터는 살아 있다.
- **영향**: 시간이 지나면 community/pagerank가 stale. Stock 추가/제거 시 자동 재계산 안 됨. 5월 19일 감사 이후 변화 없음.
- **권고**: ROADMAP v1.4 의 Phase 3 항목으로 `gds_tasks.py` 신설(주간 배치) 또는 1회성 결정을 `update_v2/decisions/` 에 명시적 기록.

### (C) 미구현 — 0건

ROADMAP v1.4 + redesign_v1 + PM_DESIGN v1.2 기준으로 완전 누락된 항목은 발견되지 않았다.

### 설계서가 명시한 "범위 밖 / 후속" (정보용, 갭 카운트 제외)

`redesign_v1/00_summary.md` "범위 밖":

- 전환 애니메이션 (300ms ease-out, bounce) — 그래프 캔버스의 시드 bounce 미적용
- LLM 기반 chain title/summary 생성 (`signals/` 응답)
- 2차 카드 LLM 설명 필드 (`relation_summary`, `why_now`, `insight_summary`) — `neighbors/` 응답에 미포함, 향후 슬롯
- 모바일 카드 리스트 풀스크린 모드
- GDS 자동 재계산 (위 CS-3-3 와 동일 항목)

**Phase 8(이벤트 전파)**: `redesign_v1/chainsight_seed_node_design.md` §4 D-1~D-3 는 ChromaDB + Gemini Embedding + lagged correlation. Phase 3 종속이며 60거래일 데이터 누적 대기 중 — ROADMAP v1.4 상 명시적 Phase 미설정. 갭이 아닌 "축적 대기".

---

## 폐기/대체 항목

### D-1. `plan/cs_51~54_*.md` (Phase 5 원안) → redesign_v1 + Phase 7 로 대체

| 원안 | 대체 위치 | 비고 |
|------|-----------|------|
| `plan/cs_51_graph_visualization.md` — `GraphView.tsx` Spotlight + force-graph-2d | `frontend/components/chainsight/MarketGraphCanvas.tsx` + `GraphCanvas.tsx` (deep dive) | force-graph-2d 채택 유지. entry 2-track (마켓 뷰 + deep dive). |
| `plan/cs_52_ai_guide_ui.md` — `SuggestionCards.tsx` 카테고리 그리드 | `components/chainsight/AIGuidePanel.tsx` (deep dive) + `RelationCardPanel.tsx` (마켓 뷰 ④) | 카테고리 컨셉 유지, 마켓 뷰는 관계 카드 패턴으로 진화. |
| `plan/cs_53_chain_trace_ui.md` — `TraceView.tsx` from/to 수동 입력 | `components/chainsight/TracePathView.tsx`, `FullPathView.tsx` (Phase 7) | Path Watchlist 의 `FullPathView` 가 trace UI 를 흡수. |
| `plan/cs_54_stock_detail_integration.md` — 종목 상세 탭 미니뷰 | `frontend/app/stocks/[symbol]/page.tsx` 통합 + `components/chainsight/GraphMiniView.tsx` | 미니뷰 유지, "Coming Soon" 탭 활성화 완료. |

### D-2. `plan/cs_5_frontend_design_v2.md` (전용 워크스페이스 단일 entry) → redesign_v1 (Market view + Deep dive 2-track)

`cs_5_frontend_design_v2.md` 는 `/chainsight/[symbol]` 단일 entry 를 제안했으나, redesign_v1 에서 **`/chainsight` 마켓 뷰가 메인** 으로 격상되고 deep dive 는 보조 화면으로 재정의.

| v2 안 | redesign_v1 (활성) | 변경 이유 |
|-------|--------------------|---------|
| `/chainsight/[symbol]` 단일 entry | `/chainsight` 마켓 허브 + `/chainsight/[symbol]` deep dive 보조 | "탐색이 검색을 선행한다" UX 원칙 |
| 3-panel (AI Guide / Graph / NodeDetail) | 5-section (SectorBar → Graph → Trail → RelationCard → ChainStory) | 그래프-카드 동등 구조 + 공유 탐색 상태 도입 |
| `useChainsight` 단일 훅 | `useChainsight`(deep dive) + `useMarketView`(seeds/sector/neighbors/signals) 분리 | 4-API 분리에 맞춘 훅 분리 |

> 컴포넌트 일괄 폐기는 아님. `AIGuidePanel`, `NodeDetailPanel`, `FilterPanel`, `RelationLegend`, `MobileCardList` 는 deep dive 화면에서 그대로 재사용.

### D-3. `CUSTOMER_OF` 별도 저장 → `SUPPLIES_TO` canonical + API 파생

- ROADMAP v1.3 §2.4 (v1.4 에서도 유지) — `CUSTOMER_OF` 별도 관계 저장 폐기.
- 코드 반영:
  - `chainsight/api/views.py::NeighborGraphView._display_type` — `SUPPLIES_TO` + outbound → `CUSTOMER_OF` 파생.
  - `chainsight/api/views.py::ChainSightGraphView` — `derived_type = "CUSTOMER_OF"` 부착.
- DB / Neo4j에 `CUSTOMER_OF` 저장 흔적 없음 (grep 결과 코드/마이그레이션 외 한국어 본문 매치 외 없음). 완전 반영.

### D-4. serverless/ Chain Sight 레거시 (CS-0-0)

- `serverless/views.py::chain_sight_*_api` 6개, `serverless/services/chain_sight_*.py` 3개, frontend `chain-sight/` 컴포넌트 8개 — 모두 제거.
- `ETFProfile/ETFHolding/ThemeMatch` 모델은 DC-2 까지 `# LEGACY_KEEP_UNTIL_DC2` 로 보존되었고, `chainsight/management/commands/load_themes_to_neo4j.py` 가 해당 모델을 읽어 Neo4j 의 `:Theme` + `HAS_THEME` 로 적재. DC-2 완료 후 제거 시점이 ROADMAP v1.4 에 명시되지 않은 점은 메모.

### D-5. ROADMAP v1.3 → v1.4 슈퍼시드

- `plan/chain_sight_roadmap_v1.3.md` 는 v1.4 (`update_v2/ROADMAP_v1.4.md`)에 의해 전면 슈퍼시드.
- 추가: Phase 6 (Path Watchlist 백엔드), Phase 7 (Path Watchlist 프론트), CS-4-4 (heat_score), CS-5-5 (마켓뷰 3영역), CS-5-6 (시드 노드 UI).
- 보존: 원칙 1~6, 4-Layer 아키텍처, 관계 신뢰도 정책, DC-1~DC-6 데이터 로드맵.
- 미반영: `plan/` 디렉토리는 v1.3 시기 파일이 남아 있음 — 위 D-1 / D-2 와 함께 폐기 마킹 권장 (`> ⚠️ ROADMAP_v1.4 로 대체` 헤더 추가).

---

## Cross-Reference 표 (설계 ↔ task_done ↔ 코드)

| 설계 문서 ID | task_done | 핵심 코드 산출물 | 상태 |
|--------------|-----------|---------------|------|
| cs_00 / update_v2/cs_00 | CS-0-0 (양쪽) | serverless 제거 | A |
| cs_01 | CS-0-1 | migrations/0001~0008 (8개) | A |
| cs_02 | CS-0-2 | graph/repository.py | A |
| cs_03 | CS-0-3 | graph/schema.py + init_neo4j_schema | A |
| cs_11 | CS-1-1 | load_stocks_to_neo4j | A |
| cs_12 | CS-1-2 | load_sectors_to_neo4j | A |
| cs_13 | CS-1-3 | tasks/peer_tasks + load_peers_to_neo4j | A |
| cs_21 | CS-2-1 | tasks/profile_tasks | A |
| cs_21b | CS-2-1b | tasks/sensitivity_tasks | A |
| cs_21c | CS-2-1c | tasks/insider_tasks | A |
| cs_22 | CS-2-2 | tasks/relation_tasks::extract_co_mentions | A |
| cs_23 | CS-2-3 | tasks/relation_tasks::calculate_price_co_movement | A |
| cs_24 + relation_confidence_design_v1 | CS-2-4 | tasks/relation_tasks::update_relation_confidence | A |
| cs_25 | CS-2-5 | tasks/sync_tasks::aggregate_chain_profiles | A |
| cs_31 | CS-3-1 | tasks/sync_tasks::sync_profiles_to_neo4j | A |
| cs_32 | CS-3-2 | tasks/sync_tasks::sync_relations_to_neo4j + neo4j_sync.py | A |
| cs_33 | CS-3-3 | (gds_tasks.py 부재 — 1회성 콘솔 적재) | **B** |
| cs_41 | CS-4-1 | ChainSightGraphView | A |
| cs_42 | CS-4-2 | ChainSightSuggestionView | A |
| cs_43 | CS-4-3 | ChainSightTraceView | A |
| update_v2/cs_44 | update_v2/CS-4-4_heat_score | tasks/seed_tasks::calculate_heat_scores | A |
| redesign_v1/api_design §2 | chain_sight_redesign_V1/PR-4 | SeedListView + SeedSnapshot fallback | A |
| redesign_v1/api_design §3 | chain_sight_redesign_V1/PR-4 | SectorGraphView | A |
| redesign_v1/api_design §4 | chain_sight_redesign_V1/PR-4 | NeighborGraphView (display_type) | A |
| redesign_v1/api_design §5 | chain_sight_redesign_V1/PR-4 | SignalFeedView | A |
| redesign_v1/seed_node_design | chain_sight_redesign_V1/PR-2 | services/seed_selection + tasks/seed_tasks | A |
| redesign_v1/ui_ux_design | chain_sight_redesign_V1/PR-5~7 | 마켓뷰 5컴포넌트 + page.tsx + explorationStore | A |
| update_v2/cs_55_market_view | update_v2/CS-5-5_market_view | (마켓뷰 레이아웃 적용) | A |
| update_v2/cs_56_seed_node | update_v2/CS-5-6_seed_node | (시드 노드 UI 적용) | A |
| update_v2/cs_61_saved_path_model | update_v2/cs_71_72_73_phase7_frontend (회고) | models/saved_path.py + migrations/0006 | A |
| update_v2/cs_62_watchlist_crud_api | 동 | views/watchlist_views.py::WatchlistViewSet + serializers/path_watchlist.py | A |
| update_v2/cs_63_summary_path | 동 | services/path_service.py + management/commands/regenerate_summary_paths.py | A |
| update_v2/cs_65_recheck_api | 동 | services/recheck_service.py | A |
| update_v2/cs_66_expand_api | 동 | services/expand_service.py | A |
| update_v2/cs_67_alternatives_api | 동 | services/alternatives_service.py | A |
| update_v2/cs_71_watch_button | update_v2/cs_71_72_73_phase7_frontend | components/chainsight/WatchButton.tsx + types/pathWatchlist.ts + services/pathWatchlistService.ts + hooks/usePathWatchlist.ts | A |
| update_v2/cs_72_watchlist_ui | 동 | frontend/app/chainsight/watchlist/* | A |
| update_v2/cs_73_full_path_view | 동 | components/chainsight/FullPathView.tsx | A |
| cs_5_frontend_design_v2 | — | redesign_v1 PR-5~7로 대체 | D |
| plan/cs_51 ~ cs_54 | (CS-5-1~5-3) | redesign_v1 + Phase 7로 대체 | D (원안 폐기, 부분 컴포넌트 재사용) |
| plan/sec_pipeline_base/pr_detail | (SEC pipeline 별도) | sec_pipeline 앱 | (본 감사 범위 외) |
| plan/remaining_work_plan | — | 우선순위 1~6 모두 완료 (Phase 6~7 도입으로 확장) | A |
| chain_sight_roadmap_v1.3 | — | ROADMAP_v1.4 로 슈퍼시드 | D |

---

## 5월 19일 대비 차이 요약

1. **활성 설계서가 v1.3 → v1.4 로 확정 인지**: `update_v2/ROADMAP_v1.4.md` 가 사실상의 현재 활성 설계.
2. **CS-4-4 heat_score, Phase 6 (CS-6-*), Phase 7 (CS-7-*) 가 모두 구현 완료** 로 카운트됨에 따라 활성 항목 분모가 34 → 46 으로 증가, 구현률이 94% → 98% 로 상향. 새 항목 12개 모두 A 등급.
3. **부분 구현 항목은 CS-3-3 GDS 자동화 1건으로 변동 없음**.
4. **폐기 항목 추가 1건**: `chain_sight_roadmap_v1.3.md` 자체가 v1.4 로 슈퍼시드(D-5 신규 항목으로 표시).

---

## 권고

1. **CS-3-3 GDS 자동화 결정**: v1.4 진행 도중에도 미해결. `chainsight/tasks/gds_tasks.py` 신설 또는 `update_v2/decisions/` 에 "수동 운영 유지" 결정 명시 필요. Stock 동기화 주기와 함께 검토.
2. **`plan/` 디렉토리 폐기 헤더 추가**: `cs_51~54_*.md`, `cs_5_frontend_design_v2.md`, `chain_sight_roadmap_v1.3.md` 상단에 `> ⚠️ 폐기. ROADMAP_v1.4 / redesign_v1 참조` 헤더 권장. 신규 작업자가 plan 디렉토리를 active source 로 오인할 위험.
3. **SeedHeatScore 모델 결정**: `redesign_v1/chainsight_api_design.md §8` 에 Phase 2 항목으로 명시되었으나, 실제 구현은 별도 모델 없이 `:Stock.heat_score` 노드 속성으로 적재됨. 향후 시계열 조회 요구 발생 시 모델 신설 여부 결정.
4. **2차 카드 LLM 필드**: `relation_summary`/`why_now`/`insight_summary` 도입 시점에 토큰 비용 + 캐시 정책 동시 검토. `signals/` 응답의 chain title/summary 도 같은 슬롯.
5. **ETF 레거시 정리 종결 시점**: `serverless/ETFProfile/ETFHolding/ThemeMatch` 의 `# LEGACY_KEEP_UNTIL_DC2` 태그가 DC-2 완료 이후에도 보존됨. `load_themes_to_neo4j.py` 이외 사용처 점검 후 제거 일정 합의.
6. **`update_v2/task_done/CS-4-4_heat_score.md`** 가 "다음: cs_51 (Phase 5 프론트)" 로 끝나는데 실제로 cs_51 은 폐기되고 cs_55/56 으로 진행됨. task_done 문서의 "다음" 포인터 보정 권장.

---

**END OF DOCUMENT**
