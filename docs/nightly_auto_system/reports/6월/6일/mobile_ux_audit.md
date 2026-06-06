# 모바일 UX 감사 보고서

> **작성일**: 2026-06-06 · **모드**: 읽기 전용 (코드 수정 없음)
> **기준 뷰포트**: 375px (iPhone SE/표준 모바일) · **터치 기준**: Apple HIG 44×44pt
> **스캔 범위**: `frontend/components/*.tsx` 205개 + `frontend/app/**/*.tsx` 50개

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 내용 |
|--------|------|-----------|
| 🔴 BLOCKER | **1** | viewport `userScalable: false` — 확대 차단(WCAG 1.4.4 위반) |
| 🟠 MAJOR | **6** | 터치 타겟 미달(필터 칩/차트 셀렉터), 데이터 테이블 모바일 카드 미분기, 작은 클릭 텍스트 |
| 🟡 MINOR | **7** | dead-code 헤더, virtualization 미적용, 차트 height 고정, 노드 라벨 폰트 등 |

### 종합 평가

전반적으로 **모바일 대응 성숙도가 높은 편**이다. Bottom Navigation(`MobileNav`), 모바일 전용 카드 분기(`MobileStockCard`), 모바일 퍼스트 레이아웃(Thesis `max-w-lg`), 그래프 캔버스의 모바일 탭/롱프레스/페이드아웃 등 이미 상당한 작업이 되어 있다. 코드 곳곳에 `audit P0 #12/#13` 주석이 있어 **이전 모바일 감사 후속 조치 이력**이 확인된다.

남은 이슈는 대부분 **터치 타겟 크기 미달**(32px 이하 칩/버튼)과 **데이터 테이블의 가로 스크롤 의존**, 그리고 **viewport 확대 차단(접근성)** 에 집중되어 있다.

---

## 반응형 누락

### 🔴 BLOCKER

**B-1. 뷰포트 확대 차단 (`app/layout.tsx:29-35`)**
```ts
viewport: {
  width: "device-width", initialScale: 1,
  maximumScale: 1, userScalable: false,   // ← 사용자 핀치 줌 차단
  viewportFit: "cover",
}
```
- 본 보고서에서 다수 발견된 `text-[10px]`/`text-[11px]` 소형 텍스트를 사용자가 **확대조차 할 수 없음**.
- WCAG 2.1 SC 1.4.4(Resize Text) / 1.4.10(Reflow) 위반. iOS Safari는 `userScalable=false`를 부분 무시하지만 Android Chrome은 엄격 적용.
- **영향 범위**: 전 페이지(루트 레이아웃).

### 🟠 MAJOR

**M-1. 데이터 테이블 모바일 카드 미분기 — `PortfolioTable`, `StockTable`**
- `components/portfolio/PortfolioTable.tsx:259` → `overflow-x-auto` + `min-w-full` 만으로 처리.
- `components/stocks/StockTable.tsx:34` → 동일.
- 다열(多列) 재무 테이블이 375px에서 **가로 스크롤로만** 노출. Screener가 `MobileStockCard`로 카드 분기한 것과 대조적(아래 참조).
- **대조군(양호)**: `app/screener/page.tsx:845-857` — `viewMode === 'table'`은 `hidden sm:block`, 모바일은 `MobileStockCard` 그리드로 자동 전환. ✅

**M-2. `ScreenerTable` 11열 가로 스크롤 (`components/strategy/ScreenerTable.tsx:128`)**
- `overflow-x-auto` 래퍼 존재(가로 스크롤 처리됨 ✅)하나, 11개 컬럼(종목/거래소/섹터/가격/변동률/시총/거래량/배당/베타/유형/키워드)을 모바일에서 모두 가로 스크롤해야 함.
- Screener 페이지 본체는 카드 분기가 있으나, 이 컴포넌트가 단독 사용되는 경로에서는 가로 스크롤 의존.

### 🟡 MINOR

**m-1. `InvestingHeader` 완전 데스크톱 전용 (dead code)**
- `components/layout/InvestingHeader.tsx` — `max-w-[1400px]`, 8개 가로 nav, top-bar 지수 정보 가로 나열. 브레이크포인트 **0개**. 375px에서 전면 overflow.
- **단, 어디에서도 import되지 않는 미사용 컴포넌트**(grep 확인). 하드코딩된 `"2025년 10월 25일"`, mock 지수 데이터 포함 → 레거시/실험 잔재. 실사용 영향 없음. **삭제 후보**.

**m-2. 고정 폭 `min-w-[NNpx]` 사용 (23개 파일, 31건)**
- 대부분 소형(`min-w-[18px]` 배지, `min-w-[60px]`/`min-w-[120px]` 값 정렬칸 등)으로 375px 내 수용 가능 → overflow 위험 낮음.
- 점검 결과 화면 폭을 강제로 넘기는 `w-[400px]`급 하드 고정은 발견되지 않음. `InvestingHeader`(m-1)의 `max-w-[1400px]`가 유일한 대형 고정폭.

---

## 터치 타겟

> Apple HIG 권장 44×44pt. 아래는 **클릭 가능 요소**의 실측 높이 기준.

### 🟠 MAJOR

**M-3. Chain Sight 관계 필터 칩 — 높이 32px (`components/chainsight/RelationFilterChips.tsx:148`)**
```
'inline-flex items-center gap-1.5 h-8 px-3 py-0'   // h-8 = 32px < 44pt
```
- 6종 관계 토글 칩 모두 `h-8`(32px). 모바일에서 핵심 인터랙션인데 12px 미달.
- "전체 켜기/전체 끄기" 버튼(`:245`,`:256`)은 `px-2 py-1` → 약 **24px**, 더 심각.
- 가로 스크롤 + 우측 페이드아웃(`:218-226`)은 잘 구현됨 ✅.

**M-4. EOD 시그널 필터 탭 — 높이 ~30px (`components/eod/SignalFilterTabs.tsx:44-48`)**
```
'... px-3 py-1.5 rounded-full text-sm ...'   // py-1.5 + text-sm ≈ 30px
```
- 메인 페이지/EOD 대시보드의 1차 필터. `overflow-x-auto scrollbar-hide`로 가로 스크롤은 처리됨 ✅이나 높이 미달.

**M-5. 작은 폰트 클릭 요소 (`text-[10px]`/`text-[11px]`) 광범위 분포**
- `text-[10px]`/`text-[11px]`가 **57개 파일 127건**, 그중 클릭/링크 요소를 포함한 파일 **30개**.
- 대표 사례:
  - `IndicatorRow.tsx:182` — 일간 차트 기간 셀렉터 `text-[10px]` + `py-0.5` (≈18px) 버튼 4종(1M/1Y/3Y/5Y).
  - `chainsight/ExplorationTrail.tsx`, `TracePathView.tsx`, `FullPathView.tsx` — 경로 탐색 칩/링크가 `text-[10px]~[11px]`.
  - `thesis/builder/OptionButton.tsx`, `NewsSelector.tsx` — 빌더 선택 버튼.
- B-1(확대 차단)과 결합 시 가독성·정확도 이중 타격.

### 🟡 MINOR

**m-3. Chain Sight 그래프 노드 터치 영역 (`MarketGraphCanvas.tsx:787-793`, `853-856`)**
- `nodePointerAreaPaint`가 노드 반경만큼만 터치 영역 지정. `sm` 노드는 반경 10px → **직경 20px**(44pt의 절반).
- 라벨 폰트 `r > 14 ? 11 : r > 10 ? 9 : 7px`(`:924`) — 작은 노드는 7px로 모바일 가독성 매우 낮음.
- 단, 모바일 탭 핸들링(첫 탭=툴팁, 둘째 탭=center 전환, `:481-517`)·롱프레스가 별도 구현되어 **상호작용 자체는 가능**.

### ✅ 양호 사례

- `MobileNav.tsx:34` — `min-h-[44px]` 명시, `h-16`(64px) 컨테이너. 주석에 HIG 근거(`audit P0 #13`). ✅
- `PeerContextBar.tsx:40,54` — validation 프리셋 탭 `min-h-[44px]` 보장. ✅
- `ScreenerTable.tsx:323` — 바구니 버튼 `min-h-[44px] min-w-[44px]`. ✅
- `Header.tsx:160` — 햄버거 버튼 `min-h-[44px] min-w-[44px]`(현재 `hidden` 처리). ✅

---

## 네비게이션

### ✅ 양호 (핵심 네비게이션 정상)

**Bottom Navigation 존재 — `components/layout/MobileNav.tsx`**
- `fixed bottom-0 ... md:hidden z-50`, 5개 탭(홈/종목/뉴스/포트폴리오/내정보).
- 각 항목 `min-h-[44px]`, `aria-label` 부여. 활성 상태 표시 로직 정상.
- 주석 `audit P0 #12`: 깨진 `/profile` → `/mypage` 교정 이력. ✅

**Header 이중 네비 제거 — `components/layout/Header.tsx`**
- 데스크톱 nav는 `hidden md:flex`(`:42`). 모바일 햄버거는 `hidden`(`:157-160`)으로 의도적 비활성화 — `MobileNav`를 모바일 단일 소스로 통일(`audit P0 #12` 주석). ✅
- 두 헤더가 `app/layout.tsx`에서 `Header` + `MobileNav` 조합으로 실사용 확인. ✅

### 🟡 MINOR

**m-4. 모바일 종목 검색 동선 부재**
- `Header.tsx`의 검색바는 `hidden md:block`(`:112`). 모바일 햄버거가 비활성(`hidden`)이라 **모바일에서 종목 검색 진입점이 헤더에 없음**.
- `MobileNav`에도 검색 탭 없음(홈/종목/뉴스/포트폴리오/내정보). 모바일 사용자는 `/stocks` 목록을 거쳐야 함.
- 참고: `Header`의 검색은 `handleSearch`가 `console.log`만 수행(`:18-20`) — 검색 기능 자체가 미구현 상태(별도 이슈).

**m-5. 긴 목록 virtualization 전무**
- `react-window`/`@tanstack/react-virtual` 등 가상화 라이브러리 **미사용**(grep 0건).
- Screener는 `Pagination`으로, EOD는 14개 시그널 고정으로 완화되어 실질 위험은 낮으나, 종목 전체 목록/뉴스 무한 스크롤 확장 시 모바일 스크롤 성능 저하 우려.

---

## 차트/그래프

### ✅ 양호 (ResponsiveContainer 커버리지 우수)

- recharts 사용 컴포넌트 **14개** 중 거의 전부가 `ResponsiveContainer`(`width="100%"`)로 가로 반응형 처리.
  - `IndicatorRow.tsx:197,235`, `StockChart`, `StockPriceChart`, `PortfolioChart`, `SentimentChart`, `YieldCurveChart`, `MetricBarChart`, `MLTrendChart`, `SectorHeatmap`, market-pulse-v2 디테일 4종, `IndividualMiniCharts`.
- `MarketGraphCanvas`는 `ResizeObserver`로 컨테이너 폭 추적(`:150-161`) → ForceGraph `width={containerWidth}` 동적 반영. ✅

### 🟡 MINOR

**m-6. 차트 height 고정값 — 모바일 세로 점유 과다**
- `MarketGraphCanvas`: `h-[560px]`(`:760`) 고정. 375×667 화면에서 캔버스가 세로 84% 점유. 동작엔 문제없으나 모바일 컨텍스트 손실.
- `IndicatorRow`: 차트 `height={160}`/`140`(`:197,235`) — 모바일에서 적정 범위.

**m-7. 분기 스파크라인 모바일 가독성 (`IndicatorRow.tsx:131-138`, `QuarterlySparkline.tsx`)**
- 인라인 스파크라인이 `flex-1 max-w-[100px]` 안에 4분기 압축. 폭 100px·축 없음 → 추세 방향만 식별 가능(상세는 펼침 차트로 보완되므로 설계 의도 부합).
- 펼침 시 분기 차트 X축 폰트 `fontSize={9}`(`:248`) — 모바일에서 작으나 `interval` 샘플링으로 라벨 겹침은 방지됨.

---

## 페이지별 상세

| 페이지 / 영역 | 모바일 대응 | 주요 이슈 | 심각도 |
|---------------|------------|-----------|--------|
| **전역 (`app/layout.tsx`)** | Header + Bottom Nav 조합 | viewport 확대 차단(B-1) | 🔴 |
| **Screener (`/screener`)** | ✅ 테이블/카드 자동 분기, `hidden sm:block` | `ScreenerTable` 단독 11열 가로 스크롤(M-2) | 🟠/✅ |
| **Portfolio (`/portfolio`)** | ⚠️ 테이블 가로 스크롤만 | 모바일 카드 미분기(M-1) | 🟠 |
| **Stocks 목록 (`StockTable`)** | ⚠️ 테이블 가로 스크롤만 | 모바일 카드 미분기(M-1) | 🟠 |
| **Stocks 상세 (`/stocks/[symbol]`)** | 부분 반응형(sm/md 7건) + 차트 ResponsiveContainer | 다열 재무 테이블 가로 스크롤 | 🟡 |
| **Thesis 관제실 (`/thesis/[id]`)** | ✅ **모바일 퍼스트** `max-w-lg mx-auto` | 차트 기간 셀렉터 `text-[10px]` 버튼(M-5) | ✅/🟠 |
| **Thesis 지표 행 (`IndicatorRow`)** | ✅ 세로 카드 + 토글 차트 | 기간 셀렉터 18px·`text-[11px]` 다수 | 🟠 |
| **Validation (`PeerContextBar`)** | ✅ 프리셋 탭 `min-h-[44px]`, flex-wrap | custom 입력 안내 `text-[10px]`(비클릭) | ✅ |
| **Chain Sight 그래프 (`MarketGraphCanvas`)** | ✅ ResizeObserver + 모바일 탭/롱프레스 | 노드 터치 20px·라벨 7px(m-3), 필터 칩 32px(M-3) | 🟠 |
| **Chain Sight 필터 (`RelationFilterChips`)** | ✅ 가로 스크롤 + 페이드아웃 | 칩 32px / 전체토글 24px(M-3) | 🟠 |
| **EOD/메인 (`SignalFilterTabs`)** | ✅ 가로 스크롤 | 탭 높이 ~30px(M-4) | 🟠 |
| **Header 검색** | ❌ 모바일 진입점 없음 | 검색 동선 부재(m-4) + 기능 미구현 | 🟡 |
| **InvestingHeader** | ❌ 데스크톱 전용 | 미사용 dead code(m-1) | 🟡 |

---

## 권고 우선순위 (수정은 별도 작업 — 본 보고서는 식별만)

1. **B-1** viewport `maximumScale`/`userScalable` 완화 → 접근성 즉시 개선, 단일 파일 1줄.
2. **M-3/M-4** 필터 칩·탭 높이 `h-8`→`min-h-[44px]` 계열로 상향 (Chain Sight·EOD 핵심 인터랙션).
3. **M-1** `PortfolioTable`/`StockTable`에 Screener식 모바일 카드 분기 도입.
4. **M-5** 차트 기간 셀렉터 등 핵심 클릭 요소 `text-[10px]` → 최소 `text-xs`(12px) + 패딩 확대.
5. **m-1** `InvestingHeader` dead code 제거(레거시 정리).

> 본 감사는 정적 코드 분석 기준이며, 실제 디바이스 렌더링 측정(브라우저 375px 뷰포트)으로 교차 검증을 권장한다.
