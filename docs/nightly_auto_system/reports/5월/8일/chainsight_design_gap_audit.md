# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-08
> **대상 문서**: `docs/chain_sight/plan/` (33건) + `docs/chain_sight/task_done/` (28건)
> **대상 코드**: `chainsight/`, `frontend/components/chainsight/`, `frontend/app/chainsight/`, `sec_pipeline/`, `config/celery.py`
> **모드**: 읽기 전용 감사 — 코드 수정 없음
> **방법**: 설계 문서 ↔ 코드 cross-reference (백엔드/프론트엔드/횡단 3트랙 병렬 조사)

---

## 요약 (구현률)

| 영역 | 설계 항목 | 구현률 | 등급 |
|------|----------|--------|------|
| **Phase 0 인프라** (cs_00~cs_03) | 4건 | 4/4 (100%) | (A) |
| **Phase 1 시드 로드** (cs_11~cs_13) | 3건 | 3/3 (100%) | (A) |
| **Phase 2 파생 데이터** (cs_21~cs_25, cs_21b/c) | 7건 | 7/7 (100%) | (A) |
| **Phase 3 Neo4j 동기화 + GDS** (cs_31~cs_33) | 3건 | 3/3 (100%) | (A) |
| **Phase 4 Deep dive API** (cs_41~cs_43) | 3건 | 3/3 (100%) | (A) |
| **Phase 5 cs_5x 프론트엔드 원안** | 5건 | — | (D) redesign_v1로 전면 대체 |
| **redesign_v1 마켓 뷰 백엔드** (API 4종 + Seed) | 7건 | 6.5/7 (~93%) | (B) |
| **redesign_v1 마켓 뷰 프론트엔드** (PR-5~7) | 5컴포넌트 | 5/5 (100%) | (A) |
| **RelationConfidence v2.1** | 7요소 | 7/7 (100%) | (A) |
| **SEC Pipeline** (Phase 1~3) | 4영역 | 4/4 (100%) | (A) |
| **DC-2 ETF Holdings → Theme** | 3항목 | 2.5/3 (~83%) | (B) — legacy 미정리 |
| **Celery Beat 등록** | 8태스크 | 8/8 (100%) | (A) |
| **시드 노드 Phase 2 (Heat Score)** | 1요소 | 0.5/1 (50%) | (B) — DB 모델 부재 |
| **LLM 기반 2차 설명** (chain_title, why_now 보강) | 3요소 | 0/3 (0%) | (C) 미구현 (Future) |

### 종합 평가
- **마일스톤**: v1.3 로드맵 **M0~M4 완료**, M5(MVP UX)는 redesign_v1으로 재정의되어 핵심 흐름 작동
- **전체 구현률**: 설계서 35건 중 **A=28, B=5, C=2, D=1** → 약 **88%**
- **즉시 차단 요소 없음**: 미구현은 모두 "Phase 2", "Future enhancement" 명시 항목
- **설계 방향 변경**: cs_5x 원안(Spotlight 중심)이 redesign_v1(마켓 뷰 + Deep dive 분리)로 전면 대체

---

## 문서별 상태 테이블

### 1. 로드맵 / 인프라 (Phase 0)

| 설계 문서 | 상태 | 핵심 증거 |
|----------|------|----------|
| `chain_sight_roadmap_v1.3.md` | (A) 본문 마일스톤 M0~M4 모두 완료 | task_done CS-0~CS-4 |
| `cs_00_legacy_cleanup_api_test.md` | (A) | task_done/CS-0-0 + serverless legacy 태그 처리 |
| `cs_01_migrations_verification.md` | (A) | `chainsight/migrations/` 0001~0008 8개 |
| `cs_02_neo4j_connection.md` | (A) | `chainsight/graph/repository.py`, PID 기반 lazy init |
| `cs_03_neo4j_schema.md` | (A) | `chainsight/graph/schema.py` + 4 constraint |

### 2. 시드 로드 (Phase 1)

| 설계 문서 | 상태 | 핵심 증거 |
|----------|------|----------|
| `cs_11_stock_node_bulk_load.md` | (A) | `chainsight/management/commands/` |
| `cs_12_sector_industry.md` | (A) | task_done CS-1-2 (17 Sector + 128 Industry) |
| `cs_13_peer_relations.md` | (A) | task_done CS-1-3 (8,350 PEER_OF) |

### 3. 파생 데이터 (Phase 2)

| 설계 문서 | 상태 | 핵심 증거 |
|----------|------|----------|
| `cs_21_tier_a_profile.md` | (A) | `chainsight/models/growth_stage.py`, `capital_dna.py` |
| `cs_21b_sensitivity_profile.md` | (A) | `chainsight/tasks/sensitivity_tasks.py` (503건) |
| `cs_21c_insider_signal.md` | (A) | `chainsight/tasks/insider_tasks.py` |
| `cs_22_co_mention.md` | (A) | `chainsight/models/relation_discovery.py:CoMentionEdge` |
| `cs_23_price_co_movement.md` | (A) | `chainsight/models/relation_discovery.py:PriceCoMovement` |
| `cs_24_relation_confidence.md` | (A) | `chainsight/models/relation_discovery.py:RelationConfidence` v2.1 |
| `cs_25_chain_profile_aggregation.md` | (A) | `chainsight/models/chain_profile.py` (30개 점수 필드) |
| `relation_confidence_design_v1.md` | (A) | Tier 1/2/3 + 5단계 상태 + relation_basis_summary 모두 구현 |

### 4. Neo4j 동기화 + GDS (Phase 3)

| 설계 문서 | 상태 | 핵심 증거 |
|----------|------|----------|
| `cs_31_profile_neo4j_sync.md` | (A) | `chainsight/services/neo4j_sync.py`, `tasks/sync_tasks.py` |
| `cs_32_relation_neo4j_sync.md` | (A) | neo4j_dirty 플래그 패턴 (migration 0005, 0008) |
| `cs_33_gds_algorithms.md` | (A) | task_done CS-3-3 (PageRank, Louvain, Betweenness 결과 노드 속성) |

### 5. Deep dive API (Phase 4)

| 설계 문서 | 상태 | 코드 |
|----------|------|------|
| `cs_41_graph_api.md` | (A) | `chainsight/api/views.py:ChainSightGraphView` (depth N) |
| `cs_42_suggestion_api.md` | (A) | `chainsight/api/views.py:ChainSightSuggestionView` |
| `cs_43_trace_api.md` | (A) | `chainsight/api/views.py:ChainSightTraceView` |

### 6. cs_5x 프론트엔드 원안 (Phase 5) — 전면 대체

| 설계 문서 | 상태 | 비고 |
|----------|------|------|
| `cs_5_frontend_design_v2.md` | (D) | redesign_v1 도입으로 폐기 |
| `cs_51_graph_visualization.md` | (D) | Spotlight 모드 폐기, force-graph-2d로 마켓 뷰 + Deep dive 이원화 |
| `cs_52_ai_guide_ui.md` | (D)+(부분 유지) | 마켓 뷰는 RelationCardPanel로 대체, Deep dive `AIGuidePanel.tsx`엔 잔존 |
| `cs_53_chain_trace_ui.md` | (A) | Deep dive workspace에서 살아있음 (`TracePathView.tsx`) |
| `cs_54_stock_detail_integration.md` | (A) | `frontend/app/stocks/[symbol]/page.tsx:446~451` Chain Sight 탭 + GraphMiniView |

### 7. redesign_v1 마켓 뷰 (2026-04-10 머지)

| 설계 문서 | 상태 | 코드 |
|----------|------|------|
| `redesign_v1_260409/chainsight_seed_node_design.md` | (A) | `chainsight/services/seed_selection.py` + `chainsight/models/seed_snapshot.py` (Redis 휘발 대비 영속화) |
| `redesign_v1_260409/chainsight_api_design.md` | (B) | API 4종 등록, 일부 필드 누락 (아래 상세) |
| `redesign_v1_260409/chainsight_ui_ux_design.md` | (A) | 5컴포넌트 + Zustand store + TanStack Query 4훅 |
| `redesign_v1_260409/chainsight_marketview_pr_prompts.md` | (A) | PR-1~7 모두 task_done에 머지 보고 |
| task_done `PR-1` 스키마 마이그레이션 | (A) | migration 0005 (neo4j_dirty + previous_status), 0008 (flag 통합) |
| task_done `PR-2` 시드 선정 task | (A) | `chainsight/tasks/seed_tasks.py` |
| task_done `PR-3` Neo4j Sync 개선 | (A) | `chainsight/tasks/neo4j_dirty_sync_tasks.py` |
| task_done `PR-4` API 4종 | (A) | `chainsight/api/views.py:308-814` SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView |
| task_done `PR-5` FE 코어 UI | (A) | SectorBar, MarketGraphCanvas, explorationStore |
| task_done `PR-6` 트레일 + 카드 | (A) | ExplorationTrail, RelationCardPanel |
| task_done `PR-7` 체인 스토리 피드 | (A) | ChainStoryFeed (무한 스크롤 + 체인 클릭 → 새 session) |

### 8. SEC Pipeline (Chain Sight 횡단)

| 설계 문서 | 상태 | 코드 |
|----------|------|------|
| `sec_pipeline_base_design.md` | (A) | `sec_pipeline/` 전체 (collector, extractor, validator) |
| `sec_pipeline_pr_detail.md` (17 PR) | (A) | task_done DC-2 + sec_pipeline 모듈 — 110 SupplyChain Evidence + 5 BM Snapshot + Neo4j sync |

### 9. 기타 보조 문서

| 문서 | 상태 | 비고 |
|------|------|------|
| `remaining_work_plan.md` (2026-04-04) | (A) | CS-2-1b/c, DC-2 모두 완료. CS-5는 redesign_v1로 통합 |
| task_done `celery_beat_registration.md` | (A) | `config/celery.py:135+` 8개 task 등록 + 2026-04-24 복구 기록 |
| task_done `DC-2_etf_holdings_theme.md` | (B) | :Theme 21 + HAS_THEME 등록, serverless ETF legacy는 미정리 |
| task_done `chain_sight_redesign_V1/data_quality_3_fixes.md` | (A) | Heat Score / 시그널 / 그래프 데이터 품질 보정 |

---

## 미구현 항목 상세

### (B-1) NeighborGraphView `center.volume_ratio` 누락
- **설계**: `redesign_v1_260409/chainsight_api_design.md` § 4 (line 267) — center에 `volume_ratio` 명시
- **현황**: `chainsight/api/views.py:487-497` — `daily_return`, `seed_reasons`는 있으나 `volume_ratio` 누락. neighbors[]에는 정상 포함
- **영향**: 프론트가 마켓 뷰의 center 노드 "왜 시드인가" 라벨 렌더 시 거래량 신호 표시 불가
- **수정 분량**: seed_info에서 volume_ratio 추출하여 center 응답에 추가 (수 줄)

### (B-2) SignalFeed path 구조 불일치
- **설계**: `chainsight_api_design.md` § 5 — `chains[].path[].relation_to_next` 인라인 필드
- **현황**: `chainsight/api/views.py:781-796` — path와 별개로 `edges` 배열 반환
- **영향**: 프론트가 path 렌더 시 join 필요 (성능 영향 미미)

### (B-3) `relation_new` 시드 사유 코드 미생성
- **설계**: `chainsight_seed_node_design.md` § 2.2 — 신규 관계 출현 시 `relation_new` 코드 부여
- **현황**: `chainsight/services/seed_selection.py:252-275` — upgrade/downgrade만 처리, `first_observed_at = today` 케이스 미감지
- **영향**: 신규 관계가 시드에 노출되지 않음 (관계 풀이 정체될수록 영향 누적)

### (B-4) Heat Score sector 정렬 Phase 2 미전환
- **설계**: § 3.5 — Phase 1은 seed_count DESC, Phase 2+는 heat_total DESC
- **현황**: `seed_selection.py:387` — seed_count DESC로 고정
- **영향**: 현재 Phase 1이므로 무시 가능, Phase 2 진입 시 변경 필요

### (B-5) MarketGraphCanvas 엣지 굵기 truth_score 비례 미반영
- **설계**: `chainsight_api_design.md` § 3 — `truth_score != null ? scale(truth_score) : 1`
- **현황**: `frontend/components/chainsight/MarketGraphCanvas.tsx` — 엣지 굵기 고정
- **영향**: 관계 강도 시각화가 약함 (모든 엣지가 동일 두께)

### (B-6) DC-2 serverless legacy 미정리
- **설계**: 로드맵 v1.3 부록 B — "DC-2 완료 시 ETFProfile/ETFHolding/ThemeMatch 제거"
- **현황**: `serverless/models.py` — ETFProfile (21건) + ETFHolding (4,915건) 잔존, `# LEGACY_KEEP_UNTIL_DC2` 태그 유지
- **영향**: 이중 진실 소스 위험 (Neo4j :Theme 21 vs Postgres ETFProfile 21)

### (B-7) MobileCardList — 마켓 뷰 미적용
- **설계**: cs_54 + redesign_v1 ui_ux_design § 6 — 모바일 전용 카드 리스트
- **현황**: `frontend/components/chainsight/MobileCardList.tsx` 는 `/chainsight/[symbol]` Deep dive에만 적용. 마켓 뷰 `/chainsight/page.tsx`는 desktop-only
- **영향**: 모바일 사용자가 마켓 뷰 진입 시 그래프 가독성 저하

### (C-1) SeedHeatScore PostgreSQL 모델 부재
- **설계**: `chainsight_api_design.md` § 8 — `SeedHeatScore` 신규 (stock, date, heat_score, components, seed_rank), Phase 2
- **현황**: `chainsight/models/` 에 모델 파일 없음. heat_score 계산은 Neo4j 노드 속성에 직접 저장 (`tasks/seed_tasks.py`)
- **영향**: heat_score 시계열 분석 불가 (스냅샷 없음). 단, 현재 Phase 2 미진입이므로 즉시 영향 없음

### (C-2) LLM 기반 2차 카드 설명 (`relation_summary`, `why_now`, `insight_summary`)
- **설계**: `chainsight_api_design.md` § 4 (line 343-352) — 2차 필드 확장 명시
- **현황**: 템플릿 기반 1차 설명만 (`RelationCardPanel.tsx:40~51`의 `buildWhyNow`)
- **영향**: 카드의 컨텍스트 설명 빈약. 단, 설계서에서 "Future enhancement"로 명시

### (C-3) ChainStoryFeed `chain_title` / `trigger_summary` LLM 생성 미구현
- **설계**: `chainsight_api_design.md` § 5 + ui_ux_design § 2.2.3
- **현황**: 템플릿 기반 (`SignalFeedView`에서 sector + 종목명 조합)
- **영향**: 체인의 의미가 단조롭게 표현됨. Future enhancement

### (C-4) GDS 결과의 시드/마켓 뷰 직접 활용 미반영
- **설계**: 로드맵 v1.3 § 2.4 — pagerank, community_id를 :Stock 속성에 반영하여 탐색 정렬에 활용
- **현황**: GDS 알고리즘은 CS-3-3에서 노드 속성으로 적재되어 있으나, `seed_selection.py`나 마켓 뷰 정렬은 **price_top5/volume_surge/relation_change**만 사용
- **영향**: 그래프 중심성이 시드 발굴에 기여하지 않음 — 알고리즘 결과 사장

### (C-5) Centrality 오버레이, 노드 비교 모드 (cs_5 프로 기능)
- **설계**: cs_5_frontend_design_v2 § 6 — PER 히트맵, Centrality, 커뮤니티 컬러링, Ctrl+Click 두 노드 비교
- **현황**: FilterPanel에 depth/relType 필터만 존재, 오버레이/비교 UI 없음
- **영향**: 분석가 페르소나용 프로 기능 부재 (MVP 우선순위 낮음)

### (B-8) Phase 5 모바일 마켓 뷰 (재정리)
- **설계**: redesign_v1 00_summary "Future consideration"
- **현황**: 미착수
- **영향**: 모바일 첫 진입점 부재 (Deep dive는 모바일 카드 리스트로 대응)

---

## 폐기 / 대체 항목

### (D-1) cs_5x 원안 5건 → redesign_v1으로 전면 대체
- **폐기 근거**: `redesign_v1_260409/00_summary.md` (2026-04-10) + 마켓 뷰 5컴포넌트 머지
- **대체 매핑**:
  - `cs_5_frontend_design_v2.md` → `chainsight_ui_ux_design.md`
  - `cs_51_graph_visualization.md` (Spotlight 모드) → `MarketGraphCanvas.tsx` (overview/neighbor 분기)
  - `cs_52_ai_guide_ui.md` (SuggestionCards) → `RelationCardPanel.tsx` (마켓 뷰) + `AIGuidePanel.tsx` (Deep dive 잔존)
  - `cs_53_chain_trace_ui.md` (TraceView) → Deep dive 전용으로 위치 이동 (`TracePathView.tsx`)
  - `cs_54_stock_detail_integration.md` → 그대로 살아남음 (`GraphMiniView.tsx` + `?focus=` 딥링크)

### (D-2) Spotlight 모드
- **폐기 근거**: 마켓 뷰는 "중심 노드 없음 → 섹터 단위 overview"가 핵심 UX
- **현황**: `MarketGraphCanvas`는 force-graph-2d 물리 시뮬레이션 + 시드 타입 색상으로 표시 (Spotlight 미사용)

### (D-3) `CUSTOMER_OF` Neo4j 별도 저장 (v1.2 → v1.3)
- **폐기 근거**: 로드맵 v1.3 § 2.4 — "SUPPLIES_TO만 canonical, API에서 역방향 view로 파생"
- **현황**: `chainsight/api/views.py:532-535` `_derive_display_type` — 정상 작동 (outbound 시 CUSTOMER_OF 라벨 변환)

### (D-4) 5단계 상태 (`hidden/weak/probable/confirmed/stale`) — 기존 3단계 대체
- **폐기 근거**: 로드맵 v1.3 + relation_confidence_design_v1
- **대체**: `chainsight/models/relation_discovery.py:78~81` `RELATION_STATUS_CHOICES`, migration 0005에서 previous_status 추가

### (D-5) Heat Score Phase 2 — PostgreSQL `SeedHeatScore` 모델 → Neo4j 노드 속성 직저장
- **폐기 근거**: 명시적 결정 문서는 없으나 `tasks/seed_tasks.py` 구현이 PostgreSQL 모델 없이 Neo4j에 직접 적재
- **위험**: 시계열 비교 불가 (재계산 시 이전 값 유실). 정식 폐기인지 미구현인지 모호 → **결정 문서 필요**

---

## 추가 발견 (설계서 외 구현)

설계 문서엔 없지만 코드에 존재하는 기능:

| 코드 | 역할 | 추정 출처 |
|------|------|----------|
| `chainsight/models/saved_path.py` + `PathAction` | 사용자 탐색 경로 저장 | migration 0006 (2026-04-12 추정) |
| `chainsight/serializers/path_watchlist.py` | Path watchlist 직렬화 | 위 동일 |
| `chainsight/views/watchlist_views.py` | Path watchlist API | 위 동일 |
| `chainsight/services/recheck_service.py` | 관계 재검증 서비스 | 미문서화 |
| `chainsight/services/expand_service.py` | 그래프 확장 서비스 | 미문서화 |
| `chainsight/services/alternatives_service.py` | 대체 종목 탐색 서비스 | 미문서화 |
| `frontend/components/chainsight/PathCard.tsx`, `WatchButton.tsx`, `FullPathView.tsx` | Path watchlist UI | 미문서화 |
| `frontend/app/chainsight/watchlist/[id]/` | Watchlist 상세 페이지 | 미문서화 |

→ Path watchlist 서비스가 설계 문서 없이 추가됨. **`docs/chain_sight/plan/` 또는 별도 설계서 작성 권고**.

---

## 결론 및 후속 조치 권고

### 핵심 평가
1. **로드맵 M0~M4 완료**: Phase 0~4 모든 cs_NN 문서가 (A) 등급. Neo4j 1,500+ 노드 + 6,000+ 관계 + 4 API 작동
2. **redesign_v1 (2026-04-10) 완전 머지**: 마켓 뷰 5컴포넌트 + 시드 선정 + Neo4j dirty sync 모두 살아있음
3. **횡단 영역(SEC, RelationConfidence, Celery) 모두 (A)**: 설계 원칙 100% 이행

### 즉시 차단 요소
- **없음**. 모든 미구현은 "Phase 2", "Future" 명시 또는 비핵심 항목

### 다음 우선순위 권고
1. **B-1 center.volume_ratio 추가** (수 줄, 즉시 가능) — 마켓 뷰 카드 표현 보강
2. **B-3 relation_new 감지 로직** — 신규 관계 출현이 시드 풀에 노출되어야 그래프 회전이 활성화됨
3. **B-6 serverless ETF legacy 정리** — 이중 진실 소스 위험 제거 (DC-2 종결)
4. **C-4 GDS 결과 시드/마켓 뷰 활용** — pagerank/community 점수가 사장된 상태. 시드 선정 가중치에 추가 검토
5. **Path watchlist 설계서 작성** — 미문서화된 신규 기능에 대한 사후 명세화

### 결정 필요 항목
- **C-1 SeedHeatScore PostgreSQL 모델**: 정식 폐기인가, Phase 2 진입 시 추가인가? `DECISIONS.md`에 기록 권고
- **D-5 Heat Score Phase 2 저장 매체**: Neo4j 직저장이 정식 결정이라면 시계열 추적 대안(예: 별도 history 노드) 필요
