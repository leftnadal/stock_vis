# 모바일 UX 감사 보고서

- **감사일**: 2026-05-21
- **대상**: `frontend/` (Next.js 16, Tailwind, TanStack Query, Recharts)
- **기준 뷰포트**: 375 × 667 (iPhone SE 2nd-gen)
- **터치 타겟 기준**: Apple HIG 44×44pt, Material 48×48dp
- **감사 모드**: 읽기 전용 (코드 변경 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 설명 |
|--------|------|------|
| **BLOCKER** | 4 | 모바일에서 사용 자체가 어려운 핵심 기능 |
| **MAJOR** | 11 | 가독성·조작성을 크게 해치지만 우회 가능 |
| **MINOR** | 7 | 폴리시 / 가독성 개선 권장 |
| **전체** | **22** | |

### BLOCKER 4건
1. **Header 햄버거 비활성 + 모바일 로그인/검색 동선 끊김** — Header.tsx:160 `hidden` 처리 → 모바일에서 로그인 / 종목 검색 진입점 없음
2. **Thesis IndicatorRow 기간 버튼 터치 타겟 부적합** — IndicatorRow.tsx:182 `px-2.5 py-0.5 text-[10px]` ≈ 22×20px (1d/7d/1m/3m 전환 불가)
3. **MoverCard 모든 부가 설명이 hover 의존** — MoverCard.tsx:138~189 `group-hover/tooltip:block` 5건 (Top Mover 카드의 키워드·맥락 설명 모바일에서 완전 미노출)
4. **긴 목록 전체에 가상화 부재** — `react-window/virtualizer/virtuoso` 0건. 종목 리스트, 뉴스 피드, 알림 목록 모두 풀 렌더링 → 모바일 저사양 단말 스크롤 끊김 위험

### MAJOR 주요
- ScreenerTable 모바일 대응 누락 (MobileStockCard는 존재하지만 ScreenerTable이 가로 스크롤만 사용)
- PortfolioTable / StockTable / watchlist `overflow-x-auto`만 — 모바일 전용 카드 뷰 없음
- ChainsightMarketGraphCanvas force-graph 노드는 반지름 10~28px, 모바일 핀치 줌만 의지
- Validation `PeerContextBar` Peer 칩(`px-2 py-0.5`)은 44px 미달 — 단, 프리셋 탭은 44px 보장
- `text-[10px]`, `text-[11px]` 사용 50+ 컴포넌트 (지표/뉴스/관계 카드 메타데이터)
- KeywordTag hover-only 툴팁 — 키워드 정의를 모바일에서 못 봄

### MINOR
- IndicatorCard `p-1` 닫기 버튼 (24~32px)
- ChainStoryFeed/FullPathView 메타 라벨 text-[10px]
- IndividualMiniCharts ResponsiveContainer 사용은 정상, but `height=160` 고정 — 모바일에서도 동일

---

## 1. 반응형 누락

### 1-1. 고정 폭 (`w-[Npx]`, `min-w-[Npx]`)

| 컴포넌트 | 위치 | 패턴 | 모바일(375px)에서 overflow? |
|---------|------|------|---------------------------|
| InvestingHeader | InvestingHeader.tsx:32,55,99 | `max-w-[1400px]` | ✅ 안전 (max만 제한) |
| DataSourceBadge | DataSourceBadge.tsx:171 | `min-w-[200px]` | ⚠️ 우측 정렬 콘텐츠에서 좌측 잘림 가능 |
| MarketGraphCanvas 노드 카드 | MarketGraphCanvas.tsx:676 | `w-[110px] min-h-[68px]` | ✅ 안전 |
| IndicatorRow 값 영역 | IndicatorRow.tsx:110,115,132 | `min-w-[60px] + min-w-[120px] + max-w-[100px]` | ⚠️ 값+변동률+스파크라인+지지/반박 = 약 320px 필요. 모바일 (375-32 padding=343) 빠듯 |
| RAG ChatInterface 전송 버튼 | ChatInterface.tsx:198 | `h-[52px] w-[52px]` | ✅ 44px 초과, OK |
| SignalDetailSheet | SignalDetailSheet.tsx:97 | `w-full md:w-[420px]` | ✅ 모바일 풀 너비 |
| NodeTooltip 라벨 | NodeTooltip.tsx:141 | `max-w-[130px]` | ✅ truncate용 |
| StockRow 종목명 | StockRow.tsx:55,66 | `max-w-[140px], min-w-[72px]` | ✅ truncate용 |
| News RecommendationCard | RecommendationCard.tsx:85 | `max-w-[150px]` | ✅ truncate용 |
| SectorBar | SectorBar.tsx:41 | `max-w-[120px]` | ✅ truncate용 |
| SuggestionChips | SuggestionChips.tsx:40 | `max-w-[150px]` | ✅ truncate용 |
| MarketNewsSection AINewsBriefing 바 | AINewsBriefingCard.tsx:70 | `max-w-[200px]` | ✅ OK |
| ActionButton 라벨 | ActionButton.tsx:68 | `max-w-[200px]` | ✅ truncate용 |
| RelationLegend | RelationLegend.tsx:51 | `max-w-[140px]` | ✅ OK |
| SystemTab/TaskLogViewer/AlertList | 여러 곳 | `max-w-[240~260px]` | ✅ truncate용 |

**판정**: 절대값 폭으로 overflow를 일으키는 컴포넌트는 사실상 없음. 대부분 `max-w-*`로 truncate 안전망. **IndicatorRow의 값 행 누적폭만 모바일에서 빠듯**.

### 1-2. 데스크톱 전용 (브레이크포인트 누락) 컴포넌트

`sm:/md:/lg:` 사용 빈도가 매우 낮음 (전 코드베이스에서 `hidden md:*` / `md:hidden` 등 11개 occurrence, 8개 파일).

| 컴포넌트 | 문제 |
|---------|------|
| `app/admin/page.tsx` 하위 (Admin*) | 모바일 가시 brakepoint 없음, 카드/탭 모두 데스크톱 그리드 가정 |
| `components/chainsight/CategorySection.tsx`, `CategorySidebar.tsx` | 사이드바 패턴 (`md:hidden` 없음) → 모바일에서 사이드바 표시 여부 불명, AskUserQuestion 없이 가정하면 좁아짐 |
| `components/admin/news/MLCompareView.tsx`, `MLTrendChart.tsx` | 그리드/표 데스크톱 가정 |
| `components/screener/ScreenerDashboard.tsx` | `md:hidden` 검색 0건 — MobileStockCard가 존재하지만 라우팅 분기 미확인 |

### 1-3. 테이블 / 가로 스크롤 대응

| 컴포넌트 | 처리 |
|---------|------|
| `components/portfolio/PortfolioTable.tsx:259` | `overflow-x-auto` |
| `components/stocks/StockTable.tsx:34` | `overflow-x-auto` |
| `components/strategy/ScreenerTable.tsx:128` | `overflow-x-auto` (별도 MobileStockCard 존재) |
| `app/watchlist/page.tsx:294` | `overflow-x-auto` |
| `components/admin/news/CollectionStatsTable.tsx` 등 admin 표 | `overflow-x-auto`만 |
| `app/stocks/[symbol]/page.tsx` 재무제표 | `overflow-x-auto`만 |

**판정**: 모든 표가 가로 스크롤은 갖추고 있지만, **모바일 전용 카드 뷰는 ScreenerDashboard 한 곳뿐**. Portfolio/Watchlist/StockDetail 재무제표는 모바일에서 손가락으로 가로 스크롤 + 작은 텍스트 가독 문제 동반.

---

## 2. 터치 타겟

### 2-1. 44px 미달 확인된 클릭 요소

| 컴포넌트 | 위치 | 패턴 | 추정 크기 |
|---------|------|------|----------|
| **Thesis IndicatorRow 기간 버튼** | IndicatorRow.tsx:179~189 | `px-2.5 py-0.5 text-[10px]` | ~22×20px **(BLOCKER)** |
| **Thesis AlertCard 닫기 버튼** | AlertCard.tsx:57 | `text-[10px] px-? py-? border` | 약 26×20px |
| **Thesis IndicatorCard 액션 버튼** | IndicatorCard.tsx:61 | `p-1` + lucide-react 기본 16px | 24×24px |
| **Thesis builder OptionButton 설명 아이콘** | OptionButton.tsx:72 | `p-1` (sm:flex로 데스크톱만 표시) | 모바일에서는 숨김 (괜찮음, 대신 안내문 노출됨) |
| **Thesis dashboard DashboardPageHeader 뒤로** | DashboardPageHeader.tsx:21,30 | `p-1` + 아이콘 ≈ 24×24px | 28~32px |
| **Thesis builder PremiseCard 닫기** | PremiseCard.tsx:35 | `p-1` 닫기 X | 24~28px |
| **Thesis builder NewsSelector 뒤로 가기** | NewsSelector.tsx:142 | `p-1` | 24~28px |
| **Validation PeerContextBar Peer 칩** | PeerContextBar.tsx:128 | `px-2 py-0.5 text-xs` | ~26×22px (정보 표시만이라 클릭 없으면 OK, but 직접 설정 시 추가 액션 가능성) |
| **Validation PeerContextBar `peer 목록 보기/접기`** | PeerContextBar.tsx:118 | `text-xs` 텍스트 링크 | 16~20px 높이 (BLOCKER 직전) |
| **AdvancedFilterPanel 카운트 칩** | AdvancedFilterPanel.tsx:247,266 | `px-1.5 text-[10px]` | 표시 only 추정 |
| **KeywordTag (size=sm)** | KeywordTag.tsx:42 | `px-2 py-0.5 text-[10px]` | ~26×20px |
| **MoverCard tooltip trigger들** | MoverCard.tsx:138~ | hover trigger | 모바일은 hover 자체가 없음 → 정보 미노출 **(BLOCKER 3)** |
| **ChainStoryFeed 메타 배지** | ChainStoryFeed.tsx:108,111 | `text-[10px] px-1.5 py-0.5` | 표시 only |
| **Thesis SuggestionCard 액션** | SuggestionCard.tsx:45,51 | `px-2 py-0.5 / px-1.5 py-0.5` | ~26×22px (클릭이라면 미달) |

### 2-2. 44px 보장된 부분 (긍정)

- MobileNav 모든 링크: `min-h-[44px] py-2` + h-16 nav (MobileNav.tsx:34)
- PeerContextBar 프리셋 탭: `min-h-[44px] px-4 py-2` (PeerContextBar.tsx:40,54)
- Pagination: `min-w-[44px] min-h-[44px]` (Pagination.tsx:127)
- SignalSummaryCard 카드 버튼: `min-w-[72px] min-h-[44px]` (SignalSummaryCard.tsx:41)
- ScreenerTable 외부 링크: `min-h-[44px] min-w-[44px]` (ScreenerTable.tsx:323)
- Header 햄버거(현재 hidden): `min-h-[44px] min-w-[44px]` 준비됨
- ChatBubble: `min-h-[44px]` (ChatBubble.tsx:14)
- StockChart 기간 탭: `min-h-[44px] px-4 py-2` (StockChart 243/252/261)

→ **44px 가이드를 따로 인지하고 적용한 흔적이 보임**. 단 thesis 대시보드 내부 인터랙션(기간 셀렉터·옵션 버튼)에는 일관 적용 안 됨.

### 2-3. 사용자 요청 중점 영역 결과

- **Thesis 관제실 지표 카드** → BLOCKER: IndicatorRow 기간 버튼 22×20px
- **Validation 프리셋 탭** → OK: `min-h-[44px]` 적용. 단 같은 컴포넌트 내 Peer 목록 보기/접기 텍스트 링크가 작음 (MAJOR)
- **Chainsight 노드** → MAJOR: force-graph SVG 노드 반지름 10~28px, 핀치 줌 의존. NodeContextMenu와 NodeTooltip은 별도 div로 표시되지만 노드 자체 탭이 어려움

---

## 3. 네비게이션

### 3-1. 사이드바 / 헤더 모바일 대응

| 항목 | 상태 |
|------|------|
| Header 데스크톱 nav | `hidden md:flex` (Header.tsx:42) — 모바일 미표시 ✅ |
| Header 검색 바 | `hidden md:block` (Header.tsx:112) — 모바일 미표시 ⚠️ **로그인된 사용자가 모바일에서 종목 검색 불가** |
| Header 사용자 액션 (로그인/로그아웃) | `hidden md:flex` (Header.tsx:126) — 모바일 미표시 ⚠️ **모바일에서 로그인 버튼 진입 불가** |
| Header 햄버거 | `hidden` (Header.tsx:160) — **항상 비활성** (audit P0 #12 주석으로 의도적이라 명시) |
| `isMenuOpen` 분기 (160~257) | 트리거할 버튼이 없어 **데드 코드** 상태 (BLOCKER) |
| MobileNav | `md:hidden` (MobileNav.tsx:20) — 모바일에서만 표시 ✅ |
| Chainsight CategorySidebar | `md:hidden` 검색 0건 — 모바일 사이드바 정책 불명, 좁아질 위험 (MAJOR) |
| Admin AdminTabNav | 가로 스크롤 (overflow-x-auto) — 작동은 함 |

**BLOCKER 1 결론**: 햄버거 hidden 처리는 의도된 결정이지만 그 결과 **MobileNav에 없는 메뉴 (로그인, 마이페이지, 스크리너, market-pulse)** 접근이 모바일에서 끊김.

> MobileNav에 노출되는 메뉴: 홈 / 종목 / 뉴스 / 포트폴리오 / 내정보
> Header 데스크톱 nav 메뉴: + Chain Sight, Thesis Control, Market Pulse, 스크리너, 마이페이지
> 결과: **모바일 사용자는 Chain Sight / Thesis / Market Pulse / Screener 접근 불가**

### 3-2. Bottom Navigation

- `components/layout/MobileNav.tsx` 존재 — `fixed bottom-0 ... md:hidden z-50` ✅
- 5개 탭, 44px 보장, aria-label 적용 ✅
- 누락 메뉴(위 3-1 참조)로 인해 정보 아키텍처 측면에서 빈약

### 3-3. 긴 목록 가상화

`react-window | react-virtual | virtuoso | virtualizer` **0건**.

| 영향 받는 화면 | 예상 행 수 |
|---------------|-----------|
| StockTable (전체 종목) | 500+ (S&P 500) |
| PortfolioTable | 사용자별 가변 |
| Watchlist | 가변 |
| News 피드 | 50~수백 |
| ScreenerTable | 200~500 |
| Thesis alerts | 가변, 누적 가능 |
| Chainsight RelationCardPanel | 수십 ~ 수백 (peers + holders + supplies + co-mentioned) |

저사양 모바일에서 **스크롤 jank, 메모리 누적** 위험. PR-31~ 작업에서 도입 검토 필요.

---

## 4. 차트 / 그래프

### 4-1. Recharts ResponsiveContainer 적용 상태

`from 'recharts'` 사용 14개 파일 중 **14개 모두 `ResponsiveContainer` 사용** ✅

| 파일 | 비고 |
|------|------|
| charts/StockPriceChart.tsx | OK |
| stock/StockChart.tsx | 기간 탭 44px 보장 |
| portfolio/PortfolioChart.tsx | OK |
| validation/MetricBarChart.tsx | text-[10px] 라벨 (가독성 MINOR) |
| screener/SectorHeatmap.tsx | OK |
| macro/YieldCurveChart.tsx | OK |
| news/SentimentChart.tsx | OK |
| admin/news/MLTrendChart.tsx | OK |
| thesis/dashboard/IndicatorRow.tsx | `<ResponsiveContainer width="100%" height={160}>` (가로 반응, 세로 고정) |
| thesis/dashboard/IndividualMiniCharts.tsx | OK |
| market-pulse-v2/details/*.tsx (4개) | OK |

### 4-2. 분기 스파크라인

- `components/thesis/dashboard/QuarterlySparkline.tsx:33` `h-10` (40px) — 모바일 가독 가능
- 인라인 사용 시 `max-w-[100px]` (IndicatorRow.tsx:132) — 모바일에서 4분기 막대 명확히 분간 어려움. 호버 툴팁 `text-[10px]` (QuarterlySparkline.tsx:62) → **모바일에서 hover 없음 → 값 확인 경로 부재** (MAJOR)

### 4-3. 차트 높이 고정

거의 모든 ResponsiveContainer가 `height={N}` 고정 픽셀 사용. 모바일에서도 동일 높이라 가로 압축이 더 두드러짐. 가독성 영향은 일반적으로 허용 범위지만, IndividualMiniCharts나 검증 차트는 비율로 전환 가능.

---

## 5. 페이지별 상세

### 5-1. `app/page.tsx` (홈 / EOD Dashboard)

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| SignalFilterTabs 알림 배지 `text-[11px]` | SignalFilterTabs.tsx:68 | MINOR |
| StockRow truncate 폭 `max-w-[140px]` | StockRow.tsx:55 | ✅ |
| StockRow 변동률 표기 `min-w-[72px]` | StockRow.tsx:66 | ✅ |
| EOD 시그널 카드 전체 그리드의 모바일 컬럼 수 미확인 | SignalCardGrid.tsx | (확인 필요) |

### 5-2. `app/thesis/[thesisId]/page.tsx` (관제실)

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| 기간 토글 버튼 `px-2.5 py-0.5 text-[10px]` | IndicatorRow.tsx:182 | **BLOCKER** |
| 값 + 변동률 + 스파크라인 + 지지/반박 4컬럼 가로 누적 | IndicatorRow.tsx:108~144 | MAJOR (모바일 빠듯) |
| 펼침 영역 `text-[11px]` 설명 본문 | IndicatorRow.tsx:161,167 | MINOR |
| QuarterlySparkline hover-only 값 표시 | QuarterlySparkline.tsx:62 | MAJOR |
| RealValueIndicatorCard `text-[10px]` 메타 라인 3개 | RealValueIndicatorCard.tsx:38,76,83 | MINOR |
| AddIndicatorSheet 옵션 칩 `px-2.5 py-2` + `text-[10px]` | AddIndicatorSheet.tsx:226,251,254 | MAJOR (옵션 칩 클릭) |
| AISummarySection 메타 `text-[10px]` | AISummarySection.tsx:24 | MINOR |
| 알림 마감 페이지 AlertCard 닫기 `text-[10px]` | AlertCard.tsx:57 | MAJOR |
| MoonPhase / ArrowIndicator 라벨 가독 | common/MoonPhase.tsx, ArrowIndicator.tsx | (UI 자체는 시각 패턴, 모바일 OK) |

### 5-3. `app/thesis/new/page.tsx` (대화형 빌더)

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| OptionButton 데스크톱 전용 설명 아이콘 `hidden sm:flex` | OptionButton.tsx:72 | ✅ 모바일은 안내 텍스트로 대체됨 |
| OptionButton 모바일 안내 `text-[10px]` "꾹 누르면 설명" | OptionButton.tsx:66 | MINOR (텍스트 작음, 단 정보 노출은 됨) |
| SuggestionCard 액션 칩 `px-1.5 py-0.5 text-[10px]` | SuggestionCard.tsx:45,51 | MAJOR |
| ChatBubble `min-h-[44px]` 적용 | ChatBubble.tsx:14 | ✅ |

### 5-4. `app/chainsight/page.tsx` & `[symbol]/page.tsx`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| force-graph 노드 (반지름 10~28px) | MarketGraphCanvas.tsx:66 | MAJOR (핀치 줌 의존) |
| RelationFilterChips `md:hidden` 패턴 사용 | RelationFilterChips.tsx | ✅ (반응형 분기 있음) |
| RelationCardPanel `text-[10px]` 관계 타입 배지 | RelationCardPanel.tsx:273,289 | MINOR |
| ChainStoryFeed 메타 배지 `text-[10px]` | ChainStoryFeed.tsx:108~122 | MINOR |
| FullPathView / TracePathView `text-[10px]` 다수 | FullPathView.tsx:182,287; TracePathView.tsx:66 | MINOR |
| MobileCardList 존재 (전용 모바일 뷰) | MobileCardList.tsx | ✅ |
| CategorySidebar 모바일 정책 미정 | CategorySidebar.tsx | MAJOR (확인 필요) |
| 인기 섹터 카드 `w-[110px] min-h-[68px]` | MarketGraphCanvas.tsx:676 | ✅ |

### 5-5. `app/screener/page.tsx`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| ScreenerTable `overflow-x-auto` + MobileStockCard 존재 | ScreenerTable.tsx:128 / MobileStockCard.tsx | ⚠️ ScreenerDashboard에서 모바일 분기 라우팅 미확인 |
| MobileStockCard 메트릭 라벨 `text-[10px]` 다수 | MobileStockCard.tsx:166,172,178 | MINOR |
| AdvancedFilterPanel 카운트 칩 `text-[10px]` | AdvancedFilterPanel.tsx:247,266 | MINOR |
| PresetGallery `text-[10px]` (rank 배지, action) | PresetGallery.tsx:184,218,230,241 | MINOR |

### 5-6. `app/portfolio/page.tsx`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| PortfolioTable overflow-x-auto만, 모바일 카드 뷰 없음 | PortfolioTable.tsx:259 | MAJOR |

### 5-7. `app/stocks/[symbol]/page.tsx`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| 재무제표 표 overflow-x-auto만 | stocks/[symbol]/page.tsx:294 | MAJOR |
| StockChart 기간 탭 44px 보장 | StockChart.tsx:243,252,261 | ✅ |

### 5-8. `app/news/page.tsx`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| InterestSelector 카테고리 라벨 `text-[10px]` | InterestSelector.tsx:96 | MINOR |
| RecommendationCard truncate OK | RecommendationCard.tsx:85 | ✅ |
| AINewsBriefingCard `text-[10px]` 모델 라벨 | AINewsBriefingCard.tsx:296 | MINOR |
| 가상화 없음 → 50+ 기사 스크롤 부담 | (전반) | MAJOR |

### 5-9. `app/market-pulse/page.tsx` & `market-pulse-v2/`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| MoverCard / MoverCardWithBatchKeywords 5개 tooltip 모두 hover-only | MoverCard.tsx:138~189 (×5), Batch 145~196 (×5) | **BLOCKER** (모바일에서 카드 본 뜻 절반 이상 못 봄) |
| MarketMoversSection 메타 `text-[10px]` | MarketMoversSection.tsx:59 | MINOR |
| MarketNewsSection 메타 `text-[10px]` | MarketNewsSection.tsx:186 | MINOR |
| ResponsiveContainer 사용 ✅ | market-pulse-v2/details/*.tsx | ✅ |

### 5-10. `app/watchlist/page.tsx`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| overflow-x-auto만 (모바일 카드 없음) | watchlist/page.tsx:294 | MAJOR |

### 5-11. `app/admin/page.tsx`

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| 다수 표 overflow-x-auto만 | admin/news/CollectionStatsTable.tsx, SystemTab.tsx, ScreenerTab.tsx, NewsTab.tsx | MAJOR (운영자용이라 우선순위 낮음) |
| AdminTabNav 가로 스크롤 ✅ | AdminTabNav.tsx | ✅ |

### 5-12. `app/login/page.tsx`, `app/signup/page.tsx`, `app/mypage/page.tsx`

- Header에서 모바일 진입점이 끊겨 있으므로 직접 URL 입력하지 않으면 도달 어려움 → BLOCKER 1과 연결.

---

## 종합 권고 (참고용, 본 감사는 읽기 전용)

| 우선순위 | 항목 |
|---------|------|
| P0 | Header 모바일 로그인/검색 진입점 부활 또는 MobileNav 확장 (스크리너/Chain Sight/Thesis/Market Pulse 누락) |
| P0 | IndicatorRow 기간 토글 44px 보장 + 단일 행 4컬럼 누적폭 모바일 분기 |
| P0 | MoverCard hover-only 툴팁 → 탭 가능한 팝오버로 전환 |
| P0 | StockTable / PortfolioTable / Watchlist 모바일 카드 뷰 추가 (ScreenerTable + MobileStockCard 패턴 확장) |
| P1 | 긴 목록 가상화 (react-window 또는 TanStack Virtual) |
| P1 | QuarterlySparkline hover → tap 인터랙션 |
| P1 | text-[10px] 시스템화 (라벨 / 메타 / 표시 only 구분, 클릭 요소엔 sm 이상) |
| P2 | CategorySidebar 모바일 분기 명문화 |
| P2 | Admin 표 모바일 대응 (운영자 모바일 사용 빈도에 따라) |

---

## 부록 — 감사 도구 자료

- 검색 패턴 1: `w-\[\d+px\]|min-w-\[\d+px\]|max-w-\[\d+px\]` (200건 표시, 상위만 인용)
- 검색 패턴 2: `text-\[(10|11)px\]` (100건 표시, 50+ 파일)
- 검색 패턴 3: `from ['"]recharts['"]` (14 파일 모두 ResponsiveContainer 사용)
- 검색 패턴 4: `overflow-x-(auto|scroll)` (13개 표 + 16개 칩 그룹)
- 검색 패턴 5: `react-window|react-virtual|virtuoso|virtualizer` (0건)
- 검색 패턴 6: `hidden md:|md:hidden|sm:hidden|lg:hidden` (8 파일 11 occurrence)

코드 변경 없음. 본 보고서는 진단만 제공.
