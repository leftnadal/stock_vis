# 모바일 UX 감사 보고서

**감사일**: 2026-04-24
**범위**: `frontend/` 전체 (페이지 23개, 컴포넌트 240+ 개)
**기준 뷰포트**: 모바일 375px (iPhone SE), Apple HIG 최소 터치 타겟 44×44pt
**감사 방법**: 정적 분석 (파일 읽기 + grep). 실제 디바이스/에뮬레이터 검증은 미수행.

---

## 요약

| 심각도 | 개수 | 비고 |
|--------|------|------|
| **BLOCKER** | 5 | 모바일 사용자에게 기능 자체가 동작하지 않거나 접근 불가 |
| **MAJOR** | 14 | Apple HIG 44px 터치 타겟 미달, 핵심 인터랙션 손상 |
| **MINOR** | 9 | 가독성·정보 밀도 저하, 즉각적 차단은 아님 |
| **합계** | **28** | |

**전체 평가**: 모바일 대응이 **이원화**되어 있다. `/` (EOD), `/chainsight/[symbol]`, `/thesis/[thesisId]` 는 모바일 우선 설계가 잘 되어 있고 카드 뷰/바텀 시트 패턴을 사용한다. 반면 `/portfolio`(PortfolioTable), `/screener`(필터 UI), validation 카테고리 사이드바, header/admin 영역은 데스크톱 가정이 강하다. **자동 디바이스 분기는 일부만 구현**되어 있어 `375px`에서 호환성 등급은 컴포넌트별로 큰 편차가 있다.

---

## 1. 반응형 누락

### 1.1 고정 폭 (w-[NNpx], min-w-[NNpx]) 사용 분석

총 50건의 고정 폭 사용을 확인했다. 대부분 **min-w-[18~120px]** 수준이라 375px 뷰포트에서 직접적 overflow를 일으키지 않으나, **누적 가로 합산**에서 깨지는 경우가 다수.

| 컴포넌트 | 위치 | 폭 | 모바일 영향 | 심각도 |
|---------|-----|----|---------|------|
| `IndicatorRow.tsx:110-132` | 값(60) + 변동률(120) + 스파크라인(100) + 라벨(auto) | 합산 ~290px+ ml-auto | 375px에서 padding 32px 제외하면 343px → 빠듯, ml-auto가 사라질 수 있음 | MAJOR |
| `SignalSummaryCard.tsx:40` | `min-w-[72px]` 카드 | 5개 나열 시 360px | 거의 fit, 작은 화면(<360px)에서 깨짐 | MINOR |
| `StockRow.tsx:55,66` | `max-w-[140px]` 회사명 + `min-w-[72px]` 가격 | OK | - | OK |
| `ChatBubble.tsx:14` | `min-h-[44px]` | ✓ HIG 준수 | - | OK |
| `OptionButton.tsx:52` | `min-h-[52px]/[56px]` | ✓ HIG 준수 | - | OK |
| `TextInput.tsx:46` | `min-h-[44px] max-h-[120px]` | ✓ HIG 준수 | - | OK |
| `MarketGraphCanvas.tsx:124,134,141` | `h-[400px]` 고정 | 세로는 OK, 가로는 ResizeObserver로 동적 | - | OK |
| `ChainsightPage` (모바일 그래프 오버레이) | `width = canvasSize.w \|\| window.innerWidth` | ✓ 반응형 | - | OK |
| `RAG ChatInterface.tsx:198` | `h-[52px] w-[52px]` 전송 버튼 | ✓ HIG 준수 (52×52) | - | OK |
| `eod/SignalDetailSheet.tsx:97` | `w-full md:w-[420px]` | ✓ 모바일 풀폭, 데스크톱 사이드 | - | OK |
| `eod/SignalFilterTabs.tsx:68` | `min-w-[18px] h-[18px]` 카운트 배지 | 카운트 표시용으로 적절 | - | OK |
| `Pagination.tsx:127` | `min-w-[32px] px-2 py-1.5` 페이지 번호 | 32×32 — HIG 미달 | MAJOR |
| `InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` | 데스크톱 컨테이너 — 문제 X (단, **이 컴포넌트는 layout.tsx에서 import 안 됨 → dead code 가능성**) | MINOR |

### 1.2 sm:/md:/lg: 브레이크포인트 미사용 컴포넌트

총 62개 파일 중 다수가 데스크톱 가정. 다음은 **인터랙션 핵심**임에도 모바일 분기가 전무한 컴포넌트:

| 컴포넌트 | 문제 | 심각도 |
|---------|-----|-----|
| `components/portfolio/PortfolioTable.tsx` | 12개 컬럼 테이블, `min-w-full divide-y` + `overflow-x-auto` 만 적용. 모바일에선 가로 스크롤 강제. **카드 뷰 폴백 없음** (PortfolioPage가 viewMode='table'을 선택하면 모바일에서도 그대로 노출됨) | MAJOR |
| `components/layout/InvestingHeader.tsx` | 전체 컴포넌트가 데스크톱 전용 (top bar, 8개 nav 항목, `max-w-xl` 검색바). md:/sm: 분기 0건. (단, layout.tsx에서 사용 안 함) | MINOR (dead code) |
| `components/validation/CategorySidebar.tsx` | `sticky top-24` 데스크톱 사이드바. 모바일에선 부모(`stocks/[symbol]/page.tsx:1058`)에서 `hidden lg:block`으로 가림 → ✓ 안전 | OK |
| `components/admin/*` | 관리자용이라 우선순위 낮음 | MINOR |

### 1.3 테이블/차트의 가로 스크롤 처리

`overflow-x-auto`를 사용하는 25개 파일 중 **테이블 가로 스크롤은 정상 작동**하지만, 다음 문제가 있다:

- **PortfolioTable** (BL #2): 12개 컬럼을 모바일에서 가로 스크롤로 강제. 일반 사용자가 "수익률" 같은 핵심 정보를 보려면 8번째 컬럼까지 스크롤. 시각적 단서(스크롤 인디케이터, 그라디언트 페이드) 없음. **MAJOR**.
- **ScreenerTable** (`strategy/ScreenerTable.tsx`): 12개 컬럼이지만 **부모 페이지(screener/page.tsx:845)에서 `hidden sm:block`으로 모바일에서 자동 카드 뷰 전환** → ✓ 잘 처리됨.
- **Recharts ResponsiveContainer**: 11개 차트 컴포넌트 모두 `width="100%"` 사용 — ✓ 정상.

---

## 2. 터치 타겟 (Apple HIG 44×44pt 기준)

### 2.1 BLOCKER (터치 자체 불가능)

| # | 컴포넌트 | 라인 | 문제 | 영향 |
|---|---------|------|------|------|
| **B1** | `components/screener/PresetGallery.tsx:192-204` | 사용자 프리셋 삭제 버튼 | `opacity-0 group-hover:opacity-100` — **터치 디바이스에는 hover 이벤트가 없어 영구히 invisible** | 모바일 사용자는 자기가 만든 프리셋을 영영 삭제 불가 |
| **B2** | `components/thesis/dashboard/QuarterlySparkline.tsx:44-62` | 호버 툴팁 | `onMouseEnter/onMouseLeave`만 — 모바일에서 분기 값 확인 불가 | 관제실의 분기 추세 값을 모바일에서 읽을 수 없음 |
| **B3** | `components/layout/MobileNav.tsx:11-15` | `/profile` 링크 | 실제 마이페이지는 `/mypage`. **404 에러** | 모바일 하단 탭 "내정보" 클릭 시 깨짐 |
| **B4** | `components/screener/PresetGallery.tsx:275-282` | `setIsMobile(window.innerWidth < 640)` | useEffect에서 동기 측정 — 첫 렌더에서 `isMobile=false` (SSR 가정). 모바일 브라우저에서 첫 프레임은 잘못된 popover 위치 | 빠르게 탭하면 데스크톱 popover가 화면 밖으로 튐 |
| **B5** | `app/chainsight/[symbol]/page.tsx:114-126` | `setIsMobile(window.innerWidth < 768)` 후 분기 | 위와 동일 — initial render는 desktop layout. **하이드레이션 후 즉시 점프** (CLS) | LCP/CLS 악화 |

### 2.2 MAJOR (HIG 44px 미달, 핵심 인터랙션)

| # | 컴포넌트 | 라인 | 측정값 | 권장 |
|---|---------|------|-------|------|
| **M1** | `thesis/dashboard/IndicatorRow.tsx:179-190` | 차트 기간 선택자 (1M/1Y/3Y/5Y) | `px-2.5 py-0.5 text-[10px]` ≈ **22×22px** | 관제실 핵심 컨트롤. py-2 text-sm으로 |
| **M2** | `validation/PeerContextBar.tsx:36-50` | Peer 프리셋 탭 (6개 + 직접설정) | `px-3 py-1 text-xs` ≈ **24×24px** | 비교 기준 변경이 핵심 인터랙션인데 너무 작음 |
| **M3** | `validation/CategorySidebar.tsx:48-61` | 카테고리 점프 버튼 | `px-3 py-2 text-sm` ≈ **36×36px** | (lg:block만 노출 → 데스크톱 전용으로 안전) |
| **M4** | `screener/AdvancedFilterPanel.tsx:236-271` | 카테고리 칩 (인기/펀더멘탈/기술/모멘텀) | `px-3 py-1.5 text-xs` ≈ **28×28px** | py-2.5 + text-sm |
| **M5** | `screener/AdvancedFilterPanel.tsx:121-140` | 숫자 입력 + X 삭제 | input `py-1.5` ≈ 32px, X 버튼 `p-1 + h-3.5` ≈ **20px** | input py-3, X button p-2.5 |
| **M6** | `layout/Header.tsx:156-161` | 햄버거 메뉴 | `p-2 + h-6 w-6` ≈ **40×40px** | p-3 또는 명시적 min-h-11 |
| **M7** | `screener/Pagination.tsx:94-158` | 페이지 화살표 + 번호 | 화살표 `p-1.5 + h-4` ≈ 28px, 번호 `min-w-[32px] py-1.5` ≈ **32×32px** | min-w-11 h-11 |
| **M8** | `screener/Pagination.tsx:165-173` | 페이지 크기 select | `py-1.5 text-sm` ≈ 32px | py-3 |
| **M9** | `screener/page.tsx:587-721` | 필터 칩 X 버튼 | `<X className="h-3 w-3"/>` 안에 padding 없음 ≈ **12×12px** | 칩 자체 클릭 = 삭제로 변경하거나 X를 p-2로 감쌈 |
| **M10** | `screener/page.tsx:752-789` | 뷰모드/AI키워드/테제 (아이콘 only) | `p-1.5` ≈ **28×28px** | 모바일에서 hidden 처리 또는 p-3 |
| **M11** | `chainsight/MobileCardList.tsx:166-184` | 가설생성/탐색/검증 CTA | `py-1.5 text-xs` ≈ **28~32px** | 모바일 진입의 핵심 동선 — py-3 필요 |
| **M12** | `chainsight/[symbol]/page.tsx:208-227` | 모바일 그래프 바텀시트 CTA | `py-2 text-xs` ≈ **32px** | py-3 |
| **M13** | `eod/SignalDetailSheet.tsx:213-219` | 정렬 선택 버튼 | `px-3 py-1 text-xs` ≈ **24px** | py-2.5 |
| **M14** | `eod/SignalFilterTabs.tsx:44-78` | 카테고리 칩 (전체/모멘텀/거래량…) | `px-3 py-1.5 text-sm` ≈ **32px** | py-2.5 또는 min-h-11 |

### 2.3 작은 글씨 클릭 요소 (text-[10px]/[11px])

| 컴포넌트 | 사용 | 모바일 가독성 |
|---------|-----|--------------|
| `IndicatorRow.tsx:95,118,148,161,167` | 날짜·라벨·전제·설명 (정적) | 가독성만 문제, 클릭 X |
| `IndicatorRow.tsx:182` | **차트 기간 버튼** | 클릭 + 작은 글씨 = 이중 문제 (M1과 중복) |
| `eod/StockRow.tsx:89,92` | 시그널 라벨, 거래량 (정적) | OK |
| `eod/SignalFilterTabs.tsx:68` | 카운트 배지 (정적) | OK |
| `eod/SignalDetailSheet.tsx:188,197` | Chain Sight 섹터 링크 | text-[10px] 링크 — **너무 작음** (MINOR) |
| `screener/ScreenerTable.tsx:209` | 회사명 (정적) | OK |
| `chainsight/MobileCardList.tsx:149-161` | sector/growth_stage/capital_dna 태그 (정적) | OK |
| `news/AlertBadge.tsx:29` | 알림 카운트 배지 (정적) | OK |
| `validation/PeerContextBar.tsx:90` | 안내문 (정적) | OK |
| `QuarterlySparkline.tsx:54` | **분기 라벨 text-[8px]** | **너무 작음** (MINOR) |

---

## 3. 네비게이션

### 3.1 사이드바/헤더 모바일 대응

| 컴포넌트 | 모바일 대응 | 평가 |
|---------|-----------|------|
| `layout/Header.tsx` | ✓ 햄버거 메뉴 + 전체 nav 폴딩 (158-256). 단 햄버거 자체가 40×40 (M6). | OK |
| `layout/MobileNav.tsx` | ✓ 5개 항목 bottom nav, `md:hidden` z-50. 단 `/profile` 링크 깨짐 (B3). | BLOCKER |
| `layout/InvestingHeader.tsx` | ✗ 데스크톱 전용. 단 layout.tsx에서 import 안 함 → **dead code 정리 필요** | MINOR |
| Thesis 헤더 (`thesis/(list)/page.tsx`, `[thesisId]/page.tsx`) | ✓ `max-w-lg mx-auto` 모바일 우선. | OK |
| Chainsight 헤더 (`chainsight/[symbol]/page.tsx`) | ✓ isMobile 분기로 별도 헤더 (155-161). 단 isMobile 초기값 false (B5). | BLOCKER |
| Stocks 헤더 (`stocks/[symbol]/page.tsx`) | L1 `px-5 py-2 text-sm` ≈ 36px (382-398), L2 `pb-3 text-sm` ≈ 28px (404-417). `flex space-x-2/6` — 모바일에서 7+ 탭 시 overflow 발생 가능, **overflow-x-auto 처리 없음** | MAJOR |
| Admin 탭 (`admin/AdminTabNav.tsx`) | overflow-x-auto 사용 | OK |

### 3.2 Bottom Navigation

`components/layout/MobileNav.tsx` 존재 — `md:hidden` 5개 항목 (홈/종목/뉴스/포트폴리오/내정보).

**문제**:
- `/profile` 라우트 미존재 (B3 BLOCKER)
- "종목" → `/stocks` (목록 페이지) 로 가는데 실제 `app/stocks/page.tsx` 가 존재하는지 미검증 — `app/stocks/[symbol]/page.tsx`만 발견됨 → **추가 라우팅 검증 필요**
- Chain Sight, 가설(Thesis), Market Pulse, 스크리너가 bottom nav에 없음 — **핵심 기능 5개가 햄버거 안에만 있어 발견성 낮음**

### 3.3 긴 목록 virtualization

`react-window`, `react-virtual`, `virtuoso` **모두 미사용** (npm 검색 결과 0건).

영향 분석:
- `screener/page.tsx`: 페이지당 50/100건 제한 (`pageSize`) → DOM 노드 ~50 → 모바일 부담 적음
- `eod/SignalDetailSheet.tsx`: 시그널당 종목 수 ~10-30개 → OK
- `chainsight/MobileCardList.tsx`: depth 3까지 노드 100+ 가능 → **리스트 길어지면 스크롤 jank 우려** (MINOR)
- `news/page.tsx`: 페이지네이션 미확인 — 추가 조사 필요
- `validation` 카테고리 섹션: 카테고리당 ~5-15 메트릭 → OK

---

## 4. 차트/그래프

### 4.1 Recharts ResponsiveContainer 사용 현황

11개 차트 컴포넌트 전수 조사 결과 **모두 `<ResponsiveContainer width="100%" height={...}>` 패턴 준수**:

| 파일 | 차트 | 높이 | 모바일 가독성 |
|------|------|------|--------------|
| `thesis/dashboard/IndicatorRow.tsx:197,235` | AreaChart (일간/분기) | 160px / 140px | OK — fontSize 9-10 X축 주의 |
| `thesis/dashboard/IndividualMiniCharts.tsx` | 미니 차트 | - | OK |
| `validation/MetricBarChart.tsx` | BarChart | - | OK |
| `admin/news/MLTrendChart.tsx:89` | `h-[200px]` | 200px | OK |
| `screener/SectorHeatmap.tsx:216` | Treemap | 400px | **`width<60` 조건으로 작은 타일 텍스트 생략** ✓, 단 모바일에선 모든 타일이 작아져서 라벨 사라질 가능성 (MAJOR) |
| `stock/StockChart.tsx` | 차트 | - | OK |
| `news/SentimentChart.tsx` | 차트 | - | OK |
| `macro/YieldCurveChart.tsx` | 차트 | - | OK |
| `portfolio/PortfolioChart.tsx:77,97` | PieChart/BarChart | 400px | **PieChart label `${entry.name} (${percent}%)` 길어서 모바일에서 잘림**, BarChart `tick fontSize:12` X축 라벨 -45도 → OK |
| `charts/StockPriceChart.tsx:272` | LineChart/AreaChart/Candlestick | 400px | **차트 타입 버튼 px-3 py-1 text-sm ≈ 32px (M14 유사)** + `cursor-pointer` 안 보이는 탭 동작 검증 안 됨 |

### 4.2 분기 스파크라인 모바일 가독성

`thesis/dashboard/QuarterlySparkline.tsx`:
- 컨테이너 `h-10` (40px) × 가로는 부모의 `flex-1 max-w-[100px]` (IndicatorRow:132)
- 4분기 표시 시 각 막대 ~20px 폭 — OK
- 20분기 펼침 시 각 막대 ~5px — **터치/호버로 개별 분기 선택 불가**
- 라벨 `text-[8px]` (54) — 모바일에서 사실상 비가독
- **호버 툴팁만 존재 → 모바일에서 값 확인 불가** (B2 BLOCKER)

### 4.3 Force Graph (Chain Sight)

`components/chainsight/MarketGraphCanvas.tsx` + `GraphCanvas.tsx`:
- `react-force-graph-2d` SSR 불가 → dynamic import ✓
- ResizeObserver로 너비 추적 ✓
- 노드 크기 6-16px (NODE_SIZE_MAP: sm=6, md=8, lg=11, xl=14, center=16)
- **노드 터치 타겟이 6-16px로 모두 44pt 미달** → 작은 노드 클릭 어려움
- 모바일에서는 `app/chainsight/[symbol]/page.tsx:152-170`에서 `MobileCardList`로 폴백 → ✓ 좋은 대응
- 단 isMobile 초기값 false 문제 (B5)

---

## 5. 페이지별 상세

### 5.1 `/` (EOD Dashboard) — `app/page.tsx`

- ✓ `max-w-6xl mx-auto px-4` 모바일 친화
- ✓ `pb-20 md:pb-0` (MobileNav 가림 회피)
- ✓ SignalCardGrid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` 반응형
- ⚠ SignalFilterTabs `py-1.5` 32px (M14)
- ⚠ SignalDetailSheet 정렬 버튼 24px (M13)
- ⚠ 시트 내 섹터 링크 text-[10px] (MINOR)
- **종합**: MOBILE READY (8/10)

### 5.2 `/screener`

- ✓ Market Breadth + Sector Heatmap `grid-cols-1 lg:grid-cols-3` 반응형
- ✓ 결과 영역 `viewMode === 'card'` 모바일 자동 전환 (854-875)
- ⚠ AdvancedFilterPanel 카테고리 탭 28px, 입력 32px (M4-M5)
- ⚠ PresetGallery 삭제 버튼 hover-only (B1)
- ⚠ 필터 칩 X 12px (M9)
- ⚠ 헤더 액션 버튼 28px (M10)
- ⚠ Pagination 컨트롤 28-32px (M7-M8)
- ⚠ SectorHeatmap Treemap 모바일에서 라벨 사라짐
- ⚠ Show/Hide 프리셋 토글, AI 키워드/테제 텍스트 `hidden sm:inline` ✓
- **종합**: PARTIAL READY (5/10) — 결과 영역은 좋으나 컨트롤이 모두 작음

### 5.3 `/portfolio` — `app/portfolio/page.tsx`

- ✓ `max-w-7xl px-4 sm:px-6 lg:px-8` 컨테이너
- ✓ `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` Stock Card 그리드
- ✗ **PortfolioTable 사용 시 12 컬럼이 가로 스크롤로 밀림** (테이블 모드는 desktop 전용 구현인데 토글이 모바일에서도 노출됨)
- ⚠ 차트 토글, 뷰 토글 버튼 px-3 py-1.5 ≈ 32px (M14 유사)
- ⚠ "종목 추가" 버튼 px-4 py-2 ≈ 40px (HIG에 4px 부족)
- **종합**: PARTIAL READY (6/10) — Grid 모드는 OK, Table 모드는 모바일에서 사용성 저하

### 5.4 `/thesis/[thesisId]` (관제실)

- ✓ `max-w-lg mx-auto px-4 pt-4 pb-20` 모바일 우선 ✨ (BEST PRACTICE)
- ✓ ThesisLayout `bg-gray-950` 다크 테마, Toaster `bottom-center`
- ✓ IndicatorRow 메인 토글 행 `px-4 py-3` ≈ 48px ✓
- ✗ 펼친 후 차트 기간 선택자 22px (M1)
- ✗ QuarterlySparkline 호버-only (B2)
- ⚠ 펼침 영역 description/recommendation_reason text-[11px] — 가독성 (MINOR)
- ⚠ 가설 마감 버튼 py-3 ✓ HIG 충족
- **종합**: MOSTLY READY (7/10) — 레이아웃은 모범, 차트 컨트롤만 보강 필요

### 5.5 `/chainsight/[symbol]`

- ✓ isMobile 분기로 MobileCardList vs 3-panel 데스크톱
- ✓ MobileCardList 카드 본체 `p-4` 적절, 카테고리 탭 `overflow-x-auto`
- ✗ isMobile 초기값 false → 첫 프레임 데스크톱 (B5)
- ✗ MobileCardList CTA 28-32px (M11), 그래프 오버레이 CTA 32px (M12)
- ⚠ 모바일 그래프 오버레이의 노드 터치 타겟 6-16px (작음)
- ⚠ 그래프 오버레이 닫기 버튼 px-3 py-1 text-sm ≈ 32px
- **종합**: MOSTLY READY (7/10) — 폴백 전략은 우수, 디테일 보강 필요

### 5.6 `/stocks/[symbol]` (1078 LOC)

- ✓ `max-w-7xl px-4 sm:px-6 lg:px-8` 컨테이너
- ✓ `grid-cols-1 lg:grid-cols-2` 차트 영역
- ✗ L1 탭 `<nav className="flex space-x-2">` `px-5 py-2` ≈ 36px, 3개 탭이라 OK
- ✗ L2 탭 `<nav className="flex space-x-6">` `pb-3` ≈ 28px, **5개 탭이 375px 화면에 안 맞아 잘림** (overflow-x-auto 없음) — MAJOR
- ✓ Validation 카테고리는 `mobileCategory` 상태로 모바일 분기 (1056) — `lg:block`
- ⚠ PeerContextBar preset 탭 24px (M2)
- ⚠ 데이터 동기화 상태/배지가 작은 텍스트
- ⚠ Recharts 차트들 모두 ResponsiveContainer 사용 ✓
- **종합**: PARTIAL READY (6/10)

### 5.7 `/dashboard`

- ✓ `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 카드
- ⚠ "보기 →" 링크 px 0 + text-sm — 터치 타겟 ~20px (MINOR)
- ⚠ 로그아웃 버튼 px-3 py-2 text-sm ≈ 36px
- **종합**: MOSTLY READY (7/10)

### 5.8 `/thesis/(list)`, `/thesis/new`, `/thesis/[id]/indicators`, `/thesis/[id]/close`

- ✓ ThesisLayout 모바일 우선
- ✓ ChatBubble/OptionButton/TextInput 모두 min-h-44~56 ✓ HIG 준수
- 별도 큰 이슈 없음 (검토 깊이 제한)

### 5.9 `/news`, `/market-pulse`, `/watchlist`, `/ai-analysis`, `/admin`, `/login`, `/signup`, `/mypage`

- 검토 깊이 제한. 일관된 패턴은 `max-w-7xl px-4`로 보이며 별도 모바일 분기는 부분적.
- Admin 영역은 우선순위 낮음.

### 5.10 Header / MobileNav (전역)

- ✓ MobileNav `md:hidden` 5개 bottom nav
- ✗ `/profile` 깨진 링크 (B3)
- ⚠ 햄버거 40×40 (M6)
- ⚠ 핵심 기능 5개(Chain Sight, Thesis, Market Pulse, 스크리너, 마이페이지)가 bottom nav에 없음 — IA 재검토 필요
- ⚠ InvestingHeader.tsx 사용처 없음 → dead code 정리

---

## 권장 우선순위

### P0 (즉시 수정 — BLOCKER 5건)
1. **B3** `MobileNav` 의 `/profile` → `/mypage` 수정
2. **B1** `PresetGallery` 삭제 버튼 hover-only 패턴 제거 (모바일에선 항상 노출 또는 long-press 메뉴)
3. **B2** `QuarterlySparkline` 에 onClick 추가 + 모바일에서 클릭 시 툴팁 표시
4. **B4/B5** `isMobile` 초기값을 SSR-safe하게 처리 (`useMediaQuery` 또는 CSS-only 분기로)

### P1 (다음 스프린트 — MAJOR 14건)
- M1, M2: 관제실 차트 기간 선택자, validation preset 탭 — 핵심 인터랙션부터
- M11, M12: Chainsight 모바일 CTA — 진입 동선 핵심
- M9: Screener 필터 칩 X 버튼 (사용 빈도 높음)
- L2 탭에 overflow-x-auto 추가
- PortfolioTable에 모바일 카드 폴백 또는 toggle 자동화

### P2 (백로그 — MINOR 9건)
- text-[8px] 분기 라벨 → text-[10px]
- InvestingHeader.tsx 삭제
- Bottom navigation 항목 재구성 검토 (Chain Sight/Thesis 추가)
- Sector Heatmap Treemap 모바일 가독성 개선
- 일부 차트 컴포넌트의 X축 fontSize 조정

---

## 검증 한계 (Disclaimer)

- 정적 코드 분석 기반. 실제 디바이스(iPhone SE/14, Android)에서의 렌더링 검증 미수행.
- Tailwind 클래스의 실제 픽셀 값은 폰트 크기/패딩 추정치 (px-3 py-1 ≈ 24px 기준 line-height 1.5).
- `frontend/components/admin/*`, `news/*`, `market-pulse/*` 는 샘플링만 수행.
- 라우팅 존재 여부 (`/stocks` 목록, `/profile` 등)는 발견된 파일 기준 — `app/stocks/page.tsx` 부재 시 추가 BLOCKER 가능.
