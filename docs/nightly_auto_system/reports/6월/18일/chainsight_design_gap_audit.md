# Chain Sight 설계 갭 감사

> **감사일**: 2026-06-18
> **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis`
> **모드**: 읽기 전용 (코드 수정 없음)
> **방법**: `docs/chain_sight/plan/` 설계서 ↔ 실제 코드(`apps/chain_sight/`, `frontend/{app,components}/chainsight/`) 대조 + `docs/chain_sight/task_done/` cross-reference
> **주의**: 백엔드 코드 경로는 설계서가 가정한 `chainsight/`가 아니라 **monorepo 구조의 `apps/chain_sight/`** (밑줄 포함). 프론트는 `frontend/.../chainsight/` (밑줄 없음).

---

## 요약 (구현률)

| 단계 | 설계 문서 수 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 |
|------|:---:|:---:|:---:|:---:|:---:|
| CS-0/CS-1 인프라·시드 | 7 | 7 | 0 | 0 | 0 |
| CS-2 프로파일·관계 | 8 | 6 | 2 | 0 | 0 |
| CS-3/CS-4 Sync·GDS·API | 6 | 2 | 4 | 0 | 0 |
| CS-5 프론트엔드 (v2 원안) | 5 | 5* | 0 | 0 | (마켓뷰 부분 대체) |
| redesign_v1 (PR-1~7) | 7 PR | 7 | 0 | 0 | — |
| **합계** | **26 문서 + 7 PR** | **27** | **6** | **0** | **부분 대체** |

> *CS-5 v2는 **컴포넌트·기능 단위로는 전건 구현(A)**되어 있으나, **마켓 뷰(`/chainsight` 루트) 화면 패러다임은 redesign_v1으로 대체**됨. "전용 워크스페이스 → 완결된 탐색 허브" 철학 전환. 아래 폐기/대체 섹션 참조.

**종합 판정**: 설계서 26개 + redesign 7개 PR 중 **미구현(C) 0건**. Chain Sight v2 + redesign_v1은 **사실상 전건 구현 완료**. 갭은 (1) CS-2-4 관계 신뢰도 엔진의 **정책 단순화(B)**, (2) CS-4 API의 **고급 기능 부분 누락(B)**, (3) 설계 대비 **플래그/타입/경로 명명 변경(개선성 편차)** 에 집중됨.

---

## 문서별 상태 테이블

### CS-0 / CS-1 — 인프라 · 시드 (전건 A)

| 문서 | 판정 | 근거 코드 | 비고 |
|------|:---:|------|------|
| cs_00_legacy_cleanup_api_test | A | `migrations/0004` (RelationConfidence 24필드), serverless 레거시 제거 | API 테스트 결과 task_done 기록 |
| cs_01_migrations_verification | A | `migrations/0001~0010` 10개, `utils.py:28` normalize_pair | 14개 테이블 검증 완료 |
| cs_02_neo4j_connection | A | `graph/repository.py` (Protocol + Neo4jGraphRepository, PID-safe lazy init) | upsert/bulk/health 전건 |
| cs_03_neo4j_schema | A | `graph/schema.py` (4 constraints + 2 indexes), `management/commands/init_neo4j_schema.py` | 멱등성 검증 |
| cs_11_stock_node_bulk_load | A | `services/neo4j_loader.py:29` + `commands/load_stocks_to_neo4j.py` | ~792 노드 |
| cs_12_sector_industry | A | `services/neo4j_loader.py:69` + `commands/load_sectors_to_neo4j.py` | Sector 23 / Industry 127 |
| cs_13_peer_relations | A | `services/neo4j_loader.py:125` (Finnhub/FMP) + `commands/load_peers_to_neo4j.py` | ~24,360 PEER_OF |

### CS-2 — 프로파일 · 관계 추출 (6 A / 2 B)

| 문서 | 판정 | 근거 코드 | 미구현/편차 |
|------|:---:|------|------|
| cs_21_tier_a_profile | A | `models/growth_stage.py`, `models/capital_dna.py`, `tasks/profile_tasks.py` | GrowthStage 6단계 + CapitalDNA 6유형 완성 |
| cs_21b_sensitivity_profile | A | `models/sensitivity.py`, `tasks/sensitivity_tasks.py` (FMP Revenue Geo + REGULATION_MAP) | 503건 적재 |
| cs_21c_insider_signal | A | `models/insider_signal.py`, `tasks/insider_tasks.py` (Finnhub 1.2s delay) | 503건 적재 |
| cs_22_co_mention | A | `models/news_event.py` (ChainNewsEvent), `models/relation_discovery.py:12` (CoMentionEdge), `tasks/relation_tasks.py:18` | 744쌍 |
| cs_23_price_co_movement | A | `models/relation_discovery.py:36` (PriceCoMovement), `tasks/relation_tasks.py:126` (90d corr) | 2,473쌍 |
| **cs_24_relation_confidence** | **B** | `models/relation_discovery.py:64` (v2.1 모델), `tasks/relation_tasks.py:211` | **정책 단순화** — 상세 ↓ |
| cs_25_chain_profile_aggregation | A | `models/chain_profile.py`, `tasks/sync_tasks.py:14` (aggregate_chain_profiles) | neo4j_dirty 적용, 503건 |
| **relation_confidence_design_v1** (상세) | **B** | 모델 90% 반영, 판정 로직 부분 | **Tier 증거 엔진 미완** — 상세 ↓ |

### CS-3 / CS-4 — Neo4j Sync · GDS · REST API (2 A / 4 B)

| 문서 | 판정 | 근거 코드 | 미구현/편차 |
|------|:---:|------|------|
| cs_31_profile_neo4j_sync | B | `tasks/sync_tasks.py:108` (Delta Sync, `s += $props`) | 플래그 `neo4j_synced`→`neo4j_dirty` 의미 반전(개선) |
| cs_32_relation_neo4j_sync | B | `services/neo4j_sync.py:22` | 고정 `RELATED_TO`→동적 `relation_type` 확장(개선). task_done은 레거시 수치 |
| cs_33_gds_algorithms | A | `services/path_service.py:194` (GDS 속성 읽기), task_done 실행 결과 | PageRank/Louvain/Betweenness 실행 증명 |
| cs_41_graph_api | A | `api/views.py:59` (ChainSightGraphView), `api/urls.py:39` | center/nodes/edges/meta, SUPPLIES_TO→CUSTOMER_OF 역파생 |
| cs_42_suggestion_api | B | `api/views.py:117` (4 카테고리) | **community_id 클러스터 추천 미구현** |
| cs_43_trace_api | B | `api/views.py:219` (shortestPath) | **alternative_paths 미구현** (단일 경로만) |

### CS-5 — 프론트엔드 v2 원안 (전건 A, 단 마켓뷰 대체)

| 문서 | 판정 | 근거 코드 | 비고 |
|------|:---:|------|------|
| cs_5_frontend_design_v2 | A | `app/chainsight/[symbol]/page.tsx` (3-panel), 11개 컴포넌트 전건 | 단 **마켓뷰 루트 화면은 redesign 대체** |
| cs_51_graph_visualization | A | `components/chainsight/GraphCanvas.tsx`, `graphStyles.ts`, `RelationLegend.tsx` | ForceGraph2D + Spotlight + lazy expansion |
| cs_52_ai_guide_ui | A | `components/chainsight/AIGuidePanel.tsx` | 카테고리 카드 + strength 라벨 |
| cs_53_chain_trace_ui | A | `components/chainsight/TracePathView.tsx`, `FullPathView.tsx` | 경로 시각화 + 단계 설명 |
| cs_54_stock_detail_integration | A | `components/chainsight/GraphMiniView.tsx`, `app/stocks/[symbol]` chain-sight 탭 | 미니뷰 + "전체 탐색" CTA |

### redesign_v1_260409 — PR-1~7 (전건 A)

| PR | 판정 | 근거 코드 |
|----|:---:|------|
| PR-1 스키마 마이그레이션 | A | `models/relation_discovery.py:139` (previous_status/neo4j_dirty/synced_at + save() override), `migrations/0005` |
| PR-2 시드 선정 Task | A | `services/seed_selection.py` (5 시드 소스), `tasks/seed_tasks.py:28` (run_seed_selection), `migrations/0006~0008` |
| PR-3 Neo4j Dirty Sync | A | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py`, `migrations/0008_unify_neo4j_flags` |
| PR-4 마켓 뷰 API 4종 | A | `api/views.py` SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView, `api/urls.py:20-45` |
| PR-5 FE 상태+섹터바+그래프 | A | `lib/stores/explorationStore.ts`, `hooks/useMarketView.ts`, `components/chainsight/{SectorBar,MarketGraphCanvas}.tsx` |
| PR-6 트레일+관계카드 | A | `components/chainsight/{ExplorationTrail,RelationCardPanel}.tsx` |
| PR-7 체인 스토리 피드 | A | `components/chainsight/ChainStoryFeed.tsx` (글로벌 chain flow + 무한 스크롤) |

### 추가 완료 항목 (remaining_work_plan 후속)

| 항목 | 판정 | 근거 |
|------|:---:|------|
| DC-2 ETF Holdings→Theme | A | `management/commands/load_themes_to_neo4j.py`, Neo4j :Theme 21 + HAS_THEME |
| Celery Beat 일괄 등록 | A | `management/commands/register_chainsight_beats.py` (구 `config/celery.py` 11 task) |
| EventBoard/Attention/Leadership (RD3 후속) | A* | `models/{attention,leadership,event_reaction}.py`, `services/{attention,leadership_compute}.py`, `api/event_views.py`, `app/chainsight/events/` — **설계서 plan/ 에 문서 없음**(코드 선행) |

---

## 미구현 항목 상세

설계서 기준 **완전 미구현(C)은 0건**. 아래는 **부분 구현(B)** 의 누락분.

### 1. cs_24 / relation_confidence_design_v1 — 관계 신뢰도 엔진 정책 단순화 (B, 최우선)

모델 스키마 v2.1은 ~90% 구현됐으나, 설계서의 **정교한 Tier 기반 증거 판정 로직**이 MVP 수준으로 단순화됨.

- **관계 타입 커버리지 부족**: 현재 `PEER_OF` / `CO_MENTIONED` / `PRICE_CORRELATED` 3종만 판정. 설계의 `SUPPLIES_TO`, `COMPETES_WITH`, `HAS_THEME`, `BELONGS_TO_*` 미처리.
- **Tier 1/2/3 증거 분류 미구현**: 현재 단순 count/correlation 기준. 설계의 증거 독립성·family 분류·provenance 기반 Tier 판정 없음.
- **has_*_source 7개 boolean 필드**: 선언만 존재, 실제 집계 로직은 2~3개 관계 타입만 채움 (`has_supply_chain_source`, `has_etf_source`, `has_llm_source` 계산 전무).
- **normalize_pair 강제 미적용**: 유틸(`utils.py:28`)은 존재하나 `RelationConfidence.save()` 레벨에서 undirected 사전순 정규화 강제 없음 → 중복 위험.
- **truth_score 타입/값 편차**: 설계 IntegerField(85/60/35/15) ↔ 구현 FloatField default=0.
- **Stale 하향 임계값 차이**: 설계(confirmed→stale 180일 / probable→weak 270일 / weak→hidden 360일, 타입별 차등) ↔ 구현(90/60/30일, 사실상 단순화).
- **relation_basis_summary / CUSTOMER_OF 역파생 / score_version 관리**: 템플릿·역방향 파생·버전 로직 미발견.

> **영향**: 최소기능(MVP)은 동작하나, 설계의 정책표 미적용 → Phase 3 Neo4j 동기화 시 신뢰도 품질 확산 위험. → `relation_confidence_design_v1.md` §3·6·10 재참조 권장.

### 2. cs_42 Suggestion API — community 클러스터 추천 미구현 (B)

- 구현된 4 카테고리: `peers` / `same_industry` / `co_mentioned` / `same_sector` (`api/views.py:117-216`).
- **누락**: 설계서가 명시한 `community_id`(Louvain 결과) 기반 클러스터 추천 카테고리. GDS community 속성은 노드에 존재하나 Suggestion API에서 미활용.

### 3. cs_43 Trace API — alternative_paths 미구현 (B)

- 구현: `shortestPath` Cypher 단일 경로 (`api/views.py:219`, LIMIT 1).
- **누락**: 설계서 `alternative_paths: 2` — 대체 경로 N개 반환 로직 없음.

### 4. 설계 대비 명명/구조 편차 (개선성, 결함 아님)

| 항목 | 설계 | 구현 | 성격 |
|------|------|------|------|
| 동기화 플래그 | `neo4j_synced` (bool) | `neo4j_dirty` (의미 반전, dirty 마킹 패턴) | 개선 |
| 관계 엣지 타입 | 고정 `RELATED_TO` | 동적 `relation_type` | 개선 |
| API 경로 | `/api/stocks/{symbol}/...` | `/api/v1/chainsight/{symbol}/...` | 변경 |
| 백엔드 앱 경로 | `chainsight/` | `apps/chain_sight/` (monorepo) | 변경 |

---

## 폐기/대체 항목

### redesign_v1_260409 ↔ 기존 cs_* 관계: **부분 대체 (마켓 뷰 한정)**

`redesign_v1_260409/`는 **기존 cs_* 전체를 폐기하지 않는다.** 마켓 뷰(`/chainsight` 루트) UI/UX·API만 대체하고, Deep-dive 워크스페이스와 백엔드 파이프라인은 **공존·계승**한다.

**대체됨 (D)**:

| 폐기/대체된 설계 | 대체물 | 근거 |
|------|------|------|
| cs_5_frontend_design_v2 의 **마켓 뷰 3-panel "전용 워크스페이스 런처"** 패러다임 | `redesign_v1/chainsight_ui_ux_design.md` 의 **5-컴포넌트 "완결된 탐색 허브"** (SectorBar→Graph→Trail→RelationCard→ChainStoryFeed) | `app/chainsight/market-graph/page.tsx`가 5개 컴포넌트를 설계 순서대로 렌더 |
| cs_51 graph_visualization (마켓 뷰 부분) | `chainsight_ui_ux_design.md` 마켓뷰 구조 | MarketGraphCanvas로 재구현 |
| (기존 마켓 뷰용 API 부재) | `redesign_v1/chainsight_api_design.md` 4종 신규 API | seeds/ · sector/{}/graph/ · {symbol}/neighbors/ · signals/ |
| 시드 선정 임시 체계 | `redesign_v1/chainsight_seed_node_design.md` 5-소스 시드 | `services/seed_selection.py` |

**계승·공존 (대체 아님)**:

- **Deep-dive API** cs_41/42/43 (`ChainSightGraphView`/`SuggestionView`/`TraceView`) → 코드 계속 존재·동작.
- **Deep-dive 워크스페이스** cs_5_v2의 `/chainsight/[symbol]` → 컴포넌트 전건 구현 유지.
- **백엔드 파이프라인** CS-0~CS-4 전체 → redesign이 건드리지 않음 (PR-1~3은 기존 RelationConfidence·sync를 확장).

### RD3 라우팅 역전 (2026-06-18, 최신)

redesign_v1 완료 후 추가로 **RD3(2026-06-18, git `c5b5ce6` "CS-RD3 라우팅 역전")** 가 화면 우선순위를 재배열:

- `/chainsight` 루트 → **EventBoard**(이벤트 보드) 우선 (`app/chainsight/page.tsx` 주석 "RD3 첫 화면 정보 구조 역전")
- `/chainsight/market-graph` → 섹터 그래프(redesign 5-컴포넌트)로 **강등**
- `/chainsight/events`, `/chainsight/events/[theme]`, `/chainsight/watchlist` → 신규
- **EventBoard·Attention·Leadership** 백엔드(`models/{attention,leadership,event_reaction}.py`, `api/event_views.py`)는 **`plan/`에 설계 문서 없이 코드가 선행**된 영역 → 설계서-갭이 아니라 **문서화 부채**(코드 ⊃ 설계).

> **결론**: 설계 방향 변경은 **마켓 뷰 화면 패러다임 1건(D)** 뿐. 나머지는 모두 구현 완료 또는 정책 단순화(B). cs_5_v2·cs_51~54 의 컴포넌트 자산은 폐기되지 않고 전부 보존됨.

---

## 부록 — 감사 메모

- **본 보고서는 코드 존재·시그니처·경로 대조 기반**이며, 런타임 동작·데이터 정합성까지 검증하지 않음(읽기 전용).
- **문서화 부채 발견**: RD3 산출물(EventBoard/Attention/Leadership/Watchlist)은 코드가 `plan/` 설계서를 앞섬 → 역방향 문서화 권장.
- **수치(노드/관계 건수)** 는 task_done 보고서 기록값 인용이며 현재 DB 재확인 미수행.
- **최우선 후속 권장 1건**: cs_24 관계 신뢰도 엔진을 `relation_confidence_design_v1` 설계 수준으로 보강(Tier 증거 판정 + 6개 관계 타입 확장 + save() 정규화 강제).
