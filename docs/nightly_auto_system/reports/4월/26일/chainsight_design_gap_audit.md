# Chain Sight 설계 갭 감사

> **감사 일시**: 2026-04-27
> **감사 범위**: `docs/chain_sight/plan/` + `docs/chain_sight/update_v2/` ↔ `chainsight/` 백엔드 + `frontend/components/chainsight/`, `frontend/app/chainsight/`
> **감사 방식**: 읽기 전용. 코드 수정 없음.

---

## 요약 (구현률)

| 분류 | 항목 수 | 비율 |
|------|--------|------|
| (A) 완전 구현 | 26 | 67% |
| (B) 부분 구현 | 7 | 18% |
| (C) 미구현 | 4 | 10% |
| (D) 폐기/대체 | 2 | 5% |
| **합계** | **39** | **100%** |

**현재 상태**:
- **백엔드 코어 파이프라인**(CS-0 ~ CS-3)과 **REST API 4종**(seeds, sector graph, neighbors, signals) + **Deep dive API 3종**(graph, suggestions, trace)이 모두 구현되어 있음.
- **마켓 뷰 프론트엔드**(redesign_v1_260409 PR-5/6/7) 5개 컴포넌트 + Zustand 상태 모두 존재.
- **Path Watchlist**(v1.4 신규 도입) Phase 6/7 백엔드 + 프론트엔드까지 완료됨.
- 미구현은 주로 **DC-2(ETF Holdings)**, **Phase 3(이벤트 전파)**, **2차 카드 설명** 등 성장 단계 기능.

**문서 트리 구조**:
- `plan/cs_*` (cs_00 ~ cs_54): 작업별 1차 설계서. 일부는 **redesign_v1_260409**로 대체됨.
- `plan/redesign_v1_260409/`: 마켓 뷰 v2.1/2.2 재설계서 (현재 구현의 직접적 근거).
- `plan/chain_sight_roadmap_v1.3.md`: v1.3 로드맵. **`update_v2/ROADMAP_v1.4.md`로 갱신됨**.
- `update_v2/`: v1.4 (Path Watchlist + heat_score 추가) 최신 정식 로드맵.
- `task_done/`: 완료 보고서 26개 (chain_sight_redesign_V1 + update_v2/task_done).

---

## 문서별 상태 테이블

### Phase 0 — 인프라 기반

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| `cs_00_legacy_cleanup_api_test.md` | 레거시 정리 + API 테스트 5개 | `decisions/003_api_access_test.md` | (A) 완전 |
| `cs_01_migrations_verification.md` | 12개 테이블 마이그레이션 | `chainsight/migrations/0001-0007` (15개 모델) | (A) 완전 |
| `cs_02_neo4j_connection.md` | `chainsight/graph/repository.py` | `chainsight/graph/repository.py` + PID 기반 lazy init | (A) 완전 |
| `cs_03_neo4j_schema.md` | constraint/index 4종 | `chainsight/management/commands/init_neo4j_schema.py` | (A) 완전 |

### Phase 1 — 시드 데이터 로드

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| `cs_11_stock_node_bulk_load.md` | S&P 500 :Stock 노드 | `management/commands/load_stocks_to_neo4j.py` (Stock 532개) | (A) 완전 |
| `cs_12_sector_industry.md` | :Sector / :Industry / BELONGS_TO | `management/commands/load_sectors_to_neo4j.py` | (A) 완전 |
| `cs_13_peer_relations.md` | PEER_OF 관계 | `services/neo4j_loader.py::load_peers_to_neo4j` (8,350개) | (A) 완전 |

### Phase 2 — 파생 데이터 파이프라인

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| `cs_21_tier_a_profile.md` | GrowthStage, CapitalDNA | `tasks/profile_tasks.py` (480/473건) | (A) 완전 |
| `cs_21b_sensitivity_profile.md` | SensitivityProfile (Tier A) | `tasks/sensitivity_tasks.py` (모델만, 데이터 미적재) | (B) 부분 |
| `cs_21c_insider_signal.md` | InsiderSignal (Tier A) | `tasks/insider_tasks.py` (모델만, 데이터 미적재) | (B) 부분 |
| `cs_22_co_mention.md` | CoMentionEdge | `tasks/relation_tasks.py` + 모델 | (A) 완전 |
| `cs_23_price_co_movement.md` | PriceCoMovement (90d) | `tasks/relation_tasks.py` + 모델 | (A) 완전 |
| `cs_24_relation_confidence.md` | RelationConfidence v2.1 (5단계) | `models/relation_discovery.py` + tasks (2,748쌍) | (A) 완전 |
| `cs_25_chain_profile_aggregation.md` | CompanyChainProfile 집약 | `tasks/sync_tasks.py::aggregate_chain_profiles` | (A) 완전 |

### Phase 3 — Neo4j 동기화 + GDS

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| `cs_31_profile_neo4j_sync.md` | ChainProfile → :Stock 노드 속성 | `tasks/sync_tasks.py` + neo4j_synced 플래그 | (A) 완전 |
| `cs_32_relation_neo4j_sync.md` | RelationConfidence → 엣지 (confirmed/probable) | `services/neo4j_sync.py` + neo4j_dirty 패턴 | (B) 부분 — 엣지 라벨이 `RELATED_TO`로 고정되고 실제 타입은 `r.relation_type` 속성에 보존됨 (`api/views.py:351,494`의 NOTE 참조) |
| `cs_33_gds_algorithms.md` | PageRank, Louvain, Betweenness | `task_done/CS-3-3` 기록 (M3 달성, 별도 GDS 태스크 모듈은 없음) | (B) 부분 — 일회성 실행, 정기 배치 미등록 |

### Phase 4 — REST API

| 문서 | 설계 엔드포인트 | 구현 위치 | 상태 |
|------|---------------|----------|------|
| `cs_41_graph_api.md` | `GET /{symbol}/graph/` (Deep dive) | `api/views.py::ChainSightGraphView` | (A) 완전 |
| `cs_42_suggestion_api.md` | `GET /{symbol}/suggestions/` | `api/views.py::ChainSightSuggestionView` | (A) 완전 |
| `cs_43_trace_api.md` | `GET /trace/` | `api/views.py::ChainSightTraceView` | (A) 완전 |

### redesign_v1_260409 — 마켓 뷰 (PR-1 ~ PR-7)

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| `chainsight_seed_node_design.md` (Phase 1) | 시드 선정 8 reason 코드 + sector_summary | `services/seed_selection.py` + `tasks/seed_tasks.py` | (A) 완전 |
| Phase 2 — Heat Score | `SeedHeatScore` PG 모델 + 6 component 가중치 | DB 모델 미생성. v1.4에서 Neo4j 노드 속성으로 단순화 (`tasks/seed_tasks.py::calculate_heat_scores`, 4 component 균등 0.25) | (D) 폐기/대체 |
| Phase 3 (D-1,2,3) | text_conditional_prob, lagged correlation, propagation_weight | 미구현 | (C) 미구현 |
| `chainsight_api_design.md` `GET /seeds/` | 시드 + 섹터 요약 + 3단 폴백 | `api/views.py::SeedListView` + `_get_today_seeds` (Redis → SeedSnapshot DB → async 복구) | (A) 완전 |
| `chainsight_api_design.md` `GET /sector/{sector}/graph/` | overview graph (node_size, edges) | `api/views.py::SectorGraphView` | (A) 완전 |
| `chainsight_api_design.md` `GET /{symbol}/neighbors/` | 중심 + neighbors + cross_edges + display_type | `api/views.py::NeighborGraphView` (CUSTOMER_OF 파생 포함) | (A) 완전 |
| `chainsight_api_design.md` `GET /signals/` | 글로벌 chain flow | `api/views.py::SignalFeedView::_build_chain_signals` (max_hop=3, total_confidence 평균식) | (A) 완전 |
| `chainsight_marketview_pr_prompts.md` PR-1 (스키마 마이그) | previous_status, neo4j_dirty | `migrations/0005_add_neo4j_dirty_previous_status.py` | (A) 완전 |
| PR-2 시드 선정 task | Celery Beat 매일 12:00 UTC | `tasks/seed_tasks.py::run_seed_selection` (이름 `chainsight-seed-selection`) | (A) 완전 |
| PR-3 Neo4j Sync 개선 | dirty 패턴 + queryset.update() | `services/neo4j_sync.py::sync_dirty_relations` | (A) 완전 |
| PR-4 마켓 뷰 API 4종 | 4 엔드포인트 | 위 4건 동일 | (A) 완전 |
| PR-5 FE 코어 UI | 페이지 골격 + SectorBar + MarketGraphCanvas | `app/chainsight/page.tsx` + `components/chainsight/SectorBar.tsx`, `MarketGraphCanvas.tsx` | (A) 완전 |
| PR-6 트레일 + 관계 카드 | ExplorationTrail + RelationCardPanel | `components/chainsight/ExplorationTrail.tsx`, `RelationCardPanel.tsx` | (A) 완전 |
| PR-7 체인 스토리 피드 | ChainStoryFeed (글로벌) | `components/chainsight/ChainStoryFeed.tsx` | (A) 완전 |
| `chainsight_ui_ux_design.md` v2.2 | 5단 화면 구조, 상태 매트릭스 | `lib/stores/explorationStore.ts` (Zustand) + 5개 컴포넌트 | (A) 완전 |

### 1차 (v1.3) Phase 5 프론트엔드 작업서

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| `cs_51_graph_visualization.md` (GraphView) | react-force-graph-2d, Spotlight | Deep dive `app/chainsight/[symbol]/page.tsx` + `GraphCanvas.tsx`, 마켓뷰는 `MarketGraphCanvas.tsx` | (A) 완전 — 두 컴포넌트로 분리 구현 |
| `cs_52_ai_guide_ui.md` (SuggestionCards) | 카테고리 카드 → 그래프 필터링 | Deep dive `AIGuidePanel.tsx` (마켓뷰에는 SuggestionCards 별도 미배치 — 관계 카드 패널이 그 역할 흡수) | (D) 대체 — 설계 재구성 |
| `cs_53_chain_trace_ui.md` (TraceView) | from→to 경로 시각화 | `components/chainsight/TracePathView.tsx` (Deep dive에서만 사용) | (B) 부분 — UI는 존재하나 마켓뷰 통합 없음 |
| `cs_54_stock_detail_integration.md` (ChainSightMiniView + 종목상세 탭) | 미니 그래프 + 탭 활성화 | `components/chainsight/GraphMiniView.tsx` 존재. 종목상세 탭은 v2.x 설계로 인해 **딥링크(`/chainsight?focus=`)로 대체** | (D) 대체 — UI/UX 설계 §11 정책에 따라 탭 → 딥링크 전환 |

### update_v2 / v1.4 — Path Watchlist (Phase 6/7)

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| `cs_61_saved_path_model.md` | SavedPath, PathAction 모델 | `models/saved_path.py` + `migrations/0006` | (A) 완전 |
| `cs_62_watchlist_crud_api.md` | `/watchlist/` ViewSet | `views/watchlist_views.py` + `serializers/path_watchlist.py` | (A) 완전 |
| `cs_63_summary_path.md` | landmark 압축 알고리즘 | `services/path_service.py::generate_summary_path` | (A) 완전 |
| `cs_65_recheck_api.md` | 6단계 Recheck 로직 | `services/recheck_service.py::run_recheck` | (A) 완전 |
| `cs_66_expand_api.md` | 1-hop 후보 + 종합 점수 | `services/expand_service.py::find_expansion_candidates` | (A) 완전 |
| `cs_67_alternatives_api.md` | 노드 대안 탐색 | `services/alternatives_service.py::find_alternatives` | (A) 완전 |
| `cs_71_watch_button.md` | Watch 버튼 + path/edge_metadata 연동 | `components/chainsight/WatchButton.tsx` + ExplorationTrail 통합 | (A) 완전 |
| `cs_72_watchlist_ui.md` | Watchlist 카드 리스트 | `components/chainsight/PathCard.tsx` + `app/chainsight/watchlist/page.tsx` | (A) 완전 |
| `cs_73_full_path_view.md` | Full Path View (액션 + Recheck UX) | `components/chainsight/FullPathView.tsx` + `app/chainsight/watchlist/[id]/page.tsx` | (A) 완전 |
| `cs_44_seed_node_heat_score.md` | heat_score 일간 배치 (4 signal × 0.25) | `tasks/seed_tasks.py::calculate_heat_scores` (Celery Beat: 07:00 UTC) | (A) 완전 |

### 데이터 수집 트랙 (DC-1 ~ DC-6)

| 문서 | 설계 | 구현 위치 | 상태 |
|------|------|----------|------|
| DC-1 (Peer/Industry) | Finnhub + FMP Peer | `services/neo4j_loader.py` (8,350 PEER_OF) | (A) 완전 |
| `DC-2_etf_holdings_theme.md` | :Theme + HAS_THEME 관계 | 미구현 — `serverless/` ETF 모델은 `LEGACY_KEEP_UNTIL_DC2` 태그로 보관만 | (C) 미구현 |
| DC-3 (수동 시드 Supply Chain) | SUPPLIES_TO 관계 ~500개 | 시드 JSON 미발견 | (C) 미구현 |
| DC-4 (Gemini Supply Chain 확장) | LLM 기반 Supply Chain | 미구현 | (C) 미구현 |
| DC-5 (뉴스 자연 축적) | CoMentionEdge 시간 누적 | `tasks/relation_tasks.py` 구현됨, 운영 단계 | (A) 완전 |
| DC-6 (유료 API) | 수익화 후 — 미실행 보류 | (보류) | — |

---

## 미구현 항목 상세

### (C-1) DC-2: ETF Holdings → :Theme + HAS_THEME

- **설계 위치**: `chain_sight_roadmap_v1.3.md` 섹션 4.2 (DC-2), `task_done/DC-2_etf_holdings_theme.md`
- **현재 상태**: `serverless/models.py`에 `ETFProfile`, `ETFHolding`, `ThemeMatch`가 `# LEGACY_KEEP_UNTIL_DC2` 태그로 보관 중. `chainsight/management/commands/load_themes_to_neo4j.py`가 존재하지만 데이터 로드 미실행.
- **차단 요인**: Finnhub ETF Holdings API가 무료 티어에서 차단(decisions/003) → 운용사 CSV 다운로드 방식으로 결정되었으나 실행되지 않음.
- **영향**: 마켓 뷰 `relation_category=truth` 관계 중 HAS_THEME 빈 상태. 그래프 풍부함 부족.

### (C-2) Phase 3 D-1/D-2/D-3 (이벤트 전파 모델)

- **설계 위치**: `chainsight_seed_node_design.md` §4 (Phase 3)
- **현재 상태**: text_conditional_prob, lagged correlation, propagation_weight 미구현. Gemini Embedding + ChromaDB 인프라 미설치.
- **의존성**: D-2는 D-1 후 60거래일(~3개월) 축적 필요.
- **영향**: 시드 → 이웃으로의 비대칭 전파 가중치 계산 불가. 현재는 단순 RelationConfidence truth_score만 사용.

### (C-3) DC-3 / DC-4 Supply Chain 시드

- **설계 위치**: 로드맵 §4.5 + §4.6
- **현재 상태**: 수동 시드 JSON 파일 없음. Gemini Flash 기반 Supply Chain 확장 코드 미구현.
- **결과**: Neo4j SUPPLIES_TO 관계가 RelationConfidence 일반 흐름만 거치고 별도 시드 진입 없음. 단, **SEC Pipeline**(`sec_pipeline/`)이 10-K Supply Chain 추출로 보완하고 있음 — 즉 DC-3/DC-4의 직접 대체.

### (C-4) 2차 카드 설명 + LLM chain title

- **설계 위치**: `chainsight_api_design.md` §4 (2차 필드 확장), §5 (체인 스토리 LLM 제목)
- **현재 상태**: `relation_summary`, `why_now`, `insight_summary` 필드 미배치. `_build_chain_signals`의 chain title은 `f'{first} → {last} chain'` 단순 템플릿만.
- **분류**: redesign_v1_260409가 명시적으로 "Future enhancement"로 미룸. 미구현이지만 의도된 보류.

---

## 부분 구현 항목

| 항목 | 갭 |
|------|----|
| **CS-2-1b SensitivityProfile** | 태스크/모델은 존재. 데이터 0건. FMP Revenue Geo Segmentation API 검증 필요. |
| **CS-2-1c InsiderSignal** | 태스크/모델은 존재. 데이터 0건. Finnhub Insider 60 RPM rate limit 고려한 배치 미실행. |
| **CS-3-2 Relation Sync 엣지 라벨** | Neo4j 엣지 라벨이 `RELATED_TO`로 고정되고 실제 타입은 `r.relation_type` 속성에 저장됨. API view에서 `COALESCE(r.relation_type, type(r))`로 처리하지만 Cypher 쿼리/GDS에서 type-aware 필터를 쓰려면 라벨 분리 필요. (`api/views.py` NOTE 명시) |
| **CS-3-3 GDS 정기 배치** | 일회성 실행은 완료(M3 달성: PageRank/Louvain/Betweenness Top 5 기록). 정기 Celery Beat 등록 미발견 — 노드 속성이 stale될 가능성. |
| **CS-2-2 NarrativeTag** | 모델은 존재. LLM 추출 태스크 미구현. |
| **CS-2-2 EventReaction** | 모델은 존재. earnings 전후 주가 반응 계산 태스크 미구현. |
| **TracePathView 마켓뷰 통합** | 컴포넌트는 존재하나 마켓 뷰 페이지에는 노출되지 않음. Deep dive workspace에서만 활성. |

---

## 폐기/대체 항목

### (D-1) Phase 2 SeedHeatScore PG 테이블 → Neo4j 속성으로 단순화

- **원 설계**: `chainsight_seed_node_design.md` §3.4 — `chainsight.SeedHeatScore` Django 모델로 매일 저장 (heat_score, components JSONB, seed_rank).
- **실 구현**: v1.4 `cs_44_seed_node_heat_score.md`가 PG 모델을 생략하고 Neo4j `:Stock.heat_score` 속성으로만 관리. Components 6개 → 4개로 축소(price/volume/relation/news, 균등 0.25).
- **이유**: 1인 개발 원칙(원칙 4) + Neo4j에서 직접 정렬/필터 가능.
- **영향**: 시계열 heat_score 추적 불가. A/B 가중치 튜닝 시 별도 로깅 필요.

### (D-2) cs_5_frontend_design_v2.md & cs_51~54 → redesign_v1_260409로 통합 재설계

- **원 설계 (v1.3)**: 종목 상세에 Chain Sight 탭(미니 뷰), 별도 `SuggestionCards`, 별도 `TraceView` 컴포넌트.
- **실 구현 (v2.x)**:
  - `chainsight_ui_ux_design.md` §11 — 종목 상세 탭은 **제거**되고 `/chainsight?focus={symbol}` 딥링크로 대체.
  - SuggestionCards는 마켓뷰의 RelationCardPanel(focused state)이 흡수 — Supply Chain / Competitors / Peers / Co-mentioned 4개 그룹.
  - TraceView는 Deep dive workspace 전용으로 유지 (`TracePathView.tsx`).
- **이유**: 마켓 뷰 = breadth-first 탐색 허브, Deep dive workspace = depth-first 분석. 두 경로 분리.

---

## 부가 관찰

### 모델 카운트 확정

- 로드맵 v1.3에서 "12개 테이블" → v1.4가 SavedPath/PathAction 추가로 14개 → **실제 코드는 SeedSnapshot까지 포함해 15개**.
- `chainsight/models/__init__.py`에 모두 export됨.

### 마이그레이션 추적

| 번호 | 내용 |
|------|------|
| 0001_initial | Tier A/B + 관계 발견 + 집약 (12개) |
| 0002 | InsiderSignal, NarrativeTag |
| 0003 | ChainProfile, RevenueStructure |
| 0004 | neo4j_synced 필드 추가 (CS-3-1) |
| 0005 | neo4j_dirty + previous_status (redesign_v1 PR-1) |
| 0006 | SavedPath + PathAction (Phase 6) |
| 0007 | SeedSnapshot (시드 fallback DB 영속화) |

### 캐시/폴백 보강 (설계 외)

- `_get_today_seeds`의 3단 폴백 (Redis → SeedSnapshot → async 복구)은 설계서에 없는 운영 보강. **2026-04-24 사건**(테스트가 운영 Redis flush) 대응으로 추가됨 (CLAUDE.md 버그 #27 참조).

### 라우팅 충돌 회피

- `urls.py`가 고정 경로(seeds/, sector/, signals/, trace/) → 동적 경로(`<symbol>/...`) 순으로 배치. PR-4 지시서의 충돌 경고가 실 코드에 반영됨.

### 미반영 v1.4 사항

- 로드맵 v1.4 §2-1은 "체인 스토리 피드(④)는 v1.3 이후로 미룸"이라고 명시했으나, **실 구현은 PR-7로 이미 마침**. 문서가 코드보다 보수적.

---

## 결론

- **핵심 파이프라인 + 마켓뷰 + Path Watchlist까지 모두 가동 가능 상태**. M5("탐색 경험 1차 릴리즈") 달성, M3("Neo4j 풍부함") 달성.
- 다음 우선순위: **DC-2 ETF Holdings 실행**(그래프 다양성 확보) → **GDS 정기 배치**(노드 속성 신선도) → **CS-2-1b/1c 데이터 적재**(현재 빈 테이블 채움).
- Phase 3 이벤트 전파 모델은 D-2 의존성(60 거래일 축적)으로 시간이 필요. 현 단계에서는 우선순위 낮음.

**END OF AUDIT**
