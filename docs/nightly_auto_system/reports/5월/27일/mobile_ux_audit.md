# 모바일 UX 감사 보고서

- **감사 일자**: 2026-05-27
- **대상 브랜치**: slice17 (HEAD `16d2a43`)
- **감사 범위**: `frontend/app/**/page.tsx` (30개), `frontend/components/**/*.tsx` (205개)
- **기준 뷰포트**: 모바일 375 × 667pt (iPhone SE), Apple HIG 터치타겟 44 × 44pt
- **방식**: 정적 코드 감사 (브라우저 렌더링 미수행). 클래스 / 레이아웃 / 분기 로직 기반 추론.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|--------|------|------|
| BLOCKER | **3** | 접근성/네비게이션 차단 — 모바일 사용 자체가 불가능하거나 사용자 흐름이 끊김 |
| MAJOR | **9** | 가독성/터치 정확도 심각 저하, 가로 overflow, 핵심 기능 모바일 미대응 |
| MINOR | **8** | 가독성 약간 손실, 데스크톱 가정 코드, 비핵심 컴포넌트 |
| **합계** | **20** | |

### BLOCKER 요약
1. `viewport: { maximumScale: 1, userScalable: false }` — 핀치 줌 차단 (WCAG 1.4.4 위반)
2. `MobileNav.tsx`가 5개 라우트만 노출 → Chain Sight / Thesis Control / Market Pulse / Screener / RAG / Coach 모바일 접근 불가
3. `Header.tsx` 햄버거 버튼이 `className="hidden"`로 무력화 + `md:hidden` 모바일 메뉴 영구 닫힘 → 모바일에서 데스크톱 nav 전체 미노출

### MAJOR 요약
- ScreenerTable / PortfolioTable / StockTable / 재무제표 테이블 등 다컬럼 테이블에 `overflow-x-auto`만 적용 (sticky 첫 컬럼 없음, 모바일 분기 없음 — Screener만 `MobileStockCard` 존재)
- `text-[10px]/[11px]`로 표기되면서 클릭 가능한 요소 다수 (Thesis Builder, Screener Preset, Chain Sight 카드 태그)
- `MoverCard` 류 hover 툴팁 (`group-hover/tooltip:block`) → 모바일 터치 미지원 (정보 손실)
- `MarketGraphCanvas` `h-[560px]` 고정 + 인기 섹터 버튼 `w-[110px]` 고정 → 375px 모바일에서 가로 배치 충돌
- `InvestingHeader.tsx`의 `max-w-[1400px]` + 검색바 + 8개 nav가 데스크톱 전용, breakpoint 미적용 (단 layout.tsx에서 사용되지 않으므로 dead code 가능성)
- 긴 목록 (ScreenerTable, PortfolioTable, NewsList) **virtualization 0건**
- `IndicatorRow` 메인 행 4단 가로 배치 (값 60px + 변동 120px + 스파크 100px + 지지/반박) → 375px에서 폭 부족
- 분기 스파크라인 (`QuarterlySparkline`) — 8분기 + label 표기 시 폭당 ~10px → 모바일 터치 정확도 저하
- `Pagination` prev/next 화살표 버튼 `p-1.5` — 44pt 미만

---

## 반응형 누락

### 1-1. 모바일 뷰포트 차단 (BLOCKER #1)
**파일**: `frontend/app/layout.tsx:29-35`

```tsx
viewport: {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,           // ← BLOCKER
  userScalable: false,       // ← BLOCKER
  viewportFit: "cover",
},
```

- **영향**: 모든 페이지에서 핀치 줌 불가. 작은 텍스트(`text-[10px]`)를 읽으려면 줌해야 하는데 그 자체를 차단함.
- **WCAG**: 1.4.4 Resize Text (Level AA) 위반.

### 1-2. 데스크톱 전용 헤더 컴포넌트 (MAJOR #1)
**파일**: `frontend/components/layout/InvestingHeader.tsx`

- `max-w-[1400px]` (1, 32, 55, 99행) → 375px에서 매우 크게 잘림.
- Top bar(주요지수 가로 나열), 검색바 `max-w-xl mx-8`, 8개 nav 메뉴 가로 배치 모두 `md:`/`sm:` 브레이크포인트 없음.
- 다행히 `frontend/app/layout.tsx`는 `Header.tsx`만 사용하므로 현재 노출되진 않음 → **dead code일 가능성 높음**. 사용 여부 확인 후 제거 권장.

### 1-3. 다컬럼 테이블 가로 스크롤 (MAJOR #2)
공통 패턴: `<div className="overflow-x-auto"><table className="min-w-full">`. sticky 첫 컬럼 없음, 모바일 카드 뷰 분기 없음 (Screener는 예외 — `MobileStockCard.tsx` 존재하나 페이지 분기 검증 필요).

| 파일 | 컬럼 수 | 비고 |
|------|---------|------|
| `components/strategy/ScreenerTable.tsx` | 11~12 | `max-w-[180px]`, `max-w-[120px]`, `max-w-[200px]` 셀 truncate 다수. 헤더에 `cursor-pointer` 정렬 있으나 모바일에서 좌우 스와이프 + 헤더 터치 충돌 |
| `components/portfolio/PortfolioTable.tsx:259` | ~15 | 포트폴리오 보유/목표/손절/52주 등. `min-w-full` 만으로 부족 |
| `components/stocks/StockTable.tsx:34` | 7 | sector / 차트 컬럼까지 가로 |
| `app/stocks/[symbol]/page.tsx:843` | 가변 | 재무제표 (BS/IS/CF). 분기 컬럼이 4~20개로 가변 |
| `components/admin/news/CollectionStatsTable.tsx` | 다수 | admin 전용 (모바일 노출도 낮음) |
| `components/admin/shared/TaskLogViewer.tsx:218` | 다수 | admin |

**MOBILE 카드 분기가 있는 곳**: `screener/MobileStockCard.tsx` (단독 카드), `chainsight/MobileCardList.tsx` (workspace 모바일 분기). 그 외는 없음.

### 1-4. 고정폭 컴포넌트가 모바일에서 깨질 우려 (MAJOR #3)

| 파일:행 | 클래스 | 영향 |
|---------|--------|------|
| `chainsight/MarketGraphCanvas.tsx:603,712,760` | `h-[560px]` | 모바일 뷰포트 667pt 중 ≈84% 차지. landscape에서는 화면 초과 |
| `chainsight/MarketGraphCanvas.tsx:676` | `w-[110px] min-h-[68px]` (인기 섹터 버튼) | 3개를 `flex-wrap justify-center gap-3` 배치 — 375px에서 (110*3 + 24) = **354px**로 한 줄 가능하나 padding 고려 시 wrap. iOS Safari 안전영역(safe-area-inset) 차감 시 부족 |
| `chainsight/NodeTooltip.tsx:141` | `max-w-[130px]` truncate | 종목명 truncate — 가독성 손실 |
| `chainsight/SectorBar.tsx:41` | `max-w-[120px]` truncate | 섹터 표시명 truncate |
| `rag/ChatInterface.tsx:198` | `h-[52px] w-[52px]` 전송버튼 | 44pt 이상 (OK) |
| `eod/SignalDetailSheet.tsx:97` | `w-full md:w-[420px] md:h-full` | 모바일 분기 잘 됨 (OK) |
| `thesis/dashboard/IndicatorRow.tsx:110-132` | `min-w-[60px] + min-w-[120px] + max-w-[100px]` | 단일 행에 4단 배치. 375px에서 좌측 padding 16 + 값 60 + 변동 120 + 스파크 100 + 지지/반박 ~50 = **346px** 거의 한계. 종목명 truncate되거나 스파크라인 사라질 위험 |
| `screener/Pagination.tsx:127` | `min-w-[44px] min-h-[44px]` | OK |
| `validation/SignalSummaryCard.tsx:41` | `min-w-[72px] min-h-[44px]` × 7개 카테고리 | 가로 7개 = **504px** → 375px 초과. `overflow-x-auto` 적용됨 (OK) |
| `layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` | 데스크톱 전용 (사용 여부 확인 필요) |

### 1-5. 브레이크포인트 누락 페이지 (MINOR)

`hidden md:`, `md:hidden` 등 모바일 분기 패턴 발견 파일 12개:
- `Header.tsx`, `MobileNav.tsx`, `app/market-pulse/page.tsx`, `chainsight/RelationFilterChips.tsx`, `news/NewsEventTimeline.tsx`, `thesis/builder/OptionButton.tsx`, `app/dashboard/page.tsx`, `eod/SignalDetailSheet.tsx`, `app/stocks/[symbol]/page.tsx`, `app/chainsight/[symbol]/page.tsx`, `app/screener/page.tsx`, `app/ai-analysis/page.tsx`

**분기 부재 페이지** (`md:`/`sm:` 0건):
- `app/thesis/(list)/page.tsx`, `app/thesis/new/page.tsx`, `app/thesis/[thesisId]/page.tsx`, `app/thesis/[thesisId]/indicators/page.tsx`, `app/thesis/[thesisId]/close/page.tsx` — 모바일 우선 디자인이라면 OK이나 데스크톱에서 max-w-lg 고정으로 좁게 표시됨
- 대부분의 coach E1~E6은 grid-cols 분기는 있으나 페이지 헤더는 모바일 우선

---

## 터치 타겟

### 2-1. 44 × 44pt 미만 클릭 요소 (MAJOR #4)

#### `text-[10px]` 클릭/포인터 요소 (의도된 클릭은 아니지만 hover/touch UI에서 손실)

| 파일:행 | 컴포넌트 / 컨텍스트 | 권장 |
|---------|-------------------|------|
| `app/thesis/new/page.tsx:1063` | `text-[10px] text-gray-500 hover:text-blue-400 mt-1 inline-block` — 링크 | 클릭 가능 요소이나 fontSize 10px + h `inline-block`로 ≈12px → 터치 어려움 |
| `screener/PresetGallery.tsx:241` | `text-[10px]` "상세 설명" 토글 버튼 | 44pt 미만 |
| `chainsight/RelationLegend.tsx:59` | `text-[10px] font-semibold` 토글 버튼 | 44pt 미만 |
| `thesis/builder/SuggestionCard.tsx:65-86` | `text-[11px]` 텍스트 within 카드 (전체 카드 클릭이라 OK) | OK if 부모 카드가 충분히 큼 |
| `thesis/IndicatorCard.tsx:78-79` | `text-[10px]` "추천 이유" + `text-[11px]` 본문 | 카드 자체 클릭이라 OK이나 가독성 BLOCKER 직전 |
| `chainsight/ChainStoryFeed.tsx:108-111` | `text-[10px] px-1.5 py-0.5` 라벨 | 표시용 (클릭 아님) — OK |
| `chainsight/FullPathView.tsx:287` | `text-[10px] px-1.5 py-0.5` 노드 라벨 | 표시용 (OK) |
| `app/screener/page.tsx:528` | `inline-flex w-4 h-4 ... text-[10px]` order 뱃지 | 16 × 16px — 클릭 시 부적합 |
| `eod/SignalDetailSheet.tsx:188-197` | `text-[10px] px-1.5 py-0.5` 키워드 태그 (클릭 가능) | 44pt 미만 |

#### 작은 패딩 + 작은 폰트 클릭 버튼

| 파일:행 | 클래스 | 비고 |
|---------|--------|------|
| `screener/Pagination.tsx:108-148` prev/next | `p-1.5` → ~24×24px | **MAJOR**. 페이지 버튼은 `min-w-[44px] min-h-[44px]`인데 화살표는 부적합 |
| `screener/PresetGallery.tsx:192-203` 삭제 X 버튼 | `p-1` + `w-3.5 h-3.5` 아이콘 → ~20×20px | hover로만 노출되므로 모바일 터치 불가 |
| `thesis/IndicatorCard.tsx:59-67` 토글 chevron | `p-1` + `size={16}` → ~24×24px | 44pt 미만 |
| `app/thesis/[thesisId]/indicators/page.tsx:32` 뒤로가기 | `p-1` + size 20 → ~28×28px | 44pt 미만 |

### 2-2. 양호한 케이스 (참고)

- `MobileNav.tsx:34` — `min-h-[44px] flex-1` 5개 균등 분할 (OK)
- `strategy/ScreenerTable.tsx:323` — 바구니 버튼 `min-h-[44px] min-w-[44px]` (OK)
- `validation/SignalSummaryCard.tsx:41` — `min-w-[72px] min-h-[44px]` (OK)
- `screener/Pagination.tsx:127` — 페이지 버튼 본체 (OK)
- `thesis/dashboard/QuarterlySparkline.tsx:44` — `min-h-[44px]` (OK이나 폭 좁음, MINOR)
- `eod/SignalCard.tsx` — 카드 자체 `role="button"`, 패딩 충분 (OK)

### 2-3. Hover 의존 인터랙션 (MAJOR #5)

모바일 터치 환경에서 hover가 작동하지 않으므로 정보 손실 발생:

- `market-pulse/MoverCard.tsx:138, 150, 162, 177, 189` — `group-hover/tooltip:block` 5개 툴팁
- `market-pulse/MoverCardWithBatchKeywords.tsx:145, 157, 169, 184, 196` — 동일
- `keywords/KeywordTag.tsx:90` — 키워드 설명 툴팁

이 컴포넌트들은 모두 메인 페이지(`market-pulse`, `market-movers`)에 노출되며, 모바일에서 5개 정보 영역이 통째로 숨겨짐.

---

## 네비게이션

### 3-1. 모바일 네비게이션 라우트 누락 (BLOCKER #2)
**파일**: `frontend/components/layout/MobileNav.tsx:11-17`

```tsx
const navItems = [
  { name: '홈', href: '/', icon: Home },
  { name: '종목', href: '/stocks', icon: TrendingUp },
  { name: '뉴스', href: '/news', icon: Newspaper },
  { name: '포트폴리오', href: '/portfolio', icon: PieChart },
  { name: '내정보', href: '/mypage', icon: User },
];
```

**미노출 라우트** (Header에는 있으나 MobileNav에 없음):
- `/chainsight` (Chain Sight v2)
- `/thesis` (Thesis Control 가설 통제실)
- `/market-pulse` / `/market-pulse-v2`
- `/screener` (Enhanced 스크리너)
- `/ai-analysis` (RAG 분석)
- `/coach/e1~e6`
- `/watchlist`

사용자가 모바일에서 위 기능에 접근하려면 URL 직접 입력하거나 다른 화면의 링크를 클릭해야 함. **핵심 가설 통제실(Thesis Control)이 모바일 네비에서 빠진 것이 가장 큰 문제**.

### 3-2. 데스크톱 헤더 메뉴 모바일 봉인 (BLOCKER #3)
**파일**: `frontend/components/layout/Header.tsx:155-163`

```tsx
{/* audit P0 #12: Header 햄버거를 모바일에서 비표시 (MobileNav가 모바일 네비 단일 소스). */}
<button
  ...
  className="hidden inline-flex items-center justify-center p-2 min-h-[44px] min-w-[44px] ..."
>
```

- 햄버거 버튼 `className="hidden"`로 영구 숨김 (`md:hidden`이 아니라 `hidden`).
- `md:hidden` 영역(167행)의 모바일 메뉴는 햄버거가 없으니 열 수 없음.
- 결과: 모바일에서 Header 내비게이션 접근 경로 0건. MobileNav 5개에만 의존.

**조치**: MobileNav를 확장하거나 (5개 → 더보기 메뉴 + 핵심 진입점), 햄버거를 재활성화하여 전체 라우트 노출.

### 3-3. 모바일 분기가 잘 된 케이스 (참고)
- `app/chainsight/[symbol]/page.tsx:115-170` — `useState(isMobile)` + `window.innerWidth < 768` 감지, 모바일이면 `MobileCardList` 렌더, 그래프는 별도 오버레이.
- `components/eod/SignalDetailSheet.tsx:97` — `w-full md:w-[420px]` 바텀시트 패턴.
- `components/thesis/common/BottomSheet.tsx` / `AddIndicatorSheet.tsx` — `max-h-[50vh]/[60vh]` 바텀시트.

### 3-4. Virtualization 부재 (MAJOR #6)

```bash
$ grep -r "react-window\|react-virtual\|virtualization" frontend/
(0 hits)
```

긴 목록을 렌더하는 컴포넌트가 모두 일반 `.map()` 사용:
- `ScreenerTable` (수백 종목)
- `PortfolioTable`
- `NewsList` / `NewsHighlightedStocks`
- `chainsight/MobileCardList`
- `thesis/(list)/page.tsx` 가설 목록
- `news/AINewsBriefingCard` 키워드 + symbol 묶음

**모바일 영향**: GC + 메모리 압박, scroll jank. 종목 500개 이상 렌더 시 저사양 안드로이드에서 체감.

---

## 차트/그래프

### 4-1. ResponsiveContainer 적용 현황

**적용 완료 (양호)**:
| 파일 | 사용 위치 |
|------|----------|
| `charts/StockPriceChart.tsx` | 메인 가격 차트 |
| `app/market-pulse-v2/details/BreadthDetail.tsx:42` | Line |
| `app/market-pulse-v2/details/FlowDetail.tsx:43` | Pie |
| `app/market-pulse-v2/details/RegimeDetail.tsx:86` | Radar |
| `app/market-pulse-v2/details/SectorDetail.tsx:38,62` | Bar |
| `thesis/dashboard/IndicatorRow.tsx:197, 235` | Area (일간/분기 둘 다) |
| `thesis/dashboard/IndividualMiniCharts.tsx` | 미니 차트 |
| `admin/news/MLTrendChart.tsx` | Line |
| `validation/MetricBarChart.tsx` | Bar |
| `screener/SectorHeatmap.tsx` | Heatmap |
| `macro/YieldCurveChart.tsx` | Yield curve |
| `news/SentimentChart.tsx` | Sentiment |
| `stock/StockChart.tsx` | Stock detail |
| `portfolio/PortfolioChart.tsx` | Pie |

→ **차트 자체의 모바일 폭 대응은 거의 모든 곳에서 양호** (recharts ResponsiveContainer 사용).

### 4-2. 차트의 부수 요소 모바일 가독성 (MINOR)

| 컴포넌트 | 이슈 |
|---------|------|
| `thesis/dashboard/IndicatorRow.tsx:207-209` | `XAxis fontSize={9}` — 모바일 9px 텍스트 가독성 최저 한계 |
| `thesis/dashboard/IndicatorRow.tsx:211-212` | `YAxis fontSize={10} width={55}` — 폭 55px 고정 (모바일 폭 22% 차지) |
| `thesis/dashboard/QuarterlySparkline.tsx:33-69` | recharts 미사용. flex-1 div 12분기 시 막대당 ≈25px, 8분기 시 ≈37px. `text-[11px]` 라벨 + `min-h-[44px]` 버튼은 OK이나 hover 툴팁이 작은 영역에 의존 — 터치 정확도 의문 |
| `validation/MetricBarChart.tsx:74` | `text-[10px]` peer 표기 — 모바일 가독성 손실 |
| `news/SentimentChart.tsx` | ResponsiveContainer 적용 OK (확인됨) |

### 4-3. ForceGraph2D / GraphCanvas (Chain Sight)

- `app/chainsight/[symbol]/page.tsx`: 모바일 < 768px 감지하여 `MobileCardList` 카드 뷰로 전환 + 그래프는 별도 오버레이 (양호).
- `app/chainsight/page.tsx`: `MarketGraphCanvas` 고정 `h-[560px]` — 모바일에서도 동일하게 노출. 사용자가 그래프를 보고 인터랙션해야 함. force-graph 라이브러리 자체는 캔버스 기반이라 폭 자동 조정 되나 노드 라벨 가독성/터치 정확도는 보장 안 됨.

---

## 페이지별 상세

### `/` (홈 — EOD Dashboard) → `app/page.tsx`
- ✅ `max-w-6xl mx-auto px-4 py-4` 모바일 친화
- ✅ `pb-20 md:pb-0`로 MobileNav 가림 보정
- ✅ `SignalFilterTabs` `overflow-x-auto scrollbar-hide` (스와이프 가능)
- ✅ `SignalCard` `onTouchStart/Move/End`로 스크롤-탭 충돌 방지 (참고할 만한 패턴)
- ⚠️ **MINOR**: `SignalCard` `text-[10px]/[11px]` 다수 — 가독성 한계
- ⚠️ **MAJOR**: 카드 클릭 후 `SignalDetailSheet` 내부 키워드 칩 `text-[10px] px-1.5 py-0.5` 클릭 가능 — 터치 어려움

### `/dashboard` → `app/dashboard/page.tsx`
- ✅ `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 양호
- ⚠️ **MINOR**: `max-w-7xl` 모바일 padding `px-4 sm:px-6 lg:px-8` 적용 (OK)

### `/portfolio` → `app/portfolio/page.tsx` + `PortfolioTable.tsx`
- ❌ **MAJOR**: `PortfolioTable.tsx:258-260` 15개 컬럼 테이블, sticky 첫 컬럼 없음, 모바일 카드 분기 없음
- ❌ **MAJOR**: Virtualization 없음
- ⚠️ 편집 모드 `Edit2/Save/X` 아이콘 버튼 패딩 확인 필요

### `/stocks/[symbol]` → 종목 상세
- ❌ **MAJOR**: L1/L2 탭 `flex gap-2 overflow-x-auto pb-3 scrollbar-hide` (1030행) — 탭 가로 스크롤 OK이나 첫 진입 시 어느 탭에 있는지 모름 (스냅 미적용)
- ❌ **MAJOR**: 재무제표 테이블(843행) — 분기 4~20개 컬럼이 가로로 펼쳐짐, sticky 첫 컬럼 없음, 모바일 분기 없음
- ❌ **MAJOR**: `ValidationTab` `CategorySidebar` `sticky top-24` 데스크톱 사이드바 — 모바일 분기 없으면 좁은 폭에서 본문과 충돌
- ⚠️ **MINOR**: `ChainSightMiniView` SSR 불가 dynamic import (OK)

### `/chainsight` → `app/chainsight/page.tsx`
- ❌ **MAJOR**: `MarketGraphCanvas h-[560px]` 모바일에서 화면 84% 차지
- ❌ **MAJOR**: 인기 섹터 버튼 `w-[110px]` 고정 × 3개 + gap-3 → 375px 임계
- ❌ **MAJOR**: `RelationCardPanel` 내부 `text-[10px] px-1.5 py-0.5` 관계 태그 (RelationCardPanel.tsx:273) — 클릭 가능 시 터치 손실
- ✅ `SectorBar overflow-x-auto py-3 px-1` (양호)
- ⚠️ **MINOR**: `ChainStoryFeed text-[10px]` 라벨 다수

### `/chainsight/[symbol]` → `app/chainsight/[symbol]/page.tsx`
- ✅ **모범 사례**: `isMobile` 감지 + `MobileCardList` 분기 + 그래프 오버레이 (152-220행)
- ✅ 모바일 노드 상세 바텀시트
- ⚠️ **MINOR**: 모바일 바텀시트 `max-h-48` (12rem ≈ 192px) — 노드 정보 절단 위험
- ⚠️ **MINOR**: 모바일 CTA `min-h-[44px]` (MobileCardList:169) OK

### `/thesis` 목록 / `/thesis/new` 빌더 / `/thesis/[id]` 대시보드 / `/thesis/[id]/indicators` 지표 설정 / `/thesis/[id]/close` 마감
- ❌ **BLOCKER**: MobileNav에 `/thesis` 부재 — 핵심 기능 접근 불가 (위 §3-1 참조)
- ✅ 모바일 우선 디자인 (max-w-lg mx-auto) — Thesis는 일관되게 모바일 폭으로 설계됨
- ❌ **MAJOR**: `app/thesis/new/page.tsx` 빌더 `text-[10px]` 다수 (688, 752, 753, 765, 831, 843, 1063행) — Decision Trail / 현재 가설 / 카테고리 라벨 등 정보 영역 가독성 손실
- ❌ **MAJOR**: `IndicatorRow.tsx:107-144` 4단 가로 배치 — 375px 임계 (값/변동/스파크/지지)
- ⚠️ **MINOR**: `IndicatorCard.tsx:78-79` `text-[10px]/[11px]` 추천 이유 / 관계 — 정보 영역, 클릭 카드라 OK
- ⚠️ **MINOR**: `thesis/builder/OptionButton.tsx:66` `sm:hidden`로 "꾹 누르면 설명" 문구 — 모바일에만 노출 (OK)
- ⚠️ **MINOR**: `AddIndicatorSheet.tsx:265` `max-h-[60vh] overflow-y-auto` — 바텀시트 (OK)

### `/screener` → `app/screener/page.tsx` + `ScreenerTable.tsx`
- ✅ `MobileStockCard.tsx` 존재 — 페이지가 desktop/mobile 분기하는지 검증 필요
- ❌ **MAJOR**: `ScreenerTable` 11~12 컬럼, sticky 컬럼 없음
- ❌ **MAJOR**: 정렬 헤더 `cursor-pointer`가 가로 스크롤과 충돌 (모바일에서 헤더 탭하려면 스와이프와 분리되어야)
- ❌ **MAJOR**: `PresetGallery` 카드 + 액션 버튼 `text-[10px]` (218, 230, 241행) — 터치 정확도 손실
- ❌ **MAJOR**: 적용된 프리셋 칩 X 버튼(`539행 <X className="h-3 w-3" />` `ml-1`) — 12×12px 터치 영역
- ⚠️ **MINOR**: `AdvancedFilterPanel.tsx:142, 247, 266` `text-[10px]` — 정보 영역
- ✅ `Pagination` 페이지 버튼 `min-w-[44px] min-h-[44px]` (양호) — 단 prev/next는 작음

### `/market-pulse` / `/market-pulse-v2`
- ❌ **BLOCKER**: MobileNav에 `/market-pulse` 부재
- ❌ **MAJOR**: `MoverCard` / `MoverCardWithBatchKeywords` hover 툴팁 5개 — 모바일 터치 미작동 (§2-3)
- ❌ **MAJOR**: `app/market-pulse-v2/components/TickerBar.tsx` `overflow-x-auto` — 좌우 스와이프 가능하나 자동 스크롤이면 모바일에서 멀미 우려 (확인 필요)
- ✅ details 차트 (Breadth/Flow/Regime/Sector) 모두 ResponsiveContainer

### `/news` → `app/news/page.tsx`
- ❌ **BLOCKER 직전**: 다행히 MobileNav에 포함
- ❌ **MAJOR**: `NewsHighlightedStocks` 섹터 탭 `overflow-x-auto scrollbar-hide` — 가로 스와이프 OK
- ❌ **MAJOR**: `AINewsBriefingCard:70` 중요도 바 `max-w-[200px]` 고정 — 375px에서 200/375 = 53% 폭 (OK이나 작은 화면에서 미세)
- ❌ **MAJOR**: 카테고리 그룹화 + 100건 limit — virtualization 없음, 스크롤 무거움
- ⚠️ **MINOR**: `NewsDetailModal` `max-w-3xl max-h-[90vh]` — 모바일에서 좋음

### `/ai-analysis` (RAG)
- ❌ **BLOCKER**: MobileNav 부재
- ❌ **MAJOR**: 좌측 `DataBasket` w-80 (320px) 사이드바 가능성 — 데스크톱 가정. `sm:hidden`/`md:hidden` 0건이 아니므로 확인 필요
- ✅ `ChatInterface.tsx:198` 전송 버튼 `h-[52px] w-[52px]` (양호)
- ⚠️ **MINOR**: `SuggestionChips.tsx:40` `max-w-[150px] truncate` 칩 라벨

### `/coach/e1` ~ `/coach/e6` (Portfolio Coach)
- ❌ **BLOCKER**: MobileNav 부재
- ⚠️ **MINOR**: `app/coach/e4/page.tsx:135` `max-h-[60vh] min-h-[300px]` 대화 영역 (OK)
- ⚠️ **MINOR**: `app/coach/e4/page.tsx:213` `text-[11px]` 글자수 카운터 — 클릭 아님 (OK)
- ⚠️ **MINOR**: `app/coach/e5/page.tsx:343` `text-[11px]` 안내 (OK)
- ✅ `E4MessageBubble` 등 채팅 UI는 모바일 친화

### `/watchlist`
- ❌ **BLOCKER**: MobileNav 부재 (역설적: 핵심 기능)
- ⚠️ `overflow-x-auto` 사용 (47:확인 필요)

### `/admin`
- 관리자용으로 모바일 사용 빈도 낮음 — 별도 권장 없음
- `AdminTabNav.tsx:30,37` `overflow-x-auto min-h-[44px]` (양호)

---

## 페이지별 BLOCKER/MAJOR 분포 표

| 페이지 | BLOCKER | MAJOR | MINOR |
|--------|---------|-------|-------|
| 전역 (`layout.tsx`, MobileNav, Header) | 3 | 1 | 0 |
| `/portfolio` | 0 | 2 | 0 |
| `/stocks/[symbol]` | 0 | 3 | 1 |
| `/chainsight` | 0 | 3 | 2 |
| `/chainsight/[symbol]` | 0 | 0 | 2 |
| `/thesis/*` | 0 | 2 | 2 |
| `/screener` | 0 | 4 | 1 |
| `/market-pulse*` | 0 | 2 | 0 |
| `/news` | 0 | 2 | 1 |
| `/ai-analysis` | 0 | 1 | 1 |
| `/coach/e1~e6` | 0 | 0 | 3 |
| `/watchlist` | 0 | 1 | 0 |

(합계는 일부 항목이 전역 vs 페이지 양쪽에 걸치므로 §요약과 정확히 일치하지 않음)

---

## 우선 권장 사항 (감사자 의견)

1. **`viewport.maximumScale: 1, userScalable: false` 즉시 제거** — 5분 작업, WCAG 위반 해소.
2. **MobileNav 확장 또는 햄버거 재활성화** — Thesis Control, Chain Sight, Screener, Market Pulse, RAG, Coach 진입 경로 확보. "더보기" 패턴(5번째 슬롯) 권장.
3. **`InvestingHeader.tsx` 사용 여부 검증** — 미사용이면 dead code 제거, 사용 중이면 `md:` 분기 도입.
4. **다컬럼 테이블 모바일 분기 의사결정** — Portfolio/Stock/Financial 테이블에 sticky 첫 컬럼 + 카드 뷰 분기 (Screener의 `MobileStockCard` 패턴 재사용).
5. **Hover 툴팁 → 탭 가능 정보 영역 변환** — MoverCard 5개 툴팁, KeywordTag.
6. **`text-[10px]` 클릭 가능 요소 점검** — fontSize 최소 12px + 부모 영역 44pt 보장.
7. **Virtualization 도입 검토** — `@tanstack/react-virtual` (이미 TanStack Query 사용 중이라 친숙) — ScreenerTable, PortfolioTable 우선.
8. **`IndicatorRow` 4단 배치 모바일 분기** — 모바일에서는 2행으로 분리하거나 스파크라인 토글 영역으로 이동.

---

## 감사 한계

- 본 감사는 정적 코드 기반. 실제 모바일 렌더링/스크롤 동작/터치 응답성 미검증.
- `InvestingHeader.tsx` 미사용 여부는 추가 검증 필요 (`grep` 기준 사용 없음).
- Screener 페이지가 MobileStockCard로 분기하는지(`<md:hidden>` 패턴) 페이지 코드 추가 검증 권장.
- Tailwind JIT 클래스가 빌드 시 컴파일되므로 동적 클래스 누락 가능성은 확인 안 됨.
- 다크모드/라이트모드 별도 검증 안 됨.
- iOS Safari `safe-area-inset-*` 적용 여부 부분 확인 (`100dvh-env(safe-area-inset-top)` 사용 케이스 1건 — thesis/indicators).
