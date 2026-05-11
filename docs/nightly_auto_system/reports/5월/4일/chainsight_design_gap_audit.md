# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-05
> **대상 디렉토리**: `chainsight/`, `frontend/components/chainsight/`, `frontend/app/chainsight/`
> **대조 설계서**: `docs/chain_sight/plan/` (cs_* 원본 + redesign_v1_260409), `docs/chain_sight/update_v2/`
> **참고**: `docs/chain_sight/task_done/` (chain_sight_redesign_V1, update_v2/task_done)
> **방법**: 코드 수정 없는 읽기 전용 정적 대조

## 요약 (구현률)

| Phase / 묶음 | 설계 항목 | 구현 | 비율 | 비고 |
|--------------|----------|------|------|------|
| **Phase 0 인프라** (CS-0-0~0-3) | 4 | 4 | **100%** | 레거시 정리, 마이그레이션, Neo4j 드라이버, 스키마 모두 완료 |
| **Phase 1 시드 로드** (CS-1-1~1-3) | 3 | 3 | **100%** | Stock(597) + Sector(17) + Industry(127) + PEER_OF(8,350) |
| **Phase 2 파이프라인** (CS-2-1~2-5) | 5 | 5 | **100%** | GrowthStage/CapitalDNA/Sensitivity/Insider/CoMention/PriceCo/Confidence/ChainProfile 전 task 존재 |
| **Phase 3 Neo4j 동기화 + GDS** (CS-3-1~3-3) | 3 | 2 | **67%** | sync_profiles/relations 구현. **GDS는 코드/태스크 부재** |
| **Phase 4 REST API** (CS-4-1~4-4) | 4 | 4 | **100%** | graph/suggestions/trace + heat_score 배치 모두 구현 |
| **Phase 5 프론트엔드 (cs_51~54 원안)** | 4 | 4 | **100%** | GraphCanvas / AIGuidePanel / TracePathView / [symbol] 통합 페이지 존재 — 단, UX 방향이 redesign_v1으로 대체됨 (D 분류) |
| **Phase 5 redesign_v1 (CS-5-5~5-6)** | 2 | 2 | **100%** | MarketView 5영역 + 시드 노드 시각 — bounce 애니메이션은 보류 |
| **Phase 5 redesign_v1 PR-1~7** | 7 | 7 | **100%** | 스키마/시드/dirty sync/마켓뷰 API/FE 코어/트레일+카드/체인스토리 |
| **Phase 6 Path Watchlist 백엔드** (CS-6-1~6-7) | 6 | 6 | **100%** | SavedPath/PathAction + CRUD + summary_path + recheck + expand + alternatives (CS-6-4 build_initial_why_now은 path_service 안에 흡수) |
| **Phase 7 Path Watchlist 프론트** (CS-7-1~7-3) | 3 | 3 | **100%** | WatchButton, Watchlist 페이지, FullPathView 모두 존재 |
| **Heat Score Phase 2 (heat_total 정렬, SeedHeatScore 모델)** | 3 | 1 | **33%** | calculate_heat_scores 배치는 있고 Neo4j 속성으로 저장. 그러나 **SeedHeatScore PostgreSQL 모델 미존재**, sector_summary 정렬 기준은 여전히 seed_count |
| **Phase 3 (D) 이벤트 전파 모델** | 3 | 0 | **0%** | text_conditional_prob / lagged_correlation / propagation_weight 전부 미구현 |
| **데이터 수집 DC-1~6** | 6 | 3 | **50%** | DC-1(Peer/Industry) ✅ / DC-2(ETF→Theme 21+534) ✅ / DC-3 수동 시드 ⚠️ ETFHolding 적재만, Supply Chain 시드 JSON 코드 부재 / DC-4(Gemini 확장) ❌ / DC-5(자연 축적) — 자연 진행 / DC-6(유료) — 보류 |

**총합 핵심 구현률 ≈ 90%** (이벤트 전파 D Phase, GDS, Phase 2 SeedHeatScore 제외 시 95% 이상).

## 문서별 상태 테이블

> 분류 정의: A=완전 구현 / B=부분 구현 / C=미구현 / D=폐기·대체

### Phase 0 / 1

| 문서 | 분류 | 코드 위치 | 상태 |
|------|------|----------|------|
| cs_00_legacy_cleanup_api_test | A | task_done 기록 + 결정문 003 | 레거시 6 view + 8 frontend 파일 정리, API 테스트 결과 결정문 보유 |
| cs_01_migrations_verification | A | `chainsight/migrations/0001~0007` | 7개 마이그레이션. RelationConfidence v2.1, neo4j_dirty/previous_status, SavedPath/PathAction, SeedSnapshot 모두 반영 |
| cs_02_neo4j_connection | A | `chainsight/graph/repository.py` (Neo4jGraphRepository, PID-based lazy init) | 로드맵의 Protocol+클래스 패턴 동일. Celery fork 안전 |
| cs_03_neo4j_schema | A | `chainsight/management/commands/init_neo4j_schema.py` + `graph/schema.py` | 4개 constraint + index 제공 |
| cs_11_stock_node_bulk_load | A | `services/neo4j_loader.py::load_stocks_to_neo4j`, `commands/load_stocks_to_neo4j.py` | DC-2 보고서 기준 597 노드 |
| cs_12_sector_industry | A | 동일 파일 `load_sectors_to_neo4j` + 명령어 | 17 Sector + 127 Industry |
| cs_13_peer_relations | A | `services/neo4j_loader.py::collect_all_peers/load_peers_to_neo4j` + `tasks/peer_tasks.py::fetch_and_load_peers` | PEER_OF 8,350 |

### Phase 2 (파이프라인)

| 문서 | 분류 | 코드 위치 | 상태 |
|------|------|----------|------|
| cs_21_tier_a_profile (GrowthStage + CapitalDNA) | A | `tasks/profile_tasks.py::calculate_growth_stages/capital_dna/all_profiles` | 480/473건 |
| cs_21b_sensitivity_profile | A | `tasks/sensitivity_tasks.py::calculate_sensitivity_profiles` (FMP geo seg 기반) | 모델 + 태스크 모두 존재 |
| cs_21c_insider_signal | A | `tasks/insider_tasks.py::calculate_insider_signals` (Finnhub Insider) | 모델 + 1.2초 rate-limit 구현 |
| cs_22_co_mention | A | `tasks/relation_tasks.py::extract_co_mentions` + `models/news_event.ChainNewsEvent` | NewsEntity → ChainNewsEvent → CoMentionEdge upsert. 구조는 설계와 동일하나 ChainNewsEvent 키가 (source, source_id) 조합 |
| cs_23_price_co_movement | A | `tasks/relation_tasks.py::calculate_price_co_movement` | 90일 rolling, 섹터 내 페어 |
| cs_24_relation_confidence | A | `tasks/relation_tasks.py::update_relation_confidence` + `check_stale_and_decay` | 5단계 상태, truth/market 분리, evidence_tier_best 등 v2.1 모두 존재 |
| cs_25_chain_profile_aggregation | A | `tasks/sync_tasks.py::aggregate_chain_profiles` + `config/celery.py` Beat 8개 | 1일/주간 스케줄 등록. cs_25 원안의 토 02:00은 **현재 토 02:00**으로 동일 적용. 추후 data_quality_3_fixes에서 일부 시각 조정됨 |

### Phase 3 (Neo4j 동기화 + GDS)

| 문서 | 분류 | 코드 위치 | 상태 |
|------|------|----------|------|
| cs_31_profile_neo4j_sync | A | `tasks/sync_tasks.py::sync_profiles_to_neo4j` | Delta sync (neo4j_synced 플래그) |
| cs_32_relation_neo4j_sync | A | `tasks/sync_tasks.py::sync_relations_to_neo4j` (현재는 dirty sync 위임) + `services/neo4j_sync.py::sync_dirty_relations` | data_quality_3_fixes 이후 dirty 패턴으로 일원화. SUPPLIES_TO만 canonical, CUSTOMER_OF는 API 파생 |
| cs_33_gds_algorithms | **C** | — | `chainsight/tasks/gds_tasks.py` 부재. `services/`에도 PageRank/Louvain/Betweenness 호출 없음. `update_v2/task_done/CS-3-3_gds_algorithms.md`에는 완료라 기록되어 있으나, 현 코드베이스에는 노드 속성 기록을 자동화하는 정기 task가 없다. 보고서가 있는 점을 보면 1회성 수동 실행으로 처리됐을 가능성. **재현 가능한 코드는 미존재** |

### Phase 4 (REST API)

| 문서 | 분류 | 코드 위치 | 상태 |
|------|------|----------|------|
| cs_41_graph_api | A | `chainsight/api/views.py::ChainSightGraphView` | depth ≤3, CUSTOMER_OF 파생, market_signals(co_mention_count, price_correlation) 포함 |
| cs_42_suggestion_api | A | `ChainSightSuggestionView` | peers/same_industry/co_mentioned/same_sector 카테고리. ⚠️ 설계서에 명시된 `community` 카테고리는 community_id 의존 → GDS 부재로 비어 있을 가능성 |
| cs_43_trace_api | A | `ChainSightTraceView` (shortestPath max 5) | 응답 포맷 부합 |
| cs_44_seed_node_heat_score (update_v2 신규) | B | `tasks/seed_tasks.py::calculate_heat_scores` (Beat 등록) | 4개 시그널 (price/volume/relation/news) Neo4j 속성 기록. **heat_total 기반 sector_summary 정렬은 미반영** (`SeedListView` 응답은 여전히 seed_count DESC) |

### Phase 5 (프론트엔드)

| 문서 | 분류 | 코드 위치 | 상태 |
|------|------|----------|------|
| cs_51_graph_visualization (원안) | **D → A** | `frontend/components/chainsight/GraphCanvas.tsx`, deep dive `/chainsight/[symbol]` | Spotlight + lazy expansion 그래프 자체는 deep dive 화면에 그대로 존재. 그러나 **메인 진입은 redesign_v1으로 대체** (cs_5_frontend_design_v2 + chainsight_ui_ux_design 흐름) |
| cs_52_ai_guide_ui | A | `AIGuidePanel.tsx` (deep dive 좌측) | 카테고리 카드 + strength 아이콘 |
| cs_53_chain_trace_ui | A | `TracePathView.tsx` | from/to 입력 + 경로 표시 |
| cs_54_stock_detail_integration | **D** | `frontend/app/stocks/[symbol]/page.tsx` | "Chain Sight 미니 뷰 임베드"는 폐기. data_quality_3_fixes 이후 종목 상세는 **딥링크 버튼**으로만 연결. UI 설계 v2.2 결론과 일치 |
| cs_5_frontend_design_v2 (전용 워크스페이스 v2) | A | `/chainsight/[symbol]` 3-panel | 좌측 AI Guide / 중앙 GraphCanvas / 우측 NodeDetailPanel + FilterPanel + MobileCardList 구현. 단, "Centrality 메트릭 표시"는 GDS 미존재로 부분적 |
| cs_55_market_view (update_v2) | A | `app/chainsight/page.tsx` + 5개 컴포넌트 (`SectorBar`/`MarketGraphCanvas`/`ExplorationTrail`/`RelationCardPanel`/`ChainStoryFeed`) | redesign_v1 PR-5~7 완료 |
| cs_56_seed_node (update_v2) | B | `MarketGraphCanvas` 시드 색상 + RelationCardPanel pre-focus | bounce 애니메이션 미적용 (CS-5-6 task_done에 명시) |

### redesign_v1 (chainsight_*_design v2.x)

| 설계서 | 분류 | 코드 위치 | 상태 |
|--------|------|----------|------|
| chainsight_seed_node_design v2.1 (Phase 1: B+A) | A | `services/seed_selection.py` 5개 소스 (price/volume/sector_outlier/relation/comention) + `tasks/seed_tasks.py::run_seed_selection` (매일 13:00 UTC Beat) | 시드 출력 7필드, MAX_SEED_NODES=20, 전일 fallback 모두 부합 |
| chainsight_seed_node_design Phase 2 (Heat Score C) | B | `calculate_heat_scores`만 존재 | **SeedHeatScore PostgreSQL 모델 부재** (`models/__init__.py`에 없음). 따라서 가중치 학습/sort_basis 전환 로직 미연결 |
| chainsight_seed_node_design Phase 3 (D 이벤트 전파) | **C** | — | `chainsight-text-conditional` / `chainsight-lagged-correlation` / `chainsight-propagation-weight` Beat 부재. text_conditional_prob, propagation_weight 코드 없음 |
| chainsight_api_design v2.1 (`/seeds/`, `/sector/{sector}/graph/`, `/{symbol}/neighbors/`, `/signals/`) | A | `chainsight/api/views.py` SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView | `truth_score?? market_score`, status 필터, node_size percentile, cross_edges, total_confidence 가중평균까지 명세 그대로 |
| chainsight_ui_ux_design v2.2 (5영역 + 상태 매트릭스) | A | `app/chainsight/page.tsx` + 5개 컴포넌트 + `lib/stores/explorationStore.ts` (Zustand 7개 상태 + 8개 액션) | 상태 매트릭스 (페이지 진입 / 섹터 / 노드 / 카드 / ?focus / 체인스토리)에 `initializeFocusExploration`, `startChainExploration` 모두 매핑 |
| chainsight_ui_ux_design 노드/엣지 디자인 토큰 | A | `MarketGraphCanvas.tsx`, `graphStyles.ts` | 시드 색상 4종, Truth/Market 엣지 스타일/굵기 적용. 다만 **truth_score 비례 굵기**는 일부 적용 (PR-5 보고서 확인) |
| chainsight_ui_ux_design 13. 모바일 | C | — | "Future consideration" 명시. 마켓 뷰 모바일 전환 미구현 (deep dive `/chainsight/[symbol]`에는 `MobileCardList.tsx` 존재) |
| chainsight_marketview_pr_prompts | A | PR-1~7 모두 task_done에 매핑 | 의존성 그래프 일치 |

### Phase 6 / 7 (update_v2 — Path Watchlist)

| 문서 | 분류 | 코드 위치 | 상태 |
|------|------|----------|------|
| cs_61_saved_path_model | A | `models/saved_path.py` SavedPath + PathAction + 마이그레이션 0006 | UUID PK, status 4종, recheck_count, ForeignKey to AUTH_USER_MODEL nullable |
| cs_62_watchlist_crud_api | A | `views/watchlist_views.py::WatchlistViewSet` + `serializers/path_watchlist.py` + `api/urls.py` router | list/create/retrieve/destroy + archive/resolve action |
| cs_63_summary_path | A | `services/path_service.py::generate_summary_path/build_path_signature/build_initial_why_now` + `commands/regenerate_summary_paths.py` | landmark 압축 |
| cs_65_recheck_api | A | `services/recheck_service.py::run_recheck` + WatchlistViewSet.recheck | 6단계 EdgeDiff, ACTIVE 전이 (2회 + 24h) |
| cs_66_expand_api | A | `services/expand_service.py::find_expansion_candidates` | RELATION_PRIORITY 가중 |
| cs_67_alternatives_api | A | `services/alternatives_service.py::find_alternatives` | before/after 제약 매칭 |
| cs_71_watch_button | A | `frontend/components/chainsight/WatchButton.tsx`, `ExplorationTrail.tsx` 통합 | sonner 토스트 + 핀 토글 |
| cs_72_watchlist_ui | A | `frontend/app/chainsight/watchlist/page.tsx`, `PathCard.tsx`, `lib/utils/pathStatus.ts`, `hooks/usePathWatchlist.ts` | 상태 필터 + 카드 + 액션 |
| cs_73_full_path_view | A | `frontend/app/chainsight/watchlist/[id]/page.tsx`, `FullPathView.tsx` | Recheck/Expand/Alternatives 상세 + 액션 로그 |

### 데이터 수집 DC-x

| 문서 | 분류 | 비고 |
|------|------|------|
| DC-1 (Peer + Industry, $0) | A | Phase 1에 흡수 완료 |
| DC-2 (ETF → Theme) | A | `commands/load_themes_to_neo4j.py`, Theme 21 + HAS_THEME 534 |
| DC-3 (수동 Supply Chain 시드 JSON) | C | 수동 시드 로더/JSON 부재. SUPPLIES_TO 엣지는 sec_pipeline 기반으로 대체된 것으로 보임 (별도 도메인) |
| DC-4 (Gemini Flash 확장) | C | rag_analysis 영역의 "관계 추출" 모델은 있으나 chainsight Supply Chain 확장 파이프라인은 미연결 |
| DC-5 (Marketaux 자연 축적) | A (자연 진행) | NewsEntity → CoMentionEdge 축적 동작 |
| DC-6 (Finnhub Premium) | C (보류) | 명시적 보류 |

## 미구현 항목 상세

### 1. Phase 3 (D) 이벤트 전파 모델 — 전면 미구현
**설계 위치**: `chainsight_seed_node_design.md` § 4
- `text_conditional_prob(A,B) = frequency × semantic_similarity`
- `lagged correlation` (lag0/1/2)
- `propagation_weight = 0.40·norm_text + 0.35·norm_price + 0.25·norm_volume` (텍스트 게이트 0.05)
- Celery Beat: `chainsight-text-conditional` (매일 13:00), `chainsight-lagged-correlation` (토 03:30), `chainsight-propagation-weight` (토 05:30) 모두 부재

**의존**: ChromaDB + Gemini Embedding (RAG 인프라). 현 chainsight 모듈에는 흔적 없음.

### 2. Heat Score Phase 2의 SeedHeatScore 모델 미존재
**설계 위치**: `chainsight_seed_node_design.md` § 3.4
```python
class SeedHeatScore(models.Model):
    stock = FK(Stock); date = DateField; heat_score; components(JSON); seed_rank
    unique_together = ('stock','date')
```
- 현재는 `calculate_heat_scores`가 Neo4j `:Stock.heat_score` 속성에만 기록.
- **PostgreSQL 영속화 + 일자별 누적이 없어 가중치 학습/sort_basis 전환·회귀 불가**.
- 결과적으로 `sector_summary` 정렬도 여전히 `seed_count DESC` 유지(설계서 § 3.5 미달).

### 3. CS-3-3 GDS 알고리즘 자동화 코드 부재
**설계 위치**: `cs_33_gds_algorithms.md`
- `chainsight/tasks/gds_tasks.py` 파일 자체 없음.
- `cs_44_seed_node_heat_score.md`의 community/centrality 시그널, `cs_42_suggestion_api`의 `community` 카테고리, deep dive UI의 "Centrality 메트릭" 모두 GDS 출력에 의존하므로 **간접 영향**.
- task_done 보고서에는 "M3 달성"으로 기재되어 있으나 재실행 가능한 코드 미존재 → 1회성 수동 실행 가능성.

### 4. cs_56 시드 노드 bounce 애니메이션
**설계 위치**: `chainsight_ui_ux_design.md` § 7 (전환 애니메이션 표)
- "시드 노드 = bounce" 미구현 (CS-5-6 task_done이 명시적으로 보류). MarketGraphCanvas는 색상 구분만 적용.

### 5. 모바일 마켓 뷰 (`/chainsight`)
**설계 위치**: `chainsight_ui_ux_design.md` § 13
- 마켓 뷰 페이지에는 모바일 전용 카드 리스트 분기 없음. 좁은 화면에서도 동일 5영역 레이아웃 사용.
- deep dive `/chainsight/[symbol]`에는 `MobileCardList.tsx`가 존재해 그래프 오버레이 UX가 구현되어 있음.

### 6. DC-3 / DC-4 (Supply Chain 수동 시드 + Gemini 확장 파이프라인)
- `chainsight/services/`에 supply_chain 시드 로더 없음. Gemini 호출 모듈도 chainsight 내부에는 부재.
- 현재 SUPPLIES_TO 데이터는 `sec_pipeline/`에서 공급되는 것으로 보임 (별도 앱). 로드맵상 chainsight 책임이라 명시되어 있어 갭으로 분류.

### 7. RelationConfidence-피드백 루프 (Thesis Control 양방향)
**설계 위치**: roadmap v1.3 § 1 원칙 5 (Thesis Control 검증 결과 → confidence 피드백)
- 코드/태스크에서 thesis 결과를 confidence에 역반영하는 경로 없음. 현재는 RelationConfidence가 자동 계산만 받음.

### 8. cs_42 community 카테고리 + cs_5 frontend_design_v2 Centrality 메트릭
- GDS 미존재로 인한 연쇄 갭 (위 §3과 동일 원인).

## 폐기/대체 항목

### D-1. cs_51~54 (종목 상세 탭 내 임베드 + 미니 그래프 + 전체 보기 진입)
- `cs_5_frontend_design_v2.md`(2026-04-04) → `chainsight_ui_ux_design.md` v2.2(2026-04-10)로 이어지는 흐름에서 **종목 상세의 Chain Sight 탭은 제거**, 대신 `/chainsight?focus={symbol}` 딥링크가 표준이 됐다.
- 코드에서도 `frontend/app/stocks/[symbol]/page.tsx`는 "Chain Sight에서 보기" 버튼만 유지. cs_54의 ChainSightMiniView 컴포넌트는 미구현.

### D-2. 단일 진입점 가정 (cs_51 원안의 메인 그래프 = 종목 단위)
- redesign_v1으로 **마켓 뷰 (`/chainsight`)가 메인 허브**, **deep dive (`/chainsight/[symbol]`)가 보조 워크스페이스**로 역할이 뒤집혔다. 코드 라우팅과 UI/UX 설계 v2.2에 동일하게 반영됨.

### D-3. CUSTOMER_OF 별도 저장 (v1.2 이전)
- 로드맵 v1.3에서 명시적으로 폐기 — `SUPPLIES_TO`만 canonical, API 응답에서 `derived_type=CUSTOMER_OF` 파생. `chainsight/api/views.py::ChainSightGraphView`/`NeighborGraphView::_display_type`에 그대로 적용됨.

### D-4. CompanyChainProfile JSONB 단일 필드
- v1.1의 `profile_data (JSONB)` 단일 필드 안은 폐기. v1.2 결정대로 30개 개별 필드 유지 (`models/chain_profile.py`).

### D-5. Sync 라벨 "RELATED_TO" 하드코딩
- 초기 `sync_relations_to_neo4j`가 모든 엣지를 `RELATED_TO`로 저장하던 패턴은 data_quality_3_fixes(2026-04-13)에서 폐기. 현재는 dirty sync 위임 + 동적 타입 (PEER_OF/CO_MENTIONED/PRICE_CORRELATED 등).

### D-6. cs_25 원안 Beat 시각 (`extract_co_mentions` 매일 06:30, `update_relation_confidence` 토 04:00 등)
- 운영 환경 보정 후 시각이 변경됨 (`config/celery.py`, data_quality_3_fixes의 "Celery Beat 타임라인" 참조).
  - co_mention: 매일 10:00
  - relation_confidence: 매일 11:00 (주간→일간으로 격상)
  - sync_relations_to_neo4j: 매일 12:30
  - seed-selection: 매일 13:00 UTC
- 설계 의도와 충돌은 없으나, 문서 대비 시각이 다름을 명시.

## 추가 관찰 — redesign_v1과 cs_* 원본의 관계

| 측면 | 결론 |
|------|------|
| `redesign_v1_260409/`가 cs_51~54를 **대체**하는가? | **부분 대체**. cs_51~54는 deep dive 워크스페이스에서 살아 있고, 마켓 뷰 진입은 redesign_v1으로 신설된 별개 트랙이다. cs_5_frontend_design_v2는 둘을 잇는 중간 설계로, 종목 상세 임베드(D-1)만 폐기하고 deep dive는 v2 사양으로 유지함 |
| update_v2 ROADMAP_v1.4가 v1.3을 대체하는가? | **확장**. v1.3까지의 Phase 0~5를 그대로 두고 Phase 6/7 (Path Watchlist), CS-4-4 (Heat Score), CS-5-5/5-6 (MarketView/Seed Node)을 추가. v1.3과 충돌 없음 |
| chainsight_seed_node_design Phase 1 vs CS-4-4 | **정합**. CS-4-4의 4-시그널(price/volume/relation/news)은 시드 노드 설계서 Phase 1 시드 5소스의 부분집합 + Heat Score 정의(§3)에 부합 |

## 결론

- 로드맵 v1.3 + redesign_v1 + update_v2(Phase 6/7)의 **MVP 범위(M5)는 사실상 모두 구현** 완료 상태.
- 명시적 갭은 (a) **GDS 자동화 코드**, (b) **이벤트 전파 D Phase**, (c) **SeedHeatScore PostgreSQL 영속화**, (d) **bounce 애니메이션 + 모바일 마켓 뷰** 4축. 이 중 (a)(c)는 후속 마켓 뷰 정렬·deep dive 시각화 품질에 직접 영향을 준다.
- 폐기/대체 항목은 모두 합리적 의사결정이며 코드와 문서가 일치함 — 단, **cs_51~54를 검토할 때는 redesign_v1을 함께 보지 않으면 오해 가능**하므로 운영 진입 가이드에 "메인은 마켓 뷰, deep dive는 cs_51~54 잔재"라는 주석을 한 번 남기는 편이 안전하다.
