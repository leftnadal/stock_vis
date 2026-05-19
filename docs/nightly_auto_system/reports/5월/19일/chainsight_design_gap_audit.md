# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-19
> **범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `chainsight/` 백엔드 + `frontend/components/chainsight/` 프론트 코드 대조
> **방식**: 읽기 전용 감사. 코드 수정 없음.
> **참조**: `docs/chain_sight/task_done/`에 기록된 완료 보고서와 cross-reference.

---

## 요약 (구현률)

| 카테고리 | 총 항목 | 완전 구현(A) | 부분 구현(B) | 미구현(C) | 폐기/대체(D) |
|----------|---------|------------|------------|----------|------------|
| Phase 0 인프라 (CS-0-*) | 4 | 4 | 0 | 0 | 0 |
| Phase 1 시드 로드 (CS-1-*) | 3 | 3 | 0 | 0 | 0 |
| Phase 2 파이프라인 (CS-2-*) | 5+2 | 7 | 0 | 0 | 0 |
| Phase 3 Neo4j Sync/GDS (CS-3-*) | 3 | 2 | 1 | 0 | 0 |
| Phase 4 REST API (CS-4-*) | 3 + 4 | 7 | 0 | 0 | 0 |
| Phase 5 Frontend (cs_51~54 원안) | 4 | 0 | 0 | 0 | 4 |
| Phase 5 Frontend (cs_5_frontend_design_v2) | 11 | 0 | 0 | 0 | 11 |
| Phase 5 Frontend (redesign_v1) | 7 PR | 7 | 0 | 0 | 0 |
| DC-2 ETF Theme | 1 | 1 | 0 | 0 | 0 |
| Celery Beat 일괄 등록 | 1 | 1 | 0 | 0 | 0 |
| **소계 (활성 설계 기준)** | **34** | **32** | **1** | **0** | **—** |
| 폐기된 설계 (소계 별도) | 15 | — | — | — | 15 |

**핵심 결과**:
- 활성 설계서(roadmap v1.3 + redesign_v1) 대비 **구현률 약 94%** (32/34).
- 미구현(C)은 0건. 부분 구현(B)은 CS-3-3 GDS 1건(스크립트 없이 Cypher 직접 실행).
- 프론트엔드의 cs_51~54 원안과 cs_5_frontend_design_v2는 모두 redesign_v1으로 **완전히 대체**됨.

---

## 문서별 상태 테이블

### 1. Phase 0 — 인프라 (CS-0-0 ~ CS-0-3)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `cs_00_legacy_cleanup_api_test.md` | `CS-0-0_legacy_cleanup_api_test.md` | (serverless 정리, decisions/003) | A |
| `cs_01_migrations_verification.md` | `CS-0-1_migrations.md` | `chainsight/migrations/0001~0008` (8개) | A |
| `cs_02_neo4j_connection.md` | `CS-0-2_neo4j_driver.md` | `chainsight/graph/repository.py`, `exceptions.py` | A |
| `cs_03_neo4j_schema.md` | `CS-0-3_neo4j_schema.md` | `chainsight/graph/schema.py` + `init_neo4j_schema` command | A |

### 2. Phase 1 — 시드 로드 (CS-1-*)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `cs_11_stock_node_bulk_load.md` | `CS-1-1_stock_nodes.md` | `management/commands/load_stocks_to_neo4j.py` | A |
| `cs_12_sector_industry.md` | `CS-1-2_sectors.md` | `management/commands/load_sectors_to_neo4j.py` | A |
| `cs_13_peer_relations.md` | `CS-1-3_peers.md` | `tasks/peer_tasks.py` + `load_peers_to_neo4j.py` | A |

### 3. Phase 2 — 파생 데이터 계산 (CS-2-*)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `cs_21_tier_a_profile.md` | `CS-2-1_tier_a_profiles.md` | `tasks/profile_tasks.py`, `models/growth_stage.py`, `capital_dna.py` | A |
| `cs_21b_sensitivity_profile.md` | `CS-2-1b_sensitivity_profile.md` | `tasks/sensitivity_tasks.py`, `models/sensitivity.py` | A |
| `cs_21c_insider_signal.md` | `CS-2-1c_insider_signal.md` | `tasks/insider_tasks.py`, `models/insider_signal.py` | A |
| `cs_22_co_mention.md` | `CS-2-2_co_mention.md` | `tasks/relation_tasks.py::extract_co_mentions` | A |
| `cs_23_price_co_movement.md` | `CS-2-3_price_co_movement.md` | `tasks/relation_tasks.py::calculate_price_co_movement` | A |
| `cs_24_relation_confidence.md` + `relation_confidence_design_v1.md` | `CS-2-4_relation_confidence.md` | `tasks/relation_tasks.py::update_relation_confidence`, `check_stale_and_decay` | A |
| `cs_25_chain_profile_aggregation.md` | `CS-2-5_chain_profile_aggregation.md` | `tasks/sync_tasks.py::aggregate_chain_profiles`, `models/chain_profile.py` | A |

### 4. Phase 3 — Neo4j 동기화 + GDS (CS-3-*)

| 설계 문서 | task_done | 코드 위치 | 상태 |
|-----------|-----------|-----------|------|
| `cs_31_profile_neo4j_sync.md` | `CS-3-1_profile_sync.md` | `tasks/sync_tasks.py::sync_profiles_to_neo4j` | A |
| `cs_32_relation_neo4j_sync.md` | `CS-3-2_relation_neo4j_sync.md` | `tasks/sync_tasks.py::sync_relations_to_neo4j` + `services/neo4j_sync.py` (PR-3 개선) | A |
| `cs_33_gds_algorithms.md` | `CS-3-3_gds_algorithms.md` | **`tasks/gds_tasks.py` 부재** — Neo4j 콘솔에서 직접 실행 (pagerank/community_id가 Stock 노드 속성에 적재됨, `services/path_service.py`에서 소비) | **B** |

### 5. Phase 4 — REST API (CS-4-*) + Market View

| 설계 문서 | 코드 위치 | 상태 |
|-----------|-----------|------|
| `cs_41_graph_api.md` (Deep dive) | `api/views.py::ChainSightGraphView` (`/<symbol>/graph/`) | A |
| `cs_42_suggestion_api.md` (Deep dive) | `api/views.py::ChainSightSuggestionView` (`/<symbol>/suggestions/`) | A |
| `cs_43_trace_api.md` (Deep dive) | `api/views.py::ChainSightTraceView` (`/trace/`) | A |
| `redesign_v1/chainsight_api_design.md` §2 `seeds/` | `api/views.py::SeedListView` + 3단 폴백 (Redis → SeedSnapshot → async 복구) | A |
| `redesign_v1/chainsight_api_design.md` §3 `sector/{sector}/graph/` | `api/views.py::SectorGraphView` | A |
| `redesign_v1/chainsight_api_design.md` §4 `{symbol}/neighbors/` | `api/views.py::NeighborGraphView` (display_type 파생 포함) | A |
| `redesign_v1/chainsight_api_design.md` §5 `signals/` | `api/views.py::SignalFeedView` (`_build_chain_signals`) | A |

> URL 등록은 `chainsight/api/urls.py`에 마켓 뷰 4개 + Deep dive 3개 모두 매핑됨. `Watchlist` 라우터도 함께 등록.

### 6. Phase 5 — Frontend (활성 설계: `redesign_v1`)

| PR (task_done) | 설계 문서 | 코드 위치 | 상태 |
|----------------|-----------|-----------|------|
| PR-1 schema_migration | `chainsight_api_design.md` §8 | `migrations/0005_add_neo4j_dirty_previous_status.py` | A |
| PR-2 seed_selection_task | `chainsight_seed_node_design.md` | `services/seed_selection.py`, `tasks/seed_tasks.py` | A |
| PR-3 neo4j_dirty_sync | `chainsight_api_design.md` §8 + neo4j_dirty | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py`, `migrations/0008_unify_neo4j_flags.py` | A |
| PR-4 market_view_api | `chainsight_api_design.md` §2~§5 | `api/views.py` (4 view + urls) | A |
| PR-5 fe_core_ui | `chainsight_ui_ux_design.md` §4 ①② | `app/chainsight/page.tsx`, `lib/stores/explorationStore.ts`, `hooks/useMarketView.ts`, `components/chainsight/SectorBar.tsx`, `MarketGraphCanvas.tsx` | A |
| PR-6 trail_and_cards | `chainsight_ui_ux_design.md` §4 ③④ | `components/chainsight/ExplorationTrail.tsx`, `RelationCardPanel.tsx` | A |
| PR-7 chain_story_feed | `chainsight_ui_ux_design.md` §4 ⑤ | `components/chainsight/ChainStoryFeed.tsx` | A |

### 7. 기타 (DC-2, Celery Beat)

| 설계 / task_done | 코드 위치 | 상태 |
|------------------|-----------|------|
| `DC-2_etf_holdings_theme.md` | `management/commands/load_themes_to_neo4j.py` (serverless ETFProfile/Holding 재활용) | A |
| `celery_beat_registration.md` | `config/celery.py::beat_schedule` (chainsight-*: 8개 + redesign 추가 2개) | A |

---

## 미구현 항목 상세

### (B) 부분 구현

#### CS-3-3 GDS 알고리즘 배치 — 자동화 미완

- **설계**: `chainsight/tasks/gds_tasks.py`에 `run_gds_algorithms` Celery task로 PageRank/Louvain/Betweenness 주간 배치.
- **실제**:
  - `chainsight/tasks/` 디렉토리에 `gds_tasks.py` 파일이 **존재하지 않음** (확인: `ls chainsight/tasks/`).
  - `chainsight/` 어디에도 `gds.pageRank`, `gds.louvain` 등의 Cypher 호출이 없음.
  - `task_done/CS-3-3_gds_algorithms.md`에 따르면 Neo4j 콘솔에서 GDS 2.13.2를 직접 실행해 노드 속성(`pagerank_score`, `community_id`, `betweenness_score`)을 1회성 적재.
  - `services/path_service.py:143`에서 `centrality[n]['pagerank']` 등을 소비하므로 **데이터는 존재**하지만 갱신 자동화는 누락.
- **영향**: 시간이 지나면 community/pagerank가 stale 상태. Stock 추가/제거 시 자동 재계산 안 됨.
- **권고**: `cs_33_gds_algorithms.md`에 명시된 task를 실제로 작성하거나, 1회성으로 명시적 결정 후 GDS 미실행을 acceptable로 문서화.

### (C) 미구현 — 없음

활성 설계서(roadmap v1.3 + redesign_v1) 기준으로 누락된 항목은 발견되지 않았다.

### 설계서 외 / 후속 범위 (정보용)

`redesign_v1/00_summary.md` "범위 밖 (후속 작업)"에 명시된 항목:

- Heat Score 계산 (Phase 2 task) — `SeedHeatScore` 모델 신규 설계만 제안됨, 모델/마이그레이션 부재.
- 2차 카드 LLM 설명 (`relation_summary`, `why_now`, `insight_summary`) — `neighbors/` 응답에 미포함.
- 전환 애니메이션 (300ms ease-out, bounce).
- LLM 기반 chain title/summary 생성.
- 모바일 대응(풀스크린 그래프 오버레이).
- Graph Data Science 자동 재계산 (CS-3-3 자동화와 동일 항목).

이들은 명시적 "범위 밖" 표기이므로 갭으로 카운트하지 않는다. 단, **장기 백로그**로 추적 권장.

---

## 폐기/대체 항목

### D-1. cs_51~54 (Frontend Phase 5 원안) → redesign_v1 으로 대체

| 원안 (cs_51~54) | 대체 위치 | 비고 |
|----------------|---------|------|
| `cs_51_graph_visualization.md` — `GraphView.tsx` Spotlight | `components/chainsight/MarketGraphCanvas.tsx` + `GraphCanvas.tsx` | force-graph-2d 채택은 유지. 메인 entry는 `/chainsight` 마켓 뷰 + `/chainsight/[symbol]` deep dive 2-track. |
| `cs_52_ai_guide_ui.md` — `SuggestionCards.tsx` 카테고리 | `components/chainsight/AIGuidePanel.tsx` (deep dive 좌측), `RelationCardPanel.tsx`(마켓 뷰 ④) | 카테고리 컨셉 유지, 그러나 마켓 뷰는 "관계 카드" 패턴으로 변경. |
| `cs_53_chain_trace_ui.md` — `TraceView.tsx` from/to 입력 | `components/chainsight/TracePathView.tsx`, `FullPathView.tsx` (deep dive 한정) | 마켓 뷰 v1 범위에서 빠짐(별도). |
| `cs_54_stock_detail_integration.md` — 종목 상세 탭 미니뷰 | `app/stocks/[symbol]/page.tsx` 통합 + `components/chainsight/GraphMiniView.tsx` | 미니뷰는 유지, "Coming Soon" 탭 활성화 완료. |

### D-2. cs_5_frontend_design_v2 (전용 워크스페이스 단일 진입) → redesign_v1 (Market view + Deep dive 2-track)

`cs_5_frontend_design_v2.md`는 "전용 워크스페이스 `/chainsight/[symbol]`" 단일 entry를 제안했으나, redesign_v1에서 **`/chainsight` 마켓 뷰가 메인 진입점**으로 격상되고 deep dive는 보조 화면으로 재정의됨.

| v2 안 | redesign_v1 (활성) | 변경 이유 |
|-------|--------------------|---------|
| `/chainsight/[symbol]` 전용 워크스페이스 단일 entry | `/chainsight` 마켓 탐색 허브 (메인) + `/chainsight/[symbol]` deep dive (보조) | 시장 탐색이 종목 검색보다 선행하는 UX 흐름. |
| 3-panel (AI Guide / Graph / NodeDetail) | 마켓 뷰 5-section (SectorBar → Graph → Trail → RelationCard → ChainStory) | 그래프+카드 동등 구조, 공유 탐색 상태 도입. |
| `useChainsight` 단일 훅 | `useChainsight`(deep dive) + `useMarketView`(seeds/sector/neighbors/signals) 분리 | 데이터 소스 4종(`seeds/`, `sector graph/`, `neighbors/`, `signals/`) 추가에 맞춰 분리. |

> 단, cs_5_frontend_design_v2의 일부 컴포넌트(`AIGuidePanel`, `NodeDetailPanel`, `FilterPanel`, `RelationLegend`, `MobileCardList`)는 deep dive 화면에서 그대로 **재사용**됨. v2 → redesign_v1는 entry 구조 재편이지 컴포넌트 일괄 폐기는 아니다.

### D-3. CUSTOMER_OF 별도 저장 → SUPPLIES_TO canonical + API 파생

- roadmap v1.3 §2.4에서 `CUSTOMER_OF` 별도 관계 저장 폐기 결정.
- 코드 반영 확인:
  - `api/views.py::NeighborGraphView::_display_type` — `SUPPLIES_TO` + `outbound` → `CUSTOMER_OF` 파생.
  - `api/views.py::ChainSightGraphView` — `derived_type = "CUSTOMER_OF"` 부착.
- DB/Neo4j에 `CUSTOMER_OF` 저장 흔적 없음(grep 무 결과). 완전 반영.

### D-4. serverless/ Chain Sight 레거시 (CS-0-0)

- `serverless/views.py::chain_sight_*_api` 6개, `serverless/services/chain_sight_*.py` 3개, frontend `chain-sight/` 컴포넌트 8개 등 모두 제거.
- `ETFProfile/ETFHolding/ThemeMatch`는 DC-2 직전까지 `# LEGACY_KEEP_UNTIL_DC2`로 보존 후 `load_themes_to_neo4j.py`에서 재활용. (DC-2 완료 이후의 제거 여부는 별도 감사 필요.)

---

## Cross-Reference 표 (설계 ↔ task_done ↔ 코드)

| 설계 문서 ID | task_done 파일 | 핵심 코드 산출물 | 상태 |
|-------------|---------------|---------------|------|
| cs_00 | CS-0-0 | serverless 제거 | A |
| cs_01 | CS-0-1 | migrations/0001~0008 (총 8개) | A |
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
| cs_32 | CS-3-2 | tasks/sync_tasks::sync_relations_to_neo4j | A |
| cs_33 | CS-3-3 | (tasks/gds_tasks.py 부재) | **B** |
| cs_41 | CS-4-1_2_3 | ChainSightGraphView | A |
| cs_42 | CS-4-1_2_3 | ChainSightSuggestionView | A |
| cs_43 | CS-4-1_2_3 | ChainSightTraceView | A |
| cs_51 | CS-5-1 | MarketGraphCanvas + GraphCanvas | A(D로 대체된 원안 포함) |
| cs_52 | CS-5-2 | AIGuidePanel + RelationCardPanel | A(D로 대체) |
| cs_53 | CS-5-3 | TracePathView + FullPathView | A(D로 대체) |
| cs_54 | CS-5-3(통합) | GraphMiniView + stocks/[symbol] | A(D로 대체) |
| cs_5_frontend_design_v2 | — | redesign_v1 PR-5~7로 대체 | D |
| redesign_v1/api_design | chain_sight_redesign_V1/PR-1~4 | api/views.py + urls.py + 4 view | A |
| redesign_v1/seed_node_design | chain_sight_redesign_V1/PR-2 | services/seed_selection + tasks/seed_tasks | A |
| redesign_v1/ui_ux_design | chain_sight_redesign_V1/PR-5~7 | 마켓 뷰 5컴포넌트 + page.tsx + explorationStore | A |
| redesign_v1/marketview_pr_prompts | (전체 PR 가이드) | — | A (가이드성 문서) |
| sec_pipeline_base/pr_detail | (별도 SEC pipeline) | sec_pipeline 앱 | (본 감사 범위 외) |
| remaining_work_plan | (체크리스트) | 모든 우선순위 1~6 항목 완료 확인 | A |

---

## 권고

1. **CS-3-3 GDS 자동화**: 현재 1회성 콘솔 실행으로 적재된 pagerank/community 값이 stale될 위험이 있다. `chainsight/tasks/gds_tasks.py`를 신설해 주간 배치로 자동화하거나, 1회성 결정을 `decisions/`에 명시적으로 기록.
2. **폐기 문서 마킹**: `cs_51~54_*.md`와 `cs_5_frontend_design_v2.md`는 redesign_v1으로 대체되었음에도 plan 디렉토리에 그대로 남아있어 신규 작업자가 혼동할 수 있음. 파일 상단에 `> ⚠️ 폐기됨. redesign_v1_260409 참조` 헤더 추가 권장.
3. **SeedHeatScore 모델**: 설계서 `chainsight_api_design.md §8`에 Phase 2 항목으로 명시되었으나 모델/마이그레이션 미생성. Phase 2+ 진입 시점에 `TASKQUEUE.md`로 끌어올릴 시점.
4. **2차 카드 LLM 설명 필드**: `neighbors/` 응답에서 `relation_summary`/`why_now`/`insight_summary`는 향후 확장 슬롯으로만 존재. 도입 시점에 LLM 토큰 비용/캐싱 정책 동시 검토 필요.

---

**END OF DOCUMENT**
