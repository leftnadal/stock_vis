# 모바일 UX 감사 보고서

> **범위**: `frontend/` 전체 (page.tsx 30개, components/*.tsx 205개)
> **기준**: 모바일 뷰포트 375px (iPhone SE/12 mini), Apple HIG 44×44pt 터치 타겟
> **방식**: 정적 코드 분석 (읽기 전용, 코드 수정 없음)
> **작성일**: 2026-06-04

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 핵심 내용 |
|--------|------|----------|
| **BLOCKER** | **3** | Coach E1~E6 `grid-cols-12` 폼 가로 overflow, `<main>` 하단 패딩 누락(MobileNav 가림), IndicatorRow 단일 행 다요소 overflow |
| **MAJOR** | **6** | market-pulse-v2 카드 `grid-cols-3/2` 미대응, stock 상세 `sm:` 누락, IndicatorRow 기간 선택 버튼 44px 미만, 긴 목록 virtualization 부재, viewport 확대 차단, InvestingHeader 데드 컴포넌트 모바일 미대응 |
| **MINOR** | **9** | chainsight/screener/thesis 보조 아이콘 버튼 < 44px, 인라인 스파크라인 가독성, text-[10px] 라벨 다수 |

**전반 평가**: 기반은 양호하다. MobileNav(하단 탭), MobileStockCard/MobileCardList(모바일 전용 카드 폴백), 전 테이블 `overflow-x-auto`, 전 Recharts `ResponsiveContainer`, 다수 컴포넌트의 `min-h-[44px]` 적용 등 모바일 대응의 토대가 이미 구축되어 있다. 다만 **(1) Coach 플로우의 데스크톱 전용 그리드**, **(2) 전역 `<main>` 하단 패딩 누락**, **(3) market-pulse-v2 신규 카드의 모바일 미대응**이 실사용을 막는 핵심 결함이다.

---

## 반응형 누락

### BLOCKER

#### 1. Coach E1~E6 — `grid-cols-12` 폼 입력 가로 overflow
데스크톱 12열 그리드에 입력 필드 4~5개를 가로 배치. 375px에서 1열 ≈ 31px로 입력 불가, 가로 스크롤 강제. `sm:`/`md:` 폴백 없음.

- `app/coach/e1/page.tsx:150` — `grid grid-cols-12 items-center gap-2` (col-span 3/2/2/2/1)
- `app/coach/e2/page.tsx:164` — `grid grid-cols-12` (col-span 4/3/4/1)
- `app/coach/e3/page.tsx:178` — 동일 구조
- `app/coach/e5/page.tsx:201` — 5열 입력 폼
- `app/coach/e6/page.tsx:181` — 동일 패턴

> 권장: 모바일은 `space-y-2` 1열, `md:grid md:grid-cols-12`로 데스크톱에서만 그리드 활성화.

#### 2. `<main>` 하단 패딩 누락 — MobileNav가 마지막 콘텐츠 가림
`MobileNav`는 `fixed bottom-0 h-16(64px) md:hidden`(`components/layout/MobileNav.tsx:20`). 그러나 루트 `<main className="min-h-screen">`(`app/layout.tsx`)에 하단 패딩이 없다. 하단 패딩(`pb-16`류)을 가진 페이지는 **`app/page.tsx` 단 1개뿐**이고 나머지 **29개 페이지**는 페이지 최하단 콘텐츠/버튼이 64px 높이 하단 탭에 가려진다.

> 권장: `app/layout.tsx`의 `<main>`에 `pb-16 md:pb-0` 추가(전역 단일 수정).

### MAJOR

#### 3. market-pulse-v2 카드 — 모바일 그리드 미대응
`grid-cols-3`/`grid-cols-2`에 `sm:grid-cols-1` 폴백 없음. 375px에서 1열 ≈ 110~125px로 지표 텍스트가 짓눌림.

- `app/market-pulse-v2/cards/FlowCardSummary.tsx:13` — `grid grid-cols-3 gap-2` (top5/top10/HHI)
- `app/market-pulse-v2/cards/BreadthCardSummary.tsx:14` — `grid grid-cols-2 gap-2` (5개 항목 → 불균등 행)
- `app/market-pulse-v2/details/BreadthDetail.tsx:29` — `grid grid-cols-3 gap-2` (상승/하락/AD-line)
- `app/market-pulse-v2/details/BreadthDetail.tsx:56` — `grid grid-cols-2 gap-2` (52주 신고/신저)

#### 4. Stock 상세 — `sm:` 베이스라인 누락
- `app/stocks/[symbol]/page.tsx:329` — `grid grid-cols-2 gap-4` (Key Metrics, `sm:grid-cols-1` 없음 → 375px 2열 압착)
- `app/stocks/[symbol]/page.tsx:568` — `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4` — `md`/`lg`는 있으나 모바일 기본이 2열 압착

#### 5. IndicatorRow — 단일 행 다요소 가로 overflow (관제실 핵심)
`components/thesis/dashboard/IndicatorRow.tsx:108~143` 2행이 `flex items-center gap-3 pl-4`로 값(`min-w-[60px]`) + 변동률(`min-w-[120px]`) + 스파크라인(`max-w-[100px]`) + 지지/반박 텍스트를 한 줄에 배치. 최소 폭 합계만 ≈ 280px + gap + 좌패딩 + 지지/반박 → 375px에서 줄바꿈 없이 우측 잘림/overflow 위험. 관제실의 주력 화면이라 영향 큼.

### 양호 (대조 확인)
- `app/dashboard/page.tsx:54`, `app/screener/page.tsx:435/855`, `app/portfolio/page.tsx:228`, `app/watchlist/page.tsx:207` — 모두 `grid-cols-1` 모바일 우선 + 상위 브레이크포인트 ✓
- 전 `<table>` 컴포넌트 13개 — `overflow-x-auto` 래퍼 적용 확인 ✓ (StockTable, PortfolioTable, ScreenerTable, admin 테이블 전체, validation LeaderComparison)

---

## 터치 타겟 (Apple HIG 44×44pt)

### MAJOR

#### 6. IndicatorRow 기간 선택 버튼 — 핵심 인터랙션이 44px 미만
- `components/thesis/dashboard/IndicatorRow.tsx:182` — `px-2.5 py-0.5 text-[10px]` (1M/1Y/3Y/5Y) ≈ **30×18px**. 차트 기간 전환은 고빈도 동작인데 터치 영역이 절반 미만.

### MINOR (보조/아이콘 버튼 < 44px)

| 컴포넌트:줄 | 문제 클래스 | 추정 크기 | 비고 |
|-------------|-------------|-----------|------|
| `thesis/IndicatorCard.tsx:61` | `p-1` 펼침 토글 | ~24×24px | 아이콘 전용 |
| `thesis/indicators/IndicatorSetupCard.tsx:52,63` | `p-2` 전원/삭제 | ~32×32px | 경계선상 |
| `thesis/alerts/AlertCard.tsx:57` | `text-[10px] px-2 py-1` 읽음 | ~30×26px | 보조 동작 |
| `thesis/builder/NewsSelector.tsx:142` | `p-1` 뒤로가기 | ~28×28px | 내비 |
| `screener/PresetDetailPopover.tsx:55,86` | `p-1`/`p-0.5` 닫기 | ~28/24px | 모달 닫기 |
| `screener/MarketBreadthCard.tsx:97` | `p-1` Info | ~28×28px | 정보 토글 |
| `chainsight/RelationLegend.tsx:56` | `text-[10px]` 토글 | ~35×12px | 범례 |
| `chainsight/TracePathView.tsx:33,48` | `text-sm` ✕ (패딩 없음) | ~14×14px | 경로 닫기 |
| `chainsight/FilterPanel.tsx:74,82` | `text-sm` ✕ / `text-xs` 링크 | ~14px | 필터 닫기/액션 |

### 양호 (처리 확인)
- `MobileNav.tsx:34` `min-h-[44px]`, `Pagination.tsx:127` `min-w/min-h-[44px]`, `Header.tsx:160` 햄버거 `min-h/w-[44px]`, `strategy/ScreenerTable.tsx:323` `min-h/w-[44px]`, `validation/PeerContextBar.tsx:40` `min-h-[44px]`(프리셋 탭 ✓), `validation/SignalSummaryCard.tsx:41` `min-w-[72px] min-h-[44px]` ✓, `chainsight/NodeContextMenu.tsx:139~` `px-3 py-2 text-sm`(노드 메뉴 ✓), `charts/StockPriceChart.tsx:243~261` 기간 버튼 `min-h-[44px]` ✓
- `QuarterlySparkline.tsx:44` 막대 버튼 `min-h-[44px]` ✓ (단 라벨 `text-[11px]`·툴팁 `text-[10px]`은 표시 전용)

> 참고: thesis 관제실 카드는 표시용 `text-[10px]/[11px]`이 광범위(IndicatorRow에만 7건). 클릭 요소가 아닌 라벨/설명이 대부분이라 가독성 MINOR로 분류하나, 6번 기간 버튼은 명백한 클릭 요소 위반.

---

## 네비게이션

| 항목 | 상태 | 근거 |
|------|------|------|
| Bottom navigation | **양호** | `MobileNav.tsx` — `fixed bottom-0 md:hidden` 하단 5탭(홈/종목/뉴스/포트폴리오/내정보), 각 탭 `min-h-[44px]` + `aria-label` ✓ |
| 헤더 모바일 대응 | **양호** | `Header.tsx` — 데스크톱 nav `hidden md:flex`, 모바일은 MobileNav 단일 소스로 위임(햄버거는 의도적 `hidden`, 155~163 주석) ✓ |
| 콘텐츠 가림 방지 | **BLOCKER** | (반응형 #2 참조) `<main>` 하단 패딩 부재 → 29개 페이지 하단 가림 |
| 긴 목록 virtualization | **MAJOR(부재)** | `react-window`/`@tanstack/react-virtual`/`virtua` 등 **미설치**. 스크리너·뉴스·종목 목록 등 장문 리스트가 전량 DOM 렌더 → 모바일 저사양 스크롤 성능 저하 우려 |
| 데드 컴포넌트 | **MAJOR(정리 대상)** | `components/layout/InvestingHeader.tsx` — 사용처 없음(자기 자신만 매치). 모바일 대응 전무(`max-w-[1400px]` 고정, 8개 nav 가로 나열, `text-xs` 상단바). 렌더되지 않으나 잔존 시 오용 위험 |

---

## 차트 / 그래프

| 항목 | 상태 | 근거 |
|------|------|------|
| Recharts ResponsiveContainer | **양호** | recharts 사용 차트 전수에서 `ResponsiveContainer width="100%"` 적용, 미사용 0건. `StockPriceChart.tsx:272`, `StockChart.tsx:652/748`, `PortfolioChart.tsx:77`, `IndicatorRow.tsx:197`, market-pulse-v2 detail 차트 등 |
| 차트 높이 | **MINOR** | 폭은 100% 반응형이나 높이는 고정 px. `PortfolioChart.tsx:77` `height={400}`는 375px에서 다소 큼(스크롤 유발). 가독성엔 무해 |
| 분기 스파크라인 가독성 | **MINOR** | `QuarterlySparkline.tsx` — IndicatorRow 인라인에서 `max-w-[100px]`에 막대 4개 → 막대 폭 ≈ 25px, 그 안 `Q1` 라벨 `text-[11px]`. 모바일 가독성 빠듯. 막대 터치 자체는 `min-h-[44px]`로 확보됨 ✓ |
| Chain Sight 그래프 모바일 | **양호(폴백 존재)** | `MarketGraphCanvas`(SVG pan/zoom 캔버스)는 모바일 터치 조작이 본질적으로 어려우나, `chainsight/MobileCardList.tsx` 모바일 전용 카드 리스트 폴백 제공 ✓. 노드 컨텍스트 메뉴도 `px-3 py-2`로 터치 대응 |
| 캔들 차트 | **양호** | `StockChart.tsx` candleWidth 동적 계산 + ResponsiveContainer. 단 다수 캔들 시 모바일 밀집 가능(MINOR) |

---

## 페이지별 상세

### Coach (E1~E6) — **BLOCKER**
- 진단 입력 폼 전체가 `grid-cols-12` 데스크톱 전용. 375px 입력 불가(#1). 모바일 1열 재배치 필수.
- E3 농도 미리보기 `grid-cols-2 ... sm:grid-cols-4`(e3:220)는 모바일 2열 빠듯하나 허용 범위(MINOR).

### Market Pulse V2 — **MAJOR**
- 요약/상세 카드 `grid-cols-2/3`에 모바일 폴백 부재(#3). FlowCardSummary, BreadthCardSummary, BreadthDetail 4곳.

### Stock 상세 (`/stocks/[symbol]`) — **MAJOR**
- Key Metrics 그리드 `sm:` 누락(#4). 단 본문 테이블은 `overflow-x-auto` 처리됨 ✓.

### Thesis 관제실 (`/thesis/[thesisId]`) — **BLOCKER + MAJOR + MINOR**
- IndicatorRow 단일 행 다요소 overflow(#5, BLOCKER 위험).
- 기간 선택 버튼 44px 미만(#6, MAJOR).
- 펼침 토글·전원/삭제·읽음 버튼 등 보조 액션 < 44px(MINOR 다수).
- `text-[10px]/[11px]` 표시 라벨 광범위 → 가독성 MINOR.

### Validation — **양호**
- 프리셋 탭(PeerContextBar), 시그널 버튼(SignalSummaryCard) 모두 `min-h-[44px]` 적용 ✓. LeaderComparison 테이블 `overflow-x-auto` ✓.

### Chain Sight — **양호 + MINOR**
- 그래프 캔버스에 MobileCardList 폴백 + 노드 메뉴 터치 대응 ✓.
- 보조 닫기/범례 토글(TracePathView, FilterPanel, RelationLegend)이 `text-sm`/`text-[10px]` 무패딩 → MINOR.

### Screener / Portfolio / Watchlist / Dashboard — **양호**
- 그리드 모바일 우선 설계, 테이블 가로 스크롤, MobileStockCard 폴백 존재. 닫기/Info 아이콘 버튼 일부 MINOR.

### 전역 (모든 페이지 공통)
- `<main>` 하단 패딩 누락(#2, BLOCKER) — 단일 수정으로 전 페이지 해소 가능.
- `app/layout.tsx` viewport `maximumScale: 1, userScalable: false` — **확대 차단(MAJOR/접근성)**. 저시력 사용자 핀치 줌 불가, WCAG 1.4.4 위반 소지.

---

## 부록: 우선순위 권장 (참고용, 수정은 별도 작업)

1. **(BLOCKER, 1줄 전역)** `app/layout.tsx` `<main>`에 `pb-16 md:pb-0`
2. **(BLOCKER)** Coach E1~E6 폼 모바일 1열 재배치(`md:grid-cols-12` 전환)
3. **(BLOCKER)** IndicatorRow 2행 모바일 줄바꿈/스택 처리
4. **(MAJOR)** market-pulse-v2 카드 4곳 `sm:grid-cols-1` 추가
5. **(MAJOR)** IndicatorRow 기간 버튼 `min-h-[36~44px]` + `px` 확대
6. **(MAJOR)** viewport `userScalable` 허용 검토(접근성)
7. **(MAJOR)** 장문 목록 virtualization 도입 검토
8. **(정리)** InvestingHeader 데드 컴포넌트 제거 검토
9. **(MINOR)** 보조 아이콘 버튼 9곳 터치 영역 확대

> 본 보고서는 정적 분석 기반이다. 실제 375px 디바이스/DevTools 렌더 검증으로 overflow·잘림을 최종 확인할 것을 권장한다.
