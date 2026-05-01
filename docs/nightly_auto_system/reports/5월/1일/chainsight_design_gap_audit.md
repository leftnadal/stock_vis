# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-02
> **범위**: `docs/chain_sight/plan/` 설계서 vs `chainsight/` + `frontend/components/chainsight/` 구현
> **모드**: 읽기 전용 감사 (코드 수정 없음)

---

## 요약 (구현률)

| 영역 | 구현률 | 비고 |
|------|--------|------|
| **Phase 0 (CS-0-0~0-3)** 인프라 | 100% (A) | 레거시 정리, Neo4j 드라이버/스키마, 마이그레이션 12 테이블 검증 완료 |
| **Phase 1 (CS-1-1~1-3)** 시드 로드 | 100% (A) | Stock 532 + Sector 18 + Industry 131 + PEER_OF 2,816 |
| **Phase 2 (CS-2-1~2-5)** 파이프라인 | 90% (B) | Tier A 4종 모두 작동, BUT SensitivityProfile/InsiderSignal Beat 미등록 |
| **Phase 3 (CS-3-1~3-3)** Neo4j 동기화 + GDS | 85% (B) | PageRank/Betweenness 사용, **Louvain 미구현** |
| **Phase 4 (CS-4-1~4-3)** REST API | 100% (A) | 3개 엔드포인트 + redesign 4개 = 총 7개 모두 작동 |
| **Phase 5 (CS-5-1~5-4)** 프론트엔드 (원안 cs_5_v2) | 80% (B) | 컴포넌트 통합 형태로 존재, 일부 모듈 분리 미완 |
| **Redesign V1 (PR-1~7)** 마켓 뷰 | 95% (A) | 모든 PR 완료, 5개 컴포넌트 + 4 API + Zustand 스토어 |
| **Stock 상세 통합 (CS-5-4)** | 50% (B) | 미니 뷰 임베드 OK, 탭 제거/딥링크 전환은 미반영 |
| **DC-2** ETF Holdings | 100% (A) | Theme 21개 + HAS_THEME 534개 (CSV 우회) |
| **DC-3~6** 데이터 수집 후속 | 0% (C) | 의도적 보류 (수동 시드, Gemini 확장, 뉴스 축적, 유료 API) |

**전체 구현률: 약 88% (Phase 0~5 핵심 + Redesign V1 + DC-2 기준)**

---

## 문서별 상태 테이블

### `docs/chain_sight/plan/` 루트 문서

| 문서 | 분류 | 상태 | 매핑되는 task_done | 비고 |
|------|------|------|---------------------|------|
| `chain_sight_roadmap_v1.3.md` | 마스터 | A 완전 구현 | (메타 문서) | Phase 0~3 + 4 + DC-2 모두 진행 완료 — 본문 참조 |
| `relation_confidence_design_v1.md` | Phase 2 상세 | A 완전 구현 | CS-2-4 | RelationConfidence v2.1 (truth/market_score, 5단계, evidence_tier_best, neo4j_dirty, previous_status) 전부 모델·태스크에 반영 |
| `remaining_work_plan.md` | 진행 계획 | (참고) | — | 2026-04-04 기준 잔여 계획 — Frontend cs_5/CS-5-4 일부, Peer Phase 6~7은 미착수 |
| `sec_pipeline_base_design.md` | SEC 파이프라인 | (별도 앱) | — | `sec_pipeline/` 앱이 별도로 구현됨, Chain Sight 직접 의존 아님 |
| `sec_pipeline_pr_detail.md` | SEC 파이프라인 | (별도 앱) | — | 동일 |

### Phase 0~4 상세 문서 (cs_*.md)

| 문서 | 분류 | task_done | 코드 위치 | 비고 |
|------|------|-----------|-----------|------|
| `cs_00_legacy_cleanup_api_test.md` | A | CS-0-0 | (정리됨) | serverless Chain Sight 6 view + 3 service 제거. ETF 모델은 LEGACY_KEEP_UNTIL_DC2 |
| `cs_01_migrations_verification.md` | A | CS-0-1 | `chainsight/migrations/0001~0007*.py` | 12 테이블 + 후속 추가(SavedPath, SeedSnapshot 포함) |
| `cs_02_neo4j_connection.md` | A | CS-0-2 | `chainsight/graph/repository.py` | PID-safe lazy driver, Protocol 인터페이스 |
| `cs_03_neo4j_schema.md` | A | CS-0-3 | `chainsight/graph/schema.py` + `management/commands/init_neo4j_schema.py` | 4 constraint + 4 index |
| `cs_11_stock_node_bulk_load.md` | A | CS-1-1 | `management/commands/load_stocks_to_neo4j.py` | 532 :Stock 노드 |
| `cs_12_sector_industry.md` | A | CS-1-2 | `management/commands/load_sectors_to_neo4j.py` | :Sector 18 + :Industry 131 |
| `cs_13_peer_relations.md` | A | CS-1-3 | `chainsight/tasks/peer_tasks.py` + `services/neo4j_loader.py` | PEER_OF 2,816 |
| `cs_21_tier_a_profile.md` | A | CS-2-1 | `chainsight/tasks/profile_tasks.py` | GrowthStage 480 + CapitalDNA 473 |
| `cs_21b_sensitivity_profile.md` | **B 부분 구현** | CS-2-1b | `chainsight/tasks/sensitivity_tasks.py` | 모델/태스크 OK, **Beat 미등록** (수동 실행) |
| `cs_21c_insider_signal.md` | **B 부분 구현** | CS-2-1c | `chainsight/tasks/insider_tasks.py` | 모델/태스크 OK, **Beat 미등록** + Finnhub 기관 데이터 부재로 bullish=0 |
| `cs_22_co_mention.md` | A | CS-2-2 | `chainsight/tasks/relation_tasks.py::extract_co_mentions` | 744 페어 추출 |
| `cs_23_price_co_movement.md` | A | CS-2-3 | `relation_tasks.py::calculate_price_co_movement` | 2,748 PEER_OF 페어 계산 |
| `cs_24_relation_confidence.md` | A | CS-2-4 | `relation_tasks.py::update_relation_confidence` + `models/relation_discovery.py` | v2.1 정책표 기반 판정 3,527 레코드 |
| `cs_25_chain_profile_aggregation.md` | A | CS-2-5 | `chainsight/tasks/sync_tasks.py::aggregate_chain_profiles` | 503 레코드 |
| `cs_31_profile_neo4j_sync.md` | A | CS-3-1 | `sync_tasks.py::sync_profiles_to_neo4j` | 503/503 동기화 |
| `cs_32_relation_neo4j_sync.md` | A | CS-3-2 | `sync_tasks.py::sync_relations_to_neo4j` + `services/neo4j_sync.py::sync_dirty_relations` | RELATED_TO 1,631 엣지 (confirmed+probable) |
| `cs_33_gds_algorithms.md` | **B 부분 구현** | CS-3-3 | (Neo4j Cypher 외부 실행) | PageRank + Betweenness만 노드 속성으로 사용. **Louvain 미구현**, **Celery 태스크 부재** (수동 트리거 가정) |
| `cs_41_graph_api.md` | A | CS-4-1 | `chainsight/api/views.py::ChainSightGraphView` | depth 1~3 |
| `cs_42_suggestion_api.md` | A | CS-4-2 | `chainsight/api/views.py::ChainSightSuggestionView` | peers/industry/co-mention/sector |
| `cs_43_trace_api.md` | A | CS-4-3 | `chainsight/api/views.py::ChainSightTraceView` | shortestPath |

### Phase 5 (Frontend) — 원안 cs_5*.md vs 신안 cs_5_frontend_design_v2.md

| 문서 | 분류 | 상태 | 비고 |
|------|------|------|------|
| `cs_51_graph_visualization.md` | **D 부분 폐기/대체** | task_done CS-5-1 (cs_5_v2 기준) | 원안의 단순 GraphView → cs_5_v2의 3-panel 워크스페이스로 흡수. GraphCanvas 구현은 cs_5_v2 기준 |
| `cs_52_ai_guide_ui.md` | **D 부분 폐기/대체** | task_done CS-5-2 (cs_5_v2 기준) | 원안의 SuggestionCards → cs_5_v2의 AIGuidePanel + CategoryCard로 흡수 |
| `cs_53_chain_trace_ui.md` | **D 부분 폐기/대체** | task_done CS-5-3 (cs_5_v2 기준) | 원안의 TraceView → cs_5_v2의 TracePanel + TracePathView로 흡수 |
| `cs_54_stock_detail_integration.md` | **B 부분 구현** | (task_done 부재) | 미니 뷰는 `GraphMiniView.tsx` 존재 ✅. 그러나 redesign V1이 요구한 "탭 제거 → /chainsight?focus= 딥링크"는 **미반영** (탭 잔존) |
| `cs_5_frontend_design_v2.md` | A 완전 구현 | CS-5-1~5-3 | Deep dive workspace `/chainsight/[symbol]`. GraphCanvas, AIGuidePanel, NodeDetailPanel, FilterPanel, RelationLegend, GraphMiniView, MobileCardList, TracePathView 모두 존재 |

### `redesign_v1_260409/` (Market View V2.1/V2.2) — cs_5_v2 위에 추가 레이어

| 문서 | 분류 | task_done | 비고 |
|------|------|-----------|------|
| `chainsight_seed_node_design.md` (v2.1) | A 완전 구현 (Phase 1) | PR-2 | 시드 5종(price/volume/sector_outlier/relation/comention) + Redis 캐시 + 3단 폴백(SeedSnapshot DB + async 트리거) |
| `chainsight_api_design.md` (v2.1) | A 완전 구현 | PR-4 | 4개 엔드포인트(`/seeds/`, `/sector/<>/graph/`, `/<>/neighbors/`, `/signals/`) 모두 view + url 등록 완료 |
| `chainsight_ui_ux_design.md` (v2.2) | **B 부분 구현 (95%)** | PR-5/6/7 | 5개 컴포넌트(SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed) 모두 존재. RelationCard/SeedCard는 RelationCardPanel 내부 함수로 inline (별도 export 미분리) |
| `chainsight_marketview_pr_prompts.md` | A | PR-1~7 모두 완료 | `task_done/chain_sight_redesign_V1/00_summary.md` 기준 |

### `task_done/chain_sight_redesign_V1/` 진행 기록

| 파일 | 상태 |
|------|------|
| `00_summary.md` | 7 PR + 2 Neo4j 개선 모두 완료 (2026-04-10) |
| `PR-1_schema_migration.md` | RelationConfidence neo4j_dirty/previous_status/save() override |
| `PR-2_seed_selection_task.md` | seed_selection.py + Redis 캐시 |
| `PR-3_neo4j_dirty_sync.md` | services/neo4j_sync.py + tasks/neo4j_dirty_sync_tasks.py |
| `PR-4_market_view_api.md` | API 4종 view + url |
| `PR-5_fe_core_ui.md` | explorationStore + SectorBar + MarketGraphCanvas + useMarketView |
| `PR-6_trail_and_cards.md` | ExplorationTrail + RelationCardPanel(pre-focus/focused) |
| `PR-7_chain_story_feed.md` | ChainStoryFeed + 무한 스크롤 |
| `browser_test_report.md` | E2E 검증, 2 핫픽스 적용(`COALESCE(r.relation_type, type(r))`) |
| `data_quality_3_fixes.md` | 데이터 품질 3건 수정 |
| `qa_evaluator_review_01.md` | QA 평가자 검수 1차 |

---

## 미구현 항목 상세

### B-1. Phase 2 Tier A — Beat 스케줄 미등록 (수동 실행만 가능)

| 항목 | 모델 | 태스크 | 결함 |
|------|------|--------|------|
| SensitivityProfile | `CompanySensitivityProfile` | `chainsight/tasks/sensitivity_tasks.py::calculate_sensitivity_profiles` | `config/celery.py` Beat dict 또는 DB(`PeriodicTask`)에 미등록 — **자동 갱신 안 됨** |
| InsiderSignal | `CompanyInsiderSignal` | `chainsight/tasks/insider_tasks.py::calculate_insider_signals` | 동일 — Beat 미등록 |

**영향**: 두 모델 모두 일회성 백필 데이터 그대로. 신규 종목/시간 경과에 따른 자동 업데이트 미작동.

> 참고: 로드맵 v1.3 §3 Phase 2 Beat 스케줄 표에는 6개 태스크 명시(co-mention, profiles, price-comovement, relation-confidence, stale-decay, chain-profile). Sensitivity/Insider는 `calculate_all_profiles`에 묶이지 않은 별도 태스크 → **추가 등록 필요**.

### B-2. Phase 3 GDS — 일부만 구현

- ✅ **PageRank**: `pagerank_score` 노드 속성으로 path_service에서 사용 중
- ✅ **Betweenness Centrality**: `betweenness_score` 노드 속성 사용 중
- ❌ **Louvain (community detection)**: 코드/속성 미사용
- ❌ **Celery 태스크 부재**: GDS 알고리즘을 주기적으로 재실행하는 태스크 없음 (외부 Cypher 수동 트리거 가정)

> 로드맵 v1.3 §3 CS-3-3는 "pagerank, community_id, betweenness 노드 속성"을 모두 산출 기준으로 명시했으나 **community_id (Louvain)** 채널은 누락.

### B-3. CS-5-4 Stock Detail Integration — 부분만 구현

cs_54 + cs_5_v2 §7이 정의한 종목 상세 통합:

| 요구 | 구현 상태 |
|------|----------|
| 종목 상세 Chain Sight 탭에 미니 그래프 임베드 | ✅ `frontend/components/chainsight/GraphMiniView.tsx` + 동적 임포트 |
| 미니 그래프 정적 (zoom/pan 비활성) | ✅ |
| 연결 종목 태그 + 프로파일 요약 | ⚠️ 일부 (확인 필요) |
| **Redesign V1: 탭 제거 → `/chainsight?focus={symbol}` 딥링크** | ❌ **미반영** — `frontend/app/stocks/[symbol]/page.tsx`에 chain-sight 탭 잔존 |

> Redesign V1 ui_ux 문서 §11이 명시한 "탭 제거"가 미실행. 이 두 설계는 상충 — **결정 필요**: cs_5_v2(탭 유지) vs redesign V1(탭 제거).

### B-4. Frontend 컴포넌트 모듈 분리 미완

설계서가 별도 컴포넌트로 명시한 것이 다른 컴포넌트 내부 함수로만 존재:

| 설계서 컴포넌트 | 실제 위치 | 상태 |
|------|-----------|------|
| `CategoryCard.tsx` (cs_5_v2 §4) | `AIGuidePanel.tsx` 내부 인라인 | ⚠️ 미분리 |
| `TracePanel.tsx` (cs_5_v2 §4) | `AIGuidePanel.tsx` 하단 인라인 | ⚠️ 미분리 |
| `RelationCard.tsx` (redesign V1 §12) | `RelationCardPanel.tsx::RelationCard()` 내부 함수 | ⚠️ 미분리 |
| `SeedCard.tsx` (redesign V1 §12) | `RelationCardPanel.tsx::SeedCardList()` 내부 함수 | ⚠️ 미분리 |
| `ChainStoryCard.tsx` (redesign V1 §12) | `ChainStoryFeed.tsx` 내부 인라인 | ⚠️ 미분리 |

기능은 모두 작동. 리팩토링 영역의 미수행 항목.

### C-1. 데이터 수집 후속 단계 (DC-3~6) — 의도적 미진행

| 항목 | 상태 | 사유 |
|------|------|------|
| DC-3 수동 시드 JSON Supply Chain | C 미구현 | 우선순위 후순위, 수익화 이후 검토 |
| DC-4 Gemini Flash 확장 | C 미구현 | DC-3 후속 |
| DC-5 Marketaux 뉴스 자연 축적 | 부분 진행 | News Intelligence Pipeline v3 별도 운영 — Chain Sight CoMention과 일부 연동 |
| DC-6 Finnhub Premium | C 미구현 | "수익화 이후" 명시 |

`remaining_work_plan.md` 기준 **명시적 보류**. 기능 갭이 아닌 비즈니스 결정.

### C-2. 미구현 부가 기능 (Phase 5+ Pro)

cs_5_v2 §6 "프로 투자자 기능" 중:

| 기능 | 상태 |
|------|------|
| 필터 패널 (관계 타입, confidence, 섹터) | ✅ `FilterPanel.tsx` 존재 |
| 노드 메트릭 오버레이 토글 (PER, 시총, Centrality, 커뮤니티) | ❌ 미구현 — 컴포넌트/UI 부재 |
| 노드 비교 모드 (Ctrl+Click, 두 종목 표 비교) | ❌ 미구현 |

→ Pro 모드 § 부분만 부분 구현. UI/UX 측면 후속 작업.

### C-3. 2차 카드 설명 + LLM 보조 텍스트

redesign V1 ui_ux §9 "카드 설명 필드 전략" 단계:
- 1차 (프론트 템플릿): ✅ 구현
- 2차 (`relation_summary`/`why_now`/`insight_summary` API 필드): ❌ 미구현
- LLM 기반 explanation: ❌ 미구현 — 명시적 Future enhancement

---

## 폐기/대체 항목

### D-1. cs_51~54 (Phase 5 원안) → cs_5_frontend_design_v2 (3-panel Deep dive)

| 원안 항목 | 폐기/대체 결과 |
|-----------|----------------|
| `GraphView.tsx` (cs_51) | `GraphCanvas.tsx`로 대체 (라이브러리 동일 react-force-graph-2d) |
| `SuggestionCards.tsx` (cs_52) | `AIGuidePanel.tsx`로 통합 (좌측 패널 일부) |
| `TraceView.tsx` (cs_53) | `TracePathView.tsx` + `AIGuidePanel.tsx::TracePanel` 인라인 |
| `ChainSightMiniView.tsx` (cs_54) | `GraphMiniView.tsx`로 대체 (네이밍 변경, 기능 동일) |

> task_done의 CS-5-1/5-2/5-3는 **원안 cs_51~53이 아닌 cs_5_v2 기준**으로 작성됨. 원안 cs_51~54.md는 사실상 폐기 상태이며, 단지 plan 디렉토리에 잔존 중.

### D-2. cs_5_frontend_design_v2 의 마켓 탐색 영역 → redesign_v1_260409 으로 분리

cs_5_v2는 `/chainsight/[symbol]` Deep dive 워크스페이스 중심이지만 redesign V1은 **`/chainsight` 마켓 뷰**를 새로 추가:

| 영역 | cs_5_v2 | redesign_v1_260409 |
|------|---------|--------------------|
| `/chainsight/[symbol]` Deep dive | ★ 정식 (유지) | (재사용) |
| `/chainsight` 마켓 뷰 | (정의 없음) | ★ 신규 정의 (5-section + Zustand) |
| 종목 상세 Chain Sight 탭 | 미니 뷰 + 전체 탐색 링크 | **탭 제거 + `?focus=` 딥링크** |

→ 두 설계는 **상호 보완**적이지만, "종목 상세 탭" 영역에서 **상충**. 현재 코드는 cs_5_v2 정책(탭 유지) 따름.

### D-3. CompanyChainProfile JSONB → 30개 개별 필드

로드맵 v1.1이 `profile_data (JSONB)` 단일 필드로 제안 → v1.2/v1.3에서 **개별 필드 구조 유지**로 정정 (원칙 4 부합). `chainsight/models/chain_profile.py`는 개별 필드.

### D-4. CUSTOMER_OF 별도 저장 → SUPPLIES_TO canonical + API 파생

로드맵 v1.3 변경: CUSTOMER_OF는 DB 미저장, View에서 `direction == 'outbound'` 시 파생. 코드도 동일(`api/views.py::_display_type` + `_derive_display_type`).

### D-5. RelationConfidence 3단 상태 → 5단 상태

기존 `confirmed/candidate/rejected` → `hidden/weak/probable/confirmed/stale` 5단계 상태 체계로 전환 (relation_confidence_design_v1 + 로드맵 v1.3). 모델 + 태스크 + sync 로직 모두 5단 기준 작동.

---

## 설계서 외 추가 구현 (Extras — 설계 미언급 / 사후 추가)

| 영역 | 위치 | 비고 |
|------|------|------|
| **워치리스트 / 저장 경로** | `chainsight/models/saved_path.py` (SavedPath, PathAction) + `views/watchlist_views.py` + `serializers/path_watchlist.py` + `services/{path_service,expand_service,alternatives_service,recheck_service}.py` + `frontend/app/chainsight/watchlist/` + `frontend/components/chainsight/{PathCard,FullPathView,WatchButton}.tsx` | 설계서 어디에도 없음 — Phase 6+ 기능으로 사후 추가 추정. 마이그레이션 0006로 도입 |
| **SeedSnapshot DB 영속화** | `models/seed_snapshot.py` + `_get_today_seeds()` 3단 폴백 | 운영 안정성 보강. pytest Redis flush 이슈(common-bugs #27) 대응 |
| **Heat Score 사전 스크리닝** | `tasks/seed_tasks.py::calculate_heat_scores` + Beat `chainsight-heat-score-daily` | redesign V1 시드 노드 설계 Phase 2 항목 — 부분 선구현 |
| **Daily Neo4j 동기화 태스크 2종** | `sync_profiles_to_neo4j` (Daily 12:00) + `sync_relations_to_neo4j` (Daily 12:30) | 로드맵 표는 주 1회 — 일 1회로 강화 |
| **Beat 드리프트 복구 노트** | `config/celery.py` 주석 (2026-04-24) | DatabaseScheduler dict drift 대응 (common-bugs #28) |

---

## 합의 필요 결정 사항 (Open Issues)

1. **종목 상세 Chain Sight 탭의 운명**: cs_5_v2(탭 유지 + 미니뷰) vs redesign V1(탭 제거 + 딥링크). 현재 코드는 전자, 설계서는 후자가 신안. → 결정 + 미반영 시 cs_5_v2 §7을 deprecated로 마킹 필요.
2. **SensitivityProfile / InsiderSignal Beat 등록**: `remaining_work_plan.md`의 "Celery Beat 일괄 등록 (1시간)" 항목이 미완료. → DatabaseScheduler에 PeriodicTask 등록 필요.
3. **Louvain GDS 채널**: 로드맵 v1.3 §2.4 노드 속성 `community_id` 누락. 사용처 없음 → 설계 후퇴인지, 후속 추가인지 결정 필요.
4. **컴포넌트 모듈 분리**: RelationCard/SeedCard/CategoryCard/TracePanel을 별도 파일로 분리할지 — 기능 영향 없음, 유지보수성만 영향. PR 우선순위 낮음.
5. **DC-3~6 데이터 확장 진입 시점**: `remaining_work_plan.md` 기준 보류 중. M5 도달 후 트리거 시점 명문화 필요.

---

## 결론

Chain Sight는 **로드맵 v1.3 + relation_confidence_design v1 + redesign V1 (260409) 3축 설계**가 핵심이며, 그 중 **백엔드 파이프라인(Phase 0~4)과 redesign V1 마켓 뷰는 모두 구현 완료** 상태. 갭은 (1) Tier A 2종 Beat 미등록, (2) Louvain 미구현, (3) Stock 상세 탭/딥링크 정책 미정, (4) Phase 5 Pro 기능 일부 미구현, (5) 컴포넌트 모듈 분리 리팩토링 보류, (6) DC-3~6 의도적 보류. **기능 결손은 적고, 운영/정책 결정 필요 항목이 다수.**

> 원안 cs_51~54.md 4건은 cs_5_frontend_design_v2.md로 대체된 사실상 폐기 문서이므로, plan 디렉토리에서 정리(아카이브 또는 deprecation 헤더 추가)하는 것이 권장됨.
