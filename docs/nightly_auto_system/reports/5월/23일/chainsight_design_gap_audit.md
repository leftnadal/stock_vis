# Chain Sight 설계 갭 감사

생성일: 2026-05-23

> **감사 범위**: `docs/chain_sight/plan/` (설계 30개) ↔ `chainsight/` 백엔드 ↔ `frontend/components/chainsight/` (21개)
> **모드**: 읽기 전용. 코드 수정 없음.
> **전회 감사**: 5월 16일(초판) + 5월 17일(갱신). 이번 보고서는 5월 17일 감사 내용을 계승하고 5월 17일 이후 델타를 반영한다.
> **5월 17일 이후 변경**: WatchlistViewSet IDOR 보안 패치 1건 (commit e8abb7b). Chain Sight 설계-구현 갭 자체에는 신규 변경 없음.

---

## 요약 (구현률)

| 분류 | 설계 항목 수 | 비고 |
|------|------------|------|
| (A) 완전 구현 | 18 | CS-0~4 전 Phase, RelationConfidence v2.1, redesign v1 PR-1~7, DC-1~2 |
| (B) 부분 구현 | 7 | GDS 자동화, SeedHeatScore 모델, Sensitivity/InsiderSignal 데이터 적재, NarrativeTag/EventReaction/RevenueStructure 태스크, signals/ chain.title LLM |
| (C) 미구현 | 3 | Phase 3 D-1/D-2/D-3 (이벤트 전파), DC-3~4 Supply Chain 수동/LLM 시드, DC-6 Finnhub Premium |
| (D) 폐기/대체 | 5 | cs_51~54 + cs_5_frontend_design_v2 (redesign v2.2로 대체), CompanyChainProfile JSONB, CUSTOMER_OF DB 저장, RELATED_TO 하드코딩, 종목 상세 Chain Sight 탭 |

**핵심 결론**:
- CS-0 ~ CS-4 (인프라/시드/파이프라인/동기화/API) 5개 Phase 전부 완료. M1~M4 마일스톤 달성.
- redesign_v1_260409 마켓 뷰 PR-1~7 전부 구현. QA 점수 91%, TypeScript 타입 에러 0건.
- 미구현은 Phase 2 Heat Score 이후 단계(D-Phase), GDS 자동화 Celery Task, 일부 Tier B 모델 데이터 적재로 한정됨.
- 5월 17일 이후 보안 패치 1건(WatchlistViewSet IDOR) 외 설계 갭 변화 없음.

---

## 문서별 상태 테이블

### Phase 0 — 인프라

| 설계 문서 | 분류 | 대응 task_done | 대응 코드 위치 | 비고 |
|----------|------|--------------|--------------|------|
| cs_00_legacy_cleanup_api_test.md | (A) | task_done/CS-0-0_legacy_cleanup_api_test.md | decisions/003 API 테스트 기록 | serverless/ 레거시 정리, LEGACY_KEEP 태그 처리 |
| cs_01_migrations_verification.md | (A) | task_done/CS-0-1_migrations.md | chainsight/migrations/0001~0008.py | 12개 테이블 + SeedSnapshot + SavedPath 추가 마이그레이션 포함 |
| cs_02_neo4j_connection.md | (A) | task_done/CS-0-2_neo4j_driver.md | chainsight/graph/repository.py, exceptions.py | fork-safe PID lazy driver |
| cs_03_neo4j_schema.md | (A) | task_done/CS-0-3_neo4j_schema.md | chainsight/graph/schema.py, management/commands/init_neo4j_schema.py | 제약 4개 + 인덱스 2개 |

### Phase 1 — 시드 로드

| 설계 문서 | 분류 | 대응 task_done | 대응 코드 위치 | 비고 |
|----------|------|--------------|--------------|------|
| cs_11_stock_node_bulk_load.md | (A) | task_done/CS-1-1_stock_nodes.md | management/commands/load_stocks_to_neo4j.py, services/neo4j_loader.py | 532 Stock 노드 |
| cs_12_sector_industry.md | (A) | task_done/CS-1-2_sectors.md | management/commands/load_sectors_to_neo4j.py | 17 Sector + 128 Industry + BELONGS_TO |
| cs_13_peer_relations.md | (A) | task_done/CS-1-3_peers.md | management/commands/load_peers_to_neo4j.py, tasks/peer_tasks.py | PEER_OF 8,350개 |

### Phase 2 — 파생 데이터 파이프라인

| 설계 문서 | 분류 | 대응 task_done | 대응 코드 위치 | 비고 |
|----------|------|--------------|--------------|------|
| cs_21_tier_a_profile.md | (A) | task_done/CS-2-1_tier_a_profiles.md | tasks/profile_tasks.py, models/growth_stage.py, models/capital_dna.py | GrowthStage 480건, CapitalDNA 473건 |
| cs_21b_sensitivity_profile.md | (B) | task_done/CS-2-1b_sensitivity_profile.md | tasks/sensitivity_tasks.py, models/sensitivity.py | 스키마/태스크 존재, 실 적재 건수 미검증 |
| cs_21c_insider_signal.md | (B) | task_done/CS-2-1c_insider_signal.md | tasks/insider_tasks.py, models/insider_signal.py | 스키마/태스크 존재, 실 적재 건수 미검증 |
| cs_22_co_mention.md | (A) | task_done/CS-2-2_co_mention.md | tasks/relation_tasks.py::extract_co_mentions, models/relation_discovery.py::CoMentionEdge | ChainNewsEvent 활용, 일간 누적 가동 중 |
| cs_23_price_co_movement.md | (A) | task_done/CS-2-3_price_co_movement.md | tasks/relation_tasks.py::calculate_price_co_movement, models/relation_discovery.py::PriceCoMovement | 90일 rolling 상관 2,473쌍 |
| cs_24_relation_confidence.md | (A) | task_done/CS-2-4_relation_confidence.md | tasks/relation_tasks.py::update_relation_confidence | 3-tier 점수 + 5단계 상태 |
| cs_25_chain_profile_aggregation.md | (A) | task_done/CS-2-5_chain_profile_aggregation.md | tasks/sync_tasks.py::aggregate_chain_profiles, models/chain_profile.py | CompanyChainProfile 30개 필드 |
| relation_confidence_design_v1.md (v1.1) | (A) | redesign v1 PR-1 / data_quality_3_fixes.md | models/relation_discovery.py::RelationConfidence, services/neo4j_sync.py | 5단계 상태·truth/market 분리·undirected 정규화 완전 구현 |

### Phase 3 — Neo4j 동기화 + GDS

| 설계 문서 | 분류 | 대응 task_done | 대응 코드 위치 | 비고 |
|----------|------|--------------|--------------|------|
| cs_31_profile_neo4j_sync.md | (A) | task_done/CS-3-1_profile_sync.md | tasks/sync_tasks.py::sync_profiles_to_neo4j | Delta Sync, neo4j_dirty 플래그 기반 |
| cs_32_relation_neo4j_sync.md | (A) | task_done/CS-3-2_relation_neo4j_sync.md | tasks/sync_tasks.py + services/neo4j_sync.py::sync_dirty_relations | RELATED_TO 하드코딩 제거, 동적 타입 저장 |
| cs_33_gds_algorithms.md | (B) | task_done/CS-3-3_gds_algorithms.md (결과 기록만) | chainsight/graph/schema.py::stock_community 인덱스 정의만 존재 | chainsight/tasks/gds_tasks.py 부재. 1회성 외부 실행으로 추정. 정기 자동화 Task 없음 |

### Phase 4 — REST API

| 설계 문서 | 분류 | 대응 task_done | 대응 코드 위치 | 비고 |
|----------|------|--------------|--------------|------|
| cs_41_graph_api.md | (A) | task_done/CS-4-1_2_3_rest_api.md | api/views.py::ChainSightGraphView | /api/v1/chainsight/{symbol}/graph/ |
| cs_42_suggestion_api.md | (B) | 같은 task_done | api/views.py::ChainSightSuggestionView | 4 카테고리만 반환 (peers/same_industry/co_mentioned/same_sector). 설계 5번째 community 카테고리 미구현 (GDS 자동화 의존) |
| cs_43_trace_api.md | (A) | 같은 task_done | api/views.py::ChainSightTraceView | shortestPath up to 5 hop |

### Phase 5 — 프론트엔드 (cs_5x 1세대 → 폐기/대체)

| 설계 문서 | 분류 | 대응 task_done | 대응 코드 위치 | 비고 |
|----------|------|--------------|--------------|------|
| cs_51_graph_visualization.md | (D) | task_done/CS-5-1_frontend_graph.md | frontend/components/chainsight/GraphCanvas.tsx, radialLayout.ts, graphStyles.ts | Spotlight + lazy expansion 개념은 redesign v2.2에 흡수. 컴포넌트명 변경 (GraphView→GraphCanvas) |
| cs_52_ai_guide_ui.md | (D) | task_done/CS-5-2_pro_features.md | frontend/components/chainsight/AIGuidePanel.tsx (deep dive), RelationCardPanel.tsx (market view) | SuggestionCards → AIGuidePanel + RelationCardPanel로 두 화면에서 분기 |
| cs_53_chain_trace_ui.md | (A) | task_done/CS-5-3_mobile_card_list.md + update_v2/task_done/cs_71_72_73 | frontend/components/chainsight/TracePathView.tsx, FullPathView.tsx, PathCard.tsx | TraceView → TracePathView 명명 변경 |
| cs_54_stock_detail_integration.md | (D) | update_v2/task_done/CS-5-4_stock_detail.md 추정 | frontend/app/stocks/[symbol]/page.tsx (Chain Sight 탭 제거, GraphMiniView + /chainsight?focus 딥링크) | redesign UI v2.2 §11 결정으로 탭 제거 |
| cs_5_frontend_design_v2.md | (D) | CS-5-1~3 + redesign PR-5~7 | frontend/app/chainsight/[symbol]/page.tsx (3-panel 워크스페이스로 잔존) | 3-panel 콘셉트는 Deep dive workspace(/chainsight/[symbol])에만 유지. 메인 흐름은 redesign 마켓 뷰로 대체 |

### Redesign V1 (redesign_v1_260409/) — 마켓 뷰

| 설계 문서 | 분류 | 대응 PR | 대응 코드 위치 | 비고 |
|----------|------|--------|--------------|------|
| chainsight_seed_node_design.md (v2.1, Phase 1) | (A) | PR-1, PR-2 | services/seed_selection.py, tasks/seed_tasks.py::run_seed_selection, models/seed_snapshot.py, migrations/0005 | B+A 소스 5종, MAX_SEED_NODES=20, Redis 캐시 + PostgreSQL SeedSnapshot 영속화 |
| chainsight_seed_node_design.md (Phase 2: SeedHeatScore) | (B) | - | tasks/seed_tasks.py::calculate_heat_scores (Neo4j 노드 속성만 저장) | SeedHeatScore PostgreSQL 모델 부재. seed_rank·components JSONB 미적재. sector_summary heat_total 정렬 미전환 |
| chainsight_seed_node_design.md (Phase 3: D-1~D-3) | (C) | - | 코드 없음 | text_conditional_prob / lagged correlation / propagation_weight 미구현. ChromaDB 인프라 미도입 |
| chainsight_api_design.md (v2.1, 4개 API) | (A) | PR-4 | api/views.py::SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView + api/urls.py | 캐시 TTL·display_type 파생·정렬 정책 설계서와 일치 |
| chainsight_ui_ux_design.md (v2.2, 5개 컴포넌트) | (A) | PR-5, PR-6, PR-7 | frontend/components/chainsight/{SectorBar,MarketGraphCanvas,ExplorationTrail,RelationCardPanel,ChainStoryFeed}.tsx + app/chainsight/page.tsx + lib/stores/explorationStore.ts + hooks/useMarketView.ts | 화면 ①~⑤ 전부 구현. ExplorationState 7개 상태 + 8개 액션 |
| chainsight_marketview_pr_prompts.md | (A) | PR-1~7 전부 | task_done/chain_sight_redesign_V1/ 7개 보고서 | QA 점수 91%. TypeScript 에러 0건 |

### 데이터 수집 트랙 (DC)

| 설계 항목 | 분류 | 대응 task_done | 비고 |
|----------|------|--------------|------|
| DC-1 Peers + Industry | (A) | Phase 1 CS-1-3 결과 충족 | PEER_OF 8,350 + BELONGS_TO 다수 |
| DC-2 ETF Holdings → :Theme | (A) | task_done/DC-2_etf_holdings_theme.md | :Theme 21개 + HAS_THEME 534개, management/commands/load_themes_to_neo4j.py |
| DC-3 수동 시드 Supply Chain JSON | (C) | 없음 | SUPPLIES_TO 적재 경로 부재. 시드 JSON 파일 미발견 |
| DC-4 Gemini Flash Supply Chain 확장 | (C) | 없음 | 관련 태스크/프롬프트 모듈 미발견. chain_insight/ 앱 미존재 |
| DC-5 Marketaux 뉴스 자연 축적 | (B) | 없음 (자연 누적) | CoMentionEdge 일간 추출 가동 중. 명시적 DC-5 task_done 없음 |
| DC-6 Finnhub Premium | (C) | 없음 | 의도된 보류. 수익화 후 결정 사항으로 roadmap에 명시 |

### 기타 설계 문서 (plan/ 내 위치하나 별도 앱)

| 설계 문서 | 분류 | 비고 |
|----------|------|------|
| sec_pipeline_base_design.md | (A) 외부 앱 | sec_pipeline/ 앱으로 분리 구현. Chain Sight Phase 3 D-3 SEC filing 연계는 미연결 |
| sec_pipeline_pr_detail.md | (A) 외부 앱 | 동일 |
| remaining_work_plan.md | 참조 문서 | 2026-04-04 기준 진척 스냅샷. 설계 문서 아님 |
| chain_sight_roadmap_v1.3.md | 참조 문서 | 전체 로드맵. 구현 대상 아님 |

---

## 미구현 항목 상세

### 1. GDS 알고리즘 자동화 (CS-3-3, B)

- **설계 의도**: `chainsight/tasks/gds_tasks.py` (또는 동등 태스크)를 통해 PageRank, Louvain Community, Betweenness Centrality를 정기 배치로 Neo4j :Stock 노드 속성에 갱신
- **누락 부분**: `chainsight/tasks/gds_tasks.py` 파일 부재. Celery Beat에 GDS 관련 태스크 미등록. `graph/schema.py`의 `stock_community` 인덱스와 `services/path_service.py`의 `pagerank_score`/`community_id` 읽기 코드는 존재하나 기록하는 태스크가 없음
- **task_done 주장과의 모순**: CS-3-3_gds_algorithms.md는 PageRank/Louvain 결과(수치 포함)를 기록함. 1회성 외부 실행으로 추정되나 코드로 재현 불가
- **영향도**: (1) pagerank_score/community_id가 stale 상태로 방치됨. (2) ChainSightSuggestionView::community 카테고리 미구현의 직접 원인. (3) redesign 00_summary "범위 밖(후속)" 항목에 GDS가 명시되어 있어 의도적 보류 가능성도 있음

### 2. SeedHeatScore PostgreSQL 모델 (chainsight_seed_node_design.md Phase 2, B)

- **설계 의도**: `SeedHeatScore(stock, date, heat_score, components JSONB, seed_rank)` PostgreSQL 모델로 일자별 heat score 이력 저장
- **누락 부분**: `SeedHeatScore` 모델 파일 부재 (models/__init__.py에 미등록). `calculate_heat_scores` 태스크는 존재하나 결과를 Neo4j :Stock 노드 속성(`s.heat_score`, `s.price_signal` 등)에만 저장
- **파생 미구현**: SeedHeatScore 부재로 sector_summary의 `heat_total` 집계 불가 → SectorGraphView의 섹터 정렬이 설계서 Phase 2 기준(`heat_total DESC`) 미전환. 현재 `seed_count DESC` 고정

### 3. Phase 3 이벤트 전파 모델 D-1/D-2/D-3 (C)

- **설계 의도**: D-1 text_conditional_prob (뉴스→Gemini Embedding→ChromaDB, 비대칭), D-2 lagged price correlation + volume_response + propagation_weight, D-3 사후 검증 + 가중치 학습
- **누락 부분**: 관련 코드 전무. ChromaDB 의존성 미도입. Celery Beat에 chainsight-text-conditional / chainsight-lagged-correlation / chainsight-propagation-weight 미등록
- **영향도**: 설계서 자체에서 "D-1 후 ~3개월 거래일 축적 필요", ChromaDB 도입 필요로 명시 → 단기 진입 불가. redesign 00_summary에서도 "범위 밖 후속 작업"으로 분류

### 4. Suggestion API community 카테고리 (cs_42, B)

- **설계 의도**: GET /{symbol}/suggestions/ 응답에 5번째 카테고리 `{ "id": "community", "label": "같은 클러스터" }` 포함
- **누락 부분**: ChainSightSuggestionView는 4 카테고리(peers, same_industry, co_mentioned, same_sector)만 반환. community_id 매칭 로직 없음
- **영향도**: GDS 자동화(#1) 해결 전까지 구현 불가. 탐색 제안 카드 완성도 미흡

### 5. Tier B 모델 데이터 미적재 (B)

- **설계 의도**: CompanyNarrativeTag, CompanyEventReaction, CompanyRevenueStructure는 설계 및 스키마 존재
- **누락 부분**:
  - CompanyRevenueStructure: 적재 태스크 미발견 (MVP 빈 상태로 시작은 의도적)
  - CompanyEventReaction: earnings 전후 주가 변동 계산 태스크 미발견
  - CompanyNarrativeTag: sync_tasks.py에서 읽기 참조는 있으나 생성 태스크 미발견
- **영향도**: 세 모델 데이터 0건으로 추정. ChainProfile 집약 품질 저하 가능성

### 6. DC-3/DC-4 Supply Chain 시드 미구현 (C)

- **설계 의도**: DC-3 수동 SUPPLIES_TO JSON 시드, DC-4 Gemini Flash 관계 확장
- **누락 부분**: 수동 시드 JSON 파일 없음. Gemini Flash 관계 추출 태스크 없음
- **영향도**: Neo4j에 SUPPLIES_TO 엣지 0건 (또는 극소). NeighborGraphView의 supply chain 카테고리 사실상 빈 상태

---

## 폐기/대체 항목

### cs_51 ~ cs_54 + cs_5_frontend_design_v2.md → redesign_v1_260409 v2.2

- **폐기 사유**: cs_51~54 원안은 종목 상세 페이지 탭 진입 모델 기반. redesign이 "마켓 허브 → 섹터 → 중심 이동" 탐색 모델로 전환함
- **대체 위치**: redesign_v1_260409/chainsight_ui_ux_design.md v2.2 → PR-5/6/7 구현 → frontend/app/chainsight/page.tsx + 5개 컴포넌트
- **잔존 자산**: /chainsight/[symbol] 워크스페이스(3-panel)와 AIGuidePanel, NodeDetailPanel, FilterPanel, TracePathView, MobileCardList는 Deep dive workspace용으로 위상 변경 후 유지. redesign UI v2.2 §12에서 "유지" 명시

### CUSTOMER_OF DB 저장 → API 파생

- **폐기 사유**: 로드맵 v1.3 결정. SUPPLIES_TO만 canonical 저장, 중복 엣지 방지
- **대체 위치**: api/views.py::NeighborGraphView._display_type (line 531~535), ChainSightGraphView derived_type (line 90~92)

### RELATED_TO 하드코딩 → 동적 타입

- **폐기 사유**: data_quality_3_fixes.md Issue 2B 에서 식별. sync_relations_to_neo4j가 모든 엣지를 RELATED_TO로 저장하던 버그
- **대체 위치**: services/neo4j_sync.py::sync_dirty_relations 가 PEER_OF/SUPPLIES_TO/COMPETES_WITH/CO_MENTIONED/PRICE_CORRELATED 동적 타입 사용

### 종목 상세 페이지 Chain Sight 탭

- **폐기 사유**: redesign UI/UX v2.2 §11 결정. 탭 공간 제한 + 마켓 뷰가 메인 진입점으로 이동
- **대체 위치**: frontend/app/stocks/[symbol]/page.tsx에서 GraphMiniView + "/chainsight?focus={symbol}" 딥링크로 대체

### CompanyChainProfile JSONB 단일 필드

- **폐기 사유**: 로드맵 v1.1 안이었으나 v1.2 결정에서 30개 개별 필드 구조 유지로 변경
- **대체 위치**: models/chain_profile.py 30개 필드 구조 그대로 반영

---

## 설계 문서에 없는 구현 자산 (계획 외 추가)

| 모델/뷰 | 위치 | 역할 | 추가 배경 추정 |
|--------|------|------|-------------|
| SeedSnapshot | models/seed_snapshot.py | Redis 휘발 대응 DB 영속화 | common-bugs #27 트러블슈팅 산물. Redis flush 시 시드 데이터 소실 방지 |
| SavedPath, PathAction | models/saved_path.py | Trace 경로 저장 + 액션 로그 | update_v2/task_done/cs_71_72_73에서 Phase 6~7로 구현됨. plan/ 문서 없음 |
| WatchlistViewSet | views/watchlist_views.py + api/urls.py | archive/resolve/recheck/expand/alternatives CRUD | redesign PR prompts의 "Watchlist 추가" CTA에서 파생. 5월 17일 이후 IDOR 패치 적용 (commit e8abb7b) |
| expand_service.py, path_service.py, alternatives_service.py, recheck_service.py | services/ | Path Watchlist 액션 서비스 4종 | update_v2 Phase 6 산물. plan/ 미포함 |
| frontend/components/chainsight/{NodeTooltip, NodeContextMenu, RelationFilterChips, radialLayout}.tsx | frontend/ | 그래프 인터랙션 보강 | 5월 13일 mobile_ux_audit 등에서 언급됨. 공식 설계 문서 없음 |

---

## 5월 17일 감사 이후 변경 사항

| 항목 | 커밋 | 내용 | 갭 영향 |
|------|------|------|--------|
| WatchlistViewSet IDOR 패치 | e8abb7b (2026-05-17~23 사이) | 다른 사용자 Watchlist 접근 차단 | 구현 정합성 향상. 설계 갭에는 영향 없음 |

5월 17일 이후 chainsight/ 백엔드 및 frontend/components/chainsight/ 에 설계 갭 관련 신규 커밋 없음. 미구현 항목(GDS 자동화, SeedHeatScore 모델, Phase 3 D-Phase, DC-3/4) 상태 유지.

---

## 권장 후속 작업 (우선순위순)

1. **GDS 자동화 태스크 신규 작성**: chainsight/tasks/gds_tasks.py 생성. PageRank/Louvain/Betweenness → Neo4j 노드 속성. Celery Beat 등록 (주 1회). 완료 후 Suggestion API community 카테고리 활성화 가능
2. **SeedHeatScore 모델 신설**: models/seed_heat_score.py (stock, date, heat_score, components JSONB, seed_rank). migration 신규. calculate_heat_scores 태스크가 Neo4j 외에 PostgreSQL도 저장하도록 확장. 완료 후 sector_summary heat_total 정렬 전환
3. **Tier B 데이터 적재 태스크**: CompanyEventReaction(earnings 전후 주가 변동 계산), CompanyNarrativeTag(Gemini 키워드 추출) 태스크 신규 작성
4. **설계 문서 갱신**: SeedSnapshot / SavedPath / PathAction / WatchlistViewSet을 plan/ 또는 roadmap 부록에 추가. update_v2/ 아래 작업들과 plan/ 간 교차 참조 연결

---

**END OF REPORT**
