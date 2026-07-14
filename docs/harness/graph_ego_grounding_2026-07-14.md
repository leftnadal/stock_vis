# GRAPH ego 그래프 read-only grounding (지시서⑯)

- **작성**: 2026-07-14
- **성격**: read-only 조사(grounding). 실행 세션 아님. 쓰기 = 본 보고서 + `common-bugs.md` 1건뿐.
- **worktree**: `monorepo/sess-16-graph-grounding` (`/Users/byeongjinjeong/Desktop/sess-16-graph-grounding`), base = origin/main `7605002` (⑬⑭⑮ 머지 후).

---

## 1. STEP 0 실측표

| 항목 | 값 |
|------|-----|
| origin/main HEAD (조사 base) | `7605002` (Merge sess-fmp-testdebt) — ⑬⑭⑮ 포함 |
| ⑬ EVENTGROUP-WINDOW 머지 | ✅ MERGED (HALT-1 발동 → 병진 머지로 해소, `7605002`) |
| ⑭ forward-survey / ⑮ fmp-testdebt | ✅ 둘 다 MERGED |
| baseline red | **chainsight 13** (attention 6 + leadership 7) — 기대와 일치. FMP 34는 ⑮ 픽스처로 해소됨 |
| Neo4j 접속 | **DOWN** (`bolt://localhost:7687` connection refused). pytest도 "Neo4j unavailable - skipping sync" 경고 |
| HALT 발생 | **HALT-1 발동**(⑬ 미머지) → 병진 머지로 해소 후 재개. HALT-2/3/4 **미발동** |

**HALT-1 경위**: STEP 0.2에서 ⑬ 미머지 확인 → 계약대로 중단·보고 → 병진이 ⑬⑭⑮를 `--no-ff` 머지(origin/main `7605002`, 충돌 0, 사전 merge-tree 검증) → HALT 해소 후 정합 base에서 재개.

---

## 2. 슬라이스별 산출물

### SLICE 1 — 그래프 데이터 모델 + 진실 소스 판정

**두 개의 서로 다른 그래프 표현이 공존한다** (혼동 주의):

```
┌─────────────────────────── PostgreSQL (진실 소스) ───────────────────────────┐
│                                                                              │
│  [A] 코어-위성 클러스터 (뉴스 co-mention jaccard, ⑬ 윈도우 적용)             │
│      EventGroup ──1:N── GroupMembership ──FK── stocks.Stock                   │
│      · 38 그룹 / as_of 2026-07-12 / window_days=21 / 288 멤버십               │
│      · member_count 3·7·13(min·med·max), core_count 3·4·6                     │
│                                                                              │
│  [B] 쌍(pairwise) 관계 그래프 = "해자"                                        │
│      RelationConfidence  (현재상태, unique(symbol_a,symbol_b,relation_type))  │
│        · 13,697행 · truth 9,635 / market 4,062                                │
│      RelationPairSnapshot (시계열 궤적, forward-only, period 축)              │
│        · 114,744행 · 9,562 canonical 쌍 × 12 period(07-01~07-13, 균일 12점)   │
│      CoMentionEdge 15,276 · PriceCoMovement 8,859 (원천 신호)                 │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
              RelationConfidence.save() → neo4j_dirty=True (단방향 동기화 플래그)
              neo4j_sync.py / neo4j_loader.py 가 confirmed 엣지를 push
                                     ▼
┌─────────────────────────── Neo4j (파생·동기화 대상) ─────────────────────────┐
│  :Stock 노드 + RELATED_TO 엣지(r.relation_type 속성). **현재 DOWN**.          │
│  neo4j_dirty=True 미동기 270행 적체.                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**진실 소스 판정 = PostgreSQL (확정).** 근거: ⑴ RelationConfidence/RelationPairSnapshot이 PostgreSQL 원본이고 Neo4j는 `neo4j_dirty` 플래그로 push되는 **단방향 파생**(코드: `apps/chain_sight/models/relation_discovery.py:162-168`, `apps/chain_sight/services/neo4j_sync.py`·`neo4j_loader.py`) ⑵ Neo4j가 DOWN인데도 관계 데이터·궤적은 PostgreSQL에 온전 ⑶ 궤적(RelationPairSnapshot)은 **Neo4j에 없다**(PG 전용).

**HALT-3 판정: 미발동.** 지시서의 "시계열 궤적" 가정은 `RelationPairSnapshot`(forward-only period 적립)로 충족. RelationConfidence는 현재상태(궤적 아님)지만, 궤적은 별도 모델에 존재하므로 구조 불일치 아님.

**파일 경로**: 모델 `apps/chain_sight/models/{relation_discovery,relation_pair_snapshot,event_group}.py` / 동기화 `apps/chain_sight/services/{neo4j_sync,neo4j_loader}.py`, `apps/chain_sight/graph/repository.py`(Neo4jGraphRepository).

### SLICE 2 — RelationConfidence 실측 (해자)

| 지표 | 값 |
|------|-----|
| 저장 | Django 모델 `chainsight_relation_confidence` (PostgreSQL), 현재상태 1행/(a,b,type) |
| 궤적 | 별도 `chainsight_relation_pair_snapshot`, period(주간 배치일) 축 forward-only |
| 규모 | RC 13,697행 / RPS 114,744행 / 9,562 canonical 쌍 |
| 궤적 깊이 | **12 period 균일**(min=med=max=12), 범위 2026-07-01~07-13 → 적립 시작 07-01, ~2주치 |
| truth_score 분포 | min 0 / mean 44.62 / max **85** (0~100 스케일이나 상한 ~85, **정규화 안 됨**) |
| status 분포 | probable 8,071 / confirmed 2,326 / hidden 1,946 / weak 1,354 |
| type 분포 | PEER_OF 9,365 / PRICE_CORRELATED 3,784 / CO_MENTIONED 278 / COMPETES_WITH 114 / SUPPLIES_TO 61 / **PARTNER_WITH 54** / **DEPENDS_ON 41** |
| 기록 시점 | first_observed 2026-04-02 ~ last_observed 2026-07-13 (약 3.5개월 활성) |
| 갱신 트리거 | 주간/일간 배치(RPS period 12개/13일) + 상향학습 루프(T-3b). neo4j_dirty 미동기 270 |

**CS-CHOICES drift 재확인**(TASKQUEUE:500): `PARTNER_WITH`(54)·`DEPENDS_ON`(41)이 DB에 있으나 `RELATION_TYPE_CHOICES` **미정의**. 역으로 `HAS_THEME`·`HELD_BY_SAME_FUND`는 choices에 있으나 **0행**. ego 필터 UI가 choices 기반이면 PARTNER_WITH/DEPENDS_ON 엣지가 필터에서 누락될 위험 → ⑰ 착수 시 choices 정합 선행 권장.

**ego 서빙 가능성 판정: 가능.** "ego 뷰에서 엣지 신뢰도·트렌드를 그린다" = `RelationConfidence`(엣지별 truth/market_score·status·evidence bool 7) + `RelationPairSnapshot`(쌍별 12점 궤적 = relevance_opp/risk trend) 조합으로 **PostgreSQL 단독 성립**. Neo4j 불요.

### SLICE 3 — ego 1-hop 조회 가용성 + 데이터 계약 초안

**PostgreSQL 1-hop 실측** (RelationConfidence, `Q(symbol_a=X)|Q(symbol_b=X)`):

| 티커 | 1-hop 엣지 | distinct 이웃 | confirmed 이웃 | RPS 궤적 보유 쌍 |
|------|-----------|--------------|---------------|-----------------|
| AAPL | 96 | 71 | 4 | 71 (1:1) |
| NVDA | 223 | 110 | 26 | 110 (1:1) |
| MSFT | 129 | 75 | 11 | 75 (1:1) |

→ 회사 하나로 1-hop 이웃망 + 엣지별 신뢰도/타입/status + 이웃 전부의 궤적을 **지금 스키마로 즉시** 꺼낼 수 있다. 인덱스: `symbol_a`·`symbol_b` db_index, `relation_status`·`relation_type`·`neo4j_dirty` Index (모델 Meta) + RPS `(canonical_a,canonical_b,-period)` 최신단면 인덱스. 상위 N 정렬(신뢰도/트렌드)은 truth_score·relevance_opp 인덱스로 가능. **추가 인덱스 불요**(SHOW INDEXES 대체 = 모델 Meta 실측).

**기존 관계 서빙 endpoint 전수** (`apps/chain_sight/api/urls.py`):

| 경로 | 뷰 | 백엔드 | 현 상태 |
|------|-----|--------|---------|
| `<symbol>/graph/?depth=` | ChainSightGraphView | **Neo4j** (`get_graph_repository().get_neighbors`) + PG 엣지 보강 | Neo4j DOWN → **404/에러** |
| `<symbol>/neighbors/?rel_types=&min_truth_score=` | NeighborGraphView | **Neo4j** (`repo.run_query` Cypher) | Neo4j DOWN → **비작동** |
| `sector/<sector>/graph/` | ChainSightSectorGraphView | Neo4j | 비작동 |
| `events/` · `events/<theme>/stocks/` | EventBoard/RankingView | PostgreSQL (EventGroup/theme_tags 플래그) | 작동 |

**★핵심 갭**: ego 서빙 endpoint 3종이 전부 **Neo4j 백엔드**인데 진실 소스·궤적은 PostgreSQL. Neo4j가 DOWN이면 ego 뷰 전체가 죽는다. RelationConfidence는 온전한데 화면이 안 나오는 구조.

**ego API 데이터 계약 초안** (⑰용):
```
GET /api/v1/chainsight/<symbol>/ego/?hop=1&min_status=probable&rel_types=PEER_OF,SUPPLIES_TO&limit=30
요청: symbol · hop(1 기본, 최대 2) · 필터(min_status|min_truth_score, rel_types) · limit
응답:
  center: {symbol, name, sector, ...}
  nodes: [{symbol, name, sector, ...}]
  edges: [{
     a, b, relation_type, relation_category, status,
     truth_score, market_score, direction,
     evidence: {tier_best, sources bool 7, basis_summary},
     trajectory: [{period, relevance_opp, relevance_risk, truth_max}]  # RPS 최근 K점
  }]
  meta: {hop, node_count, edge_count, source: "postgresql"}
```
**현 스키마와의 갭**: ⑴ 서빙 백엔드가 Neo4j → PostgreSQL RC/RPS 네이티브 조회로 재구현(또는 Neo4j 기동+동기화) 필요 ⑵ RELATION_TYPE_CHOICES ↔ DB drift(PARTNER_WITH/DEPENDS_ON) 정합 ⑶ trajectory 필드는 RPS에서 canonical (a,b) 정렬키로 join 필요(RC는 (a,b) 순서 무보장 → normalize_pair 적용).

### SLICE 4 — ChainSight 프론트 실측 (요약)

- **의존성**: `react-force-graph-2d ^1.29.1` (frontend/package.json:27).
- **컴포넌트**: `GraphCanvas.tsx`(Deep Dive, force-directed) · `MarketGraphCanvas.tsx`(**방사형 Neighbor=ego 모드 이미 구현**, radialLayout.ts) · `GraphMiniView.tsx`(정적 미니).
- **fetch 경로**: `useGraphData→/chainsight/{s}/graph/` · **`useNeighbors→/chainsight/{s}/neighbors/?rel_types=&min_truth_score=`**(ego용, TanStack Query, staleTime 5분) · sector/graph · seeds · signals. 서비스 `chainsightService.ts`(authAxios).
- **상태/타입**: `types/chainsight.ts`(ForceNode/ForceLink) · Zustand `explorationStore.ts`(centerSymbol·trail·enabledRelTypes 필터 칩).
- **ego 프로토타입 존재**: `/chainsight/market-graph?focus=SYMBOL` → `initializeFocusExploration()` → `MarketGraphCanvas.buildNeighborGraph()` + `computeRadialPositions()`(center 고정 fx/fy, Ring1 160px/Ring2 280px, 관계타입별 각도).
- **vitest**: `GraphCanvas.test.tsx` 5건 + NodeDetailPanel/EventBoard/EventRanking/RelationCardPanel 테스트 파일 존재. MarketGraphCanvas 테스트 **없음**.

**ego 뷰 자리 판단**: **신설 아님 — 기존 `MarketGraphCanvas` 방사형 Neighbor 모드 확장**이 유력(방사형 배치·필터 칩·상태 연동 이미 존재). 남은 건 백엔드 데이터 소스(Neo4j→PostgreSQL) + 궤적/신뢰도 표시 보강. GraphCanvas는 force-directed라 부분 재사용, GraphMiniView는 재사용 불가.

### SLICE 5 — chainsight 13 red 분해 (CS-EG6)

**근본원인 = 플래그 미고정**: `.env:88 CHAINSIGHT_GROUP_SOURCE=event_group`(go-live)이 `settings_test`에 상속(settings_test 미지정, `config/settings.py:567` os.getenv 기본 theme_tags를 .env가 덮음) → EventBoard/RankingView가 **EventGroup 소비**. 그러나 테스트는 `CompanyChainProfile.theme_tags`(구 경로)로 시드 → EventGroup 미시드라 빈 보드/404. **입증(read-only)**: `CHAINSIGHT_GROUP_SOURCE=theme_tags` 강제 시 `test_attention::TestEventBoardAPI` **5 passed**(← event_group에선 실패).

| # | 테스트 | 실패 assert | 원인(theme_tags 시드 ↔ event_group 소비) | 분류 |
|---|--------|-------------|------------------------------------------|------|
| 1-3 | attention `test_event_board_has_theme`·`_includes_small_groups`·`_includes_single_member_group` | `'SEMICON'/'TINYGROUP'/'SOLOGROUP' in []/{}` | EventGroup 미시드라 빈 보드 | **test-only** |
| 4-6 | attention `test_ranking_sorted_by_score_desc`·`_includes_is_low_liquidity`·(+1) | `404==200` (events/SORTED·LIQCHECK/stocks) | EventRankingView가 theme의 EventGroup 못 찾아 404 | **test-only** |
| 7 | leadership `test_ranking...`(404) | `404==200` | 동일 | **test-only** |
| 8-9 | leadership `test_m*_fields...` | `KeyError 'stocks'` | 404 응답엔 stocks 키 없음(404 → 파생) | **test-only** |
| 10-13 | leadership `TestWindowParam` 4건 | `KeyError 'window'` | 404 응답엔 window 키 없음(응답 자체엔 window/stocks 존재, line 169/171) | **test-only** |

**test-only vs prod-code 이분 분류: 13건 전부 test-only.** 보드 코드는 `use_event_group_board()` 플래그로 정확히 분기(event_views.py). 프로덕션은 event_group 경로로 정상 서빙. 실패는 순전히 **테스트가 플래그를 고정하지 않고 .env를 상속 + 구 경로로 시드**한 격리 결함(⑮ FMP 더미키와 **동형**).

**ego 종속 관계**: **독립(병행 가능).** 13 red는 EventBoard/Ranking(테마 보드)이지 ego 그래프(RelationConfidence/Neo4j)가 아니다. ego 구현의 선행 조건 아님. 단 같은 "chainsight 테스트 위생" 범주.

**청소 순서 제안(⑰)**: 택1 — (a) **빠름**: 13 테스트에 `@override_settings(CHAINSIGHT_GROUP_SOURCE='theme_tags')` 부여(레거시 경로 검증, 즉시 green) / (b) **CS-EG6 정렬**: 테스트를 EventGroup 시드 + event_group 계약으로 재작성(라이브 경로 검증). CS-EG6(theme_tags 디프리케이션)이 파괴적이라 "한참 뒤"이므로, ego 착수와 무관하게 **(a)로 즉시 green 확보 후 CS-EG6 세션에서 (b) 승계** 권장.

### SLICE 6 — KB 기재

`sub_claude_md/common-bugs.md`에 `## [테스트 함정] FMP autouse 더미키 픽스처 …` 1건 등록(⑮ 함정 + SLICE 5의 CHAINSIGHT_GROUP_SOURCE 동형 사례를 동일 엔트리 내 일반화). 유일한 code-tree 쓰기.

---

## 3. ⑰ 구현 분할 제안

전제: 진실 소스=PostgreSQL, ego 데이터 완비, 프론트 ego 프로토타입(MarketGraphCanvas 방사형) 존재, 서빙 endpoint는 Neo4j 의존(현재 DOWN).

**핵심 결정 선행(⑰ STEP 0)**: ego 서빙을 (A) **Neo4j 기동+동기화 복구** vs (B) **PostgreSQL 네이티브 재구현** 중 택1. 권장 = **(B)** — Neo4j가 운영에서 불안정(DOWN·270 dirty 적체)하고, 궤적(RPS)은 Neo4j에 없어 어차피 PostgreSQL 조회 필요. (B)면 Neo4j 의존 제거 = 단일 소스.

- **⑰-S1 (백엔드 ego API, PostgreSQL 네이티브)**: `<symbol>/ego/` 신설 또는 `NeighborGraphView`를 RelationConfidence/RelationPairSnapshot 조회로 재구현. 계약 = SLICE 3 초안. RELATION_TYPE_CHOICES↔DB drift(CS-CHOICES) 정합 선행. 단위 테스트(1-hop·필터·정렬·궤적 join). **CS-EG6 흡수 위치 아님**(관계 그래프 ≠ 테마 보드).
- **⑰-S2 (프론트 ego 배선)**: `MarketGraphCanvas` Neighbor 모드를 ⑰-S1 API로 연결 + 엣지 신뢰도/궤적 시각화(색·굵기·스파크). 신설 최소, 기존 방사형 재사용. vitest 보강.
- **⑰-S3 (chainsight 13 청소 = CS-EG6 흡수 위치)**: SLICE 5 (a) `override_settings`로 즉시 green(ego와 병행/독립). CS-EG6 정식 세션에서 (b) EventGroup 재작성 승계. **⑰-S1/S2와 순서 무관**(독립 트랙).

권장 순서: ⑰-S1 → ⑰-S2, ⑰-S3은 아무 때나 병행. Neo4j 결정(A/B)이 S1 규모를 좌우하므로 ⑰ STEP 0에서 먼저 못박을 것.

---

## 4. HALT 발생 내역

- **HALT-1: 발동** (STEP 0.2, ⑬ 미머지) → 병진이 ⑬⑭⑮ 머지(`7605002`)로 해소 → 정합 base 재개.
- **HALT-2 (shared→chain_sight 역참조): 미발동** (`packages/shared`에서 chain_sight import 0 실측).
- **HALT-3 (스키마 구조 불일치): 미발동** (RelationPairSnapshot이 시계열 궤적 충족).
- **HALT-4 (read-only 불가): 미발동** (전 측정 read-only ORM/grep/Cypher-접속시도만).

---

## 5. git status 증빙 (KB 문서 외 clean)

변경 = `sub_claude_md/common-bugs.md`(SLICE 6) + `docs/harness/graph_ego_grounding_2026-07-14.md`(본 보고서) 2개뿐. 코드·테스트·마이그레이션·설정 변경 0. 외부 API 호출 0. Neo4j 쓰기 0(접속 자체 불가). 신규 브랜치는 세션 worktree(`sess-16-graph-grounding`)뿐 — 머지/삭제 0.
