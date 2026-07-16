# 지시서 ⑱ 조사 보고 — Neo4j 잔존 3화면 전수 + 그래프 형상·GDS 시나리오 드라이런

**세션**: read-only 조사 (실행 아님) · **날짜**: 2026-07-15
**worktree**: `monorepo/sess-18-survey` (origin/main `6013865`에서 분기)
**Neo4j**: 미기동(DOWN 유지) · **외부 API**: 0 · **프로드 코드 변경**: 0
**부속**: `scripts/extract_graph.py`(PG 추출) · `scripts/analyze_graph.py`(networkx 드라이런) · `scripts/analysis_report.json`(원자료)

> 판정 방침: SLICE A는 **재료만**(살릴지 여부 = 병진 가치판단). SLICE B는 **데이터 근거 판정표** 제공.

---

## 1. STEP 0 — 경량 ground truth

| 항목 | 실측 | 비고 |
|---|---|---|
| origin/main HEAD | `6013865` | 지시서 기준 `8e08378` + 3 커밋(ancestor 확인) |
| 조사 worktree | `monorepo/sess-18-survey` | origin/main 신규 분기, `.env` 심링크 |
| pytest 전체 | **3866 passed · 53 skipped · 0 failed** (275.77s) | pristine origin/main baseline, green |
| RC (RelationConfidence) | **13,697 행** | 일간 beat 축적 정상, 급감 없음 |
| RPS (RelationPairSnapshot) | **124,306 행** (13 기간, 07-01~07-14) | 정상 범위 |
| 보조 | CoMentionEdge 15,798 · PriceCoMovement 8,859 | |

**HALT-1 미해당** — main red 없음(3866p·0f), RC/RPS 급감 없음.

> ⚠️ 조사 중 발견(참고): pytest.ini `filterwarnings`가 Django 5.2에서 제거된 `RemovedInDjango50Warning`을 참조 → **평소엔 addopts의 `-p no:warnings`가 파싱 자체를 막아 무해**하나, `-o addopts=""`로 override하면 config 파싱 단계에서 죽는다. 잠복 지뢰이나 현행 실행 경로엔 무영향(프로드 변경 범위 밖이라 미수정).

---

## 2. SLICE A — Neo4j 잔존 3화면 카드 (판정 없이 재료만)

> **핵심 맥락**: ⑰ 세션(S1-b/S2, `1323ec7`·`a9256b8`, 2026-07-14)에서 **ego API가 PostgreSQL 네이티브로 신설**되고 `MarketGraphCanvas`의 **Neighbor 모드가 ego로 전환**됨. 그 결과 3화면의 Neo4j 의존도가 서로 다르다.
> ego 뷰 데이터 계약: `GET /api/v1/chainsight/ego/{symbol}/` → **PG**(RelationConfidence + RelationPairSnapshot 궤적), 응답 `EgoGraphResponse`(center/nodes/edges+trend/meta), 1-hop, react-force-graph 시각화. 파일 `apps/chain_sight/api/ego_views.py:42-162`.

### A1 — RelationCardPanel (`frontend/components/chainsight/RelationCardPanel.tsx:1-295`)

- 이 화면은 **중심 종목의 이웃 관계를 유형별 카드 그룹(Supply Chain / Competitors / Peers / Co-mentioned / Related)으로 보여주는 화면**입니다. `/chainsight/market-graph` 페이지 내 "⑤ 관계 카드 패널"로 렌더, 섹터/centerSymbol 선택 시 활성 → **도달 가능**.
- **호출 체인**: `useNeighbors(centerSymbol)` → `GET /chainsight/{symbol}/neighbors/` → `NeighborGraphView`(`views.py:532-730`) → **Neo4j Cypher**(`MATCH (center:Stock)-[r]-(neighbor) WHERE r.status IN [confirmed,probable] ...` + cross_edges 쿼리). 응답 `NeighborResponse`.
- **ego와 겹치는 것**: 1-hop 이웃 목록·relation_type·truth_score — ego(`EgoGraphResponse`)가 **동일 데이터를 PG로 이미 제공**.
- **이 화면만의 것**: `cross_edges`(이웃끼리의 관계), 시드 카드(seed_type/seed_reasons), 관계 유형별 그룹핑 카드 UI.
- **살리는 비용**: **소~중** — 이웃/truth_score는 ego API 파라미터 수준 재사용(소). `cross_edges`만 PG에 신규 집계(RelationConfidence 2-syms 필터)가 필요(중). A3 Neighbor가 이미 ego 어댑터로 같은 전환을 완료 → 선례 존재.
- **방치 기간**: 마지막 실질 변경 `2026-07-14 a9256b8`(형제 커밋에서 무변경 유지). 즉 **ego 전환 물결에서 빠진 잔여** — 코드 자체는 최신이나 Neo4j 경로만 남음.

### A2 — Deep Dive (`frontend/app/chainsight/[symbol]/page.tsx:1-370`)

- 이 화면은 **한 종목에서 depth 1~3까지 다중 홉 관계 그래프를 탐색하는 화면**입니다. RelationCardPanel "Deep" 버튼·ExplorationTrail·직접 URL(`/chainsight/AAPL`)로 진입 → **도달 가능**.
- **호출 체인**: `useGraphData(symbol, depth)` → `GET /chainsight/{symbol}/graph/?depth=N` → `ChainSightGraphView`(`views.py:59-113`) → **Neo4j** `repo.get_neighbors(symbol, depth=depth)`(N-hop) + PG 보강(CoMentionEdge/PriceCoMovement market_signals). 응답 `GraphResponse`. 부가로 `useSuggestions`·`useTrace`(경로 탐색).
- **ego와 겹치는 것**: depth=1 층은 ego(1-hop)와 동일.
- **이 화면만의 것**: **depth≥2 다중 홉 탐색**(ego는 1-hop 전용). trace(두 종목 간 경로), AI 가이드 카테고리 제안.
- **살리는 비용**: **대** — depth≥2는 관계형 DB에 다중 홉 경로 인덱스가 없어 PG로 옮기려면 재귀 CTE 또는 반복 1-hop 확장(신규 집계 로직). depth=1만이면 ego 재사용(소)이나 화면 본질(deep 탐색)이 소멸.
- **방치 기간**: 마지막 실질 변경 `2026-07-14 a9256b8`(무변경 유지). 3화면 중 **Neo4j 의존이 본질적**인 유일한 화면.

### A3 — 섹터 그래프 (`frontend/components/chainsight/MarketGraphCanvas.tsx:111-871`, `page.tsx` `/chainsight/market-graph`)

- 이 화면은 **섹터 선택 시 그 섹터 종목들의 관계 그래프를, 종목 선택 시 그 종목의 ego 그래프를 보여주는 화면**입니다(2모드). SectorBar 칩 클릭으로 진입 → **도달 가능**.
- **호출 체인 (2모드 상이)**:
  - **Neighbor 모드**: `useEgo(centerSymbol)` → `GET /chainsight/{symbol}/ego/` → **PG**(RelationConfidence+RelationPairSnapshot). ⑰ S2에서 전환 완료(`egoAdapter.ts`가 기존 형식 호환).
  - **Sector 모드**: `useSectorGraph(sector)` → `GET /chainsight/sector/{sector}/graph/` → `SectorGraphView`(`views.py:378-478`) → **Neo4j**(`MATCH (s:Stock) WHERE s.sector=$sector ... LIMIT` + 엣지 쿼리).
- **ego와 겹치는 것**: Neighbor 모드 = **ego 뷰 그 자체**(동일 PG 원천·호출 스택).
- **이 화면만의 것**: **Sector 모드**(섹터 단위 종목 집합 + 그들 사이 관계) — ego(단일 중심)와 다른 뷰. market_cap 기반 노드 크기, force-directed 레이아웃.
- **살리는 비용**: **중** — Sector 모드는 "섹터 소속 종목 top-N(Stock.sector, PG에 존재) + 그들 사이 RelationConfidence 엣지" 조합으로 PG 대체 가능하나 신규 serializer/뷰 필요. Neighbor 모드는 이미 PG(비용 0).
- **방치 기간**: Neighbor 모드 `2026-07-14 a9256b8`(최신 전환) / Sector 모드 백엔드는 Neo4j 잔존(무변경).

**A 요약표**

| | 원천 | 깊이 | ego 중복 | 살리는 비용 | 방치 |
|---|---|---|---|---|---|
| A1 RelationCardPanel | Neo4j | 1-hop | 이웃목록 중복(cross_edges만 고유) | 소~중 | 07-14(잔여) |
| A2 Deep Dive | Neo4j | N-hop(1~3) | depth1만 중복 | **대**(N-hop이 본질) | 07-14 |
| A3 Sector 모드 | Neo4j | 섹터집합 | 낮음(다른 뷰) | 중 | Neo4j 잔존 |
| A3 Neighbor 모드 | **PG(ego)** | 1-hop | =ego 자체 | 0(완료) | 07-14(전환) |

---

## 3. SLICE B — 그래프 형상 실측 + GDS 드라이런

> 그래프 = **RelationConfidence 전량**(13,697행) → 무방향 collapse(쌍당 1엣지, weight=max(truth,market)). 노드 555 · collapse 엣지 9,551.

### B1. 그래프 형상

| 지표 | 값 |
|---|---|
| 노드 / collapse 엣지 | 555 / 9,551 |
| 밀도 | 0.0621 |
| 차수 분포 (min/median/p90/max) | 1 / 31 / 57 / 110 |
| 상위 차수 | NVDA 110, GOOGL 76, MSFT 75, GPN 74, ADP 73, CPRT 72, AAPL 71, CAT 70 |
| **연결 성분** | **1개 (자이언트 = 555, 100%)** |

**엣지 타입별 서브그래프** (raw 행 / 노드 / 성분 / 자이언트):

| relation_type | raw | 노드 | 성분 | 자이언트 | 방향성 |
|---|---|---|---|---|---|
| PEER_OF | 9,365 | 544 | 2 | **523** | both(무방향) |
| PRICE_CORRELATED | 3,784 | 500 | 10 | 403 | both |
| CO_MENTIONED | 278 | 117 | 1 | 117 | both |
| COMPETES_WITH | 113 | 128 | 23 | 45 | both |
| SUPPLIES_TO | 58 | 77 | 23 | 17 | **a→b(방향)** |
| PARTNER_WITH | 49 | 65 | 18 | 17 | **a→b** |
| DEPENDS_ON | 37 | 55 | 19 | 8 | **a→b** |

**방향성 재고**: 방향 의미를 가진 타입은 **SUPPLIES_TO·PARTNER_WITH·DEPENDS_ON 3종뿐**, 합 **144 엣지(전체 13,697의 1.05%)**. 나머지(PEER_OF/PRICE_CORRELATED/CO_MENTIONED/COMPETES_WITH)는 전부 `both`. 즉 **방향성 엣지는 희소하고, 각각 18~23개 성분으로 파편화**(자이언트 8~17).

**타입별 truth_score 분포** (median/mean):
- PEER_OF 60/62.9 · COMPETES_WITH 85/84.1 · SUPPLIES_TO 85/79.8 · DEPENDS_ON 85/79.6 · PARTNER_WITH 85/75.8
- **PRICE_CORRELATED·CO_MENTIONED = truth_score 0**(market 카테고리) → truth 가중 연산에서 자동 배제.

**★ 결정적 사실 (co-movement 검산)**: **PRICE_CORRELATED 단독 페어 = 0**. 3,784 PRICE_CORRELATED 페어 **전부**가 PEER_OF 페어와 겹침 → **co-movement 제거 시 구조 엣지 손실 0**(9,551 → 9,551 불변, 모듈러리티 0.841 불변). 주가 동조는 **구조적 연결을 하나도 추가하지 않는** 잉여 신호층. CO_MENTIONED 단독 페어 = 61 · 구조전용(공급망/경쟁, peer/price/comention 없음) 페어 = 124.

### B2. 드라이런 4종 (networkx, Neo4j 미기동)

**① 커뮤니티 (S-A) — Louvain**
- 자이언트(555) modularity **0.841**, **11 커뮤니티**(크기 124/76/73/60/57/37/33/31/25/21/18).
- **(a) 섹터 순도 = 0.99** — 11 커뮤니티가 11개 GICS 섹터와 거의 1:1(Technology 0.95, Industrials/Healthcare/Real Estate/Energy/… 1.0). → **커뮤니티 검출은 섹터를 재발견**할 뿐.
- **(b) EventGroup(45그룹) 겹침** — avg max_containment 0.868, avg spread **1.82 커뮤니티**. 대부분 1~2개 섹터 커뮤니티 안에 들지만 일부는 흩어짐(rockwell/eaton spread 4, comfort/hvac/xylem spread 3, oil/chevron spread 3). → **바텀업(EventGroup)이 톱다운(섹터 커뮤니티)과 다른 것을 보는 증거는 부분적으로 존재**(cross-sector 내러티브 그룹).
- **PriceCoMovement 제외 버전 = 전체와 완전 동일**(위 검산대로 잉여) → co-mention 중심 내러티브 커뮤니티가 **따로 서지 않음**(CO_MENTIONED 단독 61쌍뿐).

**② 중심성 (S-C)**
- **truth 가중 PageRank 상위**: NVDA·GOOGL·MSFT·AAPL·HPE·META·CSCO·MSI (**섹터 내 대형 허브**, Technology 편중).
- **Betweenness 상위**: NVDA·TSLA·GOOGL·GEV·CDNS·WMT·CTVA·CAT·CEG·LLY·FSLR·INTC (**섹터 간 브리지**).
- 두 목록 괴리 실재: hub_only 16종(META/MSFT/JPM/GS/AMD…) vs bridge_only 16종(TSLA/CAT/CEG/CTVA/FSLR/WMT/LLY/GEV…). → **허브(섹터 내 연결자) ≠ 브리지(섹터 간 중개자)**, 섹터 라벨이 주지 않는 신호.

**③ 경로 (S-B)**
- 자이언트 평균 최단 경로 **3.06**, 근사 지름 **7**.
- 이종 섹터 대표 경로: Tech→Energy `EA→GOOGL→ORCL→CVX` · Fin→Health `HOOD→MS→NVDA→LLY→ZTS` · ConsCyc→Util `HAS→TSLA→NVDA→GEV`. → **경로는 존재하나 메가 허브(NVDA/GOOGL) 경유가 지배적** — 인과적 공급망이 아닌 일반적 소세계 홉.

**④ 링크 예측 (S-D) — 라이트**
- Jaccard 상위 20 = 저차수 무명 반도체(SHAZ↔PMEC/HIMX/ACLS/STM/LSCC…) **1.0**(이웃 극소·전부 공유 = 잡음, 섹터 unknown).
- Adamic-Adar 상위 = 금융 클러스터(RJF/PFG/PRU/WFC/SCHW) — **동섹터 재제안**(저신규성).

### B3. 궤적 깊이 판정 (S-D 시간분할 성립 조건)

- **RPS 궤적**: 13 스냅샷 / 14일(07-01~07-14), 사실상 **일간**(gap 대부분 1일, 주말 1회 2일). → 기존 쌍의 truth_max/market_max **드리프트**를 추적, **신규 엣지 형성은 추적 안 함**.
- **엣지 형성 이력**(RC.first_observed): 20개 birth 날짜. 4월 대량 생성(04-03 3527·04-12 7173·04-19 2051) 후 **주간 배치**(05-17·05-24·05-31·06-07·06-14·06-21 ~주 1파). **06-21 이후 사실상 정체**(07-02 신규 2건).
- **시간분할 검증(과거→예측→미래→확인)**: 독립적 형성 파동이 다수 필요. 현재 **주간 ~7~8파**(4월 대량 + 주간 배치)이나 최근 정체 → 검증 신호 빈약.
- **도달 예상**: 견고한 깊이(예 26+ 주간 형성 파동)까지 = discovery 배치 재가동 + **~3~4개월**. RPS 일간 궤적은 ~1개월이면 30점이나, 정적 쌍의 드리프트는 **형성 이벤트가 아니라** 시간분할 링크예측을 직접 지지 못함.

### 시나리오 판정표

| 시나리오 | 판정 | 근거 |
|---|---|---|
| **S-A 커뮤니티** | **기각(재발견)** — 단 EventGroup 각도만 조건부 | Louvain 11커뮤니티 = 11 GICS 섹터, 순도 0.99. 이미 가진 `Stock.sector` 재생산. **조건부 잔가치** = EventGroup(바텀업)이 spread>1로 섹터 경계를 넘는 내러티브를 일부 포착(avg spread 1.82). |
| **S-B 전파 경로/방향** | **기각** | 방향성 엣지 144개(1.05%)·각 18~23성분 파편화. 자이언트 연결은 무방향 peer/price가 접착. 경로는 메가허브 경유라 인과 전파 해석 불가. |
| **S-C 중심성** | **성립** | 허브(PageRank) vs 브리지(betweenness) 목록 실질 괴리(각 16종 고유). 섹터 라벨 밖 신호. 단 truth 가중은 PRICE_CORRELATED(truth=0) 무시 — 가중 정의 선택 필요. |
| **S-D 링크 예측** | **기각(현 규모)** | 정적 예측 = 동섹터 재제안·저차수 잡음(저신규성). 시간분할 검증 = 궤적 깊이 부족(일간 13점·형성 주간 8파·최근 정체). |

### ★ Neo4j 필요성 명시 확인

**드라이런 4종 전체 + EventGroup 45겹침 분석이 555노드·9,551엣지 그래프에서 총 3.92초**(경로 0.59s · 링크예측 1.79s)에 **networkx in-memory로 완주, Neo4j DOWN**. 555 노드는 그래프 알고리즘엔 소규모(networkx는 1만+ 노드도 수 초). **결론: 현 규모에서 위 어느 시나리오도 Neo4j를 요구하지 않는다** — 사실로 확인됨. (Neo4j의 가치는 규모/실시간 쿼리 서빙에 있으나, 배치 분석·현 555노드에선 PG+networkx로 충분.)

---

## 4. SLICE C — KB 정산 3건 (유일한 쓰기)

`sub_claude_md/common-bugs.md`에 기록:

1. **GROUP_SOURCE 동형 노트 갱신** — "⑰ 청소 대상" → **해소됨(⑰ S3 `8377ba5`)**: chainsight 13 red를 event_group 시드로 재작성. ⑱ STEP 0 pristine 3866p·0f로 재확인 back-annotation.
2. **[검증 함정] 서브에이전트 cross-worktree 거짓 green (신규)** — 서브에이전트의 tsc/pytest 통과 주장은 인계 후 호출자 worktree에서 직접 재실행으로만 신뢰. 검증 신뢰 경계 = worktree. (⑰ S2 실증.)
3. **[배포 절차] daphne/celery 런타임 트리 서빙 (신규)** — main 머지만으로 화면 미반영. 배포 = 머지 → `sv sync` → daphne/celery 재시작 순서 필수. (⑰-M 실증.)

---

## 5. HALT 내역 · git 증빙

- **HALT 미발동** (HALT-1/2/3 전부 해당 없음). main green·역참조 신규 없음·드라이런 read-only 유지.
- 쓰기 = KB 1파일(common-bugs.md) + 보고서·부속(docs/chain_sight/neo4j_survey_2026-07-15/). 그 외 프로드 코드·테스트·설정·celery.py 무변경. Neo4j 기동 0 · 외부 API 0.

## DoD 대조

- [x] STEP 0: HEAD `6013865` · pytest 3866p·0f · RC 13697/RPS 124306 정상
- [x] A: 3화면 카드(도달성·기능·중복·쿼리 대응·전환비용 3등급·방치)
- [x] B1: 형상(성분 1·타입별 서브그래프·방향성 144엣지·타입별 스코어)
- [x] B2: 드라이런 4종 + 겹침 2종 + co-movement 제외 비교(= 잉여 확증)
- [x] B3: 궤적 깊이 판정 + 도달 예상(~3~4개월)
- [x] 시나리오 판정표(S-A 기각·S-B 기각·S-C 성립·S-D 기각) + Neo4j 불요 확인(3.92s)
- [x] C: KB 3건
- [x] Neo4j 기동 0 · 외부 API 0 · 프로드 코드 변경 0
