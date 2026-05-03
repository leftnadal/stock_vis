# 모바일 UX 감사 보고서

**감사 일자**: 2026-05-04
**감사 범위**: `frontend/` 전체 (app + components, *.tsx)
**기준 디바이스**: iPhone 13 mini (375 × 812 CSS px), Apple HIG (touch target ≥ 44 × 44 pt)
**모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 정의 |
|--------|------|------|
| **BLOCKER** | **6** | 모바일에서 기능을 사용할 수 없거나 접근성 표준 위반 |
| **MAJOR** | **14** | 사용 가능하나 명확한 마찰/불편 발생, Apple HIG 위반 |
| **MINOR** | **8** | 불편하지만 우회 가능, 가독성 저하 수준 |

### BLOCKER 6건 핵심
1. `app/layout.tsx` viewport 메타에 `userScalable: false, maximumScale: 1` — **WCAG 2.1.4.4 / 1.4.10 위반** (확대 차단)
2. `MobileNav` 5개 링크 중 **2개가 깨진 경로** (`/stocks` → 동적 라우트만 존재, `/profile` → `/mypage`로 이름 다름)
3. `Header` + `MobileNav` 동시 마운트 — `h-16` 하단 바 64px이 콘텐츠를 덮음, **`pb-20` 미적용 페이지 17/20개**
4. `app/dashboard/page.tsx`가 자체 헤더를 추가로 그려 **헤더 2개 중첩** (h-16 + h-16 = 128px 사용)
5. `app/portfolio/page.tsx` `PortfolioTable` 12열 테이블 — 375px에서 가로 스크롤만 제공, 카드 variant 없음
6. `InvestingHeader` (`bg-[#1e2329]`)는 모든 nav 항목·상단 마켓 티커가 `hidden md:` 분기 없이 항상 표시 — 375px에서 컬럼 짤림 (현재 layout.tsx에서 import되지 않으나 import 시 즉시 깨짐)

---

## 1. 반응형 누락

### 1.1 고정 폭 사용 현황

전체 `w-[NNpx]` / `min-w-[NNpx]` / `max-w-[NNpx]` 매치: **27건** (배지·아이콘 18-72px 제외 시 의미있는 위반은 8건).

#### MAJOR

| 파일 | 라인 | 패턴 | 모바일(375px) 영향 |
|------|------|------|-------------------|
| `components/layout/InvestingHeader.tsx` | 32, 55, 99 | `max-w-[1400px]` 컨테이너 + `flex items-center` 내부 nav 8개 항상 표시 | 375px에서 nav 컬럼 잘림 + 검색바 `max-w-xl` 점유 |
| `components/strategy/ScreenerTable.tsx` | 209, 224, 307 | `max-w-[180px] truncate` (종목명), `max-w-[120px]` (섹터), `max-w-[200px]` (키워드) — 12열 테이블 안에서 사용 | 테이블 자체는 `overflow-x-auto`로 가로 스크롤 가능하나, 모바일에서 12열 테이블 자체가 학습 곡선 |
| `components/admin/SystemTab.tsx` | 362 | `max-w-[240px] truncate` 로그 셀 | 어드민 화면이라 영향 작음 |
| `components/eod/SignalDetailSheet.tsx` | 97 | `w-full md:w-[420px] md:h-full` | mobile에서 100% 차지, ≥md에서 420px 사이드 시트 — **올바른 패턴** |
| `components/rag/ChatInterface.tsx` | 198 | `h-[52px] w-[52px]` 전송 버튼 | 적절한 터치 타겟 |
| `components/thesis/dashboard/IndicatorRow.tsx` | 110, 115, 132 | `min-w-[60px]` 값, `min-w-[120px]` 변동률, `max-w-[100px]` 스파크라인 | `max-w-lg` (512px) 컨테이너 안에서 합계 280px+ 차지 → 375px에서 우측 "지지/반박" 라벨이 끝까지 밀려 잘릴 가능성 |
| `components/eod/StockRow.tsx` | 55, 66 | `truncate max-w-[140px]` 회사명, `min-w-[72px]` 가격 | 측정 합계 적절, 양호 |

#### MINOR

| 파일 | 라인 | 패턴 |
|------|------|------|
| `components/news/AINewsBriefingCard.tsx` | 70 | `max-w-[200px]` progress bar |
| `components/news/RecommendationCard.tsx` | 85 | `max-w-[150px] truncate` |
| `components/rag/SuggestionChips.tsx` | 40 | `max-w-[150px] truncate` |
| `components/chainsight/SectorBar.tsx` | 41 | `max-w-[120px] truncate` |
| `components/common/DataSourceBadge.tsx` | 171 | `min-w-[200px]` 팝오버 |

### 1.2 브레이크포인트 누락 컴포넌트

`md:`/`lg:`/`sm:` 분기 사용 파일: **53/200+ 컴포넌트** (대부분의 컴포넌트는 분기 없음 = 단일 레이아웃).

#### BLOCKER
- `components/layout/InvestingHeader.tsx` — 마켓 티커, 8개 nav, 검색바 모두 분기 없이 항상 가로 정렬. layout.tsx에서 사용되지 않지만 코드베이스에 살아있음.

#### MAJOR
- `components/portfolio/PortfolioTable.tsx` (240–300) — 12열 테이블만 제공. 모바일 카드 variant가 코드베이스에 없음 (PortfolioStockCard는 다른 용도).
- `components/strategy/ScreenerTable.tsx` — 12열 테이블, 분기 없음. 다만 `app/screener/page.tsx:845`에서 `hidden sm:block` 분기 + `MobileStockCard` 분기로 페이지 레벨에서 처리됨 → **양호**.
- `app/dashboard/page.tsx:30-50` — 자체 nav가 grid에만 분기 처리, nav 자체는 `flex justify-between` 항상 가로 → 모바일에서 닉네임/로그아웃 버튼이 좁은 폭에서 짤림.
- `components/admin/*` 다수 — 어드민이라 영향 제한적이지만 `AdminTabNav` 외엔 모바일 대응 없음.

### 1.3 테이블/차트 가로 스크롤 처리

`overflow-x-auto` 사용: **31곳**. 가로 스크롤 패턴은 모바일에서 **데이터 테이블을 보여주는 표준 회피책이지만** 사용자가 가로 스크롤을 인지해야 함.

#### MAJOR
- `components/portfolio/PortfolioTable.tsx:259` — 가로 스크롤만 제공. 12열 (종목/수량/평균매수가/현재가/전일대비/평가금액/손익/수익률/목표가/손절가/비중/관리). 모바일에서 사용 불가능 수준.
- `components/admin/SystemTab.tsx:72,144,288` + `components/admin/ScreenerTab.tsx:56,111` + `components/admin/news/*` 5곳 — 어드민이라 우선순위 낮음.
- `app/stocks/[symbol]/page.tsx:843` Financial table (BS/IS/CF) — 분기 헤더가 가로로 4-5개. 가로 스크롤 작동하나 unit selector가 상단 고정 안 됨.

#### MINOR (스크롤바 숨김 + chip 스크롤은 의도된 패턴)
- `components/eod/SignalFilterTabs.tsx:33` — 카테고리 칩
- `components/chainsight/ExplorationTrail.tsx:36`, `SectorBar.tsx:24`, `ChainStoryFeed.tsx:118`, `TracePathView.tsx:52`, `FullPathView.tsx:173` — Chain Sight 경로/섹터 칩
- `components/validation/SignalSummaryCard.tsx:36` — 7개 신호등 카드
- `components/news/NewsHighlightedStocks.tsx:118`, `KeywordDetailSheet.tsx:125`
- `components/admin/AdminTabNav.tsx:30` — 어드민 탭

---

## 2. 터치 타겟 (Apple HIG 44 × 44 pt)

### 2.1 클릭 가능한 텍스트 ≤ 11px

`text-[10px]` / `text-[11px]` 사용: **~80곳**. 그중 클릭/링크/버튼 안에 있는 위반 사례:

#### BLOCKER

| 파일 | 라인 | 요소 | 측정 (대략) |
|------|------|------|------------|
| `components/eod/SignalDetailSheet.tsx` | 188 | `text-[10px] px-1.5 py-0.5` Chain Sight 섹터 링크 (Link) | ~20×16px |
| `components/eod/SignalDetailSheet.tsx` | 197 | `text-[10px] inline-flex` "관계 지도" 링크 | ~50×14px |
| `components/eod/SignalCard.tsx` | 169-177 | `<Network className="w-2.5 h-2.5" />` (10×10) 아이콘 링크 | 10×10px |
| `components/thesis/dashboard/IndicatorRow.tsx` | 182 | `px-2.5 py-0.5 text-[10px]` 차트 기간 선택 버튼 (1M/1Y/3Y/5Y) | ~30×18px |
| `components/keywords/KeywordTag.tsx` | 42 | sm 사이즈 `px-2 py-0.5 text-[10px]` (클릭 가능 키워드) | ~30×18px |
| `app/thesis/new/page.tsx` | 1063 | `text-[10px]` 인라인 링크 | ~14px 행 높이 |

#### MAJOR (클릭 가능하지만 14-20px 높이대)

| 파일 | 라인 | 요소 |
|------|------|------|
| `components/validation/PeerContextBar.tsx` | 40 | 프리셋 탭 `px-3 py-1 text-xs` → ~26px 높이 |
| `components/validation/PeerContextBar.tsx` | 53 | "직접 설정" 버튼 동일 |
| `components/validation/PeerContextBar.tsx` | 122 | "peer 목록 보기" 토글 `text-xs` |
| `components/validation/CategorySidebar.tsx` | 48 | 카테고리 항목 `px-3 py-2 text-sm` → ~36px 높이 (lg 이상에서만 사용) |
| `components/chainsight/MobileCardList.tsx` | 86, 96 | 카테고리 탭 `px-3 py-1.5 text-sm` → ~32px 높이 |
| `components/chainsight/MobileCardList.tsx` | 167-184 | "가설 생성"/"탐색"/"검증" 3분할 버튼 `text-xs py-1.5` → ~28px 높이 |
| `components/screener/Pagination.tsx` | 127 | `min-w-[32px] py-1.5 text-sm` 페이지 번호 |
| `components/eod/SignalCard.tsx` | 113 | HelpCircle 도움말 버튼 `p-1` + `w-3.5 h-3.5` 아이콘 → ~22×22px |
| `components/thesis/IndicatorCard.tsx` | 35-44 | 체크박스 `w-5 h-5` (20×20px) — 부모 `gap-3 p-3` 영역까지 포함하면 통과 가능 |
| `components/chainsight/[symbol]/page.tsx` | 251-261 | depth 1/2/3 토글 `px-3 py-1.5` → ~32px |

### 2.2 thesis 관제실 지표 카드

`components/thesis/dashboard/IndicatorRow.tsx`:
- 메인 행 `<button>` `px-4 py-3` (52px+ 높이) — **양호** (전체 행 클릭 가능)
- 펼쳤을 때 1M/1Y/3Y/5Y 버튼 `px-2.5 py-0.5 text-[10px]` (≈30×18px) — **BLOCKER 기준 미달**
- ChevronDown 토글 아이콘 (size=14) — 부모 button 영역에 포함되어 양호

`components/thesis/IndicatorCard.tsx` (지표 추천):
- 체크박스 `w-5 h-5` (20×20) — 단독으로는 미달이나 onClick이 부모와 분리됨
- `<button>` `flex-shrink-0 p-1` ChevronDown — ~24×24px — 미달

### 2.3 validation 프리셋 탭

`components/validation/PeerContextBar.tsx:40`:
- `<button className="px-3 py-1 text-xs font-medium rounded-full">` → ~60×26px
- "직접 설정" 토글 동일
- 모바일 페어 컨텍스트 변경의 핵심 진입점인데도 26px 높이 → **MAJOR**

### 2.4 chainsight 노드

`app/chainsight/[symbol]/page.tsx:200-228`:
- 모바일 그래프 오버레이 노드 상세 바텀 시트 — `flex-1 text-xs py-2` 3분할 CTA → ~30px 높이 → **MAJOR**
- 닫기 버튼 `text-sm` X 아이콘 — ~24px → **MAJOR**

`components/chainsight/MobileCardList.tsx:167-184`:
- 카드당 3개 CTA `text-xs py-1.5` → ~28px → **MAJOR**

---

## 3. 모바일 네비게이션

### 3.1 사이드바/헤더의 모바일 대응

**활성 헤더**: `components/layout/Header.tsx` (layout.tsx에서 마운트)
- ✅ `hidden md:flex` 데스크톱 nav
- ✅ `md:hidden` hamburger 메뉴 + 토글 가능한 모바일 nav
- ✅ 모바일 메뉴에 검색바 포함
- ⚠️ 햄버거 메뉴 `p-2` (40×40px) — **44pt 약간 미달**

**미사용 헤더**: `components/layout/InvestingHeader.tsx`
- ❌ 분기 없음, 모바일 대응 0% — 사용 시 즉시 깨짐

### 3.2 Bottom Navigation

`components/layout/MobileNav.tsx` (layout.tsx에 항상 마운트, `md:hidden`):

#### BLOCKER
- 5개 링크 중 **2개가 잘못된 경로**:
  | 라벨 | href | 실제 라우트 |
  |------|------|------------|
  | 홈 | `/` | ✅ 존재 |
  | 종목 | `/stocks` | ❌ `app/stocks/[symbol]/page.tsx`만 존재, `/stocks` 인덱스 페이지 없음 → 404 |
  | 뉴스 | `/news` | ✅ 존재 |
  | 포트폴리오 | `/portfolio` | ✅ 존재 |
  | 내정보 | `/profile` | ❌ 실제 경로는 `/mypage` → 404 |

#### MAJOR
- `MobileNav` 누락 항목: Chain Sight, Thesis Control, Market Pulse, 스크리너 — 5개 핵심 기능에 도달 불가, 햄버거 메뉴를 거쳐야 함
- `pb-20` 누락 페이지 — bottom nav (h-16 = 64px)가 콘텐츠 하단을 가림. `pb-20` 적용 페이지는 `app/page.tsx`, `app/thesis/[thesisId]/page.tsx`, `app/thesis/(list)/layout.tsx` **3개뿐**. 나머지 17개 페이지(login, signup, mypage, portfolio, news, screener, stocks, market-pulse, chainsight, watchlist, admin, ai-analysis, dashboard 등)는 마지막 행 콘텐츠가 가려짐.

### 3.3 긴 목록 virtualization

- `react-window`, `react-virtual`, `FixedSizeList`, `VariableSizeList` 등 **검색 결과 0건**
- **MAJOR**: 스크리너 결과 (`paginatedStocks`), 종목 검색, 뉴스 목록, validation 메트릭 목록 모두 평면 map 렌더링 — 100개+ 데이터에서 모바일 스크롤 성능 저하 가능

### 3.4 viewport 메타 (별도 BLOCKER)

`app/layout.tsx:29-35`:
```ts
viewport: {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,  // ← BLOCKER
  viewportFit: "cover",
}
```
- WCAG 2.1.4.4 (Resize text) / 1.4.10 (Reflow) 위반
- iOS Safari는 `userScalable: false`를 무시하지만 Android Chrome은 따름 → 안드로이드에서 확대 불가
- 시각 장애인 사용성 차단

---

## 4. 차트/그래프 모바일 대응

### 4.1 ResponsiveContainer 사용 현황

Recharts 사용 차트 컴포넌트 **9개** 모두 `ResponsiveContainer`로 감싸짐:

| 파일 | 사용 | width | height |
|------|------|-------|--------|
| `validation/MetricBarChart.tsx` | ✅ | 100% | 100% |
| `stock/StockChart.tsx` | ✅ ×2 | 100% | `chartHeight.price`, `chartHeight.volume` |
| `charts/StockPriceChart.tsx` | ✅ | 100% | `height` prop |
| `admin/news/MLTrendChart.tsx` | ✅ | 100% | 100% |
| `thesis/dashboard/IndicatorRow.tsx` | ✅ ×2 | 100% | 160, 140 |
| `thesis/dashboard/IndividualMiniCharts.tsx` | ✅ | 100% | 100 |
| `news/SentimentChart.tsx` | ✅ | 100% | 100% |
| `portfolio/PortfolioChart.tsx` | ✅ ×2 | 100% | 400 |
| `macro/YieldCurveChart.tsx` | ✅ | 100% | 100% |
| `screener/SectorHeatmap.tsx` | ✅ | 100% | 400 |

**전반적으로 양호**. ResponsiveContainer는 width=100%로 부모를 채움.

#### MAJOR
- `portfolio/PortfolioChart.tsx` `height={400}` — 375×400 정사각형, 라벨 6개 이상이면 X축 레이블 겹침 (Recharts 자동 회전 미설정)
- `thesis/dashboard/IndicatorRow.tsx:207` X축 `fontSize={9}` — **BLOCKER 기준 미달의 가독성**
- `screener/SectorHeatmap.tsx` Treemap `height={400}` — 모바일에서 11개 섹터 타일 글자가 매우 작음

### 4.2 분기 스파크라인 (`QuarterlySparkline.tsx`)

`components/thesis/dashboard/QuarterlySparkline.tsx`:
- 부모 `max-w-[100px]` 안에서 4개 막대 표시
- Q1/Q2/Q3/Q4 라벨 `text-[8px]` (≈8px) — **MINOR** (라벨이 비클릭이고 시각적 보조)
- 호버 툴팁 `text-[10px]` — 호버 기반이라 모바일에선 효과 미미

### 4.3 Chain Sight 그래프 캔버스

`app/chainsight/[symbol]/page.tsx`:
- ✅ `isMobile` 체크 (window.innerWidth < 768)로 모바일은 그래프 대신 `MobileCardList` + "그래프로 보기" FAB
- ✅ 그래프 오버레이가 fixed inset-0으로 풀스크린
- 노드 텍스트 (ForceGraph2D 내부 canvas) — 픽셀 기반, 줌 가능

---

## 5. 페이지별 상세

### 5.1 `/` (Home — EOD Dashboard) — `app/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| 컨테이너 | ✅ `max-w-6xl mx-auto px-4` | 적절 |
| Bottom nav 패딩 | ✅ `pb-20 md:pb-0` | 명시적 |
| 카드 그리드 | ✅ `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` | 양호 |
| SignalCard 터치 타겟 | ⚠️ HelpCircle (≈22×22) — **MAJOR** | 부모 카드는 통째 클릭 가능 |
| Network 아이콘 링크 | ❌ `w-2.5 h-2.5` (10×10) — **BLOCKER** | SignalCard:175 |
| SignalDetailSheet | ✅ 모바일 bottom sheet, md 사이드 패널 | 우수한 패턴 |

### 5.2 `/dashboard` (구 대시보드) — `app/dashboard/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| Header 중첩 | ❌ **BLOCKER** | layout의 `Header` + 페이지 자체 `<nav>` = 헤더 2개 |
| 닉네임/로그아웃 | ❌ 항상 가로 정렬 | 좁은 폭에서 깨짐 |
| 카드 그리드 | ✅ `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` | 양호 |
| Bottom nav 패딩 | ❌ 없음 | 마지막 행 가려짐 |

### 5.3 `/stocks/[symbol]` (종목 상세) — `app/stocks/[symbol]/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| Validation tab `isMobile` 분기 | ✅ MAJOR 패턴 | line 1027-1067, 모바일은 칩 + 단일 카테고리만 |
| `CategorySidebar` | ✅ `hidden lg:block` | 데스크톱 전용 적절 처리 |
| `PeerContextBar` 프리셋 탭 | ⚠️ `text-xs py-1` (~26px) — **MAJOR** | 핵심 진입점인데 작음 |
| Financial 테이블 (BS/IS/CF) | ⚠️ `overflow-x-auto`만 | UnitSelector 상단 고정 안 됨 |
| Bottom nav 패딩 | ❌ 없음 | |
| 차트 (`StockChart`) | ✅ ResponsiveContainer | |
| L1/L2 탭 | ⚠️ 분기 미확인 | 좁은 폭에서 탭 텍스트 잘릴 가능성 |

### 5.4 `/screener` (스크리너) — `app/screener/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| 테이블/카드 토글 | ✅ `viewMode === 'card'/'table'` | line 762-774 |
| 모바일 기본값 | ⚠️ `useState<'table' \| 'card'>('table')` — **MAJOR** | `hidden sm:block` 분기로 모바일에선 자동 카드 노출되지만 토글 라벨 혼란 |
| `MobileStockCard` | ✅ 별도 컴포넌트 | grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` |
| `AdvancedFilterPanel` | ⚠️ 분기 미확인 | 다중 컬럼 grid가 좁은 폭에서 어떻게 무너지는지 검증 필요 |
| Bottom nav 패딩 | ❌ 없음 | |

### 5.5 `/thesis/[thesisId]` (가설 관제실 대시보드) — `app/thesis/[thesisId]/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| 컨테이너 | ✅ `max-w-lg mx-auto px-4 pt-4 pb-20` | **모바일 우선 설계, 우수** |
| Bottom nav 패딩 | ✅ `pb-20` | |
| `IndicatorRow` 메인 행 | ✅ `px-4 py-3` 풀너비 button | |
| 차트 기간 버튼 (1M/1Y/3Y/5Y) | ❌ `px-2.5 py-0.5 text-[10px]` — **BLOCKER** | line 178-189 |
| 차트 X축 fontSize | ⚠️ `fontSize={9}` — **MAJOR** | 가독성 |
| `QuarterlySparkline` 라벨 | ⚠️ `text-[8px]` — **MINOR** | 비클릭 |
| "지지/반박" 라벨 | ⚠️ `min-w-[60px] + min-w-[120px] + max-w-[100px]` 합 ≥ 280px | 375px - 좌우 패딩(32) - pl-4(16) = 327px → 빠듯 |

### 5.6 `/thesis/new` (가설 빌더) — `app/thesis/new/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| `text-[10px]` 라벨 다수 (line 688, 752, 765, 831, 843) | ⚠️ 비클릭 — **MINOR** | UPPERCASE tracking-wider 라벨 |
| `text-[10px]` 인라인 링크 (line 1063) | ❌ 클릭 가능 — **BLOCKER** | |
| `text-[10px] px-1.5 py-0.5` 방향 칩 (line 753) | ⚠️ 비클릭 표시 — **MINOR** | |

### 5.7 `/chainsight/[symbol]` (Chain Sight 워크스페이스)

| 항목 | 평가 | 비고 |
|------|------|------|
| `isMobile` 분기 | ✅ window.innerWidth < 768 | line 53, 117 |
| 모바일 기본 뷰 | ✅ `MobileCardList` (그래프 대신 카드 리스트) | |
| 그래프 오버레이 | ✅ fixed inset-0 풀스크린 + 닫기 버튼 | |
| 노드 상세 바텀 시트 | ✅ 패턴 양호 | line 200-228 |
| 3분할 CTA 버튼 | ⚠️ `text-xs py-2` (~30px) — **MAJOR** | line 209-227 (오버레이) / MobileCardList:167-184 |
| `useEffect` 리사이즈 핸들러 | ✅ 의존성 `[leftOpen]` | |
| Right panel | ✅ `hidden lg:block` | |

### 5.8 `/portfolio` — `app/portfolio/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| `PortfolioTable` 12열 | ❌ 카드 variant 없음 — **BLOCKER** | overflow-x-auto만 |
| Header 중첩 가능성 | ⚠️ 검증 필요 | |
| Bottom nav 패딩 | ❌ 없음 | |
| `PortfolioChart` height=400 | ⚠️ 모바일 X축 레이블 겹침 — **MAJOR** | |

### 5.9 `/news` — `app/news/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| grid 분기 | ✅ 4건 (page.tsx 분기 사용) | |
| Bottom nav 패딩 | ❌ 없음 | |
| `MarketNewsSection` 메타 라벨 `text-[10px]` | ⚠️ 비클릭 — **MINOR** | |

### 5.10 `/market-pulse` — `app/market-pulse/page.tsx`

| 항목 | 평가 | 비고 |
|------|------|------|
| `MoverCard` 툴팁 다수 (`hidden group-hover/tooltip:block`) | ❌ 모바일 호버 없음 — **MAJOR** | 모바일에서 툴팁 트리거 불가 |
| `text-[10px]` 회사명 라벨 | ⚠️ 비클릭 — **MINOR** | |
| Bottom nav 패딩 | ❌ 없음 | |

### 5.11 `/admin`

| 항목 | 평가 | 비고 |
|------|------|------|
| `AdminTabNav` 가로 스크롤 | ✅ `overflow-x-auto` | |
| 다수 테이블 overflow-x-auto | ⚠️ 어드민 한정이라 우선순위 하 | |
| Bottom nav 패딩 | ❌ 없음 | |

### 5.12 인증 페이지 (`/login`, `/signup`)

| 항목 | 평가 | 비고 |
|------|------|------|
| 폼 레이아웃 | ⚠️ 검증 필요 | |
| Bottom nav 패딩 | ❌ 없음 | (인증 후 리다이렉트되므로 영향 작음) |

---

## 부록 A: 발견 통계

- 검사한 컴포넌트 파일: **200+ tsx**
- 검사한 페이지: **20**
- 활성 레이아웃: `app/layout.tsx` (Header + MobileNav 항상 마운트)
- 비활성 레거시: `components/layout/InvestingHeader.tsx`
- Recharts 차트: **9개 컴포넌트, 모두 ResponsiveContainer 사용**
- `text-[10px]` 사용: 약 **80건** (대부분 비클릭 라벨, 클릭 위반 6건)
- `overflow-x-auto`: **31건** (의도된 칩 스크롤 + 미흡한 테이블 폴백 혼재)
- Virtualization 라이브러리: **0건**

## 부록 B: 빠른 수정 우선순위 (참고)

> 본 보고서는 읽기 전용 감사이며, 아래는 향후 작업 계획 수립을 위한 참고용 정렬.

**즉시 (BLOCKER)**:
1. `MobileNav` href `/stocks`, `/profile` 수정 → `/stocks` 인덱스 페이지 신설 또는 다른 경로로
2. `app/layout.tsx` viewport에서 `userScalable: false`, `maximumScale: 1` 제거 (WCAG)
3. `app/dashboard/page.tsx` 자체 nav 제거 (헤더 중첩)
4. `pb-20` (또는 `mb-16`) 글로벌 적용 — `<main>`에 `pb-20 md:pb-0` 추가
5. `IndicatorRow` 차트 기간 버튼 크기 ≥ 32×32 + text-xs
6. `PortfolioTable` 모바일 카드 variant 추가

**단기 (MAJOR)**:
- `PeerContextBar` 프리셋 탭 ≥ 36px 높이 + 가로 스크롤
- `MoverCard` hover 툴팁을 tap-toggle로 전환
- `MobileNav`에 Chain Sight, Thesis Control 등 핵심 기능 추가
- 스크리너/뉴스 등 100+ 항목 목록에 virtualization 도입
- `chart fontSize={9}` → `12` 이상

**장기 (MINOR)**:
- `text-[8px]`/`text-[10px]` 정보 라벨 정책화 (최소 11px 권장)
- `InvestingHeader.tsx` 사용 계획 명확히 — 사용 안 하면 삭제, 사용 시 모바일 대응

---

**감사 종료** | 다음 산출물과 교차 참조: `performance_audit.md`, `api_consistency_audit.md`
