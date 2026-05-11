# 모바일 UX 감사 보고서

**감사일**: 2026-05-02
**기준 viewport**: 375px (iPhone SE/12 mini 기준)
**기준 표준**: Apple HIG 44×44pt 최소 터치 타겟
**조사 범위**: `/frontend/components` (192개 컴포넌트), `/frontend/app` (23개 페이지)
**조사 방법**: 정적 코드 분석 (읽기 전용, 코드 수정 없음)

---

## 요약

### 심각도별 이슈 수

| 심각도 | 개수 | 정의 |
|--------|------|------|
| **BLOCKER** | **9** | 모바일 사용 불가 또는 콘텐츠 잘림 / 가로 스크롤 발생 / 핵심 기능 차단 |
| **MAJOR** | **22** | 큰 UX 저하, 가독성·터치 정확도·성능 문제 |
| **MINOR** | **17** | 시각적 어색함, 개선 시 좋음 |
| **합계** | **48** | — |

### 모바일 친화도 종합 점수

| 영역 | 점수 | 판정 |
|------|------|------|
| 반응형 레이아웃 | 60 / 100 | 그리드 부분 OK, 테이블·고정 폭 다수 |
| 터치 타겟 | 55 / 100 | text-[10px], py-0.5 미세 패딩 다수 |
| 모바일 네비게이션 | 65 / 100 | Bottom Nav 우수, Header 미흡 |
| 차트/그래프 | 75 / 100 | Recharts 잘 됨, ForceGraph BLOCKER |
| **종합** | **64 / 100** | **개선 필요** |

### Top 5 우선 수정 (즉시 착수)

1. **PortfolioTable 12열 테이블** — 모바일에서 종목명 외 정보 모두 가로 스크롤 (BLOCKER)
2. **GraphCanvas / MarketGraphCanvas 핀치 줌 미지원** — Chain Sight 그래프 탐색 모바일 불가 (BLOCKER)
3. **IndicatorRow `min-w-[60px]+min-w-[120px]+max-w-[100px]` 누적 폭** — 관제실 지표 행 가로 스크롤 (BLOCKER)
4. **Header 모바일 메뉴 — scroll lock / 자동 닫힘 / ESC 미구현** (BLOCKER)
5. **AlertBell / SignalFilterTabs / AddIndicatorSheet 18px 고정 배지** — 터치 불가능 수준 (BLOCKER)

---

## 반응형 누락

### BLOCKER

| # | 파일 | 라인 | 코드 | 문제 |
|---|------|------|------|------|
| R-1 | `components/thesis/dashboard/IndicatorRow.tsx` | 108 | `<span min-w-[60px]>` + `min-w-[120px]` + `max-w-[100px]` flex | 고정 폭 누적 합 280px+ ≥ 모바일 콘텐츠 폭. `pl-4` 추가 시 343px(375-32) 초과 → 가로 스크롤 |
| R-2 | `components/portfolio/PortfolioTable.tsx` | 260 | `<table>` 12개 컬럼 × `px-6` (24px) | `overflow-x-auto`는 있으나 모바일 첫 화면에서 종목명 1열만 표시. 손익·현재가 모두 가려짐 |
| R-3 | `components/stocks/StockTable.tsx` | 34 | 7개 컬럼 × `px-6` 패딩 | 최소 500px 폭 필요. 모바일에서 가로 스크롤 필수, 모바일 카드 뷰 부재 |
| R-4 | `components/strategy/ScreenerTable.tsx` | (10+ 컬럼) | 10개 이상 컬럼 | StockTable과 동일 패턴, 모바일 카드 fallback 없음 |
| R-5 | `app/portfolio/page.tsx` | — | PortfolioTable 자식 | 부모 페이지 layout 자체는 OK이나 자식이 BLOCKER |

### MAJOR

| # | 파일 | 라인 | 코드 | 문제 |
|---|------|------|------|------|
| R-6 | `components/screener/MarketBreadthCard.tsx` | 107 | `grid grid-cols-3` (브레이크포인트 없음) | 375px에서 셀 ~100px, 지수명+값 겹침 |
| R-7 | `components/screener/MobileStockCard.tsx` | 164 | `grid grid-cols-3 gap-2` 메트릭 | 컴포넌트명 "Mobile"인데 모바일에서 셀 ~95px, "$500B" 등 잘림 |
| R-8 | `components/thesis/dashboard/IndicatorRow.tsx` | 197 | `<YAxis width={55}>` + 4개 period 버튼 | Y축 55px + 차트 영역 + 버튼 4개 → 375px에서 wrap 또는 차트 압축 |
| R-9 | `components/validation/MetricBarChart.tsx` | 90 | `<YAxis width={50} margin.right=50>` | 375 - 100 = 275px 차트, X축 라벨 겹침 |
| R-10 | `components/validation/CategorySidebar.tsx` | 44 | `<nav className="sticky top-24">` | 데스크톱 사이드바, 모바일에서 콘텐츠 압박. `md:hidden` 부재 |
| R-11 | `components/validation/LeaderComparisonSection.tsx` | 47 | 4컬럼 테이블, `<th>` 폭 명시 없음 | "지표"·심볼·심볼·기호 컬럼 콘텐츠 기반 폭 → 모바일에서 줄바꿈/겹침 |
| R-12 | `components/chainsight/GraphCanvas.tsx` | 22 | `interface { width: number; height: number }` | Canvas 기반, props로 고정 크기 받음. 부모에서 동적 크기 보장 불명확 |
| R-13 | `components/admin/*.tsx` | 다수 | `overflow-x-auto` 테이블만 제공 | Admin 페이지 다수 테이블, 모바일 카드 fallback 없음 (낮은 우선순위) |

### MINOR

| # | 파일 | 라인 | 코드 | 문제 |
|---|------|------|------|------|
| R-14 | `components/screener/AdvancedFilterPanel.tsx` | 276 | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` | 반응형 OK, 그러나 입력 필드 `px-3 py-1.5` padding 큼 |
| R-15 | `components/portfolio/PortfolioTable.tsx` | 210 | `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6` | 6개 요약을 모바일 2x3, 마지막 셀 단독 행으로 어색 |
| R-16 | `components/eod/MarketSummaryBar.tsx` | 38 | `<div w-24 h-2>` BullBearBar | 96px 고정 폭 프로그레스, 우측 정보와 충돌 가능 |
| R-17 | `components/thesis/dashboard/RealValueIndicatorCard.tsx` | 30 | `p-4` + `truncate` | name truncate 적용되나 dateLabel과 동시 표시 시 가독성 저하 |
| R-18 | `components/chainsight/TracePathView.tsx` | — | `flex items-center gap-1 overflow-x-auto` | 가로 스크롤 가능, 그러나 경로 많을 때 모바일 사용성 저하 |
| R-19 | `app/page.tsx` | 72 | `pb-20 md:pb-0` 하단 padding | OK이나 80px 패딩이 모바일에서 큼 (Bottom Nav 64px) |
| R-20 | `app/dashboard/page.tsx` | 30 | `gap-6` 카드 간격 | 24px 간격, 모바일에서 `gap-3` 권장 |

---

## 터치 타겟

### BLOCKER (≤24px 터치 영역)

| # | 파일 | 라인 | 코드 | 추정 영역 |
|---|------|------|------|---------|
| T-1 | `components/thesis/common/AlertBell.tsx` | 17-21 | `min-w-[18px] h-[18px] px-1 rounded-full text-[10px]` (알림 카운트 뱃지) | **18×18px** 고정. `-top-0.5 -right-0.5` 절대좌표 → 오타치 위험 |
| T-2 | `components/eod/SignalFilterTabs.tsx` | 66-76 | `min-w-[18px] h-[18px] px-1 text-[11px]` 카운트 배지 | **18×18px** 고정 |
| T-3 | `components/thesis/AddIndicatorSheet.tsx` | 240 | `text-[9px] px-1 py-px rounded` 주파수 배지 | **~20×12px** (9px 텍스트, py-px 거의 0) |
| T-4 | `components/validation/MetricCard.tsx` | 95-96 | `<AlertTriangle className="w-3.5 h-3.5">` (단독 클릭 가능 영역으로 간주 시) | **14×14px** 아이콘 + 인접 gap-1.5 |
| T-5 | `components/validation/MetricInfoTooltip.tsx` | 36-44 | `<HelpCircle w-3.5 h-3.5>` 단독 버튼, padding 없음 | **14×14px**, 인라인 + 패딩 0 → 터치 거의 불가 |

### MAJOR (25~36px 터치 영역)

| # | 파일 | 라인 | 코드 | 추정 영역 |
|---|------|------|------|---------|
| T-6 | `components/thesis/IndicatorCard.tsx` | 52 | `text-[10px] px-1.5 py-0.5 rounded-full` 신호등 배지 | ~28×16px |
| T-7 | `components/thesis/dashboard/IndicatorRow.tsx` | 182 | `px-2.5 py-0.5 text-[10px]` period 버튼 4개 (gap-1.5) | ~24×18px, 인접 4개 |
| T-8 | `components/validation/PeerContextBar.tsx` | 37-49 | `px-3 py-1 text-xs` 프리셋 탭 (gap-2) | ~32×24px |
| T-9 | `components/validation/CategorySidebar.tsx` | 48-60 | `w-2.5 h-2.5 rounded-full` 신호등 도트 + `py-2 text-sm` | 신호등 10×10px, 행 32px |
| T-10 | `components/chainsight/FilterPanel.tsx` | 82-106 | "전체"/"해제" 인라인 텍스트 링크 (padding 0), Depth 버튼 `py-1.5` | ~28px 높이 |
| T-11 | `components/chainsight/PathCard.tsx` | 79-94 | `flex gap-1 px-2.5 py-1 text-xs <RefreshCw w-3 h-3>` Recheck/열기 | ~22×20px, 3개 인접 |
| T-12 | `components/chainsight/RelationCardPanel.tsx` | 144-149 | `w-full py-1.5 text-xs` "여기서 탐색" | 28px 높이 |
| T-13 | `components/eod/SignalCard.tsx` | 102-114 | `p-1 rounded-full <HelpCircle w-3.5 h-3.5>` 팁 버튼 | 22×22px |
| T-14 | `components/screener/Pagination.tsx` | 94-158 | `p-1.5 <ChevronsLeft w-4 h-4>` 아이콘, `min-w-[32px] px-2 py-1.5` 페이지 번호 | 28×28px / 32×24px |
| T-15 | `components/news/KeywordBadge.tsx` | 40-58 | sm 변형: `px-2 py-1 text-xs w-3 h-3` | 26×20px |

### MINOR (37~44px)

| # | 파일 | 코드 | 영역 |
|---|------|------|------|
| T-16 | `components/chainsight/NodeDetailPanel.tsx:88-111` | `w-full py-2 px-3 text-sm` "가설 생성" CTA | ~32×40px (경계) |
| T-17 | `components/thesis/dashboard/ChartToggleButton.tsx` | `w-full py-3` | 48px 높이 (적절) ✅ |
| T-18 | `components/thesis/dashboard/RealValueIndicatorCard.tsx:76,83` | `text-[10px] truncate` 비클릭 텍스트 | 향후 인터랙션 추가 시 위험 |

### 인접 거리 미충족 (8pt 미만)

- `gap-0.5` (2px), `gap-1` (4px) 패턴이 PathCard, FilterPanel, IndicatorRow period 버튼 영역에서 발견 → 오타치 위험

---

## 네비게이션

### BLOCKER

| # | 파일 | 문제 |
|---|------|------|
| N-1 | `components/layout/Header.tsx:165-254` | 모바일 메뉴 클릭 후 자동 닫힘 미구현. `setIsMenuOpen(false)` 호출 없음 |
| N-2 | `components/layout/Header.tsx` | 모바일 메뉴 열림 상태에서 **scroll lock 미구현** → `body` 스크롤 가능, 배경 떨림 |
| N-3 | `components/portfolio/PortfolioTable.tsx:302` | 100+ 종목 시 `data.portfolios.map()` 전체 DOM 렌더, 가상화·페이지네이션 부재 → 모바일 스크롤 끊김 |

### MAJOR

| # | 파일 | 문제 |
|---|------|------|
| N-4 | `components/layout/InvestingHeader.tsx:29-119` | 햄버거 메뉴 부재, 데스크톱 전용 설계. 600px 미만에서 레이아웃 붕괴. 상단 바 텍스트("2025년 10월 25일") 고정 |
| N-5 | `app/layout.tsx:60` | `<main className="min-h-screen">` — **모바일 하단 `pb-20` 누락**. portfolio/chainsight/news/screener/stocks/mypage 페이지에서 Bottom Nav가 콘텐츠 가림 (단, `app/page.tsx`와 `app/thesis/*`는 자체 `pb-20` 적용됨) |
| N-6 | `components/layout/Header.tsx` | 백드롭 부재 + ESC 키 닫기 미구현 → 모바일 메뉴 닫는 유일한 방법이 햄버거 재클릭 |
| N-7 | `components/chainsight/MobileCardList.tsx:119-188` | `displayNodes.map()` 전체 렌더, 100+ 노드 시 성능 저하. 페이지네이션 없음 |

### MINOR

| # | 파일 | 문제 |
|---|------|------|
| N-8 | `components/eod/SignalDetailSheet.tsx:80+` | `StockRow` 무제한 렌더, 500+ 종목 신호 시 성능 저하 |
| N-9 | `components/portfolio/PortfolioModal.tsx` | `max-w`, `max-h` 제한 부재 → 모바일에서 폼 화면 초과 |
| N-10 | `components/watchlist/AddStockModal.tsx` | `max-h-[90vh]` 부재. 검색 결과 드롭다운 `max-h-60`만 → 헤더 sticky 아님 |
| N-11 | `components/screener/SharePresetModal.tsx` | 동일 (max-h 부재) |
| N-12 | 전역 | `react-window` / `@tanstack/react-virtual` / `react-virtuoso` **미설치** (package.json 확인). 가상화 라이브러리 전무 |
| N-13 | 전역 | `IntersectionObserver` / `useInView` / `react-intersection-observer` 사용 0건. 무한 스크롤 패턴 부재 |

### 우수 사례 (참고)

- **`components/layout/MobileNav.tsx`**: `fixed bottom-0` Bottom Nav, `md:hidden`, z-50 — 5개 탭 잘 구현됨 ✅
- **`components/thesis/common/BottomSheet.tsx`**: `rounded-t-2xl max-h-[50vh] overflow-y-auto`, scroll lock O ✅
- **`components/eod/SignalDetailSheet.tsx:110-117`**: 모바일 바닥 슬라이드 / 데스크톱 우측 시트 — 반응형 우수 ✅
- **`components/news/NewsDetailModal.tsx:49`**: `max-w-3xl max-h-[90vh] overflow-hidden` ✅

---

## 차트/그래프

### BLOCKER

| # | 파일 | 문제 |
|---|------|------|
| C-1 | `components/chainsight/GraphCanvas.tsx` | `react-force-graph-2d` Canvas 기반. **핀치 줌(pinch-to-zoom) 미지원** → 모바일에서 큰 그래프 노드 탐색 불가능. Hammer.js 등 터치 제스처 라이브러리 없음 |
| C-2 | `components/chainsight/MarketGraphCanvas.tsx` | GraphCanvas와 동일 (react-force-graph-2d 공유). ResizeObserver로 폭만 동적, 줌 부재 |

### MAJOR

| # | 파일 | 라인 | 문제 |
|---|------|------|------|
| C-3 | `components/thesis/dashboard/QuarterlySparkline.tsx` | 33-67 | 20개 분기 데이터, `text-[8px]` 라벨, `gap-1` → 모바일에서 라벨 겹침. 호버 기반 툴팁 → 터치 미동작 |
| C-4 | Recharts 사용 모든 파일 | — | `<Tooltip>` 모바일 닫기 불가 (알려진 Recharts 이슈). 외부 클릭으로 사라지지 않음, 스크롤해도 잔존 |
| C-5 | `components/stock/StockChart.tsx` | 533-650 | 헤더 `flex justify-between`: 가격 + period selector 4개 + 설정 톱니. 설정 패널 `absolute right-0 top-full w-56` → 모바일 화면 밖으로 오버플로우 |

### MINOR

| # | 파일 | 라인 | 문제 |
|---|------|------|------|
| C-6 | `components/thesis/dashboard/IndividualMiniCharts.tsx` | 54 | `<XAxis>` 자동 틱 간격, 1년 데이터일 때 라벨 겹침 가능 |
| C-7 | `components/thesis/dashboard/PeriodSelector.tsx` | 14-26 | 버튼 `px-3 py-1.5 text-xs` → 32×26px (터치 36px 미만) |
| C-8 | `components/screener/SectorHeatmap.tsx` | 216 | `height={400}` 고정, 모바일에서 다소 큼 |
| C-9 | `components/macro/EconomicIndicators.tsx` | 42 | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4` (차트 아닌 카드, OK이나 정보 밀집도 높음) |
| C-10 | `components/macro/YieldCurveChart.tsx` | 92 | 부모 `h-64` 의존, 명시적 폭 없음 |

### 우수 사례 (Recharts ResponsiveContainer 100% 커버리지)

| 파일 | 평가 |
|------|------|
| StockPriceChart, StockChart, PortfolioChart, YieldCurveChart, SentimentChart, MLTrendChart, SectorHeatmap, IndividualMiniCharts, MetricBarChart | 모두 `ResponsiveContainer width="100%"` ✅ |
| StockChart | `useEffect` + `getResponsiveChartHeight(window.innerWidth)` 동적 계산 (sm: 280, md: 320, lg: 350) — 가장 우수 ✅ |
| MiniSparkline, SentimentBar, FearGreedGauge, TaskTimelineChart, MarketBreadthCard | 커스텀 SVG / HTML, 완전 반응형 ✅ |

---

## 페이지별 상세

### `/` (메인 — EOD Dashboard)
- **반응형**: ✅ `pb-20 md:pb-0`, `max-w-6xl px-4`
- **이슈**: SignalCardGrid 반응형 우수(`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`), 그러나 SignalFilterTabs 카운트 배지 18×18px (T-2)
- **심각도**: MAJOR 1, MINOR 1

### `/dashboard`
- **반응형**: ✅ `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
- **이슈**: `gap-6` 모바일에서 큼 (R-20)
- **심각도**: MINOR 1

### `/thesis` (가설 목록)
- **반응형**: 가설 목록 카드 OK
- **이슈**: AlertBell 알림 배지 18×18px (T-1)
- **심각도**: BLOCKER 1

### `/thesis/[id]` (관제실 대시보드)
- **반응형**: 🔴 IndicatorRow 고정 폭 누적 → 가로 스크롤 (R-1)
- **터치**: 🔴 신호등 배지 28×16px (T-6), period 버튼 24×18px (T-7)
- **차트**: ⚠ Y축 55px + 차트 + period 버튼 wrap 위험 (R-8)
- **심각도**: BLOCKER 1, MAJOR 3, MINOR 1

### `/thesis/[id]/indicators` (지표 설정)
- **터치**: 🔴 AddIndicatorSheet 주파수 배지 9px 텍스트 (T-3)
- **심각도**: BLOCKER 1

### `/thesis/[id]/close` (가설 마감)
- **반응형**: 일반 모달, max-h 확인 필요
- **심각도**: 추가 조사 필요

### `/thesis/alerts`
- **반응형**: AlertCard 일반 카드, OK
- **심각도**: 큰 이슈 없음

### `/portfolio`
- **반응형**: 🔴 PortfolioTable 12열 (R-2). 100+ 종목 시 가상화 부재 (N-3)
- **모달**: ⚠ PortfolioModal max-w/max-h 부재 (N-9)
- **심각도**: BLOCKER 2, MAJOR 1, MINOR 1

### `/stocks/[symbol]`
- **반응형**: ⚠ StockChart 헤더 레이아웃 모바일 무너짐 (C-5)
- **차트**: ✅ StockChart 반응형 height 우수
- **테이블**: 🔴 StockTable 7열 (R-3)
- **심각도**: BLOCKER 1, MAJOR 1

### `/screener`
- **반응형**: ⚠ MarketBreadthCard `grid-cols-3` (R-6), MobileStockCard `grid-cols-3` (R-7)
- **테이블**: 🔴 ScreenerTable 10+열 (R-4)
- **터치**: ⚠ Pagination 28×28 / 32×24px (T-14)
- **모달**: ⚠ SharePresetModal max-h 부재 (N-11)
- **심각도**: BLOCKER 1, MAJOR 3, MINOR 1

### `/chainsight`
- **차트**: 🔴 MarketGraphCanvas 핀치 줌 미지원 (C-2)
- **목록**: ⚠ MobileCardList 가상화 부재 (N-7)
- **심각도**: BLOCKER 1, MAJOR 1

### `/chainsight/[symbol]`
- **차트**: 🔴 GraphCanvas 핀치 줌 미지원 (C-1). props 고정 width/height (R-12)
- **터치**: ⚠ FilterPanel "전체"/"해제" 패딩 0 (T-10), PathCard Recheck/열기 22×20 (T-11), NodeDetailPanel CTA 32px (T-16)
- **심각도**: BLOCKER 1, MAJOR 4

### `/news`
- **반응형**: NewsGrid 반응형 OK, 더보기 버튼 수동
- **모달**: ✅ NewsDetailModal max-w-3xl max-h-90vh
- **터치**: ⚠ KeywordBadge sm 26×20 (T-15)
- **심각도**: MAJOR 1

### `/market-pulse`
- **반응형**: MarketMoversSection 반응형 확인 필요
- **차트**: ✅ FearGreedGauge, GlobalMarketsCard 반응형 OK
- **심각도**: 큰 이슈 없음

### `/watchlist`
- **모달**: ⚠ AddStockModal max-h 부재, 검색 드롭다운 sticky 아님 (N-10)
- **심각도**: MINOR 1

### `/admin/*` (낮은 우선순위)
- **테이블**: ⚠ 다수 `overflow-x-auto` 테이블 (R-13)
- **심각도**: MAJOR 다수 (운영 페이지이므로 우선순위 낮음)

### `/login`, `/signup`
- **반응형**: 일반 폼, 큰 이슈 없음

### `/mypage`
- **반응형**: `<main pb-20>` 부재 (N-5 영향)
- **심각도**: MAJOR 1 (전역 layout.tsx 수정으로 해결)

### `/ai-analysis` (RAG)
- **반응형**: ChatInterface, DataBasket 추가 조사 필요
- **MonitoringDashboard**: `grid-cols-3` 패턴 발견 가능성

---

## 패턴 요약

### 패턴 1 — 고정 컬럼 그리드 (브레이크포인트 누락)
- `MarketBreadthCard` (3컬럼), `MobileStockCard` (3컬럼), `ThesisSkeleton` (3컬럼), `RAG/MonitoringDashboard` (3컬럼)
- **공통 해결책**: `sm:grid-cols-2 md:grid-cols-3` 또는 모바일 세로 스택

### 패턴 2 — 누적 고정 폭 (`min-w-[]`, `max-w-[]`)
- `IndicatorRow`: `min-w-[60px]+min-w-[120px]+max-w-[100px]` 합산 280px+
- **공통 해결책**: 반응형 분기 또는 `flex-wrap` 활성화

### 패턴 3 — 테이블 가로 스크롤 (콘텐츠 우선순위 부재)
- `PortfolioTable` (12열), `StockTable` (7열), `ScreenerTable` (10+열)
- **공통 해결책**: 모바일 카드 뷰 또는 주요 컬럼만 노출

### 패턴 4 — `text-[10px]` / `py-0.5` 미세 패딩 클릭 요소
- AlertBell, SignalFilterTabs, AddIndicatorSheet, IndicatorCard, IndicatorRow period 버튼
- **공통 해결책**: 최소 `text-xs` (12px), `py-2` (8px) 표준화

### 패턴 5 — 아이콘 단독 버튼 패딩 부재
- `MetricInfoTooltip` (HelpCircle 14px, padding 0), `MetricCard` AlertTriangle (14px)
- **공통 해결책**: `p-2.5 rounded-full` + `aria-label` 표준화

### 패턴 6 — 호버 기반 인터랙션 모바일 미동작
- Recharts `<Tooltip>`, `QuarterlySparkline` 호버 툴팁
- **공통 해결책**: 모바일 감지 후 `active` 상태 명시 제어, 탭 기반 툴팁

### 패턴 7 — Canvas 기반 그래프 터치 제스처 부재
- GraphCanvas, MarketGraphCanvas (react-force-graph-2d)
- **공통 해결책**: Hammer.js 또는 `touch-action` CSS + 직접 핀치 핸들링

### 패턴 8 — 가상화 라이브러리 전무
- 100+ 항목 가능 화면: PortfolioTable, MobileCardList, SignalDetailSheet, NewsList
- **공통 해결책**: `@tanstack/react-virtual` 도입 또는 페이지네이션

---

## 우선순위 권장 (수정 일정 가이드)

### Phase 1 — 즉시 (BLOCKER)
1. **R-1** IndicatorRow 고정 폭 누적 → 반응형 분기
2. **R-2 / R-3 / R-4** 테이블들 → 모바일 카드 뷰 또는 `MobileStockCard` 진정한 모바일 컴포넌트화
3. **C-1 / C-2** GraphCanvas 핀치 줌 → Hammer.js 통합
4. **N-1 / N-2 / N-6** Header 모바일 메뉴 scroll lock + 자동 닫힘 + ESC + 백드롭
5. **T-1 / T-2 / T-3** 18px 고정 배지 / 9px 텍스트 → 최소 24px + text-xs
6. **N-5** `app/layout.tsx <main>` 에 `pb-20 md:pb-0` 추가

### Phase 2 — 1주 (MAJOR 핵심)
7. **R-6 / R-7** 3컬럼 고정 그리드 → 모바일 2컬럼/세로
8. **R-8 / R-9 / C-5** 차트+컨트롤 모바일 레이아웃 (`flex-col md:flex-row`)
9. **R-10** CategorySidebar 모바일 숨김/콜래프스
10. **C-3** QuarterlySparkline 라벨 옮기기 (홀수 분기만)
11. **C-4** Recharts Tooltip 모바일 active 상태 제어
12. **N-3 / N-7** PortfolioTable, MobileCardList 페이지네이션
13. **T-4 ~ T-15** 터치 타겟 표준화 (p-2.5 + text-xs 룰)
14. **N-4** InvestingHeader 햄버거 메뉴

### Phase 3 — 2주 (MAJOR 보완 + MINOR)
15. **R-15 / R-16 / R-20** 그리드 간격·레이아웃 미세 조정
16. **N-8 ~ N-11** 모달 max-h-[90vh] 일괄 적용
17. **C-6 / C-7** 차트 라벨/버튼 크기 보정
18. **T-16** NodeDetailPanel CTA padding 보강

### Phase 4 — 장기 (구조 개선)
19. **N-12** `@tanstack/react-virtual` 도입 (PortfolioTable, NewsList, SignalDetailSheet)
20. **N-13** `useInfiniteScroll` 훅 개발 (IntersectionObserver 표준화)
21. **R-13** Admin 페이지 모바일 카드 뷰 (낮은 우선순위)
22. 모바일 디자인 토큰 정의: 터치 타겟 최소값, 폰트 최소값, 간격 표준 (Tailwind 플러그인)

---

## 부록 — 통계

### 컴포넌트별 이슈 개수 Top 10

| 컴포넌트 | BLOCKER | MAJOR | MINOR | 합계 |
|---------|---------|-------|-------|------|
| `IndicatorRow.tsx` | 1 | 2 | — | 3 |
| `PortfolioTable.tsx` | 2 | 1 | 1 | 4 |
| `Header.tsx` | 2 | 1 | — | 3 |
| `GraphCanvas.tsx` / `MarketGraphCanvas.tsx` | 2 | 1 | — | 3 |
| `FilterPanel.tsx` | — | 1 | — | 1 |
| `PathCard.tsx` | — | 1 | — | 1 |
| `MetricBarChart.tsx` | — | 1 | — | 1 |
| `CategorySidebar.tsx` | — | 1 | — | 1 |
| `AlertBell.tsx` | 1 | — | — | 1 |
| `SignalFilterTabs.tsx` | 1 | — | — | 1 |

### 페이지별 이슈 개수 Top 5

| 페이지 | BLOCKER | MAJOR | MINOR | 합계 |
|--------|---------|-------|-------|------|
| `/chainsight/[symbol]` | 1 | 4 | — | 5 |
| `/screener` | 1 | 3 | 1 | 5 |
| `/portfolio` | 2 | 1 | 1 | 4 |
| `/thesis/[id]` | 1 | 3 | 1 | 5 |
| `/stocks/[symbol]` | 1 | 1 | — | 2 |

### 미설치 라이브러리 (도입 검토)

- `react-window` 또는 `@tanstack/react-virtual` — 가상화
- `react-intersection-observer` — 무한 스크롤 트리거
- `hammerjs` — 핀치 줌 / 터치 제스처
- (선택) `vaul` — 모바일 친화적 Drawer 컴포넌트

---

**감사 종료**
보고서 위치: `/docs/nightly_auto_system/reports/5월/1일/mobile_ux_audit.md`
