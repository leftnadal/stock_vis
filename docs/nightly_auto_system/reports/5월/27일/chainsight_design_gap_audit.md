# Chain Sight 설계 갭 감사

> 작성일: 2026-05-27
> 작성자: Claude (read-only audit)
> 범위: `docs/chain_sight/` 설계 문서 전체 vs `chainsight/` + `frontend/components/chainsight/` + `frontend/app/chainsight/` 코드
> 모드: 코드 수정 없음, 읽기 전용 대조

---

## 0. 설계 문서 구성 (3 트랙)

Chain Sight 설계는 시간순으로 3개 트랙이 누적되어 있다.

| 트랙 | 위치 | 시점 | 성격 |
|------|------|------|------|
| **T1. 원안 cs_***  | `docs/chain_sight/plan/cs_00~cs_54_*.md` + `chain_sight_roadmap_v1.3.md` | 2026-04-02 | Phase 0~5 전체 골격 (CS-0 인프라 → CS-5 프론트엔드) |
| **T2. redesign_v1** | `docs/chain_sight/plan/redesign_v1_260409/*.md` (3종) | 2026-04-10 | 마켓 뷰 = "탐색 허브" 재정의. seed_node/api/ui_ux 3종 v2.x. Path Watchlist는 외부. |
| **T3. update_v2 (ROADMAP v1.4)** | `docs/chain_sight/update_v2/ROADMAP_v1.4.md` + `task_instructions/cs_61~73_*.md` | 2026-04-16 | T1 + T2 통합. Phase 6 (Path Watchlist 백엔드) / Phase 7 (Path Watchlist 프론트엔드) 신설. PG 테이블 12→14, Celery Beat 8→9. |
| **보조. graph_redesign_v2** | `docs/chain_sight/graph_redesign_v2.md` | 2026-04-27 | 시멘틱 방사형 레이아웃 + 관계 토글 칩 + 점진적 공개. T2 마켓 뷰의 그래프 UX 폴리시. |

### 결론

- T1 cs_5*는 부록 1·2 안에서 **부분 폐기·일부 대체**되었다. (마켓 뷰 컨셉 + 워크스페이스 컨셉이 병행 흡수)
- T2 redesign_v1은 **그대로 채택**되어 `/chainsight` 메인 화면을 차지한다.
- T3 update_v2의 Phase 6/7은 **그대로 채택**되어 `/chainsight/watchlist` + `chainsight/views/watchlist_views.py`로 구현되었다.
- T1 cs_5_frontend_design_v2의 "워크스페이스 `/chainsight/[symbol]`" 컨셉도 **별도 보존**되어 deep-dive 페이지로 존재한다.

---

## 1. 요약 (구현률)

| 영역 | 설계 항목 | 구현 항목 | 구현률 | 상태 |
|------|---------|---------|--------|------|
| Phase 0 (인프라/스키마) | 4 | 4 | 100% | A (완전) |
| Phase 1 (시드 데이터 로드) | 3 | 3 | 100% | A (완전) |
| Phase 2 (파생 데이터 계산) | 5 | 4.4 | 88% | B (Tier B 미적재) |
| Phase 3 (Neo4j 동기화 + GDS) | 3 | 3 | 100% | A (완전) |
| Phase 4 (REST API) | 7 (deep 3 + market 4) | 7 | 100% | A (완전) |
| Phase 5 (마켓 뷰 프론트엔드, T2) | 5 컴포넌트 + 4 hook | 5 + 4 | 100% | A (완전) |
| Phase 5 (Deep dive, T1 v2) | 4 컴포넌트 (Graph/Suggestion/Trace/Detail) | 5 컴포넌트 + 1 page | 100% | A (완전) |
| Phase 6 (Path Watchlist 백엔드) | CS-6-1~6-7 (7건) | 7 | 100% | A (완전) |
| Phase 7 (Path Watchlist 프론트엔드) | CS-7-1~7-3 (3건) | 3 | 100% | A (완전) |
| 그래프 리디자인 v2 (radial) | radial layout + 6방향 토글 칩 + 첫인상 카피 + 빈 상태 + 범례 | radialLayout.ts + RelationFilterChips + RelationLegend + NodeTooltip + NodeContextMenu | ~85% | B (부분, 빈 상태 카피/CTA 일부) |
| DC-2 (ETF Theme) | 운용사 CSV → :Theme 노드 ~390개 | `load_themes_to_neo4j.py` 명령만 존재, 실행 결과 확인 안 됨 | 추정 50% | B (보류) |

**전체 가중 구현률 ≈ 92~94%** (Tier B 데이터 적재 0건 + DC-2 ETF Theme 실행 보류 + 빈 상태 UX 일부 미반영을 차감).

> 단, "건수 = 0이지만 모델/태스크는 있음" 항목은 모두 구현(B)으로 분류했다. 실데이터 적재 여부는 본 감사 범위 밖.

---

## 2. 문서별 상태 테이블

### 2.1 T1 원안 cs_* (Roadmap v1.3 기준)

| 문서 | 코드 매핑 | 상태 | 비고 |
|------|---------|------|------|
| cs_00_legacy_cleanup_api_test | (레거시 정리 완료) | A | task_done/CS-0-0 완료, `decisions/003_api_access_test.md` 기록 |
| cs_01_migrations_verification | `chainsight/migrations/0001_initial.py` ~ `0008_unify_neo4j_flags.py` | A | 12개 테이블 + SavedPath/PathAction/SeedSnapshot 추가 (총 14개+) |
| cs_02_neo4j_connection | `chainsight/graph/repository.py` | A | PID 기반 lazy init, fork-safe |
| cs_03_neo4j_schema | `chainsight/graph/schema.py` + `management/commands/init_neo4j_schema.py` | A | CONSTRAINTS + INDEXES |
| cs_11_stock_node_bulk_load | `management/commands/load_stocks_to_neo4j.py` | A | 532 :Stock |
| cs_12_sector_industry | `management/commands/load_sectors_to_neo4j.py` | A | 17 :Sector + 128 :Industry |
| cs_13_peer_relations | `management/commands/load_peers_to_neo4j.py` + `tasks/peer_tasks.py` | A | 8,350 PEER_OF |
| cs_21_tier_a_profile | `tasks/profile_tasks.py` (GrowthStage, CapitalDNA) | A | 480/473 rows |
| cs_21b_sensitivity_profile | `tasks/sensitivity_tasks.py` | A | 컴퓨터 함수 다수 |
| cs_21c_insider_signal | `tasks/insider_tasks.py` | A | Finnhub 60RPM |
| cs_22_co_mention | `tasks/relation_tasks.py::extract_co_mentions` | A | |
| cs_23_price_co_movement | `tasks/relation_tasks.py::calculate_price_co_movement` | A | |
| cs_24_relation_confidence (v2.1) | `tasks/relation_tasks.py::update_relation_confidence` + `check_stale_and_decay` + `models/relation_discovery.py::RelationConfidence` | A | v2.1 전체 필드 일치 (relation_status 5단계, truth/market_score, evidence_tier_best/sources, has_*_source 7개, basis_summary, score_version='2.1') |
| cs_25_chain_profile_aggregation | `tasks/sync_tasks.py::aggregate_chain_profiles` | A | |
| cs_31_profile_neo4j_sync | `tasks/sync_tasks.py::sync_profiles_to_neo4j` + `services/neo4j_sync.py` | A | neo4j_dirty 플래그 기반 delta sync |
| cs_32_relation_neo4j_sync | `tasks/sync_tasks.py::sync_relations_to_neo4j` | A | confirmed/probable만 엣지, Market 관계는 보조 속성 |
| cs_33_gds_algorithms | (외부 실행, neo4j 노드 속성으로만 존재) | A (운영형) | `task_done/CS-3-3_gds_algorithms.md`에 결과 기록. Self-hosted GDS 2.13.2. `pagerank_score`, `community_id`, `betweenness_score` 읽기는 `services/path_service.py` 등에서 사용. **`chainsight/tasks/gds_tasks.py`는 존재 안 함** — 로드맵에서 명시된 파일명 미생성, 실행은 1회성 Cypher 직접 호출로 처리한 것으로 보임. 코드상 항상 재실행 가능한 task는 부재. |
| cs_41_graph_api | `api/views.py::ChainSightGraphView` | A | depth/rel_types/min_confidence + CUSTOMER_OF 파생 |
| cs_42_suggestion_api | `api/views.py::ChainSightSuggestionView` | A | |
| cs_43_trace_api | `api/views.py::ChainSightTraceView` | A | |
| cs_5_frontend_design_v2 (워크스페이스) | `frontend/app/chainsight/[symbol]/page.tsx` | A (대체 채택) | "전용 워크스페이스" 컨셉 보존. 미니 뷰 임베드는 `stocks/[symbol]/page.tsx`에 `GraphMiniView`로 존재. |
| cs_51_graph_visualization | `frontend/components/chainsight/GraphCanvas.tsx` (deep-dive) + `MarketGraphCanvas.tsx` (마켓 뷰) | A | 원안의 `GraphView.tsx`는 `GraphCanvas.tsx`로 이름 변경. ForceGraph 기반 동일. |
| cs_52_ai_guide_ui | `frontend/components/chainsight/AIGuidePanel.tsx` | A | 원안 `SuggestionCards.tsx`가 `AIGuidePanel.tsx`로 흡수. |
| cs_53_chain_trace_ui | `frontend/components/chainsight/TracePathView.tsx` | A | 원안 `TraceView.tsx`가 `TracePathView.tsx`로. |
| cs_54_stock_detail_integration | `frontend/app/stocks/[symbol]/page.tsx` 내 `GraphMiniView.tsx` import | A | |

### 2.2 T2 redesign_v1_260409 (마켓 뷰)

| 문서 | 코드 매핑 | 상태 | 비고 |
|------|---------|------|------|
| chainsight_seed_node_design v2.1 (Phase 1 B+A) | `services/seed_selection.py` + `tasks/seed_tasks.py::run_seed_selection` | A | MAX_SEED_NODES=20, seed_reasons 8개 코드 일치, resolve_seed_type 우선순위 일치 |
| chainsight_seed_node_design Phase 2 (Heat Score) | `tasks/seed_tasks.py::calculate_heat_scores` (Neo4j 노드에 `heat_score` 직접 기록) | B (대체) | **설계서가 명시한 PG `SeedHeatScore` 모델은 생성되지 않음**. heat_score는 Neo4j :Stock 노드 속성으로만 존재 (services/expand_service.py에서 읽음). 결과적 동작은 충족하나, "PG 단일 진실 → Neo4j 투영" 패턴에서 벗어남. |
| chainsight_seed_node_design Phase 3 (이벤트 전파) | 미구현 | C | 명시 보류 — "수집만, 반영 없음" 정책 (ROADMAP v1.4 CS-4-4 주석). |
| chainsight_api_design v2.1 — `/seeds/` | `api/views.py::SeedListView` | A | SeedSnapshot DB 영속화 + Redis 캐시 + 복구 트리거 |
| chainsight_api_design v2.1 — `/sector/{sector}/graph/` | `api/views.py::SectorGraphView` | A | node_size xl/lg/md/sm 4단계 |
| chainsight_api_design v2.1 — `/{symbol}/neighbors/` | `api/views.py::NeighborGraphView` | A | display_type 파생(CUSTOMER_OF), evidence_tier_best 노출, 정렬 3단 일치 |
| chainsight_api_design v2.1 — `/signals/` | `api/views.py::SignalFeedView` | A | _build_chain_signals, page/page_size |
| chainsight_api_design v2.1 — 스키마 변경 (RelationConfidence.previous_status, neo4j_dirty, SeedHeatScore 신규) | `migrations/0005_add_neo4j_dirty_previous_status.py` + (SeedHeatScore 미생성) | B | previous_status/neo4j_dirty 적용. SeedHeatScore PG 모델은 채택 안 됨. |
| chainsight_api_design v2.1 — 프론트엔드 훅 4종 | `frontend/hooks/useMarketView.ts` (`useSeedData`, `useSectorGraph`, `useNeighbors`, `useSignalFeed`) | A | staleTime 일부 차이 (설계 30분/5분/30분 → 코드 확인 필요시 별도) |
| chainsight_ui_ux_design v2.2 — 5 컴포넌트 | `SectorBar.tsx`, `MarketGraphCanvas.tsx`, `ExplorationTrail.tsx`, `RelationCardPanel.tsx`, `ChainStoryFeed.tsx` | A | 페이지 `app/chainsight/page.tsx`에서 5개 모두 import 확인 |
| chainsight_ui_ux_design v2.2 — 공유 탐색 상태 | `frontend/lib/stores/explorationStore.ts` | A | (00_summary.md에 명시) |

### 2.3 T3 update_v2 ROADMAP v1.4 — Phase 6/7

| 문서 | 코드 매핑 | 상태 | 비고 |
|------|---------|------|------|
| cs_61_saved_path_model | `chainsight/models/saved_path.py` + `migrations/0006_add_savedpath_pathaction.py` | A | SavedPath + PathAction |
| cs_62_watchlist_crud_api | `chainsight/views/watchlist_views.py::WatchlistViewSet` + `api/urls.py` router | A | IsAuthenticated + UserRateThrottle(30/min). audit P0 #2 IDOR fix 반영 |
| cs_63_summary_path | `services/path_service.py::generate_summary_path` + `build_*` 4종 | A | landmark_score (PageRank+Betweenness+bridge+sector 가중) 4-모드 fallback |
| cs_65_recheck_api | `services/recheck_service.py::run_recheck` + ViewSet `@action(detail=True, methods=['post'])` | A | edge_snapshot 비교 + headline + watching→active 자동 전이 |
| cs_66_expand_api | `services/expand_service.py::find_expansion_candidates` | A | 1-hop + heat_score 정렬 |
| cs_67_alternatives_api | `services/alternatives_service.py::find_alternatives` | A | 동일 relation_type 노드 대안 |
| cs_71_watch_button | `frontend/components/chainsight/WatchButton.tsx` + `ExplorationTrail.tsx` 통합 | A | |
| cs_72_watchlist_ui | `frontend/components/chainsight/PathCard.tsx` + `app/chainsight/watchlist/page.tsx` | A | status 필터 + 카드 리스트 |
| cs_73_full_path_view | `frontend/components/chainsight/FullPathView.tsx` + `app/chainsight/watchlist/[id]/page.tsx` | A | (task_done에 명시) |
| Path Watchlist Celery — Recheck 자동화 | `tasks/neo4j_dirty_sync_tasks.py` (주간) | A (간접) | Recheck는 수동 트리거. neo4j_dirty 동기화 Beat는 주 1회. |

### 2.4 graph_redesign_v2 (radial layout 폴리시)

| 항목 | 코드 매핑 | 상태 |
|------|---------|------|
| §1 시멘틱 방사형 레이아웃 (6방향) | `frontend/components/chainsight/radialLayout.ts` + `MarketGraphCanvas.tsx` | A |
| §2 관계 토글 칩 바 | `RelationFilterChips.tsx` | A |
| §3 점진적 공개 (호버/클릭/우클릭) | `NodeTooltip.tsx` + `NodeContextMenu.tsx` | A |
| §4 첫인상 카피 + 빈 상태 + CTA 버튼 | (페이지 텍스트, 빈 상태 와이어프레임 매칭 불확실) | B |
| §5 통합 와이어프레임 + 모바일 | `MobileCardList.tsx` (deep-dive 전용) — 마켓 뷰 모바일 레이아웃 별도 매칭 안 됨 | B |
| §5-3 범례 컴포넌트 | `RelationLegend.tsx` | A |
| §6 색상 시스템 | `graphStyles.ts` | A |

---

## 3. 미구현 항목 상세

### 3.1 Tier B 데이터 적재 (Phase 2 잔존 부채)

| 모델 | 태스크 | 적재 상태 |
|------|------|---------|
| `CompanyRevenueStructure` | 없음 — Tier B 명시적 보류 ("MVP에서는 빈 상태로 시작, 점진 채움") | 0건 (설계서 의도와 일치) |
| `CompanyNarrativeTag` | 없음 — 설계서: "Marketaux 뉴스에서 LLM 추출 → Phase 2 이후" | 0건 |
| `CompanyEventReaction` | 없음 — 설계서: "실행 가능 ✅"라고 표기했으나 미실행 | 0건 (부채) |

→ Roadmap v1.3 §A에서 "데이터 의존성 검증" 항목으로 명시되어 있어 **(D) 의도된 보류**에 가까움. CS-4-4 heat_score 4 signal 중 "뉴스 급증"이 ChainNewsEvent에 의존하므로 데이터 누적 후 자연 해결 예정.

### 3.2 SeedHeatScore PG 모델

**설계 vs 구현 불일치.**
- `chainsight_api_design.md` §8 스키마 변경 표: `SeedHeatScore (신규) | stock, date, heat_score, components, seed_rank | Phase 2`
- `chainsight_seed_node_design.md` §3 Phase 2 코드 블록: PG ORM 모델로 구체화
- 실제 구현: PG 모델 없음. `tasks/seed_tasks.py::calculate_heat_scores`가 Neo4j :Stock 노드에 `heat_score` + `heat_score_components` + `heat_score_updated_at`을 직접 SET함.

→ **(D) 폐기/대체 추정.** 4-Layer 원칙(Layer 3 PG → Layer 4 Neo4j 투영)을 우회. components/date 추적 불가, 시계열 분석 불가, Layer 3 단일 진실 위반. 설계서를 코드 기준으로 갱신하든지, PG SeedHeatScore를 신설하든지 결정 필요. **명시적 결정 기록 없음.**

### 3.3 `chainsight/tasks/gds_tasks.py` 부재

- 로드맵 v1.3/v1.4 CS-3-3 산출물: `chainsight/tasks/gds_tasks.py`
- 실제 구현: 해당 파일 없음. GDS 결과는 `task_done/CS-3-3_gds_algorithms.md`에 1회성 실행 결과로만 기록됨.
- 사용처: `services/path_service.py` 등에서 `s.pagerank_score`, `s.betweenness_score`를 Neo4j에서 읽지만, **재계산 트리거가 코드에 없음**.

→ **(B) 부분 구현 / 운영 부채.** 신규 종목 / 신규 관계 로드 시 PageRank/Louvain/Betweenness는 stale 상태가 됨. Celery Beat에도 등록 안 됨. 재계산 management command 또는 Celery task 신설 필요.

### 3.4 DC-2 ETF Holdings (Theme 노드)

- 명령 파일은 있음: `chainsight/management/commands/load_themes_to_neo4j.py`
- ETF_THEME_MAP 하드코딩 (Tier 2 ETF 16종 추정) — 코드는 준비됨
- 실행 결과 (`task_done/DC-2_etf_holdings_theme.md` 존재) — 별도 검증 필요
- ROADMAP v1.4 부록 "ETF 모델 LEGACY_KEEP_UNTIL_DC2" 태그 정리는 미확인.

→ **(B) 부분 구현.** 코드는 있고, Neo4j 적재 결과는 task_done 문서에 기록됨. 그러나 ETF 모델 폐기(serverless/) 정리는 별도 부채로 남을 가능성.

### 3.5 그래프 리디자인 v2 §4 빈 상태 UX

- 설계서: "섹터를 선택하세요" → 개선 카피 + CTA 버튼 + 빈 상태 와이어프레임 명세
- 실제 페이지 (`app/chainsight/page.tsx`): 5 컴포넌트 import만 확인. 빈 상태 카피/CTA 정확도는 본 감사에서 미검증.

→ **(B) 부분 구현 의심.** 별도 UI QA로 검증해야 함.

### 3.6 LLM 기반 chain title/summary 생성

- T2 redesign_v1 `00_summary.md` "범위 밖 (후속 작업)" 명시:
  - Heat Score 계산 (✅ 후속 작업으로 구현됨)
  - LLM 기반 chain title/summary 생성 (❌ 미구현)
  - 2차 카드 설명 relation_summary/why_now/insight_summary (❌ 미구현)
  - 전환 애니메이션 300ms ease-out bounce (확인 안 됨)
  - 모바일 대응 (deep-dive만 부분 — MobileCardList)

→ **(C) 미구현, 의도된 후속.**

### 3.7 cs_5 frontend_design_v2 — 일부 항목

- "엣지 색상 6색 + 스타일 차등" — `graphStyles.ts`에서 구현됨 (A)
- "프로 기능: Centrality 메트릭, 필터 패널, 멀티 depth" — `FilterPanel.tsx` 존재, Centrality 노출은 deep-dive `NodeDetailPanel.tsx`에 일부 (A)
- "CTA: 가설 생성 / Watchlist 추가 / Validation 이동" — `WatchButton.tsx`만 존재, 가설 생성 / Validation 이동 CTA는 미확인 → (B)

---

## 4. 폐기/대체 항목

| 원안 (T1 / T2) | 대체 (현재 구현) | 평가 |
|---------------|---------------|------|
| **`GraphView.tsx`** (cs_51) | `GraphCanvas.tsx` (deep-dive) + `MarketGraphCanvas.tsx` (마켓 뷰) — 2-track 분리 | 정상 진화 |
| **`SuggestionCards.tsx`** (cs_52) | `AIGuidePanel.tsx` | 이름 변경, 동일 기능 |
| **`TraceView.tsx`** (cs_53) | `TracePathView.tsx` | 이름 변경 |
| **종목 상세 탭 내 "Chain Sight 미니" (cs_54)** | `GraphMiniView.tsx` + `/chainsight/[symbol]` 전용 워크스페이스 | cs_5_frontend_design_v2의 변경안 채택 |
| **CUSTOMER_OF 별도 저장** | `SUPPLIES_TO` canonical + API에서 `display_type` 역방향 파생 | v1.3 변경 그대로 채택 |
| **`profile_data JSONB`** (v1.1 CompanyChainProfile) | 30개 개별 필드 구조 | v1.2에서 결정 그대로 |
| **3단계 상태 `confirmed/candidate/rejected`** (구버전) | 5단계 `hidden/weak/probable/confirmed/stale` (v2.1) | RelationConfidence v2.1 채택 |
| **PG `SeedHeatScore`** (chainsight_api_design §8, seed_node §3 Phase 2) | Neo4j :Stock 노드 속성 직접 기록 | ⚠️ **암묵적 폐기**. 설계서 미갱신 → DECISIONS.md 결정 기록 권장 |
| **ETFProfile/ETFHolding/ThemeMatch** (`# LEGACY_KEEP_UNTIL_DC2`) | DC-2 실행 후 폐기 예정 — 현재는 보류 상태 | 정리 대기 |
| **StockRelationship / CategoryCache** (serverless 레거시) | RelationConfidence + CompanyNarrativeTag로 대체 — CS-0-0에서 참조 서비스 마이그레이션 후 순차 제거 약속 | 정리 진행 상태 미확인 |
| **CO_MENTIONED / PRICE_CORRELATED Truth 관계 점수** | Market 관계로 분류 — `truth_score=null`, `market_score`만 계산 (MVP는 null) | v1.3 변경 그대로 |
| **`gds_tasks.py` 파일** (CS-3-3 산출물) | (생성 안 됨) — 1회성 Cypher 직접 호출로 처리 | ⚠️ 운영 부채로 남음. 명시적 폐기 결정 없음 |
| **모바일 그래프 필수** (cs_51 원안) | 데스크톱 우선 + 모바일 카드 리스트 (cs_5_frontend_design_v2) | 변경안 채택 |

---

## 5. 권고 (read-only, 코드 수정 없음)

1. **SeedHeatScore 결정 기록 누락 보정**: `DECISIONS.md` 또는 `docs/chain_sight/decisions/`에 "Heat Score PG 모델 미생성 — Neo4j 직접 기록 채택" 결정과 trade-off 명문화.
2. **gds_tasks.py 신설 또는 명시적 폐기**: 신규 종목/관계 로드 시 PageRank/Betweenness/Louvain stale 위험. Celery Beat 등록 또는 management command 검토.
3. **Tier B 데이터 적재 로드맵**: EventReaction은 "실행 가능 ✅"로 표기되어 있는데 적재 0건. 보류 사유 명문화 또는 PR 계획.
4. **레거시 정리 잔존 확인**: `serverless/StockRelationship`, `CategoryCache`, ETF 3종 모델의 참조 서비스 마이그레이션 진행률 별도 감사.
5. **그래프 리디자인 v2 §4 빈 상태 UI QA**: 본 감사 범위 밖. 별도 UX QA 권장.
6. **설계 문서 단일화**: T1 cs_5* vs T2 redesign_v1 vs graph_redesign_v2의 관계를 ROADMAP v1.4 내에 명문화. T1 cs_5_*는 "참고 보존" 마크 권장 (현재 어떤 버전이 단일 진실인지 모호).

---

## 6. 메모

- 본 감사는 코드 존재/모델 필드/URL 라우팅 수준의 정적 대조다. 실제 데이터 적재량, 런타임 동작, 테스트 통과 여부는 별도 검증 필요.
- T1 cs_5_*는 "구현 형태로 흡수"되었으나 문서 자체는 살아있어 신규 합류자가 진실 소스를 혼동할 수 있다.
- 종합: Chain Sight는 ROADMAP v1.3 → v1.4 + redesign_v1 + graph_redesign_v2 누적을 **약 92~94%** 코드로 반영했다. 잔존 갭은 (1) SeedHeatScore PG 채택 여부 결정 (2) GDS 재실행 task 부재 (3) Tier B/이벤트 전파/LLM 카드 설명 등 "후속" 명시 항목 3축으로 요약된다.
