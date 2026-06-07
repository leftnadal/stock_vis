# 모바일 UX 감사 보고서

> **감사 일자**: 2026-06-07
> **대상**: `frontend/` (Next.js 16 + Tailwind, 255개 tsx 파일 / 30개 page.tsx)
> **기준폭**: 375px (iPhone SE/표준 모바일)
> **모드**: 읽기 전용 (코드 미수정)
> **방법**: 패턴 grep(고정폭/소형폰트/브레이크포인트/ResponsiveContainer) + 4개 영역 병렬 정독

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|--------|------|------|
| 🔴 **BLOCKER** | **9** | 모바일에서 기능 사용 불가 / 콘텐츠 접근 차단 / 콘텐츠 잘림 |
| 🟠 **MAJOR** | **18** | 심각한 불편 (가독성·터치 정확도·레이아웃 붕괴) |
| 🟡 **MINOR** | **15** | 경미한 개선 권장 |

### 전역(Global) 최우선 이슈 — 모든 페이지에 영향

| # | 이슈 | 심각도 | 근거 |
|---|------|--------|------|
| G-1 | **핀치 줌 전면 차단** — `userScalable: false` + `maximumScale: 1` 설정으로 사용자가 텍스트를 확대할 수 없음. 아래 "소형 폰트" 이슈(127곳의 `text-[10px]/[11px]`)와 결합되어 **WCAG 2.1 SC 1.4.4 (Resize Text) 위반**. 저시력 사용자는 화면 정보에 접근 불가. | 🔴 BLOCKER | `frontend/app/layout.tsx:29-35` |
| G-2 | **호버 의존 정보(tooltip)** — Market Movers 지표 5종(RVOL/추세강도/알파/ETF 동행률/변동성) 설명이 `group-hover/tooltip`으로만 노출. 터치 디바이스에는 hover 이벤트가 없어 **모바일에서 핵심 지표 설명에 영구 접근 불가**. | 🔴 BLOCKER | `frontend/components/market-pulse/MoverCard.tsx:130-165`, `MoverCardWithBatchKeywords.tsx` |
| G-3 | **아이콘 버튼 터치 타겟 미달 패턴** — `p-1`/`p-1.5`/`p-2` + 14~16px 아이콘 조합이 다수 컴포넌트에 반복. 실제 터치 영역 12~24px로 Apple HIG 44pt 기준 미달. 삭제/닫기/토글 등 파괴적·필수 액션에 집중. | 🔴 BLOCKER | 다수 (아래 터치 타겟 섹션) |

> **참고 — 잘 된 부분**: `MobileNav.tsx`는 bottom nav 5개 항목 모두 `min-h-[44px]` + `h-16` 컨테이너로 HIG 준수(`frontend/components/layout/MobileNav.tsx:20-45`). `Header.tsx`/`MobileNav` 역할 분리(`md:hidden` ↔ `hidden md:flex`)도 의도적으로 설계됨. ResponsiveContainer는 차트 15곳 중 대부분에서 `width="100%"` 사용.

---

## 반응형 누락

### A. 고정 폭 → 375px 오버플로우 (BLOCKER/MAJOR)

| 파일:라인 | 심각도 | 내용 |
|----------|--------|------|
| `components/layout/InvestingHeader.tsx:32,55,99` | 🔴 BLOCKER | `max-w-[1400px]` + `px-4`만 적용된 데스크톱 전용 헤더. 상단 정보바(지수 4종 `space-x-4`) + 네비 메뉴 다수 항목이 모바일 대응(햄버거/숨김) 전무. 375px에서 콘텐츠 잘림·오버플로우. ※ 단, 실제 적용 페이지 범위 확인 필요(Header.tsx와 병존). |
| `components/portfolio/PortfolioTable.tsx:259-494` | 🔴 BLOCKER | 12열 테이블. `overflow-x-auto`는 있으나 `px-6 py-3` 고정 패딩으로 375px에서 각 컬럼 극단적 축소 + 가로스크롤 강제. 편집 입력 필드 `w-24`(96px)로 협소. |
| `components/stocks/StockTable.tsx:34-138` | 🔴 BLOCKER | 7열 테이블. `overflow-x-auto` 존재하나 `px-6 py-3` 고정. 모바일 카드 폴백 없음. |
| `components/strategy/ScreenerTable.tsx:128,845` | 🟠 MAJOR | `hidden sm:block`으로 모바일에선 숨기고 카드뷰로 폴백하는 점은 양호. 단 sm(640px) 이상에선 다열 테이블이 협소. `max-w-[180px]/[120px]` truncate 컬럼 다수. |
| `components/validation/LeaderComparisonSection.tsx:47-62` | 🟠 MAJOR | 비교 테이블 `overflow-x-auto`만으로 대응. 컬럼 축소/카드 전환 전략 없음. |
| `app/market-pulse-v2/components/TickerBar.tsx:23` | 🟠 MAJOR | `sticky top-0` + `whitespace-nowrap` 티커바. 모바일에서 4개+ 항목이 화면 밖, 가로스크롤 없이는 핵심 지수 미표시. |
| `components/validation/SignalSummaryCard.tsx:36,41` | 🟠 MAJOR | 신호등 7개 × `min-w-[72px]` = 504px > 375px. `overflow-x-auto`로 가로스크롤 강제. |
| `components/chainsight/MarketGraphCanvas.tsx:676` | 🟠 MAJOR | 빈 상태 CTA 버튼 `w-[110px]` × 3개 = 330px+gap, 375px에서 한 행 정렬 임계. |
| `app/coach/e1~e6/page.tsx:150` | 🟠 MAJOR | 입력 행이 `grid-cols-12`(col-span 3/2/2/2/2/1) 고정. 모바일 브레이크포인트 없이 12열 유지 → 입력 필드 극단 압축, 텍스트 가독 불가. **E1~E6 6개 페이지 동일 패턴**. |
| `components/admin/*` (NewsTab, ScreenerTab, CollectionStatsTable, TaskLogViewer, SystemTab) | 🟠 MAJOR | Admin 전반이 `overflow-x-auto` 테이블만 + `px-2/px-3` 패딩, `sm:` 분기 없음. 사실상 모바일 대응 포기 수준. (Admin은 데스크톱 전용 용인 가능하나 명시적 결정 필요) |

### B. 브레이크포인트 단계 누락 / 데스크톱 우선 (MINOR)

| 파일:라인 | 심각도 | 내용 |
|----------|--------|------|
| `app/screener/page.tsx:435` | 🟡 MINOR | `grid-cols-1 lg:grid-cols-3` — sm/md 중간 단계 없이 1열→3열 급변. `sm:grid-cols-2` 권장. |
| `components/screener/PresetGallery.tsx:355` | 🟡 MINOR | `grid-cols-2 md:...` 모바일 2열 → 카드 폭 ~187px, 배지·텍스트 겹침. |
| `components/news/RecommendationCard.tsx:104` | 🟡 MINOR | 이유 배지 3개가 `flex-wrap` 없이 한 줄 → 375px 오버플로우. |

### C. 통계

- 브레이크포인트(`sm:/md:/lg:`) 사용 파일: **72/255 (28%)** — 나머지 72%는 단일 레이아웃.
- `overflow-x`(가로스크롤 컨테이너) 사용: **28곳** — 대부분 테이블/칩 영역. 카드 전환 폴백을 갖춘 곳은 ScreenerTable·MobileStockCard 정도.
- 고정 px 폭(`w-[Npx]`류): **23개 파일 31곳**.

---

## 터치 타겟

> Apple HIG 44×44pt / WCAG 2.5.5 기준. `p-N` 패딩 + 아이콘 크기로 실측 추정.

### BLOCKER — 필수/파괴적 액션 버튼 미달

| 파일:라인 | 실측 추정 | 내용 |
|----------|----------|------|
| `app/coach/e1~e6/page.tsx:200` | ~16×16px | 행 삭제 버튼 `p-1.5` + `Trash2 h-4 w-4`. **E1~E6 전부**. 파괴적 액션이 가장 작음. |
| `components/admin/news/MLCompareView.tsx:116` | ~20×20px | 롤백 모달 닫기 `p-1` + `X h-4 w-4`. |
| `components/thesis/indicators/IndicatorSetupCard.tsx:49-68` | ~32×32px | 지표 토글/삭제 `p-2` + `size=16`. 관제실 지표 설정 핵심 동작. |
| `components/thesis/indicators/RecommendCard.tsx:44-56` | ~36×36px | 추천 지표 추가 `p-2.5` + `size=16`. |
| `components/thesis/builder/PremiseCard.tsx:32-40` | ~22×22px | 전제 삭제 `p-1` + `X size=14`. |
| `components/thesis/alerts/AlertCard.tsx:52-62` | ~24×20px | 알림 읽음 처리 `px-2 py-1 text-[10px]`. |

### MAJOR — 탭/칩/노드 높이 부족

| 파일:라인 | 실측 추정 | 내용 |
|----------|----------|------|
| `components/eod/SignalFilterTabs.tsx:44` | h ~32px | 시그널 필터 탭 `px-3 py-1.5`. 가로스크롤 + 작은 높이로 선택 난이도 ↑. |
| `components/chainsight/RelationFilterChips.tsx:150` | h 32px | 관계 필터 칩 `h-8 px-3`. |
| `components/chainsight/RelationCardPanel.tsx:240-257` | h ~20px | 탐색 CTA `py-1 text-xs` × 3 (flex-1). |
| `components/chainsight/MarketGraphCanvas.tsx:787,853` | r=20~28px | 노드 클릭 반경. 경계 근처 터치 실패 가능. 노드 라벨 폰트 `r>10?9:7`px — 작은 노드 7px 판독 불가. |
| `components/validation/LeaderComparisonSection.tsx:116` | ~20px | 테이블 셀 Check/X 아이콘 `py-1.5`. |
| `components/validation/SignalSummaryCard.tsx:38` | 44px(원) | 신호등 `w-11 h-11`은 충족하나 7개 가로배치 + gap으로 인접 오터치. |
| `components/thesis/dashboard/QuarterlySparkline.tsx:41` | h44/w~85px | 분기 버튼 높이는 OK, 4분기 가로배치 시 손가락 정확도 위험 + 호버 툴팁이 터치에서 토글로 오작동. |
| `components/screener/Pagination.tsx:94` | ~24px | 첫/끝 페이지 화살표 `p-1.5`(번호 버튼은 `min-w/h-[44px]`로 양호). |

### MINOR — 소형 폰트 클릭 요소 (G-1과 결합 시 격상)

`text-[10px]`/`text-[11px]`은 **127곳 57파일**에 분포. 클릭 가능 요소에 쓰인 대표 사례:

| 파일:라인 | 내용 |
|----------|------|
| `components/screener/MobileStockCard.tsx:166` | 모바일 카드 라벨 `text-[10px]` (모바일 전용 컴포넌트인데 최소 폰트) |
| `components/thesis/builder/OptionButton.tsx:72` | `text-[10px]` "꾹 누르면 설명" 안내 |
| `components/coach/ActionItemsSection.tsx:50` | 우선순위 배지 `text-[11px]` |
| `components/coach/ConfidenceBadge.tsx:31` | sm 사이즈 `text-[11px]` |
| `app/coach/e4/page.tsx:213` | 글자수 카운터 `text-[11px]` |
| `components/eod/SignalFilterTabs.tsx:68` | 카운트 배지 `text-[11px]` |

> G-1(줌 차단)이 해소되지 않는 한 이 그룹은 사실상 MAJOR로 취급해야 함.

---

## 네비게이션

| 항목 | 상태 | 근거 |
|------|------|------|
| Bottom Navigation | ✅ 존재 (양호) | `MobileNav.tsx` — 홈/종목/뉴스/포트폴리오/내정보 5개, `fixed bottom-0`, `md:hidden`, `min-h-[44px]`, `z-50`. HIG 준수. |
| Bottom Nav 커버리지 | 🟠 MAJOR | 5개 항목만 노출 → **thesis(관제실)·chainsight·screener·coach·validation·dashboard 등 주요 기능은 모바일 1차 네비에서 접근 불가**. 진입 경로 불명확. |
| 햄버거 메뉴 | 🟡 의도적 | `Header.tsx:42` 데스크톱 네비 `hidden md:flex`, 햄버거 버튼은 `hidden`(155-163)으로 비활성. MobileNav가 단일 소스라는 주석 존재 → 설계 의도이나, 위 커버리지 공백과 맞물림. |
| InvestingHeader 모바일 대응 | 🔴 BLOCKER | 별도 헤더(`InvestingHeader.tsx`)는 모바일 네비/햄버거 전무. 적용 화면에서 네비게이션 붕괴. |
| 긴 목록 virtualization | 🟡 MINOR | 스크리너(페이지네이션 50개), 뉴스(`limit:100` 일괄), 무버(~20-100개) 모두 가상화 미적용. 현재 규모에선 페이지네이션으로 완화되나 뉴스 100개 일괄 렌더는 모바일 초기 로드 부담. `app/news/page.tsx:47`. |

---

## 차트/그래프

| 파일:라인 | 심각도 | 내용 |
|----------|--------|------|
| `components/charts/StockPriceChart.tsx:272`, `components/stock/StockChart.tsx:652,748` | ✅ 양호 | `ResponsiveContainer width="100%"`. StockChart는 `getResponsiveChartHeight(windowWidth)`로 모바일 높이 동적 축소 + resize 리스너까지 구현(모범 사례). |
| `app/market-pulse-v2/details/{Sector,Flow,Regime,Breadth}Detail.tsx` | 🟠 MAJOR×4 | 인라인 `style={{height: 200~280}}` 고정. 375px에서 Radar/Pie 레이블 겹침·압축. 동적 높이 없음. |
| `components/macro/YieldCurveChart.tsx:92` | 🟠 MAJOR | 부모 `h-64` 고정, 모바일 높이 최적화 없음. |
| `components/news/SentimentChart.tsx:79` | 🟠 MAJOR | 부모 `h-80`(320px) 고정 → 모바일 뷰포트의 ~48% 차지, 범례/축 겹침. |
| `components/thesis/dashboard/IndicatorRow.tsx:197,235` | 🟠 MAJOR | 펼침 AreaChart `height={160}`, 분기차트 `height={140}` 고정. 모바일 권장 240px 대비 협소. |
| `components/validation/MetricBarChart.tsx:72,90` | 🟠 MAJOR | `h-48` 고정 + `YAxis width={50}`(375px의 13% 점유) + 라벨 `fontSize 11/10/9` 혼재 → 텍스트 잘림. |
| `components/thesis/dashboard/QuarterlySparkline.tsx:33-70` | 🟡 MINOR | 분기 스파크라인 `h-10` + 라벨 `text-[11px]` — 좁은 폭에서 라벨 겹침, 호버 툴팁 모바일 비호환. |
| 공통 (Recharts) | 🟡 MINOR | Recharts는 터치 핀치줌/팬 미지원. 데이터 밀집 차트의 모바일 탐색 제약. |

---

## 페이지별 상세

### `/` (홈/대시보드) · `/dashboard`
- EOD 시그널 영역: `SignalFilterTabs` 탭 높이 32px(MAJOR), 카운트 배지 `text-[11px]`. `StockRow` `max-w-[140px]` truncate.
- 차트 ResponsiveContainer 양호.

### `/portfolio` · `/watchlist`
- 🔴 `PortfolioTable` 12열 가로스크롤 + 편집필드 `w-24`. 요약카드 `grid-cols-2`에서 `text-2xl` 줄바꿈 위험.
- `PortfolioChart` height=400 고정이나 가로 반응형은 OK(MINOR).

### `/stocks` · `/stocks/[symbol]`
- 🔴 `StockTable` 7열 가로스크롤.
- `StockChart`는 모바일 높이 동적 처리(모범). 단 기간선택 버튼(`5d/1m/3m/1y` + 설정) `flex space-x-1`로 375px 한 줄 초과 위험(MAJOR), 차트타입 선택 버튼 3개도 동일.

### `/screener`
- 모바일 카드뷰 자동 폴백(`hidden sm:block`) 양호. `MobileStockCard` 라벨 `text-[10px]`(MINOR→G-1 결합 시 격상).
- `Pagination` 첫/끝 화살표 `p-1.5`(MINOR). grid 단계 급변(MINOR).

### `/market-pulse` · `/market-pulse-v2`
- 🔴 `MoverCard` 지표 5종 호버 툴팁 → 모바일 접근 불가(G-2).
- 🟠 `TickerBar` 가로스크롤 강제, details 차트 4종 고정 높이.
- MoverCard 가격/지표 `text-[10px]` 다수.

### `/news`
- `RecommendationCard` 이유 배지 오버플로우(MINOR), 종목명 `truncate max-w-[150px]`.
- 뉴스 100개 일괄 렌더(MINOR).

### `/thesis` (관제실) ⭐ 집중 점검 대상
- 🔴 지표 카드 액션 버튼군 터치 미달: `IndicatorSetupCard`(p-2), `RecommendCard`(p-2.5), `AlertCard`(px-2 py-1 text-[10px]).
- 🟠 `IndicatorRow` 차트 고정 높이 160/140, `QuarterlySparkline` 분기버튼·호버툴팁.
- 컨테이너 `max-w-lg mx-auto px-4`는 375px에서 안전(MINOR). 지표명/설명 `text-xs`+`text-[10px]` 4단 폰트 혼재.

### `/thesis/new` (빌더)
- 🔴 `PremiseCard` 삭제 `p-1`. `OptionButton` Info 아이콘 `hidden sm:flex`(모바일 숨김). `text-[10px]` 7곳.

### `/validation` (1차 검증) ⭐ 집중 점검 대상
- 🟠 프리셋/신호등: `SignalSummaryCard` 7개×72px 가로스크롤, `PeerContextBar` 탭 `text-xs`, `LeaderComparisonSection` 테이블+셀아이콘 작음.
- 🟠 `MetricBarChart` YAxis 50px 점유 + 폰트 잘림.

### `/chainsight` ⭐ 집중 점검 대상
- 🟠 `MarketGraphCanvas`: 더블탭/롱프레스(500ms) 인터랙션 비직관적, 노드 라벨 7px, 노드 터치 반경 협소, 빈상태 SVG viewBox 고정.
- 🟠 `RelationFilterChips` h-8, `RelationCardPanel` CTA py-1. `NodeTooltip` 종목명 줄바꿈(`max-w-[130px]`).
- `MobileCardList` CTA `min-h-[44px]` 준수(양호).

### `/coach/e1~e6`
- 🔴 입력 행 `grid-cols-12` 고정(6페이지) + 행삭제 버튼 `p-1.5`(6페이지).
- 🟡 E4 대화: 메시지 영역 `max-h-[60vh]` 모바일 과축소, 카운터 `text-[11px]`. 전송버튼 `h-[44px]` 충족.

### `/admin`
- 🟠 전 탭 테이블이 `overflow-x-auto`+소패딩만, `sm:` 분기 없음(NewsTab/ScreenerTab/CollectionStatsTable/TaskLogViewer/SystemTab).
- 🔴 `MLCompareView` 모달 닫기 `p-1`. `AdminTabNav`는 `min-h-[44px]`+가로스크롤로 양호.
- ※ Admin은 데스크톱 전용 용인 가능 — 단 정책적 명시 권장.

---

## 우선순위 권고 (요약)

1. **G-1 즉시**: `userScalable: false`/`maximumScale: 1` 제거 → 줌 허용(접근성 법규 리스크). `frontend/app/layout.tsx:33`.
2. **G-2 즉시**: MoverCard 호버 툴팁 → 탭/클릭 팝오버 전환(모바일 정보 접근 복구).
3. **G-3 / BLOCKER 터치**: 파괴적·필수 아이콘 버튼(`p-1`~`p-2`)을 `min-h-[44px] min-w-[44px]`로 일괄 상향 — coach 삭제, thesis 지표 설정/삭제, 모달 닫기.
4. **테이블 BLOCKER**: PortfolioTable/StockTable 모바일 카드뷰 폴백 도입(ScreenerTable 패턴 재사용).
5. **차트 MAJOR**: 고정 높이 차트(market-pulse-v2 details 4종, IndicatorRow, Sentiment/YieldCurve)에 `getResponsiveChartHeight` 패턴 확산.
6. **네비 MAJOR**: bottom nav 5개 외 주요 기능(thesis/screener/chainsight) 진입 경로 보강(More 메뉴 등).

> 본 보고서는 정적 코드 분석 기반 추정치입니다. 실제 렌더 검증(브라우저 375px 뷰포트 스냅샷)으로 BLOCKER 9건 우선 재현 권장.
