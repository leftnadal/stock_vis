# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-17
> **감사 범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `chainsight/` + `frontend/components/chainsight/` 구현
> **방법**: 읽기 전용 감사. 코드 수정 없음.
> **기준 문서**:
> - 1차 로드맵: `chain_sight_roadmap_v1.3.md` (2026-04-02) + `cs_01~54` 작업별 계획서
> - 2차 (마켓 뷰 리디자인): `redesign_v1_260409/` 4종 (2026-04-10, v2.1~v2.2 FINAL)
> - 완료 보고: `task_done/CS-0-1 ~ CS-5-3` + `chain_sight_redesign_V1/PR-1~7`

---

## 요약 (구현률)

| 영역 | 분류 | 비고 |
|------|------|------|
| Phase 0 인프라 (CS-0) | **(A) 완전 구현** | 12개 테이블, Neo4j 연결, 스키마 초기화 모두 완료 |
| Phase 1 시드 로드 (CS-1) | **(A) 완전 구현** | Stock 532 + Sector 17 + Industry 128 + PEER_OF 8,350 |
| Phase 2 파이프라인 (CS-2) | **(A) 완전 구현** | Tier A 4종 + 관계 발견 3종 + 집약 모두 적재 |
| Phase 3 동기화 + GDS (CS-3) | **(B) 부분 구현** | sync 완료. GDS 알고리즘 작업 코드 파일 부재(현재는 1회성 외부 실행으로 추정) |
| Phase 4 REST API (CS-4) | **(A) 완전 구현** | graph/suggestions/trace 3종 + 마켓 뷰 4종 추가 적재 |
| Phase 5 프론트엔드 (CS-5) | **(D) 폐기/대체** | `cs_5_frontend_design_v2.md` + `cs_51~54` 원안 → `redesign_v1_260409` UI/UX로 대체. Deep dive 워크스페이스(`/chainsight/[symbol]`)만 잔존, 메인은 `/chainsight` 마켓 뷰. |
| Phase 6 데이터 수집 (DC-1~6) | **(B) 부분 구현** | DC-1, DC-2 완료. DC-3~DC-6은 미시도 |
| Redesign V1 PR-1~7 (마켓 뷰) | **(A) 완전 구현** | seeds/sector/neighbors/signals API + 5개 컴포넌트 + Zustand 상태 모두 적재. QA 점수 91% |
| Heat Score / Phase 2 시드 | **(B) 부분 구현** | `calculate_heat_scores` task 존재, Neo4j 노드 속성으로 저장. 그러나 설계서가 명시한 `SeedHeatScore` PostgreSQL 모델 부재. seed_rank, components 필드 미적재 |
| Phase 3 이벤트 전파 (D-1~D-3) | **(C) 미구현** | text_conditional_prob, lagged correlation, propagation_weight 코드 부재 |
| SavedPath (CS-6-1) | **(A) 완전 구현 (계획 외)** | 로드맵에 없는 신규 모델 + Watchlist ViewSet + migration 0006 |

**전체 구현률**: 핵심 8개 단계 중 **6개 완전 구현**, 2개 부분, 1개 폐기/대체, 1개 미구현.

---

## 문서별 상태 테이블

### Phase 0 — 인프라

| 문서 | task_done | 구현 상태 | 코드 위치 / 차이 |
|------|-----------|----------|------------------|
| `cs_00_legacy_cleanup_api_test.md` | `CS-0-0_legacy_cleanup_api_test.md` | (A) | `decisions/003_api_access_test.md` 기록, serverless 레거시 LEGACY_KEEP 태그 처리 |
| `cs_01_migrations_verification.md` | `CS-0-1_migrations.md` | (A) | `chainsight/migrations/0001~0008.py` (8개), 12개 테이블 + SavedPath + SeedSnapshot 추가 |
| `cs_02_neo4j_connection.md` | `CS-0-2_neo4j_driver.md` | (A) | `chainsight/graph/repository.py` + `exceptions.py` + `__init__.py` |
| `cs_03_neo4j_schema.md` | `CS-0-3_neo4j_schema.md` | (A) | `chainsight/graph/schema.py` + `management/commands/init_neo4j_schema.py` |

### Phase 1 — 시드 로드

| 문서 | task_done | 구현 상태 | 코드 위치 |
|------|-----------|----------|----------|
| `cs_11_stock_node_bulk_load.md` | `CS-1-1_stock_nodes.md` | (A) | `chainsight/services/neo4j_loader.py::load_stocks_to_neo4j` + management command |
| `cs_12_sector_industry.md` | `CS-1-2_sectors.md` | (A) | 같은 서비스 + `load_sectors_to_neo4j.py` |
| `cs_13_peer_relations.md` | `CS-1-3_peers.md` | (A) | `chainsight/services/neo4j_loader.py::fetch_finnhub_peers/fetch_fmp_peers/collect_all_peers/load_peers_to_neo4j` |

### Phase 2 — 파생 데이터 파이프라인

| 문서 | task_done | 구현 상태 | 코드 위치 |
|------|-----------|----------|----------|
| `cs_21_tier_a_profile.md` (GrowthStage + CapitalDNA) | `CS-2-1_tier_a_profiles.md` | (A) | `chainsight/tasks/profile_tasks.py::calculate_growth_stages` + `calculate_capital_dna` |
| `cs_21b_sensitivity_profile.md` | `CS-2-1b_sensitivity_profile.md` | (A) | `chainsight/tasks/sensitivity_tasks.py::calculate_sensitivity_profiles` |
| `cs_21c_insider_signal.md` | `CS-2-1c_insider_signal.md` | (A) | `chainsight/tasks/insider_tasks.py::calculate_insider_signals` |
| `cs_22_co_mention.md` | `CS-2-2_co_mention.md` | (A) | `chainsight/tasks/relation_tasks.py::extract_co_mentions` (ChainNewsEvent 활용) |
| `cs_23_price_co_movement.md` | `CS-2-3_price_co_movement.md` | (A) | 같은 파일 `calculate_price_co_movement` |
| `cs_24_relation_confidence.md` + `relation_confidence_design_v1.md` | `CS-2-4_relation_confidence.md` | (A) | 같은 파일 `update_relation_confidence` (3-tier 점수, 5단계 상태) |
| `cs_25_chain_profile_aggregation.md` | `CS-2-5_chain_profile_aggregation.md` | (A) | `chainsight/tasks/sync_tasks.py::aggregate_chain_profiles` |

### Phase 3 — Neo4j 동기화 + GDS

| 문서 | task_done | 구현 상태 | 코드 위치 / 차이 |
|------|-----------|----------|------------------|
| `cs_31_profile_neo4j_sync.md` | `CS-3-1_profile_sync.md` | (A) | `chainsight/tasks/sync_tasks.py::sync_profiles_to_neo4j` |
| `cs_32_relation_neo4j_sync.md` | `CS-3-2_relation_neo4j_sync.md` | (A) | 같은 파일 + 이후 `redesign_v1`에서 `services/neo4j_sync.py`로 위임 (dirty 기반) |
| `cs_33_gds_algorithms.md` | `CS-3-3_gds_algorithms.md` | **(B)** | task_done에 "PageRank Top 5, Louvain 184 등 결과" 명시되어 있고 `path_service.py`/`schema.py`는 `pagerank_score`, `community_id`를 **읽음**. 그러나 `chainsight/tasks/gds_tasks.py` (또는 `management/commands/run_gds_algorithms.py`) 파일은 **존재하지 않음**. 1회성 외부 실행 또는 미반복 가능성 → 재실행 자동화 부재 |

### Phase 4 — REST API

| 문서 | task_done | 구현 상태 | 코드 위치 / 차이 |
|------|-----------|----------|------------------|
| `cs_41_graph_api.md` | `CS-4-1_2_3_rest_api.md` | (A) | `chainsight/api/views.py::ChainSightGraphView` (`/api/v1/chainsight/<symbol>/graph/`) |
| `cs_42_suggestion_api.md` | 같은 task_done | (B) | `ChainSightSuggestionView` 구현. 설계서 5개 카테고리 중 **community(클러스터)** 카테고리 미구현. peers/same_industry/co_mentioned/same_sector 4개만 반환. 같은 클러스터 카테고리는 `pagerank/community_id` 의존 → GDS 자동화 미비와 연결 |
| `cs_43_trace_api.md` | 같은 task_done | (A) | `ChainSightTraceView` 구현 |

### Phase 5 — 프론트엔드 (원안 vs 재설계)

| 원안 (cs_5* 문서) | 원안의 task_done | 현재 구현 | 상태 |
|-----------------|----------------|----------|------|
| `cs_5_frontend_design_v2.md` (전용 `/chainsight/[symbol]` 워크스페이스) | `CS-5-1_frontend_graph.md`, `CS-5-2_pro_features.md`, `CS-5-3_mobile_card_list.md` | `frontend/app/chainsight/[symbol]/page.tsx`, `GraphCanvas.tsx`, `AIGuidePanel.tsx`, `NodeDetailPanel.tsx`, `TracePathView.tsx`, `FilterPanel.tsx`, `MobileCardList.tsx`, `GraphMiniView.tsx` | **(D)→유지** Deep dive 워크스페이스로 잔존. 메인 흐름은 아님 |
| `cs_51_graph_visualization.md` (Spotlight 모드 + lazy expansion `GraphView.tsx`) | `CS-5-1_frontend_graph.md` | `GraphView.tsx` 미존재. `GraphCanvas.tsx`로 대체 명명 | (D) |
| `cs_52_ai_guide_ui.md` (`SuggestionCards.tsx`) | `CS-5-2_pro_features.md` | `SuggestionCards.tsx` 미존재. `AIGuidePanel.tsx`로 대체 | (D) |
| `cs_53_chain_trace_ui.md` (`TraceView.tsx`) | - | `TraceView.tsx` 미존재. `TracePathView.tsx`로 대체 명명 | (D) |
| `cs_54_stock_detail_integration.md` (종목 상세 탭 내 미니 그래프) | - | 종목 상세 페이지의 Chain Sight 탭 제거됨 (`stocks/[symbol]/page.tsx` line 25). `GraphMiniView` + 딥링크 `/chainsight?focus={symbol}` 추가 | (D) — redesign UI/UX의 §11 결정 적용 |

### Redesign V1 (`redesign_v1_260409/`) — 마켓 뷰

| 설계서 | PR | 구현 상태 | 코드 위치 |
|--------|----|--------|----------|
| `chainsight_seed_node_design.md` (Phase 1: B+A) | PR-1 + PR-2 | (A) | `chainsight/services/seed_selection.py` (424 lines), `tasks/seed_tasks.py::run_seed_selection`, migration 0005 (previous_status, neo4j_dirty) |
| `chainsight_api_design.md` (4개 API) | PR-4 | (A) | `api/views.py::SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView` (line 297~814) + `api/urls.py` |
| `chainsight_ui_ux_design.md` (5개 컴포넌트) | PR-5 + PR-6 + PR-7 | (A) | `frontend/lib/stores/explorationStore.ts`, `hooks/useMarketView.ts`, `components/chainsight/{SectorBar,MarketGraphCanvas,ExplorationTrail,RelationCardPanel,ChainStoryFeed,RelationFilterChips}.tsx`, `app/chainsight/page.tsx` |
| Neo4j Sync 개선 (`neo4j_dirty` 단일 소스) | PR-3 | (A) | `services/neo4j_sync.py::sync_dirty_relations` + `tasks/neo4j_dirty_sync_tasks.py` + migration 0005 + 0008 (synced_to_neo4j 제거 통일) |

### DC (데이터 수집) 트랙

| 단계 | task_done | 상태 |
|------|-----------|------|
| DC-1 (Peer + Industry) | CS-1-3에 통합 | (A) |
| DC-2 (ETF Holdings → Theme) | `DC-2_etf_holdings_theme.md` | (A) — 21개 Theme 노드 + `management/commands/load_themes_to_neo4j.py` |
| DC-3 (수동 시드 JSON Supply Chain) | - | (C) — task_done 부재, 코드 부재 |
| DC-4 (Gemini Flash 확장 Supply Chain) | - | (C) — task_done 부재, 코드 부재 |
| DC-5 (Marketaux 뉴스 자연 축적) | - | (B) — CoMentionEdge가 매일 누적 중. 명시적 task_done 없음 |
| DC-6 (Finnhub Premium) | - | (C) — 보류. 수익화 후로 명시되어 있음 |

---

## 미구현 항목 상세

### 1. (B) GDS 자동화 (CS-3-3)

- **설계 위치**: `cs_33_gds_algorithms.md`
- **현재 상태**: 노드 속성 `pagerank_score`, `betweenness_score`, `community_id`를 **읽는 코드**(`chainsight/services/path_service.py`, `chainsight/graph/schema.py`)는 존재.
- **누락**: `chainsight/tasks/gds_tasks.py` 또는 동등한 GDS 알고리즘 배치 작업 파일 부재. `run_gds_algorithms` task가 `__init__.py`에 등록되어 있지 않음.
- **task_done 기록**: `CS-3-3_gds_algorithms.md`는 "PageRank Top 5: MSFT 1.9234, META 1.8933 ..." 결과를 명시. → **1회성 외부 실행으로 추정**.
- **영향**: 정기 갱신이 안 되면 노드 속성이 stale. `ChainSightSuggestionView`의 `community` 카테고리는 이로 인해 미구현 상태 (구현 카테고리: peers/same_industry/co_mentioned/same_sector 4종만).

### 2. (B) Phase 2 SeedHeatScore PostgreSQL 모델

- **설계 위치**: `chainsight_seed_node_design.md` §3.4
- **설계 명세**: `chainsight_seed_heat_score` 테이블 (stock + date + heat_score + components JSONB + seed_rank)
- **현재 상태**: `calculate_heat_scores` (`chainsight/tasks/seed_tasks.py` line 95)는 존재. 그러나 결과를 **PostgreSQL에 저장하지 않고 Neo4j :Stock 노드 속성(`s.heat_score`, `s.price_signal` 등)으로 직접 set**.
- **누락**:
  - `SeedHeatScore` Django 모델 부재 (`grep`으로 확인됨, models 패키지 미포함)
  - `seed_rank` 필드 부재 → 히스토리 추적/시계열 분석 불가
  - `components` JSONB 부재 → 가중치 조정 후 재계산 시 원본 잔존 신호 분리 불가
- **영향**: Phase 2 "섹터 정렬 기준 `heat_total DESC`" (`chainsight_seed_node_design.md` §3.5) — 현재 코드는 Phase 1의 `seed_count DESC`만 사용 (`api/views.py::SectorGraphView`).

### 3. (C) Phase 3 이벤트 전파 모델 (D-1 ~ D-3)

- **설계 위치**: `chainsight_seed_node_design.md` §4
- **설계 명세**:
  - D-1: `text_conditional_prob(A, B)` Gemini Embedding + ChromaDB
  - D-2: lagged correlation + volume_response + propagation_weight
  - D-3: 사후 검증 → 가중치 학습
- **현재 상태**: 코드 전무. 관련 task/service 파일 없음. ChromaDB 의존성도 없음.
- **영향**: redesign UI/UX 문서의 "Future enhancement"로 명시된 영역.

### 4. (B) Phase 2 시드 정렬 기준 변경

- **설계 위치**: `chainsight_api_design.md` §2 ("Phase 1: `seed_count DESC` → Phase 2+: `heat_total DESC`")
- **현재 상태**: `chainsight/services/seed_selection.py::build_sector_summary`가 `seed_count DESC` 정렬만 사용. `heat_total` 필드는 sector_summary 응답에 0.0 고정값으로 포함되어 있으나 (PR prompts 명시), 실제 정렬에 사용되지 않음.
- **누락**: 시드 선정 시 SeedHeatScore 적재 → `heat_total` 집계 → 정렬 변경.

### 5. (B) Suggestion API `community` 카테고리

- **설계 위치**: `cs_42_suggestion_api.md` 응답 예시
- **설계 명세**: `{ "id": "community", "label": "같은 클러스터", "rel_types": [], ... }` 5번째 카테고리
- **현재 상태**: `api/views.py::ChainSightSuggestionView`는 4개 카테고리만 반환 (peers, same_industry, co_mentioned, same_sector). community_id 매칭 로직 부재.
- **연관 의존**: GDS 자동화(#1)와 직결.

### 6. (B) 마켓 뷰 API의 `display_type` 파생 — 부분 일치

- **설계 위치**: `chainsight_api_design.md` §4 "display_type 파생"
- **설계 명세**: `SUPPLIES_TO + direction=outbound → CUSTOMER_OF`
- **현재 상태**: `NeighborGraphView::_display_type` 구현 정확. ✅
- **그러나** `SectorGraphView`의 `edges[]`에는 `display_type` 필드 자체가 없음 (설계서는 명시하지 않으므로 OK). 다만 `chainsight_redesign_V1/data_quality_3_fixes.md`에 따르면 Neo4j 엣지 라벨이 `RELATED_TO`로 하드코딩된 잔류물이 있어 `COALESCE(r.relation_type, type(r))`로 우회 처리됨. → **저장 규약과 실제 저장이 불일치** (양쪽 모두 살아 있음): 새 코드는 dirty sync로 정상 타입 저장, 기존 RELATED_TO 엣지는 1회성 정리됨 (캐시 플래그로 중복 방지).

### 7. (B) `signals/` API의 `chain.title` LLM 생성

- **설계 위치**: `chainsight_api_design.md` §5 응답 예시 (`"title": "Semiconductor supply chain reaction"`)
- **현재 상태**: `api/views.py::_build_chain_signals` (line 808)가 `title = f'{path_nodes[0]["ticker"]} → {path_nodes[-1]["ticker"]} chain'` 자동 생성. PR prompts 자체에서 "LLM 기반 chain title/summary 생성"을 "범위 밖 / Future enhancement"로 명시했으므로 의도된 결과.

### 8. (B) 2차 카드 설명 필드 (`relation_summary`, `why_now`, `insight_summary`)

- **설계 위치**: `chainsight_api_design.md` §4 "2차 필드 확장 (향후)"
- **현재 상태**: 1차 템플릿(`buildWhyNow`)만 프론트 `RelationCardPanel`에서 구성. BE API 응답에는 해당 필드 없음.
- **의도**: 설계서 자체에서 "추후 LLM 기반 생성 가능"이라고 명시 → 정상 진행 중.

### 9. (B) 화면 전환 애니메이션

- **설계 위치**: `chainsight_ui_ux_design.md` §7 (translateX, opacity, bounce 300ms)
- **현재 상태**: redesign_V1/00_summary.md "범위 밖 (후속 작업)"으로 명시. 노드 시각 구분 (시드 보더 색상)은 적용됨, 애니메이션 미적용. browser_test_report.md에서 명시적으로 미테스트 항목으로 표기됨.

---

## 폐기/대체 항목

### A. 종목 상세 페이지 Chain Sight 탭 → 딥링크

- **원안 (`cs_54_stock_detail_integration.md`)**: 종목 상세 페이지에 Chain Sight 탭 + 미니 그래프
- **재설계 (`chainsight_ui_ux_design.md` §11)**: 탭 제거, `/chainsight?focus={symbol}` 딥링크로 변경. 미니 그래프(`GraphMiniView`)는 별도 영역에 잔존
- **현재 코드**: `frontend/app/stocks/[symbol]/page.tsx` line 25에 `// LEGACY REMOVED: ChainSightExplorer (CS-0-0)` 주석 + 459줄에서 GraphMiniView dynamic import + 450줄에서 `/chainsight?focus=${symbol}` 딥링크 사용 → **재설계 채택**

### B. `/chainsight/[symbol]` 전용 워크스페이스 위상 변경

- **원안 (`cs_5_frontend_design_v2.md`)**: `/chainsight/[symbol]` = 메인 진입점 (전문 투자자용 3-panel 워크스페이스)
- **재설계 (`chainsight_ui_ux_design.md` §1)**: `/chainsight` = Market exploration hub (Breadth-first, 메인), `/chainsight/[symbol]` = Deep dive workspace (Depth-first, "Deep dive" CTA에서만 진입)
- **현재 코드**: 두 라우트 모두 존재. 메인 흐름은 `/chainsight`. 워크스페이스 파일 잔존 → **재설계 채택, 기존 파일 유지**

### C. 컴포넌트 명명 (Spotlight 모드 / SuggestionCards / TraceView)

- **원안**: `GraphView.tsx`, `SuggestionCards.tsx`, `TraceView.tsx`
- **재설계 후 실제**: `GraphCanvas.tsx`, `AIGuidePanel.tsx`, `TracePathView.tsx`, `MarketGraphCanvas.tsx`
- → **재설계와 함께 명명 변경**

### D. RelationConfidence 상태 체계

- **이전 (v1.x)**: confirmed / candidate / rejected (3단계)
- **현재 (v2.1 / migration 0005)**: hidden / weak / probable / confirmed / stale (5단계)
- → **`relation_confidence_design_v1.md` 반영 완료**, 코드 일치

### E. CompanyChainProfile 구조

- **로드맵 v1.1 안**: `profile_data (JSONB)` 단일 필드
- **현재**: 30개 개별 필드 (`score_profitability`, `score_growth` 등)
- → **로드맵 v1.2에서 "개별 필드 유지" 결정 명시** (`chain_sight_roadmap_v1.3.md` 부록 A). 코드와 일치.

### F. CUSTOMER_OF 별도 저장 → API 파생

- **로드맵 v1.2 이전**: `CUSTOMER_OF` 별도 엣지 가능성
- **로드맵 v1.3**: `SUPPLIES_TO`만 canonical 저장, `direction=outbound`일 때 API에서 `CUSTOMER_OF`로 파생
- **현재 코드**: `NeighborGraphView::_display_type`에서 정확히 파생. DB/Neo4j 저장 없음 → **v1.3 결정과 일치**

### G. `sync_relations_to_neo4j` (RELATED_TO 하드코딩) → dirty sync 위임

- **이전**: `chainsight/tasks/sync_tasks.py::sync_relations_to_neo4j`가 모든 엣지를 RELATED_TO로 저장 (`data_quality_3_fixes.md` Issue 2B)
- **현재**: 동일 함수가 `chainsight/services/neo4j_sync.py::sync_dirty_relations` 위임 + 1회성 레거시 정리
- → **재설계로 교체. 양쪽 코드 잔존 형태 정상**

---

## 추가 발견

### 1. 로드맵에 없는 신규 모델 — SavedPath / PathAction / SeedSnapshot

- migration 0006 (SavedPath/PathAction), 0007 (SeedSnapshot) → 로드맵 v1.3에는 미언급
- `chainsight/views/watchlist_views.py`에 WatchlistViewSet 구현 + `/api/v1/chainsight/watchlist/` 라우트
- 추정: redesign 이후 별도 결정으로 추가됨 (PR prompts에 "Watchlist 추가" CTA 언급)
- → 설계 문서 갱신 권장. 신규 기능이 코드에 있지만 plan/에 미반영

### 2. 부분 잔존: `cs_5_frontend_design_v2.md` 진영의 코드

- 워크스페이스 라우트(`/chainsight/[symbol]`)와 그 하위 컴포넌트(AIGuidePanel/NodeDetailPanel/FilterPanel/TracePathView/MobileCardList)는 redesign V1 PR-5~7에 명시되지 않은 잔존 자산.
- redesign UI/UX 문서 §12 "유지" 섹션에 "GraphCanvas.tsx, NodeDetailPanel.tsx (Deep dive workspace)"로 명시되어 있음 → **의도된 유지**
- 따라서 cs_5 원안은 "삭제 폐기"가 아니라 "역할 변경 후 잔존"

### 3. `sec_pipeline_*.md` 2개 문서는 chain_sight/plan에 위치하지만 별도 앱

- `sec_pipeline_base_design.md` + `sec_pipeline_pr_detail.md` → `sec_pipeline/` 앱으로 분리되어 구현됨
- chain_sight와는 데이터 흐름상 연결되어 있으나 (Supply Chain 시드용) 본 감사 범위 아님

### 4. Stock `change_percent` 데이터 품질 문제 (Chain Sight 범위 밖이지만 영향)

- `data_quality_3_fixes.md`에서 식별됨. `update_sp500_change_percent` task로 해결 처리.
- 본 감사 시점에서는 별도 검증 필요. seeds API의 daily_return 0.0 fallback 다수 관찰 가능성 잔존.

### 5. `chainsight-heat-score-daily` Beat 등록 vs 실행

- `config/celery.py` line 742에 등록되어 있음
- 그러나 `calculate_heat_scores`가 Neo4j 노드에만 저장 → `seed_selection.py`가 이를 읽어 sector_summary의 `heat_total`로 환산하는 로직 부재. **Beat는 돌지만 시드 정렬에 반영되지 않는 dead-end 상태**

---

## 결론

- **로드맵 v1.3 핵심 단계**(CS-0~CS-4, CS-2-1b/c)는 모두 완료. M1~M4 마일스톤 달성.
- **CS-5 프론트엔드**는 원안(cs_51~54 / cs_5_frontend_design_v2)이 **redesign_v1_260409 마켓 뷰 설계로 사실상 대체**되었고, 원안 자산(`/chainsight/[symbol]` 워크스페이스)은 Deep dive 보조 위치로 강등되어 유지됨. plan/ 디렉토리에 cs_51~54 문서가 잔존하지만 task_done 보고와 함께 보면 의도된 상태.
- **Phase 2/3 시드 고도화** (SeedHeatScore 모델, GDS 자동화, 이벤트 전파 D-1~D-3, community 카테고리)는 **명시적 후속 작업으로 남은 영역**. 부분/미구현.
- **DC-3~6 트랙**은 의도된 보류(수익화 시점 결정 사항).
- **계획 외 추가**: SavedPath/SeedSnapshot 모델은 운영 보강 차원의 결정으로 보임. plan/ 문서 갱신 필요.

**권장 후속 작업 우선순위**:
1. GDS 알고리즘 자동화 task 작성 (CS-3-3 코드 부재 보완)
2. SeedHeatScore 모델 + Phase 2 정렬 전환 (시드 선정 정확도)
3. Suggestion API `community` 카테고리 활성화 (1번 완료 후)
4. SavedPath/SeedSnapshot 설계 문서 추가 (plan/ 일치성)

---

**END OF REPORT**
