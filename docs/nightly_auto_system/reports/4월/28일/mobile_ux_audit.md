# 모바일 UX 감사 보고서

생성일: 2026-04-29
대상: frontend/ (Next.js 16 + Tailwind)
기준: iPhone SE 375px viewport, Apple HIG 44pt

---

## 요약

| 심각도 | 개수 |
|---|---|
| BLOCKER | 5 |
| MAJOR | 14 |
| MINOR | 9 |

핵심 발견:
1. **`userScalable: false`** 설정으로 전 페이지에서 핀치줌 완전 차단 — 접근성 WCAG 위반
2. **InvestingHeader.tsx**: 모바일 대응 없음 (hamburger 없음, `max-w-[1400px]` 고정, hidden md 처리 없음) — 375px에서 레이아웃 붕괴
3. **AI Analysis 페이지**: 절대 위치 패널 `w-96`(384px), `w-80`(320px)이 375px 뷰포트 전체를 덮음
4. **MobileNav 5개 항목 vs Header 7개 항목 불일치**: Thesis Control, Market Pulse, 스크리너, Chain Sight 등 핵심 기능이 MobileNav에 없음
5. **ScreenerTable**: `overflow-x-auto` 처리는 있으나 8개 컬럼 테이블이 375px에서 극단적으로 축소되어 가독 불가능

---

## 1. 반응형 누락

### BLOCKER

- **`frontend/app/layout.tsx:33`** — `userScalable: false` 핀치줌 전면 차단
  ```tsx
  viewport: {
    userScalable: false,
    viewportFit: "cover",
  }
  ```
  권장: `userScalable: false` 제거 또는 `true`로 변경. WCAG 1.4.4 기준 위반, iOS 접근성 설정과 충돌.

- **`frontend/components/layout/InvestingHeader.tsx:32,55,99`** — `max-w-[1400px]` 3곳 + 반응형 없음
  ```tsx
  <div className="max-w-[1400px] mx-auto px-4">
    <div className="flex items-center justify-between h-10 text-xs">
      <div className="flex items-center space-x-6">  {/* 모든 항목 수평 나열 */}
  ```
  권장: `hidden md:flex`로 데스크톱 전용 처리, 모바일 hamburger 또는 Sheet 추가. 이 헤더는 현재 메인 `app/layout.tsx`에는 미사용이나 별도 페이지에서 사용 시 375px 완전 붕괴.

- **`frontend/app/ai-analysis/page.tsx:294,304`** — 절대 위치 패널이 375px 초과
  ```tsx
  <div className="absolute left-4 top-20 z-50 w-96">   {/* 384px — 375px 초과 */}
  <div className="absolute right-4 top-20 z-50 w-80">   {/* 320px — 오른쪽 잘림 */}
  ```
  권장: `w-96` → `w-full max-w-sm`, `w-80` → `w-full max-w-xs` 또는 bottom sheet 패턴으로 전환.

### MAJOR

- **`frontend/components/strategy/ScreenerTable.tsx:128`** — `overflow-x-auto` 있으나 8컬럼 테이블, 각 컬럼 최소 폭 미정의
  ```tsx
  <div className="overflow-x-auto">
    <table className="w-full"> {/* 종목/거래소/섹터/가격/변동률/시가총액/거래량/배당률 8컬럼 */}
  ```
  권장: 모바일에서는 핵심 3컬럼(종목명/가격/변동률)만 표시, 나머지 `hidden md:table-cell` 처리. 이미 `MobileStockCard` 컴포넌트가 존재하므로 뷰모드 기본값을 mobile에서 'card'로 강제.

- **`frontend/app/stocks/[symbol]/page.tsx:382-418`** — L1/L2 탭 네비게이션 `flex space-x-2`, `flex space-x-6` 고정, 스크롤 없음
  ```tsx
  <nav className="flex space-x-2">  {/* L1: 기본정보/뉴스/분석 및 검증 */}
  <nav className="flex space-x-6">  {/* L2: Overview/Balance Sheet/Income Statement/Cash Flow/기타 */}
  ```
  권장: `overflow-x-auto scrollbar-hide` 추가, 또는 `flex-wrap` 처리.

- **`frontend/components/screener/SectorHeatmap.tsx`** — Treemap 높이 `h-96` (384px) 고정, 375px에서 매우 좁아져 타일 터치 불가
  권장: 모바일에서 `h-48` 또는 `h-60`으로 축소, 또는 리스트 뷰 대체.

- **`frontend/app/portfolio/page.tsx:96`** — 헤더 `flex justify-between items-center`, `text-3xl font-bold` 타이틀이 375px에서 버튼과 충돌
  ```tsx
  <h1 className="text-3xl font-bold text-gray-900 dark:text-white">내 포트폴리오</h1>
  <div className="flex space-x-3">  {/* 새로고침 + 종목추가 버튼 */}
  ```
  권장: `text-xl sm:text-3xl` 축소 + `flex-col sm:flex-row` 구조 전환.

- **`frontend/app/chainsight/[symbol]/page.tsx:249`** — Depth 전환 버튼 `px-3 py-1.5` (32px 이하), 필터 버튼 동일
  ```tsx
  <button className={`px-3 py-1.5 ${depth === d ...}`}>{d}</button>
  ```
  권장: `px-3 py-2.5` 이상으로 높이 44px 달성.

### MINOR

- **`frontend/components/screener/AdvancedFilterPanel.tsx:142`** — `text-[10px]` 설명 텍스트 (터치 아님, 가독성 이슈)
  권장: `text-xs`(12px)로 상향.

- **`frontend/components/market-pulse/MoverCard.tsx:107`** — `text-[10px]` 본문 텍스트 다수 (5곳)
  권장: `text-xs`로 상향.

- **`frontend/components/chainsight/MarketGraphCanvas.tsx:698`** — 노드 레이블 `text-[10px]` 모바일 판독 불가
  권장: `text-xs` 최소.

---

## 2. 터치 타겟

### BLOCKER

- **`frontend/app/thesis/new/page.tsx:688`** — 섹션 헤더 `text-[10px]` 인라인 링크 (터치 가능 요소)
  ```tsx
  <a className="text-[10px] text-gray-500 hover:text-blue-400 mt-1 inline-block">
  ```
  권장: `min-h-[44px] flex items-center` 래퍼 또는 `py-3` 패딩 추가.

### MAJOR

- **`frontend/components/thesis/dashboard/IndicatorRow.tsx:178-188`** — 기간 선택 버튼 `px-2.5 py-0.5 text-[10px]` (약 20px 높이)
  ```tsx
  <button className={`px-2.5 py-0.5 text-[10px] rounded transition-colors ...`}>
    {label}
  </button>
  ```
  권장: `py-1.5 text-xs`로 최소 32px, 이상적으로 `py-2.5` (44px).

- **`frontend/components/eod/SignalDetailSheet.tsx:188`** — 뉴스 키워드 필터 태그 `text-[10px] px-1.5 py-0.5 cursor-pointer`
  ```tsx
  <button className="text-[10px] px-1.5 py-0.5 rounded ... cursor-pointer">
  ```
  권장: `py-2 px-3 text-xs`로 터치 영역 확대.

- **`frontend/components/eod/SignalDetailSheet.tsx:197`** — `text-[10px]` 더보기 링크
  ```tsx
  <a className="inline-flex items-center gap-0.5 text-[10px] ... whitespace-nowrap">
  ```
  권장: `text-xs py-2` 최소 적용.

- **`frontend/components/thesis/common/AlertBell.tsx:17`** — 알림 뱃지 `min-w-[18px] h-[18px]` (18px) — 터치 안 됨
  ```tsx
  <span className="... min-w-[18px] h-[18px] px-1 rounded-full ...">
  ```
  권장: 뱃지 자체가 아닌 부모 `Link`가 `p-2 -mr-2`(실제 48px) 처리하고 있어 허용 가능. 단, 뱃지 텍스트 `text-[10px]`는 가독성 MINOR.

- **`frontend/components/eod/SignalFilterTabs.tsx:68`** — 카테고리 카운트 뱃지 `min-w-[18px] h-[18px] text-[11px]`
  ```tsx
  <span className="inline-flex ... min-w-[18px] h-[18px] px-1 rounded-full text-[11px]">
  ```
  권장: 뱃지는 인디케이터이므로 터치 타겟 불필요. 가독성을 위해 `text-xs`(12px)로 상향.

- **`frontend/components/screener/PresetGallery.tsx:241`** — 프리셋 액션 링크 `text-[10px]` 클릭 가능
  ```tsx
  <a className={`flex items-center gap-1 text-[10px] transition-colors ...`}>
  ```
  권장: `text-xs py-2` 적용.

- **`frontend/components/keywords/KeywordTag.tsx:42`** — `sm: 'px-2 py-0.5 text-[10px]'` small 사이즈 키워드 태그 (클릭 가능)
  ```tsx
  sm: 'px-2 py-0.5 text-[10px]',
  ```
  권장: `py-1.5 text-xs`로 상향. `md: 'px-2.5 py-1 text-xs'`는 적합.

- **`frontend/components/chainsight/MarketGraphCanvas.tsx:676`** — 섹터 빠른 접근 버튼 `w-[110px] min-h-[68px]` — 폭이 375px에서 3개 표시 시 110*3+gap = 360px로 아슬아슬
  ```tsx
  'w-[110px] min-h-[68px] px-3 py-2',
  ```
  권장: `flex-wrap` 확보됨, 높이 68px은 HIG 초과로 양호. 폭은 `flex-1 min-w-[100px]` 으로 유동 처리 권장.

### MINOR

- **`frontend/components/thesis/builder/NewsSelector.tsx:142`** — 뒤로가기 버튼 `p-1` (약 28px)
  ```tsx
  <button onClick={onBack} className="p-1 text-gray-400 hover:text-white">
  ```
  권장: `p-2`로 조정.

- **`frontend/components/thesis/builder/OptionButton.tsx:72`** — 숨김 버튼 `p-1 hidden sm:flex`
  ```tsx
  <button className="hidden sm:flex p-1 text-gray-600 hover:text-gray-400 ...">
  ```
  모바일에서 hidden으로 영향 없음. 단, 동일 기능의 모바일 대체 UI 필요할 수 있음.

---

## 3. 네비게이션

### BLOCKER

- **`frontend/components/layout/MobileNav.tsx`** — 5개 항목(홈/종목/뉴스/포트폴리오/내정보)만 포함, 핵심 기능 누락
  ```tsx
  const navItems = [
    { name: '홈', href: '/' },
    { name: '종목', href: '/stocks' },
    { name: '뉴스', href: '/news' },
    { name: '포트폴리오', href: '/portfolio', icon: PieChart },
    { name: '내정보', href: '/profile', icon: User },
  ]
  ```
  누락 항목: Thesis Control(`/thesis`), Chain Sight(`/chainsight`), 스크리너(`/screener`), Market Pulse(`/market-pulse`), AI 분석(`/ai-analysis`). `/profile` 경로는 존재하지 않음(실제 경로는 `/mypage`).
  권장: 핵심 5개 재구성 — 홈/Chain Sight/Thesis/스크리너/더보기(드로어). `/profile` → `/mypage` 수정.

### MAJOR

- **`frontend/components/layout/Header.tsx:156-161`** — 모바일 hamburger 버튼 `p-2 rounded-md` (약 40px), HIG 44px 미달
  ```tsx
  <button
    onClick={() => setIsMenuOpen(!isMenuOpen)}
    className="md:hidden inline-flex items-center justify-center p-2 rounded-md ..."
  >
    <Menu className="h-6 w-6" />
  </button>
  ```
  권장: `p-2.5`로 조정하여 44px 달성.

- **`frontend/components/layout/Header.tsx:165-255`** — 모바일 드롭다운 메뉴 방식 (오버레이 없음, 스크롤 불가)
  `isMenuOpen` 토글로 `div` 펼침. 7개 메뉴 + 검색 + 로그인/아웃이 모두 인라인 드롭다운으로 렌더링되어 375px에서 길어짐.
  권장: Sheet/Drawer 패턴으로 교체, 배경 오버레이 추가, 스크롤 잠금 처리.

- **`frontend/components/layout/MobileNav.tsx`** — 하단 네비 높이 `h-16` (64px), 레이블 `text-xs`, 아이콘 `h-5 w-5`
  터치 타겟 자체는 `flex-1 h-full`으로 충분. 단 아이콘 크기 `h-5`(20px)는 HIG 권장 `h-6`(24px) 미달.
  권장: `<Icon className="h-6 w-6 mb-1" />`로 상향.

- **가상 리스트 없음** — 가설 목록(`/thesis`), 뉴스 목록(`/news`), 스크리너 목록(`/screener`) 등 100개+ 아이템 목록에 `react-window`/`react-virtual` 미적용
  권장: 뉴스 페이지(최대 100건 fetch)와 스크리너(pageSize 50)에 우선 적용. Thesis 목록은 현재 수가 적어 MINOR.

### MINOR

- **`frontend/app/thesis/(list)/layout.tsx`** — `max-w-lg mx-auto px-4 pt-4 pb-20` — `pb-20`(80px)로 MobileNav 겹침 방지 처리됨. 양호.

- **`frontend/app/page.tsx:71`** — `pb-20 md:pb-0` — EOD 대시보드도 하단 패딩 처리됨. 양호.

---

## 4. 차트/그래프

### BLOCKER

- **`frontend/components/chainsight/MarketGraphCanvas.tsx`** — react-force-graph-2d D3 Force 그래프, 모바일에서 `pointer: coarse` 감지 후 롱프레스/탭 처리는 구현됨. 그러나 **핀치줌 비활성화** (`userScalable: false`)로 그래프 확대 불가. 50+ 노드 시 375px 화면에서 노드가 너무 밀집되어 사실상 터치 불가.
  권장: `userScalable: false` 제거, 그래프 내 별도 줌 컨트롤(+/-버튼) 추가.

### MAJOR

- **`frontend/components/screener/SectorHeatmap.tsx`** — `ResponsiveContainer`는 있으나 컨테이너 자체 높이 `h-96` (384px) 고정, Treemap 셀이 375px에서 매우 작아져 `<60px` 조건 미충족 시 텍스트 겹침
  ```tsx
  <div className="rounded-xl border ... p-6">
    <ResponsiveContainer width="100%" height={350}>
      <Treemap ...>
  ```
  권장: `height={isMobile ? 200 : 350}` 동적 처리, 또는 모바일에서 리스트 뷰 대체.

- **`frontend/components/thesis/dashboard/IndicatorRow.tsx:197`** — 차트 `height={160}`, `height={140}` 고정값
  ```tsx
  <ResponsiveContainer width="100%" height={160}>
  <ResponsiveContainer width="100%" height={140}>
  ```
  `ResponsiveContainer` width=100%는 적절. height 고정은 모바일에서 가독성 적합 (160px는 적정). 양호.

- **`frontend/app/ai-analysis/page.tsx:234`** — `h-screen flex flex-col` 레이아웃, 모바일에서 키보드 팝업 시 `h-screen`이 줄어들어 채팅 UI 압축
  권장: `h-[100dvh]` 또는 `h-[calc(100vh-env(keyboard-inset-height,0px))]` 적용.

- **`frontend/components/chainsight/MobileCardList.tsx`** — 모바일 전용 카드 리스트 존재, `/chainsight/[symbol]`에서 `isMobile` 감지 후 렌더링됨. 구조는 적절. 단, `overflow-x-auto` 내부 필터 칩 처리 확인 필요.

### MINOR

- **`frontend/components/news/SentimentChart.tsx`** — `ResponsiveContainer` 사용 확인됨, 모바일 대응 적절.
- **`frontend/components/macro/YieldCurveChart.tsx`** — `ResponsiveContainer` 사용. 양호.
- **`frontend/components/stock/StockChart.tsx`** — `ResponsiveContainer` 사용. 양호.
- **`frontend/components/thesis/dashboard/IndividualMiniCharts.tsx`** — `ResponsiveContainer` 사용. 양호.
- **`frontend/components/validation/MetricBarChart.tsx`** — `ResponsiveContainer` 사용. 양호.

---

## 5. 페이지별 상세

### 5.1 인증 (login, signup)

**`frontend/app/login/page.tsx`**
- 레이아웃: `min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8` — 양호
- 폼 인풋: `py-2` (32px) — 44px 미달 MINOR
- 제출 버튼: `py-2` — 44px 미달 MINOR
- 체크박스: `h-4 w-4` (16px) — 터치 타겟 미달이나 레이블과 묶여 실질 터치 영역 큼, MINOR
- 소셜 버튼 2개: `grid-cols-2 gap-3` — 375px에서 각 약 170px, 터치 가능

**`frontend/app/signup/page.tsx`**
- 유사 구조. `min-h-screen py-12 px-4 sm:px-6` — 양호

### 5.2 대시보드 (page.tsx 메인, dashboard/)

**`frontend/app/page.tsx`** — EOD 대시보드
- `pb-20 md:pb-0` MobileNav 패딩 처리 양호
- `SignalFilterTabs`: `overflow-x-auto pb-1 scrollbar-hide` — 탭 스크롤 가능, 양호
- `SignalDetailSheet`: `flex flex-col justify-end md:justify-center md:items-end` — 모바일 bottom sheet, 데스크톱 side panel. 양호
- 필터 탭 카운트 뱃지 `min-w-[18px] h-[18px] text-[11px]` MINOR (가독성)

**`frontend/app/dashboard/page.tsx`**
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6` — 반응형 적절
- `sm:grid sm:grid-cols-3 sm:gap-4` 패턴 — 모바일에서 단일 컬럼, 양호

### 5.3 Thesis 관제실 (thesis/*)

**`frontend/app/thesis/(list)/page.tsx`** (가설 목록)
- `max-w-lg mx-auto px-4 pt-4 pb-20` — 375px 대응 양호
- Sticky 헤더 처리됨

**`frontend/app/thesis/[thesisId]/page.tsx`** (관제실 대시보드)
- `max-w-lg mx-auto px-4 pt-4 pb-20` — 양호
- IndicatorRow 버튼 `py-0.5 text-[10px]` — MAJOR (위에 기술)
- `min-w-[60px]`, `min-w-[120px]` 고정 폭 — 375px에서 2행이 겹칠 수 있음 MAJOR

**`frontend/app/thesis/new/page.tsx`** (가설 빌더)
- `h-[calc(100dvh-env(safe-area-inset-top))]` — 적절한 모바일 뷰포트 처리
- `text-[10px]` 인라인 링크 BLOCKER (위에 기술)
- `grid grid-cols-1 gap-2 sm:grid-cols-2` — 반응형 처리됨

### 5.4 Chain Sight (chainsight/*)

**`frontend/app/chainsight/page.tsx`** (마켓 뷰)
- `max-w-7xl mx-auto px-4 py-4` — 375px에서 패딩만 유지, 적절
- `SectorBar`: `overflow-x-auto py-3 px-1 scrollbar-thin` — 가로 스크롤 가능
- `RelationFilterChips`: `overflow-x-auto` 처리됨
- `MarketGraphCanvas h-[560px]` 고정 — 375px에서 높이 560px는 스크롤 필요, MINOR
- 빈 상태 섹터 버튼 `w-[110px] min-h-[68px]` 3개 — 375px에서 총 360px(3*110+30 gap) 아슬아슬 MINOR

**`frontend/app/chainsight/[symbol]/page.tsx`** (종목 그래프)
- `isMobile` 감지 후 `MobileCardList` 전환 — 적절한 모바일 분기
- Depth 버튼 `py-1.5` — MAJOR
- 모바일 bottom sheet 노드 상세 패널 `max-h-48` — 적절
- D3 Force 그래프 핀치줌 차단 — BLOCKER

### 5.5 Screener

**`frontend/app/screener/page.tsx`**
- 기본 뷰 `viewMode: 'table'` — 모바일에서 `MobileStockCard`(카드 뷰) 존재하나 기본값 table
  권장: 375px 이하에서 자동 카드 뷰 전환
- `grid grid-cols-1 lg:grid-cols-3` — 모바일 단일 컬럼 적절
- 필터 패널 `AdvancedFilterPanel` — `sm:grid-cols-2` 처리됨
- `PresetGallery` 액션 링크 `text-[10px]` — MAJOR

### 5.6 Validation

**`frontend/components/validation/SignalSummaryCard.tsx`**
- 신호등 `overflow-x-auto pb-2 scrollbar-hide` — 가로 스크롤 가능, 양호
- `min-w-[72px]` 신호등 셀 — 7개 * 72px = 504px, 375px에서 스크롤 필요, 의도적 처리됨

**`frontend/components/validation/LeaderComparisonSection.tsx`**
- `overflow-x-auto` 처리됨

### 5.7 Market Pulse (market-pulse, market-pulse-v2)

**`frontend/app/market-pulse/page.tsx`**
- `sm:px-6 lg:px-8` 반응형 패딩 처리됨
- `grid grid-cols-1 lg:grid-cols-3` — 모바일 단일 컬럼 양호
- `hidden sm:flex`, `hidden sm:block`, `hidden sm:inline` — 모바일 숨김 처리됨
- Market Movers 카드: `text-[10px]` 텍스트 다수 MINOR

**`frontend/app/market-pulse-v2/page.tsx`**
- `max-w-3xl mx-auto pb-12` — 375px 대응 양호
- `grid gap-3 sm:grid-cols-2` — 모바일 단일 컬럼, 적절
- `CardDrawer`: `items-end sm:items-center sm:justify-center` — 모바일 bottom sheet, 양호
- `rounded-t-2xl sm:rounded-2xl` — 모바일 하단 시트 형태, 적절
- footer `text-[10px]` — 디버그용 텍스트, MINOR

### 5.8 News, AI Analysis

**`frontend/app/news/page.tsx`**
- `sm:px-6` 반응형 패딩
- `grid grid-cols-1 lg:grid-cols-3/2` — 모바일 단일 컬럼 양호
- 소스 탭 `flex gap-1` — 375px에서 `all/Finnhub/Marketaux` 3개, 충분
- 시간 필터 버튼들 — `px-3 py-1.5 text-sm` (약 36px) MINOR
- 100개 아이템 목록 가상 리스트 미적용 MAJOR

**`frontend/app/ai-analysis/page.tsx`**
- `h-screen flex flex-col` — dvh 미사용 MAJOR
- 절대 위치 패널 `w-96`, `w-80` — BLOCKER (위에 기술)
- 헤더 버튼들 `hidden sm:inline` 텍스트 숨김 처리 — 모바일에서 아이콘만 표시, 양호
- 채팅 인터페이스 자체는 `flex-1 overflow-hidden` 처리, 양호

### 5.9 Stocks, Portfolio, Watchlist, MyPage, Admin

**`frontend/app/stocks/[symbol]/page.tsx`**
- `sm:px-6 lg:px-8` 반응형 패딩 양호
- `text-4xl` 주가 텍스트 — 375px에서 큰 숫자 줄바꿈 가능, `break-all` 또는 `text-3xl sm:text-4xl` MINOR
- L1/L2 탭 `flex space-x-6` 스크롤 없음 MAJOR
- 재무제표 테이블 `overflow-x-auto` 처리됨 양호
- `grid grid-cols-1 lg:grid-cols-2 gap-6` — 모바일 단일 컬럼 양호

**`frontend/app/portfolio/page.tsx`**
- `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` — 양호
- `text-3xl font-bold` 헤더 + 버튼 수평 배치 — 375px 충돌 MAJOR
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` — 반응형 양호
- 포트폴리오 테이블 `overflow-x-auto` 처리됨

**`frontend/app/watchlist/page.tsx`**
- `overflow-x-auto` 처리됨 양호
- `grid grid-cols-1 lg:grid-cols-3` — 반응형 양호

**`frontend/app/mypage/page.tsx`**
- `max-w-3xl mx-auto px-4 sm:px-6 lg:px-8` — 양호
- `px-6 py-4` 카드 패딩 — 375px 양 사이드 각 24px, 내부 컨텐츠 327px 양호
- 편집/취소/저장 버튼 `px-4 py-2 text-sm` (약 36px) MINOR

**`frontend/app/admin/page.tsx`**
- Admin 페이지는 모바일 최적화 불필요 (관리자 전용)
- `AdminTabNav`: `overflow-x-auto` 처리됨 양호

---

## 6. 권장 우선순위

1. **[BLOCKER] `userScalable: false` 제거** (`app/layout.tsx:33`) — 전체 앱 핀치줌 차단, 접근성 위반. 즉시 수정.

2. **[BLOCKER] AI Analysis 패널 `w-96`/`w-80` 반응형 수정** (`ai-analysis/page.tsx:294,304`) — 모바일에서 뷰포트 오버플로우. `w-full max-w-sm/xs` 또는 bottom drawer 전환.

3. **[BLOCKER] MobileNav 경로 수정 + 핵심 메뉴 재구성** (`MobileNav.tsx`) — `/profile` 존재하지 않는 경로 수정, Thesis Control/Chain Sight 접근 경로 추가.

4. **[BLOCKER] InvestingHeader 모바일 처리** (`InvestingHeader.tsx`) — 현재 미사용이나 사용 시 375px 완전 붕괴. 사용 여부 확인 후 `hidden md:block` 처리 또는 반응형 추가.

5. **[MAJOR] Stocks 상세 페이지 L2 탭 스크롤 처리** (`stocks/[symbol]/page.tsx:402`) — `overflow-x-auto scrollbar-hide` 추가, `whitespace-nowrap` 탭 아이템.

6. **[MAJOR] IndicatorRow 기간 선택 버튼 터치 타겟** (`IndicatorRow.tsx:178`) — `py-0.5` → `py-2` 변경으로 HIG 44pt 달성.

7. **[MAJOR] Portfolio 헤더 텍스트-버튼 충돌** (`portfolio/page.tsx:98`) — `flex-col sm:flex-row` + `text-xl sm:text-3xl` 처리.

8. **[MAJOR] Screener 기본 뷰 모드** (`screener/page.tsx:72`) — `window.innerWidth < 768` 초기값으로 모바일 자동 카드 뷰 전환.

9. **[MAJOR] News/Screener 가상 리스트 적용** — 100건+ 아이템 렌더링 성능 개선. `@tanstack/react-virtual` 권장.

10. **[MAJOR] AI Analysis `h-screen` → `h-[100dvh]`** — 모바일 키보드 팝업 시 레이아웃 압축 방지.
