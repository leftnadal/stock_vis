# 모바일 UX 감사 보고서

생성일: 2026-05-03
대상: frontend/components, frontend/app
범위: 정적 코드 분석 (런타임 미실행)

---

## 요약

| 심각도 | 이슈 수 |
|--------|---------|
| BLOCKER | 8 |
| MAJOR | 19 |
| MINOR | 14 |

**핵심 발견:**
1. `InvestingHeader.tsx`는 모바일 햄버거 메뉴가 전혀 없는 순수 데스크톱 전용 헤더이다. 다만 현재 `app/layout.tsx`에서는 `Header.tsx`가 사용되고 있어 직접 피해는 없으나, 향후 레이아웃 전환 시 즉각 BLOCKER가 된다.
2. `PortfolioTable.tsx`는 `overflow-x-auto` 래퍼 내에 9개 이상의 컬럼을 가진 테이블을 렌더링한다. 가로 스크롤은 처리되어 있으나 375px에서 첫 번째 셀(`px-6`)이 밀리며 터치 스크롤과 혼동될 수 있다.
3. 192개 컴포넌트 중 144개(75%)가 `sm:`/`md:`/`lg:`/`xl:` 브레이크포인트를 한 건도 사용하지 않는다. 대부분이 단일 뷰포트 가정 하에 설계된 컴포넌트이다.
4. `viewport` 설정에서 `userScalable: false` / `maximumScale: 1`이 명시되어 있다(`app/layout.tsx:33`). 이는 iOS Safari에서 사용자가 핀치 줌을 할 수 없게 막아 접근성 위반(WCAG 1.4.4)에 해당하는 BLOCKER이다.
5. Recharts를 사용하는 10개 컴포넌트 모두 `ResponsiveContainer`를 감싸고 있어 차트 자체의 반응형 대응은 양호하다. 단, YAxis `width`가 고정값으로 지정된 경우 소화면에서 좌측 폭을 낭비한다.
6. `react-force-graph-2d` 기반 `MarketGraphCanvas.tsx`와 `GraphCanvas.tsx`는 `h-[400px]` 고정 높이 컨테이너에서 캔버스 폭을 `ResizeObserver`로 동적 측정한다. 375px 폭에서는 좌우 스크롤 없이 캔버스가 맞춰지나, 핀치 줌이 막혀 있어 노드 텍스트(7-10px)를 읽기 불가능하다.
7. `AddIndicatorSheet.tsx` 내 지표 버튼(`px-2.5 py-2`, 약 36px 추정 높이)들은 Apple HIG 44pt 기준에 미치지 못한다. 73개 지표를 나열한 바텀 시트이므로 모바일에서 잘못 탭할 가능성이 높다.
8. `MobileNav.tsx`의 네비게이션 항목이 5개뿐이고, `Header.tsx`의 햄버거 메뉴에는 7개 항목(대시보드, 포트폴리오, Chain Sight, Thesis Control, Market Pulse, 뉴스, 스크리너)이 있어 항목 불일치가 존재한다. MobileNav에는 `/screener`, `/market-pulse`, `/thesis`, `/chainsight`가 누락되어 있다.

---

## 1. 반응형 누락

### 1.1 고정 폭/높이 사용 현황 (정량)

Grep 결과: `w-[Npx]` / `min-w-[Npx]` / `max-w-[Npx]` → 26건(19파일), `h-[Npx]` → 23건(17파일). 합계 **49건**, **28개 고유 파일**.

상위 15개 파일 (내림차순):

| 순위 | 파일 | 고정 px 클래스 수 | 가장 큰 값 | 375px overflow 가능성 |
|------|------|------------------|-----------|-----------------------|
| 1 | `components/thesis/dashboard/IndicatorRow.tsx` | 3 | `min-w-[120px]` | 낮음 (flex 내부) |
| 2 | `components/strategy/ScreenerTable.tsx` | 3 | `max-w-[200px]` | 낮음 (truncate 적용) |
| 3 | `app/screener/page.tsx` | 2 | `h-[400px]` | 낮음 (높이만) |
| 4 | `components/chainsight/MarketGraphCanvas.tsx` | 3 | `h-[400px]` | **중간** (375px 폭에서 높이 400px 고정) |
| 5 | `components/eod/SignalDetailSheet.tsx` | 3 | `w-[420px]` | **높음** — `md:w-[420px]` 사용이나 모바일에서는 `w-full`로 전환됨 (조건부 OK) |
| 6 | `components/layout/InvestingHeader.tsx` | 3 | `max-w-[1400px]` | 낮음 (max-w, 반응형 허용) |
| 7 | `components/common/DataLoadingState.tsx` | 5 | `min-h-[200px]` | 낮음 (min-h) |
| 8 | `components/eod/SignalFilterTabs.tsx` | 2 | `min-w-[18px]` / `h-[18px]` | 낮음 (뱃지) |
| 9 | `components/admin/news/MLTrendChart.tsx` | 1 | `h-[200px]` | 낮음 |
| 10 | `components/thesis/builder/OptionButton.tsx` | 1 | `min-h-[56px]` | 낮음 (터치 타겟 보장) |
| 11 | `components/thesis/builder/TextInput.tsx` | 1 | `min-h-[44px]` | 낮음 (터치 타겟 보장) |
| 12 | `components/chainsight/ExplorationTrail.tsx` | 1 | `h-[60px]` | 낮음 |
| 13 | `components/eod/StockRow.tsx` | 2 | `max-w-[140px]` | 낮음 (truncate 적용) |
| 14 | `app/chainsight/page.tsx` | 1 | `h-[200px]` | 낮음 |
| 15 | `components/admin/shared/TaskLogViewer.tsx` | 1 | `max-w-[260px]` | 낮음 (admin 전용) |

**주요 문제점:**
- `SignalDetailSheet.tsx:97`: `w-full md:w-[420px] md:h-full` — 모바일에서는 `w-full`이 올바르게 적용됨. **OK**.
- `MarketGraphCanvas.tsx:141`: `relative h-[400px]` — 컨테이너 자체가 400px 고정. 375px 폰에서 화면 높이의 60% 이상을 캔버스가 점유. **MAJOR**.
- `app/screener/page.tsx:465`: `h-[400px]` 빈 state 컨테이너 — 모바일에서 빈 공간으로 낭비됨. **MINOR**.

### 1.2 브레이크포인트 0건인 컴포넌트/페이지

**페이지 파일 (app/) 중 브레이크포인트 0건:**

| 페이지 경로 | 비고 |
|-------------|------|
| `/` (app/page.tsx) | sm: 1건만 — EODSkeleton 제외하면 사실상 없음 |
| `/thesis` (list), `/thesis/layout`, `/thesis/[thesisId]`, `/thesis/[thesisId]/indicators`, `/thesis/[thesisId]/close`, `/thesis/(list)/alerts` | 6개 thesis 페이지 모두 0건 — 모바일 퍼스트로 설계된 `max-w-lg`는 사용하나 조건부 레이아웃 없음 |
| `/admin` | 0건 — 데스크톱 전용으로 허용 가능 |
| `/chainsight` (메인), `/chainsight/watchlist`, `/chainsight/watchlist/[id]` | 3건 모두 0건 |

**컴포넌트 144개(75%)가 브레이크포인트 0건.** 그 중 UI에 직접 영향을 주는 대표 케이스:

| 컴포넌트 | 심각도 |
|----------|--------|
| `components/rag/ChatInterface.tsx` | MAJOR — 고정 폭 `w-[52px]` 버튼 |
| `components/validation/SignalSummaryCard.tsx` | MAJOR — 7개 신호등 `overflow-x-auto` 처리됨, 단 min-w-[72px] 7개 = 최소 504px 필요 |
| `components/portfolio/PortfolioTable.tsx` | MAJOR — 9+ 컬럼 테이블 |
| `components/admin/news/MLTrendChart.tsx` | MINOR — admin 페이지 |
| `components/chainsight/MarketGraphCanvas.tsx` | MAJOR — 고정 높이 캔버스 |

### 1.3 테이블/차트 가로 스크롤 처리 현황

| 컴포넌트/파일 | overflow-x 처리 | 비고 |
|---------------|----------------|------|
| `components/portfolio/PortfolioTable.tsx:259` | `overflow-x-auto` | 처리됨 |
| `components/strategy/ScreenerTable.tsx` | `overflow-x-auto` | 처리됨 (`app/screener/page.tsx` 래퍼) |
| `components/stocks/StockTable.tsx` | `overflow-x-auto` | 처리됨 |
| `components/validation/SignalSummaryCard.tsx:36` | `overflow-x-auto pb-2 scrollbar-hide` | 처리됨 |
| `components/admin/SystemTab.tsx` | `overflow-x-auto` (3건) | admin 전용 |
| `components/admin/ScreenerTab.tsx` | `overflow-x-auto` (2건) | admin 전용 |
| `components/chainsight/MobileCardList.tsx:84` | `overflow-x-auto` | 탭 바 처리됨 |
| `components/chainsight/FullPathView.tsx` | `overflow-x-auto` | 처리됨 |
| `components/chainsight/TracePathView.tsx` | `overflow-x-auto` | 처리됨 |
| `components/admin/news/MLCompareView.tsx` | `overflow-x-auto` | admin 전용 |
| `components/admin/news/CollectionStatsTable.tsx` | `overflow-x-auto` | admin 전용 |
| `components/stock/OtherFundamentalsTab.tsx` | **없음** | MAJOR — 10개 sm: 브레이크포인트는 있으나 테이블 래퍼 없음 |
| `components/eod/SignalFilterTabs.tsx:33` | `overflow-x-auto pb-1 scrollbar-hide` | 처리됨 |

**결론:** 핵심 사용자 페이지의 테이블은 대부분 `overflow-x-auto`로 처리되어 있다. `OtherFundamentalsTab.tsx`만 누락.

---

## 2. 터치 타겟

### 2.1 44pt 미만 추정 인터랙션 요소

Apple HIG 기준 44×44pt(=44px). 아래 표는 grep으로 확인한 위반 패턴이다.

| 파일:줄 | 위반 패턴 | 추정 크기 | 심각도 | 모바일 영향 |
|---------|----------|----------|--------|------------|
| `components/eod/SignalDetailSheet.tsx:138` | `p-1.5 rounded-full` (닫기 버튼) | ~28px | MAJOR | 시트 닫기 오탭 |
| `components/eod/SignalDetailSheet.tsx:188` | `text-[10px] px-1.5 py-0.5 cursor-pointer` (Chain Sight 섹터 링크) | ~18px | BLOCKER | 375px에서 클릭 불가 수준 |
| `components/thesis/builder/OptionButton.tsx:72` | `p-1 cursor-pointer` (hidden sm:flex 삭제 버튼) | ~28px | MINOR | `sm:` 이하에서는 hidden |
| `components/thesis/builder/NewsSelector.tsx:142` | `p-1 text-gray-400 hover:text-white` (뒤로가기 버튼) | ~28px | MAJOR | 가설 빌더 뒤로가기 오탭 |
| `components/layout/InvestingHeader.tsx:112` | `px-3 py-1 text-sm` ("더보기" 버튼) | ~32px | MAJOR | InvestingHeader 사용 시 |
| `components/admin/shared/ActionButton.tsx:73` | `px-2 py-0.5 text-xs` (확인/취소 버튼) | ~24px | MAJOR | admin 페이지 한정 |
| `components/thesis/AddIndicatorSheet.tsx:226` | `px-2.5 py-2 text-xs` (지표 선택 버튼 73개) | ~32px | MAJOR | 가설 지표 설정 핵심 인터랙션 |
| `components/rag/ChatInterface.tsx:198` | `h-[52px] w-[52px]` (전송 버튼) | 52px | OK | 충분함 |
| `components/thesis/builder/OptionButton.tsx:52` | `min-h-[52px] py-3` 또는 `min-h-[56px] py-4` | 52-56px | OK | 충분함 |
| `components/thesis/builder/TextInput.tsx:46` | `min-h-[44px]` | 44px | 경계 | 경계값 충족 |

**핵심 BLOCKER:** `SignalDetailSheet.tsx:188` — `text-[10px] px-1.5 py-0.5` 섹터 링크가 Chain Sight로 이동하는 인터랙션에서 터치 영역이 약 18×18px 수준.

### 2.2 thesis 관제실 (`components/thesis/dashboard/`)

`IndicatorRow.tsx` 분석:
- 메인 행 토글 버튼: `px-4 py-3 w-full` → 약 44px 이상 높이. **OK**.
- 기간 선택 버튼(`px-2.5 py-0.5 text-[10px]`): `IndicatorRow.tsx:183` → 약 22-24px 높이. MAJOR.
  - `e.stopPropagation()`로 이벤트 버블 차단은 올바르나 터치 타겟이 너무 작음.
- `min-w-[60px]`, `min-w-[120px]`, `max-w-[100px]`: flex 레이아웃 내 텍스트 최소 폭 지정 — 375px에서 2행 레이아웃으로 넘치지 않을 수 있으나 `gap-3 pl-4` 포함 시 합계 폭이 약 310px로 375px 이내.
- `text-[11px]` 날짜 라벨: 가독성 부족. MINOR.
- **전체 평가:** 메인 인터랙션(토글)은 양호. 세부 버튼(기간 선택)이 MAJOR.

`IndividualMiniCharts.tsx` 분석:
- 인터랙션 없음, 순수 차트 컴포넌트. `ResponsiveContainer width="100%" height={100}` 사용. 높이 100px는 모바일에서 스파크라인으로 적절.
- YAxis `width={55}`: 375px에서 55px 점유 → 차트 실질 폭 320px. **MINOR** (읽기는 가능하나 여유 부족).

`QuarterlySparkline` (IndicatorRow 내 inline 사용): `max-w-[100px]` 제약으로 인라인에서 100px 폭 스파크라인. 충분히 읽기 어려운 크기. **MINOR**.

### 2.3 validation 프리셋 (`components/validation/`)

`SignalSummaryCard.tsx` 분석:
- 7개 신호등 카드: `min-w-[72px]`씩 = 504px minimum. `overflow-x-auto`로 처리됨.
- 각 신호등 원(`.w-10 .h-10 = 40×40px`): Apple HIG 44pt 미만. **MAJOR**.
  - `onMouseEnter`/`onMouseLeave`로 툴팁 표시 — 모바일에서는 hover 이벤트 미지원. 툴팁 접근 불가. **MAJOR**.
- 카테고리명: `text-xs` → 12px. 읽기는 가능하나 작음. **MINOR**.

`LeaderComparisonSection.tsx`: `overflow-x-auto` 처리됨.

### 2.4 chainsight 노드/카드 (`components/chainsight/`)

`MarketGraphCanvas.tsx` (chainsight 메인 탐색 그래프):
- Canvas 위 노드 클릭 영역: `nodePointerAreaPaint`에서 `r = getNodeRadius(node)` (6~16px). 반지름 6px = 12px 직경. **BLOCKER** — Apple HIG 44pt의 1/3 이하.
- 캔버스 폰트: `7-10px sans-serif`. 375px 폰에서 종목명 읽기 불가. **MAJOR**.
- `h-[400px]` 고정 높이: 375px 폰에서 세로 공간의 70% 이상 점유. **MAJOR**.
- `pinch-zoom`: `react-force-graph-2d`는 내장 pan/zoom을 제공하나, `app/layout.tsx:33`의 `userScalable: false`가 iOS Safari에서 제스처를 차단할 수 있음. **BLOCKER**.

`MobileCardList.tsx` (모바일 대체 뷰): `/chainsight/[symbol]`에서 `isMobile` 감지 시 렌더링.
- 카드 레이아웃 `p-4`, 버튼 `text-xs py-1.5 rounded-lg` (~28-32px): MAJOR.
- "가설 생성", "탐색", "검증" 3버튼 `flex-1 text-center text-xs py-1.5`: 375px 3등분 = 약 109px 폭, 28-32px 높이. **MAJOR** — HIG 미충족.
- 카테고리 탭 버튼 `px-3 py-1.5 text-sm rounded-full`: 약 32-36px 높이. **MAJOR**.
- 전반적으로 모바일 전용 뷰가 있다는 점은 양호하나 터치 타겟이 일관되게 작음.

---

## 3. 모바일 네비게이션

### 3.1 햄버거 메뉴 / 사이드바

**Header.tsx 분석** (`app/layout.tsx`에서 전역 사용):
- 데스크톱: `hidden md:flex` nav 메뉴 7개 항목.
- 모바일: `md:hidden` 햄버거 버튼(`Menu` 아이콘, `p-2 rounded-md` = ~40px). **경계값** — Apple HIG 44pt에 4px 미달.
- 햄버거 클릭 시 `isMenuOpen` 토글로 드롭다운 메뉴 표시: 항목별 `block px-3 py-2 rounded-md text-base font-medium` = 약 44px 이상 높이. **OK**.
- 모바일 메뉴 항목: 대시보드, 포트폴리오, Chain Sight, Thesis Control, Market Pulse, 뉴스, 스크리너, 마이페이지(로그인 시). 총 7-8개.
- 모바일 검색창 포함됨: **OK**.

**InvestingHeader.tsx 분석** (현재 `app/layout.tsx`에서 사용 안 함, 단독 import 없음):
- 모바일 햄버거 메뉴 **전혀 없음**. `md:` 없이 전체 nav를 렌더링.
- Top Bar의 `flex items-center space-x-6`은 375px에서 overflow 발생.
- 만약 이 헤더로 전환되면 즉각 **BLOCKER**. 현재는 잠재적 위험.

**메뉴 항목 일관성 비교:**

| 항목 | Header.tsx 햄버거 | MobileNav.tsx 바텀 |
|------|-------------------|--------------------|
| 대시보드(/) | O | O (홈) |
| 포트폴리오 | O | O |
| Chain Sight | O | **X** |
| Thesis Control | O | **X** |
| Market Pulse | O | **X** |
| 뉴스 | O | O |
| 스크리너 | O | **X** |
| 종목 검색 | X | O (`/stocks`) |
| 내정보 | O (로그인 시) | O (`/profile`) |

MobileNav에서 **Chain Sight, Thesis Control, Market Pulse, 스크리너 4개가 누락**됨. **MAJOR**.

또한 MobileNav의 "내정보"는 `/profile`로 링크하나 실제 라우트는 `/mypage`이다. **BLOCKER** — 탭 클릭 시 404.

### 3.2 Bottom Navigation

`MobileNav.tsx`:
- `fixed bottom-0 left-0 right-0 bg-white ... md:hidden z-50`로 구현됨.
- `h-16` (64px) 높이, 5개 링크 각 `flex-1 h-full`. **OK** (높이 충분).
- 아이콘 `h-5 w-5` + 라벨 `text-xs`: 합계 ~42px 높이 내 콘텐츠. 터치 타겟은 전체 `h-full`이므로 OK.
- Safe area 처리 없음: iPhone 홈 인디케이터 영역 침범. `pb-safe` 또는 `padding-bottom: env(safe-area-inset-bottom)` 누락. **MAJOR**.
- `app/layout.tsx`: `<main className="min-h-screen">` — MobileNav 64px를 위한 `pb-16 md:pb-0` 패딩 없음. 콘텐츠가 바텀 nav에 가려짐. **BLOCKER** — 실제 확인 위치: `app/layout.tsx:61`.
- 단, `app/thesis/[thesisId]/page.tsx:62`는 `pb-20 md:pb-0`로 직접 처리. 페이지별 임시 패치이지만 전역 해결책 없음.

### 3.3 Virtualization

`react-window`, `react-virtual`, `useVirtualizer`, `FixedSizeList`, `VirtualList` — **0건 발견**.

긴 목록 페이지별 현황:

| 페이지 | 목록 크기 | Virtualization | 비고 |
|--------|----------|---------------|------|
| `/screener` | 최대 50건 (pageSize) | 없음 | 페이지네이션으로 부분 완화 |
| `/news` | 최대 100건 | 없음 | `useAllNews`로 100건 전체 렌더 |
| `/watchlist` | 관심종목 전체 | 없음 | 소규모 예상 |
| `/thesis` (list) | 가설 전체 | 없음 | 소규모 예상 |
| `/chainsight/[symbol]` MobileCardList | 그래프 노드 전체 | 없음 | 수십 건 가능 |

뉴스 페이지 100건 전체 렌더는 **MAJOR** — 모바일 저사양 기기에서 초기 파싱 비용이 크다.

---

## 4. 차트/그래프

### 4.1 Recharts ResponsiveContainer 사용 현황

`from 'recharts'` import 파일 10개 (테스트 파일 1개 제외 9개 프로덕션 컴포넌트).

| 컴포넌트 | ResponsiveContainer | 비고 |
|----------|---------------------|------|
| `components/thesis/dashboard/IndicatorRow.tsx` | O (2회) | 일간/분기 차트 모두 적용 |
| `components/thesis/dashboard/IndividualMiniCharts.tsx` | O | `width="100%" height={100}` |
| `components/validation/MetricBarChart.tsx` | O | `width="100%" height="100%"` |
| `components/admin/news/MLTrendChart.tsx` | O | admin 전용 |
| `components/screener/SectorHeatmap.tsx` | O (Treemap) | 처리됨 |
| `components/stock/StockChart.tsx` | O | 처리됨 |
| `components/news/SentimentChart.tsx` | O | `width="100%" height="100%"` |
| `components/macro/YieldCurveChart.tsx` | O | `width="100%" height="100%"` |
| `components/portfolio/PortfolioChart.tsx` | O | 처리됨 |
| `components/charts/StockPriceChart.tsx` | O | 처리됨 |

**모든 Recharts 컴포넌트가 `ResponsiveContainer`를 사용하고 있다. ResponsiveContainer 미사용 케이스 0건.** 이 항목은 전체적으로 양호하다.

### 4.2 분기 스파크라인 가독성

`IndicatorRow.tsx` 인라인 스파크라인 (`max-w-[100px]`):
- 최근 4분기 데이터를 100px 폭 영역에 렌더링.
- 차트 타입: `ResponsiveContainer width="100%"` 내 `AreaChart`. 폰트 size `9px` (XAxis). **MINOR** — 데이터 트렌드는 파악 가능하나 수치 읽기 불가.
- 상세 뷰(expanded): `height={140}` 분기 차트. XAxis 폰트 9px, YAxis 폰트 10px. 375px에서 YAxis `width={50}` 제외 시 실질 차트 폭 약 310px. 읽기 가능. **OK**.

`IndividualMiniCharts.tsx`:
- `height={100}` 미니차트. YAxis `width={55}`. 375px에서 실질 폭 265px. **MAJOR** — 매우 좁음. XAxis 날짜 레이블 `fontSize={10}` 겹칠 수 있음.
- YAxis 레이블 `tickFormatter`로 값 포맷팅은 적절.

### 4.3 그래프 시각화 (Chainsight)

**MarketGraphCanvas.tsx** (`/chainsight` 메인):
- `react-force-graph-2d`를 Canvas 기반으로 렌더링.
- 컨테이너: `h-[400px]` 고정. 375px 폰에서 전체 화면의 약 60% 점유.
- `ResizeObserver`로 `containerWidth` 동적 측정 → `ForceGraph2D width={containerWidth} height={400}` 전달. 폭은 동적, 높이는 고정.
- 노드 클릭 반경: 6~16px. **BLOCKER** — 손가락으로 작은 노드 선택 거의 불가.
- 캔버스 내 폰트: 7-10px. **MAJOR** — 375px 폰에서 종목명 읽기 불가.
- Pinch-zoom: `react-force-graph-2d`의 자체 줌/팬은 존재하나, `app/layout.tsx`의 `userScalable: false`가 iOS Safari 기본 핀치 줌을 막아 force graph 자체 줌도 충돌 가능성. **BLOCKER**.
- 이 컴포넌트는 `/chainsight` (메인 마켓뷰) 전용이며, `/chainsight/[symbol]`에서는 `MobileCardList`로 대체됨.

**GraphCanvas.tsx** (`/chainsight/[symbol]` 그래프 오버레이):
- `app/chainsight/[symbol]/page.tsx`에서 `isMobile` 감지 후 `MobileCardList`로 분기됨. 그래프 오버레이 시에는 `fixed inset-0 z-50`으로 전체화면 렌더. **OK** (모바일 대응 분기 존재).
- `canvasSize.h - 48` 높이 계산으로 헤더 제외 전체 화면 사용. **OK**.

**전반 평가:** `/chainsight/[symbol]`은 모바일 분기가 구현되어 있어 양호. `/chainsight` (메인)는 모바일 대응 없음. **MAJOR**.

---

## 5. 페이지별 상세

### /

**사용 컴포넌트:** `EODSkeleton`, `DataFreshnessBadge`, `MarketSummaryBar`, `SignalFilterTabs`, `SignalCardGrid`, `SignalDetailSheet`

- BLOCKER: `SignalDetailSheet.tsx:188` — Chain Sight 섹터 링크 `text-[10px] px-1.5 py-0.5` 터치 타겟 ~18px.
- BLOCKER: `app/layout.tsx:61` `<main className="min-h-screen">` — MobileNav 64px에 가려짐.
- MAJOR: `SignalFilterTabs` — `min-w-[18px] h-[18px]` 카운트 뱃지는 인터랙션 없음. 탭 버튼 자체 `px-3 py-1.5` ~32-36px. 경계.
- MINOR: `DataFreshnessBadge` — 브레이크포인트 없으나 단순 뱃지.
- 종합 모바일 점수: **5/10**

### /dashboard

**사용 컴포넌트:** 자체 구현 (카드 3개)

- MAJOR: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` — 올바른 반응형. 하지만 nav 중복 구현(`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`).
- MINOR: 대시보드 콘텐츠 극히 단순. 실질적 기능 없음 (리다이렉트 페이지 수준).
- 종합 모바일 점수: **6/10**

### /login, /signup

- MAJOR: `/login` — `sm:`, `md:`, `lg:` 3건 있음. 폼 레이아웃 적절.
- `/signup:6` — 브레이크포인트 6건으로 반응형 구현됨.
- MINOR: 인증 폼 특성상 모바일 최적화 양호한 편.
- 종합 모바일 점수: **7/10**

### /mypage

- 브레이크포인트 1건(`sm:` 또는 `md:`).
- MAJOR: 세부 구현 확인 필요하나 브레이크포인트 극히 부족.
- 종합 모바일 점수: **5/10**

### /stocks/[symbol]

**사용 컴포넌트:** `StockChart`, `SentimentChart`, `OtherFundamentalsTab`, `SignalSummaryCard`, `MetricBarChart`, `GraphMiniView`, 재무제표 테이블(자체 구현)

- BLOCKER: 재무제표 테이블 (`app/stocks/[symbol]/page.tsx` 내부 구현) — `overflow-x-auto` 처리 여부 불명. 브레이크포인트 5건은 있으나 테이블 래퍼 확인 필요.
- MAJOR: `SignalSummaryCard` — 신호등 40×40px (44pt 미달), hover 툴팁 모바일 미작동.
- MAJOR: `OtherFundamentalsTab` — 다중 컬럼 테이블, `overflow-x-auto` 래퍼 없음.
- MAJOR: `SentimentChart` — `margin={{ top: 20, right: 30, left: 20, bottom: 20 }}` 고정 마진으로 375px에서 YAxis 레이블 공간 부족.
- MINOR: `MetricBarChart` — `right: 50` 마진이 375px에서 차트 폭을 많이 잠식.
- 종합 모바일 점수: **4/10**

### /watchlist

- 브레이크포인트 4건.
- MAJOR: `WatchlistItemRow` 컴포넌트 내 아이콘 버튼 크기 미확인(직접 Read 범위 초과). 일반적 패턴상 MAJOR 가능성.
- MINOR: 목록 페이지로 구조 단순.
- 종합 모바일 점수: **6/10**

### /portfolio

- 브레이크포인트 2건.
- BLOCKER: `PortfolioTable` 9+ 컬럼 테이블은 `overflow-x-auto` 처리됨. 그러나 `px-6` 헤더 패딩으로 첫 셀이 밀려 터치 스크롤 혼동 가능. 허용 범위 내.
- MAJOR: `grid-cols-2 md:grid-cols-3 lg:grid-cols-6` 요약 카드 — 375px에서 2열. OK.
- MINOR: `PortfolioChart` PieChart 라벨(`renderLabel`) — 375px에서 레이블 겹칠 수 있음.
- 종합 모바일 점수: **6/10**

### /screener

- 브레이크포인트 12건 (가장 많음).
- MAJOR: `SectorHeatmap` (Treemap) — 모바일에서 타일이 너무 작아 터치 불가 가능. `width < 60 || height < 40` 조건 처리되어 있으나 텍스트 없는 색상 타일만 남음.
- MAJOR: `AdvancedFilterPanel` — 브레이크포인트 1건. 필터 패널 모바일 최적화 부족.
- MAJOR: 뷰 모드 `table/card` 전환 — 모바일에서 `card`를 기본값으로 두어야 하나 `useState<'table' | 'card'>('table')` 기본값이 table. `app/screener/page.tsx:72`.
- MINOR: `Pagination` 컴포넌트 `min-w-[32px] px-2 py-1.5` — 약 32-36px. 경계.
- 종합 모바일 점수: **5/10**

### /thesis (list)

- 브레이크포인트 0건.
- `max-w-lg mx-auto`로 모바일 폭 제한. 단일 컬럼 설계.
- MAJOR: `MoonPhase`, `ArrowIndicator` 컴포넌트 내 `sm:`, `md:`, `lg:` 각 3건 있음. 하지만 목록 페이지 자체 브레이크포인트 없음.
- MINOR: 전체적으로 모바일 퍼스트 설계에 가까움.
- 종합 모바일 점수: **7/10**

### /thesis/new

- 브레이크포인트 2건.
- MAJOR: 가설 빌더 — `OptionButton.tsx`의 `sm:hidden` 클래스 사용으로 모바일 대응 존재. 단 `hidden sm:flex` 삭제버튼 모바일 표시 안 됨 — 삭제 기능 모바일 미지원.
- MINOR: ChatBubble `min-h-[44px]` — 경계값 충족.
- 종합 모바일 점수: **6/10**

### /thesis/[thesisId]

**사용 컴포넌트:** `DashboardHeader`, `IndicatorRow`, `AISummarySection`, `NotableChangesSection`

- BLOCKER: `IndicatorRow` 기간 선택 버튼 `px-2.5 py-0.5 text-[10px]` → ~22-24px. 관제실 핵심 인터랙션.
- MAJOR: `max-w-lg mx-auto px-4 pt-4 pb-20` — `pb-20` 패딩으로 MobileNav 가림 방지 처리됨. OK.
- MAJOR: 인라인 스파크라인 `max-w-[100px]` — 100px 폭은 가독성 낮음.
- MINOR: `text-[11px]` 날짜/전제 라벨 — 11px 가독성 낮음.
- 종합 모바일 점수: **6/10**

### /thesis/[thesisId]/indicators

- `h-[calc(100dvh-env(safe-area-inset-top))]` 사용 — Safe area 처리됨. **OK**.
- MAJOR: `AddIndicatorSheet` 내 지표 버튼 `px-2.5 py-2 text-xs` (~32px) 73개.
- MINOR: 검색 인풋, 카테고리 탭 구현 확인 필요.
- 종합 모바일 점수: **6/10**

### /thesis/[thesisId]/close

- `h-[calc(100dvh-env(safe-area-inset-top))]` 사용 — Safe area 처리됨.
- `ArrowLeft size={20}` + `p-1` 래퍼 ~28px. MAJOR.
- `OutcomeSelector` 내 선택 버튼 크기 불명.
- 종합 모바일 점수: **6/10**

### /thesis/(list)/alerts

- 브레이크포인트 0건.
- `AlertCard`, `AlertFilterTabs` 내 구현에 따름.
- MINOR: 단순 목록 구조.
- 종합 모바일 점수: **7/10**

### /chainsight

- 브레이크포인트 0건.
- BLOCKER: `MarketGraphCanvas` — 고정 `h-[400px]` + 노드 6-16px 클릭 영역 + 폰트 7-10px.
- BLOCKER: `userScalable: false` 핀치 줌 차단.
- MAJOR: 모바일 분기 없음. 섹터 선택 사이드바(`SectorBar`, `ExplorationTrail`)가 데스크톱 3패널 구조로 렌더링.
- 종합 모바일 점수: **2/10**

### /chainsight/[symbol]

- 브레이크포인트 1건.
- `isMobile` 감지 후 `MobileCardList` 분기. **모바일 대응 존재** — 이 점에서 다른 chainsight 페이지와 차별화됨.
- MAJOR: `MobileCardList` 내 버튼 `text-xs py-1.5` (~28-32px).
- MAJOR: 그래프 오버레이 `GraphCanvas` — 전체화면으로 OK이나 노드 클릭 어려움.
- MINOR: `graphOverlay` FAB 버튼 `w-full py-3` — 충분한 크기.
- 종합 모바일 점수: **5/10**

### /chainsight/watchlist

- 브레이크포인트 0건. 구현 확인 불가 (Read 범위 초과).
- MAJOR: 0 브레이크포인트 추정.
- 종합 모바일 점수: **4/10** (추정)

### /chainsight/watchlist/[id]

- 브레이크포인트 0건.
- 종합 모바일 점수: **4/10** (추정)

### /news

- 브레이크포인트 7건.
- MAJOR: 100건 전체 렌더 (Virtualization 없음).
- MAJOR: `DailyKeywordCard`, `NewsHighlightedStocks` — 브레이크포인트 각 2건으로 기본 대응.
- MINOR: `AINewsBriefingCard` — `max-w-[200px]` 프로그레스 바.
- 종합 모바일 점수: **5/10**

### /market-pulse

- 브레이크포인트 9건.
- MAJOR: `YieldCurveChart` 고정 `h-64 mt-4` + `ResponsiveContainer` 사용. OK.
- MAJOR: `EconomicIndicators`, `GlobalMarketsCard` — 각 1건 브레이크포인트. 그리드 레이아웃 모바일 대응 부분적.
- MINOR: 스틱키 헤더 `sticky top-0 z-10` — 모바일에서 공간 낭비.
- 종합 모바일 점수: **5/10**

### /ai-analysis

- 브레이크포인트 2건.
- MAJOR: `ChatInterface.tsx` — `h-[52px] w-[52px]` 전송 버튼은 충분. 단 사이드 패널(DataBasket, TokenUsage) 레이아웃이 모바일에서 어떻게 동작하는지 브레이크포인트 부족으로 우려됨.
- MAJOR: `MonitoringDashboard` 토글 — 모달/오버레이 방식이나 모바일 대응 미확인.
- 종합 모바일 점수: **5/10**

### /admin

- 브레이크포인트 0건.
- 어드민 전용으로 모바일 접근 불필요 — 허용 가능.
- 종합 모바일 점수: N/A (관리자 전용)

---

## 6. 전역 이슈 요약

### BLOCKER 목록 (8건)

| # | 위치 | 이슈 |
|---|------|------|
| B1 | `app/layout.tsx:33` | `userScalable: false` + `maximumScale: 1` — WCAG 1.4.4 위반, iOS 핀치 줌 전면 차단 |
| B2 | `app/layout.tsx:61` | `<main className="min-h-screen">` — MobileNav 64px pb 없음. 하단 콘텐츠 가려짐 |
| B3 | `components/layout/MobileNav.tsx` `/profile` 링크 | 실제 라우트 `/mypage` 불일치 → 404 |
| B4 | `components/eod/SignalDetailSheet.tsx:188` | `text-[10px] px-1.5 py-0.5` 섹터 링크 ~18px 터치 영역 |
| B5 | `components/chainsight/MarketGraphCanvas.tsx:148-155` | Force graph 노드 클릭 반경 6-16px (평균 8-10px) → 손가락 탭 거의 불가 |
| B6 | `/chainsight` (app/chainsight/page.tsx) | 모바일 분기 없는 3-패널 그래프 뷰. 375px에서 사용 불가 |
| B7 | `components/layout/InvestingHeader.tsx` | 모바일 햄버거 메뉴 전혀 없음 (현재 미사용이나 잠재적 위험) |
| B8 | `components/layout/MobileNav.tsx:19` | `env(safe-area-inset-bottom)` 없음 — iPhone 홈 인디케이터 침범 |

### MAJOR 목록 (주요 19건)

| # | 위치 | 이슈 |
|---|------|------|
| M1 | `components/validation/SignalSummaryCard.tsx:46` | 신호등 40×40px — HIG 44pt 미달 |
| M2 | `components/validation/SignalSummaryCard.tsx:41-44` | onMouseEnter 툴팁 — 모바일 미작동 |
| M3 | `components/thesis/dashboard/IndicatorRow.tsx:183` | 기간 선택 버튼 `py-0.5` ~22px |
| M4 | `components/thesis/AddIndicatorSheet.tsx:226` | 지표 버튼 73개 `py-2` ~32px |
| M5 | `components/thesis/builder/NewsSelector.tsx:142` | 뒤로가기 `p-1` ~28px |
| M6 | `components/chainsight/MobileCardList.tsx:88` | 카드 CTA 버튼 `py-1.5 text-xs` ~28-32px |
| M7 | `components/chainsight/MarketGraphCanvas.tsx:141` | `h-[400px]` 고정 높이 |
| M8 | `components/chainsight/MarketGraphCanvas.tsx` | Canvas 폰트 7-10px — 모바일 읽기 불가 |
| M9 | `components/layout/MobileNav.tsx` | Chain Sight, Thesis, Market Pulse, 스크리너 항목 누락 |
| M10 | `components/stock/OtherFundamentalsTab.tsx` | 테이블 `overflow-x-auto` 래퍼 없음 |
| M11 | `app/screener/page.tsx:72` | 기본 viewMode `'table'` — 모바일에서 카드 모드가 적합 |
| M12 | `app/news/page.tsx` | 100건 Virtualization 없이 전체 렌더 |
| M13 | `components/thesis/dashboard/IndividualMiniCharts.tsx` | `height={100}` YAxis `width={55}` — 265px 유효 폭 |
| M14 | `components/news/SentimentChart.tsx:83` | `margin={{ right: 30, left: 20 }}` 375px 차트 폭 잠식 |
| M15 | `/chainsight/watchlist`, `/chainsight/watchlist/[id]` | 브레이크포인트 0건 추정 |
| M16 | `components/eod/SignalDetailSheet.tsx:138` | 닫기 버튼 `p-1.5` ~28px |
| M17 | `components/screener/SectorHeatmap.tsx` | 모바일 소형 타일 터치 불가 |
| M18 | `app/chainsight/[symbol]/page.tsx` | `MobileCardList` CTA 버튼 `py-1.5` 전반적 소형 |
| M19 | `app/ai-analysis/page.tsx` | 사이드 패널 레이아웃 브레이크포인트 2건 |

### MINOR 목록 (주요 14건)

| # | 위치 | 이슈 |
|---|------|------|
| Mi1 | `components/thesis/dashboard/IndicatorRow.tsx` | `text-[11px]` 날짜/전제 라벨 |
| Mi2 | `components/thesis/dashboard/IndicatorRow.tsx` | 인라인 스파크라인 `max-w-[100px]` 가독성 |
| Mi3 | `components/validation/MetricBarChart.tsx:79` | `margin={{ right: 50 }}` 공간 낭비 |
| Mi4 | `app/screener/page.tsx:465` | `h-[400px]` 빈 상태 컨테이너 |
| Mi5 | `components/chainsight/MarketGraphCanvas.tsx:214` | 이름 레이블 `7px sans-serif` |
| Mi6 | `components/screener/Pagination.tsx:127` | `min-w-[32px] px-2 py-1.5` 경계값 |
| Mi7 | `app/market-pulse/page.tsx` | sticky 헤더 + 긴 제목 모바일 공간 낭비 |
| Mi8 | `components/portfolio/PortfolioChart.tsx` | Pie 라벨 겹칠 수 있음 |
| Mi9 | `components/macro/YieldCurveChart.tsx` | 고정 `h-64` (256px) — `ResponsiveContainer` 내부이므로 폭은 OK |
| Mi10 | `components/thesis/builder/OptionButton.tsx:72` | `hidden sm:flex` 삭제버튼 모바일 미노출 |
| Mi11 | `components/rag/SuggestionChips.tsx` | `max-w-[150px] truncate text-xs` — 칩 내용 잘림 |
| Mi12 | `app/layout.tsx:33` | `maximumScale: 1` (userScalable false와 함께 기록) |
| Mi13 | `components/eod/SignalFilterTabs.tsx` | 카운트 뱃지 `h-[18px]` 인터랙션 없음 |
| Mi14 | 모든 thesis 페이지 | `h-[calc(100dvh-env(safe-area-inset-top))]` 사용은 양호하나 bottom safe area 미처리 |

---

## 7. 권고 우선순위

1. **즉시 수정 (B1-B4):** `app/layout.tsx` viewport `userScalable` 제거 + `<main>` pb-16 추가 + MobileNav `/profile` → `/mypage` 수정 + SignalDetailSheet 섹터 링크 패딩 확대.
2. **단기 수정 (B5-B8, M1-M6):** MarketGraphCanvas 노드 클릭 영역 확대 + MobileNav 항목 추가 + 주요 버튼 min-h-[44px] 적용.
3. **중기 개선 (M7-M19):** news 페이지 virtualization 도입 + 스크리너 기본 viewMode card 전환 + MobileCardList 버튼 크기 보완.
