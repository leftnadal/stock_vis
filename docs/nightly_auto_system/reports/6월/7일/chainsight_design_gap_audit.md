# Chain Sight 설계 갭 감사

> 읽기 전용 감사. 코드 수정 없음.
> 작성일: 2026-06-07 (야간 자동화)
> 대상: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` + `frontend/` 구현
> 방법: 영역별 3개 조사 에이전트가 file:line 단위로 1:1 대조 (데이터계층 / API·Neo4j / 프론트엔드)
> 직전 회차: `docs/nightly_auto_system/reports/6월/6일/chainsight_design_gap_audit.md`

---

## 요약 (구현률)

### 선결 사실 — 앱 경로 이동 (지시서의 `chainsight/`는 경로 오기)

지시서와 설계 문서·task_done 보고서가 가리키는 **`chainsight/`** 디렉토리는 **저장소 루트에 존재하지 않는다.** 코드는 `apps/` + `packages/` 구조로 재편되어 다음에 위치한다.

- 백엔드: **`apps/chain_sight/`** (언더스코어 + `apps.` 접두). 예: `apps/chain_sight/api/views.py:20` `from apps.chain_sight.graph import ...`
- 공유 모델: `packages/shared/stocks/models.py` (예: `views.py:24` `from packages.shared.stocks.models import Stock`)
- 프론트엔드: `frontend/components/chainsight/` + `frontend/app/chainsight/`
- Django 앱 레이블·DB 테이블명·REST Base URL은 `chainsight`로 유지 → 문서의 `chainsight/` 약칭은 앱 레이블 기준이며 **코드 자체는 정상**, 문서 경로 표기만 구버전.

이는 CLAUDE.md "진행 중 — 서비스 리모델링(데이터 구조 개편)" 항목의 실체로 확인된다.

### 영역별 구현률

| 영역 | 구현률(추정) | 핵심 판정 | 6/6 대비 |
|------|:---:|------|:---:|
| **데이터 계층** (cs_11~25, relation_confidence_v1, seed redesign) | **~80%** | 인프라/로드 ~98%, 관계 신뢰도 엔진 ~55%, 시드 redesign Phase 2/3 미착수 | 동일 |
| **서비스/Neo4j/API** (cs_31~43, redesign API) | **~82%** | Sync ~100%, **GDS 0%**, Suggestion ~60%, redesign neighbors/signals 필드 결손 | 동일 |
| **프론트엔드** (cs_51~54, v2, redesign) | **~80%** | redesign 마켓뷰 ~95%, v2 deep-dive 가동, 프로 기능 ~30% | 동일 |
| **redesign_v1 / PR-1~7** | **PR 7/7 = A** | 마켓뷰 트랙 완전 반영, Heat Score/이벤트전파 범위 외 | 동일 |
| **전체** | **~80%** | 인프라·파이프라인·기본 UI 견고, 고급 분석층(GDS·관계정책·프로기능) 미달 | 동일 |

> 코드 변경 없음(6/6→6/7). 본 회차는 redesign API의 **필드/키명/타입 단위 갭**과 **SeedHeatScore 모델 부재(C)**를 추가 특정하여 정밀도만 향상.

### 핵심 결론 4가지

1. **redesign_v1_260409는 기존 cs_5x를 "대체"가 아니라 "분업 공존"한다.** 마켓뷰 허브(`/chainsight`)는 redesign이 100% 지배, deep-dive 워크스페이스(`/chainsight/[symbol]`)는 cs_5_frontend_design_v2가 그대로 지배. cs_5x 컴포넌트(AIGuidePanel, TracePathView, FilterPanel, GraphCanvas, MobileCardList)는 **죽은 코드가 아니라 deep-dive에서 실가동 중**. 유일한 부분 대체는 종목상세 진입점(미니뷰→마켓뷰 딥링크).
2. **최대 갭은 GDS 알고리즘(cs_33) 완전 미구현(C).** PageRank/Louvain/Betweenness 쓰기 호출이 코드 전체 0건. `gds_tasks.py` 파일 부재. 그런데 `remaining_work_plan.md:15`·`docs/chain_sight/task_done/CS-3-3_gds_algorithms.md`는 "CS-3 GDS 완료"로 **과다 보고**. Suggestion API의 community 카테고리 결손·path_service centrality None 폴백의 근본 원인.
3. **두 번째 갭은 관계 신뢰도 판정 엔진(cs_24 / relation_confidence_design_v1)이 설계 정책표를 위반·단순화.** `calculate_truth_and_status`·`count_independent`·TEMPLATES·manual_seed/provenance가 전부 ad-hoc 인라인으로 대체되거나 누락. Market 관계(CO_MENTIONED/PRICE_CORRELATED)를 confirmed로 승격하는 등 설계가 명시 금지한 경로가 코드에 존재.
4. **세 번째 갭은 시드 redesign Phase 2/3.** `SeedHeatScore` Django 모델 미구현(C, Neo4j 노드 속성으로만 저장 → 일별 이력·components·seed_rank 영속화 안 됨), Heat 가중치 6→4 축소, Phase 3 이벤트 전파(text_conditional_prob/lagged correlation/propagation_weight) 전체 미착수(C).

---

## 문서별 상태 테이블

### 데이터 계층 (cs_11 ~ cs_25, relation_confidence_v1, seed redesign)

| 문서 | 분류 | 대응 코드 (file:line) | 비고 |
|------|:---:|------|------|
| cs_11 Stock 벌크로드 | **A** | `management/commands/load_stocks_to_neo4j.py` + `services/__init__.py` | 없음 |
| cs_12 Sector/Industry | **A** | `management/commands/load_sectors_to_neo4j.py:26` | BELONGS_TO_SECTOR/INDUSTRY 완비 |
| cs_13 Peer 관계 | **A** | `management/commands/load_peers_to_neo4j.py` + `tasks/peer_tasks.py:23` | finnhub+fmp 수집 |
| cs_21 Tier A 프로파일 | **A** | `tasks/profile_tasks.py:42,177,273` | GrowthStage 라벨 4→6종 세분화(확장) |
| cs_21b Sensitivity | **A** | `tasks/sensitivity_tasks.py:229` + `models/sensitivity.py` 전 필드 | 없음 |
| cs_21c InsiderSignal | **B** | `tasks/insider_tasks.py:102,163` | 기관·공매도 6필드 미수집, smart_money 단일입력 축약 |
| cs_22 CoMention | **A** | `tasks/relation_tasks.py:19` + `models/news_event.py` | 원천 NewsEntity로 변경(특이사항 §1) |
| cs_23 PriceCoMovement | **A** | `relation_tasks.py:127,143` | PEER_OF 쌍으로 범위 한정(특이사항 §2) |
| cs_24 RelationConfidence | **B** | `relation_tasks.py:212,406` | **정책표 대거 단순화·위반** (미구현 상세) |
| cs_25 ChainProfile 집약 | **A** | `tasks/sync_tasks.py:16` | Beat 재배치(폐기/대체 §C) |
| relation_confidence_design_v1 | **B** | `models/relation_discovery.py:64~183` | 모델 v2.1 반영, 판정함수·템플릿·정규화 미구현 |
| redesign seed_node_design | **B** | `services/seed_selection.py` + `tasks/seed_tasks.py:28` (Phase 1) | **Phase 2 SeedHeatScore 미구현(C), Phase 3 전파 미착수(C)** |

### 서비스 / Neo4j 동기화 / REST API (cs_02~43, redesign API)

| 문서 | 분류 | 대응 코드 (file:line) | 비고 |
|------|:---:|------|------|
| cs_02 Neo4j 연결 | **A** | `graph/repository.py:35` (PID lazy driver, health_check, bulk_upsert) | 없음 |
| cs_03 Neo4j 스키마 | **A** | `graph/schema.py:10~45` 제약4+인덱스2 + `init_neo4j_schema.py` | `--verify/--check/--reset` 완비 |
| cs_31 Profile→Neo4j sync | **A** | `tasks/sync_tasks.py:107~170` | neo4j_dirty 단일 플래그(폐기/대체 §A) |
| cs_32 Relation→Neo4j sync | **A** | `sync_tasks.py:173~207` + `services/neo4j_sync.py:22~97` | Market도 실엣지 MERGE(구조차, 결손 아님) |
| cs_33 GDS 알고리즘 | **C** | `gds_tasks.py` **부재**, `gds.*`/`pageRank.write`/`louvain.write`/`betweenness.write` **0건** | **전체 미구현 (최대 갭)** |
| cs_41 Graph API (deep dive) | **A−** | `api/views.py:59~113` + CUSTOMER_OF 파생(:94) | `edges[].explanation`(basis_summary) 미포함 |
| cs_42 Suggestion API | **B** | `views.py:117~216` 4 카테고리 | **supply_chain·community 카테고리 결손**, 경쟁사 PEER_OF만, same_sector top_tickers 빈배열 |
| cs_43 Trace API | **A−** | `views.py:222~292` shortestPath | `alternative_paths` 카운트 미포함 |
| redesign chainsight_api_design v2.1 | **B** | 7 View 전부 존재(`views.py:367,378,532,736` + `urls.py:21~40`) | neighbors/signals 응답 필드 결손·키명 불일치 (아래 표) |

### 프론트엔드 (cs_51~54, cs_5_frontend_design_v2, redesign UI/UX)

| 문서 | 분류 | 대응 코드 (file) | 비고 |
|------|:---:|------|------|
| cs_51 Graph Visualization | **D** | 원안 산출물(GraphView/GraphControls/useGraphData) 미존재 → `GraphCanvas.tsx`로 대체 | 컨셉은 cs_5_v2 경유 구현 |
| cs_52 AI Guide UI | **D** | 원안 SuggestionCards 미존재 → `AIGuidePanel.tsx`(`[symbol]/page.tsx:18,299`) 대체 | 카테고리→그래프 필터 구현 |
| cs_53 Chain Trace UI | **D** | 원안 TraceView 미존재 → `TracePathView.tsx`(`[symbol]/page.tsx:21,315`) 대체 | from/to 트레이스 구현 |
| cs_54 Stock Detail 통합 | **B** | `GraphMiniView`=`ChainSightMiniView`(`app/stocks/[symbol]/page.tsx:58,457`) | 탭 유지·링크 대상 불일치, 연결태그/프로파일 블록 미구현 |
| cs_5_frontend_design_v2 | **A** | `app/chainsight/[symbol]/page.tsx` 전체(3-panel + 컴포넌트 구조 일치) | **deep-dive 워크스페이스 진실의 소스** |
| redesign chainsight_ui_ux_design | **A** | `app/chainsight/page.tsx:7~12,64~79` 5컴포넌트 + `lib/stores/explorationStore.ts` | **마켓뷰 진실의 소스** |
| redesign marketview_pr_prompts (PR-5/6/7) | **A** | SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed 전부 + `hooks/useMarketView.ts` | 컴포넌트 파일 분리만 미준수(인라인화) |

---

## 미구현 항목 상세

### 1. GDS 알고리즘 (cs_33) — 완전 미구현 (C) ★ 최대 갭

- `gds_tasks.py` 파일 부재. `run_gds_algorithms` task·Beat 0건.
- `gds.*`, `graph.project`, `pageRank.write`, `louvain.write`, `betweenness.write` 호출 전체 0건 (grep 확인).
- GDS 산출 속성은 **읽기만 존재, 쓰기 없음**: `services/path_service.py:186~205` `_fetch_centrality`가 `s.pagerank_score`/`s.betweenness_score` 조회만 → 항상 None → :147~161에서 bridge 0.75 폴백.
- `community_id`는 `graph/schema.py:41` 인덱스만 생성, 채우는 코드·읽는 코드 없음.
- **영향**: Suggestion API community 카테고리 결손, M3 "Neo4j 풍부화" 미달. `remaining_work_plan.md:15`·`task_done/CS-3-3_gds_algorithms.md`의 "완료" 표기는 **과다 보고**.

### 2. 관계 신뢰도 엔진 (cs_24 / relation_confidence_design_v1) — 부분 구현 (B)

설계 핵심인 **정책표 기반 판정 엔진 미구현**. `relation_tasks.py:212` `update_relation_confidence`가 하드코딩 if-else로 대체.

- `calculate_truth_and_status()` 함수 없음 (설계 §10, grep 0건). 인라인 분기(relation_tasks.py:287~298)로 대체.
- **관계 타입 3종만 생성**: PEER_OF, CO_MENTIONED, PRICE_CORRELATED. **SUPPLIES_TO/COMPETES_WITH/HAS_THEME 판정 로직 없음** (path/expand 서비스·SEC 시드 커맨드에만 등장, 신뢰도 엔진 미통합).
- **Tier 규칙 위반**: 코드(relation_tasks.py:287)는 `peer + industry` 둘 다 있으면 confirmed → 설계 §6 "same_industry 단독/보강으로 confirmed 불가" 위반.
- **Market 관계 confirmed 승격(설계 명시 금지 위반)**: relation_tasks.py:329 CO_MENTIONED count≥10 → confirmed(85), :367 PRICE_CORRELATED corr≥0.8 → confirmed. 설계는 Market 관계 confirmed 절대 불가, weak 최대.
- `manual_seed`/`provenance` 프로토콜 전무 (설계 §9, grep 0건). `data/seed/` JSON 경로 없음.
- `count_independent()` 없음 (설계 §14). evidence_count_independent는 단순 리스트 길이(relation_tasks.py:310).
- `relation_basis_summary` 템플릿 10종 없음 (설계 §11 TEMPLATES). 인라인 f-string 대체.
- **stale 정책 불일치**: 설계 §13 타입별 차등(PEER_OF 180/COMPETES 90/PRICE 30/CO_MENTION 14) ↔ 코드(relation_tasks.py:417~435) 타입무관 고정값(90/60/30). 모델 기본 `stale_threshold_days=90`도 설계(180)와 불일치(relation_discovery.py:136).
- stale 기준 시각: 설계 `last_verified_at` ↔ 코드 `last_observed_at`(relation_tasks.py:419). `last_verified_at` 필드는 존재하나 세팅하는 task 0건.
- `save()` 사전순 정규화 미구현 (설계 §7) — save()는 previous_status·neo4j_dirty만 처리(relation_discovery.py:165). task 레벨 normalize_pair에만 의존 → API/admin 직접 생성 시 중복 위험.
- evidence_sources 기본형: 설계 `default=list` ↔ 코드 `default=dict`(relation_discovery.py:118). §10 리스트 순회 계산함수와 구조 비호환.
- truth_score 타입: 설계 IntegerField+null ↔ 코드 `FloatField(default=0)`(relation_discovery.py:110, null 불가) → Market 관계도 0 저장.

### 3. 시드 redesign Phase 2/3 (B/C)

- **Phase 2 SeedHeatScore 모델 미구현 (C)**: 설계 §3.4 Django 모델(stock, date, heat_score, components JSONField, seed_rank, unique_together) 코드·마이그레이션 0건. heat_score는 `tasks/seed_tasks.py:146`에서 Neo4j :Stock 노드 속성으로만 기록 → 일별 이력/components/seed_rank 영속화 안 됨.
- **Heat 가중치 불일치**: 설계 §3.3 6항목(price 0.25/volume 0.20/relation 0.20/comention 0.15/news 0.10/gds_centrality_delta 0.10) ↔ 코드 `seed_tasks.py:95` 4항목 각 0.25. **comention_surge·gds_centrality_delta 누락**.
- **Phase 3 이벤트 전파 전부 미구현 (C)**: text_conditional_prob, lagged correlation, propagation_weight, 방향성 전파 엣지 — grep 0건. Beat(chainsight-text-conditional 등) 미등록.

### 4. redesign API 응답 필드 갭 (B)

| 엔드포인트 | 설계 필드 | 구현 상태 | 위치 |
|------|------|------|------|
| GET /seeds/ | 전 필드 | **OK** (payload 통과) | `views.py:367~372` |
| GET /sector/{sector}/graph/ | nodes/edges 전 필드 | **OK** | `views.py:477~508` |
| GET /{symbol}/neighbors/ | relation.evidence_tier_best (string `tier1/2/3`) | **키명 불일치 + 타입 불일치** — 출력 키 `evidence_tier`(Cypher alias :609), 값은 IntegerField default=3(models:115) | `views.py:609,674` |
| GET /{symbol}/neighbors/ | neighbors[].signal_count | **누락** | `views.py:658~663` |
| GET /{symbol}/neighbors/ | 2차: relation_summary/why_now/insight_summary | **미구현** (설계 "향후 LLM" 명시) | neighbors 응답 0건 |
| GET /signals/ | chains[].path[].relation_to_next/relation_category/relation_truth_score/relation_market_score/seed_type/daily_return | **누락** — path는 symbol/name/sector만, 관계는 설계에 없는 별도 `edges[]`로 분리 | `views.py:898~915` |
| GET /signals/ | total_confidence (truth??market 단순평균) | **공식 차이** — 구현은 `mean*0.7 + min*0.3` 가중 | `views.py:842~853` |

- 캐싱 키: seeds/sector/neighbors는 설계 일치. signals만 키에 `page_size` 추가(설계 미포함, 무해).

### 5. Suggestion API (cs_42) — 부분 구현 (B)

- 구현 4 카테고리: peers / same_industry / co_mentioned / same_sector (`views.py:117~216`).
- **supply_chain 카테고리 없음** (SUPPLIES_TO), **community 카테고리 없음** (community_id, GDS 의존), 경쟁사가 PEER_OF만(COMPETES_WITH 제외), same_sector `top_tickers` 빈 배열 고정(:211).

### 6. cs_21c InsiderSignal — 부분 구현 (B)

- 모델 필드는 존재(`models/insider_signal.py:47~66`)하나 task 미충전: institutional_ownership_pct, institutional_change_qoq, top_holder_action, short_interest_pct, short_interest_change, days_to_cover.
- FMP Institutional Holders API 미호출. `_classify_smart_money(insider_signal, None, None)`(insider_tasks.py:163) → 기관/공매도 항상 None.

### 7. cs_54 Stock Detail 통합 — 부분 구현 (B)

- GraphMiniView 임베드됨(`app/stocks/[symbol]/page.tsx:457`).
- **불일치 1 (탭 유지)**: cs_5_v2 §11·redesign PR-5 작업7은 "Chain Sight 탭 제거→딥링크" 명시했으나 코드는 탭 유지(`page.tsx:84`).
- **불일치 2 (링크 대상)**: cs_54는 `/chainsight/{symbol}`(deep-dive 직행), 코드는 `/chainsight?focus={symbol}`(redesign 마켓뷰 딥링크, `page.tsx:450`) → redesign이 cs_54 덮어씀.
- **미구현**: "연결 종목 태그 상위 6개" + "프로파일 요약(GrowthStage/CapitalDNA)" 블록 부재(line 446~459).

### 8. 프론트엔드 기타 미구현

- MarketGraphCanvas 시드 노드 **bounce 애니메이션** 미구현 (PR-5 작업5, `bounce` grep 0건).
- cs_5_v2 §6-2 노드 메트릭 오버레이(PER 히트맵/Centrality/Louvain) + §6-3 노드 비교 모드(Ctrl+Click) — "프로 기능", 코드 흔적 없음.
- 컴포넌트 파일 분리 미준수(기능 충족): SeedCard/RelationCard → `RelationCardPanel.tsx` 인라인, ChainStoryCard → `ChainStoryFeed.tsx` 인라인, CategoryCard/GraphControls/TracePanel 별도 파일 없음.

---

## 폐기/대체 항목

### A. neo4j_synced → neo4j_dirty 단일 플래그 통일 (의도적 대체)

설계서 RelationConfidence/ChainProfile은 `synced_to_neo4j=False`. 실제는 audit P0 #9 결정으로 `neo4j_dirty=True`(default) 단일 플래그로 통일 (`relation_discovery.py:147`, `chain_profile.py:84`, migration 0008). DECISIONS 기반 의도적 아키텍처 변경.

### B. 프론트엔드 cs_51~53 원안 컴포넌트 폐기 → cs_5_v2/redesign으로 대체 (D)

cs_51(GraphView/GraphControls/useGraphData), cs_52(SuggestionCards), cs_53(TraceView) 원안 산출물 파일은 미존재. 컨셉은 보존하되 구현은 `GraphCanvas.tsx`/`AIGuidePanel.tsx`/`TracePathView.tsx`로 재명명·재구성. **cs_5_frontend_design_v2가 cs_51~54를 흡수**, redesign이 마켓뷰를 신설.

### C. Celery Beat 재배치 (config dict는 무시됨 — 잠재 리스크)

`config/celery.py:691~766`에 chainsight Beat 8개가 `app.conf.beat_schedule` dict로 정의되나, `settings.py:490` `CELERY_BEAT_SCHEDULER = DatabaseScheduler`이므로 **dict는 런타임 무시**(common-bug #28, celery.py:124~139 주석이 스스로 명시). 실제 스케줄링은 DB `PeriodicTask` 등록 여부에 의존 — 런타임 상태라 정적 감사로 확인 불가. **잠재 리스크로 분류.**

### D. 제3 설계 트랙 — Path Watchlist (update_v2, 본 감사 범위 밖)

`docs/chain_sight/update_v2/`(cs_61~67, ROADMAP_v1.4, RELATION_CONFIDENCE.md)는 cs_5x도 redesign도 아닌 별도 트랙. 대응 코드(WatchButton/PathCard/FullPathView + `hooks/usePathWatchlist.ts` + `views/watchlist_views.py` + `serializers/path_watchlist.py` + migration 0006 SavedPath/PathAction)는 정상 가동 중. 본 지시(plan/ 대비)의 비교 대상이 아니므로 별도 감사 권장.

### E. co-mention/price 원천·범위 변경 (개선성 대체)

- cs_22 원천: `news.NewsArticle.symbols` → `services.news.models.NewsEntity` news_id 그룹핑(relation_tasks.py:28).
- cs_23 범위: "같은 섹터 내 모든 쌍" → Neo4j PEER_OF 쌍 한정(relation_tasks.py:143, 더 좁음).
- GrowthStage 라벨: 4종 → 6종 세분화(growth_stage.py:7, 확장).

---

## 부록 — 권고 (읽기 전용, 실행 아님)

1. **문서 정합화**: `remaining_work_plan.md:15`·`task_done/CS-3-3_gds_algorithms.md`의 "CS-3 GDS 완료" 표기를 실제(미구현)에 맞춰 정정 — 과다 보고가 다음 착수 우선순위 판단을 왜곡.
2. **우선순위 갭 3종**: ① GDS(cs_33) 완전 미구현, ② 관계 신뢰도 정책 엔진(cs_24) 설계 위반(Market confirmed 승격), ③ SeedHeatScore 모델 부재. 셋 다 "고급 분석층"으로 인프라/UI 견고함과 대비.
3. **redesign neighbors API 필드 3건**: evidence_tier 키명/타입(int vs string), signal_count 누락, signals path 구조 — 프론트 계약 불일치 가능성, contracts/ 스펙 점검 권장.
4. **Beat DB 등록 런타임 검증**: §C의 8개 chainsight Beat가 DB PeriodicTask에 실제 등록됐는지 운영 확인 필요(정적 감사 불가 영역).
