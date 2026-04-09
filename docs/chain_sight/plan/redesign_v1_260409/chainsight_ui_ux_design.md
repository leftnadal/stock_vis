# Chain Sight UI/UX 설계서

> **버전**: v2.0  
> **작성일**: 2026-04-09  
> **상태**: 확정  
> **변경 이력**: v1.1 → v2.0 — 그래프+카드 연동형 탐색 허브로 재정의  
> **선행 문서**: chain_sight_seed_node_design.md

---

## 1. 제품 철학

### Chain Sight = 시장 탐색 허브

| 경로                   | 역할                                                                                                      | 탐색 방향     |
| ---------------------- | --------------------------------------------------------------------------------------------------------- | ------------- |
| `/chainsight`          | **Market exploration hub** — 시장 전체에서 관심 종목을 발견하고 관계를 따라 탐색                          | Breadth-first |
| `/chainsight/[symbol]` | **Expert deep-dive workspace** — 특정 종목의 관계 구조를 심층 분석 (validation, trace, advanced analysis) | Depth-first   |

마켓 뷰는 에고 그래프 워크스페이스로 보내는 런처가 아니라, 그 자체로 완결된 탐색 허브다.

### 그래프와 카드의 관계

마켓 뷰는 그래프 단독 탐색 화면이 아니다. 그래프와 카드가 함께 탐색을 이끄는 **guided exploration** 구조다.

- **그래프** = 관계 구조와 맥락을 시각적으로 보여준다
- **관계 카드** = 해석과 다음 행동 선택을 돕는다

둘은 서로 다른 기능의 UI가 아니라 **같은 탐색 상태를 공유하는 두 개의 인터페이스**다. 그래프 노드를 클릭해도, 카드 CTA를 클릭해도, 같은 상태 전이가 일어난다.

### 공유 탐색 상태

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

그래프 노드 클릭이든 카드 CTA 클릭이든, 아래가 동시에 갱신된다:

- centerSymbol → 그래프 중심 이동 + 관계 카드 패널 갱신 + 트레일 확장 + 히스토리 축적

### 장기 확장 방향

현재는 그래프-카드 동등 구조. 장기적으로 카드 중심 + 그래프 토글형으로 확장 가능 (모바일, 카드 전용 뷰 등).

---

## 2. 화면 구조 개요

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
├────────────────────────────────────────────────────┤
│  ④ 관계 카드 패널                                   │
│     현재 중심 노드 기준 로컬 탐색 후보               │
│     관계 타입별 그룹 (Suppliers / Competitors / ...) │
├────────────────────────────────────────────────────┤
│  ⑤ 체인 스토리 피드                                 │
│     현재 관찰 chain 흐름 + 새로운 chain 추천         │
└────────────────────────────────────────────────────┘
```

- ②③④는 같은 탐색 상태를 공유하며 함께 갱신
- ④는 ②의 오른쪽이 아니라 **아래**에 위치 (가로 공간 확보)
- ⑤는 ④와 역할이 다름 — ④ = 로컬 탐색, ⑤ = 글로벌 chain flow + discovery

---

## 3. ① 섹터 버튼 바

| 항목      | 값                                                   |
| --------- | ---------------------------------------------------- |
| 레이아웃  | 가로 스크롤, flex                                    |
| 버튼      | 섹터명 + 증감율, 상승=#A32D2D / 하락=#185FA5         |
| 선택 상태 | info 배경 + info 보더                                |
| 정렬      | Phase 1: seed_count DESC / Phase 2+: heat_total DESC |
| 데이터    | `seeds/` → `sector_summary`                          |

탭 → 그래프 렌더링 + 관계 카드 패널에 대표 카드 동시 표시. 재탭 → 전체 리셋.

---

## 4. ② 그래프 캔버스

### 역할

관계 구조와 맥락의 시각적 요약. 단독이 아니라 아래 관계 카드 패널과 함께 탐색을 이끈다.

### 섹터 진입 첫 화면

**그래프 + 대표 카드 동시 노출.** 그래프 = 구조 파악, 카드 = 첫 탐색 후보 선택.

### 노드 클릭 정책

**마켓 뷰에서 노드 클릭 = 항상 in-place 중심 이동.** `/chainsight/[symbol]` 자동 이동 없음. 심화 분석은 관계 카드의 "Deep dive" CTA에서만.

클릭 시 상태 전이:

1. `GET /{symbol}/neighbors/` 호출
2. 그래프 중심 이동
3. 관계 카드 패널 갱신
4. 탐색 트레일 확장
5. 좌측 히스토리 축적

### 전환 애니메이션

| 동작                  | 애니메이션                          |
| --------------------- | ----------------------------------- |
| 이전 중심 → 왼쪽      | translateX(-) + opacity 0.45, 300ms |
| 새 중심 → 캔버스 중앙 | 300ms ease-out + 크기 확대          |
| 새 이웃 → 페이드 인   | opacity 0→1, 300ms delay 100ms      |
| 시드 노드 → bounce    | 시드이면 bounce 애니메이션          |

### 좌측 히스토리 축적

- 왼쪽 노드 opacity 감소 (가장 오래된 = 가장 흐림)
- 클릭 시 undo — 그래프 + 카드 + 트레일 모두 갱신
- 화면 내 최대 3개, 이전은 트레일에서 확인

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

**Truth 관계** (truth_score 비례 굵기):

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

### 성능 제약

동시 노드 20 / 엣지 40 / bounce 3 / 중심이동 300ms / 초기렌더 500ms

---

## 5. ③ 탐색 트레일

전체 탐색 경로의 가로 슬라이드. 그래프 탐색이든 카드 탐색이든 동일하게 갱신.

| 항목        | 값                                               |
| ----------- | ------------------------------------------------ |
| 높이        | 60px                                             |
| 노드 크기   | 과거 r=12, 현재 r=18                             |
| 엣지 라벨   | 관계 타입 텍스트                                 |
| 자동 스크롤 | 새 노드 추가 시 오른쪽 끝, 300ms                 |
| 노드 간격   | 120px                                            |
| 노드 탭     | 해당 시점으로 undo (그래프 + 카드 + 트레일 모두) |

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

## 6. ④ 관계 카드 패널

### 역할

현재 중심 노드 기준 **로컬 탐색 후보**. 사용자가 다음 탐색 대상을 고르는 인터페이스.

### 위치

그래프 **아래**. 가로 공간 확보를 위해 사이드 패널이 아닌 하단 배치.

### 관계 타입별 그룹

```
[Suppliers]         [Competitors]       [Peers]           [Co-mentioned]
┌──────────┐        ┌──────────┐        ┌──────────┐      ┌──────────┐
│ TSM      │        │ AMD      │        │ INTC     │      │ MRVL     │
│ 공급     │        │ 경쟁     │        │ 피어     │      │ 동시출현 │
│ vol 3.1x │        │ +4.1%    │        │ +0.8%    │      │ ×3 급증  │
│ [탐색]   │        │ [탐색]   │        │ [탐색]   │      │ [탐색]   │
└──────────┘        └──────────┘        └──────────┘      └──────────┘
```

### 카드 구성

| 영역   | 내용                                            |
| ------ | ----------------------------------------------- |
| 상단   | symbol + name                                   |
| 관계   | relation type badge + 관계 설명 한 줄           |
| 시그널 | why now + signal badge                          |
| 메타   | confidence (truth_score ?? market_score)        |
| CTA    | **여기서 탐색** / **가설 생성** / **Deep dive** |

### 그룹 내 정렬

1. is_seed = true 우선
2. `truth_score ?? market_score ?? 0` DESC
3. market_cap DESC

### CTA 동작

| CTA         | 동작                                                       |
| ----------- | ---------------------------------------------------------- |
| 여기서 탐색 | centerSymbol 변경 → 그래프 + 카드 + 트레일 갱신 (in-place) |
| 가설 생성   | `/thesis/new?symbol={symbol}&from=chainsight`              |
| Deep dive   | `/chainsight/{symbol}` (에고 그래프 워크스페이스)          |

### 카드 설명 필드 전략

- **1차**: 프론트 규칙 기반 템플릿 조합 (기존 API 필드 활용)
- **2차**: `neighbors` 응답에 `relation_summary`, `why_now` 필드 추가
- **추후**: LLM 기반 explanation 생성

### 섹터 진입 시 (중심 노드 미선택)

관계 카드 대신 **대표 시드 카드** 표시: 섹터 내 시드 종목 나열 + 사유 + 카드 탭 → 탐색 시작.

### 데이터 소스

`GET /api/v1/chainsight/{symbol}/neighbors/` — 그래프 전환 + 관계 카드 렌더의 핵심 API.

---

## 7. ⑤ 체인 스토리 피드

### ④와의 구분

| 영역          | 역할                                 | 범위                    |
| ------------- | ------------------------------------ | ----------------------- |
| ④ 관계 카드   | 현재 중심 기준 **다음 탐색 후보**    | Local navigation        |
| ⑤ 체인 스토리 | 현재 관찰 chain 흐름 + 새 chain 추천 | Global flow + discovery |

### 구성

- **상단**: 현재 트레일에서 감지된 관계 체인 해석
- **하단**: 오늘 시드 기반 자동 구성 체인 추천 (새로운 발견 기회)

### 데이터

`GET /api/v1/chainsight/signals/`

---

## 8. 종목 상세 연결

- `/stocks/[symbol]` → Chain Sight 탭 제거, 딥링크(`/chainsight?focus={symbol}`) 추가
- `/chainsight?focus={symbol}` → 섹터 자동 선택 + 해당 종목 중심 + 관계 카드 표시
- `/chainsight/[symbol]` → Deep dive workspace. 마켓 뷰 주 흐름과 별개. "Deep dive" CTA에서만 진입.

---

## 9. 프론트엔드 코드 전략

### 신규 생성

| 파일                                          | 역할                |
| --------------------------------------------- | ------------------- |
| `app/chainsight/page.tsx`                     | 마켓 뷰 메인        |
| `components/chainsight/SectorBar.tsx`         | 섹터 버튼 바        |
| `components/chainsight/MarketGraphCanvas.tsx` | 그래프 캔버스       |
| `components/chainsight/ExplorationTrail.tsx`  | 탐색 트레일         |
| `components/chainsight/RelationCardPanel.tsx` | 관계 카드 패널      |
| `components/chainsight/RelationCard.tsx`      | 개별 카드           |
| `components/chainsight/SectorSeedCards.tsx`   | 섹터 진입 대표 카드 |
| `components/chainsight/ChainStoryFeed.tsx`    | 체인 스토리 피드    |
| `hooks/useExplorationState.ts`                | 공유 탐색 상태      |
| `hooks/useSeedData.ts`                        | 시드 API            |

### 재사용

`types/chainsight.ts`, `chainsightService.ts`, `graphStyles.ts`

### 유지 (Deep dive workspace)

`app/chainsight/[symbol]/page.tsx`, `GraphCanvas.tsx`, `NodeDetailPanel.tsx`

### 변경

`app/stocks/[symbol]/page.tsx` (탭 제거 → 딥링크), 메인 내비 (Chain Sight 추가)

---

## 10. 모바일 (Future consideration)

현재 데스크톱 우선. 장기적으로 카드 중심 탐색 UI 가능 (그래프 토글/축소). 현재 카드 중심 구조가 향후 모바일 전환의 기반.
