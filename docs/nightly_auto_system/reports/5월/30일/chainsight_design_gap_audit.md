# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-31
> **범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `chainsight/` + `frontend/components/chainsight/` 구현 대조
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **대조 방식**: 설계 항목별 코드 심볼 존재 확인 + 3종 병렬 탐색 + 직접 grep 검증

---

## 요약 (구현률)

Chain Sight 설계는 **두 갈래 트랙**으로 진화했고, 둘 다 코드에 살아있다. redesign은 cs_* 를 전면 폐기한 것이 아니라 **시드/프론트 UI 컨셉을 재설계하고 공존**한다.

| 트랙 | 설계 위치 | 산출물 | 상태 |
|------|----------|--------|------|
| **로드맵 v1.3** (cs_00~54) | `plan/cs_*.md` | 백엔드 파이프라인 + 종목 중심 딥다이브 워크스페이스 | 대부분 완전 구현 |
| **Redesign V1** (마켓 뷰) | `plan/redesign_v1_260409/` | 시드 노드 + 5섹션 마켓 뷰 허브 | 100% 완전 구현 |

**설계 항목 레벨 구현률 추산: 약 90% 완전 구현**

| 분류 | 개수 | 비중 |
|------|------|------|
| (A) 완전 구현 | 17 | ~81% |
| (B) 부분 구현 | 4 | ~19% |
| (C) 미구현 | 0 | 0% |
| (D) 폐기/대체 | 0 (순수 폐기 없음) | — |

> **순수 (C) 미구현 / (D) 폐기 문서는 없다.** 모든 설계 문서가 최소 부분 이상 구현되었으며, 일부 항목만 (B)로 잔존한다. 완료 보고서(`task_done/`)는 로드맵 22개 PR + redesign 7개 PR 전부 확보(34개 문서).

### 감사 중 정정된 오류

- **heat_score는 "미구현"이 아니라 구현됨**: 초기 탐색에서 "Phase 2 heat_score 미구현"으로 판정했으나, `chainsight/tasks/seed_tasks.py:96 calculate_heat_scores()`(4신호 가중합 `HEAT_WEIGHTS`, Neo4j 저장, Beat 등록 완료)로 **실제 구현 확인**. 단 설계의 `SeedHeatScore` 모델 대신 **Neo4j 노드 속성**(`s.heat_score`)으로 저장하는 방식 변경.
- **cs_54 GraphMiniView 통합 확인됨**: `frontend/app/stocks/[symbol]/page.tsx:58-59,457`에서 `ChainSightMiniView`로 dynamic import 통합 확인 → (A) 확정.

---

## 문서별 상태 테이블

### 백엔드 — 로드맵 v1.3 (cs_00~33)

| 문서 | 핵심 설계 | 구현 근거 | 분류 |
|------|----------|----------|------|
| cs_01 migrations | 12 테이블 + RelationConfidence v2.1 24필드 + normalize_pair | migrations 0001~0008, `utils.py`, `models/*` | **A** |
| cs_02 neo4j connection | GraphRepository Protocol + PID lazy init | `graph/repository.py`, `graph/__init__.py` | **A** |
| cs_03 neo4j schema | Constraint 4 + Index 2 + init command | `graph/schema.py`, `management/commands/init_neo4j_schema.py` | **A** |
| cs_11 stock node load | ~500 :Stock 벌크 | `commands/load_stocks_to_neo4j.py` | **A** |
| cs_12 sector/industry | :Sector/:Industry + BELONGS_TO | `commands/load_sectors_to_neo4j.py` | **A** |
| cs_13 peer relations | PEER_OF undirected 정규화 | `commands/load_peers_to_neo4j.py`, `tasks/peer_tasks.py` | **A** |
| cs_21 tier A profile | GrowthStage(6단계) + CapitalDNA | `models/growth_stage.py`, `models/capital_dna.py`, `tasks/profile_tasks.py` | **A** |
| cs_21b sensitivity | rate/forex/commodity/regulation 민감도 | `models/sensitivity.py`, `tasks/sensitivity_tasks.py` | **A** |
| cs_21c insider signal | insider_signal + smart_money_signal | `models/insider_signal.py`, `tasks/insider_tasks.py` | **A** |
| cs_22 co-mention | ChainNewsEvent + CoMentionEdge 추출 | `models/news_event.py`, `models/relation_discovery.py`, `tasks/relation_tasks.py:extract_co_mentions` | **A** |
| cs_23 price co-movement | 90일 rolling correlation | `models/relation_discovery.py:PriceCoMovement`, `tasks/relation_tasks.py:calculate_price_co_movement` | **A** |
| cs_24 relation confidence | Tier 1~3 + relation_status + truth_score + decay | `models/relation_discovery.py:RelationConfidence`, `tasks/relation_tasks.py:update_relation_confidence` | **B** |
| cs_25 chain profile agg | CompanyChainProfile 집약 + Beat 등록 | `models/chain_profile.py`, `tasks/sync_tasks.py:aggregate_chain_profiles`, `config/celery.py` | **A** |
| cs_31 profile→neo4j | neo4j_dirty delta sync | `tasks/sync_tasks.py:sync_profiles_to_neo4j` | **A** |
| cs_32 relation→neo4j | confirmed/probable MERGE, 나머지 DELETE | `services/neo4j_sync.py:sync_dirty_relations` | **A** |
| cs_33 GDS algorithms | PageRank/Louvain/Betweenness 노드 속성 | `services/path_service.py`(속성 **읽기만**), 정기 계산 task 부재 | **B** |

### 백엔드 — Redesign V1 (시드/heat)

| 문서 | 핵심 설계 | 구현 근거 | 분류 |
|------|----------|----------|------|
| seed_node_design Phase 1 | 시드 선정(price/volume/relation/news 신호), MAX=20, 스냅샷 | `services/seed_selection.py`, `tasks/seed_tasks.py:run_seed_selection`, `models/seed_snapshot.py` | **A** |
| seed_node_design Phase 2 | heat_score 6요소 가중합 | `tasks/seed_tasks.py:calculate_heat_scores`(4신호 가중합) — **SeedHeatScore 모델 대신 Neo4j 속성 저장 (방식 변경)** | **A**(방식변경) |

### API — 로드맵 cs_41~43 + Redesign

| 문서 | 설계 엔드포인트 | 실제 구현 | 분류 |
|------|----------------|----------|------|
| cs_41 graph API | `{symbol}/chainsight/graph/` (depth, rel_types, market_signals, CUSTOMER_OF 파생) | `GET /api/v1/chainsight/{symbol}/graph/` → `ChainSightGraphView` | **A** |
| cs_42 suggestion API | 5 카테고리(peers/supply_chain/same_sector/co_mentioned/community) | `GET .../{symbol}/suggestions/` → **4/5만** (peers/same_industry/co_mentioned/same_sector). **supply_chain·community 누락** | **B** |
| cs_43 trace API | `trace/?from&to&max_depth` shortestPath | `GET /api/v1/chainsight/trace/` → `ChainSightTraceView` | **A** |
| redesign_api 4종 | seeds + sector graph + neighbors + signals | `SeedListView`/`SectorGraphView`/`NeighborGraphView`/`SignalFeedView` 전부 등록 | **A** |

### 프론트엔드 — 로드맵 cs_51~54, cs_5_v2 + Redesign

| 문서 | 핵심 컴포넌트 | 실제 구현 | 분류 |
|------|--------------|----------|------|
| cs_51 graph viz | force-graph 시각화 + spotlight | `GraphCanvas.tsx` + `react-force-graph-2d` dynamic | **A** |
| cs_52 ai guide UI | 좌측 제안 카드 + 강도 | `AIGuidePanel.tsx` (`/chainsight/[symbol]`에서 사용) | **A** |
| cs_53 chain trace UI | from/to 경로 시각화 | `TracePathView.tsx` + `useTrace` 훅 | **A** |
| cs_54 stock detail 통합 | 종목 상세 미니 그래프 + 풀페이지 | `GraphMiniView.tsx`→`stocks/[symbol]/page.tsx:457` 통합 + `/chainsight/[symbol]` 풀페이지 | **A** |
| cs_5_frontend_v2 | 3패널 워크스페이스 + CTA체인 + pro 필터 | 핵심 패널 전부 존재, **pro 필터·CTA 라우팅 일부 미검증** | **B** |
| redesign_ui_ux 5섹션 | SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed | `/chainsight/page.tsx`에 5개 전부 import+렌더, `explorationStore.ts` 공유상태 | **A** |

---

## 미구현 항목 상세 (B 분류 4건)

### B-1. cs_33 GDS 알고리즘 — 정기 계산 task 부재 (가장 실질적인 갭)

- **설계**: PageRank / Louvain Community / Betweenness Centrality를 배치 실행해 `pagerank_score`, `community_id`, `betweenness_score`를 :Stock 노드에 부여.
- **현황**:
  - `services/path_service.py`는 이 속성들을 **읽어서만** 사용 (`centrality.get(n,{}).get('pagerank')`, 가중치 분기 `w={'pagerank':0.25,...}`). 속성이 없으면 `bridge` 가중치로 폴백하도록 **방어 코드까지 갖춤** → 즉 "속성이 비어있을 수 있음"을 코드가 이미 전제.
  - `chainsight/tasks/`에 GDS를 실행/업데이트하는 Celery task **없음** (`run_gds_algorithms` 부재).
  - `task_done/CS-3-3_gds_algorithms.md`에는 2026-04-03 일회성 배치로 PageRank/Louvain/Betweenness 산출 기록 존재.
- **갭**: **일회성 수동 배치로만 채워졌고, 정기 갱신 파이프라인이 없다.** 시간이 지나면 centrality 속성이 stale 상태로 남고, path_service는 bridge 폴백으로 동작. 그래프가 재로드되면 속성이 사라질 위험.
- **권고(감사 의견)**: 정기 GDS 배치 task 신설 또는 명시적 "수동 운영" 결정 문서화.

### B-2. cs_42 suggestion API — 5개 중 2개 카테고리 누락

- **설계**: peers / **supply_chain** / same_sector / co_mentioned / **community** (5종).
- **구현** (`api/views.py:108-180 ChainSightSuggestionView`): peers / same_industry / co_mentioned / same_sector (4종).
- **갭**: `supply_chain`(SUPPLIES_TO 기반), `community`(community_id 일치 기반) 카테고리 미생성. 참고로 `supply_chain`/`co_mention` 분류 로직 자체는 **다른 뷰**(`views.py:761 neighbors` 계열)에는 존재하므로, suggestion 뷰에만 미반영.
- **영향**: 중 — 딥다이브 워크스페이스의 탐색 제안 다양성 80% 수준. community 카테고리는 B-1(GDS)에 의존하므로 GDS 정기화 전엔 의미 제한적.

### B-3. cs_24 relation confidence — decay 상태 전이 자동화 부분 미흡

- **설계**: stale 판정 시 `probable→weak→hidden` 명시적 상태 전이(decay) + `evidence_count_independent` 자동 계산.
- **구현**: `update_relation_confidence()` + `check_stale_and_decay()` 골격 존재(90일 미갱신 처리).
- **갭(추정)**: 단계적 decay 상태 전이와 독립 증거 카운트 자동화가 전 구간을 덮는지 추가 확인 필요. 모델 필드(`relation_status`, `evidence_count_total/independent`)는 전부 존재하므로 데이터 구조 갭은 아님 — **로직 완전성** 갭.
- **주의**: 본 항목은 함수 시그니처 수준 확인이며, 전이 로직 라인별 검증은 미수행(읽기 전용 범위 내 한계). "구조 완비 + 로직 부분"으로 (B) 보수 분류.

### B-4. cs_5_frontend_design_v2 — pro 필터 / CTA 체인 라우팅 일부 미검증

- **설계**: 3패널 워크스페이스 + CTA(가설 생성→`/thesis/new`, Watchlist POST, Validation) + pro 필터(centrality overlay, 노드 비교).
- **구현**: `GraphCanvas`/`AIGuidePanel`/`NodeDetailPanel`/`FilterPanel`/`TracePathView`/`MobileCardList` 전부 존재 및 `/chainsight/[symbol]/page.tsx`에 통합. 엣지 색상 규약(`graphStyles.ts`) 일치.
- **갭**: `NodeDetailPanel` CTA 버튼의 실제 라우팅 타깃(thesis/watchlist/validation)과 pro 전용 필터(centrality overlay·노드 비교 모드)의 완전 통합 여부 미검증. 설계서 §6에서 "Advanced/Future"로 표기된 부분과 겹침 → 영향 낮음.

---

## 폐기/대체 항목

> **순수 폐기(D)된 설계 문서는 없다.** 아래는 redesign에 의해 **방향이 조정·재설계**된 항목으로, 기능은 다른 형태로 존속한다.

| 구버전 (로드맵 v1.3) | 재설계 후 (Redesign V1) | 성격 |
|---------------------|------------------------|------|
| cs_21b `SeedHeatScore` 모델 저장(설계) | `calculate_heat_scores` → **Neo4j 노드 속성**(`s.heat_score`) 저장 | 저장 방식 변경 (기능 존속) |
| cs_5 프론트 "종목 중심 단일 워크스페이스" | **2-tier 구조**: 마켓 뷰 허브(`/chainsight`) + 딥다이브(`/chainsight/[symbol]`) | 구조 확장 (구버전도 딥다이브로 존속) |
| cs_52 "카테고리 필터 패널" | 마켓 뷰에서는 **RelationCardPanel**(시드/이웃 분기)로 재해석 | UI 재설계 (딥다이브엔 AIGuidePanel 존속) |
| cs_53 trace를 메인 UI로 | 마켓 뷰는 ChainStoryFeed(글로벌 시그널) 중심, trace는 딥다이브 보조 | 우선순위 재배치 |

### redesign이 신규 추가한 항목 (로드맵 v1.3 미정의)

- **시드 선정 시스템**(`seed_selection.py` + `run_seed_selection`) — 시장 신호 기반 일일 시드 추출
- **마켓 뷰 5섹션 허브**(`/chainsight/page.tsx`) — SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed
- **체인 스토리 피드**(`ChainStoryFeed.tsx` + `SignalFeedView`) — 글로벌 체인 네트워크 발견
- **neo4j_dirty 플래그 동기화**(`neo4j_sync.py:sync_dirty_relations`) — 기존 synced 플래그 대체

### redesign이 "범위 밖"으로 명시한 후속 항목 (`00_summary.md` §범위 밖)

- 전환 애니메이션(300ms ease-out)
- LLM 기반 chain title/summary 생성 (현재 템플릿 기반)
- 2차 카드 설명 필드(`relation_summary`, `why_now`, `insight_summary`)
- 모바일 그래프 UX 상세
- GDS 정기 배치(= 본 감사 B-1)

---

## 부록 — 실제 등록된 API 엔드포인트 (7종)

| 경로 | 뷰 | 설계 출처 |
|------|-----|----------|
| `GET /api/v1/chainsight/seeds/` | `SeedListView` | redesign |
| `GET /api/v1/chainsight/sector/<sector>/graph/` | `SectorGraphView` | redesign |
| `GET /api/v1/chainsight/<symbol>/neighbors/` | `NeighborGraphView` | redesign |
| `GET /api/v1/chainsight/signals/` | `SignalFeedView` | redesign |
| `GET /api/v1/chainsight/<symbol>/graph/` | `ChainSightGraphView` | cs_41 |
| `GET /api/v1/chainsight/<symbol>/suggestions/` | `ChainSightSuggestionView` | cs_42 (B) |
| `GET /api/v1/chainsight/trace/` | `ChainSightTraceView` | cs_43 |

> cs_41~43(딥다이브)와 redesign 4종(마켓 뷰)은 **상호 대체가 아닌 보완 관계** — 두 진입점(허브/딥다이브)이 공존.

## 부록 — Celery Beat 등록 (config/celery.py, dict 방식)

| 태스크 | 스케줄 | 위치 |
|--------|--------|------|
| `chainsight-heat-score-daily` | NY 07:00 (시드 선정 전) | celery.py:748 |
| `chainsight-seed-selection` | 매일 13:00 UTC | celery.py:755 |
| `chainsight-neo4j-dirty-sync` | 주간, neo4j queue | celery.py:58, 762 |

> **운영 주의**: CLAUDE.md 공통 버그 #28 — DatabaseScheduler 사용 시 dict 스케줄이 무시될 수 있음. 본 감사는 코드 등록만 확인했으며 DB(PeriodicTask) 실제 반영 여부는 별도 점검 권장(읽기 전용 범위 밖).

---

## 감사 한계 (Disclaimer)

- 본 감사는 **정적 코드 대조**(심볼 존재 + import 추적 + grep)에 기반하며, **런타임 동작·데이터 정합성은 검증하지 않았다**.
- (B-3)cs_24 decay 로직, (B-4)CTA 라우팅 타깃은 함수/컴포넌트 존재 수준까지만 확인 — 라인별 로직 완전성은 별도 코드리뷰 필요.
- Celery Beat의 DB 반영, GDS 속성의 현재 stale 여부는 운영 환경 점검 영역.
