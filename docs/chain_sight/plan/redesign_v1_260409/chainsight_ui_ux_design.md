# Chain Sight UI/UX 설계서

> **버전**: v2.2 FINAL  
> **작성일**: 2026-04-10  
> **상태**: 확정 — 구현 진입 가능  
> **변경 이력**: v2.1 → v2.2 — 화면 순서 확정, pre-focus/focused 정의 통합, 상태 매트릭스 추가  
> **선행 문서**: chain_sight_seed_node_design.md

---

## 1. 제품 철학

### Chain Sight = 시장 탐색 허브

| 경로                   | 역할                                                                                             | 탐색 방향     |
| ---------------------- | ------------------------------------------------------------------------------------------------ | ------------- |
| `/chainsight`          | **Market exploration hub** — 시장 전체에서 관심 종목을 발견하고 관계를 따라 탐색                 | Breadth-first |
| `/chainsight/[symbol]` | **Deep dive workspace** — 특정 종목의 관계 구조 심층 분석 (validation, trace, advanced analysis) | Depth-first   |

마켓 뷰는 Deep dive workspace로 보내는 런처가 아니라, 그 자체로 완결된 탐색 허브다.

### 그래프와 카드의 관계

그래프와 카드는 서로 다른 기능의 UI가 아니라 **같은 탐색 상태를 공유하는 두 개의 인터페이스**다.

- **그래프** = 관계 구조와 맥락을 시각적으로 보여준다
- **카드** = 해석과 다음 행동 선택을 돕는다

그래프 노드를 클릭해도, 카드 CTA를 클릭해도, 같은 상태 전이가 일어난다. 둘이 따로 움직이는 상황은 없다.

### 장기 확장

현재는 그래프-카드 동등 구조. 장기적으로 card-first + graph toggle 확장 가능.

---

## 2. 용어 정의

| 용어                    | 정의                                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------- |
| **대표 시드 카드**      | 관계 카드 패널의 **pre-focus state** (`centerSymbol == null`). 선택된 섹터의 시드 종목을 나열. |
| **관계 카드**           | 관계 카드 패널의 **focused state** (`centerSymbol != null`). neighbors 기반 로컬 탐색 후보.    |
| **체인 스토리 카드**    | `signals/` 기반 글로벌 chain 카드. 시장 전체 chain 흐름 + 새 chain 추천.                       |
| **Deep dive workspace** | `/chainsight/[symbol]` — 에고 그래프 기반 심층 분석 화면.                                      |

---

## 3. 공유 탐색 상태

```typescript
interface ExplorationState {
	selectedSector: string | null;
	centerSymbol: string | null;
	trail: TrailNode[];
	historyNodes: string[];
	currentNeighbors: Neighbor[];
	selectedRelationGroup: string | null;
	highlightedChain: string | null;
}
```

그래프 노드 클릭이든 관계 카드 "여기서 탐색"이든, 아래가 **동시에** 갱신된다:

1. `centerSymbol` 변경
2. ② 그래프 중심 이동
3. ③ 탐색 트레일 확장
4. ④ 관계 카드 패널 갱신 (pre-focus → focused, 또는 focused → focused)
5. 좌측 히스토리 축적

---

## 4. 화면 구조 — 최종 순서

```
┌────────────────────────────────────────────────────┐
│ [Dashboard] [Chain Sight*] [Screening] [Thesis]    │  ← 메인 내비게이션
├────────────────────────────────────────────────────┤
│  ① 섹터 버튼 바 (가로 스크롤)                      │
│  [Tech +1.8%] [Health +0.6%] [Energy -1.2%] ...    │
├────────────────────────────────────────────────────┤
│  ② 그래프 캔버스                                   │
│     구조와 맥락의 시각적 요약                       │
│     노드 클릭 → in-place 중심 이동                  │
├────────────────────────────────────────────────────┤
│  ③ 탐색 트레일 (가로 스크롤)                        │
│  ○Tech ──peer── ○AAPL ──supply── ●NVDA             │
│  전체 경로 보존 + undo entry point                  │
├────────────────────────────────────────────────────┤
│  ④ 관계 카드 패널                                   │
│     centerSymbol == null → 대표 시드 카드 (pre-focus)│
│     centerSymbol != null → 관계 카드 (focused)      │
├────────────────────────────────────────────────────┤
│  ⑤ 체인 스토리 피드                                 │
│     시장 전체 chain 흐름 + 새 chain 추천 (global)    │
└────────────────────────────────────────────────────┘
```

- ②③은 시각적으로 직접 연결: 그래프에서 탐색하면 바로 아래 트레일이 확장
- ④는 ③ 아래: 현재 중심의 로컬 탐색 후보
- ⑤는 ④와 역할이 다름 — ④ = 로컬, ⑤ = 글로벌

---

## 5. 탐색 상태 매트릭스

| 상태                      | centerSymbol  | ② 그래프                                   | ③ 트레일                 | ④ 관계 카드 패널                                            | 좌측 히스토리 |
| ------------------------- | ------------- | ------------------------------------------ | ------------------------ | ----------------------------------------------------------- | ------------- |
| **페이지 진입**           | null          | 빈 캔버스 + 안내                           | 없음                     | empty state ("섹터를 선택하면 대표 시드 카드가 표시됩니다") | 없음          |
| **섹터 선택**             | null          | overview graph (market cap 상위 + 관계선)  | `○ Tech`                 | **대표 시드 카드** (pre-focus)                              | 없음          |
| **그래프 노드 클릭**      | 클릭한 symbol | 중심 이동 + 이웃                           | `○Tech ── ●NVDA`         | **관계 카드** (focused)                                     | 중앙=NVDA     |
| **카드 "여기서 탐색"**    | 카드 symbol   | 중심 이동 + 이웃                           | 확장                     | **관계 카드** 갱신                                          | 갱신          |
| **`?focus=NVDA` 진입**    | NVDA          | 섹터 자동 선택 + NVDA 중심                 | `○Tech ── ●NVDA`         | **관계 카드** (focused)                                     | 중앙=NVDA     |
| **체인 스토리 카드 클릭** | chain 첫 노드 | 섹터 확인 + 첫 노드 중심 + chain highlight | `○{sector} ── ●{첫노드}` | **관계 카드** (focused)                                     | 중앙=첫 노드  |

모든 상태 전이에서 ②③④ + 좌측 히스토리는 동시에 갱신된다.

---

## 6. ① 섹터 버튼 바

| 항목      | 값                                                       |
| --------- | -------------------------------------------------------- |
| 레이아웃  | 가로 스크롤, flex                                        |
| 버튼      | 섹터명 + 증감율, 상승=#A32D2D / 하락=#185FA5             |
| 선택 상태 | info 배경 + info 보더                                    |
| 정렬      | Phase 1: `seed_count DESC` / Phase 2+: `heat_total DESC` |
| 데이터    | `seeds/` → `sector_summary`                              |

- 탭 → ② overview graph 렌더 + ④ 대표 시드 카드 (pre-focus) 표시
- 재탭 → 전체 리셋

---

## 7. ② 그래프 캔버스

### 역할

관계 구조와 맥락의 시각적 요약. ④ 관계 카드 패널과 함께 탐색을 이끈다.

### 섹터 진입 — Overview graph

섹터 선택 시 `sector/{sector}/graph/` 호출. 이 시점의 그래프는 **탐색 시작점을 고르기 위한 overview**다. 중심 노드 기반 본격 탐색은 `neighbors/` 호출 이후 시작.

### 노드 클릭 정책

**마켓 뷰 노드 클릭 = 항상 in-place 중심 이동.** Deep dive workspace로의 자동 이동 없음. 심화 분석은 ④ 관계 카드의 "Deep dive" CTA에서만.

클릭 시:

1. `GET /{symbol}/neighbors/`
2. 그래프 중심 이동 (이전 노드 → 좌측 히스토리)
3. ③ 트레일 확장
4. ④ 관계 카드 패널 갱신 (pre-focus → focused 또는 focused → focused)

### 전환 애니메이션

| 동작                | 애니메이션                          |
| ------------------- | ----------------------------------- |
| 이전 중심 → 왼쪽    | translateX(-) + opacity 0.45, 300ms |
| 새 중심 → 중앙      | 300ms ease-out + 크기 확대          |
| 새 이웃 → 페이드 인 | opacity 0→1, 300ms delay 100ms      |
| 시드 노드           | bounce (시드만)                     |

### 좌측 히스토리 — 그래프 내부 시각적 맥락

그래프 캔버스 **내부**에서 최근 1~3 step의 노드를 흐려진 상태로 유지. "방금 어디서 왔는지"를 그래프 안에서 보여주는 **시각적 맥락 유지 레이어**.

> **좌측 히스토리 vs ③ 탐색 트레일:**  
> 좌측 히스토리 = 그래프 내부, 최근 1~3 step, 시각적 맥락.  
> 트레일 = 그래프 외부(하단), depth 0부터 전체 경로, canonical navigation log + undo.  
> 밀도가 다른 두 장치이며 중복이 아니다.

- 클릭 시 해당 시점으로 undo (②③④ + 히스토리 모두 복원)
- 화면 내 최대 3개. 그 이전은 ③ 트레일에서 확인.

### 노드 디자인

| 요소          | 사양                                   |
| ------------- | -------------------------------------- |
| 기본          | background-secondary, border-secondary |
| 시드 (가격)   | #FCEBEB + #E24B4A                      |
| 시드 (거래량) | #E1F5EE + #1D9E75                      |
| 시드 (관계)   | #E6F1FB + #378ADD                      |
| 중심          | 해당 색상 + 2.5px 보더                 |
| 히스토리      | tertiary, opacity 0.3~0.5              |

### 엣지 디자인

**Truth 관계** (truth_score 비례):

| 타입          | 색상    | 스타일     | 굵기  |
| ------------- | ------- | ---------- | ----- |
| SUPPLIES_TO   | #5DCAA5 | 실선       | 2~3px |
| COMPETES_WITH | #F0997B | 실선       | 2px   |
| PEER_OF       | #85B7EB | 점선 (4,3) | 1.5px |

**Market 관계** (truth_score=null, 고정 1px):

| 타입             | 색상    | 스타일     |
| ---------------- | ------- | ---------- |
| CO_MENTIONED     | #AFA9EC | 점선 (2,4) |
| PRICE_CORRELATED | #D3D1C7 | 점선 (3,3) |

> 프론트: `truth_score != null ? scale(truth_score) : 1`

### 성능 제약

동시 노드 20 / 엣지 40 / bounce 3 / 중심이동 300ms / 초기렌더 500ms

---

## 8. ③ 탐색 트레일 — Canonical navigation log

### 역할

전체 탐색 경로를 보존하는 **정식 네비게이션 로그**이자 **undo entry point**. 그래프 탐색이든 카드 탐색이든 동일하게 갱신.

### 위치

**그래프 바로 아래.** 그래프에서 탐색하면 시각적으로 바로 아래 트레일이 확장되는 자연스러운 흐름.

### 구조

```
[← 스크롤]  ○Tech ──peer── ○AAPL ──supply── ○NVDA ──supply── ●TSM  [스크롤 →]
             depth 0        depth 1           depth 2          depth 3 (current)
```

### 사양

| 항목        | 값                               |
| ----------- | -------------------------------- |
| 높이        | 60px                             |
| 노드 크기   | 과거 r=12, 현재 r=18             |
| 엣지 라벨   | 관계 타입 텍스트                 |
| 자동 스크롤 | 새 노드 추가 시 오른쪽 끝, 300ms |
| 노드 간격   | 120px                            |

### 인터랙션

| 동작           | 결과                                               |
| -------------- | -------------------------------------------------- |
| 트레일 노드 탭 | 해당 시점으로 undo — ②③④ + 좌측 히스토리 모두 복원 |
| 좌우 스와이프  | 경로 탐색                                          |

```typescript
interface TrailNode {
	symbol: string;
	type: "sector" | "stock";
	depth: number;
	relation_from_prev?: string;
	seed_type?: "price" | "volume" | "relation" | null;
}
```

---

## 9. ④ 관계 카드 패널

### 두 가지 상태

| 조건                   | 상태          | 표시                    |
| ---------------------- | ------------- | ----------------------- |
| `centerSymbol == null` | **Pre-focus** | 대표 시드 카드          |
| `centerSymbol != null` | **Focused**   | 관계 카드 (타입별 그룹) |

대표 시드 카드는 별도 영역이 아니라 **이 패널의 초기 상태**다.

### 위치

③ 트레일 아래, ⑤ 체인 스토리 피드 위.

### Pre-focus: 대표 시드 카드

데이터: `seeds/` 전체를 페이지 진입 시 **global preload** → 섹터 선택 시 프론트에서 `sector` 필터 → 렌더.

카드 구성:

- symbol + name + seed_type badge
- 시드 사유 (seed_reasons 기반 프론트 템플릿)
- daily_return + volume_ratio
- CTA: **여기서 탐색** → `centerSymbol` 설정 → focused state 전환

### Focused: 관계 카드

데이터: `GET /{symbol}/neighbors/`

#### 관계 타입별 그룹

| 그룹             | 포함 display_type                                   |
| ---------------- | --------------------------------------------------- |
| **Supply Chain** | `SUPPLIES_TO`, `CUSTOMER_OF` — 카드 내 badge로 구분 |
| **Competitors**  | `COMPETES_WITH`                                     |
| **Peers**        | `PEER_OF`                                           |
| **Co-mentioned** | `CO_MENTIONED`, `PRICE_CORRELATED`                  |

> `CUSTOMER_OF`는 별도 그룹이 아니라 Supply Chain 그룹의 하위 badge.

```
[Supply Chain]      [Competitors]       [Peers]           [Co-mentioned]
┌──────────┐        ┌──────────┐        ┌──────────┐      ┌──────────┐
│ TSM      │        │ AMD      │        │ INTC     │      │ MRVL     │
│ SUPPLIES │        │ 경쟁     │        │ 피어     │      │ 동시출현 │
│ vol 3.1x │        │ +4.1%    │        │ +0.8%    │      │ ×3 급증  │
│ [탐색]   │        │ [탐색]   │        │ [탐색]   │      │ [탐색]   │
└──────────┘        └──────────┘        └──────────┘      └──────────┘
```

#### 카드 1장

| 영역   | 내용                                            |
| ------ | ----------------------------------------------- |
| 상단   | symbol + name                                   |
| 관계   | display_type badge + 관계 설명 한 줄            |
| 시그널 | why now (seed_reasons 기반) + signal badge      |
| 메타   | confidence (truth_score ?? market_score)        |
| CTA    | **여기서 탐색** / **가설 생성** / **Deep dive** |

#### 정렬

1. `is_seed = true` 우선
2. `truth_score ?? market_score ?? 0` DESC
3. `market_cap` DESC

#### CTA 동작

| CTA         | 동작                                          |
| ----------- | --------------------------------------------- |
| 여기서 탐색 | centerSymbol 변경 → ②③④ + 히스토리 동시 갱신  |
| 가설 생성   | `/thesis/new?symbol={symbol}&from=chainsight` |
| Deep dive   | `/chainsight/{symbol}` → Deep dive workspace  |

### 카드 설명 필드 전략

| 단계     | 전략                                                                                         |
| -------- | -------------------------------------------------------------------------------------------- |
| **1차**  | 프론트 규칙 기반 템플릿. `display_type`, `seed_reasons`, `daily_return`, `volume_ratio` 활용 |
| **2차**  | `neighbors` 응답에 `relation_summary`, `why_now`, `insight_summary` 추가                     |
| **추후** | LLM 기반 explanation                                                                         |

#### 1차 템플릿 규칙

| 라인              | 생성 규칙                                                |
| ----------------- | -------------------------------------------------------- |
| **relation line** | `display_type` 기반 고정 문구                            |
| **why now line**  | `seed_reasons` 우선 + `daily_return`/`volume_ratio` 보조 |
| **confidence**    | `truth_score ?? market_score`                            |
| **signal badge**  | `seed_type`                                              |

**relation line 고정 문구:**

| display_type     | 문구                            |
| ---------------- | ------------------------------- |
| SUPPLIES_TO      | "공급망 상류/하류 연결"         |
| CUSTOMER_OF      | "공급망 상류/하류 연결" (badge) |
| COMPETES_WITH    | "직접 경쟁 관계"                |
| PEER_OF          | "동종 비교 대상"                |
| CO_MENTIONED     | "최근 시장/뉴스에서 동시 해석"  |
| PRICE_CORRELATED | "가격 움직임 유사"              |

---

## 10. ⑤ 체인 스토리 피드 — Global chain flow + discovery

### ④와의 구분

| 영역          | 역할                                     | 범위   | 데이터       |
| ------------- | ---------------------------------------- | ------ | ------------ |
| ④ 관계 카드   | 현재 중심 기준 **다음 탐색 후보**        | Local  | `neighbors/` |
| ⑤ 체인 스토리 | 시장 전체 **chain 흐름 + 새 chain 추천** | Global | `signals/`   |

체인 스토리 피드는 완전히 **글로벌 피드**다. 현재 사용자의 탐색 경로와 무관하게 시장 전체에서 관찰되는 chain을 보여준다.

> "현재 트레일 해석"은 이 버전에서 포함하지 않는다. Future enhancement로 검토 가능.

### 체인 스토리 카드 클릭 시 동작

체인 스토리 카드 클릭은 **새 exploration session 시작**으로 간주한다. 기존 trail과 history는 리셋되고, chain 첫 노드 기준으로 새 trail이 시작된다.

1. chain 첫 노드의 섹터 → ① 섹터 바 자동 선택 (이미 같으면 유지)
2. chain 첫 노드 → `centerSymbol` 설정
3. ② 그래프에 chain path highlight
4. ④ 관계 카드 패널 → 첫 노드 neighbors (focused state)
5. ③ 트레일 → 리셋 후 `○{sector} ── ●{첫노드}`로 새 시작

> chain path 전체를 트레일에 preload하는 것은 future enhancement.

### 데이터

`GET /api/v1/chainsight/signals/`

---

## 11. 종목 상세 연결

- `/stocks/[symbol]` → Chain Sight 탭 제거, 딥링크(`/chainsight?focus={symbol}`) 추가
- `/chainsight?focus={symbol}` → 상태 매트릭스 참조 (섹터 자동 선택 + 중심 + 관계 카드 focused)
- `/chainsight/[symbol]` → Deep dive workspace. "Deep dive" CTA에서만 진입.

---

## 12. 프론트엔드 코드

### 신규

| 파일                                          | 역할                                      |
| --------------------------------------------- | ----------------------------------------- |
| `app/chainsight/page.tsx`                     | 마켓 뷰 메인                              |
| `components/chainsight/SectorBar.tsx`         | 섹터 버튼 바                              |
| `components/chainsight/MarketGraphCanvas.tsx` | 그래프 캔버스                             |
| `components/chainsight/ExplorationTrail.tsx`  | 탐색 트레일                               |
| `components/chainsight/RelationCardPanel.tsx` | 관계 카드 패널 (pre-focus / focused 분기) |
| `components/chainsight/RelationCard.tsx`      | 관계 카드 (focused)                       |
| `components/chainsight/SeedCard.tsx`          | 대표 시드 카드 (pre-focus)                |
| `components/chainsight/ChainStoryFeed.tsx`    | 체인 스토리 피드                          |
| `components/chainsight/ChainStoryCard.tsx`    | 체인 스토리 카드                          |
| `hooks/useExplorationState.ts`                | 공유 탐색 상태                            |
| `hooks/useSeedData.ts`                        | 시드 API                                  |

### 재사용

`types/chainsight.ts`, `chainsightService.ts`, `graphStyles.ts`

### 유지

`app/chainsight/[symbol]/page.tsx`, `GraphCanvas.tsx`, `NodeDetailPanel.tsx` (Deep dive workspace)

### 변경

`app/stocks/[symbol]/page.tsx` (탭 제거 → 딥링크), 메인 내비 추가

---

## 13. 모바일 (Future consideration)

현재 데스크톱 우선. 장기적으로 card-first 탐색 UI 가능. 현재 카드 중심 구조가 향후 모바일 전환의 기반.
