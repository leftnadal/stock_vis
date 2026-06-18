# 모바일 UX 감사 보고서

> **대상**: `/Users/byeongjinjeong/Desktop/stock_vis/frontend` (Next.js 16 / React 19 / Tailwind)
> **기준 뷰포트**: 375px (iPhone SE/mini 폭), 터치 타겟 기준 Apple HIG 44×44pt
> **방식**: 읽기 전용 정적 코드 감사 (코드 수정 없음). 컴포넌트 210개 + 페이지 33개 스캔, 고정 폭/소형 텍스트/브레이크포인트/`ResponsiveContainer`/`overflow-x` 패턴 전수 + 도메인별 정밀 분석.
> **감사일**: 2026-06-18

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 정의 |
|--------|------|------|
| **BLOCKER** | **2** | 375px에서 핵심 기능의 주 인터랙션이 실질적으로 불가능 |
| **MAJOR** | **9건군** | 터치 타겟 44px 미만, 콘텐츠 가림, 데스크톱 전용 레이아웃, 비반응형 고정 차트 |
| **MINOR** | **6건군** | 소형 텍스트 가독성, 가상화 미적용(성능), 고정 세로 비율 |

> ⚠️ **에이전트 자동 분류 보정 주석**: 1차 수집 단계에서 "BLOCKER"로 보고된 항목 중 다수(`grid-cols-2` 타이트 그리드, hover 전용 `w-48` 툴팁)는 **실제로 콘텐츠를 잘라내 사용 불가로 만들지 않으므로 MAJOR/MINOR로 강등**했다. 모든 테이블이 `overflow-x-auto`를 갖추고 있어 "테이블 가로 잘림" 유형의 BLOCKER는 **0건**이다. 진짜 BLOCKER는 아래 2건으로 한정한다.

### 가장 광범위하고 실효적인 이슈 (최우선)
1. **하단 고정 네비게이션 콘텐츠 가림** — 루트 레이아웃의 `<main>`에 하단 패딩이 없어, 고정 `MobileNav`(64px)가 거의 모든 페이지의 마지막 콘텐츠를 덮는다. (전역, MAJOR)
2. **market-graph 강제 그래프의 모바일 미대응** — 카드 fallback 없이 force-graph 캔버스를 그대로 노출, 노드 반경 8~10px. (BLOCKER)
3. **줌 차단** — viewport 메타에 `userScalable: false` + `maximumScale: 1`. 저시력 사용자 확대 불가. (접근성, MAJOR)

### 긍정적 모범 사례 (참고)
- `components/stock/StockChart.tsx` — `getResponsiveChartHeight()`로 모바일/태블릿/데스크톱 차트 높이 분기 (**모범**).
- `components/eod/SignalDetailSheet.tsx` — `w-full` + `rounded-t-2xl` + 드래그 핸들 + `max-h-[90vh]` + `animate-slide-up`, 모바일 바텀시트 정석.
- 모든 데이터 테이블(`StockTable`, `PortfolioTable`, 재무제표, `Watchlist`, `ScreenerTable`)에 `overflow-x-auto` 적용.
- `components/layout/MobileNav.tsx` — `min-h-[44px]` + `aria-label`로 터치 타겟/접근성 준수.
- `app/page.tsx`(홈)만 유일하게 `pb-20 md:pb-0`로 하단 네비 회피 처리.
- 반응형 그리드 적절: `MetricCard`(`grid-cols-2 sm:grid-cols-4`), `AdvancedFilterPanel`, `PresetGallery`, `RelationCardPanel`(`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`).

---

## 1. 반응형 누락

### 1-1. 고정 폭 / 비반응형 고정 차트 (375px overflow·과점유)

| 파일 | 위치 | 패턴 | 분석 | 심각도 |
|------|------|------|------|--------|
| `components/macro/FearGreedGauge.tsx` | L54 | `w-48 h-24` (SVG, `ResponsiveContainer` 없음) | 192px = 375px의 51% 고정 점유, 좁은 컨테이너에서 overflow 위험 | MAJOR |
| `components/portfolio/PortfolioChart.tsx` | L77, L97 | `<ResponsiveContainer height={400}>` | 폭은 반응형이나 높이 400px 하드코딩 → 모바일 1화면 대부분 차지 | MAJOR |
| `components/charts/StockPriceChart.tsx` | L40, L272 | `height` 기본값 400, 반응형 분기 없음 | 부모가 높이를 주지 않으면 모바일에서 과도 | MINOR |
| `components/thesis/dashboard/IndicatorRow.tsx` | L115, L132 | `min-w-[120px]` + 스파크라인 `max-w-[100px]` | 343px 가용폭에서 변화율 영역이 35% 점유, 스파크라인 압착 | MAJOR |
| `components/macro/YieldCurveChart.tsx` | L92 | `h-64`(256px) 고정 세로 | 폭은 `ResponsiveContainer` O, 세로 비율만 비최적 | MINOR |
| `components/admin/news/MLTrendChart.tsx` | L89 | `h-[200px]` 고정 세로 | 관리자 전용, 폭 반응형 O | MINOR |
| `components/market-pulse/MoverCard.tsx` | L138~189 | hover 툴팁 `w-48` ×5, 절대위치 `left-0` | 모바일에선 hover 미발생 → 정보 접근 불가(터치 이슈), 잠재 가로 overflow | MAJOR |
| `components/keywords/KeywordTag.tsx` | L90 | hover 툴팁 `w-48`, `left-1/2 -translate-x-1/2` | 375px에서 중앙정렬 시 좌측 음수 오프셋 → overflow 가능 | MINOR |

### 1-2. 브레이크포인트 없는 데스크톱 전용 / 타이트 그리드

| 파일 | 위치 | 패턴 | 분석 | 심각도 |
|------|------|------|------|--------|
| `components/thesis/AddIndicatorSheet.tsx` | L292 | `grid grid-cols-2`(전체 카탈로그, 60+ 항목) | 같은 파일 L274는 `grid-cols-1 sm:grid-cols-2`로 올바름 → 일관성 결여. 375px에서 칸당 ~170px, 텍스트 줄바꿈 | MAJOR |
| `components/thesis/skeleton/ThesisSkeleton.tsx` | L68 | `grid grid-cols-3` | 375px에서 칸당 ~113px, 실제 대시보드 그리드도 동일 위험 시사 | MAJOR |
| `components/news/InterestSelector.tsx` | L74 | `grid grid-cols-2 sm:grid-cols-4` | 모바일 2열 = 칸당 ~183px, 한글 테마명("AI & Data Mining") truncate 필요 | MAJOR |

> 그 외 `grid-cols-1 md:/lg:` 패턴은 모바일에서 1열로 정상 축소되어 **문제 없음**(MarketMoversSection, NewsGrid, ScreenerDashboard, RelationCardPanel 등).

### 1-3. 테이블 가로 스크롤 처리

**전부 `overflow-x-auto` 적용 — 양호.** 컬럼 다수여도 모바일에서 가로 스크롤로 접근 가능.

| 파일 | 위치 | 비고 |
|------|------|------|
| `components/stocks/StockTable.tsx` | L34 | O |
| `components/portfolio/PortfolioTable.tsx` | L259 (`min-w-full`) | O, 12컬럼 |
| `app/stocks/[symbol]/page.tsx` 재무제표 | L843 | O |
| `app/watchlist/page.tsx` | L294 | O, 7컬럼 |
| `components/strategy/ScreenerTable.tsx` | L128 | O. 단 헤더/셀 `text-xs` 가독성 → MINOR |
| `components/chainsight/SectorBar.tsx`, `RelationFilterChips.tsx`, `ChainStoryFeed.tsx`, `SignalSummaryCard.tsx` | 각 | 칩/배지 바 `overflow-x-auto` O |

---

## 2. 터치 타겟 (44×44pt 미만)

### 2-1. 클릭 요소 터치 타겟 미달 (MAJOR)

| 파일 | 위치 | 요소 | 실측 추정 | 근거 |
|------|------|------|-----------|------|
| `components/thesis/dashboard/IndicatorRow.tsx` | L179~189 | 기간 선택 버튼(1M/1Y/3Y/5Y) | `px-2.5 py-0.5 text-[10px]` → 높이 ~20-22px | 자주 쓰는 기간 토글, 44px 한참 미달 |
| `components/thesis/indicators/IndicatorSetupCard.tsx` | L52, L63 | 활성 토글 / 삭제 버튼 | `p-2` + 16px 아이콘 → ~24-28px | 지표 활성·삭제는 파괴적 동작인데 과소 |
| `components/thesis/dashboard/DashboardPageHeader.tsx` | L21, L30 | 뒤로가기 / 새로고침 | `p-1` + 20px 아이콘 → ~28px | 핵심 내비 컨트롤 과소 |
| `components/chainsight/RelationFilterChips.tsx` | L150 | 관계 필터 칩 | `h-8`(32px) | 44px 미달 |
| `components/financial/FieldSettingsModal.tsx` | L186~204 | 빠른 선택 버튼 | `text-xs` + 좁은 패딩 → ~24px | 모달 내 다중 선택 버튼 과소 |
| `components/market-pulse/MoverCard.tsx` (외 NewsContextBadge 등) | L137~ | `Info` 아이콘 `w-3 h-3`(12px) | hover 전용 | **모바일에서 hover 미발생 → 터치로 정보 접근 자체 불가** |

### 2-2. 클릭 가능 태그/칩의 소형 텍스트

| 파일 | 위치 | 패턴 | 비고 |
|------|------|------|------|
| `components/keywords/KeywordTag.tsx` | L42 | 기본 `size='sm'` → `px-2 py-0.5 text-[10px]` | `MoverCard`/`DailyKeywordCard`에서 `onClick`으로 사용 → 클릭 요소인데 높이 ~20px |
| `components/eod/NewsContextBadge.tsx` | L67 | `text-[11px] px-2 py-1` | ~28-32px |
| `components/eod/SignalFilterTabs.tsx` | L68 | 카운트 배지 `min-w-[18px] h-[18px] text-[11px]` | 배지 자체는 비클릭이나 시각 구분 난해 |

> 도메인 지목 3종 점검 결과:
> - **thesis 관제실 지표 카드** → 기간 버튼/토글/삭제 다수 미달 (위 2-1). **개선 필요**.
> - **validation 프리셋 탭**(`PeerContextBar.tsx` L40, L54) → `min-h-[44px]` 적용됨. **양호**. (단 L90 경고문 `text-[10px]` = MINOR)
> - **chainsight 그래프 노드** → §4 / BLOCKER 참조 (canvas hit area r=8-10px).

### 2-3. 소형 비클릭 텍스트 가독성 (MINOR)

`text-[10px]`/`text-[11px]`가 클릭 불가 라벨에 광범위 사용(`IndicatorRow` L95/118/148, `RealValueIndicatorCard`, `RecommendCard` L30~36, `NotableChangesSection` L26, `AlertBell` L19, `MetricBarChart` L74, `RelationLegend` L59, `MobileStockCard` L166 등). 기능 차단은 아니나 모바일 가독성 저하 → `text-xs`(12px) 이상 권장.

---

## 3. 네비게이션

### 3-1. 구조 (양호)
- **루트 레이아웃**(`app/layout.tsx`): 데스크톱 상단 `Header` + 모바일 하단 고정 `MobileNav`(`md:hidden`). 이중 네비 충돌 방지를 위해 `Header`의 햄버거는 `hidden`으로 봉인됨(L157 주석). 모바일 네비 단일 소스 = `MobileNav`. **설계 양호.**
- `MobileNav`: 5탭(홈/종목/뉴스/포트폴리오/내정보), `min-h-[44px]` + `aria-label` 준수. 깨진 `/profile` → `/mypage` 교정 이력 확인.
- `InvestingHeader.tsx`는 루트 레이아웃에 **미마운트(레거시/미사용)** — 정적 더미 데이터("2025년 10월 25일") 포함. 감사 대상에서 제외하되 데드코드로 정리 권장.

### 3-2. 하단 네비 콘텐츠 가림 (MAJOR — 전역)
`app/layout.tsx`의 `<main className="min-h-screen">`에 하단 패딩이 없고, `MobileNav`는 `fixed bottom-0 ... h-16`(64px). → **콘텐츠 하단 64px가 네비에 덮인다.**

| 페이지 | 하단 패딩 | 상태 |
|--------|----------|------|
| `app/page.tsx` (홈) | `pb-20 md:pb-0` | ✅ 유일하게 처리됨 |
| `app/dashboard/page.tsx` | 없음 | ❌ 마지막 카드 가림 |
| `app/portfolio/page.tsx` | 없음 | ❌ 테이블/차트 하단 가림 |
| `app/watchlist/page.tsx` | 없음 | ❌ 테이블 하단 가림 |
| `app/mypage/page.tsx` | 없음 | ❌ 하단 섹션 가림 |
| `app/stocks/[symbol]/page.tsx` | 없음 | ❌ 하단 탭 콘텐츠 가림 |

→ **권장**: `layout.tsx`의 `<main>`에 `pb-16 md:pb-0` 일괄 적용(페이지별 중복 제거). 단일 지점 수정으로 전 페이지 해결.

### 3-3. 가상화(virtualization)
긴 목록 어디에도 `react-window`/`react-virtualized` 미적용:
- `components/market-pulse/MarketMoversSection.tsx` L177 (`.map`)
- `components/eod/SignalDetailSheet.tsx` L252 (스크롤 영역 `.map`)
- `components/news/NewsGrid.tsx` L98 ("더 보기" 페이징 방식)

→ 현재 데이터 규모에선 성능 영향 경미 → **MINOR**. 종목 수백 건 이상 확장 시 재검토.

---

## 4. 차트 / 그래프

### 4-1. `ResponsiveContainer` 사용 현황

| 파일 | `ResponsiveContainer` | 높이 처리 | 평가 |
|------|:--------------------:|-----------|------|
| `components/stock/StockChart.tsx` | O (L652, L748) | `getResponsiveChartHeight()` 분기 (모바일 280/70) | ✅ **모범** |
| `components/charts/StockPriceChart.tsx` | O (L272) | 고정 기본 400 | MINOR |
| `components/portfolio/PortfolioChart.tsx` | O (L77, L97) | 고정 400 하드코딩 | MAJOR |
| `components/news/SentimentChart.tsx` | O (L80) | `w-full h-80`, margin 고정 | MINOR (모바일 margin 과다) |
| `components/macro/YieldCurveChart.tsx` | O (L93) | `h-64` 고정 세로 | MINOR |
| `components/admin/news/MLTrendChart.tsx` | O (L90) | `h-[200px]` | MINOR (관리자) |
| `components/validation/MetricBarChart.tsx` | O | `h-48` | 양호 |
| `components/screener/SectorHeatmap.tsx` | O (Treemap) | — | 양호 |
| `components/macro/FearGreedGauge.tsx` | **X** (SVG) | `w-48 h-24` 고정 | MAJOR (§1-1) |
| `components/eod/MiniSparkline.tsx` | X (순수 SVG, viewBox) | 기본 80×24, `flex-shrink-0` | 양호 (소형) |

### 4-2. 분기 스파크라인 모바일 가독성
- `components/thesis/dashboard/QuarterlySparkline.tsx`: `ResponsiveContainer` 미사용, 컨테이너 `h-10`(40px)인데 내부 분기 막대 버튼은 `min-h-[44px]`(L44) → **컨테이너 높이 < 자식 최소높이 충돌**, 클리핑/오버플로 가능. (MAJOR)
- `components/eod/MiniSparkline.tsx`: 소형 인라인, 모바일 문제 없음.

### 4-3. 그래프 캔버스 (BLOCKER)
- `components/chainsight/MarketGraphCanvas.tsx`: react-force-graph-2d.
  - L603 컨테이너 `h-[560px]` 고정 → 375px 화면에서 세로 과점유(스크롤 강제).
  - L787~794 `nodePointerAreaPaint` hit area가 노드 반경 기반, 2차 이웃 노드 반경 8~10px → **터치 hit 영역 44px 한참 미달**.
  - L481~516에 모바일 탭(첫 탭=툴팁/더블탭=center) 처리는 있으나, **카드 fallback으로 전환하지 않고 캔버스를 그대로 노출**.
  - `MobileCardList.tsx`(터치 친화 카드 리스트)는 **`app/chainsight/[symbol]/page.tsx`에서만** 사용되고, `app/chainsight/market-graph/page.tsx`에선 미사용.
  - → **`market-graph` 페이지의 핵심 인터랙션(특정 노드 정밀 탭)이 모바일에서 실질 불가 = BLOCKER.** market-graph에도 `MobileCardList` 분기 도입 권장.

---

## 5. 페이지별 상세

### Thesis (`/thesis`)
- **관제실 대시보드**: 기간 버튼(`IndicatorRow` L179, `text-[10px] py-0.5`)·토글/삭제(`IndicatorSetupCard` L52/63 `p-2`)·헤더 아이콘(`DashboardPageHeader` `p-1`) 모두 터치 44px 미달 (MAJOR). `min-w-[120px]`+`max-w-[100px]` 스파크라인 압착 (MAJOR). `QuarterlySparkline` h-10/min-h-[44px] 충돌 (MAJOR).
- **지표 추가 시트**: `AddIndicatorSheet` 카탈로그 `grid-cols-2` 비반응형 (MAJOR), `text-[9px]` 빈도 배지 (MINOR).
- 다수 `text-[10px]/[11px]` 라벨 (MINOR).

### Chain Sight (`/chainsight`)
- **`/market-graph`**: force-graph 캔버스 노드 터치 (**BLOCKER**, §4-3).
- **`/[symbol]`**: `MobileCardList` 사용으로 카드 fallback O (**양호**). `RelationFilterChips` 칩 `h-8`(32px) (MAJOR). `RelationLegend`/`NodeTooltip` `max-w-[140px]/[130px]`는 적절.
- 관계 카드 그리드 반응형 양호.

### Screener (`/screener`)
- `ScreenerDashboard`/`AdvancedFilterPanel`/`PresetGallery` 반응형 그리드 양호. `ScreenerTable`·`MobileStockCard` 모바일 카드 + `overflow-x-auto` 양호.
- `MobileStockCard` 메트릭 라벨 `text-[10px]`(L166), `Pagination` 이전/다음 `p-1.5`(L97) (MINOR). 페이지 번호 버튼은 `min-w-[44px] min-h-[44px]` 준수.

### Validation
- 프리셋 탭(`PeerContextBar`) `min-h-[44px]` 준수 (**양호**). `MetricCard` `grid-cols-2 sm:grid-cols-4` 양호. 경고문/순위 라벨 `text-[10px]` (MINOR).

### Market Pulse (`/market-pulse`, `/market-pulse-v2`)
- `MoverCard`/`MoverCardWithBatchKeywords` hover 툴팁 `w-48` 5종 → 모바일 정보 접근 불가 + `Info` 아이콘 `w-3` 터치 불가 (MAJOR). 본문은 `flex-1 min-w-0`로 폭 유연(양호).
- `MarketNewsSection` 썸네일 `w-24 h-16` + 본문 = 타이트하나 수용 가능 (MINOR).
- v2 details/cards 스파크라인 다수 `text-[10px]/[11px]` (MINOR).

### EOD / 홈 (`/`, `/dashboard`)
- 홈(`app/page.tsx`): `pb-20 md:pb-0` 하단 네비 회피 (**모범**). `SignalDetailSheet` 바텀시트 모바일 대응 우수.
- `StockRow`·`ConfidenceBadge`·`NewsContextBadge` `text-[10px]/[11px]` (MINOR~MAJOR). `SignalFilterTabs` 배지 18px.
- `/dashboard`: 그리드 반응형이나 하단 패딩 없음 (MAJOR, §3-2).

### News (`/news`)
- `NewsGrid` `grid-cols-1 lg:grid-cols-2` 양호, 가상화 미적용(MINOR). `InterestSelector` `grid-cols-2` 한글 테마명 압착 (MAJOR). `SentimentChart` 반응형 O.

### Portfolio / Watchlist / MyPage
- 테이블 전부 `overflow-x-auto` 양호. `PortfolioChart` 고정 400px (MAJOR). **세 페이지 모두 하단 네비 패딩 없음** (MAJOR, §3-2).

### 인증 / AI 분석 (`/login`, `/signup`, `/ai-analysis`)
- 로그인/회원가입: `max-w-md w-full` + `w-full` 버튼 + sm 브레이크포인트 → **모바일 친화 양호**.
- AI 분석: `ChatInterface` 풀스크린 반응형, 헤더 버튼 `gap-2` 소형 (MINOR).

### 전역 (접근성)
- `app/layout.tsx` viewport: `maximumScale: 1, userScalable: false` → **핀치 줌 차단**. 저시력 사용자 확대 불가 (WCAG 1.4.4 위반 소지, MAJOR). `viewportFit: "cover"`는 노치 대응으로 적절하나 줌 차단은 분리 권장.

---

## 부록 — 권장 우선순위 (참고용, 본 감사는 수정 미수행)

1. **(MAJOR·전역, 1줄 수정)** `app/layout.tsx`의 `<main>` → `pb-16 md:pb-0`. 6개 페이지 콘텐츠 가림 일괄 해소.
2. **(BLOCKER)** `app/chainsight/market-graph/page.tsx`에 `(pointer: coarse)` 기준 `MobileCardList` 분기 도입 + 캔버스 높이 `max-h-[75vh]`.
3. **(MAJOR·접근성)** viewport에서 `userScalable: false` / `maximumScale: 1` 제거.
4. **(MAJOR)** thesis 관제실 터치 타겟 일괄 상향(`min-h-[44px]`): `IndicatorRow` 기간버튼, `IndicatorSetupCard` 토글/삭제, `DashboardPageHeader` 아이콘, `RelationFilterChips` 칩.
5. **(MAJOR)** hover 전용 툴팁(`MoverCard`/`KeywordTag` `w-48`)을 터치 가능 팝오버/탭으로 대체.
6. **(MAJOR)** `PortfolioChart`/`StockPriceChart` 높이를 `StockChart.getResponsiveChartHeight()` 패턴으로 통일, `FearGreedGauge` `max-w` 제한.
7. **(MAJOR)** 비반응형 그리드 교정: `AddIndicatorSheet` 카탈로그·`ThesisSkeleton`·`InterestSelector`.
8. **(MINOR)** `text-[10px]/[11px]` 라벨 `text-xs` 이상 상향, 장기적으로 긴 목록 가상화 검토, `InvestingHeader` 데드코드 정리.
