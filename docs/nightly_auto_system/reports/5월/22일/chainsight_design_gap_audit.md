# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-22
> **감사자**: Claude (read-only)
> **대상**: `docs/chain_sight/plan/` × `chainsight/` 코드 × `frontend/components/chainsight/`
> **목적**: 설계 문서와 구현체의 일치 여부 식별, 폐기/대체 관계 정리

---

## 요약 (구현률)

### 설계 문서 계보

```
초기 설계 (cs_00~54, cs_5_frontend_design_v2)  ──┬──→  task_done/CS-*.md  (Phase 0~4 완료)
                                                 │
                                                 └──→  redesign_v1_260409 (2026-04-09)
                                                          │ 마켓 뷰 전면 재설계
                                                          ▼
                                                      task_done/chain_sight_redesign_V1
                                                      (PR-1~7 완료, 2026-04-10)
```

### 구현률 (대분류)

| 영역 | 분류 | 비고 |
|------|------|------|
| Phase 0 인프라 (CS-0) | (A) 완전 구현 | 레거시 정리, Neo4j 드라이버, 스키마 12 테이블 |
| Phase 1 시드 로드 (CS-1) | (A) 완전 구현 | Stock/Sector/Industry/Peer 노드 적재 |
| Phase 2 파생 계산 (CS-2) | (B) 부분 구현 | GrowthStage/CapitalDNA/CoMention/PriceCoMovement/RelationConfidence ✅. Sensitivity·Insider는 코드는 있으나 데이터 적재·운영 결과 미확인 |
| Phase 3 동기화 + GDS (CS-3) | (A) 완전 구현 | sync_*_to_neo4j + GDS 실행 완료 (M3) |
| Phase 4 REST API (CS-4) | (A) 완전 구현 | graph/suggestions/trace + 마켓 뷰 4종 |
| Phase 5 프론트엔드 (CS-5) | (D) 폐기/대체 | 원안(cs_51~54 + cs_5_frontend_design_v2)은 redesign_v1로 전면 대체 |
| Redesign V1 마켓 뷰 (PR-1~7) | (A) 완전 구현 | seeds/sector/neighbors/signals API + SectorBar/Canvas/Trail/CardPanel/StoryFeed |
| Seed Phase 2 (Heat Score) | (C) 미구현 | SeedHeatScore 모델·Beat 미존재. 설계서 `chainsight_seed_node_design.md` §3 |
| Seed Phase 3 (이벤트 전파) | (C) 미구현 | text_conditional_prob/lagged_correlation/propagation_weight 전부 미존재 |
| Deep dive workspace 추가 기능 (SavedPath/alternatives/recheck/expand/watchlist) | (E) 문서 미정합 | 코드 존재하나 active 설계 문서 없음. 별도 트랙으로 추정 |

전체 구현률(가중 평균 추정): **약 70~75%**. 핵심 마켓 뷰는 완전 구현, Phase 2/3 시드 고도화와 일부 데이터 적재가 갭.

---

## 문서별 상태 테이블

### 1. 로드맵 / 글로벌 설계

| 문서 | 설계 의도 | 구현 위치 | 분류 |
|------|-----------|----------|------|
| `chain_sight_roadmap_v1.3.md` | 6 원칙 + 4-Layer + Phase 0~5 마스터 플랜 | `chainsight/` 전반 | (A) — Phase 5만 (D)로 대체 |
| `relation_confidence_design_v1.md` (v1.1) | 5단계 상태, truth/market 분리, Tier 1/2/3, normalize_pair | `models/relation_discovery.py` (`RelationConfidence`), `utils.py` (`normalize_pair`), `tasks/relation_tasks.py` (`update_relation_confidence`, `check_stale_and_decay`) | (A) 완전 구현 |
| `sec_pipeline_base_design.md`, `sec_pipeline_pr_detail.md` | SEC 10-K Supply Chain + Business Model | `sec_pipeline/` 앱 (별도) | 본 감사 범위 외 — task_done 별도 |

### 2. Phase 0 — 인프라 (CS-0)

| 설계 | 산출물 (task_done) | 구현 | 분류 |
|------|---------|------|------|
| `cs_00_legacy_cleanup_api_test.md` | `CS-0-0_legacy_cleanup_api_test.md` | serverless Chain Sight 6 뷰 제거, 프론트 chain-sight/ 제거, API 5종 테스트 | (A) |
| `cs_01_migrations_verification.md` | `CS-0-1_migrations.md` | `chainsight/migrations/0001~0008` (8 migration) | (A) |
| `cs_02_neo4j_connection.md` | `CS-0-2_neo4j_driver.md` | `chainsight/graph/repository.py` (PID lazy init) | (A) |
| `cs_03_neo4j_schema.md` | `CS-0-3_neo4j_schema.md` | `chainsight/graph/schema.py` + `init_neo4j_schema` 커맨드 | (A) |

### 3. Phase 1 — 시드 로드 (CS-1)

| 설계 | 산출물 | 구현 | 분류 |
|------|---------|------|------|
| `cs_11_stock_node_bulk_load.md` | `CS-1-1_stock_nodes.md` | `management/commands/load_stocks_to_neo4j.py` | (A) |
| `cs_12_sector_industry.md` | `CS-1-2_sectors.md` | `load_sectors_to_neo4j.py` | (A) |
| `cs_13_peer_relations.md` | `CS-1-3_peers.md` | `load_peers_to_neo4j.py` + `services/neo4j_loader.py` | (A) |
| (추가) | — | `load_themes_to_neo4j.py` (DC-2 ETF 테마 노드 로드) | (A) — 설계서엔 명시 없지만 DC-2 트랙 구현 |

### 4. Phase 2 — 파생 데이터 (CS-2)

| 설계 | 산출물 | 구현 | 분류 |
|------|---------|------|------|
| `cs_21_tier_a_profile.md` (GrowthStage/CapitalDNA) | `CS-2-1_tier_a_profiles.md` | `models/growth_stage.py`, `capital_dna.py`, `tasks/profile_tasks.py` | (A) |
| `cs_21b_sensitivity_profile.md` | `CS-2-1b_sensitivity_profile.md` | `models/sensitivity.py`, `tasks/sensitivity_tasks.py` (304줄) | (B) — 코드 존재, `remaining_work_plan.md`는 "다음 착수"로 적었으나 task_done에 완료 보고서 있음. 데이터 적재량 별도 검증 필요 |
| `cs_21c_insider_signal.md` | `CS-2-1c_insider_signal.md` | `models/insider_signal.py`, `tasks/insider_tasks.py` (180줄) | (B) — 위와 동일 패턴 |
| `cs_22_co_mention.md` | `CS-2-2_co_mention.md` | `models/relation_discovery.py:CoMentionEdge`, `tasks/relation_tasks.py:extract_co_mentions` | (A) |
| `cs_23_price_co_movement.md` | `CS-2-3_price_co_movement.md` | `relation_discovery.py:PriceCoMovement`, `relation_tasks.py:calculate_price_co_movement` | (A) |
| `cs_24_relation_confidence.md` | `CS-2-4_relation_confidence.md` | `RelationConfidence` (v2.1 스키마: 5단계 상태 + tier/sources/basis_summary), `relation_tasks.py:update_relation_confidence`, `check_stale_and_decay` | (A) |
| `cs_25_chain_profile_aggregation.md` | `CS-2-5_chain_profile_aggregation.md` | `models/chain_profile.py:CompanyChainProfile`, `tasks/sync_tasks.py:aggregate_chain_profiles` | (A) |

### 5. Phase 3 — Neo4j 동기화 + GDS (CS-3)

| 설계 | 산출물 | 구현 | 분류 |
|------|---------|------|------|
| `cs_31_profile_neo4j_sync.md` | `CS-3-1_profile_sync.md` | `tasks/sync_tasks.py:sync_profiles_to_neo4j` | (A) |
| `cs_32_relation_neo4j_sync.md` | `CS-3-2_relation_neo4j_sync.md` | `tasks/sync_tasks.py:sync_relations_to_neo4j`, `services/neo4j_sync.py` (dirty 기반) | (A) — redesign PR-3에서 `neo4j_dirty` 패턴으로 보강 |
| `cs_33_gds_algorithms.md` | `CS-3-3_gds_algorithms.md` | (별도 GDS task — `remaining_work_plan.md`에 M3 달성 명시) | (A) |

### 6. Phase 4 — REST API (CS-4)

| 설계 | 산출물 | 구현 | 분류 |
|------|---------|------|------|
| `cs_41_graph_api.md` | `CS-4-1_2_3_rest_api.md` | `api/views.py:ChainSightGraphView` (`/{symbol}/graph/`) | (A) |
| `cs_42_suggestion_api.md` | 위와 동일 | `ChainSightSuggestionView` (`/{symbol}/suggestions/`) | (A) |
| `cs_43_trace_api.md` | 위와 동일 | `ChainSightTraceView` (`/trace/`) | (A) |

### 7. Phase 5 — 프론트엔드 (CS-5) — **폐기, redesign_v1로 대체**

| 원안 문서 | 의도 | 대체 | 분류 |
|----------|------|------|------|
| `cs_51_graph_visualization.md` | `components/chainsight/GraphView.tsx` + GraphControls + NodeDetailPanel + useGraphData (react-force-graph-2d, Spotlight + lazy expansion) | 마켓 뷰는 redesign_v1의 `MarketGraphCanvas`로 대체. 하지만 Deep dive workspace는 원안 잔재(`GraphCanvas.tsx`, `NodeDetailPanel.tsx`)로 부분 유지 | (D) |
| `cs_52_ai_guide_ui.md` | `components/chainsight/SuggestionCards.tsx` (AI 가이드) | 일부 유지 (`AIGuidePanel.tsx`). 마켓 뷰의 RelationCardPanel(pre-focus 시드 카드)이 사실상 가이드 역할 대체 | (D) — 부분 잔류 |
| `cs_53_chain_trace_ui.md` | `components/chainsight/TraceView.tsx` (경로 하이라이트) | `TracePathView.tsx`, `FullPathView.tsx` 존재 — Deep dive workspace 잔재 | (D) — 부분 잔류 |
| `cs_54_stock_detail_integration.md` | 종목 상세에 Chain Sight 미니 뷰 임베드 | redesign_v1 UI/UX 문서 §11: **탭 제거 + `/chainsight?focus={symbol}` 딥링크**로 방침 변경 | (D) |
| `cs_5_frontend_design_v2.md` | `/chainsight/[symbol]` 전용 워크스페이스 (3-panel, 6색 엣지, Centrality, 가설/Watchlist CTA) | Deep dive workspace로 유지되었으나 마켓 뷰는 별도 `/chainsight` 페이지로 분리. v2의 "/[symbol]" 전용 워크스페이스 구조는 부분만 살아남음 | (D) — 부분 잔류, 마켓 뷰는 redesign_v1로 분리됨 |

### 8. Redesign V1 (2026-04-09/10) — **현행 active 설계**

| 설계 | 산출물 | 구현 | 분류 |
|------|---------|------|------|
| `redesign_v1_260409/chainsight_seed_node_design.md` Phase 1 | `chain_sight_redesign_V1/PR-2_seed_selection_task.md` | `services/seed_selection.py` (424줄), `tasks/seed_tasks.py:run_seed_selection`, `models/seed_snapshot.py` | (A) |
| `redesign_v1_260409/chainsight_seed_node_design.md` Phase 2 (Heat Score) | — | **미구현**. `SeedHeatScore` 모델 없음. Beat `chainsight-heat-score` 없음 | (C) |
| `redesign_v1_260409/chainsight_seed_node_design.md` Phase 3 (이벤트 전파) | — | **미구현**. text_conditional_prob, lagged_correlation, propagation_weight 어디에도 없음 | (C) |
| `redesign_v1_260409/chainsight_api_design.md` | `PR-4_market_view_api.md` | `api/views.py` SeedListView / SectorGraphView / NeighborGraphView / SignalFeedView + `urls.py` 매핑 | (A) |
| `redesign_v1_260409/chainsight_ui_ux_design.md` (마켓 뷰 ①~⑤) | `PR-5_fe_core_ui.md`, `PR-6_trail_and_cards.md`, `PR-7_chain_story_feed.md` | `frontend/components/chainsight/`: SectorBar, MarketGraphCanvas, ExplorationTrail, RelationCardPanel, ChainStoryFeed + `lib/stores/explorationStore.ts` + `hooks/useMarketView.ts` + `app/chainsight/page.tsx` | (A) |
| `redesign_v1_260409/chainsight_marketview_pr_prompts.md` PR-1 (스키마) | `PR-1_schema_migration.md` | `migrations/0005_add_neo4j_dirty_previous_status.py` (RelationConfidence.previous_status, neo4j_dirty) | (A) |
| `redesign_v1_260409/chainsight_marketview_pr_prompts.md` PR-3 (dirty sync) | `PR-3_neo4j_dirty_sync.md` | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py` | (A) |

### 9. 운영/품질 task_done (설계 문서 외)

| task_done | 비고 |
|-----------|------|
| `DC-2_etf_holdings_theme.md` | ETF Holdings 운용사 CSV 적재 (Theme 노드 + HAS_THEME) — 데이터 수집 트랙 B. `load_themes_to_neo4j.py` 존재 |
| `celery_beat_registration.md` | 11 task 일괄 등록 (Chain Sight 8 + Validation 1 + SEC 2) |
| `chain_sight_redesign_V1/data_quality_3_fixes.md` | 데이터 품질 후속 보완 |
| `chain_sight_redesign_V1/browser_test_report.md` | E2E 시나리오 검증 보고서 |
| `chain_sight_redesign_V1/qa_evaluator_review_01.md` | QA 평가 라운드 |

---

## 미구현 항목 상세

### (C-1) Seed Phase 2 — Heat Score 가중치 모델

**설계서**: `redesign_v1_260409/chainsight_seed_node_design.md` §3

**누락된 산출물**:
- `SeedHeatScore` 모델 (stock × date → heat_score, components(JSONB), seed_rank). `chainsight/models/__init__.py` 임포트 목록에 부재.
- `heat_score` 산식: `0.25·price_anomaly + 0.20·volume_surge + 0.20·relation_change + 0.15·comention_surge + 0.10·news_event + 0.10·gds_centrality_delta`
- Celery Beat 태스크 `chainsight-heat-score` (매일 11:30 UTC)
- 섹터 정렬 기준 전환 (Phase 1 `seed_count DESC` → Phase 2+ `heat_total DESC`)

**현재 영향**:
- `api/views.py:_build_chain_signals`의 `sector_summary[].heat_total`이 항상 `0.0`로 nil 유지 (`services/seed_selection.py:build_sector_summary` 주석에 "Phase 2에서 사용"으로 명시됨).
- API 응답의 `sector_summary[].heat_total` 필드는 존재하나 모든 값이 0.

### (C-2) Seed Phase 3 — 이벤트 전파 모델 (D 트랙)

**설계서**: `chainsight_seed_node_design.md` §4

**누락된 산출물**:
- D-1: `text_conditional_prob(A, B) = frequency × semantic_similarity` (ChromaDB + Gemini Embedding 의존)
- D-2: `lagged_correlation` (lag 0/1/2 max) + `volume_response(B|event_A)` + `propagation_weight(A→B)`
- D-3: 사후 검증 → 가중치 학습
- Celery Beat: `chainsight-text-conditional` (매일 13:00), `chainsight-lagged-correlation` (토 03:30), `chainsight-propagation-weight` (토 05:30)

**현재 영향**:
- 사실상 신규 트랙. ChromaDB 의존성·60 거래일 축적 등 전제가 있어 단기 미실행은 자연스러움.

### (C-3) signals API 2차 필드 (LLM 기반 설명)

**설계서**: `chainsight_api_design.md` §4 "2차 필드 확장 (향후)"

**누락된 산출물**:
- `neighbors[].relation.relation_summary` (관계 한 줄 요약)
- `neighbors[].relation.why_now` (현재 시점 시그널)
- `neighbors[].relation.insight_summary` (해석)
- 1차 템플릿(`display_type` 기반 한국어 문구)은 프론트 `RelationCard`에서 클라이언트 사이드 처리(설계 1차 단계와 일치).

**현재 영향**:
- 사용자에게 표시되는 관계 설명이 고정 6 문구로 한정. "왜 지금 흐름인지"는 `seed_reasons` 코드 라벨 매핑에 머문다.

### (C-4) signals 체인 LLM title/summary 생성

**설계서**: `redesign_v1_260409/00_summary.md` 범위 밖 항목

**현재**:
- `chain.title`은 `f'{path_nodes[0]["ticker"]} → {path_nodes[-1]["ticker"]} chain'` 단순 템플릿.
- LLM 기반 제목·요약 미적용.

### (C-5) 전환 애니메이션 정밀화

**설계서**: `chainsight_ui_ux_design.md` §7 (translateX/opacity/bounce, 300ms ease-out)

**현재**: 일부 적용되었을 수 있으나 redesign_V1/00_summary.md가 "전환 애니메이션 (300ms ease-out, bounce)"를 명시적 "범위 밖"으로 분리 — 후속 작업 큐.

### (C-6) chain path 전체 트레일 preload

**설계서**: `chainsight_ui_ux_design.md` §10 "future enhancement"로 명시
**현재**: 미구현 (future로 인식된 항목)

### (C-7) GDS 결과의 마켓 뷰 API 반영

**설계서**: PageRank/Louvain/Betweenness 등 노드 속성 — `chainsight_api_design.md` v2.1에는 명시 없음. `chain_sight_roadmap_v1.3.md` §2.4·CS-3-3에서 :Stock 속성으로 보관됨을 명시.

**현재**:
- M3 마일스톤 달성 보고 (`remaining_work_plan.md`) — Neo4j 노드에 pagerank/community 속성 적재됨.
- 그러나 `sector/{sector}/graph/`, `{symbol}/neighbors/` 응답 어디에도 pagerank/community 필드가 노출되지 않음.

**분류**: (B) 부분 구현 (저장은 됨, 노출 안 됨).

### (B-1) Tier A 확장 데이터 적재 검증 필요

**대상**: `CompanySensitivityProfile`, `CompanyInsiderSignal`
- 모델 + tasks 코드는 존재 (`sensitivity_tasks.py` 304줄, `insider_tasks.py` 180줄).
- task_done에 완료 보고서 존재.
- 그러나 `remaining_work_plan.md` (2026-04-04)는 두 항목을 "남은 작업 1·2번"으로 적시 → 문서 간 모순.
- 실제 데이터 적재 건수는 본 감사 범위 외 (DB 조회 필요).

---

## 폐기/대체 항목

### (D-1) cs_5_frontend_design_v2.md → redesign_v1 마켓 뷰로 부분 대체

**원안 의도**: `/chainsight/[symbol]` 전용 워크스페이스(3-panel) 단일 진입.

**대체**:
- 마켓 뷰 진입(`/chainsight`)이 redesign_v1로 신설.
- `/chainsight/[symbol]` Deep dive workspace는 v2 의도대로 잔류했으나, "Chain Sight에서 보기" 진입 동선이 `/chainsight?focus={symbol}` → 마켓 뷰 focused state로 변경됨.
- 원안 v2의 "Centrality 메트릭, 필터 패널, 멀티 depth"는 마켓 뷰에 부분 흡수(FilterPanel.tsx 존재), 전체 사양은 미반영.

**근거 문서**: `redesign_v1_260409/chainsight_ui_ux_design.md` §1 "마켓 뷰 vs Deep dive workspace" 분리 선언, §11 "종목 상세 연결"에서 v1 cs_54 방침을 명시적으로 무효화.

### (D-2) cs_51_graph_visualization.md GraphView.tsx → MarketGraphCanvas.tsx로 대체

**원안 의도**: `react-force-graph-2d` Spotlight 모드 + lazy expansion.

**대체**:
- 마켓 뷰는 `MarketGraphCanvas.tsx`로 신규 구현(센터 이동 + cross_edges + history dim).
- 원안 `GraphView.tsx` 파일명은 코드에 없으나 `GraphCanvas.tsx`로 Deep dive workspace에 잔류.

### (D-3) cs_52_ai_guide_ui.md SuggestionCards.tsx → RelationCardPanel pre-focus 카드로 대체

**원안 의도**: 카테고리 선택 → 그래프 필터링.

**대체**:
- 마켓 뷰의 `RelationCardPanel`이 `centerSymbol == null` 시 시드 카드(pre-focus), `!= null` 시 관계 카드(focused)로 이원화 처리.
- `/chainsight/[symbol]/suggestions/` API 자체는 Deep dive workspace용으로 유지 (`api/views.py:ChainSightSuggestionView`).
- Deep dive 잔재: `AIGuidePanel.tsx` 컴포넌트.

### (D-4) cs_53_chain_trace_ui.md TraceView → 잔류 (마켓 뷰 미사용)

**원안 의도**: 두 종목 from/to 경로 시각화.

**대체**:
- `TracePathView.tsx`, `FullPathView.tsx`로 Deep dive workspace에 잔류.
- 마켓 뷰에는 미노출. `chainsight_ui_ux_design.md`는 "현재 트레일 해석은 이 버전 미포함, future enhancement"로 명시.

### (D-5) cs_54_stock_detail_integration.md → 딥링크로 대체

**원안 의도**: 종목 상세 페이지에 미니 그래프 임베드.

**대체**:
- `chainsight_ui_ux_design.md` §11: 탭 제거 + `/chainsight?focus={symbol}` 딥링크 + 'Chain Sight에서 보기' 버튼.
- `frontend/app/stocks/[symbol]/page.tsx`가 이 패턴으로 수정됨(redesign 00_summary 명시).
- `GraphMiniView.tsx` 컴포넌트는 코드에 잔존하나 종목 상세 진입점에서는 미사용 추정.

### (D-6) CUSTOMER_OF DB 저장 → API 파생으로 대체

**원안 의도**(v1.0): CUSTOMER_OF 별도 관계 저장.
**대체**(v1.3 + v2.1): SUPPLIES_TO만 canonical 저장, API에서 `direction == 'outbound'` 조건으로 `display_type = "CUSTOMER_OF"` 파생.

**구현 위치**: `api/views.py:NeighborGraphView._display_type` (line 532~535), `ChainSightGraphView`의 derived_type (line 91).

---

## 문서-구현 정합성 이슈 (참고)

### (E) Deep dive workspace 추가 기능 — 설계 문서 없음

다음 코드는 존재하나 `docs/chain_sight/plan/` 어디에도 해당 설계 문서가 없습니다:

| 코드 | 라인 수 | 비고 |
|------|--------|------|
| `chainsight/models/saved_path.py` (SavedPath, PathAction) | — | migration 0006 |
| `chainsight/services/path_service.py` | 255 | 경로 저장/조회 |
| `chainsight/services/expand_service.py` | 91 | 노드 확장 |
| `chainsight/services/alternatives_service.py` | 175 | 대안 후보 |
| `chainsight/services/recheck_service.py` | 255 | 재확인 로직 |
| `chainsight/views/watchlist_views.py` (`WatchlistViewSet`) | — | `/chainsight/watchlist/*` REST |
| `chainsight/serializers/path_watchlist.py` | — | |
| `chainsight/management/commands/regenerate_summary_paths.py` | — | |

이들은 redesign_v1의 "범위 밖"에도 등재되지 않으며, Deep dive workspace의 후속 기능(저장/추천/재확인)으로 보입니다. **설계 문서 부재가 단일 갭** — Deep dive workspace 종합 설계서 작성이 필요합니다.

### (E-2) `remaining_work_plan.md` (2026-04-04) vs task_done 모순

- `remaining_work_plan.md`는 CS-2-1b SensitivityProfile, CS-2-1c InsiderSignal을 "남은 작업 1·2번"으로 표기.
- 한편 `docs/chain_sight/task_done/CS-2-1b_sensitivity_profile.md` 및 `CS-2-1c_insider_signal.md`는 완료 보고서 존재.
- **결론**: remaining_work_plan은 2026-04-04 시점 스냅샷으로 이후 완료된 항목을 반영하지 못함. 갱신이 필요.

### (E-3) `chain_sight_redesign_V1` 00_summary.md "범위 밖" 항목

다음은 명시적 "후속 작업"으로 큐잉되어 있어 미구현이 정상:
- Heat Score 계산
- 전환 애니메이션 (300ms ease-out, bounce)
- LLM 기반 chain title/summary 생성
- 2차 카드 설명 (relation_summary, why_now, insight_summary)
- 모바일 대응
- Graph Data Science (PageRank, Louvain) — *하지만 `remaining_work_plan.md`는 M3로 완료 표기 → 노출만 미적용이 정확*

---

## 우선순위 제안 (감사자 권고, 의사결정 미포함)

1. **(B-1) Sensitivity/Insider 적재량 실측**: `python manage.py shell -c "from chainsight.models import CompanySensitivityProfile, CompanyInsiderSignal; ..."`로 건수 확인 후 `remaining_work_plan.md` 또는 `PROGRESS.md` 갱신.
2. **(C-7) GDS 결과 API 노출**: `pagerank`/`community_id`/`betweenness`가 :Stock 노드에 적재되어 있으나 마켓 뷰 API에 미노출. `SectorGraphView`·`NeighborGraphView` 응답에 노드 속성 추가만으로 즉시 활용 가능.
3. **(E-1) Deep dive workspace 설계서 작성**: SavedPath/WatchlistViewSet/alternatives/recheck/expand 등 코드 우선 구현된 자산을 문서화. 1인 개발 원칙(README.md 원칙 3 "코드 안 열어도 파악 가능")과 직접 충돌.
4. **(C-1) Heat Score 모델 도입**: 단일 컴포넌트 모델(`SeedHeatScore`) + Beat 1개 추가만으로 `sector_summary.heat_total` 자연 활성화 — 비용 대비 효과 큼.
5. **(C-3) 2차 카드 설명 필드**: 1차 템플릿은 충분히 작동 중. LLM 도입 전에 `neighbors` 응답에 `relation_summary` 등을 정적 템플릿으로라도 채워 BE/FE 인터페이스 합의 가능.

---

**감사 종료.** 본 보고서는 read-only 분석이며 코드/문서 수정을 포함하지 않습니다.
