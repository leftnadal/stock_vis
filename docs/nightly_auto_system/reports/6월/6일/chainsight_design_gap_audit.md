# Chain Sight 설계 갭 감사

> 읽기 전용 감사. 코드 수정 없음.
> 작성일: 2026-06-06 (야간 자동화)
> 대상: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` + `frontend/` 구현
> 방법: 영역별 4개 조사 에이전트가 file:line 단위로 1:1 대조

---

## 요약 (구현률)

### 선결 사실 — 앱 경로 이동

설계 문서 전체와 task_done 보고서가 가리키는 **`chainsight/`** 디렉토리는 **실제로 존재하지 않는다.** 코드는 `apps/` 구조로 재편되어 **`apps/chain_sight/`** (언더스코어 + `apps.` 접두)에 위치한다. 단,

- Django 앱 레이블·DB 테이블명은 `chainsight`로 유지 (예: `apps/chain_sight/models/relation_discovery.py:157` `db_table="chainsight_relation_confidence"`)
- REST Base URL `/api/v1/chainsight/` 유지 (`config/urls.py:44`)

→ 문서의 `chainsight/` 약칭은 앱 레이블 기준이며, **코드 자체는 정상**. 문서 경로 표기만 구버전.

### 영역별 구현률

| 영역 | 구현률(추정) | 핵심 판정 |
|------|:---:|------|
| **데이터 계층** (cs_01~25, relation_confidence_v1) | **~82%** | 인프라/로드 ~98%, 관계 신뢰도 엔진 ~55%로 정책 단순화 |
| **서비스/Neo4j/API** (cs_31~43) | **~82%** | Sync ~100%, **GDS 0%**, Suggestion ~60% |
| **프론트엔드** (cs_51~54, v2, redesign) | **~80%** | redesign 마켓뷰 ~95%, v2 프로 기능 ~30% |
| **redesign_v1 / PR-1~7** | **PR 7/7 = A** | 마켓뷰 트랙 완전 반영, Heat Score/이벤트전파 범위 외 |
| **전체** | **~80%** | 인프라·파이프라인·기본 UI 견고, 고급 분석층(GDS·관계정책·프로기능) 미달 |

### 핵심 결론 3가지

1. **redesign_v1_260409는 기존 cs_*를 "대체"가 아니라 "추가"했다.** 기존 deep-dive workspace(`/chainsight/[symbol]`)는 그대로 공존하고, 그 위에 마켓뷰 허브(`/chainsight`)를 신설. 유일한 부분 대체는 종목상세 진입점(미니뷰→딥링크).
2. **최대 갭은 GDS 알고리즘 (cs_33) 완전 미구현.** PageRank/Louvain/Betweenness 호출이 코드 전체 0건. 그런데 `remaining_work_plan.md:15`는 "CS-3 GDS 완료"로 **과다 보고**.
3. **두 번째 갭은 관계 신뢰도 판정 로직(cs_24)이 설계 정책표를 위반.** false-positive 방지 규칙이 단순화되어 same_industry 단독으로 confirmed 승격 등 설계가 명시 금지한 경로가 코드에 존재.

---

## 문서별 상태 테이블

### 데이터 계층 (cs_01 ~ cs_25)

| 문서 | 분류 | 대응 코드 (file:line) | 비고 |
|------|:---:|------|------|
| cs_01 migrations 검증 | **A** | `migrations/0001~0008` 전 테이블 존재 | `neo4j_synced`→`neo4j_dirty` 통일(0008, 의도적 대체) |
| cs_02 Neo4j 연결 | **A** | `graph/repository.py:35` `Neo4jGraphRepository` | PID lazy driver, health_check 등 완비 |
| cs_03 Neo4j 스키마 | **A** | `graph/schema.py:13~41` 제약4+인덱스2 | `init_neo4j_schema.py` 커맨드 완비 |
| cs_11 Stock 벌크로드 | **A** | `services/neo4j_loader.py:52` | `--exchange` 옵션만 미구현(사소) |
| cs_12 Sector/Industry | **A** | `neo4j_loader.py:72` | BELONGS_TO_SECTOR/INDUSTRY 완비 |
| cs_13 Peer 관계 | **A** | `neo4j_loader.py:158,209` + `peer_tasks.py:23` | finnhub+fmp 수집, PEER_OF undirected |
| cs_21 Tier A 프로파일 | **A** | `tasks/profile_tasks.py:42,177` | GrowthStage 라벨 세분화, **CapitalDNA ma_tendency 미구현** |
| cs_21b Sensitivity | **A** | `tasks/sensitivity_tasks.py:229` | commodity는 Tier B 보류(설계 허용) |
| cs_21c InsiderSignal | **B** | `tasks/insider_tasks.py:102` | **기관·공매도 데이터 미연동** (아래 상세) |
| cs_22 CoMention | **A** | `tasks/relation_tasks.py:19` | NewsEntity 기반으로 원천 변경(개선) |
| cs_23 PriceCoMovement | **A** | `relation_tasks.py:127` | PEER_OF 쌍으로 범위 한정(개선) |
| cs_24 RelationConfidence | **B** | `relation_tasks.py:212,406` | **정책표 대거 단순화** (아래 상세) |
| cs_25 ChainProfile 집약 | **A** | `tasks/sync_tasks.py:16` | Beat는 재배치되어 활성(D 성격) |
| relation_confidence_design_v1 | **B** | `models/relation_discovery.py:64~183` | 모델 v2.1 반영, 판정함수·템플릿 미구현 |

### 서비스 / Neo4j 동기화 / REST API (cs_31 ~ cs_43)

| 문서 | 분류 | 대응 코드 (file:line) | 비고 |
|------|:---:|------|------|
| cs_31 Profile Neo4j sync | **A** | `tasks/sync_tasks.py:107` + beat `config/celery.py:735` | `neo4j_dirty=True` 필터(P0#9 의도적 대체) |
| cs_32 Relation Neo4j sync | **A** | `sync_tasks.py:173` → `services/neo4j_sync.py:22` | Market 관계 별도 엣지로 생성(설계와 구조 차이) |
| **cs_33 GDS 알고리즘** | **C** | **부재** — `gds_tasks.py` 없음, gds.* 호출 0건 | **최대 갭** (아래 상세) |
| cs_41 Graph API | **A** | `api/views.py:59` `ChainSightGraphView` | edges `explanation` 필드만 미포함(경미) |
| cs_42 Suggestion API | **B** | `api/views.py:117` | **supply_chain·community 카테고리 결손** (아래 상세) |
| cs_43 Trace API | **A** | `api/views.py:222` shortestPath | `alternative_paths` 카운트 미포함(경미) |
| cs_00 Legacy cleanup | **A** | `utils.py` normalize_pair + v2.1 필드 사용 | serverless/ 정리는 범위 외 미확인 |
| remaining_work_plan | 참고 | — | **"GDS 완료" 기재가 코드와 불일치** |

### 프론트엔드 (cs_51 ~ cs_54, v2, redesign)

| 문서 | 분류 | 대응 코드 | 비고 |
|------|:---:|------|------|
| cs_51 Graph 시각화 | **D** | `GraphCanvas.tsx`로 대체 (원안 `GraphView.tsx` 미존재) | v2가 흡수 |
| cs_52 AI Guide UI | **D→B** | `AIGuidePanel.tsx`로 대체 | `CategoryCard` 인라인, strength dots→텍스트 |
| cs_53 Chain Trace UI | **D→A** | `TracePathView.tsx`로 대체 | from/to 수동입력→노드탭 연동 |
| cs_54 종목상세 연계 | **B** | `app/stocks/[symbol]/page.tsx:446` | **설계 충돌** (탭유지 vs redesign 탭제거) |
| cs_5_frontend_design_v2 | **B** | deep-dive workspace 다수 | 프로기능(오버레이/비교/Watchlist CTA) ~30% |
| redesign ui_ux v2.2 | **A** | 마켓뷰 5컴포넌트 전부 존재 | SeedCard/RelationCard/ChainStoryCard 인라인화 |

### redesign_v1_260409 PR 트랙

| PR | 설계 대응 | 판정 | 코드 |
|----|------|:---:|------|
| PR-1 스키마 | api/seed §8 | **A** | `migrations/0005` + `relation_discovery.py:139` |
| PR-2 시드 task | seed §2 | **A** | `services/seed_selection.py` (5소스+영속화) |
| PR-3 Neo4j dirty sync | api §8 | **A** | `services/neo4j_sync.py` + `tasks/neo4j_dirty_sync_tasks.py:14` |
| PR-4 API 4종 | api 전체 | **A** | `views.py:367,378,532,736` + `urls.py:19~41` |
| PR-5 FE 골격 | ui_ux §6,7,12 | **A** | `explorationStore.ts`, `useMarketView.ts`, `page.tsx` |
| PR-6 트레일+카드 | ui_ux §8,9 | **A** | `ExplorationTrail.tsx`, `RelationCardPanel.tsx` |
| PR-7 체인스토리 | ui_ux §10 | **A** | `ChainStoryFeed.tsx` |

→ **PR-1~7 전부 코드 반영 (7/7 = A).** 미반영분은 PR 범위가 아닌 seed_design Phase 2~3(Heat Score, 이벤트 전파)뿐이며 `00_summary.md`가 명시적으로 "범위 밖" 선언.

---

## 미구현 항목 상세

### 1. (C) GDS 알고리즘 — cs_33 **[최우선 갭]**

설계 산출물 `chainsight/tasks/gds_tasks.py` **파일 부재.** 소스 전체에서 `gds.`, `graph.project`, `gds.pageRank.write`, `gds.louvain.write`, `gds.betweenness.write` 호출 **0건**. `run_gds_algorithms` 태스크·beat 스케줄 모두 0건.

GDS 산출 속성은 **쓰는 코드 없이 읽기만 존재**:
- `services/path_service.py:186-207` `_fetch_centrality`가 `s.pagerank_score`/`s.betweenness_score`를 조회만 함
- `graph/schema.py:41` `community_id` 인덱스만 생성, 채우는 로직 없음

운영상 영향: `path_service.py:147-161`이 None 폴백(bridge 0.75)을 갖춰 **동작은 하나**, M3 마일스톤("Neo4j 풍부화")은 미달성. Suggestion API의 community 카테고리(아래 #3)도 이것이 근본 원인.

**문서 부채:** `remaining_work_plan.md:15`의 "CS-3 ... GDS(PageRank, Louvain, Betweenness) 완료" 기재는 **사실과 다름**.

### 2. (B) InsiderSignal 기관·공매도 미연동 — cs_21c

`tasks/insider_tasks.py:102`는 Finnhub insider 거래 집계만 구현. 설계 데이터 원천표(cs_21c L13-26) 대비 미구현:
- `institutional_ownership_pct` / `institutional_change_qoq` / `top_holder_action` — FMP Institutional Holders 미연동
- `short_interest_pct` / `short_interest_change` / `days_to_cover` — 미구현
- 결과: `_classify_smart_money(insider_signal, None, None)`(`insider_tasks.py:163`)로 None 하드코딩 → `smart_money_signal`이 insider 단일 입력만 사용 (설계는 3종 종합)

**모델(`models/insider_signal.py`)에는 해당 필드가 전부 정의되어 있고 채우는 로직만 없음.**

### 3. (B) RelationConfidence 판정 로직이 설계 정책 위반 — cs_24 **[2순위 갭]**

설계(`relation_confidence_design_v1.md` 섹션 6/10)는 Tier 기반 보수적 판정으로 false-positive를 막도록 명시했으나 구현이 단순화됨:

- **PEER_OF**: 설계는 Tier1 독립소스 2개(fmp+finnhub) 필수, same_industry는 probable 보강만. 구현은 `peer+industry` 2개면 confirmed(85) 부여(`relation_tasks.py:287-288`) → **same_industry 단독 보강으로 confirmed 승격** (설계 명시 금지 경로)
- **CO_MENTIONED**: 설계는 Market 관계 confirmed 불가. 구현은 count≥10이면 confirmed(`relation_tasks.py:328-329`)
- **PRICE_CORRELATED**: 설계는 단독 최대 weak. 구현은 corr≥0.8이면 confirmed(`relation_tasks.py:367`)
- **판정 함수 미구현**: 설계 섹션10의 `calculate_truth_and_status`/`_calculate_market_status`가 코드에 없고 task 내 인라인 if-else로 대체
- **관계 타입 커버리지**: 7개 RELATION_TYPE 중 PEER_OF/CO_MENTIONED/PRICE_CORRELATED 3종만 산출. SUPPLIES_TO·COMPETES_WITH·HAS_THEME·BELONGS_TO_* 판정 경로 없음 (SEC pipeline 등 외부 주입 추정)
- **stale 정책**: 타입별 차등(180/90/30/14) 대신 90/60/30 하드코딩(`relation_tasks.py:420`). `stale_threshold_days` 필드 미사용. 기준이 `last_verified_at`(설계) 아닌 `last_observed_at`이고 `last_verified_at`은 영원히 null
- **evidence/summary 구조**: source_type/tier/source_family 메타 + family 독립카운트(count_independent) + 10종 설명 템플릿이 인라인 문자열로 대체 → 설명가능성·감사추적 설계 수준 미달
- **모델 save() 안전망 부재**: undirected 사전순 정규화가 모델 레벨에 없음(task의 normalize_pair 호출에만 의존)

### 4. (B) Suggestion API 카테고리 결손 — cs_42

`api/views.py:117` `ChainSightSuggestionView`는 4종(peers/same_industry/co_mentioned/same_sector)만 구현. 미구현:
- **supply_chain 카테고리 없음** (설계 SUPPLIES_TO 기반)
- **community 카테고리 없음** (community_id 매칭 — GDS 미실행이 근본 원인)
- same_sector `top_tickers`가 빈 배열 고정(`views.py:211`)
- 경쟁사가 PEER_OF만, COMPETES_WITH 미포함

완료기준 "카테고리 2개 이상"은 충족하나 설계 5개 중 3개만 실현.

### 5. (B) v2 프로 투자자 기능 + 종목상세 충돌 — cs_5_v2 / cs_54

- **노드 메트릭 오버레이 미구현** (v2 §6-2: PER 히트맵/Centrality/Louvain 토글)
- **노드 비교 모드 미구현** (v2 §6-3: Ctrl+Click 2노드 비교)
- **NodeDetailPanel Watchlist CTA 누락** (v2 §5는 5종, 실제 `NodeDetailPanel.tsx:86-113`은 4종)
- **프로파일 요약 불완전**: growth_stage/capital_dna 2종만 렌더, InsiderSignal/RateSensitivity 미렌더(`NodeDetailPanel.tsx:71-82`)
- **종목상세 설계 충돌**: redesign §11은 "Chain Sight 탭 제거 + 딥링크"를 지시했으나 실제는 탭 유지(`stocks/[symbol]/page.tsx:84`) + 딥링크 + 미니뷰 혼재(`:446-457`) → **cs_54(탭 유지)와 redesign(탭 제거) 어느 쪽과도 정확히 불일치**

---

## 폐기/대체 항목

### 의도적 대체 (정상 진화, 갭 아님)

| 설계 | 대체물 | 근거 |
|------|------|------|
| `chainsight/` 경로 | `apps/chain_sight/` | apps/ 구조 재편 (앱 레이블·DB명·URL은 `chainsight` 유지) |
| `neo4j_synced`/`synced_to_neo4j` 플래그 | `neo4j_dirty` 단일 소스 | migration 0008, audit P0 #9. CompanyChainProfile 포함 통일 |
| `news/NewsArticle.symbols` 배열 | `services.news.models.NewsEntity` (per-symbol row) | 실제 뉴스 스키마 정합 (cs_22, 개선) |
| `NEO4J_USER` 설정키 | `NEO4J_USERNAME` | `graph/__init__.py:20` |
| PriceCoMovement "같은 섹터 내" | Neo4j PEER_OF 쌍 한정 | `relation_tasks.py:143-147` (조합폭발 회피, 더 정밀) |

### 프론트엔드 설계 대체 (cs_51~54 → v2 → redesign)

**실제 채택된 방향: redesign_v1이 메인, v2가 보조, cs_51~54 원안은 폐기.** 두 화면이 독립 공존:

| 라우트 | 채택 설계 | 역할 |
|--------|------|------|
| `/chainsight` | redesign_v1 (ui_ux v2.2) | 마켓 탐색 허브 (Breadth-first) |
| `/chainsight/[symbol]` | cs_5_frontend_design_v2 | 딥다이브 워크스페이스 (Depth-first, 3-panel) |
| `/chainsight/watchlist[/id]` | **문서 외 추가** (CS-6 SavedPath 트랙) | Path Watchlist |

- cs_51 `GraphView.tsx` → **폐기**, v2 `GraphCanvas.tsx`로 대체
- cs_52 `SuggestionCards.tsx` → **폐기**, v2 `AIGuidePanel.tsx`로 대체
- cs_53 `TraceView.tsx` → **폐기**, v2 `TracePathView.tsx`로 대체
- redesign ui_ux §11이 "딥다이브 워크스페이스 유지"를 명시 → v2 산출물 의도적 보존

### redesign ↔ 기존 cs_* 관계: **(c) 별개 추가 + 진입점만 (b) 일부 대체**

- redesign은 roadmap v1.3에 없는 후속 트랙 (roadmap은 M5에서 종료)
- deep-dive(CS-4 graph/suggestions/trace API + CS-5 컴포넌트)는 그대로 유지·공존 (`urls.py`에 7경로 공존)
- redesign은 그 위에 마켓뷰(4 신규 API + 5 신규 컴포넌트)를 **추가**
- 유일한 부분 대체: 종목상세 진입점이 미니뷰(CS-5-1)→딥링크 버튼으로 교체 (단, 실제로는 둘 다 남아 충돌 — 위 #5)

### 설계 문서에 없는데 추가 구현된 항목 (설계 초과)

- 백엔드: `models/saved_path.py`, `seed_snapshot.py`(버그#27 영속화), `services/{path,expand,alternatives,recheck}_service.py`, NeighborGraphView/SectorGraphView/SignalFeedView/Watchlist
- 프론트엔드: `RelationFilterChips.tsx`(271줄), `NodeContextMenu.tsx`, `NodeTooltip.tsx`, Path Watchlist 전체(`WatchButton`/`PathCard`/`FullPathView` + 라우트 2개 + `usePathWatchlist`)

---

## 문서 부채 (수정 권고 — 본 감사 범위상 미수정)

1. **`remaining_work_plan.md:15`** — "CS-3 GDS 완료" 기재가 코드(미구현)와 불일치. 과다 보고.
2. **`chain_sight_roadmap_v1.3.md`** — redesign_v1(2026-04-10~13) + CS-6 SavedPath 트랙이 미반영 (로드맵은 M5에서 종료). 후속 확장 미기록.
3. **`00_summary.md`** — migration 0006/0007/0008, SavedPath/SeedSnapshot 모델, data_quality 3-fix가 미언급 (summary 시점 2026-04-10 이후 누적된 정상 진화. 틀린 게 아니라 시점 차이).
4. **전 task_done·설계 문서의 `chainsight/` 경로 표기** — 실제 `apps/chain_sight/`. 앱 레이블 기준 약칭이므로 코드는 정상이나 신규 작업자 혼동 소지.

---

## 종합 우선순위

| 우선순위 | 항목 | 분류 | 영향 |
|:---:|------|:---:|------|
| 🔴 1 | GDS 알고리즘 (cs_33) | C | M3/M4 "Neo4j 풍부화" 미달, community 추천·centrality 정렬 공백 |
| 🔴 2 | RelationConfidence 정책 위반 (cs_24) | B | false-positive 관계가 confirmed로 노출될 위험 |
| 🟡 3 | InsiderSignal 기관·공매도 (cs_21c) | B | smart_money_signal 신뢰도 절반만 반영 |
| 🟡 4 | Suggestion supply_chain/community (cs_42) | B | 추천 카테고리 5→3 |
| 🟡 5 | v2 프로 기능 + 종목상세 충돌 (cs_5_v2/cs_54) | B | 전문투자자 차별점 미구현 + 설계 모순 |
| 🟢 6 | 문서 부채 4건 | — | 작업자 혼동, 진행 상태 오인 |

**총평:** 인프라(cs_01~13)·파이프라인(cs_21~25)·Neo4j 동기화(cs_31~32)·REST API 골격(cs_41~43)·redesign 마켓뷰(PR-1~7)는 견고하게 구현됨(설계 초과 영역도 다수). 미달 영역은 **고급 분석층** — 그래프 알고리즘(GDS), 관계 신뢰도의 보수적 판정 정책, 멀티소스 인사이더 시그널, 전문투자자 UI에 집중. 동작은 폴백으로 유지되나 설계가 의도한 "분석 깊이"는 ~80% 수준.
