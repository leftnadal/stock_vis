# Chain Sight 설계 갭 감사

> **감사일**: 2026-06-01
> **대상**: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` + `frontend/**/chainsight/` 구현
> **유형**: 읽기 전용 감사 (코드 미수정)
> **코드 위치 주의**: monorepo 마이그레이션으로 `chainsight/` → `apps/chain_sight/` 이동됨 (설계 문서의 경로 표기는 구버전)

---

## 요약 (구현률)

| 영역 | 분류 | 구현률 | 비고 |
|------|------|--------|------|
| **Phase 0 인프라** (CS-0) | A 완전 | 100% | Neo4j 드라이버(PID-safe), schema 4 제약+인덱스, 레거시 정리 |
| **Phase 1 시드 로드** (CS-1) | A 완전 | 100% | load_stocks/sectors/peers 커맨드 존재 |
| **Phase 2 파생 파이프라인** (CS-2) | A 완전 | 100% | GrowthStage/CapitalDNA/Sensitivity/Insider/CoMention/PriceCoMove/RelationConfidence/ChainProfile 전부 task 구현 |
| **Phase 3 Neo4j Sync** (CS-3-1/3-2) | A 완전 | 100% | dirty-flag delta sync |
| **Phase 3 GDS** (CS-3-3) | **C 미구현** | 0% | ⚠️ **재현 가능 task 부재** — 점수는 읽기만, 계산 코드 없음 |
| **Phase 4 API** (CS-4) | A 완전 | 100% | graph/suggestions/trace 3종 |
| **redesign 마켓뷰 API** (PR-4) | A 완전 | 100% | seeds/sector graph/neighbors/signals 4종 |
| **redesign 마켓뷰 FE** (PR-5~7) | A 완전 | 100% | 5개 컴포넌트 + store + hooks |
| **Phase 5 Deep dive FE** (CS-5) | A 완전 | 100% | GraphCanvas/AIGuide/Trace/Mini/Mobile |
| **redesign 시드 Phase 2 Heat Score** | **B 부분** | ~60% | task 4/6 신호원, **SeedHeatScore 모델 부재** |
| **redesign 시드 Phase 3 이벤트 전파** | **C 미구현** | 0% | text_conditional_prob/lagged corr/propagation 전무 |
| **RelationConfidence v2.1 스키마** | A 완전 | 100% | 22개 핵심 필드 전부 존재 |

**종합 구현률(가중 추정): 핵심 MVP(Phase 0~5 + 마켓뷰) ≈ 95% 완성. 고도화(GDS 재현 task, Heat Score Phase 2, 이벤트 전파 Phase 3) 미완.**

### redesign_v1_260409 ↔ 기존 cs_* 의 관계 (핵심 결론)

> **redesign_v1_260409/ 는 기존 cs_* 를 "전면 대체"가 아니라 "방향 전환 + 분화"한다.**

- **백엔드 파이프라인(cs_01~cs_33)**: 그대로 유효. redesign이 건드리지 않음. RelationConfidence v2.1, Tier A/B 계산, Neo4j sync는 cs_* 설계대로 구현됨.
- **API**: 기존 cs_41~43(graph/suggestions/trace)은 **"Deep dive workspace 전용"으로 강등**되어 유지. redesign이 마켓뷰 4종(seeds/sector/neighbors/signals)을 **신규 추가**. 두 세트 모두 코드에 공존.
- **프론트엔드(cs_51~54)**: redesign이 **사실상 대체**. 단일 화면 설계(cs_5_frontend_design_v2)가 "마켓뷰(`/chainsight`) + Deep dive(`/chainsight/[symbol]`)" 2워크스페이스로 재설계됨. 원안 컴포넌트는 Deep dive 측에 흡수되어 잔존(GraphCanvas, AIGuidePanel, TracePathView, GraphMiniView).
- **시드노드 Phase 2/3(Heat Score, 이벤트 전파)**: redesign이 신규 정의했으나 **미구현**(범위 밖으로 명시 후 미착수).

---

## 문서별 상태 테이블

### A. 백엔드 파이프라인 설계 (cs_01 ~ cs_33)

| 설계 문서 | 산출물 | 실제 구현 | 분류 | 근거 |
|-----------|--------|-----------|------|------|
| cs_01 migrations | 12 테이블 | `migrations/0001~0008` | A | 8개 마이그레이션, 12+ 모델 |
| cs_02 neo4j connection | repository.py | `graph/repository.py` (PID-safe driver) | A | repository.py:192L |
| cs_03 neo4j schema | schema.py + command | `graph/schema.py` + `init_neo4j_schema` | A | 4 제약 + community 인덱스 |
| cs_11 stock 노드 로드 | load command | `commands/load_stocks_to_neo4j.py` | A | — |
| cs_12 sector/industry | load command | `commands/load_sectors_to_neo4j.py` | A | — |
| cs_13 peer 관계 | fetch task | `tasks/peer_tasks.py` | A | — |
| cs_21 Tier A 프로파일 | GrowthStage/CapitalDNA | `tasks/profile_tasks.py` | A | calculate_growth_stages/capital_dna |
| cs_21b Sensitivity | sensitivity task | `tasks/sensitivity_tasks.py:calculate_sensitivity_profiles` | A | FMP Geo+BS+beta |
| cs_21c Insider | insider task | `tasks/insider_tasks.py:calculate_insider_signals` | A | Finnhub 90일 집계 |
| cs_22 CoMention | extract task | `tasks/relation_tasks.py:extract_co_mentions` | A | NewsEntity 동시출현 |
| cs_23 PriceCoMovement | rolling corr task | `tasks/relation_tasks.py:calculate_price_co_movement` | A | 90일 rolling, \|r\|≥0.5 |
| cs_24 RelationConfidence | 종합 판정 task | `tasks/relation_tasks.py:update_relation_confidence` + `check_stale_and_decay` | A | truth_score, 5단계 상태 |
| cs_25 ChainProfile 집약 | aggregate task | `tasks/sync_tasks.py:aggregate_chain_profiles` | A | — |
| cs_31 profile→neo4j | sync task | `tasks/sync_tasks.py:sync_profiles_to_neo4j` | A | dirty delta sync |
| cs_32 relation→neo4j | sync task | `tasks/sync_tasks.py` + `services/neo4j_sync.py:sync_dirty_relations` | A | confirmed/probable 우선 |
| **cs_33 GDS 알고리즘** | **run_gds_algorithms task** | **❌ 없음** | **C** | gds_tasks.py 부재, gds.write 호출 0건 |

### B. API 설계

| 설계 | 엔드포인트 | 실제 View | 분류 |
|------|-----------|-----------|------|
| cs_41 graph API | `/{symbol}/graph/` | `ChainSightGraphView` | A |
| cs_42 suggestion API | `/{symbol}/suggestions/` | `ChainSightSuggestionView` | A |
| cs_43 trace API | `/trace/` | `ChainSightTraceView` | A |
| redesign /seeds/ | `/seeds/` | `SeedListView` (3단 폴백) | A |
| redesign /sector graph/ | `/sector/{sector}/graph/` | `SectorGraphView` | A |
| redesign /neighbors/ | `/{symbol}/neighbors/` | `NeighborGraphView` | A |
| redesign /signals/ | `/signals/` | `SignalFeedView` | A |

> 모두 `apps/chain_sight/api/{urls,views}.py`에 등록·구현. CUSTOMER_OF는 DB 저장 없이 view에서 파생(`_display_type`/`derived_type`) — 설계(v1.3) 준수.

### C. 프론트엔드 설계

| 설계 | 실제 파일 | 분류 | 비고 |
|------|-----------|------|------|
| redesign ① SectorBar | `components/chainsight/SectorBar.tsx` | A | PR-5 |
| redesign ② MarketGraphCanvas | `MarketGraphCanvas.tsx` | A | PR-5, EDGE_COLORS 6색 일치 |
| redesign ③ ExplorationTrail | `ExplorationTrail.tsx` | A | PR-6, undo |
| redesign ④ RelationCardPanel | `RelationCardPanel.tsx` | A | PR-6, pre-focus/focused 분기 |
| redesign ⑤ ChainStoryFeed | `ChainStoryFeed.tsx` | A | PR-7, 무한스크롤 |
| redesign 공유상태 | `lib/stores/explorationStore.ts` | A | Zustand 7상태 |
| redesign 훅 4종 | `hooks/useMarketView.ts` | A | seed/sector/neighbor/signal |
| cs_51 GraphView | `GraphCanvas.tsx`(Deep dive) | **D 대체** | 마켓뷰/Deep dive로 분화 |
| cs_52 SuggestionCards | `AIGuidePanel.tsx`(Deep dive) | **D 대체** | 역할 재정의 |
| cs_53 TraceView | `TracePathView.tsx`, `FullPathView.tsx` | A(잔존) | Deep dive에서 사용 |
| cs_54 종목상세 통합 | `GraphMiniView.tsx` + 딥링크 | A | 탭 제거→`?focus=` 딥링크 |
| CS-5-3 모바일 | `MobileCardList.tsx` | A | 카드리스트+FAB |

---

## 미구현 항목 상세

### 🔴 C-1. CS-3-3 GDS 알고리즘 계산 task (재현 불가)

- **설계**: `cs_33_gds_algorithms.md` — `run_gds_algorithms()` task가 graph.project → gds.pageRank.write / gds.louvain.write / gds.betweenness.write 실행.
- **구현 현실**:
  - `apps/chain_sight/tasks/gds_tasks.py` **파일 없음**.
  - 코드 전체에 `gds.`, `pageRank/louvain.write`, `graph.project` 호출 **0건**.
  - `services/path_service.py:186~203`은 Neo4j 노드의 `s.pagerank_score`, `s.betweenness_score`를 **읽기만** 함.
  - `graph/schema.py:41`은 `community_id` 인덱스만 생성(쓰기 아님).
- **모순점**: `remaining_work_plan.md`는 "CS-3 ... GDS(PageRank, Louvain, Betweenness) 2026-04-03 M3 마일스톤 달성"으로 **완료** 기록. 그러나 재현 가능한 task가 코드에 없음 → **일회성 수동/외부 스크립트 실행으로 노드 속성을 채운 것으로 추정**. 주간 배치로 자동 갱신되지 않음.
- **영향**: Neo4j 노드의 centrality 값이 stale될 수 있고, Heat Score의 `gds_centrality_delta` 구성요소도 연쇄 미구현(아래 B-1).

### 🟡 B-1. redesign 시드 Phase 2 — Heat Score (부분)

- **설계**: `chainsight_seed_node_design.md §3` — 6개 가중 구성요소 + `SeedHeatScore` ORM 모델(stock/date/heat_score/components/seed_rank).
- **구현**:
  - `tasks/seed_tasks.py:calculate_heat_scores` 존재하나 **4/6 구성요소만** (price/volume/relation_change/news_activation). `gds_centrality_delta`, `news_event_count` 누락.
  - 가중치: 설계 0.25/0.20/0.20/0.15/0.10/0.10 → 구현 균등(0.25×4)으로 불일치.
  - **`SeedHeatScore` 모델 부재** — `models/` 디렉토리에 없음. 결과를 Neo4j 노드 속성으로만 저장, PostgreSQL 이력 없음.
  - `services/seed_selection.py:378`의 `heat_total`은 **0.0 하드코딩 placeholder**.
- **결론**: 섹터 정렬은 여전히 Phase 1 `seed_count DESC` 기준. Phase 2 전환(`heat_total DESC`) 미작동.

### 🔴 C-2. redesign 시드 Phase 3 — 이벤트 전파 모델 (전무)

- **설계**: `chainsight_seed_node_design.md §4` — D-1(text_conditional_prob, Gemini Embedding + ChromaDB), D-2(lagged correlation + volume_response + propagation_weight), D-3(가중치 학습).
- **구현**: 키워드(`text_conditional`, `propagation_weight`, `lagged`) **코드 0건**. ChromaDB/Embedding 연동 없음. Beat 스케줄 미등록.
- **상태**: redesign에서도 "범위 밖(후속)"으로 명시 → 계획된 미구현(C).

### 🟡 B-2. 2차 카드 설명 필드 (부분 — 백엔드 미준비)

- **설계**: `chainsight_api_design.md §4.2차 확장` + `ui_ux_design §9` — `relation_summary`, `why_now`, `insight_summary`를 neighbors 응답에 추가.
- **구현**: `NeighborGraphView`의 relation 객체에 미포함. 프론트는 1차 템플릿(RELATION_TEMPLATES 고정 문구)만 사용.
- **상태**: 설계상 "2차" 단계 → 계획된 미구현.

### ⚪ 미구현(저우선, 설계상 Future / Pro 고도화)

| 항목 | 설계 위치 | 상태 |
|------|-----------|------|
| LLM 기반 chain title/summary | api_design §4 추후 / 00_summary 범위밖 | C |
| 전환 애니메이션 상세 스펙(translateX -, bounce, 좌측 히스토리 흐림 레이어) | ui_ux_design §7 | 부분/불명 — force-graph 기본 모션은 있으나 설계 스펙 단위 검증 불가 |
| 노드 비교 모드(Ctrl+Click) | cs_5_frontend §6-3 | C |
| Centrality/PER 오버레이 | cs_5_frontend §6-2 | C (GDS 데이터 미공급과 연동) |
| chain path 전체 트레일 preload | ui_ux_design §10 | C (Future로 명시) |

---

## 폐기/대체 항목

### D-1. cs_51~54 프론트엔드 단일화면 설계 → redesign 2워크스페이스로 대체

- **폐기 방향**: `cs_5_frontend_design_v2.md`의 단일 `/chainsight` 화면(GraphView 중심) 설계.
- **대체 방향**: redesign_v1_260409 — `/chainsight`(마켓뷰, breadth-first) + `/chainsight/[symbol]`(Deep dive, depth-first) 분리.
- **잔존**: 원안 컴포넌트는 삭제가 아니라 **Deep dive 워크스페이스로 흡수**(GraphCanvas, AIGuidePanel, TracePathView, NodeDetailPanel, GraphMiniView).

### D-2. cs_41~43 API의 위상 강등 (폐기 아님)

- graph/suggestions/trace 3종은 redesign에서 **"마켓뷰 주 흐름에서 미사용, Deep dive 전용"**으로 재정의. 코드 유지·동작.

### D-3. CUSTOMER_OF 별도 저장 폐기 (v1.3 결정, 구현 준수)

- `SUPPLIES_TO`만 canonical 저장, API view에서 역방향 파생. `views.py:94`(derived_type), `views.py:624`(_display_type)로 구현 확인.

### D-4. `synced_to_neo4j` → `neo4j_dirty` 플래그 통일

- migration `0008_unify_neo4j_flags.py`로 단일 소스화. RelationConfidence·ChainProfile 모두 `neo4j_dirty` 사용.

### D-5. 레거시 serverless/frontend Chain Sight 코드 제거 (CS-0-0)

- 구버전 `frontend/components/chain-sight/`(하이픈) 계열 제거됨. 현재는 `chainsight/`(무하이픈)만 존재.
- 단, 로드맵 부록 B 기준 serverless의 ETF 모델(ETFProfile/ETFHolding/ThemeMatch)은 `# LEGACY_KEEP_UNTIL_DC2` 보관 대상 — 본 감사 범위(apps/chain_sight) 밖이라 별도 확인 권장.

---

## 부록: 검증 근거 명령

```
# GDS task 부재 확인
grep -rniE "gds\.|pageRank|louvain\.write|graph\.project" apps/chain_sight  → 0건 (읽기 path_service.py만)
# SeedHeatScore 모델 부재
grep -rn "class SeedHeatScore" apps/chain_sight  → 0건
# heat_total placeholder
apps/chain_sight/services/seed_selection.py:378 → "heat_total": 0.0
```

## 권고 (수정 아님, 후속 작업 후보)

1. **CS-3-3 GDS를 재현 가능 task로 승격** — `tasks/gds_tasks.py` 신설 + Beat 등록. 현재 노드 점수가 stale될 위험.
2. **`remaining_work_plan.md` 정정** — "CS-3 GDS 완료"는 task 자동화가 아닌 일회성 실행 → 문서-구현 불일치(로드맵 원칙 1 위반).
3. **Heat Score Phase 2 완성 또는 명시적 보류 처리** — `SeedHeatScore` 모델 + `heat_total` placeholder가 "Phase 2 진행 중"인지 "보류"인지 PROGRESS에 명문화.
