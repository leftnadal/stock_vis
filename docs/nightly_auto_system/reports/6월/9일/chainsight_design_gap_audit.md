# Chain Sight 설계 갭 감사

> **감사일**: 2026-06-09
> **유형**: 읽기 전용 (코드 수정 없음)
> **범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` (백엔드) + `frontend/{app,components}/chainsight/` (프론트엔드) 대조
> **방법**: 설계 문서별 핵심 산출물 추출 → 코드 file:line 대조 → A/B/C/D 분류. 병렬 5개 탐색 에이전트 + 충돌 항목 직접 재검증.

---

## 0. 핵심 정정 (에이전트 충돌 재검증 결과)

감사 중 발견된 교차검증 충돌을 직접 코드로 재확인했다. 아래는 **확정된 사실**이다.

| 쟁점 | 1차 주장 | 재검증 결과 (확정) | 근거 |
|------|---------|-------------------|------|
| Chain Sight Celery Beat 등록 여부 | "미등록 (settings.py에 없음)" | **등록됨 — 11개 스케줄** | `config/celery.py:691~766` (`settings.py`가 아니라 `config/celery.py`의 `CELERY_BEAT_SCHEDULE`) |
| CS-2-1b/c (Sensitivity/Insider) 실행 | "미실행" | **코드 구현 완료 + Beat 스케줄됨** | `calculate_all_profiles`가 두 프로파일 포함(`celery.py:685-694` 주석), `sensitivity_tasks.py`/`insider_tasks.py` 완전 구현 |
| Stale decay 임계값 | "오류" | **고정값 90/60/30일 사용 (설계는 동적)** | `relation_tasks.py:418-435` — 설계 미준수(단순화)이나 동작 자체는 정상 |

> ⚠️ `remaining_work_plan.md`(2026-04-04 작성)는 "CS-2-1b/c 미착수"로 기록하나, **현재 코드에는 이미 구현·스케줄 완료** 상태다. 문서가 코드보다 뒤처져 있다.

---

## 1. 요약 (구현률)

### 전체 분포

| 분류 | 설계 문서 수 | 비율 |
|------|-------------|------|
| **(A) 완전 구현** | 16 | 57% |
| **(B) 부분 구현** | 8 | 29% |
| **(C) 미구현** | 1 | 4% |
| **(D) 폐기/대체** | 0 (순수 폐기 없음) | — |
| 참고/로드맵 문서 (분류 외) | 3 | — |

> **종합 구현률 ≈ 82%** (A=100%, B=평균 60%, C=0% 가중 추정)

### 레이어별 상태

| 레이어 | 문서 범위 | 상태 |
|--------|----------|------|
| **기반 (인프라/Neo4j 연결)** | cs_00~03 | ✅ A (100%) |
| **데이터 로드 (Neo4j 노드/엣지)** | cs_11~13 | ✅ A (100%) |
| **기업 프로파일** | cs_21, 21b, 21c | ✅ A (100%) |
| **관계 추출** | cs_22, 23 | ✅ A (100%) |
| **관계 신뢰도 엔진** | cs_24, relation_confidence_v1 | ⚠️ B (모델 완전, 점수/상태 로직 단순화) |
| **프로파일 집계** | cs_25 | ✅ A |
| **Neo4j 동기화** | cs_31, 32 | ✅ A |
| **GDS 알고리즘** | cs_33 | ❌ C (보류 — 플러그인 미설치) |
| **기본 REST API (Deep Dive)** | cs_41~43 | ⚠️ B (구현됨, 일부 필드/카테고리 누락) |
| **마켓뷰 API (redesign)** | chainsight_api_design | ✅ A |
| **Deep Dive 프론트엔드** | cs_51~54, cs_5_v2 | ⚠️ B (코어 완성, 프로 기능 미구현) |
| **마켓뷰 프론트엔드 (redesign)** | chainsight_ui_ux, marketview_pr | ⚠️ B (5 컴포넌트 완성, 일부 인터랙션 부분) |
| **시드 노드 선정 (redesign)** | chainsight_seed_node | ⚠️ B (Phase 1 완료, Phase 2/3 미완) |

### redesign 관계 결론

> **redesign_v1_260409/ 는 기존 cs_* 설계를 "대체"하지 않고 "추가"한다.**
> - cs_00~54는 시스템 기반(인프라→데이터→파이프라인→동기화→기본 API→Deep Dive UI)으로 **유지·완료**.
> - redesign은 그 위에 **마켓뷰(`/chainsight`) UI/API 레이어 + 시드 선정 로직**을 신규 구성.
> - PR-1~7 (마켓뷰 redesign)은 2026-04-10 구현 완료, 04-11 브라우저 테스트 7/8 통과, 04-13 데이터 품질 3건 수정, QA 91% 조건부 승인.
> - 유일한 부분 폐기: 종목 상세의 구 "Chain Sight 탭" → 마켓뷰로 대체(redesign PR-5).

---

## 2. 문서별 상태 테이블

### 2.1 기반 + Neo4j (cs_00~03, cs_11~13, cs_31~33)

| 문서 | 핵심 산출물 | 코드 위치 | 상태 |
|------|------------|----------|------|
| cs_00 legacy cleanup + API test | 레거시 정리, API 5개 테스트, RelationConfidence v2.1 마이그레이션 | `migrations/0001~0005`, task_done CS-0-0 기록 | **A** |
| cs_01 migrations verification | 12테이블, normalize_pair, unique_together | `utils.py:28-36`, `models/relation_discovery.py:158` | **A** |
| cs_02 neo4j connection | GraphRepository Protocol, Neo4jGraphRepository, 팩토리 | `graph/repository.py:12-193`, `graph/__init__.py:6-22` | **A** |
| cs_03 neo4j schema | Constraint 4 + Index 2, initialize/verify_schema, mgmt cmd | `graph/schema.py:10-94`, `management/commands/init_neo4j_schema.py` | **A** |
| cs_11 stock node bulk load | get_stock_data_for_neo4j, load_stocks_to_neo4j, mgmt cmd | `services/neo4j_loader.py:32-66` | **A** |
| cs_12 sector/industry | Sector/Industry 노드 + BELONGS_TO_* 관계 | `services/neo4j_loader.py:72-122` | **A** |
| cs_13 peer relations | finnhub/fmp peer fetch, PEER_OF 무방향, Celery task | `services/neo4j_loader.py:128-239`, `tasks/peer_tasks.py:23-46` | **A** |
| cs_31 profile neo4j sync | sync_profiles_to_neo4j, neo4j_dirty 델타 동기화 | `tasks/sync_tasks.py:107-170`, Beat `celery.py:734` | **A** |
| cs_32 relation neo4j sync | sync_relations_to_neo4j, confirmed/probable upsert + stale 삭제 | `tasks/sync_tasks.py:173-207`, `services/neo4j_sync.py:22-98`, Beat `celery.py:741` | **A** |
| cs_33 gds algorithms | run_gds_algorithms (PageRank/Louvain/Betweenness write) | **없음** | **C** |

### 2.2 프로파일 + 관계 (cs_21~25, relation_confidence_v1)

| 문서 | 핵심 산출물 | 코드 위치 | 상태 |
|------|------------|----------|------|
| cs_21 tier A profile | GrowthStage(6단계), CapitalDNA, calculate_all_profiles | `models/growth_stage.py`, `models/capital_dna.py`, `tasks/profile_tasks.py:41-284` | **A** |
| cs_21b sensitivity | SensitivityProfile, FMP 지역매출, rate/forex 분류 | `models/sensitivity.py`, `tasks/sensitivity_tasks.py:71-299` | **A** |
| cs_21c insider signal | InsiderSignal, Finnhub 90일, smart_money | `models/insider_signal.py`, `tasks/insider_tasks.py:29-150` | **A** |
| cs_22 co-mention | ChainNewsEvent, CoMentionEdge, normalize_pair | `models/news_event.py`, `models/relation_discovery.py:12-34`, `tasks/relation_tasks.py:18-123` | **A** |
| cs_23 price co-movement | PriceCoMovement, 90일 correlation (numpy) | `models/relation_discovery.py:36-61`, `tasks/relation_tasks.py:126-208` | **A** |
| cs_24 relation confidence | v2.1 모델 24필드 + truth/market 점수 + 5단계 상태 | 모델 `relation_discovery.py:94-180` 완전 / 로직 `relation_tasks.py:212-435` 단순화 | **B** |
| cs_25 chain profile aggregation | CompanyChainProfile 집계, neo4j_dirty, Beat 8종 | `models/chain_profile.py`, `tasks/sync_tasks.py:15-104`, Beat `celery.py:691~766` | **A** |
| relation_confidence_design_v1 | calculate_truth_and_status / _calculate_market_status / 관계타입별 정책표 / Manual Seed 프로토콜 | 핵심 함수 부재, 하드코딩 대체 | **B** |

### 2.3 REST API (cs_41~43 + redesign API)

| 문서 | 엔드포인트 | 코드 위치 | 상태 |
|------|-----------|----------|------|
| cs_41 graph api | `GET <symbol>/graph/` (depth, rel_types, min_confidence) | `api/views.py:59-113` | **B** (depth만, explanation/basis_summary 누락) |
| cs_42 suggestion api | `GET <symbol>/suggestions/` (5 카테고리) | `api/views.py:117-216` | **B** (5중 3: supply_chain/community 누락) |
| cs_43 trace api | `GET trace/?from&to&max_depth` | `api/views.py:222-292` | **B** (alternative_paths만 누락) |
| redesign chainsight_api_design | `seeds/`, `sector/<sector>/graph/`, `<symbol>/neighbors/`, `signals/` | `api/views.py:300-934` | **A** (neighbors center.volume_ratio/signal_count 미세 누락) |
| redesign chainsight_seed_node | Phase1 시드선정 / Phase2 heat / Phase3 embedding | `services/seed_selection.py`, `tasks/seed_tasks.py` | **B** (Phase1 완료, Phase2 부분, Phase3 없음) |

> **URL 변경**: 구 설계는 `/api/stocks/{symbol}/chainsight/*`, 실제는 `/api/v1/chainsight/*`로 통일. (CLAUDE.md 규칙과 일치)

### 2.4 프론트엔드 (cs_51~54, cs_5_v2 + redesign UI)

| 문서 | 핵심 컴포넌트/화면 | 구현 파일 | 상태 |
|------|-------------------|----------|------|
| cs_51 graph visualization | GraphView(spotlight/lazy expansion), depth 전환, 색상 체계 | `GraphCanvas.tsx`, `graphStyles.ts` | **B** (기본 렌더 OK, spotlight/lazy 미명시) |
| cs_52 ai guide ui | 카테고리 카드 + Trace 입력 | `AIGuidePanel.tsx` | **A** |
| cs_53 chain trace ui | 경로 하이라이트 + 단계 설명 | `TracePathView.tsx`, `FullPathView.tsx` | **B** (텍스트 경로만, 그래프 하이라이트 미구현) |
| cs_54 stock detail integration | 종목 상세 미니뷰 + "전체 탐색" | `GraphMiniView.tsx` (컴포넌트 존재) | **B** (탭 통합 적용 미확인) |
| cs_5_frontend_design_v2 | 3-panel 워크스페이스, CTA 5종, 프로기능(PER오버레이/노드비교) | `app/chainsight/[symbol]/page.tsx`, `NodeDetailPanel.tsx`, `FilterPanel.tsx`, `MobileCardList.tsx` | **B** (코어 완성, PER 오버레이·노드 비교·Watchlist CTA 미구현) |
| redesign chainsight_ui_ux | 마켓뷰: SectorBar/MarketGraphCanvas/ExplorationTrail/RelationCardPanel/ChainStoryFeed | `components/chainsight/` 동명 파일 | **B** (5 컴포넌트 완성, 일부 인터랙션 부분) |
| redesign marketview_pr_prompts | PR-1~7 (스키마→시드→sync→API→FE코어→트레일/카드→스토리피드) | PR-1~7 task_done 완료 기록 | **A** |

---

## 3. 미구현 항목 상세

### (C) cs_33 — GDS 알고리즘 [완전 미구현 / 보류]
- **부재 증거**: `apps/chain_sight/tasks/` 내 `gds*.py` 없음. `config/celery.py`에 `run_gds_algorithms`/`pagerank`/`louvain`/`betweenness` Beat 없음.
- **읽기만 존재**: `services/path_service.py`가 노드의 `pagerank`/`betweenness` 속성을 **읽기만** 함. 쓰는(write) 주체가 없어 수동 세팅 없이는 항상 비어 있음. `management/commands/regenerate_summary_paths.py`에 "run after GDS rerun" 주석 → GDS 실행은 별도 전제.
- **task_done 근거**: `CS-3-3_gds_algorithms.md` = "⏸️ 보류 (GDS 플러그인 미설치)". → **의도된 보류**, 누락 사고 아님.

### (B) cs_24 / relation_confidence_design_v1 — 관계 신뢰도 로직 단순화
모델 필드(24개)는 **완전 구현**(`relation_discovery.py:94-180`). 그러나 설계서 §10~13의 계산 로직이 단순화/미준수:
1. **`calculate_truth_and_status()` 통합 함수 부재** — `relation_tasks.py:212-398`에 하드코딩 분기. PEER_OF/CO_MENTIONED/PRICE_CORRELATED만 부분 처리, **SUPPLIES_TO / COMPETES_WITH / HAS_THEME 판정 로직 없음**.
2. **Market 관계에 confirmed 부여** — 설계는 "Market 관계는 probable까지만". 코드는 `correlation>=0.8`/`co_mention_count>=10`에서 confirmed 부여(`relation_tasks.py:328-372`). *설계 위반 (확인 권장)*.
3. **Stale decay 고정 임계값** — 설계는 `stale_threshold_days × 1.5 / ×2` 동적. 코드는 고정 90/60/30일(`relation_tasks.py:418-435`). *동작은 정상, 설계 단순화*.
4. **evidence_sources / relation_basis_summary 단순 템플릿** — 설계의 풍부한 구조·11종 문구 미구현.
5. **Manual Seed provenance 프로토콜** (design_v1 §9) 미구현.

### (B) cs_42 — Suggestion API 카테고리 부족
- 설계 5종 중 **supply_chain(SUPPLIES_TO), community(community_id) 미구현**. community는 GDS(cs_33) 의존이라 연쇄 미구현.
- peers는 PEER_OF만(COMPETES_WITH 누락), same_industry는 설계의 BELONGS_TO_SECTOR가 아닌 BELONGS_TO_INDUSTRY로 구현.

### (B) cs_41 / cs_43 — API 응답 필드 미세 누락
- cs_41: `explanation`(basis_summary) 필드 누락, `rel_types`/`min_confidence` 쿼리 파라미터 미지원.
- cs_43: `alternative_paths` 필드 누락 (shortestPath 단일 경로만).
- redesign neighbors: `center.volume_ratio`, `neighbors[].signal_count` 누락.

### (B) 프론트엔드 미구현 핵심
- **PER 오버레이 토글** (cs_5_v2 §6-2) — 미구현.
- **노드 비교 모드** (Ctrl+Click, cs_5_v2 §6-3) — 미구현.
- **NodeDetailPanel Watchlist 추가 CTA** — 설계 5 CTA 중 Watchlist 버튼 미구현(`NodeDetailPanel.tsx:86-99`, 3개만 동작). ※단 별도 `WatchButton.tsx` + `/chainsight/watchlist/` 라우트는 존재 → 진입 경로 차이.
- GraphCanvas spotlight/lazy expansion, TracePathView 그래프 하이라이트, ChainStoryFeed highlightedChain 전파 — 인터랙션 레이어 부분 구현.

### (B) chainsight_seed_node — Phase 2/3
- **Phase 1 (시장 시그널 + 관계 변화)** 완전 구현(`seed_selection.py`). signal_count/seed_type 우선순위/Redis+SeedSnapshot 3단 폴백 완성.
- **Phase 2 Heat Score**: `calculate_heat_scores()` task 존재 + Beat 스케줄(`celery.py:748`)되나, sector_summary 정렬이 아직 seed_count 기준(heat_total 미반영).
- **Phase 3 (Gemini Embedding + ChromaDB, propagation_weight)**: 미구현.

---

## 4. 폐기/대체 항목

순수 폐기(D) 문서는 **없다**. redesign은 기존 설계 위에 레이어를 추가했다. 다만 아래 부분 대체/정리가 있었다.

| 대상 | 변경 | 근거 |
|------|------|------|
| 종목 상세 "Chain Sight 탭" (구 cs_54 통합 방향) | 비활성화 → 마켓뷰(`/chainsight`)로 진입 경로 대체 | redesign PR-5, `00_summary.md` |
| 구 API URL `/api/stocks/{symbol}/chainsight/*` | `/api/v1/chainsight/*`로 통일 | `api/urls.py` |
| ETFProfile/ETFHolding/ThemeMatch 모델 | DC-2 완료 시 제거 예정 (현재 LEGACY_KEEP 태그 유지) | task_done CS-0-0 |
| 카테고리 카드 체계 (cs_52) | 마켓뷰에서 시드카드(pre-focus) + 관계카드(focused)로 재구성 | redesign chainsight_ui_ux |
| graph_redesign_v2 (시멘틱 방사형 레이아웃) | **설계서만 존재, 미구현** (2026-04-27) | roadmap 추적 |

---

## 5. 참고 사항

- **SEC Pipeline** (`sec_pipeline_base_design.md`, `sec_pipeline_pr_detail.md`)은 `docs/chain_sight/plan/`에 있으나 **별도 앱 `apps/sec_pipeline/`** 소관. CLAUDE.md상 구현 완료로 표기됨. 본 감사는 chainsight 범위로 한정해 분류 외 처리.
- **로드맵/계획 문서** (`chain_sight_roadmap_v1.3.md`, `remaining_work_plan.md`)는 명세가 아닌 추적 문서로 분류 외. 단, `remaining_work_plan.md`는 코드보다 뒤처짐(§0 참조) — 갱신 권장.

### 후속 권고 (우선순위)
1. **P1 — 관계 신뢰도 로직 정합화**: Market 관계 confirmed 부여 여부를 설계와 맞출지 결정. SUPPLIES_TO/COMPETES_WITH/HAS_THEME 판정 추가 검토.
2. **P2 — GDS 활성화**: Neo4j GDS 플러그인 설치 + `run_gds_algorithms` 구현 → cs_42 community 카테고리 연쇄 해소.
3. **P2 — Heat Score Phase 2 마감**: sector_summary 정렬을 heat_total로 전환.
4. **P3 — 문서 동기화**: `remaining_work_plan.md`의 "CS-2-1b/c 미착수" 표기를 "완료"로 갱신.
5. **P3 — API 응답 필드 보완**: neighbors signal_count/volume_ratio, graph explanation, trace alternative_paths.

---

*본 감사는 읽기 전용이며 코드를 수정하지 않았다. 모든 분류는 file:line 근거에 기반한다.*
