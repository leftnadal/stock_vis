# 모바일 UX 감사 보고서

> **감사 일자**: 2026-05-31
> **대상**: `frontend/` (Next.js 16.2.6 / Tailwind), 컴포넌트 205개 + 페이지 30개
> **기준 뷰포트**: 375px (iPhone SE/13 mini), Apple HIG 44×44pt 터치 타겟
> **성격**: 읽기 전용 정적 코드 감사 (코드 미수정). 실기기 렌더링 측정 아님.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 BLOCKER | 2 | (1) `userScalable: false` 핀치 줌 차단 (2) MobileNav `/stocks` → 인덱스 라우트 부재 (404 추정) |
| 🟠 MAJOR | 5 | (1) 하단 네비 회피 패딩 페이지별 누락 (2) 모바일 네비 기능 커버리지 공백 4개 (3) 종목 상세 탭바 가로 오버플로 (4) Chain Sight 그래프 노드 터치 타겟 미달 + 모바일 폴백 부재 (5) safe-area-inset 미적용 |
| 🟡 MINOR | 7 | 소형 토글/필터 버튼 터치 타겟, text-[10px]/[11px] 가독성, dead code 2건 등 |

**총평**: 과거 모바일 감사(`audit P0 #12/#13`) 흔적이 명확히 남아 있어 **핵심 동선의 터치 타겟·반응형은 상당 부분 정비됨** (MobileNav, PeerContextBar 프리셋 탭, QuarterlySparkline 막대, ScreenerTable 액션, 종목 L1 탭 모두 `min-h-[44px]` 적용). 그러나 **(a) 전역 레벨 결함 2건**(줌 차단, 하단 네비 패딩 일관성)과 **(b) 모바일 진입 동선 자체의 구조적 공백**(주요 4개 기능이 모바일에서 도달 불가)이 남아 있어 실사용 시 체감 품질을 떨어뜨린다.

---

## 반응형 누락

### 🔴 BLOCKER

**1. 뷰포트 핀치 줌 차단** — `frontend/app/layout.tsx:29-35`
```ts
viewport: {
  width: "device-width", initialScale: 1,
  maximumScale: 1, userScalable: false,   // ← 확대 금지
  viewportFit: "cover",
}
```
- `userScalable: false` + `maximumScale: 1` 은 사용자의 핀치 줌을 전면 차단. **WCAG 2.1 SC 1.4.4 (Resize Text) 위반**.
- 본 앱은 `text-[10px]`/`text-[11px]` 미세 텍스트를 재무·지표 카드 전반에 사용 → 저시력 사용자가 확대조차 못 함. 영향 범위가 전역이라 BLOCKER로 분류.

### 🟠 MAJOR

**2. 하단 고정 네비 회피 패딩의 페이지별 누락**
- `MobileNav`는 `fixed bottom-0 ... h-16`(64px). 콘텐츠 하단이 이 바에 가려지지 않으려면 페이지 루트에 `pb-16`~`pb-20` 필요.
- 적용된 페이지: `app/page.tsx`(`pb-20 md:pb-0`), `thesis/*` 일부 **뿐**.
- **미적용 확인**: `portfolio/page.tsx`, `watchlist/page.tsx`, `news/page.tsx`, `chainsight/page.tsx` (모두 `min-h-screen`만, `pb-*` 없음). 그 외 `dashboard`, `market-pulse`, `screener`, `coach/e1~e6`, `mypage`, `admin`, `ai-analysis`도 동일 패턴 추정.
- **영향**: 목록/테이블 마지막 행, 페이지네이션, 하단 CTA 버튼이 64px 바에 가려져 탭 불가.
- **권장**: 루트 `layout.tsx`의 `<main>`에 `pb-16 md:pb-0`를 단일 적용하여 페이지별 누락을 구조적으로 제거.

### 🟡 MINOR / 양호

- **고정 폭 오버플로 위험 낮음**: `w-[NNNpx]` 3자리 고정폭은 거의 전부 `max-w-[...]`(truncate 동반) 또는 중앙 정렬 `max-w-[1400px]`로, 375px에서 overflow를 일으키지 않음. 유일한 큰 고정폭 `SignalDetailSheet`의 `w-[420px]`도 `w-full md:w-[420px]`로 모바일은 전체 폭(양호).
- **브레이크포인트 적용률**: 255개 tsx 중 72개(28%)가 `sm:/md:/lg:` 사용. 데스크톱 전용 화면(admin/* 다수)은 모바일 우선순위 낮아 허용 가능.
- **테이블 가로 스크롤**: `<table>` 13개 파일 중 핵심(StockTable, PortfolioTable, ScreenerTable, stocks 재무표 `stocks/[symbol]/page.tsx:843`, LeaderComparisonSection)이 모두 `overflow-x-auto` 래퍼 보유 → 양호. 나머지는 admin 테이블.

---

## 터치 타겟

### 🟠 MAJOR

**3. Chain Sight 그래프 노드** — `frontend/components/chainsight/MarketGraphCanvas.tsx:65-66`
```ts
const NODE_SIZE_MAP = { xl: 20, lg: 17, md: 14, sm: 10 };  // 반경(px)
```
- 노드 직경 20~40px(2차 노드 sm=20px) 로 **44pt 미달**. `pointer: coarse` 분기로 더블탭 처리는 있으나(`:481`), 작은 노드를 정확히 탭하기 어려움.
- 인기 섹터 버튼(`:676` `w-[110px] min-h-[68px]`)은 양호.

### 🟡 MINOR

| 위치 | 코드 | 추정 높이 | 비고 |
|------|------|----------|------|
| IndicatorRow 기간 선택 (1M/1Y/3Y/5Y) | `dashboard/IndicatorRow.tsx:182` `px-2.5 py-0.5 text-[10px]` | ~20px | 관제실 차트 기간 토글, 44pt 미달 |
| Screener 컨트롤 버튼 (뷰토글/AI키워드/테제/새로고침) | `app/screener/page.tsx:755,781,795,808` `p-1.5`/`py-1.5` | ~28px | 헤더 우측, 44pt 미달 |
| Screener 필터 제거 X | `app/screener/page.tsx` 다수 `<X className="h-3 w-3">` | ~12px | 필터 칩 제거, 매우 작음 |
| PeerContextBar 커스텀 "적용" / "peer 목록 보기" | `validation/PeerContextBar.tsx:85,118` `py-1.5`/`min-h` 없음 | ~28px | 프리셋 탭 본체는 `min-h-[44px]` 양호 |

### ✅ 양호 (이미 44pt 정비됨)
- `layout/MobileNav.tsx:34` `min-h-[44px]`
- `validation/PeerContextBar.tsx:40,54` 프리셋 탭 `min-h-[44px]`
- `dashboard/QuarterlySparkline.tsx:44` 막대 버튼 `min-h-[44px]`
- `strategy/ScreenerTable.tsx:323` 바구니 버튼 `min-h-[44px] min-w-[44px]`
- `stocks/[symbol]/page.tsx:388` L1 탭 `min-h-[44px]`

> **참고**: `text-[10px]`/`text-[11px]` 클릭 요소 다수 존재(IndicatorRow, MoverCard, SuggestionCard 등)하나 대부분은 라벨/디스플레이 텍스트. 클릭 요소에 한정하면 위 표가 핵심.

---

## 네비게이션

### 🔴 BLOCKER

**4. MobileNav "종목" 탭의 깨진 라우트** — `frontend/components/layout/MobileNav.tsx:13`
```ts
{ name: '종목', href: '/stocks', icon: TrendingUp },
```
- 라우트 목록상 `/stocks` 인덱스 페이지가 **없음** (`app/stocks/[symbol]/page.tsx`만 존재). 하단 네비 "종목" 탭 → 404 추정.
- (코멘트 `#12`가 `/profile`→`/mypage`는 고친 흔적이나 `/stocks`는 누락.)

### 🟠 MAJOR

**5. 모바일 네비 기능 커버리지 공백** — `MobileNav.tsx:11-17` + `Header.tsx:42,155-163`
- `Header`의 데스크톱 nav는 `hidden md:flex`, 햄버거 버튼은 `className="hidden ..."` 로 **영구 비표시**(주석 `#12`: MobileNav를 단일 소스로 의도). 따라서 모바일에서 상단 nav·햄버거 모두 작동 안 함.
- 그런데 `MobileNav` 하단 바는 **5개 항목(홈/종목/뉴스/포트폴리오/내정보)** 뿐.
- **결과**: **Chain Sight, Thesis Control, Market Pulse, Screener** 4개 주요 기능이 모바일에서 **진입 동선이 전무**(직접 URL 입력 외 도달 불가). 데스크톱 Header에는 7개 메뉴가 있어 기능 격차 발생.
- **권장**: 하단 바에 "더보기" 항목 추가(시트로 잔여 메뉴 노출) 또는 `Header` 모바일 메뉴 재활성화.

**6. iOS safe-area-inset 미적용** — `MobileNav.tsx:20`
- 루트는 `viewportFit: "cover"`(노치/홈 인디케이터 영역까지 확장)인데 `MobileNav`의 `fixed bottom-0`에 `env(safe-area-inset-bottom)` 패딩이 없음. `globals.css`에도 safe-area 처리 없음.
- **영향**: iPhone(홈 인디케이터 기종)에서 하단 네비 항목이 홈 바와 겹쳐 탭 정확도 저하.
- **권장**: `pb-[env(safe-area-inset-bottom)]` 또는 `viewport-fit` 대응 유틸 추가.

**7. 종목 상세 탭바 가로 오버플로** — `frontend/app/stocks/[symbol]/page.tsx:383,403`
```tsx
<nav className="flex space-x-2">      {/* L1: 기본정보/뉴스/분석 및 검증 (3개) */}
<nav className="flex space-x-6">      {/* L2: Overview/Balance Sheet/Income Statement/Cash Flow/기타 펀더멘탈 (5개) */}
```
- 두 탭바 모두 `overflow-x-auto`·`flex-wrap` 없음. L2의 영문 5개 탭(`Balance Sheet`/`Income Statement` 등)은 375px에서 가로폭 초과 → 마지막 탭 화면 밖으로 잘림(스크롤 불가).
- **권장**: 탭 `<nav>`에 `overflow-x-auto whitespace-nowrap` 적용.

### ✅ 양호
- 하단 탭 active 상태 `usePathname` 기반 정확. `aria-label` 부여됨.
- 긴 목록 **virtualization 부재**: Screener는 클라이언트 페이지네이션(`pageSize` 50)으로 1회 렌더 항목 제한 → 가상화 필요성 낮음. 단, 대형 목록 페이지에서 향후 고려.

---

## 차트/그래프

### ✅ 대체로 양호
- **Recharts `ResponsiveContainer`**: 14개 파일에서 `width="100%"`로 사용 (StockPriceChart, PortfolioChart, YieldCurveChart, SentimentChart, MetricBarChart, IndicatorRow, IndividualMiniCharts, market-pulse-v2 상세 4종 등). 컨테이너 폭 추종으로 모바일 폭 적응.
- **IndicatorRow 차트**(`dashboard/IndicatorRow.tsx:197,235`): `ResponsiveContainer width="100%" height={140~160}`, 축 폰트 `fontSize 9~10`, 장기 데이터 샘플링(`sampleInterval`) + X축 `interval` 동적 thinning → 모바일 라벨 겹침 완화. 양호.
- **QuarterlySparkline**(`dashboard/QuarterlySparkline.tsx`): 막대 `min-h-[44px]` 터치 타겟 + `onTouchStart` 툴팁 지원. 인라인은 최근 4분기만(`IndicatorRow.tsx:132` `max-w-[100px]`)으로 폭 제한 → 가독성 확보. 양호.

### 🟡 MINOR
- **Chain Sight 그래프 고정 높이**(`MarketGraphCanvas.tsx:712,760` `h-[560px]`): 모바일에서 화면 대비 과도하게 높아 1스크롤 점유. 노드 라벨/툴팁 텍스트(`text-[10px]`)는 작은 화면에서 판독 난도 높음. (위 MAJOR #4와 연계 — 메인 `/chainsight`에는 `MobileCardList` 폴백이 연결돼 있지 않음. `MobileCardList`는 `chainsight/[symbol]` 상세에만 사용.)
- 스파크라인/차트 축 폰트 9~10px는 핀치 줌이 막혀 있어(BLOCKER #1) 확대 보정 불가 — 줌 차단 해제 시 자연 완화.

---

## 페이지별 상세

| 페이지 | 반응형 | 터치 | 네비 | 차트 | 주요 이슈 |
|--------|:------:|:----:|:----:|:----:|----------|
| `app/layout.tsx` (전역) | 🔴 | — | 🟠 | — | 줌 차단(BLOCKER#1), `<main>` 하단 패딩 부재(MAJOR#2), safe-area 미적용(MAJOR#6) |
| `/` (home) | ✅ | ✅ | ✅ | ✅ | `pb-20 md:pb-0` 적용된 모범 사례 |
| `/stocks/[symbol]` | 🟠 | ✅ | 🟠 | ✅ | L1/L2 탭바 가로 오버플로(MAJOR#7), 재무표는 `overflow-x-auto` 양호 |
| `/screener` | ✅ | 🟡 | — | ✅ | 테이블↔카드 반응형 전환(`hidden sm:block`/`sm:hidden`+MobileStockCard) **모범**. 컨트롤 버튼·필터 X 소형(MINOR) |
| `/chainsight` | 🟠 | 🟠 | — | 🟡 | 그래프 노드 터치 미달 + 모바일 카드 폴백 미연결(MAJOR#4), `h-[560px]` 과점유 |
| `/chainsight/[symbol]` | ✅ | — | — | — | `MobileCardList` 폴백 사용(양호) |
| `/thesis/*` | ✅ | 🟡 | 🟠 | ✅ | `pb-*` 적용됨. IndicatorRow 기간 토글 소형(MINOR). 하단 바 진입 동선 없음(MAJOR#5) |
| `/portfolio` | 🟠 | — | — | ✅ | 하단 패딩 부재(MAJOR#2), PortfolioTable `overflow-x-auto` 양호 |
| `/watchlist` | 🟠 | — | — | — | 하단 패딩 부재(MAJOR#2) |
| `/news` | 🟠 | — | — | ✅ | 하단 패딩 부재(MAJOR#2) |
| `/validation` (stocks 내 탭) | ✅ | 🟡 | — | ✅ | PeerContextBar 프리셋 탭 `min-h-[44px]` 양호, 커스텀 "적용" 버튼 소형(MINOR) |
| `/admin/*` | ⬜ | ⬜ | ⬜ | — | 데스크톱 전용 도구, 모바일 우선순위 낮음(다수 admin 테이블은 `overflow-x-auto` 보유) |

### 🟡 추가 MINOR — 정리 권장 (dead code)
- **`frontend/components/layout/InvestingHeader.tsx`**: 어디서도 import되지 않는 미사용 컴포넌트(`max-w-[1400px]` 3회). 혼선 방지 위해 제거 검토.
- **`frontend/components/layout/Header.tsx:157-257`**: 햄버거 버튼이 `hidden`으로 영구 비표시 → `isMenuOpen`이 true가 될 경로 없음 → 모바일 드롭다운 메뉴(101줄) 전체가 **도달 불가능한 dead code**. MAJOR#5 해결 시 이 메뉴를 재활용할지, 삭제할지 결정 필요.

---

## 우선 조치 권고 (영향/비용 순)

1. **(BLOCKER#1, 1줄)** `layout.tsx` viewport에서 `maximumScale`/`userScalable` 제거 → 줌 복원.
2. **(MAJOR#2, 1줄)** `layout.tsx` `<main>`에 `pb-16 md:pb-0` 추가 → 전 페이지 하단 가림 동시 해소.
3. **(BLOCKER#4)** `/stocks` 인덱스 페이지 추가 또는 하단 네비 링크를 실제 존재 라우트로 교체.
4. **(MAJOR#7, 1줄×2)** 종목 상세 L1/L2 `<nav>`에 `overflow-x-auto whitespace-nowrap`.
5. **(MAJOR#6)** `MobileNav`에 `pb-[env(safe-area-inset-bottom)]`.
6. **(MAJOR#5)** 하단 바 "더보기" 시트로 Chain Sight/Thesis/Market Pulse/Screener 노출 (또는 Header 모바일 메뉴 재활성화).
7. **(MAJOR#4 / MINOR)** Chain Sight 노드 hit 영역 확대 + 메인 그래프 모바일 카드 폴백 연결, 소형 토글 버튼 터치 타겟 보강.

> 코드는 수정하지 않았습니다. 본 보고서는 정적 분석 기반 추정이며, 실제 잘림/가림은 실기기(375px) 렌더링으로 최종 확인 권장.
