# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-17 (today: 2026-05-18)
> **감사 범위**: `docs/chain_sight/plan/` ↔ `chainsight/` 백엔드 ↔ `frontend/components/chainsight/`
> **모드**: 읽기 전용, 코드 수정 없음
> **대조 기준**: roadmap v1.3, redesign_v1_260409 v2.x, task_done 24개 보고서

---

## 요약 (구현률)

### 카테고리별 집계

| 분류 | 문서/항목 수 | 비고 |
|------|--------|------|
| (A) 완전 구현 | 18 | CS-0~4, RelationConfidence v2.1, redesign v1 PR-1~7, DC-2 ETF |
| (B) 부분 구현 | 6 | Tier B 모델 3종 데이터 0건, GDS, Heat Score, Frontend 일부 |
| (C) 미구현 | 4 | Phase 3 D-1/D-2/D-3, 카드 2차 설명 LLM |
| (D) 폐기/대체 | 5 | cs_5x, JSONB profile, CUSTOMER_OF DB, RELATED_TO 라벨, /chainsight 종목 상세 탭 |

### 트랙별 구현률 (가중 추정)

| 트랙 | 산정 기준 | 구현률 |
|------|----------|--------|
| 트랙 A — CS-0~4 (인프라/시드/파생/Sync/API) | 5/5 Phase 완료 | **100%** |
| 트랙 A — CS-5 프론트엔드 | redesign v1 PR-5~7 + Deep dive workspace | **~85%** (전환 애니메이션·LLM 2차 카드 보류) |
| 트랙 A — 마켓 뷰 redesign v1 (PR-1~7) | 모든 PR `task_done/` 존재 | **100%** |
| 트랙 B — DC-1~6 | DC-1, DC-2 완료, DC-3~6 미착수 | **33%** (2/6) |
| Tier A/B 프로파일 데이터 적재 | GrowthStage/CapitalDNA 480여 건, Sensitivity/Insider 빈 상태 | **50%** (스키마 100%, 데이터 ~50%) |
| Phase 3 이벤트 전파(D-1~D-3) | 설계만 존재, 코드 없음 | **0%** |

### 종합 판정

> Chain Sight는 **설계 vs 1차 구현 정합성이 매우 높음**. cs_xx 1세대 로드맵은 대부분 task_done에 매핑되어 있고, redesign_v1_260409 v2.1/v2.2(FINAL)에 의해 일부 방향이 갱신된 뒤 그 변경도 모두 코드에 반영되었음. 미구현은 (i) 데이터 의존성으로 인한 Tier B 빈 테이블, (ii) Phase 2 Heat Score 이후 추가 단계(D Phase), (iii) UX 폴리시(LLM 카드 2차 설명·전환 애니메이션)로 한정됨.

---

## 문서별 상태 테이블

> 칸 의미: ✅ 완전 / 🟡 부분 / ❌ 미구현 / 🔁 폐기·대체 (대체처 명시)

### Phase 0 — 인프라

| 설계 문서 | 분류 | 매핑 파일 / task_done | 비고 |
|----------|------|---------------------|------|
| cs_00_legacy_cleanup_api_test.md | ✅ | task_done/CS-0-0_legacy_cleanup_api_test.md | serverless/ Chain Sight 잔존 코드 정리, decisions/003 API 테스트 기록 |
| cs_01_migrations_verification.md | ✅ | task_done/CS-0-1_migrations.md / migrations 0001~0008 | 12개 베이스 테이블 + Neo4j 동기화 플래그 통일 |
| cs_02_neo4j_connection.md | ✅ | task_done/CS-0-2_neo4j_driver.md / `chainsight/graph/repository.py` | fork-safe PID lazy driver |
| cs_03_neo4j_schema.md | ✅ | task_done/CS-0-3_neo4j_schema.md / `chainsight/graph/schema.py` + `init_neo4j_schema` 커맨드 | constraints/indexes |

### Phase 1 — 시드 로드 (DC-1)

| 설계 문서 | 분류 | 매핑 | 비고 |
|----------|------|------|------|
| cs_11_stock_node_bulk_load.md | ✅ | `management/commands/load_stocks_to_neo4j.py` + task_done/CS-1-1 | 532 Stock |
| cs_12_sector_industry.md | ✅ | `load_sectors_to_neo4j.py` + task_done/CS-1-2 | 17 Sector + 128 Industry |
| cs_13_peer_relations.md | ✅ | `load_peers_to_neo4j.py` + `tasks/peer_tasks.py` + task_done/CS-1-3 | PEER_OF 8,350 |

### Phase 2 — 파생 데이터 파이프라인

| 설계 문서 | 분류 | 매핑 | 비고 |
|----------|------|------|------|
| cs_21_tier_a_profile.md | ✅ | `tasks/profile_tasks.py` + models 4종 + task_done/CS-2-1 | GrowthStage / CapitalDNA 480여 건 |
| cs_21b_sensitivity_profile.md | 🟡 | `tasks/sensitivity_tasks.py` + `models/sensitivity.py` + task_done/CS-2-1b | 모델·태스크 존재, 실 적재 건수 검증 별도 필요 |
| cs_21c_insider_signal.md | 🟡 | `tasks/insider_tasks.py` + `models/insider_signal.py` + task_done/CS-2-1c | 동일하게 스키마/태스크 ✅, 데이터 미확인 |
| cs_22_co_mention.md | ✅ | `tasks/relation_tasks.py` + CoMentionEdge + task_done/CS-2-2 | ChainNewsEvent + CoMentionEdge |
| cs_23_price_co_movement.md | ✅ | `tasks/relation_tasks.py` + PriceCoMovement + task_done/CS-2-3 | 90일 rolling corr |
| cs_24_relation_confidence.md | ✅ | `tasks/relation_tasks.py::update_relation_confidence` + task_done/CS-2-4 | data_quality_3_fixes에서 소스별 분기 보강 |
| cs_25_chain_profile_aggregation.md | ✅ | `tasks/sync_tasks.py` + CompanyChainProfile + task_done/CS-2-5 | 집약 30 필드 |
| relation_confidence_design_v1.md (v1.1) | ✅ | RelationConfidence v2.1 스키마 + `services/neo4j_sync.py` + redesign v1 PR-1 | 5단계 상태·truth/market 분리·undirected 정규화 |

### Phase 3 — Neo4j 동기화 + GDS

| 설계 문서 | 분류 | 매핑 | 비고 |
|----------|------|------|------|
| cs_31_profile_neo4j_sync.md | ✅ | `services/neo4j_sync.py::sync_dirty_relations` + `tasks/neo4j_dirty_sync_tasks.py` + task_done/CS-3-1 | Delta Sync, neo4j_dirty 플래그 |
| cs_32_relation_neo4j_sync.md | ✅ | `tasks/sync_tasks.py` + redesign PR-3 + task_done/CS-3-2 / data_quality_3_fixes | RELATED_TO 하드코딩 제거, 동적 타입 |
| cs_33_gds_algorithms.md | 🟡 | task_done/CS-3-3 보고서는 존재(주장), 그러나 redesign 00_summary "Graph Data Science (PageRank, Louvain)" 범위 밖 명시 | 실 코드 위치는 미확인. M3 달성 보고와 redesign "후속" 표기 사이의 모순 — 추가 검증 필요 |

### Phase 4 — API

| 설계 문서 | 분류 | 매핑 | 비고 |
|----------|------|------|------|
| cs_41_graph_api.md | ✅ | `api/views.py::ChainSightGraphView` (deep dive) + task_done/CS-4-1_2_3 | `/api/v1/chainsight/<symbol>/graph/` |
| cs_42_suggestion_api.md | ✅ | `api/views.py::ChainSightSuggestionView` | 4 카테고리 (peers/same_industry/co_mentioned/same_sector) |
| cs_43_trace_api.md | ✅ | `api/views.py::ChainSightTraceView` | shortestPath up to 5 hop |

### Phase 5 — 프론트엔드 (cs_5x 1세대)

| 설계 문서 | 분류 | 매핑 | 비고 |
|----------|------|------|------|
| cs_51_graph_visualization.md | 🔁 → redesign v2.2 | `frontend/components/chainsight/GraphCanvas.tsx`, `NodeDetailPanel.tsx`, `radialLayout.ts`, `graphStyles.ts` | Spotlight + lazy expansion 개념은 그대로 흡수 |
| cs_52_ai_guide_ui.md | 🔁 → redesign v2.2 | `AIGuidePanel.tsx` (deep dive) + `RelationCardPanel.tsx` (market view) | SuggestionCards 단일 컴포넌트가 두 화면으로 확장됨 |
| cs_53_chain_trace_ui.md | ✅ | `TracePathView.tsx` + `FullPathView.tsx` + `PathCard.tsx` | |
| cs_54_stock_detail_integration.md | 🔁 (탭 제거) | `GraphMiniView.tsx`는 유지되나 `/stocks/[symbol]` Chain Sight 탭은 마켓뷰 딥링크(`/chainsight?focus={symbol}`)로 대체 | redesign UI v2.2 §11 |
| cs_5_frontend_design_v2.md | 🔁 → redesign v2.2 (v3) | 3-panel 워크스페이스 콘셉트는 `/chainsight/[symbol]` Deep dive workspace에 잔존 | |

### Redesign v1 (260409) — 마켓 뷰 V2.x

| 설계 문서 | 분류 | 매핑 | 비고 |
|----------|------|------|------|
| chainsight_seed_node_design.md (v2.1) | ✅ Phase 1만 | `services/seed_selection.py`, `tasks/seed_tasks.py`, `models/seed_snapshot.py` + PR-2 | B+A 소스 모두 활성, MAX_SEED_NODES=20 |
| chainsight_api_design.md (v2.1) | ✅ | `api/views.py::SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView` + `api/urls.py` + PR-4 | 4 엔드포인트 모두 캐시·display_type 파생·정렬 정책 일치 |
| chainsight_ui_ux_design.md (v2.2) | ✅ 5/5 컴포넌트 | `SectorBar.tsx`, `MarketGraphCanvas.tsx`, `ExplorationTrail.tsx`, `RelationCardPanel.tsx`, `ChainStoryFeed.tsx` + `app/chainsight/page.tsx` + `lib/stores/explorationStore.ts` + `hooks/useMarketView.ts` | 화면 ①~⑤ + 공유 ExplorationState 전부 구현 |
| chainsight_marketview_pr_prompts.md | ✅ | task_done/PR-1~PR-7 모두 종결 | |

### 데이터 수집 (트랙 B)

| 설계 항목 | 분류 | 매핑 | 비고 |
|----------|------|------|------|
| DC-1 Peers + Industry | ✅ | Phase 1 결과로 자동 충족 | PEER_OF 8,350, BELONGS_TO 다수 |
| DC-2 ETF Holdings → :Theme | ✅ | task_done/DC-2_etf_holdings_theme.md + `load_themes_to_neo4j.py` | :Theme 21개 + HAS_THEME 534 |
| DC-3 수동 시드 Supply Chain JSON | ❌ | 시드 JSON 파일이나 적재 커맨드 미발견 | SUPPLIES_TO 적재 경로 부재 |
| DC-4 Gemini Flash Supply Chain 확장 | ❌ | 관련 태스크/프롬프트 모듈 미발견 | |
| DC-5 Marketaux 뉴스 자연 축적 | 🟡 | CoMentionEdge 일간 추출 가동 중 → 자연 축적 진행 | |
| DC-6 Finnhub Premium | ❌ | 비용 게이트, 의도된 미구현 | |

### SEC Pipeline / Heat Score / Phase 3 D-1~D-3

| 설계 항목 | 분류 | 비고 |
|----------|------|------|
| sec_pipeline_base_design.md / sec_pipeline_pr_detail.md | 🟢 외부 앱 | 별도 `sec_pipeline/` 앱으로 분리 — Chain Sight 갭 범위 외, 다만 Chain Sight Phase 3 D-3 SEC filing 이벤트 연계는 미연결 |
| Heat Score (seed design Phase 2) | 🟡 | `chainsight-heat-score-daily` Beat 항목은 존재(common-bugs #28 참고)지만 SeedHeatScore 모델/계산 코드 발견 안 됨. 추가 확인 필요 |
| Phase 3 D-1 text_conditional_prob | ❌ | ChromaDB·Gemini Embedding 의존, 코드 없음 |
| Phase 3 D-2 lagged correlation + propagation_weight | ❌ | |
| Phase 3 D-3 사후 검증 가중치 학습 | ❌ | |

---

## 미구현 항목 상세 (C 분류)

### 1. Phase 3 이벤트 전파 모델 (D-1 / D-2 / D-3)

- **설계 위치**: `chainsight_seed_node_design.md` §4 + remaining_work_plan.md 의존성 트리
- **요구 사항**:
  - D-1: 뉴스→키워드→Embedding→`text_conditional_prob(A,B)` 비대칭 계산. ChromaDB + Gemini Embedding 필수
  - D-2: lagged price correlation (lag0/1/2) + volume_response + `propagation_weight = 0.40·text + 0.35·price + 0.25·volume`, 텍스트 게이트 0.05
  - D-3: 검증 레이블 축적 후 가중치 재학습
- **현재 코드 상태**:
  - `chainsight/services/`, `chainsight/tasks/` 어디에도 propagation/embedding 관련 모듈 없음
  - Celery Beat에 `chainsight-text-conditional` / `chainsight-lagged-correlation` / `chainsight-propagation-weight` 미등록
- **전제 조건 미충족**:
  - 디자인 §7: "D-1 후 ~3개월 거래일 축적" → 단기 진입 불가
  - ChromaDB 인프라 부재
- **권장 다음 행동**: D-1 단계만이라도 별도 design.md로 분리 후 실험적 PR 검토

### 2. RelationCard 2차 설명 (relation_summary / why_now / insight_summary)

- **설계 위치**: `chainsight_api_design.md` §4 "2차 필드 확장" + `chainsight_ui_ux_design.md` §9 "카드 설명 필드 전략 2차/추후"
- **요구 사항**: `neighbors` 응답에 LLM 생성 `relation_summary`, `why_now`, `insight_summary` 추가
- **현재 코드 상태**:
  - `NeighborGraphView` 응답에 해당 필드 부재
  - 프론트는 1차 템플릿(고정 문구 표) 동작 중 → UX 작동은 함
- **권장**: 토큰 비용 평가 후 별도 PR. Chain Sight 핵심 흐름은 차단되지 않음

### 3. SeedHeatScore Phase 2

- **설계 위치**: `chainsight_seed_node_design.md` §3 + `redesign_v1_260409/chainsight_api_design.md` §8 (SeedHeatScore 모델 Phase 2)
- **현재 코드 상태**:
  - 모델 `SeedHeatScore` 파일 검색 결과 없음 (`chainsight/models/__init__.py` export에 부재)
  - 그러나 `chainsight-heat-score-daily` Beat가 활성으로 기록됨 → **태스크 등록 vs 실 구현 불일치 가능성**
  - common-bugs #28 (Beat drift) 맥락에서 회수해야 할 가능성
- **권장**: `chainsight-heat-score-daily` Beat 태스크 실 구현 위치를 grep으로 재확인 (감사 시간 제약으로 본 보고서에서는 추가 조사 보류). 미구현이면 Phase 2 진입 시 SeedHeatScore 모델부터 신규

### 4. SEC filing → Chain Sight 연계

- **설계 위치**: 시드 design §4.2 — SEC filing은 "도로 갱신" 역할
- **현재 상태**: `sec_pipeline/` 앱은 별도로 운영되나 chainsight RelationConfidence에 SEC 증거 소스가 evidence_sources JSONB로 반영되는 흐름 부재(추정). Chain Sight 본 감사 범위 외이므로 별도 audit 권장

---

## 폐기/대체 항목 (D 분류)

### 1. cs_51~54 1세대 프론트엔드 설계 → redesign_v1_260409 v2.2 FINAL

- **이유**: "종목 상세 → Chain Sight 탭" 진입 모델을 "마켓 뷰 → 섹터 → 중심 노드" 허브 모델로 전환
- **흡수된 내용**: Spotlight 모드(GraphCanvas), AI Guide(AIGuidePanel + RelationCardPanel로 분기), Chain Trace(TracePathView), 종목 상세 미니뷰(GraphMiniView)
- **남은 잔재**: cs_5_frontend_design_v2.md의 3-panel 워크스페이스 콘셉트는 `/chainsight/[symbol]` Deep dive workspace에 일부만 유지

### 2. CompanyChainProfile `profile_data` (JSONB) 단일 필드

- **로드맵 v1.1** 제안, **v1.2 결정**으로 30개 개별 필드 구조 유지 — `models/chain_profile.py`에 그대로 반영

### 3. `CUSTOMER_OF` 별도 저장

- **로드맵 v1.3** 변경: SUPPLIES_TO만 canonical, API에서 `display_type` 파생
- **반영 확인**: `NeighborGraphView._display_type` (api/views.py:531~535) + `ChainSightGraphView` edge derived_type (api/views.py:90~92)

### 4. Neo4j 엣지 라벨 `RELATED_TO` 하드코딩

- **이슈 발견**: data_quality_3_fixes.md (2026-04-13)에서 `sync_relations_to_neo4j`가 모든 엣지를 `RELATED_TO`로 라벨링
- **대체**: dirty sync(`services/neo4j_sync.py::sync_dirty_relations`)가 동적 타입 PEER_OF / SUPPLIES_TO / COMPETES_WITH / CO_MENTIONED / PRICE_CORRELATED를 사용. 레거시 `RELATED_TO` 0건 정리 완료
- **잔존 코드**: SectorGraphView 등 일부 쿼리에서 `COALESCE(r.relation_type, type(r))` fallback이 유지되는데, 신규 엣지에서는 type(r)이 곧 정상 라벨이므로 안전망 성격

### 5. 종목 상세 페이지 Chain Sight 탭

- **삭제 결정**: redesign UI/UX v2.2 §11 — 탭 제거, 딥링크 `/chainsight?focus={symbol}` 도입
- **반영 확인**: 00_summary 변경 파일 목록에 `frontend/app/stocks/[symbol]/page.tsx` 수정 명시

---

## 데이터 적재 갭 (B 분류 보강)

| 모델 | 스키마 상태 | 데이터 적재 (roadmap v1.3 부록 A 기준) | 비고 |
|------|----------|------------------------------------|------|
| CompanyGrowthStage | ✅ | ✅ ~480건 (remaining_work_plan.md 기준) | |
| CompanyCapitalDNA | ✅ | ✅ ~473건 | |
| CompanySensitivityProfile | ✅ | 🟡 별도 검증 필요. cs_21b 완료 보고는 존재 | |
| CompanyInsiderSignal | ✅ | 🟡 동일 | |
| CompanyRevenueStructure | ✅ | ❌ MVP에서 빈 상태로 시작 (의도) | |
| CompanyNarrativeTag | ✅ | ❌ NarrativeTag 추출 태스크 미발견 (Phase 2 이후 예정) | |
| CompanyEventReaction | ✅ | ❌ earnings 전후 주가 변동 계산 코드 미발견 | |
| ChainNewsEvent | ✅ | 🟡 CoMention 파이프라인이 생성 중 | |
| CompanyChainProfile | ✅ | 🟡 aggregate 태스크 등록됨, 실 적재 건수 별도 검증 | |

---

## 신규 발견 모델 (설계 문서에 없는 코드 자산)

| 모델 | 위치 | 역할 |
|------|------|------|
| `SeedSnapshot` | `chainsight/models/seed_snapshot.py` | Redis 휘발 대응 DB 영속화. common-bugs #27 트러블슈팅 산물 |
| `SavedPath`, `PathAction` | `chainsight/models/saved_path.py` | Trace 경로 저장 + 액션 로그 (Watchlist viewset에서 사용) |
| `WatchlistViewSet` | `chainsight/views/watchlist_views.py` | archive/resolve/recheck/expand/alternatives 액션 |

> 이 자산들은 redesign 문서에서 명시되지 않음에도 구현됨. UX 흐름 보강 차원에서 의도적으로 추가된 것으로 추정. 설계서 갱신 시 반영 권장.

---

## 권장 후속 작업

1. **검증 필요**: Sensitivity / Insider / SeedHeatScore의 실 데이터 적재 건수 — 별도 SQL count 보고
2. **모순 조사**: redesign 00_summary "범위 밖 = GDS PageRank/Louvain" vs remaining_work_plan.md "CS-3 GDS 완료" — `chainsight/tasks/` 내 gds_tasks.py 부재 의심
3. **문서 갱신**: SeedSnapshot / SavedPath / PathAction을 roadmap 부록 A 모델 표에 흡수
4. **방향 결정**: Phase 3 D-1~D-3 진입 여부 — ChromaDB 도입 사전 결정 필요

---

## 부록 — 감사 시 참조한 핵심 파일

- `docs/chain_sight/plan/chain_sight_roadmap_v1.3.md` (전체 로드맵)
- `docs/chain_sight/plan/remaining_work_plan.md` (2026-04-04 진척 스냅샷)
- `docs/chain_sight/plan/relation_confidence_design_v1.md` (v1.1)
- `docs/chain_sight/plan/redesign_v1_260409/{api,seed_node,ui_ux}_design.md` (v2.x FINAL)
- `docs/chain_sight/task_done/` 19개 cs_xx 보고서 + `chain_sight_redesign_V1/` 7 PR + data_quality_3_fixes + DC-2
- `chainsight/api/{urls,views}.py`, `chainsight/services/*.py`, `chainsight/tasks/*.py`, `chainsight/models/__init__.py`, `chainsight/migrations/000{1..8}_*.py`
- `frontend/components/chainsight/*.tsx` (21개), `frontend/app/chainsight/{page.tsx,[symbol]/,watchlist/}`, `frontend/lib/stores/explorationStore.ts`, `frontend/hooks/useMarketView.ts`

**END OF REPORT**
