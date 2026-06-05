# Chain Sight 설계 갭 감사

> **감사일**: 2026-06-05
> **범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` + `frontend/components/chainsight/` 구현 대조
> **방식**: 읽기 전용 (코드 수정 없음). 설계서 항목별 코드 존재 여부 + Celery Beat 등록 + task_done 완료기록 교차검증
> **주의**: 데이터 적재 건수(노드/관계/프로파일 수)는 `task_done/*.md` 완료기록 기반이며 런타임 DB를 직접 조회하지 않았다. 정적 코드 + 문서 대조 결과다.

---

## 요약 (구현률)

| 분류 | 개수 | 문서 |
|------|------|------|
| **(A) 완전 구현** | 23 | cs_00~cs_43 (GDS 제외), redesign_v1 4개 문서, DC-2, celery_beat |
| **(B) 부분 구현** | 1 | cs_33 GDS 알고리즘 (결과 적재 O, 정기 배치 태스크 X) |
| **(C) 미구현** | 0 | — |
| **(D) 폐기/대체** | 4 | cs_51~cs_54 (원안 컴포넌트명 → v2/redesign 명칭으로 재설계) |

**종합 구현률**: 설계된 백엔드 파이프라인(모델 15개 · 태스크 17개 · 서비스 7개 · API 8개)과 프론트엔드(컴포넌트 21개 · 페이지 4개)는 **사실상 전부 구현**되었다. 단 하나의 실질 기능 갭은 **GDS 알고리즘의 재현 가능한 배치 태스크 부재**다(아래 상세).

### 핵심 결론 3가지
1. **트랙 A(CS-0~CS-5) + redesign_v1(마켓 뷰) 모두 구현 완료.** Phase 0~5 마일스톤 M0~M5 달성 기록과 실제 코드가 일치한다.
2. **redesign_v1_260409는 기존 cs_* 문서를 "전면 대체"하지 않고 "상위 진입 계층 신설 + 기존 deep-dive 공존"한다.** (§폐기/대체 참조)
3. **유일한 실질 갭은 cs_33 GDS 정기 배치.** `pagerank_score`/`community_id`/`betweenness_score`는 2026-04-03에 1회 수동 적재됐으나, 이를 갱신하는 `gds_tasks.py`/`run_gds_algorithms` 태스크가 없고 Celery Beat에도 미등록 → 시간 경과 시 stale 위험. (path_service는 값 부재 시 bridge 0.75 fallback으로 방어됨)

---

## 문서별 상태 테이블

### Phase 0~4 백엔드 (cs_00 ~ cs_43)

| 문서 | 판정 | 구현 증거 | task_done |
|------|------|-----------|-----------|
| cs_00 레거시 정리 + API 테스트 | A | serverless/frontend 레거시 제거, RelationConfidence v2.1 마이그레이션, ETF는 LEGACY_KEEP 보관 | CS-0-0 ✅ |
| cs_01 마이그레이션 검증 | A | migrations 0001~0008, 12개 테이블 | CS-0-1 ✅ |
| cs_02 Neo4j 연결 레이어 | A | `graph/repository.py` (Neo4jGraphRepository, PID lazy driver), `graph/exceptions.py` | CS-0-2 ✅ |
| cs_03 온톨로지 스키마 | A | `graph/schema.py` (constraint/index), `init_neo4j_schema` command | CS-0-3 ✅ |
| cs_11 Stock 노드 벌크 로드 | A | `load_stocks_to_neo4j` command + `neo4j_loader.py` | CS-1-1 ✅ |
| cs_12 Sector/Industry + BELONGS_TO | A | `load_sectors_to_neo4j` command | CS-1-2 ✅ |
| cs_13 Peer 관계 로드 | A | `load_peers_to_neo4j` command + `fetch_and_load_peers` task | CS-1-3 ✅ |
| cs_21 Tier A (GrowthStage/CapitalDNA) | A | `profile_tasks.py`: calculate_growth_stages / calculate_capital_dna / calculate_all_profiles | CS-2-1 ✅ |
| cs_21b SensitivityProfile | A | `sensitivity_tasks.py`: calculate_sensitivity_profiles | CS-2-1b ✅ |
| cs_21c InsiderSignal | A | `insider_tasks.py`: calculate_insider_signals | CS-2-1c ✅ |
| cs_22 CoMentionEdge | A | `relation_tasks.py`: extract_co_mentions (+ ChainNewsEvent) | CS-2-2 ✅ |
| cs_23 PriceCoMovement | A | `relation_tasks.py`: calculate_price_co_movement | CS-2-3 ✅ |
| cs_24 RelationConfidence 종합 | A | `relation_tasks.py`: update_relation_confidence + check_stale_and_decay, 모델 5단계 상태/28필드 | CS-2-4 ✅ |
| cs_25 ChainProfile 집약 | A | `sync_tasks.py`: aggregate_chain_profiles | CS-2-5 ✅ |
| cs_31 Profile → Neo4j 동기화 | A | `sync_tasks.py`: sync_profiles_to_neo4j (Delta Sync) | CS-3-1 ✅ |
| cs_32 Relation → Neo4j 동기화 | A | `sync_tasks.py`: sync_relations_to_neo4j (+ neo4j_sync.sync_dirty_relations) | CS-3-2 ✅ |
| **cs_33 GDS 알고리즘** | **B** | **결과(pagerank/community/betweenness)는 1회 적재됐으나 `gds_tasks.py`/`run_gds_algorithms` 미작성, Beat 미등록** | CS-3-3 ⚠️ (결과만) |
| cs_41 그래프 탐색 API | A | `api/views.py`: ChainSightGraphView (`<symbol>/graph/`) | CS-4-1 ✅ |
| cs_42 탐색 제안 API | A | `api/views.py`: ChainSightSuggestionView (`<symbol>/suggestions/`) | CS-4-2 ✅ |
| cs_43 경로 탐색 API | A | `api/views.py`: ChainSightTraceView (`trace/`) | CS-4-3 ✅ |

### Phase 5 프론트엔드 (cs_51 ~ cs_54) — 원안 대비

| 문서 | 판정 | 원안 컴포넌트 → 실제 구현 | task_done |
|------|------|---------------------------|-----------|
| cs_51 그래프 시각화 | D | `GraphView.tsx` → `GraphCanvas.tsx` + NodeDetailPanel/FilterPanel 분할 | CS-5-1 ✅ |
| cs_52 AI 가이드 UI | D | `SuggestionCards.tsx` → `AIGuidePanel.tsx` 통합 | CS-5-2 ✅ |
| cs_53 Chain Trace 시각화 | D | `TraceView.tsx` → `TracePathView.tsx` (+ AIGuidePanel) | CS-5-2/5-3 ✅ |
| cs_54 종목 상세 연계 | D | `ChainSightMiniView.tsx` → `GraphMiniView.tsx` | CS-5-1 ✅ |

> 기능은 전부 구현됨. "폐기/대체"는 **컴포넌트 명칭·구조가 cs_5_frontend_design_v2 / redesign으로 재설계**됐음을 의미한다(기능 누락 아님).

### redesign_v1_260409 (마켓 뷰 신규 계층)

| 문서 | 판정 | 구현 증거 | task_done |
|------|------|-----------|-----------|
| chainsight_seed_node_design | A | `seed_selection.py` (5개 시드 소스), `seed_tasks.py`: run_seed_selection + **calculate_heat_scores**, SeedSnapshot 모델 | PR-2 ✅ |
| chainsight_api_design | A | `api/views.py`: SeedListView(`seeds/`), SectorGraphView(`sector/<>/graph/`), NeighborGraphView(`<>/neighbors/`), SignalFeedView(`signals/`) + display_type 파생 | PR-4 ✅ |
| chainsight_ui_ux_design | A | SectorBar / MarketGraphCanvas / ExplorationTrail / RelationCardPanel / ChainStoryFeed + explorationStore | PR-5/6/7 ✅ |
| chainsight_marketview_pr_prompts | A | migration 0005/0006/0007, SavedPath/PathAction, neo4j_dirty 패턴 | PR-1~7 ✅ |

> **정정**: 1차 분석에서 "Heat Score(redesign Phase 2) 미구현" 의견이 있었으나 **오류**다. `calculate_heat_scores`(`chainsight-heat-score-daily`)는 구현 + Beat 등록(`config/celery.py:748`)되어 있다.

### Celery Beat 등록 (config/celery.py) — 11개 전부 등록 확인

```
chainsight-all-profiles        토 02:00   calculate_all_profiles
chainsight-co-mentions         매일 10:00 extract_co_mentions
chainsight-price-co-movement   토 03:00   calculate_price_co_movement
chainsight-relation-confidence 매일 11:00 update_relation_confidence
chainsight-stale-decay         토 04:00   check_stale_and_decay
chainsight-aggregate-profiles  토 04:30   aggregate_chain_profiles
chainsight-sync-profiles-neo4j 매일 12:00 sync_profiles_to_neo4j (neo4j 큐)
chainsight-sync-relations-neo4j 매일 12:30 sync_relations_to_neo4j (neo4j 큐)
chainsight-heat-score-daily    매일 07:00 calculate_heat_scores
chainsight-seed-selection      매일 13:00 run_seed_selection
chainsight-neo4j-dirty-sync    일 04:30   run_neo4j_dirty_sync (neo4j 큐)
```
→ `celery_beat_registration.md` 완료기록(11개)과 **정확히 일치**. **단 GDS 배치 스케줄 키는 없음.**

---

## 미구현 항목 상세

### 🔴 cs_33 GDS 알고리즘 정기 배치 — (B) 부분 구현 [유일한 실질 갭]

**설계 (cs_33):**
- 산출물: `chainsight/tasks/gds_tasks.py`
- 태스크: `run_gds_algorithms()` — projection 생성 → `gds.pageRank.write` / `gds.louvain.write` / `gds.betweenness.write` → projection 삭제
- 목표: pagerank_score, community_id, betweenness_score 노드 속성을 **재현 가능하게 갱신**

**구현 현황:**
| 항목 | 상태 |
|------|------|
| `gds_tasks.py` 파일 | ❌ 없음 |
| `run_gds_algorithms` 태스크 | ❌ 없음 |
| Celery Beat 등록 | ❌ 없음 |
| 노드 속성 1회 적재 (2026-04-03) | ✅ CS-3-3 기록: MSFT/META PageRank, Louvain 184 등 |
| 속성 소비 (읽기) | ✅ `path_service.py:185 _fetch_centrality` 가 `s.pagerank_score`/`s.betweenness_score` 읽음 |
| 값 부재 시 방어 | ✅ pagerank/betweenness 무효 시 weight를 bridge 0.75로 fallback (path_service.py:154~161) |
| schema 인덱스 | ✅ `schema.py`: stock_community 인덱스 정의 |

**영향 평가:**
- GDS 결과는 **2026-04-03 수동 실행 시점에 고정**. PEER_OF/RELATED_TO 관계가 주간 파이프라인으로 계속 변동하지만 centrality는 재계산되지 않음 → **시간 경과에 따른 stale**.
- 단, `compute_landmark_scores`가 centrality 부재/노후를 graceful하게 처리(fallback)하므로 **즉각적 장애는 없음**. 랜드마크 점수 품질이 점진적으로 저하될 뿐.
- **권장(보고용, 조치 아님)**: `run_gds_algorithms` 태스크를 작성하고 `chainsight-gds-weekly`로 토요일 파이프라인(aggregate 이후)에 등록하면 cs_33이 (A)로 완성됨.

### 🟡 redesign 설계 내 "범위 밖" 명시 항목 (의도적 보류, 갭 아님)
설계서가 명시적으로 "Future enhancement / 이번 버전 미포함"으로 표기한 항목들 — 미구현이지만 계획된 보류:
- UI 전환 애니메이션 세부(중심 노드 translateX 300ms, 시드 bounce) — browser_test_report "범위 밖" 표기
- LLM 기반 chain title/summary 자동 생성 (현재 seed_reasons 템플릿 기반 `REASON_LABELS`)
- "현재 트레일 해석" 기능 (chainsight_ui_ux_design §10 Future)

---

## 폐기/대체 항목

### cs_51~54 프론트엔드 원안 → cs_5_frontend_design_v2 / redesign으로 재설계 (D)
원안에서 지정한 컴포넌트 파일명은 코드에 존재하지 않으나, **기능은 다른 이름·구조로 전부 구현**됨:

| 원안 (cs_51~54) | 실제 구현 |
|-----------------|-----------|
| GraphView.tsx | GraphCanvas.tsx (+ NodeDetailPanel, FilterPanel, NodeTooltip, NodeContextMenu) |
| SuggestionCards.tsx | AIGuidePanel.tsx |
| TraceView.tsx | TracePathView.tsx |
| ChainSightMiniView.tsx | GraphMiniView.tsx |

### redesign_v1_260409의 대체 vs 공존 성격
**전면 대체가 아니라 "상위 진입 계층 신설 + 기존 deep-dive 공존"이다.**

- **신설 (마켓 뷰 계층)**: `app/chainsight/page.tsx` + 4개 신규 API(`seeds/`·`sector/<>/graph/`·`signals/`·`neighbors/`) + 시드/heat-score 파이프라인 + 워치리스트(SavedPath/PathAction). 사용자 **진입 허브** 역할.
- **공존 (deep-dive)**: 기존 cs_41/42/43 API(`<symbol>/graph/`·`suggestions/`·`trace/`)와 `app/chainsight/[symbol]/page.tsx`는 **그대로 유지**되어 심화 분석 경로로 동작. urls.py에 신·구 API가 함께 등록됨.

즉 redesign은 cs_4*/cs_5* 자산을 **폐기하지 않고 하위 계층으로 재배치**하며, 그 위에 마켓 뷰를 얹은 구조다.

### 레거시 보관 (cs_00 결정)
- serverless의 `ETFProfile/ETFHolding/ThemeMatch`는 `# LEGACY_KEEP_UNTIL_DC2` 태그로 보관(DC-2 완료 시 제거 예정). 폐기 결정됐으나 현재 보류 중.

---

## 부록: 코드 인벤토리 (감사 기준점)

- **모델 (15)**: Tier A 4 (Sensitivity/GrowthStage/CapitalDNA/InsiderSignal) + Tier B 3 (RevenueStructure/NarrativeTag/EventReaction) + 관계발견 4 (ChainNewsEvent/CoMentionEdge/PriceCoMovement/RelationConfidence) + 집약 1 (CompanyChainProfile) + redesign 3 (SavedPath/PathAction/SeedSnapshot)
- **서비스 (7)**: alternatives / expand / neo4j_loader / neo4j_sync / path_service / recheck_service / seed_selection
- **태스크 (17)**: insider 1 · peer 1 · profile 3 · relation 4 · sensitivity 1 · sync 3 · seed 3 · neo4j_dirty 1
- **API (8)**: Graph / Suggestion / Trace / Neighbor / SectorGraph / SeedList / SignalFeed / WatchlistViewSet
- **Management commands (6)**: init_neo4j_schema / load_stocks / load_sectors / load_peers / load_themes / regenerate_summary_paths
- **Frontend (21 컴포넌트 + 4 페이지)**: market-view(SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed) + deep-dive(GraphCanvas, NodeDetailPanel, AIGuidePanel, TracePathView, GraphMiniView 등)
- **GDS 전용 태스크**: ❌ 없음 (유일 갭)

---

**END OF AUDIT**
