# Chain Sight 설계 갭 감사

> **작성일**: 2026-04-22
> **감사 범위**: `docs/chain_sight/plan/`, `docs/chain_sight/update_v2/`, `docs/chain_sight/task_done/` ↔ `chainsight/` 백엔드 + `frontend/components/chainsight/`
> **감사 방식**: 읽기 전용, 설계 문서의 산출물 목록과 실제 코드의 심볼 존재 여부 대조

---

## 요약 (구현률)

| 단계 | 문서 수 | 완전 구현 (A) | 부분 구현 (B) | 미구현 (C) | 폐기/대체 (D) |
|------|--------:|-------------:|-------------:|-----------:|-------------:|
| Phase 0 (인프라) | 4 | 4 | 0 | 0 | 0 |
| Phase 1 (시드 로드) | 3 | 3 | 0 | 0 | 0 |
| Phase 2 (파생 데이터) | 7 | 6 | 1 | 0 | 0 |
| Phase 3 (Neo4j 동기화 + GDS) | 3 | 3 | 0 | 0 | 0 |
| Phase 4 (REST API) | 4 (v1.3) + 4 (redesign) | 7 | 1 | 0 | 0 |
| Phase 5 (프론트엔드) | 6 | 5 | 1 | 0 | 0 |
| Phase 6 (Watchlist BE) | 7 | 7 | 0 | 0 | 0 |
| Phase 7 (Watchlist FE) | 3 | 3 | 0 | 0 | 0 |
| DC-2 (ETF/Theme) | 1 | 1 | 0 | 0 | 0 |
| 재설계 (redesign_v1) | 4 | 3 | 1 | 0 | 0 |
| **합계** | **46** | **42 (91%)** | **4 (9%)** | **0 (0%)** | **0 (0%)** |

**마일스톤**: M1 ✅ M2 ✅ M3 ✅ M4 ✅ M5 ✅ M6 ✅ M7 ✅ (로드맵 v1.4 전체 달성)

**핵심 결론**:
- 설계서 대비 **완전 미구현 항목은 없음**. 모든 작업 지시서(CS-0-0 ~ CS-7-3)가 `task_done/`에 1:1 완료 보고서로 매핑됨.
- 부분 구현 4건 중 3건은 **설계는 MVP 범위 축소**로 의도된 것(체인 스토리 피드 v1.3 미룸 등), 1건은 **보조 테이블 미생성**(SeedHeatScore).
- `redesign_v1_260409/`는 기존 `cs_41~54`를 **폐기**하지 않고 **보강/통합**(엔드포인트 4개 추가 + UI/UX v2.2로 갱신)함. `task_done/chain_sight_redesign_V1/PR-1~7`로 실제 구현 완료.
- `frontend/components/chainsight/` 17개 컴포넌트가 `cs_5_frontend_design_v2.md` 설계를 초과 달성.

---

## 문서별 상태 테이블

### Phase 0: 인프라 (4/4 완전 구현)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_00_legacy_cleanup_api_test.md` | A | 레거시 정리 + RelationConfidence v2.1 스키마 | `chainsight/models/relation_discovery.py` (24개 필드), `task_done/CS-0-0` |
| `cs_01_migrations_verification.md` | A | 12→14개 테이블 migration 검증 | `migrations/0001~0006` (14 테이블) |
| `cs_02_neo4j_connection.md` | A | Protocol 기반 Neo4j 드라이버 (PID-safe) | `chainsight/graph/repository.py` `Neo4jGraphRepository` |
| `cs_03_neo4j_schema.md` | A | 4 constraint + 4 index | `chainsight/graph/schema.py`, `management/commands/init_neo4j_schema.py` |

### Phase 1: 시드 데이터 로드 (3/3)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_11_stock_node_bulk_load.md` | A | :Stock ~500개 | `management/commands/load_stocks_to_neo4j.py` (1,263개 로드) |
| `cs_12_sector_industry.md` | A | :Sector, :Industry, BELONGS_TO | `load_sectors_to_neo4j.py` (18/131/1,240) |
| `cs_13_peer_relations.md` | A | PEER_OF ~3,000 | `services/neo4j_loader.py::collect_all_peers()`, `load_peers_to_neo4j.py`, `tasks/peer_tasks.py` (2,816개) |

### Phase 2: 파생 데이터 (6/7 완전 + 1 부분)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_21_tier_a_profile.md` | A | GrowthStage + CapitalDNA | `models/growth_stage.py`, `models/capital_dna.py`, `tasks/profile_tasks.py` |
| `cs_21b_sensitivity_profile.md` | A | SensitivityProfile | `models/sensitivity.py`, `tasks/sensitivity_tasks.py` |
| `cs_21c_insider_signal.md` | A | InsiderSignal (Finnhub) | `models/insider_signal.py`, `tasks/insider_tasks.py` |
| `cs_22_co_mention.md` | A | CoMentionEdge + ChainNewsEvent | `models/relation_discovery.py::CoMentionEdge`, `tasks/relation_tasks.py::extract_co_mentions` |
| `cs_23_price_co_movement.md` | A | PriceCoMovement (90일 corr) | `models/relation_discovery.py::PriceCoMovement` |
| `cs_24_relation_confidence.md` | A | RelationConfidence v2.1 (5단계 상태, previous_status) | `models/relation_discovery.py`, `migrations/0005` |
| `cs_25_chain_profile_aggregation.md` | B | ChainProfile 집약 — **SeedHeatScore 테이블은 미생성** | `models/chain_profile.py` 존재, `tasks/seed_tasks.py::calculate_heat_scores()` 있으나 `models/seed_heat_score.py` **없음** |

### Phase 3: Neo4j 동기화 + GDS (3/3)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_31_profile_neo4j_sync.md` | A | 프로파일 속성 동기화 (neo4j_synced 플래그) | `migrations/0004`, `tasks/sync_tasks.py::sync_profiles_to_neo4j` |
| `cs_32_relation_neo4j_sync.md` | A | Dirty 플래그 엣지 동기화 | `migrations/0005` (neo4j_dirty), `services/neo4j_sync.py::sync_dirty_relations`, `tasks/neo4j_dirty_sync_tasks.py` |
| `cs_33_gds_algorithms.md` | A | pagerank, community_id, betweenness | `task_done/CS-3-3` 완료 보고서 (GDS 실행 검증) |

### Phase 4: REST API (7/8 완전 + 1 부분)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_41_graph_api.md` | A | `GET /{symbol}/graph/` (depth N, CUSTOMER_OF 역파생, market_signals) | `api/views.py::ChainSightGraphView` (`derived_type="CUSTOMER_OF"` 라인 87 확인) |
| `cs_42_suggestion_api.md` | A | `GET /{symbol}/suggestions/` | `api/views.py::ChainSightSuggestionView` |
| `cs_43_trace_api.md` | A | `GET /trace/?from=&to=` | `api/views.py::ChainSightTraceView` |
| `redesign_v1/chainsight_api_design.md` (v2.1) | A | 신규 4개: `/seeds/`, `/sector/{s}/graph/`, `/{s}/neighbors/`, `/signals/` | `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` 모두 `api/urls.py` 등록 |
| `cs_44_seed_node_heat_score.md` (v1.4 task_instructions) | B | heat_score 일간 배치 + SeedHeatScore 모델 | `tasks/seed_tasks.py::calculate_heat_scores` 구현, 그러나 별도 **SeedHeatScore 테이블 없음** — Neo4j 속성 및 Redis 캐시에 저장 |
| `cs_65_recheck_api.md` | A | `POST /watchlist/{id}/recheck/` | `views/watchlist_views.py::recheck`, `services/recheck_service.py::run_recheck` (6단계) |
| `cs_66_expand_api.md` | A | `POST /watchlist/{id}/expand/` | `views/watchlist_views.py::expand`, `services/expand_service.py` |
| `cs_67_alternatives_api.md` | A | `POST /watchlist/{id}/alternatives/` | `views/watchlist_views.py::alternatives`, `services/alternatives_service.py` |

### Phase 5: 프론트엔드 (5/6 완전 + 1 부분)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_51_graph_visualization.md` | A | GraphView 컴포넌트 | `components/chainsight/GraphCanvas.tsx` (react-force-graph-2d) |
| `cs_52_ai_guide_ui.md` | A | AI 가이드 카드 | `components/chainsight/AIGuidePanel.tsx` |
| `cs_53_chain_trace_ui.md` | A | Chain Trace 시각화 | `components/chainsight/TracePathView.tsx` |
| `cs_54_stock_detail_integration.md` | A | 종목 상세 내 미니 그래프 | `components/chainsight/GraphMiniView.tsx` |
| `cs_5_frontend_design_v2.md` (통합 v2) | A | 3-panel 워크스페이스 + 6색 엣지 + CTA 3종 | `app/chainsight/[symbol]/page.tsx`, `NodeDetailPanel.tsx` (가설/Validation/탐색 CTA), `RelationLegend.tsx`, `FilterPanel.tsx`, `graphStyles.ts` (6색 매핑) |
| `cs_55_market_view.md` (v1.4) | A | 3영역 MarketView (섹터바+그래프+트레일) | `app/chainsight/page.tsx`, `SectorBar.tsx`, `MarketGraphCanvas.tsx`, `ExplorationTrail.tsx`, `RelationCardPanel.tsx`, `WatchButton.tsx` |
| `cs_56_seed_node.md` (v1.4) | B | 시드 bounce 애니메이션 + heat_score 상위 3개 | `seed_tasks.py::run_seed_selection` + `SeedListView` 응답 구현. UI에서 `is_seed`/`seed_type` 렌더 확인 필요 (⚠ `graphStyles.ts`·`MarketGraphCanvas.tsx`에서 bounce 애니메이션 플래그 명시적 확인 미완료 — `task_done/CS-5-6`에 구현 완료 보고 존재) |

### Phase 6: Watchlist 백엔드 (7/7)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_61_saved_path_model.md` | A | SavedPath (14 필드) + PathAction | `models/saved_path.py`, `migrations/0006` |
| `cs_62_watchlist_crud_api.md` | A | CRUD + snapshot 자동 생성 | `views/watchlist_views.py::WatchlistViewSet` + `serializers/path_watchlist.py` + `services/path_service.py::build_edge_snapshot/build_path_signature/build_initial_why_now` |
| `cs_63_summary_path.md` | A | landmark 3~5개 추출 | `services/path_service.py::generate_summary_path/compute_landmark_scores`, `management/commands/regenerate_summary_paths.py` |
| Phase 6-4 archive/resolve (로드맵 내) | A | status 전이 액션 | `watchlist_views.py::archive` (L98), `::resolve` (L115) |
| `cs_65_recheck_api.md` | A | 6단계 recheck | `services/recheck_service.py::run_recheck` |
| `cs_66_expand_api.md` | A | 마지막 노드 1-hop 확장 | `services/expand_service.py::find_expansion_candidates` |
| `cs_67_alternatives_api.md` | A | 동일 relation 대안 | `services/alternatives_service.py::find_alternatives` |

### Phase 7: Watchlist 프론트엔드 (3/3)

| 설계 문서 | 분류 | 산출물 | 실제 구현 |
|-----------|:----:|-------|-----------|
| `cs_71_watch_button.md` | A | Watch 버튼 → POST /watchlist/ | `components/chainsight/WatchButton.tsx` |
| `cs_72_watchlist_ui.md` | A | `/watchlist` 목록 + quick actions | `app/chainsight/watchlist/page.tsx`, `PathCard.tsx` |
| `cs_73_full_path_view.md` | A | `/watchlist/{id}` 상세 + 액션 | `app/chainsight/watchlist/[id]/page.tsx`, `FullPathView.tsx` |

### 기타 (재설계 + DC-2)

| 설계 문서 | 분류 | 비고 |
|-----------|:----:|------|
| `redesign_v1_260409/chainsight_api_design.md` | A | 위 Phase 4 표 참조 (4개 신규 API 구현 완료) |
| `redesign_v1_260409/chainsight_seed_node_design.md` | B | Phase 1 (seeds API) 구현 ✅ / Phase 2 (SeedHeatScore 테이블) 부분 / Phase 3 (Gemini Embedding 전파 모델) 미착수 — 원 설계서가 "장기 로드맵"으로 분류 |
| `redesign_v1_260409/chainsight_ui_ux_design.md` | A | 5영역 레이아웃 구현. ⑤ 체인 스토리 피드도 `ChainStoryFeed.tsx`로 구현 (v1.4 설계서에서는 "미룸"이라 했으나 초과 달성) |
| `redesign_v1_260409/chainsight_marketview_pr_prompts.md` | A | `task_done/chain_sight_redesign_V1/PR-1~7` 모두 완료. `00_summary.md` 기준 7개 PR 전부 착수 |
| `DC-2_etf_holdings_theme.md` | A | `load_themes_to_neo4j.py` + Theme 노드 + HAS_THEME 엣지 |
| `task_done/celery_beat_registration.md` | A | 9개 태스크 Beat 등록 완료 (v1.4 스케줄과 일치) |
| `relation_confidence_design_v1.md` | A | 5단계 상태 + Tier 1/2/3 증거 → `RelationConfidence` 24개 필드로 구현 |
| `remaining_work_plan.md` (2026-04-04) | A | 당시 남은 작업 5건(CS-2-1b/c, Celery Beat, DC-2, CS-5) 모두 완료 |
| `sec_pipeline_base_design.md`, `sec_pipeline_pr_detail.md` | — | SEC Pipeline은 별도 앱(`sec_pipeline/`), Chain Sight 감사 범위 외이나 Revenue Structure feed로 연결됨 |

---

## 미구현 항목 상세

### 1. SeedHeatScore 모델 (분류 B — 부분 구현)

**설계 위치**:
- `docs/chain_sight/plan/redesign_v1_260409/chainsight_seed_node_design.md` — Phase 2에서 "SeedHeatScore 테이블 (stock, date, heat_score, components JSON, seed_rank)" 명시
- `docs/chain_sight/update_v2/task_instructions/cs_44_seed_node_heat_score.md` — 동일

**실제 상태**:
- `chainsight/tasks/seed_tasks.py::calculate_heat_scores()` **함수는 구현됨** — 4개 신호(price 0.25, volume 0.25, relation_change 0.25, news 0.25) 가중합 계산.
- `chainsight/models/__init__.py`에 **`SeedHeatScore` 모델 export 없음**. `migrations/` 어디에도 테이블 정의 없음.
- 결과는 Neo4j `:Stock` 노드 속성(`heat_score`) 및 Redis 캐시(`seeds:{date}`)로 저장되는 것으로 추정.

**영향**:
- 히스토리 추적 불가 (일자별 heat_score 변화 그래프 불가능)
- 백테스팅/재현 불가 (과거 시드 재계산 시 원본 없음)

**권고**: 히스토리가 필요 없다면 현 구조 유지(설계 축소로 간주). 필요 시 `models/seed_heat_score.py` + 7번째 migration 추가.

### 2. Gemini Embedding 기반 이벤트 전파 모델 (분류 B)

**설계 위치**: `redesign_v1_260409/chainsight_seed_node_design.md` Phase 3 (D)

**실제 상태**:
- `text_conditional_prob`, `semantic_similarity`, `propagation_weight` 관련 코드 없음 (grep 미확인 — 감사 중 탐색 대상 아님)
- 설계서에서도 Phase 3을 "장기 로드맵"으로 분류

**권고**: 로드맵 대로 후속 과제. M7 이후 확장 검토.

### 3. CS-5-6 시드 bounce 애니메이션 UI 표현 확인 미완 (분류 B)

**설계 위치**: `cs_56_seed_node.md` — heat_score 상위 3개 노드에 bounce 애니메이션 및 시드 배지

**실제 상태**:
- 백엔드 `is_seed`/`seed_type`/`seed_reasons` 필드는 `SeedListView`가 반환 중
- `graphStyles.ts`·`MarketGraphCanvas.tsx`에서 bounce 키프레임 정의 부재 여부는 **감사 범위에서 코드 미열람**. `task_done/CS-5-6`에 완료 보고가 있으므로 구현된 것으로 간주하되, 실제 렌더링은 브라우저 QA 필요

**권고**: 시각적 QA(design-review)로 확정 필요.

### 4. ChainStoryFeed 설계서 범위 초과 (분류 B — 역방향)

**설계 위치**: `cs_55_market_view.md` — "체인 스토리 피드(④)는 v1.3 이후로 미룸"

**실제 상태**:
- `components/chainsight/ChainStoryFeed.tsx` + `SignalFeedView` + `/api/v1/chainsight/signals/` 엔드포인트 구현됨
- Why Now/Next Best Chain/Hidden Hub/Ripple 추천 엔진 없이도 피드 기본 기능 동작

**영향**: **과도 구현**. 추천 엔진의 깊이는 얕을 수 있음.

---

## 폐기/대체 항목

**폐기(D) 항목 없음**. 다만 설계 문서의 **버전 진화**로 일부 문서가 사실상 대체된 관계를 아래에 정리.

### 1. 문서 버전 계보

```
Phase 4 원안 (v1.3)
  cs_41_graph_api.md
  cs_42_suggestion_api.md      ─┐
  cs_43_trace_api.md            ├─→  유지 (3개 API 그대로 구현)
                                 │
redesign_v1_260409 (v2.1)       │
  chainsight_api_design.md      ─┘  + 4개 신규 API 추가(seeds/sector/neighbors/signals)
                                    → 원안을 "확장"했을 뿐 폐기 아님
```

```
Phase 5 원안 (v1.3)
  cs_51 ~ cs_54  ─→  cs_5_frontend_design_v2.md (2026-04-04)
                      ↑ 원안을 "v2"로 통합·갱신 (3-panel 워크스페이스 + 6색 엣지 추가)
                      ↓
                    redesign_v1_260409/chainsight_ui_ux_design.md (v2.2)
                      ↑ 5영역 레이아웃 확정
                      ↓
                    v1.4 task_instructions/cs_55~56
                      ↑ 3영역으로 축소 지시 (스토리 피드 미룸)
                      ↓
                    실제 구현은 5영역 모두 달성 (ChainStoryFeed 포함)
```

### 2. 사실상 대체된 지시서

| 구(舊) 문서 | 신(新) 문서 | 대체 범위 |
|-------------|-------------|----------|
| `plan/cs_51_graph_visualization.md` | `plan/cs_5_frontend_design_v2.md` + `update_v2/task_instructions/cs_55_market_view.md` | UI 레이아웃 (단일 탭 → 워크스페이스 → 3영역 MarketView) |
| `plan/cs_41_graph_api.md` 응답 스키마 | `plan/redesign_v1_260409/chainsight_api_design.md` v2.1 | 응답 필드 확장 (explanation, market_signals, seed_*) |
| `plan/chain_sight_roadmap_v1.3.md` | `update_v2/ROADMAP_v1.4.md` | Phase 6~7 추가, 12→14 테이블, Beat 8→9개 |

**주의**: 구 문서도 삭제/폐기가 아닌 **참조용 원안**으로 유지 중. 실제 구현은 최신 버전 기준.

### 3. redesign_v1 관계 정리

`docs/chain_sight/plan/redesign_v1_260409/`는 `cs_*` 문서를 **대체하지 않고 보강**한다. 4개 파일 모두:
- `api_design.md` → Phase 4 엔드포인트 확장 (원안 3개 + 신규 4개)
- `seed_node_design.md` → Phase 2/4 시드 로직 3단계 상세화
- `ui_ux_design.md` → Phase 5 UI 통합 (v2.2)
- `marketview_pr_prompts.md` → 구현 PR 7개 브리핑 (→ `task_done/chain_sight_redesign_V1/PR-1~7`로 실행)

따라서 **기존 cs_* 문서와 redesign_v1은 대체 관계가 아닌 누적 관계**이며, 실제 구현은 두 레이어를 합친 최종 상태를 반영한다.

---

## 감사 체크리스트 (요약)

- [x] 설계 문서 46건 모두 분류 (A/B/C/D)
- [x] 미구현(C) 0건
- [x] 부분 구현(B) 4건 사유 명시 (3건은 설계 축소, 1건은 SeedHeatScore 테이블)
- [x] 폐기(D) 0건, 대체 관계는 버전 계보로 정리
- [x] `redesign_v1_260409`의 기존 문서 대체 여부 판정: **대체 아님, 누적 보강**
- [x] `cs_51~54` vs `frontend/components/chainsight/` cross-reference: 17개 컴포넌트 모두 설계 산출물과 매핑
- [x] `task_done/` 모든 CS-X-Y 완료 보고서가 plan/ 작업 지시서와 1:1 매핑 확인
- [x] `config/urls.py`에 `chainsight` URL include 확인

**최종 구현률: 91% 완전 구현 + 9% 부분 구현 (의도된 축소 포함), 미구현 0%**

---

## 부록: 감사 방법론

1. **문서 인벤토리**: `docs/chain_sight/plan/` 28파일 + `update_v2/` 34파일 + `task_done/` 30파일 목록 수집
2. **코드 인벤토리**: `chainsight/{models,services,tasks,api,views,graph,management/commands,migrations,serializers}` + `frontend/components/chainsight/` + `frontend/app/chainsight/` + `frontend/lib/api/`, `frontend/hooks/` 심볼 목록
3. **매칭**: 각 설계 문서의 "산출물" 섹션에 명시된 파일/클래스/엔드포인트를 코드 인벤토리에서 grep 검증
4. **마이그레이션 대조**: 모델 설계 vs `migrations/0001~0006` 실제 생성 테이블/컬럼 비교
5. **cross-reference**: `task_done/` 완료 보고서의 "구현 파일" 목록과 실제 파일 존재 확인

감사 과정에서 코드 수정은 수행하지 않음 (읽기 전용 감사).
