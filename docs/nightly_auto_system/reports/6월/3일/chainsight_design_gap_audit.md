# Chain Sight 설계 갭 감사

> **작성일**: 2026-06-03
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **대상**: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` (백엔드) + `frontend/{app,components}/chainsight/` (프론트)
> **방법**: 설계 문서 전수 독해 → 코드 대조 → task_done cross-reference → 핵심 갭 직접 검증

---

## 0. 사전 사실 (구조 이동)

감사 지시서의 경로 `chainsight/` 는 **현재 존재하지 않음**. "서비스 리모델링(데이터 구조 개편)"으로 코드가 이동됨:

| 지시서 경로 | 실제 위치 |
|------------|----------|
| `chainsight/` (백엔드) | **`apps/chain_sight/`** |
| `frontend/components/chainsight/` | 동일 (유지) |
| `frontend/app/chainsight/` | 동일 (유지) |

- 백엔드 라우팅 base: `/api/v1/chainsight/` (config/urls.py:44) — URL prefix는 `chainsight` 유지
- redesign 문서 내 `chainsight/services/...` 경로 표기는 이동 전 기준 → 현재 `apps/chain_sight/services/...`

---

## 1. 요약 (구현률)

| 영역 | 완전(A) | 부분(B) | 미구현(C) | 폐기·대체(D) | 종합 |
|------|:------:|:------:|:--------:|:-----------:|------|
| **백엔드 파이프라인** (cs_00~33, relation_confidence) | 14 | 3 | 0 | 0 | **~88%** |
| **API 계층** (cs_41~43 + redesign 4종) | 6 | 1 | 0 | 0 | **~93%** |
| **프론트엔드** (cs_51~54, redesign UI) | 핵심5/5 | 2 | 1 | 2 | **~92%** |

**총평**: redesign_v1_260409 (2026-04-10 완료, `data_structure_remodeling_V1` 브랜치)가 **마켓 뷰 아키텍처(API 4종 + FE 5컴포넌트)를 신규 추가**했고, 기존 cs_* 설계의 백엔드 파이프라인은 거의 완성 상태. 잔여 갭은 **(1) GDS 자동화, (2) relation_confidence 정밀 규칙, (3) suggestions API 카테고리 2종** 3건에 집중.

### redesign ↔ 기존 cs_* 관계 (핵심 판정)

> **redesign은 기존 cs_*를 "폐기"하지 않고 "병존·분리"시킴.**
> - **마켓 뷰** (신규): redesign API 4종 + FE 5컴포넌트 → `/chainsight` 메인 페이지
> - **Deep Dive workspace** (기존 유지): cs_41~43 API + GraphCanvas/AIGuidePanel/TracePathView → `/chainsight/[symbol]` 심화 탐색
> - 프론트엔드 `cs_5_frontend_design_v2.md` 의 Spotlight 그래프(cs_51)만 마켓 뷰용 MarketGraphCanvas로 **대체(D)**, 나머지는 Deep Dive로 흡수

---

## 2. 문서별 상태 테이블

### 2-A. 백엔드 파이프라인

| 문서ID | 핵심 설계 항목 | 대응 코드 | 분류 | 근거 |
|--------|--------------|----------|:----:|------|
| cs_00 legacy_cleanup | 레거시 정리 + RelationConfidence v2.1 스키마 | `models/relation_discovery.py`, migrations 0001~0008 | **A** | relation_category/canonical_direction/neo4j_dirty 반영 |
| cs_01 migrations | 12 테이블 + normalize_pair | `utils.py`, migrations | **A** | normalize_pair 구현, 마이그레이션 8개 |
| cs_02 neo4j_connection | GraphRepository + 팩토리 | `graph/repository.py` | **A** | get_graph_repository(), lazy driver |
| cs_03 neo4j_schema | 4 constraint + 2 index + init 커맨드 | `graph/schema.py`, `management/commands/init_neo4j_schema.py` | **A** | 제약 4 + 인덱스 2 정의 |
| cs_11 stock_node_load | Stock ~500 로드 | `management/commands/load_stocks_to_neo4j.py` | **A** | 벌크 로드 구현 |
| cs_12 sector_industry | Sector/Industry + BELONGS_TO | `load_sectors_to_neo4j.py` | **A** | BELONGS_TO 로드 |
| cs_13 peer_relations | PEER_OF (Finnhub/FMP) | `tasks/peer_tasks.py`, `load_peers_to_neo4j.py` | **A** | 양 API 호출 |
| cs_21 tier_a_profile | GrowthStage + CapitalDNA | `models/growth_stage.py`, `models/capital_dna.py`, `tasks/profile_tasks.py` | **A** | 두 모델 + 계산 태스크 |
| cs_21b sensitivity | SensitivityProfile (FMP Revenue Geo) | `models/sensitivity.py`, `tasks/sensitivity_tasks.py` | **A** | 모델 + calculate_sensitivity_profiles + **Beat 등록**(아래 ※1) |
| cs_21c insider_signal | InsiderSignal (Finnhub) | `models/insider_signal.py`, `tasks/insider_tasks.py` | **A** | 모델 + calculate_insider_signals + **Beat 등록**(※1) |
| cs_22 co_mention | CoMentionEdge (뉴스) | `tasks/relation_tasks.py::extract_co_mentions` | **A** | 전체 구현, ChainNewsEvent 저장 |
| cs_23 price_co_movement | 90일 상관 | `tasks/relation_tasks.py::calculate_price_co_movement` | **A** | 전체 구현 |
| cs_24 relation_confidence | 종합 판정 | `tasks/relation_tasks.py::update_relation_confidence`, `check_stale_and_decay` | **B** | 골격만 — 정밀 규칙 단순화(§3-1) |
| cs_25 chain_profile_agg | CompanyChainProfile 집약 | `tasks/sync_tasks.py::aggregate_chain_profiles` | **A** | 태스크 + Beat 등록 |
| cs_31 profile_neo4j_sync | ChainProfile → Neo4j (neo4j_dirty) | `services/neo4j_sync.py`, `tasks/sync_tasks.py::sync_profiles_to_neo4j` | **A** | neo4j_dirty 플래그 활용 |
| cs_32 relation_neo4j_sync | confirmed/probable 엣지 동기화 | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py` | **A** | undirected 정규화 |
| cs_33 gds_algorithms | PageRank/Louvain/Betweenness **배치** | (수동 실행만, 자동화 태스크 없음) | **B** | ※2 — 1회 매뉴얼 실행 완료, 자동 재계산 파이프라인 부재 |
| relation_confidence_design_v1 | Tier 1/2/3 증거 + 상태 전이 + truth_score 철학 | `tasks/relation_tasks.py`, `models/relation_discovery.py` | **B** | 프레임워크 O, 정밀 규칙 미구현(§3-1) |

> **※1 정정**: 사전 에이전트 분석은 "Sensitivity/Insider 태스크 Beat 미등록"으로 봤으나 **오류**. 직접 검증 결과 `profile_tasks.py:281-282`에서 `calculate_all_profiles`가 두 태스크를 호출하고, `config/celery.py:691 'chainsight-all-profiles'`로 Beat 등록됨 → **자동 실행됨 (A 유지)**.
>
> **※2 정정**: GDS는 "0% 미구현"이 아님. `task_done/CS-3-3` 기록상 2026-04-03 **수동 1회 실행 완료**(Neo4j 5.26.3 + GDS 2.13.2 설치, PageRank/Louvain 결과 산출). 그러나 코드에는 `gds_tasks.py`/`run_gds_algorithms` **없음** — `path_service.py`는 노드 속성을 **READ만** 함. 따라서 "데이터는 1회 채워졌으나 자동 재계산 불가" → **B(부분)** 가 정확.

### 2-B. API 계층

| 설계 항목 (엔드포인트) | 대응 코드 (클래스) | 분류 | 근거 |
|----------------------|-------------------|:----:|------|
| **redesign** `GET /seeds/` | `SeedListView` | **A** | sector_summary + seeds[], Redis 캐시 + DB fallback |
| **redesign** `GET /sector/{sector}/graph/` | `SectorGraphView` | **A** | nodes/edges 전 필드, node_size percentile |
| **redesign** `GET /{symbol}/neighbors/` | `NeighborGraphView` | **A** | center/neighbors/relation/cross_edges/pagination, 정렬 준수 |
| **redesign** `GET /signals/` | `SignalFeedView` | **A** | total_confidence(mean×0.7+min×0.3), strength, path |
| cs_41 `GET /{symbol}/graph/` | `ChainSightGraphView` | **A** | depth 제한, market_signals, SUPPLIES_TO 역방향(CUSTOMER_OF 파생) |
| cs_42 `GET /{symbol}/suggestions/` | `ChainSightSuggestionView` | **B** | 5 카테고리 중 2 누락 — supply_chain·community 미구현(§3-3) |
| cs_43 `GET /trace/` | `ChainSightTraceView` | **A** | shortestPath, path/path_edges, found/path_length, 404 |
| (범위 밖) `watchlist/` + 5 액션 | `WatchlistViewSet` (archive/resolve/recheck/expand/alternatives) | **A** | 설계 미포함 추가분, IsAuthenticated 적용 |

- **폐기 API 없음**: cs_41~43 전부 활성(Deep Dive 용도). redesign 4종과 **용도 분리 병존**.

### 2-C. 프론트엔드

| 설계 항목 | 대응 코드 | 분류 | 근거 |
|----------|----------|:----:|------|
| **redesign ① SectorBar** | `SectorBar.tsx` | **A** | seed_count DESC, 상승/하락 색상 |
| **redesign ② MarketGraphCanvas** | `MarketGraphCanvas.tsx` (37KB) | **A** | 동적 노드 크기, 엣지 색/굵기/점선, 라디얼 레이아웃 |
| **redesign ③ ExplorationTrail** | `ExplorationTrail.tsx` | **A** | 가로 스크롤 + undo + 엣지 라벨 |
| **redesign ④ RelationCardPanel** | `RelationCardPanel.tsx` (10KB) | **A** | pre-focus/focused 분기, 4 그룹, CTA 3종 |
| **redesign ⑤ ChainStoryFeed** | `ChainStoryFeed.tsx` | **A** | 무한 스크롤, strength 배지, chain.title 사용 |
| 공유 상태 인프라 | `explorationStore.ts`, `hooks/useMarketView.ts`, `types/chainsight.ts`, `services/chainsightService.ts` | **A** | Zustand + TanStack Query 전부 구현 |
| cs_51 GraphView(Spotlight) | `GraphCanvas.tsx` (Deep Dive 유지) | **D** | 마켓 뷰는 MarketGraphCanvas로 대체, GraphCanvas는 심화탐색 잔존 |
| cs_52 SuggestionCards | `AIGuidePanel.tsx` | **B** | Deep Dive workspace에만 존재(마켓 뷰 미포함=설계 범위) |
| cs_53 TraceView | `TracePathView.tsx`, `FullPathView.tsx` | **B** | Deep Dive workspace에만 존재 |
| cs_54 종목상세 연결 | `app/chainsight/[symbol]/page.tsx`, `?focus=` 딥링크 | **A** | initializeFocusExploration 원자 처리 |
| (범위 밖) 모바일 대응 | `MobileCardList.tsx` | **A** | [symbol] 페이지 모바일 카드 + 그래프 오버레이 |
| (범위 밖) 관계 필터 칩 | `RelationFilterChips.tsx` + store | **A** | 다중 토글 + 전체 ON/OFF + 실시간 필터 |
| (범위 밖) 전환 애니메이션 | — | **C** | 설계 명세(300ms translateX)는 있으나 코드 없음(§3-4) |

---

## 3. 미구현 항목 상세

### 3-1. relation_confidence 정밀 규칙 — **부분 구현 (가장 큰 갭)**

`relation_confidence_design_v1.md` (v1.1, 37KB)의 핵심 정책이 코드에서 단순화됨:

- **(a) §6 관계별 confirmed 판정 규칙 미적용**
  - 설계: `PEER_OF` = Tier1×2 독립소스 필수 → confirmed / Tier1×1 + same_industry → probable; `SUPPLIES_TO` = Tier1(manual+provenance)만 confirmed; `PRICE_CORRELATED` = confirmed 불가
  - 코드(`relation_tasks.py`): `len(peer_sources) >= 2 → "confirmed"` 식의 단순 count/tier 조합. SUPPLIES_TO 판정 경로 없음(CoMention/Price만), PRICE_CORRELATED raw 상관계수 기준 미적용
- **(b) §10 `calculate_truth_and_status()` 미구현** — truth_score가 고정값(85/60/35/15) 할당만, 69행 정책 자동판정 부재
- **(c) §11 `relation_basis_summary` 템플릿 생성 미적용** — 단순 문자열("뉴스 동시출현 N회")만 할당, TEMPLATES 딕셔너리 미사용
- **(d) §6.1 same_industry 역할 제한 미구현** — boolean 체크만, "보강 증거로만 인정" 규칙 없음
- **(e) §9 manual_seed provenance 검증 / §8 CUSTOMER_OF 역방향 파생** — 미구현/미검증 (DC-3 이후 항목)

> **리스크**: 관계 신뢰도 판정이 설계보다 느슨 → confirmed 오탐 가능성. 단, `check_stale_and_decay`(시간 경과 하향 전이)는 구현됨.

### 3-2. GDS 자동화 배치 — **수동 실행만, 파이프라인 부재**

- 데이터: `task_done/CS-3-3`상 2026-04-03 수동 1회 실행으로 pagerank_score/community_id/betweenness_score 노드 속성 채워짐
- 코드: `gds_tasks.py` 없음. `path_service.py:147-202`는 centrality 값을 **읽기 전용**으로 path 가중치(pagerank 0.25 / betweenness 0.20 / bridge 0.30 / sector 0.25)에 사용
- **갭**: 그래프 구조 변경(신규 PEER_OF/SUPPLIES_TO) 시 centrality **재계산 자동화 없음** → 시간이 지나면 stale. Beat에 GDS rerun 미등록. (`regenerate_summary_paths` 커맨드는 "GDS rerun 이후 수동 실행" 전제)

### 3-3. suggestions API 카테고리 2종 누락 — **부분**

- 구현됨: `peers`, `same_industry`, `co_mentioned`, `same_sector` (views.py:133~209)
- 누락: `supply_chain`(SUPPLIES_TO 양방향), `community`(GDS cluster 기반)
  - supply_chain 키워드는 views.py:878의 **다른 뷰(graph)** 에만 존재
  - community는 GDS community_id 의존 → 3-2 미완과 연쇄
- 필드명 혼동: 설계 `same_sector` vs Neo4j 실제 `BELONGS_TO_INDUSTRY` → `same_industry`로 구현, 명명 불일치

### 3-4. 프론트 전환 애니메이션 — **미구현 (범위 밖 명시 항목)**

- 설계(redesign ui_ux): 중심 이동 시 300ms ease-out, 이전 중심 노드 왼쪽 슬라이드
- 코드: MarketGraphCanvas에 transition/animate 로직 없음 (즉시 리렌더)
- redesign `00_summary.md`가 **"범위 밖(후속 작업)"** 으로 명시 → 의도된 미구현. 기능 영향 낮음.

### 3-5. (참고) redesign 범위 밖 후속 작업 — 미착수

`00_summary.md` "범위 밖" 5항목 현황: Heat Score 계산(C), 전환 애니메이션(C, §3-4), LLM chain title/summary 생성(부분 — API가 title 제공 시 FE 표시 O, 생성 주체 미검증), 2차 카드 설명(relation_summary/why_now/insight_summary, 미검증), 모바일 대응(A, 완료됨).

---

## 4. 폐기/대체 항목

| 구분 | 설계 | 처리 | 비고 |
|------|------|------|------|
| **대체(D)** | cs_51 GraphView (Spotlight 단일 그래프) | → MarketGraphCanvas (마켓 overview/neighbor 분기) | GraphCanvas.tsx는 Deep Dive로 잔존 |
| **흡수(D 부분)** | cs_5_frontend_design_v2 의 마켓 진입 플로우 | → redesign ui_ux_design 으로 재설계 | 5컴포넌트 구조로 전면 개편 |
| **분리·병존(폐기 아님)** | cs_41~43 API, cs_52/53 UI | Deep Dive workspace로 용도 한정 | 마켓 뷰와 공존, 코드 활성 유지 |

> **명확화**: `redesign_v1_260409/` 는 기존 cs_* 문서를 **전면 폐기하지 않음**. 마켓 뷰 레이어를 **신규 추가**하고, 기존 그래프 탐색 UI를 "Deep Dive"로 재배치한 **증분 재설계**. 백엔드 파이프라인(cs_00~33)은 redesign과 무관하게 그대로 유효.

---

## 5. 권고 (우선순위)

| # | 항목 | 근거 | 예상 영향 |
|---|------|------|----------|
| 1 | relation_confidence §6/§10/§11 정밀 규칙 구현 | §3-1, confirmed 오탐 리스크 | 🔴 높음 — 관계 신뢰도 정확성 |
| 2 | GDS 재계산 자동화 (`gds_tasks.py` + Beat) | §3-2, centrality stale화 | 🟡 중간 — path 추천 품질 |
| 3 | suggestions supply_chain·community 카테고리 | §3-3, 제안 다양성 제한 | 🟡 중간 — (community는 #2 선행) |
| 4 | LLM chain title/2차 카드 설명 생성 주체 검증 | §3-5 | 🟢 낮음 |
| 5 | 전환 애니메이션 | §3-4, 범위 밖 명시 | 🟢 낮음 — UX 폴리시 |

---

## 부록: cross-reference (task_done ↔ 코드 일치 여부)

| task_done 문서 | 주장 | 코드 검증 |
|---------------|------|----------|
| CS-0~CS-2-5 | 인프라/시드/파이프라인 완료 | ✅ 일치 (models/services/tasks 존재) |
| CS-3-3_gds_algorithms | GDS 결과 산출 완료 | ⚠️ 데이터는 수동 산출됨, **자동화 코드 없음** (§3-2) |
| CS-4-1_2_3_rest_api | API 3종 완료 | ✅ 일치 (1 부분 — suggestions) |
| CS-5-1/2/3 frontend | 그래프/Pro/모바일 완료 | ✅ 일치 |
| redesign_V1/PR-1~7 | 마켓 뷰 7 PR 완료 | ✅ 일치 (API 4 + FE 5 전부 확인) |
| redesign_V1/data_quality_3_fixes | 데이터 품질 3건 수정 | (본 감사 범위 외 — 미검증) |

---

*감사 한계: 본 보고서는 정적 코드/문서 대조 기반. 런타임 동작(Neo4j 실데이터, Beat 실제 발화, API 응답 스키마 실측)은 검증 범위 밖. relation_confidence §3-1 판정은 `relation_tasks.py` 로직 정독 기반이며 일부 분기 미확인분 존재 가능.*
