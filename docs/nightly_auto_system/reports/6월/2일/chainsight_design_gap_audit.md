# Chain Sight 설계 갭 감사

> **작성일**: 2026-06-02
> **범위**: 읽기 전용 감사. 코드 수정 없음.
> **대상**: `docs/chain_sight/plan/` 설계 문서 ↔ `apps/chain_sight/` 백엔드 + `frontend/components/chainsight/` 프론트엔드 구현
> **교차 참조**: `docs/chain_sight/task_done/*.md`

---

## 0. 감사 전제 — 코드 위치 변경 (메타 갭)

> ⚠️ **지시서의 `chainsight/` 경로는 더 이상 존재하지 않는다.**

| 지시서/CLAUDE.md 표기 | 실제 위치 (2026-05-31 디렉토리 리모델링 이후) |
|---|---|
| `chainsight/` (루트 앱) | **`apps/chain_sight/`** |
| (테스트) | `tests/chainsight/` (그대로 유지) |
| (프론트) | `frontend/components/chainsight/` + `frontend/app/chainsight/` (그대로 유지) |

- 루트의 `chainsight/`는 **삭제됨**. 백엔드 앱은 `apps/chain_sight/`로 이동(`apps.py` 확인).
- CLAUDE.md의 앱 테이블(`chainsight` → `/api/v1/chainsight/*`)은 **경로 표기가 stale**. 실제 API base는 `/api/v1/chainsight/`로 동일하게 노출되지만(라우트 prefix는 유지), 소스 디렉토리는 `apps/chain_sight/`.
- 본 감사는 실제 코드(`apps/chain_sight/`)를 기준으로 한다.

---

## 1. 요약 (구현률)

### 1.1 설계 세대 계보 (핵심 결론)

Chain Sight 설계는 **3세대**로 진화했으며, 최신 세대가 이전 세대를 대체한다.

```
[1세대] cs_01~cs_54 (2026-03~04 초기, roadmap_v1.3 체계)
   │      백엔드 파이프라인(cs_0~3) + API(cs_41~43) + 프론트(cs_51~54)
   ▼
[2세대] cs_5_frontend_design_v2 (2026-04-04, 프론트만 재설계)
   │      탭 → 전용 워크스페이스 /chainsight/[symbol] 3-panel
   ▼
[3세대] redesign_v1_260409/ (2026-04-10, 확정·구현 대상) ★ 현재 진실의 소스
          마켓 뷰 /chainsight 신규 + Deep dive workspace 통합
          → task_done/chain_sight_redesign_V1/ (PR-1~7 실제 구현 기록)
```

- **백엔드 파이프라인(cs_0~cs_3계열)**: 1세대 설계가 그대로 유효하며 대부분 구현됨.
- **API(cs_41~43)**: 3세대 `redesign_v1_260409/chainsight_api_design.md`가 **상위 집합으로 흡수·확장**. cs_41~43 자체는 그대로 구현되어 있고, 여기에 마켓 뷰 4종 API가 추가됨.
- **프론트엔드(cs_51~54)**: 2·3세대로 **폐기·대체**. v1 컴포넌트명은 거의 사라지고 재편성됨.

### 1.2 구현률 집계

| 영역 | 완전(A) | 부분(B) | 미구현(C) | 폐기·대체(D) | 영역 구현률 |
|---|---|---|---|---|---|
| 백엔드 인프라 (cs_0x) | 3 | 0 | 0 | 0 | **100%** |
| 백엔드 그래프 로드 (cs_1x) | 3 | 0 | 0 | 0 | **100%** |
| 백엔드 프로파일/관계 (cs_2x) | 4 | 2 | 0 | 0 | **~85%** |
| 백엔드 Neo4j sync/GDS (cs_3x) | 1 | 1 | 1 | 0 | **~55%** |
| API (cs_41~43) | 3 | 0 | 0 | 0 | **100%** |
| API (redesign 마켓 뷰 4종) | 4 | 0 | 0 | 0 | **100%** |
| 프론트 (cs_51~54 v1) | 1 | 2 | 0 | 1 | 재편성 (아래 참조) |
| 프론트 (redesign 마켓뷰 5종) | 5 | 0 | 0 | 0 | **100%** |
| 프론트 (v2 workspace 고급) | — | 1 | — | — | **~75%** |

**종합 평가**:
- **3세대(redesign_v1) 기준 = 핵심 기능 90~95% 구현 완료, 프로덕션 배포 가능.**
- **미완 영역은 "Phase 2/고급 분석"으로 일관**: ① Neo4j GDS 배치(PageRank/Louvain/Betweenness) ② Heat Score 계산 ③ LLM 기반 카드 설명 ④ Tier별 자동 신뢰도 판정/상태 전이.

---

## 2. 문서별 상태 테이블

### 2.1 백엔드 — 인프라/로드 (cs_0x, cs_1x)

| 문서 | 제목 | 분류 | 핵심 근거 |
|---|---|---|---|
| cs_01 | Migrations 검증 | **A** | `migrations/0001~0008`, RelationConfidence v2.1 24필드 |
| cs_02 | Neo4j 연결 레이어 | **A** | `graph/repository.py:35-193` GraphRepository + PID lazy init, `get_graph_repository()` |
| cs_03 | Neo4j 온톨로지 스키마 | **A** | `graph/schema.py` CONSTRAINTS 4 + INDEXES 2, `management/commands/init_neo4j_schema.py` (--verify/--check/--reset) |
| cs_11 | Stock 노드 벌크 로드 | **A** | `services/neo4j_loader.py:32-66`, `load_stocks_to_neo4j.py`, 100개 배치 |
| cs_12 | Sector/Industry + BELONGS_TO | **A** | `neo4j_loader.py:72-120`, `load_sectors_to_neo4j.py` |
| cs_13 | Peer 관계 로드 | **A** | `neo4j_loader.py:122+`, `load_peers_to_neo4j.py`, Finnhub 1.2s 딜레이 + FMP 보조, `normalize_pair()` |

### 2.2 백엔드 — 프로파일/관계 (cs_2x)

| 문서 | 제목 | 분류 | 핵심 근거 / 미구현 항목 |
|---|---|---|---|
| cs_21 | Tier A 프로파일 (GrowthStage+CapitalDNA) | **A** | `models/growth_stage.py`, `models/capital_dna.py`, `tasks/profile_tasks.py:42-283` (6단계 stage 분류) |
| cs_21b | SensitivityProfile | **B** | 모델(`models/sensitivity.py` 18필드)+task(`tasks/sensitivity_tasks.py`) 존재. **미확인**: `calculate_all_profiles()` 통합 여부, debt/interest 계산 정밀도, REGULATION_MAP 커버리지 |
| cs_21c | InsiderSignal | **A** | `models/insider_signal.py`, `tasks/insider_tasks.py:1-183`, Finnhub Insider Tx + smart_money_signal 종합 |
| cs_22 | CoMentionEdge 추출 | **A** | `models/news_event.py`(ChainNewsEvent), `models/relation_discovery.py`(CoMentionEdge), `tasks/relation_tasks.py:18+` |
| cs_23 | PriceCoMovement | **A** | `models/relation_discovery.py`(PriceCoMovement), `relation_tasks.py:100+`, 90일 rolling corr, 섹터 필터 |
| cs_24 | RelationConfidence 종합 판정 | **B** | 모델 v2.1 완비(`relation_discovery.py:64-184`). **미구현**: Tier별 confirmed 규칙 자동 판정, `relation_basis_summary` 템플릿 생성, stale decay 자동 전이 |
| cs_25 | CompanyChainProfile 집약 + Beat | **A** | `models/chain_profile.py`(30+필드), `tasks/sync_tasks.py:15+`(aggregate), Beat 스케줄 `config/celery.py`에 16개 `chainsight-*` 항목 등록 확인 |

### 2.3 백엔드 — Neo4j sync / GDS (cs_3x)

| 문서 | 제목 | 분류 | 핵심 근거 / 미구현 항목 |
|---|---|---|---|
| cs_31 | ChainProfile → Neo4j 속성 동기화 | **B** | `tasks/sync_tasks.py`에 sync_profiles_to_neo4j 스켈레톤 + neo4j_dirty 플래그. **미확인/미완**: `_profile_to_neo4j_props()` 완전성, delta sync 배치 로직 |
| cs_32 | RelationConfidence → Neo4j 엣지 동기화 | **A** | `services/neo4j_sync.py:22-98` sync_dirty_relations 완비 (confirmed/probable upsert, stale/hidden/weak delete, UNDIRECTED 정규화) |
| cs_33 | GDS 알고리즘 배치 | **C** | **GDS 실행 배치 없음**: `management/commands/`·`tasks/`에 PageRank/Louvain/Betweenness 계산·저장 코드 부재. ⚠️ 단, **소비측은 구현됨** — `services/path_service.py:186-202`가 Neo4j 노드의 `pagerank_score`/`betweenness_score`를 읽고 graceful fallback(`pagerank_valid` 분기)으로 동작. 즉 **생산자(GDS 배치) 누락, 소비자만 존재** |
| relation_confidence_design_v1 | 관계 신뢰도 설계 v1 (37KB) | **B** | 모델 필드 차원은 거의 반영(status 머신, truth/market score, evidence 추적, canonical_direction). **미구현**: Tier별 confirmed 규칙표 코드화, 시간 경과 하향 전이(probable→weak→hidden), previous_status 전이 트리거 |

### 2.4 API (cs_41~43 + redesign 마켓 뷰)

| 문서/엔드포인트 | 분류 | 핵심 근거 (apps/chain_sight/api/) |
|---|---|---|
| cs_41 `GET /{symbol}/graph/` | **A** | `views.py:59-113` ChainSightGraphView, depth 1~3, CUSTOMER_OF 역방향 파생, market_signals 보강 |
| cs_42 `GET /{symbol}/suggestions/` | **A** | `views.py:116-216` ChainSightSuggestionView, 5~6 카테고리(peers/supply/industry/co_mention/sector) |
| cs_43 `GET /trace/?from=&to=` | **A** | `views.py:222-292` ChainSightTraceView, shortestPath(max 5), found/path_length |
| redesign `GET /seeds/` | **A** | `views.py:367-372` SeedListView, 3단 폴백(Redis→DB SeedSnapshot→async), `tasks/seed_tasks.py:27-90` |
| redesign `GET /sector/{sector}/graph/` | **A** | `views.py:378-526` SectorGraphView, node_size percentile, 1h 캐시 |
| redesign `GET /{symbol}/neighbors/` | **A** | `views.py:532-732` NeighborGraphView, 양방향 쿼리, CUSTOMER_OF 파생, cross_edges, 30m 캐시 |
| redesign `GET /signals/` | **A** | `views.py:735-934` SignalFeedView, shortestPath chain, confidence=mean·0.7+min·0.3, 1h 캐시 |
| (보조) `watchlist/` | **A** | `views/watchlist_views.py` WatchlistViewSet (경로 저장), `serializers/path_watchlist.py` |

> **redesign이 cs_41~43을 대체하는가?** → **대체가 아닌 "흡수·확장"**. cs_41~43(Deep dive workspace 3종)은 그대로 구현되어 살아있고, redesign이 마켓 뷰 4종을 추가해 **총 7개 엔드포인트**가 모두 프로덕션 노출 중.

### 2.5 프론트엔드 (cs_51~54 v1 → v2 → redesign)

| 문서 | 제목 | 분류 | 대응 컴포넌트 / 비고 |
|---|---|---|---|
| cs_51 | 그래프 시각화 | **B** | `GraphView`(v1) → **`GraphCanvas.tsx`로 폐기·개명**. Spotlight·섹터색·depth전환 완료. lazy expansion → depth API 호출 방식으로 진화 |
| cs_52 | AI 가이드 탐색 UI | **B** | `SuggestionCards`(v1) → `AIGuidePanel.tsx`(workspace) + `RelationCardPanel.tsx`(마켓뷰)로 **분산 재편성** |
| cs_53 | Chain Trace 시각화 | **A** | `TraceView`(v1) → `TracePathView.tsx` + `AIGuidePanel` 입력부. from/to·경로표시·경로없음 안내 완료 |
| cs_54 | 종목 상세 연계 | **A** | `GraphMiniView.tsx` (`/stocks/[symbol]`에 동적 import), "전체 보기" → `/chainsight?focus={symbol}` 딥링크 |
| cs_5_frontend_design_v2 | 프론트 v2 (3-panel) | **B** | 3-panel workspace 완료. **미구현**: Centrality/Louvain 오버레이, PER 히트맵, 노드 비교(Ctrl+Click) — 모두 GDS/데이터 의존 |
| redesign chainsight_ui_ux_design | 마켓 뷰 (5 컴포넌트) | **A** | `SectorBar`/`MarketGraphCanvas`/`ExplorationTrail`/`RelationCardPanel`/`ChainStoryFeed` 전부 구현 + `lib/stores/explorationStore.ts` + `hooks/useMarketView.ts` (검증 완료) |

**구현된 라우트** (검증 완료):
```
frontend/app/chainsight/page.tsx              ← 마켓 뷰 (breadth-first)
frontend/app/chainsight/[symbol]/page.tsx     ← workspace (depth-first, 3-panel)
frontend/app/chainsight/watchlist/page.tsx    ← Path Watchlist 목록
frontend/app/chainsight/watchlist/[id]/page.tsx ← Path 상세
```

**Dead(미사용) 컴포넌트** — 파일은 존재하나 실제 렌더 경로 없음:
| 파일 | 상태 |
|---|---|
| `NodeContextMenu.tsx` | import만, 호출 안 됨 |
| `NodeTooltip.tsx` | import만, 렌더 안 됨 |
| `PathCard.tsx` / `FullPathView.tsx` | Path Watchlist 상세용 (기능 미완) |
| `WatchButton.tsx` | NodeDetailPanel이 링크로 대체, 미사용 |

---

## 3. 미구현 항목 상세

### 3.1 (C) 완전 미구현

#### ① cs_33 — Neo4j GDS 알고리즘 배치 ★ 가장 명확한 갭
- **설계**: PageRank, Louvain(커뮤니티), Betweenness Centrality를 주기적으로 계산해 노드 속성으로 저장.
- **현황**: 계산·저장하는 management command / Celery task **부재**.
- **중요 nuance**: 소비측(`services/path_service.py:147-202`)은 이미 `s.pagerank_score`, `s.betweenness_score`를 읽도록 작성되어 있고, 값이 없으면 `pagerank_valid=False` 분기로 bridge/sector 가중치만 사용하는 **graceful fallback**으로 동작. 즉 현재는 **항상 fallback 경로로 동작 중**(GDS 점수가 채워진 적이 없으므로).
- **영향**: 프론트 v2의 Centrality/Louvain 오버레이(cs_5_frontend_design_v2)가 데이터 부재로 미구현 상태에 묶임.
- **원인**: Neo4j GDS 플러그인 별도 설치 필요, AuraDB Free 미지원, MVP 우선순위 낮음.

### 3.2 (B) 부분 구현 — 미완 항목

#### ② cs_24 / relation_confidence_design_v1 — Tier 자동 판정 & 상태 전이
- 모델 필드(truth_score, evidence_tier_best, relation_status 5단계, previous_status)는 **완비**.
- **미구현**:
  - Tier별 confirmed 규칙표 자동 적용 (PEER_OF: Tier1×2 필수, SUPPLIES_TO: manual_seed+provenance 등)
  - 시간 경과 하향 전이 (probable → weak → hidden) 자동 로직
  - `relation_basis_summary` 설명 템플릿 자동 생성
  - 상태 전이 트리거(previous_status 갱신 시점) 명확화

#### ③ cs_31 — ChainProfile → Neo4j 속성 동기화
- sync_profiles_to_neo4j 스켈레톤 + neo4j_dirty 플래그 존재.
- **미완**: `_profile_to_neo4j_props()` 헬퍼 완전성, delta sync 배치 처리 검증 필요.

#### ④ cs_21b — SensitivityProfile
- 모델 + task 구현됨.
- **미확인**: `calculate_all_profiles()` 통합 여부, BalanceSheet 기반 debt/interest 계산 정밀도, REGULATION_MAP 전체 커버리지.

#### ⑤ Heat Score (redesign seed_node_design Phase 2)
- `tasks/seed_tasks.py:95+`에 **가중치 정의만** 존재. 실제 계산 로직·SeedHeatScore 영속화 미구현.
- Beat 스케줄 `chainsight-heat-score-daily`는 placeholder 상태.

#### ⑥ 프론트 v2 고급 분석 (cs_5_frontend_design_v2)
- Centrality/Louvain 오버레이 (GDS 의존 → ① 때문에 차단)
- PER 히트맵 오버레이 (데이터 API 부재)
- 노드 비교 모드 (Ctrl+Click) UI 미구현
- 전환 애니메이션(300ms ease-out) 미구현

#### ⑦ LLM 기반 카드 설명 (redesign chainsight_api_design §4.2 "2차 필드 확장")
- `relation_summary`, `why_now`, `insight_summary` 필드 — Phase 2 예약, 현재 API는 기본 필드만 반환.

#### ⑧ Phase 3: Event Propagation (redesign seed_node_design §4, D-1~D-3)
- text_conditional_prob, lagged_correlation, propagation_weight — 설계만 존재, 미구현.

### 3.3 모델만 있고 task 미구현 (설계서 외 또는 Tier B 예약)
| 모델 | 파일 | 상태 |
|---|---|---|
| `CompanyEventReaction` | `models/event_reaction.py` | 모델만, 계산 task 없음 (Tier B 예약) |
| `CompanyRevenueStructure` | `models/revenue_structure.py` | 모델만 (SEC 10-K + LLM 보조 예정) |
| `CompanyNarrativeTag` | `models/narrative_tag.py` | 모델만, 계산 task 없음 |

---

## 4. 폐기/대체 항목

### 4.1 프론트엔드 세대 교체 (D)
| 구(舊) — v1 설계 | 신(新) — v2/redesign 구현 | 사유 |
|---|---|---|
| `GraphView.tsx` (cs_51) | `GraphCanvas.tsx` | 명명 통일, 기능 동일 |
| `SuggestionCards` (cs_52) | `AIGuidePanel` + `RelationCardPanel` | 마켓뷰/workspace 분리로 분산 재편성 |
| `TraceView` (cs_53) | `TracePathView` + `AIGuidePanel` 입력부 | 입력 UI를 좌측 패널로 통합 |
| 종목 상세 탭 내 그래프 (cs_51~54 전제) | 전용 워크스페이스 `/chainsight/[symbol]` + 마켓뷰 딥링크 | "탭 공간 제약" 해결 (v2 설계 동기) |
| 모바일-우선 터치 인터랙션 (cs_51) | 데스크톱-우선 + `MobileCardList` 폴백 | 모바일 정책 변경 |

### 4.2 백엔드 설계 방향 전환 (D / 운영 결정)
| 구(舊) | 신(新) | 사유 |
|---|---|---|
| CUSTOMER_OF를 DB/Neo4j 엣지로 저장 | View-only 파생(SUPPLIES_TO 역방향) | cs_41 §36-46, 저장 중복 제거 |
| 1차 legacy 시드 선정 | Phase 1→2→3 진화형 seed_selection | redesign seed_node_design |

### 4.3 설계 문서 자체의 대체 관계
- `cs_51~54` (1세대 프론트) → `cs_5_frontend_design_v2` → `redesign_v1_260409/chainsight_ui_ux_design.md` 가 **유효 설계**. cs_51~54는 역사적 참고 자료로 강등.
- `cs_41~43`는 폐기가 아니라 `redesign_v1_260409/chainsight_api_design.md`에 **흡수**되어 여전히 유효(Deep dive 3종 API).

---

## 5. 설계서에 없으나 코드에만 존재 (역갭)

| 항목 | 위치 | 비고 |
|---|---|---|
| `SeedSnapshot` 모델 | `models/seed_snapshot.py` | 시드 선정 결과 DB 영속화 (3단 폴백의 2단). 버그#27(pytest Redis flush) 대응 |
| `SavedPath` / `PathAction` | `models/saved_path.py` | 사용자 탐색 경로 저장 + 액션 추적 |
| `ChainNewsEvent` | `models/news_event.py` | Chain Sight 전용 뉴스 이벤트 저장소 |
| seed/alternatives/expand/recheck 서비스 | `services/*.py` | 시드 선정·대안·확장·재검사 비즈니스 로직 (로드맵 미명시) |
| `tasks/neo4j_dirty_sync_tasks.py` | tasks/ | neo4j_dirty 플래그 기반 더티 동기화 (cs_31/32 통합 운영) |

---

## 6. 권고 (감사 결과 기반, 실행 아님)

1. **CLAUDE.md 경로 갱신**: `chainsight/` → `apps/chain_sight/` 표기 수정 필요 (메타 갭 §0). 멀티에이전트 담당 테이블의 경로도 stale.
2. **cs_33 GDS 우선순위 판단**: 소비 코드(path_service)가 이미 fallback으로 묶여 있어, GDS 배치 1건만 추가하면 path scoring 품질 + 프론트 오버레이 2종이 동시 해금됨 — ROI 높은 단일 갭.
3. **cs_24 자동 판정 로직**: 모델은 준비됐으나 "수동/암묵 판정" 상태. relation_confidence_design_v1의 Tier 규칙표 코드화가 데이터 신뢰도의 핵심 미싱 링크.
4. **Dead 컴포넌트 5종** (NodeContextMenu/NodeTooltip/WatchButton/PathCard/FullPathView): Path Watchlist 기능 완성 여부에 따라 활성화 또는 정리 결정 필요.
5. **설계 문서 정리**: 1세대 `cs_51~54`에 "redesign_v1로 대체됨" 헤더 추가 권고 (혼선 방지).

---

*본 감사는 읽기 전용으로 수행되었으며 어떤 코드/설계 파일도 수정하지 않았다. 라인 번호는 감사 시점(2026-06-02) `apps/chain_sight/` 기준이다.*
