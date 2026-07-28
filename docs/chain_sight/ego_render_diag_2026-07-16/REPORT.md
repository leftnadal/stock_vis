# ⑳-D — ego 그래프 렌더 단절 진단 보고서 (read-only)

- **일시**: 2026-07-16
- **세션 종류**: 조사(read-only) — 코드 diff 0
- **진단 기준 코드**: `origin/main @ aafdd97` (배포 실화면 기준)
- **결론 한 줄**: market-graph 캔버스는 **모든 진입 경로에서 빈 화면**이다. focus/ego 경로는 프론트 2중 게이트(시드 제약 + ego URL 미스매치 404), 섹터/시드 경로는 데이터 소스(Neo4j 동결)로 각각 차단된다. **ego API·데이터는 건강**하며 아무 경로도 그에 도달하지 못한다.

---

## 0. 진단 정합성 정정 (중요)

- 세션 진입 시 worktree 브랜치 `monorepo/sess-eventgroup-window`(fc97683)는 **origin/main(aafdd97)보다 102 커밋 뒤**였다. ⑰/⑲/⑳-1 ego·중심성 작업(`ego_views.py`·`centrality_views.py`·`symbol_centrality.py`·`egoAdapter.ts`·leaderboard)이 전부 origin/main에만 존재.
- 배포 실화면은 origin/main 기준이므로 진단 브랜치를 `git reset --hard origin/main`으로 맞춘 뒤 재진단했다. (stale 브랜치를 읽으면 구 neighbors 배선만 보여 오진 위험 — 실제로 초기 탐색 2건이 그 함정에 빠졌다가 정정.)

---

## 1. 원인 분류표 (경로 × 계층)

| 진입 경로 | API 계층 | 프론트 배선 계층 | 데이터 소스 계층 | 최종 원인 |
|---|---|---|---|---|
| **① 리더보드 focus** (`?focus=SYM`) | ✅ **건강** — `EgoGraphView` PG 네이티브, `/api/v1/chainsight/ego/<sym>/` HTTP 200 (NVDA 48노드/224엣지 405ms 실측) | ❌ **2중 결함** — **Gate A**: `page.tsx:24` 시드 제약(`seedData.seeds.find`)으로 비-시드 심볼 조용히 무시 / **Gate B**: `chainsightService.ts:85` **URL 미스매치** `/chainsight/<sym>/ego/` → **404** | ✅ PG 데이터 존재 | **프론트 배선** |
| **② 섹터 칩** (SectorBar) | ❌ `SectorGraphView`가 Neo4j Cypher 직접 실행 → 연결 실패 → `GraphQueryError` (뷰가 `GraphConnectionError`만 포착해 **미포착 500**) | ✅ 배선 정상 (`selectSector`→`useSectorGraph`→`/sector/<s>/graph/`) | ❌ **Neo4j 다운** (`localhost:7687` 연결 실패, ⑲ 이후 동결) | **데이터 소스**(Neo4j 동결) + 부수: API 견고성 |
| **③ 시드 카드** | (②와 동일) | (②와 동일) | (②와 동일) | **②와 동일** — "시드 카드"=SectorBar의 섹터 요약 칩(예: Healthcare=섹터). 별도 seed→ego 카드는 **존재하지 않음** |

### 근거 (코드 라인·실측)

**① focus/ego 경로**
- 리더보드 링크: `leaderboardConfig.ts:56-57` → `/chainsight/market-graph?focus=${SYMBOL}`.
- Gate A: `frontend/app/chainsight/market-graph/page.tsx:22-30` — `focusSymbol && seedData` 이고 `seedData.seeds.find(s.symbol === focusSymbol)`가 있을 때만 `initializeFocusExploration` 호출. 없으면 setState 없이 조용히 종료 → `centerSymbol` null 유지 → 빈 캔버스.
  - **실측**: 오늘 시드 20개 = `AMZN,BLK,BNY,CBRE,CTAS,CTRA,DELL,ELV,ERIE,GOOGL,GS,IBM,…` — **NVDA/AAPL/MSFT 미포함**. 반면 centrality pagerank top = **NVDA#1, GOOGL#2, MSFT#3, AAPL#4**. → 리더보드 #1 NVDA 클릭 시 Gate A에서 무시(= 메모리의 "NVDA 등 비-시드는 빈 화면" 재현).
- Gate B: `frontend/services/chainsightService.ts:79-96` `fetchEgo` → `authAxios.get('/chainsight/${symbol}/ego/')`. 백엔드 실제 라우트는 `apps/chain_sight/api/urls.py:36` `path("ego/<str:symbol>/")`. **경로 순서 반대.**
  - **실측(URL resolver)**: `/api/v1/chainsight/AAPL/ego/` → **404** / `/api/v1/chainsight/ego/AAPL/` → `EgoGraphView` 해석 OK.
  - 결과: Gate A를 통과한 시드 심볼(예 GOOGL)조차 `useEgo`→`fetchEgo`→404 → `egoData` undefined → `egoToNeighborShape` null → `buildNeighborGraph` 미실행 → 빈 캔버스.
  - ego 호출자는 `fetchEgo`(→`useEgo`→`MarketGraphCanvas.tsx:217`) **단 하나** = 단일 실패점.
- ego API 건강 실측(올바른 경로, `EgoGraphView.as_view()` test client):
  - NVDA: 200, nodes=48, edges=50, total_edges=224, 405ms
  - AAPL: 200, nodes=51, edges=50, total_edges=97, 141ms
  - MSFT: 200, nodes=45, edges=50, total_edges=130, 196ms
  - → **API·PG 데이터 100% 건강. 문제는 전적으로 프론트 배선.**

**② 섹터/③ 시드 카드 경로**
- `SectorBar.tsx` 섹터 칩 onClick → `explorationStore.selectSector` → `MarketGraphCanvas.tsx:214` `useSectorGraph(selectedSector && !centerSymbol)` → `chainsightService.ts` `/chainsight/sector/<s>/graph/`.
- `apps/chain_sight/api/views.py:402` `SectorGraphView`가 `get_graph_repository()`로 Neo4j Cypher 실행.
- **실측**: `SectorGraphView.as_view()` (Technology) → `GraphQueryError: Cypher 실행 실패: Couldn't connect to localhost:7687`. 뷰의 `except GraphConnectionError`(views.py:522)는 이 예외를 **못 잡음** → 클라이언트에 500 전파(503 아님).
- → 섹터/시드 경로는 Neo4j 동결로 빈 캔버스(+ 부수적으로 에러 코드가 500으로 새는 견고성 결함).

---

## 2. 이력 분류 (Q4)

| 결함 | 도입 커밋 | 분류 |
|---|---|---|
| ego URL 미스매치(Gate B) | 프론트 `fetchEgo` 경로 = `a9256b8`(S2, 2026-07-14). 백엔드 라우트 `ego/<sym>/`는 이미 `1323ec7`(S1-b)에 의도적 `ego/` 프리픽스로 존재 | **(a) 미검증** — 프론트 배선 첫 순간부터 경로 불일치, **한 번도 작동한 적 없음**. 회귀 아님. `feedback_ui_slice_live_screenshot` 규약(라이브 렌더 확인 전 완료 금지) 위반 사례 |
| 시드 제약(Gate A) | focus 핸들러 = `f0bd037`(cs-rd3-route) 이후 유지 | **(a) 미검증** — 리더보드(⑳-1)가 비-시드 심볼을 focus로 넘기게 되면서 표면화. focus 핸들러는 시드 화면 전제로 설계됨 |
| 섹터 모드 빈 렌더 | — | **(c) 데이터 조건 변화** — Neo4j 동결(⑲, `D` 결정). 코드 회귀 아님 |

**종합**: ego 렌더 단절은 **회귀가 아니라 미검증 이월**(a)이다. ⑰/⑲/⑳-1이 API green·테스트 green으로 통과했으나 **focus→ego 라이브 화면을 한 번도 검증하지 않아** URL 불일치·시드 게이트가 그대로 배포됐다.

---

## 3. 복구 후보 슬라이스 스코핑 (수정 금지 — 명세만)

> 우선순위: 후보① → ② 를 함께 착수하면 리더보드→ego 동선이 완전 복구된다. 후보④는 ⑳-2 백본 결정과 묶음.

| # | 후보 | 규모 | 의존성 | 명세 |
|---|---|---|---|---|
| **①** | **ego URL 미스매치 수정** | **S** (한 줄) | 없음 · **최우선** | `chainsightService.ts:85` 경로를 `/chainsight/${symbol}/ego/` → **`/chainsight/ego/${symbol}/`** 로 교정. 백엔드 라우트에 정합. 시드 심볼의 ego 즉시 복구. 계약 드리프트 재발 방지 위해 `contracts/` OpenAPI에 ego 경로 명시 권장 |
| **②** | **focus 시드 제약 해제 (PG ego 직행)** | **S~M** | ①과 병행 · 리더보드 비-시드 심볼 언블록 | `page.tsx:24` 시드 `find` 게이트 제거/우회. sector 없이도 `centerSymbol`만 세팅해 ego 모드 진입 가능하게 `initializeFocusExploration` 시그니처 완화(sector optional). ego API `nodes[].sector`로 사후 보강 가능. NVDA 등 centrality 상위(비-시드) focus 복구 |
| **③** | **빈 상태 2분리** | **S** | ①② 후 | 현 `isEmpty = !selectedSector && !centerSymbol`(canvas)는 "이웃 없음"과 "focus 미해석/에러(404·시드밖)"를 구분 못함. ego fetch 에러/빈 이웃을 별도 카피로 노출(무한 스켈레톤·백지 방지) |
| **④** | **섹터 모드 거취** | **M~L** | ⑳-2 백본과 통합 결정 필요 | Neo4j 의존 `SectorGraphView`를 (a) PG 재구현(RelationConfidence + Stock.sector 필터, ego와 동일 소스) 또는 (b) 섹터 모드 숨김/비활성 중 택. ⑳-2 "백본 PG 기반" 방향과 합치 |
| **⑤** | **SectorGraphView 예외 견고성** | **S** | 독립 | `except GraphConnectionError`에 `GraphQueryError` 합류(또는 상위 `GraphError`)해 Neo4j 다운 시 **503**(현 미포착 500) 반환. ④로 섹터를 PG 전환하면 자연 소멸 |

---

## 4. DoD 체크

- [x] Q1~Q4 전부 코드 라인·실측 응답 근거로 답변 (URL resolver·test client·git log)
- [x] 원인 분류표 + 복구 후보 스코핑 완성
- [x] 코드 diff 0 (`git status` clean, 문서만 추가)
- [x] KB 1건 등록 (common-bugs — 아래 §5)
- [x] 보고서 push (규칙 A 문서 머지 대행)

---

## 5. KB 정산

`sub_claude_md/common-bugs.md`에 신규 버그 **#57** 등록 (origin/main이 세션 중 #56=STEP0-P2-AXIS를 선점 → 번호 양보):
- **ego 그래프 렌더 단절 = FE↔BE URL 미스매치(미검증 이월)**: 백엔드 `ego/<symbol>/`(프리픽스 분리) vs 프론트 `<symbol>/ego/`. API green·테스트 green이었으나 라이브 focus→ego 화면 미검증으로 배포. `feedback_ui_slice_live_screenshot` 규약(라이브 렌더 확인 전 완료 아님)의 실증 사례. 교정=프론트 경로 순서 정합 + `contracts/`에 ego 경로 명시.
