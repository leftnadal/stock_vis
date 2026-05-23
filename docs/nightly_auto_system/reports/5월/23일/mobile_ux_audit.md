# 모바일 UX 감사 보고서

생성일: 2026-05-23
대상: Stock-Vis Frontend (Next.js 16, TypeScript)
기준 뷰포트: iPhone 375x812
총 점검 파일 수: 289 (tsx 기준, node_modules 제외 실 컴포넌트 ~120개)

---

## 요약

- BLOCKER: 6건
- MAJOR: 14건
- MINOR: 18건
- 총 점검 파일 수: 120 (node_modules 제외)

---

## 1. 반응형 누락

### 1-1. 고정 폭 컴포넌트

**[BLOCKER] ScreenerTable — 테이블 11컬럼 고정 폭**
- 파일: `frontend/components/strategy/ScreenerTable.tsx:128-129`
- `overflow-x-auto` 래퍼는 있으나, 테이블이 375px에서 최소 600px+ 이상 차지.
  11개 컬럼(종목/거래소/섹터/가격/변동률/시가총액/거래량/배당률/베타/유형/AI키워드) 전부 표시. 모바일에서 핵심 버튼(RAG 바구니 추가) 가로 스크롤 없이 보이지 않음.
- `frontend/components/strategy/ScreenerTable.tsx:209`: `max-w-[180px]`
- `frontend/components/strategy/ScreenerTable.tsx:224`: `max-w-[120px]`
- 심각도 근거: 스크리너의 핵심 액션(바구니 추가 버튼)이 마지막 컬럼에 배치되어 375px에서 가로 스크롤 없이 도달 불가.

**[MAJOR] MarketGraphCanvas — 그래프 고정 높이 560px**
- 파일: `frontend/components/chainsight/MarketGraphCanvas.tsx:603`, `:712`, `:760`
- `h-[560px]` 고정. 375px iPhone에서 세로 비율 과다. 상하 UI와 겹칠 위험.
- 단, Chain Sight 마켓 뷰는 `/chainsight` 페이지에서 별도 모바일 분기가 없어 직접 노출.

**[MINOR] SignalDetailSheet — 데스크톱 드로어 폭 420px 고정**
- 파일: `frontend/components/eod/SignalDetailSheet.tsx:97`
- `md:w-[420px]` — md 이상에서만 사이드 드로어, 모바일은 `rounded-t-2xl`로 바텀시트 전환. 설계는 적절하나 `max-h-[90vh]`이 375px 짧은 컨텐츠에서는 과도한 여백.

**[MINOR] InvestingHeader — 최대 폭 1400px 고정**
- 파일: `frontend/components/layout/InvestingHeader.tsx:32`, `:55`, `:99`
- `max-w-[1400px]` — 모바일에서 자동 전체폭으로 동작하므로 직접 overflow는 없음. 다만 `px-4` 패딩만 적용, 컨텐츠 밀도가 모바일 기준 불명확.

---

### 1-2. 반응형 브레이크포인트 미적용 컴포넌트

**[MAJOR] RealtimePriceDisplay — grid-cols-2 고정 (반응형 없음)**
- 파일: `frontend/components/RealtimePriceDisplay.tsx:64`
- `grid grid-cols-2 gap-4 text-sm` — sm:/md: 변형 없음. 375px에서 두 컬럼 각 약 170px. 숫자 데이터가 길면 잘림.

**[MAJOR] PortfolioSummary — grid-cols-2 고정 (반응형 없음)**
- 파일: `frontend/components/portfolio/PortfolioSummary.tsx:64`
- `grid grid-cols-2 gap-4 pt-4 border-t` — 반응형 없음. 포트폴리오 요약 핵심 지표가 375px에서 여백 없이 쪼개짐.

**[MAJOR] MonitoringDashboard — grid-cols-3 고정 (반응형 없음)**
- 파일: `frontend/components/rag/MonitoringDashboard.tsx:131`
- `grid grid-cols-3 gap-3` — 반응형 없음. 375px에서 3컬럼 각 약 115px. 금액 표기(`$0.0000` 형태)가 overflow.

**[MAJOR] MonitoringDashboard — grid-cols-2 고정 (반응형 없음)**
- 파일: `frontend/components/rag/MonitoringDashboard.tsx:215`, `:261`
- `grid grid-cols-2 gap-2`, `grid grid-cols-3 gap-2` 반응형 없음. AI 분석 페이지 내 팝업 패널.

**[MINOR] rag/TokenUsageDisplay — grid-cols-2 고정**
- 파일: `frontend/components/rag/TokenUsageDisplay.tsx:143`, `:175`
- `grid grid-cols-2 gap-3` — 모바일 팝업 패널에서 반응형 없음.

**[MINOR] admin/news/MLModelCard — grid-cols-3, grid-cols-2 고정**
- 파일: `frontend/components/admin/news/MLModelCard.tsx:110`, `:116`
- 어드민 페이지지만 모바일에서 사용 시 깨짐.

**[MINOR] screener/MarketBreadthCard — grid-cols-3 고정**
- 파일: `frontend/components/screener/MarketBreadthCard.tsx:107`
- `grid grid-cols-3 gap-2 mb-4 p-3` — 반응형 없음.

**[MINOR] YieldCurveChart — grid-cols-3 고정**
- 파일: `frontend/components/macro/YieldCurveChart.tsx:147`
- `grid grid-cols-3 gap-4 mt-4 pt-4` — Yield Curve 하단 스프레드 정보 3컬럼 고정.

**[MINOR] admin/news/LLMUsageSummary — grid-cols-2 고정**
- 파일: `frontend/components/admin/news/LLMUsageSummary.tsx:51`, `:82`
- 어드민 전용이나 375px에서 overflow 위험.

**[MINOR] thesis/skeleton/ThesisSkeleton — grid-cols-3 고정**
- 파일: `frontend/components/thesis/skeleton/ThesisSkeleton.tsx:68`
- 스켈레톤 UI에서 `grid grid-cols-3 gap-3` 반응형 없음.

---

### 1-3. 테이블 / 차트 스크롤 처리

**[BLOCKER] stocks/[symbol] 재무제표 테이블 — 분기 컬럼 수 무제한**
- 파일: `frontend/app/stocks/[symbol]/page.tsx:843`
- `overflow-x-auto` 래퍼 있음. 그러나 최대 20개 분기 컬럼이 생길 수 있어 모바일에서 테이블 폭 3000px+ 가능. 스크롤은 작동하나 첫 번째 컬럼(항목명) 고정(sticky) 처리 없어 어느 컬럼 데이터인지 파악 불가.

**[MAJOR] PortfolioTable — grid-cols-6 (md 이상만)**
- 파일: `frontend/components/portfolio/PortfolioTable.tsx:210`
- `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4` — 기본 2컬럼은 적절. 단 그 위 `overflow-x-auto`로 감싼 테이블과 그리드 혼합 사용으로 레이아웃 예측 어려움.

---

## 2. 터치 타겟

Apple HIG 기준 최소 44x44pt. 아래는 44pt 미만 클릭 요소로 확인된 것들.

### 2-1. 아이콘만 있는 초소형 버튼

**[BLOCKER] validation/PeerContextBar — peer 목록 접기/펼치기 버튼**
- 파일: `frontend/components/validation/PeerContextBar.tsx:118-124`
- `flex items-center gap-1 text-xs text-blue-600 hover:underline` — 패딩 없음, 텍스트 크기 xs. 실제 터치 영역 약 20x18px.
- 비교 대상: 같은 컴포넌트 프리셋 버튼(`:40`)은 `min-h-[44px]` 적용됨. 접기/펼치기만 누락.

**[BLOCKER] validation/LeaderComparisonSection — 상세 보기 버튼**
- 파일: `frontend/components/validation/LeaderComparisonSection.tsx:73`
- `w-3 h-3` ChevronDown/Up 아이콘 단독 사용. 래퍼 버튼에 패딩 없음.

**[MAJOR] market-pulse/MoverCard — Info 아이콘 버튼 (5개)**
- 파일: `frontend/components/market-pulse/MoverCard.tsx:137`, `:149`, `:161`, `:176`, `:188`
- `<Info className="w-3 h-3">` — 12x12px 아이콘만. 래퍼에 패딩 없어 44pt 미달.
- 동일 이슈: `frontend/components/market-pulse/MoverCardWithBatchKeywords.tsx:144`, `:156`, `:168`, `:183`, `:195`

**[MAJOR] chainsight/PathCard — RefreshCw, Maximize2 아이콘 버튼**
- 파일: `frontend/components/chainsight/PathCard.tsx:84`, `:92`
- `w-3 h-3` 아이콘. 패딩 없는 상태. Chain Sight 경로 카드 내 기능 버튼.

**[MAJOR] news/AINewsBriefingCard — ChevronUp/Down 토글 버튼**
- 파일: `frontend/components/news/AINewsBriefingCard.tsx:111`, `:113`
- `w-3 h-3` 아이콘 단독. 뉴스 섹션 접기/펼치기에 터치 영역 부족.

**[MAJOR] eod/SignalFilterTabs — 필터 버튼 높이 미보장**
- 파일: `frontend/components/eod/SignalFilterTabs.tsx:44-77`
- `px-3 py-1.5` — 높이 약 36px. 44pt 기준 미달. 시그널 카테고리 전환 핵심 인터랙션.

**[MAJOR] chainsight/MobileCardList — 카테고리 탭 버튼**
- 파일: `frontend/components/chainsight/MobileCardList.tsx:86-108`
- `px-3 py-1.5 text-sm rounded-full` — 높이 약 36px. 44pt 미달. 모바일 전용 컴포넌트임에도 기준 미충족.

**[MINOR] eod/SignalDetailSheet — X(닫기) 버튼**
- 파일: `frontend/components/eod/SignalDetailSheet.tsx:136-139`
- `p-1.5 rounded-full` — 패딩 6px. 아이콘 h-4 w-4(16px) + 패딩 = 28px. 44pt 미달.

**[MINOR] market-pulse-v2/CardDrawer — 닫기 버튼**
- 파일: `frontend/app/market-pulse-v2/components/CardDrawer.tsx:24`
- `px-2 py-1 text-sm` — 텍스트 버튼이지만 높이 약 32px. 44pt 미달.

**[MINOR] Header — 햄버거 메뉴 버튼 (숨겨진 상태)**
- 파일: `frontend/components/layout/Header.tsx:157-163`
- `hidden inline-flex ... min-h-[44px] min-w-[44px]` — 현재 `hidden`으로 비표시. MobileNav가 단일 소스이나, 미래 복원 시 터치 타겟 기준은 충족된 상태(긍정적 케이스).

### 2-2. 소형 폰트 클릭 요소

**[MAJOR] thesis/dashboard/IndicatorRow — 날짜 라벨 (11px)**
- 파일: `frontend/components/thesis/dashboard/IndicatorRow.tsx:95`
- `text-[11px] text-gray-500` — 11px. 버튼 내부 라벨이므로 직접 클릭 요소는 아니나, 가독성 심각 저하.

**[MINOR] chainsight/MobileCardList — 태그 배지 (10px)**
- 파일: `frontend/components/chainsight/MobileCardList.tsx:149`, `:154`, `:158`
- `text-[10px] px-2 py-0.5` — 10px. 375px 모바일에서 가독성 최악.

**[MINOR] QuarterlySparkline — 분기 라벨 및 툴팁 (11px, 10px)**
- 파일: `frontend/components/thesis/dashboard/QuarterlySparkline.tsx:57`, `:62`
- `text-[11px]`, `text-[10px]` — 스파크라인 하단 Q1/Q2/Q3/Q4 라벨과 호버 툴팁.

**[MINOR] market-pulse-v2/page.tsx — footer 텍스트 (10px)**
- 파일: `frontend/app/market-pulse-v2/page.tsx:77`
- `text-[10px] text-slate-400` — 디버그성 메타 정보이나 375px에서 읽기 불가.

---

## 3. 네비게이션

### 3-1. 헤더 / MobileNav

**[MAJOR] Header — 모바일 햄버거 완전 비활성화**
- 파일: `frontend/components/layout/Header.tsx:155-163`
- `hidden` 클래스로 완전 숨김. 주석에 "MobileNav가 모바일 네비 단일 소스"라고 명시.
- **문제점**: MobileNav에는 5개 링크(홈/종목/뉴스/포트폴리오/내정보)만 있음. 헤더 데스크톱 nav에는 8개 항목(대시보드/포트폴리오/ChainSight/Thesis/MarketPulse/뉴스/스크리너/마이페이지). **Chain Sight, Thesis Control, Market Pulse, 스크리너가 모바일 바텀 네비에 없어 접근성 단절**.
- 직접 URL 입력 또는 내부 링크를 통한 우회로만 접근 가능.

**[BLOCKER] MobileNav — Thesis Control / Chain Sight / Market Pulse / 스크리너 진입점 없음**
- 파일: `frontend/components/layout/MobileNav.tsx:11-17`
- navItems: `['/', '/stocks', '/news', '/portfolio', '/mypage']` — 핵심 기능 4개 누락.
- Thesis Control, Market Pulse, Chain Sight는 이 프로젝트의 주요 기능. 모바일에서 바로 접근 불가.

### 3-2. Bottom Navigation

**[MINOR] MobileNav — pb-20 하단 여백 미적용 페이지 존재**
- 파일: `frontend/app/page.tsx:71`
- `pb-20 md:pb-0` — 홈 페이지는 적용됨. 그러나 `/thesis`, `/chainsight`, `/screener`, `/ai-analysis` 등 다른 페이지의 컨텐츠가 MobileNav(h-16, 64px)에 가려질 가능성 있음.
- `frontend/app/ai-analysis/page.tsx:234`: `relative flex h-screen flex-col` — overflow:hidden으로 MobileNav와 겹침 없으나, 바텀 고정 여백 없어 chatInput이 네비 영역과 충돌 위험.

### 3-3. Virtualization

**[MAJOR] 긴 리스트에 Virtualization 미적용**
- `package.json` 확인 결과: `react-window`, `react-virtual`, `@tanstack/virtual` 등 가상화 라이브러리 미설치.
- 영향 범위:
  - `frontend/components/news/NewsList.tsx` — 뉴스 목록 전체 DOM 렌더링
  - `frontend/components/news/NewsGrid.tsx` — 뉴스 그리드 전체 렌더링
  - `frontend/components/strategy/ScreenerTable.tsx` — 스크리너 결과 전체 테이블
  - `frontend/components/watchlist/WatchlistItemRow.tsx` — 워치리스트 전체 렌더링
- 375px iPhone에서 수백 개 DOM 노드가 메모리에 상주, 스크롤 성능 저하.

### 3-4. 드로어 / 모달 모바일 대응

**[MAJOR] ai-analysis 모니터링/토큰 팝업 — 절대 위치 고정**
- 파일: `frontend/app/ai-analysis/page.tsx:294-300`, `:303-313`
- `absolute left-4 top-20 z-50 w-96` (w-96 = 384px) — 375px 화면에서 패널이 화면 우측으로 overflow. 닫기 버튼 접근 불가 위험.
- `absolute right-4 top-20 z-50 w-80` (w-80 = 320px) — 375px에서 전체폭의 85%를 차지하며 좌측 콘텐츠를 가림.

**[MINOR] market-pulse-v2/CardDrawer — 모바일 바텀시트 구현 존재하나 높이 85vh**
- 파일: `frontend/app/market-pulse-v2/components/CardDrawer.tsx:21`
- `max-h-[85vh]` — 컨텐츠(RegimeDetail, BreadthDetail 등)에 차트가 포함될 때 스크롤 영역 부족 위험.

---

## 4. 차트/그래프

### 4-1. ResponsiveContainer 사용 현황

전체 Recharts 차트 컴포넌트 통계:
- ResponsiveContainer 적용 파일: 13개 (validation/MetricBarChart, stock/StockChart, charts/StockPriceChart, admin/news/MLTrendChart, thesis/dashboard/IndicatorRow, thesis/dashboard/IndividualMiniCharts, portfolio/PortfolioChart, screener/SectorHeatmap, macro/YieldCurveChart, news/SentimentChart, market-pulse-v2/details/ 4개)
- 모든 Recharts 사용처에 ResponsiveContainer 적용됨 (100%)
- 긍정적 평가: Recharts 기반 차트는 모두 반응형 처리.

**[MINOR] PortfolioChart — h-[400px] 고정 높이 안에 ResponsiveContainer**
- 파일: `frontend/components/portfolio/PortfolioChart.tsx:77`, `:97`
- `ResponsiveContainer width="100%" height={400}` — 400px 고정 높이. 375px 화면에서 차트가 화면 절반 이상 차지하나 가독성은 유지됨.

### 4-2. MiniSparkline — 고정 크기 SVG

**[MINOR] eod/MiniSparkline — width 80, height 24 기본값**
- 파일: `frontend/components/eod/MiniSparkline.tsx:9`
- `width = 80, height = 24` 기본값. SVG viewBox 기반이나 컨테이너 반응형 미적용. 375px 리스트 내에서 부모 flex로 자동 조정되지 않으면 고정 80px 노출.

### 4-3. QuarterlySparkline — 모바일 가독성

**[MINOR] thesis/dashboard/QuarterlySparkline — 최소 높이 h-10 (40px)**
- 파일: `frontend/components/thesis/dashboard/QuarterlySparkline.tsx:33`
- `relative flex items-end gap-1 h-10` — h-10 = 40px. 분기별 바 차트가 40px 안에 표시됨. 375px에서 가독성 낮음.
- 분기 라벨 `text-[11px]` (11px)로 추가 가독성 저하.

### 4-4. react-force-graph-2d (Chain Sight 그래프)

**[MAJOR] Chain Sight 그래프 — 모바일 핀치줌 미구현**
- 파일: `frontend/app/chainsight/[symbol]/page.tsx:173-200`
- 모바일에서 그래프 오버레이 모드로 전환되나 (긍정적), `ForceGraph2D` 자체 터치 이벤트에 핀치줌/팬 가속 지원이 라이브러리 기본 설정에 의존.
- `frontend/components/chainsight/MarketGraphCanvas.tsx:487`: `window.matchMedia('(pointer: coarse)')` 체크하여 터치 디바이스 감지 후 `isMobile` 분기 처리됨 (부분 대응).
- 그래프 오버레이 헤더 닫기 버튼: `px-3 py-1 text-sm border` — 높이 약 32px, 44pt 미달.

**[BLOCKER] chainsight/[symbol] — 모바일 그래프 오버레이 닫기 버튼 터치 타겟 미달**
- 파일: `frontend/app/chainsight/[symbol]/page.tsx:178-183`
- `px-3 py-1 text-sm border border-gray-200 rounded-lg` — 36px 이하. 그래프 전체화면에서 탈출하는 유일한 버튼이 44pt 미달.

---

## 5. 페이지별 상세

### / (홈 — EOD Dashboard)

**[MINOR]** `frontend/app/page.tsx:71`
- `pb-20 md:pb-0` 적용으로 MobileNav 가리기 방지. 양호.
- SignalFilterTabs 버튼이 `py-1.5`로 44pt 미달 (MAJOR 중복).
- MiniSparkline SVG 고정 크기 (MINOR 중복).

### /thesis (Thesis Control)

**[MINOR]** `frontend/app/thesis/[thesisId]/page.tsx:62`
- `max-w-lg mx-auto px-4 pt-4 pb-20` — 모바일 최적화 의도 명확. 양호.
- IndicatorRow 내 `text-[11px]` 날짜 라벨 (MAJOR 중복).
- QuarterlySparkline h-10 가독성 (MINOR 중복).

**[MAJOR]** `frontend/components/thesis/dashboard/IndicatorRow.tsx:115`
- `min-w-[120px]` — 현재값 영역 최소 폭 고정. 375px 화면에서 좁은 공간에 강제 배치.

**[MAJOR]** `frontend/components/thesis/dashboard/IndicatorRow.tsx:132`
- `max-w-[100px]` — 스파크라인 영역 100px 고정. 반응형 미적용.

### /thesis/new (Thesis Builder)

**[MINOR]** `frontend/app/thesis/new/page.tsx:672`, `:715`
- `grid grid-cols-1 gap-2 sm:grid-cols-2` — sm: 브레이크포인트 적용. 375px에서 1컬럼 정상.
- 양호한 반응형 처리.

### /validation (1차 검증 — stocks/[symbol] 내 탭)

**[BLOCKER]** `frontend/components/validation/PeerContextBar.tsx:118-124`
- peer 목록 접기/펼치기 버튼 터치 타겟 없음 (위 2-1 반복).

**[MINOR]** `frontend/components/validation/CategorySidebar.tsx:44`
- `sticky top-24 space-y-1` — 사이드바가 모바일에서도 렌더링될 경우 레이아웃 충돌. 실제로는 `frontend/app/stocks/[symbol]/page.tsx:1058`에서 `hidden lg:block`으로 숨김. 양호.

### /chainsight (Chain Sight)

**[BLOCKER]** MobileNav에서 진입점 없음 (섹션 3-1 반복).

**[BLOCKER]** 모바일 그래프 오버레이 닫기 버튼 44pt 미달 (섹션 4-4 반복).

**[MAJOR]** `frontend/components/chainsight/MarketGraphCanvas.tsx:712`
- `/chainsight` (마켓 뷰) 페이지에서 `h-[560px]` 고정. 모바일 전환 분기 없음.
- ChainSight 마켓 뷰는 `/chainsight/[symbol]`와 달리 isMobile 분기 로직 부재. 560px 그래프가 375px에서 전체 화면 차지.

**[MINOR]** `frontend/components/chainsight/MobileCardList.tsx:149`, `:154`, `:158`
- 태그 배지 10px 텍스트. 모바일 전용 컴포넌트에서 가독성 저하.

### /screener (스크리너)

**[BLOCKER]** MobileNav에서 진입점 없음.

**[BLOCKER]** ScreenerTable 11컬럼 — 마지막 액션 버튼 도달 불가 (섹션 1-1 반복).

**[MAJOR]** `frontend/app/screener/page.tsx:465`
- `h-[400px] flex items-center justify-center` — 스크리너 내 빈 상태 영역 400px 고정.

**[MINOR]** `frontend/components/screener/SectorHeatmap.tsx:216`
- `ResponsiveContainer width="100%" height={400}` — Treemap 400px. 375px에서 세로 비율 큼.

### /ai-analysis (RAG 분석)

**[MAJOR]** `frontend/app/ai-analysis/page.tsx:294`, `:304`
- `w-96`(384px), `w-80`(320px) 절대위치 팝업 — 375px에서 overflow (섹션 3-4 반복).

**[MINOR]** `frontend/app/ai-analysis/page.tsx:234`
- `h-screen flex flex-col` — MobileNav(h-16, 64px) 영역 미고려. 채팅 입력창이 MobileNav에 가려질 가능성.

### /market-pulse (Market Pulse v1)

**[MAJOR]** `frontend/app/market-pulse/page.tsx:187`
- `grid grid-cols-1 lg:grid-cols-3 gap-6` — 기본 1컬럼, 적절함.
- 내부 Fear & Greed Gauge: `w-48 h-24` (`frontend/components/macro/FearGreedGauge.tsx:54`) — 192x96px 고정 SVG. 375px 중앙 배치로 시각적으로는 문제없음.

**[MAJOR]** `frontend/components/market-pulse/MoverCard.tsx:137~188`
- Info 아이콘 w-3 h-3 터치 타겟 5건 미달 (섹션 2-1 반복).

### /market-pulse-v2 (Market Pulse v2)

**[MINOR]** 카드 레이아웃 `sm:grid-cols-2` 적용 — 375px에서 1컬럼. 양호.
- CardDrawer 바텀시트 구현 양호.
- `text-[10px]` footer 가독성 저하 (MINOR 반복).

### /news (뉴스)

**[MAJOR]** Virtualization 미적용 (섹션 3-3 반복).

**[MINOR]** `frontend/app/news/page.tsx:210`
- `grid grid-cols-1 lg:grid-cols-3 gap-4` — 기본 1컬럼. 적절.

**[MINOR]** `frontend/components/news/AINewsBriefingCard.tsx:111`, `:113`
- ChevronUp/Down w-3 h-3 터치 타겟 미달 (섹션 2-1 반복).

### /macro (Market Pulse 내 거시경제)

**[MINOR]** `frontend/components/macro/EconomicIndicators.tsx:42`
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4` — 기본 1컬럼. 적절.

**[MINOR]** `frontend/components/macro/GlobalMarketsCard.tsx:59`
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6` — 기본 1컬럼. 적절.

### /watchlist (워치리스트)

**[MAJOR]** Virtualization 미적용. 워치리스트 항목 무제한 DOM 렌더링.

**[MINOR]** `frontend/app/watchlist/page.tsx:207`
- `grid grid-cols-1 lg:grid-cols-3 gap-6` — 기본 1컬럼. 적절.

### /portfolio (포트폴리오)

**[MAJOR]** PortfolioSummary grid-cols-2 고정 (섹션 1-2 반복).

**[MINOR]** `frontend/components/portfolio/RealtimePortfolio.tsx:53`
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4` — 기본 1컬럼. 적절.

### /dashboard (구 대시보드)

**[MINOR]** `frontend/app/dashboard/page.tsx:117`, `:123`, `:129`
- `sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6` — sm 이하(375px)에서 기본 블록 레이아웃. 적절.

### /stocks/[symbol] (종목 상세)

**[BLOCKER]** 재무제표 테이블 sticky 컬럼 없음 (섹션 1-3 반복).

**[MAJOR]** L1/L2 탭 — `frontend/app/stocks/[symbol]/page.tsx:1030`
- `flex gap-2 overflow-x-auto pb-3 scrollbar-hide` — L2 탭이 `overflow-x-auto`로 스크롤 처리됨. 적절하나 탭 버튼 높이 확인 필요.

---

## 6. 우선 조치 권고 (Top 5)

### Priority 1 — MobileNav에 핵심 기능 진입점 추가 [BLOCKER]
**파일**: `frontend/components/layout/MobileNav.tsx`
- 현재 5개 탭(홈/종목/뉴스/포트폴리오/내정보)에서 Chain Sight, Thesis Control, Market Pulse, 스크리너가 모바일에서 진입 불가.
- 권고: 탭을 재구성하거나 "더보기" 탭을 추가해 누락된 핵심 기능에 접근 가능하게 할 것. 예시: `홈 / 시장 / 분석 / 뉴스 / 더보기` 구조로 재편.

### Priority 2 — ai-analysis 팝업 패널 375px 대응 [BLOCKER→MAJOR]
**파일**: `frontend/app/ai-analysis/page.tsx:294`, `:304`
- `w-96`(384px) MonitoringDashboard와 `w-80`(320px) TokenUsageDisplay가 절대위치로 375px 화면 overflow.
- 권고: `w-full max-w-[320px]` 또는 바텀시트 패턴으로 전환. 모바일에서는 `fixed bottom-0 left-0 right-0` 슬라이드업 방식 적용.

### Priority 3 — ScreenerTable 모바일 뷰 분리 [BLOCKER]
**파일**: `frontend/components/strategy/ScreenerTable.tsx`
- 11컬럼 테이블은 375px에서 핵심 액션(바구니 추가)이 가로 스크롤 없이 도달 불가.
- 권고: `MobileStockCard.tsx` 컴포넌트가 이미 존재(`frontend/components/screener/MobileStockCard.tsx`). 스크리너 페이지에서 이미 모바일 분기 로직이 일부 구현된 상태(`frontend/app/screener/page.tsx`)이므로, ScreenerTable 직접 사용처에도 동일 분기 적용.

### Priority 4 — SignalFilterTabs / 소형 Info 아이콘 터치 타겟 보강 [MAJOR]
**파일**: `frontend/components/eod/SignalFilterTabs.tsx`, `frontend/components/market-pulse/MoverCard.tsx`
- EOD 홈 화면 SignalFilterTabs `py-1.5`를 `py-2.5`(44px 달성)로 상향.
- MoverCard Info 아이콘에 `p-2 min-h-[44px] min-w-[44px]` 래퍼 적용. 또는 터치 영역 확장 위해 `::before` 가상 요소로 44px 확장.

### Priority 5 — 재무제표 테이블 첫 컬럼 sticky 처리 [BLOCKER]
**파일**: `frontend/app/stocks/[symbol]/page.tsx:843-886`
- 다분기 재무제표 테이블에서 가로 스크롤 시 항목명 컬럼이 사라짐.
- 권고: `<th>` 및 첫 번째 `<td>`에 `sticky left-0 bg-white dark:bg-gray-800 z-10` 추가.

---

## 부록 A — 브레이크포인트 사용 현황 요약

| 파일 유형 | 브레이크포인트 적용 | 미적용 |
|----------|-----------------|--------|
| page.tsx (24개) | 18개 | 6개 (chainsight 하위, ai-analysis, admin) |
| components/ (120개) | 65개 | 55개 |
| 레이아웃 컴포넌트 | Header, MobileNav 적용 | InvestingHeader 부분 미적용 |

가장 브레이크포인트가 잘 적용된 영역: `components/screener/`, `components/macro/`, `components/news/` (lg:/md: 반응형 다수 적용)

가장 취약한 영역: `components/rag/` (MonitoringDashboard, TokenUsageDisplay — 3컬럼 고정), `components/market-pulse/MoverCard.tsx` (Info 아이콘 반복 패턴), `components/chainsight/MobileCardList.tsx` (모바일 전용이면서 터치 타겟 미충족)

---

## 부록 B — 가상화 라이브러리 도입 평가

현재 `package.json`에 가상화 라이브러리 미포함. 뉴스 목록, 스크리너 결과, 워치리스트가 무제한 DOM을 마운트함.

- 권고 라이브러리: `@tanstack/react-virtual` (TanStack Query와 동일 생태계)
- 적용 우선순위: NewsGrid > ScreenerTable > WatchlistItemRow
- 예상 효과: 100+ 항목 리스트에서 375px 디바이스 프레임 드롭 방지

---

_보고서 생성: @frontend agent, 2026-05-23_
