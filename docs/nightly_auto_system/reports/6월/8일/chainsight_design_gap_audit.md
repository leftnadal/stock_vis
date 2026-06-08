# Chain Sight 설계 갭 감사

> 감사일: 2026-06-08 | 유형: 읽기 전용 (코드 미수정) | 방법: 설계 문서 ↔ 코드 직접 대조 + task_done cross-reference

## 0. 사전 정정 — 경로 변경 (서비스 리모델링)

지시서의 `chainsight/` 경로는 **존재하지 않음**. "서비스 리모델링"으로 모노레포 구조 개편이 일어나 실제 코드는 아래로 이동됨:

| 지시서 경로 | 실제 경로 |
|------------|----------|
| `chainsight/` (백엔드) | **`apps/chain_sight/`** |
| `chainsight/` (프론트 컴포넌트) | **`frontend/components/chainsight/`** (변동 없음) |
| 프론트 라우트 | **`frontend/app/chainsight/`** (변동 없음) |

> 그 외 다른 백엔드 앱도 이동됨: `stocks/`→`packages/shared/stocks/`, `news/`→`services/news/`, `serverless/`→`services/serverless/`, `validation/`→`services/validation/`, `sec_pipeline/`→`services/sec_pipeline/`. 이는 이번 감사 범위 밖이나 CLAUDE.md의 앱 경로 표가 stale함을 시사.

---

## 1. 요약 (구현률)

| Phase | 설계 문서 수 | A 완전 | B 부분 | C 미구현 | D 폐기 | 구현률(가중) |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| Phase 0 인프라/Neo4j | 4 | 3 | 1 | 0 | 0 | ~95% |
| Phase 1 그래프 데이터 적재 | 3 | 3 | 0 | 0 | 0 | 100% |
| Phase 2 프로파일/관계 | 8 | 5 | 3 | 0 | 0 | ~75% |
| Phase 3 Neo4j Sync/GDS | 3 | 0 | 2 | 1 | 0 | ~55% |
| Phase 4 REST API | 3 | 1 | 2 | 0 | 0 | ~75% |
| Phase 5 프론트엔드 | 5 | 5 | 0 | 0 | 0 | ~90% |
| redesign_v1 (마켓뷰) | 4 설계 / 7 PR | 6 PR | 1 PR | 0 | 0 | ~95% |
| **종합** | **30** | — | — | — | — | **~85%** |

**핵심 결론**:
- **백본(인프라·데이터 적재·프로파일 계산·프론트엔드·마켓뷰)은 거의 완전 구현** — MVP 동작 수준 달성.
- **관계 추론 정밀도(Phase 2 RelationConfidence Tier 시스템)와 그래프 분석(Phase 3 GDS 배치)이 최대 갭**.
- **redesign_v1은 기존 cs_*를 폐기하지 않음** — "마켓뷰" 신규 레이어를 추가한 **병행 구조**. 두 API 세트가 `api/urls.py`에 공존(검증 완료).

---

## 2. 문서별 상태 테이블

### Phase 0 — 인프라 / Neo4j

| 설계 문서 | 분류 | 근거 (코드 위치) | 갭 |
|----------|:---:|------|----|
| cs_00_legacy_cleanup_api_test | **A** | `apps/chain_sight/utils.py:normalize_pair`, `models/relation_discovery.py:RelationConfidence` v2.1 (truth_score/market_score/neo4j_dirty 등 전 필드) | — |
| cs_01_migrations_verification | **A** | `migrations/0001~0008`, `models/chain_profile.py` neo4j_dirty+synced_at | — |
| cs_02_neo4j_connection | **B** | `graph/repository.py:Neo4jGraphRepository` (PID lazy init), `graph/__init__.py:get_graph_repository`, settings NEO4J_* | **GraphRepository Protocol 정의 불완전**: `bulk_upsert_nodes/edges`, `health_check`, `node_count`, `edge_count` 5개가 구현체엔 있으나 Protocol 선언엔 누락 (타입 안전성 이슈, 런타임 정상) |
| cs_03_neo4j_schema | **A** | `graph/schema.py` CONSTRAINTS 4 + INDEXES 2, `management/commands/init_neo4j_schema.py` (--verify/--check/--reset) | — |

### Phase 1 — 그래프 데이터 적재

| 설계 문서 | 분류 | 근거 | 갭 |
|----------|:---:|------|----|
| cs_11_stock_node_bulk_load | **A** | `services/neo4j_loader.py:load_stocks_to_neo4j` (STOCK_FIELD_MAP, batch=100), `commands/load_stocks_to_neo4j.py` | — |
| cs_12_sector_industry | **A** | `neo4j_loader.py:load_sectors_to_neo4j` (Sector/Industry MERGE + BELONGS_TO 관계) | — |
| cs_13_peer_relations | **A** | `neo4j_loader.py:collect_all_peers/load_peers_to_neo4j` (Finnhub+FMP, PEER_OF UNWIND 배치) | — |

### Phase 2 — 프로파일 / 관계 추출

| 설계 문서 | 분류 | 근거 | 갭 |
|----------|:---:|------|----|
| cs_21_tier_a_profile | **A** | `models/growth_stage.py`, `capital_dna.py` + `tasks/profile_tasks.py` (전 필드, Beat 등록) | — |
| cs_21b_sensitivity_profile | **A** | `models/sensitivity.py` + `tasks/sensitivity_tasks.py` (금리/환율/시장/규제 민감도 분류 규칙 전부) | — |
| cs_21c_insider_signal | **B** | `models/insider_signal.py` + `tasks/insider_tasks.py` (Finnhub insider, 90일 필터, insider_signal 분류) | **institutional_ownership_pct / short_interest_pct 데이터 소스 없음** (별도 API 미연결) → smart_money_signal 종합 계산 제한 (insider만 반영) |
| cs_22_co_mention | **A** | `models/news_event.py:ChainNewsEvent`, `relation_discovery.py:CoMentionEdge` + `tasks/relation_tasks.py:extract_co_mentions` | — |
| cs_23_price_co_movement | **A** | `relation_discovery.py:PriceCoMovement` + `relation_tasks.py:calculate_price_co_movement` (90일 rolling corr) | — |
| cs_24_relation_confidence | **B** | `relation_discovery.py:RelationConfidence` (전 필드), `relation_tasks.py:update_relation_confidence/check_stale_and_decay` | **Tier 증거 체계 대부분 미수집**, **SUPPLIES_TO/COMPETES_WITH/HAS_THEME/HELD_BY_SAME_FUND 관계 판정 미구현** (PEER_OF/CO_MENTIONED/PRICE_CORRELATED만), 상향 전이 로직 없음(하향 decay만), investment_relevance 미계산, has_supply_chain/etf/llm_source 플래그 미설정 |
| cs_25_chain_profile_aggregation | **A** | `models/chain_profile.py` + `tasks/sync_tasks.py:aggregate_chain_profiles` (profile_completeness 자동 계산) | — |
| relation_confidence_design_v1 (정책서) | **B** | 5단계 status·truth/market 분리·relation_basis_summary 구현 | **Tier 1/2/3 정책표 전체 미구현**, 상향 전이 규칙 미구현, 다중 관계 타입 대부분 미구현, 점수 맵핑이 설계(Tier별 고정점)와 불일치(count/corr 기반) |

### Phase 3 — Neo4j Sync / GDS

| 설계 문서 | 분류 | 근거 | 갭 |
|----------|:---:|------|----|
| cs_31_profile_neo4j_sync | **B** | `tasks/sync_tasks.py:sync_profiles_to_neo4j` (neo4j_dirty 필터, 503/503) | 설계의 `_profile_to_neo4j_props()` 헬퍼 없이 직접 dict 구성 (기능 동치), 플래그 의미 반전(audit P0 #9: synced→dirty) — **문서 미갱신** |
| cs_32_relation_neo4j_sync | **B** | `sync_tasks.py:sync_relations_to_neo4j` + `services/neo4j_sync.py:sync_dirty_relations` | 설계는 고정 RELATED_TO 엣지, 구현은 **동적 타입(PEER_OF 등) + RELATED_TO 1회 정리**로 진화 — 설계 문서 미갱신. CUSTOMER_OF 역방향은 API 파생(설계와 일치) |
| cs_33_gds_algorithms | **C** | — (tasks/ 내 GDS/PageRank/Louvain/Betweenness 매치 **0건**, config/celery.py에 GDS Beat 미등록) | **Celery GDS 배치 태스크 부재**. 속성(pagerank_score/betweenness_score/community_id)은 `path_service.py`가 조회·사용하나 **1회 수동 Neo4j 실행으로만 계산**됨. 자동 재계산 파이프라인 없음 |

### Phase 4 — REST API

| 설계 문서 | 분류 | 근거 (`api/views.py` + `api/urls.py` 검증 완료) | 갭 |
|----------|:---:|------|----|
| cs_41_graph_api | **A** | `ChainSightGraphView` → `GET /<symbol>/graph/` (center/nodes/edges/meta, CUSTOMER_OF 파생, market_signals) | — |
| cs_42_suggestion_api | **B** | `ChainSightSuggestionView` → `GET /<symbol>/suggestions/` (PEER_OF, CO_MENTIONED, 같은 섹터 범주) | **누락 범주**: COMPETES_WITH 쿼리, SUPPLIES_TO 양방향, community_id 클러스터 매칭 |
| cs_43_trace_api | **B** | `ChainSightTraceView` → `GET /trace/` | **HTTP 메서드**: 완료보고서는 POST 명시했으나 구현은 GET만. **응답 필드 `alternative_paths` 누락**, path 각 스텝 basis_summary는 edge props에만 존재 |

### Phase 5 — 프론트엔드 (cs_5 계열)

| 설계 문서 | 분류 | 근거 | 갭 |
|----------|:---:|------|----|
| cs_5_frontend_design_v2 | **A** | `/chainsight/[symbol]` 3-panel 워크스페이스, 관계 6색 체계 정확 일치(`graphStyles.ts`), CTA, 모바일 카드, 필터 패널 | (Advanced 범위) 노드 메트릭 오버레이·노드 비교 모드 미구현 — v2 "Advanced" 섹션이라 MVP 외 |
| cs_51_graph_visualization | **A** | `GraphCanvas.tsx` (ForceGraph2D, Spotlight, Lazy expansion, 섹터 11색) | — |
| cs_52_ai_guide_ui | **A** | `AIGuidePanel.tsx` (카테고리 카드 + 그래프 필터링 + strength dots) | — |
| cs_53_chain_trace_ui | **A** | `TracePathView.tsx` (경로 시각화 + 단계 설명 + 경로 없음 안내) | — |
| cs_54_stock_detail_integration | **A** | `GraphMiniView.tsx` (360px 정적 미니그래프), 종목 상세 탭 + "전체 탐색" CTA | — |

### redesign_v1_260409 (마켓뷰 PR-1~7)

| PR | 분류 | 근거 | 갭 |
|----|:---:|------|----|
| PR-1 스키마 마이그레이션 | **A** | `migrations/0005~0008`, `models/saved_path.py`, `seed_snapshot.py`, RelationConfidence.previous_status/neo4j_dirty | — |
| PR-2 시드 선정 Task | **A** | `services/seed_selection.py` (price/volume/sector_outlier/relation_change/comention_surge 5종), `tasks/seed_tasks.py`, Beat 등록, Redis 캐시 | — |
| PR-3 Neo4j Dirty Sync | **B** | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py`, Beat 등록 | `sync_dirty_relations` 상세 동작 정상이나 (cs_24 Tier 미구현과 연동되어) 동기화 대상 관계 타입이 설계보다 좁음 |
| PR-4 마켓뷰 API 4종 | **A** | `SeedListView`/`SectorGraphView`/`NeighborGraphView`/`SignalFeedView` → `seeds/`, `sector/<sector>/graph/`, `<symbol>/neighbors/`, `signals/` (urls.py 검증) | — |
| PR-5 FE 탐색상태+섹터바+그래프 | **A** | `lib/stores/explorationStore.ts`, `hooks/useMarketView.ts`, `SectorBar.tsx`, `MarketGraphCanvas.tsx`(37KB), `app/chainsight/page.tsx` | — |
| PR-6 트레일+관계카드 | **A** | `ExplorationTrail.tsx`, `RelationCardPanel.tsx` (pre-focus/focused 분기) | — |
| PR-7 체인 스토리 피드 | **A** | `ChainStoryFeed.tsx` (useSignalFeed) + page.tsx 통합 | — |

---

## 3. 미구현 항목 상세

### (C) 완전 미구현 — 1건

**cs_33 GDS 알고리즘 배치 태스크**
- 증거: `apps/chain_sight/tasks/` 내 GDS/PageRank/Louvain/Betweenness 코드 0건, `config/celery.py`에 GDS Beat 미등록.
- 현황: GDS 산출 속성(`pagerank_score`, `betweenness_score`, `community_id`)은 그래프 스키마(`schema.py` community 인덱스)와 `path_service.py:194-195` 조회에 사용되나, **1회 수동 Neo4j 실행으로만 계산**됨.
- 영향: 데이터가 갱신돼도 중심성/커뮤니티 점수가 자동 재계산되지 않아 시간이 지날수록 stale. cs_42 suggestion의 "같은 클러스터" 범주가 미구현인 것도 이와 연결.

### (B) 부분 구현 — 핵심 누락 항목

**1. RelationConfidence Tier 시스템 (cs_24 + relation_confidence_design_v1)** ← **최대 갭**
- 미수집 증거: manual_seed, etf_holding, gemini_extracted, theme_inferred, news_sc_keyword, price_corr_30d, gemini_raw.
- 미구현 관계 타입: SUPPLIES_TO, COMPETES_WITH, HAS_THEME, HELD_BY_SAME_FUND, BELONGS_TO_SECTOR/INDUSTRY(독립 관계로는 미생성).
- 미구현 로직: 상향 전이(hidden→weak→probable→confirmed), investment_relevance 계산, score_version 관리.
- 미설정 모델 필드: `has_supply_chain_source`, `has_etf_source`, `has_llm_source` (모델엔 존재, 코드에서 미설정).
- 점수 산정 방식 불일치: 설계는 Tier별 고정점(T1=85, T2=60, T3=35), 구현은 count/correlation 임계 기반.

**2. cs_42 Suggestion API 누락 범주**: COMPETES_WITH, SUPPLIES_TO 양방향, community_id 클러스터.

**3. cs_43 Trace API**: `alternative_paths` 응답 필드 누락, HTTP 메서드 GET/POST 문서-구현 불일치.

**4. cs_21c InsiderSignal**: institutional_ownership_pct / short_interest_pct 데이터 소스 미연결 → smart_money_signal 제한.

**5. cs_02 GraphRepository Protocol**: 5개 메서드 시그니처 Protocol 미선언(타입 안전성).

**6. cs_5 프론트 Advanced(v2 6-2)**: 노드 메트릭 오버레이(PER/시총/Centrality 히트맵), 노드 비교 모드(Ctrl+Click).

---

## 4. 폐기/대체 항목

### (D) 폐기 — 0건

**redesign_v1_260409은 기존 cs_*를 폐기하지 않음.** 검증 결과:

1. **API 공존 (urls.py 직접 검증)**: 마켓뷰 4종(`seeds/`, `sector/<sector>/graph/`, `signals/`, `<symbol>/neighbors/`)과 Deep dive 3종(`<symbol>/graph/`, `<symbol>/suggestions/`, `trace/`)이 **동일 `api/urls.py`에 모두 등록**되어 동작.
2. **프론트 공존**: `/chainsight/[symbol]` Deep dive 워크스페이스(cs_5)와 `/chainsight` 마켓뷰 대시보드(redesign)가 별개 라우트로 병존.
3. **로드맵 정합**: `chain_sight_roadmap_v1.3.md`·`remaining_work_plan.md`가 cs_* Deep dive 트랙을 여전히 활성으로 명시.

**관계 판정: 병행 추가 (마켓뷰 = 신규 글로벌 탐색 레이어, Deep dive = 기존 심층 분석 레이어)**. redesign 설계 4종(seed_node/api/ui_ux/marketview_pr)은 cs_* 로드맵에 **종속 신규 기능**으로 위치.

### 설계 진화로 "문서 stale" 처리가 필요한 항목 (폐기는 아니나 문서-구현 괴리)

| 항목 | 설계 명시 | 실제 구현 | 권고 |
|------|---------|---------|------|
| cs_32 관계 엣지 | 고정 RELATED_TO | 동적 타입(PEER_OF 등)+RELATED_TO 1회 정리 | 설계 문서에 진화 반영 |
| cs_31/전반 동기화 플래그 | `synced_to_neo4j` | `neo4j_dirty` (audit P0 #9 반전) | DECISIONS.md 박제 확인 |
| cs_43 Trace 메서드 | (완료보고서 POST) | GET | 문서 통일 |

---

## 부록 — 감사 방법 및 신뢰도

- **방법**: 설계 문서 30종 전수 정독 → `apps/chain_sight/` 코드 Read/Grep 대조 → `docs/chain_sight/task_done/` 완료보고서 cross-reference. 5개 영역 병렬 분석 후 종합.
- **직접 검증 항목**: `api/urls.py`/`api/views.py` 라우팅(두 API 세트 공존 확인), `tasks/` GDS 부재 확인, `config/celery.py` chainsight Beat 등록(약 9~10건).
- **미검증/추정 주의**: 각 Beat 태스크의 런타임 실제 적재 건수는 완료보고서 기재값 인용(코드 실행 안 함). Neo4j 실데이터 상태(노드/관계 수)는 미조회.
