# 모바일 UX 감사 보고서

- **작성일**: 2026-05-24
- **대상**: `frontend/` 전체 (Next.js 16, Tailwind v4)
- **기준 뷰포트**: 375px (iPhone SE/12 mini), 390px (iPhone 14)
- **터치 타겟 기준**: Apple HIG 44×44pt, Material 48×48dp
- **방법**: 정적 코드 분석 (Grep / 컴포넌트 Read). 런타임 측정 없음 — 실제 픽셀 높이는 Tailwind 클래스로부터 추정.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 설명 |
|--------|------|------|
| **BLOCKER** | 0 | 모바일에서 사용 자체가 불가능한 이슈 없음. `MobileNav` 하단 탭바 + `isMobile` 분기 + grid 모바일 우선 패턴이 잘 깔려 있음. |
| **MAJOR** | 8 | 핵심 인터랙션이 44pt 미만이거나, 모바일 진입점이 누락된 케이스. |
| **MINOR** | 9 | 가독성 저하, 보조 정보의 작은 텍스트, 향후 확장 시 성능 우려. |

### 종합 진단

- ✅ **잘된 점**: `MobileNav.tsx` (Bottom Nav, `md:hidden`, `min-h-[44px]`), `chainsight/[symbol]` `isMobile` 분기 + `MobileCardList` 별도 컴포넌트, `thesis/[thesisId]` `max-w-lg mx-auto` 모바일 우선 레이아웃, 15개 차트 파일 모두 `ResponsiveContainer` 사용, 33개 위치에서 `overflow-x-auto`로 테이블 가로 스크롤 처리.
- ⚠ **체계적 결함**:
  1. **`text-[10px]` 남용** — 73+ 위치. 정보용은 무방하나, 일부는 `cursor-pointer` 영역.
  2. **`MobileNav` 5개 탭 한계** — `thesis`, `chainsight`, `screener`, `market-pulse` 등 핵심 화면이 하단 탭에 없음. 헤더 햄버거는 `audit P0 #12`로 `hidden` 처리됨 → **모바일에서 진입 경로 없음**.
  3. **모바일 검색 부재** — `Header.tsx`의 검색바는 `hidden md:block`. 햄버거도 hidden → 모바일에서 종목 검색 불가.
  4. **가상화(virtualization) 0건** — `react-window`/`virtuoso` 미사용. 500+ 종목 스크리너/뉴스 리스트 모바일 스크롤 성능 우려.

---

## 반응형 누락

### 1. 고정 폭 사용 현황 (`w-[NNpx]`, `min-w-[NNpx]`, `max-w-[NNpx]`)
- 총 **36회 / 26개 파일**. 대부분 `max-w-[…]`로 자동 축소되어 375px 안전.
- **375px 안전한 케이스**:
  - `InvestingHeader.tsx:32`: `max-w-[1400px] mx-auto px-4` — 모바일에서 자동 축소 ✅
  - `ScreenerTable.tsx:209,224,307`: `max-w-[180px]/120px/200px` truncate ✅
  - `NodeTooltip.tsx:141`, `SectorBar.tsx:41`, `RelationLegend.tsx:51`: 모두 `max-w` + truncate ✅
- **잠재적 overflow 위험**:
  - `IndicatorRow.tsx:108`: 한 줄에 `min-w-[60px]` 값 + `min-w-[120px]` 변동률 + `max-w-[100px]` 스파크라인 + 우측 지지/반박. 합계 ≥ 280px + 좌측 padding 16px. **375px 거의 한계** — 한국어 라벨("전분기대비")이 길면 줄바꿈 또는 우측 텍스트가 잘릴 가능성. **MAJOR**
  - `MarketGraphCanvas.tsx:676`: `w-[110px] min-h-[68px]` 인기 섹터 버튼 3개 + `gap-3`. 110×3 + 24 = 354px, `flex-wrap`이 적용되어 있어 wrap 가능 ✅
  - `SignalDetailSheet.tsx:97`: `w-full md:w-[420px]` — 모바일 full-width ✅
  - `ChatInterface.tsx:198`: `w-[52px] h-[52px]` 전송 버튼 — 적절한 터치 타겟 ✅

### 2. `sm:/md:/lg:` 브레이크포인트 없이 데스크톱 전용 grid
- **MAJOR**: `frontend/components/rag/MonitoringDashboard.tsx:131,261` — `grid-cols-3 gap-3` (모바일 분기 없음). 카드 3개를 375px에서 약 110px씩 — 텍스트 압축.
- **MAJOR**: `frontend/app/market-pulse-v2/details/BreadthDetail.tsx:29`, `FlowDetail.tsx:34`, `cards/FlowCardSummary.tsx:13` — `grid-cols-3 gap-2 text-center` 헤더. 모바일에서 그대로 3컬럼.
- **MINOR**: `MarketBreadthCard.tsx:107`, `MoverCard 툴팁`, `MLModelCard.tsx:110`, `YieldCurveChart.tsx:147` — `grid-cols-3 gap-3` (정보 카드, 작지만 정렬 가능).
- ✅ **대부분 정상**: 36개 grid 사용 중 약 75%가 `grid-cols-1 (sm:|md:|lg:)2-6` 모바일 우선 패턴.

### 3. 테이블/차트 가로 스크롤 처리
- **33개 위치 `overflow-x-auto` 적용** ✅
  - `ScreenerTable`, `PortfolioTable`, `StockTable`, `CollectionStatsTable`, 모든 admin 탭, `SignalSummaryCard`, `SignalFilterTabs`, `chainsight/SectorBar`, `chainsight/RelationFilterChips` 등.
- ❌ **누락 의심**:
  - `frontend/app/stocks/[symbol]/page.tsx:843` — `overflow-x-auto` 있음 ✅
  - `frontend/components/financial/QuickAddDropdown.tsx:197` — `w-80` 드롭다운, 모바일 절반 화면 차지 → `max-w-[calc(100vw-2rem)]` 등 fallback 없음. **MINOR**

### 4. 데스크톱 전용 사이드/패널
- `app/ai-analysis/page.tsx:294`: `absolute left-4 top-20 z-50 w-96` 좌측 패널 — 모바일 분기 없음. **MAJOR**
- `app/ai-analysis/page.tsx:304`: `absolute right-4 top-20 z-50 w-80` 우측 패널 — 모바일 분기 없음. **MAJOR**
- `chainsight/FilterPanel.tsx:71`: `absolute top-12 right-4 z-50 w-72` — `[symbol]/page.tsx`에서 모바일 isMobile 분기로 호출 자체를 안 하면 OK. 단독 호출 시 위험.
- `chainsight/[symbol]/page.tsx:358`: `<aside className="w-72 ... hidden lg:block">` — 우측 패널 `lg:` 이상에서만 표시 ✅
- `chainsight/[symbol]/page.tsx:298`: 좌측 AI Guide `w-60`. 모바일에서는 `isMobile` 분기로 미표시 ✅

---

## 터치 타겟

### 44pt 보장 컴포넌트 (정상) ✅
- `MobileNav.tsx:34`: 하단 탭 `min-h-[44px]`
- `Header.tsx:160`: 햄버거 `min-h-[44px] min-w-[44px]` (단 현재 `hidden`)
- `screener/Pagination.tsx:127`: `min-w-[44px] min-h-[44px]`
- `validation/SignalSummaryCard.tsx:41`: 카테고리 신호등 `min-w-[72px] min-h-[44px]`
- `strategy/ScreenerTable.tsx:323`: peer 액션 `min-h-[44px] min-w-[44px]`
- 총 13개 파일에서 `min-h-[44]` 적용.

### MAJOR — 핵심 인터랙션의 44pt 미달
1. **`thesis/dashboard/IndicatorRow.tsx:177-190`** — 차트 기간 토글 1M/1Y/3Y/5Y
   - 클래스: `px-2.5 py-0.5 text-[10px] rounded`
   - 추정 높이: `py-0.5(4px) + text-[10px](≈14px line) = ~22px`
   - 관제실 펼침 시 주요 인터랙션. 손가락으로 정확히 누르기 어려움.
2. **`chainsight/[symbol]/page.tsx:209-227`** — 모바일 BottomSheet 노드 액션 (탐색/가설/검증)
   - 클래스: `flex-1 text-center text-xs py-2 rounded-lg`
   - 추정 높이: `py-2(16px) + text-xs(≈16px) = ~32px`
   - 모바일 전용 인터랙션인데 44pt 미달.
3. **`chainsight/[symbol]/page.tsx:250-262`** — Depth 1/2/3 버튼
   - 클래스: `px-3 py-1.5 ... text-sm`
   - 추정 높이: `py-1.5(12px) + text-sm(20px) = ~32px`
   - 데스크톱 헤더지만 태블릿/소형 노트북에서도 작음.
4. **`eod/SignalDetailSheet.tsx:188-197`** — 키워드 칩 (`cursor-pointer transition-colors`)
   - 클래스: `text-[10px] px-1.5 py-0.5 rounded`
   - 추정 높이: `py-0.5(4px) + text-[10px](14px) = ~18px` ← 매우 작음. 클릭 가능 요소.
5. **`thesis/builder/SuggestionCard.tsx` / `PremiseCard.tsx`** — 가설 빌더 옵션 칩 일부 `text-[10px]` + 짧은 padding.
6. **`screener/AdvancedFilterPanel.tsx:247,266`** — 필터 카운트 배지 `text-[10px]` (배지지만 모달 트리거 영역 포함).
7. **`Header.tsx:111-122`** — 검색바 `hidden md:block`, **모바일에서 검색 진입점 없음** (햄버거도 hidden). MobileNav에도 검색 미포함.
8. **`Header.tsx 모바일 메뉴 Link`** (167-241행) — 햄버거 비활성화 상태이므로 표시되지 않음. 코드는 살아 있지만 UX 경로 단절.

### MINOR — 가독성 저하 (클릭 영역 아님)
- `text-[9px]`: `keywords/KeywordTag.tsx:69,77,94`, `thesis/AddIndicatorSheet.tsx:240`, `screener/PresetGallery.tsx:213`, `screener/AdvancedFilterPanel.tsx`
- `text-[10px]` 정보용: `MoverCard`, `KeywordList`, `BriefCardSummary`, `MarketNewsSection` 등 ~60+ 위치.
- 정보 표기에는 무방하나, 한국어 환자/한자 혼용 시 가독성 한계.

### 특히 지시받은 케이스
- **`thesis 관제실 지표 카드`** (`IndicatorRow`):
  - 카드 전체 `<button>`이 `w-full ... px-4 py-3` → 약 56px 이상, 카드 토글은 ✅
  - 펼친 후 기간 토글은 **MAJOR(위 #1)**
- **`validation 프리셋 탭`** (`SignalSummaryCard`):
  - 신호등 버튼 `min-w-[72px] min-h-[44px]` ✅
  - 단, 신호등 원 자체는 `w-11 h-11 = 44×44px`이고 부모가 `flex-col` — 텍스트까지 합쳐 hit area 충분.
- **`chainsight 노드`** (`MarketGraphCanvas` / `GraphCanvas`):
  - Force-directed 노드는 canvas 안에 그려짐 — Tailwind hit area 측정 불가. 노드 클릭은 react-force-graph의 노드 반경(`val: 10`)에 의존. 데스크톱 마우스는 OK, **모바일 손가락은 어려움** → 모바일에서는 `MobileCardList`로 대체하는 분기가 있어 ✅.

---

## 네비게이션

### Bottom Navigation ✅
- `components/layout/MobileNav.tsx`: `fixed bottom-0 ... md:hidden z-50`, 5개 탭 (홈/종목/뉴스/포트폴리오/내정보), 각 `min-h-[44px]`, `aria-label` 정상.
- `audit P0 #12,#13` 주석으로 명시적 보강 흔적 ✅.

### Hamburger / Drawer
- `Header.tsx:157-163`: 햄버거 버튼이 `className="hidden ..."` → **항상 비활성화**. 주석상 "이중 네비 제거 + MobileNav 단일 소스" 의도.
- `Header.tsx:166-257`: 모바일 메뉴 div(`md:hidden`) 코드는 살아 있으나 `isMenuOpen`을 토글할 트리거가 없음 → **dead code**.
- 결과: **MobileNav에 없는 라우트(`/thesis`, `/chainsight`, `/screener`, `/market-pulse`, `/admin`)는 모바일에서 URL 직접 입력 또는 외부 링크로만 접근 가능**. **MAJOR**.

### 핵심 진입점 누락
- 검색 진입점 없음 (위 터치 #7).
- AI 분석(`/ai-analysis`), Market Pulse v2, Admin 등 모바일 탭 미등록.

### 긴 목록 Virtualization
- `react-window`, `react-virtuoso`, `virtualize` 검색 결과 **0건**.
- 영향:
  - `screener/page.tsx` (S&P 500, 500+ 행): 모바일에서 전체 렌더 시 메모리/스크롤 부담. **MINOR** (현재 페이지네이션으로 완화 중).
  - `news/page.tsx`: 카테고리별 뉴스 리스트, 무한 스크롤 시 잠재 이슈.
  - `chainsight/MobileCardList`: 카드 리스트, 노드 수가 적으면 OK. 깊이 3+ 에서 100+ 노드면 위험.

---

## 차트/그래프

### Recharts `ResponsiveContainer` 사용 현황 — 15개 파일 ✅
```
charts/StockPriceChart.tsx
market-pulse-v2/details/BreadthDetail.tsx
market-pulse-v2/details/FlowDetail.tsx
market-pulse-v2/details/RegimeDetail.tsx
market-pulse-v2/details/SectorDetail.tsx
thesis/dashboard/IndicatorRow.tsx
thesis/dashboard/IndividualMiniCharts.tsx
admin/news/MLTrendChart.tsx
validation/MetricBarChart.tsx
screener/SectorHeatmap.tsx
macro/YieldCurveChart.tsx
news/SentimentChart.tsx
stock/StockChart.tsx
portfolio/PortfolioChart.tsx
```
- `IndicatorRow.tsx:197,235`: `ResponsiveContainer width="100%" height={160}` / `height={140}` — 모바일에서도 동일. 적절.
- `XAxis fontSize={9}` / `YAxis fontSize={10}` (IndicatorRow:207,211): 모바일에서 축 레이블 매우 작음. 그러나 차트 자체가 작은 카드 안이라 디자인 의도. **MINOR**

### Recharts 미사용 / 자체 캔버스
- **`chainsight/MarketGraphCanvas.tsx`** (force-directed): width/height props 직접 받음. 모바일 분기로 대체 컴포넌트(`MobileCardList`) 제공 ✅
- **`chainsight/GraphCanvas.tsx`** (react-force-graph-2d): `canvasSize.w/h` state 사용, `containerRef` 측정. 모바일 분기 ✅ (단 measurement effect의 신뢰성은 별도 검증 필요)

### 분기 스파크라인 모바일 가독성
- `thesis/dashboard/QuarterlySparkline.tsx` — `min-h-[44px]` 명시 ✅
- `IndicatorRow.tsx:132`: 인라인 스파크라인 `max-w-[100px]`, 최근 4분기 — 모바일 한 줄에 들어가나, 다른 요소와 함께 배치 시 압축됨 (위 반응형 #1 참조).

---

## 페이지별 상세

### `/` (홈, `app/page.tsx`, 115줄)
- 상태: 짧은 랜딩 페이지로 추정. 별도 이슈 없음.

### `/dashboard` (`app/dashboard/page.tsx`, 141줄)
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6` ✅
- `sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6` (117/123/129행): 모바일에서는 block, sm 이상에서 grid ✅
- **이슈 없음**

### `/stocks/[symbol]` (`app/stocks/[symbol]/page.tsx`, 1078줄)
- `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4` (568행) ✅
- `overflow-x-auto` × 2 (843, 1030행) ✅
- `flex gap-2 overflow-x-auto pb-3 scrollbar-hide` (1030행): 탭/칩 가로 스크롤 ✅
- **MINOR**: 1078줄 → 컴포넌트 분리 권장 (모바일 첫 페인트 비용).

### `/screener` (`app/screener/page.tsx`, 934줄)
- 모바일 전용 `MobileStockCard.tsx` 별도 ✅
- `MobileStockCard:164` `grid grid-cols-3 gap-2 rounded-lg bg-[#0D1117] p-2`: 시총/PER/거래량 3컬럼. `text-[10px] uppercase` 라벨 — 가독성 한계 **MINOR**.
- `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` (855행) ✅
- `AdvancedFilterPanel.tsx:142,247,266`: `text-[10px]` 설명 + 카운트 배지 → 모바일에서 매우 작음 **MINOR**.

### `/thesis/(list)` (`app/thesis/(list)/page.tsx`)
- 미열람, 별도 이슈 미확인.

### `/thesis/[thesisId]` (관제실, 138줄)
- `max-w-lg mx-auto px-4 pt-4 pb-20` ✅ (모바일 우선, 512px 폭, 하단 80px MobileNav 회피)
- `IndicatorRow` 카드 토글 ✅
- **MAJOR**: 펼친 후 1M/1Y/3Y/5Y 토글 `text-[10px] py-0.5` (위 터치 #1)
- **MAJOR**: 한 줄 정보 밀집 (값+변동률+스파크라인+지지) → 한국어 비교 라벨이 길면 줄바꿈/잘림 위험

### `/thesis/[thesisId]/indicators` / `close`
- 미열람, `AddIndicatorSheet.tsx` 빈도 라벨 `text-[9px]/[10px]` **MINOR**.

### `/thesis/new` (가설 빌더)
- `text-[10px]` 8회 (688, 752, 753, 765, 831, 843, 1063행): 라벨/카테고리/시간 — 정보용 **MINOR**.

### `/chainsight` (`app/chainsight/page.tsx`)
- 미열람.

### `/chainsight/[symbol]` (3-panel 워크스페이스)
- `isMobile` 상태 + `MobileCardList` 분기 ✅
- 우측 패널 `hidden lg:block` ✅
- **MAJOR**: 모바일 BottomSheet 액션 버튼 3개 `py-2 text-xs` ~32px (위 터치 #2)
- **MAJOR**: Depth 버튼 데스크톱 헤더 `px-3 py-1.5` ~32px (위 터치 #3, 태블릿에서 문제)
- ForceGraph 노드 hit area 모바일 부적합 → MobileCardList 분기로 우회 ✅

### `/market-pulse` / `/market-pulse-v2` (107줄)
- v2 `text-[10px]` 푸터 **MINOR**
- `details/BreadthDetail.tsx:29`, `FlowDetail.tsx:34`: **MAJOR** — `grid-cols-3` 모바일 분기 없음 (3개 카드 압축)

### `/news` (304줄)
- `grid grid-cols-1 lg:grid-cols-3 gap-4` (210행) ✅
- `MarketNewsSection.tsx:186,196`: `text-[10px]/[9px]` 메타데이터 **MINOR**
- `NewsHighlightedStocks.tsx:118`: `overflow-x-auto scrollbar-hide` ✅

### `/portfolio` (267줄)
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4` (228행) ✅
- `PortfolioTable:210`: `grid-cols-2 md:grid-cols-3 lg:grid-cols-6` ✅ + `overflow-x-auto`(259행)
- **이슈 없음**

### `/watchlist`
- `grid grid-cols-1 lg:grid-cols-3 gap-6` (207행) ✅
- `overflow-x-auto` (294행) ✅
- **이슈 없음**

### `/ai-analysis`
- **MAJOR**: 좌(`w-96`) / 우(`w-80`) 절대 위치 패널 모바일 분기 없음 (위 반응형 #4)

### `/admin`
- 데스크톱 전용 가정. `AdminTabNav.tsx:30` `overflow-x-auto` ✅
- 다수 테이블 `overflow-x-auto` ✅
- 모바일 사용 시나리오 외이면 MINOR.

### `/login`, `/signup`, `/mypage`
- 미열람, 별도 이슈 미확인.

---

## 권장 우선순위 (수정 시 가치 vs 비용)

1. **`MobileNav` 진입점 확장 또는 햄버거 부활** — `thesis`/`chainsight`/`screener` 모바일 접근 경로 확보. (1줄 수정 또는 햄버거 `hidden` 제거)
2. **`Header` 모바일 검색** — 검색 바 모바일 노출 또는 MobileNav에 `Search` 탭 추가.
3. **`IndicatorRow` 차트 기간 토글** — `min-h-[44px]` + `text-xs` 이상으로 변경.
4. **`chainsight` 모바일 BottomSheet 액션 버튼** — `py-3` 이상.
5. **`market-pulse-v2 BreadthDetail/FlowDetail`** — `grid-cols-1 sm:grid-cols-3` 분기 추가.
6. **`ai-analysis` 패널** — 모바일 분기 또는 Sheet 컴포넌트로 전환.
7. (선택) virtualization 도입 — `screener` 500+ 종목 모바일 스크롤 개선.
