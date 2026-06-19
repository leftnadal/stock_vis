# Chain Sight 설계 갭 감사

> **감사일**: 2026-06-19 (야간 자동화)
> **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis`
> **감사 방식**: 읽기 전용. 설계 문서(`docs/chain_sight/plan/`) ↔ 코드(`apps/chain_sight/`, `frontend/.../chainsight/`) ↔ 완료 보고서(`docs/chain_sight/task_done/`) 3중 대조
> **코드 수정 없음** — 감사 보고서만 작성

---

## ⚠️ 전제: 경로 이전 (monorepo 개편)

모든 설계 문서와 task_done 보고서는 구 경로 `chainsight/`를 언급하지만, 실제 백엔드 코드는 **monorepo 개편으로 `apps/chain_sight/`로 이동**했다. 본 감사는 `apps/chain_sight/`를 진실의 소스로 삼는다. (프론트엔드는 `frontend/components/chainsight/`, `frontend/app/chainsight/` 유지.)

문서가 가리키는 `chainsight/services/...` → 실제 `apps/chain_sight/services/...`로 읽으면 됨. 이 drift 자체는 문서 정리 부채(코드 영향 없음).

---

## 요약 (구현률)

| 단계 | 영역 | 구현률 | 종합 판정 |
|------|------|--------|-----------|
| **Phase 0** | 인프라 (레거시정리·마이그레이션·Neo4j연결·스키마) | ~94% | A (경미 갭 2건) |
| **Phase 1** | 시드 로드 (Stock·Sector·Industry·Peer) | ~100% | A |
| **Phase 2** | 프로파일·관계 파이프라인 | ~75% | B (CS-2-4 핵심 갭) |
| **Phase 3** | Neo4j 동기화 + GDS | ~67% | B (GDS 미구현) |
| **Phase 4** | REST API (graph/suggestion/trace) | ~85% | A/B (공존, 일부 부분) |
| **Phase 5 v1** | 프론트엔드 초안 (cs_51~54) | — | **D (폐기·대체)** |
| **Phase 5 v2** | 프론트엔드 정식 (cs_5_v2) | ~98% | A |
| **Redesign V1** | 마켓 뷰 (redesign_v1_260409) | ~95% | A |
| (인접) | SEC Pipeline | 별도 앱 구현 | A (범위 외) |

**전체 평가**: Chain Sight는 인프라·데이터·API·프론트엔드 전 계층이 **운영 가능한 수준으로 구현**되어 있다. 다만 두 가지 **실질적 갭**이 있다:

1. **🔴 CS-2-4 RelationConfidence** — 928줄 설계서(`relation_confidence_design_v1.md`)의 Tier 체계·confirmed 판정 규칙이 코드에서 대폭 단순화·위반됨. **데이터 신뢰성에 직접 영향**.
2. **🟠 CS-3-3 GDS** — PageRank/Louvain/Betweenness 자동 실행 코드 부재. 수동 1회 실행 결과만 task_done에 기록됨. 재배포 시 점수 재생성 불가, suggestion `community` 카테고리 미작동의 근원.

그 외 미구현 항목은 대부분 설계 단계에서 명시적으로 "Future/Out-of-Scope"로 표기된 것들이다.

---

## 설계 세대 관계 (프론트엔드)

프론트엔드 설계는 3세대로 진화했고, 세대 간 관계 파악이 중요하다.

```
v1 (cs_51~54, 2026-04 초)           v2 (cs_5_frontend_design_v2, 04-04)
─ cs_51 graph_visualization   ──┐    ─ /chainsight/[symbol] 3-panel 워크스페이스
─ cs_52 ai_guide_ui           ──┼──▶ ─ 관계 2색→6색, 모바일 카드리스트 정책
─ cs_53 chain_trace_ui        ──┤    ─ 프로 필터/CTA 5종
─ cs_54 stock_detail_integ.   ──┘    → v1 컴포넌트 전부 v2로 흡수 (D)
                                              │
                                              ▼
                            Redesign V1 (redesign_v1_260409, 04-09~)
                            ─ /chainsight, /chainsight/market-graph 마켓 허브
                            ─ SectorBar/MarketGraphCanvas/ExplorationTrail/
                              RelationCardPanel/ChainStoryFeed (5종)
                            ─ + EventBoard (CS-RD2) → 현재 메인 페이지

현재(2026-06): v2(Deep Dive, /[symbol]) + v3(Market Hub, /market-graph, /events) **공존**
```

**결론**: v1(cs_51~54)은 v2가 완전히 대체했고(기능은 100% 흡수), v2와 v3는 서로 다른 화면으로 **병렬 유지** 중. redesign_v1_260409는 v2를 대체한 것이 아니라 **새 진입점(마켓 허브)을 추가**한 것.

---

## 백엔드 API 라우팅 실측 (`apps/chain_sight/api/urls.py`)

> ⚠️ 교정: 일부 조사에서 "기존 API가 redesign API로 대체됨"으로 본 것은 **부정확**. 실측 결과 **모두 공존**한다.

| 엔드포인트 | View | 설계 출처 | 상태 |
|-----------|------|-----------|------|
| `GET events/` | EventBoardView | CS-RD2 (redesign 후속) | ✅ 활성 |
| `GET events/<theme>/stocks/` | EventRankingView | CS-RD2 | ✅ 활성 |
| `GET seeds/` | SeedListView | redesign V1 | ✅ 활성 |
| `GET sector/<sector>/graph/` | SectorGraphView | redesign V1 | ✅ 활성 |
| `GET signals/` | SignalFeedView | redesign V1 | ✅ 활성 |
| `GET trace/` | ChainSightTraceView | **cs_43** | ✅ 활성 |
| `GET <symbol>/neighbors/` | NeighborGraphView | redesign V1 | ✅ 활성 |
| `GET <symbol>/graph/` | ChainSightGraphView | **cs_41** | ✅ 활성 |
| `GET <symbol>/suggestions/` | ChainSightSuggestionView | **cs_42** | ✅ 활성(부분) |
| `watchlist/*` | WatchlistViewSet | redesign 후속 | ✅ 활성 |

→ cs_41/42/43의 원 설계 API는 폐기되지 않았다. redesign 4종 API와 함께 라우팅되어 있다.

---

## 문서별 상태 테이블

### Phase 0 — 인프라

| 문서 | 판정 | 근거 |
|------|------|------|
| cs_00 legacy_cleanup_api_test | **B** | 레거시 정리·RelationConfidence 마이그레이션 완료. 단 설계가 요구한 `docs/chain_sight/decisions/003_api_access_test.md` 결정 문서 **부재** (task_done 내부 표로만 존재) |
| cs_01 migrations_verification | **A** | 12개 테이블·RelationConfidence 29필드·`normalize_pair` 확인 (`migrations/0001_initial.py`) |
| cs_02 neo4j_connection | **B** | `get_graph_repository()` 팩토리 + PID 기반 fork 안전 구현. 단 `GraphRepository` Protocol에 `bulk_upsert_nodes/edges`, `health_check`, `node_count`, `edge_count` 5개 메서드 **누락** (구현체엔 존재, `graph/repository.py:12-32`) |
| cs_03 neo4j_schema | **A** | 4 constraints + 2 indexes (`graph/schema.py`). task_done의 "4 indexes" 표기는 오기 — 코드가 설계(2개)를 올바르게 따름 |

### Phase 1 — 시드 로드

| 문서 | 판정 | 근거 |
|------|------|------|
| cs_11 stock_node_bulk_load | **A** | `load_stocks_to_neo4j.py` + `neo4j_loader.py` |
| cs_12 sector_industry | **A** | `load_sectors_to_neo4j.py` + BELONGS_TO 관계 |
| cs_13 peer_relations | **A** | `load_peers_to_neo4j.py` + `normalize_pair` undirected 정규화 |

### Phase 2 — 프로파일·관계 파이프라인

| 문서 | 판정 | 근거 |
|------|------|------|
| cs_21 tier_a_profile | **A** | GrowthStage(`models/growth_stage.py`) + CapitalDNA(`models/capital_dna.py`) 필드 100% 매칭 |
| cs_21b sensitivity_profile | **B** | 모델·FMP geo-segmentation 구현(`models/sensitivity.py`, `tasks/sensitivity_tasks.py`). **revenue-product-segmentation 미사용** |
| cs_21c insider_signal | **B** | Finnhub Insider 구현(`tasks/insider_tasks.py`). **institutional_ownership·short_interest 원천 미확보 → None 처리** → bullish 0건 결과 왜곡 |
| cs_22 co_mention | **A** | ChainNewsEvent + `extract_co_mentions`(`tasks/relation_tasks.py`) |
| cs_23 price_co_movement | **A** | `calculate_price_co_movement` 90일 rolling correlation |
| cs_24 relation_confidence | **C/D** | 🔴 **핵심 갭** — 아래 상세 |
| cs_25 chain_profile_aggregation | **B** | chain_profile 모델·집계 구현. 단 설계가 요구한 8종 정기 Beat 미완 (아래 Beat 섹션) |
| relation_confidence_design_v1 (928줄) | **D** | 🔴 코드가 설계 정책의 ~1/10 규모로 단순화·규칙 위반 (아래 상세) |

### Phase 3 — Neo4j 동기화 + GDS

| 문서 | 판정 | 근거 |
|------|------|------|
| cs_31 profile_neo4j_sync | **A** | `sync_profiles_to_neo4j`(`tasks/sync_tasks.py`). 설계의 `neo4j_synced` → 실제 `neo4j_dirty` 플래그(의도적 반전, audit P0 #9) |
| cs_32 relation_neo4j_sync | **A** | `sync_dirty_relations`(`services/neo4j_sync.py`). RELATED_TO 고정 → relation_type 동적 엣지로 진화 |
| cs_33 gds_algorithms | **C** | 🟠 **GDS 실행 코드 부재** — `gds.*.write` 0건. `path_service.py`는 점수를 **읽기**만 함. task_done은 수동 1회 실행 결과만 기록 |

### Phase 4 — REST API

| 문서 | 판정 | 근거 |
|------|------|------|
| cs_41 graph_api | **A** | ChainSightGraphView 활성(`api/views.py`). depth·market_signals·CUSTOMER_OF 역파생 |
| cs_42 suggestion_api | **B** | ChainSightSuggestionView 활성. **4/6 카테고리만**: peers·same_industry·co_mentioned·same_sector ✅ / supply_chain·community ❌ (community는 GDS 미구현이 근원) |
| cs_43 trace_api | **A** | ChainSightTraceView `shortestPath` Cypher 완전 구현 |

### Phase 5 v1 — 프론트엔드 초안

| 문서 | 판정 | 근거 |
|------|------|------|
| cs_51 graph_visualization | **D** | GraphCanvas.tsx로 흡수·확장(ForceGraph2D). 단순 "GraphView.tsx" 구조는 v2 3-panel로 대체 |
| cs_52 ai_guide_ui | **D→A** | AIGuidePanel.tsx + CategoryCard로 완전 이행. strength dots→텍스트는 v2 리뷰 개선 |
| cs_53 chain_trace_ui | **D→A** | TracePathView.tsx로 완전 이행 |
| cs_54 stock_detail_integration | **D→A** | GraphMiniView.tsx + `/chainsight/[symbol]` 전용 페이지로 완전 이행 |

> v1 4종 문서는 "설계 문서로서는 폐기(D)"이나 **기능은 v2에 100% 흡수**됨.

### Phase 5 v2 — 프론트엔드 정식

| 문서 | 판정 | 근거 |
|------|------|------|
| cs_5_frontend_design_v2 (409줄) | **A** | MVP 100% 구현. 3-panel 레이아웃·6색 엣지·관계 필터·모바일 카드리스트·CTA 5종 모두 동작. **미구현: PER 히트맵 오버레이, 노드 비교 모드**(§6, v2.1 예약) |

### Redesign V1 — 마켓 뷰

| 문서 | 판정 | 근거 |
|------|------|------|
| redesign_v1_260409/chainsight_seed_node_design | **B** | Phase 1 시드 선정 완전 구현(`services/seed_selection.py`). Heat Score 후속 구현. **Phase 3 이벤트 전파 미구현** |
| redesign_v1_260409/chainsight_api_design | **A** | 4종 API(seeds/sector/neighbors/signals) 라우팅·캐싱·스키마 일치 |
| redesign_v1_260409/chainsight_ui_ux_design | **A** | 마켓뷰 5종 컴포넌트 완전 구현 + `?focus=` 딥링크 |
| redesign_v1_260409/chainsight_marketview_pr_prompts | **A** | PR-1~7 의존성 그래프 순서대로 완료 (task_done 교차검증 일치) |

### 인접 (Chain Sight 본체 아님)

| 문서 | 판정 | 근거 |
|------|------|------|
| chain_sight_roadmap_v1.3 (907줄) | **A(부분)** | 마스터 로드맵. 하위 cs_* 문서로 세분 추적됨. GDS·CS-2-4 정책만 미달 |
| sec_pipeline_base_design / sec_pipeline_pr_detail | **A(별도앱)** | `sec_pipeline/` top-level 앱으로 구현. CLAUDE.md SEC Pipeline 완료 표기. Chain Sight 본체 범위 밖 |
| remaining_work_plan (2026-04-04) | 갱신 필요 | redesign 이전 작성. 당시 "남은 작업"(Sensitivity/Insider/Beat/ETF/FE) 대부분 완료됨 |

---

## 미구현 항목 상세

### 🔴 1. CS-2-4 RelationConfidence — 설계 정책 대폭 단순화·위반 (최우선)

`relation_confidence_design_v1.md`(928줄)는 Tier 체계와 엄격한 confirmed 판정 규칙을 정의하나, `tasks/relation_tasks.py:274-402`의 구현은 이를 따르지 않는다.

**설계 규칙 vs 코드:**

| 설계 규칙 | 코드 실제 | 위반 |
|-----------|-----------|------|
| same_industry는 Tier 2(보강만), 단독 probable 불가 | `has_industry`를 Tier 1처럼 취급, peer+industry=confirmed | 🔴 |
| CO_MENTIONED는 confirmed 불가 (max probable) | `count>=10` → `status="confirmed"` | 🔴 |
| PRICE_CORRELATED는 confirmed 불가 (Market 관계) | `corr>=0.8` → `status="confirmed"` | 🔴 |
| Market 관계 `truth_score = None` | `truth_score = 0` 할당 (모델도 `FloatField(default=0)`, nullable 아님) | 🟡 |
| `evidence_sources`: list of `{source_type, tier, raw_value}` | `dict {"sources": [...], "count": ...}` (모델 `default=dict`) | 🟡 |
| source_type(fmp_peer/finnhub_peer/manual_seed) 구분 | Neo4j 관계 존재 여부만 확인, source 미구분 | 🔴 |

**영향**: confirmed/probable 등급이 설계 의도보다 관대하게 부여됨. 특히 Market 신호(주가상관·동시언급)에 confirmed가 붙어 **Truth 관계와 Market 관계의 구분이 무너짐**(설계 원칙 5 위반). 추천·신뢰도 표시의 데이터 품질에 직접 영향.

**권고**: 설계서를 현 구현 수준으로 다운그레이드하든지, 코드를 Tier 규칙대로 수정하든지 **둘 중 하나로 정합화** 결정 필요. 현재는 "설계는 엄격, 코드는 관대"로 drift.

### 🟠 2. CS-3-3 GDS 알고리즘 — 자동 실행 부재

- `gds.pageRank.write` / `gds.louvain.write` / `gds.betweenness.write` 호출 **0건** (`apps/chain_sight` grep 전수).
- `services/path_service.py`는 `pagerank_score`·`betweenness_score`를 **읽기만** 함 → 노드에 속성이 있어야 작동.
- task_done(CS-3-3)은 Top 5 결과를 기록 → **Neo4j Browser/cypher-shell 수동 1회 실행** 추정. 배치 태스크(`gds_tasks.py`)·Beat 등록 없음.
- **파급**: ① Neo4j 재배포/엣지 증분 시 점수 stale, ② cs_42 suggestion `community` 카테고리 미작동, ③ "M3 달성" task_done 주장과 자동화 부재 불일치.

### 🟡 3. Celery Beat — 정기 파이프라인 등록 불완전

`management/commands/register_chainsight_beats.py`는 **attention-daily·leadership-daily 2개만** 등록한다.

- redesign 분: `chainsight-seed-selection`(매일 13:00 UTC), `chainsight-neo4j-dirty-sync`(주1 일 04:30) — 별도 등록(00_summary 확인).
- **cs_25가 요구한 8종 파이프라인 Beat**(co-mention-daily, profiles-weekly, price-comovement-weekly, relation-confidence-weekly, stale-decay-weekly, chain-profile-weekly, sync-profiles-weekly, sync-relations-weekly)는 register 커맨드에 **없음**. 태스크 자체는 `@shared_task`로 정의되어 수동/별도 트리거 가능하나 **정기 스케줄 등록 여부 불확실** → 데이터 신선도 운영 리스크. (config의 DB 등록 상태 별도 확인 권장.)

### 🟡 4. CS-2-1c InsiderSignal — 데이터 원천 미확보

institutional_ownership_pct·short_interest_pct를 받는 API 미연동(`insider_tasks.py`에서 `None` 전달). smart_money 종합 계산이 insider transaction 단독으로만 작동 → task_done에서 bullish 0건 / bearish 276건으로 결과 편향.

### 🟡 5. cs_5_v2 프로 기능 2종 (명시적 예약)

PER 히트맵 오버레이, 노드 비교 모드(Ctrl+Click) — 설계 §6에 있으나 미구현. v2.1 예약으로 명시되어 의도적.

### 경미 (문서/타입 품질)

- cs_00: `decisions/003_api_access_test.md` 결정 문서 부재.
- cs_02: `GraphRepository` Protocol 메서드 5개 누락(구현체엔 존재) → 타입 체킹·백엔드 교체성만 영향.
- 문서 경로 drift: 전 설계/task_done 문서가 `chainsight/` 표기(실제 `apps/chain_sight/`).

---

## 폐기/대체 항목

| 항목 | 처리 | 대체/현황 |
|------|------|-----------|
| **cs_51~54 (FE v1)** | 폐기 → v2 흡수 | cs_5_frontend_design_v2가 4종 문서를 통합. 기능은 100% 이행, 문서는 아카이빙 권장 |
| **관계 2색 체계** (confirmed/probable) | 폐기 → 6색 | SUPPLIES_TO/CUSTOMER_OF/COMPETES_WITH/PEER_OF/CO_MENTIONED/HAS_THEME 타입별 색상 (v2) |
| **strength dots (●●●)** | 폐기 → 텍스트 | 강함/보통/약함 라벨 (v2 리뷰 반영) |
| **RELATED_TO 고정 엣지** | 폐기 → 동적 타입 | `relation_type` 다형성 엣지 (`neo4j_sync.py`) |
| **`neo4j_synced` 플래그** | 폐기 → `neo4j_dirty` | 의미 반전 (audit P0 #9, 의도적). 단 설계 문서 미반영 |
| **`relation_confidence_design_v1` 정책표** | 사실상 폐기(미정합) | 코드가 설계의 ~1/10로 단순화. **공식 폐기 결정 없이 drift** → 정합화 결정 필요 |
| **remaining_work_plan (04-04)** | 만료 | 명시된 남은작업 대부분 완료. redesign 이후 갱신 안 됨 |

---

## 후속 권고 (우선순위)

1. **🔴 CS-2-4 정합화 결정** — 설계서를 구현 수준으로 내릴지, 코드를 Tier 규칙대로 올릴지 명문화. 현 drift는 데이터 신뢰성 표기에 직접 영향.
2. **🟠 GDS 자동화** — `gds_tasks.py` + Beat 등록으로 PageRank/Louvain/Betweenness 재실행 자동화. → suggestion `community` 카테고리 복구.
3. **🟡 cs_25 파이프라인 Beat 등록 검증** — 8종 정기 태스크의 실제 DB 스케줄 등록 상태 확인·보강.
4. **🟡 InsiderSignal 원천 보강** — institutional/short interest API 연동 또는 설계에서 해당 필드 제거.
5. **문서 정리** — cs_51~54 아카이빙, 경로 drift(`chainsight/`→`apps/chain_sight/`) 일괄 정정, remaining_work_plan 폐기 표기, task_done 오기(CS-0-3 index 개수) 수정.

---

> 본 보고서는 읽기 전용 감사 산출물이며 코드/문서를 일절 변경하지 않았다. 판정 근거는 모두 `apps/chain_sight/`·`frontend/.../chainsight/` 실제 코드 및 `docs/chain_sight/` 문서 대조에 기반한다.
