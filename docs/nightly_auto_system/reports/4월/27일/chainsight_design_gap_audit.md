# Chain Sight 설계 갭 감사

> **감사일**: 2026-04-28
> **감사 범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `chainsight/` 백엔드 + `frontend/{app,components}/chainsight/` 프론트엔드
> **방법**: 읽기 전용 파일 대조 (코드 수정 없음)
> **참고**: `docs/chain_sight/task_done/` 완료 기록과 cross-reference

---

## 요약 (구현률)

| 영역 | 설계 항목 수 | 완전 구현 (A) | 부분 구현 (B) | 미구현 (C) | 폐기/대체 (D) | 구현률 (A+B 가중) |
|------|------------:|--------------:|---------------:|-----------:|--------------:|------------------:|
| Phase 0 (CS-0-0~3) 인프라 | 4 | 4 | 0 | 0 | 0 | **100%** |
| Phase 1 (CS-1-1~3) 시드 로드 | 3 | 3 | 0 | 0 | 0 | **100%** |
| Phase 2 (CS-2-1~5) 파생 파이프라인 | 5 | 5 | 0 | 0 | 0 | **100%** |
| Phase 3 (CS-3-1~3) Neo4j 동기화 + GDS | 3 | 3 | 0 | 0 | 0 | **100%** |
| Phase 4 (CS-4-1~3) Deep dive REST API | 3 | 3 | 0 | 0 | 0 | **100%** |
| Phase 5 원안 (cs_51~54) | 4 | 0 | 1 | 0 | 3 | **— (대체)** |
| Phase 5 v2 (cs_5_frontend_design_v2) | 1 | 1 | 0 | 0 | 0 | **100%** (Deep dive 전용 워크스페이스) |
| Redesign v1 마켓 뷰 (PR-1~7) | 7 | 7 | 0 | 0 | 0 | **100%** |
| 시드 노드 설계 Phase 1 (B+A) | 6 시드 소스 | 5 | 1 | 0 | 0 | **92%** |
| 시드 노드 설계 Phase 2 (Heat Score) | 1 모델 + 1 task | 0 | 1 | 1 | 0 | **30%** |
| 시드 노드 설계 Phase 3 (이벤트 전파, D-1~3) | 3 단계 | 0 | 0 | 3 | 0 | **0%** |
| 데이터 수집 DC-1~6 | 6 phase | 3 (DC-1, DC-2, DC-3 시드 일부) | 1 (DC-4 Gemini 확장 미실행) | 2 (DC-5 누적, DC-6 유료) | 0 | — |
| 추가 미설계 기능 (Watchlist, SavedPath, Recheck) | (설계서 외) | — | — | — | — | (보너스 구현) |

**총평**: 로드맵 v1.3에 정의된 "제품 출시 가능한 핵심 기능"(Phase 0~4 백엔드 + Redesign v1 프론트엔드 + 마켓 뷰 시드)은 **전부 구현 완료**되어 있다. 미구현 영역은 Phase 2 Heat Score 영속 모델, Phase 3 이벤트 전파, 2차 LLM 카드 설명 등 **로드맵 후속 단계** 또는 **DC-5 이후 데이터 누적이 전제**인 항목.

---

## 문서별 상태 테이블

### Phase 0 — 인프라 기반

| 문서 | 상태 | 코드 위치 / 근거 |
|------|------|-----------------|
| `cs_00_legacy_cleanup_api_test.md` | A 완전 | `task_done/CS-0-0_legacy_cleanup_api_test.md` (decisions/003). serverless Chain Sight 코드 제거, frontend Chain Sight 탭 비활성화 → 이후 `/chainsight/[symbol]` 딥링크로 재활성화 |
| `cs_01_migrations_verification.md` | A 완전 | `chainsight/migrations/0001_initial.py`~`0007_seedsnapshot.py` (총 7개), `chainsight/models/__init__.py` 13개 모델 export |
| `cs_02_neo4j_connection.md` | A 완전 | `chainsight/graph/repository.py:Neo4jGraphRepository` (PID 기반 lazy init, fork 안전), `graph/exceptions.py` |
| `cs_03_neo4j_schema.md` | A 완전 | `chainsight/management/commands/init_neo4j_schema.py`, `graph/schema.py` |

### Phase 1 — 초기 데이터 로드

| 문서 | 상태 | 코드 위치 / 근거 |
|------|------|-----------------|
| `cs_11_stock_node_bulk_load.md` | A 완전 | `chainsight/management/commands/load_stocks_to_neo4j.py`, `services/neo4j_loader.py:load_stocks_to_neo4j` |
| `cs_12_sector_industry.md` | A 완전 | `chainsight/management/commands/load_sectors_to_neo4j.py`, `services/neo4j_loader.py:load_sectors_to_neo4j` |
| `cs_13_peer_relations.md` | A 완전 | `chainsight/tasks/peer_tasks.py:fetch_and_load_peers`, `management/commands/load_peers_to_neo4j.py` (task_done에 8,350 PEER_OF 적재 확인) |

### Phase 2 — 파생 데이터 계산 파이프라인

| 문서 | 상태 | 코드 위치 / 근거 |
|------|------|-----------------|
| `cs_21_tier_a_profile.md` (GrowthStage, CapitalDNA) | A 완전 | `tasks/profile_tasks.py:calculate_growth_stages`, `calculate_capital_dna`, `calculate_all_profiles` |
| `cs_21b_sensitivity_profile.md` | A 완전 | `tasks/sensitivity_tasks.py:calculate_sensitivity_profiles` (FMP Geo segmentation + BalanceSheet + Stock.beta) |
| `cs_21c_insider_signal.md` | A 완전 | `tasks/insider_tasks.py:calculate_insider_signals` (Finnhub Insider Transactions) |
| `cs_22_co_mention.md` | A 완전 | `tasks/relation_tasks.py:extract_co_mentions` (Marketaux 90일) |
| `cs_23_price_co_movement.md` | A 완전 | `tasks/relation_tasks.py:calculate_price_co_movement` (90일 rolling correlation) |
| `cs_24_relation_confidence.md` + `relation_confidence_design_v1.md` | A 완전 | `tasks/relation_tasks.py:update_relation_confidence`, `check_stale_and_decay`. RelationConfidence v2.1 스키마(5단계 status + truth/market_score + evidence_tier_best + evidence_sources + 7개 has_*_source bool + relation_basis_summary + previous_status + neo4j_dirty)가 `models/relation_discovery.py`에 모두 존재 |
| `cs_25_chain_profile_aggregation.md` | A 완전 | `tasks/sync_tasks.py:aggregate_chain_profiles` |

### Phase 3 — Neo4j 동기화 + GDS

| 문서 | 상태 | 코드 위치 / 근거 |
|------|------|-----------------|
| `cs_31_profile_neo4j_sync.md` | A 완전 | `tasks/sync_tasks.py:sync_profiles_to_neo4j` (delta sync, neo4j_synced 플래그) |
| `cs_32_relation_neo4j_sync.md` | A 완전 | `tasks/sync_tasks.py:sync_relations_to_neo4j` + Redesign v1에서 `services/neo4j_sync.py:sync_dirty_relations` (neo4j_dirty 패턴) + `tasks/neo4j_dirty_sync_tasks.py` 추가 |
| `cs_33_gds_algorithms.md` | A 완전 | `task_done/CS-3-3_gds_algorithms.md`에 PageRank/Louvain/Betweenness 결과 기록(MSFT pagerank 1.92 등). 코드상 별도 `gds_tasks.py`는 없으며 일회성 management command 또는 외부 GDS 실행으로 처리한 것으로 추정 |

### Phase 4 — Deep dive REST API

| 문서 | 상태 | 코드 위치 / 근거 |
|------|------|-----------------|
| `cs_41_graph_api.md` (`GET /{symbol}/chainsight/graph/`) | A 완전 | `api/views.py:ChainSightGraphView` (depth 1~3, market_signals 보강, CUSTOMER_OF 파생, _sanitize_neo4j) |
| `cs_42_suggestion_api.md` (`GET /{symbol}/chainsight/suggestions/`) | A 완전 | `api/views.py:ChainSightSuggestionView` (peers/same_industry/co_mentioned/same_sector 4개 카테고리) |
| `cs_43_trace_api.md` (`GET /chainsight/trace/`) | A 완전 | `api/views.py:ChainSightTraceView` (shortestPath, max_depth 5) |

### Phase 5 — 프론트엔드 (3개 설계 세대)

| 문서 | 상태 | 코드 위치 / 근거 |
|------|------|-----------------|
| **원안 cs_51_graph_visualization.md** ("종목 상세 탭 내 GraphView, Spotlight + lazy expansion") | D 폐기/대체 | v2(cs_5_frontend_design_v2.md)에서 "전용 워크스페이스 `/chainsight/[symbol]`"로 변경. 단 Spotlight + lazy expansion 코어 UX는 `frontend/components/chainsight/GraphCanvas.tsx`에 그대로 살아있음 |
| **원안 cs_52_ai_guide_ui.md** ("SuggestionCards.tsx") | B 부분 (이름만 변경) | `frontend/components/chainsight/AIGuidePanel.tsx`로 구현 (좌측 패널 통합) |
| **원안 cs_53_chain_trace_ui.md** ("TraceView.tsx") | B 부분 (이름만 변경) | `frontend/components/chainsight/TracePathView.tsx` |
| **원안 cs_54_stock_detail_integration.md** ("종목 상세 Chain Sight 탭 활성화 + ChainSightMiniView") | D 폐기/대체 | `task_done/CS-5-1_frontend_graph.md`에서 GraphMiniView로 일시 활성화 → Redesign v1에서 종목 상세 탭은 "Chain Sight에서 보기" 딥링크 버튼으로 변경 (`frontend/app/stocks/[symbol]/page.tsx` 수정) |
| **v2 `cs_5_frontend_design_v2.md`** (전용 워크스페이스 + 3-panel + 6색 엣지 + CTA + 모바일 카드 리스트) | A 완전 | `frontend/app/chainsight/[symbol]/page.tsx` + 3-panel 컴포넌트(AIGuidePanel/GraphCanvas/NodeDetailPanel) + FilterPanel(CS-5-2 프로 기능) + MobileCardList(CS-5-3) |

### Redesign v1 (2026-04-09) — 마켓 뷰 + 시드 노드

> 위치: `docs/chain_sight/plan/redesign_v1_260409/` (chainsight_seed_node_design.md, chainsight_api_design.md, chainsight_ui_ux_design.md, chainsight_marketview_pr_prompts.md)

| 문서 / PR | 상태 | 코드 위치 / 근거 |
|-----------|------|-----------------|
| **PR-1 스키마 마이그레이션** (previous_status, neo4j_dirty, neo4j_synced_at) | A 완전 | `migrations/0005_add_neo4j_dirty_previous_status.py` + `models/relation_discovery.py:save()` 오버라이드 |
| **PR-2 시드 선정 task** (5개 시드 소스 + signal_count 랭킹 + 섹터 요약) | A 완전 | `services/seed_selection.py` (get_price_seeds, get_volume_seeds, get_sector_outlier_seeds, get_relation_change_seeds, get_comention_surge_seeds, select_seeds, build_sector_summary, cache_seed_result) + `tasks/seed_tasks.py:run_seed_selection`. 추가로 `models/seed_snapshot.py:SeedSnapshot` (Redis 휘발 대비 DB 영속화) — 설계서 외 보강 |
| **PR-3 Neo4j Dirty Sync** (neo4j_dirty=True 선택 동기화) | A 완전 | `services/neo4j_sync.py:sync_dirty_relations` + `tasks/neo4j_dirty_sync_tasks.py:run_neo4j_dirty_sync`. confirmed/probable upsert + hidden/weak/stale delete + market 관계 weak 동기화 |
| **PR-4 마켓 뷰 API 4종** (`/seeds/`, `/sector/{sector}/graph/`, `/{symbol}/neighbors/`, `/signals/`) | A 완전 | `api/views.py:SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView` (CUSTOMER_OF 파생, evidence_tier 노출, cross_edges, total_confidence 계산, sector seed pair shortestPath) |
| **PR-5 FE: 상태 + 섹터바 + 그래프** | A 완전 | `frontend/lib/stores/explorationStore.ts` (Zustand 7 상태 + 8 액션), `hooks/useMarketView.ts`, `components/chainsight/SectorBar.tsx`, `MarketGraphCanvas.tsx`, `app/chainsight/page.tsx` (`?focus=` 딥링크) |
| **PR-6 FE: 트레일 + 관계 카드** | A 완전 | `components/chainsight/ExplorationTrail.tsx`, `RelationCardPanel.tsx` (pre-focus/focused 분기) |
| **PR-7 FE: 체인 스토리 피드** | A 완전 | `components/chainsight/ChainStoryFeed.tsx` |

**API 설계서 cross-check** (`chainsight_api_design.md` v2.1):
- `/seeds/` 응답 스키마: date/total_seeds/sector_summary/seeds — ✅ `services/seed_selection.py:cache_seed_result` 페이로드와 일치
- `/sector/{sector}/graph/` 응답: nodes[node_size xl/lg/md/sm + is_seed + seed_type] / edges[truth_score/market_score/relation_category/status] — ✅ `SectorGraphView` 일치
- `/{symbol}/neighbors/` 응답: center + neighbors[relation{type, display_type, direction, evidence_tier_best, ...}] + cross_edges — ✅ `NeighborGraphView` 일치 (필드명 `evidence_tier`로 약간 축약)
- `/signals/` 응답: chains[id/title/category/strength/total_confidence/path/trigger_summary] — ✅ `SignalFeedView` 일치

**UI/UX 설계서 cross-check** (`chainsight_ui_ux_design.md` v2.2):
- 5단계 화면 구조(① SectorBar ② MarketGraphCanvas ③ ExplorationTrail ④ RelationCardPanel ⑤ ChainStoryFeed) — ✅ 일치
- 노드 디자인 6색(price/volume/relation 시드별), 엣지 6색(SUPPLIES_TO/COMPETES_WITH/PEER_OF/CO_MENTIONED/PRICE_CORRELATED) — ✅ `MarketGraphCanvas.tsx` (1,017줄) 내 styling 존재
- pre-focus/focused 분기 — ✅ `RelationCardPanel.tsx` 분기 처리
- 종목 상세 → `?focus=` 딥링크 — ✅ `app/chainsight/page.tsx` `useEffect` + `initializeFocusExploration`

### 시드 노드 설계 Phase 1 (B+A) — `chainsight_seed_node_design.md`

| 시드 소스 | 상태 | 근거 |
|----------|------|------|
| EOD 수익률 이상치 (price_top5/bottom5) | A | `services/seed_selection.py:get_price_seeds` (±2σ) |
| EOD 거래량 급증 (volume_surge) | A | `get_volume_seeds` (volume/SMA20 ≥ 2.0) |
| 섹터 평균 ±2σ (sector_outlier) | A | `get_sector_outlier_seeds` |
| RelationConfidence 상태 전이 (relation_upgrade/downgrade) | A | `get_relation_change_seeds` (previous_status 활용) |
| co-mention 급증 (comention_surge) | A | `get_comention_surge_seeds` |
| 신규 관계 발견 (relation_new) | B 부분 | `SEED_REASONS` 상수에는 정의되어 있으나 별도 시드 소스 함수 없음 — `relation_change_seeds` 안에서 previous_status 빈 값을 신규로 분류 가능하나 명시적 코드 흐름 없음 |

### 시드 노드 설계 Phase 2 (Heat Score)

| 항목 | 상태 | 근거 |
|------|------|------|
| `SeedHeatScore` 모델 (heat_score, components JSON, seed_rank) | C 미구현 | 설계서 §3.4에 정의되어 있으나 `chainsight/models/`에 해당 모델 파일 없음 (sensitivity, growth_stage, capital_dna, insider_signal, narrative_tag, event_reaction, revenue_structure, chain_profile, news_event, relation_discovery, saved_path, seed_snapshot 12개만 존재) |
| `chainsight-heat-score` Beat task (매일 11:30) | B 부분 | `tasks/seed_tasks.py:calculate_heat_scores` 함수 자체는 존재. 단 결과를 `SeedHeatScore`가 아닌 **Neo4j :Stock 노드 속성**(`s.heat_score`, `s.price_signal` 등)에 직접 SET. 설계서의 PostgreSQL 영속화 + seed_rank 정렬 부분은 미구현 |
| sector_summary 정렬 기준 `heat_total DESC` (Phase 2+) | C 미구현 | `services/seed_selection.py:build_sector_summary`는 `seed_count DESC` (Phase 1)로 고정 정렬. heat_total 가중 정렬 분기 없음 |

### 시드 노드 설계 Phase 3 (이벤트 전파, D-1~D-3)

| 단계 | 상태 | 근거 |
|------|------|------|
| D-1 text_conditional_prob (ChromaDB + Gemini Embedding) | C 미구현 | 코드/설정/모델 모두 없음. ChromaDB 의존성 미설정 |
| D-2 lagged correlation + volume_response + propagation_weight | C 미구현 | 60 거래일 전제 + D-1 의존 |
| D-3 사후 검증 → 가중치 학습 | C 미구현 | D-2 의존 |
| `chainsight-text-conditional` Beat (매일 13:00) | C 미구현 | Beat 등록 없음 |
| `chainsight-lagged-correlation` Beat (토 03:30) | C 미구현 | Beat 등록 없음 |
| `chainsight-propagation-weight` Beat (토 05:30) | C 미구현 | Beat 등록 없음 |

### 데이터 수집 (DC-1 ~ DC-6)

| Phase | 상태 | 근거 |
|-------|------|------|
| DC-1 PEER_OF + SAME_INDUSTRY | A | task_done CS-1-3에 PEER_OF 8,350개 적재 확인 |
| DC-2 ETF Holdings → HAS_THEME | A | `task_done/DC-2_etf_holdings_theme.md` Theme 21개 적재 + `management/commands/load_themes_to_neo4j.py` 존재. 단 운용사 CSV 방식으로 진행 (Finnhub 403) |
| DC-3 수동 시드 JSON → SUPPLIES_TO | B 부분 | task_done에 별도 DC-3 문서 없음. `RelationConfidence` SUPPLIES_TO 적재는 일부 진행된 것으로 보이나 manual_seed JSON 위치/규모는 별도 검증 필요 |
| DC-4 Gemini Flash → Supply Chain 확장 ~1,100개 | C 미구현 | 코드/태스크 흔적 없음 |
| DC-5 뉴스 자연 축적 | B 부분 | 인프라(extract_co_mentions Beat)는 있으나 누적은 시간 의존 |
| DC-6 유료 API 업그레이드 | C 미구현 (보류) | 수익화 이후 트리거 — 정책상 의도적 보류 |

### Celery Beat 스케줄

> 설계서 vs `task_done/celery_beat_registration.md` (8개 Chain Sight Beat 등록 완료)

| Beat 이름 | 설계 (cs roadmap §2.4 / seed §6) | 실제 등록 |
|----------|-----------------------------|----------|
| chainsight-co-mentions | 매일 06:30 | 매일 10:00 (드리프트) |
| chainsight-relation-confidence | 토 04:00 | 매일 11:00 (드리프트, 매일 실행으로 강화) |
| chainsight-stale-decay | 토 04:30 | 토 04:00 |
| chainsight-aggregate-profiles | 토 05:00 | 토 04:30 |
| chainsight-all-profiles (Tier A 묶음) | 토 02:00 | 토 02:00 |
| chainsight-price-co-movement | 토 03:00 | 토 03:00 |
| chainsight-sync-profiles-neo4j | (설계 무명시) | 매일 12:00 |
| chainsight-sync-relations-neo4j | (설계 무명시) | 매일 12:30 |
| chainsight-seed-selection | 매일 12:00 | 매일 13:00 UTC (Redesign v1 PR-2) |
| chainsight-neo4j-dirty-sync | (Redesign v1 PR-3) | 매주 일 04:30 (neo4j queue) |
| chainsight-heat-score-daily | 매일 11:30 (설계서) | 코드(`calculate_heat_scores`)는 있으나 `task_done/celery_beat_registration.md`에 미등록 — Beat에서 호출되지 않을 가능성 |

---

## 미구현 항목 상세

### 1. Heat Score Phase 2 영속화 — Critical Gap

**설계서**: `chainsight_seed_node_design.md` §3.4 ~ §3.5, §6
- `SeedHeatScore(stock, date, heat_score, components, seed_rank)` 모델
- `chainsight-heat-score` Beat 매일 11:30
- sector_summary 정렬을 `heat_total DESC`로 전환

**현 구현**:
- `tasks/seed_tasks.py:calculate_heat_scores`는 존재하나 결과를 **Neo4j :Stock 노드 속성**으로만 저장
- Postgres `SeedHeatScore` 테이블 미생성 → 일별 시계열/seed_rank/components 검증 불가
- `services/seed_selection.py:build_sector_summary`는 여전히 `seed_count DESC` 고정 정렬
- Beat 등록 자체가 누락된 것으로 보이며 (`celery_beat_registration.md`의 8개 task에 없음), 이 함수는 사실상 dead code일 가능성

**영향**: 마켓 뷰 섹터 바 정렬 기준이 Phase 1 단순 카운트에서 벗어나지 못함. 시드 노출 우선순위 정밀도 부족.

### 2. Phase 3 이벤트 전파 모델 (D-1 / D-2 / D-3)

**설계서**: `chainsight_seed_node_design.md` §4
- D-1: 뉴스 → Gemini Embedding → text_conditional_prob (ChromaDB)
- D-2: lagged price correlation + volume_response → propagation_weight (텍스트 게이트 0.05)
- D-3: 사후 검증 → 가중치 학습

**현 구현**: 전무. ChromaDB 의존성, propagation_weight 계산, 텍스트 게이트 어디에도 없음.

**영향**: "이벤트 전파"라는 Chain Sight 핵심 가치 제안 중 정성→정량 변환 축이 미작동. 단기 출시는 영향 없음(Phase 3 = 60 거래일 데이터 누적 후 진입).

### 3. 2차 카드 설명 필드 (LLM 기반)

**설계서**: `chainsight_api_design.md` §4 "2차 필드 확장 (향후)" + `chainsight_ui_ux_design.md` §9 카드 설명 필드 전략 2단계
- `relation.relation_summary`, `why_now`, `insight_summary` 필드를 `/{symbol}/neighbors/` 응답에 추가
- `signals/`의 chain title/trigger_summary를 LLM 생성으로 강화

**현 구현**:
- `RelationCardPanel.tsx`는 1차 템플릿(고정 문구) 기준만 렌더
- API 응답에 LLM 생성 필드 미포함
- chain title은 `f'{path_nodes[0]} → {path_nodes[-1]} chain'` 단순 포맷

**영향**: 사용자 학습 곡선/탐색 효율성 저하. 출시 후 점진 보완 가능 영역.

### 4. 신규 관계 (relation_new) 시드 소스 명시 함수 부재

**설계서**: SEED_REASONS 상수에 `relation_new` 정의

**현 구현**: `services/seed_selection.py`에 `get_relation_new_seeds` 함수 없음. `get_relation_change_seeds`가 previous_status 빈 값을 처리하지 않아 신규 생성 케이스가 시드로 잡히지 않을 수 있음.

### 5. Phase 2 Beat 스케줄 드리프트

설계서의 매일 06:30 (co-mention), 토 04:00 (relation_confidence)이 실제로는 매일 10:00, 매일 11:00로 변경. 의도된 정책 변경(매일 강화)일 수 있으나 설계서와 실제 운영 스케줄 간 단일 소스가 없음. `chain_sight_roadmap_v1.3.md` §2.4 코드 블록과 `celery_beat_registration.md` 표가 차이남.

### 6. DC-3 manual_seed JSON / DC-4 Gemini Supply Chain 확장

DC-3 수동 JSON 시드 위치, 적재 절차에 대한 task_done 기록이 없음. DC-4(Gemini Flash로 Supply Chain ~1,100개 확장) 코드/태스크 흔적 없음. Supply Chain 관계 풍부도가 낮은 상태로 출시됨을 의미.

---

## 폐기/대체 항목

### D-1. cs_51 원안 — "종목 상세 탭 내 그래프"

| 항목 | 원안 | 실제 |
|------|------|------|
| 진입 경로 | 종목 상세 페이지 Chain Sight 탭 | (1차) 전용 워크스페이스 `/chainsight/[symbol]` (cs_5_frontend_design_v2) → (2차) 마켓 뷰 허브 `/chainsight` 우선 (redesign_v1) |
| 그래프 구조 | Spotlight + lazy expansion + 1-depth | Deep dive workspace는 동일 유지. 마켓 뷰는 sector overview + neighbor 그래프(MarketGraphCanvas)로 분기 |
| 출처 | `cs_51_graph_visualization.md`, `cs_54_stock_detail_integration.md` | `cs_5_frontend_design_v2.md`(섹션 0 변경 사유 표) → `redesign_v1_260409/chainsight_ui_ux_design.md` |

### D-2. ChainSightMiniView (종목 상세 임베드)

| 항목 | 원안 | 실제 |
|------|------|------|
| 종목 상세 통합 | ForceGraph2D 미니 그래프 + 연결 종목 태그 + "전체 보기" 링크 | Redesign v1에서 미니 그래프 제거 → "Chain Sight에서 보기" 딥링크 버튼만 유지 (`?focus={symbol}`) |
| 출처 | `cs_54_stock_detail_integration.md` | `chainsight_ui_ux_design.md` v2.2 §11 |
| 코드 잔재 | `frontend/components/chainsight/GraphMiniView.tsx` 파일은 잔존 (203줄). 사용처 검증 필요 — `app/stocks/[symbol]/page.tsx`에서 더 이상 임베드 안 할 가능성 |

### D-3. CUSTOMER_OF 별도 저장

| 항목 | 원안 (v1.1) | 실제 (v1.3 / Redesign v1) |
|------|------------|---------------------------|
| 저장 모델 | CUSTOMER_OF를 RelationConfidence에 별도 row로 저장 | **SUPPLIES_TO만 canonical 저장**, API에서 `direction='outbound'`일 때 `display_type='CUSTOMER_OF'` 파생 |
| 출처 | `chain_sight_roadmap_v1.3.md` §2.4 변경 |
| 코드 | `RelationConfidence.RELATION_TYPE_CHOICES`에 CUSTOMER_OF 없음. `api/views.py:NeighborGraphView._display_type` + `ChainSightGraphView`에서 파생 처리 |

### D-4. 종목 상세 Chain Sight 탭 활성화 (Coming Soon → 임베드 → 딥링크)

3단 변경:
1. CS-0-0: 기존 serverless Chain Sight 탭 → "Coming Soon" 비활성화
2. CS-5-1 (`task_done`): GraphMiniView로 1차 활성화
3. Redesign v1 (`task_done/chain_sight_redesign_V1/PR-5_fe_core_ui.md`): 미니 그래프 제거 → "Chain Sight에서 보기" 딥링크 버튼만 유지

### D-5. CompanyChainProfile JSONB 단일 필드

로드맵 v1.1에서 제안된 `profile_data (JSONB)` 단일 필드는 v1.2에서 30개 개별 필드로 대체 결정. 현 코드(`models/chain_profile.py`)는 개별 필드 구조를 따름.

### D-6. 시드 노드 시각 강조 — Spotlight bounce

설계서 §7 "시드만 bounce" 애니메이션은 코드상 구현 여부가 보고서 범위 외 (모니터링 필요). `MarketGraphCanvas.tsx`(1,017줄)에 bounce 관련 styling이 들어있을 가능성 — 별도 시각 QA 필요.

---

## 보너스 — 설계서 외 추가 구현 (CS-6 영역?)

설계서(plan/)에 명시되지 않으나 코드에 존재하는 기능:

| 기능 | 코드 위치 | 비고 |
|------|----------|------|
| **SavedPath / PathAction** (경로 저장 + 액션 로그) | `models/saved_path.py`, `migrations/0006`, `views/watchlist_views.py:WatchlistViewSet` | UUID PK + status (watching/active/archived/resolved) + path_signature + edge_snapshot. CS-6-1로 추정 — `docs/chain_sight/plan/`에 cs_6* 문서 없음 |
| **Recheck 서비스** (저장 경로 변경 감지 + headline 생성 + 자동 watching→active 전이) | `services/recheck_service.py`, `WatchlistViewSet.recheck` | EdgeDiff/RecheckResult 데이터클래스 |
| **Expand 서비스** (경로 확장 후보 추천) | `services/expand_service.py`, `WatchlistViewSet.expand` | truth_score + heat_score 기반 확장 점수 |
| **Alternatives 서비스** (대안 경로 제시) | `services/alternatives_service.py`, `WatchlistViewSet.alternatives` | both-side / one-side 쿼리 |
| **Path Service** (summary_path, landmark scores, signature) | `services/path_service.py` | centrality(pagerank/betweenness/community) + sector_uniqueness + bridge_score |
| **`regenerate_summary_paths` management command** | `management/commands/regenerate_summary_paths.py` | 배치 재생성 |
| **`SeedSnapshot` 모델** (Redis 휘발 대비 DB 영속화) | `models/seed_snapshot.py`, `migrations/0007` | 2026-04-24 운영 사건 기반 보강 — 설계서 외 운영 보강 |
| **프론트 Watchlist 페이지** | `frontend/app/chainsight/watchlist/page.tsx`, `[id]/page.tsx`, `components/chainsight/PathCard.tsx`, `FullPathView.tsx`, `WatchButton.tsx` | |
| **RelationFilterChips** (관계 토글 칩 바) | `frontend/components/chainsight/RelationFilterChips.tsx` | 최근 5 커밋(`FE-PR-1~5 chainsight 그래프 v2`)에서 추가된 시각 위계/시멘틱 방사형 좌표/점진적 공개/빈 상태 일러스트 — 설계서 외 UX 강화 |

→ **권고**: 이 영역(SavedPath + Watchlist + Recheck/Expand/Alternatives)은 plan/cs_6*.md 문서가 부재. 추후 **Chain Sight 가설 통제 / 경로 저장 설계서**를 사후 작성하여 단일 소스를 확보하는 것을 권장.

---

## 결론

- **출시 가능 핵심 기능**(Phase 0~4 + Redesign v1 마켓 뷰 + Phase 5 Deep dive workspace)은 설계 대비 **완전 구현**.
- **남은 갭**은 (a) Phase 2 Heat Score 영속 모델, (b) Phase 3 이벤트 전파 D-1~3, (c) LLM 2차 카드 설명, (d) DC-4 Gemini Supply Chain 확장 — 모두 **로드맵상 후속 단계** 또는 **데이터 누적 의존**.
- **설계서 갱신 필요**:
  1. Beat 스케줄 단일 소스(설계서 vs `celery_beat_registration.md` 드리프트 정리)
  2. SavedPath/Watchlist/Recheck/Expand/Alternatives 사후 설계서 작성 (CS-6 plan 문서)
  3. `cs_51~54` 폐기 명시 헤더 + Redesign v1로 위임 표시 (현재는 v1.3 로드맵 본문에서만 v1.1과 동일 처리)
  4. Heat Score 영속화 결정 — Neo4j 속성 단독 vs `SeedHeatScore` 테이블 신설 중 선택 필요
- **redesign_v1_260409/는 cs_5*에 대한 부분 대체**: 마켓 뷰(`/chainsight`) 영역은 redesign_v1이 사실상 단일 소스. Deep dive workspace(`/chainsight/[symbol]`)는 cs_5_frontend_design_v2.md가 여전히 유효.
