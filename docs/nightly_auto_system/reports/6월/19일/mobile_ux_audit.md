# 모바일 UX 감사 보고서

> 감사 대상: `/Users/byeongjinjeong/Desktop/stock_vis/frontend`
> 기준 뷰포트: **모바일 375px** (iPhone SE/표준 모바일)
> 기준: Apple HIG 터치 타겟 44×44pt
> 방식: 정적 코드 분석 (읽기 전용, 코드 수정 없음)
> 범위: 210개 컴포넌트 + 33개 페이지 전수
> 작성일: 2026-06-19

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 정의 |
|--------|------|------|
| 🔴 **BLOCKER** | **7** | 모바일에서 콘텐츠/기능 사용 불가 (오버플로우, 메뉴 호출 불가) |
| 🟠 **MAJOR** | **28** | 명백한 사용 불편, 일부 잘림, 터치 타겟 미달, 가독성 저하 |
| 🟡 **MINOR** | **15** | 경미한 개선 권장 사항 |

### BLOCKER 7건 한눈에 보기

| # | 컴포넌트 | 문제 | 파일:라인 |
|---|----------|------|-----------|
| B1 | `Header` | 햄버거 메뉴 버튼이 `hidden` 처리 → 모바일에서 메뉴 호출 불가 | `layout/Header.tsx:157` |
| B2 | `MarketGraphCanvas` | 그래프 고정 높이 `h-[560px]` → 375px 화면의 92% 점유 + 주변 오버플로우 | `chainsight/MarketGraphCanvas.tsx:603,712,760` |
| B3 | `MarketGraphCanvas` | 인기 섹터 버튼 `w-[110px]`×3 = 330px+ → 수평 스크롤 | `chainsight/MarketGraphCanvas.tsx:676` |
| B4 | `ScreenerTable` | 12컬럼 테이블, 모바일 카드 분기 없음 → 각 셀 ~30px 텍스트 손상 | `strategy/ScreenerTable.tsx:127` |
| B5 | `PortfolioTable` | 12컬럼 테이블, `overflow-x-auto`만 존재, 모바일 레이아웃 없음 | `portfolio/PortfolioTable.tsx:259` |
| B6 | Coach E1~E6 | 입력폼 `grid-cols-12` 6필드 가로 배치, 모바일 stacking 없음 | `app/coach/e1~e6/page.tsx` |
| B7 | `QuarterlySparkline` | 분기 막대 터치 타겟 + 라벨 가독성 부족 | `thesis/dashboard/QuarterlySparkline.tsx:42` |

### 핵심 패턴 (전역 통계)

| 항목 | 수치 | 평가 |
|------|------|------|
| `text-[10px]` / `text-[11px]` 사용처 | **131회** | 🟠 모바일 가독성 저하, 일부 클릭 요소 포함 |
| 고정 픽셀 폭(`w-[Npx]` 류) 사용 파일 | 43개 / 67회 | 🟠 다수가 모바일 분기 없음 |
| `ResponsiveContainer` (Recharts) 사용 | 16개 파일 / 51회 | ✅ 차트 반응형 폭은 대체로 양호 (높이 고정이 문제) |
| `overflow-x` (가로 스크롤 처리) | 34개 파일 | 🟡 존재하나 일부 scrollbar 최적화 누락 |
| Virtualization 라이브러리 (react-window 등) | **0개** | 🟡 긴 목록(뉴스 100건, 시그널 종목) 전부 일괄 렌더 |
| viewport meta 태그 | ✅ 설정됨 | `app/layout.tsx:29` (device-width, viewportFit: cover) |

---

## 1. 반응형 누락

### 1.1 테이블 — 모바일 카드 분기 부재 (최다 BLOCKER)

| 심각도 | 컴포넌트 | 컬럼 수 | 처리 현황 | 파일:라인 |
|--------|----------|---------|-----------|-----------|
| 🔴 BLOCKER | `ScreenerTable` | 12 (종목·거래소·섹터·가격·변동률·시총·거래량·배당·베타·유형·키워드·액션) | `overflow-x-auto`만, 모바일 분기 없음 | `strategy/ScreenerTable.tsx:127` |
| 🔴 BLOCKER | `PortfolioTable` | 12 (종목·수량·평단·현재가·전일대비·평가금액·손익·수익률·목표가·손절가·비중·관리) | `overflow-x-auto`만 | `portfolio/PortfolioTable.tsx:259` |
| 🟠 MAJOR | `LeaderComparisonSection` | 4 + 중첩 테이블 | `overflow-x-auto`, 카드 분기 없음 | `validation/LeaderComparisonSection.tsx:47` |

- **공통 문제**: `overflow-x-auto`는 가로 스크롤을 허용할 뿐, 375px에서 셀당 폭이 30~90px로 줄어 텍스트가 손상되거나 잘림. 가로 스크롤은 모바일에서 발견성·사용성이 매우 낮음.
- **주목**: `screener/MobileStockCard.tsx`라는 모바일 전용 카드 컴포넌트가 **이미 존재하나 `ScreenerTable`에서 미사용**. 분기 연결만으로 B4 해소 가능.

### 1.2 그래프/캔버스 고정 높이

| 심각도 | 컴포넌트 | 코드 | 영향 | 파일:라인 |
|--------|----------|------|------|-----------|
| 🔴 BLOCKER | `MarketGraphCanvas` | `h-[560px]` | 375px 화면의 92% 점유, 섹터바·필터칩·트레일과 겹쳐 오버플로우 | `chainsight/MarketGraphCanvas.tsx:603,712,760` |
| 🟠 MAJOR | `SectorHeatmap` | `<ResponsiveContainer height={400}>` | 375px×400px → 1:1 이상 세로 직사각형, Treemap 비율 붕괴 | `screener/SectorHeatmap.tsx:216` |
| 🟠 MAJOR | `MetricBarChart` | `h-48` (192px) + `margin right:50` + `YAxis width=50` | 데이터 영역이 13% 잠식되어 극히 좁음 | `validation/MetricBarChart.tsx:72,79` |

> 그래프의 **폭**은 ResizeObserver/ResponsiveContainer로 반응하나, **높이가 고정 px**라 모바일에서 비율이 깨짐. 모바일 breakpoint별 높이(`h-[300px] md:h-[560px]` 식) 부재가 공통 원인.

### 1.3 고정 폭 버튼/그리드

| 심각도 | 컴포넌트 | 코드 | 영향 | 파일:라인 |
|--------|----------|------|------|-----------|
| 🔴 BLOCKER | `MarketGraphCanvas` 인기 섹터 | `w-[110px]`×3 + `gap-3` | 366px+ 필요 → 수평 스크롤 | `chainsight/MarketGraphCanvas.tsx:676` |
| 🔴 BLOCKER | Coach E1~E6 폼 | `grid-cols-12` 6필드 가로 | 입력칸 illegible, 모바일 stacking 없음 | `app/coach/e1:150,e2:164,e3:178,e5:201,e6:181` |
| 🟠 MAJOR | `PresetGallery` | `grid-cols-2 md:grid-cols-3...` | 375px에서 카드 ~168px, 내부 3~4줄 텍스트 붕괴 | `screener/PresetGallery.tsx:355,380,405,430` |
| 🟠 MAJOR | `QuickAddDropdown` | `w-80` (320px) 고정 | 375px에서 패딩 포함 화면 밖 침범 | `financial/QuickAddDropdown.tsx:197` |
| 🟠 MAJOR | `SectorBar` 버튼 | 텍스트만 `max-w-[120px]`, 버튼 자체 무제한 | 섹터명+수익률이 폭 초과 → 스크롤바 | `chainsight/SectorBar.tsx:41` |
| 🟠 MAJOR | `IndicatorRow` | `min-w-[60px]`/`min-w-[120px]`/`max-w-[100px]` flex row | 지표 다수 시 가로 오버플로우 | `thesis/dashboard/IndicatorRow.tsx:110,115,132` |
| 🟠 MAJOR | `MoverCard` | `flex gap-3 p-3` 5지표 2줄 | 375px에서 지표 겹침/잘림 | `market-pulse/MoverCard.tsx:82` |
| 🟡 MINOR | `RecommendationCard` | `max-w-[150px] truncate` 회사명 | 375px의 40% 점유, 다소 넉넉 | `news/RecommendationCard.tsx:85` |
| 🟡 MINOR | `AINewsBriefingCard` | `max-w-[200px]` 중요도 바 | 모바일 폭 계산 부재 | `news/AINewsBriefingCard.tsx:70` |
| 🟡 MINOR | `SuggestionChips` | `max-w-[150px] truncate` 이유 | 모바일에서 글자 수 과소 | `rag/SuggestionChips.tsx:40` |

---

## 2. 터치 타겟 (Apple HIG 44×44pt 기준)

### 2.1 44pt 미만 아이콘/버튼 (MAJOR)

| 컴포넌트 | 코드 | 실측 크기 | 파일:라인 |
|----------|------|-----------|-----------|
| `Pagination` 페이지 이동 | `p-1.5` + 아이콘 16px | ~28×28px | `screener/Pagination.tsx:94,104,141,151` |
| `WatchlistItemRow` 편집/삭제 | `p-1.5` + `h-4 w-4` | ~28×28px | `watchlist/WatchlistItemRow.tsx:111` |
| `IndicatorSetupCard` 전원/삭제 | `p-2` + 16px | ~32×32px | `thesis/indicators/IndicatorSetupCard.tsx:49,60` |
| Coach 폼 행 삭제 | `p-1.5` + `h-4 w-4` | ~28×28px | `app/coach/e1:200,e2:195,e3:232,e5:232,e6:220` |
| `IndicatorCard` 체크박스 | `w-5 h-5` | 20×20px | `thesis/IndicatorCard.tsx:37` |
| `AddIndicatorSheet` 지표 버튼 | `px-2.5 py-2 text-xs` | ~28~32px 높이 | `thesis/AddIndicatorSheet.tsx:226` |
| `AlertCard` 읽음 버튼 | `px-2 py-1 text-[10px]` | ~24~28px 높이 | `thesis/alerts/AlertCard.tsx:57` |
| `SuggestionChips` (RAG) | `px-3 py-1.5 text-sm` | ~32~36px 높이 | `rag/SuggestionChips.tsx:30` |
| `BasketActionCard` 토글 | `px-2 py-1 text-xs` | ~28px 높이 | `rag/BasketActionCard.tsx:72` |
| `AINewsBriefingCard` 확대/축소 | `text-xs` + `w-3 h-3` 아이콘 | ~16px 높이 | `news/AINewsBriefingCard.tsx:106` |
| `MoverCard` 정보 아이콘 | `w-3 h-3` | 12×12px | `market-pulse/MoverCard.tsx:132` |

### 2.2 text-[10px] / text-[11px] 클릭·정보 요소

- **전역 131회** 사용. 대부분 읽기 전용 라벨이나, 일부는 클릭 요소:
  - `screener/PresetGallery.tsx:241` — `text-[10px]` "상세 설명" Info 버튼 (🟠 클릭 요소, 폭 ~40px·높이 ~16px)
  - `thesis/builder/OptionButton.tsx:66` — `text-[10px]` "꾹 누르면 설명" 힌트, 데스크톱 Info 아이콘은 `p-1`+14px = ~22px (🟠)
  - `chainsight/MobileCardList.tsx:149,154,159`, `RelationCardPanel.tsx:273,289` — `text-[10px]` 태그/배지 (읽기 전용, 🟡)
- **정보 가독성**: `eod/StockRow.tsx:89,92`의 `text-[11px]` 시그널 라벨·거래량은 행 전체가 44px이상이라 터치는 OK이나 텍스트 작음 (🟡).

### 2.3 양호 사례 (✅)

- `layout/MobileNav.tsx:34` — 하단 탭 `min-h-[44px]` 보장 ✅
- `validation/SignalSummaryCard` — 신호등 버튼 `min-w-[72px] min-h-[44px]` ✅
- `validation/PeerContextBar` 프리셋 버튼 — `min-h-[44px]` ✅
- `eod/SignalFilterTabs` — `text-sm px-3 py-1.5` 높이 충족 ✅ (단 폭 협소, §3 참조)

---

## 3. 네비게이션

### 3.1 헤더/메뉴 (BLOCKER + MAJOR)

| 심각도 | 항목 | 문제 | 파일:라인 |
|--------|------|------|-----------|
| 🔴 BLOCKER | `Header` 햄버거 | 버튼이 `className="hidden ..."`로 완전 비활성. 드롭다운 메뉴(`isMenuOpen`) 마크업은 존재하나 **열 방법이 없음** (주석 "audit P0 #12") | `layout/Header.tsx:157` |
| 🟠 MAJOR | `Header` 모바일 메뉴 | 아코디언 항목 `px-3 py-2`, `min-h-[44px]` 미보장 | `layout/Header.tsx:170` |
| 🟠 MAJOR | `InvestingHeader` | 8개 네비 항목(`시장·주식·지수·암호화폐·상품·분석·기술적분석·경제캘린더`)을 `flex` 고정 배치, hamburger/scroll 대응 없음 → 375px 초과 | `layout/InvestingHeader.tsx:98` |

> **하단 네비 자체는 양호**: `MobileNav.tsx`가 `fixed bottom-0 ... md:hidden` bottom navigation으로 5탭(홈·종목·뉴스·포트폴리오·내정보) 구현, `app/layout.tsx:63`에서 전역 렌더. 단 상단 `Header` 햄버거가 죽어 있어 **상·하단 진입점이 이중으로 어긋남** — `Header`/`InvestingHeader`가 동시 렌더되는 페이지에서는 상단 메뉴 접근 불가.

### 3.2 가로 스크롤 탭 — 활성 탭 가시성

| 심각도 | 컴포넌트 | 문제 | 파일:라인 |
|--------|----------|------|-----------|
| 🟠 MAJOR | `PeerContextBar` 프리셋 탭 | `flex flex-wrap` → 4~5개 탭이 375px에서 2~3줄로 줄바꿈 (가로 스크롤이 더 적합) | `validation/PeerContextBar.tsx:33` |
| 🟡 MINOR | `eod/SignalFilterTabs` | 7탭 `overflow-x-auto` 있으나 활성 탭 `scroll-into-view` 없음 + 스크롤 가능 표시(chevron) 없음 → 숨은 탭 인지 불가 | `eod/SignalFilterTabs.tsx:33` |
| 🟡 MINOR | `AdminTabNav` | `overflow-x-auto`만, `scrollbar-hide`/`WebkitOverflowScrolling` 최적화 누락 (대조: `RelationFilterChips.tsx:229`는 적용됨) | `admin/AdminTabNav.tsx:30` |
| 🟡 MINOR | `chainsight/MobileCardList` 카테고리 탭 | `overflow-x-auto min-w-max`, 10+ 탭 시 전부 DOM 렌더 | `chainsight/MobileCardList.tsx:84` |

### 3.3 긴 목록 — Virtualization 부재 (MAJOR)

> 프로젝트 전체에 `react-window`/`react-virtual`/`virtuoso` import **0건**. 아래는 일괄 `map()` 렌더:

| 심각도 | 위치 | 잠재 항목 수 | 파일:라인 |
|--------|------|--------------|-----------|
| 🟠 MAJOR | 뉴스 페이지 | `limit: 100` 기사 한 번에 로드+렌더 | `app/news/page.tsx:47`, `news/NewsList.tsx:234` |
| 🟠 MAJOR | `SignalDetailSheet` 종목 리스트 | "거래량 급증" 등 시그널은 수백~1000+ 종목 가능 | `eod/SignalDetailSheet.tsx:242` |
| 🟠 MAJOR | `PortfolioTable` | 보유 종목 행 전부 렌더 (가상화 없음) | `portfolio/PortfolioTable.tsx` |
| 🟡 MINOR | `thesis IndicatorRow` 확장 | 20+ 지표 동시 확장 시 차트 DOM 선형 증가 | `thesis/dashboard/IndicatorRow.tsx` |
| 🟡 MINOR | `thesis alerts` 목록 | 페이지네이션/가상화 없음 | `app/thesis/(list)/alerts/page.tsx:74` |

> 대부분 일상 데이터량(10~100개)에서는 체감 문제 없으나, 경계 케이스(뉴스 100건 고정·대형 시그널)에서 모바일 프레임 드롭 위험.

---

## 4. 차트/그래프

### 4.1 Recharts ResponsiveContainer 현황

- **사용 양호**: 16개 파일 51회. 폭은 `width="100%"`로 반응형 ✅
- **공통 결함**: **높이가 고정 px**라 모바일에서 비율·가독성 저하.

| 심각도 | 컴포넌트 | 고정 높이 | 모바일 문제 | 파일:라인 |
|--------|----------|-----------|-------------|-----------|
| 🟠 MAJOR | `SectorHeatmap` | `height={400}` | Treemap 타일 `width<60px`면 텍스트 생략 → 375px에선 대부분 색상만, 정보 손실 (모바일은 hover 툴팁도 불가) | `screener/SectorHeatmap.tsx:216,31` |
| 🟠 MAJOR | `MetricBarChart` | `h-48` + `margin right:50`/`YAxis width:50` | 데이터 영역 13% 잠식, tick `fontSize:11` 가독성 저하 | `validation/MetricBarChart.tsx:72,79,83` |
| 🟠 MAJOR | `thesis/IndicatorRow` AreaChart | `height={160}` + `YAxis width={55}` + `XAxis fontSize=9` | 55px(폭 15%) 잠식, 9px 라벨 판독 어려움 | `thesis/dashboard/IndicatorRow.tsx:197` |
| 🟠 MAJOR | `IndividualMiniCharts` | `height={100}` + `YAxis width=55` | 동일 패턴 | `thesis/dashboard/IndividualMiniCharts.tsx:54` |
| 🟡 MINOR | `StockPriceChart` | 기본 `height={400}` | ResponsiveContainer OK이나 모바일 기본 높이 과대(200~250 권장) | `charts/StockPriceChart.tsx:272` |
| 🟡 MINOR | `StockChart` | `YAxis fontSize={12}` 고정 | 모바일에서 틱 라벨 겹침 가능 | `stock/StockChart.tsx:150` |
| 🟡 MINOR | `MarketBreadthCard` | `w-48` 게이지 + `stroke-width=16` | 375px에서 게이지가 시각적으로 과대 | `screener/MarketBreadthCard.tsx:122` |

### 4.2 분기 스파크라인 가독성 (BLOCKER + MAJOR)

| 심각도 | 컴포넌트 | 문제 | 파일:라인 |
|--------|----------|------|-----------|
| 🔴 BLOCKER | `QuarterlySparkline` | `h-10`(40px) 컨테이너에 막대 `heightPct%` → 50%면 20px. `flex-1` 막대지만 실제 색상 영역 협소, 분기 라벨 `text-[11px]`로 판독 어려움. 터치 시 정밀 타격 필요 | `thesis/dashboard/QuarterlySparkline.tsx:33,42` |

### 4.3 캔버스 그래프 (chainsight)

- `MarketGraphCanvas` / `GraphCanvas`는 `react-force-graph-2d` 사용. **폭은 ResizeObserver로 동적**, canvas 자동 스케일 → 렌더 자체는 모바일 대응 ✅
- 단 **높이 `560px` 고정**(B2)과 노드 터치 영역이 핵심 문제. `chainsight/ExplorationTrail.tsx:55`의 동적 노드 버튼은 `r=12`일 때 24×24px로 44pt 미만 (🟡 MINOR).

### 4.4 차트 없는 영역

- `chainsight` 데이터 시각화는 Recharts 미사용(SVG/canvas만) → ResponsiveContainer 해당 없음.
- `chainsight/EventRanking` 테이블은 메트릭 컬럼 `w-20`×3 고정으로 암묵적 가로 오버플로우, 명시적 `overflow-x-auto` 없음 (🟠 MAJOR).

---

## 5. 페이지별 상세

### 📄 코치 (`/coach/e1`~`e6`)
- 🔴 **B6** 입력폼 `grid-cols-12` 6필드 가로 배치 → 모바일 illegible (e1:150, e2:164, e3:178, e5:201, e6:181)
- 🟠 행 삭제 버튼 `p-1.5` ~28px (각 페이지)
- 🟠 E4 채팅 `max-w-3xl` + `max-h-[60vh]` 모바일 협소 (e4:115,135)
- 🟠 E1/E2 헤더 그리드는 `grid-cols-1 md:grid-cols-N`으로 모바일 1열 OK이나 입력칸 cramped

### 📄 관제실/가설 (`/thesis/*`)
- 🔴 **B7** `QuarterlySparkline` 막대 터치·가독성
- 🟠 `IndicatorRow` 고정 min-width flex row 오버플로우 + AreaChart 9px 축 라벨
- 🟠 `IndividualMiniCharts` 고정 height + 55px YAxis
- 🟠 `IndicatorCard` 체크박스 20px / `AddIndicatorSheet` 지표 버튼 ~30px / `IndicatorSetupCard` 액션 ~32px
- 🟠 `AlertCard` 읽음 버튼 `text-[10px]` ~24px
- 🟡 `AlertFilterTabs`/`PeriodSelector` `py-1.5 text-xs` ~18~20px, 알림 목록 가상화 없음

### 📄 체인사이트 (`/chainsight/*`)
- 🔴 **B2** `MarketGraphCanvas` `h-[560px]` 화면 92% 점유
- 🔴 **B3** 인기 섹터 버튼 `w-[110px]`×3 수평 스크롤
- 🟠 `SectorBar` 버튼 폭 무제한 / `[symbol]` 페이지 모바일 바텀시트(`max-h-48`) 3CTA 버튼 텍스트 잘림 (325-328)
- 🟠 `MobileCardList` 3-버튼 CTA(`text-xs flex-1`)가 375px에서 한글 텍스트 미수용 / `EventRanking` 테이블 암묵 오버플로우
- 🟠 `text-[10px]` 태그·배지 다수(MobileCardList, RelationCardPanel, RelationLegend, ExplorationTrail)
- 🟡 `ExplorationTrail` 노드 24×24px / 카테고리 탭 가상화 없음
- ✅ `NodeTooltip`(hover 기반), `RelationFilterChips`(md:hidden 그라디언트), `EventBoard`(반응형 그리드)

### 📄 스크리너 (`/screener`)
- 🔴 **B4** `ScreenerTable` 12컬럼, `MobileStockCard` 미연결
- 🟠 `PresetGallery` `grid-cols-2` 카드 ~168px 붕괴 / `SectorHeatmap` height 400 + 텍스트 생략 / `MarketBreadthCard`
- 🟠 `Pagination` 아이콘 버튼 ~28px
- 🟡 `PresetCard` Info 버튼 `text-[10px]`, `AdvancedFilterPanel` 탭 wrapping 가능성
- ✅ `ScreenerDashboard`, `MobileStockCard`, `ThesisBuilder`, `SignalCardGrid` 반응형 양호

### 📄 EOD 대시보드 (`/dashboard`)
- 🟠 `SignalDetailSheet` 종목 리스트 가상화 없음 (대형 시그널 위험)
- 🟠 `SignalFilterTabs` 7탭 좁음 + 활성 탭 scroll-into-view 없음
- 🟡 `StockRow` `text-[11px]` 보조 텍스트

### 📄 1차 검증 (`/validation` 관련)
- 🟠 `MetricBarChart` h-48 + 마진 과다 / `LeaderComparisonSection` 4컬럼+중첩 테이블 카드 분기 없음
- 🟠 `PeerContextBar` 프리셋 탭 `flex-wrap` 2~3줄 (가로 스크롤 권장)
- 🟡 `PeerContextBar` `text-[10px]` 안내문
- ✅ `SignalSummaryCard`(min-h-44), `IndustryPosition`, `CategorySection`(모바일 accordion) 양호

### 📄 뉴스 (`/news`)
- 🟠 `limit:100` 기사 일괄 로드/렌더, 가상화 없음 (page.tsx:47, NewsList.tsx:234)
- 🟠 `AINewsBriefingCard` 확대/축소 버튼 ~16px
- 🟡 `RecommendationCard`/`SuggestionChips`/`AINewsBriefingCard` max-w truncate 모바일 미세 조정 부재
- ✅ `DailyKeywordCard` `max-h-[200px] overflow-y-auto` 제한 적용

### 📄 마켓 펄스 (`/market-pulse`, `/market-pulse-v2`)
- 🟠 `MoverCard` 5지표 2줄, 정보 아이콘 12px, `text-[10px]` 섹터 정보
- 🟡 `GlobalMarketsCard` 4컬럼 각 ~90px 텍스트 협소
- ✅ `market-pulse-v2/details/*` 4개 ResponsiveContainer 적용

### 📄 포트폴리오/관심종목 (`/portfolio`, `/watchlist`)
- 🔴 **B5** `PortfolioTable` 12컬럼, 모바일 카드 분기 없음, 행 가상화 없음
- 🟠 `WatchlistItemRow` 편집/삭제 ~28px 버튼

### 📄 종목 상세/재무 (`/stocks/[symbol]`)
- 🟠 `QuickAddDropdown` `w-80`(320px) 고정 드롭다운 화면 침범
- 🟡 `StockChart`/`StockPriceChart` 모바일 높이·축 라벨 미세 조정 부재

### 📄 전역 (모든 페이지)
- 🔴 **B1** `Header` 햄버거 `hidden` → 상단 메뉴 호출 불가
- 🟠 `Header` 모바일 메뉴 min-h-44 미보장, `InvestingHeader` 8탭 오버플로우
- ✅ viewport meta (`app/layout.tsx:29`), `MobileNav` bottom nav, `max-w-7xl` 컨테이너는 모바일 자동 축소

---

## 부록: 우선순위 권장 (감사 의견)

> 본 보고서는 읽기 전용 감사이며 아래는 수정 권고일 뿐 코드 변경은 수행하지 않았습니다.

**P0 (BLOCKER 7건)**
1. `Header.tsx:157` 햄버거 버튼 `hidden` 제거 + 메뉴 항목 `min-h-[44px]`
2. `ScreenerTable` / `PortfolioTable` → 모바일 카드 분기 (`MobileStockCard` 재사용 가능)
3. `MarketGraphCanvas` `h-[560px]` → `h-[300px] md:h-[560px]`, 인기 섹터 버튼 `flex-1 md:w-[110px]`
4. Coach E1~E6 폼 `grid-cols-12` → 모바일 세로 stacking
5. `QuarterlySparkline` 막대 높이/터치 영역 확대

**P1 (MAJOR 군)**
- 차트 고정 높이 → breakpoint 분기 (`SectorHeatmap`, `MetricBarChart`, `IndicatorRow`, `IndividualMiniCharts`)
- 가로 스크롤 탭의 `flex-wrap` → `overflow-x-auto` + scroll-into-view (`PeerContextBar`, `SignalFilterTabs`)
- `InvestingHeader` 모바일 네비 대응
- 긴 목록 가상화 도입 (뉴스 100건, 대형 시그널)
- 44pt 미만 아이콘 버튼 일괄 패딩 상향 (`Pagination`, `WatchlistItemRow`, Coach 삭제 버튼 등)

**P2 (MINOR 군)**
- `text-[10px]`/`text-[11px]` 131회 → 클릭 요소부터 `text-xs`(12px) 통일, 메타는 `sm:` 조건부
- `overflow-x-auto`에 `scrollbar-hide`/`WebkitOverflowScrolling: touch` 일관 적용
- 모바일 차트 기본 높이/축 폰트 미세 조정
