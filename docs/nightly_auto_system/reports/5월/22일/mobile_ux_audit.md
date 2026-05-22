# 모바일 UX 감사 보고서
- 날짜: 2026-05-22
- 대상: frontend/
- 감사자: @frontend (읽기 전용 — 코드 수정 없음)

---

## 요약

| 심각도 | 건수 |
|--------|------|
| BLOCKER | 5건 |
| MAJOR | 11건 |
| MINOR | 7건 |

**총계: 23건**

---

## 반응형 누락

### BLOCKER-1: PortfolioTable — 12컬럼 테이블, 모바일 collapse 없음
**파일**: `frontend/components/portfolio/PortfolioTable.tsx:260–300`
```tsx
<div className="overflow-x-auto">
  <table className="min-w-full divide-y ...">
    <thead>
      <tr>
        <th>종목</th>
        <th>보유수량</th>
        <th>평균매수가</th>
        <th>현재가</th>
        <th>전일대비</th>
        <th>평가금액</th>
        <th>손익</th>
        <th>수익률</th>
        <th>목표가</th>
        <th>손절가</th>
        <th>비중</th>
        <th>관리</th>  {/* 12컬럼 */}
      </tr>
```
**영향**: `overflow-x-auto`로 가로 스크롤은 가능하지만, 375px에서 컬럼 수가 12개 — 종목명도 식별하기 어려운 수준. 각 셀 `px-6 py-4` 패딩이 더해져 최소 800px+ 필요. 모바일 카드 레이아웃으로 분기하는 로직 없음. 포트폴리오는 핵심 기능 — **BLOCKER**.

### BLOCKER-2: StrategyScreener ScreenerTable — 10컬럼 테이블, 모바일 뷰 부재
**파일**: `frontend/components/strategy/ScreenerTable.tsx:128–185`
```tsx
<div className="overflow-x-auto">
  <table className="w-full">
    <thead>
      <tr>
        <th>종목</th><th>거래소</th><th>섹터</th>
        <th>가격</th><th>변동률</th><th>시가총액</th>
        <th>거래량(주)</th><th>배당률</th><th>베타</th>
        <th>유형</th><th>AI 키워드</th>
        {onAddToBasket && <th>액션</th>}  {/* 최대 12컬럼 */}
      </tr>
```
**영향**: `screener/page.tsx`에 `viewMode: 'table' | 'card'` + `MobileStockCard` 분기가 존재하나, 기본값이 `'table'`이고 모바일에서 자동 전환 없음. 사용자가 직접 카드 모드로 전환해야 함 — 발견성 낮음. ScreenerTable 자체에는 반응형 숨김 없음.

### BLOCKER-3: /stocks/[symbol] — L2 탭 내비게이션 `flex space-x-6`, 모바일 줄바꿈 없음
**파일**: `frontend/app/stocks/[symbol]/page.tsx:402–418`
```tsx
<nav className="flex space-x-6">
  {L2_TABS[activeL1].map((l2) => (
    <button
      className="pb-3 text-sm font-medium border-b-2 ..."
    >
```
**영향**: `fundamentals` L1 선택 시 L2 탭이 5개(Overview / Balance Sheet / Income Statement / Cash Flow / 기타 펀더멘탈). `flex` + `space-x-6`만 있고 `overflow-x-auto`나 `sm:` 분기 없음. 375px에서 탭이 잘려 마지막 탭("기타 펀더멘탈") 접근 불가.

### BLOCKER-4: /stocks/[symbol] 재무제표 테이블 — `min-w-full`, 다분기 컬럼 고정 폭 없음
**파일**: `frontend/app/stocks/[symbol]/page.tsx:843–886`
```tsx
<div className="overflow-x-auto">
  <table className="min-w-full">
    <thead>
      {data.map((item, index) => (
        <th ...>  {/* 분기별 컬럼 — 8분기면 8컬럼 */}
```
**영향**: 분기 8개 × `px-4 py-2` = 약 650px+. `overflow-x-auto` 처리는 되어 있으나 항목명 컬럼(좌측)이 고정되지 않아 스크롤 시 행 레이블이 사라짐. 데이터 추적 불가.

### BLOCKER-5: /chainsight/[symbol] 데스크톱 3-패널 — `hidden lg:block` CategorySidebar
**파일**: `frontend/app/stocks/[symbol]/page.tsx:1058`  
(`/stocks/[symbol]` 내 ValidationTab의 데스크톱 분기)
```tsx
<div className="w-48 flex-shrink-0 hidden lg:block">
  <CategorySidebar .../>
</div>
```
**영향**: md(768px~1023px) 범위에서 CategorySidebar가 숨겨지지만 카테고리 이동 수단이 모바일 Chip 분기(`isMobile`)에 걸리지 않아 공백. `isMobile`은 `window.innerWidth < 768`로 판단 — 768px~1023px 구간이 사각지대. 7개 카테고리를 탐색할 방법이 없음.

---

## 터치 타겟

### MAJOR-1: AlertCard — "읽음" 버튼 (36px 미만 추정)
**파일**: `frontend/components/thesis/alerts/AlertCard.tsx:57–63`
```tsx
<button
  className="flex-shrink-0 text-[10px] text-gray-500 border border-gray-700
             px-2 py-1 rounded-lg ..."
>
  읽음
</button>
```
**영향**: `px-2 py-1` = 수직 8px 패딩. 텍스트 `text-[10px]` 포함 총 높이 약 26px. Apple HIG 44pt 기준 크게 미달. 알림 읽음 처리가 모바일에서 어렵고 오터치 빈번.

### MAJOR-2: thesis/dashboard/IndicatorRow — 기간 선택 버튼 (1M/1Y/3Y/5Y)
**파일**: `frontend/components/thesis/dashboard/IndicatorRow.tsx:182`
```tsx
className={`px-2.5 py-0.5 text-[10px] rounded transition-colors ...`}
```
**영향**: `py-0.5` = 2px 패딩, `text-[10px]` — 버튼 높이 약 18~20px. 4개 기간 버튼 모두 해당. 관제실 메인 차트 기간 전환이 사실상 터치 불가.

### MAJOR-3: Header 데스크톱 Nav 링크 — 모바일 접근 불가 + `hidden md:flex`
**파일**: `frontend/components/layout/Header.tsx:42–108`
```tsx
<nav className="hidden md:flex space-x-8">
  <Link className="... px-3 py-2 text-sm font-medium">
```
**영향**: `py-2` = 8px 패딩, 텍스트 sm = 14px → 총 높이 약 30px. 단, `hidden md:flex`로 모바일에서 아예 숨겨짐. 대신 MobileNav가 Bottom Navigation 역할 — `thesis`, `market-pulse`, `screener`, `ai-analysis`, `watchlist`, `chainsight` 6개 주요 경로가 MobileNav에 없음. MobileNav는 홈/종목/뉴스/포트폴리오/내정보 5개만 제공.

### MAJOR-4: eod/SignalFilterTabs — 카운트 뱃지 (18px × 18px)
**파일**: `frontend/components/eod/SignalFilterTabs.tsx:68`
```tsx
className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[11px]"
```
**영향**: 탭 버튼 자체는 충분히 크지만, 뱃지가 탭 텍스트 위에 겹쳐 표시되어 탭 유효 터치 영역을 줄임. 18px 높이 뱃지가 터치 피드백의 혼동 유발 가능.

### MAJOR-5: thesis/AddIndicatorSheet — 지표 빈도 뱃지 (`text-[9px]`)
**파일**: `frontend/components/thesis/AddIndicatorSheet.tsx:240`
```tsx
<span className={`text-[9px] px-1 py-px rounded ${freqStyle}`}>
```
**영향**: 9px 텍스트는 일반 모바일 가독성 기준(최소 11px) 미달. 지표 선택 화면에서 빈도 레이블이 사실상 안 보임. 선택 판단 근거 정보가 소실.

### MAJOR-6: SignalDetailSheet — 닫기 버튼 `p-1.5` (약 30px)
**파일**: `frontend/components/eod/SignalDetailSheet.tsx:137`
```tsx
<button
  onClick={onClose}
  className="ml-3 p-1.5 rounded-full hover:bg-gray-100 ... flex-shrink-0"
>
```
**영향**: `p-1.5` = 6px 패딩 사방. 아이콘 크기 미확인이나 총 약 28~32px 추정. HIG 44pt 미달. Sheet를 닫는 주요 액션이라 영향 큼.

### MINOR-1: thesis/alerts/AlertCard severity 뱃지 `text-[10px]`
**파일**: `frontend/components/thesis/alerts/AlertCard.tsx:28`
```tsx
<span className="text-[10px] px-1.5 py-0.5 rounded-full ...">
```
**영향**: 클릭 불가 요소이므로 터치 타겟 문제는 없으나, 10px 텍스트는 375px 화면에서 읽기 어려움 — MINOR.

### MINOR-2: KeywordTag `sm` 사이즈 `text-[10px]`
**파일**: `frontend/components/keywords/KeywordTag.tsx:42`
```tsx
sm: 'px-2 py-0.5 text-[10px]',
```
**영향**: 키워드 뱃지 클릭 시 어렵고 가독성 낮음.

---

## 네비게이션

### MAJOR-7: MobileNav — 6개 주요 페이지 누락
**파일**: `frontend/components/layout/MobileNav.tsx:11–17`
```tsx
const navItems = [
  { name: '홈', href: '/' },
  { name: '종목', href: '/stocks' },
  { name: '뉴스', href: '/news' },
  { name: '포트폴리오', href: '/portfolio' },
  { name: '내정보', href: '/mypage' },
];
```
**영향**: Thesis Control(`/thesis`), Market Pulse(`/market-pulse`), Screener(`/screener`), Chain Sight(`/chainsight`), Watchlist(`/watchlist`), AI Analysis(`/ai-analysis`)가 모바일 Bottom Nav에 없음. 이 페이지들은 URL 직접 입력 또는 각 페이지 내 링크로만 접근 가능. 특히 Thesis Control은 주요 기능임에도 모바일 진입점 없음.

### MAJOR-8: Header 모바일 Hamburger 버튼이 `hidden` 처리됨
**파일**: `frontend/components/layout/Header.tsx:157–163`
```tsx
{/* 본 버튼은 hidden — 향후 모바일 검색 패널 등 확장 시 부활 검토 */}
<button
  className="hidden inline-flex ..."
```
**영향**: 주석에 의도적으로 숨김 처리가 명시되어 있으나, MobileNav에서 커버되지 않는 페이지들(thesis, market-pulse, screener 등)로의 모바일 진입 수단이 없음. MAJOR-7과 복합적으로 영향.

### MAJOR-9: /stocks/[symbol] 모바일 L1 탭 — `flex space-x-2`, overflow 처리 없음
**파일**: `frontend/app/stocks/[symbol]/page.tsx:383–397`
```tsx
<nav className="flex space-x-2">
  {L1_TABS.map((l1) => (
    <button className="min-h-[44px] px-5 py-2 text-sm font-medium rounded-full ...">
```
**영향**: L1 탭 3개(기본정보/뉴스/분석 및 검증) — 각 탭 텍스트가 길어 375px에서 "분석 및 검증" 버튼이 잘릴 수 있음. `overflow-x-auto`나 `flex-wrap` 없음.

### MINOR-3: /chainsight/[symbol] 모바일 헤더 닫기 버튼 `px-3 py-1 text-sm`
**파일**: `frontend/app/chainsight/[symbol]/page.tsx:180`
```tsx
<button className="px-3 py-1 text-sm border border-gray-200 rounded-lg">
  닫기
</button>
```
**영향**: `py-1` = 4px 패딩 — 높이 약 28px. 그래프 오버레이를 닫는 중요 버튼이므로 HIG 44pt 권장. MINOR.

### MINOR-4: chainsight/MobileCardList — 정렬 탭 overflow
**파일**: `frontend/components/chainsight/MobileCardList.tsx:84`
```tsx
<div className="bg-white border-b ... overflow-x-auto">
```
**영향**: overflow-x-auto 처리는 있으나 scrollbar 표시 여부 불명확. 모바일에서 스크롤 가능성이 보이지 않을 수 있음 — MINOR.

---

## 차트/그래프

### MAJOR-10: thesis/dashboard/QuarterlySparkline — 고정 높이 `h-10`, 좁은 화면 가독성
**파일**: `frontend/components/thesis/dashboard/QuarterlySparkline.tsx:33`
```tsx
<div className="relative flex items-end gap-1 h-10">
```
**영향**: 분기 데이터가 8개+ 이면 각 막대 폭이 375px ÷ 8 ≈ 46px. gap-1(4px) 적용 후 약 40px/막대 — 터치는 가능하나 툴팁 정확도 낮음. 분기 라벨(`Q1~Q4`)이 `text-[11px]`로 작아 가독성 문제. MAJOR.

### MAJOR-11: chainsight/GraphCanvas & MarketGraphCanvas — Canvas 기반 그래프, 핀치줌 미처리
**파일**: `frontend/components/chainsight/GraphCanvas.tsx` / `MarketGraphCanvas.tsx`
```tsx
// react-force-graph-2d + Canvas 렌더링
// SSR 불가 → dynamic import 필수
```
**영향**: react-force-graph-2d는 Canvas 기반 — 모바일에서 핀치줌(pinch-to-zoom) 기본 지원이 라이브러리 의존적. `/chainsight/[symbol]`은 `isMobile` 감지 후 `MobileCardList` fallback + 그래프 오버레이 분기 구현이 있어 기본 대응은 됨. 그러나 그래프 오버레이 내 노드 터치 정확도는 Canvas 픽셀 기반으로 제한적. MarketGraphCanvas(`/chainsight` 메인)는 별도 모바일 분기 없음 — MAJOR.

### MINOR-5: thesis/dashboard/IndividualMiniCharts — ResponsiveContainer 사용
**파일**: `frontend/components/thesis/dashboard/IndividualMiniCharts.tsx`
```tsx
// ResponsiveContainer 사용 확인 (grep 결과)
```
**영향**: `ResponsiveContainer` 사용으로 자동 리사이즈 처리 — 양호. MINOR 이슈 없음.

### MINOR-6: SectorHeatmap (Screener) — `ResponsiveContainer` 사용
**파일**: `frontend/components/screener/SectorHeatmap.tsx`
**영향**: `ResponsiveContainer` 확인 — 모바일 적응 됨. 다만 Heatmap 특성상 모바일에서 셀이 매우 작아져 가독성 문제. MINOR.

### MINOR-7: eod/MiniSparkline — `width={52}` 고정 폭
**파일**: `frontend/components/eod/SignalCard.tsx:188`
```tsx
<MiniSparkline data={stock.mini_chart_20d} width={52} height={20} />
```
**영향**: 고정 폭 52px SVG. 작지만 스파크라인 목적으로는 적절. 모바일에서 비율적 문제 없음 — MINOR.

---

## 페이지별 상세

### / (홈, EOD Dashboard)
- **양호**: SignalCardGrid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` — 모바일 1컬럼 처리 됨
- **양호**: SignalDetailSheet — 모바일 bottom sheet(rounded-t-2xl) + 데스크톱 side panel 분기 됨
- **양호**: SignalCard 터치 이벤트 (`onTouchStart/Move/End/Cancel`) 구현 됨
- **양호**: `pb-20 md:pb-0` MobileNav 공간 확보 됨
- MINOR: MarketSummaryBar — `flex-wrap` 처리로 양호하나 `text-2xl font-extrabold` 숫자가 375px에서 줄바꿈 유발 가능

### /thesis (가설 목록)
- **양호**: max-w-lg 단일 컬럼 — 모바일 우선 설계
- MAJOR-1: AlertCard "읽음" 버튼 소형
- MAJOR-2: IndicatorRow 기간 버튼 `py-0.5`
- MAJOR-7 영향: Bottom Nav에서 진입 불가

### /thesis/[id] (관제실 대시보드)
- **양호**: `max-w-lg mx-auto px-4 pt-4 pb-20` — 모바일 최적화 레이아웃
- MAJOR-2: 기간 선택 버튼 소형
- MAJOR-10: QuarterlySparkline h-10 고정

### /thesis/[id]/indicators (지표 설정)
- MAJOR-5: AddIndicatorSheet `text-[9px]` 빈도 뱃지

### /stocks/[symbol] (종목 상세)
- BLOCKER-3: L2 탭 가로 overflow 미처리
- BLOCKER-4: 재무제표 테이블 고정 컬럼 미처리
- BLOCKER-5: Validation 카테고리 탐색 768-1023px 사각지대
- MAJOR-9: L1 탭 `flex space-x-2` overflow 미처리

### /portfolio (포트폴리오)
- BLOCKER-1: 12컬럼 테이블, 모바일 카드 없음

### /screener (스크리너)
- BLOCKER-2: ScreenerTable 기본값 table 모드, 자동 전환 없음
- **양호**: MobileStockCard 컴포넌트 존재 — 수동 전환 가능
- **양호**: ScreenerDashboard `grid-cols-1 lg:grid-cols-2` 처리 됨

### /chainsight/[symbol] (Chain Sight 워크스페이스)
- **양호**: isMobile 감지 후 MobileCardList fallback 구현됨
- MAJOR-11: Canvas 그래프 핀치줌 제한적
- MINOR-3: 그래프 오버레이 닫기 버튼 소형

### /chainsight (Chain Sight 마켓뷰)
- MAJOR-11: MarketGraphCanvas 모바일 분기 없음

### /news (뉴스)
- **양호**: 카드 기반 레이아웃, 반응형 처리 됨
- **양호**: `overflow-x-auto scrollbar-hide` 소스/시간 탭 처리

### /market-pulse (Market Pulse)
- MAJOR-7 영향: Bottom Nav에서 진입 불가
- 내부 레이아웃 반응형 처리는 `sm:/md:/lg:` 브레이크포인트 확인됨

### /watchlist (Watchlist)
- `overflow-x-auto` 테이블 처리 됨 (`app/watchlist/page.tsx:294`)
- MAJOR-7 영향: Bottom Nav에서 진입 불가

---

## 체크리스트 요약

| 영역 | 상태 |
|------|------|
| MobileNav Bottom Navigation | 주요 페이지 6개 누락 |
| SignalCard / SignalDetailSheet | 모바일 대응 양호 |
| Thesis Dashboard | 모바일 우선 설계 양호, 버튼 소형 이슈 |
| Portfolio Table | 12컬럼 — 모바일 카드 없음 |
| Screener Table | 수동 전환 필요, 자동 전환 없음 |
| stocks/[symbol] L2 탭 | overflow 미처리 |
| Chain Sight 워크스페이스 | MobileCardList fallback 존재 |
| Chain Sight 마켓뷰 | 모바일 분기 없음 |
| 재무제표 테이블 | 좌측 고정 컬럼 없음 |
| Recharts ResponsiveContainer | 15개 파일에서 사용 — 대부분 양호 |
| 가상화(react-window 등) | 미사용 — 긴 목록 성능 잠재 이슈 |
