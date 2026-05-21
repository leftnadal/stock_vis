# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-22
> **범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `chainsight/` 백엔드 + `frontend/{app,components}/chainsight/` 프론트엔드 + `tests/unit/chainsight/`
> **방식**: 읽기 전용 (코드 수정 없음)

---

## 요약 (구현률)

| 범주 | 설계 항목 | (A) 완전 구현 | (B) 부분 구현 | (C) 미구현 | (D) 폐기/대체 | 비고 |
|------|-----------|---------------|---------------|------------|----------------|------|
| Phase 0 — 인프라 (CS-0-0~0-3) | 4 | 4 | 0 | 0 | 0 | task_done 4종 |
| Phase 1 — 시드 로드 (CS-1-1~1-3) | 3 | 3 | 0 | 0 | 0 | task_done 3종 |
| Phase 2 — Tier A/관계 (CS-2-1~2-5) | 5+2 | 5 | 2 | 0 | 0 | Tier B 모델만, 채움 task 없음 |
| Phase 3 — Neo4j Sync + GDS (CS-3-1~3-3) | 3 | 3 | 0 | 0 | 0 | dirty_sync 패턴으로 보강 |
| Phase 4 — REST API (CS-4-1~4-3) | 3 | 3 | 0 | 0 | 0 | task_done 통합 1종 |
| Phase 5 — 프론트엔드 (cs_51~54, v2) | 4 | 4 | 0 | 0 | 0 | Deep dive workspace 형태 |
| Redesign V1 마켓 뷰 (PR-1~7) | 7 | 7 | 0 | 0 | 0 | 2026-04-10 완료 |
| 시드 노드 Phase 1 (B+A) | 1 | 1 | 0 | 0 | 0 | run_seed_selection |
| 시드 노드 Phase 2 (Heat Score) | 1 | 0 | 1 | 0 | 0 | DB 모델(SeedHeatScore) 미생성, Neo4j 속성으로만 적재 |
| 시드 노드 Phase 3 (이벤트 전파 D-1~D-3) | 3 | 0 | 0 | 3 | 0 | 텍스트 조건확률/lagged corr/propagation 미착수 |
| 데이터 수집 (DC-1~6) | 6 | 3 | 1 | 2 | 0 | DC-1/DC-2/DC-3 완료, DC-4 보류, DC-5 자연 축적, DC-6 보류 |
| Saved Path 시스템 (CS-6 시리즈) | — | 5+ | 0 | 0 | 0 | SavedPath/PathAction/recheck/expand/alternatives 모두 구현 |

전체 가중 구현률 ≒ **86%** (Phase 0~5 + Redesign V1 코어는 사실상 100%, Phase 3 이벤트 전파/Heat Score/DC-4·6만 비어 있음).

---

## 문서별 상태 테이블

### `docs/chain_sight/plan/` 24개 문서

| 문서 | 분류 | 코드 매핑 | 상태 |
|------|------|-----------|------|
| `chain_sight_roadmap_v1.3.md` | (A) 완전 구현 | 전체 — 12개 PG 모델 + Neo4j 4 constraint + 7 API | Phase 0~4 모두 task_done 기록 존재 |
| `relation_confidence_design_v1.md` (v1.1) | (A) | `models/relation_discovery.py:RelationConfidence` v2.1, `migrations/0008_unify_neo4j_flags.py` | 5단계 상태/truth+market 분리/normalize_pair/previous_status 모두 반영 |
| `remaining_work_plan.md` | (A) (트래킹 문서) | — | 2026-04-04 작성 후 항목 5개 중 5개 모두 완료 |
| `cs_00_legacy_cleanup_api_test.md` | (A) | task_done/CS-0-0 | legacy 정리 완료 (serverless 잔존은 별도 LEGACY_KEEP 태그) |
| `cs_01_migrations_verification.md` | (A) | migrations 0001~0008 (8개) | 12개 테이블 검증 완료 |
| `cs_02_neo4j_connection.md` | (A) | `graph/repository.py` Neo4jGraphRepository (PID-safe driver) | |
| `cs_03_neo4j_schema.md` | (A) | `graph/schema.py` + `management/commands/init_neo4j_schema.py` | 4 constraint + 2 index |
| `cs_11_stock_node_bulk_load.md` | (A) | `management/commands/load_stocks_to_neo4j.py` | 532 Stock |
| `cs_12_sector_industry.md` | (A) | `management/commands/load_sectors_to_neo4j.py` | 17 Sector + 128 Industry |
| `cs_13_peer_relations.md` | (A) | `services/neo4j_loader.py`, `tasks/peer_tasks.py:fetch_and_load_peers` | 8,350 PEER_OF |
| `cs_21_tier_a_profile.md` | (A) | `tasks/profile_tasks.py:calculate_growth_stages/calculate_capital_dna` | 480 GrowthStage + 473 CapitalDNA |
| `cs_21b_sensitivity_profile.md` | (A) | `tasks/sensitivity_tasks.py` | FMP Revenue Geo + BalanceSheet 기반 |
| `cs_21c_insider_signal.md` | (A) | `tasks/insider_tasks.py` | Finnhub Insider 60 RPM 준수 |
| `cs_22_co_mention.md` | (A) | `tasks/relation_tasks.py:extract_co_mentions` | NewsEntity → CoMentionEdge |
| `cs_23_price_co_movement.md` | (A) | `tasks/relation_tasks.py:calculate_price_co_movement` | 90일 rolling |
| `cs_24_relation_confidence.md` | (A) | `tasks/relation_tasks.py:update_relation_confidence` + `check_stale_and_decay` | 5단계 상태 + 소스별 분리 (data_quality_3_fixes 반영) |
| `cs_25_chain_profile_aggregation.md` | (A) | `tasks/sync_tasks.py:aggregate_chain_profiles` | 30개 개별 필드 구조 유지 결정 |
| `cs_31_profile_neo4j_sync.md` | (A) | `tasks/sync_tasks.py:sync_profiles_to_neo4j` | neo4j_dirty 플래그 기반 |
| `cs_32_relation_neo4j_sync.md` | (A) | `tasks/sync_tasks.py:sync_relations_to_neo4j` + `services/neo4j_sync.py:sync_dirty_relations` | dirty 패턴으로 보강 |
| `cs_33_gds_algorithms.md` | (A) | task_done/CS-3-3 (Neo4j 2026 → 5.26.3 다운그레이드 후 GDS 2.13.2) | PageRank/Louvain/Betweenness 실행 완료. 코드는 manual command/외부 실행이며 `chainsight/`에 GDS 전용 task 파일은 없음 |
| `cs_41_graph_api.md` | (A) | `api/views.py:ChainSightGraphView` | depth 1~3 |
| `cs_42_suggestion_api.md` | (A) | `api/views.py:ChainSightSuggestionView` | 4 카테고리 (peers/same_industry/co_mentioned/same_sector) |
| `cs_43_trace_api.md` | (A) | `api/views.py:ChainSightTraceView` | shortestPath max_depth 5 |
| `cs_51_graph_visualization.md` | (A) | `frontend/app/chainsight/[symbol]/page.tsx` + `components/chainsight/GraphCanvas.tsx` (react-force-graph-2d) | Deep dive 형태로 통합 |
| `cs_52_ai_guide_ui.md` | (A) | `components/chainsight/AIGuidePanel.tsx` | |
| `cs_53_chain_trace_ui.md` | (A) | `components/chainsight/TracePathView.tsx` | |
| `cs_54_stock_detail_integration.md` | (A) | `frontend/app/stocks/[symbol]/page.tsx` Chain Sight 탭 → "Chain Sight에서 보기" 딥링크 | redesign V1 PR-5에서 변경 |
| `cs_5_frontend_design_v2.md` | (A) | Deep dive workspace 3-panel 레이아웃 (좌 AI Guide, 중 그래프, 우 NodeDetail) | cs_51~54의 v2 통합본 |
| `sec_pipeline_base_design.md`, `sec_pipeline_pr_detail.md` | (별도 도메인) | `sec_pipeline/` 앱 | Chain Sight 범위 외 — SEC 17 PR 별도 완료 |

### `redesign_v1_260409/` — 마켓 뷰 신규 설계 (4 docs)

| 문서 | 코드 매핑 | 상태 |
|------|-----------|------|
| `chainsight_seed_node_design.md` (v2.1) | `services/seed_selection.py` + `tasks/seed_tasks.py:run_seed_selection` + `models/seed_snapshot.py:SeedSnapshot` | (A) Phase 1 (B+A) 완료, (B) Phase 2 Heat Score 부분, (C) Phase 3 미구현 |
| `chainsight_api_design.md` (v2.1) | `api/views.py:SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView` + `api/urls.py` | (A) 4 엔드포인트 모두 |
| `chainsight_ui_ux_design.md` (v2.2) | `app/chainsight/page.tsx` + `components/chainsight/{SectorBar,MarketGraphCanvas,ExplorationTrail,RelationCardPanel,ChainStoryFeed}.tsx` + `lib/stores/explorationStore.ts` + `hooks/useMarketView.ts` | (A) 5개 컴포넌트 + zustand 상태 + 6개 액션 모두 구현 |
| `chainsight_marketview_pr_prompts.md` | task_done/chain_sight_redesign_V1/PR-1~7 + browser_test_report + qa_evaluator_review_01 | (A) 7 PR 완료 |

### `task_done/` 22개 기록 — 설계 문서별 대응 검증

| task_done | 설계 매핑 | 검증 결과 |
|-----------|-----------|-----------|
| CS-0-0~0-3 | cs_00~03 | 4건 모두 일치 |
| CS-1-1~1-3 | cs_11~13 | 3건 모두 일치 |
| CS-2-1, 2-1b, 2-1c, 2-2, 2-3, 2-4, 2-5 | cs_21~25 + 21b/c | 7건 모두 일치 |
| CS-3-1, 3-2, 3-3 | cs_31~33 | 3건 모두 일치 |
| CS-4-1_2_3_rest_api | cs_41~43 (3개 통합 기록) | 일치 |
| CS-5-1_frontend_graph, CS-5-2_pro_features, CS-5-3_mobile_card_list | cs_51, cs_5_v2 (pro_features), cs_53 (모바일) | 3건 일치, **cs_54 단독 task_done 없음** (cs_5-3에 통합) |
| DC-2_etf_holdings_theme | DC-2 (로드맵 4.2) | 일치 — 21 Theme 노드 |
| celery_beat_registration | remaining_work_plan #3 | 일치 |
| chain_sight_redesign_V1/ (8 sub-docs) | redesign_v1_260409 4 docs | 7 PR + qa + browser_test + data_quality_fixes 모두 기록 |

---

## 미구현 항목 상세

### (B) 부분 구현

#### B-1. SeedHeatScore (시드 Phase 2)
- **설계 위치**: `redesign_v1_260409/chainsight_seed_node_design.md` 섹션 3 (Phase 2: Heat Score)
- **설계 요구**: `class SeedHeatScore(Stock FK + date + heat_score + components(JSONB) + seed_rank)` + 매일 11:30 Celery Beat + 섹터 정렬을 `seed_count DESC` → `heat_total DESC`로 전환
- **현재 구현**:
  - `tasks/seed_tasks.py:calculate_heat_scores` 함수는 존재 — Neo4j `:Stock` 노드에 `s.heat_score`, `s.heat_score_components`, `s.heat_score_updated_at` 속성 직접 SET
  - **PG 모델 `SeedHeatScore` 자체는 없음** (`models/__init__.py` 13개 모델에 포함되지 않음)
  - Celery Beat에 `chainsight-heat-score-daily` 등록 확인됨 (config/celery.py:742)
- **미구현 영향**: heat_score 히스토리(과거 N일치 추적) 불가능. seed_rank 영속화 없음. 섹터 정렬은 여전히 `seed_count DESC` 유지 가능성 (별도 확인 필요).
- **권고**: Phase 2 본격 적용 시 SeedHeatScore PG 모델 + migration 추가, sector_summary 응답 필드 `heat_total` 채우기.

#### B-2. Tier B 모델 채움 태스크 (NarrativeTag, EventReaction, RevenueStructure)
- **설계 위치**: 로드맵 v1.3 섹션 2.5 Tier B (반자동)
- **현재 구현**:
  - 3개 모델 존재 (`models/narrative_tag.py`, `event_reaction.py`, `revenue_structure.py`)
  - **계산/채움 태스크가 chainsight/tasks/에 없음**
  - 로드맵에서 "MVP에서는 빈 상태로 시작, 점진 채움" 명시 → 의도된 보류
- **권고**: Phase 3 이후 LLM 기반 NarrativeTag 추출 시점에 작업.

#### B-3. DC-5 뉴스 축적 (Marketaux 시간 경과 누적)
- **현재**: News Intelligence Pipeline v3는 별도 완료, CoMentionEdge 추출 task 작동 중
- **부분**: 시간 경과 축적은 운영 중인 Celery Beat에 의존 (`chainsight-co-mentions` 매일 06:30) — 코드 측면에서는 완전 구현, 데이터 측면에서는 누적 진행 중

### (C) 미구현

#### C-1. 시드 노드 Phase 3 — 이벤트 전파 모델 (D-1, D-2, D-3)
- **설계 위치**: `chainsight_seed_node_design.md` 섹션 4
- **설계 요구**:
  - D-1: `text_conditional_prob(A,B) = frequency × semantic_similarity` (ChromaDB + Gemini Embedding 90일 rolling)
  - D-2: `lagged correlation (lag 0/1/2) + volume_response + propagation_weight`
  - D-3: 사후 검증 + 가중치 학습
- **현재 구현**:
  - chainsight/tasks/에 `text_conditional`, `lagged_correlation`, `propagation_weight` 관련 함수/task 없음
  - Celery Beat에 D-1/D-2 스케줄 미등록
- **선행 조건 미충족**: ChromaDB 미도입, Gemini Embedding은 News 파이프라인 일부에서 사용 중이나 chainsight에 연결 안 됨
- **권고**: MVP 이후 Phase 3 진입 시 별도 PR 묶음 필요. 60 거래일 데이터 축적 후 D-2 실행 가능.

#### C-2. DC-4 — Gemini Flash Supply Chain 확장
- **설계 위치**: 로드맵 v1.3 섹션 4.2
- **설계 요구**: 수동 시드 JSON 기반 → Gemini Flash로 ~1,100개 supply chain 관계 확장 ($0.05 1회)
- **현재 구현**: DC-3 수동 시드는 SEC Pipeline 별도 경로로 진행됨. chainsight/tasks/에 Gemini 기반 supply chain 확장 task 없음.
- **권고**: SEC Pipeline의 Supply Chain 추출이 DC-4를 대체할 가능성 있음 — `sec_pipeline/` 결과 → `RelationConfidence` 적재 경로 확인 필요 (Celery Beat에 `sec-seed-relations-to-chainsight` 등록되어 있음 → C-2 일부 보강).

#### C-3. DC-6 — Finnhub Premium 업그레이드 ($200/월)
- **설계 위치**: 로드맵 v1.3 섹션 4.1
- **상태**: 수익화 이후 트리거 — 의도된 미구현. 별도 조치 불필요.

#### C-4. neighbors 응답의 2차 LLM 필드 (`relation_summary`, `why_now`, `insight_summary`)
- **설계 위치**: `chainsight_api_design.md` 섹션 4 "2차 필드 확장 (향후)"
- **현재 구현**: NeighborGraphView 응답에 미포함 (1차 템플릿만, 프론트 측에서 fallback 처리)
- **분류**: 설계서 자체에서 "향후"로 마킹 → 의도된 보류

### (D) 폐기/대체

#### D-1. legacy `serverless/` Chain Sight 코드 일부 잔존
- **설계 의도** (cs_00 + 로드맵 부록 B): chain_sight 관련 6개 view, 3개 service, 6개 url 모두 제거
- **현재 상태**:
  - `serverless/migrations/0009_chain_sight_stock.py`, `0010_etf_holdings.py` 잔존 (정상 — migration 히스토리는 보존)
  - `serverless/management/commands/migrate_chain_sight_to_neo4j.py` 잔존 (1회성 도구)
  - `serverless/tasks.py` 일부 chain_sight 참조 (LEGACY_KEEP 가능성)
  - **프론트엔드 `frontend/components/chain-sight/` 디렉토리는 완전 삭제 확인** (대신 `chainsight/` 신규 디렉토리)
- **분류**: 로드맵 부록 B에서 명시한 LEGACY_KEEP_UNTIL_DC2 패턴이 부분 적용. ETF 모델은 DC-2 완료 이후에도 보존 중 — 추가 정리 가능.

#### D-2. `CUSTOMER_OF` 별도 저장 폐기 → SUPPLIES_TO + 역방향 view 파생
- **설계 변경**: roadmap v1.2 → v1.3에서 결정
- **구현 반영**: `api/views.py:NeighborGraphView._display_type()`에서 `SUPPLIES_TO + outbound → CUSTOMER_OF` 파생. DB에는 SUPPLIES_TO만 저장. **설계 의도대로 폐기/대체 완료.**

#### D-3. cs_5_frontend_design_v2 → redesign_v1_260409 보완 관계
- **설계 진화**: cs_51~54 → cs_5_frontend_design_v2 (Deep dive workspace 3-panel) → redesign_v1_260409 (마켓 뷰 추가)
- **현재 구현**:
  - `/chainsight` (마켓 뷰) = redesign_v1_260409 PR-5/6/7 결과 — `app/chainsight/page.tsx` + 5개 마켓 뷰 컴포넌트
  - `/chainsight/[symbol]` (Deep dive workspace) = cs_5_v2 결과 — 기존 GraphCanvas, AIGuidePanel, NodeDetailPanel, TracePathView, FilterPanel, MobileCardList 유지
- **분류**: **redesign이 cs_51~54를 대체한 것이 아니라 보완**. 두 화면이 공존. 종목 상세 페이지의 Chain Sight 탭은 redesign PR-5에서 딥링크로 축소됨.

#### D-4. RelationConfidence 상태 체계 — 3단계(confirmed/candidate/rejected) → 5단계(hidden/weak/probable/confirmed/stale)
- **설계 변경**: relation_confidence_design v1 → v1.1
- **구현 반영**: `models/relation_discovery.py:RelationConfidence.RELATION_STATUS_CHOICES`에 5단계 모두 정의 + `tasks/relation_tasks.py:check_stale_and_decay` 하향 전이 task 구현 + previous_status 필드 추가. **완전 대체 완료.**

#### D-5. Neo4j 엣지 라벨 — 관계 타입별 → `RELATED_TO` 단일 라벨 + `r.relation_type` 속성
- **암묵적 설계 변경**: roadmap에서는 관계 타입별 엣지 라벨(SUPPLIES_TO, PEER_OF 등)로 정의했으나, 실제 sync는 `RELATED_TO` 단일 라벨 + 속성으로 구현됨 (`api/views.py:SectorGraphView` 주석에 명시)
- **구현 반영**: 모든 API 쿼리에서 `COALESCE(r.relation_type, type(r))`로 처리. data_quality_3_fixes Issue 2에서 원인 진단 및 보강.
- **분류**: 설계 의도와 다른 구현이지만, 데이터 품질 수정 후 일관성 확보. 향후 라벨 정규화 시 마이그레이션 필요.

---

## 폐기/대체 항목 요약 (표)

| 항목 | 원안 | 변경 후 | 시점 | 코드 반영 |
|------|------|---------|------|-----------|
| CUSTOMER_OF | 별도 엣지 저장 | SUPPLIES_TO + API 역방향 파생 | roadmap v1.2 → v1.3 | ✅ |
| Relation 상태 | 3단계 (confirmed/candidate/rejected) | 5단계 (hidden/weak/probable/confirmed/stale) | relation_confidence v1 → v1.1 | ✅ |
| Neo4j 엣지 라벨 | 관계 타입별 (SUPPLIES_TO 등) | RELATED_TO + r.relation_type 속성 | 암묵적 (sync 구현 시) | ⚠️ 코드는 일관, 라벨 미정규화 |
| 종목 상세 Chain Sight 탭 | 인터랙티브 그래프 | 딥링크 버튼만 (`/chainsight?focus=`) | redesign V1 PR-5 | ✅ |
| Frontend `/chainsight` | 단일 종목 진입 | 마켓 뷰 허브 + Deep dive workspace 분리 | redesign_v1_260409 | ✅ |
| ChainProfile 구조 | `profile_data` JSONB 단일 필드 | 30개 개별 필드 | roadmap v1.1 → v1.2 결정 | ✅ |
| neo4j_synced 플래그 | True=동기화됨 | neo4j_dirty (의미 반전, True=동기화 필요) | audit P0 #9 | ✅ migration 0008 |

---

## 핵심 발견

1. **설계 대비 완성도 매우 높음** — Phase 0~5 + Redesign V1 마켓 뷰까지 task_done 22개 기록 일치, 코드 매핑 명확.
2. **유일한 진성 미구현은 Phase 3 (이벤트 전파 D-1~D-3)** — 60 거래일 데이터 축적 의존이라 의도된 보류.
3. **Heat Score는 "Neo4j 속성 only" 형태로 부분 구현** — `SeedHeatScore` PG 모델 누락이 유일한 스키마 갭. Phase 2 본격화 시 추가 필요.
4. **Tier B (NarrativeTag/EventReaction/RevenueStructure)는 모델만 있고 채움 task 없음** — 로드맵에서 명시한 "MVP 빈 상태 시작"과 일치.
5. **Neo4j 엣지 라벨 단일화 (`RELATED_TO`)는 설계서에 없는 implicit 결정** — 향후 GDS 알고리즘 확장 시 라벨별 분리 필요할 수 있음 (현재는 r.relation_type 속성으로 우회).
6. **redesign_v1_260409는 cs_51~54의 대체가 아닌 보완** — 마켓 뷰 (`/chainsight`)와 Deep dive (`/chainsight/[symbol]`) 두 화면이 공존.
7. **Saved Path 시스템 (SavedPath/PathAction/recheck/expand/alternatives)은 plan/ 디렉토리에 단독 설계서 없음** — `cs_6_*` 계열로 추정되나 docs/chain_sight/plan/에 부재. `task_done/`에도 없음. **설계 문서 없이 구현된 영역** (코드는 견고하지만 설계 추적 불가).

---

**END OF AUDIT**
