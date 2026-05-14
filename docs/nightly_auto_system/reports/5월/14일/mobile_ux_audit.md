# 모바일 UX 감사 보고서

- 감사 일시: 2026-05-14
- 대상: `frontend/` 전체 (192 components / 24 pages)
- 기준: 모바일 viewport 375×667 (iPhone SE/13 mini), Apple HIG 44×44pt, Material 48×48dp
- 방식: 정적 코드 감사 (런타임 측정 없음). overflow 발생 여부는 실제 텍스트 길이와 결합되는 가정치임.
- 범위: 코드만. 디자인 의도/디자인 토큰 통일 여부는 별도 감사 (`design_system_audit.md` 등).

---

## 요약 (심각도별 이슈 수)

| 심각도 | 정의 | 건수 |
|--------|------|------|
| BLOCKER | 모바일에서 화면 자체가 깨지거나 핵심 기능 사용 불가 | **5** |
| MAJOR | 사용 가능하나 터치 실패율 높음 / 가독성 심각 저하 / 핵심 정보 누락 | **11** |
| MINOR | 데스크톱 대비 폴리시 부족, 사용 가능 | **9** |

**한눈에 보는 결론**
- 페이지 레벨에서는 모바일 우선 설계가 상당 부분 정착되어 있다 (`MobileNav` bottom-tab, chainsight `isMobile` 분기, screener 카드 뷰 강제, 가설 빌더 모바일 채팅 UI 등).
- 다만 **테이블 컴포넌트(`PortfolioTable`, `ScreenerTable`)와 thesis 대시보드 `IndicatorRow`가 모바일에서 가장 약한 고리**다.
- 터치 타겟은 일관성이 부족하다. `MobileNav`/`Header`는 명시적으로 `min-h-[44px]`을 박았지만, 내부 위젯(차트 토글, `HelpCircle`, peer 칩, 분기 막대)에서 14~24px 수준의 작은 터치 표적이 산재한다.
- 차트는 전부 `ResponsiveContainer`를 쓰지만 폰트 크기 9~11px이 모바일에서 가독성을 끌어내린다.
- **Virtualization은 어디에도 적용되어 있지 않음** (`react-window`/`react-virtual` 0건). 긴 리스트(news 100개, screener 페이지당 50개, validation peer/metric)의 모바일 스크롤 성능이 잠재 리스크.

---

## 반응형 누락

### 1. PortfolioTable — 12열 가로 스크롤 의존 (BLOCKER)
- **위치**: `frontend/components/portfolio/PortfolioTable.tsx:259`
- **현상**: `overflow-x-auto` + 12개 컬럼 (`종목/보유수량/평균매수가/현재가/전일대비/평가금액/손익/수익률/목표가/손절가/비중/관리`). `px-6 py-3`로 컬럼당 최소 폭이 매우 큼.
- **모바일 영향**: 375px viewport에서 한 화면에 종목명+가격 두 개 정도만 보이고 나머지는 가로 스크롤 필수. "전일대비/손익/수익률" 같은 의사결정용 컬럼이 헤더만 보고 가서야 데이터 도달.
- **대안 존재 여부**: `app/portfolio/page.tsx:228`에서 `viewMode='grid'`일 때 `PortfolioStockCard`를 사용하지만 **`grid` 와 `table` 토글 버튼이 데스크톱/모바일 동일하게 노출되어 초기값이 그대로면 BLOCKER**. 카드 뷰는 `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`로 모바일 대응 정상.
- **권장**: 모바일 viewport에서 `viewMode` 강제 `grid`, 또는 테이블 12열 → 핵심 5열(`종목/현재가/손익률/평가금액/액션`) 축약.

### 2. PortfolioTable 요약 카드 (MAJOR)
- **위치**: `frontend/components/portfolio/PortfolioTable.tsx:210` (`grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4`)
- **현상**: 모바일에서 `grid-cols-2`로 6개 항목을 3행에 표시. `text-2xl font-bold` 금액이 컬럼 폭(약 165px)을 넘는 케이스 발생 가능. "총 평가금액 $1,234,567.89" 같은 7자리 이상에서 줄바꿈/잘림.
- **권장**: `grid-cols-2`에서는 단위 자동 단축(`$1.23M`)을 강제.

### 3. ScreenerTable — 11열 + max-w 잘림 (BLOCKER)
- **위치**: `frontend/components/strategy/ScreenerTable.tsx:128`
- **현상**: `overflow-x-auto`로 11열 (종목/거래소/섹터/가격/변동률/시가총액/거래량/배당률/베타/유형/AI키워드 + 옵션 액션). 셀 내부에 `max-w-[180px]`, `max-w-[120px]`, `max-w-[200px]` 하드코딩.
- **모바일 영향**: 카드 뷰 토글(`viewMode='card'`)이 `app/screener/page.tsx:752`에서 **`hidden sm:flex`**로 데스크톱 전용. 모바일은 `sm:hidden`으로 강제 카드 뷰(`page.tsx:854`)가 적용되어 실제로는 BLOCKER → MAJOR로 격하. 단, `MAX_PRESETS=3` 등 코드 변경 시 토글 노출 분기 실수하면 즉시 회귀 위험.
- **참고**: screener는 페이지 레벨에서 모바일 카드 뷰 강제가 잘 되어 있어, 컴포넌트 자체의 max-w-[NNpx]는 데스크톱 뷰 잘림 이슈에 가깝다.

### 4. Header — 데스크톱 nav가 7개 링크 가로 배치 (MINOR)
- **위치**: `frontend/components/layout/Header.tsx:42-109`
- **현상**: `hidden md:flex`로 데스크톱 전용. 모바일에서는 안 보이고 `MobileNav` bottom tab이 5개 항목으로 대체. 햄버거 버튼은 `hidden`(layout/Header.tsx:160) 상태로 의도적 비활성화.
- **모바일 영향**: 페이지 헤더가 로고+Stock-Vis 텍스트만 남아 단순함. 화면 폭 360px에서도 OK. **MobileNav가 단일 소스로 잘 분리**되어 있음.
- **남는 이슈**: 모바일에서 `Header.tsx:111`의 search bar(`hidden md:block`)가 안 보임 → 모바일 사용자는 종목 검색 진입점이 없음. 종목 페이지 직접 URL 입력 또는 `/screener` 경유 필요. (MAJOR 네비게이션 이슈로 별도 기록 — §네비게이션 #11)

### 5. InvestingHeader (dead code) — `max-w-[1400px]` 3개 (참고)
- **위치**: `frontend/components/layout/InvestingHeader.tsx:32,55,99`
- **상태**: `Grep` 결과 자기 자신만 import → 실제 렌더 안 됨. 모바일 영향 없음. 제거 후보(`design_system_audit`에 별도 기록 권장).

### 6. dashboard/page.tsx — 자체 nav 추가 (MINOR)
- **위치**: `frontend/app/dashboard/page.tsx:31`
- **현상**: `layout.tsx`에 이미 `<Header />`가 있는데 dashboard 페이지가 자체 `<nav>`를 또 그림. 모바일에서는 두 nav가 위아래로 쌓임.
- **권장**: 페이지별 nav 제거하거나 `Header`에 통합.

### 7. md: 브레이크포인트 사용 빈도 부족 (MAJOR — 횡단)
- **수치**: `app/` 24개 페이지 중 `md:hidden|md:block|md:flex|md:grid|sm:hidden|lg:hidden` 매칭 **4건만** (portfolio, dashboard, stocks/[symbol], screener).
- **의미**: news, market-pulse-v2, thesis 페이지군, chainsight, watchlist, mypage 등은 **페이지 레벨에서 모바일 표시 토글이 없음**. 데스크톱 레이아웃이 그대로 모바일에 흘러내려가는 케이스가 많을 가능성.
- **단**: `Tailwind`는 기본이 mobile-first라 `grid-cols-1 md:grid-cols-2` 같은 점진적 확장은 별도 카운트되지 않음. 그래서 절대 BLOCKER는 아니지만, **모바일 전용 분기/숨김이 거의 없다는 신호**는 명확하다.

### 8. 가로 스크롤 컨테이너 33곳 (MAJOR — 횡단)
- **`overflow-x-auto`/`overflow-x-scroll` 매칭 33건**. 이 중 모바일에서 의도된 가로 스크롤(탭/칩 UI)은 OK:
  - `eod/SignalFilterTabs.tsx:33`, `chainsight/SectorBar.tsx:24`, `chainsight/ExplorationTrail.tsx:36`, `validation/SignalSummaryCard.tsx:36` (카테고리 칩) → 정상
  - `news/KeywordDetailSheet.tsx:125`, `news/NewsHighlightedStocks.tsx:118` (가로 캐러셀) → 정상
- 의도하지 않은 가로 스크롤 = 모바일에서 핵심 데이터 가림:
  - `admin/*` 7곳(SystemTab/NewsTab/ScreenerTab/TaskLogViewer/CollectionStatsTable/NewsCategoryManager/MLCompareView) — admin은 데스크톱 전용 가정, 그러나 보호 분기 없음
  - `stocks/[symbol]/page.tsx:843` (FinancialTab 재무제표), `:1030` (탭) — **FinancialTab은 BLOCKER §16 참조**
  - `watchlist/page.tsx:294` — 별도 조사 필요(이번 감사 범위 밖)
  - `strategy/ScreenerTable.tsx:128` — §3 참조
  - `validation/LeaderComparisonSection.tsx:47`, `stocks/StockTable.tsx:34` — 미확인

### 9. FinancialTab 재무제표 표 (BLOCKER)
- **위치**: `frontend/app/stocks/[symbol]/page.tsx:843`
- **현상**: `<table className="min-w-full">` + 항목 행 + 분기/연도별 컬럼(평균 5~8열, 분기 데이터 시 최대 20열까지). `overflow-x-auto`만 적용.
- **모바일 영향**: "Total Revenue, Cost of Goods, ..." 같은 항목명이 `px-4` 셀에 들어가면서 가로 스크롤이 매우 길어지고, 첫 컬럼(항목명)이 sticky가 아니므로 스크롤 후 어떤 항목인지 알 수 없음.
- **권장**: 첫 컬럼 `sticky left-0` + 모바일 전용 카드 펼침형 뷰.

### 10. AdvancedFilterPanel/FilterPanel — 모바일 대응 미확인
- **위치**: `frontend/components/screener/AdvancedFilterPanel.tsx`, `frontend/components/chainsight/FilterPanel.tsx`
- **상태**: 본 감사에서 본문 미열람. chainsight의 경우 `app/chainsight/[symbol]/page.tsx:285`에 절대 위치 패널로 띄움 → 모바일에서 width 처리 불명. 후속 감사 필요.

---

## 터치 타겟

### Apple HIG 44×44pt 기준 위반 후보

#### 11. ThesisDashboard `IndicatorRow` 전체 동작 면적은 OK, 내부 차트 토글 작음 (MAJOR)
- **위치**: `frontend/components/thesis/dashboard/IndicatorRow.tsx`
- **메인 토글**: `<button>` 전체 행이 `px-4 py-3` (`:82`) → 약 50px 높이, 폭 100% → **OK**.
- **하지만 내부**:
  - `:178-189` 차트 기간 버튼 1M/1Y/3Y/5Y: `px-2.5 py-0.5 text-[10px]` → 실측 **약 25×16px**. **위반**.
  - `:100` `ChevronDown size={14}` 토글 아이콘: 자체는 14×14, 부모 행 클릭으로 토글되므로 명목상 OK이나 **시각적 affordance 부족**.
- **2행 레이아웃 폭 압박**:
  - `:108-144` 한 줄에 값(`min-w-[60px]`) + 변동률(`min-w-[120px]`) + 스파크라인(`max-w-[100px]`) + 지지/반박 텍스트.
  - 합산 최소 ~280px + gap-3(3*12=36) = **316px**. 375px 모바일에서 좌우 padding(`px-4`=32) 제하면 **343px** → 빠듯하지만 들어감.
  - 단, 지지/반박 텍스트 길이("매우 강한 지지" 등 5자) 또는 값 단위가 커지면 즉시 줄바꿈/잘림.

#### 12. QuarterlySparkline — 분기 막대 hover 의존 (MAJOR)
- **위치**: `frontend/components/thesis/dashboard/QuarterlySparkline.tsx`
- **현상**:
  - 분기 라벨 `text-[8px]` (`:54`) → **위반** (HIG 권장 11pt 이상).
  - 값 표시가 `onMouseEnter/onMouseLeave` 호버 의존 (`:44`) → **모바일에서 호버 없음**. 탭 시 의도 모호(toggle 미구현). 분기별 정확한 값을 모바일에서 볼 수 없음.
- **권장**: 모바일 tap → tooltip 토글, 라벨 `text-[10px]` 이상.

#### 13. IndicatorRow 차트 내부 폰트 (MINOR)
- **위치**: 같은 파일 `:207,210,247,251`
- **현상**: Recharts `fontSize={9}` (X축), `fontSize={10}` (Y축). 모바일에서 판독 어려움.
- **권장**: `fontSize={10~11}` 통일 + Y축 width 55 → 모바일에서는 더 늘릴 여지.

#### 14. EOD SignalCard `HelpCircle` 토글 (MAJOR)
- **위치**: `frontend/components/eod/SignalCard.tsx:102-115`
- **현상**: `<button className="p-1">` + `<HelpCircle className="w-3.5 h-3.5">` → 실제 hit area **약 22×22px**. **위반**.
- **모바일 사용성**: 카드 클릭은 메인 액션(상세 시트 열기), 우측 상단 작은 ? 버튼은 교육 팁 토글. 카드 전체 onClick과 ?의 `stopPropagation` 동작은 코드상 정상이지만 손가락 hit가 어려움.
- **권장**: `p-2`로 확장(40×40), 또는 ? 표시를 카드 우측 상단 코너에서 카드 본문 안으로 통합.

#### 15. EOD `MiniSparkline` 영역 클릭 영향 없음 (참고)
- **위치**: `SignalCard.tsx:188`
- **상태**: `width={52} height={20}` 작은 스파크라인. 단순 시각 표시, 클릭 핸들러 없음 → OK.

#### 16. PeerContextBar `prest_key` 탭 (MAJOR)
- **위치**: `frontend/components/validation/PeerContextBar.tsx:37-49`
- **현상**: `<button className="px-3 py-1 text-xs">` → 실측 **약 80×26px**. 높이가 26px로 **위반** (44pt 미달).
- **추가**: peer 목록 칩(`:128`) `px-2 py-0.5 text-xs` → 더 작음 (약 18px 높이). 단, 이건 표시용이지 클릭 가능 표적이 아님(텍스트만) → 시각 OK.
- **권장**: 탭 버튼 `py-2 min-h-[44px]`로 확장. 모바일에서는 한 줄에 1~2개 탭만 보여도 OK (`flex-wrap gap-2`는 이미 적용).

#### 17. SignalSummaryCard 신호등 카드 (MINOR)
- **위치**: `frontend/components/validation/SignalSummaryCard.tsx:38-62`
- **현상**: `min-w-[72px]` 카드 안에 `w-10 h-10`(40×40) 신호등. 호버로만 툴팁(`:54`).
- **모바일 영향**: 탭 인터랙션 없음 → 모바일에서 회색 신호등의 이유를 볼 수 없음. **MAJOR 후보**지만 정보 자체는 우측 `summaryText`에 함의로 들어가므로 격하.

#### 18. text-[10px] / text-[11px] 클릭 가능 요소 (MAJOR — 분산)
- **수치**: `text-[10px]` 또는 `text-[11px]` 50개 파일에 산재.
- **클릭 가능 요소로 추정되는 위치 (샘플)**:
  - `chainsight/MobileCardList.tsx:149,154,159` — 프로파일 태그 (시각 표시, 클릭 X) → OK
  - `eod/SignalCard.tsx:91,178` — 카테고리 라벨/시그널 라벨 (시각 표시) → OK
  - `thesis/dashboard/IndicatorRow.tsx:118,148,161,167,182` — 비교 라벨/전제명/설명/`text-[10px]` 기간 버튼 → 기간 버튼은 §11에 포함
  - `thesis/indicators/RecommendCard.tsx:30,33,36` — 타입/방향/소스 칩 (시각 표시) → OK
- **결론**: text-[10/11px] 자체가 모두 위반은 아님. **클릭 가능한 표적에 한정해서** §11, §14, §16과 같은 케이스를 별도 다뤘다. 가독성 폴리시는 §디자인 시스템 별도 감사.

#### 19. Header 모바일 햄버거 — 비활성 상태 코멘트 일치 (참고)
- `Header.tsx:157-163`: `hidden inline-flex ... min-h-[44px] min-w-[44px]`. 의도적 비활성, 44pt 사이즈는 부활 대비 보존. 모범 사례.

#### 20. ChatInterface 전송 버튼 (참고)
- `frontend/components/rag/ChatInterface.tsx:198`: `h-[52px] w-[52px]` → **OK** (44pt 초과).

#### 21. AlertBell / AlertBadge — 18×18px (참고)
- `thesis/common/AlertBell.tsx:18`, `admin/news/AlertBadge.tsx:29`: `min-w-[18px] h-[18px]` 카운트 배지. 클릭 표적이 아닌 상위 버튼의 시각적 라벨 → OK.

---

## 네비게이션

### 22. MobileNav bottom-tab (정상 — 강점)
- **위치**: `frontend/components/layout/MobileNav.tsx`
- **확인 사항**:
  - `fixed bottom-0 left-0 right-0 ... md:hidden z-50` — 모바일 전용 노출
  - `min-h-[44px] py-2` — **HIG 44pt 보장 (`:34`)**
  - 5개 탭(홈/종목/뉴스/포트폴리오/내정보) — Apple HIG 권장 5개 이하 부합
  - `flex-1` 균등 분배 → 모바일 폭에 자동 적응
- **이슈 없음**.

### 23. /thesis 진입점 부재 (MAJOR — 사용자 흐름)
- `MobileNav`의 5개 탭에 **`/thesis` (Thesis Control)가 없음**. 데스크톱 `Header`는 7개 메뉴(thesis 포함), 모바일은 5개로 축소된 결과 thesis가 빠짐.
- **영향**: 모바일에서 가설 관제실에 가려면 `/news` 또는 `/portfolio`에서 딥링크가 있어야 도달 가능. 현재 어디서 deep link하는지 추가 조사 필요.
- **권장**: `MobileNav`의 "내정보" 자리에 `/thesis` 추가, 또는 햄버거 보조 메뉴 도입.

### 24. Header 검색바 — 모바일에서 없음 (MAJOR)
- §4 참조. 모바일 사용자는 종목 검색 진입점이 없음. `/screener`로 우회.
- **권장**: `MobileNav` 위에 floating search action button, 또는 종목 탭(`/stocks` listing 페이지 진입 시 검색바 노출) 신설.

### 25. chainsight 모바일 분기 (정상)
- `app/chainsight/[symbol]/page.tsx:115-126`: `window.innerWidth < 768` 감지 → `MobileCardList` 강제 (그래프 미렌더).
- `:151-170`: 모바일 카드 리스트 / `:172-232`: 모바일 그래프 오버레이 + 바텀 시트. 모바일 우선 설계 우수.
- **이슈 없음**.

### 26. thesis 페이지 그룹 (정상 — 다크 모바일 전용)
- `app/thesis/[thesisId]/page.tsx:62`: `max-w-lg mx-auto` → 최대 폭 512px로 잡혀 있어 사실상 모바일/태블릿 폭에 최적화.
- 대시보드, 빌더, 인디케이터 설정, 마감 등 thesis 하위 페이지가 일관되게 모바일 폭으로 설계.
- 단, **데스크톱 사용자에게는 화면 좌우 여백이 크게 남는다** (다른 감사 주제).

### 27. Virtualization 부재 (MAJOR — 성능)
- `react-window`, `react-virtual`, `VirtualList` 0건.
- **잠재 영향**:
  - `news/page.tsx:48` `limit: 100` → 100개 카드 렌더
  - `screener` 페이지당 50개 (페이지네이션으로 분할되어 OK)
  - `validation` 메트릭 카테고리(7개) × 메트릭(카테고리당 3~7개) = 30~50개 카드, 모바일 1열 펼치면 길어짐
- **모바일 영향**: 저사양 기기에서 스크롤 jank 가능. 현재 인지된 사용자 보고는 없으나 사전 예방 측면 MAJOR.

### 28. 모달/시트 모바일 대응
- **EOD `SignalDetailSheet`** (`components/eod/SignalDetailSheet.tsx:97`): `w-full md:w-[420px] md:h-full` + 모바일에서 `rounded-t-2xl` 바텀 시트 + 드래그 핸들(`:107`). **모범**.
- **chainsight 그래프 오버레이**: `fixed inset-0 z-50 bg-white` 풀스크린, 바텀 시트 노드 상세 `max-h-48 overflow-y-auto`. **정상**.
- **PortfolioModal**: 본문 미열람. 후속 확인 필요.
- **AddIndicatorSheet**: `frontend/components/thesis/AddIndicatorSheet.tsx` BottomSheet 컴포넌트 사용 (`:4`). **정상**.

---

## 차트/그래프

### 29. ResponsiveContainer 사용 현황 (정상)
- **확인 컴포넌트** (`width="100%"` + 명시 height 또는 height="100%"):
  - `validation/MetricBarChart.tsx`, `stock/StockChart.tsx`, `thesis/dashboard/IndicatorRow.tsx`, `thesis/dashboard/IndividualMiniCharts.tsx`, `charts/StockPriceChart.tsx`, `admin/news/MLTrendChart.tsx`, `portfolio/PortfolioChart.tsx`, `news/SentimentChart.tsx`, `screener/SectorHeatmap.tsx`, `macro/YieldCurveChart.tsx`
  - market-pulse-v2 details: BreadthDetail, RegimeDetail, SectorDetail, FlowDetail — 전부 `ResponsiveContainer`
- **결론**: 차트 컨테이너 자체는 모바일에서 폭에 맞춰 줄어듦. **이슈 없음**.

### 30. 차트 폰트 가독성 (MAJOR — 횡단)
- **현황**: 거의 모든 차트에서 axis `fontSize={9}` 또는 `{10}`, `tick={{ fontSize: 11 }}` 사용.
- **모바일 영향**: iPhone 13 mini DPR 환경에서도 9~10px은 흐릿. Y축 tickFormatter(`formatRawValue`)가 "$123.45K" 같은 다중 글자열을 반환할 때 인접 tick 간 겹침 위험.
- **샘플**:
  - `IndicatorRow.tsx:207,210` → `fontSize={9}` (X), `{10}` (Y)
  - `stock/StockChart.tsx:657,667` → `fontSize: 11`
  - `QuarterlySparkline.tsx:54` → `text-[8px]` (§12)
- **권장**: 모바일에서 `fontSize={11}` 하한 + Y축 width 동적 조정.

### 31. 차트 height 고정 (MINOR)
- `IndicatorRow.tsx:197` height={160}, `:235` height={140}
- `IndividualMiniCharts.tsx:54` height={100}
- `StockPriceChart.tsx:272`, `StockChart.tsx:652` — `chartHeight.price` 변수 사용(반응형으로 추정)
- **현황**: 대부분 고정 height. 모바일 가로 폭은 줄어드는데 height는 그대로 → 가로 압축 발생. 데이터 포인트가 많을수록 X축 겹침 심각.
- **권장**: 모바일 viewport에서 `chartHeight` 조정 또는 `aspect-ratio` 사용.

### 32. SectorHeatmap (MINOR)
- `frontend/components/screener/SectorHeatmap.tsx:216`: `<ResponsiveContainer width="100%" height={400}>` + Treemap.
- **모바일 영향**: 400px 고정 높이 + 11개 섹터 영역에 한국어 라벨이 들어가면 모바일 폭(375px)에서 라벨 잘림 빈발.
- **권장**: 모바일 height 250~300px + 작은 섹터는 영역 점유율에 따라 라벨 숨김.

### 33. StockChart Candlestick (MINOR)
- `components/stock/StockChart.tsx:652-724`: ComposedChart, 캔들 barSize={8}, wick barSize={1}.
- **모바일 영향**: 90일치 데이터에서 캔들 8px + gap → 720px 이상 필요. ResponsiveContainer가 폭 압축하면 캔들이 1~2px로 변형되어 시각 정보 손실.
- **권장**: 모바일에서는 `barSize` 동적 또는 표시 범위 축소(1M 기본).

---

## 페이지별 상세

### `/` (홈 = EOD Dashboard)
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `max-w-6xl mx-auto px-4` | OK |
| 카드 그리드 | `SignalCardGrid` (별도 컴포넌트, 확인 필요) | 모바일 1열 가정 시 OK |
| 카테고리 필터 | `SignalFilterTabs` `flex gap-2 overflow-x-auto pb-1` | **정상** (가로 스크롤 칩) |
| 카운트 배지 | `min-w-[18px] h-[18px] text-[11px]` | 시각 표시, OK |
| 시그널 카드 ? 버튼 | `p-1` + `w-3.5 h-3.5` ≈ 22px | **MAJOR §14** |
| 카드 내 stock 링크 | `text-xs` Link | hit area는 인접 영역 포함하면 OK |
| 상세 시트 | 모바일 바텀시트 + 드래그 핸들 | **정상** |
| 하단 여백 | `pb-20 md:pb-0` (MobileNav 가림 방지) | **정상** |

**판정**: MAJOR 1건 (?버튼), 그 외 양호.

---

### `/stocks/[symbol]` (종목 상세)
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` | OK |
| 헤더 grid | `grid-cols-1 lg:grid-cols-2` | 모바일 1열로 stack. OK |
| 현재가 | `text-4xl font-bold` | OK |
| Key Metrics grid | `grid-cols-2 gap-4` | 6개 항목 3행. OK |
| L1 탭 | `flex space-x-2` (Pill) | 3개 탭, 모바일 OK |
| L2 탭 | `flex space-x-6` (Underline) | 최대 5개 탭, 모바일에서 가로 스크롤 없음 → **MAJOR**(잘림 가능) |
| FinancialTab | `overflow-x-auto` 표 | **BLOCKER §9** |
| Validation 탭 | `useState isMobile` 분기, 카테고리 칩 UI | **정상** (모바일 분기 있음) |
| Chain Sight 탭 | `ChainSightMiniView` (dynamic) | 본문 미확인, 모바일 동작 별도 검증 필요 |
| 새로고침 버튼 | `px-3 py-2` ~ **44px 미달** | **MAJOR** (피로감) |

**판정**: BLOCKER 1건 (재무제표), MAJOR 2건 (L2 탭/새로고침).

---

### `/screener`
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `mx-auto max-w-7xl px-4` | OK |
| 프리셋 카드 | `PresetGallery` (본문 미확인) | 후속 |
| 결과 헤더 | `flex flex-col sm:flex-row` | **정상** (모바일 stack) |
| 뷰 모드 토글 | `hidden sm:flex` | 모바일에서 카드 강제, **정상** |
| 테이블 뷰 | `hidden sm:block` | 모바일에서 비표시, **정상** |
| 카드 뷰 | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` | **정상** |
| AI 키워드 버튼 | `<span className="hidden sm:inline">AI 키워드</span>` | 모바일 아이콘만, 의미 손실 가능 → **MINOR** |
| 필터 태그 | `flex flex-wrap gap-2` | OK |
| MobileStockCard | 자체 컴포넌트, 카드 디자인 양호 | **정상** |

**판정**: 핵심 BLOCKER 없음. MINOR 1건.

---

### `/portfolio`
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` | OK |
| 헤더 | `flex justify-between` 새로고침/추가 버튼 가로 | 모바일에서 좁음 → **MINOR** |
| Summary | `PortfolioSummary` (본문 미확인) | 후속 |
| 차트 토글 (pie/bar) | `flex space-x-2` | OK |
| 뷰 모드 토글 (grid/table) | 데스크톱 동일 노출 | 모바일에서도 table 선택 가능 → **§1 BLOCKER 트리거** |
| 카드 뷰 | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` | **정상** |
| 테이블 뷰 | `PortfolioTable` 12열 | **BLOCKER §1** |
| 종목 추가 모달 | `PortfolioModal` (본문 미확인) | 후속 |

**판정**: BLOCKER 1건 (PortfolioTable), MINOR 1건 (헤더 버튼 배치).

---

### `/thesis` (가설 통제실 메인)
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | 부모 layout `max-w-lg`로 가정 (`(list)/page.tsx`만으로 미확정) | 후속 |
| 섹션 구조 | `space-y-8` 3섹션 | OK |
| ThesisListCard | `ul.space-y-3 > li` | 본문 미확인 |
| EmptyTheses | `MoonPhase` + 안내 | OK |
| 다크 테마 | bg-gray-900 + 텍스트 회색 계열 | 일관성 양호 |

**판정**: 페이지 자체는 모바일 친화. 카드 내부 상세 별도 감사.

---

### `/thesis/[thesisId]` (가설 대시보드)
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `max-w-lg mx-auto px-4 pt-4 pb-20` | **모바일 우선, 정상** |
| DashboardPageHeader | 별도 컴포넌트 | 후속 |
| AISummarySection | 별도 컴포넌트 | 후속 |
| NotableChangesSection | 별도 컴포넌트 | 후속 |
| IndicatorRow | 토글형, 차트 펼침 | **MAJOR §11, §13** (차트 폰트/기간 버튼) |
| QuarterlySparkline | hover 의존 + text-[8px] | **MAJOR §12** |
| 하단 마감 버튼 | `block w-full py-3` | **OK** (44pt 충족) |
| 지표 설정 링크 | `Settings size={12}` + `text-xs` | **MINOR** (아이콘 작음, 텍스트 hit area 보완) |

**판정**: MAJOR 3건.

---

### `/thesis/new` (가설 빌더)
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `h-[calc(100dvh-env(safe-area-inset-top))]` | **모바일 풀스크린 채팅, 우수** |
| 뒤로 가기 | `<ArrowLeft size={20}>` `p-1` | 약 28px hit area → **MAJOR** (44pt 미달) |
| 진행 표시 | `ProgressBar` | 후속 |
| 채팅 버블 | 별도 컴포넌트 | 모바일 우선 설계 가정 |
| 옵션 버튼 | `OptionButton` (본문 미확인) | 후속 |
| 가설 카드 | `PremiseCard` (본문 미확인) | 후속 |
| 뉴스 선택 | `NewsSelector` (본문 미확인) | 후속 |
| 다중 선택 푸터 | `MultiSelectFooter` (본문 미확인) | 후속 |
| BottomSheet | `BottomSheet` 공통 컴포넌트 | **정상** |

**판정**: 큰 틀은 모바일 우선. 뒤로 가기 버튼 1건 MAJOR.

---

### `/thesis/[thesisId]/indicators` (지표 설정)
| 항목 | 상태 | 비고 |
|------|------|------|
| RecommendCard | `flex items-start gap-3 p-4` + `+` 버튼 `p-2.5` (40px) | **OK** (40px도 거의 44에 근접) |
| 추가 버튼 | `<Plus size={16}>` `p-2.5` | **OK** |
| 칩 라벨 | `text-[10px]` 타입/방향/소스 | 시각 표시, OK |

**판정**: 양호.

---

### `/chainsight/[symbol]`
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `h-screen flex flex-col` | OK |
| isMobile 분기 | `window.innerWidth < 768` (`:117`) | **정상** |
| MobileCardList | 별도 컴포넌트 | **정상** (탭 + 카드 + CTA 3개) |
| 카드 내 CTA | 가설/탐색/검증 3개 버튼 `py-1.5 text-xs` ≈ 30px | **MAJOR** (44pt 미달) |
| 그래프 보기 FAB | `w-full py-3 text-sm` | **OK** |
| 모바일 그래프 | 풀스크린 + 바텀 시트 | **정상** |
| 데스크톱 3-panel | 헤더 + 좌/중/우 | 데스크톱 전용, OK |

**판정**: MAJOR 1건 (카드 CTA 높이).

---

### `/news`
| 항목 | 상태 | 비고 |
|------|------|------|
| 페이지 폭 | `px-4 sm:px-6` | OK |
| 헤더 | `flex items-center justify-between` | OK |
| Source Tabs | `flex gap-1` 3개 탭 | **OK** (가로 공간 충분) |
| Time Filter | `flex items-center gap-1.5` 3개 칩 + 아이콘 | **MINOR** (Source Tabs와 같은 줄, 좁은 화면에서 잘림 가능) |
| Intelligence 그리드 | `grid-cols-1 lg:grid-cols-2` 또는 `lg:grid-cols-3` | **정상** |
| 카테고리 섹션 | `NewsCategorySection` | 후속 |
| 새로고침 버튼 | `p-2` + `w-5 h-5` ≈ 36px | **MINOR** (44pt 미달) |

**판정**: MINOR 2건.

---

### `/market-pulse-v2` 및 details
- `app/market-pulse-v2/page.tsx`: 본문 미확인.
- `details/*Detail.tsx`: 전부 `<ResponsiveContainer>` 사용 → 차트 컨테이너 OK.
- **TickerBar** (`market-pulse-v2/components/TickerBar.tsx:23`): `overflow-x-auto sticky top-0` → 모바일 가로 스크롤 ticker, **정상**.
- **판정**: 외형은 모바일 친화로 추정. 본문 미확인 페이지는 후속 감사.

---

### `/dashboard`
- `app/dashboard/page.tsx`: §6 이중 nav 이슈.
- 카드 grid `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` → **정상**.
- 사용자 정보 `sm:grid sm:grid-cols-3` → 모바일에서 1열 stack, **정상**.
- **판정**: MINOR 1건 (이중 nav).

---

### `/login`, `/signup`, `/mypage`, `/admin`, `/ai-analysis`, `/market-pulse`, `/watchlist`
- **본 감사 미열람**. 후속 페이지별 감사 필요.
- 특히 `/admin`은 `overflow-x-auto` 표가 7곳 — 데스크톱 전용 가정이지만 모바일 보호 분기가 명시되어 있지 않으므로 별도 점검 권장.

---

## 종합 권장 사항 (우선순위)

### P0 — BLOCKER 즉시 대응
1. **`PortfolioTable` 모바일 카드 뷰 강제** — `viewMode` 초기값을 `window.innerWidth < 768`에서 `'grid'`로 고정하거나, `<MobileNav>` 자동 노출처럼 `md:hidden`으로 테이블 숨김.
2. **`FinancialTab` 첫 컬럼 sticky + 모바일 카드 뷰** — 항목명이 스크롤 후 사라지는 문제 해결.
3. **dashboard 페이지 자체 nav 제거** — `Header` 이중 노출 정리.

### P1 — MAJOR 단기 대응
4. **`MobileNav`에 `/thesis` 추가** — Thesis Control 진입점 부재 해소.
5. **`Header`에 모바일 검색 진입점** — bottom action button 또는 종목 탭 검색바.
6. **`SignalCard` ? 버튼 hit area 확대** — `p-1` → `p-2` 또는 통합 디자인.
7. **`QuarterlySparkline` 모바일 tap 대응** — hover 의존 제거, tap → tooltip toggle.
8. **`IndicatorRow` 차트 기간 버튼 확대** — `py-0.5` → `py-2`.
9. **Recharts axis fontSize 11px 하한** — 횡단 일관성.
10. **`/chainsight/[symbol]` 카드 CTA 버튼 `py-2.5 min-h-[44px]`**.
11. **`PeerContextBar` 프리셋 탭 `py-2 min-h-[44px]`**.

### P2 — MINOR / 장기
12. Virtualization 도입 검토 (`react-window`) — news 100개, validation peer 그리드.
13. `InvestingHeader` dead code 제거.
14. 모바일 차트 height 동적화 (`aspect-ratio` 활용).
15. screener AI 키워드/테제 버튼 모바일에서 짧은 라벨 부활.
16. 모든 차트 Y축 width를 모바일 viewport에서 늘리거나 tickFormatter 단축 강화.

---

## 부록: 본 감사에서 확인하지 못한 영역

- 페이지: `/login`, `/signup`, `/mypage`, `/admin/*`, `/ai-analysis`, `/market-pulse`, `/watchlist`, `/thesis/(list)/alerts`, `/thesis/[thesisId]/close`, `/chainsight/watchlist/*`
- 컴포넌트: `PortfolioModal`, `PortfolioStockCard`, `PortfolioSummary`, `AdvancedFilterPanel`, `FilterPanel(chainsight)`, `PresetGallery`, `PresetDetailPopover`, `Pagination`, `SignalCardGrid`, `AIGuidePanel`, `NodeDetailPanel`, `GraphCanvas`, `ChatBubble`, `OptionButton`, `PremiseCard`, `NewsSelector`, `MultiSelectFooter`, `BottomSheet`, `SuggestionCard`, `AddIndicatorSheet`(이하 부분 확인), `RealValueIndicatorCard`, `IndividualMiniCharts`, `AISummarySection`, `NotableChangesSection`, `DashboardHeader`, `DashboardPageHeader`, `AlertCard`, `IndicatorCard`
- 런타임 측정: 실제 폰 시뮬레이터/디바이스에서 overflow/터치 인식 실측 (`/qa` 또는 `/design-review`로 후속)

본 감사는 정적 코드 기반이므로, 위 영역과 실제 인터랙션 회귀 테스트는 별도 자동화 또는 디바이스 QA를 권장한다.
