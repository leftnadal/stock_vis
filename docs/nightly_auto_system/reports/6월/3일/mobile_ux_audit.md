# 모바일 UX 감사 보고서

> 대상: `frontend/` (Next.js 16.2.6 + Tailwind) · 기준 뷰포트 **375px**
> 방식: **읽기 전용 정적 코드 분석** (코드 수정 없음)
> 일자: 2026-06-03
> 범위: 컴포넌트 205개 + 페이지 30개 (총 tsx 255개)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 **BLOCKER** | 2 | bottom nav '종목' 탭 깨진 라우트(`/stocks` 404), 뷰포트 줌 차단(`userScalable:false`) |
| 🟠 **MAJOR** | 6 | bottom nav main 하단 패딩 누락(콘텐츠 가림), bottom nav 5탭이 핵심 라우트 미커버, Portfolio/Watchlist 테이블 카드 미전환, IndicatorRow 2행 고정폭 overflow, IndicatorRow 기간 셀렉터 터치타겟 미달, 긴 목록 가상화 전무 |
| 🟡 **MINOR** | 7 | text-[10px/11px] 125회(가독성), MarketGraphCanvas 560px 고정 높이, 차트 축 폰트 9px, SignalDetailSheet 칩 터치타겟, Header 모바일 메뉴 죽은 코드, QuarterlySparkline 모바일 가독성, dashboard 통계 grid-cols-3 |

**총평**: 일부 영역(MobileNav, BottomSheet 패턴, Chainsight 모바일 분기, Recharts ResponsiveContainer 100%)은 모바일 대응이 우수하나, **전역 네비게이션 무결성**과 **데이터 밀집 화면(테이블·관제실)**에서 모바일 결함이 집중됨. 특히 BLOCKER 2건은 즉시 검증·수정 권장.

---

## 반응형 누락

### 🔴 BLOCKER

**B-1. 뷰포트 줌 차단 — `userScalable: false` + `maximumScale: 1`**
- 위치: `app/layout.tsx:30-36`
```ts
viewport: { width: "device-width", initialScale: 1,
  maximumScale: 1, userScalable: false, viewportFit: "cover" }
```
- 영향: 본 앱은 `text-[10px]`/`text-[11px]`가 **125회** 사용될 만큼 작은 폰트 의존도가 높음. 그 상태에서 사용자 핀치 줌까지 차단 → 저시력 사용자 콘텐츠 접근 불가. WCAG 2.1 **1.4.4(Resize Text)**/**1.4.10(Reflow)** 위반.
- 권장: `maximumScale`/`userScalable` 제거 (PWA라도 줌 허용이 접근성 기본).

### 🟠 MAJOR

**M-1. Portfolio/Watchlist 테이블 — 모바일 카드 미전환, 가로 스크롤만**
- 위치: `components/portfolio/PortfolioTable.tsx:259-260` (`overflow-x-auto` + `min-w-full`), 셀 다수 `px-6 py-4 whitespace-nowrap` (8+ 컬럼)
- 영향: 375px에서 8컬럼 테이블이 가로 스크롤로만 노출. 종목명·수익률 등 핵심 컬럼이 화면 밖으로 밀림. **동일 성격의 Screener는 `MobileStockCard`로 카드 전환**(`components/screener/MobileStockCard.tsx`)하는데 Portfolio/Watchlist는 미적용 → 패턴 불일치.
- 참고: `overflow-x-auto`는 적용되어 있어 "잘림"은 아니나(스크롤 가능), 핵심 데이터가 기본 화면에서 안 보이는 구조.

**M-2. IndicatorRow 2행 고정폭 합산 overflow (thesis 관제실)**
- 위치: `components/thesis/dashboard/IndicatorRow.tsx:108-143`
```
값 min-w-[60px] + 변동률 min-w-[120px] + 스파크라인 max-w-[100px] + 지지/반박 라벨
+ gap-3(×3) + pl-4
```
- 영향: 고정 하한 합계가 `60+120 = 180px` + gap/padding + "전분기대비 +3.2%"가 `min-w-[120px]`에 들어가야 함. 375px에서 라벨 텍스트가 길면 한 줄에 모두 수용 불가 → 변동률 라벨 줄바꿈/잘림 또는 스파크라인 압착. flex 줄바꿈(`flex-wrap`) 미적용.
- 관제실은 지표 카드가 수직 반복되는 핵심 화면이라 체감도 높음.

### 🟡 MINOR

- **MN-1. 브레이크포인트 0개 컴포넌트 154/205(75%)**: 다수는 부모가 반응형을 책임지는 atomic(badge/tag/card 내부)이라 즉시 문제는 아님. 단, **페이지 레벨에서 sm/md/lg 전무한 10개 페이지**(`app/admin`, `app/chainsight`(×4), `app/coach/e4`, `app/thesis/*`(×4))는 레이아웃 검증 권장.
- **MN-2. MarketGraphCanvas 높이 `h-[560px]` 고정** (`components/chainsight/MarketGraphCanvas.tsx:712,760`): 폭은 `ResizeObserver`로 동적 대응(✅)하나 높이 560px는 모바일 세로 화면(667~812px)의 70%+를 점유. 단일 화면에 그래프만 가득 차 주변 컨텍스트 소실.

---

## 터치 타겟

> 기준: Apple HIG **44×44pt**

### 🟠 MAJOR

**M-3. IndicatorRow 기간 셀렉터 (1M/1Y/3Y/5Y) 터치타겟 미달**
- 위치: `components/thesis/dashboard/IndicatorRow.tsx:179-190`
```tsx
className="px-2.5 py-0.5 text-[10px] rounded ..."  // 높이 ≈ 20px
```
- 영향: 실제 높이 약 20px (`py-0.5` + `text-[10px]`). 44px의 절반 미만. 인접 4버튼이 `gap-1.5`로 촘촘 → 오터치 빈발. 차트 기간 전환은 핵심 인터랙션.

### 🟡 MINOR

- **MN-3. SignalDetailSheet 클릭 칩** (`components/eod/SignalDetailSheet.tsx:188`): `text-[10px] px-1.5 py-0.5 cursor-pointer` → 터치타겟 미달.
- **MN-4. text-[10px]/[11px] 총 125회**: 클릭 비대상(메타·날짜·전제 라벨)이 대부분이라 가독성 이슈에 가깝지만, 클릭 요소와 혼재된 화면에서 탭 정확도 저하. 빈도 상위: `IndicatorRow`(7), `thesis/new`(7), `MoverCard`/`MoverCardWithBatchKeywords`(6), `KeywordTag`(6), `SuggestionCard`(5), `PresetGallery`(5).

### ✅ 양호 (터치타겟 준수 사례)

- `MobileNav` 하단 탭: `min-h-[44px]` + `h-16`(64px) (`layout/MobileNav.tsx:22,34`)
- Validation 프리셋 탭: `min-h-[44px] px-4 py-2` + `flex-wrap` (`validation/PeerContextBar.tsx:40,54`) — **요청에서 우려한 프리셋 탭은 실제로 44pt 준수**
- MarketGraphCanvas 빈 상태 노드 버튼: `min-h-[68px]` (`MarketGraphCanvas.tsx:676`)
- Chainsight 노드: SVG/Canvas 기반 force-graph, `isMobile` 분기로 `MobileCardList` 대체 제공(아래 네비 참조)

---

## 네비게이션

### 🔴 BLOCKER

**B-2. Bottom nav '종목' 탭 → `/stocks` 깨진 라우트 (404)**
- 위치: `components/layout/MobileNav.tsx:13` → `href: '/stocks'`
- 검증: `app/stocks/` 하위에는 `[symbol]/page.tsx`만 존재하고 **`app/stocks/page.tsx` 없음**. `next.config`의 `rewrites`는 `/api/v1/*`만 처리(라우트 매핑 없음), middleware 없음 → `/stocks` 진입 시 **404**.
- 영향: 모바일 5개 핵심 탭 중 1개가 사망. 코드 주석에 `'/profile'→'/mypage'` 수정 이력은 있으나 `/stocks`는 누락됨.

### 🟠 MAJOR

**M-4. main 하단 패딩 누락 → bottom nav가 콘텐츠 가림**
- 위치: `app/layout.tsx:62` `<main className="min-h-screen">` (하단 패딩 없음), MobileNav는 `fixed bottom-0 ... h-16`(64px)
- 영향: 페이지 최하단 콘텐츠/버튼이 64px 고정 bottom nav에 가려짐. 하단 패딩(`pb-16`류) 처리 페이지는 **3개뿐**(`thesis/(list)/layout.tsx`, `thesis/[thesisId]/page.tsx`, `app/page.tsx`). 나머지 ~27개 페이지(`portfolio`, `watchlist`, `news`, `screener`, `chainsight`, `coach/*` 등)는 미처리 → 하단 액션 버튼/마지막 항목 탭 불가 위험.
- 권장: `layout.tsx`의 `<main>`에 `pb-16 md:pb-0` 전역 적용(단일 소스).

**M-5. Bottom nav 5탭이 핵심 라우트를 미커버**
- 위치: `MobileNav.tsx:11-17` — 탭: 홈/종목/뉴스/포트폴리오/내정보
- 영향: 데스크톱 Header(`Header.tsx:42` `hidden md:flex`)는 **모바일에서 완전 숨김**이고, 햄버거 버튼도 `hidden`(`Header.tsx:157,160`, 주석상 의도적 비활성)이라 **모바일 상단 네비 진입점이 전무**. 결과적으로 `Chain Sight`, `Thesis Control`, `Market Pulse`, `Screener`, `Watchlist`, `Dashboard`는 **모바일에서 직접 도달 경로 없음**(딥링크/내부 링크로만 접근). 정보구조상 주요 기능 다수가 모바일에서 고립.

### 🟡 MINOR

- **MN-5. Header 모바일 메뉴 죽은 코드**: `Header.tsx:167-257`의 `isMenuOpen` 토글 패널이 존재하나, 이를 여는 버튼이 `hidden`(`:160`)이라 영구히 열 수 없음 → 도달 불가 코드. 의도라면 제거, 아니라면 M-5 해결책으로 부활 검토.

### 🟠 가상화 (목록 성능)

**M-6. 긴 목록 가상화(virtualization) 라이브러리 전무**
- 검증: `react-window`/`react-virtual`/`@tanstack/react-virtual`/`virtualizer` **사용처 0건**
- 영향: News 피드, Screener 결과, Chainsight 관계/스토리 피드, 키워드 목록 등 수백 행 렌더 시 모바일(저사양 기기) 스크롤 버벅임·메모리 압박 우려. 데이터 규모가 큰 화면 우선 도입 권장.

### ✅ 양호 (네비/모바일 분기 사례)

- `MobileNav` 하단 탭바 자체는 존재 + `md:hidden`로 모바일 한정 노출(✅)
- Chainsight: `app/chainsight/[symbol]/page.tsx:117` `setIsMobile(window.innerWidth < 768)` + `getBoundingClientRect`/`ResizeObserver`로 캔버스 동적 사이징, 모바일은 `MobileCardList` 대체 제공
- Stocks 상세: `app/stocks/[symbol]/page.tsx:928` `isMobile` 분기
- 가로 스크롤 탭/칩: `SignalFilterTabs`, `RelationFilterChips`, `AdminTabNav` 등 `overflow-x-auto` 처리(✅)
- BottomSheet 패턴 채택: `thesis/common/BottomSheet`, `eod/SignalDetailSheet`, `news/KeywordDetailSheet` 등 모바일 친화 인터랙션 도입

---

## 차트/그래프

### ✅ 양호

- **Recharts ResponsiveContainer 적용률 100%**: Recharts import 14개 파일 == ResponsiveContainer 사용 14개 파일 완전 일치. 차트 폭 반응형은 전역 보장됨.
  - 대상: `StockPriceChart`, `StockChart`, `YieldCurveChart`, `SentimentChart`, `PortfolioChart`, `MetricBarChart`, `SectorHeatmap`, `MLTrendChart`, `IndividualMiniCharts`, `IndicatorRow`, market-pulse-v2 detail 4종

### 🟡 MINOR

- **MN-6. 차트 축 폰트 9px**: `IndicatorRow.tsx:207,248` `fontSize={9}` (XAxis). 375px에서 눈금 라벨 가독성 저하. YAxis `width={55}`(`:212`)는 모바일 차트 폭의 ~15%를 축이 점유.
- **MN-7. QuarterlySparkline 모바일 가독성**: `IndicatorRow.tsx:132` 인라인 스파크라인 `max-w-[100px]`에 최근 4분기 압축. 100px 내 4점 추이는 변별 어려움(보조 지표라 영향 제한적).
- **MN-8. dashboard 통계 `grid-cols-3`**: `app/dashboard/page.tsx:117-129` `sm:grid sm:grid-cols-3` — `sm` 미만(375px)에서는 grid 미적용(세로 스택)이라 실제 문제 없음. 단 `MarketBreadthCard.tsx:107`, `MobileStockCard.tsx:164`, `FlowDetail.tsx:34`의 `grid-cols-3`(반응형 prefix 없음)는 375px에서 3등분 강제 → 셀 내 숫자/라벨 압착 가능(검증 권장).

---

## 페이지별 상세

| 페이지 | 모바일 상태 | 주요 이슈 | 심각도 |
|--------|------------|-----------|--------|
| `app/layout.tsx` (전역) | ⚠️ | 줌 차단(B-1), main 하단패딩 누락(M-4), Header 모바일 숨김(M-5) | BLOCKER/MAJOR |
| `MobileNav` (전역) | ⚠️ | '종목'→`/stocks` 404(B-2), 핵심 라우트 미커버(M-5) | BLOCKER/MAJOR |
| `app/portfolio` | ⚠️ | 8컬럼 테이블 카드 미전환·가로스크롤(M-1), 하단패딩 없음(M-4) | MAJOR |
| `app/watchlist` | ⚠️ | 테이블 `overflow-x-auto`만, `max-w-7xl` 데스크톱 지향, 하단패딩 없음 | MAJOR |
| `app/thesis/[thesisId]` (관제실) | ⚠️ | IndicatorRow 2행 고정폭 overflow(M-2), 기간셀렉터 터치타겟(M-3). 단 `max-w-lg`+`pb` 적용은 ✅ | MAJOR |
| `app/thesis/(list)`, `/new`, `/indicators`, `/close` | ⚠️ | 페이지 레벨 브레이크포인트 0개, `text-[10px/11px]` 밀집(`thesis/new` 7회) | MINOR |
| `app/chainsight/[symbol]` | ✅ | `isMobile` 분기 + `MobileCardList` + 캔버스 동적 사이징. 그래프 높이 560px 고정만 보완(MN-2) | MINOR |
| `app/chainsight` (목록/watchlist ×3) | ⚠️ | 페이지 레벨 브레이크포인트 0개 — 레이아웃 검증 권장 | MINOR |
| `app/screener` | ✅ | `MobileStockCard` 카드 전환 + `isMobile` 분기(640) 모범. `px-2` 다용은 점검 | 양호 |
| `app/news` | △ | `grid-cols-1`/`grid-cols-2` 반응형 적용. 가상화 부재(M-6), 하단패딩 없음 | MAJOR(목록) |
| `app/market-pulse` / `market-pulse-v2` | △ | 차트 ResponsiveContainer ✅, `FlowDetail`/`BreadthDetail` `grid-cols-3` 압착 가능(MN-8) | MINOR |
| `app/dashboard` | ✅ | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 정상 반응형 | 양호 |
| `app/coach/e1~e6` | △ | `e4` 브레이크포인트 0개(`max-w-3xl`), 채팅/말풍선 UI 모바일 가독성 검증 권장, 하단패딩 없음 | MINOR |
| `app/admin/*` | — | 데스크톱 관리자 화면(테이블 다수 `overflow-x-auto`). 모바일 비대상으로 간주, 우선순위 낮음 | (제외) |
| `app/stocks/[symbol]` | ✅ | `isMobile` 분기 적용 | 양호 |
| `app/validation`(stocks 상세 통합) | ✅ | `PeerContextBar` 프리셋 `min-h-[44px]`+`flex-wrap`, 테이블 `overflow-x-auto` | 양호 |

---

## 권장 우선순위 (수정은 본 감사 범위 밖 — 참고용)

1. **B-2** `/stocks` 라우트 복구 또는 bottom nav href 교정 (404 즉시 해소)
2. **B-1** viewport 줌 허용 복원 (접근성)
3. **M-4** `layout.tsx` `<main>`에 `pb-16 md:pb-0` 전역 적용 (1줄로 27개 페이지 가림 해소)
4. **M-5** 모바일 네비 정보구조 재설계 (bottom nav 확장 or 햄버거 부활)
5. **M-1** Portfolio/Watchlist에 Screener식 `MobileStockCard` 패턴 이식
6. **M-2 / M-3** IndicatorRow `flex-wrap` + 기간 셀렉터 `min-h-[44px]`
7. **M-6** 대형 목록 가상화 도입 (News/Screener/Chainsight 피드)

---

### 부록: 분석 방법

- 고정폭: `grep -E 'w-\[[0-9]+px\]|min-w-\[[0-9]+px\]|max-w-\[[0-9]+px\]'`
- 브레이크포인트: 파일별 `\b(sm|md|lg|xl):` 존재 여부 카운트
- 터치타겟: `text-[10px/11px]` ∩ (`button|onClick|Link|cursor-pointer`)
- 차트: `recharts` import 파일 vs `ResponsiveContainer` 사용 파일 대조
- 라우트: `app/` 디렉토리 실재 `page.tsx` vs `next.config` rewrites/middleware 대조
- 모든 결론은 `파일:라인` 증거 기반. 일부 항목(`grid-cols-3` 압착, coach 채팅 가독성)은 정적 분석 한계로 **실기기 렌더 검증 권장**으로 명시.
