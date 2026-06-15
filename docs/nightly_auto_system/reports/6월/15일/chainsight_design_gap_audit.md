# Chain Sight 설계 갭 감사

> 읽기 전용 감사 보고서 (코드 무수정). 작성일 2026-06-15.
> 대상: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` + `frontend/` 코드.
> 방법: 4개 영역 병렬 감사 + 충돌 항목(GDS) 직접 코드 검증.

---

## 0. 사전 확인 (지시서 가정 vs 실제)

| 지시서 가정 | 실제 |
|---|---|
| `chainsight/` 앱 | **존재하지 않음.** 앱은 모노레포 구조로 `apps/chain_sight/` 에 위치 |
| `frontend/components/chainsight/` | 실제는 `frontend/components/chainsight/` (21개) + `frontend/app/chainsight/` (4 라우트) |
| 테스트 | `frontend/__tests__/chainsight/` 3개, `tests/chainsight/` |

> 앱 경로 차이로 인해 본 감사는 `apps/chain_sight/` 기준으로 수행함.

---

## 1. 요약 (구현률)

**종합 구현률: 약 88%** (자동화 파이프라인 + API + FE 마켓뷰는 실질 완성, GDS 배치 자동화와 일부 관계 타입 생성이 갭)

| Phase | 영역 | 상태 | 구현률 |
|---|---|---|---|
| Phase 0 (CS-0) | 레거시 정리 / Neo4j 연결 / 스키마 | ✅ 거의 완성 | ~95% |
| Phase 1 (CS-1) | Stock/Sector/Industry/Peer 로드 | ✅ 완성 | 100% |
| Phase 1 시드 (redesign) | 시드 선정 5소스 + 스냅샷 | ✅ 완성 | ~95% |
| Phase 2 (CS-2) | 프로파일·관계 신뢰도 엔진 | ✅ 완성 | 100% |
| Phase 3 동기화 (CS-3-1/2) | Neo4j dirty sync | ✅ 완성 | 100% |
| **Phase 3 GDS (CS-3-3)** | **PageRank/Louvain/Betweenness 배치** | ❌ **미구현(자동화)** | **~10%** |
| Phase 4 (CS-4) | REST API (graph/suggestion/trace + 마켓뷰 4종) | 🟡 거의 완성 | ~95% |
| Phase 5 (CS-5) | 프론트엔드 (마켓뷰 + Deep dive) | ✅ 거의 완성 | ~95% |
| 관계 타입 확장 | SUPPLIES_TO / COMPETES_WITH / HAS_THEME 자동 생성 | ❌ 미구현 | ~10% |

**핵심 갭 3개**
1. **CS-3-3 GDS 배치 자동화 미구현** — 가장 큰 갭. 계산·저장 태스크 부재, 읽기 측만 존재.
2. **공급망/경쟁/테마 관계 자동 생성 로직 부재** — `relation_confidence_design_v1`이 정의한 SUPPLIES_TO/COMPETES_WITH/HAS_THEME 생성기 미구현. 자동 관계는 PEER_OF / CO_MENTIONED / PRICE_CORRELATED 3종에 한정.
3. **CS-4-2 suggestion API 공급망 카테고리 누락** — 위 2번의 직접 결과(SUPPLIES_TO 데이터 빈약).

---

## 2. 문서별 상태 테이블

분류: **(A)** 완전 구현 · **(B)** 부분 구현 · **(C)** 미구현 · **(D)** 폐기/대체

### Phase 0 — 인프라

| 문서 | 분류 | 근거 / 비고 |
|---|---|---|
| cs_00 legacy_cleanup_api_test | A/D | 레거시 6뷰·3서비스·FE 제거 완료. API 테스트는 decision으로 기록(Finnhub 403 등). `utils.normalize_pair` 구현 |
| cs_01 migrations_verification | A | RelationConfidence v2.1 필드군 전부 구현 (`models/relation_discovery.py:64-184`) |
| cs_02 neo4j_connection | **B** | `Neo4jGraphRepository` PID-lazy init + bulk/health/count 메서드 구현. **단** Protocol에는 bulk/health/count 미선언(구현체에만 존재), 설정명 `NEO4J_USER`(설계)↔`NEO4J_USERNAME`(코드) 불일치 |
| cs_03 neo4j_schema | **B** | Constraint 4종 + `init_neo4j_schema` 명령(--verify/--check/--reset) 구현. 인덱스 2개(stock_sector, stock_community)는 설계(cs_03)와 일치하나 task_done에 "4개"로 오기록 |
| cs_11 stock_node_bulk_load | A | `load_stocks_to_neo4j` + 필드매핑 + 명령(--limit/--dry-run), batch_size=100 |
| cs_12 sector_industry | A | `load_sectors_to_neo4j` (Sector/Industry + BELONGS_TO_*) + 명령 |
| cs_13 peer_relations | A | finnhub/fmp peer fetch + `collect_all_peers` + `load_peers_to_neo4j` + peer_tasks + 명령 |

### Phase 1 시드 (redesign)

| 문서 | 분류 | 근거 / 비고 |
|---|---|---|
| chainsight_seed_node_design | **B** | Phase 1 시드 5소스(price/volume/sector_outlier/relation_change/comention_surge) + `select_seeds`(MAX=20) + `build_sector_summary` + `SeedSnapshot` + Redis TTL + Beat 등록 = 완성. **미구현**: 설계 §3.4 `SeedHeatScore` 모델(별도 테이블 없이 Neo4j 노드 속성으로 대체) / **Phase 2 Heat Score 정식화·Phase 3 이벤트 전파**(의도적 보류) |

### Phase 2 — 프로파일·관계 엔진 (전건 A)

| 문서 | 분류 | 근거 |
|---|---|---|
| cs_21 tier_a_profile | A | `CompanyGrowthStage`/`CompanyCapitalDNA` + `profile_tasks.py` (task_done 480/503 적재) |
| cs_21b sensitivity_profile | A | `CompanySensitivityProfile` + `sensitivity_tasks.py` (FMP Geo, 503/503) |
| cs_21c insider_signal | A | `CompanyInsiderSignal` + `insider_tasks.py` (Finnhub, 503/503) |
| cs_22 co_mention | A | `CoMentionEdge`/`ChainNewsEvent` + `relation_tasks.extract_co_mentions` (744쌍) |
| cs_23 price_co_movement | A | `PriceCoMovement` + `calculate_price_co_movement` (2,473쌍) |
| cs_24 relation_confidence | A | `RelationConfidence` v2.1 + `update_relation_confidence` + stale/decay (3,527건). 설계 대비 Tier 체계 일부 단순화(논리 동일) |
| cs_25 chain_profile_aggregation | A | `CompanyChainProfile` + `aggregate_chain_profiles` + Beat 7종 등록 (503건) |

### Phase 3 — 동기화 + GDS

| 문서 | 분류 | 근거 |
|---|---|---|
| cs_31 profile_neo4j_sync | A | `sync_profiles_to_neo4j` + `neo4j_dirty` 플래그 (503/503) |
| cs_32 relation_neo4j_sync | A | `services/neo4j_sync.sync_dirty_relations` + `_upsert_edge`/`_delete_edge`, normalize_pair (1,631 엣지) |
| **cs_33 gds_algorithms** | **C** | **미구현(자동화).** ↓ §3.1 직접검증 참조 |

### relation_confidence_design_v1 (상세 설계)

| 문서 | 분류 | 근거 |
|---|---|---|
| relation_confidence_design_v1 | **B** | v2.1 모델 스키마 / 상태 5단계(hidden→weak→probable→confirmed→stale) / PEER_OF·CO_MENTIONED·PRICE_CORRELATED 규칙 = 구현. **미구현**: SUPPLIES_TO·COMPETES_WITH·HAS_THEME 관계 **생성** 로직(§ 관계타입별 규칙), Evidence Tier(1/2/3) 명시 세분화는 JSONB 통합 저장으로 약화 |

### Phase 4 — API

| 문서 | 분류 | 근거 |
|---|---|---|
| cs_41 graph_api | A | `ChainSightGraphView` (`/{symbol}/graph/?depth=`), market_signals 보강, CUSTOMER_OF 역방향 파생 |
| cs_42 suggestion_api | **B** | `ChainSightSuggestionView` 5카테고리 중 **4개만**(경쟁사/같은산업/뉴스/같은섹터). **공급망(SUPPLIES_TO) 카테고리 누락** |
| cs_43 trace_api | A | `ChainSightTraceView` (`/trace/?from=&to=`) shortestPath + 400/404 처리 |
| redesign chainsight_api_design | A | 마켓뷰 4종 전부: `SeedListView`/`SectorGraphView`/`NeighborGraphView`/`SignalFeedView` + display_type 파생 + Redis 캐시 |

### Phase 5 — 프론트엔드

| 문서 | 분류 | 근거 |
|---|---|---|
| cs_51 graph_visualization | A | `GraphCanvas.tsx` (Spotlight + lazy expansion + 섹터색 + depth 전환) |
| cs_52 ai_guide_ui | A | `AIGuidePanel.tsx` (카테고리 카드 필터링, strength dots) |
| cs_53 chain_trace_ui | A | `TracePathView.tsx` (from/to → 체인 시각화 + 한글 라벨) |
| cs_54 stock_detail_integration | **B** | `GraphMiniView.tsx` + stocks 상세 탭 교체 + "전체보기" 링크 = 동작. **미구현(미세)**: "N개 종목과 연결" count 텍스트 / 상위 6 ticker 태그 UI |
| **cs_5_frontend_design_v2** | **D** | **폐기/대체.** 종목상세 탭 중심 원안 → redesign(마켓뷰 `/chainsight` + 전용 워크스페이스 `/chainsight/[symbol]`)로 교체. 코드는 redesign을 따름 |
| redesign chainsight_ui_ux_design | A | 마켓뷰 5컴포넌트 전부: `SectorBar`/`MarketGraphCanvas`/`ExplorationTrail`/`RelationCardPanel`/`ChainStoryFeed` + explorationStore + `?focus=` 딥링크 |

### redesign PR 단위 (chainsight_marketview_pr_prompts → task_done)

| PR | 분류 | 근거 |
|---|---|---|
| PR-1 스키마 마이그레이션 | A | `neo4j_dirty`/`previous_status`/`neo4j_synced_at` (migration 0005) + save() 오버라이드 |
| PR-2 시드 선정 Task | A | 5소스 + Redis 캐시 + Beat(매일 13:00 UTC). data_quality fix로 change_percent 보정 |
| PR-3 Neo4j Dirty Sync | A | `sync_dirty_relations` + Beat(일 04:30, neo4j 큐) + market weak 동기화 |
| PR-4 마켓뷰 API 4종 | A | 4 View 완성, FE 타입과 일치 |
| PR-5 FE 상태+섹터바+그래프 | A | explorationStore(Zustand) + useMarketView(TanStack) + 2 컴포넌트 |
| PR-6 트레일+카드 패널 | A | `ExplorationTrail` + `RelationCardPanel` (pre-focus/focused 분기) |
| PR-7 체인 스토리 피드 | A | `ChainStoryFeed` 무한스크롤 + 카테고리 라벨(가격상관 포함) |

### 범위 외 추가 구현 (설계서엔 없으나 코드에 존재)

| 기능 | 상태 | 비고 |
|---|---|---|
| Watchlist | A | `WatchlistViewSet` + `/chainsight/watchlist/` 라우트 + `SavedPath`/`PathAction` |
| 이벤트 보드 (CS-RD2 관심도 M1) | A | `EventBoardView`/`EventRankingView` + `StockAttentionScore` + `attention_service` (최근 커밋 d4407f6) |
| recheck/expand/alternatives 서비스 | A | 경로 재점검·확장·대안 탐색 서비스 (SavedPath 회고 기능 기반) |

---

## 3. 미구현 항목 상세

### 3.1 [최우선] CS-3-3 GDS 배치 자동화 — (C) 미구현 ★직접검증★

> 병렬 감사에서 판정이 충돌하여(영역2=미구현 / 영역4=완료) 코드로 직접 확인함.

**직접 검증 결과 (영역2가 정확):**
- `apps/chain_sight/tasks/gds_tasks.py` → **파일 없음**
- GDS를 **계산·write 하는 코드 전무**: `gds.pageRank.write` / `gds.louvain.write` / `gds.betweenness.write` / `graph.project(...)` 호출 0건
- `graph/repository.py`에 GDS projection/write 메서드 없음
- Celery Beat에 GDS 스케줄 미등록
- **읽기 측만 존재**: `services/path_service.py:185 _fetch_centrality()`가 Neo4j 노드의 `s.pagerank_score` / `s.betweenness_score`를 **조회만** 함. 게다가 `pagerank_valid`/`betweenness_valid` 분기로 **값이 없을 경우(None) 폴백 가중치**를 명시 처리(`path_service.py:147-161`) → 속성이 비어있을 수 있음을 코드 스스로 전제
- `graph/schema.py:41` 의 `stock_community` 인덱스, `regenerate_summary_paths` 명령의 "run after GDS rerun" 주석 → GDS가 **수동 1회 실행 전제**로만 소비됨

**결론**: GDS 알고리즘 자체는 (task_done 기록상) Neo4j에서 **수동 1회** 돌려 노드 속성을 주입했을 수 있으나, **설계가 요구한 "Celery 배치 자동화"는 미구현**. 데이터가 stale 되어도 자동 재계산되지 않음. 영역4의 "Phase 3 100% 완료"는 task_done 문서의 "M3 달성" 표현을 과신한 것이며, 정작 CS-3-3 task_done 본문도 "보류 / GDS 플러그인 별도 설치 / 수동 실행"으로 기록됨.

**필요 작업**: `gds_tasks.run_gds_algorithms()` + repository GDS 메서드 + Beat 등록 (3종 알고리즘).

### 3.2 [높음] 관계 타입 자동 생성 — SUPPLIES_TO / COMPETES_WITH / HAS_THEME — (C)

- `relation_confidence_design_v1`은 truth/market 관계로 SUPPLIES_TO(공급망)·COMPETES_WITH(경쟁)·HAS_THEME(테마)를 정의하나, `relation_tasks.py`의 자동 생성기는 **PEER_OF / CO_MENTIONED / PRICE_CORRELATED 3종만** 처리
- SUPPLIES_TO: manual_seed 기반 — 현재 자동 생성 경로 없음
- COMPETES_WITH: 설계만 존재, 생성 로직 없음
- HAS_THEME: ETF holdings 기반 — **DC-2(ETF→Theme 노드)** 미완(진행 중)에 종속

### 3.3 [중간] CS-4-2 suggestion API 공급망 카테고리 누락 — (B)

- `ChainSightSuggestionView`가 5카테고리 중 4개만 반환(공급망 빠짐). §3.2의 SUPPLIES_TO 데이터 빈약이 근인.

### 3.4 [낮음] cs_02 Protocol 계약 + 설정명 불일치 — (B)

- `GraphRepository` Protocol에 `bulk_upsert_nodes`/`bulk_upsert_edges`/`health_check`/`node_count`/`edge_count` 미선언(구현체에만 존재) → 동작엔 무해, 계약 불완전
- 설정명 `NEO4J_USER`(설계) vs `NEO4J_USERNAME`(코드)

### 3.5 [낮음] cs_54 미니뷰 정보 표시 — (B)

- "N개 종목과 연결" count 텍스트 / 상위 6 ticker 태그 UI 미전시 (미니 그래프 자체는 동작)

### 3.6 [낮음] 시드 Heat Score / Phase 3 이벤트 전파 — (C, 의도적 보류)

- `SeedHeatScore` 모델 미생성(Neo4j 노드 속성으로 대체), Phase 2 가중치 학습·Phase 3 전파(text_conditional_prob/lagged correlation/propagation_weight) 로드맵 범위 외 보류

### 3.7 [낮음] task_done 기록 오류 (문서 결함, 코드 정상)

- CS-0-3 task_done: 인덱스 "4개" 기록 ↔ 실제 코드·설계 2개. 코드는 정상, **완료 보고서 기록이 부정확**.

---

## 4. 폐기/대체 항목

### 4.1 redesign_v1_260409 의 대체 관계 판정 → **부분 대체 + 병렬 공존** (전면 대체 아님)

| 영역 | 기존 cs_* | redesign_v1_260409 | 판정 |
|---|---|---|---|
| 마켓뷰 `/chainsight` | (없음) | 신규 4 API + 5 FE 컴포넌트 | **신규 추가** |
| Deep dive `/chainsight/[symbol]` | cs_51~54 | 개념 유지·기존 코드 활용 | **병렬 공존** |
| 프론트 화면 아키텍처 | **cs_5_frontend_design_v2** (종목상세 탭) | 전용 워크스페이스 분리 | **(D) 폐기/대체** |
| 시드 선정 | cs_13 peer load만 | 5소스 재설계 | **부분 대체** |
| Neo4j 동기화 | cs_31/32 정적 | `neo4j_dirty` 델타 동기화 | **부분 대체** |
| API | cs_41~43 (deep) | cs_41~43 유지 + 마켓뷰 4종 추가 | **확장(병존)** |
| 기업 프로파일 | cs_21~25 | 영향 없음 | **독립 병존** |

**완전 폐기된 설계 문서: `cs_5_frontend_design_v2` 1건** (종목상세 탭 인터랙티브 그래프 원안 → redesign 워크스페이스 모델로 교체, 코드는 redesign을 따름).
나머지 cs_* 문서는 모두 유효하며 redesign과 공존. cs_41~43은 deep-dive API로 살아있고 마켓뷰 API가 그 위에 추가됨.

### 4.2 설계→구현 방향 전환 (D 성격의 부분 대체)

| 설계 항목 | 전환 결과 |
|---|---|
| `SeedHeatScore` 모델 (별도 테이블) | Neo4j Stock 노드 속성(heat_score 등)으로 대체 |
| `synced_to_neo4j` 불리언 | `neo4j_dirty` 플래그 패턴으로 대체 (audit P0 #9, 양방향 델타) |
| Neo4j 엣지 `RELATED_TO` 하드코딩 | dirty sync 동적 타입(PEER_OF/PRICE_CORRELATED/CO_MENTIONED)으로 대체 |
| RelationConfidence Tier 1/2/3 명시 분류 | evidence_sources JSONB 통합 저장으로 단순화 |

---

## 5. 권장 후속 조치 (우선순위)

1. **CS-3-3 GDS 배치 자동화 구현** — `gds_tasks.run_gds_algorithms()` + repository GDS write 메서드 + Beat 등록. 현재 path landmark scoring이 stale/없는 centrality에 폴백 의존 중.
2. **SUPPLIES_TO / COMPETES_WITH / HAS_THEME 자동 생성** — DC-2(ETF→Theme) 완료와 연계. 완료 시 CS-4-2 공급망 카테고리(§3.3)도 자동 해소.
3. **task_done 기록 정정** — CS-0-3 인덱스 개수(2개), CS-3-3 GDS "완료" 표현을 "수동 1회/배치 미자동화"로 정정.
4. (낮음) cs_02 Protocol 메서드 선언 보강 + 설정명 통일, cs_54 미니뷰 count/태그 표시.

---

## 부록: 감사 방법론 주석

- 4개 영역(인프라/엔진/API·FE/redesign·로드맵)을 병렬 읽기 전용 에이전트로 코드 직접 대조.
- 영역 간 판정 충돌은 **CS-3-3 GDS 1건**뿐이었고, 본 작성자가 `grep`로 직접 검증하여 "미구현(자동화)"로 확정(§3.1).
- task_done 완료 보고서는 보조 근거로만 사용하고, 최종 분류는 **현재 코드 존재 여부**를 1차 소스로 삼음(따라서 일부 항목에서 task_done "완료" 기록보다 보수적으로 판정).
