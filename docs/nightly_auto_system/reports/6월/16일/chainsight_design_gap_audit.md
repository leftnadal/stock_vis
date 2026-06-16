# Chain Sight 설계 갭 감사

> 생성일: 2026-06-16 · 읽기 전용 감사 (코드 미수정)
> 대상: `docs/chain_sight/plan/` + `docs/chain_sight/redesign(26.06)/` 설계서 ↔ `apps/chain_sight/` + `frontend/{app,components}/chainsight/` 구현
> 교차참조: `docs/chain_sight/task_done/`

---

## 요약 (구현률)

총 **3개 설계 세대**로 나뉜다. 세대를 섞으면 갭이 왜곡되므로 세대별로 본다.

| 세대 | 설계 문서 | 범위 | 분류 결과 | 구현률 |
|------|----------|------|-----------|--------|
| **G1: 데이터 파이프라인** (cs_0~3, roadmap v1.3) | 17개 | Neo4j 연결·스키마·노드/관계 로드·프로파일·관계신뢰도·동기화·GDS | A×14, B×2, D×1 | **~92%** |
| **G1: REST API** (cs_41~43) | 3개 | graph / suggestion / trace API | A×2, B×1 | **~85%** |
| **G2: 프론트엔드 딥다이브** (cs_51~54, cs_5_v2) | 5개 | `/chainsight/[symbol]` 워크스페이스 | A×5 (고급기능 일부 미구현) | **~95%** |
| **G2: redesign_v1_260409 마켓뷰** (PR-1~7) | 7개 | `/chainsight` 마켓 뷰 신설 | A×6, B×1 | **~97%** |
| **G3: redesign(26.06) 관심도/이벤트** | 5개+ | 관심도 M1·이벤트 보드·실험 | A×1, C×3, 보류×2 | **~25%** |

**전체 핵심 결론**
- **G1 데이터 파이프라인 + G2 프론트엔드는 사실상 완성**. 설계-코드 매핑이 거의 1:1.
- **유일한 명확한 갭**: GDS 정기 배치 자동화(cs_33) — 수동 실행 결과만 Neo4j에 영속화, Celery 태스크 부재.
- **현재 진행 전선은 G3(redesign 26.06)**: 관심도 M1 백엔드(CS-RD2)는 **이미 머지 완료**(커밋 d4407f6), 그 위의 **이벤트 보드 프론트(CS-RD3)는 미구현**, EXP 문서들은 결정 대기.

---

## 세대 관계 (대체 vs 병행)

질문 1·3에 대한 직접 답:

```
G1 (cs_0~4, roadmap v1.3)  ──  데이터 파이프라인 + 딥다이브 API/UI
    │  └ cs_5*  ……………………… /chainsight/[symbol] 딥다이브 워크스페이스 (유지)
    │
    ▼ (대체 아님 — 병행. 마켓 뷰만 신설)
G2 redesign_v1_260409 (PR-1~7)  ──  /chainsight 루트 = 마켓 뷰 신설
    │   · cs_5_frontend_design_v2 가 cs_51~54 를 상위 통합한 문서
    │   · API: chainsight_api_design.md 가 cs_4* 마켓뷰 부분만 신설/보강
    │
    ▼ (다음 세대 — 진행 중)
G3 redesign(26.06)  ──  관심도 M1 + 이벤트 보드 + 유니버스 확장 실험
        · CS-RD1 하네스/테마 데이터  (부분)
        · CS-RD2 관심도 M1 백엔드    (완료, 머지됨)
        · CS-RD3 이벤트 보드 프론트  (미구현)
        · CS-EXP merge/universe      (결정 대기)
```

- **redesign_v1_260409 는 cs_* 를 "대체"하지 않는다.** `cs_5_frontend_design_v2`가 cs_51~54를 상위 통합(§0에 원안 대비 7개 변경점 명시)했고, redesign_v1은 그 위에 **`/chainsight` 루트의 마켓 뷰를 신설**했다. 딥다이브(`/chainsight/[symbol]`)와 마켓뷰(`/chainsight`)는 공존한다.
- **redesign(26.06) 은 redesign_v1 이후의 차세대 설계가 맞다.** 단, 일부는 이미 코드로 진입(CS-RD2)했으므로 "전부 미구현"이 아니다.

---

## 문서별 상태 테이블

### G1 — 데이터 파이프라인 (cs_0~3)

| 문서 | 제목 | 분류 | 근거 | task_done |
|------|------|:----:|------|:---------:|
| cs_00 | 레거시 정리 + API 테스트 | **A** | `models/relation_discovery.py`, `utils.py:28` normalize_pair | ✅ |
| cs_01 | Migrations 검증 | **A** | migrations 0001~0009 (12 테이블) | ✅ |
| cs_02 | Neo4j 연결 레이어 | **A** | `graph/repository.py` (PID 기반 fork-safe driver), `graph/__init__.py` 팩토리 | ✅ |
| cs_03 | 온톨로지 스키마 | **A** | `graph/schema.py` (제약 4 + 인덱스), `management/commands/init_neo4j_schema.py` | ✅ |
| cs_11 | Stock 노드 벌크 로드 | **A** | `services/neo4j_loader.py` STOCK_FIELD_MAP + `load_stocks_to_neo4j.py` | ✅ |
| cs_12 | Sector/Industry + BELONGS_TO | **A** | `services/neo4j_loader.py:72` + `load_sectors_to_neo4j.py` | ✅ |
| cs_13 | Peer 관계 로드 | **A** | `services/neo4j_loader.py:128` (Finnhub+FMP), `tasks/peer_tasks.py` | ✅ |
| cs_21 | Tier A 프로파일 (GrowthStage+CapitalDNA) | **A** | `tasks/profile_tasks.py`, `models/growth_stage.py`, `models/capital_dna.py` | ✅ |
| cs_21b | SensitivityProfile | **A** | `tasks/sensitivity_tasks.py`, `models/sensitivity.py` | ✅ |
| cs_21c | InsiderSignal | **A** | `tasks/insider_tasks.py`, `models/insider_signal.py` | ✅ |
| cs_22 | CoMentionEdge | **A** | `tasks/relation_tasks.py:18`, `models/relation_discovery.py:12`, `models/news_event.py` | ✅ |
| cs_23 | PriceCoMovement | **A** | `tasks/relation_tasks.py:126`, `models/relation_discovery.py:36` | ✅ |
| cs_24 | RelationConfidence 판정 | **A** | `tasks/relation_tasks.py:211` update_relation_confidence / check_stale_and_decay | ✅ |
| cs_25 | ChainProfile 집약 + Beat | **A** | `tasks/sync_tasks.py:15` aggregate_chain_profiles, `models/chain_profile.py` | ✅ |
| cs_31 | Profile → Neo4j 동기화 | **B** | `services/neo4j_sync.py` + `tasks/neo4j_dirty_sync_tasks.py`로 **대체 구현** (설계의 `sync_profiles_to_neo4j()` 전용 함수 없음, dirty 플래그 범용 동기화로 통합) | ✅ |
| cs_32 | Relation → Neo4j 엣지 동기화 | **B** | `services/neo4j_sync.py:22` sync_dirty_relations. 엣지 라벨을 `RELATED_TO`로 고정, relation_type은 속성 (설계와 표현 다름) | ✅ |
| cs_33 | GDS 알고리즘 배치 | **D** | ⚠️ **정기 배치 Celery 태스크 부재**. `services/path_service.py:185` `_fetch_centrality()`는 이미 계산된 pagerank/betweenness/community 속성을 **조회만** 함. 결과는 Neo4j에 1회 수동 실행 후 영속. task_done은 "완료" 기록이나 자동화 미달 | ✅(과대기록) |

### G1 — REST API (cs_4*)

| 문서 | 엔드포인트 | 분류 | 근거 | 미구현 |
|------|-----------|:----:|------|--------|
| cs_41 | `GET /{symbol}/graph/` | **A** | `api/views.py:59` ChainSightGraphView (depth 1~3, CUSTOMER_OF 역파생 L94, market_signals) | edge `explanation`(basis_summary) 필드 누락 |
| cs_42 | `GET /{symbol}/suggestions/` | **B** | `api/views.py:117` ChainSightSuggestionView (peers/same_industry/co_mentioned/same_sector = 4/5) | **community 클러스터 기반 제안 미구현**, strength 동적계산 없음(하드코딩) |
| cs_43 | `GET /trace/?from=&to=` | **A** | `api/views.py:222` ChainSightTraceView (shortestPath, found 분기, max_depth) | 없음 |
| relation_confidence_design_v1 | 신뢰도 엔진 상세 | **B** | tier/status/score/normalize_pair 구현됨 | 설계 §10 `calculate_truth_and_status()` 중앙함수 부재(규칙이 `tasks/relation_tasks.py`에 분산), §11 basis_summary 10개 템플릿 미적용(간이 문자열), save() 자동 정규화 미내장 |
| remaining_work_plan | 잔여 작업 계획 | (참고) | CS-2-1b/c는 이후 구현 완료. Beat 일괄등록·DC-2 ETF·CS-5는 후속 추적용 | — |

### G2 — 프론트엔드 딥다이브 (cs_5*)

| 문서 | 제목 | 분류 | 근거 | 미구현 |
|------|------|:----:|------|--------|
| cs_5_frontend_design_v2 | FE 설계 v2 (상위 통합) | **A** | cs_51~54 통합 + §0 변경점. `/chainsight/[symbol]/page.tsx` 3-panel | 노드 비교(Ctrl+Click §6-3), 메트릭 오버레이(PER/Centrality §6-2), 커뮤니티 시각화 §6-2 |
| cs_51 | 그래프 시각화 | **A** | `components/chainsight/GraphCanvas.tsx`, `graphStyles.ts`, `radialLayout.ts` (Spotlight, lazy expand, 6색 엣지) | — |
| cs_52 | AI 가이드 UI | **A** | `components/chainsight/AIGuidePanel.tsx` (카테고리→필터, 강도, top3) | — |
| cs_53 | Chain Trace UI | **A** | `components/chainsight/TracePathView.tsx` (경로 시각화, 한글 라벨) | — |
| cs_54 | 종목 상세 연계 | **A** | `components/chainsight/GraphMiniView.tsx` + stocks 상세 탭 | 프로파일 요약(GrowthStage/CapitalDNA 등) 미니뷰 §7 부분 미표시 |

### G2 — redesign_v1_260409 마켓 뷰 (PR-1~7)

| PR | 제목 | 분류 | 근거 | 미구현 |
|----|------|:----:|------|--------|
| PR-1 | RelationConfidence 스키마 확장 | **A** | migration 0005, `models/relation_discovery.py` (neo4j_dirty/previous_status/neo4j_synced_at) | — |
| PR-2 | 시드 선정 Celery Task | **B** | `services/seed_selection.py`, `tasks/seed_tasks.py` | comention_surge 시드 소스 1개 stub/하드코딩 (5소스 중 4 구현) |
| PR-3 | Neo4j Dirty Sync | **A** | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py` | — |
| PR-4 | 마켓 뷰 API 4종 | **A** | `api/views.py` SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView + urls 등록 | — |
| PR-5 | FE 탐색상태+섹터바+그래프 | **A** | `lib/stores/explorationStore.ts`, `hooks/useMarketView.ts`, `components/chainsight/{SectorBar,MarketGraphCanvas}.tsx` | — |
| PR-6 | FE 트레일+관계카드 | **A** | `components/chainsight/{ExplorationTrail,RelationCardPanel,PathCard}.tsx` | — |
| PR-7 | FE 체인 스토리 피드 | **A** | `components/chainsight/ChainStoryFeed.tsx` | 데이터 부족 시 empty state (설계상 정상) |

### G3 — redesign(26.06) 관심도/이벤트/실험

| 문서 | 제목 | 분류 | 근거 |
|------|------|:----:|------|
| Cs redesign 01 harness and theme data | 하네스 정합화 + 테마 데이터 적재 | **B(부분)** | 테마 로더 `management/commands/load_themes_to_neo4j.py` 존재. STEP0 측정 완료(`CS-EXP_STEP0_findings.md`). 테마 채움률 정합화는 진행/부분 |
| Cs redesign 02 attention m1 backend (+ v2) | **관심도 M1 백엔드 (CS-RD2)** | **A** | ✅ **머지 완료** 커밋 d4407f6: `models/attention.py` StockAttentionScore(migration 0009) + `services/attention_service.py`(compute_attention_scores/get_event_board/get_event_ranking, M1=0.5·volz+0.3·volpct+0.2·retpct, ADV_FLOOR 유동성가드) + `tasks/attention_tasks.py` compute_daily_attention + `api/event_views.py` 2개 API + 시리얼라이저 + 테스트 20 |
| Cs redesign 03 event board frontend | 이벤트 보드 프론트 (CS-RD3) | **C** | ⚠️ **미구현**. 백엔드 `events/` + `events/<theme>/stocks/` API는 존재하나, 이를 소비하는 프론트엔드 컴포넌트 없음(`frontend/**/chainsight`에서 events/attention API 호출 0건). TASKQUEUE 상 "ready(unblock)" 대기 상태 |
| Cs exp universe expansion | 유니버스 확장 실험 | **보류** | 설계 스케치, 결정 대기 |
| Cs exp merge | v1+v2 통합 / graph_analysis 흡수 검토 | **보류** | 결정 대기 컨텍스트 문서 |
| CS-EXP_STEP0_findings | STEP0 측정 결과 | (진행 보고) | 유니버스 670, ADV_FLOOR 등 측정값 — CS-RD2 진입 근거 |

---

## 미구현 항목 상세

### 🔴 우선순위 높음

1. **cs_33 — GDS 알고리즘 정기 배치 자동화 부재 (분류 D)**
   - 현상: PageRank/Louvain/Betweenness 결과가 Stock 노드 속성(`pagerank_score`, `community_id`, `betweenness_score`)에 존재하나, 이를 주기적으로 재계산하는 Celery 태스크(`run_gds_algorithms` 등)가 없음. GDS 프로젝션 생성/삭제 로직도 코드에 없음.
   - 영향: 그래프가 갱신돼도 centrality/community가 자동 갱신되지 않음 → 시간 경과 시 stale.
   - task_done(`CS-3-3`)은 "완료"로 기록되어 있으나 이는 수동 1회 실행 결과 영속화일 뿐. **기록과 실제 자동화 수준 불일치.**

2. **relation_confidence_design_v1 — 신뢰도 엔진 중앙 함수 부재 (분류 B)**
   - `calculate_truth_and_status()` 단일 함수(설계 §10) 없이 규칙이 `tasks/relation_tasks.py` 곳곳에 분산. SUPPLIES_TO 단독 confirmed 규칙 등 일부 분기 누락 가능.
   - `relation_basis_summary` 설계 §11의 10개 풍부 템플릿 대신 간이 문자열 조합.
   - `RelationConfidence.save()` 자동 정규화 미내장(호출부에서 `normalize_pair`만).

### 🟡 우선순위 중간

3. **CS-RD3 이벤트 보드 프론트엔드 미구현 (분류 C, 현재 전선)**
   - 백엔드 관심도 M1 + events API는 완성. 이를 그리는 프론트 화면만 미작성. **다음 작업 1순위로 ready 상태.**

4. **cs_42 — community 기반 제안 카테고리 미구현 (분류 B)**
   - suggestions API 5개 카테고리 중 community(Louvain 클러스터) 1개 누락. cs_33 GDS 자동화 부재와 연쇄(community_id 신선도 의존).

5. **cs_41 — graph API edge `explanation` 필드 누락 (분류 A 내 결함)**
   - basis_summary 기반 관계 설명이 응답에 미포함.

6. **PR-2 — comention_surge 시드 소스 stub (분류 B)**
   - 일일 시드 선정 5소스 중 co-mention 급증 소스가 하드코딩/미완. 시드 종목 수 소폭 감소 가능.

### 🟢 우선순위 낮음 (스코프 제외/후속)

7. **cs_5_v2 프론트 고급 기능** — 노드 비교 모드(Ctrl+Click), 메트릭 오버레이(PER 히트맵/Centrality), 커뮤니티 시각화. 설계서에서 "Future Path"로 명시 제외.
8. **cs_54 미니뷰 프로파일 요약** — 탭은 활성, GrowthStage/CapitalDNA 요약 표시는 미포함.
9. **CS-RD1 테마 데이터 채움률 정합화** — 부분 진행.

---

## 폐기/대체 항목

| 항목 | 설계 방향 | 실제 채택 | 비고 |
|------|----------|----------|------|
| **cs_31/cs_32 동기화 함수** | `sync_profiles_to_neo4j()` / `sync_relations_to_neo4j()` 전용 함수 + `synced_to_neo4j` 플래그 | `neo4j_dirty` 플래그 + 범용 dirty sync 서비스(`services/neo4j_sync.py`)로 **통합 대체** | audit P0 #9 결정. 플래그 의미 반전(synced→dirty). 기능은 동등 이상 |
| **cs_32 엣지 라벨** | relation_type별 엣지 라벨 | 모든 관계 `RELATED_TO` 단일 라벨 + relation_type 속성 | 설계와 표현 다름, 동작 동등 |
| **cs_33 GDS 배치** | Celery 정기 배치 자동화 | 수동 1회 실행 + 결과 속성 영속화 | 자동화는 사실상 폐기/미달 상태 |
| **cs_51~54 (개별 FE 문서)** | 4개 분리 설계 | `cs_5_frontend_design_v2`가 상위 통합(원안 7개 변경점 반영) | 개별 문서는 이력 보존용. 구현은 v2 기준 |

---

## 부록 — 감사 신뢰도 노트

- 본 감사는 **설계서 텍스트 ↔ 코드 심볼/파일 존재 여부** 대조 기준이다. 런타임 동작·데이터 정확성은 검증 범위 밖(별도 `task_done/.../browser_test_report.md` 참조).
- **정정 이력**: 1차 병렬 탐색에서 "redesign(26.06) 관심도 M1 = 미구현(C)"으로 보고됐으나, 커밋 `d4407f6`(990줄, 2026-06-15 머지) 및 `apps/chain_sight/{models/attention,services/attention_service,tasks/attention_tasks,api/event_views}.py` 직접 확인으로 **(A) 완전구현**으로 정정함. 설계 문서만 보고 git/코드를 보지 않으면 최신 머지를 놓칠 수 있다는 점이 본 감사의 핵심 교훈.
- task_done 문서의 "완료" 기록과 실제 자동화 수준이 어긋나는 사례(cs_33 GDS)가 있으므로, task_done은 단독 진실원천이 아니라 코드와 교차검증해야 한다.
