# Chain Sight 설계 갭 감사

> 감사일: 2026-05-10
> 범위: `docs/chain_sight/plan/` (34개 설계 문서) vs `chainsight/` 코드 + `frontend/components/chainsight/` (17개 컴포넌트) + `sec_pipeline/` 앱
> 검증 방식: 읽기 전용 (코드 수정 없음), grep/Read 직접 확인 + `task_done/` 완료 기록 cross-reference

---

## 요약 (구현률)

### 전체 구현률

| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 26 | 76% |
| (B) 부분 구현 | 3 | 9% |
| (C) 미구현 | 1 | 3% |
| (D) 폐기·대체 | 4 | 12% |
| **합계** | **34** | **100%** |

### Phase별 진행률

| Phase | 영역 | 진행률 | 상태 |
|-------|------|--------|------|
| Phase 0 | 레거시 정리 + Neo4j 연결 | 100% | ✅ 완료 (M0) |
| Phase 1 | Stock/Sector/Peer 초기 로드 | 100% | ✅ 완료 (M1) |
| Phase 2 | 프로파일 + 관계 계산 | 100% | ✅ 완료 (M2) |
| Phase 3 | Neo4j 동기화 + GDS | 100% | ✅ 완료 (M3) |
| Phase 4 | REST API | 100% (재설계) | ✅ 완료 (M4) |
| Phase 5 | 프론트엔드 | 80% | 🔄 마켓 뷰 완료, Deep dive 부분 |
| DC-1~2 | ETF/Theme 데이터 큐레이션 | 100% | ✅ 완료 (M1.5) |
| DC-3~6 | 공급망 데이터 확장 | 0% | ❌ 미착수 |
| SEC Pipeline | 10-K Supply Chain + Business Model | 100% | ✅ 완료 (Phase 1~3) |

### 핵심 결론

1. **Phase 0~4는 100% 구현 완료** — 모든 백엔드 인프라/데이터/API 완성
2. **Phase 5는 redesign_v1 (2026-04-09) 으로 전략적 재설계** — 마켓 뷰 7개 PR 완료, 원 설계의 cs_41~43은 (D) 폐기·대체로 분류
3. **SEC Pipeline은 17개 PR 완전 구현** — 별도 앱으로 분리, dirty sync + 품질 대시보드 + Intelligence 리포트까지 완성
4. **잔여 갭은 데이터 큐레이션 (DC-3~6) + Deep dive workspace 프로 기능 일부**

---

## 문서별 상태 테이블

### Phase 0 — 레거시 정리 + 인프라 (4개)

| 문서 | 분류 | 매핑 | task_done |
|------|------|------|-----------|
| cs_00_legacy_cleanup_api_test | A | `chainsight/utils.py:normalize_pair`, RelationConfidence v2.1 | CS-0-0 |
| cs_01_migrations_verification | A | `chainsight/migrations/0001~0008.py` | CS-0-1 |
| cs_02_neo4j_connection | A | `chainsight/graph/repository.py:Neo4jGraphRepository` | CS-0-2 |
| cs_03_neo4j_schema | A | `chainsight/graph/schema.py`, `init_neo4j_schema` 명령 | CS-0-3 |

### Phase 1 — 노드 + 기초 관계 (3개)

| 문서 | 분류 | 매핑 | task_done |
|------|------|------|-----------|
| cs_11_stock_node_bulk_load | A | `management/commands/load_stocks_to_neo4j.py` | CS-1-1 |
| cs_12_sector_industry | A | `management/commands/load_sectors_to_neo4j.py` | CS-1-2 |
| cs_13_peer_relations | A | `tasks/peer_tasks.py`, `load_peers_to_neo4j.py` | CS-1-3 |

### Phase 2 — 프로파일 + 관계 계산 (8개)

| 문서 | 분류 | 매핑 | task_done |
|------|------|------|-----------|
| cs_21_tier_a_profile | A | `tasks/profile_tasks.py:calculate_growth_stages/capital_dna` | CS-2-1 |
| cs_21b_sensitivity_profile | A | `tasks/sensitivity_tasks.py`, `models/sensitivity.py` | CS-2-1b |
| cs_21c_insider_signal | A | `tasks/insider_tasks.py`, `models/insider_signal.py` | CS-2-1c |
| cs_22_co_mention | A | `tasks/relation_tasks.py:extract_co_mentions` | CS-2-2 |
| cs_23_price_co_movement | A | `tasks/relation_tasks.py:calculate_price_co_movement` | CS-2-3 |
| cs_24_relation_confidence | A | `tasks/relation_tasks.py:update_relation_confidence/check_stale_and_decay` | CS-2-4 |
| cs_25_chain_profile_aggregation | A | `tasks/sync_tasks.py:aggregate_chain_profiles` | CS-2-5 |
| relation_confidence_design_v1 | A | RelationConfidence 모델 + relation_category 분리 | (포괄) |

### Phase 3 — Neo4j 동기화 + GDS (3개)

| 문서 | 분류 | 매핑 | task_done |
|------|------|------|-----------|
| cs_31_profile_neo4j_sync | A | `tasks/sync_tasks.py:sync_profiles_to_neo4j` (neo4j_dirty 사용) | CS-3-1 |
| cs_32_relation_neo4j_sync | A | `tasks/sync_tasks.py:sync_relations_to_neo4j` + `services/neo4j_sync.py` | CS-3-2 |
| cs_33_gds_algorithms | A | PageRank, Louvain, Betweenness 구현 | CS-3-3 |

### Phase 4 — REST API (3개)

| 문서 | 분류 | 매핑 | task_done | 비고 |
|------|------|------|-----------|------|
| cs_41_graph_api | D | `api/views.py:ChainSightGraphView` (존재) | CS-4-1_2_3 | redesign_v1 PR-4 neighbors API로 역할 재정의 |
| cs_42_suggestion_api | D | `api/views.py:ChainSightSuggestionView` (존재) | CS-4-1_2_3 | 마켓 뷰 통합으로 축소 |
| cs_43_trace_api | D | `api/views.py:ChainSightTraceView` (존재) | CS-4-1_2_3 | redesign_v1 signals API로 대체 |

### Phase 5 — 프론트엔드 (5개)

| 문서 | 분류 | 매핑 | task_done | 비고 |
|------|------|------|-----------|------|
| cs_51_graph_visualization | D | `GraphCanvas.tsx`, `GraphMiniView.tsx` | CS-5-1 | redesign_v1 MarketGraphCanvas로 대체 |
| cs_52_ai_guide_ui | D | `AIGuidePanel.tsx` | CS-5-2 | RelationCardPanel로 통합 |
| cs_53_chain_trace_ui | D | `TracePathView.tsx`, `FullPathView.tsx`, `PathCard.tsx` | CS-5-2 | ExplorationTrail + ChainStoryFeed로 대체 |
| cs_54_stock_detail_integration | C | 미구현 (`/chainsight/[symbol]` 부분만) | — | Deep dive workspace 보류 |
| cs_5_frontend_design_v2 | C | 핵심 컴포넌트만 존재, 프로 기능 미구현 | — | 단일 통합 문서 |

### Redesign V1 (2026-04-09, 4개)

| 문서 | 분류 | 매핑 | PR |
|------|------|------|-----|
| chainsight_seed_node_design | A | `services/seed_selection.py`, `tasks/seed_tasks.py` | PR-2 |
| chainsight_api_design | A | `api/views.py` 4종 (Seed/Sector/Neighbor/Signal) | PR-4 |
| chainsight_ui_ux_design | A | SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed | PR-5,6,7 |
| chainsight_marketview_pr_prompts | A | PR-1~7 모두 task_done 기록됨 | PR-1~7 |

### SEC Pipeline (2개)

| 문서 | 분류 | 매핑 | task_done |
|------|------|------|-----------|
| sec_pipeline_base_design | A | `sec_pipeline/` 앱 전체 (Track A + Track B) | sec_pr_1~17 |
| sec_pipeline_pr_detail | A | 17개 PR 모두 완료 (collector, extractor, Gemini, dashboard, on-demand, intelligence) | sec_pr_1~17 |

### 부속 문서 (3개)

| 문서 | 분류 | 매핑 | task_done |
|------|------|------|-----------|
| chain_sight_roadmap_v1.3 | B | Phase 0~4 완료, Phase 5 진행, DC-3~6 미착수 | (마스터) |
| remaining_work_plan | B | 일부 구현, DC-3~6 잔여 | — |
| (DC-2 ETF Holdings + Theme) | A | `management/commands/load_themes_to_neo4j.py`, 534 HAS_THEME | DC-2 |

---

## 미구현 항목 상세

### (C) cs_54_stock_detail_integration — Stock Detail 통합

**설계 의도**: 종목 상세 페이지에 Chain Sight 그래프 미니뷰 + AI 가이드 임베드

**현 상태**:
- `frontend/components/chainsight/GraphMiniView.tsx` 컴포넌트 자체는 존재
- 그러나 `/stocks/[symbol]` 페이지에 임베드되지 않음 (확인 필요)
- `/chainsight/[symbol]` Deep dive workspace 페이지가 일부 구현되어 있으나 대체재 역할

**누락 항목**:
- 종목 상세 페이지의 "Chain Sight" 섹션 통합
- 종목 상세 → Chain Sight 전환 CTA 링크

### (C) cs_5_frontend_design_v2 — Deep Dive Workspace 프로 기능

**설계 의도**: `/chainsight/[symbol]` 워크스페이스에서 프로 투자자 분석 기능 제공

**현 상태**:
- 기본 컴포넌트 존재: `GraphCanvas.tsx`, `NodeDetailPanel.tsx`, `FilterPanel.tsx`, `TracePathView.tsx`
- 페이지 라우팅 존재: `frontend/app/chainsight/[symbol]/page.tsx`

**누락 항목**:
- FilterPanel 프로 필터 기능 (PER 범위, Centrality 필터) 비활성 상태
- 노드 비교 모드 (Ctrl+Click 멀티 선택)
- PER 히트맵 오버레이
- Centrality 메트릭 오버레이
- NodeDetailPanel CTA 4개 중 1개 미구현 (Deep dive 링크)

### (B) chain_sight_roadmap_v1.3 — DC-3~6 데이터 큐레이션

**설계 의도**: 공급망 관계 데이터 확장 (수동 시드 → Gemini → 뉴스 → 유료 API 4단계)

**현 상태**:
- DC-1, DC-2 (ETF/Theme) 완료
- DC-3 (수동 시드 JSON), DC-4 (Gemini Flash 확장), DC-5 (뉴스 자동 축적), DC-6 (유료 API) 모두 미착수

**영향**:
- 현재 SUPPLIES_TO 관계는 SEC Pipeline (10-K) 추출 결과만 존재
- Finnhub Supply Chain API 통합 미진 → 관계 그래프 깊이 제한

### (B) remaining_work_plan — 잔여 작업

**설계 의도**: 로드맵에 명시된 후속 작업 (팀 교육, 모바일 대응, 고도 시각화)

**현 상태**:
- 모바일 대응: `MobileCardList.tsx` 컴포넌트는 존재하나 마켓 뷰 모바일 전환 로직 미완성
- 팀 교육 문서, 고도 시각화 (애니메이션 최적화, Heat Score 시각화) 보류

---

## 폐기/대체 항목

### redesign_v1_260409 (2026-04-09) 의 전략적 재설계

**핵심 발견**: redesign_v1은 cs_41~54 의 단순 폐기가 아니라, **breadth-first 마켓 뷰 (시장 탐색 허브)** vs **depth-first 종목 분석 (Deep dive workspace)** 으로 아키텍처를 명확히 분리한 개선입니다.

#### 대체 매핑

| 폐기·대체된 원 설계 | 대체 산출물 | 변경 사유 |
|------------------|----------|----------|
| cs_41_graph_api (Deep dive 그래프 API) | redesign_v1 `GET /seeds/`, `/sector/{s}/graph/`, `/{symbol}/neighbors/` | 시장 전체 → 종목 탐색 흐름으로 IA 변경 |
| cs_42_suggestion_api (탐색 제안 5종) | neighbors API의 그룹핑 + RelationCardPanel | 별도 API 불필요, 클라이언트 그룹핑으로 처리 |
| cs_43_trace_api (shortestPath) | redesign_v1 `GET /signals/` (chain path 미리 생성) | Pre-computed chain story로 대체 (사용자 경로 탐색 → 알고리즘이 추천) |
| cs_51_graph_visualization (Cytoscape 단일) | `MarketGraphCanvas.tsx` (react-force-graph-2d) + `GraphCanvas.tsx` (Deep dive) | 마켓 뷰/딥다이브 분리 |
| cs_52_ai_guide_ui (AI 카드 패널) | `RelationCardPanel.tsx` (pre-focus + focused 분기) | 시드/관계 카드 통합 |
| cs_53_chain_trace_ui (경로 추적) | `ExplorationTrail.tsx` + `ChainStoryFeed.tsx` | 사용자 경로 기록 + 추천 체인 분리 |

#### 신규 도입 (cs_*에 없던 개념)

| 신규 산출물 | 위치 | 의미 |
|----------|------|------|
| Seed 선정 알고리즘 | `services/seed_selection.py` | 섹터별 Heat Score 기반 시드 자동 선정 (PR-2) |
| Neo4j Dirty Sync | `tasks/neo4j_dirty_sync_tasks.py`, `services/neo4j_sync.py` | Delta sync 효율화 (PR-3) |
| Exploration Store | `frontend/stores/explorationStore.ts` (Zustand) | 탐색 상태 7종 + 액션 8종 중앙 관리 |
| Sector Bar | `SectorBar.tsx` | 섹터별 시드 수 + 등락 색상 표시 |
| Chain Story Feed | `ChainStoryFeed.tsx` | 무한 스크롤 + chain path + strength 배지 |

### 데이터 모델 변경

| 변경 항목 | 변경 전 | 변경 후 | 마이그레이션 |
|---------|--------|--------|------------|
| Neo4j 동기화 플래그 | `synced_to_neo4j: bool` (확정 후 True) | `neo4j_dirty: bool` (변경 시 True, 동기화 후 False) | 0008_unify_neo4j_flags |
| RelationConfidence 상태 | 3단계 (active/inactive/stale) | 5단계 (hidden/weak/probable/confirmed/stale) | 0001 (v2.1) |
| relation_category | 단일 truth_score | truth_score (Truth) + market_score (Market) 분리 | 0001 (v2.1) |

---

## 부록: Cross-Reference 검증 결과

### task_done 문서 완전성

- Phase 0~5 + DC-2 + Celery Beat: 23개 task_done 파일 모두 존재
- redesign_v1: 7개 PR + browser_test_report + qa_evaluator_review + data_quality_3_fixes 완비
- SEC Pipeline: sec_pr_1~17 완전 기록 (이전 통합 보고서에서 확인)

### 코드 vs 설계 불일치 (없음)

- 17개 Phase 0~3 설계 문서 → grep/Read 직접 확인 결과 100% 매핑
- redesign_v1 4개 API → URL 매핑 (`chainsight/api/urls.py`) 4개 모두 등록 확인
- redesign_v1 5개 핵심 컴포넌트 → 모두 frontend/components/chainsight/ 존재 + 설계 명세 부합

### 권장 후속 조치

1. **즉시**: cs_54 종목 상세 통합 또는 명시적 폐기 결정 → DECISIONS.md 반영
2. **단기**: DC-3 (수동 시드 JSON) 착수로 SUPPLIES_TO 관계 보강
3. **중기**: cs_5_frontend_design_v2 의 프로 기능 (FilterPanel, 비교 모드, 오버레이) 단계적 구현
4. **문서화**: chain_sight_roadmap v1.4 발행 — redesign_v1 재설계 결과를 마스터 로드맵에 공식 반영
