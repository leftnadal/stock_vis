# Chain Sight 설계 갭 감사

> **작성일**: 2026-05-15
> **분석 대상**: `docs/chain_sight/plan/` 30+ 설계 문서 vs `chainsight/` 백엔드 + `frontend/components/chainsight/` 프론트
> **방식**: 읽기 전용 — 코드/문서 수정 없음
> **분류 기준**:
> - **(A) 완전 구현** — 설계의 모든 항목이 코드에 존재
> - **(B) 부분 구현** — 일부만 구현, 미구현 항목 명시
> - **(C) 미구현** — 설계만 있고 코드 없음
> - **(D) 폐기/대체** — 설계 방향이 변경되어 대체 구현으로 옮겨감

---

## 요약 (구현률)

| Phase | 문서 수 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 가중 구현률 |
|-------|--------|-------|-------|---------|-----------|-----------|
| Phase 0 (CS-0-0~3) | 4 | 2 | 2 | 0 | 0 | 88% |
| Phase 1 (CS-1-1~3) | 3 | 3 | 0 | 0 | 0 | 100% |
| Phase 2 (CS-2-1~5 + 1b/c) | 7 | 6 | 1 | 0 | 0 | 90% |
| Phase 3 (CS-3-1~3) | 3 | 1 | 1 | 1 (GDS) | 0 | 50% |
| Phase 4 (CS-4-1~3) | 3 | 2 | 1 | 0 | 0 | 90% |
| Phase 5 — 기존 cs_5* | 5 | 2 | 0 | 0 | 3 (대체) | 40% (D 비중 큼) |
| Redesign V1 — PR-1~7 | 7 | 5 | 2 | 0 | 0 | 90% |
| 보조 (sec_pipeline, DC-2, relation_confidence) | 4 | 2 | 1 | 1 (Phase 3 D-1~3) | 0 | 65% |
| **전체** | **36** | **23** | **8** | **2** | **3** | **~80%** |

### 큰 그림

- **Phase 0~2 데이터 파이프라인**: 거의 완성. RelationConfidence 정책 엔진(CS-2-4)만 부분.
- **Phase 3 GDS 알고리즘**: 완전 미구현 (M3 마일스톤 미달성). pagerank/community/betweenness 노드 속성 없음.
- **Phase 4 REST API**: 기존 3개(graph/suggestions/trace) + redesign V1 신규 4개(seeds/sector/neighbors/signals) 모두 동작. 일부 응답 필드 누락.
- **Phase 5 프론트**: 원래 cs_51~54 설계는 redesign V1 (PR-5/6/7)로 마켓 뷰가 신설되며 부분 흡수. Deep dive workspace는 cs_51~54 컴포넌트 기반 유지.
- **Redesign V1 (260409) 7개 PR**: PR-1~7 모두 구현 완료. seed_selection, neo4j_dirty sync, 마켓 뷰 5개 영역, signals API 등.
- **장기 미구현**: GDS, Phase 2 SeedHeatScore 모델, Phase 3 D-1/2/3(임베딩+lagged correlation), 2차 카드 설명 LLM, 모바일 마켓 뷰.

---

## 문서별 상태 테이블

### Phase 0 — 인프라 기반

| 문서 | 상태 | 핵심 산출물 | 갭 |
|------|------|------------|----|
| `cs_00_legacy_cleanup_api_test.md` | **B** | 레거시 제거, API 테스트 5개, RelationConfidence v2.1 | showmigrations "12개 [X]" 체크 항목과 실제 마이그레이션 8개(0001~0008) 불일치 — 테이블 12개는 0001~0004에 분산 생성됨 |
| `cs_01_migrations_verification.md` | **A** | 12개 chainsight_* 테이블, RelationConfidence 28필드, normalize_pair | — |
| `cs_02_neo4j_connection.md` | **A** | `chainsight/graph/repository.py` Protocol + Neo4jGraphRepository | — (PID 기반 lazy init 포함, Celery fork 안전) |
| `cs_03_neo4j_schema.md` | **B** | constraint 4개 + index 2개 | 인덱스 4개 추가 구현(stock_market_cap, stock_industry) — 로드맵 미정의 인덱스 (원칙 위반 소지, 기능적 무해) |

### Phase 1 — 시드 로드

| 문서 | 상태 | 핵심 산출물 | 갭 |
|------|------|------------|----|
| `cs_11_stock_node_bulk_load.md` | **A** | `load_stocks_to_neo4j` (532 노드) | — |
| `cs_12_sector_industry.md` | **A** | `load_sectors_to_neo4j` (Sector 18 + Industry 131 + BELONGS_TO 2,398) | 설계 기대치(11/70/1,000)를 초과 적재 — 데이터 풍부화로 양호 |
| `cs_13_peer_relations.md` | **A** | `load_peers_to_neo4j` (PEER_OF 2,816개 / Finnhub+FMP 병합) | — |

### Phase 2 — 파생 데이터 파이프라인

| 문서 | 상태 | 핵심 산출물 | 갭 |
|------|------|------------|----|
| `cs_21_tier_a_profile.md` | **A** | GrowthStage 480 + CapitalDNA 473 + `profile_tasks.py` shared_task | — |
| `cs_21b_sensitivity_profile.md` | **A** | `sensitivity_tasks.py` + 503건 적재 (FMP Revenue Geo 통합) | — |
| `cs_21c_insider_signal.md` | **A** | `insider_tasks.py` + 503건 적재 | institutional/short 데이터 미확보로 smart_money_signal = insider_signal만 사용 (API 제약, 정책 아님) |
| `cs_22_co_mention.md` | **A** | `relation_tasks.extract_co_mentions` (CoMentionEdge 744쌍) | — |
| `cs_23_price_co_movement.md` | **A** | `relation_tasks.calculate_price_co_movement` (2,473건) | — |
| `cs_24_relation_confidence.md` + `relation_confidence_design_v1.md` | **B** | `update_relation_confidence` + 5단계 status + truth_score 필드 | **중대 갭**: ① relation_type별 정책표 미반영 (PEER_OF만 처리, SUPPLIES_TO/COMPETES_WITH/HAS_THEME/BELONGS_TO_* 미처리), ② peer_sources 합산 시 Tier 1 독립 ×2 규칙 무시, ③ stale decay 시간 계수 오차 (설계 90/270/360일 vs 실제 90/60/30일), ④ truth_score 타입 IntegerField 설계↔FloatField 구현 |
| `cs_25_chain_profile_aggregation.md` | **A** | `aggregate_chain_profiles` (CompanyChainProfile 503건 + 30개 개별 필드) | neo4j_synced→neo4j_dirty 의미 반전 (의도된 변경) |

### Phase 3 — Neo4j 동기화 + GDS

| 문서 | 상태 | 핵심 산출물 | 갭 |
|------|------|------------|----|
| `cs_31_profile_neo4j_sync.md` | **A** | `sync_tasks.sync_profiles_to_neo4j` neo4j_dirty 기반 delta sync | neo4j_synced→neo4j_dirty 플래그 명칭 변경 (의미 동일) |
| `cs_32_relation_neo4j_sync.md` | **B** | `services/neo4j_sync.py` confirmed/probable upsert + hidden/weak/stale 삭제 | 설계 "RELATED_TO 단일 엣지 + relation_type 속성" vs 실제 "동적 라벨 (PEER_OF/SUPPLIES_TO/CO_MENTIONED 등)" — Market 관계 처리 방식 불일치 |
| `cs_33_gds_algorithms.md` | **C** | (없음) | **완전 미구현**. `chainsight/tasks/gds_tasks.py` 파일 없음. pagerank_score/community_id/betweenness_score 노드 속성 없음. task_done 기록상 "GDS 플러그인 미설치 → 보류"(2026-04-03 이후 진행 없음). M3 마일스톤 미달성 |

### Phase 4 — REST API

| 문서 | 상태 | 엔드포인트 | 갭 |
|------|------|-----------|----|
| `cs_41_graph_api.md` | **B** | `GET /api/stocks/{symbol}/chainsight/graph/` | edges[].explanation 필드 누락 (basis_summary 매핑 안됨), min_confidence 파라미터 미지원 (depth만 지원) |
| `cs_42_suggestion_api.md` | **A** | `GET /api/stocks/{symbol}/chainsight/suggestions/` (peers/supply_chain/same_sector/co_mentioned/community 카테고리) | pagerank/community 활용은 GDS 미구현으로 불가 (대체 쿼리로 처리) |
| `cs_43_trace_api.md` | **A** | `GET /api/chainsight/trace/` shortestPath | — |

### Phase 5 — 기존 프론트엔드 설계 (cs_5*)

| 문서 | 상태 | 비고 |
|------|------|------|
| `cs_5_frontend_design_v2.md` | **D** (부분 대체) | 마켓 뷰 부분은 redesign V1로 신설. Deep dive 부분만 cs_5_v2 기반 유지 |
| `cs_51_graph_visualization.md` | **D** (부분 대체) | Deep dive `GraphCanvas.tsx` 살아있으나 마켓 뷰 그래프는 `MarketGraphCanvas.tsx`로 신설 |
| `cs_52_ai_guide_ui.md` | **A** | `AIGuidePanel.tsx`(Deep dive) + `SectorBar.tsx`(마켓 뷰) 두 곳에서 구현 |
| `cs_53_chain_trace_ui.md` | **A** | Deep dive `TracePathView.tsx`/`FullPathView.tsx` 존재 |
| `cs_54_stock_detail_integration.md` | **A** | `GraphMiniView.tsx`(미니 뷰) + `/chainsight?focus={symbol}` 딥링크 모두 동작 |

### Redesign V1 (260409) — 마켓 뷰 PR

| PR | 상태 | 핵심 산출물 | 갭 |
|----|------|------------|----|
| PR-1 스키마 마이그레이션 | **A** | previous_status, neo4j_dirty, SeedSnapshot, SavedPath/PathAction 마이그레이션 0005~0008 | SavedPath 모델 정의 위치만 미확인 (마이그레이션 존재) |
| PR-2 시드 선정 Task | **B** | `services/seed_selection.py` + `tasks/seed_tasks.py` + 8개 SEED_REASONS + `get_market_date()` | comention_surge 기준 완화 (설계 ≥avg7d×2.0 vs 실제 ≥5), Beat 스케줄 시간 차이 (설계 12:00 UTC vs 실제 13:00 UTC) |
| PR-3 Neo4j Dirty Sync | **A** | `services/neo4j_sync.py` + `tasks/neo4j_dirty_sync_tasks.py` | — (Phase 3 cs_32 항목과 동일 평가) |
| PR-4 마켓 뷰 API 4종 | **B** | seeds/, sector/{sector}/graph/, {symbol}/neighbors/, signals/ 4개 View 모두 구현, Redis 캐시, display_type 파생, cross_edges | signals path[] 구조 차이 (설계 `relation_to_next` 필드 vs 실제 edges[] 분리), sector_graph relation_category 명시 누락 (default truth) |
| PR-5 FE 코어 UI | **A** | `SectorBar`, `MarketGraphCanvas`, `explorationStore`(Zustand), `useMarketView` | — |
| PR-6 트레일 + 카드 | **A** | `ExplorationTrail`, `RelationCardPanel`, `SeedCard`, `RelationCard`, `RelationFilterChips` | — |
| PR-7 체인 스토리 피드 | **A** | `ChainStoryFeed` + 무한 스크롤 + chain highlight | — |

### 보조 / 후속 작업

| 문서/주제 | 상태 | 비고 |
|----------|------|------|
| `sec_pipeline_base_design.md` + `sec_pipeline_pr_detail.md` | **B** | `sec_pipeline/` 별도 앱 존재 (8개 모델), `sync_dirty_to_neo4j` 5분, `sec-seed-relations-to-chainsight` 12:00 UTC 등록. LLM 추출 단계 진행 중 (~40%) |
| `task_done/DC-2_etf_holdings_theme.md` | **A** | `load_themes_to_neo4j.py` + Theme 21노드 + HAS_THEME 534관계 |
| `task_done/celery_beat_registration.md` | **B** | seed-selection 13:00, heat-score 07:00, neo4j-dirty-sync 토 04:30, sec-seed-relations 12:00 — 모두 등록되었으나 일부 시간이 설계서와 차이 |
| Phase 2 SeedHeatScore 모델 | **C** | task(`seed_tasks.py:95-158`)는 구현되어 Neo4j 노드에 직접 저장. **DB 모델은 미생성**. 가중치도 설계와 다름 (설계 6항목 vs 실제 4항목) |
| Phase 3 D-1/D-2/D-3 (Embedding/Lagged Correlation/Propagation) | **C** | 전체 미구현. ChromaDB/Gemini Embedding 통합 없음. 3개 Beat 태스크(text-conditional, lagged-correlation, propagation-weight) 미등록 |

---

## 미구현 항목 상세

### 🔴 Critical (M3 마일스톤 차단)

#### 1. CS-3-3 Graph Data Science (GDS) 완전 미구현
- **요구사항**: PageRank, Louvain Community, Betweenness Centrality 결과 → :Stock 노드 속성
- **현 상태**:
  - `chainsight/tasks/gds_tasks.py` 파일 없음
  - `pagerank_score`, `community_id`, `betweenness_score` 속성 없음
  - GDS projection/write Cypher 없음
  - task_done 기록: "GDS 플러그인 미설치 → 보류"(2026-04-03)
- **영향**:
  - M3 마일스톤("Neo4j 풍부해짐") 미달성
  - CS-4-2 Suggestion API의 community 카테고리는 대체 쿼리로 우회 처리됨
  - Redesign V1 sector_graph의 node_size를 market_cap만으로 결정 (centrality 미사용)
- **선행 조건**: Neo4j GDS 플러그인 설치 (Community Edition 무료, Apache 2.0)

### 🟡 Major (정책 엔진 정확도 영향)

#### 2. CS-2-4 RelationConfidence 정책 엔진 부분 구현
설계서 `relation_confidence_design_v1.md` v2.1의 정책표가 코드에 일부만 반영됨.
- **미처리 관계 타입** (5종):
  - SUPPLIES_TO (confirmed/probable/weak 규칙 있으나 코드 없음)
  - COMPETES_WITH
  - HAS_THEME
  - BELONGS_TO_SECTOR
  - BELONGS_TO_INDUSTRY
- **PEER_OF 판정 단순화**:
  - 설계: "Tier 1 증거 ×2 독립 → confirmed, Tier 1 + same_industry → probable"
  - 구현: `len(peer_sources) >= 2` 단일 조건 (peer/industry 합산)
- **CO_MENTIONED 기준 차이**:
  - 설계: raw correlation 값 기반
  - 구현: count 기반
- **PRICE_CORRELATED 임계값 차이**:
  - 설계: ≥0.7만 weak (≥0.5는 hidden)
  - 구현: ≥0.5 기준
- **stale decay 시간 계수**:
  - 설계: confirmed→stale 90일, probable→weak 270일, weak→hidden 360일
  - 구현: 90 / 60 / 30일 (시간 ×4.5 빠름)
- **truth_score 타입 불일치**:
  - 설계: IntegerField 대표값 85/60/35/15
  - 구현: FloatField

#### 3. CS-4-1 Graph API 응답 누락 필드
- `edges[].explanation` 필드 미포함 (`relation_basis_summary` 매핑 안됨)
- `min_confidence` 쿼리 파라미터 미지원 (depth만 지원)

#### 4. Redesign V1 PR-4 signals API path[] 구조 불일치
- 설계: `path[].relation_to_next` 필드로 단계별 관계 표시
- 구현: edges[] 별도 리스트 분리 — 프론트 호환성 주의 (현재 ChainStoryFeed가 어느 형태를 소비하는지 추가 확인 필요)

### 🟢 Minor (장기 로드맵)

#### 5. Phase 2 SeedHeatScore 모델 미생성
- task는 구현되어 Neo4j 노드에 직접 저장
- DB 모델 (chainsight_seed_heat_score) 부재 — 분석/재계산 시 trail 부족
- 가중치도 설계 6항목(price/volume/relation/comention/news/gds_centrality) vs 실제 4항목(price/volume/relation_change/news_activation)

#### 6. Phase 3 D-1/D-2/D-3 전체 미구현
- D-1: Gemini Embedding + ChromaDB 통합 → text_conditional_prob
- D-2: lagged correlation + volume_response → propagation_weight
- D-3: 사후 검증 + 가중치 학습
- Beat 태스크 3종 미등록
- 예상 기간: 3개월+ (60 거래일 데이터 축적 후)

#### 7. 마이그레이션 개수 명세 불일치
- CS-0-0 체크리스트: "showmigrations 12개 [X]"
- 실제: 마이그레이션 파일 8개(0001~0008), 그러나 chainsight_* 테이블 수는 12개 (0001~0004에 분산 생성)
- 체크리스트 문구 자체의 오류 (실해 없음)

#### 8. CS-0-3 추가 인덱스
- 로드맵 미정의 인덱스 2개(stock_market_cap, stock_industry) 추가 구현
- 원칙 위반 소지 있으나 기능적 무해

#### 9. Beat 스케줄 시간 차이
- chainsight-seed-selection: 설계 12:00 UTC vs 실제 13:00 UTC
- chainsight-heat-score: 설계 11:30 vs 실제 07:00 UTC
- chainsight-neo4j-dirty-sync: 설계 토 05:30 vs 실제 토 04:30
- 운영상 무해, 문서 동기화만 필요

#### 10. 향후 카드 설명 LLM 통합
- 1차 템플릿(프론트 규칙)만 구현
- 2차 API 필드(`relation_summary`, `why_now`, `insight_summary`) 미구현
- LLM 기반 explanation 미구현
- 모두 설계서에서 "Future enhancement"로 명시된 항목

---

## 폐기/대체 항목

### 1. cs_5_frontend_design_v2 → redesign_v1 마켓 뷰 (부분 대체)
- **변경 시점**: 2026-04-09
- **사유**: 마켓 뷰의 위상이 "Deep dive로 가는 런처"에서 "독립 완결 탐색 허브(breadth-first)"로 전략 변경
- **대체 관계**:
  - 마켓 뷰 부분 → redesign_v1 PR-5/6/7로 신설 (`MarketGraphCanvas`, `SectorBar`, `ExplorationTrail`, `RelationCardPanel`, `ChainStoryFeed`)
  - Deep dive workspace 부분(`/chainsight/[symbol]`)은 cs_5_v2 기반 유지
- **잔존 코드**: `GraphCanvas.tsx`, `NodeDetailPanel.tsx`, `AIGuidePanel.tsx`, `FilterPanel.tsx`, `MobileCardList.tsx`, `TracePathView.tsx`, `FullPathView.tsx`

### 2. cs_51 Graph Visualization → MarketGraphCanvas 별도 신설
- 단일 ForceGraph2D 컴포넌트 → 두 컴포넌트로 분기 (Deep dive용 + 마켓 뷰 전용)
- 사유: 에고 그래프(depth N) vs 마켓 오버뷰(radial layout) 용도 차별화
- 폐기 아님 — 두 컴포넌트가 동시 운용

### 3. CompanyChainProfile JSONB 단일 필드 → 30개 개별 필드 (이미 결정됨)
- v1.1 로드맵: `profile_data (JSONB)` 단일 필드 제안
- v1.2 결정: 30개 개별 필드 유지 (원칙 4 — 1인 개발 단순 구조)
- 현재 구현: 30개 개별 필드 ✅

### 4. CUSTOMER_OF 별도 저장 → SUPPLIES_TO canonical + API 역방향 파생
- v1.3 로드맵 변경 (2026-04-02)
- 구현 확인: `NeighborGraphView._derive_display_type()` (코드 line 532-535)
  ```python
  if rel_type == 'SUPPLIES_TO' and direction == 'outbound':
      return 'CUSTOMER_OF'
  ```
- ✅ 설계 정확히 반영

### 5. RELATED_TO 단일 엣지 + relation_type 속성 → 동적 라벨 (PEER_OF/SUPPLIES_TO/CO_MENTIONED 등)
- 설계 cs_32: 모든 관계를 `RELATED_TO` 단일 엣지로 통합, 속성에 relation_type 저장
- 구현: 동적 라벨 (Cypher 타입) 사용
- 사유 미문서화 — 사실상 설계 변경. 현 운영에는 문제 없으나 설계서 갱신 필요

### 6. neo4j_synced 플래그 → neo4j_dirty 의미 반전
- 변경 위치: 마이그레이션 0008(unify_neo4j_flags), 2026-04-09 audit P0 #9
- True 의미 반전: synced=True(완료) → dirty=True(동기화 필요)
- ✅ 마이그레이션으로 정식 전환, 모든 sync 코드에 반영됨

---

## 부록 A — 디렉토리 매핑 인덱스

```
설계 문서 → 코드 매핑
─────────────────────────────────────────────────────────
cs_00, cs_01, cs_03   → chainsight/migrations/0001~0008.py
cs_02                 → chainsight/graph/{repository,schema,exceptions}.py
cs_11~13              → chainsight/management/commands/load_*.py
cs_21, cs_21b/c       → chainsight/tasks/{profile,sensitivity,insider}_tasks.py
                        chainsight/models/{growth_stage,capital_dna,sensitivity,insider_signal}.py
cs_22, cs_23, cs_24   → chainsight/tasks/relation_tasks.py
                        chainsight/models/{news_event,relation_discovery}.py
cs_25                 → chainsight/tasks/sync_tasks.py
                        chainsight/models/chain_profile.py
cs_31, cs_32          → chainsight/services/neo4j_sync.py
                        chainsight/tasks/{sync,neo4j_dirty_sync}_tasks.py
cs_33                 → (없음 — 미구현)
cs_41~43              → chainsight/api/{urls,views}.py
                        chainsight/services/{path,expand,alternatives}_service.py
cs_51~54              → frontend/components/chainsight/{GraphCanvas,AIGuidePanel,...}.tsx
                        frontend/app/chainsight/[symbol]/page.tsx
redesign_v1 PR-1~3    → chainsight/migrations/0005~0008.py
                        chainsight/services/{seed_selection,neo4j_sync}.py
                        chainsight/tasks/{seed,neo4j_dirty_sync}_tasks.py
                        chainsight/utils.py (get_market_date)
redesign_v1 PR-4      → chainsight/api/views.py (SeedListView, SectorGraphView,
                                                  NeighborGraphView, SignalFeedView)
redesign_v1 PR-5~7    → frontend/components/chainsight/{SectorBar,MarketGraphCanvas,
                                                          ExplorationTrail,RelationCardPanel,
                                                          ChainStoryFeed,SeedCard,RelationCard,
                                                          RelationFilterChips}.tsx
                        frontend/lib/stores/explorationStore.ts
                        frontend/hooks/useMarketView.ts
                        frontend/app/chainsight/page.tsx
sec_pipeline_*        → sec_pipeline/ (별도 앱)
DC-2 ETF              → chainsight/management/commands/load_themes_to_neo4j.py
```

## 부록 B — 다음 우선순위 (감사 결과 기반)

1. **GDS 알고리즘 활성화** (CS-3-3) — Neo4j GDS 플러그인 설치 + `gds_tasks.py` 구현 → M3 달성
2. **RelationConfidence 정책표 풀 구현** (CS-2-4) — 5개 미처리 관계타입 + stale decay 보정
3. **SeedHeatScore DB 모델 신설** — Phase 2 분석/재계산 가능성 확보
4. **신규 응답 필드 보강** — CS-4-1 explanation/min_confidence, signals path[].relation_to_next
5. **설계서 동기화** — Beat 스케줄 시간, 마이그레이션 개수 표기, RELATED_TO→동적 라벨 변경 사유 문서화

---

**END OF REPORT**
