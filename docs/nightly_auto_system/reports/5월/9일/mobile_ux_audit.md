# 모바일 UX 감사 보고서

- **감사 일자**: 2026-05-10
- **대상**: `/Users/byeongjinjeong/Desktop/stock_vis/frontend` (Next.js 16, Tailwind, Recharts, react-force-graph-2d)
- **컴포넌트 수**: 192개 (`.tsx`), 페이지 24개 (`page.tsx`)
- **기준**: iPhone SE (375px), Apple HIG 44×44pt, WCAG 2.5.5 (AA 24×24px / AAA 44×44px)
- **모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (심각도별 이슈 수)

| 영역 | BLOCKER | MAJOR | MINOR | 합계 |
|------|:-------:|:-----:|:-----:|:----:|
| 반응형 누락 (고정 폭 / 브레이크포인트) | 3 | 7 | 20+ | 30+ |
| 터치 타겟 (버튼/링크 크기·간격) | 5 | 15 | 2 | 22 |
| 네비게이션 (헤더·BottomNav·진입 동선) | 3 | 6 | 3 | 12 |
| 차트/그래프 (Recharts·SVG·ForceGraph) | 3 | 7 | 11 | 21 |
| **총계** | **14** | **35** | **36+** | **85+** |

### 핵심 결론
1. **모바일 진입 동선이 깨졌다**. BottomNav 5개 탭이 핵심 페이지(Thesis/Screener/ChainSight/AI Analysis/Market Pulse v2)를 커버하지 못해, 사용자가 찾아갈 수 없는 페이지가 8개 이상이다.
2. **테이블 기반 화면이 일관되게 무너진다**. Portfolio·Watchlist·StockTable·ScreenerTable·Validation Peer가 모바일 카드 뷰 없이 `overflow-x-auto`로만 처리되어 핵심 데이터가 가로 스크롤 안에 숨는다.
3. **차트의 hover-only Tooltip은 터치 디바이스에서 작동하지 않는다**. 거의 모든 Recharts 차트가 영향. 모바일 사용자는 차트 데이터값을 읽을 수 없다.
4. **터치 타겟이 24px 이하인 BLOCKER 5개**. 검색 입력의 X 아이콘(16px), 필터 삭제(22px), Edit/Delete(22px), 가설 빌더 Info(22px), Preset 차순 배지(20px)가 사용자 손가락으로 누를 수 없다.

---

## 반응형 누락

### BLOCKER (375px에서 명백한 overflow 또는 사용 불가)

| # | 파일 | 라인 | 코드 / 문제 |
|---|------|------|-------------|
| R-B1 | `components/portfolio/PortfolioTable.tsx` | 259-495 | 12개 컬럼(종목·수량·평균가·현재가·전일대비·평가금액·손익·수익률·목표가·손절가·비중·관리)에 `px-6` 고정. 합산 768px+. `overflow-x-auto`로 가로 스크롤되지만 열이 잘려 비교 불가. 모바일 카드 뷰 없음 |
| R-B2 | `app/watchlist/page.tsx` | 294-332 | 7개 컬럼 `<th class="px-6 ...">`. 모바일 카드 뷰 미구현. 가로 스크롤 강제 |
| R-B3 | `app/stocks/[symbol]/page.tsx` | 329 | `grid grid-cols-2 gap-4` (sm: 분기 없음). 메트릭 라벨이 187px 안에서 줄바꿈, 값이 잘림 |

### MAJOR (UX 깨짐 / 가독성 심각)

| # | 파일 | 라인 | 문제 |
|---|------|------|------|
| R-M1 | `components/stocks/StockTable.tsx` | 34-130 | 7개 컬럼, 모든 셀 `px-6` 고정, 반응형 없음. `차트` 컬럼 모바일 표시 불필요 |
| R-M2 | `components/strategy/ScreenerTable.tsx` | 128-337 | 11개 컬럼 `px-4`. 페이지 레벨에서 `hidden sm:block`으로 데스크톱만 노출하고 모바일은 `MobileStockCard`로 분기되어 있음 — sm~md(640~750px) 구간이 어색 |
| R-M3 | `app/login/page.tsx` | 157 | `grid grid-cols-2` (회원가입/홈으로 버튼). sm 분기 없음 |
| R-M4 | `app/market-pulse-v2/cards/FlowCardSummary.tsx` | 13 | `grid grid-cols-3 gap-2` (375÷3=125px), 라벨 잘림 |
| R-M5 | `app/market-pulse-v2/cards/BreadthCardSummary.tsx` | 14 | `grid grid-cols-2 gap-2`, sm 없음 |
| R-M6 | `app/market-pulse-v2/details/FlowDetail.tsx` | 34 | `grid grid-cols-3 gap-2` |
| R-M7 | `app/market-pulse-v2/details/BreadthDetail.tsx` | 29, 56 | `grid grid-cols-3`, `grid-cols-2` |

### MINOR (반응형 미세 조정 필요)

`grid grid-cols-2` / `grid-cols-3` 하드코딩(반응형 없음) — 20개 컴포넌트:
- `components/screener/MarketBreadthCard.tsx:107` (`grid-cols-3`)
- `components/screener/MobileStockCard.tsx:164` (`grid-cols-3`) — *이름과 달리 반응형 미적용*
- `components/financial/FieldSettingsModal.tsx:334`
- `components/admin/news/LLMUsageSummary.tsx:51, 82`
- `components/admin/news/MLModelCard.tsx:110, 116`
- `components/macro/YieldCurveChart.tsx:147`
- `components/portfolio/PortfolioStockCard.tsx:165`
- `components/portfolio/PortfolioSummary.tsx:64`
- `components/portfolio/RealtimePortfolio.tsx:143`
- `components/rag/TokenUsageDisplay.tsx:143, 175`
- `components/rag/MonitoringDashboard.tsx:131, 215, 261`
- `components/news/MLModelStatusCard.tsx:86`
- `components/thesis/skeleton/ThesisSkeleton.tsx:44, 68`
- `components/thesis/AddIndicatorSheet.tsx:292` (`grid-cols-2 gap-1.5`)
- `app/stocks/[symbol]/page.tsx:568` (`grid-cols-2 md:grid-cols-3 lg:grid-cols-4` — sm 누락)

### Admin 영역 테이블 (별도 분류)
관리자 전용이므로 우선순위는 낮지만 동일한 패턴이 반복됨:
- `components/admin/NewsCategoryManager.tsx:40-50`
- `components/admin/NewsTab.tsx`, `ScreenerTab.tsx`, `SystemTab.tsx`
- `components/admin/shared/TaskLogViewer.tsx`
- `components/admin/news/CollectionStatsTable.tsx:41`
- `components/admin/news/MLCompareView.tsx`

### 잘 된 사례 (참고)
- `components/eod/SignalCardGrid.tsx:34` — `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`
- `app/dashboard/page.tsx:54`, `app/portfolio/page.tsx:228`, `app/screener/page.tsx:855` — 동일 패턴
- 페이지 컨테이너 `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` — 일관됨
- `components/stock/StockChart.tsx:177-187` — `getResponsiveChartHeight()` 동적 계산

---

## 터치 타겟

### BLOCKER (24px 미만 — WCAG AA 위반)

| # | 파일 | 라인 | 추정 크기 | 문제 |
|---|------|------|:--------:|------|
| T-B1 | `components/screener/AdvancedFilterPanel.tsx` | 222-228 | **16px** | 검색 인풋 내부 X 아이콘. `<X className="h-4 w-4" />`에 패딩 없음. 가장 심각 |
| T-B2 | `components/screener/PresetGallery.tsx` | 184 | **20px** | `w-5 h-5 rounded-full` 차순 배지(1차/2차…). 클릭 가능한 영역으로 보일 수 있음 |
| T-B3 | `components/screener/PresetDetailPopover.tsx` | 86 | **20px** | `p-0.5` + `w-4 h-4` X 버튼. 패딩 2px |
| T-B4 | `components/admin/NewsCategoryManager.tsx` | 390, 397 | **22px** | `p-1` + `h-3.5 w-3.5` Edit/Delete. 행 단위 액션이 손가락 폭보다 작음 |
| T-B5 | `components/screener/AdvancedFilterPanel.tsx` | 137 | **22px** | `p-1` + `h-3.5 w-3.5` 필터 클리어 X |
| T-B6 | `components/thesis/builder/OptionButton.tsx` | 72 | **22px** | `p-1` + `Info size={14}`. *`hidden sm:flex`로 데스크톱 한정 — 모바일은 미노출, 반쪽 우회* |
| T-B7 | `components/screener/PresetGallery.tsx` | 192-203 | **22px** | `p-1` + `w-3.5 h-3.5` 삭제 SVG. `opacity-0 group-hover:opacity-100`이라 모바일에서 영영 노출되지 않음 — 이중 BLOCKER |

### MAJOR (24~32px / 인접 겹침 위험)

| # | 파일 | 라인 | 문제 |
|---|------|------|------|
| T-M1 | `components/admin/news/MLCompareView.tsx` | 118 | `p-1` + `h-4 w-4` ≈ 24px. 최소 통과지만 안전 마진 없음 |
| T-M2 | `components/screener/PresetGallery.tsx` | 241-248 | `text-[10px]` + `w-3 h-3` 아이콘 "상세 설명" 버튼. 카드 클릭 영역과 4px 간격 — 오탭 위험 |
| T-M3 | `components/screener/PresetGallery.tsx` | 218 | `text-[10px] px-1.5 py-0.5` 활성 배지(`적용중`/`N차`). 약 14~16px |
| T-M4 | `components/thesis/builder/NewsSelector.tsx` | 142 | `p-1` + `ArrowLeft size={20}` ≈ 28px. 헤더 백 버튼 |
| T-M5 | `components/news/StockInsightCard.tsx` | 114-119 | `text-xs` + `w-3 h-3` 인라인 "종목 보기" 링크. 줄 안 작은 화살표 |
| T-M6 | `components/validation/LeaderComparisonSection.tsx` | 70 | `text-xs` + `w-3 h-3` "상세 N개 더 보기/접기" 인라인 토글 |
| T-M7 | `components/validation/PeerContextBar.tsx` | 120 | `text-xs` + `w-3 h-3` "peer 목록 보기/접기" |
| T-M8 | `components/screener/AdvancedFilterPanel.tsx` | 236-271 | 카테고리 탭 `px-3 py-1.5 text-xs` ≈ 24px |
| T-M9 | `components/validation/PeerContextBar.tsx` | 37-49 | 프리셋 탭 `px-3 py-1 text-xs` ≈ 22~24px |
| T-M10 | `components/admin/NewsCategoryManager.tsx` | 380 | `gap-1`(4px)로 ActionButton + Edit + Delete 인접 — 오탭 |
| T-M11 | `components/screener/AdvancedFilterPanel.tsx` | 120-139 | 입력 + 클리어 X가 `gap-2`로 인접, 클리어가 22px |

### MINOR
- `components/eod/SignalDetailSheet.tsx:152` `w-3.5 h-3.5` Chevron — 부모 버튼이 충분하면 OK
- 일반 `text-xs` 인라인 링크 다수 — 줄 안에 들어가는 한도 내에서는 허용 가능

### 화면별 우선 점검 결과
- **Thesis 관제실 카드**: `OptionButton`의 Info(22px, 모바일 미노출), `NewsSelector` Back(28px), `AddIndicatorSheet`의 `gap-1.5` 칩 그룹 → 카드 자체 hit 영역은 큼, 부속 토글이 위험
- **Validation 프리셋 탭**: `PeerContextBar` 탭 22~24px + 인라인 펼침/접힘 → 모두 MAJOR
- **ChainSight 노드**: Canvas 기반(react-force-graph-2d)이라 DOM 측정 불가, 노드 크기 prop `nodeRelSize`로 제어. 작은 노드는 손가락 탭 어려움 (별도 차트 섹션 참조)

---

## 네비게이션

### BLOCKER

| # | 영역 | 파일 | 문제 |
|---|------|------|------|
| N-B1 | BottomNav 탭 부족 | `components/layout/MobileNav.tsx` | 탭 5개(홈/종목/뉴스/포트폴리오/마이페이지)만 노출. **Thesis(가설 통제실), Screener, ChainSight, AI Analysis, Market Pulse v2, Watchlist, Thesis New가 모두 누락** |
| N-B2 | 헤더 모바일 드롭다운 | `components/layout/Header.tsx:42, 168` | 데스크톱 nav `hidden md:flex` + 드롭다운 `md:hidden`. 토글 버튼은 `hidden`(line 157, "audit P0 #12") 처리되어 **모바일에서 드롭다운을 펼칠 트리거가 없음** — Header 메뉴가 숨김 상태로 유지 |
| N-B3 | Thesis 진입 동선 부재 | `app/thesis/(list)/page.tsx`, `app/thesis/new/page.tsx` | BottomNav 미포함, Header도 위 N-B2로 닫힘. 모바일 사용자가 가설 통제실에 도달할 경로 없음 |

### MAJOR

| # | 영역 | 파일 | 문제 |
|---|------|------|------|
| N-M1 | Screener 진입 | Header만 (N-B2로 닫힘) | BottomNav 미포함 |
| N-M2 | ChainSight 진입 | — | BottomNav/Header 양쪽 모두 |
| N-M3 | AI Analysis 진입 | `app/ai-analysis/page.tsx` | 진입점 없음 + 복잡 UI |
| N-M4 | Market Pulse v2 | `app/market-pulse-v2/page.tsx` | 진입점 없음 |
| N-M5 | Thesis 서브 페이지 padding | `app/thesis/[thesisId]/close/page.tsx`, `.../indicators/page.tsx` | 본문 `pb-4` 만 — 64px BottomNav가 액션 버튼 가림. `(list)/layout.tsx`는 `pb-20`으로 정상 처리되어 있음 |
| N-M6 | 모바일 long-list virtualization 부재 | 전 영역 | `react-window`/`@tanstack/react-virtual` 의존 없음. News(100건 batch), Screener(50/page), Thesis 목록, ChainSight 노드 리스트 — 모두 전체 렌더링 |

### MINOR

- `app/dashboard/page.tsx` 와 `app/page.tsx`(홈) 중 BottomNav `홈` 탭이 어디로 가는지 일관성 검토 필요
- 모달들(`SharePresetModal`, `NewsDetailModal`, `BottomSheet`)은 `p-4 max-w-*`로 모바일 대응 OK. `NewsDetailModal`은 `max-w-3xl`이지만 컨테이너 패딩으로 흡수
- BottomSheet(`components/thesis/builder/BottomSheet.tsx`, `components/thesis/common/BottomSheet.tsx`, `components/eod/SignalDetailSheet.tsx`) — 드래그 바 + `max-h-[50vh]`로 best practice

### 페이지 ↔ 진입 동선 매트릭스

| 페이지 | BottomNav | Header (모바일) | 다른 진입 | 평가 |
|--------|:---------:|:----------------:|----------|------|
| `/` (홈/대시보드) | 홈 | (닫힘) | - | OK |
| `/stocks` | 종목 | - | - | OK |
| `/news` | 뉴스 | - | - | OK |
| `/portfolio` | 포트폴리오 | - | - | OK (테이블 별도) |
| `/mypage` | 내정보 | - | - | OK |
| `/thesis` (목록) | ✗ | ✗ | - | **BLOCKER** |
| `/thesis/[id]` | ✗ | ✗ | 목록 경유 | BLOCKER (목록 못 감) |
| `/thesis/new` | ✗ | ✗ | - | BLOCKER |
| `/thesis/[id]/close`, `/indicators` | ✗ | ✗ | 상세 경유 | MAJOR (pb-4 겹침) |
| `/screener` | ✗ | ✗ | - | BLOCKER |
| `/chainsight` 및 하위 | ✗ | ✗ | - | BLOCKER |
| `/ai-analysis` | ✗ | ✗ | - | BLOCKER |
| `/market-pulse-v2` | ✗ | ✗ | - | BLOCKER |
| `/watchlist` | ✗ | ✗ | - | MAJOR |
| `/admin` | ✗ | ✗ | 관리자 한정 | MINOR |
| `/dashboard` | (홈과 중복?) | - | - | MINOR (확인 필요) |
| `/login`, `/signup` | - | - | - | OK |

---

## 차트/그래프

### BLOCKER

| # | 파일 | 문제 |
|---|------|------|
| C-B1 | 모든 Recharts 컴포넌트 | **Hover-only Tooltip**. `onMouseMove` 기반이라 터치 디바이스에서 작동 안 함. `StockChart`(363-430), `StockPriceChart`(64-96), `SentimentChart`(210-246), `YieldCurveChart`(110-119), `PortfolioChart`(33-52), `MetricBarChart`(92-105), `MLTrendChart`(30-42) 등 — 차트 값 자체를 읽을 수 없음 |
| C-B2 | `components/chainsight/GraphCanvas.tsx`, `MarketGraphCanvas.tsx` | **터치 제스처 미구현**. react-force-graph-2d는 마우스 휠/드래그만 지원. 핀치 줌·팬 핸들러 없음. 모바일에서 그래프 사용 불가. 초기 width 800px 디폴트로 좁은 모바일에서 잘림 |
| C-B3 | `app/market-pulse-v2/details/RegimeDetail.tsx` | **RadarChart 모바일에서 판독 불가**. 280px 고정 높이, KEY_LABELS 15개+ 항목이 320px 폭에서 라벨 완전 겹침 |

### MAJOR

| # | 파일 | 라인 | 문제 |
|---|------|------|------|
| C-M1 | `components/portfolio/PortfolioChart.tsx` | 77, 97 | PieChart·BarChart `<ResponsiveContainer height={400}>` 고정. 모바일에서 vh 과점유 |
| C-M2 | `components/screener/SectorHeatmap.tsx` | 216, 220 | Treemap `height={400}`, `aspectRatio=4/3`. 11개 섹터가 320×240에서 라벨 표시 임계(`width<60 || height<40` 시 hide) |
| C-M3 | `components/charts/StockPriceChart.tsx` | 40 | 디폴트 `height = 400`, 리사이즈 핸들러 없음 |
| C-M4 | `app/market-pulse-v2/details/SectorDetail.tsx` | 37, 61 | BarChart 240/200px 인라인 고정. 모달(CardDrawer) 안이라 더 협소 |
| C-M5 | `app/market-pulse-v2/details/FlowDetail.tsx` | 42 | PieChart 260px + 가로 Legend (10+ 섹터) 줄바꿈 |
| C-M6 | `components/chainsight/GraphCanvas.tsx`, `MarketGraphCanvas.tsx` | 53 | 모바일 노드 라벨(티커+회사명) 겹침. `nodeRelSize` 작아도 라벨은 그대로 |
| C-M7 | `components/thesis/dashboard/QuarterlySparkline.tsx` | 33, 36, 54 | `h-10`(40px), `gap-1`, `text-[8px]` 분기 라벨. 20분기에서 막대 6~8px, 라벨 판독 불가 — 메모리에 저장된 "전분기대비 라벨 필수" 원칙과 정합성 검토 필요 |

### MINOR (높이/마진/라벨 미세 조정)

| 컴포넌트 | 파일 | 라인 | 비고 |
|----------|------|------|------|
| YieldCurveChart | `components/macro/YieldCurveChart.tsx` | 92 | 부모 `h-64` 고정 |
| SentimentChart | `components/news/SentimentChart.tsx` | 79 | `h-80` 고정 |
| MetricBarChart | `components/validation/MetricBarChart.tsx` | 72 | `h-48` 고정 |
| BreadthDetail | `app/market-pulse-v2/details/BreadthDetail.tsx` | 41, 45 | 200px + `tick fontSize:10` |
| IndividualMiniCharts | `components/thesis/dashboard/IndividualMiniCharts.tsx` | 54 | AreaChart 100px 고정 |
| MiniSparkline | `components/eod/MiniSparkline.tsx` | 9 | 80×24 고정 |
| StockChart Legend | `components/stock/StockChart.tsx` | 163 | layout 미지정, 좁은 폭에서 줄바꿈 |
| 차트 margin | StockChart `right:60`, PortfolioChart `bottom:60` | 653, 100 | 모바일에서 면적 손실 |
| 축 fontSize | 다수 | - | 12px 고정 — 표시는 되나 빽빽 |
| Pie Legend | FlowDetail | 51 | `fontSize:11` + 다항목 줄바꿈 |

### 잘 된 사례
- `components/stock/StockChart.tsx:177-187`의 `getResponsiveChartHeight()`는 동적 높이 계산의 모범. 다른 차트도 동일 패턴으로 마이그레이션 권장.
- 모든 핵심 차트가 `<ResponsiveContainer width="100%">`를 쓰고 있어 폭은 유연함.

---

## 페이지별 상세

### `/` (Home / Dashboard)
- **반응형**: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6` (good)
- **터치/네비**: BottomNav `홈` 진입 정상
- **차트**: `MiniSparkline` 사용 — MINOR

### `/stocks` 및 `/stocks/[symbol]`
- **반응형**: 상세 페이지 `grid grid-cols-2 gap-4`(line 329) 모바일 미대응 → **R-B3 BLOCKER**. line 568은 sm 누락 (MAJOR)
- **터치**: `StockTable` `px-6` (R-M1)
- **차트**: `StockChart` 동적 높이 OK / **C-B1**(Tooltip)
- **네비**: BottomNav `종목`

### `/news`
- **반응형**: NewsList — OK
- **터치**: `StockInsightCard` 인라인 링크 (T-M5)
- **차트**: `SentimentChart` `h-80` 고정 (MINOR)
- **장기 위험**: 100건 batch + virtualization 없음 (N-M6)

### `/portfolio`
- **반응형**: 카드 그리드 `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` OK
- **테이블**: `PortfolioTable.tsx` 12개 컬럼 → **R-B1 BLOCKER**
- **차트**: `PortfolioChart` 400px 고정 (C-M1) + Tooltip (C-B1)
- **네비**: BottomNav `포트폴리오`

### `/watchlist`
- **반응형**: 7개 컬럼 테이블 → **R-B2 BLOCKER**
- **네비**: 진입 동선 없음 (N-M MAJOR)

### `/screener`
- **반응형**: 페이지 레벨 `hidden sm:block` 테이블 + `MobileStockCard` 분기 OK. `MarketBreadthCard` `grid-cols-3` (MINOR)
- **터치**: `PresetDetailPopover` X(T-B3), `AdvancedFilterPanel` X·필터삭제(T-B1·T-B5), `PresetGallery` 차순배지·삭제·Info(T-B2·T-B7·T-M2)
- **차트**: `SectorHeatmap` 400px (C-M2) + Tooltip (C-B1)
- **네비**: BottomNav 진입 없음 (**N-B 누락**)

### `/thesis` (목록 / 상세 / new / close / indicators / alerts)
- **반응형**: `(list)/layout.tsx` `max-w-lg pb-20` good. `ThesisSkeleton` 일부 (MINOR)
- **터치**: `OptionButton` Info 모바일 미노출(T-B6), `NewsSelector` Back(T-M4), `AddIndicatorSheet` `gap-1.5`(R-MINOR)
- **차트**: `QuarterlySparkline` 막대·라벨 작음(C-M7), `IndividualMiniCharts` 100px(MINOR), `IndicatorPanel` 다수
- **네비**: **목록·new·close·indicators 전부 BottomNav/Header 미연결 (N-B3, N-M5)**. close/indicators 페이지 `pb-4` 누락으로 BottomNav가 액션 버튼 덮을 가능성

### `/chainsight` 및 하위
- **반응형**: `MobileCardList`는 모바일 친화. 하지만 자동 전환 트리거 명확치 않음
- **터치**: 그래프 노드 자체가 작음
- **차트**: **C-B2 BLOCKER** (터치 제스처 부재 + 초기 width)
- **네비**: 진입점 부재 (N-M2)

### `/ai-analysis`
- **반응형**: ChatInterface + DataBasket 복잡 레이아웃, 모바일 검토 부재
- **네비**: 진입점 부재 (N-M3)

### `/market-pulse-v2`
- **반응형**: 카드/디테일 전반 `grid-cols-2`/`grid-cols-3` 하드코딩 (R-M4·M5·M6·M7)
- **차트**: BarChart/PieChart/RadarChart 인라인 고정 (C-M4·M5, **C-B3 BLOCKER**)
- **네비**: 진입점 부재 (N-M4)

### `/admin`
- **반응형**: 다수 관리자 테이블에 동일 패턴 (운영 한정으로 우선순위 낮음)
- **터치**: `NewsCategoryManager` Edit/Delete(T-B4) **BLOCKER**, `MLCompareView` X(T-M1)
- **차트**: `MLTrendChart` Tooltip (C-B1)
- **네비**: 진입점 없음 (관리자 한정 OK)

### `/login`, `/signup`
- **반응형**: `grid grid-cols-2`(R-M3 MAJOR), 그 외 OK

---

## 부록: 우선순위 권장 (참고)

> 본 보고서는 읽기 전용 감사이며, 아래는 작업 분류 시 참고용 우선순위 제안임.

**Phase 1 — BLOCKER 14건**
1. BottomNav 탭 재설계 또는 Header 모바일 hamburger 복구 (N-B1·B2·B3, 8개 페이지 진입 회복)
2. PortfolioTable / WatchlistTable 모바일 카드 뷰 (R-B1·B2)
3. 검색 인풋 X / Edit·Delete / 차순 배지 / 가설 빌더 Info 패딩 보강 (T-B1~T-B7)
4. 차트 Tooltip 터치 대응 + ChainSight 그래프 핀치/팬 (C-B1·B2)
5. RadarChart 모바일 대체 뷰 (C-B3)

**Phase 2 — MAJOR 35건**
- 테이블 패딩 `px-2 sm:px-4 lg:px-6` 일괄, 차트 높이 `h-48 md:h-80` 패턴, Thesis close/indicators `pb-20`, 진입점 누락 보강

**Phase 3 — MINOR**
- `grid-cols-N` → `grid-cols-1 sm:grid-cols-N` 일괄, 차트 축 폰트/마진 모바일 분기, 분기 스파크라인 막대/라벨 크기 재설계

**테스트 체크리스트**
- 375px(iPhone SE) / 390px(iPhone 13) / 414px(Plus) 뷰포트
- iOS Safari 터치 (hover-tooltip 검증), Android Chrome
- 라이트/다크 모드, 가로/세로 회전
- BottomNav 64px 와 본문 액션 버튼 겹침 확인
