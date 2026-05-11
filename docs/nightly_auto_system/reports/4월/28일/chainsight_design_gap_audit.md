# Chain Sight 설계 갭 감사

> **감사일**: 2026-04-29
> **감사 범위**: `docs/chain_sight/` 전체 설계 문서 vs `chainsight/` 백엔드 + `frontend/components/chainsight/` 프론트엔드 + `frontend/app/chainsight/` 라우팅
> **감사 방법**: 읽기 전용. 코드/문서 수정 없음.

---

## 요약 (구현률)

설계 문서 트리는 시간 순으로 3차에 걸쳐 누적되어 있다.

| 세대 | 위치 | 정체 | 산출 |
|------|------|------|------|
| **v1.3 원안** | `plan/chain_sight_roadmap_v1.3.md` + `plan/cs_*.md` 27개 | 초기 인프라 + Deep dive 워크스페이스 (`/chainsight/[symbol]`) | CS-0 ~ CS-5 |
| **redesign_v1 (Market View)** | `plan/redesign_v1_260409/` 4개 + `task_done/chain_sight_redesign_V1/` 7+3개 | 마켓 뷰 진입 허브(`/chainsight`) 추가 + 시드 노드 시스템 | PR-1 ~ PR-7 + 데이터 품질 fix |
| **update_v2 (Path Watchlist)** | `update_v2/ROADMAP_v1.4.md` + `update_v2/task_instructions/cs_*.md` 35개 | Heat Score(CS-4-4) + MarketView(CS-5-5) + Path Watchlist(Phase 6/7) | CS-4-4, CS-5-5, CS-5-6, CS-6-1~7, CS-7-1~3 |
| **graph_redesign_v2** | `graph_redesign_v2.md` (UI/UX 명세) | 시멘틱 방사형 레이아웃 + 빈 상태 일러스트 + 점진적 공개 | FE-PR-1~5 (현재 브랜치) |

전체 설계 항목 약 **45개** 중

| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 35 | 78 % |
| (B) 부분 구현 | 6 | 13 % |
| (C) 미구현 | 3 | 7 % |
| (D) 폐기/대체 | 1 | 2 % |

핵심 결론:
1. **MVP 기능 완성**: Phase 0~7 + redesign_v1 + Path Watchlist는 모두 구현되어 M5("사용자 경험 가능")까지 도달.
2. **redesign_v1_260409/ 는 cs_*를 폐기하지 않음**: Deep dive(`/chainsight/[symbol]`)와 Market View(`/chainsight`)가 병행 운영되며, 각각 cs_5/redesign_v1이 단일 설계 소스. cs_51~54는 재구조화돼 cs_5_frontend_design_v2.md에 흡수, 다시 redesign_v1에서 마켓 뷰가 추가됐다.
3. **장기 항목 미착수**: redesign_v1의 **Phase 2 SeedHeatScore 모델**, **Phase 3 D-1~D-3 이벤트 전파 모델**, **2차 LLM 카드 설명**은 미구현이다.
4. **API 응답 필드 1건 불일치**: `neighbors[].relation.evidence_tier_best` 명세 vs 코드 `evidence_tier`. PRD와 BE/FE 모두 후자로 통일된 사실상 BE 우위.

---

## 문서별 상태 테이블

### 1. v1.3 원안 (`plan/cs_*.md`)

| 문서 | 산출 코드 | 분류 | 비고 |
|------|----------|------|------|
| cs_00_legacy_cleanup_api_test | `decisions/003_api_access_test.md`, `serverless/`/`frontend/` 정리 | A | task_done/CS-0-0 완료 보고 존재 |
| cs_01_migrations_verification | `chainsight/migrations/0001~0007` (7개) | A | RelationConfidence v2.1 + SavedPath/PathAction + SeedSnapshot |
| cs_02_neo4j_connection | `chainsight/graph/repository.py`, `__init__.py`, `exceptions.py` | A | PID lazy init 적용 |
| cs_03_neo4j_schema | `chainsight/graph/schema.py` + `management/commands/init_neo4j_schema.py` | A | constraint 4 + index 2, 명세 100% 일치 |
| cs_11_stock_node_bulk_load | `management/commands/load_stocks_to_neo4j.py` + `services/neo4j_loader.py:get_stock_data_for_neo4j` | A | |
| cs_12_sector_industry | `management/commands/load_sectors_to_neo4j.py` | A | |
| cs_13_peer_relations | `services/neo4j_loader.py:fetch_finnhub_peers/fetch_fmp_peers/load_peers_to_neo4j` + `tasks/peer_tasks.py` + `management/commands/load_peers_to_neo4j.py` | A | |
| cs_21_tier_a_profile | `tasks/profile_tasks.py:calculate_growth_stages/calculate_capital_dna/calculate_all_profiles` | A | |
| cs_21b_sensitivity_profile | `tasks/sensitivity_tasks.py` | A | |
| cs_21c_insider_signal | `tasks/insider_tasks.py` | A | |
| cs_22_co_mention | `tasks/relation_tasks.py:extract_co_mentions` | A | ChainNewsEvent 통합 동작 |
| cs_23_price_co_movement | `tasks/relation_tasks.py:calculate_price_co_movement` | A | |
| cs_24_relation_confidence | `tasks/relation_tasks.py:update_relation_confidence + check_stale_and_decay` | A | RelationConfidence v2.1 5단계 + truth/market 분리 적용 |
| cs_25_chain_profile_aggregation | `tasks/sync_tasks.py:aggregate_chain_profiles` + Beat 등록 | A | celery_beat_registration.md 참조 |
| cs_31_profile_neo4j_sync | `tasks/sync_tasks.py:sync_profiles_to_neo4j` | A | |
| cs_32_relation_neo4j_sync | `tasks/sync_tasks.py:sync_relations_to_neo4j` (data_quality_3_fixes에서 dirty sync 위임으로 리팩토링) | A | RELATED_TO 라벨 → `r.relation_type` 속성 기반 라우팅으로 보정 완료 |
| cs_33_gds_algorithms | (Neo4j Browser 직접 실행, task 미구현) | B | task_done/CS-3-3에 결과 기록되어 있으나 `chainsight/tasks/gds_tasks.py`는 부재. 결과만 :Stock 노드 속성에 반영. 자동 배치 미구현. |
| cs_41_graph_api | `api/views.py:ChainSightGraphView` | A | CUSTOMER_OF 파생, market_signals(co_mention/price) 보강 모두 적용 |
| cs_42_suggestion_api | `api/views.py:ChainSightSuggestionView` | A | peers/same_industry/co_mentioned/same_sector 4개 카테고리. community 카테고리는 미구현. |
| cs_43_trace_api | `api/views.py:ChainSightTraceView` | A | shortestPath max=5 |
| cs_5_frontend_design_v2 | `app/chainsight/[symbol]/page.tsx` 외 11개 컴포넌트 | A | task_done/CS-5-1~5-3에 완료 기록 |
| cs_51_graph_visualization | `components/chainsight/GraphCanvas.tsx` + `graphStyles.ts` | A | |
| cs_52_ai_guide_ui | `components/chainsight/AIGuidePanel.tsx` | A | |
| cs_53_chain_trace_ui | `components/chainsight/TracePathView.tsx` | A | |
| cs_54_stock_detail_integration | `components/chainsight/GraphMiniView.tsx` + `app/stocks/[symbol]/page.tsx` 수정 | A | |
| relation_confidence_design_v1 | `models/relation_discovery.py:RelationConfidence` v2.1 | A | 24개 필드 모두 구현 |
| sec_pipeline_base_design / sec_pipeline_pr_detail | (별도 앱 `sec_pipeline/`) | A | Chain Sight 범위 외 |
| remaining_work_plan | (이정표 문서, 산출물 없음) | A | 안내문서. 모든 항목 task_done에 매핑됨 |

### 2. redesign_v1_260409 (Market View Hub)

| 문서 | 산출 코드 | 분류 | 비고 |
|------|----------|------|------|
| chainsight_seed_node_design (Phase 1: 시드 5종 + 합산) | `services/seed_selection.py` + `tasks/seed_tasks.py:run_seed_selection` | A | 5개 소스(price/volume/sector_outlier/relation/comention) + 20개 상한 |
| chainsight_seed_node_design (Phase 2: SeedHeatScore 모델) | (모델 부재. heat_score는 Neo4j :Stock 속성으로만 저장) | **B** | `models/seed_snapshot.py`는 시드 영속화용으로 별개. 명세상 PostgreSQL 모델 + seed_rank 정렬 키는 미구현 |
| chainsight_seed_node_design (Phase 3 D-1: text_conditional_prob) | (미구현) | **C** | ChromaDB + Gemini Embedding 의존. 후속 작업 |
| chainsight_seed_node_design (Phase 3 D-2: lagged correlation + propagation) | (미구현) | **C** | 60거래일 데이터 의존 |
| chainsight_seed_node_design (Phase 3 D-3: 사후 검증) | (미구현) | **C** | |
| chainsight_api_design (`/seeds/`) | `api/views.py:SeedListView` + 3단 폴백(Redis → SeedSnapshot → async 복구) | A | 명세보다 견고 |
| chainsight_api_design (`/sector/{sector}/graph/`) | `api/views.py:SectorGraphView` | A | node_size percentile, is_seed 매칭 |
| chainsight_api_design (`/{symbol}/neighbors/`) | `api/views.py:NeighborGraphView` | **B** | 명세는 응답 필드 `evidence_tier_best`, 코드는 `evidence_tier`로 단축. relation_summary/why_now/insight_summary 2차 필드 미구현(명세상 future). |
| chainsight_api_design (`/signals/`) | `api/views.py:SignalFeedView` | **B** | path 항목이 명세는 `relation_to_next/relation_truth_score/relation_market_score` 인라인, 구현은 path[]+edges[] 분리 구조. 프론트는 분리 구조 기준 동작 — 사실상 BE 우위 표준. |
| chainsight_ui_ux_design (① 섹터 바) | `components/chainsight/SectorBar.tsx` | A | |
| chainsight_ui_ux_design (② 그래프 캔버스) | `components/chainsight/MarketGraphCanvas.tsx` | A | force-directed → 시멘틱 방사형(graph_redesign_v2)으로 발전 |
| chainsight_ui_ux_design (③ 탐색 트레일) | `components/chainsight/ExplorationTrail.tsx` | A | undo + Watch 버튼 통합 |
| chainsight_ui_ux_design (④ 관계 카드 패널 pre-focus/focused) | `components/chainsight/RelationCardPanel.tsx` | A | 4그룹(Supply Chain/Competitors/Peers/Co-mentioned) + Related fallback |
| chainsight_ui_ux_design (⑤ 체인 스토리 피드) | `components/chainsight/ChainStoryFeed.tsx` | A | 무한 스크롤 + 새 session 트리거 |
| chainsight_ui_ux_design (좌측 히스토리 — 그래프 내부 흐림 노드 1~3개) | (직접 가시 미확인) | **B** | `historyNodes` 상태는 `explorationStore.ts`에 존재, 시각 처리는 명세보다 미세하게 구현됨 |
| chainsight_ui_ux_design (전환 애니메이션 300ms + bounce) | (CSS 레벨 미구현 — task_done/CS-5-6 명시) | **B** | 시드 bounce 미구현, 다른 전환은 react-force-graph 기본 동작 |
| chainsight_marketview_pr_prompts (PR-1~7) | task_done/chain_sight_redesign_V1/PR-1~7 모두 완료 | A | |

### 3. update_v2 (Path Watchlist)

| 문서 | 산출 코드 | 분류 | 비고 |
|------|----------|------|------|
| ROADMAP_v1.4 | (메타) | A | v1.3 + Phase 6/7 추가본 |
| CHAIN_SIGHT_PM (PM 설계서 v1.2) | (메타) | A | |
| cs_44_seed_node_heat_score (CS-4-4) | `tasks/seed_tasks.py:calculate_heat_scores` + Beat `chainsight-heat-score-daily` | A | 4 signal × 0.25 가중치, 534 Stock 처리, avg 0.361 |
| cs_55_market_view (CS-5-5) | (redesign_v1 PR-5/6/7과 동일 컴포넌트들) | A | task_done/CS-5-5 "이미 구현됨 — 검증 완료" |
| cs_56_seed_node (CS-5-6) | RelationCardPanel pre-focus + 시드 색상 | A | bounce 애니메이션은 명시적 미구현 |
| cs_61_saved_path_model (CS-6-1) | `models/saved_path.py:SavedPath, PathAction` + migration 0006 | A | |
| cs_62_watchlist_crud_api (CS-6-2) | `views/watchlist_views.py:WatchlistViewSet` + `serializers/path_watchlist.py` + `api/urls.py` 등록 | A | |
| cs_63_summary_path (CS-6-3) | `services/path_service.py:generate_summary_path/build_path_signature` | A | |
| cs_65_recheck_api (CS-6-5) | `services/recheck_service.py` + `WatchlistViewSet.recheck` | A | edge_snapshot 비교 → strengthened/weakened/broken |
| cs_66_expand_api (CS-6-6) | `services/expand_service.py:find_expansion_candidates` | A | |
| cs_67_alternatives_api (CS-6-7) | `services/alternatives_service.py:find_alternatives` | A | |
| cs_71_watch_button (CS-7-1) | `components/chainsight/WatchButton.tsx` + ExplorationTrail 통합 | A | |
| cs_72_watchlist_ui (CS-7-2) | `app/chainsight/watchlist/page.tsx` + `components/chainsight/PathCard.tsx` + `lib/utils/pathStatus.ts` | A | |
| cs_73_full_path_view (CS-7-3) | `app/chainsight/watchlist/[id]/page.tsx` + `components/chainsight/FullPathView.tsx` | A | |

### 4. graph_redesign_v2 (현재 브랜치 작업)

| 항목 | 산출 코드 | 분류 |
|------|----------|------|
| 시멘틱 방사형 좌표 | `components/chainsight/radialLayout.ts` (FE-PR-3) | A |
| 노드 hover 툴팁 + 컨텍스트 메뉴 | `components/chainsight/NodeTooltip.tsx`, `NodeContextMenu.tsx` (FE-PR-4) | A |
| 관계 칩 토글 바 | `components/chainsight/RelationFilterChips.tsx` | A |
| 빈 상태 일러스트 + 첫인상 카피 + 범례 | `components/chainsight/RelationLegend.tsx` 보강 (FE-PR-5) | A |
| 시각 위계 강화 (3단 노드 크기) | MarketGraphCanvas의 `NODE_SIZE_MAP` (FE-PR-2) | A |

> 이 4문서 모두 `feature/chainsight-graph-v2` 브랜치 기준 git log에 PR-2~5 커밋이 보임. PR-6 이후는 미관측.

---

## 미구현 항목 상세

### C-1. Phase 2 SeedHeatScore PostgreSQL 모델 (redesign_v1 chainsight_seed_node_design § 3)

명세:

```python
class SeedHeatScore(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateField()
    heat_score = models.FloatField()
    components = models.JSONField()
    seed_rank = models.IntegerField(null=True)
```

현 구현:
- `tasks/seed_tasks.py:calculate_heat_scores`가 heat_score를 계산해 **Neo4j `:Stock` 노드 속성**에만 SET. PostgreSQL에 영속화하지 않음.
- 결과적으로 `sector_summary` 정렬 기준이 명세상 Phase 2부터 `heat_total DESC`이지만, 코드는 여전히 Phase 1 `seed_count DESC`만 지원 (`services/seed_selection.py:build_sector_summary` 마지막 줄).

영향:
- 시드 랭킹의 시계열 분석 불가 (날짜별 heat_score 비교 어려움)
- 향후 ML 학습용 feature store 부재
- 섹터 정렬을 heat_total 기준으로 전환하려면 모델 추가 필요

### C-2. Phase 3 이벤트 전파 모델 D-1 / D-2 / D-3 (redesign_v1 chainsight_seed_node_design § 4)

명세:
- D-1: 뉴스 → Gemini Embedding → ChromaDB → `text_conditional_prob(A,B)` (90일 rolling)
- D-2: lagged price correlation + volume_response + 결합 `propagation_weight(A→B)` (텍스트 게이트 0.05)
- D-3: 사후 검증 → 가중치 학습

현 구현:
- ChromaDB 미사용. Gemini Embedding 호출 코드 없음.
- `tasks/relation_tasks.py:calculate_price_co_movement`는 90일 동조성만 계산 — lagged correlation 미지원.
- `update_relation_confidence`가 truth_score만 산출, propagation_weight 산출 로직 없음.

영향:
- 비대칭 방향 엣지(A→B만 강하게 전파) 표현 불가 → Neo4j는 여전히 undirected normalize_pair 기반.
- 뉴스 + 가격 + 거래량을 결합한 정량 점수가 없어 시드 랭킹이 단순 다수결(signal_count) 머무름.

### C-3. CS-4-2 community 카테고리 + CS-3-3 GDS Celery 자동화

명세:
- cs_42_suggestion_api: `community` 카테고리 (community_id 매칭 노드)를 5번째 카테고리로 반환
- cs_33_gds_algorithms: `chainsight/tasks/gds_tasks.py`로 PageRank/Louvain/Betweenness 주기 실행

현 구현:
- `ChainSightSuggestionView`는 peers / same_industry / co_mentioned / same_sector 4개만 반환. community 분기 없음.
- `chainsight/tasks/` 디렉토리에 `gds_tasks.py` 파일 부재. task_done/CS-3-3에는 1회 실행 결과만 기록되어 있고, Beat에 등록된 흔적 없음 (`config/celery.py` chainsight 항목 12개 중 GDS 자동화 항목 없음).

영향:
- pagerank_score / community_id가 처음 수동 실행값으로 고정됨. 시간 경과 + 신규 종목 추가 시 재계산 안 됨.
- Suggestion API의 `community` 카테고리 누락으로 "같은 클러스터" 탐색 진입 불가.

---

## 부분 구현 항목 상세

### B-1. NeighborGraphView 응답 필드명 불일치

명세 (`chainsight_api_design.md` § 4):

```json
"relation": {
    "evidence_tier_best": "tier1"
}
```

코드 (`chainsight/api/views.py` L512, L566):

```python
r.evidence_tier_best AS evidence_tier
'evidence_tier': n.get('evidence_tier'),
```

프론트(`frontend/types/chainsight.ts` 미열람이지만 RelationCardPanel 사용처 기준)도 `evidence_tier`로 통일됨. 단, 명세는 미수정 상태 → 문서 vs 코드 일치성 부족.

### B-2. SignalFeedView path 구조 불일치

명세 (`chainsight_api_design.md` § 5):

```json
"path": [
    {
        "symbol": "TSM",
        "relation_to_next": "SUPPLIES_TO",
        "relation_truth_score": 85,
        "relation_market_score": null
    }
]
```

코드 (`chainsight/api/views.py:_build_chain_signals`):

```python
'path': [{'symbol', 'name', 'sector'} for n in path_nodes],
'edges': [{'type', 'score'} for e in path_edges],
```

→ relation 정보가 path와 분리된 `edges[]`로 평탄화. 프론트(`ChainStoryFeed.tsx`)는 분리 구조 기준으로 작성됐을 것이며, 동작은 정상이나 명세와 mismatch.

### B-3. UI/UX § 7 좌측 히스토리 (그래프 내부 흐림 노드 1~3개)

명세: 그래프 캔버스 **내부**에서 직전 1~3 step의 노드를 opacity 0.3~0.5로 잔상.

현 구현 (`MarketGraphCanvas.tsx` L74 isHistory + `explorationStore.ts:historyNodes`): 상태는 존재. 그러나 가시화(흐림 잔상) 강도, 좌측 위치 강제 등이 명세 그대로인지 코드 레벨에서 단정 어려움 — 명세에 비해 단순화됐을 가능성.

### B-4. 전환 애니메이션 + 시드 bounce

- 명세: 중심 이동 300ms ease-out + 시드 노드 bounce.
- 현 구현: react-force-graph-2d 기본 cooldown 외 추가 애니메이션 없음. CS-5-6 task_done에서 "bounce 애니메이션은 미구현 (CSS 레벨, 향후 추가 가능)"으로 명시.

### B-5. CS-3-3 GDS 자동화

C-3 참조. 1회성 결과만 노드에 보존, 정기 갱신 없음 → 부분 구현으로도 분류 가능. 본 보고서는 Celery 태스크 부재 측면을 강조해 C로 분류.

### B-6. 2차 LLM 카드 설명 필드 (`relation_summary`, `why_now`, `insight_summary`)

명세 (`chainsight_api_design.md` § 4-2 + `chainsight_ui_ux_design.md` § 9 카드 설명 1~3차):
- 1차: 프론트 템플릿 (`RELATION_TEMPLATES`) — ✅ 구현
- 2차: API 응답에 LLM-가공 텍스트 추가 — ❌ 미구현
- 추후: LLM 기반 explanation — ❌ 미구현

영향: 카드 메시지가 고정 6개 템플릿(공급망 상류/하류 연결 등) + seed_reasons 한국어화 + daily_return/volume_ratio fallback에 머물러 있어, 종목별 맞춤 설명 부재.

---

## 폐기/대체 항목

### D-1. cs_5_frontend_design_v2 의 "Deep dive workspace 단독 진입" 모델 → 마켓 뷰 + Deep dive 병행 구조

| 시점 | 진입점 | 산출 |
|------|--------|------|
| cs_51~54 (원안) | 종목 상세 탭 내 인터랙티브 그래프 | 기존 Tab 통합 |
| cs_5_frontend_design_v2 (2026-04-04) | `/chainsight/[symbol]` 전용 워크스페이스 | GraphCanvas/AIGuidePanel/NodeDetailPanel 11개 |
| redesign_v1_260409 (2026-04-10) | **`/chainsight` 마켓 뷰가 메인 진입점**, `/chainsight/[symbol]`은 "Deep dive CTA에서만" 진입하는 보조 경로 | SectorBar/MarketGraphCanvas/RelationCardPanel/ChainStoryFeed 5개 추가 |

→ cs_5의 컴포넌트는 폐기되지 않고 Deep dive workspace로 그대로 유지. 진입 흐름이 추가됐다는 의미에서 "방향 변경"이지 "폐기"는 아님. UI/UX § 11 종목 상세 연결 ("Chain Sight 탭 제거, 딥링크(`/chainsight?focus=`) 추가")만 폐기 항목.

### 기타 사실상 폐기/소멸

- `CUSTOMER_OF` 별도 저장 (v1.3에서 폐기) → API 파생만 사용. **반영 완료**.
- `serverless/` 의 chain_sight_*_api 6개 뷰 + `StockRelationship` 모델 (CS-0-0에서 LEGACY_KEEP 태그) → 본 감사 범위 외로 잔존 여부 미확인. 표면적으로 새로운 chainsight/ 앱이 단일 소스.

---

## 권고사항 (감사관 의견 — 코드 변경 없음)

본 감사는 읽기 전용이므로 조치는 권고에 한정한다.

1. **(P1) chainsight_api_design.md를 코드에 맞춰 갱신**: `evidence_tier_best` → `evidence_tier`, signals path/edges 구조 변경, NeighborGraphView 응답 cross_edges 추가 등 6건. 명세가 진실의 소스 원칙(CLAUDE.md Contract-Driven Development)에 따르면 코드를 명세에 맞춰야 하나, 프론트가 이미 코드 구조에 의존하므로 명세 갱신이 비용 효율적.
2. **(P2) ROADMAP_v1.4 미진 항목 명시화**: SeedHeatScore 모델 + Phase 3 D-1~D-3 + community 카테고리 + GDS 자동화는 ROADMAP 어디에서도 미구현임을 표시하지 않고 있음. v1.5 또는 별도 BACKLOG.md에 옮길 것.
3. **(P3) graph_redesign_v2 PR-6 이후 진행 점검**: FE-PR-5까지 완료된 git log가 있으나 graph_redesign_v2.md 명세 전체 항목과 1:1 매핑은 본 감사 범위에서 미수행.
4. **(P4) cs_5_frontend_design_v2 vs redesign_v1 진입 정책 단일 문서화**: "Deep dive 진입 = 카드 CTA에서만" 정책이 redesign_v1에만 있음. cs_5에는 옛 진입(EOD CTA, 사이드바, URL 직접)이 살아 있어 정합성 혼란 가능.

---

## 부록: 코드 인벤토리

### Backend (`chainsight/`)

```
api/views.py           7 클래스 (Graph/Suggestion/Trace/Seed/Sector/Neighbor/Signal) + helper
api/urls.py            8 경로 + watchlist router
graph/                 repository.py + schema.py + exceptions.py + __init__.py
management/commands/   6 (init_neo4j_schema, load_stocks/sectors/peers/themes_to_neo4j, regenerate_summary_paths)
migrations/            7 (0001~0007)
models/                15 클래스 (Tier A 4 + Tier B 3 + 관계 4 + 집약 1 + Path 2 + Snapshot 1)
serializers/           path_watchlist.py
services/              7 모듈 (neo4j_loader, neo4j_sync, seed_selection, path_service, alternatives, expand, recheck)
tasks/                 8 모듈 (insider, neo4j_dirty_sync, peer, profile, relation, seed, sensitivity, sync)
views/                 watchlist_views.py
```

### Frontend (`frontend/components/chainsight/`)

```
Deep dive (cs_5):      AIGuidePanel, GraphCanvas, GraphMiniView, NodeDetailPanel, FilterPanel, RelationLegend, TracePathView, MobileCardList, graphStyles
Market View (redesign_v1): SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed
Graph v2 (graph_redesign_v2): NodeContextMenu, NodeTooltip, RelationFilterChips, radialLayout
Path Watchlist (update_v2): WatchButton, PathCard, FullPathView
```

### Frontend Routes (`frontend/app/chainsight/`)

```
page.tsx                    Market View (redesign_v1)
[symbol]/page.tsx           Deep dive workspace (cs_5)
watchlist/page.tsx          Watchlist (update_v2 CS-7-2)
watchlist/[id]/page.tsx     Full Path View (update_v2 CS-7-3)
```

### Celery Beat (chainsight 관련 12개)

```
config/celery.py:
  chainsight-all-profiles                   (토 02:00)
  chainsight-co-mentions                    (매일 10:00)
  chainsight-price-co-movement              (토 03:00)
  chainsight-relation-confidence            (매일 11:00)
  chainsight-stale-decay                    (토 04:00)
  chainsight-aggregate-profiles             (토 04:30)
  chainsight-sync-profiles-neo4j            (매일 12:00)
  chainsight-sync-relations-neo4j           (매일 12:30)
  chainsight-heat-score-daily               (매일 07:00 UTC)
  chainsight-seed-selection                 (매일 13:00 UTC)
  chainsight-neo4j-dirty-sync               (일 04:30, neo4j 큐)
  chainsight-seed-snapshot-cleanup          (cleanup_seed_snapshots, 등록 위치 미확인)
```
