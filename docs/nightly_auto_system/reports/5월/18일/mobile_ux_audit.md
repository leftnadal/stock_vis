# 모바일 UX 감사 보고서

**감사 대상**: `/Users/byeongjinjeong/Desktop/stock_vis/frontend`
**감사 일자**: 2026-05-19 (보고서 폴더: 5월/18일)
**감사 모드**: 읽기 전용 (코드 수정 없음)
**기준 뷰포트**: 모바일 375px (iPhone SE/12 mini), Apple HIG 44×44pt 터치 타겟

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 설명 |
|--------|------|------|
| **BLOCKER** | 2 | 모바일 375px에서 콘텐츠가 잘리거나 사용 불가 |
| **MAJOR** | 8 | 사용은 가능하나 가독성·터치 정확도 저하 |
| **MINOR** | 11 | UX 폴리시 수준의 권장 개선 |
| **총계** | **21** | — |

**총평**
- 모바일 네비게이션은 단일 소스(`MobileNav.tsx`)로 깔끔하게 구축되어 있고, `min-h-[44px]` 터치 타겟이 34개 이상 파일에 적용되어 있어 **기본기는 견고**하다.
- 차트(recharts)는 **14개 파일 전부 ResponsiveContainer 사용**으로 양호.
- 약점은 (1) `market-pulse-v2/details` 페이지의 데스크톱 가정 그리드, (2) 일부 클릭 요소의 `text-[10px]/[11px]`, (3) Chainsight 그래프 노드(`w-[110px]`)와 ScreenerTable 셀의 모바일 가독성, (4) **긴 목록 가상화 0건**.

---

## 반응형 누락

### BLOCKER

**1. `market-pulse-v2/details` 페이지 — 데스크톱 전용 3컬럼 헤더**
- `frontend/app/market-pulse-v2/details/BreadthDetail.tsx:29` — `grid grid-cols-3 gap-2 text-center` (브레이크포인트 없음)
- `frontend/app/market-pulse-v2/details/FlowDetail.tsx:34` — `grid grid-cols-3 gap-2 text-center`
- `frontend/app/market-pulse-v2/cards/FlowCardSummary.tsx:13` — `grid grid-cols-3 gap-2 text-center`
- **영향**: 375px 폭에서 3개 셀이 강제로 압축되어 텍스트가 잘리거나 줄바꿈 폭주. Market Pulse v2 디테일 페이지의 핵심 헤더라 노출 빈도가 높다.
- **참고**: 동일 디렉터리의 `RegimeDetail.tsx`, `SectorDetail.tsx`는 반응형 처리됨.

**2. `MarketGraphCanvas` 노드 카드 — 110px 고정폭 + 8개 이상 동시 노출**
- `frontend/components/chainsight/MarketGraphCanvas.tsx:676` — `'w-[110px] min-h-[68px] px-3 py-2'`
- **영향**: Chain Sight 그래프 캔버스에 8~12개 노드가 펼쳐지면 375px 폭에서 노드끼리 겹치거나 캔버스 한 화면을 벗어남. force-graph 라이브러리가 panning을 지원하므로 우회는 가능하지만, 첫 진입 시 시각적 손상 발생.
- 동일 영역에서 `MobileCardList` 컴포넌트가 별도 존재하므로 **모바일에서는 그래프 대신 카드 리스트로 라우팅**되어야 하는데, 현재 캔버스 자체가 mobile에서도 렌더링되는지 확인 필요(코드만으로 분기 불명).

### MAJOR

**3. `InvestingHeader` 컨테이너 `max-w-[1400px]` × 3 위치**
- `frontend/components/layout/InvestingHeader.tsx:32,55,99`
- 모바일에서는 `mx-auto px-4`로 패딩이 들어가 잘림은 없으나, 1400px 상한이 모바일 의도와 무관한 데스크톱 컨테이너 표시. 현재 헤더 사용처가 어디인지 추적 후 `Header.tsx`와의 이중 헤더 가능성 점검 필요.

**4. ScreenerTable 셀 고정 폭 — 모바일에서 정보 손실**
- `frontend/components/strategy/ScreenerTable.tsx:209` — `max-w-[180px] truncate text-xs` (종목명)
- `frontend/components/strategy/ScreenerTable.tsx:224` — `max-w-[120px] truncate text-xs` (섹터)
- `frontend/components/strategy/ScreenerTable.tsx:307` — `max-w-[200px]` (테제 컬럼)
- **영향**: `overflow-x-auto`로 수평 스크롤은 보장되지만, truncate된 셀에 hover title이 있어도 모바일 long-press는 UX가 어색. Screener의 `MobileStockCard.tsx`로 라우팅되는 viewMode가 있긴 하다(긍정).

**5. `text-[10px]` 작은 텍스트 — 정보성 뱃지**
- `frontend/components/admin/news/AlertBadge.tsx:29` — `text-[10px] font-bold` (알림 카운터)
- `frontend/components/eod/SignalFilterTabs.tsx:68` — `text-[11px] font-semibold` (탭 내부 카운트)
- **영향**: 자체는 클릭 요소가 아니지만, 부모(탭/뱃지)가 클릭 가능하면 정보 가독성 저하. AdminMobile 사용 빈도는 낮으나, EOD 시그널 탭은 메인 페이지 노출.

---

## 터치 타겟

### MAJOR

**6. `OptionButton` 등 `role="button"` 4개 위치 — 크기 검증 필요**
- `frontend/components/thesis/builder/OptionButton.tsx:68`
- `frontend/components/eod/SignalCard.tsx:72`
- `frontend/components/admin/news/RecentErrorsList.tsx:22`
- `frontend/components/admin/shared/IssueList.tsx:37`
- **영향**: `<div role="button">` 사용 시 `min-h-[44px]`가 명시되어 있는지 확인 필요. OptionButton은 Thesis Builder의 대화형 선택지라 자주 탭됨 → 실측 권장.

**7. ScreenerTable 액션 버튼 — 44pt 보장은 되지만 `text-xs`**
- `frontend/components/strategy/ScreenerTable.tsx:323` — `min-h-[44px] min-w-[44px]` + `text-xs` (긍정/약점 혼재)
- **영향**: 터치 영역은 충족하나, 라벨 가독성 저하. 모바일에서 아이콘+한글 라벨로 보완 권장.

### MINOR

**8. Chain Sight 노드 카드 — 터치 타겟 명확성**
- `MarketGraphCanvas.tsx:676` — `w-[110px] min-h-[68px]`
- 68px 높이는 충분(44pt 통과), 너비도 OK. 단 노드 간 간격이 좁으면 인접 노드 오탭 가능 → force-graph의 노드 padding 설정 점검 권장.

**9. Validation `SignalSummaryCard` 신호등 — 44pt 통과**
- `frontend/components/validation/SignalSummaryCard.tsx:41` — `min-w-[72px] min-h-[44px]` (긍정)
- 다만 신호등 5~7개가 한 줄에 나열되면 `overflow-x-auto`(L36)로 스크롤 → 첫 진입 시 "더 있다"는 affordance가 약함. 그라데이션 mask 또는 페이지 인디케이터 권장.

**10. Thesis 관제실 `IndicatorRow` — 작은 텍스트 영역 다수**
- `frontend/components/thesis/dashboard/IndicatorRow.tsx:110,115,132` — `min-w-[60px]`, `min-w-[120px]`, `max-w-[100px]`
- 텍스트 영역의 고정폭이라 클릭 요소는 아니나, 행 전체가 탭 가능하면 별도 검증 필요. 현재 코드만으로는 분기 불명.

---

## 네비게이션

### 긍정 (이슈 없음)

- `frontend/components/layout/MobileNav.tsx` — **단일 모바일 네비 소스**. `fixed bottom-0`, `md:hidden`, `h-16`, 각 항목 `min-h-[44px]`, 5개 핵심 항목(홈/종목/뉴스/포트폴리오/내정보). audit P0 #12·#13 주석으로 의도 명시. **모범 사례**.
- `frontend/components/layout/Header.tsx:157-163` — 모바일 햄버거 버튼은 `className="hidden ..."`으로 **의도적 비활성화**. 이중 네비 방지(주석 명시). 데스크톱(`hidden md:flex`)과 모바일(MobileNav) 분리 명확.

### MAJOR

**11. Bottom navigation에 Thesis Control / Chain Sight / Market Pulse / Screener 미포함**
- `MobileNav.tsx:11-17`의 5개 항목: 홈, 종목, 뉴스, 포트폴리오, 내정보.
- **영향**: Thesis(가설 통제실), Chain Sight, Screener, Market Pulse는 프로젝트의 시그니처 기능인데 모바일에서는 `/` → 메뉴 카드를 통해서만 진입. Header가 모바일에서 비활성화된 햄버거를 갖고 있어, **모바일 사용자가 시그니처 기능까지 도달하는 경로가 길다**.
- 권장: 햄버거 복원 또는 MobileNav 항목 재구성("더보기" 항목 추가).

### MAJOR

**12. 긴 목록 가상화 0건**
- `react-window`, `react-virtualized` 패키지 사용 grep 결과 **0**.
- **영향 후보**:
  - Screener 결과(`MobileStockCard` × N) — 페이지네이션으로 대응(`Pagination.tsx`).
  - News 목록 — 카테고리별 분할.
  - Chain Sight 노드 카드 리스트 — 미확인.
  - Watchlist, Portfolio 보유 종목 리스트 — 보유 종목 100건 이상 시 성능 저하 위험.
- 페이지네이션으로 부분 대응되지만, Watchlist/Portfolio처럼 무한 스크롤 가능성이 있는 영역은 점검 필요.

### MINOR

**13. `InvestingHeader` 사용 페이지가 별도 존재할 가능성**
- `Header.tsx`와 `InvestingHeader.tsx` 동시 존재. 어느 페이지가 어느 헤더를 쓰는지 일관성 점검 필요. `max-w-[1400px]` 컨테이너가 셋(L32, L55, L99)으로 분리되어 있다 — 모바일 진입 시 두 헤더가 동시에 표시되지 않는지 확인.

---

## 차트/그래프

### 긍정 (이슈 없음)

- recharts import 14개 파일이 **모두 `ResponsiveContainer` 사용** (테스트 1개 제외):
  - `charts/StockPriceChart.tsx`, `stock/StockChart.tsx`, `portfolio/PortfolioChart.tsx`
  - `thesis/dashboard/IndicatorRow.tsx`, `thesis/dashboard/IndividualMiniCharts.tsx`
  - `validation/MetricBarChart.tsx`, `news/SentimentChart.tsx`
  - `macro/YieldCurveChart.tsx`, `screener/SectorHeatmap.tsx`
  - `admin/news/MLTrendChart.tsx`
  - `market-pulse-v2/details/{Breadth,Flow,Regime,Sector}Detail.tsx`
- 차트 width/height 하드코딩 사례 0건.

### MAJOR

**14. Thesis 관제실 분기 스파크라인 — `max-w-[100px]` 폭**
- `frontend/components/thesis/dashboard/IndicatorRow.tsx:132` — `<div className="flex-1 max-w-[100px]">`
- **영향**: 분기 4~20개 데이터 포인트를 100px에 압축. 모바일 가독성도 데스크톱 가독성도 박빙. 더 중요한 건 `IndividualMiniCharts.tsx`로 들어가는 모달에서 확장 차트가 제공되는지 여부 — 미확인.

### MINOR

**15. force-graph-2d (Chain Sight) — 터치 제스처**
- `package.json:25` — `react-force-graph-2d: ^1.29.1`
- pinch-zoom, two-finger pan 지원은 라이브러리 레벨이지만 옵션 명시 여부 확인 필요. `MarketGraphCanvas.tsx`에서 모바일 제스처 props 부재 시 데스크톱 마우스 휠 줌만 가능.

---

## 페이지별 상세

### `/` (메인 대시보드) — `app/page.tsx` + `app/dashboard/page.tsx`
- **레이아웃**: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` (반응형 ✓)
- **상태**: 양호. MobileNav가 하단 고정.
- **이슈**: 없음 (코드 기반).

### `/thesis` (가설 통제실) — `app/thesis/(list)/page.tsx`, `app/thesis/[thesisId]/page.tsx`
- **컨테이너**: `max-w-lg mx-auto px-4 pb-20` (모바일 우선 ✓, `pb-20` MobileNav 공간 ✓)
- **주요 컴포넌트**: `IndicatorRow`, `AISummarySection`, `NotableChangesSection`
- **이슈**:
  - **[MAJOR #14]** `IndicatorRow.tsx:132` 스파크라인 100px 폭 — 분기 데이터 가독성.
  - **[MINOR #10]** `IndicatorRow.tsx:110,115,132` — 텍스트 영역 고정폭(60/120/100px), 클릭 영역인지 분기 불명.
  - **[MAJOR #11]** 모바일 진입 경로(MobileNav에 없음).

### `/thesis/[thesisId]/indicators` (지표 설정)
- **컨테이너**: `h-[calc(100dvh-env(safe-area-inset-top))]` (iOS 안전 영역 고려 ✓)
- **이슈**: `IndicatorSetupCard`, `AddIndicatorSheet` 내부 미감사 — 추후 점검 권장.

### `/validation` (1차 검증) — `stocks/[symbol]` 내부에 포함
- **컴포넌트**: `SignalSummaryCard`, `PeerContextBar`, `MetricBarChart`, `LeaderComparisonSection`
- **이슈**:
  - **[MINOR #9]** `SignalSummaryCard.tsx:36` 신호등 `overflow-x-auto` — affordance 약함.
  - **[긍정]** `PeerContextBar`는 `flex flex-wrap` + `min-h-[44px]` (L35,97,126).

### `/chainsight` — `app/chainsight/page.tsx`, `app/chainsight/[symbol]/page.tsx`
- **컴포넌트**: `SectorBar`(L24 `overflow-x-auto`), `RelationFilterChips`(L229), `MarketGraphCanvas`, `MobileCardList`, `RelationCardPanel`
- **이슈**:
  - **[BLOCKER #2]** `MarketGraphCanvas` 노드 `w-[110px]` — 모바일 분기 라우팅 확인 필요.
  - **[MINOR #8]** 노드 간격 좁을 시 오탭.
  - **[MINOR #15]** force-graph 모바일 제스처 옵션 확인 필요.
  - **[긍정]** `MobileCardList.tsx` 전용 모바일 컴포넌트 존재.

### `/screener` — `app/screener/page.tsx`
- **컴포넌트**: `ScreenerTable`(데스크톱) ↔ `MobileStockCard`(모바일, viewMode 토글, L854)
- **이슈**:
  - **[MAJOR #4]** `ScreenerTable.tsx:209,224,307` 셀 고정폭 — `overflow-x-auto`로 보강되나 truncate 정보 손실.
  - **[MAJOR #7]** L323 액션 버튼 `text-xs` 라벨.
  - **[긍정]** `Pagination.tsx:127` `min-w-[44px] min-h-[44px]`, `MobileStockCard` 전용 컴포넌트 존재.
  - **[MAJOR #11]** 모바일 진입 경로(MobileNav 미포함).

### `/stocks/[symbol]` — `app/stocks/[symbol]/page.tsx` (1100줄+)
- **레이아웃**: `grid grid-cols-1 lg:grid-cols-2` (반응형 ✓), L1/L2 탭, `overflow-x-auto` L843·L1030
- **컴포넌트**: `StockChart`(ResponsiveContainer ✓), `MetricCard`(grid-cols-2 sm:grid-cols-4 ✓), `OtherFundamentalsTab`
- **이슈**: 코드 기반 큰 이슈 없음. 다만 1100줄+ 파일 자체가 모바일 초기 로드 시 무거울 가능성 — Lighthouse 측정 권장.

### `/portfolio` — `app/portfolio/page.tsx`
- **컴포넌트**: `PortfolioSummary`, `PortfolioChart`(ResponsiveContainer ✓), `PortfolioTable`(L259 overflow-x-auto ✓)
- **이슈**: 가상화 없음 — 보유 종목 100건 이상 시 성능. [MAJOR #12]

### `/watchlist` — `app/watchlist/page.tsx`
- **레이아웃**: `grid grid-cols-1 lg:grid-cols-3` (반응형 ✓)
- **컴포넌트**: `WatchlistCard`, `WatchlistItemRow`(L294 overflow-x-auto)
- **이슈**: 가상화 없음. [MAJOR #12]

### `/news` — `app/news/page.tsx`
- **컴포넌트**: `NewsHighlightedStocks`(grid-cols-1 md:grid-cols-2 ✓), `NewsGrid`(grid-cols-1 lg:grid-cols-2 ✓), `SentimentChart`(ResponsiveContainer ✓), `DailyKeywordCard`(flex flex-wrap ✓)
- **이슈**: 코드 기반 큰 이슈 없음.

### `/market-pulse-v2` — `app/market-pulse-v2/page.tsx` + `details/*.tsx`
- **컴포넌트**: `TickerBar`(overflow-x-auto sticky ✓), `BreadthCardSummary`, `SectorCardSummary`, `StatusBanner`
- **이슈**:
  - **[BLOCKER #1]** `BreadthDetail.tsx:29`, `FlowDetail.tsx:34`, `FlowCardSummary.tsx:13` — `grid-cols-3` 고정 헤더.
  - **[MAJOR #11]** 모바일 진입 경로(MobileNav 미포함).

### `/market-pulse` (구버전) — `app/market-pulse/page.tsx`
- 자세히 감사하지 않음. `market-pulse-v2`로 마이그레이션 중인지 확인 필요.

### `/admin` — `app/admin/page.tsx`
- **컴포넌트**: `AdminTabNav`(min-h-[44px] ✓), `SystemTab`(overflow-x-auto L72,144,288 ✓), `NewsCategoryManager`, `MLCompareView` 등
- **이슈**:
  - **[MAJOR #5]** `AlertBadge.tsx:29` `text-[10px]`.
  - **[MINOR]** `SystemTab.tsx:362`, `TaskLogViewer.tsx:218` `max-w-[240/260px] truncate text-xs` — 운영자 화면이라 모바일 사용 빈도 낮음.

### `/ai-analysis`, `/login`, `/signup`, `/mypage`
- 코드 기반 큰 이슈 없음. RAG `ChatInterface.tsx:198` `h-[52px] w-[52px]` 전송 버튼은 44pt 통과(긍정).

---

## 부록: 핵심 통계

| 항목 | 개수 | 평가 |
|------|------|------|
| `overflow-x-auto` 사용 | 30 파일 | ✅ 수평 스크롤 광범위 적용 |
| `min-h-[44px]` 적용 | 34+ 파일 | ✅ 터치 타겟 기준 준수 |
| recharts + ResponsiveContainer | 14/14 | ✅ 차트 반응형 100% |
| `flex flex-wrap` 사용 | 38 파일 | ✅ 줄바꿈 처리 |
| 반응형 grid (`sm:/md:/lg:`) | 75+ 위치 | ✅ 대부분 반응형 |
| `grid-cols-N` 고정 (브레이크포인트 없음) | 3 파일 | ⚠️ market-pulse-v2 집중 |
| `w-[NNpx]` / `min-w-[NNpx]` / `max-w-[NNpx]` 고정 폭 | 22 파일 | ⚠️ 일부 검토 필요 |
| `text-[10px]` / `text-[11px]` 클릭 가능 영역 | 2 파일 | ⚠️ 가독성 |
| 가상 스크롤(react-window 등) | **0** | ⚠️ 페이지네이션으로 부분 대응 |
| `<table>` 직접 사용 | 미감사 | — Screener는 div 기반 |
| 모바일 전용 컴포넌트 (`Mobile*`) | 2개 (`MobileNav`, `MobileStockCard`, `MobileCardList`) | ✅ 분기 라우팅 시도 |

---

## 권장 우선순위 (코드 수정 없음 — 참고용)

1. **BLOCKER #1·#2** — `market-pulse-v2/details/{Breadth,Flow}Detail.tsx` 헤더에 `sm:` 브레이크포인트 추가, `MarketGraphCanvas` 모바일 분기 라우팅(또는 MobileCardList로 fallback) 검증.
2. **MAJOR #11** — MobileNav 항목 재구성: "더보기" 시트 추가하여 Thesis/Chain Sight/Screener/Market Pulse 진입 경로 단축.
3. **MAJOR #4·#5·#7** — Screener 셀 폭 재설계, AlertBadge·SignalFilterTabs 카운트 텍스트 최소 12px로 상향.
4. **MAJOR #12** — Watchlist/Portfolio 100건 이상 시나리오에 한해 가상 스크롤 적용 (`react-window` 도입).
5. **MAJOR #14** — Thesis 관제실 분기 스파크라인 확장 차트 동선 검증.
6. **MINOR** — 신호등 그라데이션 mask, force-graph 모바일 제스처 props 명시, InvestingHeader/Header 사용처 일원화.

---

**감사 종료**. 코드 수정 없음 (read-only).
