# Chain Sight 설계 갭 감사

> **감사일**: 2026-05-18
> **대상**: `docs/chain_sight/plan/` 설계서 ↔ `chainsight/` + `frontend/components/chainsight/` 구현
> **방식**: 읽기 전용 (코드 미수정)
> **선행 문서**: `chain_sight_roadmap_v1.3.md`, `redesign_v1_260409/`(v2.x), `cs_5_frontend_design_v2.md`, `cs_51~54_*.md`

---

## 요약 (구현률)

| 영역 | 설계서 수 | 완전 구현 | 부분 구현 | 미구현 | 폐기/대체 |
|------|---------:|---------:|---------:|------:|--------:|
| Phase 0 인프라 (CS-0-0~0-3) | 4 | 4 | 0 | 0 | 0 |
| Phase 1 시드 로드 (CS-1-1~1-3) | 3 | 3 | 0 | 0 | 0 |
| Phase 2 파생 파이프라인 (CS-2-1~2-5) | 7 | 5 | 2 | 0 | 0 |
| Phase 3 Neo4j 동기화 + GDS (CS-3-1~3-3) | 3 | 3 | 0 | 0 | 0 |
| Phase 4 REST API (CS-4-1~4-3 + 마켓뷰 4종) | 7 | 7 | 0 | 0 | 0 |
| Phase 5 프론트엔드 (cs_51~54 / v2 / redesign) | — | — | — | — | cs_51~54 → v2/redesign 대체 |
| 데이터 수집 (DC-1~6) | 6 | 2 | 1 | 3 | 0 |
| Redesign V1 PR (PR-1~7) | 7 | 7 | 0 | 0 | 0 |
| Redesign 범위 밖 (Phase 2 Heat Score / 애니/LLM/모바일) | 4 | 0 | 1 | 3 | 0 |

**총평**:
- **Phase 0 ~ Phase 4 = 핵심 백엔드/API 사실상 완전 구현.**
- 프론트엔드는 `redesign_v1_260409`가 `cs_51~54` 원안과 `cs_5_frontend_design_v2`를 **부분 대체**(Market View 신규, Deep Dive Workspace는 유지).
- DC-3/DC-4/DC-6 미실행, DC-5(뉴스 자연 축적)는 계속 진행.
- Redesign에서 명시한 **Heat Score 모델, 300ms 전환 애니메이션, LLM relation_summary, 모바일 대응**은 범위 밖으로 누락.

---

## 문서별 상태 테이블

### Phase 0 — 인프라 (CS-0-0 ~ CS-0-3)

| 설계서 | task_done | 구현 위치 | 상태 |
|--------|----------|----------|------|
| `cs_00_legacy_cleanup_api_test.md` | `CS-0-0_legacy_cleanup_api_test.md` | serverless Chain Sight 6 view + FE 8 컴포넌트 제거 | (A) 완전 |
| `cs_01_migrations_verification.md` | `CS-0-1_migrations.md` | `chainsight/migrations/0001_initial.py` (12 테이블) | (A) 완전 |
| `cs_02_neo4j_connection.md` | `CS-0-2_neo4j_driver.md` | `chainsight/graph/repository.py:Neo4jGraphRepository` (PID 기반 lazy init) | (A) 완전 |
| `cs_03_neo4j_schema.md` | `CS-0-3_neo4j_schema.md` | `chainsight/management/commands/init_neo4j_schema.py` | (A) 완전 |

### Phase 1 — 시드 데이터 로드 (CS-1-1 ~ CS-1-3)

| 설계서 | 구현 | 상태 |
|--------|------|------|
| `cs_11_stock_node_bulk_load.md` | `load_stocks_to_neo4j.py` (532 :Stock) | (A) 완전 |
| `cs_12_sector_industry.md` | `load_sectors_to_neo4j.py` (17 Sector + 128 Industry + 1,038 BELONGS_TO) | (A) 완전 |
| `cs_13_peer_relations.md` | `chainsight/tasks/peer_tasks.py` + 8,350 PEER_OF | (A) 완전 |

### Phase 2 — 파생 파이프라인 (CS-2-1 ~ CS-2-5)

| 설계서 | 구현 위치 | 상태 |
|--------|----------|------|
| `cs_21_tier_a_profile.md` | `profile_tasks.py:calculate_all_profiles` (GrowthStage 480, CapitalDNA 473) | (A) 완전 |
| `cs_21b_sensitivity_profile.md` | `sensitivity_tasks.py` + `CompanySensitivityProfile` | (A) 완전 |
| `cs_21c_insider_signal.md` | `insider_tasks.py` + `CompanyInsiderSignal` | (A) 완전 |
| `cs_22_co_mention.md` | `relation_tasks.py:extract_co_mentions` + ChainNewsEvent 중간 저장 | (A) 완전 |
| `cs_23_price_co_movement.md` | `relation_tasks.py:calculate_price_co_movement` | (A) 완전 |
| `cs_24_relation_confidence.md` / `relation_confidence_design_v1.md` | `relation_tasks.py:update_relation_confidence` (소스별 타입 분리: PEER_OF/CO_MENTIONED/PRICE_CORRELATED) + `check_stale_and_decay` | **(B) 부분** — Truth-only `truth_score` 산출. `market_score`, `investment_relevance` 필드는 모델에는 존재하나 **MVP 정의대로 null 유지**(설계 의도와 일치). `relation_basis_summary` 템플릿 생성 로직은 모델에 필드 존재하나 채워지는지 별도 확인 필요 |
| `cs_25_chain_profile_aggregation.md` | `sync_tasks.py:aggregate_chain_profiles` + `CompanyChainProfile`(30 개별 score 필드, JSONB 채택 안 함 — 의도된 결정) | **(B) 부분** — task 함수 존재. 실 적재 결과(0건 → 채워졌는지) Stale, 운영 가동 여부는 별도 검증 권장 |

### Phase 3 — Neo4j 동기화 + GDS (CS-3-1 ~ CS-3-3)

| 설계서 | 구현 | 상태 |
|--------|------|------|
| `cs_31_profile_neo4j_sync.md` | `sync_tasks.py:sync_profiles_to_neo4j` (`neo4j_synced` 플래그 → `neo4j_dirty` 일원화: migration 0008) | (A) 완전 |
| `cs_32_relation_neo4j_sync.md` | `chainsight/services/neo4j_sync.py:sync_dirty_relations` (confirmed+probable+market weak 허용, RELATED_TO 레거시 정리) | (A) 완전 |
| `cs_33_gds_algorithms.md` | Neo4j 5.26.3 + GDS 2.13.2 / PageRank·Louvain·Betweenness 결과 Neo4j 속성으로 반영 | (A) 완전 — 단, **GDS 정기 Beat task는 코드에 없음**(수동 실행으로 보임, 부분 위험) |

### Phase 4 — REST API (CS-4-1~4-3 + Redesign 마켓 뷰 4종)

| 엔드포인트 | View 클래스 | 상태 |
|-----------|------------|------|
| `GET /{symbol}/graph/` (CS-4-1) | `ChainSightGraphView` | (A) 완전 |
| `GET /{symbol}/suggestions/` (CS-4-2) | `ChainSightSuggestionView` | (A) 완전 |
| `GET /trace/` (CS-4-3) | `ChainSightTraceView` | (A) 완전 |
| `GET /seeds/` (Redesign) | `SeedListView` | (A) 완전 |
| `GET /sector/{sector}/graph/` (Redesign) | `SectorGraphView` | (A) 완전 |
| `GET /{symbol}/neighbors/` (Redesign) | `NeighborGraphView` (display_type 파생, CUSTOMER_OF) | (A) 완전 |
| `GET /signals/` (Redesign) | `SignalFeedView` | (A) 완전 |

### Phase 5 — 프론트엔드

| 설계서 | 후속 설계서 | 구현 | 상태 |
|--------|------------|------|------|
| `cs_51_graph_visualization.md` (원안) | → `cs_5_frontend_design_v2.md` → `redesign_v1_260409/chainsight_ui_ux_design.md` | `GraphCanvas.tsx`, `graphStyles.ts`, `app/chainsight/[symbol]/page.tsx` | (D) **폐기/대체** (cs_51 → v2/redesign으로 흡수) |
| `cs_52_ai_guide_ui.md` | → 동상 | `AIGuidePanel.tsx`, `RelationCardPanel.tsx` (pre-focus/focused) | (D) 대체 |
| `cs_53_chain_trace_ui.md` | → 동상 | `TracePathView.tsx` (Deep Dive Workspace 측에 잔존) | (D) 대체 |
| `cs_54_stock_detail_integration.md` | → 동상 | `GraphMiniView.tsx` + `app/stocks/[symbol]/page.tsx` chain-sight 탭 | **(B) 부분** — 설계 v2.2는 "탭 제거 → 딥링크"로 명시했으나 `chain-sight` 탭은 잔존하여 미니 뷰 + 딥링크 버튼 두 형태 공존 |

#### Redesign V1 PR (마켓 뷰 신축)

| PR | task_done | 핵심 구현 | 상태 |
|----|----------|----------|------|
| PR-1 스키마 마이그레이션 | `PR-1_schema_migration.md` | migration 0005 (`previous_status`, `neo4j_dirty`) + 0008(플래그 통합) | (A) 완전 |
| PR-2 시드 선정 Task | `PR-2_seed_selection_task.md` | `services/seed_selection.py` (price/volume/sector_outlier/relation/comention) + `tasks/seed_tasks.py` | (A) 완전 |
| PR-3 Neo4j Dirty Sync | `PR-3_neo4j_dirty_sync.md` | `services/neo4j_sync.py` + `tasks/neo4j_dirty_sync_tasks.py` (neo4j 큐) | (A) 완전 |
| PR-4 마켓 뷰 API 4종 | `PR-4_market_view_api.md` | 위 Phase 4 표 참조 | (A) 완전 |
| PR-5 FE 코어 (상태/섹터바/그래프) | `PR-5_fe_core_ui.md` | `explorationStore.ts`, `useMarketView.ts`, `SectorBar`, `MarketGraphCanvas`, `app/chainsight/page.tsx` | (A) 완전 |
| PR-6 트레일 + 관계 카드 | `PR-6_trail_and_cards.md` | `ExplorationTrail.tsx`, `RelationCardPanel.tsx` (pre-focus/focused) | (A) 완전 |
| PR-7 체인 스토리 피드 | `PR-7_chain_story_feed.md` | `ChainStoryFeed.tsx` (useInfiniteQuery) | (A) 완전 |

### 데이터 수집 (DC-1 ~ DC-6)

| DC | 설계 위치 | 상태 |
|----|----------|------|
| DC-1 Peer + Industry | roadmap §4.2 | (A) 완전 — 8,350 PEER_OF + 1,038 BELONGS_TO |
| DC-2 ETF Holdings → Theme | `DC-2_etf_holdings_theme.md` | (A) 완전 — 21 :Theme + 534 HAS_THEME (운용사 CSV 경유) |
| DC-3 수동 시드 JSON (Supply Chain ~500) | roadmap §4.5 | (C) 미구현 — 수동 JSON 시드 파일 미확인 |
| DC-4 Gemini Flash Supply Chain 확장 (~1,100) | roadmap §4.6 | (C) 미구현 |
| DC-5 Marketaux 뉴스 자연 축적 | roadmap §4.7 | **(B) 부분** — CoMentionEdge 적재 파이프라인은 가동(2,748 쌍 → CO_MENTIONED 193 Neo4j), 자연 누적 진행 중 |
| DC-6 Finnhub Premium | roadmap §4.8 | (C) 미구현 (수익화 이후 트리거, 의도된 보류) |

### Redesign V2 범위 밖 (Roadmap 또는 redesign에 명시된 후속 항목)

| 항목 | 설계 위치 | 상태 | 비고 |
|------|----------|------|------|
| **Heat Score 계산 (Phase 2)** | `chainsight_seed_node_design.md` §3, `chainsight_api_design.md` §8 | **(B) 부분** — `tasks/seed_tasks.py:calculate_heat_scores` 함수 존재 + Neo4j 노드 속성으로 사용. **그러나 `SeedHeatScore` 별도 모델은 미생성** (마이그레이션 없음) | components/seed_rank 필드 없이 Neo4j 속성만 사용하는 단순 변형 |
| 300ms 전환 애니메이션 / bounce | UX design §7 | (C) 미구현 — FE 컴포넌트에 명시적 transition 미발견 |
| LLM 기반 relation_summary / why_now / insight_summary | API design §4 "2차 필드 확장" | (C) 미구현 — 1차 템플릿(고정 문구) 단계 |
| 모바일 대응 (card-first FAB 등) | UX design §13 | **(B) 부분** — `MobileCardList.tsx`는 CS-5-3(이전 설계 기준)에서 구축. redesign v2 매트릭스 기반 모바일 분기는 미정 |
| GDS 정기 Beat | `cs_33_gds_algorithms.md` | (C) 미구현 — 1회 수동 실행 결과만 task_done에 기록, 정기 task 코드 미발견 |

---

## 미구현 항목 상세

### 1. DC-3 수동 시드 JSON (Supply Chain ~500)

- **설계 의도**: `docs/chain_sight/seeds/manual_supply_chain.json` 형태로 핵심 공급망 수동 시드.
- **현 상태**: `chainsight/` 하위 시드 디렉토리/JSON 미발견. `SUPPLIES_TO` 관계는 CUSTOMER_OF 2건 외 Neo4j 카운트가 task_done 보고서에 명시되지 않음.
- **영향**: M1.5 다음 단계 차단. RelationConfidence Tier 1 evidence (수동 시드) 미공급.

### 2. DC-4 Gemini Flash 공급망 확장

- **설계 의도**: DC-3 시드 → LLM 추가 추출로 ~1,100건 도달.
- **현 상태**: `chainsight/` 하위 LLM 호출 task 미발견(`relation_tasks.py`에 LLM 추출 함수 없음).
- **영향**: SUPPLIES_TO truth 관계가 사실상 비어 있음.

### 3. SeedHeatScore 모델 (redesign Phase 2)

- **설계 의도**: `SeedHeatScore(stock, date, heat_score, components, seed_rank)` 모델 신설.
- **현 상태**: 모델 미존재. Heat Score 계산 함수(`calculate_heat_scores`)는 있으나 결과를 PostgreSQL에 영속화하지 않고 Neo4j 노드 속성에만 반영하는 단순화 채택.
- **영향**: 시드 순위 변동의 시계열 추적 불가, `components` 분해 미보존.

### 4. LLM 기반 2차 카드 설명

- **설계 의도**: `relation_summary`, `why_now`, `insight_summary` 필드를 `neighbors/` 응답에 추가.
- **현 상태**: 1차 템플릿(고정 문구) 단계.

### 5. 300ms 전환 애니메이션 + bounce

- **설계 의도**: 중심 이동 시 좌측 페이드/우측 확대, 시드 노드 bounce.
- **현 상태**: `MarketGraphCanvas.tsx` 등에서 transition 키워드 미발견.

### 6. GDS 정기 배치 task

- **설계 의도**: `chainsight/tasks/gds_tasks.py` 신설하여 주 1회 실행.
- **현 상태**: `gds_tasks.py` 파일 없음, Celery Beat에도 미등록. 1회성 결과만 보유.
- **영향**: PageRank/Community ID가 신규 노드/관계 추가에 따라 stale 됨.

---

## 폐기/대체 항목

### 1. `cs_51_graph_visualization.md` ~ `cs_54_stock_detail_integration.md` (원안)

- **대체**: `cs_5_frontend_design_v2.md`(2026-04-04) → `redesign_v1_260409/chainsight_ui_ux_design.md`(v2.2, 2026-04-10).
- **차이**: 원안은 종목 상세 탭 내 인터랙티브 그래프. v2/redesign은 전용 워크스페이스(`/chainsight/[symbol]`) + 마켓 뷰 허브(`/chainsight`) 이중 구조.
- **현 코드 구조**:
  - 종목 상세 `chain-sight` 탭에 `GraphMiniView` (정적 미니 그래프) 유지 + `/chainsight?focus=` 딥링크 버튼 추가. **redesign v2.2의 "탭 제거" 지침과 불일치 — 부분 적용**.

### 2. `RelationConfidence` v1 (3단계 confirmed/candidate/rejected)

- **대체**: `relation_confidence_design_v1.md` v1.1 → v2.1 5단계(`hidden/weak/probable/confirmed/stale`).
- **현 코드**: migration 0005~0008로 v2.1 정착. `previous_status`, `neo4j_dirty` 일원화 완료.

### 3. `CUSTOMER_OF` 별도 Neo4j 엣지 저장

- **대체**: `SUPPLIES_TO` canonical 단방향 저장 + API에서 `display_type` 파생.
- **현 코드**: `NeighborGraphView._display_type`이 SUPPLIES_TO + outbound → CUSTOMER_OF 변환.
- **잔여 위험**: Neo4j에 레거시 CUSTOMER_OF 엣지 2건이 DC-2 보고서에 남아 있음(정리 여부 미확인).

### 4. `RELATED_TO` 단일 엣지 라벨

- **대체**: `data_quality_3_fixes.md`에서 소스별 타입(PEER_OF / CO_MENTIONED / PRICE_CORRELATED)으로 분리. 레거시 RELATED_TO 1회성 정리 완료.

### 5. CompanyChainProfile `profile_data` JSONB 단일 필드 안

- **대체**: 30개 개별 score 필드 구조(원칙 4 부합 결정). roadmap v1.2에서 공식화.

### 6. `synced_to_neo4j` / `neo4j_synced` 이중 플래그

- **대체**: migration 0008에서 `neo4j_dirty` 단일 패턴으로 통합.

---

## 보강 권장 (감사 결론, 의사결정 필요)

1. **GDS 정기 Beat 등록**: PageRank/Community 결과 stale. `chainsight/tasks/gds_tasks.py` + Beat 주 1회 추가 검토.
2. **DC-3 수동 시드 JSON 도입**: SUPPLIES_TO truth 관계 공급 부재. relation_confidence v2.1의 Tier 1 evidence 활용 차단 중.
3. **종목 상세 Chain Sight 탭 처리**: redesign v2.2 지침("탭 제거 → 딥링크")과 현 코드 차이 정리.
4. **Heat Score 영속화**: `SeedHeatScore` 모델 도입 여부 결정(현재 Neo4j 속성만 사용 — 시계열 분석 불가).
5. **CompanyChainProfile 적재 검증**: `aggregate_chain_profiles` task가 운영에서 실제로 데이터를 채우는지 별도 점검.

---

**END OF AUDIT**
