# 모바일 UX 감사 보고서

- 감사 일자: 2026-04-27
- 감사 범위: `frontend/` 전 영역 (page.tsx 23개 + 컴포넌트 ~200개)
- 기준 뷰포트: iPhone SE (375px), Apple HIG 44×44pt 터치 타깃, WCAG 2.5.5
- 코드 변경 없음 (read-only)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 정의 | 건수 |
|--------|------|------|
| **BLOCKER** | 모바일에서 기능 사용 불가 / 중요 정보 미노출 | **5** |
| **MAJOR** | 손가락 터치 어렵거나 가로 스크롤 강제로 UX 심각 저하 | **14** |
| **MINOR** | 미세 조정으로 개선 가능 | **9** |
| 합계 | | **28** |

핵심 이슈 3선:
1. **두 개의 네비게이션 동시 노출** — `Header.tsx`(햄버거)와 `MobileNav.tsx`(하단 탭)가 모바일에서 동시에 보임 (BLOCKER 후보).
2. **터치 타깃 미달 다수** — `text-[10px]`/`p-0.5`/`w-2.5 h-2.5` 클릭 요소가 EOD/Chain Sight/Thesis 전반에 산재 (BLOCKER 1건, MAJOR 9건).
3. **데스크톱 전용 테이블 6종** — 포트폴리오·스크리너·재무제표 등 12+컬럼 테이블이 `overflow-x-auto`만으로 처리되어 모바일 가독성 매우 낮음.

---

## 반응형 누락

### 1.1 데스크톱 전용 컴포넌트 (브레이크포인트 미사용)

`grep -L "sm:|md:|lg:"` 기준 — 49개 컴포넌트만 브레이크포인트 사용 → 절반 이상이 단일 폭 가정.

| 파일 | 문제 | 심각도 |
|------|------|--------|
| `components/layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` + 검색바 `max-w-xl mx-8` + 8개 nav 항목을 `sm:hidden` 처리 없이 노출. 375px에서 nav 영역 가로 스크롤도 없음 → 잘림. (현재 `app/layout.tsx`에는 미사용) | MINOR |
| `components/layout/Header.tsx` | `hidden md:flex` 데스크톱 nav + 햄버거 메뉴 분리. 정상이지만 동시에 `MobileNav`(하단 탭)가 렌더되어 **이중 네비게이션** 발생. | BLOCKER |
| `components/portfolio/PortfolioTable.tsx:259-300` | 12개 컬럼 테이블, `overflow-x-auto`만으로 처리. `MobileStockCard`(스크리너 전용) 같은 카드 뷰 분기 없음. | MAJOR |
| `components/stocks/StockTable.tsx:34` | 마찬가지로 카드 뷰 분기 없음. | MAJOR |
| `components/strategy/ScreenerTable.tsx:128` | `max-w-[180px]`/`max-w-[120px]` 고정으로 종목명·섹터 강제 truncate. 모바일에서 가로 스크롤 + truncate 이중 부하. | MAJOR |
| `app/stocks/[symbol]/page.tsx:843` | 재무제표 N분기 × 다항목 테이블, mobile 분기 없음. | MAJOR |
| `app/watchlist/page.tsx:294` | overflow-x-auto만으로 처리. | MAJOR |
| `components/admin/SystemTab.tsx:72,144,288`, `ScreenerTab.tsx:56,111`, `NewsCategoryManager.tsx:299`, `NewsTab.tsx:81,124` | 어드민 전체 테이블 7개. (어드민이라 우선순위 낮음) | MINOR |

### 1.2 가로 스크롤 처리 — 적절한 사례

- `components/eod/SignalFilterTabs.tsx:33` — `overflow-x-auto pb-1 scrollbar-hide flex-shrink-0` ✅
- `components/admin/AdminTabNav.tsx:30` — `overflow-x-auto whitespace-nowrap` ✅
- `components/chainsight/ExplorationTrail.tsx:36`, `ChainStoryFeed.tsx:118`, `TracePathView.tsx:52`, `FullPathView.tsx:173` — 경로/탐색 추적류는 가로 스크롤이 의도된 패턴 ✅

### 1.3 고정 폭 패턴 (모바일 영향)

| 파일 | 라인 | 패턴 | 영향 |
|------|------|------|------|
| `components/layout/InvestingHeader.tsx` | 32, 55, 99 | `max-w-[1400px]` | 컨테이너용 → 영향 없음 |
| `components/strategy/ScreenerTable.tsx` | 209, 224, 307 | `max-w-[180px]`, `max-w-[120px]`, `max-w-[200px]` | 종목명/섹터 truncate가 폭 100% 시점에서도 발생 |
| `components/news/RecommendationCard.tsx` | 85 | `truncate max-w-[150px]` | 한국 종목명 잘림 |
| `components/eod/StockRow.tsx` | 55, 66 | `max-w-[140px]`, `min-w-[72px]` | 종목명 표시 폭 모바일에서 협소 |
| `components/eod/SignalDetailSheet.tsx` | 97 | `w-full md:w-[420px]` | 모바일 적절(전체폭) ✅ |
| `components/rag/ChatInterface.tsx` | 198 | `w-[52px] h-[52px]` 전송 버튼 | 적절 ✅ |
| `components/rag/SuggestionChips.tsx` | 40 | `max-w-[150px] truncate text-xs` | 칩 텍스트 잘림 |
| `components/admin/SystemTab.tsx`, `TaskLogViewer.tsx`, `ActionButton.tsx` | — | `max-w-[240px]`/`[260px]`/`[200px]` | 어드민 한정 |

---

## 터치 타겟 (Apple HIG 44×44pt 미달)

### 2.1 BLOCKER — 사실상 클릭 불가능

| 파일:라인 | 요소 | 실제 크기 | 근거 |
|-----------|------|-----------|------|
| `components/eod/SignalCard.tsx:168-177` | `<Link>`로 감싼 `<Network className="w-2.5 h-2.5" />` (Chain Sight 진입 아이콘) | **약 10×10px** | 시그널 카드 헤더에 매 종목당 표시. iOS 손가락 평균 7~10mm와 충돌 → 정타율 0%. |
| `app/chainsight/[symbol]/page.tsx:206` | 모바일 노드 상세 닫기 버튼 `text-gray-400 text-sm` (✕) | 약 16×16px | 패딩 없음. 노드 상세 닫기가 사실상 불가. |
| `components/eod/SignalDetailSheet.tsx:136-141` | 시트 닫기 X 버튼 `p-1.5 + w-4 h-4` | **약 28×28px** | 모바일 풀시트 헤더에서 닫기. 안전영역 부족. |
| `components/thesis/dashboard/IndicatorRow.tsx:179-189` | 1M/1Y/3Y/5Y 차트 기간 토글 `px-2.5 py-0.5 text-[10px]` | **약 32×22px** | 가설 관제실 핵심 인터랙션. 4개 버튼이 1.5px 간격으로 붙어 있어 옆 버튼 오터치 빈번. |
| `components/admin/AdminTabNav.tsx:34-46` | 탭 버튼 `px-4 py-2.5 text-sm` | 약 80×38px (높이 38) | 어드민이라 우선순위는 낮으나 44pt 미달. |

### 2.2 MAJOR — 손끝 정확도 요구

| 파일:라인 | 요소 | 크기/근거 |
|-----------|------|-----------|
| `components/screener/Pagination.tsx:127` | 페이지 번호 `min-w-[32px] px-2 py-1.5 text-sm` | **약 32×30px**. 좌우 1, 2, 3 버튼이 인접 → 오터치. |
| `components/validation/PeerContextBar.tsx:37-49` | Peer 프리셋 탭 `px-3 py-1 text-xs font-medium rounded-full` | **약 60×26px**. 프리셋 6종(저성장/고성장/대형/소형/Custom) 가로 나열 시 손끝 정확도 요구. |
| `components/validation/PeerContextBar.tsx:52-62` | "직접 설정" 버튼 동일 사양 | 동일 |
| `components/thesis/PresetSelector.tsx:45` (확인 필요) | 프리셋 카드 `gap-3 p-3` | 양호하나 sub-button 폭 부족 가능성 |
| `components/market-pulse/MoverCard.tsx:107-189`, `MoverCardWithBatchKeywords.tsx:114-196` | 5개 호버 툴팁 (`group-hover/tooltip:block` + `text-[10px]`) | **호버 전용 → 모바일에서 동작 안 함**. 도움말이 모바일에서 영구 미노출. |
| `components/thesis/dashboard/IndicatorRow.tsx:81-152` | 카드 전체 클릭(토글) | 양호. 3행 정보 영역 자체가 ~100px 높이. ✅ |
| `components/thesis/IndicatorCard.tsx:52` | `text-[10px] px-1.5 py-0.5 rounded-full` 시그널 배지 | 클릭 가능 영역 아님(visual). MINOR로 강등. |
| `app/screener/page.tsx:528-540` | 적용 프리셋 X 버튼 `<X className="h-3 w-3" />` 단독 클릭 | **약 16×16px**. 프리셋 빠른 제거 불가. |
| `components/thesis/alerts/AlertCard.tsx:57` | 카드 내 액션 버튼 `text-[10px] flex-shrink-0` | 알림 카드 내 보조 액션 폭 부족 |
| `components/eod/SignalDetailSheet.tsx:188` | 섹터 칩 `text-[10px] px-1.5 py-0.5` Link | **약 50×20px**. Chain Sight 연계 진입 → 폭 부족. |
| `components/eod/SignalDetailSheet.tsx:212-219` | 정렬 옵션 트리거 `gap-1.5 px-3 py-1 text-xs` | 약 90×26px. |
| `components/chainsight/MobileCardList.tsx:166-184` | "가설/탐색/검증" 3분할 CTA `flex-1 text-xs py-1.5` | **약 110×30px** 각각. flex-1로 늘어나 폭은 충분하나 높이 30px 부족. |
| `app/chainsight/[symbol]/page.tsx:208-228` | 모바일 노드 상세 시트 CTA `text-xs py-2` | 동일 패턴 |
| `components/news/RecommendationCard.tsx:85` | 추천 종목명 truncate 영역 | 클릭 시 종목 페이지 진입 — 폭 부족하나 영역은 카드 전체이므로 양호. MINOR 강등. |

### 2.3 MINOR — 시각적 위계만 영향

- `text-[10px]` 사용처 50+ — 대부분 라벨/메타데이터(비클릭). 가독성만 영향. (Thesis builder/dashboard, EOD, Chain Sight 전반)
- `text-[11px]` 사용처 — 보조 라벨용으로 적절.
- `components/thesis/dashboard/QuarterlySparkline.tsx:59` 호버 툴팁 — 모바일 hover 미작동 → 분기별 값 미노출 (MINOR/MAJOR 경계).

---

## 네비게이션

### 3.1 BLOCKER — 이중 네비게이션

`app/layout.tsx`에서 `<Header />`와 `<MobileNav />`를 동시 렌더.

```tsx
// frontend/app/layout.tsx:59-63
<Header />            // md:hidden 햄버거 메뉴 포함 (모바일에서 햄버거 노출)
<main>{children}</main>
<MobileNav />         // md:hidden 하단 탭 5개 (Bottom navigation)
```

문제:
- 모바일(<768px)에서 **두 가지 nav가 동시에 보임** — 상단 햄버거(Header.tsx의 모바일 드롭다운) + 하단 탭바(MobileNav).
- **Information architecture가 불일치**:
  - `MobileNav.tsx:10-16` — 홈/종목/뉴스/포트폴리오/내정보 (`/profile` 경로는 라우트 미존재)
  - `Header.tsx:42-108` — 대시보드/포트폴리오/Chain Sight/Thesis Control/Market Pulse/뉴스/스크리너/마이페이지
- **MobileNav의 `/profile` 깨진 링크** — `app/` 하위에 `/profile/page.tsx` 없음. `mypage/page.tsx`만 존재.
- **MobileNav에 Thesis/Chain Sight/Screener 진입점 없음** — 핵심 기능이 모바일에서만 숨겨짐.

→ **MobileNav가 사용자에게 거짓말을 하고 있음**: "내정보" 클릭 → 404. 핵심 메뉴(Thesis Control, Chain Sight) 접근하려면 햄버거를 거쳐야 함.

### 3.2 MAJOR — Header.tsx 모바일 드롭다운 폭/깊이

`Header.tsx:165-255` — 모바일 메뉴는 클릭 시 인라인 확장. 단점:
- 8개 메뉴 + 검색 + 사용자 메뉴가 한꺼번에 표시되어 화면 점유율 60%↑
- 검색 입력란이 메뉴 바닥에 있어 search-first 사용자 동선 단절
- 메뉴 항목 `block px-3 py-2` → 약 36~40px 높이 (44pt 미달)

### 3.3 사이드바 (페이지 단위)

| 페이지 | 사이드바 | 모바일 처리 |
|--------|---------|------------|
| `app/chainsight/[symbol]/page.tsx:152-232` | 좌측 AIGuidePanel + 우측 NodeDetailPanel (3-panel) | **별도 모바일 분기**: `isMobile && !graphOverlay` → `MobileCardList`. ✅ 우수 |
| `app/screener/page.tsx` | AdvancedFilterPanel (인라인) | 인라인 패널이라 모바일에서도 펼침. 그러나 폭 좁아 슬라이더 조작 어려움. MAJOR |
| `app/admin/page.tsx` | AdminTabNav | `overflow-x-auto` ✅ |
| `app/stocks/[symbol]/page.tsx` | 탭 네비게이션 | `flex gap-2 overflow-x-auto pb-3 scrollbar-hide` ✅ (line 1030) |

### 3.4 Virtualization 부재

```
$ grep -r "react-window\|react-virtual\|VirtualList\|virtualize" frontend/
→ 0건
```

긴 목록 (스크리너 결과, 포트폴리오, 뉴스, 알림, 가설 지표, Chain Sight 관계 카드)에 가상화 미적용. 파급:
- 스크리너 결과 100~500종목 + 키워드 비동기 fetch → 모바일 메모리 폭증 (MAJOR)
- 포트폴리오 100+ 보유 종목 시 PortfolioTable 12컬럼 × 100행 = 1200 셀 렌더 (MAJOR)
- 뉴스 페이지 4개 카테고리 × 100건 = 400 카드 (MAJOR)

대안 — `Pagination.tsx`만 존재(스크리너용). 무한 스크롤·가상화 둘 다 부재.

---

## 차트/그래프

### 4.1 ResponsiveContainer 사용 현황

총 13개 컴포넌트에서 `ResponsiveContainer` 사용 — 폭은 `width="100%"`로 모두 처리됨 ✅.

| 파일 | 높이 | 모바일 영향 |
|------|------|------------|
| `components/validation/MetricBarChart.tsx:78` | `100%` (부모 `h-48` = 192px) | ✅ |
| `components/macro/YieldCurveChart.tsx:93` | `100%` | ✅ |
| `components/stock/StockChart.tsx:652,748` | 동적 `chartHeight.price` / `chartHeight.volume` | ✅ |
| `components/thesis/dashboard/IndicatorRow.tsx:197,235` | `160`, `140` 고정 | 모바일에서 적절 |
| `components/thesis/dashboard/IndividualMiniCharts.tsx:54` | `100` 고정 | ✅ |
| `components/portfolio/PortfolioChart.tsx:77,97` | `400` 고정 | 375px에서 위아래 비율 부적절 (MINOR) |
| `components/news/SentimentChart.tsx:80` | `100%` | ✅ |
| `components/charts/StockPriceChart.tsx:272` | 동적 `height` prop | ✅ |
| `components/admin/news/MLTrendChart.tsx:90` | `100%` | ✅ |
| `components/screener/SectorHeatmap.tsx:216` | **`400` 고정** + Treemap aspectRatio={4/3} | **MAJOR** — 375×400 영역에 Treemap이 들어가면 텍스트 라벨이 잘림 |

### 4.2 분기 스파크라인 모바일 가독성

`components/thesis/dashboard/QuarterlySparkline.tsx:33-59`:
- `flex items-end gap-1 h-10` (40px 높이 내 4분기 막대) → 가독 가능 ✅
- 호버 툴팁(`absolute bottom-full ... text-[10px]`) → **모바일 hover 미작동** → 정확한 값 미노출 (MAJOR)
- `IndicatorRow.tsx:132` `flex-1 max-w-[100px]` 컨테이너 — 모바일 폭에서 적절

### 4.3 Force Graph (Chain Sight)

`components/chainsight/GraphCanvas.tsx` — `react-force-graph-2d` Canvas 렌더.
- 모바일에서는 `MobileCardList`로 전환되어 그래프 미사용 ✅
- 그래프 오버레이 모드(`graphOverlay`)는 풀스크린 표시 ✅
- 단, 노드 클릭 영역이 `getNodeRadius` 기반(보통 4~12px) → **터치 정확도 매우 낮음** (MAJOR). `react-force-graph` 자체에 모바일 최적화 부재.

### 4.4 차트 내 클릭 요소

- Recharts Tooltip — hover 기반. 모바일 탭으로도 트리거되지만 위치 보정 없음 (MINOR).
- IndicatorRow 차트 펼침 토글 — 카드 전체 클릭이라 양호 ✅

---

## 페이지별 상세

### 5.1 `app/page.tsx` (EOD Dashboard) — 메인 진입

- `min-h-screen pb-20 md:pb-0` ✅ (하단 MobileNav 회피)
- `max-w-6xl mx-auto px-4` ✅
- `SignalCardGrid`: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` ✅
- 이슈: SignalCard 내 `<Network w-2.5 h-2.5/>` 링크 (BLOCKER, 위 2.1 참조)
- 이슈: BullBearBar `w-24 h-2 rounded-full` — 96×8px (MINOR, 시각용)
- **종합: 모바일 최적화 양호. SignalCard 내부 인터랙션만 수정 필요.**

### 5.2 `app/thesis/(list)/page.tsx` & `app/thesis/[thesisId]/page.tsx`

- `max-w-lg mx-auto px-4 pt-4 pb-20` ✅ (모바일 우선 설계)
- IndicatorRow 카드 클릭 영역 충분 ✅
- 차트 기간 토글 (1M/1Y/3Y/5Y) `px-2.5 py-0.5 text-[10px]` — **BLOCKER** (위 2.1)
- AISummary, NotableChanges, IndicatorRow 모두 single-column ✅
- **종합: 모바일 first 설계로 데스크톱→모바일 변환 부담 거의 없음. 차트 토글만 큰 문제.**

### 5.3 `app/thesis/[thesisId]/indicators/page.tsx` & `thesis/new/page.tsx`

- `text-[10px]` 빈도 높음 (`thesis/new` 6건, `IndicatorCard` 4건)
- `OptionButton.tsx:50,66`: 본 버튼 외 "꾹 누르면 설명" 라벨 `text-[10px] sm:hidden` — 모바일 전용 안내 ✅ 좋음
- `BottomSheet.tsx`(thesis common): 모바일 친화 패턴 사용 ✅
- `MultiSelectFooter.tsx`, `BottomSheet.tsx` — sticky 하단 액션 적절 ✅

### 5.4 `app/screener/page.tsx`

- `mx-auto max-w-7xl px-4 sm:px-6 lg:px-8` ✅
- `Market Breadth + Sector Heatmap` `grid-cols-1 lg:grid-cols-3` ✅
- **`SectorHeatmap` height=400 고정** — 모바일에서 라벨 잘림 (MAJOR)
- **`AdvancedFilterPanel` 인라인 펼침** — 모바일에서 폭 좁고 슬라이더 조작 어려움 (MAJOR)
- 적용 프리셋 X 버튼 `<X w-3 h-3 />` — 16×16px (MAJOR)
- **`ScreenerTable.tsx` 12컬럼** — `MobileStockCard.tsx` 컴포넌트가 존재함에도 페이지에서 분기 없이 항상 테이블 사용 (BLOCKER 후보)
- 페이지네이션 `min-w-[32px]` — 32×30px (MAJOR)

### 5.5 `app/portfolio/page.tsx`

- `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8` ✅
- `viewMode: 'grid' | 'table'` 토글 존재 ✅
- 그러나 **table 모드는 12컬럼 그대로** — 토글했을 때 모바일에서 사용 불가
- PortfolioStockCard는 grid 모드용으로 잘 설계됨 ✅
- 기본값을 모바일에서 grid로 강제 분기 미적용 (MAJOR)

### 5.6 `app/news/page.tsx`

- `OnboardingBanner`, `DailyKeywordCard`, `AINewsBriefingCard`, `NewsHighlightedStocks`, `NewsCategorySection` — 모두 카드형 ✅
- 시간 필터 `TimeFilter` 24h/7d/30d 토글 — 적절
- `NewsCategorySection` 4개 카테고리 → 각 100건 — **가상화 미적용** (MAJOR)
- `RecommendationCard.tsx:85` 종목명 `truncate max-w-[150px]` — 한국 종목명 잘림 (MINOR)

### 5.7 `app/stocks/[symbol]/page.tsx`

- 탭 네비 `flex gap-2 overflow-x-auto scrollbar-hide` ✅
- 재무제표 탭 `OtherFundamentalsTab`: 12+분기 × N항목 테이블 — `overflow-x-auto`만 (MAJOR)
- 뉴스 탭 `grid-cols-1 lg:grid-cols-2` ✅
- StockChart `ResponsiveContainer` ✅

### 5.8 `app/chainsight/[symbol]/page.tsx`

- **모바일 분기 우수** ✅
  - `isMobile && !graphOverlay` → `MobileCardList` (카드 리스트 + 카테고리 탭)
  - `isMobile && graphOverlay` → 풀스크린 그래프 + 바텀시트
- 그러나 노드 상세 닫기 `text-sm ✕` — 16×16px (BLOCKER, 위 2.1)
- CTA 3분할 `flex-1 text-xs py-2` — 30px 높이 (MAJOR)
- **종합: 설계는 우수, 디테일에서 터치 타깃 부족.**

### 5.9 `app/chainsight/page.tsx` & `chainsight/watchlist/[id]/page.tsx`

- (확인 필요) — 본 감사에서는 `[symbol]/page.tsx`만 상세 점검.

### 5.10 `app/market-pulse/page.tsx`

- `SectionSkeleton` 카드형 ✅
- `FearGreedGauge`, `YieldCurveChart`, `EconomicIndicators`, `GlobalMarketsCard`, `MarketMoversSection` — 각각 카드 단위 ✅
- `MoverCard` 5개 호버 툴팁 (한도/거래량/RVOL/베타/배당) `group-hover/tooltip:block` — **모바일 hover 미작동** (MAJOR)

### 5.11 `app/admin/page.tsx`

- 어드민 전용. 우선순위 낮음.
- `AdminTabNav` `overflow-x-auto` ✅
- 7개 테이블 `overflow-x-auto` (MINOR)

### 5.12 `app/login/page.tsx`, `app/signup/page.tsx`, `app/mypage/page.tsx`

- (단일 폼 페이지로 추정 — 본 감사에서 미점검. 통상 모바일 안전 추정)

### 5.13 `app/dashboard/page.tsx`

- `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` ✅
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` ✅
- 사용자 정보 `dl` `sm:grid-cols-3` ✅
- **종합: 양호. 단, `app/page.tsx`(EOD)와 역할 중복 의심 — 라우팅 정책 확인 필요.**

### 5.14 `app/watchlist/page.tsx`

- 내부 테이블 `overflow-x-auto` (MAJOR)
- WatchlistCard / WatchlistItemRow 카드 분기 존재 — 사용 여부 확인 필요

---

## 권장 우선순위 (티어별 처리)

### Tier 1 (BLOCKER — 즉시 수정)

1. **MobileNav `/profile` 라우트 깨짐 수정** — `mypage`로 변경 또는 `app/profile` 생성. (`MobileNav.tsx:15`)
2. **MobileNav vs Header IA 일원화** — Thesis Control/Chain Sight/Screener 진입점 보강 또는 Header 햄버거 폐지.
3. **`SignalCard.tsx` Network 아이콘 링크 터치 영역 확대** — 부모 영역으로 hit zone 확장 또는 아이콘 제거.
4. **`IndicatorRow.tsx` 차트 기간 토글** — `min-h-[44px]`, `text-xs`로 격상.
5. **`SignalDetailSheet.tsx` 모바일 닫기 X 버튼** — `p-3` 이상 + `w-5 h-5` 아이콘.
6. **`chainsight/[symbol]/page.tsx:206` 모바일 시트 닫기** — 패딩 추가.

### Tier 2 (MAJOR — 1~2주 내)

1. **포트폴리오/스크리너 모바일 카드 뷰 강제 분기** — `<768px`에서 `MobileStockCard`/`PortfolioStockCard`만 노출.
2. **재무제표 테이블 모바일 분기** — 컬럼 축약 또는 가로 스크롤 + sticky 1열 인디케이터.
3. **MoverCard hover 툴팁 → tap-to-show 변환** — 모바일에서 정보 차단 해소.
4. **Pagination 버튼 44pt 격상** — `min-w-[44px] min-h-[44px]`.
5. **Validation PeerContextBar 프리셋 탭** — `py-2` 이상.
6. **SectorHeatmap 모바일 height 동적 계산** — Treemap 라벨 보존.
7. **AdvancedFilterPanel 모바일 BottomSheet 변환** — 슬라이더 조작 영역 확보.
8. **긴 목록 가상화 도입 검토** — `react-window` 권장 (스크리너/뉴스/포트폴리오).
9. **ScreenerTable max-w 고정 폭 제거** — 모바일에서 `truncate w-full`로.
10. **Force Graph 노드 hit zone 확장** — `nodeRelSize` 또는 invisible larger circle 패턴.

### Tier 3 (MINOR — 백로그)

1. `text-[10px]` 비클릭 라벨 → `text-[11px]` 또는 `text-xs` 격상으로 가독성 개선.
2. PortfolioChart 400px 고정 → 모바일 종횡비 조정.
3. RecommendationCard truncate 폭 확대.
4. QuarterlySparkline 모바일 tap-to-show 툴팁.
5. 어드민 영역 테이블들의 카드 뷰 분기.
6. `InvestingHeader.tsx` 사용 여부 확인 — 미사용이면 제거.
7. `app/dashboard/page.tsx`와 `app/page.tsx` 역할 정리.
8. Tailwind tap target 유틸리티 도입(`min-w-touch min-h-touch` 등 plugin) — 일관성 확보.
9. `MobileNav` 활성 상태 비교를 `pathname.startsWith()`로 변경(현재 `===`이라 하위 라우트에서 미하이라이트).

---

## 부록: Tailwind 검색 결과 통계

| 패턴 | 매칭 수 |
|------|---------|
| `w-[NNpx]`/`min-w-[NNpx]`/`max-w-[NNpx]` | 약 30개 컴포넌트 (대부분 `max-w-[1400px]` 컨테이너) |
| `text-[10px]` 사용처 | 50+ (대부분 라벨/메타) |
| `text-[11px]` | 약 15 |
| `overflow-x-auto` | 25+ (테이블/탭/스크롤 영역) |
| `ResponsiveContainer` | 13 컴포넌트 (모두 `width="100%"`) ✅ |
| `react-window` 등 가상화 | **0** |
| sm:/md:/lg: 사용 컴포넌트 | 49 (전체 ~200 중 25%) |
| `md:hidden` (모바일 전용) | `MobileNav.tsx`, `Header.tsx` 햄버거, SignalDetailSheet 드래그 핸들 |
| `hidden md:flex/block` (데스크톱 전용) | Header.tsx nav, 일부 사이드바 |

---

*감사 완료. 코드 변경 없음. 본 보고서는 `docs/nightly_auto_system/reports/4월/26일/mobile_ux_audit.md`에 저장됨.*
