# 모바일 UX 감사 보고서

> **감사일**: 2026-05-31
> **대상**: `frontend/` (컴포넌트 205개, 페이지 30개)
> **기준 뷰포트**: 375px (iPhone SE/12 mini), Apple HIG 터치 타겟 44×44pt
> **범위**: 읽기 전용 정적 분석 (Tailwind 클래스 + 컴포넌트 구조 기반). 실기기 렌더링 검증 아님.
> **모드**: 코드 미수정, 감사 전용

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 내용 |
|--------|------|----------|
| **BLOCKER** | 1 | 전역 Bottom Nav(64px)가 다수 페이지 하단 콘텐츠를 가림 (페이지별 `pb` 누락) |
| **MAJOR** | 4 | thesis 관제실 지표 행 고정폭 합산 / 기간 셀렉터 터치타겟 미달 / validation 카테고리 탭 높이 미달 / 작은 클릭 칩 다수 |
| **MINOR** | 5 | 스파크라인 가독성 / admin 테이블 데스크톱 편중 / 작은 라벨 텍스트 / chainsight 칩 등 |

### 양호 항목 (Positive Findings)
잘 처리된 부분도 함께 기록한다. 회귀 방지 기준선으로 활용.

- ✅ **Bottom Navigation 존재**: `MobileNav.tsx` — `md:hidden fixed bottom-0`, 각 항목 `min-h-[44px]`, `aria-label` 부여, 깨진 라우트(`/profile`) 이미 `/mypage`로 교정됨.
- ✅ **chainsight 모바일 분기**: `chainsight/[symbol]/page.tsx`가 `isMobile` 상태로 그래프 캔버스 대신 `MobileCardList` + 전체화면 그래프 오버레이로 전환 — 모바일 전용 UX 구현됨.
- ✅ **Recharts 전수 ResponsiveContainer 적용**: recharts를 import하는 14개 파일 **전부** `ResponsiveContainer` 사용. 고정폭 차트 0건.
- ✅ **테이블 전수 가로 스크롤 래핑**: 모든 `<table>`이 `overflow-x-auto` div로 감싸져 있음 (admin, portfolio, validation, stocks, strategy).
- ✅ **thesis 모바일 우선 레이아웃**: thesis 페이지는 `max-w-lg mx-auto px-4 pb-20` — 의도적 모바일 폭 고정 + bottom nav 회피. (브레이크포인트 0개는 "누락"이 아니라 모바일 우선 설계)
- ✅ **터치 타겟 명시 확보 사례**: `Pagination`(`min-w-[44px] min-h-[44px]`), `SignalSummaryCard`(`min-h-[44px]`), `ScreenerTable` 액션 버튼(`min-h-[44px] min-w-[44px]`), `MobileCardList` 액션 버튼(`min-h-[44px]`).
- ✅ **Header 햄버거 의도적 비표시**: 이중 네비 제거 목적으로 `hidden` 처리 + 주석 명시. MobileNav 단일 소스 원칙 일관됨.

---

## 1. 반응형 누락

### 1-1. [BLOCKER] Bottom Nav가 페이지 하단 콘텐츠를 가림 — 전역 구조 문제

루트 레이아웃이 Bottom Nav 높이만큼의 하단 여백을 보장하지 않는다.

- `frontend/app/layout.tsx:60` — `<main className="min-h-screen">` (하단 패딩 **없음**)
- `frontend/components/layout/MobileNav.tsx:20` — `fixed bottom-0 ... h-16`(64px) `z-50`

`<main>`에 전역 `pb-16 md:pb-0`이 없으므로, **각 페이지가 개별적으로** 하단 여백을 책임지는 구조다. 실제 페이지별 하단 패딩 점검 결과:

| 페이지 | 하단 패딩 | 모바일에서 하단 가림 |
|--------|----------|---------------------|
| `dashboard/page.tsx` | 없음 | **64px 가림** ❌ |
| `portfolio/page.tsx` | 없음 | **64px 가림** ❌ |
| `mypage/page.tsx` | 없음 | **64px 가림** ❌ |
| `watchlist/page.tsx` | 없음 | **64px 가림** ❌ |
| `news/page.tsx` | `pb-3`(12px) | **52px 가림** ❌ |
| `screener/page.tsx` | `pb-3`(12px) | **52px 가림** ❌ |
| `thesis/[thesisId]/page.tsx` | `pb-20`(80px) | OK ✅ |
| `app/page.tsx`(홈) | `pb-20` 일부 / `pb-0` 혼재 | 부분 OK ⚠️ |

**영향**: 페이지 최하단의 버튼·링크·마지막 카드가 Bottom Nav에 가려 **접근 불가**하거나 클릭 충돌. 목록형 페이지(portfolio, watchlist)에서 마지막 항목 조작 불가 가능성.

**근본 원인**: 하단 여백이 페이지별 개별 처리 → 신규 페이지마다 누락 재발 구조. 전역 `<main>` 레벨 일괄 처리가 없음.

---

### 1-2. [MINOR] 페이지 레벨 브레이크포인트 0개 페이지군

`sm:/md:/lg:` 사용 횟수가 0인 페이지 (페이지 파일 기준):

```
0  admin/page.tsx
0  chainsight/page.tsx, chainsight/watchlist/*
0  thesis/(list)/*, thesis/[thesisId]/*
0  coach/e4/page.tsx
```

단, 0개라고 모두 문제는 아니다. 분류:

- **thesis 계열**: `max-w-lg`(512px) 모바일 우선 고정 폭 — **의도된 설계, 문제 없음**. 다만 데스크톱에서는 좌우 여백이 과도하게 넓게 보임(태블릿/PC 사용자 화면 활용도 낮음, MINOR).
- **chainsight 계열**: 페이지 클래스 대신 **`isMobile` JS 분기**로 처리 — Tailwind 브레이크포인트가 없는 게 정상.
- **admin 계열**: 테이블 위주 + `overflow-x-auto` 래핑은 있으나, 데스크톱 전용 성격(아래 4-2 참조).

### 1-3. 고정 폭(`w-[NNpx]`, `min-w-[NNpx]`) 사용처 분석

`max-w-[NNpx] truncate` 조합(대부분)은 **안전**하다 — 최대폭 제한 + 말줄임이라 375px에서 오버플로하지 않는다. 위험한 것은 **`min-w-` 합산**과 **고정 `w-`**다.

| 컴포넌트:라인 | 클래스 | 375px 위험도 |
|--------------|--------|-------------|
| `thesis/dashboard/IndicatorRow.tsx:110,115,132` | `min-w-[60px]` + `min-w-[120px]` + `max-w-[100px]` 한 행 합산 | **MAJOR** (아래 2-1) |
| `chainsight/MarketGraphCanvas.tsx:676` | `w-[110px] min-h-[68px]` 노드 카드 | 캔버스 내부, 스크롤/줌 처리 시 양호 |
| `eod/SignalDetailSheet.tsx:97` | `w-full md:w-[420px]` | ✅ 모바일 `w-full`, 데스크톱만 고정 — 정상 |
| `layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px] mx-auto` | ✅ 컨테이너 최대폭, 안전 |
| `common/DataSourceBadge.tsx:171` | `min-w-[200px]` 툴팁 | 375px에서 화면폭의 53%, 위치에 따라 우측 오버플로 가능 (MINOR) |
| 다수 `max-w-[NNpx] truncate` | RelationLegend, NodeTooltip, SectorBar, StockRow, RecommendationCard 등 | ✅ truncate 동반, 안전 |

---

## 2. 터치 타겟 (Apple HIG 44×44pt 기준)

### 2-1. [MAJOR] thesis 관제실 지표 행 — 고정폭 합산으로 375px 압박

`thesis/dashboard/IndicatorRow.tsx:108-143` 2행 레이아웃:

```
값(min-w-[60px]) + 변동률(min-w-[120px]) + 스파크라인(max-w-[100px]) + 지지/반박(ml-auto)
```

`gap-3`(12px×3) + `pl-4`(16px) 포함 시 최소 폭 합계 ≈ **60+120+100+44(gap/pad) ≈ 324px**. 375px 화면에서 좌우 컨테이너 패딩(`max-w-lg px-4` = 좌우 16px씩 → 가용 343px)을 빼면 **여유 ~19px**. 종목명이 긴 지표나 `ml-auto`로 밀리는 지지/반박 라벨에서 **줄바꿈 깨짐 또는 가로 압축** 발생 가능. (관제실은 모바일 핵심 화면이므로 MAJOR)

### 2-2. [MAJOR] thesis 차트 기간 셀렉터 버튼 — 터치 타겟 미달

`thesis/dashboard/IndicatorRow.tsx:182` — `1M/1Y/3Y/5Y` 기간 버튼:

```
px-2.5 py-0.5 text-[10px]   →  실측 약 32×20px (44×44 대비 좌우 73%, 상하 45%)
```

지표 카드의 핵심 인터랙션(차트 기간 전환)인데 손가락 터치 영역이 절반 이하. 인접 버튼 간 오터치 위험.

### 2-3. [MAJOR] validation 카테고리 탭 — 높이 미달

`validation/CategorySidebar.tsx:48-60` — 카테고리 전환 버튼:

```
w-full ... px-3 py-2 ... text-sm   →  높이 약 36px (py-2=8px×2 + text-sm 라인 ~20px)
```

폭은 `w-full`이라 충분하나 **높이 36px로 44px 미달**. 프리셋/카테고리 전환은 검증 화면의 주 내비게이션이므로 상향 권장. (데스크톱 사이드바 형태가 모바일에서 어떻게 적층/가로전환되는지는 실기기 확인 필요)

### 2-4. [MINOR] 작은 클릭 가능 칩/토글 (`text-[10px]`/`text-[11px]`)

클릭 핸들러를 가진 작은 텍스트 요소들. 대부분 보조 액션이라 MINOR로 분류하나 누적 시 사용성 저하:

| 컴포넌트:라인 | 요소 | 비고 |
|--------------|------|------|
| `screener/PresetGallery.tsx:241` | `flex ... text-[10px] transition-colors` 비교 토글 | 클릭 요소, 패딩 부족 |
| `chainsight/RelationLegend.tsx:59` | `text-[10px]` 범례 토글 버튼 | `w-full`이라 폭은 확보 |
| `chainsight/RelationFilterChips.tsx:229` | `overflow-x-auto` 가로 칩 스크롤 | 칩 패딩 확인 필요 |
| `eod/SignalDetailSheet.tsx:188,197` | `text-[10px]` 관련 종목/링크 칩 | 시트 내 보조 액션 |
| `eod/SignalFilterTabs.tsx:68` | `text-[11px] min-w-[18px] h-[18px]` 카운트 배지 | 배지(비클릭)면 무관 |

> **참고**: `text-[10px]` 사용처 총 ~40건 중 다수는 라벨·배지·단위 표기(비클릭)로 터치 타겟 무관. 위 표는 클릭 핸들러 동반 요소만 추렸다.

---

## 3. 모바일 네비게이션

### 3-1. [양호] Bottom Navigation 구현됨
`MobileNav.tsx` — 5개 탭(홈/종목/뉴스/포트폴리오/내정보), `md:hidden`, 각 탭 `min-h-[44px]` + `aria-label`. 활성 상태 표시 로직 포함. **모바일 1차 내비게이션 적절히 구현.**

### 3-2. [양호] 헤더 햄버거 의도적 비표시
`Header.tsx:160` 햄버거 버튼에 `hidden` 클래스 — 주석에 "MobileNav가 모바일 네비 단일 소스, 이중 네비 제거" 명시. 단일 소스 원칙 일관. (단 `Header.tsx:166`의 `isMenuOpen` 모바일 드롭다운은 토글 버튼이 죽어 있어 **도달 불가능한 데드 코드** — 정리 대상, MINOR)

### 3-3. [MINOR] 긴 목록 가상화(virtualization) 미적용
`react-window`/`@tanstack/react-virtual`/`virtua` 등 가상화 라이브러리 **앱 코드 사용 0건**. portfolio·watchlist·screener·news 목록이 길어질 경우 모바일에서 DOM 노드 과다로 스크롤 버벅임 가능. 현재 데이터 규모에서는 즉각 문제 아니므로 MINOR. (단 1-1 BLOCKER로 인해 목록 하단 접근성 문제가 우선)

### 3-4. [MINOR] 두 개의 헤더 컴포넌트 공존
`Header.tsx`(루트 layout 사용)와 `InvestingHeader.tsx`(별도)가 공존. InvestingHeader가 어느 페이지에서 쓰이는지/모바일 대응 여부는 라우팅 확인 필요. 중복 유지보수 리스크.

---

## 4. 차트/그래프 모바일 대응

### 4-1. [양호] ResponsiveContainer 전수 적용
recharts import 14개 파일 전부 `ResponsiveContainer` 사용 (`width="100%"`). 차트 자체는 컨테이너 폭에 맞춰 축소됨. 누락 0건.

- market-pulse-v2 상세 차트 5종, `SectorHeatmap`(Treemap height=400), `MLTrendChart`, `StockPriceChart`(height 가변), `IndicatorRow` area chart 등.

### 4-2. [MINOR] 분기 스파크라인 모바일 가독성
`thesis/dashboard/QuarterlySparkline.tsx:33` — `flex items-end gap-1 h-10`(div bar 방식, recharts 아님), 부모 컨테이너 `IndicatorRow.tsx:132`에서 `max-w-[100px]`. 최근 4분기를 100px 폭에 막대로 표현 → 막대당 ~22px. 모바일에서 추세 식별은 가능하나 값 비교는 어려움. 펼침(expanded) 시 풀 차트가 나오므로 치명적이지 않음 (MINOR).

### 4-3. [확인 필요] chainsight 그래프 캔버스 높이
`chainsight/[symbol]/page.tsx:154,190` — `h-screen` + `window.innerHeight - 48`. 모바일에서 `h-screen`(100vh)은 iOS Safari 주소창 동적 높이 문제(`100vh` ≠ 실제 가시 영역)로 하단 잘림 가능. `100dvh` 사용 검토 권장. 단 모바일은 별도 오버레이 분기라 영향 제한적 (MINOR~확인필요).

---

## 5. 페이지별 상세

| 페이지 | 반응형 | 터치 타겟 | 네비/하단가림 | 차트 | 종합 |
|--------|--------|-----------|--------------|------|------|
| `dashboard` | 브레이크포인트 1 | — | **하단 64px 가림 (BLOCKER)** | — | ⚠️ |
| `portfolio` | — | 테이블 `overflow-x-auto` ✅ | **하단 가림 (BLOCKER)**, 목록 길면 마지막 행 가림 | — | ❌ |
| `watchlist` | — | 테이블 래핑 ✅ | **하단 가림 (BLOCKER)** | — | ❌ |
| `mypage` | 1 | — | **하단 가림 (BLOCKER)** | — | ⚠️ |
| `news` | — | 가로 칩 스크롤 ✅ | 하단 `pb-3`만 → 52px 가림 | — | ⚠️ |
| `screener` | — | `MobileStockCard` 분기 존재, Pagination 44 ✅ | 하단 `pb-3`만 → 52px 가림 | SectorHeatmap Responsive ✅ | ⚠️ |
| `thesis/[id]` (관제실) | 모바일 우선 `max-w-lg` ✅ | **지표 행 고정폭 압박 + 기간버튼 미달 (MAJOR×2)** | `pb-20` ✅ | IndicatorRow Responsive ✅ / 스파크라인 좁음 | ⚠️ |
| `thesis` 목록/알림/마감 | 모바일 우선 ✅ | — | `pb-20` ✅ | — | ✅ |
| `chainsight/[symbol]` | **`isMobile` 분기 ✅** | MobileCardList 버튼 44 ✅ | 오버레이 처리 | 그래프 `h-screen`(dvh 검토) | ✅(우수) |
| `chainsight` (목록) | 브레이크포인트 0 | RelationLegend/FilterChips 작은 칩 (MINOR) | — | — | ⚠️ |
| `admin` | 브레이크포인트 0 | 탭 `overflow-x-auto`, 테이블 래핑 ✅ | — | MLTrendChart Responsive ✅ | ⚠️(데스크톱 편중) |
| `market-pulse-v2` | 1 | TickerBar `overflow-x-auto` ✅ | — | 상세 5종 Responsive ✅ | ✅ |
| `stocks/[symbol]` | `md:hidden` 분기 사용 | 테이블 래핑 + 가로 탭 스크롤 ✅ | — | StockPriceChart Responsive ✅ | ✅ |
| `coach/e1~e6` | e3/e5 2개, 나머지 0~1 | — | — | — | ⚠️(확인 필요) |
| `login`/`signup` | — | 폼 요소 확인 필요 | — | — | — |

---

## 권고 우선순위 (감사 의견)

> 본 보고서는 읽기 전용 감사이며 아래는 수정 제안이 아니라 우선순위 정리다.

1. **[BLOCKER 즉시]** 루트 `app/layout.tsx`의 `<main>`에 `pb-16 md:pb-0` 일괄 적용 → 페이지별 `pb` 누락 재발 구조 근절. (현재 thesis만 `pb-20`, 나머지 다수 누락)
2. **[MAJOR]** thesis 관제실 — 기간 셀렉터 버튼 터치 영역 확대(`py-2` 이상 또는 `min-h-[44px]`), 지표 행 고정폭(`min-w-[120px]` 등) 모바일 완화.
3. **[MAJOR]** validation 카테고리 탭 `min-h-[44px]` 확보.
4. **[MINOR]** `Header.tsx` 도달 불가 모바일 드롭다운 데드코드 정리, 작은 클릭 칩들 패딩 보강, `h-screen`→`100dvh` 검토, 장기적으로 목록 가상화 도입 검토.

---

## 부록: 점검 방법론

- 고정폭: `grep -rnE 'min-w-\[[0-9]+px\]|w-\[[0-9]{3,}px\]'` (`max-w-[…]+truncate`는 안전으로 분류)
- 작은 텍스트: `grep -rnE 'text-\[1[01]px\]'` 후 클릭 핸들러 동반 여부 수동 분류
- 가로 스크롤: `grep -rnE 'overflow-x-auto|<table'`
- 차트: recharts import 파일 대비 `ResponsiveContainer` 부재 파일 차집합 (= 0건)
- 가상화: `react-window|@tanstack/react-virtual|virtua|FixedSizeList` (= 앱 코드 0건)
- 하단 가림: `app/layout.tsx`의 `<main>` 패딩 부재 + 페이지별 `pb-*` 실측 교차 확인

> **한계**: 정적 클래스 분석 기반. 실제 px 치수·줄바꿈·iOS Safari 동적 뷰포트는 실기기/브라우저 DevTools(375px) 검증으로 확정 필요. 특히 2-1(고정폭 합산 압박)과 4-3(`h-screen`)은 실측 권장.
