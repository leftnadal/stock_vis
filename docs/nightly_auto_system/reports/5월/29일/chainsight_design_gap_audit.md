# Chain Sight 설계 갭 감사

> 읽기 전용 감사 보고서 (코드 수정 없음)
> 작성: 2026-05-29 야간 자동화 세션
> 범위: `docs/chain_sight/` 설계 문서 전체 vs `chainsight/` + `frontend/.../chainsight` 구현
> 방법: 설계 항목 인벤토리 추출 → 실제 코드 인벤토리 대조 → 직접 grep 검증

---

## 요약 (구현률)

### 핵심 결론

1. **설계 문서는 3세대 계보다.** 사용자가 지정한 `plan/`은 1·2세대이며, **실제 구현의 진실 소스는 `update_v2/ROADMAP_v1.4`(3세대)**다. `plan/`만으로는 코드에 존재하는 watchlist·Phase 2/3·heat_score의 설계 출처를 설명할 수 없어, 감사 범위에 `update_v2/`와 `graph_redesign_v2.md`를 포함했다.

2. **`redesign_v1_260409/`는 cs_* 문서를 "대체"하지 않는다.** redesign_v1은 *마켓 뷰(`/chainsight`) 1개 화면*만 다루는 부분 설계다. cs_* 전체를 대체·흡수한 것은 `update_v2/ROADMAP_v1.4`이며, redesign_v1의 마켓 뷰는 v1.4의 Phase 5(CS-5-5/5-6)로 편입되었다.

3. **전체 구현률은 높다(약 90%).** Phase 0·1·4·5·6·7은 사실상 완전 구현. **유일한 명확한 코드 갭은 CS-3-3 GDS 알고리즘 자동화**다 — task_done엔 "완료(수치 검증)"로 기록됐으나 실제로는 일회성 수동 Cypher 실행만 했고, 반복 실행 코드(`gds_tasks.py`)·관리 커맨드·Celery Beat 등록·`community_id`/`pagerank_score` 영속화 코드가 **전부 부재**하다.

### Phase별 구현률 (ROADMAP_v1.4 기준)

| Phase | 내용 | 분류 | 비고 |
|-------|------|------|------|
| Phase 0 | 인프라·스키마·Neo4j 연결 | **(A) 완전** | 마이그레이션 0001~0008, graph/repository·schema 구현 |
| Phase 1 | 노드/Peer 로드 | **(A) 완전** | management command 4종 + peer task |
| Phase 2 | 프로파일·관계 신뢰도 엔진 | **(A) 완전** | profile/relation/sensitivity/insider task 전부 구현 + Beat 등록 |
| Phase 3 | Neo4j 동기화 + GDS | **(B) 부분** | 동기화(3-1/3-2)는 완전 / **GDS(3-3) 자동화 미구현** |
| Phase 4 | 그래프/제안/추적 API + heat_score | **(A) 완전** | View 7종 + `calculate_heat_scores` + Beat |
| Phase 5 | 코어 프론트엔드 (그래프·마켓뷰·시드) | **(A) 완전** | 컴포넌트 21개 / bounce 애니메이션 등 일부 미세 항목만 미완 |
| Phase 6 | Path Watchlist 백엔드 | **(A) 완전** | SavedPath/PathAction + CRUD + recheck/expand/alternatives |
| Phase 7 | Path Watchlist 프론트엔드 | **(A) 완전** | WatchButton·PathCard·FullPathView + 라우트 2개 |

### redesign_v1 (마켓 뷰 PR-1~7) 구현률

| | 분류 | 비고 |
|--|------|------|
| PR-1~7 전체 | **(A) 완전** | 마켓 뷰 API 4종 + FE 컴포넌트 5종 전부 구현, v1.4 Phase 5로 편입됨 |

---

## 문서별 상태 테이블

### 문서 계보 (3세대)

| 세대 | 위치 | 성격 | 현재 위상 |
|------|------|------|----------|
| 1세대 | `plan/cs_00~54` + `plan/chain_sight_roadmap_v1.3.md` | 초기 단계별 설계 (Phase 0~5) | **대체됨** → `update_v2/task_instructions/`로 재구성 |
| 2세대 | `plan/redesign_v1_260409/` (4문서) | 마켓 뷰 1화면 리디자인 (PR-1~7) | **흡수됨** → v1.4 Phase 5(CS-5-5/5-6) |
| 3세대 | `update_v2/ROADMAP_v1.4.md` + `update_v2/task_instructions/cs_*` (Phase 0~7) | **최신 확정 설계** (진실 소스) | **활성** |
| 보완 트랙 | `graph_redesign_v2.md` (38KB) | 그래프 시각 UI 재설계 (시멘틱 방사형 레이아웃) | Phase 5 시각 트랙으로 활성 |

### plan/cs_* (1세대) — 구현 대조

| 문서 | 설계 항목 | 코드 위치 | 분류 |
|------|----------|-----------|------|
| cs_00 legacy_cleanup | 레거시 제거 + API 테스트 5종 | (정리 완료) | (A) |
| cs_01 migrations | 12개 테이블 | `migrations/0001~0003` | (A) |
| cs_02 neo4j_connection | repository.py Protocol + Neo4jGraphRepository | `graph/repository.py` | (A) |
| cs_03 neo4j_schema | constraint 4 + index | `graph/schema.py`, `init_neo4j_schema` | (A) |
| cs_11 stock_node | load_stocks_to_neo4j | `management/commands/load_stocks_to_neo4j.py` | (A) |
| cs_12 sector_industry | load_sectors_to_neo4j | `management/commands/load_sectors_to_neo4j.py` | (A) |
| cs_13 peer_relations | load_peers + task | `load_peers_to_neo4j.py` + `peer_tasks.py` | (A) |
| cs_21 tier_a_profile | GrowthStage/CapitalDNA task | `profile_tasks.py` | (A) |
| cs_21b sensitivity | SensitivityProfile | `sensitivity_tasks.py::calculate_sensitivity_profiles` | (A) ※주1 |
| cs_21c insider_signal | InsiderSignal | `insider_tasks.py::calculate_insider_signals` | (A) ※주1 |
| cs_22 co_mention | extract_co_mentions | `relation_tasks.py` | (A) ※주1 |
| cs_23 price_co_movement | calculate_price_co_movement | `relation_tasks.py` | (A) ※주1 |
| cs_24 relation_confidence | update_relation_confidence + decay | `relation_tasks.py` | (A) ※주1 |
| cs_25 chain_profile_agg | aggregate_chain_profiles | `sync_tasks.py` | (A) ※주1 |
| cs_31 profile_neo4j_sync | sync_profiles_to_neo4j | `sync_tasks.py` | (A) |
| cs_32 relation_neo4j_sync | sync_relations_to_neo4j | `sync_tasks.py` + `neo4j_sync.py` | (A) |
| **cs_33 gds_algorithms** | **gds_tasks.py::run_gds_algorithms** | **부재** | **(B/C)** ※주2 |
| cs_41 graph_api | GET /{symbol}/graph/ | `api/views.py::ChainSightGraphView` | (A) |
| cs_42 suggestion_api | GET /{symbol}/suggestions/ | `ChainSightSuggestionView` | (A) |
| cs_43 trace_api | GET /trace/ | `ChainSightTraceView` | (A) |
| cs_51 graph_visualization | GraphCanvas, RelationLegend, NodeDetailPanel | `components/chainsight/*` | (A) |
| cs_52 ai_guide_ui | AIGuidePanel, FilterPanel | `components/chainsight/*` | (A) |
| cs_53 chain_trace_ui | TracePathView, MobileCardList | `components/chainsight/*` | (A) |
| cs_54 stock_detail_integration | GraphMiniView (종목 상세 탭) | `components/chainsight/GraphMiniView.tsx` | (A) |

> **주1**: `plan/task_done/CS-2-*`·`CS-3-1/3-2`는 v1.3 시점 기준 "설계만 완료"로 기록돼 있으나, **실제 코드는 모두 존재**한다. 이는 `update_v2`(v1.4)에서 구현이 완료되었고 v1.3 task_done이 갱신되지 않은 **문서 시차(stale doc)**다. `update_v2/task_done/CS-2-*`에는 구현+수치 검증 완료로 기록됨 (예: RelationConfidence 10,738건, CoMentionEdge 1,047건).
>
> **주2**: 상세는 아래 "미구현 항목 상세" 참조.

### plan/redesign_v1_260409 (2세대) — 구현 대조

| PR | 설계 항목 | 코드 위치 | 분류 |
|----|----------|-----------|------|
| PR-1 schema | RelationConfidence.previous_status/neo4j_dirty/synced_at | `migrations/0005` | (A) |
| PR-2 seed_selection | 시드 5소스 + select_seeds + Beat | `services/seed_selection.py` + `seed_tasks.py::run_seed_selection` | (A) ※주3 |
| PR-3 neo4j_dirty_sync | sync_dirty_relations | `neo4j_sync.py` + `neo4j_dirty_sync_tasks.py::run_neo4j_dirty_sync` | (A) |
| PR-4 market_view_api | seeds/sector graph/neighbors/signals | `SeedListView`·`SectorGraphView`·`NeighborGraphView`·`SignalFeedView` | (A) |
| PR-5 fe_core_ui | explorationStore + SectorBar + MarketGraphCanvas | `components/chainsight/*` | (A) |
| PR-6 trail_and_cards | ExplorationTrail + RelationCardPanel | `components/chainsight/*` | (A) |
| PR-7 chain_story_feed | ChainStoryFeed (무한 스크롤) | `components/chainsight/ChainStoryFeed.tsx` | (A) |

> **주3**: 설계 함수명과 구현 함수명이 일부 다르나 기능은 동등(리네이밍). `get_volume_seeds`→`get_volume_surge_seeds`, `get_relation_change_seeds`→`get_relation_upgrade_seeds`/`get_relation_downgrade_seeds`/`get_new_relation_seeds`로 분화. (D) 폐기가 아닌 정상 진화.

### update_v2 (3세대, Phase 6/7) — 구현 대조

| 작업지시서 | 설계 항목 | 코드 위치 | 분류 |
|-----------|----------|-----------|------|
| cs_44/cs_56 heat_score | calculate_heat_scores (4 signal) + Beat 일간 | `seed_tasks.py::calculate_heat_scores` + `chainsight-heat-score-daily` | (A) ※주4 |
| cs_55 market_view | 3영역 레이아웃 | `app/chainsight/page.tsx` + 컴포넌트 | (A) |
| cs_61 saved_path_model | SavedPath(UUID) + PathAction | `models/saved_path.py` + `migrations/0006` | (A) |
| cs_62 watchlist_crud_api | CRUD + archive/resolve | `views/watchlist_views.py::WatchlistViewSet` | (A) |
| cs_63 summary_path | landmark 압축 | `services/path_service.py::generate_summary_path` + `regenerate_summary_paths` cmd | (A) |
| cs_65 recheck_api | 6단계 recheck | `services/recheck_service.py` + `WatchlistViewSet.recheck` | (A) |
| cs_66 expand_api | 1-hop 확장 후보 | `services/expand_service.py` + `WatchlistViewSet.expand` | (A) |
| cs_67 alternatives_api | 노드 대안 | `services/alternatives_service.py` + `WatchlistViewSet.alternatives` | (A) |
| cs_71 watch_button | WatchButton + 9 훅 + 17 인터페이스 | `components/chainsight/WatchButton.tsx` | (A) |
| cs_72 watchlist_ui | PathCard + watchlist 페이지 | `PathCard.tsx` + `app/chainsight/watchlist/page.tsx` | (A) |
| cs_73 full_path_view | FullPathView + 액션 4종 | `FullPathView.tsx` + `watchlist/[id]/page.tsx` | (A) |

> **주4**: redesign_v1은 heat_score를 "Phase 2 보류"로 명시했으나, v1.4 CS-4-4에서 구현 완료됨. 설계 방향이 진화한 (D→A) 사례.

### graph_redesign_v2.md (시각 트랙) — 구현 대조

| 설계 항목 | 코드 위치 | 분류 |
|----------|-----------|------|
| 시멘틱 방사형 레이아웃 (각도-관계 매핑) | `components/chainsight/radialLayout.ts` | (A) 추정 ※주5 |
| 관계 토글 칩 바 (6칩, 기본 OFF) | `RelationFilterChips.tsx` | (A) |
| 관계 범례 | `RelationLegend.tsx` | (A) |
| 노드 컨텍스트 메뉴·툴팁 | `NodeContextMenu.tsx`·`NodeTooltip.tsx` | (A) |
| 5단계 점진적 공개 | (page.tsx 흐름) | (B) 미세 검증 필요 |

> **주5**: `radialLayout.ts` 파일 존재로 레이아웃 구현 확인. 시멘틱 각도 매핑의 정확도(12시=공급망 등)는 코드 정독 미수행으로 (A) 추정.

---

## 미구현 항목 상세

### ★ C-1. CS-3-3 GDS 알고리즘 자동화 — (B 부분 / 사실상 C)

**가장 명확한 설계-구현 갭.**

**설계 (cs_33 / update_v2/task_instructions/cs_33_gds_algorithms.md)**:
- `chainsight/tasks/gds_tasks.py::run_gds_algorithms` 생성
- PageRank → `pagerank_score`, Louvain → `community_id`, Betweenness → `betweenness_score`
- Neo4j 노드 속성에 영속화, Celery Beat 배치

**task_done 주장 (update_v2/task_done/CS-3-3_gds_algorithms.md, 2026-04-18)**:
- "GDS version 2.13.2 설치 + 활성화"
- "PageRank Top 10 (MSFT 1.9234…), Community 23개, Betweenness Top 5 (ACGL 24,351.5…)"
- "이미 구현됨 — 검증 완료"

**실제 코드 검증 결과 (grep)**:
| 확인 항목 | 결과 |
|-----------|------|
| `chainsight/tasks/gds_tasks.py` | **부재** |
| `tasks/__init__.py` GDS 등록 | **없음** |
| GDS management command | **없음** |
| `CALL gds.*` Cypher 호출 코드 | **전무** |
| `community_id =` / `pagerank_score =` SET 코드 | **없음** (schema.py에 community_id *인덱스 정의*만, path_service는 *읽기*만) |
| Celery Beat GDS 항목 | **없음** (`config/celery.py`에 미등록) |

**판정**: GDS는 **개발자가 Neo4j Browser에서 일회성 수동 Cypher로 실행해 수치만 확인**한 상태다. 반복 실행 가능한 코드 자산이 0이므로, 데이터가 노후화되면 갱신할 자동화 수단이 없다. task_done의 "완료" 기록은 *검증 완료*이지 *코드 구현 완료*가 아니다 — **문서가 구현 상태를 과대 표기**하고 있다.

**영향**: `community_id`/`pagerank_score`는 프로파일 동기화·그래프 가중치 계산의 입력인데, 영속·갱신 경로가 없어 시간이 지나면 stale 또는 null이 된다.

### C-2. ticker 형식 검증 (ultra review C-3) — (B 부분)

- ultra review가 권고한 `re.match(r'^[A-Z]{1,5}$')` ticker 형식 검증이 `serializers/path_watchlist.py`에서 **확인되지 않음** (`import re`는 있으나 정규식 사용처 미검출).
- path_nodes 리스트/길이 검증(2~10개)은 구현됨.
- "BRK.B" 같은 점 포함 심볼 처리 여부 불확실.

### C-3. 자동 모니터링/알림 — (C 미구현, 설계상 의도된 후속)

- phase6_7_ultra_review가 지적한 최대 제품 갭: **Path Watchlist의 모니터링이 전적으로 수동**(사용자가 직접 Recheck). "Watch"가 아니라 "Bookmark" 수준.
- 자동 알림은 v1.5 후속 과제로 설계상 명시 — 현 범위에서는 의도된 미구현.

### C-4. Phase 5 미세 항목 — (B 부분, 비차단)

- 시드 노드 **bounce 애니메이션** 미구현 (CS-5-6에 "향후 추가 가능"으로 명시).
- 마켓 뷰 전환 애니메이션(300ms ease-out) "범위 밖" 표시.
- 체인 스토리 피드: 컴포넌트는 구현됐으나 signals API 경로 데이터 부족으로 실데이터 렌더 미검증 (데이터 파이프라인 이슈, 코드 갭 아님).

### ultra review P0 7건 반영 현황 (직접 검증)

| # | 이슈 | 반영 여부 |
|---|------|----------|
| C-1 | AllowAny → 인증 강제 | ✅ **반영** — `IsAuthenticated` (security audit P0 #2, 2026-05-19 주석). 권고안(`IsAuthenticatedOrReadOnly`)보다 엄격 |
| C-2 | int() 캐스트 미검증 → 500 | ✅ **반영** — `except (ValueError, TypeError)` (watchlist_views.py:173-174, 218-219) |
| C-3 | ticker isAlpha 검증 | ⚠️ **부분/미확인** — 길이 검증만, 형식 정규식 미검출 (위 C-2 참조) |
| I-4 | GraphQueryError 미처리 → 500 | ✅ **반영** — `except (GraphConnectionError, GraphQueryError)` (60·136·182행) |
| 트랜잭션 atomic | create/archive/resolve atomic 없음 | ⏳ 미검증 (본 감사 범위 밖) |
| FE off-by-one / hydration | I-6/I-8 | ⏳ 미검증 (FE 코드 정독 필요) |
| 접근성 ARIA | 3/10 | ⏳ 미검증 |

> 보안 P0(C-1/C-2/I-4)는 별도 security audit 트랙에서 이미 수정 완료. ticker 형식 검증(C-3)만 추적 권장.

---

## 폐기/대체 항목

### (D-1) plan/cs_* 1세대 → update_v2 task_instructions로 재구성

- `plan/cs_00~54`와 `plan/task_done/CS-*`는 v1.3 시점 산출물. v1.4에서 동일 번호 체계가 `update_v2/task_instructions/`로 재작성되며 **선행 위상 상실**.
- `plan/task_done/CS-2-*`·`CS-3-1/3-2`의 "설계만 완료" 표기는 **현행 코드와 불일치**(실제 구현됨). → `update_v2/task_done/`가 정본.

### (D-2) redesign_v1 "마켓 뷰 = 완결 허브" 방향 → v1.4 Phase 5로 흡수

- redesign_v1은 마켓 뷰를 독립 리디자인으로 제안했으나, v1.4가 이를 Phase 5(CS-5-5/5-6)로 정식 편입. redesign_v1 문서는 **단독 진실 소스 아님** (v1.4의 하위 근거 문서).

### (D-3) heat_score "Phase 2 보류" → v1.4에서 구현

- redesign_v1의 "heat_score는 Phase 2 별도 PR" 방향이 폐기되고, v1.4 CS-4-4에서 `calculate_heat_scores`로 구현 + 일간 Beat 등록.

### (D-4) seed_selection 함수명 리네이밍

- `get_volume_seeds`→`get_volume_surge_seeds`, `get_relation_change_seeds`→ 3개 함수로 분화(`upgrade`/`downgrade`/`new_relation`). 설계 명칭 폐기, 기능 동등.

### (D-5) RelationConfidence neo4j 플래그 통일

- 초기 `synced_to_neo4j`(bool) → `neo4j_dirty` 패턴으로 전환 (`migrations/0008_unify_neo4j_flags`). CompanyChainProfile의 `neo4j_synced`도 `neo4j_dirty`로 의미 반전. (common-bugs/DECISIONS의 dirty 플래그 결정과 일치)

---

## 부록: 감사 범위 및 한계

**대조한 설계 문서**: `plan/`(cs_00~54, roadmap v1.3, redesign_v1 7문서, relation_confidence_design_v1), `update_v2/`(ROADMAP v1.4, task_instructions cs_00~73, task_done CS-*, review 6문서), `graph_redesign_v2.md`.

**대조한 코드**: `chainsight/`(models 12, migrations 8, services 7, tasks 8, api/views 7, graph 3, management 6), `frontend/app/chainsight/`(라우트 4), `frontend/components/chainsight/`(21), `frontend/__tests__/chainsight/`(3).

**검증 방법**: 인벤토리 대조 + 직접 grep (permission/int 캐스트/ticker 정규식/GDS Cypher/Celery Beat).

**한계 (미검증, 후속 권장)**:
- FE 컴포넌트 내부 로직(off-by-one, hydration, ARIA) 정독 미수행.
- 트랜잭션 atomic 적용 여부 미확인.
- `graph_redesign_v2` 시멘틱 각도 매핑 정확도 미확인.
- ticker 형식 검증(`^[A-Z]{1,5}$`) 적용 여부 — `path_watchlist.py` 정독 권장.

**핵심 후속 액션 (우선순위)**:
1. **CS-3-3 GDS 자동화 구현** — `gds_tasks.py` + Beat 등록 (현재 코드 자산 0).
2. **task_done 문서 정정** — CS-3-3 "완료"를 "수동 검증, 자동화 미구현"으로, plan/task_done CS-2/3 stale 표기 정리.
3. ticker 형식 검증(C-3) 확인 및 보강.
