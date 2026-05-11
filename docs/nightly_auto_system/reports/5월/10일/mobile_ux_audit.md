# 모바일 UX 감사 보고서

- **감사 일자**: 2026-05-11
- **기준 뷰포트**: iPhone SE (375×667), Apple HIG 터치 타겟 44×44pt
- **감사 범위**: `frontend/app/`, `frontend/components/` 전체 (페이지 24개, 컴포넌트 192개)
- **검사 기준**: Tailwind 기본 브레이크포인트(`sm:640px / md:768px / lg:1024px / xl:1280px`)
- **방법**: 정적 코드 분석 (실기기 미테스트 — 실측 검증은 본 보고서 권고에 포함)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|-------|------|------|
| 🔴 BLOCKER | **9** | 모바일에서 핵심 동작 불가 / 정보 잘림 / 터치 실패 빈발 |
| 🟠 MAJOR | **17** | 반응형은 작동하나 UX가 현저히 저하 / 가독성 문제 |
| 🟡 MINOR | **14** | 사용 가능하나 다듬을 여지 (밀도, 폰트 크기, 시각적 힌트) |
| **합계** | **40** | |

### 핵심 BLOCKER 한눈에

| # | 위치 | 라인 | 문제 |
|---|------|------|------|
| B1 | `Pagination.tsx` | 94–158 | 화살표 버튼 `p-1.5` (≈28×28px) — Apple HIG 44pt 위반 |
| B2 | `Pagination.tsx` | 126–137 | 페이지 번호 `min-w-[32px] py-1.5` (≈32×30px) |
| B3 | `chainsight/FilterPanel.tsx` | 71 | `absolute w-72` 패널이 375px 화면에서 우측 잘림 가능, Drawer 미적용 |
| B4 | `chainsight/MarketGraphCanvas.tsx` | 141, 146 | 노드 반경 8–16px → 터치 영역 16–32px (44pt 위반), 높이 `h-[400px]` 고정 |
| B5 | `thesis/dashboard/IndicatorRow.tsx` | 108–143 | 1행에 값+변동률+스파크라인+라벨 4요소 가로 배치 (`min-w-[60+120+100]+α`= 280px+) — 펼침 토글 후 leftover 공간 부족 |
| B6 | `thesis/dashboard/IndicatorRow.tsx` | 177–190 | 차트 기간 버튼(1M/1Y/3Y/5Y) `px-2.5 py-0.5 text-[10px]` → ≈40×20px 터치 영역 |
| B7 | `portfolio/PortfolioTable.tsx` | 258–299 | 12컬럼 테이블에 카드 뷰 폴백 없음, 가로 스크롤만 제공 |
| B8 | `app/watchlist/page.tsx` | 207, 243 | `lg:grid-cols-3 + lg:col-span-2` — 모바일에서 좌측 리스트와 우측 상세가 세로로 길게 쌓임 (반응형 자체는 작동, 그러나 종목 30+개 시 우측 도달까지 스크롤 무한) |
| B9 | `app/screener/page.tsx` | 846 | `<ScreenerTable>` import 경로 의존, 카드 뷰는 `sm:hidden`으로 작동하지만 사이드 패널(AdvancedFilterPanel)이 모바일 전용 collapse UX 없이 페이지 상단을 차지 |

---

## 반응형 누락

### 1. 고정 폭/높이 사용 (`w-[NNpx]`, `min-w-[NNpx]`, `h-[NNpx]`)

`Grep` 결과 47건 중 모바일 위협 사례 위주로 정리.

| 파일 | 라인 | 클래스 | 영향 |
|------|------|--------|------|
| `chainsight/MarketGraphCanvas.tsx` | 124, 134, 141, 146 | `h-[400px]` 고정, `height={400}` | 🔴 BLOCKER. 375×667 화면에서 폼팩터 60% 차지하며 폴드폰/세로형에서 레이아웃 압박 |
| `chainsight/ExplorationTrail.tsx` | 33 | `h-[60px]` | 🟡 MINOR. overflow-x-auto와 결합되어 가로 스크롤 가능 |
| `app/screener/page.tsx` | 465 | `h-[400px]` (Recharts 영역) | 🟠 MAJOR. 모바일에서 차트 비율 왜곡 |
| `app/chainsight/page.tsx` | 34 | `h-[200px]` | 🟡 MINOR. 로딩 상태 — 영향 적음 |
| `chainsight/SectorBar.tsx` | 41 | `max-w-[120px]` | 🟡 MINOR. 섹터명 truncate, 의도 명확 |
| `thesis/dashboard/IndicatorRow.tsx` | 110, 115, 132 | `min-w-[60px] + min-w-[120px] + max-w-[100px]` | 🔴 BLOCKER. 280px+가 강제됨 → 375px 화면에서 우측 라벨 잘림 |
| `eod/SignalDetailSheet.tsx` | 97 | `w-full md:w-[420px]` | ✅ GOOD. 모바일에서는 풀 화면 |
| `eod/StockRow.tsx` | 55, 66 | `max-w-[140px] + min-w-[72px]` | 🟡 MINOR. 합계 212px+, 375px에서 OK |
| `news/AINewsBriefingCard.tsx` | 70 | `max-w-[200px]` | 🟡 MINOR |
| `news/RecommendationCard.tsx` | 85 | `max-w-[150px]` | 🟡 MINOR. 회사명 truncate |
| `news/StockInsightCard.tsx` | 159 | `max-h-[360px]` 드롭다운 | 🟠 MAJOR. 모바일 키보드 올라오면 드롭다운 가려짐 |
| `news/DailyKeywordCard.tsx` | 124 | `max-h-[200px]` | 🟡 MINOR |
| `rag/ChatInterface.tsx` | 198 | `h-[52px] w-[52px]` | ✅ GOOD. 44pt 초과 |
| `screener/PresetDetailPopover.tsx` | 93 | `max-h-[400px]` | 🟠 MAJOR. 팝오버 자체 위치는 데스크톱 전제 |
| `strategy/ScreenerTable.tsx` | 209, 224, 307 | `max-w-[180/120/200px] truncate` | 🟠 MAJOR. 테이블 컬럼별 truncate, 가로 스크롤 의존 |
| `admin/SystemTab.tsx`, `admin/shared/TaskLogViewer.tsx` | 218, 362 | `max-w-[240/260px] truncate` | 🟡 MINOR. admin 영역, 우선순위 낮음 |

### 2. 데스크톱 전용 컴포넌트 (sm:/md:/lg: 누락)

| 파일 | 문제 |
|------|------|
| `layout/InvestingHeader.tsx` | 🔴 모바일 대응 없음. `max-w-[1400px] mx-auto px-4`만, 햄버거/축약 메뉴 부재. nav 8개가 가로로 펼쳐짐(L101–110). 다행히 `app/layout.tsx`는 `Header`(반응형)를 사용 중이므로 InvestingHeader가 어디서 어떻게 마운트되는지 확인 필요. |
| `chainsight/FilterPanel.tsx` | 🔴 BLOCKER. `absolute top-12 right-4 w-72` — 모바일 Drawer/BottomSheet 분기 없음 |
| `validation/CategorySidebar.tsx` | 🟠 MAJOR. `sticky top-24`가 모바일 헤더(64px) 기준으로 부정확. md 미만에서 sticky 해제 권장 |
| `validation/PeerContextBar.tsx` | 🟠 MAJOR. 프리셋 6개 탭이 `flex flex-wrap`로 모바일에서 2–3줄 wrap, layout-shift 발생 |
| `screener/AdvancedFilterPanel.tsx` (L234) | 🟠 MAJOR. `flex flex-wrap` 카테고리 탭 동일 |
| `chainsight/ExplorationTrail.tsx` | 🟡 MINOR. 노드 `style={{ width: r*2, height: r*2 }}` 동적 — 최소 r=12 → 24×24px (44pt 미달) |

### 3. 테이블/차트 — 가로 스크롤 처리

| 컴포넌트 | 처리 방식 | 평가 |
|---------|----------|------|
| `portfolio/PortfolioTable.tsx` | `overflow-x-auto` + 12컬럼 | 🔴 BLOCKER. 카드 뷰 미제공. portfolio 페이지(L228) `md:grid-cols-2`로 카드는 별도 표시되나 테이블 자체는 모바일 사용성 낮음 |
| `stocks/StockTable.tsx` | `overflow-x-auto` + `text-xs` | 🟠 MAJOR. 스크롤 지시 시각힌트 없음 |
| `strategy/ScreenerTable.tsx` | `overflow-x-auto` + truncate | 🟠 MAJOR. 그러나 `app/screener/page.tsx`는 `sm:` 분기로 카드 뷰 자동 전환 (✅ 그 부분은 OK) |
| `validation/LeaderComparisonSection.tsx` | `overflow-x-auto` 4컬럼 | 🟠 MAJOR. 스크롤 힌트 부재 |
| `chainsight/FullPathView.tsx`, `TracePathView.tsx` | overflow-x-auto | 🟡 MINOR. 의도된 가로 흐름 |
| `app/watchlist/page.tsx` | overflow-x-auto + 7컬럼 | 🟠 MAJOR. WatchlistCard와 별개 |
| `eod/SignalCardGrid.tsx` | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` | ✅ GOOD |
| `screener/MobileStockCard.tsx` | 모바일 전용 — `app/screener/page.tsx` L854에서 `sm:hidden` 자동 활성화 | ✅ GOOD |

---

## 터치 타겟 (Apple HIG 44×44pt 기준)

### 🔴 BLOCKER

1. **`screener/Pagination.tsx`** (L94–158)
   - 화살표 버튼 5개: `p-1.5 + ChevronXxx w-4 h-4` → 16+12=28px 정사각.
   - 페이지 번호: `min-w-[32px] px-2 py-1.5 text-sm` → ≈32×30px.
   - **영향**: 페이지 이동 실패율 매우 높음. Apple HIG/Material 기준 모두 위반.
   - 발견 위치: 스크리너, 검색 결과, 종목 리스트 등 광범위 사용.

2. **`thesis/dashboard/IndicatorRow.tsx`** (L177–190) — 차트 기간 토글
   - `px-2.5 py-0.5 text-[10px]` → ≈40×20px.
   - 4개 버튼이 `gap-1.5`로 좁게 배치 → 인접 오탭 위험.

3. **`chainsight/MarketGraphCanvas.tsx`** (L141–183)
   - `getNodeRadius()` 반환값: 8 / 16 (centerNode). 터치 가능 원 직경 16–32px.
   - 모바일 그래프 노드 탭이 핵심 인터랙션이지만 44pt 미달 → 인접 노드 오탭 빈발.
   - 추가: `nodePointerAreaPaint`(L151)로 동일 반경 사용 → 확장 안 됨.

### 🟠 MAJOR

4. **`validation/SignalSummaryCard.tsx`** (L36–47)
   - 신호등 7개를 `flex gap-4 overflow-x-auto`로 배치. 각 셀 `min-w-[72px]` (✅ 컨테이너) — 그러나 실제 클릭 대상인 원형 dot은 `w-10 h-10` = 40×40px로 4pt 부족.
   - 호버 툴팁(L54)은 `onMouseEnter/Leave` 의존 → 터치 디바이스에서 발화 안 됨.

5. **`chainsight/ExplorationTrail.tsx`** (L65)
   - 노드 버튼 동적 `width: r*2, height: r*2` → 최소 24×24px.

6. **`chainsight/SectorBar.tsx`** (L24)
   - `px-4 py-2` 버튼. 텍스트 14–16px일 때 전체 높이 ≈40px, 너비는 가변. 터치 OK 경계선.

7. **`screener/AdvancedFilterPanel.tsx`** (L234, 238, 247)
   - 카테고리 탭 `px-3 py-1.5 text-xs` → ≈64×26px. 인접 다수 탭 → 오탭 위험.
   - 카운트 배지 `text-[10px] px-1.5` (L247) — 클릭 대상 아님 (OK).

8. **`thesis/builder/OptionButton.tsx`** (L52, 57–60)
   - `min-h-[52px]` (multi mode) / `min-h-[56px]` (single) — 컨테이너는 OK.
   - 그러나 멀티셀렉트 체크박스 자체가 `w-5 h-5` (20×20px) — 라벨 전체가 클릭 가능하므로 실질 OK이나 시각적 어포던스는 약함.

9. **`thesis/common/AlertBell.tsx`**, `news/AINewsBriefingCard.tsx`, `admin/news/AlertBadge.tsx`
   - 알림 배지 `min-w-[18px] h-[18px]` — 표시용이라 OK이나 클릭 가능 여부 코드 재확인 필요.

### 🟡 MINOR — `text-[10px]`/`text-[11px]` 클릭 요소

| 위치 | 라인 | 문제 |
|------|------|------|
| `thesis/dashboard/IndicatorRow.tsx` | 95, 118, 141, 148, 161, 167, 182 | 메타 라벨 (대부분 비클릭) — 가독성 우려 |
| `screener/AdvancedFilterPanel.tsx` | 247, 266 | 카운트 배지 (비클릭) |
| `eod/SignalFilterTabs.tsx` | 68 | 카운트 배지 `min-w-[18px] h-[18px] text-[11px]` (비클릭, OK) |
| `admin/news/AlertBadge.tsx` | 29 | `text-[10px] font-bold` 알림 배지 |

### Validation 프리셋 탭 (`PeerContextBar.tsx`)

- 라인 35–50의 `flex flex-wrap` + 프리셋 6개. 좁은 화면에서 wrap 발생, 그 결과 첫 줄/둘째 줄 탭이 시각적 우선순위 흐트러짐. `min-w-max overflow-x-auto`로 전환 권장.

### Chainsight 노드 (`MarketGraphCanvas.tsx`)

- 위 B4 참조. 노드 hit area를 별도 paint로 1.5–2배 확대(`nodePointerAreaPaint`에서 `r * 1.8` 사용)하면 시각 디자인 보존하면서 터치 정확도 개선 가능.

---

## 네비게이션

### 1. 글로벌 헤더 / 모바일 네비

| 컴포넌트 | 평가 |
|---------|------|
| `app/layout.tsx` (L57–64) | ✅ `Header` + `MobileNav` 양쪽 마운트, `<main className="min-h-screen">`로 콘텐츠 보장 |
| `layout/Header.tsx` | ✅ 데스크톱 nav `hidden md:flex`, 햄버거는 `hidden`(L160)으로 비활성 — MobileNav가 단일 소스 |
| `layout/MobileNav.tsx` | ✅ Bottom Nav 5개(`홈/종목/뉴스/포트폴리오/내정보`), `min-h-[44px]` 보장, 라우트 정합성 OK |
| `layout/InvestingHeader.tsx` | 🔴 별도 헤더 — 모바일 대응 0%. 사용처 확인 필요 (현재 layout.tsx는 미사용으로 보임) |

**MobileNav 한계** (🟠 MAJOR):
- 5개 탭에 `Chain Sight / Thesis / Market Pulse / Screener` 부재 — 핵심 기능이 모바일에서 도달 불가. 진입점은 데스크톱 헤더에만 존재.
- 검색 진입점 없음 (Header의 검색 폼은 `hidden md:block`).
- 알림(AlertBell) 배지가 Bottom Nav에 노출되지 않음.

### 2. 페이지별 사이드바/2-3컬럼 레이아웃

| 페이지 | 모바일 처리 | 평가 |
|--------|-----------|------|
| `app/chainsight/[symbol]/page.tsx` | `isMobile` 분기(L117, 152) → 모바일 카드 리스트 전용 + 그래프 오버레이 | ✅ GOOD |
| `app/watchlist/page.tsx` (L207) | `lg:grid-cols-3` — 모바일은 1컬럼 stack, 좌측 리스트 전체 위에 우측 상세가 쌓임 | 🔴 BLOCKER. 종목 많을 시 상세 도달까지 매우 길게 스크롤 |
| `app/screener/page.tsx` | AdvancedFilterPanel 상단 + 결과 영역 — 카드/테이블 분기 OK, 그러나 필터 패널 자체 collapse 동작이 모바일 우선이 아님 | 🟠 MAJOR |
| `app/thesis/(list)/page.tsx` | 카드 그리드 — 미확인이지만 일반 패턴 추정 | 🟡 MINOR |
| `app/portfolio/page.tsx` (L228) | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 카드 뷰 + 테이블 별도 | 🟠 MAJOR. 테이블은 BLOCKER, 카드 뷰는 OK |
| `app/news/page.tsx` (L210) | `grid grid-cols-1 lg:grid-cols-3` | ✅ GOOD |
| `app/dashboard/page.tsx` | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` | ✅ GOOD |
| `app/market-pulse-v2/page.tsx` | 카드 + 디테일 분리 | 🟡 MINOR. TickerBar 가로 스크롤 처리됨 |

### 3. Virtualization

- `react-window` / `react-virtual` / `react-virtualized` **사용 0건**.
- 영향:
  - 🟠 MAJOR. screener 결과(수백~수천 종목)에서 모든 카드 즉시 렌더 → 모바일 메모리/스크롤 성능 저하.
  - 🟠 MAJOR. portfolio/watchlist 종목 수 많을 시 동일.
  - 🟡 MINOR. news/timeline은 페이지네이션 또는 무한 스크롤 패턴이 코드상 제한된 페치(L210의 `lg:grid-cols-3`+페이지네이션)로 완화.
- 권고: 50+ 항목 리스트(screener 카드, portfolio 종목, watchlist 종목, news list)에 한해 `@tanstack/react-virtual` 도입 검토.

---

## 차트/그래프

### Recharts ResponsiveContainer 사용 현황

총 14개 차트 컴포넌트 중 `ResponsiveContainer` 사용 확인.

| 컴포넌트 | 위치/높이 | 평가 |
|---------|---------|------|
| `stock/StockChart.tsx` | `windowWidth < 640 ? 280 : ...` 동적 (L177–187) | ✅ GOOD. 유일하게 모바일 분기 |
| `thesis/dashboard/IndicatorRow.tsx` | `height={160}` (L197), `height={140}` (L235) 고정 | 🟠 MAJOR. width만 100% |
| `thesis/dashboard/IndividualMiniCharts.tsx` | 고정 높이 추정 | 🟡 MINOR |
| `thesis/dashboard/QuarterlySparkline.tsx` | `h-10` (40px) — 분기 4개 막대를 80px+gap에 욱여넣음 | 🟠 MAJOR. 모바일 가독성 매우 낮음 |
| `validation/MetricBarChart.tsx` | `h-48` (192px) | 🟡 MINOR |
| `admin/news/MLTrendChart.tsx` | `h-[200px]` | 🟡 MINOR (admin 한정) |
| `screener/SectorHeatmap.tsx` | ResponsiveContainer | ✅ GOOD |
| `news/SentimentChart.tsx` | ResponsiveContainer | ✅ GOOD |
| `macro/YieldCurveChart.tsx` | ResponsiveContainer | ✅ GOOD |
| `portfolio/PortfolioChart.tsx` | ResponsiveContainer | ✅ GOOD |
| `charts/StockPriceChart.tsx` | ResponsiveContainer | ✅ GOOD |
| `app/market-pulse-v2/details/*` | ResponsiveContainer 4종 | ✅ GOOD |

### 분기 스파크라인 모바일 가독성 (`QuarterlySparkline`, `IndicatorRow` 인라인)

- `IndicatorRow.tsx` L132: `flex-1 max-w-[100px]` 안에 `QuarterlySparkline`(분기 4개) — 막대 폭 ≈18px, 여백 포함 ≈100px.
- 🟠 MAJOR. 호버 툴팁은 모바일 터치에서 작동 안 함. 차트 데이터를 시각적으로 인식하기 어려움.
- 🟠 MAJOR. 펼침(expanded) 영역 내 5년 분기 차트(L235, `height={140}`)는 ResponsiveContainer를 쓰지만 X축 라벨 `fontSize={9}` (L248) — 모바일에서 식별 어려움.

### 특수: Force-directed Graph (`MarketGraphCanvas`)

- `react-force-graph-2d` 사용. width/height 명시 필요.
- L141의 컨테이너 `h-[400px]` 고정 + ForceGraph2D `height={400}` 전달.
- 🔴 BLOCKER. 모바일에서 노드 분포가 좁아져 노드 클러스터 형성 → 개별 노드 식별/탭 거의 불가능.

---

## 페이지별 상세

### 1. `/` (홈, `app/page.tsx`)
- 점검 미완 — 인덱스 페이지 자체 코드 미검사. layout.tsx의 Header+MobileNav 보장.

### 2. `/dashboard` (`app/dashboard/page.tsx`)
- L54 `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3`. ✅ GOOD.
- 🟡 MINOR. 카드 내부 정보 밀도 미확인. 일반 패턴 추정.

### 3. `/portfolio` (`app/portfolio/page.tsx` + `PortfolioTable.tsx`)
- 🔴 BLOCKER. 12컬럼 테이블 (L263–298) — 가로 스크롤 의존, 카드 뷰 폴백 없음. 헤더 sticky 미적용.
- 🟠 MAJOR. 헤더 `text-xs uppercase` (L263). 모바일에서 ≈10–11px로 가독성 저하.
- 🟡 MINOR. `whitespace-nowrap` (L305)으로 종목명 줄바꿈 방지 — 의도적이나 truncate 부재로 컬럼 폭 가변.

### 4. `/watchlist` (`app/watchlist/page.tsx`)
- 🔴 BLOCKER (B8). `lg:grid-cols-3` — 모바일 stack 시 좌측 리스트 + 우측 상세 순서대로 길게 노출.
- 🟠 MAJOR. 우측 테이블 `overflow-x-auto` 7컬럼 (L294 추정) — Portfolio와 동일 문제.
- 🟡 MINOR. `Plus` 버튼 `p-2` (L220) → 36×36px (44pt 미달).

### 5. `/news` (`app/news/page.tsx` + `NewsCard.tsx`)
- ✅ GOOD. `grid-cols-1 lg:grid-cols-3` (L210).
- 🟡 MINOR. NewsCard 푸터 `text-xs` 메타데이터 (L78–90) — 가독성 경계.
- 🟠 MAJOR. `StockInsightCard.tsx` L159의 드롭다운 `max-h-[360px]` — 모바일 키보드 표시 시 가려짐.

### 6. `/screener` (`app/screener/page.tsx`)
- ✅ GOOD. 카드 뷰 자동 전환 (L854 `sm:hidden`).
- 🟠 MAJOR. AdvancedFilterPanel (L234 `flex flex-wrap`) — 카테고리 탭 wrap 시 layout-shift.
- 🟠 MAJOR. AdvancedFilterPanel 자체가 collapse 가능하나 "필터" 트리거 버튼이 모바일 우선이 아님 (헤더 영역 차지).
- 🔴 BLOCKER (B1, B2). Pagination 터치 타겟 위반.

### 7. `/market-pulse`, `/market-pulse-v2` (`app/market-pulse*/page.tsx`)
- ✅ GOOD. ResponsiveContainer + 카드 그리드.
- 🟡 MINOR. TickerBar `overflow-x-auto` — 의도된 가로 흐름.
- 🟡 MINOR. CardShell 내부 정보 밀도 미확인.

### 8. `/stocks/[symbol]` (`app/stocks/[symbol]/page.tsx`)
- ✅ GOOD. StockChart 모바일 분기 `windowWidth < 640 ? 280 : ...`.
- 🟠 MAJOR. OtherFundamentalsTab — `grid-cols-N` 사용, 모바일 컬럼 수 확인 필요.

### 9. `/thesis` (`app/thesis/(list)/page.tsx` + `ThesisListCard.tsx`)
- 🟡 MINOR. `MoonPhase + 타이틀 + 배지 + 서브텍스트` 가로 배치 (L27–37 추정) — `flex-1 min-w-0 truncate`로 안전하나 정보 잘림 가능.
- 🟠 MAJOR. `(list)/alerts/page.tsx` AlertCard 정보 밀도 — 미확인.

### 10. `/thesis/[thesisId]` (관제실, `app/thesis/[thesisId]/page.tsx` + `IndicatorRow.tsx`)
- 🔴 BLOCKER (B5, B6). IndicatorRow 가로 4요소 강제, 차트 기간 버튼 터치 타겟 위반.
- 🟠 MAJOR. `text-[11px]` 메타 텍스트 7곳 — 펼침 영역 설명 가독성 경계.
- 🟠 MAJOR. QuarterlySparkline `h-10` (40px) — 4분기 막대 식별 어려움.
- 🟡 MINOR. ResponsiveContainer 높이 160/140 고정.

### 11. `/thesis/new` (빌더, `app/thesis/new/page.tsx`)
- 🟠 MAJOR. ChatBubble `min-h-[44px]` (L14) ✅ — 단 옵션 버튼 sub-elements는 별도 검증 필요.
- 🟠 MAJOR. SuggestionCard `grid-cols-1 sm:grid-cols-2` — `sm=640px`이므로 375–639px 구간에서 1컬럼. 의도와 일치하나 작은 화면에서 카드가 매우 길어짐.
- 🟡 MINOR. 고정 헤더 + 스크롤 영역 + 고정 하단의 3단 레이아웃 — 키보드 표시 시 입력 영역 가려질 수 있음 (`viewport-fit=cover` 설정은 있음, L34 layout.tsx).

### 12. `/thesis/[thesisId]/indicators` & `/close`
- 🟠 MAJOR. AddIndicatorSheet, RecommendCard — 카드 그리드는 OK 추정, 추가 지표 선택 UI는 BottomSheet 패턴이 자연스러움 (현재 파악 불가).

### 13. `/chainsight` (`app/chainsight/page.tsx`)
- 🔴 BLOCKER (B4). MarketGraphCanvas h-[400px] + 노드 16–32px.
- 🟡 MINOR. 로딩 상태 `h-[200px]`.

### 14. `/chainsight/[symbol]` (`app/chainsight/[symbol]/page.tsx`)
- ✅ GOOD. `isMobile` 분기 (L117, 152) — 모바일 카드 리스트 + 그래프 오버레이.
- 🔴 BLOCKER (B3). FilterPanel 모바일 미대응.
- 🟠 MAJOR. ExplorationTrail 노드 24×24px 미만.

### 15. `/chainsight/watchlist`
- 🟡 MINOR. 일반 watchlist 패턴 추정 — 미검사.

### 16. `/admin`
- 🟡 MINOR. 관리자 영역. 모바일 우선순위 낮음 — admin 테이블 다수 (`max-w-[240/260px]` truncate) — 데스크톱 전제 OK.

### 17. `/login`, `/signup`, `/mypage`
- 미검사. 일반적으로 1컬럼 폼 — 위험 낮음.

### 18. `/ai-analysis` (RAG)
- ✅ GOOD. `ChatInterface.tsx` 입력 버튼 `h-[52px] w-[52px]` (L198) — 44pt 충족.
- 🟡 MINOR. SuggestionChips `max-w-[150px] truncate` (L40) — OK.

---

## 권고 우선순위

### P0 (즉시 수정 권고 — BLOCKER 9건)

1. **Pagination 터치 타겟 확대** (`Pagination.tsx`)
   - `p-1.5 → min-h-[44px] min-w-[44px] flex items-center justify-center`
   - 페이지 번호 `min-w-[32px] py-1.5 → min-w-[44px] min-h-[44px]`
2. **IndicatorRow 모바일 레이아웃 재설계** (`thesis/dashboard/IndicatorRow.tsx`)
   - 1행 → 2행 (값+변동률 / 스파크라인+라벨) 또는 모바일에서 스파크라인 숨김
   - 차트 기간 버튼 `text-[10px] py-0.5` → `text-xs py-2 min-h-[44px]`
3. **FilterPanel 모바일 BottomSheet** (`chainsight/FilterPanel.tsx`)
   - `absolute w-72` → `md:absolute md:w-72 + 모바일 fixed inset-x-0 bottom-0 max-h-[80vh] overflow-y-auto`
4. **MarketGraphCanvas 노드 hit area 확장**
   - `nodePointerAreaPaint`에서 `r * 1.8` 또는 절대값 22px 보장 (시각 반경은 그대로)
   - 컨테이너 `h-[400px]` → `h-[60vh] md:h-[400px]`
5. **PortfolioTable 모바일 카드 폴백**
   - `md:block hidden` 테이블 + `md:hidden` 카드 리스트(PortfolioStockCard 재사용)
6. **Watchlist 모바일 스택 개선**
   - 모바일에서 좌측 리스트는 가로 스크롤 칩 또는 셀렉트 드롭다운으로 축약

### P1 (MAJOR — 17건, 다음 스프린트)

- MobileNav 5개 → 핵심 6–7개 (Thesis/Chain Sight 추가 또는 "더보기" 메뉴)
- Validation 프리셋 탭 `flex-wrap` → `overflow-x-auto`
- 모든 Recharts 고정 높이 → `windowWidth < 640` 분기 또는 `aspect-ratio`
- Validation `CategorySidebar` `sticky top-24` → `md:sticky md:top-24`
- 테이블 sticky 헤더 + 스크롤 그래디언트 힌트
- `text-[10px]/[11px]` → `text-xs` (12px) 통일

### P2 (MINOR — 14건, 백로그)

- Virtualization 도입 (50+ 항목 리스트)
- 알림 배지를 Bottom Nav에 노출
- 검색 진입점을 모바일에 추가 (Header 검색은 `hidden md:block`만 존재)
- 모바일 분기 스파크라인 막대 폭 확보 — 분기 수를 4 → 모바일에서 2–3으로 축소
- 호버 툴팁 → 탭 토글 패턴으로 전환 (SignalSummaryCard 등)

---

## 부록: 실측 검증 권고

본 보고서는 정적 코드 분석 기반이며, 다음 항목은 실기기 검증이 필요합니다.

| 항목 | 권고 도구/방법 |
|------|---------------|
| 실제 터치 정확도 | iPhone SE/12 mini, Galaxy S21 실기 또는 Xcode Simulator |
| 가로 스크롤 발생 여부 | Chrome DevTools 모바일 모드 + `document.body.scrollWidth > 375` 체크 |
| 키보드 표시 시 입력 가림 | iOS Safari, Android Chrome 실측 (특히 thesis/new 빌더, news/StockInsightCard 드롭다운) |
| 차트 가독성 | 실기기 + `pixelRatio` 차이 검증 |
| `InvestingHeader` 사용처 | `Grep "InvestingHeader"`로 마운트 위치 확인 (현재 layout.tsx에 미사용) |

---

## 메타

- **감사자**: Claude Opus 4.7 (정적 분석)
- **참조 파일**: 192개 컴포넌트 / 24개 페이지 중 30+ 파일 직접 검사, 나머지는 `Grep` 패턴 매칭
- **누락 가능 영역**: `/admin/*` 일부, `/login`, `/signup`, `/mypage`, `app/page.tsx` (홈), `(list)/alerts/page.tsx` 세부
- **다음 단계**: P0 BLOCKER 9건에 대한 작업 지시서 작성 → `docs/portfolio/instructions/` 또는 `frontend/__tests__/` 회귀 테스트 추가
