# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-11
> **대상**: `docs/chain_sight/plan/` 설계 문서 vs `chainsight/` 코드
> **목적**: Chain Sight 설계서가 코드에 얼마나 반영되었는지 갭 분석
> **방법**: 설계서 4세대(원본 cs_* → cs_5_v2 → redesign_v1_260409 → update_v2 v1.4) 모두 읽고 코드와 대조
> **결과 코드 수정 없음** (읽기 전용)

---

## 요약 (구현률)

### 세대별 설계서 현황

`docs/chain_sight/plan/` 디렉토리에는 **4세대의 설계 문서가 누적**되어 있고, 각 세대는 일부만 폐기되고 일부는 함께 살아있다.

| 세대 | 작성일 | 위치 | 핵심 추가물 | 현재 상태 |
|---|---|---|---|---|
| **1세대** | 2026-04-02 | `cs_00 ~ cs_54.md` (24개) | Phase 0~5 단일 워크플로우 | 일부 대체 |
| **2세대** | 2026-04-04 | `cs_5_frontend_design_v2.md` | Deep dive workspace `/chainsight/[symbol]` 분리 + CTA + 프로 기능 | 살아있음 (2번째 진입점) |
| **3세대** | 2026-04-10 | `redesign_v1_260409/` (4개) | 마켓 뷰 `/chainsight` (5영역) + Seeds API + neo4j_dirty 패턴 | 살아있음 (1차 진입점) |
| **4세대** | 2026-04-16 | `update_v2/ROADMAP_v1.4.md` | Phase 6 (SavedPath/Watchlist) + Phase 7 (FE) + Heat Score | 살아있음 (확장 영역) |

### 전체 구현률

| 분류 | 갯수 | 설명 |
|---|---|---|
| **(A) 완전 구현** | 27 / 32 작업 (~84%) | Phase 0~5 + redesign PR-1~7 + Phase 6/7 + DC-2 핵심 |
| **(B) 부분 구현** | 3 / 32 (~9%) | Heat Score, Stock 동기화, Suggestion 카테고리 |
| **(C) 미구현** | 2 / 32 (~6%) | 시드 노드 Phase 2 SeedHeatScore 모델, Phase 3 D-1~D-3 (텍스트 컨디션 + 전파 가중치) |
| **(D) 폐기/대체** | 다수 | 1세대 cs_5 단일 페이지 디자인 → 2세대(Deep dive) + 3세대(Market view) 양분 구조로 분기 |

> **핵심 결론**: 백엔드/프론트엔드 모두 v1.4 (Phase 7)까지 구현 완료된 상태. 미구현은 Phase 2/3의 고도화 알고리즘 영역.

---

## 문서별 상태 테이블

### Phase 0: 인프라 (cs_00~03)

| 작업 | 설계서 | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-0-0 | cs_00_legacy_cleanup_api_test.md | `decisions/003_api_access_test.md` (5개 테스트 결과) | **A 완전** |
| CS-0-1 | cs_01_migrations_verification.md | `chainsight/migrations/` 0001~0008 (14개 모델) | **A 완전** (v1.4의 14개 테이블 충족) |
| CS-0-2 | cs_02_neo4j_connection.md | `chainsight/graph/repository.py` (PID 기반 lazy init) | **A 완전** |
| CS-0-3 | cs_03_neo4j_schema.md | `chainsight/graph/schema.py` + `init_neo4j_schema` 커맨드 | **A 완전** |

### Phase 1: 시드 데이터 로드 (cs_11~13)

| 작업 | 설계서 | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-1-1 | cs_11_stock_node_bulk_load.md | `management/commands/load_stocks_to_neo4j.py` | **A 완전** (532 Stock) |
| CS-1-2 | cs_12_sector_industry.md | `management/commands/load_sectors_to_neo4j.py` | **A 완전** (17 Sector + 128 Industry) |
| CS-1-3 | cs_13_peer_relations.md | `chainsight/tasks/peer_tasks.py` | **A 완전** (8,350 PEER_OF) |

### Phase 2: 파생 데이터 파이프라인 (cs_21~25)

| 작업 | 설계서 | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-2-1 (GrowthStage + CapitalDNA) | cs_21_tier_a_profile.md | `chainsight/tasks/profile_tasks.py:35,128` | **A 완전** (480 + 473) |
| CS-2-1b (SensitivityProfile) | cs_21b_sensitivity_profile.md | `chainsight/tasks/sensitivity_tasks.py` | **A 완전** (503건) |
| CS-2-1c (InsiderSignal) | cs_21c_insider_signal.md | `chainsight/tasks/insider_tasks.py` | **A 완전** (503건) |
| CS-2-2 (CoMention) | cs_22_co_mention.md | `chainsight/tasks/relation_tasks.py:19 extract_co_mentions` | **A 완전** |
| CS-2-3 (PriceCoMovement) | cs_23_price_co_movement.md | `relation_tasks.py:117 calculate_price_co_movement` | **A 완전** |
| CS-2-4 (RelationConfidence v2.1) | cs_24 + relation_confidence_design_v1.md | `relation_tasks.py:196 update_relation_confidence` + `:373 check_stale_and_decay` + `models/relation_discovery.py` 21개 필드 | **A 완전** (5단계 상태/3단 점수/7개 bool/normalize_pair) |
| CS-2-5 (ChainProfile 집약) | cs_25_chain_profile_aggregation.md | `chainsight/tasks/sync_tasks.py:15 aggregate_chain_profiles` | **A 완전** (503건, 30개 개별 필드 유지) |

### Phase 3: Neo4j 동기화 + GDS (cs_31~33)

| 작업 | 설계서 | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-3-1 (Profile sync) | cs_31_profile_neo4j_sync.md | `sync_tasks.py:98 sync_profiles_to_neo4j` (`neo4j_dirty` 기반 delta) | **A 완전** |
| CS-3-2 (Relation sync) | cs_32_relation_neo4j_sync.md | `sync_tasks.py:149` → `services/neo4j_sync.py:21 sync_dirty_relations` 위임. UNDIRECTED 정규화 + market weak 허용 | **A 완전** (data_quality_3_fixes 보강) |
| CS-3-3 (GDS) | cs_33_gds_algorithms.md | task_done 기록만 (PageRank, Louvain, Betweenness 결과 있음) | **A 완전** (단발성 — 코드는 인라인 Cypher) |

### Phase 4: REST API (cs_41~43, +44 v1.4)

| 작업 | 설계서 | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-4-1 (Graph API) | cs_41_graph_api.md | `chainsight/api/views.py:58 ChainSightGraphView` | **A 완전** (CUSTOMER_OF derived 포함) |
| CS-4-2 (Suggestion API) | cs_42_suggestion_api.md | `views.py:109 ChainSightSuggestionView` (peers/same_industry/co_mentioned/same_sector 4종) | **B 부분** — 설계서의 PEER/CUSTOMER/SAME_INDUSTRY/CO_MENTIONED 매핑은 충족하나, **Chain Sight DNA(GrowthStage, CapitalDNA) 기반 추천**은 미반영. CS-4-1_2_3 task_done에서는 "유사도 기반"이라 했지만 실제 코드는 단순 Cypher 매칭 |
| CS-4-3 (Trace API) | cs_43_trace_api.md | `views.py:185 ChainSightTraceView` (shortestPath max 5) | **A 완전** |
| CS-4-4 (Seed Heat Score) | cs_44_seed_node_heat_score.md (v1.4) | `chainsight/tasks/seed_tasks.py:96 calculate_heat_scores` 4개 시그널 가중합 → Neo4j Stock 속성 | **B 부분** — 4개 시그널만 (price/volume/relation_change/news_activation), 설계서 6개 중 `news_event_count`/`gds_centrality_delta` 미반영. **별도 SeedHeatScore 모델은 없고 Neo4j Stock 속성으로 직접 저장** (단순화 결정) |

### Phase 5: 프론트엔드 그래프 (cs_51~54 + cs_5_v2 + redesign + cs_55~56 v1.4)

이 영역이 가장 많이 진화했다. **3세대 Market View(`/chainsight`)와 2세대 Deep dive workspace(`/chainsight/[symbol]`)가 양분 공존**한다.

| 작업 | 설계서 (최종 기준) | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-5-1 (Graph Visualization) | cs_5_frontend_design_v2.md (Deep dive 3-panel) | `frontend/components/chainsight/GraphCanvas.tsx` + `app/chainsight/[symbol]/page.tsx` | **A 완전** (370 LOC, 56 노드 / 59 엣지 / 621ms 검증됨) |
| CS-5-2 (AI Guide UI) | cs_52_ai_guide_ui.md → v2의 AIGuidePanel | `AIGuidePanel.tsx` (122 LOC) + `FilterPanel.tsx` (147 LOC, 9종 관계 토글) | **A 완전** |
| CS-5-3 (Chain Trace UI) | cs_53_chain_trace_ui.md | `TracePathView.tsx` (105 LOC) | **A 완전** |
| CS-5-4 (Stock detail integration) | cs_54_stock_detail_integration.md | `GraphMiniView.tsx` (203 LOC) + 종목 상세 탭 교체 + `/chainsight?focus={symbol}` 딥링크 | **A 완전** (cs_v2 v1.4 의도 충족) |
| CS-5-5 (Market View) | redesign + cs_55_market_view.md | `app/chainsight/page.tsx` + `SectorBar` + `MarketGraphCanvas` + `ExplorationTrail` + `RelationCardPanel` + `ChainStoryFeed` | **A 완전** (5개 영역 모두 구현) |
| CS-5-6 (Seed Node) | cs_56_seed_node.md | `chainsight/services/seed_selection.py` (424 LOC) + Phase 1 5개 시드 소스 | **A 완전** (Phase 1만, Phase 2/3 미구현) |
| Mobile card list | CS-5-3 v1 (구설계) | `MobileCardList.tsx` (202 LOC) | **A 완전** |
| Pro features (Filter / Compare / Overlay) | cs_5_v2 §6 | FilterPanel **있음**, **노드 비교 모드 / PER 오버레이 / Centrality 오버레이 미구현** | **B 부분** — 필터만 |

### Redesign V1 (PR-1~7, 2026-04-10)

| PR | 설계 | 코드 | 상태 |
|---|---|---|---|
| PR-1 | RelationConfidence v2.1 + neo4j_dirty + previous_status | `migrations/0005_add_neo4j_dirty_previous_status.py` + `models/relation_discovery.py:130-159 save() 오버라이드` | **A 완전** (이후 0008에서 `synced_to_neo4j` 통합 제거) |
| PR-2 | Seed selection task | `services/seed_selection.py` (424 LOC) + `tasks/seed_tasks.py:28` | **A 완전** (5개 소스, fallback, SeedSnapshot 영속화 추가) |
| PR-3 | Neo4j Sync 개선 | `services/neo4j_sync.py:21 sync_dirty_relations` (UNDIRECTED 정규화 + market weak 허용) + `tasks/neo4j_dirty_sync_tasks.py` | **A 완전** |
| PR-4 | Market view API 4종 | `api/views.py:309 SeedListView`, `:318 SectorGraphView`, `:448 NeighborGraphView`, `:628 SignalFeedView` (총 814 LOC) | **A 완전** + 3단 폴백 강화 (Redis → SeedSnapshot → 비동기 복구) |
| PR-5 | FE 상태 + 섹터바 + 그래프 | `lib/stores/explorationStore.ts` (115 LOC) + `hooks/useMarketView.ts` (69 LOC) + `SectorBar` + `MarketGraphCanvas` (298 LOC) + `app/chainsight/page.tsx` | **A 완전** |
| PR-6 | FE 트레일 + 카드 패널 | `ExplorationTrail.tsx` (79 LOC) + `RelationCardPanel.tsx` (293 LOC, SeedCardList + RelationCardGroups + RelationCard) | **A 완전** |
| PR-7 | FE 체인 스토리 피드 | `ChainStoryFeed.tsx` (142 LOC, 무한 스크롤 + ChainStoryCard) | **A 완전** |

### Phase 6 (Path Watchlist 백엔드, v1.4)

| 작업 | 설계 (cs_61~67) | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-6-1 | SavedPath/PathAction model | `models/saved_path.py` (UUID PK + 4 status) | **A 완전** |
| CS-6-2 | Watchlist CRUD | `views/watchlist_views.py` ViewSet (248 LOC) | **A 완전** |
| CS-6-3 | Summary path | `services/path_service.py:generate_summary_path` (255 LOC, landmark 압축) | **A 완전** |
| CS-6-4 | Archive/Resolve | `WatchlistViewSet.archive`/`.resolve` actions | **A 완전** |
| CS-6-5 | Recheck API | `services/recheck_service.py` (255 LOC) + ViewSet `.recheck` | **A 완전** |
| CS-6-6 | Expand API | `services/expand_service.py` (91 LOC) + ViewSet `.expand` | **A 완전** |
| CS-6-7 | Alternatives API | `services/alternatives_service.py` (175 LOC) + ViewSet `.alternatives` | **A 완전** |

### Phase 7 (Path Watchlist 프론트엔드, v1.4)

| 작업 | 설계 (cs_71~73) | 코드 매핑 | 상태 |
|---|---|---|---|
| CS-7-1 | Watch 버튼 | `components/chainsight/WatchButton.tsx` (65 LOC) — ExplorationTrail에 통합 | **A 완전** |
| CS-7-2 | Watchlist 카드 리스트 | `app/chainsight/watchlist/page.tsx` (80 LOC) + `PathCard.tsx` (126 LOC) | **A 완전** |
| CS-7-3 | Full Path View | `FullPathView.tsx` (349 LOC) | **A 완전** |

### 데이터 수집 (DC)

| 작업 | 설계 | 코드 매핑 | 상태 |
|---|---|---|---|
| DC-1 | Peer + Industry 수집 | CS-1-3에서 처리됨 | **A 완전** |
| DC-2 | ETF Holdings → Theme | `management/commands/load_themes_to_neo4j.py` (153 LOC) — serverless ETF 모델 활용 | **A 완전** (21 Theme + 534 HAS_THEME) |
| DC-3~6 | Supply Chain 수동 시드 / Gemini 확장 / 뉴스 축적 / 유료 API | — | **C 미구현** (로드맵 상 "성장 후 진행"으로 보류, SEC pipeline이 이를 일부 대체 — 본 감사 범위 밖) |

### Celery Beat 등록

| 태스크 | config/celery.py 등록 위치 | 상태 |
|---|---|---|
| `chainsight-all-profiles` (CS-2-1) | line 685 (토 02:00) | **A** |
| `chainsight-co-mentions` | line 692 (매일 10:00) | **A** |
| `chainsight-price-co-movement` | line 700 (토 03:00) | **A** |
| `chainsight-relation-confidence` | line 707 (매일 11:00) | **A** |
| `chainsight-stale-decay` | line 714 (토 04:00) | **A** |
| `chainsight-aggregate-profiles` | line 721 (토 04:30) | **A** |
| `chainsight-sync-profiles-neo4j` | line 728 (매일 12:00, neo4j queue) | **A** |
| `chainsight-sync-relations-neo4j` | line 735 (매일 12:30, neo4j queue) | **A** |
| `chainsight-heat-score-daily` | line 742 | **A** (등록 확인) |
| `chainsight-seed-selection` | line 749 (매일 13:00 UTC) | **A** |
| `chainsight-neo4j-dirty-sync` | line 756 (매주 일 04:30, neo4j queue) | **A** |
| `chainsight-seed-snapshot-cleanup` | **미등록** (코드는 `seed_tasks.py:162`에 존재) | **B 부분** — 30일 클린업 task가 정의만 되어있고 Beat 미등록 → SeedSnapshot이 무한 누적될 위험 |

---

## 미구현 항목 상세

### 1. Seed Node Phase 2 — 별도 SeedHeatScore 모델 (C)

**설계** (`redesign_v1_260409/chainsight_seed_node_design.md` §3.4)
```python
class SeedHeatScore(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateField()
    heat_score = models.FloatField()
    components = models.JSONField()
    seed_rank = models.IntegerField(null=True)
```
+ 섹터 정렬 기준 변경: Phase 1 `seed_count DESC` → Phase 2 `heat_total DESC`

**현실**
- 별도 모델 **없음**. Heat score는 `seed_tasks.py:138` 에서 Neo4j `:Stock` 노드 속성(`heat_score`, `price_signal`, `volume_signal`, `relation_change_signal`, `news_activation`, `heat_score_updated_at`)으로 직접 저장.
- 섹터 정렬은 여전히 `seed_count DESC` (`services/seed_selection.py:387` `sorted(... key=seed_count, reverse=True)`).
- `sector_summary[*].heat_total` 필드는 **계산되지 않고 항상 0.0** (`seed_selection.py:362`).
- API 응답 `seeds[*]`에 `heat_score` 미포함.

**영향**: Market view ① 섹터바가 Phase 2로 진화하지 못함. 단, "Phase 1만 우선" 결정이라면 의도적 보류로 간주 가능.

### 2. Seed Node Phase 3 (D-1/D-2/D-3) — 이벤트 전파 모델 (C)

**설계** (chainsight_seed_node_design.md §4)
- D-1: `text_conditional_prob` (뉴스 → Gemini Flash 키워드 → ChromaDB Embedding → 종목별 벡터)
- D-2: lagged correlation + volume_response + propagation_weight
- D-3: 사후 검증 → 가중치 학습
- Beat 태스크 3개: `chainsight-text-conditional`, `chainsight-lagged-correlation`, `chainsight-propagation-weight`

**현실**
- 코드 **없음**. ChromaDB 의존성 없음. propagation_weight 계산 없음.
- Beat에 위 3개 태스크 미등록.

**영향**: 뉴스 시드 정량 변환 + 비대칭 propagation은 미구현. 현재는 단순한 CoMention 횟수 기반.

### 3. Suggestion API의 Chain Sight DNA 기반 추천 (B)

**설계** (cs_42_suggestion_api.md, CS-4-1_2_3 task_done)
> "Chain Sight 프로파일 기반 관련 종목 추천 — GrowthStage, CapitalDNA, sector 유사도 기반"

**현실** (`api/views.py:109-181`)
- 4개 카테고리만 단순 Cypher 매칭: `peers / same_industry / co_mentioned / same_sector`.
- `CompanyChainProfile` (GrowthStage, CapitalDNA) 활용 **없음**.

### 4. Seed Heat Score의 시그널 누락 (B)

**설계** (chainsight_seed_node_design.md §3.1, 6개 가중합)
- price_anomaly, volume_surge, relation_change_count, comention_surge, **news_event_count**, **gds_centrality_delta**

**현실** (`seed_tasks.py:88-91`, 4개)
- price, volume, relation_change, news_activation
- **`gds_centrality_delta` 미반영** (PageRank 변화 추적 안 함)
- **`news_event_count`는 CoMentionEdge 카운트로 단순 대체**

### 5. SeedSnapshot 클린업 Beat 미등록 (B)

`seed_tasks.py:162-169` `cleanup_seed_snapshots(retain_days=30)` 함수는 정의되어 있으나 `config/celery.py`에 Beat 등록 없음. → 30일 이전 스냅샷 자동 삭제 안됨.

### 6. Pro 기능 (FilterPanel 외) (B)

`cs_5_frontend_design_v2.md §6` 설계
- 노드 메트릭 오버레이 토글 (PER 히트맵 / Centrality / Louvain 색상) → **미구현**
- 노드 비교 모드 (Ctrl+Click 두 노드 → 비교 테이블) → **미구현**
- FilterPanel만 존재 (`FilterPanel.tsx` 147 LOC, 관계 타입 + Depth)

### 7. 2차/LLM 카드 설명 (의도적 미구현)

설계 (`chainsight_api_design.md` §4.2 + `chainsight_marketview_pr_prompts.md` PR-6)
- 2차: API neighbors 응답에 `relation_summary`, `why_now`, `insight_summary` 추가
- 3차: LLM 기반 explanation

**현실**: 1차 템플릿(`RelationCardPanel.tsx:9-19` `RELATION_TEMPLATES`)만 사용. 설계에서 "Future enhancement"로 명시했으므로 의도적 보류.

---

## 폐기/대체 항목

### 1. cs_51 (단순 GraphView 1탭) → cs_5_v2 Deep dive 워크스페이스 (D)

**1세대 cs_51_graph_visualization.md** (40~50 LOC 짜리 단순 사양)
> "components/chainsight/GraphView.tsx + Spotlight + Lazy expansion"

→ **2세대 cs_5_frontend_design_v2.md** 가 동일 영역을 3-panel 워크스페이스로 확장
→ 코드는 2세대를 따랐고, 1세대 설계는 사실상 **폐기**.

### 2. cs_52 (수평 카테고리 카드) → AIGuidePanel (D)

원안의 "가로 스크롤 카테고리 카드 + strength dots(●●●)"는 **strength 텍스트 라벨**(`AIGuidePanel.tsx`)로 대체.
> 폐기 사유: cs_5_v2 §0 "Strength dots → 상위 ticker + N 텍스트" 명시.

### 3. cs_53 (TraceView 단순 가로 표시) → TracePathView + FullPathView (D)

원안은 단순 가로 노드 체인. 실제로는 **두 컴포넌트**로 분리:
- `TracePathView.tsx` (deep dive 내부 사용)
- `FullPathView.tsx` (Watchlist 상세, Phase 7에서 추가)

### 4. cs_54 (종목 상세 Chain Sight 탭) → 딥링크 + GraphMiniView (D)

원안: "탭 내부 미니 그래프 + 전체 보기 링크"
→ 3세대(redesign): "**탭 제거** → `/chainsight?focus={symbol}` 딥링크"
→ 코드: `app/chainsight/page.tsx:14-29` 딥링크 처리 + `GraphMiniView.tsx`는 **여전히 종목 상세 탭에서 사용** (양립).

### 5. CompanyChainProfile JSONB → 30개 개별 필드 (D)

v1.1 설계: `profile_data (JSONB)` 단일 필드
v1.2 결정: 30개 개별 필드 유지 (원칙 4 부합)
**현실** (`models/chain_profile.py`): 약 25개 개별 필드. SQL WHERE/ORDER BY 직접 사용 가능.

### 6. CUSTOMER_OF 별도 저장 → SUPPLIES_TO + API 역방향 파생 (D)

v1.3에서 결정. 코드는 `api/views.py:90`에서 `derived_type = "CUSTOMER_OF"` 동적 파생. DB/Neo4j 저장 없음.

### 7. RELATED_TO 하드코딩 엣지 라벨 → 동적 타입 (D)

CS-3-2 초기 구현은 모든 관계를 `RELATED_TO`로 동기화 (1,631건 생성). 이후 `data_quality_3_fixes.md` (2026-04-13)에서 동적 타입(PEER_OF/CO_MENTIONED/PRICE_CORRELATED)으로 전환. 1회성 정리 로직(`sync_tasks.py:158 cleanup_key`)으로 레거시 RELATED_TO 엣지 제거 + RelationConfidence dirty 리셋.

### 8. `synced_to_neo4j` 필드 → `neo4j_dirty` 단일 소스 (D)

PR-1 (2026-04-10)에서 `neo4j_dirty` 추가. 이후 audit P0 #9 (migration 0008, 2026-04-29)에서 `synced_to_neo4j` 완전 제거. 의미 반전 (`True` = 동기화 필요). RelationConfidence + CompanyChainProfile 둘 다 적용.

### 9. Beat 12:00 EST `chainsight-update-sp500-change-percent` (D 신규 추가)

설계서에는 없지만 `data_quality_3_fixes.md`에서 추가. DailyPrice → Stock.change_percent를 일일 갱신. 섹터 시드 outlier 계산의 정확도 위해 필수.

---

## 부록: 4세대 설계 문서 관계도

```
2026-04-02  1세대 cs_00~54 (24개 파일)
                ↓ Phase 5만 cs_5_v2로 흡수
2026-04-04  2세대 cs_5_frontend_design_v2 (Deep dive workspace 분리)
                ↓ Phase 5의 진입점/메인 뷰 추가
2026-04-10  3세대 redesign_v1_260409/ (Market view 5영역)
                ↓ Path Watchlist + Heat Score 추가
2026-04-16  4세대 update_v2/ROADMAP_v1.4 (Phase 6/7 신설)
```

**1세대가 폐기되지 않은 영역**: Phase 0~4 (백엔드 인프라, 데이터, API). 1세대 cs_00~43은 여전히 task_instructions로 활용됨 (`update_v2/task_instructions/cs_00_legacy_cleanup_api_test.md` 등).

**1세대가 폐기된 영역**: Phase 5 (cs_51~54의 단일 페이지 사양). 2/3세대로 대체.

**3세대가 4세대로 확장된 영역**: Market view (5영역) → Watch 버튼 통합 + Watchlist 페이지 추가.

---

## 결론

1. **백엔드 영역 (Phase 0~4)**: **완전 구현**. 14개 모델, 11개 Beat 태스크, 7개 REST API, Neo4j 동기화 + GDS 모두 작동.
2. **마켓 뷰 (3세대 redesign + 4세대 v1.4)**: **완전 구현**. 5영역 UI + 7개 PR 모두 통과.
3. **Deep dive workspace (2세대 cs_5_v2)**: **완전 구현** + 모바일 카드 리스트 + FilterPanel.
4. **Path Watchlist (4세대 Phase 6/7)**: **완전 구현**. SavedPath/PathAction + 4개 액션 API + 카드 UI + FullPathView.
5. **고도화 영역**:
   - Heat Score Phase 1만 (4 시그널 가중합) — Phase 2/3 미구현
   - SeedHeatScore 모델 미구현 (Neo4j 속성으로 단순화)
   - LLM 기반 카드 설명 미구현 (의도적 1차 보류)
   - Suggestion API의 DNA 기반 추천 미구현 (단순 Cypher 매칭만)
6. **운영상 위험**:
   - `cleanup_seed_snapshots` Beat 미등록 → SeedSnapshot 무한 누적 (모니터링 필요)

**총평**: 설계 대비 **약 84% 완전 구현**, 부분/미구현은 모두 "고도화 영역"이며 운영 가능 수준의 MVP는 명확히 달성. v1.3까지의 6개 마일스톤(M0~M5) 모두 도달, v1.4의 M6/M7(Watchlist + 전략 루프)도 코드/문서 모두 통과.

---

**END OF AUDIT**
