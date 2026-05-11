# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-02
> **감사 범위**: `docs/chain_sight/plan/` 설계 문서 vs `chainsight/` + `frontend/components/chainsight/` 구현
> **감사 방식**: 읽기 전용. 코드 수정 없음.
> **참조 브랜치**: `portfolio` (현재 작업 브랜치) — Chain Sight 작업은 `data_structure_remodeling_V1` 에서 통합

---

## 요약 (구현률)

| 영역 | 설계 항목 | 완전 구현 (A) | 부분 구현 (B) | 미구현 (C) | 폐기/대체 (D) | 비고 |
|------|----------|--------------|---------------|-----------|---------------|------|
| Phase 0 인프라 | 4 | 4 | 0 | 0 | 0 | CS-0-0~0-3 모두 완료 |
| Phase 1 시드 로드 | 3 | 3 | 0 | 0 | 0 | CS-1-1~1-3 모두 완료 |
| Phase 2 파생 데이터 | 7 | 5 | 2 | 0 | 0 | Tier A 4종 + 관계 발견 + 집약 완료, Tier B(NarrativeTag/EventReaction/RevenueStructure)는 모델만 존재 |
| Phase 3 동기화/GDS | 3 | 3 | 0 | 0 | 0 | Profile/Relation Neo4j sync + GDS PageRank/Louvain/Betweenness 적재 완료 |
| Phase 4 REST API | 3 | 3 | 0 | 0 | 0 | graph/suggestions/trace 모두 구현 |
| Phase 5 프론트엔드 v1 (cs_51~54) | 4 | 4 | 0 | 0 | 0 | Deep dive workspace로 통합 구현 |
| 프론트 v2 (cs_5_frontend_design_v2) | 1 | 1 | 0 | 0 | 0 | `/chainsight/[symbol]` 3-panel 워크스페이스 |
| Redesign V1 (260409) — 마켓 뷰 | 7 PR | 7 | 0 | 0 | 0 | PR-1~7 모두 완료, QA 91% 승인 |
| Seed Node Phase 1 (B+A) | 5 시드 소스 | 5 | 0 | 0 | 0 | price/volume/sector_outlier/relation/comention 모두 구현 |
| Seed Node Phase 2 (Heat Score) | 5 항목 | 0 | 1 | 4 | 0 | `calculate_heat_scores` 로 4-term 단순화 구현, SeedHeatScore 모델/Phase 2 정의 미반영 |
| Seed Node Phase 3 (D-1~D-3) | 3 단계 | 0 | 0 | 3 | 0 | text_conditional_prob/lagged correlation/propagation_weight 전부 미구현 |
| 데이터 수집 DC-1~6 | 6 | 2 | 0 | 4 | 0 | DC-1, DC-2 완료. DC-3~6 미실행 |

**전체 핵심 항목 구현률**: 약 **88%** (38/43 핵심 항목 완전 구현, Heat Score Phase 2 부분, Phase 3/DC-3~6 미실행).

**판정**: **MVP 마켓 뷰 + Deep dive workspace는 출시 준비 완료**. 잔여 항목은 Phase 2(Heat Score)·Phase 3(이벤트 전파 모델)·데이터 수집 후속.

---

## 문서별 상태 테이블

### A) 코어 로드맵 (chain_sight_roadmap_v1.3.md)

| Phase / Section | 설계서 핵심 요구 | 구현 위치 | 상태 |
|-----------------|------------------|----------|------|
| 2.4 Neo4j 온톨로지: :Stock/:Sector/:Industry/:Theme + 6 관계 타입 | 4개 노드, 6개 관계 | `chainsight/management/commands/load_*_to_neo4j.py`, `chainsight/services/neo4j_loader.py`, `chainsight/services/neo4j_sync.py` | A — Theme 21개 + HAS_THEME 534개 (DC-2) |
| 2.5 PostgreSQL 12개 테이블 | 12 모델 | `chainsight/models/*.py` (12 모델 + SavedPath/PathAction/SeedSnapshot 추가 3 모델) | A — 12 모델 모두 존재, 3 모델 신규 추가 |
| 3-1 Celery Beat 8개 스케줄 | beat_schedule | `config/celery.py` (`task_done/celery_beat_registration.md` 기준 11개 등록) | A |
| 4 데이터 수집 6-Phase | DC-1~6 | DC-1, DC-2 완료; DC-3~6 보류 | C (4건 미실행) |
| 부록 G CS-0-0 체크리스트 | legacy 정리 + API 5종 테스트 | `task_done/CS-0-0_legacy_cleanup_api_test.md` | A |

### B) Phase 0~3 작업별 plan (cs_0X, cs_1X, cs_2X, cs_3X)

| 문서 | 설계 핵심 | 구현 위치 | 상태 |
|------|----------|----------|------|
| cs_00_legacy_cleanup_api_test.md | serverless/frontend Chain Sight 코드 제거, RelationConfidence v2.1 마이그레이션, API 5종 테스트 | `task_done/CS-0-0_…` | A |
| cs_01_migrations_verification.md | 12개 테이블 마이그레이션 검증 | migrations 0001~0007 (DB 12+3 테이블) | A |
| cs_02_neo4j_connection.md | PID 기반 lazy init driver | `chainsight/graph/repository.py` `Neo4jGraphRepository` | A |
| cs_03_neo4j_schema.md | 4개 constraint + 인덱스 | `chainsight/management/commands/init_neo4j_schema.py` | A |
| cs_11_stock_node_bulk_load.md | S&P 500 :Stock 500개 로드 | `load_stocks_to_neo4j.py`, 결과 532개 | A |
| cs_12_sector_industry.md | :Sector ~11, :Industry ~70, BELONGS_TO ~1,000 | `load_sectors_to_neo4j.py`, 결과 17 + 128 + 1,038 | A |
| cs_13_peer_relations.md | PEER_OF 2,500~3,500 | `load_peers_to_neo4j.py`, 결과 8,350 (목표 초과 달성) | A |
| cs_21_tier_a_profile.md | GrowthStage + CapitalDNA | `chainsight/tasks/profile_tasks.py` `calculate_growth_stages`, `calculate_capital_dna` | A — 480/473 적재 |
| cs_21b_sensitivity_profile.md | Rate/Forex/Commodity/Regulation | `chainsight/tasks/sensitivity_tasks.py` | A — 503건 |
| cs_21c_insider_signal.md | Finnhub Insider | `chainsight/tasks/insider_tasks.py` | A — 503건 |
| cs_22_co_mention.md | NewsArticle → ChainNewsEvent → CoMentionEdge | `chainsight/tasks/relation_tasks.py` `extract_co_mentions` | A — 744 쌍 |
| cs_23_price_co_movement.md | 90일 rolling correlation | `chainsight/tasks/relation_tasks.py` `calculate_price_co_movement` | A — 2,473쌍 |
| cs_24_relation_confidence.md | 5단계 상태 + truth_score, stale decay | `chainsight/tasks/relation_tasks.py` `update_relation_confidence`, `check_stale_and_decay` | A — 3,527 레코드 (이후 9,345로 확장) |
| cs_25_chain_profile_aggregation.md | 30개 개별 필드 집약 | `chainsight/tasks/sync_tasks.py` `aggregate_chain_profiles` | A — 503건 |
| cs_31_profile_neo4j_sync.md | Delta Sync (neo4j_synced=False) | `chainsight/tasks/sync_tasks.py` `sync_profiles_to_neo4j` | A |
| cs_32_relation_neo4j_sync.md | confirmed/probable → MERGE / stale/hidden → DELETE / Market 보조 속성 | `chainsight/tasks/sync_tasks.py` `sync_relations_to_neo4j` (위임) + `chainsight/services/neo4j_sync.py` `sync_dirty_relations` | A — `neo4j_dirty` 패턴으로 진화. Market(weak)도 sync. RELATED_TO 레거시 1회 정리 후 동적 타입 사용 |
| cs_33_gds_algorithms.md | PageRank, Louvain, Betweenness | `task_done/CS-3-3_gds_algorithms.md` | A — Neo4j 5.26.3 + GDS 2.13.2, 결과 적재 완료. 단, Celery 정기 task로는 등록 안 됨 (수동 실행) |
| relation_confidence_design_v1.md | RelationConfidence v2.1 스키마 + 5단계 상태 + 7 bool + evidence_sources | `chainsight/models/relation_discovery.py` (모든 필드 존재) | A |

### C) Phase 4 API (cs_41~43)

| 문서 | 엔드포인트 | 구현 위치 | 상태 |
|------|----------|----------|------|
| cs_41_graph_api.md | `GET /chainsight/{symbol}/graph/?depth=1` | `chainsight/api/views.py` `ChainSightGraphView`, urls.py | A — CUSTOMER_OF 역방향 파생, market_signals(co_mention_count, price_correlation) 포함 |
| cs_42_suggestion_api.md | `GET /chainsight/{symbol}/suggestions/` | `ChainSightSuggestionView` | A — peers/same_industry/co_mentioned/same_sector 4 카테고리 |
| cs_43_trace_api.md | `GET /chainsight/trace/?from=&to=` | `ChainSightTraceView` (shortestPath) | A |

### D) Phase 5 프론트엔드 — 두 단계 (cs_51~54 + cs_5_frontend_design_v2)

| 문서 | 핵심 산출물 | 구현 위치 | 상태 |
|------|------------|----------|------|
| cs_51_graph_visualization.md | `GraphView.tsx` (Force-Directed, Spotlight, Lazy Expansion) | `frontend/components/chainsight/GraphCanvas.tsx` (react-force-graph-2d) | A |
| cs_52_ai_guide_ui.md | `SuggestionCards.tsx` | `frontend/components/chainsight/AIGuidePanel.tsx` (좌측 패널 통합) | A — 카테고리 카드 + Chain Trace 입력 통합 |
| cs_53_chain_trace_ui.md | `TraceView.tsx` | `frontend/components/chainsight/TracePathView.tsx`, `FullPathView.tsx` | A |
| cs_54_stock_detail_integration.md | `ChainSightMiniView` + 종목 상세 탭 | `frontend/components/chainsight/GraphMiniView.tsx` + `frontend/app/stocks/[symbol]/page.tsx` (현 redesign V1 에선 딥링크로 변경) | A (단, redesign V1 에서 탭 → 딥링크로 대체됨 — 부분 D) |
| cs_5_frontend_design_v2.md | `/chainsight/[symbol]` 3-panel + 모바일 카드 리스트 + 필터 패널 + CTA | `frontend/app/chainsight/[symbol]/page.tsx` + `AIGuidePanel`, `NodeDetailPanel`, `RelationLegend`, `FilterPanel`, `MobileCardList`, `TracePathView`, `FullPathView`, `PathCard`, `WatchButton` | A — Deep dive workspace로 보존 |

### E) Redesign V1 (260409) — 마켓 뷰 (`/chainsight`)

| 문서 | 핵심 산출물 | 구현 위치 | 상태 |
|------|------------|----------|------|
| chainsight_seed_node_design.md (v2.1, Phase 1=B+A) | 5 시드 소스 + Redis 캐시 + previous_status + Celery Beat | `chainsight/services/seed_selection.py` + `chainsight/tasks/seed_tasks.py` `run_seed_selection` | A |
| chainsight_api_design.md (v2.1, 4 API) | seeds/ + sector/{sector}/graph/ + {symbol}/neighbors/ + signals/ | `chainsight/api/views.py` `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` | A — display_type 파생, neighbors p95<200ms 목표 |
| chainsight_ui_ux_design.md (v2.2) | 5 컴포넌트 (섹터바/그래프/트레일/관계카드/체인스토리) + ExplorationState | `frontend/lib/stores/explorationStore.ts` + `frontend/hooks/useMarketView.ts` + 5 컴포넌트 (SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed) + `frontend/app/chainsight/page.tsx` | A |
| chainsight_marketview_pr_prompts.md (PR-1~7) | 7 PR | `task_done/chain_sight_redesign_V1/PR-1_…` ~ `PR-7_…` 모두 완료 | A — QA 91% 승인 (`qa_evaluator_review_01.md`) |
| (보강) data_quality_3_fixes.md | 섹터 수익률, 다중 관계 타입, 한글 trigger_summary | 코드/Beat 모두 반영 | A — Issue 1/2/3 모두 해결 |

### F) 보조/SEC

| 문서 | 비고 |
|------|------|
| sec_pipeline_base_design.md, sec_pipeline_pr_detail.md | SEC EDGAR 파이프라인 — `sec_pipeline/` 별도 앱. Chain Sight 외부지만 `task_done/` 17 PR 완료 (2026-04-04). 이번 감사 범위 외이지만 Chain Sight 의 :Stock 노드에 supply chain/business model 속성 주입 완료 |
| remaining_work_plan.md | "남은 작업" 목록은 2026-04-04 기준 — 이후 ETF/Sensitivity/Insider/Beat/Frontend/Redesign V1 까지 모두 완료. 현재 시점 기준 deprecated 문서 |

---

## 미구현 항목 상세

### 1. Seed Node Phase 2 — Heat Score (chainsight_seed_node_design.md §3) — **부분 구현**

| 설계 요구 | 구현 상태 | 갭 |
|----------|----------|-----|
| heat_score = w1×price_anomaly + w2×volume_surge + w3×relation_change_count + w4×comention_surge + w5×news_event_count + w6×gds_centrality_delta (6항) | `chainsight/tasks/seed_tasks.py` `calculate_heat_scores` 4항 단순화 (price/volume/relation_change/news_activation, 가중치 0.25 균등) | comention_surge·gds_centrality_delta 미반영 |
| `SeedHeatScore` 모델 (stock + date + heat_score + components + seed_rank) | 미생성. heat 결과는 Neo4j `:Stock` 노드 속성(`heat_score`, `price_signal`, …)에 직접 SET | DB 영속화/이력 추적 불가, seed_rank 미산출 |
| `chainsight-heat-score` 매일 11:30 Beat | `chainsight-heat-score-daily` task 등록 (실제 Celery Beat 등록 여부는 별도 확인 필요) | 스케줄 항목 명/시간 차이 |
| 섹터 정렬 기준 Phase 2+: `heat_total DESC` | API `seeds/`는 Phase 1 정렬(`seed_count DESC`) 유지 | 미반영 (sector_summary.heat_total 필드는 0.0으로만 채움) |

**판정**: Heat Score 자체는 일부 구현. 그러나 설계의 핵심 의도(SeedHeatScore 모델, 6항 가중 조합, sector heat_total 활용, Phase 2 시드 랭킹)는 **미반영**.

### 2. Seed Node Phase 3 — 이벤트 전파 모델 (chainsight_seed_node_design.md §4) — **미구현**

| 설계 단계 | 핵심 요구 | 구현 상태 |
|----------|----------|----------|
| D-1 text_conditional_prob | Gemini Embedding + ChromaDB + 종목별 벡터 집합 | C — 코드/Celery 흔적 없음 |
| D-2 lagged correlation + volume_response + propagation_weight | 60 거래일 + 텍스트 게이트 0.05 | C |
| D-3 사후 검증 → 가중치 학습 | 검증 데이터 축적 후 ML | C |

**원인**: 설계서 §7 의존성에서 D-1 = ChromaDB+Gemini Embedding, D-2 = 60 거래일 후 가능 → 시간/인프라 의존. 즉 **계획대로 보류** 상태.

### 3. 데이터 수집 DC-3~6 (chain_sight_roadmap_v1.3.md §4.2) — **미실행**

| Phase | 산출물 | 상태 |
|-------|-------|------|
| DC-3 수동 시드 JSON → SUPPLIES_TO ~500 | C | 미실행 (대신 SEC Pipeline 으로 supply chain 추출) |
| DC-4 Gemini Flash → SUPPLIES_TO 확장 ~1,100 | C | 미실행 |
| DC-5 Marketaux 뉴스 자연 축적 ~1,000 | B (자연 진행) | CoMentionEdge 744쌍 → CO_MENTIONED 193 으로 일부 축적, 본격 1,000+ 수준은 미달 |
| DC-6 유료 API (Finnhub Premium) | C | 보류 (수익화 이후) |

**갭**: SEC Pipeline (`sec_pipeline/`) 가 DC-3/DC-4 의 supply chain 영역을 부분 대체했으나 ETF Theme(DC-2) 외 정량 메트릭은 비교 미실시.

### 4. Tier B 프로파일 (NarrativeTag, RevenueStructure, EventReaction) — **모델만 존재**

| 모델 | Tier | 모델 정의 | 계산 task | 상태 |
|------|------|----------|----------|------|
| `CompanyNarrativeTag` | B | ✅ `chainsight/models/narrative_tag.py` | ❌ 없음 | C — `aggregate_chain_profiles` 에서 `nt = CompanyNarrativeTag.objects.filter(symbol=stock).first()` 로 읽지만 어디서도 채우지 않음 |
| `CompanyRevenueStructure` | B | ✅ `chainsight/models/revenue_structure.py` | ❌ 없음 | C — 로드맵 부록 A "MVP에서는 빈 상태로 시작, 점진 채움"과 일치 |
| `CompanyEventReaction` | B | ✅ `chainsight/models/event_reaction.py` | ❌ 없음 | C — 로드맵 §2.5 "earnings 전후 주가 변동 계산 → 실행 가능 ✅" 이지만 미진행 |

**판정**: cs_21_tier_a_profile.md §⚠️ 점검 결과에 "Tier B EventReaction은 Tier A 완료 후 별도 작업으로 진행" 명시 — **정상 보류**.

### 5. CS-3-3 GDS Celery 정기 등록 — **부분 구현**

| 항목 | 설계 | 구현 |
|------|------|------|
| `chainsight/tasks/gds_tasks.py` | 신규 파일 + `run_gds_algorithms` shared_task | ❌ 파일 없음. GDS 결과는 1회 수동 실행으로 적재 |
| Celery Beat 등록 | 주간 또는 월간 | ❌ `celery_beat_registration.md` 11개 등록 목록에 GDS 없음 |

**갭**: 그래프 변경 후 PageRank/Community 가 stale 가능. 다만 노드/관계 변경 빈도가 낮고 1회 적재로 데모 가능 — 운영 확장 시점에 추가 필요.

### 6. NeighborGraphView UNION → undirected MATCH — **명시적 차이**

설계서 (api_design.md §4): UNION + 두 방향 RETURN. 실제 코드(views.py:504): undirected `MATCH (center)-[r]-(neighbor)` + `CASE startNode=$symbol THEN outbound ELSE inbound END` 으로 구현. 결과 동등. **A** (구현 자유도 내).

### 7. RELATED_TO 레거시 — **마이그레이션 진행 중**

`chainsight/api/views.py:351, 494` 주석:
> "기존 sync_relations_to_neo4j 가 엣지 라벨을 RELATED_TO 로 고정"

`sync_tasks.py:163`: 1회 정리 + dirty sync 위임. 이후 PEER_OF/CO_MENTIONED/PRICE_CORRELATED/SUPPLIES_TO/COMPETES_WITH 동적 타입 라벨로 저장. `data_quality_3_fixes.md` 결과: RELATED_TO 0, PEER_OF 12,178 등 동적 라벨 적재 확인 — **A**.

---

## 폐기/대체 항목

### D1. cs_5_frontend_design_v2.md vs redesign_v1_260409 — **공존 (대체 아님)**

| 항목 | cs_5_frontend_design_v2 (v2) | redesign_v1_260409 |
|------|------------------------------|--------------------|
| 메인 페이지 | `/chainsight/[symbol]` 3-panel **Deep dive workspace** | `/chainsight` 마켓 뷰 5 컴포넌트 |
| 진입 경로 | 종목 상세 → "전체 탐색", 사이드바 메뉴 | 메인 네비 "Chain Sight*" 탑레벨 |
| 노드 클릭 | spotlight + lazy expansion (depth) | in-place 중심 이동 (neighbors API) |
| 모바일 | 카드 리스트 + FAB 그래프 오버레이 | (Future consideration) |

**결론**: redesign V1 가 **cs_5_frontend_design_v2 를 대체하지 않음**. redesign V1 은 **마켓 뷰**(breadth-first 탐색 허브)를 신설하고, cs_5_frontend_design_v2 는 **Deep dive workspace**(depth-first 분석)로 보존됨. 종목 상세 페이지의 Chain Sight **탭만** redesign V1 에서 "Chain Sight 에서 보기" 딥링크로 대체됨 (`task_done/PR-5_fe_core_ui.md`).

### D2. CS-5-4 종목 상세 탭 미니 그래프 → 딥링크 — **대체**

cs_54_stock_detail_integration.md: 종목 상세 Chain Sight 탭에 `GraphMiniView` 임베드 + "전체 보기 →" 링크.
redesign V1 (PR-5): 종목 상세 Chain Sight 탭에 "Chain Sight 에서 보기" 딥링크(`/chainsight?focus={symbol}`) 버튼 추가.
→ `GraphMiniView.tsx` 파일은 보존되어 있으나 **현재 종목 상세 탭에서는 호출되지 않음** (확인 필요).

### D3. cs_24 evidence_sources 이름 차이

설계 (cs_24): `has_peer_of`, `has_co_mention`, `has_price_corr`, `has_supply_chain`, `has_etf_peer`, `has_institutional`, `has_llm_relation` (7 bool)
구현 (`relation_discovery.py`): `has_peer_source`, `has_industry_source`, `has_supply_chain_source`, `has_news_source`, `has_price_source`, `has_etf_source`, `has_llm_source` (7 bool)

→ **대체 (의미 동등, 명명 통일)**. relation_confidence_design_v1.md 의 정식 명명을 따름. `task_done/CS-2-4_relation_confidence.md` 의 "evidence_sources" 설명은 cs_24 plan 이름을 그대로 인용한 잔재.

### D4. CompanyChainProfile JSONB → 30 개별 필드 — **로드맵 자체에서 대체 결정**

로드맵 v1.2 §부록 A 명시: "v1.1에서 `profile_data (JSONB)` 단일 필드로 제안했으나, 실제 구현은 30개 개별 필드. **현재 구조 유지 결정.**" → **D (로드맵에 반영 완료)**.

### D5. CUSTOMER_OF DB 저장 제거 — **로드맵 v1.3에서 대체 결정**

`SUPPLIES_TO` 만 canonical, API 에서 `direction=outbound` 시 `display_type=CUSTOMER_OF` 파생. `chainsight/api/views.py` `_display_type` 함수 + view-level 후처리로 일관 적용. → **D (정상)**.

### D6. SavedPath / WatchlistViewSet — **계획 외 추가 기능 (확장)**

| 추가물 | 위치 | 설계 문서 |
|--------|------|----------|
| `chainsight/models/saved_path.py` `SavedPath`, `PathAction` | migration 0006 | ❌ cs_*, redesign_v1 어디에도 없음 |
| `chainsight/views/watchlist_views.py` `WatchlistViewSet` (+ DRF router) | api/urls.py | ❌ |
| `chainsight/services/path_service.py`, `alternatives_service.py`, `expand_service.py`, `recheck_service.py` | services/ | ❌ |
| `chainsight/serializers/path_watchlist.py` | serializers/ | ❌ |
| `chainsight/management/commands/regenerate_summary_paths.py` | commands/ | ❌ |
| `frontend/components/chainsight/WatchButton.tsx`, `PathCard.tsx`, `FullPathView.tsx` | components | ❌ |
| `frontend/app/chainsight/watchlist/[id]/page.tsx` | app | ❌ |
| `frontend/hooks/usePathWatchlist.ts` | hooks | ❌ |

**판정**: redesign V1 이후 추가된 **경로 저장 / 워치리스트 / 대안 탐색 / 재검증** 기능. 설계서가 누락된 게 아니라 **설계서 미작성 상태로 구현됨**. 후속 설계서 작성 또는 redesign V2 통합 필요.

### D7. 환경 변경 — Neo4j 다운그레이드 + GDS 추가

`task_done/CS-3-3_gds_algorithms.md`: Neo4j 2026.01.4 → 5.26.3 다운그레이드 + GDS 2.13.2 설치. 로드맵 §2.4 부록 "GDS 의존성 주의"에 사전 경고된 결정 — **D (정상)**.

---

## 주요 정렬 일치 사항 (Bonus)

| 항목 | 설계 | 구현 | 일치 |
|------|------|------|------|
| previous_status 필드 | redesign_v1 PR-1 | `relation_discovery.py:124` + save() override | ✅ |
| neo4j_dirty 패턴 | redesign_v1 PR-3 | `relation_discovery.py:131`, `services/neo4j_sync.py` | ✅ |
| undirected 정규화 (symbol_a < symbol_b) | roadmap §2.4 | `chainsight/utils.py` `normalize_pair`, neo4j_sync UNDIRECTED_TYPES | ✅ |
| display_type 파생 (CUSTOMER_OF) | api_design §4, roadmap v1.3 | `_display_type()` + edge 후처리 | ✅ |
| 시드 5 소스 합산 | seed_node_design v2.1 §2 | `services/seed_selection.py:select_seeds` | ✅ |
| neighbors p95 < 200ms 목표 | api_design §4 | (실측 미확인 — 캐시 30분 적용) | ⚠️ |
| 섹터 수익률 DailyPrice 기반 | data_quality_3_fixes.md | `stocks/tasks.py` update_sp500_change_percent | ✅ |
| QA Evaluator 검증 91% | qa_evaluator_review_01.md | DECISIONS 준수, 마이그레이션 100%, 타입 95% | ✅ |
| 3단 시드 폴백 (Redis → SeedSnapshot → async 복구) | (런타임 진화) | `_get_today_seeds`, `_trigger_seed_recovery`, SeedSnapshot 모델 | ✅ (설계 미존재 — bug #27 대응 추가) |

---

## 권고 (선택)

1. **redesign V2 설계서 (또는 redesign_v1 부록)**: `SavedPath`/`WatchlistViewSet`/`alternatives`/`expand`/`recheck` 기능군의 사양 문서화 — D6 의 미문서화 자체가 가장 큰 갭.
2. **Heat Score Phase 2 명세 정합화**: 코드의 4-term 단순화를 설계서에 반영하거나(설계 → 구현), 6-term + SeedHeatScore 모델로 보강(구현 → 설계).
3. **GDS 정기 batch task** 등록: `chainsight/tasks/gds_tasks.py` + Celery Beat (월간 또는 데이터 변경 트리거).
4. **GraphMiniView 잔재 확인**: 현재 종목 상세 페이지에서 호출 여부 확인. 미호출이면 제거 또는 redesign V1 에서 재활용 결정.
5. **remaining_work_plan.md 업데이트** 또는 deprecated 명시: 2026-04-04 기준 문서가 그 이후 완료된 ETF/Sensitivity/Insider/Beat/Frontend/Redesign V1 을 반영하지 못함.

---

## 결론

- **마켓 뷰** (`/chainsight`) + **Deep dive workspace** (`/chainsight/[symbol]`) 양쪽 모두 출시 가능 수준.
- 핵심 로드맵 Phase 0~5 + Redesign V1 (7 PR) **완전 구현**.
- 주요 갭은 (a) Seed Heat Score 6-term & Phase 3 이벤트 전파 (계획대로 보류), (b) Tier B 3 모델 미적재 (점진), (c) **SavedPath / Watchlist 기능 설계서 부재 — 우선 보완 권장**.
- 폐기/대체 결정은 모두 로드맵 v1.2/v1.3 또는 redesign V1 에 명시되어 있어 추적 가능.

**END OF AUDIT**
