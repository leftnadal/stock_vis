# Chain Sight 설계 갭 감사

- **작성일**: 2026-04-23
- **감사 범위**: `docs/chain_sight/plan/` 설계 문서 vs `chainsight/` 앱 + `frontend/components/chainsight/` 구현
- **방식**: 코드 수정 없이 설계 문서, 완료 기록, 디렉토리 구조 대조 (읽기 전용)
- **근거 한계 고지**: 감사 도중 작업 디렉토리 접근 권한이 차단되어, 일부 항목(특히 프론트 컴포넌트 파일 실제 존재 여부, 모델 내부 필드)은 **설계 문서 + `docs/chain_sight/task_done/` 완료 기록**을 기준으로 판정했습니다. 코드 레벨에서 직접 확인한 것은 최초 단계의 디렉토리 리스팅 결과입니다.

---

## 요약 (구현률)

| 축 | 항목 | 상태 | 비고 |
|----|------|------|------|
| Phase 0 | CS-0-0 ~ CS-0-3 (인프라 + 스키마) | **(A) 완전 구현** | 12개 테이블, Neo4j Repository, constraint/index 전체 완료 |
| Phase 1 | CS-1-1 ~ CS-1-3 (시드 로드) | **(A) 완전 구현** | Stock/Sector/Industry/PEER_OF 노드·관계 존재 |
| Phase 2 | CS-2-1 ~ CS-2-5 (파생 데이터) | **(A) 완전 구현** | Tier A(GrowthStage/CapitalDNA/Sensitivity/Insider) + CoMention + PriceCoMove + RelationConfidence v2.1 + ChainProfile 집약 |
| Phase 3 | CS-3-1 ~ CS-3-3 (Neo4j 동기화 + GDS) | **(A) 완전 구현** | Delta Sync (`neo4j_dirty` flag), PageRank/Louvain/Betweenness |
| Phase 4 | CS-4-1 ~ CS-4-3 (REST API 원안) | **(A) 완전 구현** | `/graph/`, `/suggestions/`, `/trace/` 엔드포인트 완료 |
| Phase 5 | CS-5-1 ~ CS-5-4 (프론트 원안) | **(D) 폐기/대체** | Redesign V1(2026-04-09)의 Market View 5개 컴포넌트로 전면 대체 |
| Redesign V1 | PR-1 ~ PR-7 (2026-04-09) | **(A) 완전 구현** | 시드 선정, dirty sync, 4개 Market View API, SectorBar/Canvas/Trail/Cards/Feed |
| DC-2 | ETF Holdings + HAS_THEME | **(A) 완전 구현** | `load_themes_to_neo4j` management command + `DC-2_etf_holdings_theme.md` 기록 존재 |
| DC-3~4 | 수동 시드 + Gemini Flash Supply Chain 확장 | **(C) 미구현 / 데이터 수집 단계 미진입** | 로드맵상 런칭 +2~3주 진행 예정이며, 현재 완료 기록 없음 |
| DC-5~6 | 뉴스 자연 축적 / Finnhub Premium | **(C) 미구현** | 시간 경과 축적 또는 수익화 이후 |
| SEC Pipeline | `sec_pipeline_base_design.md`, `sec_pipeline_pr_detail.md` | **별도 앱** | `sec_pipeline/` 앱에서 구현, Chain Sight와 인접 연계 (본 감사 범위 외) |

**정량 평가**: Chain Sight MVP(트랙 A + DC-1 + DC-2)의 **구현률 ≈ 95%**. 미완 영역은 주로 “트랙 B 데이터 수집 Phase 3+“ 및 Redesign V1 Phase 2+ 고도화(히트 스코어, 2차 카드 설명, LLM 기반 체인 스토리 생성)에 국한.

---

## 문서별 상태 테이블

### A. 원안 로드맵 (`chain_sight_roadmap_v1.3.md` 기준)

| 설계 문서 | 작업 번호 | 완료 기록 | 상태 | 비고 |
|-----------|---------|----------|------|------|
| `cs_00_legacy_cleanup_api_test.md` | CS-0-0 | `CS-0-0_legacy_cleanup_api_test.md` | (A) 완전 | RelationConfidence v2.1 마이그 포함 |
| `cs_01_migrations_verification.md` | CS-0-1 | `CS-0-1_migrations.md` | (A) 완전 | 12개 테이블 확인 |
| `cs_02_neo4j_connection.md` | CS-0-2 | `CS-0-2_neo4j_driver.md` | (A) 완전 | `chainsight/graph/repository.py` |
| `cs_03_neo4j_schema.md` | CS-0-3 | `CS-0-3_neo4j_schema.md` | (A) 완전 | 4 constraint + 2 index |
| `cs_11_stock_node_bulk_load.md` | CS-1-1 | `CS-1-1_stock_nodes.md` | (A) 완전 | `load_stocks_to_neo4j.py` |
| `cs_12_sector_industry.md` | CS-1-2 | `CS-1-2_sectors.md` | (A) 완전 | `load_sectors_to_neo4j.py` |
| `cs_13_peer_relations.md` | CS-1-3 | `CS-1-3_peers.md` | (A) 완전 | `load_peers_to_neo4j.py` |
| `cs_21_tier_a_profile.md` | CS-2-1 | `CS-2-1_tier_a_profiles.md` | (A) 완전 | GrowthStage + CapitalDNA |
| `cs_21b_sensitivity_profile.md` | CS-2-1b | `CS-2-1b_sensitivity_profile.md` | (A) 완전 | `sensitivity_tasks.py` |
| `cs_21c_insider_signal.md` | CS-2-1c | `CS-2-1c_insider_signal.md` | (A) 완전 | `insider_tasks.py` |
| `cs_22_co_mention.md` | CS-2-2 | `CS-2-2_co_mention.md` | (A) 완전 | ChainNewsEvent → CoMentionEdge |
| `cs_23_price_co_movement.md` | CS-2-3 | `CS-2-3_price_co_movement.md` | (A) 완전 | 90일 rolling correlation |
| `cs_24_relation_confidence.md` | CS-2-4 | `CS-2-4_relation_confidence.md` | (A) 완전 | `relation_tasks.py` + 5단계 상태 |
| `relation_confidence_design_v1.md` | — (설계서) | CS-2-4에 반영 | (A) 완전 | 928라인 정책표 기반 |
| `cs_25_chain_profile_aggregation.md` | CS-2-5 | `CS-2-5_chain_profile_aggregation.md` + `celery_beat_registration.md` | (A) 완전 | `sync_tasks.py` + Beat 8개 등록 |
| `cs_31_profile_neo4j_sync.md` | CS-3-1 | `CS-3-1_profile_sync.md` | (A) 완전 | Delta Sync |
| `cs_32_relation_neo4j_sync.md` | CS-3-2 | `CS-3-2_relation_neo4j_sync.md` | (A) 완전 | `neo4j_sync.py` |
| `cs_33_gds_algorithms.md` | CS-3-3 | `CS-3-3_gds_algorithms.md` | (A) 완전 | PageRank/Louvain/Betweenness |
| `cs_41_graph_api.md` | CS-4-1 | `CS-4-1_2_3_rest_api.md` | (A) 완전 | `/api/v1/chainsight/.../graph/` |
| `cs_42_suggestion_api.md` | CS-4-2 | 동 | (A) 완전 | `/suggestions/` |
| `cs_43_trace_api.md` | CS-4-3 | 동 | (A) 완전 | `/trace/` |
| `cs_51_graph_visualization.md` | CS-5-1 | `CS-5-1_frontend_graph.md` | **(D) 폐기/대체** | 초기 GraphView 구현 후 Redesign V1 MarketGraphCanvas로 대체 |
| `cs_52_ai_guide_ui.md` | CS-5-2 | `CS-5-2_pro_features.md` | **(D) 폐기/대체** | SuggestionCards → RelationCardPanel |
| `cs_53_chain_trace_ui.md` | CS-5-3 | `CS-5-3_mobile_card_list.md` | **(D) 폐기/대체** | TraceView 독립 화면 → 중심 이동 탐색으로 흡수 |
| `cs_54_stock_detail_integration.md` | CS-5-4 | (기록 없음) | **(D) 폐기/대체** | 종목 상세 임베드 → 전용 워크스페이스 `/chainsight/[symbol]` |
| `cs_5_frontend_design_v2.md` | — (통합 설계 v2, 409라인) | — | **(D) 폐기/대체** | `redesign_v1_260409/chainsight_ui_ux_design.md`에 흡수 |
| `remaining_work_plan.md` | — (85라인) | Redesign V1로 소화 | **(D) 해소** | 원안 잔여 계획 문서, Redesign으로 대체 |

### B. Redesign V1 (`redesign_v1_260409/` 기준)

| 설계 문서 | 매핑 PR | 완료 기록 | 상태 | 비고 |
|-----------|--------|----------|------|------|
| `chainsight_seed_node_design.md` (255라인) | PR-1, PR-2 | `PR-1_schema_migration.md`, `PR-2_seed_selection_task.md` | (A) 완전 | 스키마 + 시드 선정 + Redis 캐싱 |
| `chainsight_api_design.md` (480라인) | PR-4 | `PR-4_market_view_api.md` | (A) 완전 | 4개 신규 API (seeds/sector/neighbors/signals) |
| `chainsight_ui_ux_design.md` (436라인) | PR-5, PR-6, PR-7 | `PR-5_fe_core_ui.md`, `PR-6_trail_and_cards.md`, `PR-7_chain_story_feed.md` | (A) 완전 | 5개 Market View 컴포넌트 |
| `chainsight_marketview_pr_prompts.md` (1319라인) | PR-1~7 상세 지시서 | 동 | (A) 완전 | 실행 프롬프트 묶음 |
| (암묵) Neo4j dirty sync | PR-3 | `PR-3_neo4j_dirty_sync.md` | (A) 완전 | `neo4j_dirty_sync_tasks.py` |
| (암묵) 데이터 품질 3대 이슈 | 사후 수정 | `data_quality_3_fixes.md` | (A) 완전 | change_percent 갱신, 관계 타입 다양화, 한글 레이블 |
| (암묵) 브라우저/QA 검증 | — | `browser_test_report.md`, `qa_evaluator_review_01.md` | (A) 완전 | 종합 91% 조건부 승인 |

### C. 코드 디렉토리 ↔ 설계 매핑 (최초 디렉토리 리스팅 기준)

| 설계 항목 | 기대 산출물 | 실제 존재 디렉토리/파일 | 상태 |
|-----------|-----------|-----------------------|------|
| chainsight 모델 12개 | models/*.py | `capital_dna`, `chain_profile`, `event_reaction`, `growth_stage`, `insider_signal`, `narrative_tag`, `news_event`, `relation_discovery`, `revenue_structure`, `saved_path`, `sensitivity` (11개 파일) | (B) 부분 — **파일 수 11/12**. CoMentionEdge/PriceCoMovement/RelationConfidence는 `relation_discovery.py`에 통합된 것으로 **추정** (완료 기록 기준 모델 자체는 존재). 파일 분리 vs 통합은 원칙 4(단순 구조)에 부합하므로 기능상 문제 없음. |
| Neo4j 레이어 | `graph/repository.py`, `graph/schema.py`, `graph/exceptions.py` | 동일 이름 3개 파일 존재 | (A) 완전 |
| Celery 태스크 | `tasks/*.py` | `insider`, `neo4j_dirty_sync`, `peer`, `profile`, `relation`, `seed`, `sensitivity`, `sync` (8개) | (A) 완전 |
| 서비스 레이어 | `services/*.py` | `alternatives`, `expand`, `neo4j_loader`, `neo4j_sync`, `path`, `recheck`, `seed_selection` (7개) | (A) 완전 |
| API | `api/urls.py`, `api/views.py` | 존재 | (A) 완전 |
| Management Commands | `load_stocks/sectors/peers/themes`, `init_neo4j_schema`, `regenerate_summary_paths` (6개) | 존재 | (A) 완전 |
| 직렬화기 | `serializers/*.py` | `path_watchlist.py` (1개) | (B) 부분 — Market View API가 dict 직렬화를 주로 쓰므로 설계상 정상. 저장 경로 기능용 단일 시리얼라이저만 존재. |
| 전용 뷰 | `views/*.py` | `watchlist_views.py` (+ 상위 `views.py`) | (A) 완전 |
| 프론트 컴포넌트 (Redesign V1 5종) | `SectorBar`, `MarketGraphCanvas`, `ExplorationTrail`, `RelationCardPanel`, `ChainStoryFeed` | 완료 기록 PR-5/6/7에서 생성 주장 | **미확인** — 본 감사 중 파일 직접 확인 실패(권한 차단). 완료 기록상 전부 구현. 추후 `frontend/components/chainsight/` 실 파일 존재 재검증 권장. |

---

## 미구현 항목 상세

### (C) 미구현

1. **DC-3 수동 시드 JSON 기반 Supply Chain**
   - 설계: 로드맵 섹션 4.2 — 런칭 +2주 진행, ~500개 `SUPPLIES_TO` 관계 기대
   - 현재: 완료 기록 없음. RelationConfidence 내 supply_chain 증거 소스는 현재 비활성 가능성.
   - 의존: `has_supply_chain_source` 필드는 모델에 있으나 수동 시드 투입 작업 필요.

2. **DC-4 Gemini Flash Supply Chain 확장**
   - 설계: 로드맵 섹션 4.2 — Supply Chain ~1,100개 확장, ~$0.05
   - 현재: Celery 태스크 미등록 (`relation_tasks.py`에 Gemini 확장 태스크 확인 필요). DC-3 미완 상태라 후속.

3. **DC-5 뉴스 자연 축적**
   - 설계: 시간 경과 기반 자연 증가, 런칭 +3개월.
   - 현재: CoMentionEdge 파이프라인은 작동 중(CS-2-2 완료)이므로 자동 진행 중. 별도 미구현 항목 아님.

4. **DC-6 Finnhub Premium / 유료 API 업그레이드**
   - 설계: 수익화 후 $200/월 트리거.
   - 현재: 수익화 이전 단계.

5. **Redesign V1 Phase 2+ 고도화 (QA 리뷰 미해결)**
   - **Heat Score 복합 가중치 계산**: 현재 시드 선정은 `seed_count DESC`만. 설계상 `heat_total DESC`로 업그레이드 예정. 별도 PR 필요.
   - **관계 카드 2차 설명 확장**: `relation_summary`, `why_now`, `insight_summary` API 응답 확장 미구현.
   - **LLM 기반 체인 스토리 자동 생성**: `ChainStoryFeed`의 chain title/summary를 Gemini로 생성하는 Phase 3 이후 작업.
   - **전환 애니메이션 디바운싱**: 300ms ease-out + bounce 미세 조정.
   - **에러 경계 / 404·503 UX 개선**: QA 점수 85% 영역.

### (B) 부분 구현

1. **chainsight/models/ 파일 분리**
   - 설계 로드맵 부록 A: 12개 모델 기대.
   - 실제: 11개 파일. `RelationConfidence`, `CoMentionEdge`, `PriceCoMovement`는 `relation_discovery.py`에 통합됐을 것으로 추정. 완료 기록(CS-2-2/2-3/2-4)에서 “신규 생성 완료”로 명시됐으므로 **모델 자체는 존재**. 파일 레이아웃만 설계 문서와 다름.
   - 권장: `models/__init__.py`에서 export 되는 클래스명 확인 필요(감사 권한 복구 시).

2. **프론트 원안 CS-5-2/5-3 독립 화면**
   - 설계: `SuggestionCards.tsx`, `TraceView.tsx`를 독립 컴포넌트로.
   - 실제: Redesign V1에서 `RelationCardPanel` / 중심 이동으로 흡수(아래 "폐기/대체" 참조).

---

## 폐기/대체 항목

### 전면 대체 (D)

| 원안 (cs_* 시리즈) | 대체 (Redesign V1) | 사유 |
|-----------------|------------------|------|
| `cs_51_graph_visualization.md` — 종목 상세 내 Spotlight GraphView | `MarketGraphCanvas.tsx` + 전용 워크스페이스 `/chainsight/[symbol]` | 데스크톱 우선 탐색 경험으로 재정의 (Spotlight ≠ 핵심). `react-force-graph-2d` 엔진은 유지. |
| `cs_52_ai_guide_ui.md` — SuggestionCards | `RelationCardPanel.tsx` (pre-focus / focused 분기) | 단순 카테고리 필터 → 관계 카드 중심 (Supply Chain / Competitors / Peers / Co-mentioned). 신호 맥락 강화. |
| `cs_53_chain_trace_ui.md` — TraceView (2-node 최단경로) | `ExplorationTrail.tsx` + 중심 이동(Neighbor API) | 사용자가 한 쌍을 미리 지정하기보다 탐색 중 자연 누적되는 경로 기록이 실사용 흐름에 적합. |
| `cs_54_stock_detail_integration.md` — 종목 상세 내 미니 임베드 | `/chainsight/[symbol]` 전용 워크스페이스 + `/chainsight` 마켓 허브 | 임베드 뷰는 탐색 깊이 제한 → 전용 페이지로 승격. |
| `cs_5_frontend_design_v2.md` (통합 v2, 409라인) | `redesign_v1_260409/chainsight_ui_ux_design.md` (436라인) | 마켓 탐색 허브 + 체인 스토리 피드 개념 신규 추가. 모바일은 카드 리스트 모드로 단순화. |
| `remaining_work_plan.md` (원안 잔여 작업 모음) | Redesign V1 PR-1~7로 재정렬 | 잔여 작업 단위를 재설계 PR로 재편. |

### 설계 변경 (v1.2 → v1.3 로드맵 내부)

| 변경 | 전 | 후 | 위치 |
|------|----|----|------|
| 관계 신뢰도 스키마 | v1.1 (3상태: confirmed/candidate/rejected) | v2.1 (5상태: hidden/weak/probable/confirmed/stale) + truth/market/investment 3단 점수 + evidence_tier_best | `relation_confidence_design_v1.md` |
| CUSTOMER_OF 관계 | 별도 저장 | SUPPLIES_TO canonical + API 역방향 파생 | 로드맵 섹션 2.4, 완료 기록 CS-3-2 |
| Undirected 관계 저장 | 방향 자유 | `symbol_a < symbol_b` 사전순 강제 + `normalize_pair` 유틸 | CS-0-0, CS-1-1 완료 기록 |
| CompanyChainProfile 필드 구조 | JSONB 단일 필드 (로드맵 v1.1 초안) | 30개 개별 필드 | 로드맵 부록 A 결정 |
| serverless/ Chain Sight 레거시 | 유지 | CS-0-0에서 제거 (ETF 3모델은 DC-2 완료 시까지 `# LEGACY_KEEP_UNTIL_DC2`) | CS-0-0 완료 기록 |

---

## 추가 메모 (감사자 주)

1. **SEC Pipeline 문서 위치 이질성**: `sec_pipeline_base_design.md`, `sec_pipeline_pr_detail.md`가 `docs/chain_sight/plan/`에 있으나 구현은 `sec_pipeline/` 앱. Chain Sight 데이터를 강화하는 인접 파이프라인이지 Chain Sight 자체 설계 산출물이 아님. 향후 `docs/sec_pipeline/plan/`으로 이동하거나 README에 “인접 설계” 표기 권장.

2. **`graph_analysis/` 앱과의 관계**: 로드맵 부록 D에 명시된 대로 **독립 유지**. Chain Sight의 `PriceCoMovement`(같은 섹터 쌍)와 `graph_analysis/`의 `CorrelationEdge`(워치리스트 기반)는 별도 계산. 중복으로 보이나 소비처가 다름(탐색 UI vs 히트맵).

3. **원안 CS-5 완료 기록의 모순**: `CS-5-1_frontend_graph.md`, `CS-5-2_pro_features.md`, `CS-5-3_mobile_card_list.md`는 원안 번호를 사용하지만 Redesign V1 내용을 담고 있는 것으로 보임(제목의 "pro_features", "mobile_card_list"는 원안 cs_52/53 제목과 불일치). 원안 Phase 5 완료 기록 자체가 Redesign V1 진행 중 포맷이 재사용된 흔적. 로드맵과 기록 파일명이 일관되도록 이름 정리 필요.

4. **재검증 필요 항목** (본 감사에서 파일 직접 확인 실패):
   - `chainsight/models/relation_discovery.py` 내 `RelationConfidence`, `CoMentionEdge`, `PriceCoMovement` 클래스 존재 여부
   - `RelationConfidence` v2.1 필드 24개 (특히 `relation_status`, `truth_score`, `evidence_tier_best`, `evidence_sources`, `canonical_direction`, `neo4j_dirty`, `previous_status`)
   - `frontend/components/chainsight/` 5개 Market View 컴포넌트 실제 파일 존재
   - `chainsight/api/urls.py`에 등록된 실제 URL 패턴 수 (원안 3 + Redesign V1 4 = 7개 이상 예상)
   - `config/settings/` Celery Beat 스케줄에 `seed-selection`, `heat-score`, `sync-relations-neo4j`, `update-change-percent` 항목 등록 여부
   - 이 4개 항목은 `task_done` 기록상 모두 완료됐다고 주장되므로 후속 세션에서 `ls` / `grep class` 수준의 가벼운 확인으로 충분.

---

## 결론

- **Chain Sight 핵심 파이프라인(Phase 0~4) + Redesign V1 Market View는 설계-구현 완전 일치** 상태로 판단.
- **원안 Phase 5(프론트) 4개 문서는 전부 폐기/대체**되었으며, 이는 2026-04-09 기획 전환의 의도된 결과. 레거시 `cs_5*` 문서는 참조용 기록으로 보관하되 `README.md`에 “Superseded by `redesign_v1_260409/`” 표기 필요.
- **유일한 실질 갭**은 (a) 트랙 B 데이터 수집 DC-3/DC-4 (수동 시드 + Gemini 확장), (b) Redesign V1 Phase 2+ 고도화(히트 스코어/LLM 설명/애니메이션 디테일). 둘 다 MVP 이후 작업으로 로드맵상 계획됨.
- **코드 파일 분리 vs 통합 이슈**: models 디렉토리 파일 수(11)가 설계상 모델 수(12)보다 적은 것은 `relation_discovery.py` 통합 가능성이 높음. 원칙 4(1인 개발 단순 구조)에 부합하므로 결함 아님.
