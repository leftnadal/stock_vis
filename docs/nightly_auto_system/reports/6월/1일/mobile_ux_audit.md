# 모바일 UX 감사 보고서

> **감사일**: 2026-06-01
> **대상**: `frontend/` (페이지 30개, 컴포넌트 205개)
> **기준 뷰포트**: 375px (iPhone SE/모바일 표준)
> **방식**: 정적 코드 분석 (읽기 전용, 코드 수정 없음)
> **참조 기준**: Apple HIG 44×44pt 터치 타겟, WCAG 2.1 (1.4.4 줌/리사이즈), Material 권장

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 **BLOCKER** | 2 | 모바일 주요 기능 페이지 접근 경로 부재, `userScalable: false` 줌 차단 |
| 🟠 **MAJOR** | 6 | bottom nav 콘텐츠 가림(6개 페이지), `/stocks` 깨진 라우트, 차트 기간 버튼 터치 미달, InvestingHeader 레거시, 작은 폰트 클릭요소 44개 파일, 데스크톱 차트 다수 |
| 🟡 **MINOR** | 5 | 고정폭 truncate 의존, text-[10px]/[11px] 가독성, 관제실 2행 폭 빠듯, 미사용 헤더, virtualization 부재 |

**총 13개 이슈군** — 네비게이션·레이아웃 골격은 모바일을 고려한 흔적(MobileNav, MobileCardList, `pb-20` 일부 적용)이 보이나, **전역 일관성이 깨져** 페이지별로 모바일 경험 편차가 크다.

---

## 반응형 누락

### 고정 폭 사용 현황
`w-[NNpx]` / `min-w-[NNpx]` / `max-w-[NNpx]` 패턴: **42개 파일, 66건**

대부분은 `max-w-[NNpx] truncate`(텍스트 말줄임) 또는 `min-w-[NNpx]`(최소 정렬폭)로, 375px에서 **즉각적 overflow를 일으키지 않는** 방어적 사용이다. 단 아래는 주의:

| 파일 | 위치 | 패턴 | 375px 영향 | 심각도 |
|------|------|------|-----------|--------|
| `chainsight/MarketGraphCanvas.tsx` | L676 | `w-[110px] min-h-[68px]` (인기 섹터 버튼) | `flex-wrap justify-center`로 줄바꿈 → 안전 | 🟡 MINOR |
| `thesis/dashboard/IndicatorRow.tsx` | L110·115·132 | `min-w-[60px]` + `min-w-[120px]` + `max-w-[100px]` | 합산 ~280px + gap + pl-4(16px) → 375px 빠듯하나 truncate로 수용 | 🟡 MINOR |
| `strategy/ScreenerTable.tsx` | L209·224·307 | `max-w-[180/120/200px] truncate` | 테이블 셀, `overflow-x-auto` 래퍼 내부 → 안전 | 🟡 MINOR |
| `chainsight/SectorBar·NodeTooltip·RelationLegend` | — | `max-w-[120~140px] truncate` | 안전 | — |

→ **고정 폭으로 인한 BLOCKER급 overflow는 발견되지 않음.** 대부분 `truncate`·`flex-wrap`·`overflow-x-auto`와 결합되어 방어됨.

### 데스크톱 전용 컴포넌트 (브레이크포인트 부재)
- **`layout/InvestingHeader.tsx`** — 🟠 MAJOR(레거시): top bar에 지수 정보를 `space-x-6` flex 단일 행으로 나열(L34~41), `max-w-[1400px]` 고정, 모바일 분기 전무. **단, 어디에서도 import되지 않는 미사용 레거시**(하드코딩 "2025년 10월 25일" 가짜 데이터 포함). 실제 렌더링 안 되므로 사용자 영향 없음 → **삭제 권고 대상**.
- 실 사용 헤더 `layout/Header.tsx`는 `sm:`/`md:`/`lg:` 브레이크포인트를 적극 사용(`hidden md:flex` 등) → 반응형 자체는 양호하나, 모바일 네비 누락 문제는 별도(아래 네비게이션 섹션).

### 테이블 가로 스크롤 처리 — ✅ 양호
검사한 주요 테이블 3종 모두 `overflow-x-auto` 래퍼로 감쌈:
- `strategy/ScreenerTable.tsx` L128 `<div className="overflow-x-auto">`
- `stocks/StockTable.tsx` L34 동일
- `portfolio/PortfolioTable.tsx` L259 동일 (`min-w-full`)

→ 테이블은 모바일에서 가로 스크롤로 정상 처리. 다만 테이블은 본질적으로 모바일 비친화적이므로, screener는 별도 `MobileStockCard.tsx`(카드형)를 제공하는 것이 확인됨 → **모범 패턴**.

---

## 터치 타겟

### 🟠 MAJOR — 차트 기간 선택 버튼 (thesis 관제실)
**`thesis/dashboard/IndicatorRow.tsx` L177~190** — 일간 지표 차트의 기간 셀렉터(1M/1Y/3Y/5Y):
```
className="px-2.5 py-0.5 text-[10px] ..."
```
- `py-0.5`(2px) + `text-[10px]` → 실제 높이 **약 18~20px**. HIG 44pt의 절반 미만.
- 분기 토글식 차트 진입 후 핵심 인터랙션인데 손가락 정확도 부족. **관제실 지표 카드의 대표 터치 결함.**

### ✅ 양호 — validation 프리셋 탭
**`validation/PeerContextBar.tsx` L40·54** — 프리셋 탭 및 "직접 설정" 버튼 모두 `min-h-[44px] px-4 py-2` 적용. **HIG 충족.** (단 peer 목록 보기 버튼 L118, 커스텀 "적용" 버튼 L85는 `py-1.5`로 작으나 보조 액션).

### ✅ 양호 — chainsight 노드/카드
- `MobileCardList.tsx` L169·175·181 — CTA(가설생성/탐색/검증) 모두 `min-h-[44px]`. 단 3개를 `flex-1`로 한 행 배치 → 375px에서 각 ~105px·`text-xs`, 수용 가능하나 여백 빠듯(🟡).
- `MarketGraphCanvas.tsx` L676 인기 섹터 버튼 `min-h-[68px]` → 충분.
- `SignalSummaryCard.tsx` L41 `min-w-[72px] min-h-[44px]` → 충족.

### 🟠 MAJOR — 작은 폰트 클릭 요소 광범위
- `text-[10px]` / `text-[11px]`: **57개 파일, 127건** 사용.
- 이 중 **클릭 요소(`onClick`/`<button>`/`<Link>`)를 동반한 파일 44개.**
- 대표 사례: `market-pulse/MoverCard.tsx`(6건), `thesis/dashboard/IndicatorRow.tsx`(7건), `thesis/builder/SuggestionCard.tsx`(5건), `keywords/KeywordTag.tsx`(3건), `screener/PresetGallery.tsx`(4건).
- 작은 폰트 자체가 곧 작은 터치 영역은 아니나(패딩으로 보정 가능), 다수가 `py-0.5~1` 저패딩과 결합 → 실측 터치 미달 위험 높음. **개별 검수 필요 항목**.

---

## 네비게이션

### 🔴 BLOCKER — 모바일에서 주요 기능 페이지 접근 경로 없음
구조 분석 (`app/layout.tsx` L59·63: `<Header/>` + `<MobileNav/>` 마운트):

1. **`Header.tsx`**: 데스크톱 nav는 `hidden md:flex`(L42), 햄버거 버튼은 아예 `hidden`(L157, 주석상 "audit P0 #12로 의도적 비표시"). 검색바도 `hidden md:block`(L112).
   → **모바일(<768px)에서 상단 헤더에는 로고만 표시되고 네비게이션 링크가 전무.**

2. **`MobileNav.tsx`** (bottom nav, `md:hidden`): 항목 **5개뿐** — 홈/종목/뉴스/포트폴리오/내정보.
   → **chainsight, thesis(관제실), market-pulse, screener, mypage 외 핵심 기능은 모바일에서 진입 경로가 없음.** 데스크톱 nav에는 7개 메뉴(대시보드·포트폴리오·Chain Sight·Thesis·Market Pulse·뉴스·스크리너)가 있으나 모바일 bottom nav와 불일치.
   → 모바일 사용자는 Chain Sight·Thesis Control·Screener·Market Pulse에 **직접 URL 입력 외 도달 불가**. 서비스 핵심 기능 대부분이 모바일에서 묻힘.

**권고**: 모바일 햄버거 메뉴 부활(Header L157 버튼은 이미 구현되어 있고 `hidden`만 제거하면 전체 메뉴 노출) 또는 bottom nav 항목 재구성.

### 🟠 MAJOR — `/stocks` 깨진 라우트
`MobileNav.tsx` L13 `{ name: '종목', href: '/stocks' }` → 그러나 `app/stocks/`에는 `[symbol]/page.tsx`만 존재하고 **`/stocks` 인덱스 페이지(page.tsx)가 없음**.
→ bottom nav "종목" 탭 탭 시 **404**. 모바일 5개 탭 중 하나가 작동 불능.

### 🟠 MAJOR — bottom nav가 콘텐츠 하단을 가림 (전역 패턴)
`MobileNav.tsx` L20 `fixed bottom-0 ... h-16`(64px). `layout.tsx`의 `<main>`(L60)에는 하단 패딩이 없어, **각 페이지가 자체적으로 `pb-*`를 줘야** 마지막 콘텐츠가 안 가려진다. 실측:

| 페이지 | 하단 패딩 | 상태 |
|--------|----------|------|
| `app/page.tsx`(홈) | `pb-20` | ✅ |
| `app/thesis/[thesisId]/page.tsx`(관제실) | `pb-20` | ✅ |
| `app/dashboard/page.tsx` | 없음 | ❌ 가림 |
| `app/chainsight/page.tsx` | 없음 | ❌ 가림 |
| `app/screener/page.tsx` | 없음 | ❌ 가림 |
| `app/news/page.tsx` | 없음 | ❌ 가림 |
| `app/portfolio/page.tsx` | 없음 | ❌ 가림 |
| `app/market-pulse/page.tsx` | 없음 | ❌ 가림 |

→ **6개 주요 페이지에서 최하단 콘텐츠/버튼이 64px bottom nav에 가림.** `layout.tsx`의 `<main>`에 `pb-16`(또는 safe-area 포함 `pb-[calc(4rem+env(safe-area-inset-bottom))]`)을 일괄 부여하면 전역 해결. globals.css에도 safe-area 처리 없음.

### 🟡 MINOR — virtualization 부재
긴 목록(screener 결과, news 목록, chainsight 카드 리스트, watchlist)에 `react-window`/`virtua` 등 가상화 미적용. `MobileCardList.tsx`는 `overflow-y-auto`로 전체 DOM 렌더 → 노드 수백 개 시 모바일 스크롤 성능 저하 가능. 현재 데이터 규모에선 영향 제한적.

---

## 차트/그래프

### Recharts ResponsiveContainer 사용 현황 — ✅ 대체로 양호
`ResponsiveContainer` 사용: **15개 파일** (`StockPriceChart`, `IndicatorRow`, `MetricBarChart`, `YieldCurveChart`, `SentimentChart`, `PortfolioChart`, market-pulse-v2 details 4종 등).
- `thesis/dashboard/IndicatorRow.tsx` L197·235 — `width="100%" height={160/140}` → 모바일 폭 자동 대응. ✅
- `charts/StockPriceChart.tsx` L272 — `ResponsiveContainer width="100%"` ✅

차트 렌더 컴포넌트(`BarChart`/`LineChart`/`AreaChart` 등 직접 사용)는 ~26개 파일에서 확인되나, 그중 ResponsiveContainer로 감싸지 않은 케이스는 개별 정밀 확인 필요(상당수는 위 15개 파일과 중복). **체계적으로 ResponsiveContainer 패턴이 정착**되어 있어 차트 가로 overflow 위험은 낮음.

### 🟡 MINOR — 분기 스파크라인 모바일 가독성
`thesis/dashboard/IndicatorRow.tsx` L131~138 — 인라인 스파크라인이 `flex-1 max-w-[100px]`로 최근 4분기만 표시. 100px 폭에 4포인트 → 추세 식별엔 충분하나 값 라벨 없음. 펼침 시 전체 차트(`height={140}`) 제공으로 보완 → **설계 의도 양호**.

### ✅ chainsight 그래프 — 모바일 분기 처리 우수
`app/chainsight/[symbol]/page.tsx` L53·152·173 — `isMobile` 상태로 분기:
- 모바일: `MobileCardList`(카드형) 렌더 (그래프 대신)
- 데스크톱: `MarketGraphCanvas`(SVG 그래프)
→ **SVG 노드 그래프를 모바일에 강제하지 않고 카드 UI로 대체하는 모범 패턴.** 그래프 보기는 FAB(`onShowGraph`)로 선택 제공.

---

## 페이지별 상세

| 페이지 | 모바일 상태 | 주요 이슈 | 심각도 |
|--------|------------|----------|--------|
| `app/page.tsx`(홈) | 양호 | `pb-20` 적용, EOD 대시보드 | — |
| `app/dashboard/page.tsx` | 주의 | 하단 패딩 없음 → bottom nav 가림 | 🟠 |
| `app/chainsight/page.tsx` | 주의 | bottom nav 가림 / 모바일 진입 경로 없음(nav) | 🟠/🔴 |
| `app/chainsight/[symbol]/page.tsx` | **우수** | isMobile 분기 + MobileCardList 카드 UI | ✅ |
| `app/thesis/(list)/page.tsx` | 양호 | 관제실 목록 | — |
| `app/thesis/[thesisId]/page.tsx`(관제실) | 양호 | `max-w-lg mx-auto pb-20` 모바일 우선 설계 / 단 IndicatorRow 기간버튼 터치 미달 | 🟠(터치) |
| `app/screener/page.tsx` | 주의 | bottom nav 가림 / 테이블은 카드 대체(MobileStockCard) 제공 | 🟠 |
| `app/news/page.tsx` | 주의 | bottom nav 가림 | 🟠 |
| `app/portfolio/page.tsx` | 주의 | bottom nav 가림 / 테이블 overflow-x 처리됨 | 🟠 |
| `app/market-pulse/page.tsx` | 주의 | bottom nav 가림 | 🟠 |
| `app/stocks/[symbol]/page.tsx` | 양호 | overflow-x 처리, ResponsiveContainer 차트 | — |
| `/stocks`(인덱스) | **부재** | 라우트 자체 없음 → MobileNav "종목" 404 | 🟠 |
| validation(주식 상세 내 탭) | 양호 | PeerContextBar 프리셋 탭 44pt 충족 | ✅ |

---

## 핵심 권고 (우선순위)

1. 🔴 **모바일 네비게이션 복구** — `Header.tsx` L157 햄버거 버튼의 `hidden` 제거(이미 전체 메뉴 구현됨) 또는 MobileNav 항목을 데스크톱 7개 메뉴와 정합. chainsight/thesis/screener/market-pulse 모바일 도달 경로 확보.
2. 🔴 **`userScalable: false` 재고** — `layout.tsx` L33. WCAG 1.4.4 위반. 저시력 사용자 핀치 줌 차단. PWA 정책상 의도라면 최소 `maximumScale` 상향 검토.
3. 🟠 **`/stocks` 인덱스 페이지 생성** 또는 MobileNav href를 유효 라우트로 교체 (404 제거).
4. 🟠 **`layout.tsx` `<main>`에 `pb-16` + safe-area 일괄 적용** — 6개 페이지 bottom nav 가림 전역 해결.
5. 🟠 **`IndicatorRow` 기간 버튼 터치 영역 확대** — `py-0.5 text-[10px]` → 최소 `py-2`/`min-h-[36px]`급.
6. 🟡 **`InvestingHeader.tsx` 미사용 레거시 삭제** (가짜 하드코딩 데이터 포함).
7. 🟡 **작은 폰트 클릭 요소 44개 파일 패딩 검수** — `text-[10px/11px]` + 저패딩 결합 케이스 우선.

---

## 모범 패턴 (유지 권장)

- ✅ chainsight `isMobile` 분기 → 그래프를 카드 UI로 대체
- ✅ screener 테이블 → `MobileStockCard` 카드형 병행
- ✅ 모든 테이블 `overflow-x-auto` 래핑
- ✅ Recharts `ResponsiveContainer` 일관 적용
- ✅ thesis 관제실 `max-w-lg` 모바일 우선 레이아웃
- ✅ validation 프리셋 탭 / MobileNav / chainsight CTA의 `min-h-[44px]` 명시적 터치 타겟

---

> **주의**: 본 보고서는 정적 코드 분석 기반이며, 실제 375px 렌더링 측정(브라우저)을 거치지 않았다. overflow·터치 실측 검증은 별도 디바이스 QA로 보완 권장. 코드는 일절 수정하지 않았다.
