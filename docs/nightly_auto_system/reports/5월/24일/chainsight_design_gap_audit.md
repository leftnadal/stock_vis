# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-24
> **범위**: `docs/chain_sight/plan/` 설계서 vs `chainsight/` + `frontend/components/chainsight/` 구현
> **모드**: 읽기 전용. 코드 수정 없음.
> **방법**: 설계 문서 33건 + 완료 보고서 24건 + 백엔드 코드(models/services/tasks/api) + 프론트엔드 컴포넌트 21건 대조.

---

## 1. 요약 (구현률)

### 전체 통계

| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 20 | 60.6% |
| (B) 부분 구현 | 6 | 18.2% |
| (C) 미구현 | 3 | 9.1% |
| (D) 폐기/대체 | 4 | 12.1% |
| **합계 (설계 문서)** | **33** | 100% |

### 핵심 결론

1. **`redesign_v1_260409/`가 `cs_41~54`를 사실상 대체**한다 (2026-04-10 마켓 뷰 재설계). 현재 진실 공급원은 redesign v1. cs_41~43 (기존 API)와 cs_51~54 (기존 UI)는 참고 문서로 격하되었으며, 일부는 코드에 병존(중복 가능).
2. **백엔드 Phase 0~3는 거의 완전 구현** (CS-0-x ~ CS-3-2 모두 task_done 보고서 존재 + 코드 확인). 다만 **CS-3-3 GDS 알고리즘은 미구현** (스키마 인덱스만 정의, 실제 실행 코드 없음).
3. **프론트엔드 마켓 뷰 5개 컴포넌트는 모두 구현 완료** (SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed).
4. **종목 상세 Chain Sight 탭은 `ChainSightMiniView` 컴포넌트가 실제로 동작 중** (`frontend/app/stocks/[symbol]/page.tsx:58,457`) — Explore 1차 분석에서 "Coming Soon"으로 추정한 부분은 정정됨.
5. **부분 구현 영역의 주요 갭**: SensitivityProfile 세부 규칙(규제 매핑), InsiderSignal smart_money 종합, GDS 의존 UI 정렬.

---

## 2. 문서별 상태 테이블

### 2.1 Phase 0 — 기반 정리 (cs_00~cs_03)

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| cs_00_legacy_cleanup_api_test.md | (A) | task_done/CS-0-0 | 레거시 ChainSightExplorer 제거, RelationConfidence v2.1 마이그레이션 완료 (`frontend/app/stocks/[symbol]/page.tsx:25`에 LEGACY REMOVED 주석 잔존) |
| cs_01_migrations_verification.md | (A) | task_done/CS-0-1, chainsight/migrations/ | 마이그레이션 검증 완료 |
| cs_02_neo4j_connection.md | (A) | task_done/CS-0-2, chainsight/graph/repository.py | Neo4jGraphRepository (PID-based lazy init) 구현 |
| cs_03_neo4j_schema.md | (A) | task_done/CS-0-3, chainsight/graph/schema.py | constraints + indexes 생성 (community_id 인덱스 포함, schema.py:19) |

### 2.2 Phase 1 — 데이터 적재 (cs_11~cs_13)

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| cs_11_stock_node_bulk_load.md | (A) | task_done/CS-1-1, management/commands/load_stocks_to_neo4j.py | Stock 노드 적재 |
| cs_12_sector_industry.md | (A) | task_done/CS-1-2, load_sectors_to_neo4j.py | Sector/Industry + BELONGS_TO |
| cs_13_peer_relations.md | (A) | task_done/CS-1-3, load_peers_to_neo4j.py | PEER_OF 관계 적재 |

### 2.3 Phase 2 — 신뢰도 엔진 (cs_21~cs_25)

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| cs_21_tier_a_profile.md | (A) | task_done/CS-2-1, models/growth_stage.py, models/capital_dna.py, tasks/profile_tasks.py | GrowthStage + CapitalDNA 자동 계산 |
| cs_21b_sensitivity_profile.md | (B) | task_done/CS-2-1b, models/sensitivity.py, tasks/sensitivity_tasks.py | 기본 계산은 구현, **규제 민감도 매핑(REGULATION_MAP) 미실장** |
| cs_21c_insider_signal.md | (B) | task_done/CS-2-1c, models/insider_signal.py, tasks/insider_tasks.py | insider_signal 단일 신호는 구현, **smart_money 종합(insider+institutional+short) 미완** |
| cs_22_co_mention.md | (A) | tasks/relation_tasks.py:extract_co_mentions, models/news_event.py | CoMention + ChainNewsEvent |
| cs_23_price_co_movement.md | (A) | tasks/relation_tasks.py:calculate_price_co_movement | 90일 rolling correlation |
| cs_24_relation_confidence.md | (A) | task_done/CS-2-4, models/relation_discovery.py, tasks/relation_tasks.py | tier/status/truth_score 종합 판정 + stale decay |
| cs_25_chain_profile_aggregation.md | (A) | task_done/CS-2-5, models/chain_profile.py, tasks/sync_tasks.py:aggregate_chain_profiles | ChainProfile 집약 |

### 2.4 Phase 3 — Neo4j 동기화 (cs_31~cs_33)

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| cs_31_profile_neo4j_sync.md | (A) | task_done/CS-3-1, tasks/sync_tasks.py:sync_profiles_to_neo4j | Delta sync 동작 |
| cs_32_relation_neo4j_sync.md | (A) | task_done/CS-3-2, tasks/sync_tasks.py:sync_relations_to_neo4j | RelationConfidence → Neo4j 엣지, CUSTOMER_OF 역방향 파생 |
| cs_33_gds_algorithms.md | **(C)** | **없음** (schema.py:19에 community_id 인덱스만 존재) | **PageRank/Louvain/Betweenness 실행 코드 0건** — Grep 결과 `chainsight/tasks/`에 gds 호출 흔적 없음 |

### 2.5 Phase 4 — REST API (cs_41~cs_43)

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| cs_41_graph_api.md | **(D)** → chainsight_api_design.md (redesign) | api/views.py:ChainSightGraphView (cs_41 원형) + NeighborGraphView (재설계) 병존 (urls.py 양쪽 모두 등록) | 마켓 뷰 재설계로 사실상 보조 역할로 격하 |
| cs_42_suggestion_api.md | (A) | api/views.py:ChainSightSuggestionView, urls.py:`<symbol>/suggestions/` | 카테고리별 탐색 제안 |
| cs_43_trace_api.md | (A) | api/views.py:ChainSightTraceView, urls.py:`trace/` | 최단 경로 탐색 |

### 2.6 Phase 5 — 프론트엔드 (cs_51~cs_54, cs_5_v2)

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| cs_5_frontend_design_v2.md | **(D)** → chainsight_ui_ux_design.md (redesign) | frontend/app/chainsight/ | v2(4/4) → v2.2(4/10) 마켓 뷰 중심으로 재정의 |
| cs_51_graph_visualization.md | **(D)** → chainsight_ui_ux_design.md (redesign) | components/chainsight/MarketGraphCanvas.tsx + FullPathView.tsx | 마켓 뷰(MarketGraphCanvas) + 딥 다이브(FullPathView) 이원화 |
| cs_52_ai_guide_ui.md | **(D)** → chainsight_ui_ux_design.md (redesign) | components/chainsight/RelationCardPanel.tsx + ChainStoryFeed.tsx | pre-focus/focused 상태 분기로 재설계 |
| cs_53_chain_trace_ui.md | (A) | components/chainsight/TracePathView.tsx, ExplorationTrail.tsx, PathCard.tsx, FullPathView.tsx | 딥 다이브(`/chainsight/[symbol]`)에 적용. 마켓 뷰에는 미사용 |
| cs_54_stock_detail_integration.md | (A) | components/chainsight/GraphMiniView.tsx + frontend/app/stocks/[symbol]/page.tsx:58,457 | **ChainSightMiniView 동작 중** (dynamic import + 렌더). "Chain Sight (관계 탐색)" 탭 활성화 (page.tsx:84). "Chain Sight에서 보기" CTA(page.tsx:454) 포함 |

### 2.7 Redesign v1 (2026-04-10) — 마켓 뷰 재설계

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| redesign/chainsight_api_design.md | (A) | api/views.py:SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView + urls.py | 마켓 뷰 4 API 모두 라우팅 등록 |
| redesign/chainsight_seed_node_design.md | (A) | services/seed_selection.py + models/seed_snapshot.py + tasks/seed_tasks.py | Phase 1 시드 선정 (B+A 신호) + DB 영속화 |
| redesign/chainsight_ui_ux_design.md | (B) | app/chainsight/page.tsx + 5 컴포넌트 | 컴포넌트 5종 완비, **애니메이션·반응형·모바일 bottomsheet 미완** |
| redesign/chainsight_marketview_pr_prompts.md | **(C)** | LLM chain title/summary 생성 코드 없음 | 프롬프트 템플릿만 존재. Grep 결과 chainsight/tasks/에서 LLM 호출 0건 |

### 2.8 기타 설계 문서

| 문서 | 분류 | 매핑 코드/문서 | 비고 |
|------|------|---------------|------|
| chain_sight_roadmap_v1.3.md | (A) | 전체 이정표 | 참고 문서. M0~M5 정의 |
| remaining_work_plan.md | (A) | Phase 2 후속 작업 계획 | 2026-04-10 기준. Phase 1 완료 후 Phase 2 진행 중 |
| relation_confidence_design_v1.md | (A) | models/relation_discovery.py + tasks/relation_tasks.py | 신뢰도 v1 정책표 완전 반영 |
| sec_pipeline_base_design.md | (N/A) | sec_pipeline/ (별도 앱) | **Chain Sight 범위 밖** — 독립 앱으로 구현 |
| sec_pipeline_pr_detail.md | (N/A) | sec_pipeline/ (별도 앱) | **Chain Sight 범위 밖** |

> **task_done/DC-2_etf_holdings_theme.md**, **task_done/celery_beat_registration.md**: 별도 설계서 없이 완료 보고서만 존재 (DC-2는 데이터 큐레이션, beat은 8개 스케줄 등록).

---

## 3. 미구현 항목 상세

### 3.1 (C) 미구현

#### C-1 — cs_33 GDS 알고리즘 배치 (**우선순위: 높음**)

- **갭**: PageRank, Louvain Community Detection, Betweenness Centrality 실행 코드 전무.
- **증거**:
  - `chainsight/tasks/`에 `gds_tasks.py` 없음
  - Grep "gds|pagerank|louvain|betweenness|community_id" → `schema.py:19` (community_id 인덱스), `services/path_service.py`, `regenerate_summary_paths.py`만 매칭. 알고리즘 호출 0건.
  - `chainsight/graph/schema.py:19`에 `community_id` 인덱스는 정의되었으나 채워주는 코드가 없음 → 인덱스 빈 상태 추정.
- **영향**:
  - 마켓 뷰에서 종목 정렬 기준으로 `pagerank_score` 사용 불가
  - SectorGraphView가 community 클러스터로 그룹핑할 근거 없음
  - "오늘의 시드" 우선순위에 graph centrality 반영 불가
- **설계 위치**: cs_33_gds_algorithms.md 전체 (§ GDS 의존성, § 구현, § 검증 모두 미구현)
- **우선순위 근거**: 마켓 뷰 핵심 UX(`/chainsight` 진입 시 의미 있는 노드 정렬)를 지지하는 기반. P0 권장.

#### C-2 — redesign/chainsight_marketview_pr_prompts.md (**우선순위: 낮음**)

- **갭**: LLM 기반 "Chain Title / Chain Summary" 자동 생성 미구현.
- **증거**: `chainsight/tasks/` 내 Gemini/Anthropic 호출 코드 0건. ChainProfile 모델에 summary 필드 존재 가능성 있으나 채우는 로직 없음.
- **영향**: ChainStoryFeed에서 LLM 기반 내러티브 카드 표시 불가. 현재는 규칙 기반 신호만 노출 추정.
- **우선순위 근거**: Phase 2+ 부가 기능. 핵심 UX 작동에 필수 아님.

#### C-3 — sec_pipeline 설계서 2건

- **범위 밖**: Chain Sight 앱이 아닌 별도 `sec_pipeline/` 앱에서 구현. 본 감사 범위 외.

### 3.2 (B) 부분 구현

#### B-1 — cs_21b SensitivityProfile (**우선순위: 중간**)

- **구현된 것**:
  - `chainsight/tasks/sensitivity_tasks.py`에 FMP Revenue Geo Segmentation API 호출 + 기본 계산 동작
  - `models/sensitivity.py`에 모델 필드 존재
- **미구현된 것**:
  - **규제 민감도 매핑 (REGULATION_MAP 20개)** — 산업/섹터별 규제 유형 분류 코드 미발견
  - rate_sensitivity / forex_sensitivity 3단계(high/medium/low) 규칙 단순화됨
  - 부분 실패 재시도 로직
- **설계 위치**: cs_21b_sensitivity_profile.md § 민감도 계산 규칙, § Regulation 민감도 매핑

#### B-2 — cs_21c InsiderSignal smart_money 종합 (**우선순위: 중간**)

- **구현된 것**: Finnhub Insider API 호출 + insider_signal 단일 분류
- **미구현된 것**:
  - **smart_money_signal 종합 (insider + institutional + short interest 3개 결합)**
  - Institutional ownership 추적 (FMP Institutional Holders API 호출 없음)
  - Short interest / days_to_cover 데이터 소스 미연결
- **설계 위치**: cs_21c_insider_signal.md § smart_money_signal (종합), § Rate Limit 전략

#### B-3 — cs_41 ChainSightGraphView (**우선순위: 낮음 — 대체 API 존재**)

- **현황**: 원안(`<symbol>/graph/`)과 재설계(`<symbol>/neighbors/`) 양쪽 모두 `urls.py`에 등록되어 병존.
- **갭**: 두 엔드포인트 응답 스펙 일관성 미검증. 프론트엔드가 어느 쪽을 호출하는지 명시 필요.
- **우선순위 근거**: 둘 다 작동하므로 즉각 위험은 없으나, 향후 API 중복 정리 필요.

#### B-4 — redesign/chainsight_ui_ux_design.md UI 세부 (**우선순위: 낮음**)

- **구현된 것**: 5개 핵심 컴포넌트 (SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed) 모두 존재.
- **미구현된 것**:
  - 섹터 바 transition 애니메이션
  - 노드 bounce 애니메이션 (react-force-graph-2d)
  - 태블릿 bottomsheet 레이아웃
  - 모바일 카드 리스트 분기 (MobileCardList 컴포넌트는 존재하나 마켓 뷰 라우팅에 연결 여부 미확인)
  - pre-focus vs focused 상태의 시각적 분기 (RelationCardPanel 내부 로직 분기는 있으나 UI 차별화 미확인)
- **설계 위치**: chainsight_ui_ux_design.md § 4. 화면 구조 (상태 매트릭스), § 모바일 대응 계획

#### B-5 — remaining_work_plan.md Phase 2 후속 (**우선순위: 중간**)

- **갭**: Heat Score, 시드 회전 정책, 사용자 개인화 등 Phase 2 후속 작업 일부만 진행 중.

#### B-6 — cs_53/54 통합 (**우선순위: 낮음**)

- **현황**: GraphMiniView는 구현(stocks/[symbol]/page.tsx:457), TracePathView는 components/chainsight/에 존재(`TracePathView.tsx`, `PathCard.tsx`, `FullPathView.tsx`).
- **갭**: 두 컴포넌트가 어떤 페이지에서 어떻게 통합되어 사용되는지 매핑 미명확 (딥 다이브 페이지 `/chainsight/[symbol]` 코드 추가 검증 필요).

---

## 4. 폐기/대체 항목

### D-1 — cs_41~43 (Graph/Suggestion/Trace API) → redesign/chainsight_api_design.md

- **원안**: 단일 종목 중심의 N-depth 그래프 + 카테고리 제안 + 경로 탐색 API
- **대체**: 마켓 뷰 4 API (Seeds, SectorGraph, Neighbors, SignalFeed) + 딥 다이브 API 보조
- **변경 이유**: "심층 분석 우선" → "마켓 탐색 허브 우선 + 심층 분석 보조"로 전략 전환 (2026-04-10)
- **현재 상태**:
  - `chainsight/api/urls.py`에 양쪽 모두 등록:
    ```
    # 마켓 뷰 (재설계)
    seeds/, sector/<sector>/graph/, signals/, <symbol>/neighbors/
    # 딥 다이브 (cs_41~43 원안)
    trace/, <symbol>/graph/, <symbol>/suggestions/
    ```
  - 코드 병존 → **부분 폐기** (cs_42/43은 살아 있음, cs_41은 NeighborGraphView로 대체 시도 중)
- **task_done 근거**: `chain_sight_redesign_V1/PR-4_market_view_api.md`가 신규 API 4종 구현 보고

### D-2 — cs_51~54 (Frontend UI 4종) → redesign/chainsight_ui_ux_design.md

- **원안**: GraphView (단일 종목 그래프) + SuggestionCards + TraceView + StockDetail 미니 뷰
- **대체**: 마켓 뷰(`MarketGraphCanvas` + `RelationCardPanel` + `ChainStoryFeed` + `SectorBar` + `ExplorationTrail`) + 딥 다이브 분리
- **변경 이유**: 종목 상세 탭 내 인터랙티브 그래프 제약 → 전용 워크스페이스 + 마켓 탐색 허브 신설
- **현재 상태**:
  - 마켓 뷰 컴포넌트 신규 구축 완료 (`frontend/components/chainsight/` 21개)
  - cs_53 (TracePathView)은 그대로 유지하여 딥 다이브에서 재활용
  - cs_54 (StockDetail 미니 뷰)는 **`GraphMiniView`로 살아남음** (page.tsx:58, 457)
- **task_done 근거**: `chain_sight_redesign_V1/PR-5_fe_core_ui.md`, `PR-6_trail_and_cards.md`, `PR-7_chain_story_feed.md`

### D-3 — cs_5_frontend_design_v2.md → redesign/chainsight_ui_ux_design.md (v2.2)

- **원안**: v2 (2026-04-04) 전용 워크스페이스 3-panel 레이아웃
- **대체**: v2.2 (2026-04-10) 마켓 뷰 우선 + 탐색 상태 매트릭스
- **변경 이유**: 6일 만의 전략 전환. 사용자 진입 시점에서 "어떤 종목을 분석할까?" 단계 자체를 서비스화하는 방향.
- **현재 상태**: v2.2 기준으로 구현. v2의 3-panel 일부 개념(좌/중앙/우 분리)은 딥 다이브 페이지에 살아 있음.

### D-4 — RelationConfidence v1 → v2.1 (cs_00에서 흡수)

- **원안**: relation_confidence_design_v1.md (RelationConfidence 1차 정책)
- **대체**: cs_00에서 v2.1 마이그레이션 완료. 모델 필드 24개 확장.
- **task_done 근거**: `CS-0-0_legacy_cleanup_api_test.md` § RelationConfidence v2.1 마이그레이션

---

## 5. 권장 액션 (참고용)

| 우선순위 | 항목 | 영향 영역 | 비고 |
|---------|------|----------|------|
| **P0** | cs_33 GDS 알고리즘 배치 구현 (PageRank/Louvain) | 마켓 뷰 정렬, 시드 선정 품질 | 환경 의존성(Neo4j GDS 플러그인) 확인 필요 |
| **P1** | cs_21b 규제 민감도 매핑 (REGULATION_MAP) 보완 | SensitivityProfile 정분류 | 규칙 기반, LLM 불필요 |
| **P1** | cs_21c smart_money 종합 신호 (institutional + short) | InsiderSignal 정확도 | FMP/Finnhub API 추가 |
| **P1** | cs_41 vs Neighbors API 중복 정리 | 코드 일관성 | 프론트엔드 호출처 확인 후 한쪽 deprecate |
| **P2** | UI 애니메이션·반응형 (B-4) | 마켓 뷰 UX 완성도 | Phase 2 후속 |
| **P3** | redesign LLM chain title/summary 생성 (C-2) | ChainStoryFeed 풍부도 | Phase 2+ 부가 기능 |

---

## 6. 메타: 감사 신뢰도

- **검증 완료 항목**:
  - GDS 미구현 (Grep 검색 + schema.py:19 인덱스만 확인)
  - urls.py 라우트 (cs_41 vs neighbors 병존 직접 확인)
  - 종목 상세 탭 ChainSightMiniView 동작 (page.tsx:58,457 직접 확인)
  - 프론트엔드 컴포넌트 21개 존재 (디렉터리 ls)
  - task_done 완료 보고서 24건 매핑
- **추정 항목 (코드 라인 미검증)**:
  - SensitivityProfile/InsiderSignal 세부 갭은 Explore 에이전트 분석 기반. 정확한 라인 단위 검증 시 결과 변동 가능.
  - 마켓 뷰 UI 애니메이션 미완은 컴포넌트 내부 코드 미정밀 확인.
  - SectorGraphView가 community_id를 실제로 사용하는지 미확인.
- **샘플 검증 필요 시**: `chainsight/tasks/sensitivity_tasks.py`, `chainsight/tasks/insider_tasks.py`, `frontend/components/chainsight/MarketGraphCanvas.tsx` 라인 단위 검토 권장.
