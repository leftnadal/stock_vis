# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-12
> **대상 코드**: `chainsight/`, `frontend/components/chainsight/`, `frontend/app/chainsight/`
> **대상 설계서**: `docs/chain_sight/plan/`, `docs/chain_sight/update_v2/`
> **읽기 전용** — 코드 수정 없음

---

## 요약 (구현률)

### 설계서 트랙 구성

Chain Sight 설계서는 시간순으로 **3개의 동심원**을 형성한다:

| 트랙 | 위치 | 시기 | 상태 |
|------|------|------|------|
| **트랙 1: 원안 cs_*** | `plan/cs_00 ~ cs_54.md` | 2026-04-02 (v1.3) | 대부분 구현 완료, 프론트는 v2/redesign으로 이행 |
| **트랙 2: redesign V1** | `plan/redesign_v1_260409/` (3개 설계서) | 2026-04-10 (v2.1/v2.2) | 7개 PR 모두 구현 완료 (PR-1~7) |
| **트랙 3: v1.4 (Path Watchlist)** | `update_v2/ROADMAP_v1.4.md` + `task_instructions/cs_61~73` | 2026-04-16 | Phase 6/7 구현 완료 (Watchlist + SavedPath) |

### 종합 구현률

| 분류 | 항목 수 | 비율 |
|------|---------|------|
| (A) 완전 구현 | 24 | 73% |
| (B) 부분 구현 | 5 | 15% |
| (C) 미구현 | 3 | 9% |
| (D) 폐기/대체 | 1 | 3% |
| **합계** | **33** | **100%** |

> **트랙 2(redesign V1)는 트랙 1의 cs_51~54 + 일부 cs_5_frontend_design_v2를 패러다임 수준에서 대체**한다 (종목 중심 워크스페이스 → 시장 탐색 허브). 두 트랙 모두 구현되어 공존하지만, 사용자 진입점은 마켓 뷰(`/chainsight`)가 메인이고 Deep Dive(`/chainsight/[symbol]`)는 보조다.

### 마일스톤 달성

- ✅ M0 (CS-0): 인프라 + 레거시 정리
- ✅ M1 (CS-1 + DC-1): Neo4j 1,528 노드 + 6,217 관계
- ✅ M1.5 (DC-2): ETF Theme 21개 (DC-3 supply chain seed는 미실행)
- ✅ M2 (CS-2): RelationConfidence 3,527건, 5단계 상태 + truth_score
- ✅ M3 (CS-3): GDS PageRank/Louvain/Betweenness
- ✅ M4 (CS-4): Deep dive API 3종 + 마켓 뷰 API 4종 + Watchlist API
- ✅ M5 (CS-5): 종목 상세 미니 뷰 + Deep dive workspace + 마켓 뷰 + Path Watchlist UI
- ✅ M6/M7 (Path Watchlist): SavedPath/PathAction + Watch/Recheck/Expand/Alternatives + FullPathView/PathCard/WatchButton

---

## 문서별 상태 테이블

### Phase 0 — 인프라 기반 (모두 완료)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_00_legacy_cleanup_api_test.md` | serverless/frontend Chain Sight 레거시 제거 + `decisions/003` API 테스트 | (A) |
| `cs_01_migrations_verification.md` | `chainsight/migrations/0001~0008` (총 12+2개 테이블) | (A) |
| `cs_02_neo4j_connection.md` | `chainsight/graph/repository.py` (PID-based fork-safe driver) | (A) |
| `cs_03_neo4j_schema.md` | `chainsight/graph/schema.py` + `init_neo4j_schema` management command | (A) |

### Phase 1 — 시드 로드 (모두 완료)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_11_stock_node_bulk_load.md` | `load_stocks_to_neo4j` command — Stock 532 노드 | (A) |
| `cs_12_sector_industry.md` | `load_sectors_to_neo4j` — Sector 17 + Industry 128 + BELONGS_TO | (A) |
| `cs_13_peer_relations.md` | `chainsight/tasks/peer_tasks.py` — PEER_OF 8,350 | (A) |

### Phase 2 — 파생 데이터 파이프라인 (대부분 완료, Tier B 부분 구현)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_21_tier_a_profile.md` | `profile_tasks.py` — GrowthStage 480, CapitalDNA 473 | (A) |
| `cs_21b_sensitivity_profile.md` | `sensitivity_tasks.py` — SensitivityProfile 503 | (A) |
| `cs_21c_insider_signal.md` | `insider_tasks.py` — InsiderSignal 503 | (A) |
| `cs_22_co_mention.md` | `relation_tasks.extract_co_mentions` — CoMentionEdge 744 | (A) |
| `cs_23_price_co_movement.md` | `relation_tasks.calculate_price_co_movement` — 2,473쌍 | (A) |
| `cs_24_relation_confidence.md` + `relation_confidence_design_v1.md` (v1.1) | `relation_tasks.update_relation_confidence` + `check_stale_and_decay` — RelationConfidence 3,527건 | (A) |
| `cs_25_chain_profile_aggregation.md` | `sync_tasks.aggregate_chain_profiles` — 503건 | (A) |
| Tier B (NarrativeTag, EventReaction, RevenueStructure) | 모델 존재, 데이터 파이프라인 미실행 (Phase 2 우선순위 낮음) | (B) |

### Phase 3 — Neo4j 동기화 + GDS (모두 완료)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_31_profile_neo4j_sync.md` | `sync_tasks.sync_profiles_to_neo4j` (delta sync + neo4j_dirty 패턴) | (A) |
| `cs_32_relation_neo4j_sync.md` | `services/neo4j_sync.py` + `tasks/neo4j_dirty_sync_tasks.py` (UNDIRECTED 정규화 + market weak 허용) | (A) |
| `cs_33_gds_algorithms.md` | Neo4j 5.26.3 + GDS 2.13.2 — PageRank/Louvain/Betweenness 적재 (별도 GDS task 모듈 없이 Neo4j Browser/Cypher로 실행 후 노드 속성에 영속) | (A) |

### Phase 4 — REST API (모두 완료)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_41_graph_api.md` | `ChainSightGraphView` (`/<symbol>/graph/`) — N-depth + market_signals 보강 | (A) |
| `cs_42_suggestion_api.md` | `ChainSightSuggestionView` (`/<symbol>/suggestions/`) — peers/same_industry/co_mentioned/same_sector 4 카테고리 | (A) — 단, 설계서의 `community` 카테고리(community_id 매칭)는 미구현 → (B) |
| `cs_43_trace_api.md` | `ChainSightTraceView` (`/trace/`) — Neo4j shortestPath 사용 | (A) |
| `cs_44_seed_node_heat_score.md` (v1.4 신설) | `seed_tasks.calculate_heat_scores` + Celery Beat (NY 07:00) — Neo4j `:Stock.heat_score` 속성에 직접 영속 (별도 SeedHeatScore PG 모델 없음) | (D) — 설계서 PG 모델 → 실제 Neo4j 속성으로 단순화 |

### Phase 4 마켓 뷰 — redesign_v1_260409 (모두 완료)

| 설계서 / PR | 코드 산출물 | 상태 |
|-------------|-------------|------|
| `chainsight_seed_node_design.md` Phase 1 | `services/seed_selection.py` + `tasks/seed_tasks.run_seed_selection` (5 소스 합산: price/volume/sector_outlier/relation_change/comention_surge) | (A) |
| `chainsight_seed_node_design.md` Phase 2 (Heat Score `SeedHeatScore` 모델) | Neo4j `:Stock.heat_score` 속성으로 단순화 (CS-4-4 참조) — DB 모델 미생성 | (D) |
| `chainsight_seed_node_design.md` Phase 3 (이벤트 전파 D-1/D-2/D-3) | 미구현 (ChromaDB, text_conditional_prob, lagged correlation) | (C) |
| `chainsight_api_design.md` (4 API) | `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` | (A) |
| `chainsight_api_design.md` 2차 필드 (`relation_summary`, `why_now`, `insight_summary`) | 미구현 (LLM 기반, future enhancement) | (C) |
| `chainsight_ui_ux_design.md` ① 섹터 바 | `SectorBar.tsx` | (A) |
| `chainsight_ui_ux_design.md` ② 그래프 캔버스 | `MarketGraphCanvas.tsx` | (A) |
| `chainsight_ui_ux_design.md` ③ 탐색 트레일 | `ExplorationTrail.tsx` + `explorationStore.ts` (undo + history) | (A) |
| `chainsight_ui_ux_design.md` ④ 관계 카드 패널 | `RelationCardPanel.tsx` (pre-focus / focused 분기) | (A) |
| `chainsight_ui_ux_design.md` ⑤ 체인 스토리 피드 | `ChainStoryFeed.tsx` (useInfiniteQuery + IntersectionObserver) | (A) |
| `chainsight_ui_ux_design.md` 노드 클릭 in-place 중심 이동 | `selectNode` action + neighbors fetch + trail push | (A) |
| `chainsight_ui_ux_design.md` 모바일 (Future consideration) | 마켓 뷰 모바일 미대응 (설계서 자체가 데스크톱 우선 명시) | (D) |
| 좌측 히스토리 (그래프 내부 1~3 step opacity) | `historyNodes` state는 있으나 그래프 내부 시각적 fade-in 표현은 미적용 — 트레일에 포함 | (B) |

### Phase 5 — 프론트엔드 (Deep Dive workspace, 모두 완료)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_51_graph_visualization.md` (원안) | (D) cs_5_frontend_design_v2로 대체 | (D) |
| `cs_52_ai_guide_ui.md` (원안) | `AIGuidePanel.tsx` | (A) |
| `cs_53_chain_trace_ui.md` (원안) | `TracePathView.tsx` | (A) |
| `cs_54_stock_detail_integration.md` (원안: 미니 그래프 + 탭 활성화) | `GraphMiniView.tsx` 존재 + 탭에 "Chain Sight에서 보기" 딥링크 (탭 내부 미니 그래프 표시는 redesign에서 딥링크로 단순화) | (D) — 부분 (D) |
| `cs_5_frontend_design_v2.md` 전용 워크스페이스 (`/chainsight/[symbol]`) | `app/chainsight/[symbol]/page.tsx` (3-panel: AIGuide + Graph + NodeDetail) | (A) |
| `cs_5_frontend_design_v2.md` 프로 기능 (FilterPanel, depth 전환) | `FilterPanel.tsx` (관계 타입 9종 + Depth 1/2/3) | (A) |
| `cs_5_frontend_design_v2.md` 모바일 카드 리스트 | `MobileCardList.tsx` (3-tier 렌더링 분기) | (A) |
| 엣지 색상 6색 + 스타일 차등 | `graphStyles.ts` | (A) |
| CTA 4개 (가설/Watchlist/Validation/탐색) | `NodeDetailPanel.tsx` | (A) |

### Phase 6 — Path Watchlist 백엔드 (v1.4 신설, 모두 완료)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_61_saved_path_model.md` | `models/saved_path.py` (SavedPath, PathAction) + migration 0006 | (A) |
| `cs_62_watchlist_crud_api.md` | `views/watchlist_views.py` (WatchlistViewSet, ModelViewSet) + `serializers/path_watchlist.py` | (A) |
| `cs_63_summary_path.md` | `services/path_service.py` (`generate_summary_path`, `build_edge_snapshot`, `build_path_signature`, `build_initial_why_now`) | (A) |
| `cs_65_recheck_api.md` | `services/recheck_service.py` (6단계 로직 + ACTIVE 전이) | (A) |
| `cs_66_expand_api.md` | `services/expand_service.py` (`find_expansion_candidates`) | (A) |
| `cs_67_alternatives_api.md` | `services/alternatives_service.py` (`find_alternatives`) | (A) |

### Phase 7 — Path Watchlist 프론트엔드 (v1.4 신설, 모두 완료)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| `cs_71_watch_button.md` | `WatchButton.tsx` | (A) |
| `cs_72_watchlist_ui.md` | `app/chainsight/watchlist/page.tsx` + `PathCard.tsx` | (A) |
| `cs_73_full_path_view.md` | `app/chainsight/watchlist/[id]/page.tsx` + `FullPathView.tsx` + `NodeContextMenu.tsx` + `RelationFilterChips.tsx` + `NodeTooltip.tsx` | (A) |

### 데이터 수집 (DC-1 ~ DC-6)

| 설계서 | 코드 산출물 | 상태 |
|--------|-------------|------|
| DC-1 (Peers + Industry) | CS-1-3에서 실행 완료 | (A) |
| DC-2 (ETF → :Theme) | `load_themes_to_neo4j` — Neo4j Theme 21개 (CSV 폴백) | (A) |
| DC-3 (수동 시드 JSON Supply Chain) | 미실행 (ETF 21개로 부분 충당, Supply Chain Phase 미진입) | (C) |
| DC-4 (Gemini Flash Supply Chain 확장) | 미실행 (DC-3 선행 필요) | (C) |
| DC-5 (Marketaux 자연 축적) | CoMentionEdge 744쌍 / News Intelligence Pipeline v3에서 자연 축적 진행 중 | (B) |
| DC-6 (Finnhub Premium $200/월) | 보류 (수익화 이후) | (D) |

---

## 미구현 항목 상세

### (B-1) cs_42 `community` 카테고리 미구현

**설계서**: `cs_42_suggestion_api.md` 카테고리 5종 중 `community` (community_id 매칭).

**현재 코드**: `views.py:108~181` `ChainSightSuggestionView`는 4 카테고리만 반환 — peers / same_industry / co_mentioned / same_sector.

**근거**: GDS Louvain community_id가 Neo4j :Stock 노드 속성에 적재되어 있음(CS-3-3 task_done 확인)에도 불구하고 카테고리 생성 로직 없음.

**영향**: AI Guide Panel에서 "같은 클러스터" 탭이 표시되지 않음.

---

### (B-2) Tier B 모델 (NarrativeTag / EventReaction / RevenueStructure) 데이터 미적재

**설계서**: 로드맵 v1.3 섹션 2.5 — Tier B 3개 테이블, 분기~주 1회 갱신.

**현재 코드**:
- `models/narrative_tag.py`, `event_reaction.py`, `revenue_structure.py` — 모델 정의 ✅
- `tasks/profile_tasks.py` `calculate_all_profiles`에서 호출하는 함수 없음 ❌

**근거**: CS-2-1 task_done에 GrowthStage/CapitalDNA만 기록. Tier B는 "MVP에서는 빈 상태로 시작, 점진 채움"으로 명시(v1.3 섹션 2.5).

**영향**: 차후 NarrativeTag 기반 Theme 추천, EventReaction 기반 시드 보강 등이 동작하지 않음. CompanyChainProfile 집계의 일부 필드가 null.

---

### (B-3) 좌측 히스토리 — 그래프 내부 시각적 fade-in 미구현

**설계서**: `chainsight_ui_ux_design.md` 섹션 7 "좌측 히스토리 — 그래프 내부 시각적 맥락" — 그래프 캔버스 **내부**에서 최근 1~3 step의 노드를 흐려진 상태(opacity 0.3~0.5)로 유지.

**현재 코드**: `explorationStore.ts`에 `historyNodes` state는 정의되어 있으나, `MarketGraphCanvas.tsx`에서 그래프 노드 자체에 opacity fade-in 처리는 미적용. ExplorationTrail(③)에서 전체 경로를 보여주는 것으로 대체.

**영향**: 설계서가 의도한 "방금 어디서 왔는지 그래프 안에서 보이는" 시각적 맥락이 약함. 트레일을 봐야만 직전 경로 파악 가능.

---

### (B-4) DC-5 Marketaux 자연 축적 — 진행 중

**설계서**: 런칭 +1개월 ~ +3개월 동안 ~1,000건의 CO_MENTIONED 누적 목표.

**현재 코드**: CoMentionEdge 744쌍 (CS-2-2 task_done 시점). `chainsight-co-mentions` Beat (매일 10:00) 작동 중.

**영향**: 충분한 누적까지 시간 경과 필요. 코드 변경 불필요.

---

### (B-5) 마켓 뷰 모바일 대응

**설계서**: `chainsight_ui_ux_design.md` 섹션 13 "현재 데스크톱 우선. 장기적으로 card-first 탐색 UI 가능."

**현재 코드**: `app/chainsight/page.tsx`에 모바일 분기 없음. Deep Dive workspace는 `MobileCardList.tsx`로 대응되지만, 마켓 뷰(`/chainsight`)는 미대응.

**영향**: 모바일에서 마켓 뷰 진입 시 데스크톱 레이아웃이 그대로 표시되어 가독성 저하.

---

### (C-1) Phase 3 이벤트 전파 모델 (D-1 / D-2 / D-3) 미구현

**설계서**: `chainsight_seed_node_design.md` 섹션 4 — `text_conditional_prob` (ChromaDB + Gemini Embedding), lagged correlation, propagation_weight 가중치 학습.

**현재 코드**: 관련 모듈/태스크/모델 일체 없음 (`grep -rn "text_conditional\|chromadb\|propagation_weight" chainsight/` 결과 없음).

**의도된 상태**: 설계서 자체가 "Phase 3 (D-1: ChromaDB 도입 후, D-2: 60 거래일 축적 후, D-3: 검증 레이블 축적 후)"의 단계적 전제 명시. 현 시점은 의도적 미진입.

**영향**: 향후 시드 선정의 정성→정량 변환 고도화 보류 상태.

---

### (C-2) `neighbors/` 2차 응답 필드 (`relation_summary` / `why_now` / `insight_summary`) 미구현

**설계서**: `chainsight_api_design.md` 섹션 4.2차 필드 확장 — LLM 기반 생성.

**현재 코드**: `NeighborGraphView` 응답에 해당 필드 없음. 프론트는 1차 템플릿(고정 문구 매핑) 기반으로 카드 설명 생성.

**영향**: 카드 설명이 "공급망 상류/하류 연결" 등 고정 템플릿에 머무름. LLM 기반 동적 설명 부재.

---

### (C-3) DC-3 (수동 시드 JSON) + DC-4 (Gemini Supply Chain 확장) 미실행

**설계서**: 로드맵 섹션 4.2 — DC-3에서 수동 시드 JSON ~500건, DC-4에서 Gemini Flash 확장 ~1,100건 SUPPLIES_TO 관계 추가.

**현재 코드**: SUPPLIES_TO 관계는 RelationConfidence에 정의되어 있으나, 시드 데이터가 적재되지 않아 실제 SUPPLIES_TO 엣지는 매우 적음 (CS-2-4 task_done의 truth_score 분포에서 PEER_OF 기반이 대부분).

**영향**: 마켓 뷰 ④ 관계 카드의 "Supply Chain" 그룹이 일부 종목에서만 표시됨. 본격적인 공급망 탐색 경험 한계.

---

## 폐기/대체 항목

### (D-1) cs_51 원안 (`/components/chainsight/GraphView.tsx`) → cs_5_frontend_design_v2 (`GraphCanvas.tsx`) + redesign V1 (`MarketGraphCanvas.tsx`)

**설계 변경**: 종목 상세 탭 내 인터랙티브 그래프 → **전용 워크스페이스** + **시장 탐색 허브** 2-tier 구조.

**현재 코드**:
- Deep Dive: `GraphCanvas.tsx` (3-panel 워크스페이스 내, react-force-graph-2d)
- Market View: `MarketGraphCanvas.tsx` (마켓 뷰 페이지, in-place 중심 이동 정책)

**근거**: cs_5_frontend_design_v2.md 원안 대비 변경 요약 표 첫 행 — "탭 공간 제한 → 전문가용 넓은 화면 필요".

---

### (D-2) cs_54 종목 상세 Chain Sight 탭 (미니 그래프 + 인터랙션) → 단순 딥링크 + GraphMiniView

**설계 변경**: 원안의 "탭 내부에 미니 그래프 + 연결 종목 태그 + CTA"를 **딥링크 버튼**(`/chainsight?focus=<symbol>`) + 정적 미니 뷰로 단순화.

**현재 코드**: `app/stocks/[symbol]/page.tsx:446~450` — Chain Sight 탭에서 GraphMiniView 컴포넌트는 존재하지만, 메인 진입은 "Chain Sight에서 보기" 딥링크 버튼으로 변경됨.

**근거**: redesign_v1_260409의 UI/UX 설계서 섹션 11 "종목 상세 연결" — "Chain Sight 탭 제거, 딥링크 추가" 명시.

> ⚠️ **현 상태 노트**: 종목 상세 페이지에 Chain Sight 탭(`tab === 'chain-sight'`) 자체는 **여전히 표시**되고 있으며 (page.tsx:84), 그 안에 딥링크 버튼이 들어 있는 형태. 설계서가 의도한 "탭 제거"는 부분 적용. 향후 정리 여지 있음.

---

### (D-3) Heat Score `SeedHeatScore` PostgreSQL 모델 → Neo4j `:Stock.heat_score` 속성

**설계 변경**: `chainsight_seed_node_design.md` 섹션 3.4의 `SeedHeatScore` Django 모델(stock, date, heat_score, components JSONB, seed_rank) → CS-4-4 구현은 **Neo4j 노드 속성에 직접 적재**.

**현재 코드**: `chainsight/tasks/seed_tasks.py:95~` `calculate_heat_scores` task — 4 signal (price/volume/relation_change/news_activation) × 균등 0.25 가중치 → `:Stock.heat_score` upsert.

**근거**: CS-4-4 task_done에 명시. Neo4j 속성 직접 영속이 단일 질의에서 사용하기 단순함 (원칙 4 부합).

**영향**: 시간축 추적(과거 heat_score 보관) 불가. 일별 히스토리가 필요해지면 별도 테이블 도입 필요.

---

### (D-4) DC-6 Finnhub Premium ($200/월)

**설계서**: 수익화 이후 활성화. 현 시점 의도적 보류.

---

## 부록: 검증된 핵심 사실

### 코드 통계 (clean 파일 기준, " 2.py" 등 OS 중복 제외)

- `chainsight/models/`: 14 모델 파일 (Tier A 4 + Tier B 3 + 관계 발견 3 + 뉴스 1 + 집약 1 + Watchlist 2)
- `chainsight/tasks/`: 8 모듈 (insider, neo4j_dirty_sync, peer, profile, relation, seed, sensitivity, sync)
- `chainsight/services/`: 7 서비스 (alternatives, expand, neo4j_loader, neo4j_sync, path, recheck, seed_selection)
- `chainsight/migrations/`: 0001~0008 (8개 마이그레이션)
- `chainsight/api/views.py`: 7 뷰 (Graph, Suggestion, Trace, SeedList, SectorGraph, Neighbor, SignalFeed)
- `chainsight/views/watchlist_views.py`: WatchlistViewSet (ModelViewSet)
- `frontend/components/chainsight/`: 21 컴포넌트 (마켓 뷰 5 + Deep dive 6 + Watchlist 5 + 공통 5)
- `frontend/app/chainsight/`: page.tsx (마켓 뷰) + [symbol]/ + watchlist/[id]/

### Celery Beat 등록 현황 (config/celery.py:685~)

| Beat 이름 | 스케줄 | 출처 |
|-----------|--------|------|
| `chainsight-all-profiles` | 토 02:00 | celery_beat_registration task_done |
| `chainsight-co-mentions` | 매일 10:00 | celery_beat_registration |
| `chainsight-price-co-movement` | 토 03:00 | celery_beat_registration |
| `chainsight-relation-confidence` | 매일 11:00 | celery_beat_registration |
| `chainsight-stale-decay` | 토 04:00 | celery_beat_registration |
| `chainsight-aggregate-profiles` | 토 04:30 | celery_beat_registration |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | celery_beat_registration |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | celery_beat_registration |
| `chainsight-seed-selection` | 매일 13:00 UTC | redesign V1 PR-2 |
| `chainsight-neo4j-dirty-sync` | 매주 일 04:30 UTC | redesign V1 PR-3 |
| `chainsight-heat-score-daily` | 매일 NY 07:00 | v1.4 CS-4-4 |

> ⚠️ `config/celery.py:13~21` 주석에 명시된 대로 dict는 **DatabaseScheduler 사용 시 무시**되며, 실제 진실의 소스는 `django_celery_beat.PeriodicTask` DB 테이블. dict와 DB가 어긋나면 dict의 태스크는 실행되지 않음. (CLAUDE.md common-bug #28)

### 설계서 디렉토리 구조

```
docs/chain_sight/
├── plan/                                  ← v1.3 시점 원안
│   ├── chain_sight_roadmap_v1.3.md       (907 lines)
│   ├── relation_confidence_design_v1.md  (관계 신뢰도 엔진 v1.1)
│   ├── cs_00 ~ cs_03 (Phase 0)
│   ├── cs_11 ~ cs_13 (Phase 1)
│   ├── cs_21 ~ cs_25 + cs_21b/c (Phase 2)
│   ├── cs_31 ~ cs_33 (Phase 3)
│   ├── cs_41 ~ cs_43 (Phase 4)
│   ├── cs_51 ~ cs_54 (Phase 5 원안 — 일부 폐기)
│   ├── cs_5_frontend_design_v2.md (Phase 5 정제)
│   ├── redesign_v1_260409/               ← 마켓 뷰 redesign (3개 설계서)
│   │   ├── chainsight_seed_node_design.md (v2.1)
│   │   ├── chainsight_api_design.md (v2.1)
│   │   ├── chainsight_ui_ux_design.md (v2.2)
│   │   └── chainsight_marketview_pr_prompts.md (PR-1~7 프롬프트)
│   ├── remaining_work_plan.md
│   └── sec_pipeline_*.md (별도 SEC Pipeline)
├── task_done/                            ← v1.3 작업 완료 기록
│   ├── CS-0-0 ~ CS-5-3 (대부분)
│   ├── DC-2_etf_holdings_theme.md
│   ├── celery_beat_registration.md
│   └── chain_sight_redesign_V1/         ← redesign V1 PR 7개 + 보고서
│       ├── 00_summary.md
│       ├── PR-1 ~ PR-7
│       ├── browser_test_report.md
│       ├── data_quality_3_fixes.md
│       └── qa_evaluator_review_01.md (91% 승인)
└── update_v2/                            ← v1.4 (Path Watchlist) 별도 트랙
    ├── ROADMAP_v1.4.md
    ├── CHAIN_SIGHT_PM.md
    ├── RELATION_CONFIDENCE.md (복사본)
    ├── task_instructions/cs_00 ~ cs_73   (v1.4 전체 재작성)
    ├── task_done/CS-0-0 ~ CS-5-6 + cs_71_72_73 + CS-4-4
    └── review/CHANGES_v1.4.md, REVIEW_*, CLEANUP_GUIDE_*
```

### 트랙 간 관계 정리

- **트랙 1 (v1.3 원안)**: cs_00~cs_54로 표기되는 단일 트랙. Phase 0~3은 그대로 적용, Phase 4 API는 `/<symbol>/graph|suggestions/trace/`로 적용.
- **트랙 2 (redesign V1)**: 트랙 1 위에 **마켓 뷰 패러다임을 추가**. 시장 탐색 허브(`/chainsight`)를 메인으로 하고 cs_5_frontend_design_v2의 워크스페이스는 Deep Dive로 보조 위치 변경. Phase 4 API에 4개 추가(seeds/sector graph/neighbors/signals).
- **트랙 3 (v1.4 Path Watchlist)**: 트랙 1+2 위에 **Phase 6/7 추가**. SavedPath/PathAction 도입, Watch/Recheck/Expand/Alternatives API 신설, 프론트에 WatchButton/PathCard/FullPathView 추가.

세 트랙은 모두 살아있는 코드로 공존하며, 충돌 없음.

---

**END OF AUDIT**
