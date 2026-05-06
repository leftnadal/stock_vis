# 모바일 UX 감사 보고서

- 감사 일자: 2026-05-07
- 대상: `frontend/` (Next.js 16, Tailwind, Recharts, react-force-graph-2d)
- 감사 방식: 정적 분석 (코드 수정 없음). Tailwind 클래스/JSX 패턴 기반.
- 가정: Apple HIG 모바일 터치 타겟 = 44×44pt, 모바일 기준폭 = 375px (iPhone 12/13 mini 표준).

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|--------|------|------|
| **BLOCKER** | 4 | 모바일에서 기능을 사용하지 못하거나, 접근성/콘텐츠 가림이 발생 |
| **MAJOR** | 11 | 핵심 기능의 사용성이 의미있게 저하 (작은 터치 영역, 가로 스크롤 강제 등) |
| **MINOR** | 8 | 가독성/일관성 저하. 즉시 차단은 아니지만 누적되면 인상 악화 |
| 합계 | 23 | |

핵심 결론
1. **글로벌 BottomNav(`MobileNav.tsx`)가 5개 라우트만 노출** — 실제 핵심 기능(Chain Sight, Thesis, Screener, Market Pulse)은 햄버거 메뉴를 열어야 도달.
2. **`pb-20`(MobileNav 회피 패딩) 누락 페이지가 다수** — 화면 하단 콘텐츠가 항상 64px 폭 BottomNav에 가려짐.
3. **`viewport.userScalable: false` + `maximumScale: 1`** — 시각 보조 사용자가 화면을 확대할 수 없음(WCAG 1.4.4 위반).
4. **Thesis 관제실 IndicatorRow / Chain Sight Mobile CTA** — 핵심 인터랙션 버튼들이 HIG 44pt 미만(20~32px).

---

## 반응형 누락

### 고정 폭 사용 컴포넌트 (375px 영향 분석)

| 파일 | 위치 | 클래스 | 모바일 영향 | 심각도 |
|------|------|--------|-------------|--------|
| `components/layout/InvestingHeader.tsx` | 32, 55, 99 | `max-w-[1400px]` | 미사용(`InvestingHeader`는 `app/layout.tsx`에 import되지 않음). 실 영향 없음 | INFO |
| `components/thesis/dashboard/IndicatorRow.tsx` | 110, 115, 132 | `min-w-[60px]`, `min-w-[120px]`, `max-w-[100px]` | 값 + 변동률 + 스파크라인 합계 280px 이상이 한 줄에 강제됨. 375px - padding 32px = 343px의 80% 점유 → **종목명/지표명이 2글자 truncate**. 실제로 `flex items-center gap-3 pl-4` 안에서 4컬럼 강제 | MAJOR |
| `components/eod/StockRow.tsx` | 55, 66 | `truncate max-w-[140px]`, `min-w-[72px]` | 회사명 매우 일찍 잘림. "Microsoft Corp" 정도까지만 | MINOR |
| `components/news/AINewsBriefingCard.tsx` | 70 | `max-w-[200px]` (진행바) | 박스 안에 들어가므로 OK | OK |
| `components/strategy/ScreenerTable.tsx` | 209, 224, 307 | `max-w-[180px]`, `max-w-[120px]` | 테이블 셀 내부 truncate. `overflow-x-auto` 부모 있음 → OK | OK |
| `components/admin/SystemTab.tsx`, `admin/shared/TaskLogViewer.tsx` | - | `max-w-[240px]`, `max-w-[260px]` | Admin은 데스크톱 전용. 영향 낮음 | INFO |
| `components/rag/ChatInterface.tsx` | 198 | `h-[52px] w-[52px]` | 입력 송신 버튼. 52×52 → HIG 충족 | OK |

### 브레이크포인트 없이 데스크톱 전용 가정

| 파일 | 사용 패턴 | 모바일 영향 | 심각도 |
|------|----------|-------------|--------|
| `components/screener/PresetGallery.tsx` | `grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6` (309, 355, 380, 405, 430) | 모바일 2열 → 카드당 ~150px 폭. 카드 내부에 이름+Enhanced 뱃지+적용중 뱃지+필터 요약+상세설명 모두 압축 | MAJOR |
| `app/dashboard/page.tsx`, `app/portfolio/page.tsx` 등 | `grid grid-cols-1 md:... lg:...` | 모바일은 1열 — OK | OK |
| `components/screener/SectorHeatmap.tsx` | `<ResponsiveContainer width="100%" height={400}>` Treemap | Treemap은 `width<60 || height<40` 타일 텍스트를 숨김. 11개 섹터를 375×400에 분할하면 **상당수 타일이 빈 사각형**으로 표시 | MINOR |

### 테이블/차트 가로 스크롤 처리

| 파일 | overflow-x-auto | 모바일 결과 | 심각도 |
|------|----------------|-------------|--------|
| `stocks/StockTable.tsx` (34) | ✅ | 가로 스크롤로 7컬럼 접근 가능. 그러나 모바일 카드뷰가 별도 없음 | MAJOR |
| `portfolio/PortfolioTable.tsx` (259) | ✅ | 가로 스크롤만 — 비교/정렬 어려움. 카드뷰가 portfolio/page.tsx에 별도 존재(228줄) → toggle 가능 | OK |
| `strategy/ScreenerTable.tsx` (128) | ✅ + `MobileStockCard.tsx` 별도 존재 | 카드뷰 있음 → OK | OK |
| `app/watchlist/page.tsx` (294) | ✅ | 카드뷰 없음 | MAJOR |
| `validation/LeaderComparisonSection.tsx` (47) | ✅ | 가로 스크롤 — 데이터 비교가 핵심인데 모바일에서 어려움 | MAJOR |
| `components/admin/*` 다수 | ✅ | Admin은 데스크톱 전용으로 가정. 영향 없음 | INFO |
| `app/stocks/[symbol]/page.tsx` (843) | ✅ | 재무제표 가로 스크롤. 컬럼명이 분기별이라 옆으로 길어짐 → 모바일에서 항목명이 사라짐 | MAJOR |

---

## 터치 타겟 (Apple HIG 44×44pt 기준)

### BLOCKER — 핵심 인터랙션이 20~32px 수준

| 파일:라인 | 요소 | 측정 (대략) | 사용 빈도 |
|-----------|------|-------------|-----------|
| `components/thesis/dashboard/IndicatorRow.tsx:182` | 1M/1Y/3Y/5Y 기간 선택 버튼 (`px-2.5 py-0.5 text-[10px]`) | ~30×18px | Thesis 관제실 핵심 인터랙션. 카드를 펼쳐 차트 기간 변경 시 항상 사용 |

### MAJOR — 32~36px (HIG 미달이지만 사용 가능)

| 파일:라인 | 요소 | 측정 | 위치 |
|-----------|------|------|------|
| `components/validation/PeerContextBar.tsx:40,52` | 프리셋 탭 (`px-3 py-1 text-xs`) | ~64×24px | 1차 검증 진입 시 매번 사용 |
| `components/chainsight/MobileCardList.tsx:88,100` | 카테고리 탭 (`px-3 py-1.5 text-sm`) | ~70×28px | Chain Sight 모바일 진입 화면 |
| `components/chainsight/MobileCardList.tsx:169,175,181` | "가설/탐색/검증" CTA (`text-xs py-1.5`) | ~80×28px | Chain Sight 노드별 다음 액션 |
| `app/chainsight/[symbol]/page.tsx:211,217,223` | 그래프 오버레이 바텀시트 CTA (`text-xs py-2`) | ~80×32px | 그래프에서 노드 선택 후 |
| `app/chainsight/[symbol]/page.tsx:251` | Depth 1/2/3 토글 (`px-3 py-1.5`) | ~38×30px | 그래프 깊이 변경 |
| `components/screener/AdvancedFilterPanel.tsx:236,257` | 카테고리 탭 (`px-3 py-1.5 text-xs`) | ~50×28px | 스크리너 고급 필터 |
| `components/screener/PresetGallery.tsx:241` | "상세 설명" 버튼 (`text-[10px]` + 12px 아이콘) | 영역 클릭 가능하지만 시각적으로 매우 작음 | 프리셋 카드마다 |
| `components/eod/SignalDetailSheet.tsx:188,197` | Chain Sight 섹터 링크/관계 지도 (`text-[10px]`) | 클릭영역 ~28px | 시그널 상세 |
| `components/thesis/AddIndicatorSheet.tsx:240` | freq 뱃지 `text-[9px]` | 표시용이지만 클릭 영역에 포함 | 지표 추가 시트 |
| `components/admin/news/AlertBadge.tsx:29` | `min-w-[18px] h-[18px]` 알림 뱃지 | 18×18 — 표시 전용이라 OK이지만 SignalFilterTabs(68)도 동일 | OK이면 제외 |
| `app/chainsight/[symbol]/page.tsx:206` | 모바일 그래프 시트 닫기 ✕ (`text-gray-400 text-sm`) | ~16px 글자만 | 시트 닫기 |

### MINOR — 표시용 작은 텍스트 (`text-[10px]`, `text-[11px]`) 클릭 요소

광범위하게 분포 (총 90+ 사용처). 클릭 영역이 부모 박스에 의존하기 때문에 실제 클릭 가능성은 OK이지만 가독성 부담:
- `components/market-pulse/MoverCard.tsx`, `MoverCardWithBatchKeywords.tsx` (5×2 = 10건) — 호버 툴팁
- `components/thesis/builder/SuggestionCard.tsx`, `NewsSelector.tsx`, `OptionButton.tsx` — 부수 라벨
- `components/thesis/dashboard/RealValueIndicatorCard.tsx`, `IndicatorRow.tsx` (95, 118, 148, 161, 167) — 메타 정보
- `components/keywords/KeywordTag.tsx:42` — `sm` 사이즈 프리셋이 `text-[10px]`
- `components/chainsight/MobileCardList.tsx:149,154,159` — 섹터/성장단계/자본DNA 칩 (표시용, OK)

---

## 네비게이션

### 글로벌 헤더/네비게이션 구조 (`app/layout.tsx`)

```
<Header />               ← md+ 데스크톱 nav, 모바일 햄버거 (md:hidden)
<main className="min-h-screen">
  {children}
</main>
<MobileNav />            ← md:hidden, fixed bottom-0, h-16
```

**작동 방식**:
- `Header.tsx`: 데스크톱(`md:flex`)에서 8개 라우트 노출. 모바일은 햄버거 메뉴 펼침 시 노출.
- `MobileNav.tsx`: 모바일 전용 fixed BottomNav. **5개 라우트만**: `홈 / 종목 / 뉴스 / 포트폴리오 / 내정보`.

### BLOCKER

| # | 이슈 | 파일:라인 | 영향 |
|---|------|----------|------|
| N-1 | **MobileNav가 핵심 기능 라우트 누락** — Chain Sight, Thesis Control, Market Pulse, Screener가 BottomNav에 없음 | `components/layout/MobileNav.tsx:10-16` | 모바일 사용자는 햄버거 → 메뉴 항목 클릭의 2탭 경로로만 핵심 기능 도달 가능. 발견성/이탈률 영향 |
| N-2 | **BottomNav 회피 패딩(`pb-20`) 누락** — `h-16` BottomNav가 fixed bottom-0이지만, 화면 하단 콘텐츠가 가려짐 | 누락 페이지: `chainsight/[symbol]`(154 `h-screen`, 173 `inset-0`), `ai-analysis/page.tsx:234`(`h-screen`), `market-pulse/page.tsx:98`, `news/page.tsx:126`, `portfolio/page.tsx:95`, `watchlist/page.tsx:172`, `dashboard/page.tsx:30`, `mypage/page.tsx:98` | 마지막 카드/리스트가 64px만큼 BottomNav에 가려짐. 특히 chainsight `h-screen` + 하단 노드 시트는 **선택된 노드 액션 버튼이 BottomNav 아래로 밀림** |
| N-3 | **viewport scaling 차단** — `userScalable: false, maximumScale: 1` | `app/layout.tsx:29-35` | iOS Safari/Android에서 핀치줌 차단. 시력 보조 사용자가 작은 텍스트(`text-[10px]` 다수) 확대 불가 → WCAG 1.4.4 위반 |

### MAJOR

| # | 이슈 | 파일:라인 |
|---|------|----------|
| N-4 | Header 햄버거 메뉴 펼침 시 z-index/포커스 트랩 미설정. 메뉴 외부 클릭 닫힘 처리 없음 | `Header.tsx:165-255` |
| N-5 | Chain Sight 데스크톱 좌측 AI Guide 패널은 `w-60` 항상 노출이지만, 햄버거 패턴 없이 `leftOpen` 토글 버튼만 있음. 모바일은 카드 리스트로 분기되지만, 데스크톱→모바일 사이즈 변경 시 즉각 반응하지 않을 수 있음(`window.innerWidth < 768` 단일 useEffect) | `app/chainsight/[symbol]/page.tsx:114-126` |

### Virtualization

`react-window`/`react-virtual`/`@tanstack/react-virtual` **사용 흔적 없음**. 다음 화면이 잠재적 부하:
- Screener 결과 리스트 (수백 종목 이상 가능)
- Watchlist (사용자 선언적 목록 — 보통 수십 개라 OK)
- News list (페이징 사용 시 OK)

→ 현 단계에서 **블로커 아님**. 페이징/무한스크롤로 대처 중.

---

## 차트/그래프

### Recharts ResponsiveContainer 사용 현황

11개 차트 컴포넌트 검사. **모두 `<ResponsiveContainer width="100%" height={N}>` 사용**:

| 파일 | height | 모바일 영향 |
|------|--------|-------------|
| `thesis/dashboard/IndicatorRow.tsx` | 160 (daily), 140 (quarterly) | 적정. 단 Y축 `width={55}` 고정 → 375px의 14% 점유 |
| `thesis/dashboard/IndividualMiniCharts.tsx` | 100 | 적정 |
| `validation/MetricBarChart.tsx` | (미확인 — `ResponsiveContainer` 사용) | 가정상 적정 |
| `admin/news/MLTrendChart.tsx` | (미확인) | Admin은 데스크톱 |
| `screener/SectorHeatmap.tsx` | 400 | **MINOR** — 11 섹터를 375×400에 분할 시 작은 타일 텍스트 사라짐(`width<60 \|\| height<40` 가드) |
| `stock/StockChart.tsx` | (미확인) | - |
| `news/SentimentChart.tsx` | (미확인) | - |
| `macro/YieldCurveChart.tsx` | (미확인) | - |
| `portfolio/PortfolioChart.tsx` | 400 (Pie/Bar) | Pie는 OK. Bar는 가로 시리즈 많아지면 라벨 겹침 가능 |
| `charts/StockPriceChart.tsx` | 400 (default prop) | OK |

### 분기 스파크라인의 모바일 가독성

| 파일 | 패턴 | 모바일 영향 | 심각도 |
|------|------|-------------|--------|
| `components/thesis/dashboard/QuarterlySparkline.tsx:54` | Q1/Q2/...Q4 라벨이 `text-[8px]` | 라벨 거의 안 보임. 4분기 표시는 카드 안 `flex-1`이라 ~25px 폭 | MINOR |
| `components/eod/MiniSparkline` (StockRow.tsx 사용) | `width={64} height={24}` 고정 | 작은 추세선만 표시 — 의도된 디자인 | OK |
| `components/eod/SignalCard.tsx:188` | `width={52} height={20}` | 의도된 마이크로뷰 | OK |

### 그래프 캔버스 (Force Graph 2D)

`app/chainsight/[symbol]/page.tsx`:
- 모바일 분기 처리 ✅ (`isMobile && !graphOverlay` → `<MobileCardList>` 렌더)
- `graphOverlay` 모드는 fixed inset-0 z-50, BottomNav 위로 덮음. 닫기 버튼 노출됨 → OK
- 그러나 노드 선택 후 바텀시트가 `max-h-48`이고 BottomNav(h-16) **위로 위치하지 않음** — `inset-0` 안의 flex-col 마지막 자식이라 화면 바닥에 붙음. 단 부모가 `fixed inset-0 z-50`라 BottomNav를 가린 상태이므로 OK.

→ 그래프 자체는 모바일 대응 양호. 다만 **3개 액션 버튼(`text-xs py-2`)이 32px**로 HIG 미달.

---

## 페이지별 상세

### `/` (EOD Dashboard) — `app/page.tsx`

| 심각도 | 이슈 |
|--------|------|
| OK | `pb-20 md:pb-0` (71) — BottomNav 회피 적용 |
| MAJOR | `SignalFilterTabs`(`overflow-x-auto`) 카운트 뱃지 `text-[11px]` — 작지만 OK |
| MAJOR | `SignalDetailSheet` 시트 패널 모바일에서 `max-h-[90vh]` — `top: 10vh` 노출이라 헤더와 겹치는 영역 미발생 OK. 단 내부 "관계 지도" 링크 `text-[10px]` 클릭 영역 작음 |

### `/stocks/[symbol]` — `app/stocks/[symbol]/page.tsx`

| 심각도 | 이슈 |
|--------|------|
| BLOCKER | `pb-20` 누락 (258 `min-h-screen` only). 마지막 탭 콘텐츠가 BottomNav에 가림 |
| MAJOR | 재무제표 탭(843) `overflow-x-auto` — 모바일에서 가로 스크롤로 항목명(`첫 번째 컬럼`)이 사라짐. `sticky left-0` 미적용 |
| MAJOR | Validation 탭은 `isMobile` 분기로 카테고리 chip + 단일 카테고리 리스트로 잘 분기(1027~) |
| MINOR | `PeerContextBar` 프리셋 탭 ~24px (위 N에 기재) |

### `/chainsight/[symbol]`

| 심각도 | 이슈 |
|--------|------|
| BLOCKER | `h-screen`(154, 236) — BottomNav가 화면 하단을 64px 가림. `pb-20` 또는 `h-[calc(100vh-4rem)]` 필요 |
| MAJOR | MobileCardList 카테고리 탭 ~28px, CTA 3개 버튼 ~28px |
| MAJOR | 그래프 오버레이 바텀시트 닫기 ✕ (206) ~16px 글자 |
| OK | 모바일/데스크톱 분기 처리 ✅ (`isMobile`로 컴포넌트 자체 분리) |

### `/thesis` (관제실)

| 심각도 | 이슈 |
|--------|------|
| OK | `app/thesis/(list)/layout.tsx`에 `pb-20` 적용. 개별 페이지(`[thesisId]/page.tsx`)에도 `pb-20` 적용 |
| BLOCKER | `IndicatorRow` 1M/1Y/3Y/5Y 버튼 `px-2.5 py-0.5 text-[10px]` ~30×18px |
| MAJOR | `IndicatorRow` 메인 행: 값(60px) + 변동률(120px) + 스파크라인(100px) + 지지/반박 라벨이 한 줄 강제. 375px - padding 32px = 343px의 ~80% 점유 → 지표명 truncate 발생 |
| MAJOR | `AddIndicatorSheet` 지표 항목 freq 뱃지 `text-[9px]` 매우 작음 |
| MINOR | `RealValueIndicatorCard.tsx`의 추천 이유/설명 라벨 `text-[10px]` 다수 |

### `/screener`

| 심각도 | 이슈 |
|--------|------|
| MAJOR | `PresetGallery` 모바일 2열 그리드 — 카드당 ~150px에 5개 정보(이름/뱃지/뱃지2/필터요약/상세설명) 압축 |
| MAJOR | `AdvancedFilterPanel` 카테고리 탭 ~28px (8개 이상 → 줄바꿈) |
| MAJOR | 결과 테이블에 모바일 분기(`MobileStockCard.tsx`) 존재. **그러나 페이지(app/screener/page.tsx)에서 사용 여부 미확인** — `ScreenerDashboard`/`ScreenerTable` 모두 데스크톱 컴포넌트로 보임 |
| OK | `MobileStockCard.tsx` 자체는 모바일 친화적 디자인 (시가총액/PER/거래량 3컬럼 그리드, ROE/배당/베타 별도 칩) |

### `/portfolio`

| 심각도 | 이슈 |
|--------|------|
| MAJOR | `pb-20` 누락(95) — BottomNav 가림 |
| OK | 카드뷰 ↔ 테이블뷰 토글 존재(228) — 모바일에서 카드 기본 |
| MINOR | 테이블 모드는 6컬럼 grid (`md:grid-cols-3 lg:grid-cols-6`) — 모바일은 2열로 OK |

### `/watchlist`

| 심각도 | 이슈 |
|--------|------|
| MAJOR | `pb-20` 누락 |
| MAJOR | 테이블만 존재 — 카드뷰 분기 없음. `overflow-x-auto`만으로 가로 스크롤 |

### `/news`

| 심각도 | 이슈 |
|--------|------|
| MAJOR | `pb-20` 누락 |
| MINOR | `KeywordDetailSheet`, `NewsHighlightedStocks`에서 `overflow-x-auto scrollbar-hide` 사용 — 칩 가로 스크롤 OK |

### `/market-pulse`

| 심각도 | 이슈 |
|--------|------|
| MAJOR | `pb-20` 누락 |
| MINOR | `MoverCard.tsx` 호버 툴팁이 `text-[10px]` — 모바일은 호버 없음 → 정보 접근 불가. 탭/롱프레스 대체 미구현 |

### `/dashboard` (구 데모)

| 심각도 | 이슈 |
|--------|------|
| MAJOR | `pb-20` 누락 |
| MINOR | 사용 빈도 낮음(EOD가 메인). 우선순위 낮음 |

### `/admin`

| 심각도 | 이슈 |
|--------|------|
| INFO | Admin은 데스크톱 전용 가정. `overflow-x-auto` 테이블 다수, 모바일 대응 비투자 정당화 |

### `/ai-analysis`

| 심각도 | 이슈 |
|--------|------|
| BLOCKER | `h-screen flex-col` (234) — BottomNav 가림 |
| OK | RAG 챗 화면 자체는 모바일 친화적 (입력바 가로 100% + 송신 52×52px) |

---

## 권장 우선순위

1. **(BLOCKER 한 번에 해결)** `app/layout.tsx`의 `viewport` 설정에서 `userScalable: false`/`maximumScale: 1` 제거 → WCAG 준수.
2. **(BLOCKER)** 글로벌 `<main>`에 `pb-16 md:pb-0` 적용하거나, 각 페이지 root에 `pb-20` 일괄 패치. Chain Sight `h-screen` 페이지는 `h-[calc(100vh-4rem)]` 또는 BottomNav 자체를 페이지별 옵트아웃하는 패턴 도입.
3. **(BLOCKER)** `MobileNav.tsx` 라우트 재설계: 5개 슬롯에 핵심 기능 우선 배치. 후보: `홈 / Chain Sight / Thesis / 포트폴리오 / 더보기(햄버거 시트)`.
4. **(BLOCKER)** Thesis `IndicatorRow` 기간 선택 버튼 패딩 확대(`px-3 py-1.5`로) 또는 별도 셀렉터 컴포넌트화.
5. **(MAJOR 묶음)** Chain Sight 모바일 CTA, Validation 프리셋 탭, Screener 카테고리 탭의 패딩 일괄 `py-1.5 → py-2.5`로 상향.
6. **(MAJOR)** Stocks 재무제표 첫 번째 컬럼(항목명) `sticky left-0 bg-*` 적용.
7. **(MINOR)** `text-[10px]` 라벨은 `text-xs(12px)`로 통합. 디자인 토큰 차원에서 정리.

이상 23개 이슈. 코드 수정 없음. 보고서만 작성.
