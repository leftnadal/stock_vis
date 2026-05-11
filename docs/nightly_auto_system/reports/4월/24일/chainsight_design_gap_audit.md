# Chain Sight 설계 갭 감사

> **작성일**: 2026-04-24
> **감사 범위**: `docs/chain_sight/plan/` ↔ `chainsight/` (백엔드) + `frontend/components/chainsight/` + `frontend/app/chainsight/`
> **보조 참조**: `docs/chain_sight/task_done/` (과거 완료 기록), `docs/chain_sight/update_v2/` (파생 계획)
> **감사 방식**: 읽기 전용 (코드 수정 없음)

---

## 요약 (구현률)

| 구분 | 문서 수 | 완전 구현 (A) | 부분 구현 (B) | 미구현 (C) | 폐기/대체 (D) |
|------|--------:|--------------:|--------------:|-----------:|--------------:|
| 개발 로드맵 (`chain_sight_roadmap_v1.3.md`) | 1 | — | ★ 주축 | — | — |
| Phase 0 (CS-0-0 ~ CS-0-3) | 4 | 4 | 0 | 0 | 0 |
| Phase 1 (CS-1-1 ~ CS-1-3) | 3 | 3 | 0 | 0 | 0 |
| Phase 2 (CS-2-1 ~ CS-2-5) | 8 | 5 | 2 | 1 | 0 |
| Phase 3 (CS-3-1 ~ CS-3-3) | 3 | 2 | 0 | 1 | 0 |
| Phase 4 (CS-4-1 ~ CS-4-3) | 3 | 3 | 0 | 0 | 0 |
| Phase 5 (CS-5-1 ~ CS-5-4) | 4 | — | — | — | 4 (redesign_v1로 대체) |
| Phase 5 (cs_5_frontend_design_v2) | 1 | 0 | 1 | 0 | 1 (부분 대체) |
| Redesign v1 (`redesign_v1_260409/`) | 4 | 3 | 1 | 0 | 0 |

**총괄**:
- 백엔드 파이프라인은 Phase 0~4까지 **대부분 구현** (Phase 2 일부 Tier B 미흡, Phase 3의 GDS 배치 태스크 부재)
- 프론트엔드는 **redesign_v1_260409/가 cs_51~54를 사실상 대체**. 두 설계가 `/chainsight/[symbol]`(Deep dive)과 `/chainsight`(Market view)로 **공존**
- 문서화되지 않은 "Path Watchlist" 기능(`SavedPath`, `WatchlistViewSet`)이 존재하며, `docs/chain_sight/plan/`에 해당 설계서가 없음 → **`update_v2/` 또는 별도 문서 기반**

---

## 문서별 상태 테이블

### Phase 0: 인프라 기반

| 문서 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| `cs_00_legacy_cleanup_api_test.md` | **A 완전 구현** | `task_done/CS-0-0_legacy_cleanup_api_test.md` | serverless/ 레거시 제거 완료. frontend 탭도 `/chainsight?focus=` 딥링크로 변환. |
| `cs_01_migrations_verification.md` | **A 완전 구현** | `chainsight/migrations/0001_initial.py` ~ `0006_*.py` | 12개 테이블 존재 확인, RelationConfidence v2.1 스키마 반영. |
| `cs_02_neo4j_connection.md` | **A 완전 구현** | `chainsight/graph/repository.py` + `exceptions.py` | PID 기반 lazy driver 구조 적용. |
| `cs_03_neo4j_schema.md` | **A 완전 구현** | `chainsight/graph/schema.py`, `management/commands/init_neo4j_schema.py` | constraint/index 초기화 명령 구현. |

### Phase 1: 초기 데이터 로드

| 문서 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| `cs_11_stock_node_bulk_load.md` | **A 완전 구현** | `management/commands/load_stocks_to_neo4j.py` | |
| `cs_12_sector_industry.md` | **A 완전 구현** | `management/commands/load_sectors_to_neo4j.py` | |
| `cs_13_peer_relations.md` | **A 완전 구현** | `chainsight/tasks/peer_tasks.py` (`fetch_and_load_peers`) | Finnhub + FMP peer 수집 태스크. |

### Phase 2: 파생 데이터 계산

| 문서 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| `cs_21_tier_a_profile.md` (GrowthStage, CapitalDNA) | **A 완전 구현** | `chainsight/tasks/profile_tasks.py` (`calculate_growth_stages`, `calculate_capital_dna`) | |
| `cs_21b_sensitivity_profile.md` | **A 완전 구현** | `chainsight/tasks/sensitivity_tasks.py` | FMP Revenue Geographic + Beta 기반. |
| `cs_21c_insider_signal.md` | **B 부분 구현** | `chainsight/tasks/insider_tasks.py` | Finnhub Insider Transactions 수집 완료. `FMP Institutional Holders`, `short_interest`, `smart_money_signal` 종합 계산은 코드에서 확인 필요. |
| `cs_22_co_mention.md` | **A 완전 구현** | `chainsight/tasks/relation_tasks.py::extract_co_mentions` | ChainNewsEvent 중간저장 + normalize_pair 정규화 반영. |
| `cs_23_price_co_movement.md` | **A 완전 구현** | `chainsight/tasks/relation_tasks.py::calculate_price_co_movement` | PEER_OF 쌍 기반 90일 correlation. |
| `cs_24_relation_confidence.md` / `relation_confidence_design_v1.md` | **B 부분 구현** | `chainsight/tasks/relation_tasks.py::update_relation_confidence`, `check_stale_and_decay` + `models/relation_discovery.py` | v2.1 스키마 필드 전부 존재. **누락**: evidence_tier 판정에서 `relation_basis_summary` 템플릿 부분 적용(간소화), `investment_relevance`는 항상 null, `has_etf_source`/`has_llm_source`는 모든 분기에서 미설정. LLM 기반 평가 태스크 부재. |
| `cs_25_chain_profile_aggregation.md` | **A 완전 구현** | `chainsight/tasks/sync_tasks.py::aggregate_chain_profiles` | validation/CategorySignal 연계 포함. |

### Phase 3: Neo4j 동기화 + GDS

| 문서 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| `cs_31_profile_neo4j_sync.md` | **A 완전 구현** | `chainsight/tasks/sync_tasks.py::sync_profiles_to_neo4j` | Delta sync (neo4j_synced=False). |
| `cs_32_relation_neo4j_sync.md` | **A 완전 구현** | `chainsight/services/neo4j_sync.py` + `sync_tasks.py::sync_relations_to_neo4j` | **`neo4j_dirty` 플래그 패턴으로 개선**된 상태. 레거시 `RELATED_TO` 엣지 1회 정리 로직 포함. Market weak 관계도 동기화 허용(설계서와 일치). |
| `cs_33_gds_algorithms.md` | **C 미구현 (현행 코드)** | `chainsight/tasks/gds_tasks.py` **파일 없음** | 과거 `task_done/CS-3-3_gds_algorithms.md`에서 PageRank/Louvain/Betweenness 수동 실행 기록은 있으나, **자동화된 Celery 태스크가 코드베이스에 존재하지 않음**. `path_service.py`는 centrality 데이터가 없을 때의 fallback weight를 갖고 있음 → 데이터 재실행 방법 명시되지 않음. |

### Phase 4: API 엔드포인트

| 문서 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| `cs_41_graph_api.md` | **A 완전 구현** | `chainsight/api/views.py::ChainSightGraphView` | CUSTOMER_OF 역방향 파생, market_signals 보강 모두 반영. |
| `cs_42_suggestion_api.md` | **A 완전 구현** | `chainsight/api/views.py::ChainSightSuggestionView` | peers/same_industry/co_mentioned/same_sector 4종 카테고리. |
| `cs_43_trace_api.md` | **A 완전 구현** | `chainsight/api/views.py::ChainSightTraceView` | shortestPath 기반. |

### Phase 5 (원안 cs_51~54): 프론트엔드

| 문서 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| `cs_51_graph_visualization.md` | **D 폐기/대체** | — | redesign_v1_260409/ 및 `cs_5_frontend_design_v2.md`로 대체. |
| `cs_52_ai_guide_ui.md` | **D 폐기/대체** | — | 동상. |
| `cs_53_chain_trace_ui.md` | **D 폐기/대체** | — | 동상. |
| `cs_54_stock_detail_integration.md` | **D 폐기/대체** | — | 동상. `/chainsight?focus=` 딥링크로 재정의됨. |

### Phase 5 (중간안 cs_5_frontend_design_v2.md)

| 항목 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| 3-panel 워크스페이스 (`/chainsight/[symbol]`) | **B 부분 구현** | `frontend/app/chainsight/[symbol]/page.tsx` + `GraphCanvas/AIGuidePanel/NodeDetailPanel/FilterPanel/MobileCardList/RelationLegend/TracePathView` | 좌/중/우 3-panel 레이아웃 존재. |
| 엣지 색상 체계 (6색 + 스타일) | **B 부분 구현** | `graphStyles.ts`, `MarketGraphCanvas.tsx::EDGE_COLORS` | 마켓 뷰 쪽은 redesign_v1 5색으로 덮어씀. Deep dive 쪽(`GraphCanvas.tsx`)은 `getRelationStyle` 유지. |
| CTA 체계 (가설 생성/Watchlist/Validation/여기서 탐색/경로 찾기) | **B 부분 구현** | `NodeDetailPanel.tsx` | CTA 존재 여부는 파일 존재로 확인. 세부 항목별 검증은 별도 리뷰 필요. |
| 프로 기능 (필터 패널, PER 히트맵, Centrality 오버레이, 노드 비교) | **B 부분 구현** | `FilterPanel.tsx` | 필터 패널은 존재. **PER 히트맵/Centrality 오버레이/Ctrl+Click 비교 모드는 파일·로직 미확인**. |
| 종목 상세 미니 뷰 (CS-5-4 재정의) | **A 완전 구현** | `GraphMiniView.tsx`, `frontend/app/stocks/[symbol]/page.tsx:58` | Chain Sight 탭 → "전체 탐색 →" 링크 + 미니 뷰. `focus=` 딥링크 연결. |
| 모바일 카드 리스트 | **B 부분 구현** | `MobileCardList.tsx` | 컴포넌트는 존재. Deep dive 워크스페이스에서만 사용. 마켓 뷰는 모바일 대응 없음(PR-7 설계서의 "future" 범위). |

### Redesign v1 (마켓 뷰)

| 문서 | 상태 | 코드 위치 | 비고 |
|------|------|----------|------|
| `chainsight_seed_node_design.md` | **B 부분 구현 (Phase 1만)** | `chainsight/services/seed_selection.py`, `chainsight/tasks/seed_tasks.py` | Phase 1 (B+A: 시장 시그널 + 관계 변화)만 구현. **Phase 2 Heat Score(SeedHeatScore 모델/태스크) 미구현**, Phase 3 이벤트 전파 미구현 → 설계서에 "Phase 발전 경로"로 예고된 범위. |
| `chainsight_api_design.md` (4개 엔드포인트) | **A 완전 구현** | `chainsight/api/views.py::SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView` + `api/urls.py` | 응답 형식, 캐싱 키(TTL 30분/1시간/30분/1시간), SUPPLIES_TO→CUSTOMER_OF 파생, `truth_score`/`market_score`/`status` 노출 모두 일치. `relation_basis_summary`/`why_now`/`insight_summary` 2차 필드는 설계서도 "향후"로 예고. |
| `chainsight_ui_ux_design.md` (5구역 마켓 뷰) | **A 완전 구현** | `frontend/app/chainsight/page.tsx` + `SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed` | ①~⑤ 5개 구역 모두 구현. pre-focus/focused 분기, `?focus=` 딥링크, undo (`initializeFocusExploration`), chain 카드 클릭 시 세션 리셋 모두 확인. |
| `chainsight_marketview_pr_prompts.md` (PR-1~7) | **A 완전 구현** | `task_done/chain_sight_redesign_V1/00_summary.md` | 7개 PR 전부 완료 보고. |

### 문서에 없고 코드에만 존재 (Undocumented Implementations)

| 항목 | 코드 위치 | 상태 | 비고 |
|------|----------|------|------|
| Path Watchlist (`SavedPath`, `PathAction`) | `chainsight/models/saved_path.py`, `chainsight/views/watchlist_views.py`, `chainsight/serializers/path_watchlist.py` | **문서 누락** | `docs/chain_sight/plan/`에 설계서 없음. `docs/chain_sight/update_v2/task_done/`의 CS-6-1/CS-7-* 시리즈에서 별도 설계. 이 감사의 범위 밖이나 **plan/ 스코프에는 명시되지 않은 기능**. |
| Path Watchlist 프론트엔드 (`/chainsight/watchlist`, `PathCard`, `WatchButton`, `FullPathView`) | `frontend/app/chainsight/watchlist/`, `components/chainsight/{PathCard,WatchButton,FullPathView}.tsx` | **문서 누락** | 동상. |
| `update_relation_confidence`에서 `COMPETES_WITH`, `HAS_THEME`, `SUPPLIES_TO`, `HELD_BY_SAME_FUND` 관계 생성 | `chainsight/tasks/relation_tasks.py` | **설계 있음, 구현 일부 누락** | 모델 choices에는 있으나 현재 태스크는 PEER_OF/CO_MENTIONED/PRICE_CORRELATED 3종만 생성. 나머지 타입은 v1.3 로드맵에 언급되나 (DC-3/DC-4/ETF/LLM) 코드에서 자동 판정 로직 부재. |

---

## 미구현 항목 상세

### C-1. CS-3-3 GDS 자동화 태스크 부재

**설계**: `cs_33_gds_algorithms.md` — `chainsight/tasks/gds_tasks.py`에 `run_gds_algorithms` Celery 태스크로 PageRank / Louvain / Betweenness 주기 실행.

**현행**:
- `chainsight/tasks/` 디렉토리에 `gds_tasks.py` 파일 없음.
- Celery Beat에 GDS 스케줄 없음 (`task_done/chain_sight_redesign_V1/data_quality_3_fixes.md`의 Beat 타임라인에도 없음).
- 과거 `task_done/CS-3-3_gds_algorithms.md`에서 1회 수동 실행 기록만 존재 (2026-04-03).
- `chainsight/services/path_service.py`는 centrality 데이터 부재 시 fallback weight를 적용하므로 런타임 장애는 없음.

**영향**:
- `:Stock.pagerank_score` / `community_id` / `betweenness_score`가 오래되어 경로 스코어링 품질 저하 가능.
- Deep dive 워크스페이스의 "Centrality 오버레이" 프로 기능이 동작할 데이터 근거 취약.

### C-2. CS-2-4 관계 판정의 LLM/ETF 소스 미반영

**설계**: `relation_confidence_design_v1.md` 및 v1.3 로드맵 — `evidence_sources`에 LLM/ETF 증거 tier 평가 포함, `has_llm_source`/`has_etf_source` 플래그 설정.

**현행**: `update_relation_confidence` 태스크는 세 소스(peer, industry, co-mention, price)만 처리. `has_llm_source`, `has_etf_source`는 항상 False. `investment_relevance`도 상시 null.

**영향**:
- DC-2 (ETF Holdings → HAS_THEME)와 DC-4 (Gemini Flash → SUPPLIES_TO 확장) 파이프라인 부재로 정합.
- 설계서에서 향후 실행하기로 한 단계이므로 **설계적으론 예정된 gap**. 구현 상태 표기는 필요.

### C-3. SeedHeatScore (Phase 2 heat score) 미구현

**설계**: `chainsight_seed_node_design.md` §3 — `SeedHeatScore` 모델 + `chainsight-heat-score` Celery Beat (매일 11:30) + 섹터 정렬을 `heat_total DESC`로 변경.

**현행**:
- `SeedHeatScore` 모델 부재 (`chainsight/models/`에 파일 없음).
- `get_sector_summary` 정렬은 Phase 1 스펙대로 `seed_count DESC` 유지.
- 설계서 자체가 "Phase 1 → Phase 2 → Phase 3" 단계적 전개를 명시하므로 **예정된 gap**.

### C-4. Phase 3 이벤트 전파 모델 (D 단계) 미구현

**설계**: `chainsight_seed_node_design.md` §4 — `text_conditional_prob` + lagged correlation + propagation_weight → 뉴스→주가 전파 가중치.

**현행**: 해당 태스크/모델/ChromaDB 연동 코드 없음. 설계서에도 "D-1~D-3 단계" 로드맵 형태로만 기재 → **예정된 gap**.

### C-5. 2차 카드 설명 (`relation_summary`, `why_now`, `insight_summary`) 부재

**설계**: `chainsight_api_design.md` §4 "2차 필드 확장 (향후)".

**현행**: `NeighborGraphView` 응답에 해당 키 없음. 프론트는 `display_type` + `seed_reasons` 기반 템플릿 문구만 사용. 설계서가 명시적으로 "추후" 범위로 구분 → **예정된 gap**.

### C-6. 종목 상세 Chain Sight 탭의 "미니 그래프" 완전 구현 여부 검증 필요

**설계**: `cs_5_frontend_design_v2.md` §7 — 정적 스냅샷(interaction 없음), "전체 탐색" 링크.

**현행**: `GraphMiniView.tsx`가 존재하고 `ChainSightMiniView` 동적 import로 사용됨. 내부 동작(cooldownTicks=80 이후 freeze, 노드 탭 → 종목 상세 이동) 여부는 본 감사에서 상세 확인하지 않음 → **검증 필요**.

### C-7. 프로 기능 중 PER 히트맵 / Centrality 오버레이 / 노드 비교 모드

**설계**: `cs_5_frontend_design_v2.md` §6-2, §6-3 — 노드 메트릭 오버레이 드롭다운 + Ctrl+Click 비교.

**현행**: Deep dive 워크스페이스에 `FilterPanel` 컴포넌트는 존재. 오버레이 토글(PER/Centrality/Louvain 컬러)과 비교 모드 UI는 확인되지 않음 → **미구현 추정**. C-1(GDS 데이터 부재)과도 연결.

---

## 폐기/대체 항목

### D-1. `cs_51_graph_visualization.md` → `cs_5_frontend_design_v2.md` + `redesign_v1_260409/chainsight_ui_ux_design.md`

**이유**:
- cs_51 원안은 "종목 상세 탭 내 인터랙티브 그래프"였으나, v2에서 "전용 워크스페이스 `/chainsight/[symbol]`"로 방향 전환.
- 이어 redesign_v1에서 마켓 뷰(`/chainsight`)를 추가, 탐색 허브와 deep dive를 분리.

**반영**: 두 라우트 모두 프론트에 존재. 종목 상세 탭은 미니 뷰 + 딥링크로 축소.

### D-2. `cs_52_ai_guide_ui.md` → 좌측 패널 `AIGuidePanel.tsx` + redesign_v1의 `RelationCardPanel`

**이유**: Deep dive는 좌측 `AIGuidePanel`로, 마켓 뷰는 중앙 하단 `RelationCardPanel`(대표 시드 카드 / 관계 카드)로 역할 분리.

### D-3. `cs_53_chain_trace_ui.md` → Deep dive 워크스페이스 내부 + 마켓 뷰에서 제외

**이유**: redesign_v1 설계서 §1 "Deep dive workspace API (별도)"에서 `/trace/`를 Deep dive 전용으로 명시. 마켓 뷰의 트레일(③ ExplorationTrail)은 navigation log로 역할 축소.

### D-4. `cs_54_stock_detail_integration.md` → `/chainsight?focus={symbol}` 딥링크 + 미니 뷰

**이유**: `cs_5_frontend_design_v2.md`에서 "종목 상세 탭 = 미니 그래프(정적) + 연결 종목 태그 + '전체 탐색' CTA"로 재정의. 이후 redesign v2.2의 `chainsight_ui_ux_design.md` §11에서 "Chain Sight 탭 제거, 딥링크(`?focus=`) 추가"로 재정의. 코드는 둘 다 지원(탭 내 미니뷰 + focus 딥링크 공존).

### D-5. `CUSTOMER_OF` 별도 저장 제거 (v1.3 의사결정)

**적용**: `sync_relations_to_neo4j` / `neo4j_sync.py`에서 SUPPLIES_TO만 저장, API에서 `direction=outbound`일 때 `display_type='CUSTOMER_OF'` 파생. 설계-구현 일치.

### D-6. `sync_relations_to_neo4j` 레거시 RELATED_TO 엣지 라벨

**이유**: 초기 구현이 모든 관계를 `[:RELATED_TO]`로 저장 → 타입 기반 쿼리 불가.

**반영**: `data_quality_3_fixes.md` Issue 2B에서 동적 타입으로 전환. 현행 `sync_tasks.py`는 1회성 cleanup 후 `sync_dirty_relations()`에 위임.

### D-7. 프론트엔드 마켓 뷰 관계 카드 모바일 대응

**이유**: redesign_v1 `chainsight_ui_ux_design.md` §13 — "현재 데스크톱 우선. 장기적으로 card-first 탐색 UI 가능". `cs_5_frontend_design_v2.md`의 모바일 카드 리스트는 deep dive 전용으로 유지.

---

## 교차 참조 확인 (redesign_v1 vs cs_*)

### "redesign_v1_260409/가 기존 cs_* 문서를 대체하는가?"

**결론**: **부분 대체**.

- redesign_v1은 **Phase 5 프론트엔드 + 마켓 뷰 API 재설계**가 핵심.
- cs_00 ~ cs_43 (Phase 0~4 백엔드 파이프라인)은 **여전히 유효**. redesign_v1 설계서는 Layer 3 (chainsight/) 모델 계층과 `/graph/`/`/suggestions/`/`/trace/` API를 "Deep dive" 전용으로 **유지**한다고 명시 (§1).
- cs_51~54 (원안 Phase 5)는 cs_5_frontend_design_v2.md 경유하여 redesign_v1로 완전 대체.
- 따라서 plan/ 디렉토리에 cs_* 문서가 남아있는 것은 **백엔드 계약 문서로서 여전히 유효한 참조**. 프론트 부분만 폐기됨.

### Redesign v2.1/v2.2 내부 일관성

- `chainsight_api_design.md` v2.1 (2026-04-10) + `chainsight_ui_ux_design.md` v2.2 (2026-04-10) + `chainsight_seed_node_design.md` v2.1 (2026-04-10) 모두 같은 날짜의 FINAL.
- `chainsight_marketview_pr_prompts.md`의 PR-1~7 분할과 `task_done/chain_sight_redesign_V1/`의 7개 PR 완료 파일이 1:1 대응 → **일관성 확보**.

### 남은 "업데이트 계획" (plan/ 밖)

- `docs/chain_sight/update_v2/ROADMAP_v1.4.md`: 본 감사의 직접 범위 밖이지만 `CS-4-4_heat_score`, `CS-5-5_market_view`, `CS-5-6_seed_node`, `cs_71_72_73_phase7_frontend` 같은 확장 계획이 별도로 관리됨. `SavedPath`/Path Watchlist의 설계서는 여기에 있을 가능성이 높음. plan/ 안에는 없음이 확인됨.

---

## 권고 (감사 결과 기반 관찰)

> 이 절은 의사결정용 관찰 사항만. 코드 변경 권고가 아님.

1. **GDS 자동화 부재(C-1)**가 가장 실무적 리스크. 수동 실행 이후 데이터 freshness가 유지되지 않음. `chainsight/tasks/gds_tasks.py` 부재를 plan/에 별도 기록하거나 `update_v2/`로 이관 여부 확정 필요.
2. **Path Watchlist 기능의 설계서가 `docs/chain_sight/plan/`에 없음**. `update_v2/`에 모든 설계가 몰려있으므로, `chain_sight/plan/README.md` 또는 로드맵 문서에서 "이후 설계는 update_v2/에서 관리" 주석 필요.
3. **관계 생성 태스크가 3종만 커버** (PEER_OF/CO_MENTIONED/PRICE_CORRELATED). 모델은 7종 choices를 열었으나 `COMPETES_WITH`, `SUPPLIES_TO`, `HAS_THEME`, `HELD_BY_SAME_FUND` 자동 생성 파이프라인 부재 — DC-2~DC-4 계획과 정합하지만, 프론트 `RelationCardPanel`이 Competitors 그룹을 렌더하므로 **현재 데이터로는 빈 그룹이 출력될 수 있음**.
4. **cs_5_frontend_design_v2.md와 redesign_v1이 서로 다른 라우트(`/chainsight/[symbol]` vs `/chainsight`)에서 공존**. 한 명세로 통합하거나 "Deep dive vs Market view" 이중 구조를 공식적으로 문서화 필요.

---

## 참조 파일

**설계서**:
- `docs/chain_sight/plan/chain_sight_roadmap_v1.3.md`
- `docs/chain_sight/plan/relation_confidence_design_v1.md`
- `docs/chain_sight/plan/cs_00` ~ `cs_54` (26개)
- `docs/chain_sight/plan/cs_5_frontend_design_v2.md`
- `docs/chain_sight/plan/redesign_v1_260409/*.md` (4개)

**구현**:
- 백엔드: `chainsight/models/` (12 모델 + SavedPath/PathAction), `chainsight/services/` (7 파일), `chainsight/tasks/` (8 파일), `chainsight/api/views.py` (7 뷰), `chainsight/graph/` (repository/schema/exceptions)
- 프론트엔드: `frontend/app/chainsight/page.tsx` (마켓 뷰), `frontend/app/chainsight/[symbol]/page.tsx` (Deep dive), `frontend/app/chainsight/watchlist/` (Path Watchlist), `frontend/components/chainsight/` (16 컴포넌트)

**완료 보고서**:
- `docs/chain_sight/task_done/` (18개 CS-* 파일)
- `docs/chain_sight/task_done/chain_sight_redesign_V1/` (PR-1~7, 00_summary, data_quality_3_fixes, browser_test_report, qa_evaluator_review_01)

**END OF DOCUMENT**
