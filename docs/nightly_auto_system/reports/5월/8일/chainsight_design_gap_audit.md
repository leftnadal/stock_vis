# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-08
> **대상**: `docs/chain_sight/plan/` 설계 문서 ↔ `chainsight/` + `frontend/components/chainsight/` 구현
> **읽기 전용 감사**. 코드 수정 없음.

---

## 요약 (구현률)

| 단계 | 설계서 | 구현 비율 | 평가 |
|------|--------|----------|------|
| Phase 0 (CS-0) 인프라 | 4건 | 4/4 (100%) | (A) 완전 구현 |
| Phase 1 (CS-1) 시드 로드 | 3건 | 3/3 (100%) | (A) 완전 구현 |
| Phase 2 (CS-2) 파생 데이터 | 5건 | 5/5 (100%) | (A) 완전 구현 |
| Phase 3 (CS-3) Neo4j 동기화 + GDS | 3건 | 2/3 (67%) | (B) 부분 — CS-3-3 코드 부재 |
| Phase 4 (CS-4) Deep dive API | 3건 | 3/3 (100%) | (A) 완전 구현 |
| Phase 5 (CS-5) 프론트 (Deep dive 중심) | 4건 | 2.5/4 (~63%) | (D) 설계 방향 변경 + (B) 부분 |
| **redesign_v1** 마켓 뷰 (PR-1~7) | 7건 | 7/7 (100%) | (A) 완전 구현 |
| 시드 노드 Phase 2 (Heat Score) | 1건 | 0.5/1 (50%) | (B) 부분 — Neo4j 직저장, 모델 미생성 |
| 시드 노드 Phase 3 (이벤트 전파 D-1~D-3) | 3건 | 0/3 (0%) | (C) 미구현 |
| 추가 구현 (설계서 외) | — | +6건 | path watchlist + recheck/expand/alternatives |

**종합**: 로드맵 v1.3 기준 M0~M4 마일스톤 완료 (Phase 5만 부분), redesign V1 PR-1~7 모두 머지 완료(2026-04-10 ~ 2026-04-13). GDS 정기 배치 코드 흔적이 없으며, Heat Score Phase 2가 SeedHeatScore PostgreSQL 모델 대신 Neo4j 노드 속성 저장으로 대체됨.

---

## 문서별 상태 테이블

### 로드맵 / 설계 핵심 문서

| 문서 | 상태 | 구현 위치 | 비고 |
|------|------|----------|------|
| `chain_sight_roadmap_v1.3.md` | (A) 메타 문서 — 1~5단계 안내서 | — | redesign_v1과 공존 |
| `relation_confidence_design_v1.md` | (A) | `chainsight/models/relation_discovery.py` (RelationConfidence v2.1) + `tasks/relation_tasks.py` | 5단계 status, evidence_tier_best, normalize_pair 모두 반영 |
| `remaining_work_plan.md` | (A) 작업 추적 | — | 2026-04-04 기준, redesign V1 이전 |

### Phase 0 — CS-0 (인프라)

| 문서 | 상태 | 구현 |
|------|------|------|
| `cs_00_legacy_cleanup_api_test.md` | (A) | `task_done/CS-0-0_legacy_cleanup_api_test.md` |
| `cs_01_migrations_verification.md` | (A) | `chainsight/migrations/0001_initial.py` ~ `0008_unify_neo4j_flags.py` (8개) |
| `cs_02_neo4j_connection.md` | (A) | `chainsight/graph/repository.py` (Neo4jGraphRepository, PID 기반 lazy init) |
| `cs_03_neo4j_schema.md` | (A) | `chainsight/graph/schema.py` + `management/commands/init_neo4j_schema.py` |

### Phase 1 — CS-1 (시드 로드)

| 문서 | 상태 | 구현 |
|------|------|------|
| `cs_11_stock_node_bulk_load.md` | (A) | `management/commands/load_stocks_to_neo4j.py` |
| `cs_12_sector_industry.md` | (A) | `management/commands/load_sectors_to_neo4j.py` |
| `cs_13_peer_relations.md` | (A) | `chainsight/tasks/peer_tasks.py` |

### Phase 2 — CS-2 (파생 데이터)

| 문서 | 상태 | 구현 |
|------|------|------|
| `cs_21_tier_a_profile.md` | (A) | `tasks/profile_tasks.py` (calculate_growth_stages, calculate_capital_dna, calculate_all_profiles) |
| `cs_21b_sensitivity_profile.md` | (A) | `tasks/sensitivity_tasks.py` |
| `cs_21c_insider_signal.md` | (A) | `tasks/insider_tasks.py` |
| `cs_22_co_mention.md` | (A) | `tasks/relation_tasks.py::extract_co_mentions` |
| `cs_23_price_co_movement.md` | (A) | `tasks/relation_tasks.py::calculate_price_co_movement` |
| `cs_24_relation_confidence.md` | (A) | `tasks/relation_tasks.py::update_relation_confidence` + `check_stale_and_decay` |
| `cs_25_chain_profile_aggregation.md` | (A) | `tasks/sync_tasks.py::aggregate_chain_profiles` |

### Phase 3 — CS-3 (Neo4j 동기화 + GDS)

| 문서 | 상태 | 구현 |
|------|------|------|
| `cs_31_profile_neo4j_sync.md` | (A) | `tasks/sync_tasks.py::sync_profiles_to_neo4j` (neo4j_dirty 패턴) |
| `cs_32_relation_neo4j_sync.md` | (A) | `services/neo4j_sync.py::sync_dirty_relations` + `tasks/neo4j_dirty_sync_tasks.py` (PR-3 갱신) |
| `cs_33_gds_algorithms.md` | **(B) 부분** | **`gds_tasks.py` 코드 미발견.** `services/path_service.py:190`이 `s.pagerank_score`를 *읽기*만 하며, `graph/schema.py:19`에 `community_id` 인덱스만 존재. 정기 배치 task(`run_gds_algorithms`)는 코드베이스에 없음. `remaining_work_plan.md`는 "2026-04-03 완료"라 기재 — 일회성 cypher로만 실행되었을 가능성. |

### Phase 4 — CS-4 (Deep dive REST API)

| 문서 | 상태 | 구현 |
|------|------|------|
| `cs_41_graph_api.md` | (A) | `api/views.py::ChainSightGraphView` (`/{symbol}/graph/?depth=`) |
| `cs_42_suggestion_api.md` | (A) | `api/views.py::ChainSightSuggestionView` (`/{symbol}/suggestions/`) |
| `cs_43_trace_api.md` | (A) | `api/views.py::ChainSightTraceView` (`/trace/?from=&to=`) |

### Phase 5 — CS-5 (프론트엔드)

| 문서 | 상태 | 비고 |
|------|------|------|
| `cs_51_graph_visualization.md` | (D) **방향 변경** | 원안: 종목 상세 탭 내 GraphView. v2/redesign_v1: Deep dive workspace `/chainsight/[symbol]` + 마켓 뷰. 구현은 `GraphCanvas.tsx` (Deep dive). |
| `cs_52_ai_guide_ui.md` | (B) | 원안 `SuggestionCards.tsx` → 실제 `AIGuidePanel.tsx` (Deep dive 좌측 패널)로 통합. `CategoryCard.tsx` 별도 파일 없음(AIGuidePanel 내부). |
| `cs_53_chain_trace_ui.md` | (A) | `TracePathView.tsx` + `FullPathView.tsx`. 별도 `TraceView.tsx`는 없으나 동등한 컴포넌트 다수 존재. |
| `cs_54_stock_detail_integration.md` | (B) | `GraphMiniView.tsx` 존재. 종목 상세 탭이 `Coming Soon`인지 활성 미니 뷰인지 정확한 상태는 `frontend/app/stocks/[symbol]/page.tsx`에서 추가 확인 필요(이번 감사 범위 밖). 딥링크 `/chainsight?focus={symbol}`는 redesign_v1에서 추가됨. |
| `cs_5_frontend_design_v2.md` | (D) **방향 변경** | v2가 cs_51~54의 통합 후속이지만, 그 이후 redesign_v1이 `/chainsight` 마켓 뷰를 메인으로 재정의. v2의 Deep dive 워크스페이스(3-panel 분할)는 `/chainsight/[symbol]` 라우트로 잔존. NodeDetailPanel CTA(가설/Validation/여기서 탐색)는 부분 구현(WatchButton 분리). FilterPanel.tsx, MobileCardList.tsx 모두 존재. |

### redesign_v1_260409 (마켓 뷰 — 현재 정식 설계)

| 문서 | 상태 | 구현 |
|------|------|------|
| `chainsight_seed_node_design.md` (v2.1) Phase 1 (B+A) | (A) | `services/seed_selection.py` (5개 시드 소스) + `tasks/seed_tasks.py::run_seed_selection` |
| `chainsight_seed_node_design.md` Phase 2 (Heat Score) | **(B) 부분/대체** | `tasks/seed_tasks.py::calculate_heat_scores` 존재. 그러나 설계서의 `SeedHeatScore` PostgreSQL 모델은 미생성 — Neo4j `:Stock.heat_score` 속성에 직접 저장. 가중치 4종(price/volume/relation_change/news_activation)으로 단순화. 설계서 6종(news_event_count, gds_centrality_delta 포함) 미구현. |
| `chainsight_seed_node_design.md` Phase 3 (이벤트 전파, D-1~D-3) | **(C) 미구현** | text_conditional_prob, lagged correlation, propagation_weight, ChromaDB/Embedding 연동 모두 없음. PR-7 task_done에서 "범위 밖"으로 명시. |
| `chainsight_api_design.md` | (A) | `api/views.py` SeedListView / SectorGraphView / NeighborGraphView / SignalFeedView 4종. URL 등록 `chainsight/api/urls.py`. |
| `chainsight_ui_ux_design.md` | (A) | `app/chainsight/page.tsx` + 컴포넌트 5종(SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed). Zustand `explorationStore.ts` + TanStack `useMarketView.ts`. |
| `chainsight_marketview_pr_prompts.md` | (A) | PR-1~7 모두 머지 (`task_done/chain_sight_redesign_V1/`). |

### task_done cross-reference

| task_done 디렉토리 | 매칭 plan 문서 | 상태 |
|-------------------|---------------|------|
| `task_done/CS-0-0`~`CS-5-3` | `plan/cs_00`~`cs_5_frontend_design_v2` | 일관 |
| `task_done/DC-2_etf_holdings_theme.md` | DC-2 (로드맵 4.x), 별도 plan 미존재 | 데이터 수집 트랙 |
| `task_done/celery_beat_registration.md` | `remaining_work_plan.md` 항목 #3 | 일관 (config/celery.py에 14개 chainsight 비트 등록) |
| `task_done/chain_sight_redesign_V1/` | `plan/redesign_v1_260409/` | 7건 PR + browser test + data_quality 3건 + qa_evaluator review (91점) |

---

## 미구현 항목 상세

### 1. CS-3-3 GDS 알고리즘 정기 배치 (B)

- 설계: `gds.pageRank.write`, `gds.louvain.write`, `gds.betweenness.write`, projection 관리.
- 구현 흔적
  - `services/path_service.py:182~190`이 `s.pagerank_score`, `s.betweenness_score`, `s.degree`를 *읽음*.
  - `graph/schema.py:19`에 `stock_community` 인덱스(community_id) 정의.
  - `chainsight/tasks/`에 `gds_tasks.py` 또는 `run_gds_algorithms` 함수 **부재**.
- 영향: 노드 속성이 한 번 채워졌더라도 신규 종목/관계 변화 시 재계산되지 않음. M3 마일스톤("Neo4j가 풍부해짐") 정기성 미보장.
- 검증 권장: Neo4j에서 `MATCH (s:Stock) WHERE s.pagerank_score IS NOT NULL RETURN count(s)` 실행.

### 2. Heat Score Phase 2 (시드 노드 설계서 §3) (B)

- 설계: `SeedHeatScore` 모델(stock, date, heat_score, components(JSONB), seed_rank), 가중치 6종 + 정규화.
- 구현: `tasks/seed_tasks.py::calculate_heat_scores`가 4종 가중치(price/volume/relation_change/news_activation)로 Neo4j `:Stock` 노드 속성에 직접 기록.
- 미구현 요소
  - `SeedHeatScore` PostgreSQL 모델 + 마이그레이션
  - `gds_centrality_delta`, `news_event_count` 신호
  - 섹터 정렬 Phase 2 전환(`heat_total DESC`) — 현재 `seed_count DESC` 유지
- 영향: 시드 랭킹 history 추적 불가, Heat Score 기반 섹터 정렬 미적용. 사용자 노출 지표가 단순한 signal_count에 머무름.

### 3. 이벤트 전파 Phase 3 (시드 노드 설계서 §4) (C)

- 설계: 뉴스 키워드 → Gemini Embedding → ChromaDB 벡터, `text_conditional_prob`, `lagged correlation`, `propagation_weight` 비대칭 엣지.
- 구현: 전무. PR-7 summary에 "범위 밖"으로 공식 보류.
- 의존성: ChromaDB 인프라 도입 + Gemini Embedding 비용 + 60거래일 이상 누적 데이터.
- 위치: future enhancement. 단계 D-1~D-3 모두 미착수.

### 4. cs_5 v2 Deep dive 컴포넌트 보강 (B)

| 설계 컴포넌트 | 구현 |
|--------------|------|
| `GraphControls.tsx` (depth/필터/리셋) | **부재** — `MarketGraphCanvas`/`GraphCanvas` 내부에 인라인 통합되었거나 미구현 |
| `CategoryCard.tsx` | **부재** — `AIGuidePanel.tsx` 내부 컴포넌트로 추정 |
| `TracePanel.tsx` (좌측 패널 from/to 입력) | **부재** — `TracePathView.tsx`(결과 시각화)만 존재 |
| 노드 비교 모드 (Ctrl+Click 비교 패널) | **부재** — v2 §6-3 "프로 기능" |
| 노드 메트릭 오버레이 (PER 히트맵, Centrality 토글) | **부재** — v2 §6-2 |

- NodeDetailPanel CTA: "가설 생성", "Validation 보기", "여기서 탐색 시작" 라인 확인됨. "Watchlist 추가"는 별도 `WatchButton.tsx`로 분리.

### 5. cs_54 종목 상세 미니 뷰 활성화 여부 (B)

- 설계: `Coming Soon` 플레이스홀더 → 미니 그래프 + 연결 종목 태그 + "전체 보기 →".
- 구현 검증 필요: `frontend/app/stocks/[symbol]/page.tsx`의 Chain Sight 탭이 redesign_v1 기준으로 "Chain Sight에서 보기" 딥링크 버튼으로 교체되었는지(PR-5 보고서 line 27 시사) 또는 미니 뷰 임베드 유지 여부.
- 이번 감사 범위에서 단정 보류.

---

## 폐기/대체 항목

### 1. cs_5 / cs_5_frontend_design_v2 → redesign_v1 마켓 뷰 (D)

- **변경**: 메인 진입점이 종목 상세 탭(cs_51 원안) → 종목 전용 워크스페이스(cs_5 v2) → **마켓 탐색 허브 `/chainsight`(redesign_v1)**.
- **잔존**: `/chainsight/[symbol]` Deep dive workspace 라우트는 redesign_v1에서도 보존됨(`app/chainsight/[symbol]/page.tsx`). v2 컴포넌트(GraphCanvas, NodeDetailPanel, AIGuidePanel, TracePathView)는 deep dive에서 그대로 사용.
- **신규**: 마켓 뷰 5개 컴포넌트(SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed)는 redesign_v1에서 추가.
- 결론: cs_5/cs_5 v2는 **부분 폐기, 부분 흡수**. 새 표준은 `redesign_v1_260409/`.

### 2. CUSTOMER_OF 별도 저장 (D — v1.3 명시)

- v1.1: `CUSTOMER_OF` 별도 엣지 저장.
- v1.3 + 구현: `SUPPLIES_TO`만 canonical, API 응답에서 `display_type` 파생 (`api/views.py::_display_type`, `_derive_display_type`).
- DB·Neo4j에 `CUSTOMER_OF` 엣지 저장 없음 — 의도된 폐기.

### 3. RELATED_TO 엣지 (D — data_quality_3_fixes에서 정리 완료)

- 과거 `sync_relations_to_neo4j`가 모든 관계를 `RELATED_TO`로 저장.
- 2026-04-13 data_quality 수정으로 동적 타입(PEER_OF / CO_MENTIONED / PRICE_CORRELATED)으로 전환, 1회성 cypher로 RELATED_TO 엣지 삭제 (`sync_tasks.py:159` 참조). 과거 형식 폐기.

### 4. RelationConfidence v1 → v2.1 (D)

- v1: confirmed/candidate/rejected 3단 + 단일 score.
- v2.1: hidden/weak/probable/confirmed/stale 5단 + truth_score/market_score/investment_relevance 3단 점수 + evidence_tier_best + 7개 has_*_source bool. 마이그레이션 0001~0005에서 단계적 적용.
- v1 형식 폐기 (모델 코드에 흔적 없음).

### 5. CompanyChainProfile.profile_data JSONB 단일 필드 (D)

- v1.1 본문 제안.
- v1.2 결정으로 30개 개별 필드 구조 유지 (원칙 4 부합) — 모델은 개별 필드. JSONB 단일 폐기.

### 6. ETF Theme 모델 보관 (D — 부분 진행)

- 로드맵 v1.2: `ETFProfile/ETFHolding/ThemeMatch`에 `# LEGACY_KEEP_UNTIL_DC2` 태그 후 DC-2 완료 시 제거.
- task_done에 `DC-2_etf_holdings_theme.md` 존재 — DC-2 완료. 그러나 `serverless/` 모델 잔존 여부는 본 감사 범위 밖. 본 chainsight 앱에는 ETF/Theme 모델 없음.

---

## 추가 구현 (설계서에 없는 항목)

설계서에 명시되지 않았으나 구현된 기능 — 향후 설계 문서 보강 또는 회수 검토 대상.

| 영역 | 구현 위치 | 비고 |
|------|----------|------|
| Path Watchlist (저장된 경로) | `models/saved_path.py` (SavedPath, PathAction) + `serializers/path_watchlist.py` + `views/watchlist_views.py` (`WatchlistViewSet`) + migration `0006_add_savedpath_pathaction.py` | redesign_v1에도 명시 없음. Deep dive workspace 보조 기능. |
| Path 보조 서비스 | `services/path_service.py`, `alternatives_service.py`, `expand_service.py`, `recheck_service.py` | summary path 생성, 대체 경로 탐색, 확장 후보, 재검증 — Deep dive UX 지원. |
| `regenerate_summary_paths` 관리 명령 | `management/commands/regenerate_summary_paths.py` | 저장된 경로 요약 재생성. |
| `load_themes_to_neo4j` 관리 명령 | `management/commands/load_themes_to_neo4j.py` | DC-2 ETF 테마 로드. |
| SeedSnapshot 영속화 + 3단 폴백 | `models/seed_snapshot.py` + migration `0007_seedsnapshot.py` + `api/views.py::_get_today_seeds` | CLAUDE.md 버그 #27 대응(pytest Redis flush 회피). 설계서에 없는 운영 보강. |
| `unify_neo4j_flags` 마이그레이션 | `0008_unify_neo4j_flags.py` | audit P0 #9 — `synced_to_neo4j` 제거, `neo4j_dirty` 단일 소스 통합. |
| `update_sp500_change_percent` Beat (data_quality fix) | `stocks/tasks.py` (chainsight 외부) | DailyPrice → Stock.change_percent 일괄 갱신 — 섹터 수익률 표시용. |

---

## 부록: 핵심 코드 ↔ 설계 매핑

- `chainsight/api/views.py:308~315` ↔ `chainsight_api_design.md §2 GET /seeds/`
- `chainsight/api/views.py:317~444` ↔ `chainsight_api_design.md §3 GET /sector/{sector}/graph/`
- `chainsight/api/views.py:447~624` ↔ `chainsight_api_design.md §4 GET /{symbol}/neighbors/`
- `chainsight/api/views.py:627~814` ↔ `chainsight_api_design.md §5 GET /signals/`
- `chainsight/api/views.py:58~105` ↔ `cs_41_graph_api.md` (Deep dive)
- `chainsight/api/views.py:108~181` ↔ `cs_42_suggestion_api.md` (Deep dive)
- `chainsight/api/views.py:184~235` ↔ `cs_43_trace_api.md` (Deep dive)
- `chainsight/services/seed_selection.py` ↔ `chainsight_seed_node_design.md §2`
- `chainsight/services/neo4j_sync.py` ↔ `cs_32_relation_neo4j_sync.md` (재정의: dirty sync 패턴)
- `chainsight/tasks/relation_tasks.py::update_relation_confidence` ↔ `relation_confidence_design_v1.md` 정책표
- `chainsight/models/relation_discovery.py::RelationConfidence` ↔ 로드맵 v1.3 §2.5 + RELATION_CONFIDENCE.md §7

**END OF AUDIT**
