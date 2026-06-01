# Chain Sight 설계 갭 감사

> 감사일: 2026-06-01 · 모드: **read-only (코드/문서 수정 없음)**
> 방법: 설계 문서(`docs/chain_sight/plan/`, `update_v2/`, `decisions/`, `graph_redesign_v2.md`) ↔ 구현 코드(`apps/chain_sight/`, `frontend/components|app/chainsight/`) 1:1 대조 + `task_done/` 완료 보고서 교차 검증
> 경로 주의: 설계서의 `chainsight/` 경로는 monorepo 이동으로 실제 **`apps/chain_sight/`**. 프론트는 **`frontend/components/chainsight/`**, **`frontend/app/chainsight/`**.

---

## 요약 (구현률)

| 영역 | 분류 | 구현률(설계 항목 기준) | 핵심 갭 |
|------|------|----------------------|---------|
| **백엔드 Phase 0~1** (인프라·시드 로드, cs_00~13) | **A 완전** | ~100% | 없음 |
| **백엔드 Phase 2** (파생 파이프라인, cs_21~25) | **A 완전** | ~100% | 없음 (RelationConfidence v2.1 전 필드 존재) |
| **백엔드 Phase 3 sync** (cs_31~32) | **A 완전** | 100% | 없음 |
| **백엔드 Phase 3 GDS** (cs_33) | **C 미구현** | 0% (재현 task) | ⚠️ 문서는 완료 주장, 코드 없음 |
| **백엔드 Phase 4 API** (cs_41~43) | **A / B** | ~85% | cs_42 suggestion 카테고리 2종 누락 |
| **redesign 백엔드** (api/seed/marketview PR-1~4) | **A 완전 + 초과달성** | ~100% | Heat Score Phase 2 일부, Phase 3 전체 미구현 |
| **redesign 시드 Phase 2** (heat score) | **B 부분** | ~65% | gds_centrality_delta 누락, heat_total 정렬 미적용 |
| **redesign 시드 Phase 3** (이벤트 전파) | **C 미구현** | 0% | 설계상 후순위로 명시 |
| **프론트 레거시** (cs_51~54, v2) | **A / D** | ~80% | v2 프로 기능(오버레이·비교) 미구현 |
| **프론트 redesign 마켓뷰** (PR-5~7) | **A 구현 / B 미검증** | ~90% | 체인스토리·path highlight 데이터 부족 미검증 |
| **graph_redesign_v2** (FE 방사형 레이아웃) | **C 미구현** | 0% | 미래 FE 설계, 백엔드 항목 0건 |

**총평**: Chain Sight의 **핵심 MVP(백엔드 파이프라인 + redesign 마켓뷰)는 거의 완전 구현(A)** 상태. 진짜 갭은 세 곳에 집중 — ① **cs_33 GDS 재현 task 부재(문서-코드 불일치, 가장 시급)**, ② **redesign 시드 Heat Score Phase 2 부분구현 + Phase 3 전체 미구현**(후순위로 의도된 것), ③ **프론트 v2 프로 기능(메트릭 오버레이·노드 비교) 미구현**. redesign은 cs_*를 **대체한 것이 아니라 위에 마켓뷰를 덧씌운 구조**로, 두 세대가 코드에 공존한다.

---

## 핵심 질문 답변

### Q1. redesign_v1_260409가 기존 cs_* 문서를 대체하는가?

**아니다. "대체"가 아니라 "위에 덧씌운 마켓 뷰 재구성"이다. cs_* 백엔드 기반(관계 엔진·Neo4j·heat_score·Watchlist)은 그대로 유지·재사용된다.**

근거:
- `redesign_v1_260409/chainsight_api_design.md`가 명시적으로 cs_* 자산 재사용 선언 — "새 엔드포인트 추가 없이 기존 4개를 재사용"(line 13), deep dive API(`{symbol}/graph/`, `suggestions/`, `trace/`)는 "기존 유지"(line 444-446).
- 코드에서 cs_* API(`ChainSightGraphView`/`SuggestionView`/`TraceView`)와 redesign 마켓뷰 4종(`SeedListView`/`SectorGraphView`/`NeighborGraphView`/`SignalFeedView`)이 **공존** (`apps/chain_sight/api/views.py`, `api/urls.py`).
- 모델 레이어는 cs_* 그대로 유지(`RelationConfidence`, `CoMentionEdge`, `PriceCoMovement`, `SavedPath/PathAction`, Tier A 4종). redesign은 여기에 `previous_status`/`neo4j_dirty` **필드만 추가**(migration 0005).
- **결정적 증거 — 두 heat_score 시스템 공존**: cs_44 Neo4j heat_score(`chainsight-heat-score-daily` 07:00 beat)와 redesign daily seed(`chainsight-seed-selection` 13:00 beat)가 **둘 다 활성**. 대체였다면 하나가 제거됐어야 함.

**대체된 부분**: 프론트 진입 UX만. cs_51~54 단일화면 설계 → redesign 2워크스페이스(마켓뷰 `/chainsight` breadth-first + Deep dive `/chainsight/[symbol]` depth-first)로 대체. 레거시 컴포넌트는 Deep dive로 흡수·강등.

### Q2. update_v2 / graph_redesign_v2의 위치는?

- **update_v2/** = **cs_* 시스템의 원본 사양서(ROADMAP_v1.4)**. `task_instructions/cs_00~cs_73` + `task_done/CS-0-0~cs_71_72_73`로 이미 **구현된 시스템의 설계 문서**(미래 설계 아님). 코드와 1:1 대응. 단 PM 문서 일부(strengthening/weakening 자동전환, path-level compare, 개인화)는 §10 제외 목록으로 미구현 명시.
- **graph_redesign_v2.md** = **순수 프론트엔드 미래 설계(C 미구현)**. 시멘틱 방사형 레이아웃(관계=각도), 관계 토글 칩 바 6종, 5단계 점진적 공개, Canvas/react-force-graph 구현 주의사항. **백엔드 작업 항목 0건.** 자체 Deferred Commits도 전부 FE 태스크(RelationChipBar, MarketGraphCanvas 좌표계산). 일부는 이미 `RelationFilterChips.tsx`/`radialLayout.ts`로 선반영됨.

### Q3. cs_51~54 vs frontend/components/chainsight/ 구현?

레거시 컴포넌트는 redesign으로 **대체되지 않고 Deep dive workspace로 잔존**. 역할 분담만 발생(상세 매핑은 아래 §폐기/대체 항목 참조). cs_51~54 핵심(그래프/노드상세/미니뷰/Trace/AI가이드)은 모두 구현됐으나, 일부는 독립 파일이 아닌 **부모 컴포넌트 인라인 함수**로 구현됨(D).

---

## 문서별 상태 테이블

### 백엔드 — Phase 0~1 인프라·시드 로드

| 문서 | 설계 핵심 | 분류 | 근거 (코드) |
|------|----------|------|------|
| cs_00 legacy cleanup | serverless/frontend 레거시 제거 + API 테스트 | **A** | 구버전 `frontend/components/chain-sight/` 제거, `decisions/003` 기록 |
| cs_01 migrations | 12 테이블 생성 | **A** | `migrations/0001~0008`, CreateModel 12건 |
| cs_02 neo4j connection | PID-safe driver | **A** | `graph/repository.py` |
| cs_03 neo4j schema | 4 constraint + index + command | **A** | `graph/schema.py`, `commands/init_neo4j_schema.py` |
| cs_11 stock 노드 로드 | load command | **A** | `commands/load_stocks_to_neo4j.py` |
| cs_12 sector/industry | load command | **A** | `commands/load_sectors_to_neo4j.py` |
| cs_13 peer 관계 | fetch task | **A** | `tasks/peer_tasks.py`, `commands/load_peers_to_neo4j.py` |

### 백엔드 — Phase 2 파생 파이프라인

| 문서 | 설계 핵심 | 분류 | 근거 (코드:심볼) |
|------|----------|------|------|
| cs_21 Tier A | GrowthStage + CapitalDNA | **A** | `tasks/profile_tasks.py:calculate_growth_stages`, `calculate_capital_dna` |
| cs_21b Sensitivity | FMP Geo + BS + beta | **A** | `tasks/sensitivity_tasks.py:calculate_sensitivity_profiles` |
| cs_21c Insider | Finnhub 90일 집계 | **A** | `tasks/insider_tasks.py:calculate_insider_signals` |
| cs_22 CoMention | NewsEntity 동시출현 | **A** | `tasks/relation_tasks.py:extract_co_mentions` |
| cs_23 PriceCoMovement | 90일 rolling corr | **A** | `tasks/relation_tasks.py:calculate_price_co_movement` |
| cs_24 RelationConfidence | tier/score/status + stale decay | **A** | `tasks/relation_tasks.py:update_relation_confidence` + `check_stale_and_decay` |
| cs_25 ChainProfile 집약 + Beat | aggregate + Beat 8개 | **A** | `tasks/sync_tasks.py:aggregate_chain_profiles`, `config/celery.py` |
| relation_confidence_design_v1 | v2.1 스키마(22필드, 5단계 상태) | **A** | `models/relation_discovery.py:RelationConfidence` 전 필드 존재, `utils.py:normalize_pair` |

### 백엔드 — Phase 3 동기화 + GDS

| 문서 | 설계 핵심 | 분류 | 근거 |
|------|----------|------|------|
| cs_31 profile→neo4j | dirty delta sync | **A** | `tasks/sync_tasks.py:sync_profiles_to_neo4j` |
| cs_32 relation→neo4j | confirmed/probable 엣지 sync | **A** | `tasks/sync_tasks.py:sync_relations_to_neo4j` → `services/neo4j_sync.py:sync_dirty_relations` |
| **cs_33 GDS 알고리즘** | `gds_tasks.py:run_gds_algorithms` (pageRank/louvain/betweenness write) | **C 미구현** | ⚠️ `gds_tasks.py` 파일 없음. `gds.`/`graph.project`/`.write` 호출 0건 |

### 백엔드 — Phase 4 API

| 문서 | 설계 핵심 | 분류 | 근거 |
|------|----------|------|------|
| cs_41 graph API | N-depth 그래프 | **A** | `api/views.py:ChainSightGraphView` |
| cs_42 suggestion API | 카테고리 제안 5종 | **B 부분** | `ChainSightSuggestionView` — peers/same_industry/co_mentioned/same_sector만. supply_chain·community(클러스터)·COMPETES_WITH 누락 |
| cs_43 trace API | 최단 경로 | **A** | `api/views.py:ChainSightTraceView` |

### 백엔드 — redesign_v1_260409

| 문서 | 설계 핵심 | 분류 | 근거 (코드:심볼) |
|------|----------|------|------|
| api_design §2 GET /seeds/ | 시드+섹터요약 Redis 읽기 | **A** | `api/views.py:SeedListView` + `_get_today_seeds` (3단 폴백) |
| api_design §3 GET /sector/{}/graph/ | overview graph, node_size percentile | **A** | `views.py:SectorGraphView._node_size` |
| api_design §4 GET /{symbol}/neighbors/ | 중심+이웃, display_type 파생 | **A** | `views.py:NeighborGraphView._display_type` |
| api_design §5 GET /signals/ | 시드페어 shortestPath 체인 | **A** | `views.py:SignalFeedView._build_chain_signals` |
| api_design §8 스키마 previous_status/neo4j_dirty | Phase 1 필드 | **A** | `models/relation_discovery.py` + migration 0005 |
| api_design §8 `SeedHeatScore` 신규 모델 | Phase 2 모델 | **D 폐기·대체** | Django 모델 부재 → Neo4j `:Stock.heat_score` 속성으로 대체 |
| seed_node_design §2 Phase 1 시드 5소스 | price/volume/sector/relation/comention | **A** | `services/seed_selection.py` 5개 함수 모두 존재 |
| seed_node_design §3 Phase 2 Heat Score | 6요소 가중, SeedHeatScore 저장 | **B 부분** | `seed_tasks.py:calculate_heat_scores` 4요소 균등 0.25, gds_centrality_delta 누락 |
| seed_node_design §4 Phase 3 이벤트 전파 | text_conditional_prob, propagation | **C 미구현** | 코드·beat 전무 (설계상 후순위 명시) |
| marketview PR-2 시드 task | get_market_date, N+1 방지 | **A** | `utils.py:get_market_date`, `seed_tasks.py:run_seed_selection` |
| marketview PR-3 neo4j_dirty sync | dirty 플래그, undirected 정규화 | **A** | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py` |
| marketview PR-4 API 4종 + URL 순서 | 고정경로 먼저 | **A** | `api/urls.py` 순서 정확 |
| graph_redesign_v2 | 방사형 레이아웃, 칩 바, 점진 공개 | **C 미구현 (FE 전용)** | 백엔드 항목 0건 |

### 프론트엔드 — 레거시 cs_51~54 + v2 (→ Deep dive `/chainsight/[symbol]`)

| 문서 | 설계 컴포넌트 | 분류 | 실제 코드 |
|------|------|------|------|
| cs_51 GraphView | 그래프 시각화 | **A** | `components/chainsight/GraphCanvas.tsx` (명명 변경) |
| cs_51 GraphControls | depth/reset/필터 | **D** | 별도 파일 없음, page 헤더 인라인 + FilterPanel 분리 |
| cs_51 NodeDetailPanel | 노드 상세 | **A** | `NodeDetailPanel.tsx` |
| cs_52 SuggestionCards/CategoryCard | AI 가이드 | **D** | `AIGuidePanel.tsx`가 카테고리 카드 인라인 렌더 |
| cs_53 TraceView/TracePanel | 경로 추적 | **B** | `TracePathView.tsx`(결과) + 입력은 AIGuidePanel 인라인. 독립 TracePanel 없음 |
| cs_54 ChainSightMiniView | 종목상세 미니뷰 | **A** | `GraphMiniView.tsx` (명명 변경) |
| cs_54 종목상세 탭 활성화 | 탭 통합 | **A** | `app/stocks/[symbol]/page.tsx:446-459` |
| v2 §5 NodeDetailPanel CTA 5개 | 가설/Watchlist/Validation/탐색/경로 | **B** | "⭐ Watchlist 추가" CTA 누락(4개만 검증) |
| v2 §6-2 노드 메트릭 오버레이 | PER/시총/Centrality/Louvain | **C 미구현** | 흔적 없음 |
| v2 §6-3 노드 비교 모드 | Ctrl+Click 비교 | **C 미구현** | 흔적 없음 |
| cs_53/v2 Trace 그래프 하이라이트 | 캔버스 경로 강조 | **C 미구현** | TracePathView는 텍스트만 |

### 프론트엔드 — redesign v2.2 마켓뷰 (→ `/chainsight`) + PR-5~7

| 문서 | 설계 컴포넌트/화면 | 분류 | 실제 코드 |
|------|------|------|------|
| §12 마켓뷰 메인 | app/chainsight/page.tsx | **A** | `app/chainsight/page.tsx` |
| §12 SectorBar | 섹터 바 | **A** | `components/chainsight/SectorBar.tsx` |
| §12 MarketGraphCanvas | 마켓 그래프 | **A** | `MarketGraphCanvas.tsx` (37KB 최대 구현) |
| §12 ExplorationTrail | 탐색 트레일 | **A** | `ExplorationTrail.tsx` |
| §12 RelationCardPanel | 관계/시드 카드 | **A** | `RelationCardPanel.tsx` |
| §12 RelationCard / SeedCard / ChainStoryCard | 개별 카드 | **D** | 별도 파일 없음, 부모 내부 함수 인라인 |
| §12 ChainStoryFeed | 체인 스토리 피드 | **A (코드) / B (미검증)** | `ChainStoryFeed.tsx`, browser_test 데이터 부족 미검증 |
| §12 useExplorationState | 상태 훅 | **D→A** | `lib/stores/explorationStore.ts` (Zustand로 변경) |
| §12 useSeedData/useSectorGraph/useNeighbors/useSignalFeed | 데이터 훅 4종 | **A** | `hooks/useMarketView.ts`에 통합 |
| §7 chain path highlight | 그래프 경로 강조 | **B 미검증** | `MarketGraphCanvas:785,878 highlightedChain` 전달되나 데이터 부족 미검증 |
| §7 시드 bounce 애니메이션 | 전환 애니메이션 | **B 미구현** | browser_test "범위 밖(후속)" 명시 |
| §11 `?focus=` 딥링크 | 딥링크 진입 | **A** | `app/chainsight/page.tsx:22-30` |

---

## 미구현 항목 상세

### [C-1] cs_33 GDS 알고리즘 재현 task 부재 — **가장 시급 (문서-코드 불일치)**
- **설계**(`cs_33_gds_algorithms.md`): `run_gds_algorithms()` task가 `graph.project` → `gds.pageRank.write`/`gds.louvain.write`/`gds.betweenness.write`로 `pagerank_score`/`community_id`/`betweenness_score` 노드 속성을 주간 배치로 채움.
- **현실**: `apps/chain_sight/tasks/gds_tasks.py` 부재. GDS 쓰기 호출 0건. `services/path_service.py:186~203`은 `s.pagerank_score`/`s.betweenness_score`를 **읽기만** 함. `graph/schema.py:41`은 `community_id` **인덱스만** 생성하고 쓰는 코드 없음.
- **영향**: centrality/community 값이 일회성으로만 채워졌고 자동 갱신 안 됨. cs_42의 "같은 클러스터(community)" 카테고리도 이 데이터 부재로 연쇄 미구현.
- ⚠️ `task_done/CS-3-3_gds_algorithms.md` + `remaining_work_plan.md`는 "2026-04-03 M3 마일스톤 달성"으로 **완료** 기록(Top 5 수치까지 명시)하나 재현 task가 코드에 전혀 없음 → **일회성 수동/외부 스크립트 실행 추정**. 로드맵 원칙(문서-코드 일치) 위반.

### [B-1] cs_42 suggestion API — 카테고리 일부 누락
- 설계 5종(peers[PEER_OF+COMPETES_WITH, pagerank 정렬], supply_chain[SUPPLIES_TO], same_sector, co_mentioned, community[community_id]) 중 구현은 4종(peers[PEER_OF만], same_industry, co_mentioned, same_sector).
- 누락: `supply_chain` 카테고리, `community`(클러스터) 카테고리, peers의 `COMPETES_WITH`/pagerank 정렬. 단 supply_chain/community는 데이터 자체 미공급(SUPPLIES_TO 시드 미적재, GDS 미실행)이라 사실상 **데이터 의존 미구현**.

### [B-2] redesign 시드 Heat Score Phase 2 — 축소 구현
- 설계(`seed_node_design §3`): 6개 가중 구성요소(0.25/0.20/0.20/0.15/0.10/0.10) + `SeedHeatScore` ORM 모델.
- 구현(`seed_tasks.py:calculate_heat_scores`): **4/6 구성요소만**(price/volume/relation_change/news_activation), 가중치 균등 0.25×4. **`gds_centrality_delta`·`news_event_count` 누락**. `SeedHeatScore` 모델 부재(Neo4j 노드 속성으로만 저장, PostgreSQL 이력 없음).
- `services/seed_selection.py:378`의 `heat_total`은 `0.0` 하드코딩 placeholder → 섹터 정렬은 여전히 Phase 1 `seed_count DESC`(`seed_selection.py:407`). 설계의 `heat_total DESC` 정렬 미적용.

### [C-2] redesign 시드 Phase 3 이벤트 전파 — 전체 미구현
- `text_conditional_prob`/lagged correlation/`propagation_weight`/ChromaDB·Embedding 연동 코드 0건. beat 3종(`chainsight-text-conditional`/`chainsight-lagged-correlation`/`chainsight-propagation-weight`) 미등록. **설계에서 "범위 밖/후순위"로 명시한 계획된 미구현**.

### [C-3] 프론트 v2 프로 투자자 기능 — 미구현
- **v2 §6-2 노드 메트릭 오버레이**(PER 히트맵/시총 크기/Centrality/Louvain 색상 토글): 코드·보고서 흔적 없음. v2가 내세운 "전문 투자자 수준" 목표의 핵심 항목 통째 누락.
- **v2 §6-3 노드 비교 모드**(Ctrl+Click 2노드 비교): 미구현.
- **Chain Trace 그래프 경로 하이라이트**: `TracePathView.tsx`는 텍스트 step 나열만, Deep dive 캔버스 연동 없음.

### [B-3] 프론트 redesign 마켓뷰 — 미검증/일부 미구현
- **chain path highlight**: `highlightedChain` 전달은 되나 signals Neo4j 경로 데이터 부족으로 **실동작 미검증**(browser_test_report).
- **시드 bounce 애니메이션**: browser_test "범위 밖(후속)"으로 명시적 미구현.
- **ChainStoryFeed**: 코드 완성, signals 데이터 부족으로 렌더/클릭/무한스크롤 **미테스트**.
- **NodeDetailPanel "⭐ Watchlist 추가" CTA**: v2 §5 명세 5개 중 누락(4개만 검증).

---

## 폐기/대체 항목

| # | 항목 | 분류 | 내용 | 근거 |
|---|------|------|------|------|
| D-1 | cs_51~54 단일화면 설계 | 대체 | redesign 2워크스페이스(마켓뷰 breadth-first + Deep dive depth-first)로 대체. 원안 컴포넌트는 Deep dive로 흡수·강등 | redesign v2.2 §12 |
| D-2 | cs_41~43 API (graph/suggestions/trace) | 위상 강등(폐기 아님) | "Deep dive 전용"으로 강등. 코드 유지·동작. redesign 마켓뷰 4종 신규 추가, 두 세트 공존 | `api/urls.py` |
| D-3 | CUSTOMER_OF 별도 저장 | 폐기(설계 준수) | SUPPLIES_TO canonical로 통일, view에서 역방향 파생 | `views.py:94 derived_type`, `views.py:624 _display_type` |
| D-4 | `synced_to_neo4j` 플래그 | 폐기·통일 | `neo4j_dirty` 단일화. RelationConfidence/ChainProfile 모두 사용. RELATION_CONFIDENCE.md §7 스키마(synced_to_neo4j)는 **stale 문서** | `migrations/0008_unify_neo4j_flags.py`, `relation_discovery.py:147` |
| D-5 | `SeedHeatScore` Django 모델 | 폐기·대체 | DB 모델 대신 Neo4j `:Stock.heat_score` 속성으로 구현(cs_44 방식). expand/alternatives 서비스가 Cypher 직접 읽음 | `expand_service.py:_compute_expansion_score`, `seed_tasks.py` |
| D-6 | 레거시 RelationCard/SeedCard/ChainStoryCard/CategoryCard/TracePanel/GraphControls 독립 파일 | 인라인화 | 설계가 별도 파일로 명시했으나 부모 컴포넌트 내부 함수로 인라인 구현(기능 충족, 파일구조만 불일치) | `RelationCardPanel.tsx`, `ChainStoryFeed.tsx`, `AIGuidePanel.tsx` |
| D-7 | useExplorationState (useReducer 훅) | 변경 | Zustand store로 변경 | `lib/stores/explorationStore.ts` |

### 설계 외 추가 구현 (코드에만 존재 — 두 설계 문서에 근거 없음)
- **Path Watchlist 기능 전체**: `app/chainsight/watchlist/page.tsx`, `watchlist/[id]/page.tsx`, `PathCard.tsx`, `FullPathView.tsx`, `WatchButton.tsx`, `hooks/usePathWatchlist.ts`, 백엔드 `views/watchlist_views.py`, `serializers/path_watchlist.py`, `models/saved_path.py`(migration 0006). cs_6_1(SavedPath/PathAction) 기반의 후속 작업으로 추정.
- **RelationFilterChips / NodeContextMenu / NodeTooltip / radialLayout**: redesign v2.2 명세에 없는 신규(일부는 graph_redesign_v2 선반영).

---

## task_done 완료 주장 vs 실제 코드 불일치

| # | 보고서 | 주장 | 실제 | 심각도 |
|---|--------|------|------|--------|
| 1 | CS-3-3_gds_algorithms | GDS 3종 완료(M3 달성) | 재현 task/command 코드 부재, 일회성 실행 추정 | **중대** (자동 갱신 안 됨) |
| 2 | PR-5_fe_core_ui | 종목상세 Chain Sight 탭에 딥링크 "추가" | redesign §11은 "탭 **제거** → 딥링크"인데 탭+미니뷰가 그대로 잔존(`stocks/[symbol]/page.tsx:446-459`). 레거시 미니뷰 + redesign 딥링크 혼재 | **중** (spec-구현 불일치, 의도적 절충 가능성) |
| 3 | PR-7_chain_story_feed | ChainStoryFeed 완료 | browser_test_report: signals 데이터 부족으로 렌더/클릭/무한스크롤/path highlight **미테스트** | 중 (코드 작성 O, 실데이터 검증 X) |
| 4 | PR-1_schema_migration | `0005_add_neo4j_dirty_previous_status`만 언급 | 이후 `0008_unify_neo4j_flags`에서 `synced_to_neo4j` 제거됨 → PR-1 시점 필드는 현재 없음(문서 stale) | 낮음 (정상 진화) |
| 5 | redesign_V1 PR 보고서 전반 | 경로 `chainsight/...` 표기 | 실제 `apps/chain_sight/...`(앱 이동 후 보고서 미갱신) | 낮음 (표기만) |
| 6 | marketview PR-2 / seed_tasks docstring | seed-selection "12:00 UTC" | 실제 beat 13:00 UTC(data_quality 보고서가 정정, docstring stale) | 낮음 |
| 7 | CS-5-2_pro_features | NodeDetailPanel CTA 검증 | v2 §5 명세 5개 중 "Watchlist 추가" CTA 누락(4개만) | 낮음 |

> 참고: 동일 주제의 기존 야간 감사 보고서가 `docs/nightly_auto_system/reports/`에 5/2~5/31 다수 존재. 본 독립 검증은 5/31 보고서와 동일 결론에 도달(특히 cs_33 GDS 갭).

---

## 권고 (read-only — 정보 제공용, 조치 미수행)

1. **최우선**: cs_33 GDS 재현 task(`gds_tasks.py:run_gds_algorithms`) 신규 구현 또는 CS-3-3 완료 보고서를 "수동 1회 실행, 자동 갱신 없음"으로 정정. centrality/community 데이터 신선도 직결.
2. cs_42 supply_chain/community 카테고리는 GDS + SUPPLIES_TO 시드 데이터 선행 필요(데이터 의존).
3. redesign 시드 Heat Score Phase 2(gds_centrality_delta, heat_total 정렬)는 GDS 구현에 종속 → cs_33 해결 후 연계.
4. stale 문서 정리: RELATION_CONFIDENCE.md §7(synced_to_neo4j), seed_tasks docstring(12:00 UTC), redesign_V1 PR 보고서 경로 표기.
5. 종목상세 탭 잔존(불일치 #2)은 의도적 절충 여부를 DECISIONS.md에 명문화 필요(현재 코드 주석 근거 없음).
