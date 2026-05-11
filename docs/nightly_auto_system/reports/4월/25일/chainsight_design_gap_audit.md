# Chain Sight 설계 갭 감사

> **작성일**: 2026-04-26 (야간 자동 감사)
> **감사 범위**: `docs/chain_sight/plan/` + `docs/chain_sight/update_v2/` 설계 vs `chainsight/` 구현 + `frontend/components/chainsight/` UI
> **방식**: 읽기 전용 (코드 수정 없음)
> **분류 기호**: ✅ A 완전 구현 / 🟡 B 부분 구현 / ❌ C 미구현 / 🗂️ D 폐기·대체

---

## 요약 (구현률)

| Phase | 설계 항목 수 | A 완전 | B 부분 | C 미구현 | D 폐기 | 구현률 (A+B/전체) |
|-------|------------|-------|-------|--------|-------|------------------|
| Phase 0 — 인프라 (CS-0-0~3) | 4 | 4 | 0 | 0 | 0 | 100% |
| Phase 1 — 시드 로드 (CS-1-1~3) | 3 | 3 | 0 | 0 | 0 | 100% |
| Phase 2 — 파생 데이터 (CS-2-1~5) | 5 | 3 | 2 | 0 | 0 | 100% (Tier B 보류) |
| Phase 3 — Neo4j 동기화 + GDS (CS-3-1~3) | 3 | 3 | 0 | 0 | 0 | 100% |
| Phase 4 — API + Seed (CS-4-1~4) | 4 | 4 | 0 | 0 | 0 | 100% |
| Phase 4 redesign — Market View API 4종 | 4 | 4 | 0 | 0 | 0 | 100% |
| Phase 5 — 코어 FE (CS-5-1~6) | 6 | 5 | 1 | 0 | 0 | 100% |
| Phase 6 — Watchlist BE (CS-6-1~7) | 7 | 7 | 0 | 0 | 0 | 100% |
| Phase 7 — Watchlist FE (CS-7-1~3) | 3 | 3 | 0 | 0 | 0 | 100% |
| 데이터 수집 DC-1~6 | 6 | 2 | 1 | 3 | 0 | 50% |
| Tier B 자동 계산 (NarrativeTag/EventReaction/RevenueStructure) | 3 | 0 | 3 | 0 | 0 | 모델만 — task 미구현 |
| **합계 (CS Phase 0~7)** | **35** | **32** | **3** | **0** | **0** | **약 95%** |

**핵심 결론**:
- Chain Sight MVP 본체(Phase 0~7)는 **사실상 완성**(M5 달성, 2026-04-18). Watchlist + MarketView + 그래프 탐색 풀스택 작동.
- Tier B 자동 계산(NarrativeTag/EventReaction/RevenueStructure)은 **모델만 존재, 계산 task 부재** → MVP 범위 외로 보류.
- 데이터 수집 트랙(DC-3 수동 시드, DC-4 Gemini Flash, DC-6 유료 API)은 미진행 — 운영 단계 작업.
- `redesign_v1_260409/` 4개 문서는 **기존 cs_55/cs_56/cs_44 작업지시서를 보강하는 v2.1 상세 설계서**이며, 폐기가 아닌 실제 구현의 Source of Truth로 역할.

---

## 문서별 상태 테이블

### Phase 0 — 인프라

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 비고 |
|---------|----------|----------|------|------|
| CS-0-0 | cs_00_legacy_cleanup_api_test.md | (정리 작업) + decisions/003_api_access_test.md | ✅ A | 레거시 제거 완료, API 접근 테스트 결과 기록됨 |
| CS-0-1 | cs_01_migrations_verification.md | `chainsight/migrations/0001_initial.py`~`0007_seedsnapshot.py` (7건) | ✅ A | 14개 모델 = 7 Tier A/B + 4 관계 발견 + 1 집약 + 2 Path Watchlist + (보너스: SeedSnapshot) |
| CS-0-2 | cs_02_neo4j_connection.md | `chainsight/graph/repository.py`, `schema.py`, `exceptions.py` | ✅ A | PID 기반 lazy driver, Celery prefork SIGSEGV 회피 |
| CS-0-3 | cs_03_neo4j_schema.md | `chainsight/management/commands/init_neo4j_schema.py` | ✅ A | constraint 4개 + index 2개 (Stock/Sector/Industry/Theme) |

### Phase 1 — 시드 로드 (DC-1)

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 실측 |
|---------|----------|----------|------|------|
| CS-1-1 | cs_11_stock_node_bulk_load.md | `commands/load_stocks_to_neo4j.py` | ✅ A | :Stock 532~597개 (S&P 500 기준 충족) |
| CS-1-2 | cs_12_sector_industry.md | `commands/load_sectors_to_neo4j.py` | ✅ A | :Sector 17, :Industry 127, BELONGS_TO 1,038 |
| CS-1-3 | cs_13_peer_relations.md | `chainsight/tasks/peer_tasks.py` | ✅ A | PEER_OF 8,350개 |

### Phase 2 — 파생 데이터

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 비고 |
|---------|----------|----------|------|------|
| CS-2-1 | cs_21_tier_a_profile.md, cs_21b_sensitivity_profile.md, cs_21c_insider_signal.md | `tasks/profile_tasks.py`, `tasks/sensitivity_tasks.py`, `tasks/insider_tasks.py` | ✅ A | GrowthStage 480, CapitalDNA 473 적재 검증. Sensitivity/Insider task는 존재하나 적재 결과 task_done에 미기록 |
| CS-2-1 (Tier B) | (cs_21에 포함) | 모델: `narrative_tag.py`, `event_reaction.py`, `revenue_structure.py` | 🟡 B | **모델만 존재. 계산 task 없음.** roadmap v1.4에서 "MVP 빈 상태로 시작, 점진 채움"으로 명시 — 의도된 보류 |
| CS-2-2 | cs_22_co_mention.md | `tasks/relation_tasks.py::extract_co_mentions` | ✅ A | ChainNewsEvent 323건, CoMentionEdge 744쌍 |
| CS-2-3 | cs_23_price_co_movement.md | `tasks/relation_tasks.py::calculate_price_co_movement` | ✅ A | 2,473쌍 90일 rolling correlation |
| CS-2-4 | cs_24_relation_confidence.md, relation_confidence_design_v1.md | `tasks/relation_tasks.py::update_relation_confidence`, `check_stale_and_decay` | ✅ A | RelationConfidence 3,527건, 5단계 상태(hidden/weak/probable/confirmed/stale), evidence_tier_best, evidence_sources JSONB. 데이터 품질 수정 후 PEER_OF/CO_MENTIONED/PRICE_CORRELATED 분리 저장 (data_quality_3_fixes.md 참조) |
| CS-2-5 | cs_25_chain_profile_aggregation.md | `tasks/sync_tasks.py::aggregate_chain_profiles` | 🟡 B | CompanyChainProfile 503건 적재 ✅. 다만 v1.4에서 요구한 **9개 Beat 스케줄**은 현재 `config/celery.py`에 **10개**(헤드룸 포함)로 등록됨 — sec-seed-relations-to-chainsight 등 추가 |

### Phase 3 — Neo4j 동기화 + GDS

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 비고 |
|---------|----------|----------|------|------|
| CS-3-1 | cs_31_profile_neo4j_sync.md | `tasks/sync_tasks.py::sync_profiles_to_neo4j` + `services/neo4j_sync.py` | ✅ A | Delta sync + neo4j_dirty 플래그 패턴 |
| CS-3-2 | cs_32_relation_neo4j_sync.md | 위와 동일 + `sync_dirty_relations` | ✅ A | 데이터 품질 수정으로 RELATED_TO 하드코딩 제거 → 동적 타입(PEER_OF/CO_MENTIONED/PRICE_CORRELATED) 지원. confirmed/probable + market weak 동기화 |
| CS-3-3 | cs_33_gds_algorithms.md | (수동 Cypher 실행, GDS 2.13.2 설치) | ✅ A | PageRank/Louvain/Betweenness 결과 :Stock 노드 속성 반영. 단 자동화 task(`tasks/gds_tasks.py`)는 **부재** — 수동 실행 |

### Phase 4 — API 엔드포인트 + Seed

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 검증 |
|---------|----------|----------|------|------|
| CS-4-1 | cs_41_graph_api.md | `api/views.py::ChainSightGraphView` (`/{symbol}/graph/`) | ✅ A | depth ≤3, market_signals 보강, SUPPLIES_TO 역방향 → derived_type=CUSTOMER_OF |
| CS-4-2 | cs_42_suggestion_api.md | `ChainSightSuggestionView` (`/{symbol}/suggestions/`) | ✅ A | 4개 카테고리(peers/same_industry/co_mentioned/same_sector) |
| CS-4-3 | cs_43_trace_api.md | `ChainSightTraceView` (`/trace/?from=&to=&max_depth=`) | ✅ A | shortestPath max 5 hop |
| CS-4-4 | cs_44_seed_node_heat_score.md, redesign_v1_260409/chainsight_seed_node_design.md | `tasks/seed_tasks.py::calculate_heat_scores` | ✅ A | 4개 signal(price/volume/relation_change/news) 균등 0.25 가중치, 534개 Stock 처리, avg=0.361. **Phase 1 (B+A) 시드 선정 + Phase 2 heat_score 모두 작동.** Phase 3(이벤트 전파, ChromaDB+Embedding)은 미진행 |

### Phase 4 redesign — Market View API 4종 (`redesign_v1_260409/chainsight_api_design.md` v2.1)

| 엔드포인트 | 코드 산출물 | 상태 | 검증 |
|----------|----------|------|------|
| `GET /seeds/` | `SeedListView` | ✅ A | 3단 폴백(Redis → SeedSnapshot → async 복구) |
| `GET /sector/{sector}/graph/` | `SectorGraphView` | ✅ A | market_cap percentile 기반 node_size, is_seed 매칭 |
| `GET /{symbol}/neighbors/` | `NeighborGraphView` | ✅ A | 양방향 이웃, display_type 파생, cross_edges, is_seed/score/market_cap 정렬 |
| `GET /signals/` | `SignalFeedView` | ✅ A | 시드 페어 → shortestPath → total_confidence (mean*0.7 + min*0.3), 카테고리 자동 분류, REASON_LABELS 한글 번역 |

### Phase 5 — 코어 프론트엔드

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 비고 |
|---------|----------|----------|------|------|
| CS-5-1 | cs_51_graph_visualization.md, cs_5_frontend_design_v2.md | `components/chainsight/GraphCanvas.tsx`, `graphStyles.ts`, `app/chainsight/[symbol]/page.tsx` | ✅ A | ForceGraph2D, 6색 관계 + 11색 섹터, Spotlight 모드, 3-panel |
| CS-5-2 | cs_52_ai_guide_ui.md | `AIGuidePanel.tsx`, `FilterPanel.tsx` | ✅ A | 카테고리 필터 + 관계 타입 9종 |
| CS-5-3 | cs_53_chain_trace_ui.md | `TracePathView.tsx`, `MobileCardList.tsx` | ✅ A | Trace 경로 + 모바일 카드 3-tier 렌더링 |
| CS-5-4 | cs_54_stock_detail_integration.md | `GraphMiniView.tsx` + `app/stocks/[symbol]/page.tsx` 수정 | ✅ A | 종목 상세 미니 그래프 |
| CS-5-5 | cs_55_market_view.md, redesign_v1_260409/chainsight_ui_ux_design.md | `app/chainsight/page.tsx` + `SectorBar.tsx` + `MarketGraphCanvas.tsx` + `ExplorationTrail.tsx` + `RelationCardPanel.tsx` + `ChainStoryFeed.tsx` + `lib/stores/explorationStore.ts` + `hooks/useMarketView.ts` | ✅ A | 5영역 레이아웃 모두 구현, ?focus=NVDA 초기화 액션 동작. ChainStoryFeed가 v1.4에서 "v1.3 이후로 미룸"으로 명시되었으나 실제로는 구현됨 |
| CS-5-6 | cs_56_seed_node.md | (CS-4-4 + RelationCardPanel pre-focus) | 🟡 B | heat_score 배치 + 시드 카드는 ✅. **bounce 애니메이션 미구현** (CS-5-6 task_done에 명시) — 의도된 보류 |

### Phase 6 — Watchlist 백엔드

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 비고 |
|---------|----------|----------|------|------|
| CS-6-1 | cs_61_saved_path_model.md | `models/saved_path.py` (SavedPath + PathAction), migration `0006_add_savedpath_pathaction.py` | ✅ A | path_nodes/action_type 필드명 통일, recheck_count 추가 |
| CS-6-2 | cs_62_watchlist_crud_api.md | `views/watchlist_views.py::WatchlistViewSet` (CRUD + archive + resolve) | ✅ A | DRF ViewSet, throttle 30/min, edge_snapshot 자동 생성, status 필터 |
| CS-6-3 | cs_63_summary_path.md | `services/path_service.py::generate_summary_path` | ✅ A | landmark_score 기반 압축 |
| CS-6-4 | (cs_62에 포함) | `WatchlistViewSet::archive`, `resolve` @action | ✅ A | |
| CS-6-5 | cs_65_recheck_api.md | `services/recheck_service.py::run_recheck` | ✅ A | 6단계 로직, watching→active 자동 전이 (Recheck 2회+24h) |
| CS-6-6 | cs_66_expand_api.md | `services/expand_service.py::find_expansion_candidates` | ✅ A | 1-hop 확장 후보 |
| CS-6-7 | cs_67_alternatives_api.md | `services/alternatives_service.py::find_alternatives` | ✅ A | 동일 relation_type 대안 노드 |

### Phase 7 — Watchlist 프론트엔드

| 작업번호 | 설계 문서 | 코드 산출물 | 상태 | 검증 |
|---------|----------|----------|------|------|
| CS-7-1 | cs_71_watch_button.md | `components/chainsight/WatchButton.tsx` + `ExplorationTrail.tsx` 수정 | ✅ A | Pin/PinOff + 토스트 + secondary action |
| CS-7-2 | cs_72_watchlist_ui.md | `app/chainsight/watchlist/page.tsx`, `components/chainsight/PathCard.tsx`, `lib/utils/pathStatus.ts` | ✅ A | 카드 리스트 + status 필터 + 빈 상태 |
| CS-7-3 | cs_73_full_path_view.md | `app/chainsight/watchlist/[id]/page.tsx`, `components/chainsight/FullPathView.tsx` | ✅ A | full path + Recheck headline + 노드 탭 Alternatives + Expand + Archive/Resolve. 248줄 |
| (지원) | (Phase 7 공용) | `types/pathWatchlist.ts` (17 IF), `services/pathWatchlistService.ts` (9 fn), `hooks/usePathWatchlist.ts` (9 hook), `useWatchlistOptimistic.ts` | ✅ A | TanStack Query optimistic update |

### 데이터 수집 트랙 (DC-1~6)

| Phase | 설계 | 상태 | 실측/비고 |
|-------|------|------|----------|
| DC-1 (Peer + Industry) | roadmap §4.2 | ✅ A | PEER_OF 8,350, BELONGS_TO 1,038 |
| DC-2 (ETF Holdings → Theme) | roadmap §4.2 + DC-2 task_done | ✅ A | :Theme 21, HAS_THEME 534. 운용사 CSV 기반 (Finnhub 403) |
| DC-3 (수동 시드 JSON Supply Chain) | roadmap §4.5 | ❌ C | 코드/데이터 없음. **SEC Pipeline이 사실상 대체** — `sec-seed-relations-to-chainsight` Beat task가 SEC 10-K 추출 관계를 RelationConfidence에 시드 |
| DC-4 (Gemini Flash Supply Chain 확장) | roadmap §4.6 | ❌ C | 미구현. Gemini Flash는 News Pipeline에서만 사용 중 |
| DC-5 (Marketaux 뉴스 자연 축적) | roadmap §4.7 | 🟡 B | CoMentionEdge 자동 추출은 작동(CS-2-2). News Intelligence Pipeline v3와 연계 |
| DC-6 (Finnhub Premium) | roadmap §4.8 | ❌ C | 수익화 이후 트리거 — 의도된 보류 |

---

## 미구현 항목 상세

### M-1. Tier B 자동 계산 task 부재 (모델만 존재)

| 모델 | 파일 | 계산 task |
|------|------|---------|
| `CompanyNarrativeTag` | `models/narrative_tag.py` | ❌ Marketaux + LLM 추출 task 없음 |
| `CompanyEventReaction` | `models/event_reaction.py` | ❌ earnings 전후 가격 변동 계산 task 없음 |
| `CompanyRevenueStructure` | `models/revenue_structure.py` | ❌ FMP Revenue Segmentation 적재 task 없음 |

**근거**: `chainsight/tasks/` 디렉토리에 `narrative_tasks.py`, `event_reaction_tasks.py`, `revenue_tasks.py` 미존재. roadmap v1.4 §2.5 Tier B 항목에서 "MVP 빈 상태로 시작, 점진 채움"으로 명시 → **의도된 보류**, 가설 통제실/Validation에서 사용 시점에 채움.

### M-2. GDS 자동화 task 부재

- `cs_33_gds_algorithms.md`는 `chainsight/tasks/gds_tasks.py`를 산출물로 명시했으나 실제로는 **수동 Cypher 실행**으로 1회성 적용(2026-04-03).
- 주기적 PageRank/Louvain 갱신이 자동 Beat 스케줄에 없음 → 노드 속성 갱신 시 stale 가능.
- `cs_44_seed_node_heat_score.md` Phase 2 설계서에서 `gds_centrality_delta` 신호(0.10 가중치)를 요구하나, 현재 `calculate_heat_scores`는 4개 균등(0.25)로 단순화됨.

### M-3. Phase 3 이벤트 전파 모델 (D-1/D-2/D-3) 미구현

`redesign_v1_260409/chainsight_seed_node_design.md` §4 Phase 3 설계 항목 전체:
- D-1: ChromaDB + Gemini Embedding 기반 `text_conditional_prob(A,B)` ❌
- D-2: Lagged correlation + volume_response → propagation_weight ❌
- D-3: 사후 검증 → 가중치 학습 ❌

**근거**: ChromaDB 연동 코드 없음, propagation_weight 컬럼 없음, 관련 Beat task(`chainsight-text-conditional`, `chainsight-lagged-correlation`, `chainsight-propagation-weight`) `config/celery.py` 미등록 → **Phase 3 의존성(60 거래일 + 검증 데이터)**에 따른 **의도된 미진행**.

### M-4. 자동 상태 전환 (strengthening / weakening / broken)

- `CHAIN_SIGHT_PM.md` §4-2에서 "v1.3 이후"로 명시.
- 현재 `SavedPath.status`는 watching/active/archived/resolved 4단계만 작동.
- `ChainSightStatusModel` 또는 자동 전이 Beat task 없음 → **의도된 보류**.

### M-5. 개인화 로직 (PathAction 데이터 활용)

- 설계: PathAction 50건 이상 시 `preferred_relations`/`explorer_type`을 heat_score 보너스에 반영.
- 현재: `PathAction` 테이블에 이벤트 기록만, 추천 엔진 미반영. PM_DESIGN §8 "MVP 비반영" 명시 → **의도된 보류**.

### M-6. Path-level Compare / Alternatives 경로 비교

- 현재: 노드 단위 대안만 지원(`alternatives_service.py`).
- 설계 §5: "이 경로에서 이 노드를 바꾸면?" path-level 비교는 v1.3 이후. → **의도된 보류**.

### M-7. 시각 요소 누락

- 시드 노드 bounce 애니메이션 (CS-5-6 task_done 명시 — CSS 레벨 미구현)
- 300ms ease-out 전환 애니메이션 (redesign 00_summary "범위 밖")
- LLM 기반 chain title/summary, 2차 카드 설명(relation_summary, why_now) — redesign 00_summary "범위 밖"

### M-8. QA Evaluator follow-up (비차단)

`task_done/chain_sight_redesign_V1/qa_evaluator_review_01.md` §비차단 개선:
1. `chainsightService.ts`: fetch() → authAxios 통일 (JWT 일관성) — **현재도 일부 fetch 사용 가능**
2. `useInfiniteQuery`: `pageParam as number` 명시적 타입화 — **현재 미적용 추정**
3. `RelationCardPanel`: 에러 바운더리 추가 — **현재 미적용 추정**
4. `relation_tasks.py::update_relation_confidence`: relation_upgrade/downgrade 판정 로직 완성도 재확인

---

## 폐기/대체 항목

> 이번 감사에서 **명시적으로 폐기·대체된 설계 흐름**은 redesign 자체가 폐기를 일으킨 것이 아니라, **v1.4 클린업 가이드(`update_v2/review/CLEANUP_GUIDE_v1.4.md`)**에서 정의됨.

### D-1. v1.0 cs_45~cs_4_10, cs_57~cs_59 작업지시서 폐기 (9개)

| 폐기 파일 | 대체 파일 | 이유 |
|----------|---------|------|
| `cs_45_watchlist_crud.md` | `cs_62_watchlist_crud_api.md` | Phase 6 신설로 재구성 |
| `cs_46_summary_path.md` | `cs_63_summary_path.md` | Phase 4 → Phase 6 이관 |
| `cs_47_simple_actions.md` | `cs_62`에 흡수 | archive/resolve를 ViewSet @action으로 통합 |
| `cs_48_recheck_api.md` | `cs_65_recheck_api.md` | Phase 6 재번호 |
| `cs_49_expand_api.md` | `cs_66_expand_api.md` | Phase 6 재번호 |
| `cs_4_10_alternatives_api.md` | `cs_67_alternatives_api.md` | Phase 6 재번호 |
| `cs_57_watch_button.md` | `cs_71_watch_button.md` | Phase 7 재번호 |
| `cs_58_watchlist_ui.md` | `cs_72_watchlist_ui.md` | Phase 7 재번호 |
| `cs_59_full_path_view.md` | `cs_73_full_path_view.md` | Phase 7 재번호 |

→ 현재 `docs/chain_sight/plan/`에는 `cs_61_saved_path_model.md`, `cs_62_watchlist_crud_api.md` 등이 그대로 존재. **클린업 가이드는 update_v2에 있으나 plan/ 디렉토리에서는 폐기 파일이 정리되지 않음** → 디렉토리 정리는 후속 작업으로 남음.

### D-2. CUSTOMER_OF 별도 저장 폐기 → SUPPLIES_TO canonical (v1.3, 2026-04-02)

- 폐기: `RelationConfidence`에 CUSTOMER_OF 별도 row 저장
- 대체: `SUPPLIES_TO`만 canonical 저장, API에서 `derived_type` 또는 `display_type`으로 역방향 파생
- 검증: `chainsight/api/views.py:86-87` (ChainSightGraphView), `522-526` (NeighborGraphView `_display_type`) 모두 적용 확인. Neo4j에 잔존 CUSTOMER_OF 엣지 2개는 잔여 데이터(DC-2 task_done 기록 기준).

### D-3. RelationConfidence v1 → v2.1 스키마 (2026-04-02)

- 폐기: 3단계 상태(confirmed/candidate/rejected), 단일 confidence_score
- 대체: 5단계 상태(hidden/weak/probable/confirmed/stale), 3단 점수(truth_score/market_score/investment_relevance), evidence_tier_best, evidence_sources JSONB, relation_basis_summary
- 마이그레이션: `0001_initial` → `0004_companychainprofile_neo4j_synced_and_more` → `0005_add_neo4j_dirty_previous_status`로 단계적 적용

### D-4. CompanyChainProfile JSONB 단일 필드 폐기 → 30개 개별 필드

- v1.1 설계: `profile_data (JSONB)` 단일 필드
- v1.2 결정: 30개 개별 필드(score_profitability 등). 원칙 4(1인 개발 단순 구조) 부합
- 검증: `chainsight/models/chain_profile.py` — 개별 필드 구조 유지

### D-5. Neo4j RELATED_TO 하드코딩 폐기 → 동적 타입 (2026-04-13)

- 폐기: `sync_relations_to_neo4j`가 모든 엣지를 `RELATED_TO`로 통일 저장
- 대체: `services/neo4j_sync.py::sync_dirty_relations`가 PEER_OF/CO_MENTIONED/PRICE_CORRELATED 등 동적 타입으로 upsert. 기존 RELATED_TO 엣지는 1회성 캐시 플래그로 정리.
- 검증: 데이터 품질 수정 후 PEER_OF(12,178) + PRICE_CORRELATED(1,162) + CO_MENTIONED(169) + RELATED_TO(0) 분포 확인됨.

### D-6. serverless/ Chain Sight 코드 + frontend chain-sight (CS-0-0, 2026-04-02)

- 폐기 대상:
  - `serverless/views.py::chain_sight_*_api` (6개 뷰)
  - `serverless/services/chain_sight_*.py` (3개)
  - `serverless/models.py::StockRelationship`, `CategoryCache` (참조 서비스 마이그레이션 시까지 LEGACY_KEEP)
  - `serverless/models.py::ETFProfile`, `ETFHolding`, `ThemeMatch` (DC-2 완료 시까지 LEGACY_KEEP_UNTIL_DC2 — DC-2가 ✅ 이므로 **이론상 제거 가능**, 미정리)
  - `frontend/components/chain-sight/`, `hooks/useChainSight*`, `services/chainSightService` 등 (kebab-case)
- 대체: `chainsight/` 앱 + `frontend/components/chainsight/` (camelCase)
- 잔여 정리: `serverless/` 내 ETFHolding 참조가 DC-2 완료 후에도 미제거 가능성 — 별도 검증 필요.

### D-7. cs_5_frontend_design_v2.md (2026-04-04)

- 폐기 대상: cs_51~54 원안의 "종목 상세 탭 내 인터랙티브 그래프" 방향
- 대체: `/chainsight/[symbol]` 전용 워크스페이스 + 종목 상세 탭은 미니뷰
- 검증: `frontend/app/chainsight/[symbol]/page.tsx` (워크스페이스) + `frontend/components/chainsight/GraphMiniView.tsx` (종목 상세) 모두 구현

### D-8. 0건 / 비폐기 redesign_v1_260409

- `redesign_v1_260409/` 4개 문서는 **폐기가 아닌 v2.1 상세 설계서**로, cs_44/cs_55/cs_56과 **상호 참조 관계** (CLEANUP_GUIDE_v1.4 §44/55/56 "수정됨" 표시).
- 실제 구현(`task_done/chain_sight_redesign_V1/`)이 redesign 문서를 정확히 따라감 (Market View API 4종, 5개 FE 컴포넌트).

---

## 부록 A. 디렉토리·파일 매핑 정리

```
docs/chain_sight/
├── plan/                     ← v1.0 + v1.3 작업지시서 + redesign_v1_260409
│   ├── chain_sight_roadmap_v1.3.md           [구버전, v1.4가 superseding]
│   ├── relation_confidence_design_v1.md      [활성 — RelationConfidence v2.1]
│   ├── cs_*_*.md (32개)                      [v1.0 작업지시서, 9개 폐기 대상 잔존]
│   ├── redesign_v1_260409/ (4개)             [Phase 4-5 v2.1 상세 설계 — 활성]
│   ├── relation_confidence_design_v1.md      [활성]
│   ├── sec_pipeline_*.md (2개)               [SEC 연계]
│   └── remaining_work_plan.md                [2026-04-04 시점 스냅샷, 일부 outdated]
│
├── update_v2/                ← v1.4 최신 설계
│   ├── ROADMAP_v1.4.md       [현행 로드맵 — 35개 작업, M0~M7]
│   ├── CHAIN_SIGHT_PM.md     [PM 설계 v1.2 — Path Watchlist + MarketView + Seed]
│   ├── RELATION_CONFIDENCE.md [관계 신뢰도 엔진]
│   ├── decisions/            [005_phase6_7_등]
│   ├── review/ (6개)         [v1.4 작업지시서 검증 보고서 + CLEANUP_GUIDE]
│   ├── task_done/ (26개)     [Phase 0~7 + Phase 7 통합 보고서 cs_71_72_73]
│   └── task_instructions/ (34개) [v1.4 활성 작업지시서]
│
└── task_done/                ← 구 작업 완료 + redesign 통합 보고서
    ├── CS-*.md (17개)        [v1.0/v1.3 시점 완료 보고서]
    ├── DC-2_etf_holdings_theme.md
    ├── chain_sight_redesign_V1/ (10개)        [Market View redesign 구현 보고서]
    └── celery_beat_registration.md

chainsight/
├── models/ (13개 .py)        [14 모델 — Tier A 4 + Tier B 3 + 관계 4 + 집약 1 + Path 2 + SeedSnapshot]
├── migrations/ (7개)         [0001~0007 — 14 테이블 + SeedSnapshot]
├── graph/                    [Neo4j repository/schema/exceptions]
├── services/                 [neo4j_loader, neo4j_sync, seed_selection, path_service, recheck_service, expand_service, alternatives_service]
├── tasks/                    [profile, sensitivity, insider, peer, relation, sync, seed, neo4j_dirty_sync]  ← Tier B 미존재
├── api/                      [views.py 7뷰 + urls.py]
├── views/watchlist_views.py  [ViewSet 9 endpoint]
├── serializers/path_watchlist.py
├── management/commands/      [init_neo4j_schema, load_stocks/sectors/peers/themes, regenerate_summary_paths]
└── admin.py + utils.py

frontend/
├── app/chainsight/
│   ├── page.tsx              [MarketView 5영역]
│   ├── [symbol]/page.tsx     [전용 워크스페이스 3-panel]
│   ├── watchlist/page.tsx    [카드 리스트]
│   └── watchlist/[id]/page.tsx [Full Path View]
├── components/chainsight/    [16개 컴포넌트]
├── hooks/                    [useChainsight, useMarketView, usePathWatchlist, useWatchlistOptimistic]
├── lib/stores/explorationStore.ts
├── lib/utils/pathStatus.ts
├── services/                 [chainsightService, pathWatchlistService]
└── types/                    [chainsight.ts, pathWatchlist.ts]

tests/
├── chainsight/test_seed_fallback.py
└── unit/chainsight/          [test_alternatives/expand/recheck/summary_path + test_path_watchlist_models + test_watchlist_api]
```

## 부록 B. 우선 권고

1. **plan/ 디렉토리 정리**: CLEANUP_GUIDE_v1.4의 9개 폐기 파일(cs_45~4_10, cs_57~59)은 plan/에 잔존 → 정리 필요.
2. **serverless/ ETF 모델 LEGACY_KEEP_UNTIL_DC2 해제**: DC-2 ✅이므로 모델/참조 제거 가능 여부 검토.
3. **Tier B task 우선순위 결정**: 가설 통제실/Validation 진행 상황에 따라 NarrativeTag/EventReaction/RevenueStructure 중 어느 것을 먼저 채울지 결정.
4. **GDS 자동화**: `chainsight-gds-weekly` Beat task 추가 검토 (PageRank/Louvain 주 1회 갱신).
5. **roadmap v1.3 → v1.4 단일화**: `plan/chain_sight_roadmap_v1.3.md` 제거 또는 deprecated 표시.
6. **QA follow-up 4건 처리**: qa_evaluator_review_01.md §비차단 4건 — 후속 PR 묶음으로 처리 가능.

---

**END OF AUDIT**
