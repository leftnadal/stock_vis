# 모바일 UX 감사 보고서

**감사일**: 2026-05-09
**감사 범위**: `frontend/app/**`, `frontend/components/**`
**기준 뷰포트**: 375px (iPhone SE/12 mini 기준)

---

## 요약

| 심각도 | 이슈 수 | 주요 영역 |
|--------|---------|-----------|
| BLOCKER | 4 | InvestingHeader 모바일 미지원, market-pulse-v2 grid-cols-3 고정, thesis 뒤로가기 터치 타겟 3곳 |
| MAJOR | 12 | MobileNav 누락 항목, IndicatorRow 고정 min-w/소형 기간버튼, MarketBreadthCard/YieldCurveChart grid-cols-3 미적용, chainsight 고정 h-[400px], screener 테이블뷰 은닉, ThesisSkeleton grid-cols-3 |
| MINOR | 9 | text-[10px] 정보성 라벨 다수, 스파크라인 축 폰트, PortfolioChart Pie height 직접 지정, MonitoringDashboard/MLModelCard admin 그리드 |

---

## 1. 반응형 누락

### 1.1 고정 폭(px) 사용 — overflow 위험

| 심각도 | 파일경로:라인 | 클래스 | 모바일 영향 |
|--------|-------------|--------|------------|
| BLOCKER | `components/layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` + 내부 flex 수평 나열 | 모바일 대응 전무. 상단 티커 바·nav·검색바·우측 액션이 브레이크포인트 없이 수평 배치되어 375px에서 심각한 overflow 발생. 현재 어떤 page.tsx에서도 import되지 않아 즉시 영향은 없으나 향후 사용 시 BLOCKER |
| MAJOR | `components/thesis/dashboard/IndicatorRow.tsx:115` | `min-w-[120px]` (변동률+라벨 영역) | `min-w-[60px]`(값) + `min-w-[120px]`(변동률) + 스파크라인 `max-w-[100px]` 합산 ≥280px. 375px에서 오른쪽 지지/반박 텍스트가 잘릴 위험 |
| MAJOR | `components/thesis/dashboard/IndicatorRow.tsx:110` | `min-w-[60px]` | 위와 동일 행에서 복합 작용 |
| MINOR | `components/validation/SignalSummaryCard.tsx:40` | `min-w-[72px]` | `flex + overflow-x-auto` 래퍼로 스크롤 처리되어 실제 overflow 없음. 단 7개 카드의 `whitespace-nowrap` 라벨이 작게 표시될 수 있음 |
| MINOR | `components/common/DataSourceBadge.tsx:171` | `min-w-[200px]` | 절대위치 드롭다운 팝오버. 좁은 화면에서 뷰포트 우측 이탈 가능성 |
| MINOR | `components/eod/StockRow.tsx:66` | `min-w-[72px]` flex-shrink-0 | 우측 가격 영역. 좁은 화면에서 왼쪽 회사명 텍스트 압축 |

### 1.2 브레이크포인트 누락 — 데스크톱 전용 레이아웃

| 심각도 | 파일경로:라인 | 클래스 | 모바일 영향 |
|--------|-------------|--------|------------|
| BLOCKER | `app/market-pulse-v2/cards/FlowCardSummary.tsx:13` | `grid grid-cols-3` (sm:/md: 없음) | 375px에서 3열 고정, 각 열 ~117px. 숫자·라벨 판독 불편 |
| BLOCKER | `app/market-pulse-v2/details/FlowDetail.tsx:34` | `grid grid-cols-3` (sm:/md: 없음) | 동일 |
| BLOCKER | `app/market-pulse-v2/details/BreadthDetail.tsx:29` | `grid grid-cols-3` (sm:/md: 없음) | 동일 |
| MAJOR | `components/screener/MarketBreadthCard.tsx:107` | `grid grid-cols-3` (sm:/md: 없음) | 3열 고정. 내부 text-xs 수치가 375px에서 매우 좁아짐 |
| MAJOR | `components/macro/YieldCurveChart.tsx:147` | `grid grid-cols-3` (sm:/md: 없음) | Key Rates 요약(기준금리, 2년물, 10년물) 3열. text-lg 크기는 OK, 레이아웃 밀도 과다 |
| MAJOR | `components/rag/MonitoringDashboard.tsx:131` | `grid grid-cols-3` (sm:/md: 없음) | admin/monitoring 전용이지만 모바일 접근 시 overflow |
| MAJOR | `components/rag/MonitoringDashboard.tsx:261` | `grid grid-cols-3` (sm:/md: 없음) | 동일 |
| MAJOR | `components/admin/news/MLModelCard.tsx:110` | `grid grid-cols-3` (sm:/md: 없음) | admin 페이지 동일 |
| MAJOR | `components/thesis/skeleton/ThesisSkeleton.tsx:68` | `grid grid-cols-3` (sm:/md: 없음) | 관제실 로딩 스켈레톤. 375px에서 스켈레톤 카드 3개가 ~100px 폭으로 압축 |
| MINOR | `app/stocks/[symbol]/page.tsx:329` | `grid grid-cols-2` (sm:/md: 없음) | 2열이므로 375px에서도 각 열 ~167px. 내용상 수용 가능하나 명시적 브레이크포인트 권장 |
| MINOR | `app/market-pulse-v2/cards/BreadthCardSummary.tsx:14` | `grid grid-cols-2` (sm: 없음) | 2열로 큰 문제 없음 |

### 1.3 테이블 / 가로 스크롤 처리

| 심각도 | 파일경로:라인 | 처리 상태 | 판정 |
|--------|-------------|----------|------|
| OK | `components/stocks/StockTable.tsx:34` | `overflow-x-auto` 래퍼 있음 | 정상 |
| OK | `components/portfolio/PortfolioTable.tsx:259` | `overflow-x-auto` 래퍼 있음 | 정상 |
| OK | `components/strategy/ScreenerTable.tsx:128` | `overflow-x-auto` 래퍼 있음 | 정상 |
| OK | `components/validation/LeaderComparisonSection.tsx:47` | `overflow-x-auto` 래퍼 있음 | 정상 |
| MAJOR | `app/stocks/[symbol]/page.tsx:843` | `overflow-x-auto` + `min-w-full` 테이블 | 래퍼 존재하나 컬럼 수에 따라 375px에서 다수 컬럼 압축 가능 |
| OK | `app/watchlist/page.tsx:294` | `overflow-x-auto` 래퍼 있음 | 정상 |

---

## 2. 터치 타겟

### 2.1 44pt 미만 추정 요소

| 심각도 | 파일경로:라인 | 요소 | 추정 크기 |
|--------|-------------|------|----------|
| BLOCKER | `app/thesis/new/page.tsx:640` | `<Link href="/thesis" className="p-1 ...">` 뒤로가기 | p-1(4px padding) + ArrowLeft 20px = ~28x28px. 44pt 크게 미달 |
| BLOCKER | `app/thesis/[thesisId]/close/page.tsx:51` | `<Link href="/thesis" className="p-1 ...">` 뒤로가기 | 동일, ~28x28px |
| BLOCKER | `app/thesis/[thesisId]/indicators/page.tsx:199` | `<Link href="/thesis" className="p-1 ...">` 뒤로가기 | 동일, ~28x28px |
| MAJOR | `app/thesis/[thesisId]/close/page.tsx:136` | `className="p-1 ..."` 추가 액션 버튼 | ~28x28px |
| MAJOR | `components/thesis/builder/NewsSelector.tsx:142` | `<button onClick={onBack} className="p-1 ...">` 뒤로가기 | ~28x28px |
| MINOR | `components/thesis/builder/OptionButton.tsx:72` | `className="hidden sm:flex p-1 ..."` | 모바일에서 `hidden`으로 실제 미표시됨 |
| MINOR | `components/chainsight/WatchButton.tsx:48` | `py-1.5` 버튼 | 높이 ~32px. 44pt 미달이나 버튼 폭이 넓어 실제 탭 영역은 양호 |
| MINOR | `components/screener/Pagination.tsx:127` | `min-w-[32px] px-2 py-1.5` 페이지 버튼 | 높이 ~32px. 44pt 미달 |

### 2.2 작은 폰트 클릭 요소

| 심각도 | 파일경로:라인 | 요소 | 크기 |
|--------|-------------|------|------|
| MAJOR | `components/thesis/dashboard/IndicatorRow.tsx:182` | 기간 선택 버튼 (`px-2.5 py-0.5 text-[10px]`) — 클릭 가능 `<button>` 4개 (1M/1Y/3Y/5Y) | 높이 ~18-20px. 10px 폰트. 터치 타겟 크게 미달 |
| MINOR | `app/thesis/new/page.tsx:753` | `span.text-[10px]` 방향성 배지 (정보성, 비클릭) | 비클릭 요소 |
| MINOR | `app/screener/page.tsx:528` | `span.text-[10px]` 뱃지 (비클릭) | 정보성 요소 |
| MINOR | `components/screener/PresetGallery.tsx:241` | `text-[10px] transition-colors` span (hover 전용) | 실제 클릭 없음 |
| MINOR | `components/eod/SignalFilterTabs.tsx:68` | `text-[11px]` 필터 탭 내 카운트 배지 | 배지 자체는 클릭 없음, 탭은 충분한 크기 |

---

## 3. 네비게이션

### 3.1 MobileNav 분석

파일: `components/layout/MobileNav.tsx`

- 존재: `fixed bottom-0 md:hidden` 바텀 탭 (5개 항목)
- 터치 타겟: 각 항목 `min-h-[44px]` 보장 — Apple HIG 준수
- 현재 항목: 홈 / 종목(`/stocks`) / 뉴스 / 포트폴리오 / 내정보
- **MAJOR 누락**: Thesis Control, Chain Sight, Market Pulse, Screener, Watchlist, AI Analysis 등 주요 기능 페이지가 모바일 탭에 없음. 해당 페이지 접근 경로가 바텀 탭에서 완전히 누락됨

### 3.2 Header.tsx 분석

- 데스크톱 nav `hidden md:flex` — 모바일에서 숨겨짐 (정상)
- 햄버거 버튼(라인 157): `className="hidden inline-flex ..."` — **의도적으로 비활성화**. 주석 "MobileNav가 모바일 네비 단일 소스"로 명시
- 결과: Header의 햄버거 드롭다운(Chain Sight, Thesis, Market Pulse 포함) 모바일에서 접근 불가
- **MAJOR**: `/thesis`, `/chainsight`, `/market-pulse`, `/screener`, `/watchlist`, `/ai-analysis` 경로의 모바일 직접 네비게이션 경로 없음. URL 직접 입력 또는 페이지 내 링크에만 의존

### 3.3 InvestingHeader.tsx 분석

- **BLOCKER**: 모바일 대응 전무. 상단 티커 바(`flex items-center space-x-6`)와 nav(`flex items-center h-10`)가 데스크톱 전용
- 현재 어떤 page.tsx에서도 import되지 않음(grep: 컴포넌트 파일 내 정의 1건만). 미사용 상태로 판단되나 향후 사용 시 BLOCKER 확정

### 3.4 Virtualization

- `react-window`, `react-virtualized`, `useVirtual` 미사용 (검색 결과 0건)
- 스크리너 결과·뉴스 목록·watchlist에서 DOM 노드 대량 렌더링 가능
- 현재 `Pagination.tsx`로 일부 제어. 한 페이지 항목 수 많을 경우 모바일에서 성능 저하 잠재
- **MINOR**: 긴 목록 페이지에 virtualization 도입 권장

---

## 4. 차트/그래프

### 4.1 ResponsiveContainer 사용 현황 (정상 파일)

| 파일 | 상태 |
|------|------|
| `components/charts/StockPriceChart.tsx` | `ResponsiveContainer width="100%"` — 정상 |
| `components/macro/YieldCurveChart.tsx` | `ResponsiveContainer width="100%" height="100%"` — 정상 |
| `components/news/SentimentChart.tsx` | 정상 |
| `components/portfolio/PortfolioChart.tsx` | `ResponsiveContainer` 있으나 내부 `<Pie height={100}>` 직접 지정 — MINOR |
| `components/screener/SectorHeatmap.tsx` | `ResponsiveContainer width="100%" height={400}` — 폭 반응형, 높이 고정 |
| `components/thesis/dashboard/IndicatorRow.tsx` | `ResponsiveContainer width="100%" height={160}` — 정상 |
| `app/market-pulse-v2/details/*` | `ResponsiveContainer` 래퍼 사용 — 정상 |

### 4.2 ResponsiveContainer 미사용 / 고정 크기 차트

| 심각도 | 파일경로:라인 | 문제 |
|--------|-------------|------|
| MINOR | `components/portfolio/PortfolioChart.tsx:106` | `<Pie ... height={100}>` PieChart 요소에 height 직접 지정. `ResponsiveContainer` 래퍼 있지만 내부 Pie에 height 중복 지정으로 충돌 가능 |

### 4.3 고정 높이 컨테이너 내 차트

| 심각도 | 파일경로:라인 | 클래스 | 영향 |
|--------|-------------|--------|------|
| MAJOR | `app/screener/page.tsx:465` | `h-[400px]` 차트 컨테이너 | 375px 폰에서 400px = 화면 87% 점유. 실제 차트 없고 placeholder이지만 스크롤 부담 |
| MAJOR | `components/chainsight/MarketGraphCanvas.tsx:141` | `h-[400px]` force-graph 캔버스 | 375px에서 화면 대부분 차지. 그래프 탐색 UI가 스크롤 없이 접근 불가 |
| MAJOR | `components/chainsight/MarketGraphCanvas.tsx:124,134` | `h-[400px]` 로딩/에러 상태 | 동일 |
| MINOR | `components/screener/SectorHeatmap.tsx:216` | `height={400}` (ResponsiveContainer 있음) | 폭 반응형, 높이 고정. 모바일에서 여백 낭비 |

### 4.4 스파크라인 가독성

파일: `components/thesis/dashboard/IndicatorRow.tsx`

- 인라인 스파크라인: `max-w-[100px]` 컨테이너 내 `QuarterlySparkline` (최근 4분기). 100px 이하 너비로 바 높이 판독 어려움 — **MINOR**
- 확장 시 `AreaChart height={160}` + `ResponsiveContainer width="100%"` — 정상
- XAxis `fontSize={9}`, YAxis `fontSize={10}` — 모바일에서 매우 작음. 최소 11px 권장 — **MINOR**

---

## 5. 페이지별 상세

### `/thesis/[thesisId]` (가설 관제실)

- **BLOCKER**: IndicatorRow 내 min-w-[60px] + min-w-[120px] 고정 폭 조합. 375px에서 스파크라인과 지지/반박 텍스트 공간 부족
- **MAJOR**: IndicatorRow 기간 선택 버튼 `px-2.5 py-0.5 text-[10px]` — 높이 ~18-20px, 터치 타겟 크게 미달
- **MINOR**: `text-[11px]` 라벨(날짜, 전제명, 설명) 다수
- OK: 페이지 최상위 `max-w-lg mx-auto pb-20` (바텀 탭 여백) 정상

### `/thesis/new` (가설 세우기)

- **BLOCKER**: 뒤로가기 Link `p-1` (~28x28px). 좌상단 배치, 손가락 정확 터치 어려움
- **MINOR**: `text-[10px]` 섹션 레이블 다수 (거시 Macro, 미시 Micro, 현재 가설 등)
- OK: 전체 세로 flex 레이아웃, 모바일 전용 설계

### `/thesis/[thesisId]/close` (마감 결과)

- **BLOCKER**: 뒤로가기 Link `p-1` (line:51) + 추가 액션 버튼 `p-1` (line:136)

### `/thesis/[thesisId]/indicators` (지표 설정)

- **BLOCKER**: 뒤로가기 Link `p-1` (line:199)

### `/chainsight/[symbol]` (Chain Sight 그래프)

- **OK**: `isMobile`(`window.innerWidth < 768`) 분기 존재. 모바일에서 `MobileCardList` + 그래프 오버레이로 전환
- **MAJOR**: 데스크톱 3-패널 레이아웃 — 좌측 `w-60` 패널은 `leftOpen` true 시 항상 렌더링. `768px~1023px` 구간에서 우측 `hidden lg:block` 패널은 숨겨지나 좌측 w-60이 잠재적 overflow 발생 가능
- **MINOR**: 모바일 오버레이 닫기 버튼 `px-3 py-1` — 높이 ~32px, 44pt 미달

### `/screener` (스크리너)

- **MAJOR**: 스크리너 테이블 뷰 `hidden sm:block` — 640px 미만 모바일에서 hidden. 카드 뷰로 대체되지만 뷰 전환 버튼이 명확하지 않으면 결과 미표시로 오해 가능
- **MAJOR**: `MarketBreadthCard` `grid-cols-3` 브레이크포인트 누락
- OK: `PresetGallery` `grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6` 반응형 올바름
- OK: `AdvancedFilterPanel` 반응형 올바름
- OK: `MobileStockCard` 모바일 전용 카드 컴포넌트 존재

### `/stocks/[symbol]` (종목 상세)

- **MINOR**: `grid grid-cols-2` Key Metrics 영역(line:329) — 2열이므로 375px에서 수용 가능, 브레이크포인트 명시 권장
- OK: 재무제표 테이블 `overflow-x-auto` 래퍼 있음
- OK: `isMobile` 분기 존재(line:926). 모바일에서 탭 `overflow-x-auto` 처리

### `/market-pulse-v2`

- **BLOCKER**: `FlowCardSummary`, `FlowDetail`, `BreadthDetail`의 `grid-cols-3` 브레이크포인트 미적용. 375px에서 열 폭 ~117px, 숫자/라벨 판독 불편
- **MINOR**: `BriefDetail` — `text-[10px]` 정보성 텍스트
- **MINOR**: `page.tsx:77` — `text-[10px]` footer 텍스트

### `/portfolio` (포트폴리오)

- OK: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 반응형 올바름
- OK: `PortfolioTable` `overflow-x-auto` 있음
- OK: `PortfolioChart` `ResponsiveContainer` 사용
- MINOR: `PortfolioChart.tsx:106` `<Pie height={100}>` 직접 지정

### `/watchlist` (관심종목)

- OK: `grid grid-cols-1 lg:grid-cols-3` 반응형
- OK: 테이블 `overflow-x-auto` 래퍼 있음

### `/news` (뉴스)

- OK: `grid grid-cols-1 lg:grid-cols-3` 반응형
- MINOR: `SentimentChart` `grid grid-cols-2 md:grid-cols-4` — 모바일 2열이 좁음

### 기타 페이지

- `/login:157` — `grid grid-cols-2` 소셜 로그인 버튼. 2열, 375px에서 허용 가능
- `/dashboard` — `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 반응형 올바름
- `/validation` — `CategorySection`에 `isMobile` 분기 + `MobileMetricAccordion` 별도 구현. 비교적 양호

---

## 권장 우선순위

1. **[BLOCKER] thesis 계열 뒤로가기 터치 타겟 확대** — `app/thesis/new/page.tsx:640`, `app/thesis/[thesisId]/close/page.tsx:51,136`, `app/thesis/[thesisId]/indicators/page.tsx:199`, `components/thesis/builder/NewsSelector.tsx:142` — `p-1` → `p-2.5 min-h-[44px] min-w-[44px]` 교체

2. **[BLOCKER] market-pulse-v2 grid-cols-3 반응형 추가** — `FlowCardSummary.tsx:13`, `FlowDetail.tsx:34`, `BreadthDetail.tsx:29` — `grid grid-cols-1 sm:grid-cols-3`으로 변경

3. **[MAJOR] MobileNav 누락 항목 보완** — Thesis Control, Chain Sight, Market Pulse, Screener, Watchlist 접근 경로 추가 (바텀 탭 항목 확장 또는 홈 화면 그리드 메뉴 제공)

4. **[MAJOR] IndicatorRow 기간 선택 버튼 터치 타겟 확대** — `components/thesis/dashboard/IndicatorRow.tsx:182` — `py-0.5 text-[10px]` → `py-1.5 text-xs` (최소 32px 높이 확보)

5. **[MAJOR] IndicatorRow min-w 고정폭 조정** — `IndicatorRow.tsx:110,115` — `min-w-[120px]` 제거 후 flex-wrap 또는 모바일 2행 레이아웃 재구성

6. **[MAJOR] screener MarketBreadthCard grid-cols-3 반응형** — `components/screener/MarketBreadthCard.tsx:107` — `grid-cols-3` → `grid-cols-1 sm:grid-cols-3`

7. **[MAJOR] ThesisSkeleton grid-cols-3 반응형** — `components/thesis/skeleton/ThesisSkeleton.tsx:68` — `grid grid-cols-3` → `grid grid-cols-1 sm:grid-cols-3`

8. **[MAJOR] YieldCurveChart Key Rates grid-cols-3 반응형** — `components/macro/YieldCurveChart.tsx:147`

9. **[MAJOR] chainsight MarketGraphCanvas 고정 h-[400px] 유연화** — `components/chainsight/MarketGraphCanvas.tsx:141` — `h-[400px]` → `h-64 md:h-[400px]` 또는 `min-h-[200px] max-h-[60vh]`

10. **[MAJOR] MonitoringDashboard / MLModelCard grid-cols-3 반응형** — admin 전용이지만 동일하게 `grid-cols-1 sm:grid-cols-3` 적용 권장

11. **[MINOR] IndicatorRow 차트 축 폰트 크기 상향** — `XAxis fontSize={9}` → 11 이상

12. **[BLOCKER 예비] InvestingHeader 모바일 대응 설계** — 현재 미사용이나 도입 전 모바일 햄버거 메뉴 또는 별도 모바일 레이아웃 설계 필요

---

*이 보고서는 코드 정적 분석(grep + read) 기반으로 작성되었습니다. 실제 렌더링 결과는 브라우저 DevTools 모바일 뷰포트 시뮬레이션으로 추가 검증을 권장합니다.*
