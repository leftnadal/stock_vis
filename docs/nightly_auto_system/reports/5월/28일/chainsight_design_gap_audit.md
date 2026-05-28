# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-28
> **감사 범위**: `docs/chain_sight/plan/` 31개 설계 문서 vs `chainsight/` 백엔드 코드 + `frontend/components/chainsight/` 프론트엔드 코드
> **방식**: 읽기 전용. 코드 수정 없음.
> **교차 참조**: `docs/chain_sight/task_done/` 24개 완료 보고서

---

## 1. 요약 (구현률)

| 트랙 | 설계 문서 수 | 완전(A) | 부분(B) | 미구현(C) | 폐기/대체(D) | 구현률 |
|------|------------|--------|--------|----------|------------|--------|
| CS-0 인프라 (legacy/migration/neo4j) | 4 | 4 | 0 | 0 | 0 | 100% |
| CS-1 시드 로드 (stock/sector/peer) | 3 | 3 | 0 | 0 | 0 | 100% |
| CS-2 파생 데이터 (profile/relation) | 8 | 7 | 1 | 0 | 0 | 94% |
| CS-3 Neo4j 동기화 + GDS | 3 | 3 | 0 | 0 | 0 | 100% |
| CS-4 REST API (graph/suggest/trace) | 1 | 1 | 0 | 0 | 0 | 100% |
| CS-5 프론트엔드 (구안 cs_51~54) | 5 | 3 | 1 | 1 | 1 (cs_54) | 60%→대체 |
| redesign_v1_260409 (4 PR + 신규 API) | 4 (설계서) / 7 (PR) | 7 | 0 | 0 | 0 | 100% |
| Phase 2 Heat Score | (roadmap §3) | 0 | 1 | 1 (SeedHeatScore 모델) | 0 | 50% |
| Phase 3 이벤트 전파 (D) | (roadmap §4) | 0 | 0 | 3 (D-1/D-2/D-3) | 0 | 0% |
| SEC Pipeline (base + pr_detail) | 2 | 2 | 0 | 0 | 0 | 100% (별도 `sec_pipeline/` 앱) |

**핵심 결론**:
- **Phase 1 (M1) — M3 완전 구현** — 인프라, 시드 로드, 파생 데이터, Neo4j 동기화, GDS, REST API 4개 + 마켓뷰 4개 = 7개 API 모두 가동.
- **redesign_v1_260409가 cs_5_frontend_design_v2 / cs_54의 일부를 대체** — 메인 진입이 `/chainsight/[symbol]` 워크스페이스에서 `/chainsight` 마켓뷰로 전환. `[symbol]` 워크스페이스는 deep dive 보조 화면으로 격하 + 기존 컴포넌트 유지.
- **Phase 2 (Heat Score) 부분 구현** — `calculate_heat_scores()` 태스크는 있으나 설계서가 요구한 `SeedHeatScore` Django 모델은 미생성. Heat score는 Neo4j `:Stock` 속성으로만 저장.
- **Phase 3 (이벤트 전파) 미진입** — D-1 텍스트 조건부 확률 / D-2 lagged correlation / D-3 가중치 학습 미구현.

---

## 2. 문서별 상태 테이블

### 2-1. CS-0 인프라

| 설계 문서 | 코드 위치 | 상태 | 비고 |
|----------|---------|------|------|
| `cs_00_legacy_cleanup_api_test.md` | `task_done/CS-0-0_legacy_cleanup_api_test.md` | **A** | RelationConfidence v2.1 마이그레이션 포함 |
| `cs_01_migrations_verification.md` | `chainsight/migrations/0001~0008` | **A** | 8개 마이그레이션 적용 |
| `cs_02_neo4j_connection.md` | `chainsight/graph/repository.py` + `exceptions.py` | **A** | `get_graph_repository()` 진입점 |
| `cs_03_neo4j_schema.md` | `chainsight/graph/schema.py` + `management/commands/init_neo4j_schema.py` | **A** | 4 제약 조건 |

### 2-2. CS-1 시드 로드

| 설계 문서 | 코드 위치 | 상태 | 비고 |
|----------|---------|------|------|
| `cs_11_stock_node_bulk_load.md` | `services/neo4j_loader.py::load_stocks_to_neo4j` + `commands/load_stocks_to_neo4j.py` | **A** | 532 Stock 노드 (~Memory 1573 노드 기록) |
| `cs_12_sector_industry.md` | `services/neo4j_loader.py::load_sectors_to_neo4j` + `commands/load_sectors_to_neo4j.py` | **A** | 17 Sector / 128 Industry / BELONGS_TO_* |
| `cs_13_peer_relations.md` | `services/neo4j_loader.py::fetch_finnhub_peers/fmp_peers/load_peers_to_neo4j` + `tasks/peer_tasks.py` + `commands/load_peers_to_neo4j.py` | **A** | PEER_OF ~8350 → 누적 12,178 (data_quality fix 이후) |

### 2-3. CS-2 파생 데이터 파이프라인

| 설계 문서 | 모델 | Celery Task | 상태 | 비고 |
|----------|------|------------|------|------|
| `cs_21_tier_a_profile.md` (Growth+Capital) | `CompanyGrowthStage`, `CompanyCapitalDNA` | `profile_tasks.calculate_growth_stages`, `calculate_capital_dna`, `calculate_all_profiles` | **A** | 480 GS + 473 CD |
| `cs_21b_sensitivity_profile.md` | `CompanySensitivityProfile` | `sensitivity_tasks.calculate_sensitivity_profiles` | **A** | rate/forex/commodity/regulation/beta |
| `cs_21c_insider_signal.md` | `CompanyInsiderSignal` | `insider_tasks.calculate_insider_signals` | **A** | Finnhub Insider Transactions |
| `cs_22_co_mention.md` | `CoMentionEdge` | `relation_tasks.extract_co_mentions` | **A** | 90일 윈도우 |
| `cs_23_price_co_movement.md` | `PriceCoMovement` | `relation_tasks.calculate_price_co_movement` | **A** | 90일 rolling correlation |
| `cs_24_relation_confidence.md` + `relation_confidence_design_v1.md` (v2.1) | `RelationConfidence` (v2.1: truth/market score, evidence_tier, status 5단) | `relation_tasks.update_relation_confidence`, `check_stale_and_decay` | **A** | data_quality fix 후 PEER_OF(9,345) + CO_MENTIONED(193) + PRICE_CORRELATED(1,162) 분리 생성 |
| `cs_25_chain_profile_aggregation.md` | `CompanyChainProfile` | `sync_tasks.aggregate_chain_profiles` | **A** | validation CategorySignal까지 흡수 |
| (확장 모델) | `CompanyNarrativeTag`, `CompanyEventReaction`, `CompanyRevenueStructure` | — | **B** | 모델만 정의됨. **계산 태스크 미존재**. `aggregate_chain_profiles`에서 NarrativeTag는 읽지만 EventReaction/RevenueStructure는 미사용 |

### 2-4. CS-3 Neo4j 동기화 + GDS

| 설계 문서 | 코드 위치 | 상태 |
|----------|---------|------|
| `cs_31_profile_neo4j_sync.md` | `tasks/sync_tasks.sync_profiles_to_neo4j` + `migration 0008_unify_neo4j_flags` (neo4j_dirty 통일) | **A** |
| `cs_32_relation_neo4j_sync.md` | `tasks/sync_tasks.sync_relations_to_neo4j` (dirty sync 위임) + `services/neo4j_sync.sync_dirty_relations` + `tasks/neo4j_dirty_sync_tasks.run_neo4j_dirty_sync` | **A** | dirty 패턴 패턴화. data_quality_3_fixes 2B/2D에서 동적 관계 타입 지원 + market weak 허용 |
| `cs_33_gds_algorithms.md` | (PageRank/Louvain/Betweenness — 코드 위치 미확인, task_done CS-3-3 존재) | **A** | M3 마일스톤 보고 — 480 ranking row |

### 2-5. CS-4 REST API

| 설계 엔드포인트 | 코드 위치 | 상태 |
|---------------|---------|------|
| `GET /{symbol}/graph/` (CS-4-1) | `api/views.ChainSightGraphView` | **A** |
| `GET /{symbol}/suggestions/` (CS-4-2) | `api/views.ChainSightSuggestionView` | **A** |
| `GET /trace/` (CS-4-3) | `api/views.ChainSightTraceView` | **A** |

### 2-6. CS-5 프론트엔드 (구안 v2)

| 설계 문서 | 컴포넌트 | 상태 | 비고 |
|----------|---------|------|------|
| `cs_51_graph_visualization.md` | `GraphCanvas.tsx`, `NodeDetailPanel.tsx`, `RelationLegend.tsx` | **A** | react-force-graph-2d dynamic import |
| `cs_52_ai_guide_ui.md` | `AIGuidePanel.tsx`, `FilterPanel.tsx` | **A** | 카테고리 카드 필터링 |
| `cs_53_chain_trace_ui.md` | `TracePathView.tsx`, `FullPathView.tsx` | **A** | from/to → 경로 하이라이트 |
| `cs_54_stock_detail_integration.md` (종목 상세 미니 뷰 탭) | `GraphMiniView.tsx` (잔존 컴포넌트) | **D** | redesign UI/UX §11에서 **"탭 제거 → 딥링크 `/chainsight?focus={symbol}`로 변경"** 결정 |
| `cs_5_frontend_design_v2.md` (3-panel 워크스페이스) | `app/chainsight/[symbol]/page.tsx` (3-panel 유지) | **A** | redesign 이후 "deep dive workspace" 보조 화면으로 격하. 메인 진입 아님 |

### 2-7. redesign_v1_260409 (현행 메인 설계)

| 설계 문서 / PR | 백엔드 코드 | 프론트엔드 코드 | 상태 |
|--------------|------------|---------------|------|
| `chainsight_seed_node_design.md` (Phase 1 B+A 시드) | `services/seed_selection.py` (price/volume/sector_outlier/relation/comention) + `tasks/seed_tasks.run_seed_selection` | — | **A** |
| PR-1 schema migration | `migration 0005_add_neo4j_dirty_previous_status` (previous_status + neo4j_dirty) | — | **A** |
| PR-2 시드 선정 Task | `tasks/seed_tasks.py` + Beat 등록 | — | **A** |
| PR-3 Neo4j Dirty Sync | `services/neo4j_sync.py` + `tasks/neo4j_dirty_sync_tasks.py` + Beat (neo4j queue) | — | **A** |
| `chainsight_api_design.md` v2.1 PR-4: `GET /seeds/` | `api/views.SeedListView` + `_get_today_seeds()` (Redis → SeedSnapshot → async 복구 3단 폴백) + `migration 0007_seedsnapshot` | — | **A** |
| PR-4: `GET /sector/{sector}/graph/` | `api/views.SectorGraphView` | — | **A** |
| PR-4: `GET /{symbol}/neighbors/` | `api/views.NeighborGraphView` (display_type 파생 / cross_edges / 정렬 룰) | — | **A** |
| PR-4: `GET /signals/` | `api/views.SignalFeedView` + `_build_chain_signals` | — | **A** |
| `chainsight_ui_ux_design.md` v2.2 PR-5 (섹터 바 + 그래프 + 상태) | — | `lib/stores/explorationStore.ts`, `hooks/useMarketView.ts`, `SectorBar.tsx`, `MarketGraphCanvas.tsx`, `app/chainsight/page.tsx` | **A** |
| PR-6 (트레일 + 관계 카드) | — | `ExplorationTrail.tsx`, `RelationCardPanel.tsx`, `RelationFilterChips.tsx` | **A** |
| PR-7 (체인 스토리 피드) | — | `ChainStoryFeed.tsx` | **A** |

### 2-8. SavedPath / Trail (확장)

| 설계 문서 | 코드 | 상태 |
|----------|------|------|
| (별도 설계서 없음, `task_done/CS-3-1` 등에서 파생) | `models/saved_path.py` (`SavedPath`, `PathAction`) + `services/path_service.py`, `recheck_service.py`, `alternatives_service.py`, `expand_service.py` + `serializers/path_watchlist.py` + `views/watchlist_views.py` + `migration 0006_add_savedpath_pathaction` + `regenerate_summary_paths` 커맨드 | **A** | 설계서 외 확장 — 저장된 경로 + 재검토 + 대안 + 확장 후보 |

### 2-9. SEC Pipeline

| 설계 문서 | 코드 | 상태 |
|----------|------|------|
| `sec_pipeline_base_design.md` | `sec_pipeline/` 별도 앱 (CLAUDE.md 등록) | **A** |
| `sec_pipeline_pr_detail.md` | 동상 (8 모델, 110 관계, 5 BM Snapshot — `remaining_work_plan.md`) | **A** |

---

## 3. 미구현 항목 상세

### 3-1. Phase 2 — Heat Score

**상태**: **B (부분 구현)**

**구현된 것**:
- `tasks/seed_tasks.calculate_heat_scores()` — price/volume/relation_change/news_activation 4축 가중 평균. Neo4j `:Stock` 노드에 `heat_score` + 4개 component 속성 set.
- Beat 등록: `chainsight-heat-score-daily`.

**미구현된 것**:
1. **`SeedHeatScore` Django 모델 미생성** — 설계서 `chainsight_seed_node_design.md` §3.4에서 `stock/date/heat_score/components/seed_rank` 모델을 요구했으나 부재. PostgreSQL 영속화 없음 → 일간 추이 추적 불가.
2. **섹터 정렬 `heat_total DESC` 미반영** — `services/seed_selection.build_sector_summary`는 여전히 Phase 1 `seed_count DESC`. API 응답의 `sector_summary[].heat_total` 필드 부재 (UI/UX 설계 §6 정렬 기준 미적용).
3. **GDS centrality_delta 항목 미반영** — 설계서 §3.1의 6번째 가중치 (`gds_centrality_delta`)가 현 `HEAT_WEIGHTS`에 없음 (4축만 사용).
4. **`comention_surge` 시드 소스 코드** — `services/seed_selection.get_comention_surge_seeds` 존재하나 heat_score 4축에는 별도 미반영 (relation_change에 통합 추정 — 검증 필요).

### 3-2. Phase 3 — 이벤트 전파 모델 (D)

**상태**: **C (전체 미구현)**

| 단계 | 의존 | 상태 |
|------|------|------|
| D-1 text_conditional_prob (ChromaDB + Gemini Embedding) | ChromaDB 운영, Gemini Embedding API 통합 | **미진입** |
| D-2 lagged price correlation + volume_response + propagation_weight | D-1 + 60 거래일 데이터 | **미진입** |
| D-3 사후 검증 → 가중치 학습 | D-2 + 검증 레이블 | **미진입** |

뉴스 정량 변환 / 비대칭 전파 가중치 / 뉴스 이벤트 게이트(`norm_text < 0.05`) 등 설계서 §4.4 전체가 코드 부재.

### 3-3. neighbors API 2차 필드 확장

**상태**: **C (미구현)**

설계서 `chainsight_api_design.md` §4 2차 확장:
- `relation.relation_summary` (자연어 한 줄)
- `relation.why_now` (시드 사유 기반)
- `relation.insight_summary` (LLM 생성)

00_summary.md "범위 밖" 명시. 현재는 1차 템플릿 (display_type 기반 고정 문구 + seed_reasons + daily_return/volume_ratio) 만 프론트에서 합성 (UI/UX §9 §1차 템플릿).

### 3-4. LLM 기반 chain title/summary

**상태**: **C (미구현)**

`SignalFeedView._build_chain_signals`는 룰 기반 trigger_summary만 반환 (data_quality_3_fixes Issue 3: REASON_LABELS 한글 매핑). LLM 생성 chain title 부재. 00_summary "범위 밖" 명시.

### 3-5. 전환 애니메이션 + bounce

**상태**: **C (미구현)**

UI/UX 설계 §7 — 노드 클릭 시 좌측 translate + opacity 0.45 (300ms), 새 중심 ease-out 확대, 시드 bounce. 00_summary "범위 밖" 명시. 검증 필요 (`MarketGraphCanvas.tsx` 미정독).

### 3-6. 모바일 대응

**상태**: **C (마켓뷰 미적용)**

- `MobileCardList.tsx` 컴포넌트 잔존 (cs_5_v2 기반, deep dive workspace 용)
- 마켓뷰 메인 `/chainsight` 페이지의 모바일 카드 뷰 전환은 미구현. 00_summary "범위 밖" 명시.

### 3-7. 노드 비교 모드 / 메트릭 오버레이

**상태**: **C (미구현)**

cs_5_frontend_design_v2 §6-2/§6-3 — Ctrl+Click 두 노드 비교 + PER/ROE 테이블 + Centrality/Louvain 컬러링 토글. 해당 컴포넌트 (`NodeComparison.tsx` 등) 부재.

### 3-8. `/{symbol}/profile/` API

**상태**: **C (미구현)**

cs_5_frontend_design_v2 §8에서 "추가 필요 API" 명시 — `{ growth_stage, capital_dna, sensitivity, insider, business_model }` 단일 응답. 현재 `api/urls.py`에 routes 없음. 우측 패널 프로파일 요약은 `/graph/` 응답 내 center 메타로 일부 충당 추정.

### 3-9. 확장 모델 계산 태스크

**상태**: **B (모델만 존재)**

| 모델 | 정의 | 계산 태스크 | 사용처 |
|------|------|------------|--------|
| `CompanyNarrativeTag` | `models/narrative_tag.py` | **부재** | `sync_tasks.aggregate_chain_profiles`에서 read-only 흡수 |
| `CompanyEventReaction` | `models/event_reaction.py` | **부재** | 어디서도 사용 안 함 |
| `CompanyRevenueStructure` | `models/revenue_structure.py` | **부재** (CompanyChainProfile에 일부 컬럼 미러링) | aggregate에서도 미사용 |
| `ChainNewsEvent` | `models/news_event.py` | **부재** | 어디서도 사용 안 함 |

→ 향후 계산기 추가 또는 모델 정리 검토 필요.

---

## 4. 폐기 / 대체 항목

### 4-1. cs_54 종목 상세 Chain Sight 미니 탭 → **딥링크 대체**

- **구설계** (`cs_54_stock_detail_integration.md`, `cs_5_frontend_design_v2.md` §7): `/stocks/[symbol]` 페이지에 ChainSightMiniView (정적 1-depth 그래프 + 연결 종목 태그 + "전체 보기 →" CTA) 탭 추가.
- **신설계** (`redesign_v1_260409/chainsight_ui_ux_design.md` §11): **"`/stocks/[symbol]` → Chain Sight 탭 제거, 딥링크(`/chainsight?focus={symbol}`) 추가"**.
- **현 상태**:
  - 잔존 컴포넌트: `frontend/components/chainsight/GraphMiniView.tsx` (cs_54 산출물이 미삭제 상태)
  - 마켓 페이지 `app/chainsight/page.tsx`는 `?focus=` 쿼리 파라미터를 처리 (`initializeFocusExploration` 호출) — 신설계 진입로 적용 확인됨.
  - `/stocks/[symbol]` 페이지에서 GraphMiniView 임포트 여부 미확인 — **잔존 미사용 컴포넌트 가능성** (정리 검토 후보).

### 4-2. `/chainsight/[symbol]` 워크스페이스 = 메인 진입로 → **마켓 허브로 격하**

- **구설계** (`cs_5_frontend_design_v2.md`): 사용자가 종목을 알고 진입하는 **전용 워크스페이스**가 메인. 3-panel 분할.
- **신설계** (`redesign_v1_260409/chainsight_ui_ux_design.md` §1): `/chainsight` = **Market exploration hub** (Breadth-first), `/chainsight/[symbol]` = **Deep dive workspace** (Depth-first, "Deep dive" CTA에서만 진입).
- **현 상태**: 두 페이지 모두 존재. 메인 내비게이션에서 `/chainsight`가 디폴트 진입. `/chainsight/[symbol]` 워크스페이스 코드는 유지 (AIGuidePanel, NodeDetailPanel CTA 4종, FilterPanel, FullPathView 등).

### 4-3. `CUSTOMER_OF` DB 저장 → **API 파생만 (canonical 없음)**

- 의사결정: API 설계 §8에서 명시 — "`CUSTOMER_OF` DB 저장 없음. SUPPLIES_TO만 canonical, API에서 역방향 파생".
- **현 구현 일치**: `NeighborGraphView._display_type()` + `ChainSightGraphView`에서 `direction == 'outbound'`일 때 `derived_type = CUSTOMER_OF` 부여.
- v1.3 roadmap 변경 기록에 "CUSTOMER_OF 별도 저장 제거" 명시 — 의도된 폐기.

### 4-4. 섹터 정렬 v1 (`seed_count DESC`) → v2 (`heat_total DESC`) 전환

- 설계서 정의: Phase 1 `seed_count DESC`, Phase 2+ `heat_total DESC`.
- **현 상태**: Phase 2 미진입으로 인해 **여전히 Phase 1 `seed_count DESC` 사용** — 폐기 아닌 **점진적 전환 대기**. SeedHeatScore 모델 미생성과 직결.

### 4-5. `RELATED_TO` 엣지 라벨 → **동적 관계 타입 분리**

- 구현: `sync_relations_to_neo4j`가 모든 엣지를 `RELATED_TO`로 하드코딩 → Neo4j 그래프 의미 손실.
- 폐기 결정: `data_quality_3_fixes.md` Issue 2B — dirty sync 위임으로 동적 타입 (PEER_OF / CO_MENTIONED / PRICE_CORRELATED / SUPPLIES_TO / COMPETES_WITH) 분리.
- 마이그레이션: 1회성 레거시 RELATED_TO 정리 캐시 플래그로 멱등성 보장.

---

## 5. 부수 관찰

### 5-1. 신뢰도 / 데이터 무결성

- **Redis 휘발 방어** (`_get_today_seeds` 3단 폴백 Redis → SeedSnapshot → async 복구): 운영 안정성 측면 모범 사례. 버그 #27 (pytest가 운영 Redis flush) 대응책.
- **neo4j_dirty 통일** (migration 0008): `synced_to_neo4j` (RelationConfidence) / `neo4j_synced` (CompanyChainProfile) 양가 의미를 `neo4j_dirty` 단일 의미(반전)로 통일 — audit P0 #9 마이그레이션 패턴 모범.

### 5-2. 잔존 미사용 코드 가능성

- `GraphMiniView.tsx` — cs_54 폐기 이후 stocks/[symbol] 페이지에서 import 여부 미확인.
- `MobileCardList.tsx` — cs_5_v2 기반, deep dive workspace에서만 사용 추정.
- `CompanyEventReaction`, `ChainNewsEvent`, `CompanyRevenueStructure` — 모델만 정의, 계산 태스크 부재.

### 5-3. 문서 갱신 lag

- `chain_sight_roadmap_v1.3.md` 상태: "Phase 1 완료 (M1) — 다음 Phase 2 (CS-2-1~2-5)" — 그러나 실제로는 **Phase 2 CS-2-1~2-5 모두 완료** + redesign v1까지 진행됨. 로드맵 텍스트 갱신 필요 (M3 마일스톤 보고는 `remaining_work_plan.md`에 별도 기록).
- `remaining_work_plan.md` 작성일 2026-04-04 — redesign v1 (2026-04-09~13) 전 시점. CS-5 진입 순서가 redesign으로 대체된 점 미반영.

### 5-4. CS-5 frontend 코드 라우팅 분기

- `redesign_v1_260409`의 4개 마켓뷰 컴포넌트와 cs_5_v2의 deep dive workspace 컴포넌트가 **동일 디렉토리** (`frontend/components/chainsight/`)에 공존.
- 명시적 디렉토리 분리 없음 → 신규 진입자가 어느 컴포넌트가 어느 화면에 속하는지 식별 비용 발생.

---

## 6. 결론

- **백엔드는 거의 완전 구현**. CS-0~CS-3 + CS-4 + redesign v1 4개 API = 코드와 설계 정합도 ~95%.
- **프론트엔드는 두 설계가 공존**. redesign v1이 메인을 차지하고 cs_5_v2 deep dive workspace는 보조 화면으로 보존 — 의도된 양립.
- **Phase 2 진입의 핵심 누락**: `SeedHeatScore` 모델 미생성 → heat score 일간 추이 추적 불가, 섹터 정렬 v2 (`heat_total DESC`) 차단. heat 계산 자체는 Neo4j에 잘 저장되나, 영속화 + sector_summary API 응답 변경이 필요.
- **Phase 3 (이벤트 전파 D)**: 미진입. ChromaDB + Gemini Embedding + 60거래일 데이터 사전 조건 필요.
- **정리 후보**: `GraphMiniView.tsx` 사용 여부 확인 → 미사용이면 제거. `CompanyEventReaction`, `ChainNewsEvent` 모델 — 향후 6개월 내 미사용이면 마이그레이션으로 정리.
- **문서 갱신 필요**: `chain_sight_roadmap_v1.3.md` 진행 상태 텍스트 + `remaining_work_plan.md`에 redesign v1 결과 반영.
