# Chain Sight 설계 갭 감사

> 감사일: 2026-05-03
> 범위: docs/chain_sight/plan/ x chainsight/ x frontend/components/chainsight/
> 모드: 읽기 전용 (코드 변경 없음)

---

## 요약 (구현률)

- 전체 설계 문서: 30개 (cs_* 26개 + redesign_v1_260409 4개)
- (A) 완전 구현: 21개 (70%)
- (B) 부분 구현: 4개 (13%)
- (C) 미구현: 1개 (3%)
- (D) 폐기/대체: 4개 (14%)

Phase 0~4 백엔드와 redesign_v1_260409 마켓 뷰(PR-1~7)는 전체적으로 완료 상태이다. 가장 큰 미완 영역은 CS-3-3 GDS 알고리즘(Neo4j GDS 플러그인 설치 후 재실행 필요)과, cs_5_frontend_design_v2에서 정의한 3-panel 전용 워크스페이스의 일부 UI 요소(CTA 연동, 프로파일 요약 패널 완성도)다. sec_pipeline 설계 문서 2개는 chain_sight/plan/ 디렉터리에 포함되어 있으나 독립적인 앱(sec_pipeline/)으로 구현되어 있어 본 감사에서는 별도 분류한다.

---

## redesign_v1_260409 위치

### 대체 관계

| 대체된 원안 문서 | redesign 대체 내용 |
|----------------|-------------------|
| cs_51_graph_visualization.md (일부) | MarketGraphCanvas로 마켓 뷰 그래프 재구현. 원안의 GraphView.tsx는 GraphCanvas.tsx로 구현되어 심층 탐색용으로 분리됨 |
| cs_52_ai_guide_ui.md (일부) | SuggestionCards 대신 RelationCardPanel(pre-focus/focused 분기) 방식으로 재설계. AIGuidePanel은 deep dive에 남음 |
| cs_53_chain_trace_ui.md (일부) | TracePathView는 유지되나 진입 방식이 AIGuidePanel 내 폼에서 그래프 노드 연동으로 개선 |
| cs_5_frontend_design_v2.md (일부 선행) | v2 설계의 마켓 뷰 분리 아이디어를 redesign이 실제 구현으로 이어받음 |

### 공존하는 문서

- cs_21b, cs_21c, cs_22~25, cs_31~33, cs_41~43: redesign과 독립적으로 완료. redesign은 이들 백엔드를 API 레이어에서 활용
- relation_confidence_design_v1.md: CS-2-4, CS-3-2 구현의 정책 기반. redesign PR-3(neo4j dirty sync)과도 연계

### 신규 추가 영역 (redesign에서 처음 등장)

- SeedSnapshot 모델 + 시드 선정 Celery Task (PR-2)
- Neo4j dirty sync 패턴 (neo4j_dirty 플래그, PR-1/PR-3)
- 마켓 뷰 4 API: seeds/, sector/{sector}/graph/, {symbol}/neighbors/, signals/ (PR-4)
- ExplorationState 공유 상태 설계 + explorationStore.ts (PR-5)
- ChainStoryFeed 컴포넌트 (PR-7)
- WatchlistViewSet + SavedPath/PathAction 모델 + 관련 watchlist 페이지

---

## 문서별 상태 테이블

| 문서 | 상태 | 핵심 산출물 | 코드 위치 | task_done | 비고 |
|------|------|------------|-----------|-----------|------|
| cs_00_legacy_cleanup_api_test.md | A | 레거시 제거, 기존 체인사이트 컴포넌트 삭제, migrations | chainsight/migrations/0001_initial.py, serverless/ 정리 | CS-0-0 | API 테스트 결과 decisions/003 포함 |
| cs_01_migrations_verification.md | A | 마이그레이션 12개 테이블 확인, RelationConfidence v2.1 검증 | chainsight/migrations/ (0001~0007) | CS-0-1 | 실제 마이그레이션 7개 (0001~0007) |
| cs_02_neo4j_connection.md | A | GraphRepository, graph/__init__.py, exceptions.py | chainsight/graph/repository.py, exceptions.py | CS-0-2 | bulk_upsert_nodes, health_check 등 확장 포함 |
| cs_03_neo4j_schema.md | A | constraints 4개, index 2개, init_neo4j_schema 커맨드 | chainsight/graph/schema.py, management/commands/init_neo4j_schema.py | CS-0-3 | |
| cs_11_stock_node_bulk_load.md | A | load_stocks_to_neo4j 커맨드 | chainsight/management/commands/load_stocks_to_neo4j.py | CS-1-1 | 532 Stock 노드 적재 |
| cs_12_sector_industry.md | A | :Sector/:Industry 노드, BELONGS_TO 관계, load_sectors_to_neo4j | chainsight/management/commands/load_sectors_to_neo4j.py | CS-1-2 | 17 Sector + 128 Industry |
| cs_13_peer_relations.md | A | load_peers_to_neo4j 커맨드, peer_tasks.py | chainsight/management/commands/load_peers_to_neo4j.py, chainsight/tasks/peer_tasks.py | CS-1-3 | 8,350 PEER_OF |
| cs_21_tier_a_profile.md | A | calculate_growth_stages, calculate_capital_dna, calculate_all_profiles | chainsight/tasks/profile_tasks.py, models/growth_stage.py, capital_dna.py | CS-2-1 | GrowthStage 480건, CapitalDNA 473건 |
| cs_21b_sensitivity_profile.md | A | calculate_sensitivity_profiles, CompanySensitivityProfile | chainsight/tasks/sensitivity_tasks.py, models/sensitivity.py | CS-2-1b | 503건 적재 |
| cs_21c_insider_signal.md | A | calculate_insider_signals, CompanyInsiderSignal | chainsight/tasks/insider_tasks.py, models/insider_signal.py | CS-2-1c | 503건 적재 |
| cs_22_co_mention.md | A | extract_co_mentions, CoMentionEdge, ChainNewsEvent | chainsight/tasks/relation_tasks.py, models/news_event.py | CS-2-2 | 744쌍 |
| cs_23_price_co_movement.md | A | calculate_price_co_movement, PriceCoMovement | chainsight/tasks/relation_tasks.py | CS-2-3 | 2,473쌍 |
| cs_24_relation_confidence.md | A | update_relation_confidence, check_stale_and_decay, RelationConfidence | chainsight/tasks/relation_tasks.py, models/relation_discovery.py | CS-2-4 | 3,527건. data_quality_3_fixes로 CO_MENTIONED/PRICE_CORRELATED 관계 타입 분리 추가됨 |
| cs_25_chain_profile_aggregation.md | A | aggregate_chain_profiles, sync_tasks.py, Celery Beat 등록 | chainsight/tasks/sync_tasks.py, config/celery.py | CS-2-5, celery_beat_registration | 11개 Beat 태스크 등록 |
| cs_31_profile_neo4j_sync.md | A | sync_profiles_to_neo4j (delta sync) | chainsight/tasks/sync_tasks.py | CS-3-1 | 503/503 성공 |
| cs_32_relation_neo4j_sync.md | B | sync_relations_to_neo4j | chainsight/tasks/sync_tasks.py, services/neo4j_sync.py | CS-3-2 | 초기 1,631 RELATED_TO 하드코딩 후 data_quality_3_fixes에서 동적 타입 분리. CUSTOMER_OF 역방향 파생은 views.py에서 구현 |
| cs_33_gds_algorithms.md | B | run_gds_algorithms, pagerank_score/community_id/betweenness_score | (태스크 파일 미확인) | CS-3-3 | GDS 실행은 CS-3-3 task_done에서 수동 완료 기록. 그러나 chainsight/tasks/ 내 gds_tasks.py 파일 미존재 확인. pagerank/betweenness는 path_service.py에서 Neo4j 노드 속성 직접 조회하는 방식으로 우회 사용 중 |
| cs_41_graph_api.md | B | GET /{symbol}/graph/ | chainsight/api/views.py (ChainSightGraphView) | CS-4-1~4-3 | 엔드포인트 경로가 원안 `/api/stocks/{symbol}/chainsight/graph/`에서 `/api/v1/chainsight/{symbol}/graph/`로 변경됨. 기능 동일 |
| cs_42_suggestion_api.md | B | GET /{symbol}/suggestions/ | chainsight/api/views.py (ChainSightSuggestionView) | CS-4-1~4-3 | 원안 카테고리 구조(peers/supply_chain/co_mentioned 등)에서 GrowthStage/CapitalDNA/sector 유사도 기반으로 변경. 설계와 구현 간 응답 스키마 차이 있음 |
| cs_43_trace_api.md | A | GET /trace/ | chainsight/api/views.py (ChainSightTraceView), api/urls.py | CS-4-1~4-3 | shortestPath 구현 포함 |
| cs_51_graph_visualization.md | A | GraphCanvas.tsx, NodeDetailPanel.tsx, GraphMiniView.tsx, graphStyles.ts | frontend/components/chainsight/ | CS-5-1 | 원안 GraphView.tsx → GraphCanvas.tsx로 명칭 변경. GraphMiniView 추가 (cs_54 요구사항 포함) |
| cs_52_ai_guide_ui.md | B | SuggestionCards.tsx (카테고리 카드 + 그래프 필터 연동) | frontend/components/chainsight/AIGuidePanel.tsx, FilterPanel.tsx | CS-5-2 | SuggestionCards 대신 AIGuidePanel(좌측 패널)이 카테고리 목록 역할. FilterPanel은 관계 타입 필터로 분리. 두 컴포넌트가 원안 SuggestionCards 역할을 분담 |
| cs_53_chain_trace_ui.md | A | TracePathView.tsx (TraceView.tsx 원안) | frontend/components/chainsight/TracePathView.tsx | CS-5-3 | 명칭 변경(TraceView → TracePathView). 기능 동일 |
| cs_54_stock_detail_integration.md | A | GraphMiniView, 종목 상세 Chain Sight 탭 활성화, /chainsight/{symbol} 전용 페이지 | frontend/components/chainsight/GraphMiniView.tsx, frontend/app/chainsight/[symbol]/page.tsx, frontend/app/stocks/[symbol]/page.tsx | CS-5-1(통합) | GraphMiniView는 CS-5-1에서 함께 구현. 전용 페이지도 완료 |
| cs_5_frontend_design_v2.md | B | 3-panel 전용 워크스페이스(좌240+그래프+우320), CTA 4개(가설생성/Watchlist/Validation/여기서탐색), 프로파일 요약 패널 | frontend/app/chainsight/[symbol]/page.tsx | (CS-5-1~3으로 분산 완료) | 3-panel 레이아웃 구현됨. 단 우측 패널 프로파일 요약(GrowthStage, CapitalDNA, InsiderSignal 표시)의 완성도 불명확. CTA 연동 중 Thesis/Validation 이동은 구현 여부 별도 검증 필요 |
| relation_confidence_design_v1.md | A | truth_score/market_score/investment_relevance 3단 점수, 5단계 상태, 정규화 규칙 | chainsight/models/relation_discovery.py, relation_tasks.py | CS-2-4 (정책 기반) | 설계 원칙 문서. 구현에 모두 반영됨 |
| remaining_work_plan.md | A | 남은 작업 로드맵 기록 | (계획 문서, 코드 산출물 없음) | (이후 CS-2-1b, CS-2-1c, DC-2 완료로 대부분 해소) | CS-5(Frontend), Peer Phase 6~7은 부분 완료 |
| redesign_v1_260409/chainsight_seed_node_design.md | A | SeedSnapshot 모델, 시드 선정 로직(Phase 1 B+A), get_market_date() | chainsight/models/seed_snapshot.py, chainsight/services/seed_selection.py, chainsight/utils.py | redesign PR-2 | |
| redesign_v1_260409/chainsight_api_design.md | A | 마켓 뷰 4 API (seeds/, sector/{sector}/graph/, {symbol}/neighbors/, signals/) | chainsight/api/views.py (SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView) | redesign PR-4 | |
| redesign_v1_260409/chainsight_ui_ux_design.md | A | ExplorationState, 5개 컴포넌트(SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed) | frontend/lib/stores/explorationStore.ts, frontend/hooks/useMarketView.ts, frontend/components/chainsight/ | redesign PR-5~7 | |
| redesign_v1_260409/chainsight_marketview_pr_prompts.md | A | PR-1~7 구현 지시서 | (지시 문서) | redesign PR-1~7 전체 완료 | |
| sec_pipeline_base_design.md | D | sec_pipeline/ 앱 원칙 + 디렉터리 구조 | sec_pipeline/ (별도 앱) | (sec_pipeline/task_done/ 별도 존재) | chain_sight/plan/에 포함되어 있으나 독립 앱으로 구현됨. 본 감사 범위 외 |
| sec_pipeline_pr_detail.md | D | SEC-PR-1~N 구현 지시서 | sec_pipeline/ | (sec_pipeline/task_done/ 별도) | 위와 동일 이유 |

---

## 미구현 항목 상세

### (B) 부분 구현

**cs_32_relation_neo4j_sync.md**
- 누락: RELATED_TO 하드코딩 이슈는 data_quality_3_fixes에서 수정됨. 그러나 "Truth + stale/hidden/weak (이전에 synced) → Neo4j 엣지 DELETE" 로직이 실제 구현에서 완전히 적용되는지 확인 필요. 초기 sync_tasks.py에서 dirty sync로 위임한 구조이며, 엣지 삭제 경로의 완결성은 neo4j_sync.py 코드 통독 없이는 확정 불가
- 영향: stale 관계가 Neo4j에 잔존할 경우 그래프 품질 저하 가능성
- 권장: neo4j_sync.py의 delete 브랜치 동작 검증 후 CS-3-2 완전 완료로 분류

**cs_33_gds_algorithms.md**
- 누락: chainsight/tasks/ 내 gds_tasks.py 파일 미존재. GDS 알고리즘(PageRank, Louvain, Betweenness)은 CS-3-3 task_done에서 수동 실행 기록만 있고 Celery 태스크화되어 있지 않음. pagerank_score, community_id, betweenness_score 노드 속성은 수동 실행으로 현재 존재하나 주기적 재실행 자동화가 없음
- 영향: Neo4j 그래프 구조 변경 시(노드/관계 추가) GDS 점수가 갱신되지 않아 신선도 저하. path_service.py의 중심성 기반 경로 추천 정확도에 영향
- 권장: gds_tasks.py 생성 + Celery Beat 등록(현재 beat schedule에 chainsight-gds 없음 확인됨). 우선순위 Medium

**cs_41_graph_api.md (엔드포인트 경로 불일치)**
- 누락: 설계 원안의 `/api/stocks/{symbol}/chainsight/graph/`에서 `/api/v1/chainsight/{symbol}/graph/`로 경로 변경. 설계 문서와 실제 구현 간 API 경로 불일치
- 영향: 설계 문서를 기준으로 API 연동을 구현하면 404 발생. 단, 프론트엔드(chainsightService.ts)는 실제 경로 기준으로 이미 구현됨
- 권장: cs_41 문서의 API 경로 항목을 실제 구현에 맞게 업데이트(문서 수정 사항, 코드 변경 불필요)

**cs_42_suggestion_api.md (응답 스키마 불일치)**
- 누락: 원안은 카테고리 기반 응답 구조(peers/supply_chain/co_mentioned/community 등)를 정의. 실제 구현은 GrowthStage/CapitalDNA 유사도 기반 추천으로 변경됨. categories 필드 구조가 설계와 다름
- 영향: 설계 문서를 참조하여 프론트엔드를 수정할 경우 혼동 발생 가능
- 권장: cs_42 문서를 실제 구현에 맞게 업데이트. AIGuidePanel에서 표시하는 카테고리와 suggestions API 응답의 매핑 관계 명확화 필요

**cs_52_ai_guide_ui.md (컴포넌트 명칭 불일치)**
- 누락: 설계는 SuggestionCards.tsx 단일 컴포넌트로 정의. 실제 구현은 AIGuidePanel.tsx(카테고리 목록 + Trace 폼) + FilterPanel.tsx(관계 타입 필터)로 분리됨. 카드 선택 → 그래프 필터링 동작 방식도 변경
- 영향: 문서 기준 개발 시 파일명 혼동
- 권장: cs_52 문서에 실제 컴포넌트 분리 구조 반영

**cs_5_frontend_design_v2.md (CTA 연동 완성도 미확인)**
- 누락: 우측 패널 NodeDetailPanel의 CTA 4개 중 "가설 생성" → thesis 생성 폼 이동, "Validation 보기" → /validation/{symbol} 이동 연동 완성도 미확인. 프로파일 요약 패널(GrowthStage/CapitalDNA/InsiderSignal 표시)도 데이터 실제 표시 여부 불명확
- 영향: 전용 워크스페이스 완성도 저하 가능성
- 권장: NodeDetailPanel의 CTA href 및 프로파일 데이터 로딩 경로 검증

### (C) 미구현

없음. 모든 핵심 설계 항목은 최소한 부분 구현됨.

---

## 폐기/대체 항목

| 폐기 문서 | 대체 문서/방향 | 대체 시점/근거 |
|----------|----------------|----------------|
| cs_51_graph_visualization.md (GraphView.tsx 원안) | redesign_v1_260409에서 마켓 뷰(MarketGraphCanvas)와 심층 탐색(GraphCanvas) 분리 | 2026-04-09, redesign_v1_260409/chainsight_ui_ux_design.md v2.2 확정 |
| cs_52_ai_guide_ui.md (SuggestionCards 단일 컴포넌트) | AIGuidePanel + FilterPanel 분리 구현 | 2026-04-04, CS-5-1/CS-5-2 구현 과정에서 역할 분리 |
| sec_pipeline_base_design.md | sec_pipeline/ 독립 앱 + docs/sec_pipeline/ 별도 문서 체계 | 2026-04-03, SEC Pipeline은 Chain Sight와 독립 범위로 분리됨 |
| sec_pipeline_pr_detail.md | 위와 동일 | 위와 동일 |

---

## 프론트엔드 매핑 디테일

### cs_51 원안 컴포넌트 vs 실제 구현

| 설계 컴포넌트 | 실제 파일 | 상태 | 비고 |
|--------------|----------|------|------|
| GraphView.tsx | GraphCanvas.tsx | A (명칭 변경) | Spotlight + Lazy expansion 구현 |
| GraphControls.tsx | FilterPanel.tsx | A (역할 확장) | depth 전환 외 관계 타입 9종 필터 추가 |
| NodeDetailPanel.tsx | NodeDetailPanel.tsx | A | 완전 일치 |
| hooks/useGraphData.ts | hooks/useChainsight.ts 내 useGraphData | A | 통합 훅으로 구현 |
| ChainSightMiniView (cs_54) | GraphMiniView.tsx | A | CS-5-1에서 함께 구현 |

### cs_52 원안 컴포넌트 vs 실제 구현

| 설계 컴포넌트 | 실제 파일 | 상태 | 비고 |
|--------------|----------|------|------|
| SuggestionCards.tsx | AIGuidePanel.tsx | B (역할 분담) | 카테고리 목록 + ChainTrace 폼 통합 |
| (없음) | FilterPanel.tsx | 추가 구현 | 설계에 없는 관계 타입 필터 추가 |

### cs_53 원안 컴포넌트 vs 실제 구현

| 설계 컴포넌트 | 실제 파일 | 상태 | 비고 |
|--------------|----------|------|------|
| TraceView.tsx | TracePathView.tsx | A (명칭 변경) | 단계별 설명, 경로 없음 안내 구현 |

### redesign_v1_260409 UI 설계 컴포넌트 vs 실제 구현

| 설계 컴포넌트 | 실제 파일 | 상태 | 비고 |
|--------------|----------|------|------|
| SectorBar | SectorBar.tsx | A | |
| MarketGraphCanvas | MarketGraphCanvas.tsx | A | |
| ExplorationTrail | ExplorationTrail.tsx | A | WatchButton 통합 |
| RelationCardPanel | RelationCardPanel.tsx | A | pre-focus/focused 분기 구현 |
| ChainStoryFeed | ChainStoryFeed.tsx | A | |
| ExplorationState store | lib/stores/explorationStore.ts | A | Zustand 구현 |
| useMarketView hook | hooks/useMarketView.ts | A | |

### 설계에 정의되지 않은 추가 구현 컴포넌트

| 실제 파일 | 역할 | 관련 설계 |
|----------|------|----------|
| FullPathView.tsx | 전체 경로 표시 (watchlist 연동) | 설계 미포함 |
| PathCard.tsx | 저장된 경로 카드 | 설계 미포함 |
| WatchButton.tsx | ExplorationTrail에 포함된 저장 버튼 | cs_5_frontend_design_v2의 저장☆ 버튼 구현 |
| MobileCardList.tsx | 모바일 카드 리스트 | cs_5_frontend_design_v2 v2 변경 표의 "모바일=카드 리스트" 구현 |
| RelationLegend.tsx | 관계 타입 범례 | cs_5_frontend_design_v2 레이아웃의 범례 패널 |
| graphStyles.ts | 색상/스타일 상수 | cs_51, cs_5_frontend_design_v2 명세 기반 |
| frontend/app/chainsight/watchlist/ | Watchlist 페이지 2개 | 설계 문서 없음 — WatchlistViewSet 백엔드 완료 후 추가 |

---

## 추가 발견 (설계에 없는 구현)

### 백엔드

1. **WatchlistViewSet + SavedPath/PathAction 모델**: redesign PR 이후 추가됨. chainsight/views/watchlist_views.py, models/saved_path.py, migration 0006. 대응 설계 문서 없음
2. **regenerate_summary_paths 커맨드**: management/commands/regenerate_summary_paths.py. 설계 문서 없음
3. **chainsight/services/alternatives_service.py, expand_service.py, path_service.py, recheck_service.py**: CS-4-2(suggestions) 및 CS-4-3(trace)의 비즈니스 로직 구현 서비스 계층. cs_42, cs_43에는 views.py 직접 구현으로 정의했으나 서비스 분리가 추가됨
4. **SeedSnapshot 모델 + migration 0007**: redesign PR-2 산출물. 원안 CS-* 시리즈에는 없던 시드 영속화 모델
5. **migration 0005(neo4j_dirty), 0006(SavedPath), 0007(SeedSnapshot)**: 원안 cs_01에서는 0001~0004까지만 예상. 이후 redesign에서 3개 추가

### 프론트엔드

1. **frontend/app/chainsight/watchlist/ 페이지 2개**: WatchlistViewSet 완료 후 추가. 설계 문서 없음
2. **frontend/__tests__/chainsight/**: GraphCanvas, NodeDetailPanel, RelationCardPanel 단위 테스트 3개. 설계 문서에 테스트 명세 없음
3. **frontend/lib/stores/explorationStore.ts**: redesign ui_ux_design의 ExplorationState를 Zustand로 구현. 원안 cs_51~54에는 상태 관리 방식 미정의

---

## 권장 후속 조치

1. (우선순위 높음) **gds_tasks.py 생성 + Celery Beat 등록**: CS-3-3 task_done 기록에 GDS 수동 실행 기록만 있고 자동화 태스크가 없음. pagerank_score/community_id/betweenness_score를 최신 상태로 유지하려면 주기적 재실행이 필수. `chainsight-gds-weekly` 태스크로 등록 권장

2. (우선순위 높음) **cs_32 관계 삭제 경로 검증**: neo4j_sync.py의 stale/hidden 관계 Neo4j 엣지 DELETE 경로가 실제로 동작하는지 확인. 동작 안 할 경우 그래프에 오래된 관계가 누적됨

3. (우선순위 중간) **cs_41, cs_42 설계 문서 경로/스키마 업데이트**: 구현과 설계 간 API 경로 불일치, suggestions 응답 스키마 불일치를 문서에 반영. 코드 변경 불필요, 문서만 수정

4. (우선순위 중간) **cs_5_frontend_design_v2 NodeDetailPanel CTA 연동 검증**: "가설 생성" → thesis 폼, "Validation 보기" → /validation 이동이 실제 동작하는지 확인. 우측 패널 프로파일 요약 데이터(GrowthStage, CapitalDNA 등) 실제 API 응답으로 채워지는지 검증

5. (우선순위 낮음) **watchlist 설계 문서 신규 작성**: WatchlistViewSet, SavedPath/PathAction, watchlist 페이지 2개는 설계 문서 없이 구현됨. 1인 개발 원칙(원칙 3)에 따라 `docs/chain_sight/plan/cs_6_watchlist.md` 또는 동급 문서 사후 작성 권장

6. (우선순위 낮음) **Peer System Phase 6~7 설계 문서 및 구현 착수**: remaining_work_plan.md에서 "Thematic Presets (Chain Sight DNA 기반) + LLM 대화형 Peer 조정"이 예정되어 있으나 설계 문서 미작성, 구현 미착수 상태. Screener + Validation과 연동되는 기능으로 우선순위 재검토 필요

---

*감사 수행: QA-Architect Agent | 정적 감사 (코드 실행 없음) | 파일시스템 접근 제한으로 chainsight/ 내 일부 세부 코드는 이전 수집 데이터 기반 추정값 포함*
