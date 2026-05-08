# 모바일 UX 감사 보고서

**작성일**: 2026-05-08
**대상**: stock-vis frontend (Next.js 16 + Tailwind v3)
**기준 뷰포트**: iPhone SE 가로 375px / Android Compact 360px
**기준 가이드라인**: Apple HIG 44×44pt, Material Design 48×48dp
**모드**: 읽기 전용 감사 (코드 수정 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 이슈 수 | 주요 영역 |
|--------|---------|----------|
| **BLOCKER** | 3 | Portfolio Table, ScreenerTable, Stocks 상세 페이지 |
| **MAJOR** | 11 | Thesis 관제실, Validation Sidebar, Chainsight 그래프, Mobile Nav 라우트 누락, 데스크톱 헤더 검색, 차트 가독성, EOD MarketSummaryBar 등 |
| **MINOR** | 9 | text-[10/11px] 클릭 요소, 작은 아이콘 버튼, 작은 배지 등 |

**총 이슈 수**: 23건
**1차 우선순위 화면**: ① Portfolio Table ② Stocks 상세 ③ Thesis 관제실 ④ Chainsight Detail
**대응 가능 화면 (모바일 친화)**: 홈 (`/`), Thesis 목록·생성·관제실, Screener (MobileStockCard), Chainsight 메인 (`MobileCardList` 분기 존재)

---

## 반응형 누락

코드베이스 통계
- 고정 폭 클래스(`w-[NNpx]` / `min-w-[NNpx]` / `max-w-[NNpx]`) 사용: **20개 파일, 27건**
- `text-[10/11/12px]` 사용 (클릭 요소 다수 포함): **50개 파일, 117건**

### BLOCKER 1. Portfolio Table — 12 컬럼 데스크톱 전용 테이블, 모바일 카드 분기 부재
- 파일: `frontend/components/portfolio/PortfolioTable.tsx`
- 현상: `<table>`이 12개 컬럼 (`종목/수량/평균가/현재가/전일대비/평가금액/손익/수익률/목표가/손절가/비중/관리`) 을 가지며 `overflow-x-auto`(259) 만 적용됨.
  - 컬럼별 padding `px-6 py-4` (255~298) → 컬럼당 ~120px ⇒ **테이블 폭 ≈ 1,440px**
  - 375px 화면에서 가로 스크롤이 4배 발생, 헤더는 sticky가 아님 → 스크롤 시 어떤 컬럼인지 식별 불가.
  - `overflow-x-auto` 컨테이너는 부모 `<div className="bg-white ... overflow-hidden">` (258) 에 의해 한 번 더 감싸져 있어 스크롤 컨트롤이 모호.
- 영향: 사용자는 모바일에서 본인 포트폴리오 손익을 한눈에 확인할 수 없음 (핵심 화면 차단).
- 메모: `frontend/components/portfolio/PortfolioStockCard.tsx`는 별도로 존재하지만 `app/portfolio/page.tsx`의 `viewMode='table'` 분기에서는 모바일에서도 무조건 테이블이 렌더됨. 모바일 분기 부재.

### BLOCKER 2. Stocks 상세 — Tab 시스템 + 재무제표 테이블 비반응형
- 파일: `frontend/app/stocks/[symbol]/page.tsx`
- 현상: L1 탭 3개 + L2 탭 5개(fundamentals)가 `flex` 일렬 배치, 모바일에서 좁은 폭에 `Balance Sheet`, `Income Statement`, `Cash Flow`, `기타 펀더멘탈`이 다 들어가지 못함.
- 재무제표 테이블 (Balance/Income/Cash Flow)은 `overflow-x-auto`만 있고 컬럼은 모든 분기를 펼친 wide table → 가로 스크롤 깊음, sticky 헤더 없음.

### BLOCKER 3. Strategy/ScreenerTable — `max-w-[180px]/[120px]/[200px]` + 12 컬럼 wide
- 파일: `frontend/components/strategy/ScreenerTable.tsx:127-336`
- 현상: 12개 컬럼 (종목/거래소/섹터/가격/변동률/시가총액/거래량/배당률/베타/유형/AI키워드/액션) → 데스크톱 전용. `overflow-x-auto`만 적용.
- `app/screener/page.tsx`에 `MobileStockCard` 컴포넌트가 존재하나, 자동 전환되지 않고 사용자가 `viewMode` 토글을 명시적으로 눌러야 카드뷰로 전환됨 → 첫 진입에서 모바일 사용자는 가로 스크롤 테이블을 만남.

### MAJOR 1. Validation `CategorySidebar` — `sticky top-24 space-y-1` 사이드바, 모바일 분기 없음
- 파일: `frontend/components/validation/CategorySidebar.tsx`
- 현상: `<nav className="sticky top-24">`로 데스크톱 사이드바를 가정. 모바일에서는 sticky가 위쪽에 메뉴가 박힌 채 본문과 겹치거나, 부모 그리드 레이아웃 (예: `grid lg:grid-cols-[200px_1fr]`)에서 전체 폭을 차지하게 됨.
- 7개 카테고리(`재무체질/현금흐름/수익성/성장성/안정성/효율성/밸류에이션`) 사이드바 → 모바일에서 가로 칩/탭 또는 BottomSheet로 전환되지 않음.

### MAJOR 2. SignalSummaryCard 7개 신호등 — `min-w-[72px]`로 가로 스크롤 발생
- 파일: `frontend/components/validation/SignalSummaryCard.tsx:36-62`
- 현상: 7개 카테고리 × 72px = **504px** → 375px 모바일에서 `overflow-x-auto`로 가로 스크롤. 첫 화면에 4개만 보이고 나머지 3개는 잘림.
- `scrollbar-hide`로 스크롤바도 숨겨져 있어 추가 컨텐츠 존재 표시(affordance) 부재.

### MAJOR 3. Chainsight `MarketGraphCanvas` — `h-[400px]` 고정, force-graph 모바일 인터랙션
- 파일: `frontend/components/chainsight/MarketGraphCanvas.tsx:140`
- 현상: `<div className="relative h-[400px]">`로 높이 고정. 모바일 가로폭이 좁아 노드/엣지 라벨 (`8px ~ 10px sans-serif`, 218~219, 225) 이 가독 불가.
- `containerWidth`는 ResizeObserver로 받지만(63), 모바일에서 노드가 빽빽하게 겹쳐 force layout이 안정될 때까지 시각적 노이즈 큼. 핀치 줌은 react-force-graph 기본 지원하나, 노드 클릭 영역(`getNodeRadius` 8~16) 이 좁아 터치 정확도 떨어짐.

### MAJOR 4. Chainsight `[symbol]` Detail — 모바일 분기 일부 존재하나 그래프 그대로 노출
- 파일: `frontend/components/chainsight/MobileCardList.tsx`
- 현상: `MobileCardList`는 카드 리스트 + 카테고리 탭으로 모바일 친화적이지만, 부모 페이지가 자동으로 모바일에서 카드뷰로 분기하는지 확인 필요. 페이지에서 `onShowGraph` 토글로 전환 가능하나, 그래프 보기 진입 후 돌아갈 명시적 UI 없음 (FAB만).
- `text-[10px]` 태그(149/154/159) 와 카드 액션 버튼 `py-1.5`(169/175/181) 은 권장 44pt 미만.

### MAJOR 5. Header 데스크톱 검색바 + 햄버거 비활성화
- 파일: `frontend/components/layout/Header.tsx:112-163`
- 현상: 데스크톱 검색바(`hidden md:block`) + 햄버거 버튼 (`hidden`로 강제 숨김, 156-163) → 모바일에는 검색 진입점 없음.
- `MobileNav`(BottomNav) 가 검색을 포함하지 않아 모바일 사용자는 종목 검색을 시작할 진입점이 부재.
  - 코드 주석: "audit P0 #12: Header 햄버거를 모바일에서 비표시 (MobileNav가 모바일 네비 단일 소스)" — 현재는 검색 부재가 잔존.

### MAJOR 6. Thesis `IndicatorRow` — 인라인 메타 폭 부족 (`min-w-[60px]`+`min-w-[120px]`+`max-w-[100px]`+ 우측 ml-auto 라벨)
- 파일: `frontend/components/thesis/dashboard/IndicatorRow.tsx:108-144`
- 현상: 한 줄 안에 **값(60px)+변동률(120px)+스파크라인(100px)+지지/반박 라벨**이 들어감 = 약 280~300px. 좌측 padding `pl-4`까지 더하면 **모바일 320~375px에서 스파크라인이 잘리거나 지지/반박 라벨이 줄바꿈**.
- 1행의 이름 라벨은 `truncate flex-1`이지만 dateLabel `text-[11px]`(95)가 옆에 붙어 짧은 가설 이름도 잘림.

### MAJOR 7. AI 키워드 / Recommendation 카드 — 가로 스크롤 강제
- 파일들: `frontend/components/news/AINewsBriefingCard.tsx:70` (`max-w-[200px]` 진행바), `frontend/components/news/RecommendationCard.tsx:85` (`max-w-[150px]` truncate).
- 현상: 카드가 좁은 모바일에서 truncate 되며 핵심 키워드/회사명이 보이지 않음.

### MAJOR 8. RAG ChatInterface — `h-[52px] w-[52px]` 송신 버튼 + 입력 영역 고정
- 파일: `frontend/components/rag/ChatInterface.tsx:198`
- 현상: 송신 버튼 자체는 52×52로 충분하나, 입력 폼이 모바일 가상 키보드 노출 시 `100dvh` 미적용으로 채팅 컨테이너 높이가 흔들리는지 점검 필요. (코드상 명시적 `100dvh`/`100svh` 사용 없음).

### MAJOR 9. EOD `SignalDetailSheet` 사이드 시트 — `md:w-[420px] md:h-full`
- 파일: `frontend/components/eod/SignalDetailSheet.tsx:97`
- 모바일에서는 bottom sheet (`w-full`)로 동작하므로 OK. 다만 Sticky 헤더의 카테고리 칩과 정렬 메뉴가 `text-[11px]` 인 영역이 있어 (StockRow 89-93) 가독성·터치성 저하.

### MAJOR 10. Strategy/Screener 상단 액션 — 데스크톱 가정 가로 배치
- 파일: `frontend/app/screener/page.tsx`
- 현상: 헤더에 `Search/RefreshCw/Sparkles/Grid/List/Lightbulb/Share2/X/AlertTriangle/AlertCircle/BarChart3/Loader2` 아이콘 다수 (5)에 `viewMode` 토글, `MAX_PRESETS=3`(31), 활성 프리셋 표시 등이 모바일 작은 폭에서 wrap이 보장되는지 확인 필요. 페이지 본체가 길어 검토 추가 필요.

### MAJOR 11. SectorBar — 가로 스크롤 + `max-w-[120px]` 라벨 truncate
- 파일: `frontend/components/chainsight/SectorBar.tsx:24-55`
- 현상: 11개 섹터 칩이 가로 스크롤 (24, `flex gap-2 overflow-x-auto`). 라벨이 `text-xs` 외 추가 `text-xs mt-0.5` 변동률 → 칩 높이 ~60px, 터치 OK이지만 변동률이 `+0%` 처럼 짧을 때 칩 사이 간격이 부족.

### MINOR 1. Header `max-w-[1400px]` 컨테이너
- 파일: `frontend/components/layout/InvestingHeader.tsx:32, 55, 99`
- 모바일 px-4 적용되어 issue 없음. 데스크톱 가정 폭이지만 모바일 영향 없음.

### MINOR 2. ScreenerTable `max-w-[180px]/[120px]/[200px]` truncate
- 파일: `frontend/components/strategy/ScreenerTable.tsx:209/224/307`
- 현상: 데스크톱 테이블 내부 셀이라 BLOCKER 3에 포함됨. 모바일에서는 카드뷰 전환이 안정화되면 자연 해소.

---

## 터치 타겟

기준: **44×44pt** (Apple HIG) / 48×48dp (Material). 미만이면 오작동·오터치 가능.

### MAJOR 12. ThesisListCard 카드 자체는 OK이나 내부 액션 부재
- 파일: `frontend/components/thesis/list/ThesisListCard.tsx`
- 카드 전체가 Link로 충분히 큼 (✅). 다만 카드 내 ChevronRight(42)는 비클릭 장식.

### MAJOR 13. Thesis `PeriodSelector` — `px-3 py-1.5 text-xs` (≈ 28px 높이)
- 파일: `frontend/components/thesis/dashboard/PeriodSelector.tsx:18`
- 현상: 4개 기간 버튼(1M/1Y/3Y/5Y)이 약 **28px 높이** → 44pt 미달. 그룹 간 `gap-2`로 살짝 확장은 되지만 단일 타깃은 미달.
- 동일 패턴: `IndicatorRow.tsx:179-189` 의 `px-2.5 py-0.5 text-[10px]` 차트 기간 버튼도 **약 16px 높이** → BLOCKER 수준 (관제실 진입 후 차트 내부).

### MAJOR 14. Thesis `IndicatorSetupCard` — `Power`/`Trash2` 아이콘 버튼 `p-2`
- 파일: `frontend/components/thesis/indicators/IndicatorSetupCard.tsx:48-69`
- 현상: `<button className="p-2 rounded-lg">`에 lucide `size={16}` → **약 32×32px** 터치 영역. 44pt 미달. 두 버튼이 `gap-1`로 인접 → 오터치 위험.

### MAJOR 15. Validation `PeerContextBar` 프리셋 칩 — `px-3 py-1 text-xs`
- 파일: `frontend/components/validation/PeerContextBar.tsx:37-50`
- 현상: 프리셋 탭 (`growth_g3/large_cap/...`) 각 칩이 약 **24px 높이**로 매우 작음. 다중 옵션이 있고 가로 wrap (`flex flex-wrap`) 되어 있어 인접 칩 간 오터치 가능성 큼.

### MAJOR 16. Chainsight `RelationCardPanel` Deep/가설/탐색 3-버튼 — `py-1 px-2 text-xs`
- 파일: `frontend/components/chainsight/RelationCardPanel.tsx:240-257`
- 현상: 카드당 3개 버튼이 좁은 카드 폭에 들어가 한 버튼당 약 60-90px 폭, 24px 높이. 44pt 미달.

### MINOR 3. Mobile Nav 자체는 충분 (`min-h-[44px]` 명시)
- 파일: `frontend/components/layout/MobileNav.tsx:34`
- ✅ `min-h-[44px]` + `flex-1` + `h-16(64px)` 컨테이너 → 가이드라인 충족.

### MINOR 4. `text-[10px]` 클릭 요소 — 36개 라인
- 대표 위치:
  - `frontend/app/screener/page.tsx:528` — 활성 프리셋 번호 배지 (16×16) (활성 표시 전용, 반드시 클릭 안 됨)
  - `frontend/app/thesis/new/page.tsx:752-1063` — 가설 빌더 7개 위치에서 `text-[10px]` 라벨/버튼.
  - `frontend/components/eod/SignalFilterTabs.tsx:68` — `min-w-[18px] h-[18px] text-[11px]` 카운트 배지 (배지 자체는 클릭 안 됨, OK)
  - `frontend/components/eod/StockRow.tsx:89, 92` — 시그널 라벨 (장식)
  - `frontend/components/screener/PresetDetailPopover.tsx:121` — popover 내부 텍스트 (장식)

### MINOR 5. `Pagination` 페이지 버튼 — `min-w-[32px] px-2 py-1.5 text-sm`
- 파일: `frontend/components/screener/Pagination.tsx:127`
- 현상: 페이지 번호 버튼이 32×32 정도 → 44pt 미달. 페이지네이션은 보통 다중 버튼 인접이라 오터치 가능.

### MINOR 6. SeedBadge / DisplayTypeBadge — `text-[10px] px-1.5 py-0.5`
- 파일: `frontend/components/chainsight/RelationCardPanel.tsx:265-292`
- 배지는 비클릭 (장식) 이므로 가독성만 문제. 다크모드 대비는 양호.

### MINOR 7. KeywordTag/KeywordList — `text-[10px]/[11px]`
- 파일들: `frontend/components/keywords/KeywordTag.tsx`, `KeywordList.tsx`
- 클릭 가능한지 확인 필요. 단순 표시면 OK. 키워드 검색 진입점이라면 44pt 미달.

### MINOR 8. EOD `MarketSummaryBar.tsx:48` — `text-[10px]` 비율 표시
- 장식 텍스트, 클릭 안 됨, OK.

### MINOR 9. `RecommendCard` / `AlertCard` — `text-[10px]/[11px]` 다용
- 파일들: `frontend/components/thesis/indicators/RecommendCard.tsx` (3건), `frontend/components/thesis/alerts/AlertCard.tsx` (3건)
- 카드 내부 액션이 작은 폰트 + 작은 패딩일 가능성. 상세 검토 권장.

---

## 네비게이션

### 모바일 네비게이션 ✅ MobileNav 존재
- 파일: `frontend/components/layout/MobileNav.tsx`
- BottomNav 5개 항목: 홈/종목/뉴스/포트폴리오/내정보
- `md:hidden`로 모바일 전용, `min-h-[44px]` 명시 ✅
- ⚠ **MAJOR 누락**: 핵심 기능인 **Thesis Control / Screener / Chainsight** 가 BottomNav에 없음. 사용자가 모바일에서 가설 통제실에 진입할 단축 경로가 없고, Header(데스크톱 전용)에 있는 Thesis Control 링크는 모바일 햄버거가 비활성화되어 접근 불가.
- ⚠ **MINOR**: `'/종목'` 항목이 `/stocks` 인데 stocks 인덱스 페이지가 없음 — 진입 시 `/stocks`만 입력하면 빈 페이지 또는 404 발생 가능 (코드베이스에 `app/stocks/page.tsx` 없음, `app/stocks/[symbol]/page.tsx`만 존재).

### 사이드바 모바일 대응
- `frontend/components/validation/CategorySidebar.tsx` — sticky 사이드바, 모바일 분기 없음 (MAJOR 1).
- 다른 사이드바 패턴 미발견. 대부분 화면이 stacked 레이아웃.

### 긴 목록 virtualization
- `react-window`/`react-virtualized` 사용 흔적 없음 (`grep -r "react-window"` 결과 0건).
- 영향 큰 화면:
  - **Screener**: Pagination으로 처리 → OK
  - **Watchlist**: 페이지네이션 또는 limit 처리되는지 미확인 (별도 점검 필요)
  - **News 목록**: 무한 스크롤 또는 virtualization 없으면 모바일에서 메모리 압박 가능
  - **EOD 시그널 카드 그리드**: 카테고리 필터로 분할되지만 ALL 탭에서는 14개 카드 모두 렌더 (소량이라 OK)
  - **Thesis 관제실 IndicatorRow**: 가설당 보통 5~15개라 OK

---

## 차트/그래프

### Recharts 사용 현황 (15 파일)
ResponsiveContainer **사용** 파일:
- `frontend/app/market-pulse-v2/details/{Sector,Regime,Flow,Breadth}Detail.tsx` ✅
- `frontend/components/thesis/dashboard/IndicatorRow.tsx` ✅
- `frontend/components/thesis/dashboard/IndividualMiniCharts.tsx` ✅
- `frontend/components/validation/MetricBarChart.tsx` ✅
- `frontend/components/admin/news/MLTrendChart.tsx` ✅
- `frontend/components/screener/SectorHeatmap.tsx` ✅
- `frontend/components/stock/StockChart.tsx` ✅
- `frontend/components/news/SentimentChart.tsx` ✅
- `frontend/components/macro/YieldCurveChart.tsx` ✅
- `frontend/components/portfolio/PortfolioChart.tsx` ✅
- `frontend/components/charts/StockPriceChart.tsx` ✅

→ ResponsiveContainer 미적용 차트는 발견되지 않음. ✅

### MAJOR 17. 차트 폰트 사이즈 모바일 가독성
- IndicatorRow XAxis `fontSize={9}` (207, 248), YAxis `fontSize={10}` (211, 252) → **모바일 가독성 한계치**.
- ResponsiveContainer 높이 `height={160}` (197), `height={140}` (235) — 적당. 그러나 X/Y 축 폭 (`width={55}`, `width={50}`) 이 크면 데이터 영역이 더 작아짐.
- `formatRawValue`로 단위 변환은 적용되나 1Y/3Y/5Y에서 X축 라벨 잘림 발생 가능 (`interval` 보정 있음, 208).

### MAJOR 18. QuarterlySparkline — 4분기 미니바 차트
- 파일: `frontend/components/thesis/dashboard/QuarterlySparkline.tsx`
- 부모 `max-w-[100px]` (`IndicatorRow.tsx:132`) 영역에 들어감 → 4분기 바 + Q1/Q2/Q3/Q4 라벨이 `text-[8px]` (54)
- **8px는 가독성 한계 미만**. 라벨이 보이긴 하나 시각적 노이즈에 가까움.
- 호버 툴팁 `text-[10px]` (59) — 모바일에선 호버가 없으므로 (탭 = 클릭) 분기값을 확인할 인터랙션 부재.

### MAJOR 19. Chainsight Force Graph — 모바일 인터랙션 빈약
- `MarketGraphCanvas.tsx`: `cooldownTicks={100}`, `warmupTicks={50}` → 시뮬레이션 안정화에 시간 소요. 모바일 저성능 기기에서 첫 진입 lag 가능.
- 노드 라벨 `8px ~ 10px sans-serif` (218-219) — 가독 어려움.
- 핀치 줌은 react-force-graph 기본 지원이지만, `zoomToFit(400, 80)` (109) 후 사용자가 줌인하면 force가 다시 흔들리는 UX 문제.

### MINOR (정보) StockChart 등은 height prop 받음 → 컴포넌트 사용처에서 height를 넉넉히 주면 OK.

---

## 페이지별 상세

### 1. `/` 홈 (EOD Dashboard) — ✅ 모바일 친화 우수
- 파일: `frontend/app/page.tsx`
- BottomNav 보장 (`pb-20 md:pb-0`, 71)
- `max-w-6xl mx-auto px-4`로 단일 컬럼 + 카드 그리드
- SignalCard / SignalDetailSheet 모바일 분기 (sheet) 존재
- **MINOR**: SignalFilterTabs 카운트 배지 `text-[11px]` 가독성 그럭저럭, 클릭 영역은 탭 자체이므로 OK.

### 2. `/portfolio` — ❌ BLOCKER (테이블뷰가 모바일에서 차단)
- BLOCKER 1 참조.
- 카드뷰(`PortfolioStockCard`)가 있지만 디폴트가 `viewMode='grid'` 인지 `'table'`인지 page.tsx 24번 줄: `useState<'grid' | 'table'>('grid')` → 디폴트는 grid. ✅ **하지만** sticky 컬럼 헤더, 화면 폭 자동 분기 부재.

### 3. `/stocks/[symbol]` — ❌ BLOCKER
- BLOCKER 2 참조 (탭 + 재무제표 wide table).

### 4. `/screener` — ⚠ MAJOR 3
- BLOCKER 3, MAJOR 10 참조.
- 카드뷰 분기 (`MobileStockCard`) 존재 ✅, 그러나 자동 진입 없음.
- 프리셋 갤러리는 `flex flex-wrap`으로 OK이지만 프리셋 활성 표시 (`text-[10px]` 번호 배지) 작음.

### 5. `/news` — 검토 필요
- AINewsBriefingCard `max-w-[200px]` 진행바 (MAJOR 7), RecommendationCard truncate.
- 무한 스크롤/virtualization 미확인. 추가 검토 권장.

### 6. `/thesis` (목록) — ✅ 모바일 친화
- ThesisListCard가 `<Link>` 기반 카드 → 카드 자체가 큰 터치 영역. ✅

### 7. `/thesis/new` (대화형 빌더) — ⚠ MAJOR
- `text-[10px]` 라벨 7건 (752, 753, 765, 831, 843, 1063, 688) — 가설 방향 표시·전제 카드·거시/미시 그룹 라벨에 사용. 가독성 한계.
- BottomSheet UX 적용 (`builder/BottomSheet.tsx`) ✅

### 8. `/thesis/[thesisId]` (관제실) — ⚠ MAJOR 6
- IndicatorRow가 가로 폭 부족 (값+변동률+스파크라인+라벨이 380px 넘음).
- 하단 차트는 ResponsiveContainer 사용 ✅이지만 fontSize 9~10 가독성 한계.
- 토글 펼침 후 차트 기간 버튼(`text-[10px] py-0.5`) → ❌ **MAJOR (터치 타겟 16px)**.

### 9. `/thesis/[thesisId]/indicators` — ⚠ MAJOR 14
- IndicatorSetupCard의 Power/Trash 아이콘 버튼 32×32 → 44pt 미달.
- 100dvh 사용 (`h-[calc(100dvh-env(safe-area-inset-top))]`, 196) ✅

### 10. `/thesis/[thesisId]/close` — 검토 미상세
- `OutcomeSelector`, `CloseConfirmDialog` 존재. 추가 검토 권장.

### 11. `/thesis/(list)/alerts` — 검토 미상세
- AlertFilterTabs 가로 스크롤 가능, AlertCard `text-[11px]` 3건. 추가 검토 권장.

### 12. `/chainsight` — ⚠ MAJOR 3 (그래프) + MINOR
- SectorBar 가로 스크롤 ✅
- MarketGraphCanvas `h-[400px]` 고정, 노드/엣지 라벨 작음.
- RelationCardPanel `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` ✅ — 모바일은 1열.
- 카드 내부 3-버튼 (Deep/가설/탐색) 24px → MAJOR 16.

### 13. `/chainsight/[symbol]` — ⚠ MAJOR
- `MobileCardList` 분기 존재하나 자동 전환 여부 확인 필요.
- GraphCanvas `width/height` props로 외부에서 받음 → 부모 컨테이너에 따라 다름.

### 14. `/chainsight/watchlist`, `/chainsight/watchlist/[id]` — 검토 미상세
- 페이지가 존재하나 본 감사에서 별도 분석 안 함.

### 15. `/market-pulse`, `/market-pulse-v2` — ✅ 일부 양호
- TickerBar `overflow-x-auto` 적용 ✅
- BriefDetail/BriefCardSummary `text-[10px]` (장식 메타정보 — generated_at, model_version) → MINOR.
- Detail 페이지들 ResponsiveContainer 적용 ✅.

### 16. `/news` — 검토 미상세 (위 참조)

### 17. `/admin` — 데스크톱 전용 (감사 범위 외)
- Admin 영역은 운영자 전용으로 모바일 우선 대상 아님. 기록만:
  - SystemTab.tsx `max-w-[240px] truncate` (362), MLCompareView, NewsTab 등에 `overflow-x-auto`.

### 18. `/dashboard`, `/watchlist`, `/mypage`, `/login`, `/signup` — 검토 미상세
- watchlist는 `app/watchlist/page.tsx`에서 `overflow-x-auto`만 보임 → 추가 검토 권장.

---

## 최우선 권고 (참고용, 코드 변경 없음)

본 보고서는 읽기 전용 감사이므로 권고는 **분석 결론**으로 한정.

1. **BLOCKER 우선순위**: Portfolio Table → Stocks 상세 → Screener Table 의 모바일 카드 자동 분기.
2. **Thesis 관제실** IndicatorRow의 인라인 메타 폭 재설계 필요 (모바일 2행 분리 권장).
3. **터치 타겟 일괄 점검**: `text-[10px]` + `px-2 py-1` 또는 `p-2` 패턴이 클릭 가능 요소에 적용된 곳 16건 식별. 최소 터치 영역 44pt 보장 정책 수립 필요.
4. **모바일 네비게이션 보강**: BottomNav에 Thesis/Chainsight 진입점 추가 또는 Header 햄버거 부활. 검색 진입점 누락 (현재 모바일 검색 불가능).
5. **차트 폰트**: fontSize 9~10 → 모바일에선 11~12로 상향 또는 height 조정.
6. **MobileCardList 자동 분기**: 화면 폭 < 768px에서 자동으로 카드뷰가 디폴트가 되도록 (사용자 토글 의존하지 않음).

---

## 감사 메서드 요약

- 분석 도구: 정적 grep + 핵심 파일 읽기 (Read tool)
- 검사 패턴:
  - 고정 폭: `w-\[\d+px\]|min-w-\[\d+px\]|max-w-\[\d+px\]` → 27건
  - 작은 텍스트: `text-\[(10|11)px\]` → 117건 (50 파일)
  - ResponsiveContainer: 15 파일에서 사용 확인
  - overflow-x-auto: 27 파일
- 검사 제외: 백엔드 코드, 테스트 코드, admin 운영자 화면 (데스크톱 전용), `node_modules`
- 검증되지 않은 영역(추가 점검 필요): `/news`, `/watchlist`, `/dashboard`, `/login`, `/signup`, thesis close/alerts 페이지 본체, ChainSight watchlist, Mobile dvh 키보드 동작

---

**감사 종료**: 코드 수정 없음. 본 문서는 정적 코드 감사 결과만 포함.
