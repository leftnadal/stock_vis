# Chain Sight 설계 갭 감사

> **감사일**: 2026-06-04
> **유형**: 읽기 전용 (코드 미수정)
> **범위**: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` + `frontend/{app,components}/chainsight/` 구현 대조
> **방법**: 설계 문서 33개 + 완료기록 34개 읽기 + 코드 심볼 레벨 교차검증 (4-way 병렬 감사)

---

## 요약 (구현률)

Chain Sight는 **설계서 대비 구현 완성도가 매우 높음**. 백엔드 파이프라인(Phase 0~4)은 거의 완전 구현, 프론트엔드는 두 트랙(원안 cs_5x + redesign_v1)이 모두 코드로 실재한다.

| 영역 | 설계 문서 수 | 완전(A) | 부분(B) | 미구현(C) | 폐기·대체(D) | 구현률 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Phase 0 인프라 (cs_00~03) | 4 | 3 | 1 | 0 | 0 | ~90% |
| Phase 1 시드로드 (cs_11~13) | 3 | 3 | 0 | 0 | 0 | 100% |
| Phase 2 파이프라인 (cs_21~25) | 7 | 5 | 1 | 0 | 2(소스대체) | ~90% |
| Phase 3 동기화/GDS (cs_31~33) | 3 | 2 | 0 | 1(자동화) | 0 | ~75% |
| Phase 4 API (cs_41~43) | 3 | 3 | 0 | 0 | 0(경로재배치) | 100% |
| Phase 5 FE 원안 (cs_51~54+v2) | 5 | 4 | 1(프로기능) | 0 | 0(리네임) | ~85% |
| **redesign_v1 (PR-1~7)** | 4 | 7/7 PR | 0 | 0 | 0 | 100% |
| **종합** | — | — | — | — | — | **~90%** |

**핵심 결론 3줄**
1. 백엔드 관계 발견 엔진(Tier A/B 프로파일 + CoMention + PriceCoMove + RelationConfidence v2.1 + Neo4j sync)은 **task + 모델 모두 완전 구현**, 실데이터도 적재됨(RelationConfidence 3,527건).
2. **redesign_v1_260409가 프론트엔드 패러다임을 "종목 중심 ego-graph" → "시장 탐색 허브"로 대체**했고, 7개 PR 전부 코드에 실재. cs_5x 원안 컴포넌트도 deep-dive workspace로 살아있음(이중 트랙 공존).
3. 갭은 **GDS 자동 재계산 task 부재**(1회 수동 실행만), **InsiderSignal 기관/공매도 지표 누락**, **프로 투자자 Advanced FE 기능 미구현**, **serverless 레거시 미제거** 4건에 집중.

> ⚠️ **로드맵 버전 주의**: `plan/`의 최신본은 `chain_sight_roadmap_v1.3.md`이나, `docs/chain_sight/update_v2/ROADMAP_v1.4.md` + `update_v2/task_done/`가 더 최신 진행상황(GDS 실행 기록 등)을 담고 있다. 본 감사는 지시대로 `plan/` 기준이며, update_v2는 보조 참조로 표기한다.

---

## 문서별 상태 테이블

### Phase 0 — 인프라

| 문서 | 작업ID | 분류 | 근거 (구현 파일 / 심볼) |
|------|:---:|:---:|------|
| cs_00 legacy_cleanup_api_test | CS-0-0 | **B 부분** | RelationConfidence v2.1 마이그레이션 ✅, `normalize_pair` ✅(`utils.py:28`), API 테스트 5건 기록(decisions). **미완**: serverless 레거시(`StockRelationship`/`CategoryCache` + 관련 서비스) 미제거 — `services/serverless/`에 잔존 |
| cs_01 migrations_verification | CS-0-1 | **A 완전** | 모델 14 db_table 존재(설계 "12"보다 2개↑: saved_path/path_action 후속 추가). RelationConfidence 24필드 + unique_together 충족 |
| cs_02 neo4j_connection | CS-0-2 | **A 완전** | `graph/repository.py:Neo4jGraphRepository` PID 기반 lazy driver, bulk upsert/health_check/node_count 전부 존재 |
| cs_03 neo4j_schema | CS-0-3 | **A 완전** | `graph/schema.py` CONSTRAINTS 4 + INDEXES 2, `management/commands/init_neo4j_schema.py` |

### Phase 1 — 시드 로드

| 문서 | 작업ID | 분류 | 근거 |
|------|:---:|:---:|------|
| cs_11 stock_node_bulk_load | CS-1-1 | **A 완전** | `services/neo4j_loader.py:load_stocks_to_neo4j` + command(--limit/--dry-run). :Stock 532 적재 |
| cs_12 sector_industry | CS-1-2 | **A 완전** | `neo4j_loader.load_sectors_to_neo4j` + command. :Sector 18 + :Industry 131 + BELONGS_TO |
| cs_13 peer_relations | CS-1-3 | **A 완전** | `neo4j_loader`(finnhub+fmp peers) + `tasks/peer_tasks.py:fetch_and_load_peers`. PEER_OF 2,816 |

### Phase 2 — 파생 데이터 파이프라인

| 문서 | 작업ID | 분류 | 근거 |
|------|:---:|:---:|------|
| cs_21 tier_a_profile | CS-2-1 | **A 완전** | `tasks/profile_tasks.py`: calculate_growth_stages / calculate_capital_dna / calculate_all_profiles |
| cs_21b sensitivity_profile | CS-2-1b | **A 완전** | `tasks/sensitivity_tasks.py:calculate_sensitivity_profiles` (geo seg + D/E + interest coverage + REGULATION_MAP). 503건 |
| cs_21c insider_signal | CS-2-1c | **B 부분** | `tasks/insider_tasks.py:calculate_insider_signals`(Finnhub insider, BUY/SELL, smart_money). **미구현**: institutional_ownership_pct / short_interest = None 고정(`:162-163`), institutional_change_qoq / top_holder_action / days_to_cover 미계산 |
| cs_22 co_mention | CS-2-2 | **A 완전**(소스대체) | `relation_tasks.py:extract_co_mentions`. 설계 `news.NewsArticle.symbols` → `services.news.models.NewsEntity`로 스키마 적응 |
| cs_23 price_co_movement | CS-2-3 | **D 대체** | `relation_tasks.py:calculate_price_co_movement`. 설계 "같은 섹터 내 전체 쌍" → **Neo4j PEER_OF 쌍**으로 범위 축소(계산량 절감). 90일 corr 동일 |
| cs_24 relation_confidence | CS-2-4 | **A 완전** | `relation_tasks.py:update_relation_confidence` + `check_stale_and_decay`. 5단계 상태·truth_score·evidence_tier_best 모델+task 완전. 3,527건 |
| cs_25 chain_profile_aggregation | CS-2-5 | **A 완전** | `tasks/sync_tasks.py:aggregate_chain_profiles`. 503건. Beat는 `config/celery.py:691~` 8개 등록(DatabaseScheduler 운영) |

### Phase 3 — Neo4j 동기화 + GDS

| 문서 | 작업ID | 분류 | 근거 |
|------|:---:|:---:|------|
| cs_31 profile_neo4j_sync | CS-3-1 | **A 완전** | `sync_tasks.py:sync_profiles_to_neo4j` — neo4j_dirty=True Delta Sync, `SET s += $props` |
| cs_32 relation_neo4j_sync | CS-3-2 | **A 완전** | `sync_tasks.py:sync_relations_to_neo4j` → `services/neo4j_sync.py:sync_dirty_relations`(confirmed/probable upsert, hidden/weak/stale delete). CUSTOMER_OF는 API view 파생(설계 일치) |
| cs_33 gds_algorithms | CS-3-3 | **C 미구현(앱 자동화 기준)** | `gds_tasks.py`/`run_gds_algorithms`/Beat 스케줄 **부재**. pagerank_score/community_id/betweenness는 **수동 Cypher 1회 주입**(`update_v2/task_done/CS-3-3`: Neo4j 5.26.3 다운그레이드 + GDS 2.13.2 설치 후 532노드 실행 완료). path_service는 **읽기만** 함 |

### Phase 4 — API

| 문서 | 작업ID | 분류 | 근거 |
|------|:---:|:---:|------|
| cs_41 graph_api | CS-4-1 | **A 완전**(경로 재배치) | `api/views.py:ChainSightGraphView` + `api/urls.py` `<symbol>/graph/`. market_signals/derived_type(CUSTOMER_OF)/meta.query_ms 구현 |
| cs_42 suggestion_api | CS-4-2 | **A 완전** | `ChainSightSuggestionView` + `<symbol>/suggestions/`. categories(peers/same_industry/co_mentioned/same_sector) + strength |
| cs_43 trace_api | CS-4-3 | **A 완전** | `ChainSightTraceView` + `trace/`. shortestPath + found/path_length/next_relation + 400 처리 |

### Phase 5 — 프론트엔드 (원안)

| 문서 | 작업ID | 분류 | 근거 |
|------|:---:|:---:|------|
| cs_51 graph_visualization | CS-5-1 | **A 리네임 구현** | `GraphView`→`GraphCanvas.tsx`(react-force-graph-2d, ssr:false, spotlight, lazy expansion, depth 1/2/3) |
| cs_52 ai_guide_ui | CS-5-2 | **A 리네임 구현** | `SuggestionCards`→`AIGuidePanel.tsx`(카테고리 카드 + highlightRelTypes 필터). strength dots→텍스트(v2 결정) |
| cs_53 chain_trace_ui | CS-5-3 | **A 리네임 구현** | `TraceView`→`TracePathView.tsx`(노드 체인 + step 한글 라벨) |
| cs_54 stock_detail_integration | CS-5-4 | **A 완전**(독립기록 無) | `GraphMiniView.tsx`(=ChainSightMiniView), `app/stocks/[symbol]/page.tsx` chain-sight 탭. **별도 task_done 없음**(5-1/5-2에 흡수) |
| cs_5_frontend_design_v2 | — | **B 상위설계 채택** | cs_51~54를 대체하는 상위 설계(문서 §0 자체 명시). MVP 필수(§12) 충족, **프로 Advanced(§6) + profile API + 일부 CTA 미구현** |

### redesign_v1_260409 (현행 프론트 트랙)

| PR | 설계 항목 | 분류 | 근거 |
|----|------|:---:|------|
| PR-1 | 스키마 neo4j_dirty/previous_status/save() override | **A** | `models/relation_discovery.py:139~179`, `migrations/0005` |
| PR-2 | 시드 선정 task(5소스, MAX 20, Redis) | **A** | `services/seed_selection.py`, `tasks/seed_tasks.py` |
| PR-3 | neo4j_dirty 동기화 + undirected 정규화 | **A** | `services/neo4j_sync.py`, `tasks/neo4j_dirty_sync_tasks.py` |
| PR-4 | 마켓 뷰 API 4종(seeds/sector/neighbors/signals) | **A** | `api/views.py`(SeedListView/SectorGraphView/NeighborGraphView/SignalFeedView) |
| PR-5 | 탐색 상태 + 섹터바 + 캔버스 + `?focus=` 딥링크 | **A** | `lib/stores/explorationStore.ts`, `components/chainsight/{SectorBar,MarketGraphCanvas}.tsx` |
| PR-6 | 탐색 트레일 + 관계 카드 패널 | **A** | `components/chainsight/{ExplorationTrail,RelationCardPanel}.tsx` |
| PR-7 | 체인 스토리 피드(무한 스크롤) | **A** | `components/chainsight/ChainStoryFeed.tsx` |

> QA 91% 조건부 승인. 단 작업 브랜치 `data_structure_remodeling_V1`로 진행(CLAUDE.md "진행 중: redesign v1"과 일치).

---

## 미구현 항목 상세

### C-1. CS-3-3 GDS 자동 재계산 파이프라인 부재 (가장 큰 갭)
- **현상**: `gds_tasks.py` / `run_gds_algorithms` / Celery Beat 스케줄이 **존재하지 않음**.
- **실태**: PageRank/community_id/betweenness 노드 속성은 `update_v2/task_done/CS-3-3`에서 **Neo4j 5.26.3 다운그레이드 + GDS 2.13.2 설치 후 수동 Cypher로 1회 주입**됨(532노드, 검증 완료). path_service는 이 값을 **읽기만** 함.
- **영향**: 그래프(노드/엣지)가 변경되어도 PageRank/커뮤니티가 자동 갱신되지 않음. 시간 경과 시 stale.
- **권장**: 주간 Beat task로 GDS projection→write 배치 추가 필요(설계 cs_33의 원래 의도).

### C-2. CS-2-1c InsiderSignal 기관/공매도 지표 누락
- `institutional_ownership_pct`, `short_interest_pct`가 항상 `None`(`insider_tasks.py:162-163`, 주석 "별도 API 없음").
- `institutional_change_qoq` / `top_holder_action` / `days_to_cover` 미계산 → `smart_money_signal`이 insider 신호만으로 산출(설계는 기관 데이터 결합 의도).
- 설계의 FMP Institutional Holders 연동 미구현.

### C-3. cs_5_frontend_design_v2 프로 투자자 Advanced 기능 (§6) 미구현
- **노드 메트릭 오버레이**(PER 히트맵/시총 크기/Centrality/커뮤니티 색상 토글) — `GraphCanvas.tsx`는 섹터 색상 단일 모드만.
- **노드 비교 모드**(Ctrl+Click 두 노드 PER/ROE/Growth 비교) — `handleNodeClick`은 단일 선택 토글만.
- **노드 테두리 = InsiderSignal**(strong_buy 초록/sell 빨강) — `paintNode`는 선택/호버/center 테두리만.
- **프로파일 API** `GET /api/v1/chainsight/{symbol}/profile/` — `api/urls.py`에 라우트 없음(graph API 응답 필드로 부분 대체).

### C-4. CTA 미연결 (cs_5_v2 §5)
- NodeDetailPanel `[⭐ Watchlist 추가]` CTA — `NodeDetailPanel.tsx`에 없음(가설생성/Validation/탐색/경로 4개만). Watchlist 기능 자체는 `WatchButton.tsx`+`WatchlistViewSet`로 별도 존재하나 패널 CTA 미연결.
- TracePathView `[이 경로 기반 가설 생성]` CTA 없음.

### C-5. CS-0-0 serverless 레거시 미제거
- `StockRelationship`, `CategoryCache` 및 관련 서비스(supply_chain/institutional/regulatory/theme_matching/keyword_enricher)가 `services/serverless/`에 잔존.
- 설계는 "정리 먼저, 구축 다음"(원칙 4)이나 참조 서비스 존재로 보류 처리됨(설계서도 `# LEGACY_KEEP` 태그로 보류 인정). 백엔드 정리 단계 미완.

### 누락된 독립 완료기록
- **CS-5-4**: 종목 상세 통합(GraphMiniView)이 CS-5-1/5-2에 흡수되어 독립 task_done 없음(기능은 구현됨).
- **CS-4-1/4-2/4-3**: `CS-4-1_2_3_rest_api.md` 통합 기록으로 커버(실질 완료).
- **DC 트랙**: DC-1~6 중 독립 완료기록은 **DC-2(ETF→:Theme 21 + HAS_THEME 534)뿐**. DC-1은 CS-1-3에 흡수, DC-3/DC-4는 계획·흔적만(Finnhub 403 fallback, SEC Pipeline 트랙으로 이관 추정).

---

## 폐기/대체 항목

### D-1. neo4j_dirty 단일 소스 패턴 (설계 전반 변경, 전면 채택)
- 설계 전반의 `synced_to_neo4j`/`neo4j_synced`(동기화 완료 플래그) → **`neo4j_dirty`(default=True, True=동기화 필요)** 단일 소스로 통일.
- `RelationConfidence.save()`가 자동 `neo4j_dirty=True` 세팅(`relation_discovery.py:179`), bulk `update()` 경로는 수동 토글.
- `migrations/0008_unify_neo4j_flags.py`: `RemoveField(relationconfidence.synced_to_neo4j)` + `CompanyChainProfile.neo4j_synced`→`neo4j_dirty` 반전 마이그레이션. (audit P0 #9, common-bug #와 정합)

### D-2. redesign_v1이 폐기시킨 cs_5x 원안 UX
| 폐기 대상 | 근거 |
|------|------|
| 종목 상세 Chain Sight **탭 내 그래프** | `app/stocks/[symbol]/page.tsx` `href=/chainsight?focus={symbol}` 딥링크로 대체. 탭 내장 GraphView/GraphControls 구조 폐기 |
| `/chainsight` = 종목중심 워크스페이스 | **시장 탐색 허브**(breadth-first)로 전환. `/chainsight/[symbol]`은 deep-dive workspace로 강등 |
| `synced_to_neo4j` 동기화 패턴(cs_31/32) | 코드에서 완전 제거(`0008`) |
| `RELATED_TO` 하드코딩 엣지 라벨 | `data_quality_3_fixes.md` Step 2B — 동적 타입 위임으로 폐기 |

> **보존(폐기 아님)**: `GraphCanvas.tsx`/`NodeDetailPanel.tsx` 등 cs_5x 컴포넌트는 deep-dive 전용으로 **코드 유지**. 원안과 redesign이 이중 트랙으로 공존(원안=symbol deep-dive, redesign=market hub).

### D-3. 소스/범위 대체 (기능 동일)
- **cs_22**: 뉴스 소스 `news.NewsArticle.symbols`(JSON 배열) → `NewsEntity`(정규화 테이블).
- **cs_23**: 가격 동조 범위 "같은 섹터 전체 쌍" → "Neo4j PEER_OF 쌍".
- **cs_41~43 경로**: `/api/stocks/{symbol}/chainsight/...` → `/api/v1/chainsight/{symbol}/...`(독립 앱 경로 재배치, v2 §8이 정정 반영). 폐기 아닌 경로 정정.
- **CS-2-5 Beat 위치**: settings.py dict → `config/celery.py` + DatabaseScheduler(PeriodicTask DB가 진실의 소스, common-bug #28).

### D-4. CUSTOMER_OF 저장 폐기 (설계 의도대로)
- v1.3 결정대로 `SUPPLIES_TO`만 canonical 저장, `CUSTOMER_OF`는 API view에서 역방향 파생(`api/views.py`). 설계 일치 = 의도된 대체.

---

## 부록: redesign_v1 대체 관계 최종 판정

- **redesign_v1_260409는 cs_5x(cs_51~54 + cs_5_frontend_design_v2)의 프론트엔드 탐색 패러다임을 대체**한다("종목 중심 ego-graph" → "시장 탐색 허브").
- **단, cs_1x~cs_3x 백엔드 인프라(Neo4j 스키마/peer/co-mention/relation_confidence/sync)는 그대로 재사용**. redesign API 설계서가 "새 엔드포인트 없이 기존 4개 재사용 + 마켓뷰 4개 추가"를 명시.
- 신규 개념(seed node 선정 / neo4j_dirty / market view API / exploration trail / chain story feed) **5개 전부 코드 실재**.
- 의도적 deferral(분류 D 아님): Heat Score(Phase 2 SeedHeatScore), 전환 애니메이션, LLM chain title/summary, 2차 카드 설명, GDS PageRank 갱신.

---

## 후속 권장 (감사 의견, 실행 아님)

| 우선순위 | 항목 | 근거 |
|:---:|------|------|
| ★★★ | GDS 자동 재계산 Beat task 추가 | C-1, 현재 1회 수동 주입만 → 그래프 변경 시 stale |
| ★★ | InsiderSignal 기관/공매도 지표 연동 | C-2, smart_money 신호 정확도 |
| ★★ | serverless 레거시 단계적 제거 | C-5, CS-0-0 미완 부채 |
| ★ | 프로 Advanced FE(메트릭 오버레이/비교) | C-3, MVP 외 차별화 기능 |
| ★ | NodeDetailPanel/Trace CTA 연결 | C-4, 기존 백엔드 기능 활용 |

---
*감사 종료. 본 문서는 읽기 전용 보고서이며 코드 변경을 수반하지 않음.*
