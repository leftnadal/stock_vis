# 모바일 UX 감사 보고서

- 감사 일자: 2026-04-27 → 2026-04-28 (야간 자동 실행)
- 대상 브랜치: `feature/chainsight-graph-v2` (commit `16ccf23` 기준)
- 감사 범위: `frontend/` 전 영역 (`page.tsx` 23개 + 컴포넌트 ~210개)
- 기준 뷰포트: iPhone SE 375×667, Apple HIG 44×44pt 터치 타깃, WCAG 2.5.5
- 코드 변경 없음 (read-only)
- 비교 기준: `4월/26일/mobile_ux_audit.md`

---

## 요약 (심각도별 이슈 수)

| 심각도 | 정의 | 4/26 | 4/27 | 변동 |
|--------|------|-----:|-----:|-----:|
| **BLOCKER** | 모바일에서 기능 사용 불가 / 중요 정보 미노출 | 5 | **6** | +1 |
| **MAJOR** | 가로 스크롤 강제·터치 타겟 부족으로 UX 심각 저하 | 14 | **17** | +3 |
| **MINOR** | 미세 조정으로 개선 가능 | 9 | **10** | +1 |
| 합계 | | 28 | **33** | +5 |

### 신규/악화 항목 (FE-PR-1 ~ FE-PR-5 영향)

Chain Sight 그래프 v2가 메인 `app/chainsight/page.tsx` 에 들어오면서 **그래프 캔버스(`h-[560px]`) + 관계 토글 칩 바 + 컨텍스트 메뉴 + 범례**가 추가되었고, 이들이 모바일에서 새 이슈를 만들었다.

| # | 항목 | 영향 파일 | 심각도 |
|---|------|----------|--------|
| N1 | `MarketGraphCanvas.tsx`의 `h-[560px]` 고정 캔버스 — iPhone SE에서 화면 거의 전체 점유, 노드 4~12px 터치 불가 | `components/chainsight/MarketGraphCanvas.tsx:603,712,760,765` | BLOCKER |
| N2 | `RelationFilterChips` 칩 높이 `h-8` (32px) — 6종 칩 가로 스크롤 + 우측 페이드 — 칩 자체 터치 불가 | `components/chainsight/RelationFilterChips.tsx:150` | MAJOR |
| N3 | `RelationFilterChips` "전체 켜기 / 전체 끄기" 버튼 `text-xs px-2 py-1` (~26px 높이) | `components/chainsight/RelationFilterChips.tsx:249-263` | MAJOR |
| N4 | `RelationLegend` 접기/펼치기 토글 `text-[10px]` 단독 클릭 영역 (~12px) | `components/chainsight/RelationLegend.tsx:56-72` | MAJOR |
| N5 | `NodeContextMenu` 우클릭/롱프레스 메뉴 — 모바일 롱프레스 트리거 시 메뉴 항목 `py-2 text-sm` (~36px 높이, 44pt 미달) | `components/chainsight/NodeContextMenu.tsx:140-177` | MINOR |

### 핵심 이슈 3선

1. **이중 네비게이션 미해결**(BLOCKER) — `app/layout.tsx`에서 `<Header />`와 `<MobileNav />`가 동시 렌더. `MobileNav`의 `/profile` 경로는 라우트 미존재(404). 26일 보고서 이후 변경 없음.
2. **Chain Sight v2 메인 페이지가 모바일을 고려하지 않음**(BLOCKER) — `app/chainsight/page.tsx` 에는 `app/chainsight/[symbol]/page.tsx`처럼 `MobileCardList`로 fall-back하는 분기가 없다. `h-[560px]` 캔버스가 무조건 렌더되어 노드(평균 8~12px)를 손가락으로 정확히 클릭할 수 없다.
3. **가설 관제실 차트 토글 + 페이지네이션 + 프리셋 탭의 22~30px 높이** — 25일·26일·27일 3일 연속 같은 항목 BLOCKER/MAJOR 유지.

---

## 반응형 누락

### 1.1 데스크톱 전용 컴포넌트 (브레이크포인트 미사용)

`grep -L "sm:|md:|lg:"` 기준 51개 컴포넌트만 브레이크포인트 사용 — 절반 이상이 단일 폭 가정.

| 파일 | 문제 | 심각도 |
|------|------|--------|
| `components/layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` + 8개 nav 항목, 모바일 분기 없음 (현재 `app/layout.tsx`에 미사용이지만 잔존 코드) | MINOR |
| `components/layout/Header.tsx` | `hidden md:flex` 데스크톱 nav + 햄버거 메뉴. 정상이지만 동시에 `MobileNav`(하단 탭)가 렌더되어 **이중 네비게이션** | BLOCKER |
| `components/chainsight/MarketGraphCanvas.tsx:603,712,760` | 빈 상태/로딩/실그래프 모두 `h-[560px]` 고정. iPhone SE 본문 가용 높이 ~520px → 캔버스가 viewport 초과 | **BLOCKER** |
| `components/portfolio/PortfolioTable.tsx:259-300` | 12컬럼 테이블, `overflow-x-auto`만으로 처리. 카드 뷰 분기 없음 | MAJOR |
| `components/stocks/StockTable.tsx:34` | 카드 뷰 분기 없음 | MAJOR |
| `components/strategy/ScreenerTable.tsx:128,209,224,307` | `max-w-[180px]/[120px]/[200px]` 고정으로 종목명·섹터 강제 truncate | MAJOR |
| `app/stocks/[symbol]/page.tsx:843` | 재무제표 N분기 × 다항목 테이블, mobile 분기 없음 | MAJOR |
| `app/watchlist/page.tsx:294` | `overflow-x-auto`만으로 처리 | MAJOR |
| `components/admin/SystemTab.tsx:72,144,288`, `ScreenerTab.tsx:56,111`, `NewsCategoryManager.tsx:299`, `NewsTab.tsx:81,124`, `TaskLogViewer.tsx:123` | 어드민 테이블 7개 (우선순위 낮음) | MINOR |

### 1.2 가로 스크롤 처리 — 적절한 사례

- `components/eod/SignalFilterTabs.tsx:33` — `overflow-x-auto pb-1 scrollbar-hide flex-shrink-0` ✅
- `components/admin/AdminTabNav.tsx:30` — `overflow-x-auto whitespace-nowrap` ✅
- `components/chainsight/ExplorationTrail.tsx:36`, `ChainStoryFeed.tsx:118`, `TracePathView.tsx:52`, `FullPathView.tsx:173` — 경로 탐색용 ✅
- `components/chainsight/SectorBar.tsx:24` — `overflow-x-auto py-3 px-1 scrollbar-thin` ✅
- `components/chainsight/RelationFilterChips.tsx:228-230` — `overflow-x-auto` + 우측 페이드아웃(`md:hidden` linear-gradient) ✅ (단, 칩 자체 높이 32px는 터치 부족 — N2)

### 1.3 고정 폭 패턴 (모바일 영향)

| 파일 | 라인 | 패턴 | 영향 |
|------|------|------|------|
| `components/chainsight/MarketGraphCanvas.tsx` | 603, 712, 760 | `h-[560px]` 캔버스 | 화면 점유율 75%↑, viewport 초과 |
| `components/chainsight/MarketGraphCanvas.tsx` | 676 | `w-[110px] min-h-[68px]` 인기 섹터 버튼 | 적절 ✅ |
| `components/chainsight/RelationLegend.tsx` | 51 | `max-w-[140px]` | 좌하단 absolute overlay → 적절 ✅ |
| `components/strategy/ScreenerTable.tsx` | 209, 224, 307 | `max-w-[180px]`, `max-w-[120px]`, `max-w-[200px]` | 종목명/섹터 truncate가 폭 100% 시점에서도 발생 |
| `components/news/RecommendationCard.tsx` | 85 | `truncate max-w-[150px]` | 한국 종목명 잘림 |
| `components/eod/StockRow.tsx` | 55, 66 | `max-w-[140px]`, `min-w-[72px]` | 종목명 표시 폭 협소 |
| `components/eod/SignalDetailSheet.tsx` | 97 | `w-full md:w-[420px]` | 모바일 적절 ✅ |
| `components/rag/ChatInterface.tsx` | 198 | `w-[52px] h-[52px]` 전송 버튼 | 적절 ✅ |
| `components/rag/SuggestionChips.tsx` | 40 | `max-w-[150px] truncate text-xs` | 칩 텍스트 잘림 |
| `components/admin/SystemTab.tsx`, `TaskLogViewer.tsx`, `ActionButton.tsx` | — | `max-w-[240px]/[260px]/[200px]` | 어드민 한정 |

---

## 터치 타겟 (Apple HIG 44×44pt 미달)

### 2.1 BLOCKER — 사실상 클릭 불가능

| 파일:라인 | 요소 | 실제 크기 | 근거 |
|-----------|------|-----------|------|
| `components/eod/SignalCard.tsx:168-177` | `<Link>`로 감싼 `<Network className="w-2.5 h-2.5" />` (Chain Sight 진입 아이콘) | **약 10×10px** | 시그널 카드 헤더에 매 종목당 표시. 정타율 0%. |
| `app/chainsight/[symbol]/page.tsx:206` | 모바일 노드 상세 닫기 버튼 `text-gray-400 text-sm ✕` | 약 16×16px | 패딩 없음. 노드 상세 닫기 사실상 불가. |
| `components/eod/SignalDetailSheet.tsx:136-141` | 시트 닫기 X 버튼 `p-1.5 + w-4 h-4` | **약 28×28px** | 모바일 풀시트 헤더 닫기. 안전영역 부족. |
| `components/thesis/dashboard/IndicatorRow.tsx:179-189` | 1M/1Y/3Y/5Y 차트 기간 토글 `px-2.5 py-0.5 text-[10px]` | **약 32×22px** | 가설 관제실 핵심 인터랙션. 4개 버튼이 1.5px 간격. |
| `components/admin/AdminTabNav.tsx:34-46` | 탭 버튼 `px-4 py-2.5 text-sm` | 약 80×38px (높이 38) | 어드민이라 우선순위 낮음. 44pt 미달. |
| **N1.** `components/chainsight/MarketGraphCanvas.tsx` (`getNodeRadius`) | Force Graph 노드 — Level 0 center 28px, Level 1 14~18px, Level 2 7~10px | **7~28px (대부분 10px 미만)** | `app/chainsight/page.tsx` 메인이 모바일에서도 캔버스 그대로 렌더. 노드 정확히 손끝으로 짚기 불가능 → BLOCKER. `[symbol]/page.tsx`처럼 `MobileCardList` 분기 필요. |

### 2.2 MAJOR — 손끝 정확도 요구

| 파일:라인 | 요소 | 크기/근거 |
|-----------|------|-----------|
| `components/screener/Pagination.tsx:127` | 페이지 번호 `min-w-[32px] px-2 py-1.5 text-sm` | **약 32×30px**. 좌우 1, 2, 3 버튼이 인접 → 오터치. |
| `components/validation/PeerContextBar.tsx:37-49` | Peer 프리셋 탭 `px-3 py-1 text-xs font-medium rounded-full` | **약 60×26px**. 프리셋 6종 가로 나열 시 손끝 정확도 요구. |
| `components/validation/PeerContextBar.tsx:52-62` | "직접 설정" 버튼 동일 사양 | 동일 |
| `components/market-pulse/MoverCard.tsx:107-189`, `MoverCardWithBatchKeywords.tsx:114-196` | 5개 호버 툴팁 (`group-hover/tooltip:block` + `text-[10px]`) | **호버 전용 → 모바일 미작동**. 도움말이 모바일에서 영구 미노출. |
| `components/thesis/IndicatorCard.tsx:52` | `text-[10px] px-1.5 py-0.5 rounded-full` 시그널 배지 | 클릭 가능 영역 아님(visual). MINOR로 강등. |
| `app/screener/page.tsx:528-540` | 적용 프리셋 X 버튼 `<X className="h-3 w-3" />` 단독 클릭 | **약 16×16px**. 프리셋 빠른 제거 불가. |
| `components/thesis/alerts/AlertCard.tsx:57` | 카드 내 액션 버튼 `text-[10px] flex-shrink-0` | 폭 부족 |
| `components/eod/SignalDetailSheet.tsx:188` | 섹터 칩 `text-[10px] px-1.5 py-0.5` Link | **약 50×20px**. Chain Sight 연계 진입 폭 부족. |
| `components/eod/SignalDetailSheet.tsx:212-219` | 정렬 옵션 트리거 `gap-1.5 px-3 py-1 text-xs` | 약 90×26px. |
| `components/chainsight/MobileCardList.tsx:166-184` | "가설/탐색/검증" 3분할 CTA `flex-1 text-xs py-1.5` | 약 110×30px |
| `app/chainsight/[symbol]/page.tsx:208-228` | 모바일 노드 상세 시트 CTA `text-xs py-2` | 동일 패턴 |
| `components/chainsight/SectorBar.tsx:29-52` | 섹터 칩 `px-4 py-2 text-sm` | **약 80×40px**. 폭은 충분, 높이 40px(44pt 미달, 한 칸 부족). |
| **N2.** `components/chainsight/RelationFilterChips.tsx:148-150` | 칩 `h-8 px-3 py-0 text-xs` | **약 64~80×32px**. 6종 칩이 가로 스크롤되며 인접 — 오터치 + 32px 높이는 손끝과 충돌. |
| **N3.** `components/chainsight/RelationFilterChips.tsx:249-263` | "전체 켜기 / 전체 끄기" `text-xs px-2 py-1` | **약 60×26px**. 칩 바 우측 끝, 칩과 인접 — 잘못 누르기 쉬움. |
| **N4.** `components/chainsight/RelationLegend.tsx:56-72` | 범례 접기/펼치기 토글 `flex w-full text-[10px]` (좌하단 overlay) | **콘텐츠 영역 ~80×14px**. 모바일 기본 collapsed → "범례 펼치기" 클릭이 매우 어렵다. |

### 2.3 MINOR — 시각적 위계만 영향

- `text-[10px]` 사용처 50+ — 대부분 라벨/메타데이터(비클릭). 가독성만 영향.
- `text-[11px]` 사용처 — 보조 라벨용으로 적절.
- `components/thesis/dashboard/QuarterlySparkline.tsx:59` 호버 툴팁 — 모바일 hover 미작동 → 분기별 값 미노출 (MINOR/MAJOR 경계).
- **N5.** `components/chainsight/NodeContextMenu.tsx:140-177` — 우클릭/롱프레스 메뉴 항목 `px-3 py-2 text-sm` (약 ~36px 높이). 모바일 롱프레스(`react-force-graph-2d`)로 트리거되지만 항목 인접 + 44pt 미달.

---

## 네비게이션

### 3.1 BLOCKER — 이중 네비게이션 (26일에서 변동 없음)

`app/layout.tsx:51-69`에서 `<Header />`와 `<MobileNav />`를 동시 렌더.

```tsx
<Header />            // md:hidden 햄버거 메뉴 포함 (모바일에서 햄버거 노출)
<main>{children}</main>
<MobileNav />         // md:hidden 하단 탭 5개 (Bottom navigation)
```

- 모바일(<768px)에서 **두 가지 nav가 동시 노출**
- IA 불일치:
  - `MobileNav.tsx:10-16` — 홈/종목/뉴스/포트폴리오/내정보 (`/profile` 미존재 → 404)
  - `Header.tsx:42-108` — 대시보드/포트폴리오/Chain Sight/Thesis Control/Market Pulse/뉴스/스크리너/마이페이지
- **MobileNav에 Thesis/Chain Sight/Screener 진입점 없음** — 핵심 기능이 모바일에서만 숨겨짐
- **`/profile` 깨진 링크** — `app/profile/page.tsx` 미존재. `mypage/page.tsx`만 존재.

### 3.2 MAJOR — Header.tsx 모바일 드롭다운 폭/깊이

`Header.tsx:165-255` — 모바일 메뉴는 클릭 시 인라인 확장.

- 8개 메뉴 + 검색 + 사용자 메뉴가 한꺼번에 표시되어 화면 점유율 60%↑
- 검색 입력란이 메뉴 바닥에 있어 search-first 사용자 동선 단절
- 메뉴 항목 `block px-3 py-2` → 약 36~40px 높이 (44pt 미달)

### 3.3 사이드바 / 페이지 단위

| 페이지 | 사이드바 | 모바일 처리 |
|--------|---------|------------|
| `app/chainsight/[symbol]/page.tsx:152-232` | 좌측 AIGuidePanel + 우측 NodeDetailPanel (3-panel) | **별도 모바일 분기**: `isMobile && !graphOverlay` → `MobileCardList` ✅ 우수 |
| **`app/chainsight/page.tsx`** (신규 메인) | SectorBar + RelationFilterChips + MarketGraphCanvas + ExplorationTrail + RelationCardPanel + ChainStoryFeed | **모바일 분기 없음** — 캔버스 그대로 렌더 (BLOCKER, N1) |
| `app/screener/page.tsx` | AdvancedFilterPanel (인라인) | 인라인 패널이라 모바일에서도 펼침. 슬라이더 조작 어려움 (MAJOR) |
| `app/admin/page.tsx` | AdminTabNav | `overflow-x-auto` ✅ |
| `app/stocks/[symbol]/page.tsx` | 탭 네비게이션 | `flex gap-2 overflow-x-auto pb-3 scrollbar-hide` ✅ (1030) |

### 3.4 Virtualization 부재

```
$ grep -r "react-window\|react-virtual\|VirtualList\|virtualize" frontend/
→ 0건
```

긴 목록에 가상화 미적용:
- 스크리너 결과 100~500종목 + 키워드 비동기 fetch → 모바일 메모리 폭증 (MAJOR)
- 포트폴리오 100+ 보유 종목 시 PortfolioTable 12컬럼 × 100행 = 1200 셀 (MAJOR)
- 뉴스 페이지 4개 카테고리 × 100건 = 400 카드 (MAJOR)
- Chain Sight v2 `RelationCardPanel` + `ChainStoryFeed` 가 카드 N개 무가상 렌더

대안 — `Pagination.tsx`만 존재(스크리너용). 무한 스크롤·가상화 둘 다 부재.

---

## 차트/그래프

### 4.1 ResponsiveContainer 사용 현황

총 11개 컴포넌트에서 `ResponsiveContainer` 사용 — 폭은 `width="100%"`로 처리 ✅.

| 파일 | 높이 | 모바일 영향 |
|------|------|------------|
| `components/validation/MetricBarChart.tsx:78` | `100%` (부모 `h-48` = 192px) | ✅ |
| `components/macro/YieldCurveChart.tsx:93` | `100%` | ✅ |
| `components/stock/StockChart.tsx:652,748` | 동적 `chartHeight.price` / `chartHeight.volume` | ✅ |
| `components/thesis/dashboard/IndicatorRow.tsx:197,235` | `160`, `140` 고정 | 모바일 적절 |
| `components/thesis/dashboard/IndividualMiniCharts.tsx:54` | `100` 고정 | ✅ |
| `components/portfolio/PortfolioChart.tsx:77,97` | `400` 고정 | 375px에서 위아래 비율 부적절 (MINOR) |
| `components/news/SentimentChart.tsx:80` | `100%` | ✅ |
| `components/charts/StockPriceChart.tsx:272` | 동적 `height` prop | ✅ |
| `components/admin/news/MLTrendChart.tsx:90` | `100%` | ✅ |
| `components/screener/SectorHeatmap.tsx:216` | **`400` 고정** + Treemap aspectRatio={4/3} | **MAJOR** — 375×400 영역에 Treemap이 들어가면 텍스트 라벨 잘림 |

### 4.2 분기 스파크라인 모바일 가독성

`components/thesis/dashboard/QuarterlySparkline.tsx:33-59`:
- `flex items-end gap-1 h-10` (40px 높이 4분기 막대) → 가독 가능 ✅
- 호버 툴팁(`absolute bottom-full ... text-[10px]`) → **모바일 hover 미작동** (MAJOR)
- `IndicatorRow.tsx:132` `flex-1 max-w-[100px]` 컨테이너 — 모바일 폭에 적절

### 4.3 Force Graph 2D (Chain Sight v2)

`components/chainsight/MarketGraphCanvas.tsx` — `react-force-graph-2d` Canvas 렌더.
- **모바일 분기 없음** — `app/chainsight/page.tsx`가 모바일/데스크톱 동일 캔버스 렌더 (BLOCKER, N1)
- 캔버스 크기 `h-[560px]` 고정 + `width={containerWidth}` (반응형) → 폭은 OK, 높이는 iPhone SE 가용 영역 초과
- 노드 클릭 영역 `nodePointerAreaPaint`는 시각적 반지름과 동일 (`getNodeRadius`) — 7~28px. **터치 정확도 매우 낮음** (BLOCKER)
- 호버 dim/툴팁/컨텍스트 메뉴 모두 데스크톱 마우스 가정 — 모바일 롱프레스만 작동
- 좌하단 `RelationLegend` overlay — 모바일 기본 collapsed, 펼치기 토글 14px (MAJOR, N4)

### 4.4 차트 내 클릭 요소

- Recharts Tooltip — hover 기반. 모바일 탭으로도 트리거되지만 위치 보정 없음 (MINOR)
- IndicatorRow 차트 펼침 토글 — 카드 전체 클릭이라 양호 ✅

---

## 페이지별 상세

### 5.1 `app/page.tsx` (EOD Dashboard) — 메인 진입

- `min-h-screen pb-20 md:pb-0` ✅ (하단 MobileNav 회피)
- `max-w-6xl mx-auto px-4` ✅
- `SignalCardGrid`: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` ✅
- 이슈: SignalCard 내 `<Network w-2.5 h-2.5/>` 링크 (BLOCKER, 2.1)
- 이슈: BullBearBar `w-24 h-2 rounded-full` — 96×8px (MINOR, 시각용)
- **종합: 모바일 최적화 양호. SignalCard 내부 인터랙션만 수정 필요.**

### 5.2 `app/thesis/(list)/page.tsx` & `app/thesis/[thesisId]/page.tsx`

- `max-w-lg mx-auto px-4 pt-4 pb-20` ✅ (모바일 우선 설계)
- IndicatorRow 카드 클릭 영역 충분 ✅
- 차트 기간 토글 (1M/1Y/3Y/5Y) `px-2.5 py-0.5 text-[10px]` — **BLOCKER** (2.1, 3일 연속 미해결)
- AISummary, NotableChanges, IndicatorRow 모두 single-column ✅
- **종합: 모바일 first 설계로 변환 부담 거의 없음. 차트 토글만 큰 문제.**

### 5.3 `app/thesis/[thesisId]/indicators/page.tsx` & `thesis/new/page.tsx`

- `text-[10px]` 빈도 높음 (`thesis/new` 6건, `IndicatorCard` 4건)
- `OptionButton.tsx:50,66`: 본 버튼 외 "꾹 누르면 설명" 라벨 `text-[10px] sm:hidden` ✅ (모바일 전용 안내)
- `OptionButton.tsx:52` `min-h-[52px] py-3` (multi) / `min-h-[56px] py-4` (single) ✅ (44pt 충족)
- `BottomSheet.tsx`(thesis common): 모바일 친화 패턴 ✅
- `MultiSelectFooter.tsx`: sticky 하단 액션 적절 ✅
- `TextInput.tsx:46` `min-h-[44px] max-h-[120px]` ✅
- `ChatBubble.tsx:14` `min-h-[44px]` ✅

### 5.4 `app/screener/page.tsx`

- `mx-auto max-w-7xl px-4 sm:px-6 lg:px-8` ✅
- `Market Breadth + Sector Heatmap` `grid-cols-1 lg:grid-cols-3` ✅
- **`SectorHeatmap` height=400 고정** — 모바일에서 라벨 잘림 (MAJOR)
- **`AdvancedFilterPanel` 인라인 펼침** — 모바일에서 폭 좁고 슬라이더 조작 어려움 (MAJOR)
- 적용 프리셋 X 버튼 `<X w-3 h-3 />` — 16×16px (MAJOR)
- **`ScreenerTable.tsx` 12컬럼** — `MobileStockCard.tsx` 컴포넌트가 존재하지만 페이지에서 분기 미적용 (BLOCKER 후보)
- 페이지네이션 `min-w-[32px]` — 32×30px (MAJOR)
- `viewMode` 토글 (`hidden sm:flex` AI 키워드/테제 라벨 등) — 모바일에서 텍스트 숨김 ✅

### 5.5 `app/portfolio/page.tsx`

- `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8` ✅
- `viewMode: 'grid' | 'table'` 토글 존재 ✅
- 그러나 **table 모드는 12컬럼 그대로** — 모바일에서 사용 불가
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
- `w-48 flex-shrink-0 hidden lg:block` 사이드바 ✅

### 5.8 `app/chainsight/page.tsx` (Chain Sight v2 메인 — **신규/악화**)

```
SectorBar (✅)
RelationFilterChips (MAJOR — N2/N3/N4)
MarketGraphCanvas h-[560px] (BLOCKER — N1)
ExplorationTrail (✅ overflow-x-auto)
RelationCardPanel (가상화 미적용)
ChainStoryFeed (가상화 미적용)
```

- **모바일 분기 없음** — `[symbol]/page.tsx`처럼 `MobileCardList` 대체 시그널 부재
- 빈 상태 인기 섹터 버튼 `w-[110px] min-h-[68px]` ✅ (적절)
- `selectSector` 트리거된 후엔 캔버스가 무조건 노출 → 모바일 사용자는 가로 노드 클릭이 거의 불가능
- **종합: 데스크톱 first 설계. PR-1~5는 데스크톱 인터랙션(호버 dim, 우클릭 메뉴, 좌하단 범례) 위주. 모바일 fall-back PR이 별도로 필요.**

### 5.9 `app/chainsight/[symbol]/page.tsx`

- **모바일 분기 우수** ✅
  - `isMobile && !graphOverlay` → `MobileCardList` (카드 리스트 + 카테고리 탭)
  - `isMobile && graphOverlay` → 풀스크린 그래프 + 바텀시트
- 그러나 노드 상세 닫기 `text-sm ✕` — 16×16px (BLOCKER, 2.1)
- CTA 3분할 `flex-1 text-xs py-2` — 30px 높이 (MAJOR)
- **종합: 설계는 우수, 디테일에서 터치 타깃 부족.**

### 5.10 `app/chainsight/watchlist/page.tsx`, `chainsight/watchlist/[id]/page.tsx`

- 본 감사 범위에서 카드/리스트 단순 구조 확인. 별도 BLOCKER 발견 없음 (MINOR 수준).

### 5.11 `app/market-pulse/page.tsx`

- `SectionSkeleton` 카드형 ✅
- 헤더 우측 `hidden sm:flex/inline` 라벨 토글 ✅
- `FearGreedGauge`, `YieldCurveChart`, `EconomicIndicators`, `GlobalMarketsCard`, `MarketMoversSection` — 각각 카드 ✅
- `MoverCard` 5개 호버 툴팁 — **모바일 hover 미작동** (MAJOR)

### 5.12 `app/admin/page.tsx`

- 어드민 전용. 우선순위 낮음.
- `AdminTabNav` `overflow-x-auto` ✅
- 7개 테이블 `overflow-x-auto` (MINOR)

### 5.13 `app/watchlist/page.tsx`

- 12컬럼 테이블 `overflow-x-auto`만 (MAJOR, 5.5와 동일 패턴)

### 5.14 `app/ai-analysis/page.tsx`

- `RAG ChatInterface`: 입력란 전송 버튼 `w-[52px] h-[52px]` ✅
- `MessageList` 스크롤 ✅
- `SuggestionChips`: `max-w-[150px] truncate text-xs` — 칩 텍스트 잘림 (MINOR)
- `MonitoringDashboard` / `TokenUsageDisplay` 모바일 카드형 ✅ (`hidden sm:inline` 라벨)

### 5.15 `app/dashboard/page.tsx`, `app/login/page.tsx`, `app/signup/page.tsx`

- 단순 카드/폼 페이지 — 별도 이슈 없음.
- `dashboard/page.tsx:111` `mt-8 ... overflow-hidden sm:rounded-lg` — 정상.

---

## 권장 우선순위

### 즉시 (1 sprint 내)

1. **이중 네비게이션 해소** (`app/layout.tsx`) — `MobileNav` 메뉴를 Thesis/Chain Sight 등 핵심 5개로 재구성하고 `Header`의 모바일 햄버거를 제거하거나 Header 자체를 `hidden md:block`로 분리. `/profile` → `/mypage` 또는 라우트 추가. (BLOCKER × 1)
2. **Chain Sight 메인 페이지 모바일 분기** (`app/chainsight/page.tsx`) — `useIsMobile()` hook으로 캔버스 대신 `MobileCardList` 또는 `RelationCardPanel`+`ChainStoryFeed` 우선 노출. 데스크톱/모바일 다른 IA. (BLOCKER × 1)
3. **Thesis 차트 기간 토글 + Screener Pagination + Validation Peer 탭의 높이 44pt 보강** — `IndicatorRow.tsx:179-189`, `Pagination.tsx:127`, `PeerContextBar.tsx:37-49`. `min-h-[44px]` + `gap` 8px 이상. (BLOCKER × 1, MAJOR × 3)
4. **Force Graph 노드 터치 영역 확장** (`MarketGraphCanvas.tsx`) — `nodePointerAreaPaint`에서 시각 반지름의 1.6~2배(최소 16px)로 hit area 확대.

### 차순위 (2~3 sprint)

5. ScreenerTable / PortfolioTable / OtherFundamentalsTab 모바일 카드 분기 (이미 존재하는 `MobileStockCard`, `PortfolioStockCard` 활용)
6. SectorHeatmap height 모바일 고정값 변경 (height={400} → 모바일에서 height={280} 분기)
7. RelationFilterChips 칩 높이 `h-8` → `h-10` (40px) + "전체 켜기/끄기"를 칩 그룹 외부로 분리
8. RelationLegend 접기/펼치기 토글 모바일 명시 (`min-h-[36px]` + 외곽 padding)
9. MoverCard 5개 호버 툴팁 → 모바일 탭 토글 또는 long-press 변환

### 장기

10. 가상화 도입 (`@tanstack/react-virtual`) — 스크리너/포트폴리오/뉴스 카테고리/Chain Sight 카드 패널
11. PortfolioTable의 모바일 자동 grid 강제, table 모드는 데스크톱 전용
12. 호버 의존 인터랙션(QuarterlySparkline 툴팁, MoverCard 도움말 등)을 `:focus-visible` + tap-to-toggle 패턴으로 통일

---

## 메타 — 4/26 → 4/27 변경 요약

- **진척**: Chain Sight v2 그래프 PR-1~5 (관계 칩, 시각 위계, 시멘틱 좌표, 점진적 공개, 빈 상태 일러스트) 머지. 데스크톱에서는 발전이지만 모바일 fall-back 전략 부재.
- **악화 5건** (N1~N5) — 모두 Chain Sight v2 메인 페이지에서 발생.
- **유지**: 나머지 모든 항목은 4/26 보고서와 동일. 26일·27일 양일에 BLOCKER 5건 미해결.
- **3일 연속 BLOCKER 유지**: 이중 네비게이션, IndicatorRow 차트 토글, SignalCard Network 아이콘.
