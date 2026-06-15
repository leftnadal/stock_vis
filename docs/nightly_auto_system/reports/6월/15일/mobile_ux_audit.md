# 모바일 UX 감사 보고서

> 감사일: 2026-06-15 · 기준 뷰포트: **375px (iPhone SE/표준 모바일)** · Apple HIG 터치 타겟 **44×44pt**
> 범위: `frontend/components/` 205개 + `frontend/app/` 30개 페이지 · **읽기 전용 — 코드 미수정**
> 방법: 고정 폭/브레이크포인트/터치 타겟/`ResponsiveContainer` 패턴 grep + 도메인별 정밀 분석(5개 병렬)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|--------|------|------|
| 🔴 **BLOCKER** | **6** | 375px에서 콘텐츠가 잘리거나 기능에 접근 불가 |
| 🟠 **MAJOR** | **17** | 사용은 가능하나 심각한 불편 (오버플로우/터치 실패/정보 손실) |
| 🟡 **MINOR** | **14** | 경미한 가독성/여백/스크롤 힌트 문제 |

### 🔴 BLOCKER 6건 — 즉시 조치 대상

| # | 이슈 | 위치 | 영향 |
|---|------|------|------|
| B1 | **fixed bottom nav가 콘텐츠 하단 64px 가림** — `pb-16/20`이 `app/page.tsx`에만 존재 | 전역 (`layout.tsx` + 29개 페이지) | 모든 페이지 마지막 콘텐츠/CTA 클릭 불가 |
| B2 | **핀치 줌 비활성화** — `userScalable:false, maximumScale:1` | `app/layout.tsx:32-34` | 저시력 사용자 확대 불가 (접근성 위반) |
| B3 | **호버 전용 툴팁** — `group-hover:block hidden` 지표 5종 | `MoverCard.tsx`, `MoverCardWithBatchKeywords.tsx` | 터치 기기에서 지표 설명 영구 접근 불가 |
| B4 | **PortfolioTable 12열 테이블 카드뷰 미전환** + 편집 input `w-24` | `PortfolioTable.tsx:259,378,416` | 모바일 편집 모드 실질 사용 불가 |
| B5 | **그래프 캔버스 터치 제스처 미지원** (ForceGraph2D pinch/pan 없음) | `MarketGraphCanvas.tsx` | MobileCardList 폴백 있으나 오버레이 토글 잔존 |
| B6 | **채팅 입력창 키보드 대응 부재** (`fixed` 미사용, 스크롤 영역 내 배치) | `coach/e4/page.tsx:185`, `rag/ChatInterface.tsx:166` | 모바일 키보드 노출 시 입력창 가려짐 |

---

## 반응형 누락

### 고정 폭 사용 현황
`w-[NNpx]`/`min-w-[NNpx]`/`max-w-[NNpx]`/`h-[NNpx]` 패턴은 **42개 파일 66건**에서 발견. 375px에서 오버플로우 위험이 있는 항목:

| 심각도 | 위치 | className | 분석 |
|--------|------|-----------|------|
| 🟠 MAJOR | `eod/SignalDetailSheet.tsx:97` | `md:w-[420px]` | 420px > 375px, 안전 마진 없음 — 우측 잘림 |
| 🟠 MAJOR | `thesis/dashboard/IndicatorRow.tsx:110,115` | `min-w-[60px]` + `min-w-[120px]` | 값+변동률+스파크라인+지지/반박이 한 행 → 260px+ 누적, 압축/넘침 |
| 🟠 MAJOR | `chainsight/SectorBar.tsx:24` | `flex-shrink-0` + `max-w-[120px]` | 섹터 버튼 고정폭, 320px에서 3개만 표시·잘림 |
| 🟠 MAJOR | `chainsight/NodeTooltip.tsx` | `minWidth:160, maxWidth:220` | 320px 폭의 절반 이상 점유, 캔버스 가림 |
| 🟡 MINOR | `chainsight/MarketGraphCanvas.tsx:676` | `w-[110px] min-h-[68px]` | 빈 상태 섹터 CTA 3개 = 350px+, 줄바꿈 |
| 🟡 MINOR | `chainsight/RelationLegend.tsx:51` | `max-w-[140px]` | 320px의 43% 점유, 그래프 가림 |
| 🟡 MINOR | `eod/StockRow.tsx:55` | `max-w-[140px]` | 회사명 영역, 좁은 화면 여유 부족 |
| 🟡 MINOR | `eod/SignalDetailSheet.tsx:221` | `w-36` | 정렬 드롭다운 우측 정렬 시 오버플로우 |
| 🟡 MINOR | `keywords/KeywordTag.tsx` | 호버 툴팁 `w-48` | 192px 고정, 뷰포트 끝에서 넘침 |
| 🟡 MINOR | `news/AINewsBriefingCard.tsx:70` | 중요도 바 `max-w-[200px]` | 좁은 화면에서 전체 폭 미활용 |

### 데스크톱 전용 / 브레이크포인트 누락 레이아웃

| 심각도 | 위치 | 이슈 |
|--------|------|------|
| 🟠 MAJOR | `app/market-pulse-v2/components/TickerBar.tsx:23-37` | `flex gap-4` **반응형 전무** — 항목당 ~160px, 375px에 2개만, gap 미축소 |
| 🟠 MAJOR | `screener/PresetGallery.tsx:306+` | `grid-cols-2 md:grid-cols-3` — 모바일 2열이 항목당 ~172px로 과밀, `grid-cols-1` 권장 |
| 🟡 MINOR | `chainsight/watchlist/page.tsx` | `max-w-3xl` 고정, sm/md/lg 그리드 전환 없음 |
| 🟡 MINOR | `eod/SignalCardGrid.tsx:34` | `sm:grid-cols-2` — 480~600px 소형 태블릿에서 조기 2열 |
| 🟡 MINOR | `thesis/skeleton ThesisSkeleton.tsx:68` | `grid-cols-3` 고정 (로딩 단계라 영향 낮음) |
| ℹ️ 정보 | `layout/InvestingHeader.tsx` | **미사용 컴포넌트**(dead code). `max-w-[1400px]`·8개 메뉴 가로 배열·하드코딩 날짜, 모바일 대응 전무. 부활 시 전면 재작업 필요 |

> ✅ **양호**: `screener/AdvancedFilterPanel.tsx:276`(`grid-cols-1 sm:2 lg:3 xl:4`), `thesis/AddIndicatorSheet.tsx:274`(`grid-cols-1 sm:grid-cols-2`), `MarketMoversSection`(`1→md:2→lg:3`)은 올바른 반응형.

### 테이블/차트 가로 스크롤 처리

`<table>` 사용 13개 파일 중 대응 현황:

| 위치 | overflow-x-auto | 카드뷰 전환 | 평가 |
|------|:---:|:---:|------|
| `stocks/StockTable.tsx:34` | ✅ | — | 🟡 가로스크롤만, 스크롤 힌트 없음 |
| `strategy/ScreenerTable.tsx:128` | ✅ | — | 🟠 12열, AI키워드 `max-w-[200px]` 가독성 저하 |
| `portfolio/PortfolioTable.tsx:259` | ✅ | ❌ | 🔴 **B4** — 12열 + `px-6` + 편집 `w-24`, 카드뷰 없음 |
| `validation/LeaderComparisonSection.tsx:47` | ✅ | ❌ | 🟠 4열 스택 미전환, 모바일 가독성 급락 |
| `screener` (별도) | — | ✅ `MobileStockCard` | ✅ 모바일 카드뷰 보유 (모범 사례) |

> overflow-x-auto는 **28개 파일**에 적용되어 있으나, 대부분 **스크롤 가능 힌트(페이드/인디케이터) 부재** — 사용자가 가로 콘텐츠 존재를 인지하지 못함 (`SignalSummaryCard`, `TickerBar`, `SectorBar`, `MobileCardList` 탭 등 공통).

---

## 터치 타겟

### 🔴/🟠 클릭 가능 요소의 타겟 미달

| 심각도 | 위치 | 현재 | 분석 |
|--------|------|------|------|
| 🔴 BLOCKER | `rag/SuggestionChips.tsx:34` | `px-3 py-1.5 text-sm` (~32px) | 추천 칩 높이 부족 + `max-w-[150px] truncate` |
| 🟠 MAJOR | `screener/Pagination.tsx:97,107,144,154` | `p-1.5` (~28px) | 화살표 버튼 44pt 미달 (단, 페이지 번호 버튼은 `min-w-[44px] min-h-[44px]` ✅) |
| 🟠 MAJOR | `thesis/dashboard/DashboardPageHeader.tsx:21,30` | `p-1` (~28px) | 뒤로가기/새로고침 아이콘 버튼 |
| 🟠 MAJOR | `thesis/builder/NewsSelector.tsx:142` | `p-1` | 뒤로가기 버튼 동일 |
| 🟠 MAJOR | `chainsight/ExplorationTrail.tsx:33` | 노드 `r=12~18` (24~36px) | 이전 노드 클릭 어려움 |
| 🟠 MAJOR | `chainsight/RelationFilterChips.tsx:150` | `h-8 px-3 py-0` (32px) | 칩 높이 부족 + 가로스크롤 |
| 🟡 MINOR | `screener/AdvancedFilterPanel.tsx:238` | `px-3 py-1.5` (~32px) | 토글 버튼 |
| 🟡 MINOR | `screener/MarketBreadthCard.tsx:97` | `p-1` (~24px) | 설정 버튼 |
| 🟡 MINOR | `eod/SignalFilterTabs.tsx:68` | 카운트 배지 `min-w-[18px] h-[18px]` | 배지 자체는 비클릭이나 부모 탭 확인 필요 |

> ✅ **모범**: `MobileNav`(`min-h-[44px]`), `Pagination` 번호 버튼, `ScreenerTable:323`, `Header` 햄버거(`min-h/w-[44px]`, 단 현재 `hidden`)는 44pt 준수.

### 🟡 소형 텍스트 (`text-[9px]`/`[10px]`/`[11px]`)
`text-[10px]`·`[11px]`은 **57개 파일 127건**으로 광범위. 모바일 권장 최소 12px 미달 — 대부분 비클릭 메타데이터라 **MINOR**로 분류하되, 클릭 요소에 결합된 경우 위 표에서 MAJOR 처리. 대표 집중 구간:

- `thesis/dashboard/IndicatorRow.tsx`(7건), `RealValueIndicatorCard.tsx`(`text-[10px]` 설명/가설), `AddIndicatorSheet.tsx:240`(**`text-[9px]`** freq 배지 — 판독 한계)
- `chainsight/MobileCardList.tsx`(배지), `ChainStoryFeed.tsx`(경로 칩 `text-[10px]`)
- `coach/ConfidenceBadge.tsx:28`, `ActionItemsSection.tsx:51` (`text-[11px]` 배지)
- `news/MLModelStatusCard.tsx:193,202`, `AINewsBriefingCard.tsx:296`, `InterestSelector.tsx:96`
- `keywords/KeywordTag.tsx`(`sm: text-[10px]`), `KeywordList.tsx:115`(`+N` 배지)

### 도메인 지시 항목 확인
- **thesis 관제실 지표 카드**: `IndicatorRow`/`RealValueIndicatorCard` — 고정 `min-w-[120px]` 오버플로우 + `text-[10px]~[11px]` 다수 → 🟠 MAJOR
- **validation 프리셋 탭**: `PeerContextBar.tsx:40` — 탭 높이 `min-h-[44px]` ✅ 충족, 단 `text-xs` 가독성 + `flex-wrap`로 다줄 래핑(공간 낭비) → 🟠 MAJOR
- **chainsight 노드**: `ExplorationTrail` 24~36px, `RelationFilterChips` 32px → 🟠 MAJOR

---

## 네비게이션

| 심각도 | 항목 | 분석 |
|--------|------|------|
| 🔴 BLOCKER | **하단 nav 콘텐츠 가림 (B1)** | `layout.tsx`의 `<MobileNav/>`는 `fixed bottom-0 h-16`(64px). `<main>`은 `min-h-screen`만 있고 전역 하단 여백 없음. `pb-20 md:pb-0`은 **`app/page.tsx`에만** 존재 → news·dashboard·mypage·portfolio·watchlist·screener·thesis·chainsight 등 **29개 페이지 마지막 64px 콘텐츠가 nav에 가려짐** |
| ✅ 양호 | **MobileNav 자체** | 하단 5탭(홈/종목/뉴스/포트폴리오/내정보), `min-h-[44px]`, `aria-label`, active 상태, `md:hidden` — 구조 우수 |
| ✅ 양호 | **이중 네비 제거** | `Header` 햄버거를 `hidden`으로 처리해 모바일 단일 소스(MobileNav)로 통일 (주석 audit P0 #12) |
| 🟡 MINOR | **데스크톱 햄버거 메뉴 비활성** | `Header.tsx:157` 햄버거가 `hidden` — 모바일에서 상단 헤더에는 로고만 표시, 검색바도 `hidden md:block`. 모바일 검색 진입점 없음 (MobileNav에도 검색 탭 없음) |
| 🟠 MAJOR | **긴 목록 virtualization 부재** | `react-window`/`react-virtualized` 미사용. StockTable·ScreenerTable·PortfolioTable·뉴스 목록 등 긴 리스트가 전부 DOM 렌더 → 모바일 스크롤 성능 저하 |
| 🟡 MINOR | **iOS Safari 주소창 레이아웃 시프트** | `chainsight/[symbol]/page.tsx:155` `h-14` 고정 헤더, `100vh` 계열 동적 높이 미처리 |

---

## 차트/그래프

### ResponsiveContainer 사용 현황 (15개 파일)

| 위치 | ResponsiveContainer | 평가 |
|------|:---:|------|
| `stock/StockChart.tsx:652,748` | ✅ + 반응형 높이(`getResponsiveChartHeight`) | ✅ 모범 — 모바일 280/70px |
| `portfolio/PortfolioChart.tsx:77,97` | ✅ `width=100% height=400` | ✅ |
| `validation/MetricBarChart.tsx:78` | ✅ `100%/100%` | ✅ (단 `right:50` 마진 모바일 검토) |
| `macro/YieldCurveChart.tsx:93` | ✅ | ✅ |
| `screener/SectorHeatmap.tsx` | ✅ Treemap | ✅ |
| `thesis/dashboard/IndicatorRow.tsx:197,235` | ✅ `height=160/140` | ✅ |
| `thesis/dashboard/IndividualMiniCharts.tsx:54` | ✅ `height=100` | 🟡 100px 다소 작음 |
| `market-pulse-v2/details/*` (4개) | ✅ | ✅ |
| `news/SentimentChart.tsx:175` | ✅ but `h-80` 고정 | 🟠 모바일 라벨 겹침 우려 |
| `admin/news/MLTrendChart.tsx` | ✅ | ✅ |
| `charts/StockPriceChart.tsx:35` | ❌ `height=400` 고정 | 🟡 반응형 미구현 |

### 분기 스파크라인 / 커스텀 차트 모바일 가독성

| 심각도 | 위치 | 분석 |
|--------|------|------|
| 🟠 MAJOR | `thesis/dashboard/QuarterlySparkline.tsx:41-66` | 막대 `flex-1` + `gap-1` → 4분기가 좁은 폭에 분할, 차트 높이 `h-10`(40px)로 추이 식별 한계. **호버 툴팁(`text-[10px]`)이 터치 환경에서 작동 안 함** |
| 🔴 BLOCKER | `chainsight/MarketGraphCanvas.tsx` (B5) | ForceGraph2D 캔버스 pinch-zoom/pan 미지원. `MobileCardList` 폴백 존재하나 그래프 오버레이 상태(`graphOverlay`) 완전 비활성화 안 됨 |
| 🟡 MINOR | `screener/MarketBreadthCard.tsx` | 커스텀 게이지, ResponsiveContainer 미사용 (고정 크기) |

---

## 페이지별 상세

### 🏠 `/` (홈, `app/page.tsx`)
- ✅ 유일하게 `pb-20 md:pb-0` 보유 — 하단 nav 대응 정상.
- `max-w-6xl mx-auto px-4` — 모바일 여백 양호.

### 📊 `/dashboard`, `/mypage`
- 🔴 **B1**: `min-h-screen`만 있고 `pb-16` 없음 → 하단 콘텐츠 가림.

### 📰 `/news`
- 🔴 **B1**: `px-4 sm:px-6 py-5` — 하단 nav 여백 없음, 마지막 섹션 가림.
- 🟠 `KeywordDetailSheet` 키워드 스트립 가로스크롤, 스크롤 힌트 없음(화살표 버튼은 존재).
- 🟠 `SentimentChart` `h-80` 고정 — 모바일 라벨 겹침.

### 💼 `/portfolio`
- 🔴 **B4**: `PortfolioTable` 12열, 카드뷰 없음, 편집 input `w-24` 2개 동시 표시 불가.
- 🔴 **B1**: 하단 nav 여백 없음.

### 📋 `/watchlist`
- 🔴 **B1**: 여백 없음.
- 🟡 테이블 `overflow-x-auto`만, 카드뷰 전환 없음.

### 🔍 `/screener`
- ✅ `MobileStockCard` 카드뷰 + `Pagination` 44pt 준수 — 모바일 대응 **모범**.
- 🟠 `PresetGallery` 모바일 2열 과밀, `AdvancedFilterPanel` 반응형 ✅.
- 🟡 `MobileStockCard` 메트릭 라벨 `text-[10px]`.
- 🔴 **B1**: 페이지 root 여백 없음.

### 📈 `/stocks/[symbol]`
- ✅ `StockChart` 반응형 높이 우수.
- 🟡 `StockTable` 가로스크롤만, 스크롤 힌트 없음.

### 🎯 `/thesis` (관제실)
- 🟠 `IndicatorRow` `min-w-[120px]` 오버플로우 + `text-[10px]~[11px]` 다수.
- 🟠 `QuarterlySparkline` 호버 툴팁 터치 미작동 + 40px 높이.
- 🟠 `DashboardPageHeader`/`NewsSelector` `p-1` 버튼 터치 미달.
- 🟡 `AddIndicatorSheet` `text-[9px]` freq 배지.
- 🔴 **B1**: 여백 없음.

### 🕸️ `/chainsight`, `/chainsight/[symbol]`
- 🔴 **B5**: 그래프 캔버스 터치 제스처 미지원.
- 🟠 `SectorBar`/`RelationFilterChips`/`ExplorationTrail` 고정폭·작은 터치 타겟.
- 🟡 `NodeTooltip`/`RelationLegend` 고정폭 캔버스 가림, 모바일 감지 방식 불일치(`pointer:coarse` vs `max-width:767px`).
- 🟡 `watchlist` `max-w-3xl` 고정.

### ✅ `/validation` (Peer 비교, LeaderComparisonSection 경유)
- 🟠 `PeerContextBar` 프리셋 탭 `flex-wrap` 다줄 래핑, `text-xs` 가독성.
- 🟠 `LeaderComparisonSection` 4열 테이블 스택 미전환.
- ✅ `MetricBarChart` ResponsiveContainer.

### 📉 `/market-pulse`, `/market-pulse-v2`
- 🔴 **B3**: `MoverCard`/`MoverCardWithBatchKeywords` 호버 전용 툴팁 5종 — 터치 접근 불가.
- 🟠 **TickerBar** 반응형 전무, `gap-4` 고정.
- 🟡 `MarketMoversSection` 카드 그리드 `gap-2` 모바일 식별성.

### 💬 `/coach/e1~e6`, `/ai-analysis` (RAG)
- 🔴 **B6**: `coach/e4` 입력창·`ChatInterface` 키보드 대응 부재(`fixed` 미사용).
- 🟠 `coach/e4` 메시지 영역 `max-h-[60vh]` 고정 — 키보드 노출 시 찌그러짐.
- 🔴 **B5(연관)**/🔴 **B1**: `ai-analysis`/`dashboard` 하단 nav 여백 없음.
- 🔴 **B1**: 다수 coach 페이지 여백 미확인 — 점검 필요.

### ⚙️ `/admin`
- 다수 `overflow-x-auto` 테이블(NewsTab, ScreenerTab, SystemTab 등). 관리자 전용 화면으로 모바일 우선순위 낮음 → 본 감사에서 **심각도 제외**(가로스크롤로 최소 대응).

---

## 부록: 전역 권장 조치 (우선순위순, 분석만 — 미적용)

1. **(B1) `layout.tsx`의 `<main>`에 `pb-16 md:pb-0` 추가** — 단일 수정으로 29개 페이지 하단 가림 해소.
2. **(B2) `viewport`에서 `userScalable:false`·`maximumScale:1` 제거** — 핀치 줌 복원(접근성).
3. **(B3) `MoverCard` 호버 툴팁을 tap-to-expand/시트로 전환.**
4. **(B6) 채팅 입력창 `fixed bottom-16 left-0 right-0`** + `max-h` 동적 계산.
5. **(B4) `PortfolioTable` 모바일 카드뷰 추가** (`screener/MobileStockCard` 패턴 재사용).
6. **공통**: `text-[9px]/[10px]/[11px]` → `text-xs` 이상, `p-1/py-1.5` 클릭 요소 → `min-h-[44px]`, 가로스크롤 컨테이너에 페이드 힌트 추가, 긴 목록 virtualization 검토.

---

*본 보고서는 정적 코드 분석 기반이며 실기기 렌더링 검증은 포함하지 않음. 실제 잘림/터치 실패는 디바이스 QA로 확정 권장.*
