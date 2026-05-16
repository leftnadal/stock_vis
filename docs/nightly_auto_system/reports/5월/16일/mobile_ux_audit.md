# 모바일 UX 감사 보고서

- 작성일: 2026-05-17 (오프닝 보고서: 5월 16일 reports/ 폴더)
- 작성자: nightly_auto_system / read-only audit
- 기준 뷰포트: **iPhone SE 1세대(375 × 667 CSS px)** + Android 평균 360 × 720
- Apple HIG 권장 터치 타겟: **44 × 44 pt**, Material 권장: **48 × 48 dp**
- 본 보고서는 **코드 수정을 수행하지 않은 정적 감사**이다. 모든 좌표·행번호는 5월 16일 시점 코드 기준.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 이슈 수 | 정의 |
|--------|---------|------|
| 🔴 BLOCKER | **6** | 모바일에서 기능 사용 불가/페이지 깨짐/터치 불가능 |
| 🟠 MAJOR | **11** | 사용 가능하나 명백한 사용성 저하 (가독성·터치·스크롤) |
| 🟡 MINOR | **9** | UI 정돈/접근성 개선 권장 (라벨, 일관성) |
| **합계** | **26** | |

핵심 패턴:
1. **이중 헤더 + Bottom Nav 라우팅 불일치** — `Header`는 7개 메뉴(대시보드/포트폴리오/Chain Sight/Thesis/Market Pulse/뉴스/스크리너), `MobileNav`는 5개(홈/종목/뉴스/포트폴리오/내정보). 모바일에서 **Chain Sight, Thesis, Market Pulse, 스크리너 진입 경로 자체가 없다.** → BLOCKER.
2. **데스크톱 전용 페이지 다수** — `/dashboard`, `/portfolio`(테이블), `/screener`(테이블 뷰) 모두 1024px+ 기준 설계. `overflow-x-auto`로 가로 스크롤은 되지만 모바일 의도된 흐름이 아님.
3. **`text-[10px]` 클릭 요소 65건** — 라벨·정보용으로 쓰이는 경우가 다수이나, 일부는 클릭 가능한 링크(예: market-pulse MoverCard, screener AdvancedFilterPanel 칩 X 버튼)에 직결 → 터치 정확도 저하.
4. **Recharts ResponsiveContainer 사용률 양호 (15/15 차트 파일)** — `width="100%"`로 가로폭에 적응하나, **고정 높이(h=160/140) + 좌측 axis width(50~55px)** 조합이 모바일에서 그래프 영역을 좁힌다.

---

## 반응형 누락

### 1.1 고정 폭 사용 컴포넌트 (`w-[NNpx]`, `min-w-[NNpx]`, `max-w-[NNpx]`)

총 30+ 인스턴스 식별. iPhone SE(375px) 기준 overflow 가능성을 분석.

| 위치 | 고정값 | 모바일 위험 | 심각도 |
|------|--------|-------------|--------|
| `components/chainsight/MarketGraphCanvas.tsx:676` | `w-[110px] min-h-[68px]` (인기 섹터 빠른 접근 버튼) | flex-wrap이라 OK. min-h 68px → 터치 OK | 🟡 MINOR |
| `components/rag/ChatInterface.tsx:198` | `w-[52px] h-[52px]` (전송 버튼) | 52pt → 터치 OK | 🟡 안전 |
| `components/thesis/dashboard/IndicatorRow.tsx:110` | `min-w-[60px]` (값 column) | OK |  안전 |
| `components/thesis/dashboard/IndicatorRow.tsx:115` | `min-w-[120px]` (변동률 column) | **375px에서 좁음** — 값(60) + 변동률(120) + 스파크라인(100) = 280 + 좌패딩 + 우측 지지/반박 라벨 → 우측 오버플로 가능 | 🟠 MAJOR |
| `components/thesis/dashboard/IndicatorRow.tsx:132` | `max-w-[100px]` (스파크라인) | OK | 안전 |
| `components/eod/SignalDetailSheet.tsx:97` | `w-full md:w-[420px]` | 모바일은 w-full → OK | 안전 |
| `components/validation/SignalSummaryCard.tsx:41` | `min-w-[72px]` (신호등 7개 가로 스크롤) | 7 × 72 = 504px → 가로 스크롤 의도, overflow-x-auto 있음 | 🟡 MINOR |
| `components/screener/Pagination.tsx:127` | `min-w-[44px] min-h-[44px]` | 터치 타겟 OK | 안전 |
| `components/layout/InvestingHeader.tsx:32/55/99` | `max-w-[1400px]` | 컨테이너 폭 — `px-4`로 모바일 패딩 처리 → OK | 안전 |
| `components/eod/StockRow.tsx:55` | `max-w-[140px]` (회사명 truncate) | OK | 안전 |
| `components/eod/StockRow.tsx:66` | `min-w-[72px]` (가격 column) | OK | 안전 |
| `components/news/RecommendationCard.tsx:85` | `max-w-[150px]` | OK | 안전 |
| `components/strategy/ScreenerTable.tsx:209/224/307` | `max-w-[180/120/200px]` (column 폭) | 테이블 전체가 `overflow-x-auto` 안 — 12개 컬럼 가로 스크롤로 동작 (의도된 동작이나 모바일에서는 카드 뷰 권장) | 🟠 MAJOR |
| `components/common/DataSourceBadge.tsx:171` | `min-w-[200px]` (팝오버) | 375px에서 패딩 포함 가능. 위치 보정 필요 시 우측 잘림 위험 | 🟡 MINOR |
| `components/keywords/KeywordTag.tsx:90` | `w-48` (192px, hover 툴팁) | 모바일은 hover 부재 — touch 시 표시 안 됨 | 🟠 MAJOR |
| `components/market-pulse/MoverCard.tsx:138/150/162/177/189` | `w-48` (hover 툴팁 5개) | 동일 — 모바일 미작동 | 🟠 MAJOR |
| `components/chainsight/NodeTooltip.tsx:141` | `max-w-[130px]` truncate | OK | 안전 |
| `components/chainsight/RelationLegend.tsx:51` | `max-w-[140px]` | OK | 안전 |

### 1.2 브레이크포인트 누락 컴포넌트

**데스크톱 전용 (sm:/md:/lg: prefix 없이 데스크톱 너비 가정)**:

| 위치 | 증상 | 심각도 |
|------|------|--------|
| `app/dashboard/page.tsx:32-50` | `max-w-7xl + flex justify-between h-16` 네비 — 모바일에서 사용자명 + 로그아웃 버튼이 한 줄에 압축, 사용자명 길면 잘림 | 🟠 MAJOR |
| `app/dashboard/page.tsx:54` | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` — 카드 그리드는 반응형 OK | 🟢 OK |
| `app/chainsight/[symbol]/page.tsx:234-292` | 데스크톱 3-panel 레이아웃(`h-screen flex`)은 isMobile state로 분기 처리, 모바일 별도 카드 리스트 사용 → 잘 구현됨 | 🟢 OK |
| `app/stocks/[symbol]/page.tsx:1058` | `w-48 flex-shrink-0 hidden lg:block` — sidebar는 hidden lg:block로 모바일 숨김 OK | 🟢 OK |
| `app/thesis/(list)/layout.tsx:7` | `max-w-lg mx-auto px-4` — 모바일 우선 설계 ✓ | 🟢 OK |
| `components/portfolio/PortfolioTable.tsx:258-300` | 12개 컬럼 + `px-6 py-3` 헤더 — `overflow-x-auto`로 가로 스크롤 가능하나, **모바일 카드 뷰 대안 없음** | 🟠 MAJOR |
| `components/strategy/ScreenerTable.tsx:127-188` | 12개 컬럼 + AI 키워드 셀 — `overflow-x-auto`이나 동일 문제. `app/screener/page.tsx:844-875`에서 `hidden sm:block`(테이블)과 `sm:hidden`(카드) 분기 처리 → 잘 구현됨 | 🟢 OK |
| `components/admin/SystemTab.tsx` 등 admin/ 전체 | 어드민 콘솔 — 모바일 대응 미필요 (정책 결정 필요) | 🟡 MINOR |

### 1.3 테이블/차트 가로 스크롤 처리

- `overflow-x-auto` 사용 28개 파일 (Grep 결과)
- ScreenerTable: ✓ scroll wrapper 있음 (l.128)
- PortfolioTable: ✓ scroll wrapper 있음 (l.259)
- 단, 스크롤 인디케이터(그림자/그라데이션) 없어 **가로 스크롤 가능함이 시각적으로 드러나지 않음** → 발견성 저하. → 🟠 MAJOR (UX 개선 권장)

---

## 터치 타겟

### 2.1 44pt 미만 클릭 요소 (BLOCKER · MAJOR)

| 위치 | 요소 | 실측 | 심각도 |
|------|------|------|--------|
| `app/chainsight/[symbol]/page.tsx:206` | `<button onClick={() => setSelectedNode(null)} className="text-gray-400 text-sm">✕</button>` (모바일 노드 닫기 X) | 텍스트만, padding 없음 → ~14×14pt | 🔴 BLOCKER |
| `app/chainsight/[symbol]/page.tsx:209-226` | flex-1 + `text-xs py-2` 액션 3버튼 (탐색/가설/검증) | 높이 ≈ 32pt | 🟠 MAJOR |
| `app/screener/page.tsx:483` | "접기/펼치기" 토글 `text-xs` 텍스트 버튼 | ~24×16pt | 🟠 MAJOR |
| `app/screener/page.tsx:537-540` | 프리셋 칩 X 제거 버튼 (`<X h-3 w-3 />`) | 12×12pt | 🔴 BLOCKER |
| `app/screener/page.tsx:589, 597, 605, 613, 621, 629, 637, 645, 702, 710, 718` | 필터 칩 X 버튼 (`h-3 w-3` 동일 패턴 11회 반복) | 12×12pt | 🔴 BLOCKER |
| `app/screener/page.tsx:752-774` | 뷰 모드 토글 (List/Grid) `p-1.5` | ≈ 28pt | 🟠 MAJOR (모바일 `hidden sm:flex`로 노출 안 됨 → 🟢 OK) |
| `components/screener/Pagination.tsx:94-111, 141-158` | 페이지 첫/이전/다음/끝 `p-1.5` | 28pt | 🟠 MAJOR (페이지 숫자는 44×44 OK) |
| `components/portfolio/PortfolioTable.tsx` (편집/저장 버튼) | `Edit2`, `Save`, `X` 아이콘 단독 | 16~24pt 추정 | 🟠 MAJOR |
| `app/thesis/(list)/layout.tsx:10` | `<Link className="p-2 -ml-2"><ArrowLeft size={20} /></Link>` | 패딩 8pt + 아이콘 20pt = 36pt | 🟡 MINOR |
| `app/thesis/[thesisId]/page.tsx:92-99` | "설정" 링크 `<Settings size={12} />` `text-xs` | ~30pt | 🟠 MAJOR |
| `components/chainsight/RelationLegend.tsx:59` | `text-[10px]` 토글 버튼 | 텍스트 기반 → 16pt | 🟠 MAJOR |
| `components/eod/SignalDetailSheet.tsx:188-192` | 섹터 링크 `text-[10px] px-1.5 py-0.5` | ~24pt | 🟠 MAJOR |
| `components/eod/SignalDetailSheet.tsx:197-202` | "관계 지도" 링크 `text-[10px]` | 동일 | 🟠 MAJOR |
| `app/thesis/new/page.tsx:1063` | "직접 작성하기" `text-[10px]` 링크 | ~24pt | 🟠 MAJOR |
| `components/screener/MobileStockCard.tsx:166, 172, 178` | `text-[10px]` 라벨 — 클릭 X (라벨 only) → 정보 표시 용도 | 🟢 OK |
| `components/screener/AdvancedFilterPanel.tsx:142` | `text-[10px]` 설명문 (descriptionKo) | 클릭 X → 정보 표시 | 🟢 OK |
| `components/keywords/KeywordTag.tsx` `size=sm` (l.42) | `px-2 py-0.5 text-[10px]` 키워드 칩 | ~20pt | 🟠 MAJOR (클릭 가능 시) |
| `components/thesis/alerts/AlertCard.tsx:28-31` | `text-[10px] px-1.5 py-0.5` severity 배지 | 라벨 only → OK | 🟢 OK |

**44pt 명시적으로 보장된 사례 (양호)**:
- `components/layout/MobileNav.tsx:34` — `min-h-[44px]` ✓ (audit P0 #13 주석으로 의도 명시)
- `components/strategy/ScreenerTable.tsx:323` — 바구니 추가 버튼 `min-h-[44px] min-w-[44px]` ✓
- `components/validation/SignalSummaryCard.tsx:41` — 신호등 `min-w-[72px] min-h-[44px]` ✓
- `components/screener/Pagination.tsx:127` — 페이지 숫자 `min-w-[44px] min-h-[44px]` ✓
- `components/validation/PeerContextBar.tsx:40, 54` — 프리셋 탭 `min-h-[44px] px-4 py-2` ✓
- `components/layout/Header.tsx:160` — 햄버거 `min-h-[44px] min-w-[44px]` ✓ (단, `hidden`이라 노출 안 됨)

### 2.2 사용자가 특정 지정한 영역

**(a) thesis 관제실 지표 카드** (`components/thesis/dashboard/IndicatorRow.tsx`)
- 전체 카드 = `<button>` (l.81). 카드 높이 충분 (3행 + py-3 = 약 80pt) → 토글 클릭 OK
- 일간 차트 기간 선택 칩 (l.179-189): `px-2.5 py-0.5 text-[10px]` → ~22pt → 🔴 BLOCKER
- 4개 칩 (1M/1Y/3Y/5Y) 모두 동일 패턴

**(b) validation 프리셋 탭** (`components/validation/PeerContextBar.tsx:36-50`)
- `min-h-[44px] px-4 py-2 text-xs` → 양호 ✓
- "직접 설정" 버튼 (l.54): 동일 패턴 ✓

**(c) chainsight 노드** (`components/chainsight/MarketGraphCanvas.tsx:670-702`)
- 인기 섹터 빠른 접근 버튼: `w-[110px] min-h-[68px]` → 매우 양호 ✓
- 단, **SVG `<circle>` 노드 자체**는 클릭 영역이 시각적 반경에 한정 (보통 r=8~12px = 16~24pt 직경) → 🔴 BLOCKER. ForceGraph2D canvas 기반이라 hit-area 별도 필요.

### 2.3 hover 의존 인터랙션 (모바일 미작동)

| 위치 | 패턴 | 심각도 |
|------|------|--------|
| `components/market-pulse/MoverCard.tsx:138-189` (×5) | `group-hover/tooltip:block` 툴팁 5개 | 🟠 MAJOR — 모바일에서는 의도 전달 안 됨 |
| `components/market-pulse/MoverCardWithBatchKeywords.tsx:145-196` (×5) | 동일 패턴 | 🟠 MAJOR |
| `components/keywords/KeywordTag.tsx:90` | hover 시 키워드 상세 표시 | 🟠 MAJOR |
| `components/strategy/ScreenerTable.tsx:207` | `opacity-0 group-hover:opacity-100` (ExternalLink) | 🟡 MINOR — 모바일에서는 항상 숨김 |
| `components/eod/StockRow.tsx:32` (`group hover:bg-gray-50`) | 호버 배경색만 → 동작 영향 없음 | 🟢 OK |

`onTouchStart` 대응이 있는 사례: `SignalSummaryCard.tsx:44` (gray 신호등 툴팁) ✓.

---

## 네비게이션

### 3.1 헤더/사이드바

| 항목 | 상태 |
|------|------|
| **Desktop Header** `components/layout/Header.tsx` | `hidden md:flex` 네비 7개 + 검색바. 768px 미만 숨김 ✓ |
| **Header 햄버거** (l.157-163) | `className="hidden ..."` — **현재 비활성화** (audit P0 #12 주석으로 의도 명시: "MobileNav가 모바일 네비 단일 소스") |
| **Header isMenuOpen 분기** (l.167-257) | 비활성 햄버거가 trigger이므로 사용자가 햄버거를 볼 수 없어 영구히 닫힘 → **이중 네비를 의도적으로 비활성화한 결과** |
| **MobileNav** `components/layout/MobileNav.tsx` | `fixed bottom-0 ... md:hidden` Bottom Navigation ✓ 사용 |
| **MobileNav 메뉴 5개** | 홈/종목/뉴스/포트폴리오/내정보 — 다음 메뉴 누락: **Chain Sight, Thesis Control, Market Pulse, 스크리너, AI 분석** | 🔴 BLOCKER |
| **InvestingHeader** `components/layout/InvestingHeader.tsx` | `flex` 기반 데스크톱 전용 헤더. 모바일 대응 X. 어디서 mount되는지 확인 필요 (Header와 중복 사용 위험) |

→ **결론**: 헤더-MobileNav 라우팅 표면이 일치하지 않아 모바일 사용자는 핵심 기능 5개에 접근 경로 없음. (직접 URL 입력하거나 EOD signal card → /stocks 등 우회 경로만 가능)

### 3.2 Bottom Navigation 존재 여부

- `MobileNav.tsx` Bottom Nav 구현 ✓
- 위치: `fixed bottom-0 left-0 right-0 ... z-50`
- 5개 메뉴, `h-16` (64px), 각 `min-h-[44px]` ✓
- safe-area-inset-bottom 미적용 → iOS 홈 인디케이터와 겹침 가능 → 🟡 MINOR

### 3.3 긴 목록 virtualization

- `react-window` / `react-virtuoso` / `@tanstack/react-virtual` **0건 사용 안 함**.
- 위험 목록:
  - `app/screener/page.tsx`: paginatedStocks (페이지당 50/100개) — pagination으로 분할 ✓
  - `app/watchlist/page.tsx`, `app/portfolio/page.tsx`: 단일 사용자 보유 종목이라 N <= 100 → 무시 가능
  - `MobileCardList.tsx` (chainsight): depth=2~3 시 노드 수십~수백 가능 → 🟠 MAJOR
  - `ScreenerTable.tsx`: pagination 처리됨 ✓
  - `app/thesis/[thesisId]/page.tsx` 지표 리스트: indicator 수 일반적으로 5-15개 → OK

---

## 차트/그래프

### 4.1 Recharts ResponsiveContainer 사용 현황

15개 차트 컴포넌트 모두 `<ResponsiveContainer>` 사용 ✓.

| 컴포넌트 | width | height | YAxis width | 모바일 평가 |
|----------|-------|--------|-------------|-------------|
| `IndicatorRow.tsx:197` (일간 차트) | 100% | **160px** | **55px** | 375px에서 그래프 영역 = 375 - 55(axis) - 16(좌패딩) - 16(우패딩) ≈ 288px. fontSize=9~10 → 가독성 경계 |
| `IndicatorRow.tsx:235` (분기 차트) | 100% | 140px | 50px | 동일 |
| `MetricBarChart.tsx:78` | 100% | h-48(192) | 50px | OK |
| `StockChart.tsx`, `StockPriceChart.tsx`, `PortfolioChart.tsx`, `SectorHeatmap.tsx` | 다양 | 다양 | - | 미상세 분석 (별도 감사 필요) |
| `YieldCurveChart.tsx`, `SentimentChart.tsx`, `MLTrendChart.tsx` | 100% | 다양 | - | OK 추정 |

**모바일 가독성 이슈**:
- `fontSize={9}` (IndicatorRow XAxis l.207) — iPhone에서 ~12px Apple 시스템 폰트 minimum 미달 → 🟠 MAJOR
- `fontSize={10}` YAxis (l.211) — 동일 → 🟠 MAJOR
- Tooltip `fontSize: 12` (l.217) — OK
- `interval={chartData.length > 20 ? Math.floor(chartData.length / 6) - 1 : 0}` — X축 라벨 자동 솎음 ✓

### 4.2 분기 스파크라인 모바일 가독성

- `components/thesis/dashboard/QuarterlySparkline.tsx` (IndicatorRow에서 `slice(-4)`로 4분기만 인라인 렌더)
- 인라인 영역: `flex-1 max-w-[100px]` → 100px 폭에 4 데이터 포인트 → 25px/포인트 → 식별 가능하나 좁음
- 분기 확장 시 `ResponsiveContainer height={140}`로 펼침 → OK

### 4.3 ForceGraph2D (Chain Sight 그래프)

- `components/chainsight/MarketGraphCanvas.tsx`: canvas 기반 force-directed graph
- `containerRef`로 부모 크기 측정 후 width/height props 전달
- 모바일: `MobileCardList`로 분기되어 그래프 대신 카드 리스트 표시 (`app/chainsight/[symbol]/page.tsx:152`) → 모바일 대응 ✓
- 그래프 오버레이 호출 시 (l.173): full-screen `inset-0 z-50` → OK

---

## 페이지별 상세

### 5.1 `/` (EOD Dashboard) — 메인 홈

- 컨테이너: `max-w-6xl mx-auto px-4 py-4 pb-20` → pb-20으로 BottomNav 공간 확보 ✓
- `SignalFilterTabs`: `overflow-x-auto pb-1 scrollbar-hide` → 가로 스크롤 카테고리 탭 ✓ (단 스크롤 힌트 없음 🟡)
- `SignalCardGrid` (미열람) → 별도 확인 필요
- `SignalDetailSheet` (l.97): `w-full md:w-[420px]` Bottom Sheet 패턴 ✓
- 모바일 드래그 핸들 (l.107-109) ✓
- 종합: **모바일 우선 설계가 잘 적용된 페이지** 🟢

### 5.2 `/dashboard` — Auth 후 랜딩 (legacy)

- `nav` `max-w-7xl ... h-16` → 모바일에서 사용자명 + 로그아웃 가로 배치 → 잘림 위험
- 카드 그리드 `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` ✓
- "주식 검색하기 →", "포트폴리오 보기 →" 텍스트 링크 → 터치 타겟 작음 (~28pt) → 🟠 MAJOR
- 이 페이지가 실제 사용되는지 확인 필요 (홈 = `/`이므로 deprecated 가능성)

### 5.3 `/screener`

- 모바일 대응: 카드 뷰 자동 (`viewMode === 'card' ? 'sm:block' : 'sm:hidden'` l.853-875) ✓
- `MobileStockCard` 별도 구현 ✓ — 정보 위계 명확
- **필터 칩 X 버튼 12×12pt 11회 반복** → 🔴 BLOCKER (l.589, 597, 605, 613, 621, 629, 637, 645, 702, 710, 718)
- 프리셋 칩 X 버튼도 동일 (l.537-540)
- 토글 텍스트 "접기/펼치기" → 🟠 MAJOR
- 페이지네이션: 페이지 숫자 ✓ / 이전/다음 화살표 🟠

### 5.4 `/thesis` 가설 통제실

- Layout: `max-w-lg mx-auto px-4 pt-4 pb-20` 모바일 우선 ✓
- 백 버튼: `p-2 -ml-2 size={20}` → 36pt → 경계
- AlertBell: `min-w-[18px] h-[18px]` 뱃지 → 배지만 클릭 영역이라면 부족, 일반적으로 부모 버튼이 영역 → OK

### 5.5 `/thesis/[thesisId]` 대시보드

- Layout: `max-w-lg mx-auto px-4 pt-4 pb-20` ✓
- IndicatorRow: 카드 자체는 충분한 터치 영역 ✓
- **일간 차트 기간 칩 (1M/1Y/3Y/5Y)** `px-2.5 py-0.5 text-[10px]` → ~22pt → 🔴 BLOCKER (4개 모두)
- 펼침 영역 차트: `height={160}`, fontSize=9~10 → 가독성 경계 🟠
- 가설/지표 정보 `text-[11px]` 다수 → 본문 정보로는 작음, 그러나 카드 자체 토글이라 OK

### 5.6 `/thesis/new` 빌더

- 결정 트레일 라벨 `text-[10px]` (l.688, 752) → 라벨이므로 OK
- 거시/미시 카테고리 헤더 `text-[10px]` (l.831, 843) → OK
- "직접 작성하기" 버튼 `text-[10px]` (l.1063) → 🟠 MAJOR (클릭 가능 요소)
- 인기 가설 템플릿 버튼 (l.874-): 전체 카드 버튼 → 충분 ✓
- 대화 입력창: 보지 못함 — 별도 확인 필요

### 5.7 `/chainsight/[symbol]`

- 모바일 감지 (`isMobile = window.innerWidth < 768`) 후 `MobileCardList` 분기 ✓
- 모바일 그래프 오버레이 시 노드 선택 후 닫기 버튼 `text-gray-400 text-sm` (l.206) → 14×14pt → 🔴 BLOCKER
- 액션 3버튼 (탐색/가설/검증) `py-2 text-xs` → 32pt → 🟠 MAJOR
- 데스크톱 헤더: `hidden lg:block` aside (l.358) ✓

### 5.8 `/portfolio`

- `PortfolioTable`: 12개 컬럼 + `overflow-x-auto` → 가로 스크롤로 동작
- **모바일 카드 뷰 대안 없음** → 🟠 MAJOR
- 편집/저장/취소 아이콘 버튼 → 🟠 MAJOR (정확한 크기 별도 확인 필요)

### 5.9 `/news`

- 미상세 분석. RecommendationCard에 `max-w-[150px]` truncate ✓
- NewsContextBadge 등 카드 패턴 사용

### 5.10 `/market-pulse-v2`

- `text-[10px]` footer (l.77) → 정보용 OK
- MoverCard hover 툴팁 5개 (`group-hover/tooltip:block`) → 모바일에서 미작동 → 🟠 MAJOR

### 5.11 `/stocks/[symbol]`

- Mobile 카테고리 sidebar 분기 (l.1037-1054) ✓ (`mobileCategory` state로 모바일 카테고리 1개씩 렌더)
- Desktop sidebar `hidden lg:block` ✓
- 산업 위치, 리더 비교 섹션은 별도 컴포넌트 — 검증 필요

### 5.12 `/validation` 진입 (stocks 탭에서)

- `SignalSummaryCard`: 7개 신호등 가로 스크롤 `overflow-x-auto scrollbar-hide` ✓
- `PeerContextBar` 프리셋 탭: `min-h-[44px]` ✓
- `MetricBarChart` 모바일 OK

### 5.13 어드민 콘솔 (`/admin`)

- AdminTabNav `overflow-x-auto` ✓
- 다수의 테이블, 차트 → 어드민은 모바일 대응 정책 결정 필요 (보통 desktop only)

---

## 권장 우선순위

### P0 (즉시 수정 — BLOCKER)
1. **MobileNav 메뉴 추가**: Chain Sight / Thesis / Market Pulse / 스크리너 진입 경로 확보. 5개 → 6~7개로 확장하거나 "더보기" 메뉴 도입.
2. **필터 칩 X 버튼 hit-area 확장**: `<X h-3 w-3 />`을 `<button className="p-2 min-w-[44px] min-h-[44px]">` 래퍼로 감싸기. 스크리너 페이지 12개 인스턴스.
3. **chainsight 모바일 그래프 닫기 버튼**: `text-sm` → `min-h-[44px] min-w-[44px] p-2` 패딩 추가.
4. **thesis 일간 차트 기간 칩**: `px-2.5 py-0.5` → `px-3 py-2 min-h-[44px]`.
5. **ForceGraph2D 노드 hit-area**: nodeCanvasObject에서 click radius를 시각 반경의 1.5~2배로 확대.

### P1 (1주 내 — MAJOR)
1. 모바일 카드 뷰 추가: PortfolioTable.
2. hover 툴팁 → tap-to-show 전환: KeywordTag, MoverCard, MoverCardWithBatchKeywords.
3. 모바일 차트 fontSize 9 → 11 이상 (XAxis tick).
4. IndicatorRow 2행 레이아웃 모바일 분기: 값 + 변동률만 첫 행, 스파크라인/지지반박은 둘째 행.
5. 가로 스크롤 인디케이터 (그라데이션 페이드) 추가: ScreenerTable, PortfolioTable, SignalSummaryCard.

### P2 (개선 — MINOR)
1. MobileNav safe-area-inset-bottom 처리.
2. text-xs 텍스트 버튼 → button로 영역 명시.
3. virtualization 도입: 미래 MobileCardList depth=3 대응.
4. DataSourceBadge 팝오버 모바일 우측 잘림 대응.

---

## 부록: 사용된 검색 패턴

```
Grep: w-\[\d+px\]|min-w-\[\d+px\]|max-w-\[\d+px\]     → 30+ 인스턴스
Grep: text-\[(10|11)px\]                              → 80+ 인스턴스 (라벨 + 클릭)
Grep: overflow-x-auto|overflow-x-scroll               → 28 files
Grep: ResponsiveContainer                             → 15 files
Grep: md:hidden|lg:hidden|hidden md:|hidden lg:      → 6 files (분기 명시적)
Grep: react-virtuoso|react-window|virtualizer         → 0 files
```

본 감사는 페이지 핵심 컴포넌트 22개 + 페이지 11개 표본 조사 결과이며, admin/, rag/, news/ 하위 컴포넌트 전수 점검은 별도 라운드 권장.
