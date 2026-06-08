# 모바일 UX 감사 보고서

> 대상: `frontend/` (Next.js 16 / React 19 / Tailwind)
> 기준 뷰포트: 모바일 375px (iPhone SE/미니), 태블릿 768px
> 감사 범위: 컴포넌트 205개 + 페이지 30개 (읽기 전용, 코드 미수정)
> 작성일: 2026-06-08
> 기준: Apple HIG 터치 타겟 44×44pt, WCAG 2.1 (1.4.4 Resize Text / 2.5.5 Target Size)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 **BLOCKER** | 2 | ① 뷰포트 줌 차단(`userScalable:false`) ② 모바일에서 핵심 메뉴 4종 도달 경로 없음 |
| 🟠 **MAJOR** | 4 | ③ 관제실 기간선택 버튼 터치 미달 ④ EOD 시트 칩 버튼 터치 미달 ⑤ 긴 목록 가상화 전무 ⑥ 차트 축 라벨 모바일 가독성 |
| 🟡 **MINOR** | 4 | ⑦ md 브레이크포인트 건너뜀 ⑧ 사이드바 버튼 높이 ⑨ 스파크라인 막대 폭 ⑩ 일부 `text-[10px]` 본문 다수 |

**총평**: 골격(Bottom Nav, `overflow-x-auto` 테이블 래핑, `ResponsiveContainer` 차트, 모바일 분기 카드, `min-h-[44px]` 다수 적용)은 상당히 성숙. 그러나 **두 개의 BLOCKER가 모바일 사용성을 구조적으로 막음** — 줌 불가 + 절반의 핵심 메뉴 미도달. 이 둘은 각각 한 파일 수정으로 해결 가능.

---

## 반응형 누락

### 고정 폭 사용 현황 — 대체로 안전
고정 px 폭은 다수 발견되나 **대부분 overflow를 유발하지 않는 안전 패턴**이다:

| 패턴 | 위치 | 모바일(375px) 영향 |
|------|------|------------------|
| `max-w-[Npx] truncate` | ScreenerTable, SystemTab, NodeTooltip, SectorBar, RecommendationCard 등 다수 | ✅ 안전 — 상한선 + 말줄임. overflow 없음 |
| `min-w-[44px]` / `min-h-[44px]` | Pagination, Header, ScreenerTable 액션, SignalSummaryCard | ✅ 의도된 터치 타겟 |
| `w-[110px]` 인기섹터 버튼 | MarketGraphCanvas:676 | ✅ 부모가 `flex-wrap justify-center` → 줄바꿈 |
| `w-[52px]` 전송 버튼 | rag/ChatInterface:198 | ✅ flex-shrink-0 단일 버튼 |
| `max-w-[1400px] mx-auto` | InvestingHeader | ✅ 컨테이너 상한 |
| `md:w-[420px]` 사이드 시트 | eod/SignalDetailSheet:97 | ✅ 모바일 `w-full` → md부터 고정 |

➡️ **고정 폭으로 인한 실제 모바일 overflow는 식별되지 않음.** `truncate`와 `flex-wrap`이 일관되게 동반됨.

### 데스크톱 전용(브레이크포인트 부재) 그리드 — MINOR
일부 그리드가 `grid-cols-1`에서 곧바로 `lg:grid-cols-3`으로 점프하여 **태블릿(768~1023px)에서 1열**로 떨어진다(공간 낭비, overflow는 아님):

- `app/market-pulse/page.tsx:187` — `grid-cols-1 lg:grid-cols-3`
- `app/watchlist/page.tsx:207` — `grid-cols-1 lg:grid-cols-3`
- `app/news/page.tsx:210/237/277` — `grid-cols-1 lg:grid-cols-2|3`

➡️ 모바일 자체는 1열로 정상. **태블릿 최적화 누락**(MINOR). `md:grid-cols-2` 중간 단계 추가 권장.

### 테이블 가로 스크롤 처리 — 양호 ✅
테이블/와이드 콘텐츠는 **`overflow-x-auto`로 일관되게 래핑**됨 (33개소 확인):
StockTable, PortfolioTable, ScreenerTable, admin 전 테이블(SystemTab/ScreenerTab/NewsTab/TaskLogViewer/CollectionStatsTable), validation/LeaderComparisonSection, stocks/[symbol] 재무 테이블 등.
일부는 `scrollbar-hide`/`scrollbar-thin`까지 적용. ➡️ **테이블 가로 스크롤은 모범적**.

---

## 터치 타겟

### 준수 사례 ✅ (이미 잘 된 부분)
| 컴포넌트 | 처리 |
|----------|------|
| `MobileNav` 하단 탭 | `h-16` + `min-h-[44px]` (주석에 HIG 명시) |
| `Header` 햄버거 | `min-h-[44px] min-w-[44px]` (단, hidden — 아래 BLOCKER ②) |
| `Pagination` | `min-w-[44px] min-h-[44px]` |
| `validation/PeerContextBar` 프리셋 탭 | `min-h-[44px] px-4 py-2` ✅ |
| `validation/SignalSummaryCard` | `min-w-[72px] min-h-[44px]` ✅ |
| `thesis/QuarterlySparkline` 막대 | `min-h-[44px]` ✅ |
| `strategy/ScreenerTable` 액션 | `min-h-[44px] min-w-[44px]` ✅ |
| `chainsight` 인기섹터 버튼 | `min-h-[68px]` ✅ |

➡️ 사용자가 우려한 **validation 프리셋 탭은 44pt 준수 / chainsight 노드는 force-graph canvas(별도 모바일 클릭 핸들러 `handleNodeClickMobile` 구현) — 양호.**

### 🟠 MAJOR — ③ Thesis 관제실 기간선택 버튼
`components/thesis/dashboard/IndicatorRow.tsx:179-189`
```
className="px-2.5 py-0.5 text-[10px] rounded ..."  // 1M / 1Y / 3Y / 5Y
```
- 실측 높이 약 **20px** (py-0.5 + text-[10px]) → 44pt 대비 **절반 미만**.
- 차트 토글 펼친 상태에서 기간 전환은 핵심 인터랙션인데 손가락으로 정확히 누르기 어려움.
- 사용자가 지목한 "관제실 지표 카드" 영역. 카드 본체 토글은 `py-3`로 양호하나 **내부 기간 칩이 취약**.

### 🟠 MAJOR — ④ EOD SignalDetailSheet 칩/링크 버튼
`components/eod/SignalDetailSheet.tsx:188,197`
```
className="text-[10px] px-1.5 py-0.5 ... cursor-pointer"   // 클릭 가능 칩
className="text-[10px] ... font-medium"                    // 인라인 액션 링크
```
- `px-1.5 py-0.5 + text-[10px]` → 높이 ~18px. 클릭 가능 요소인데 타겟 과소.

### 🟡 MINOR — 기타 소형 클릭 요소
- `app/thesis/new/page.tsx:1063` — `text-[10px] ... inline-block` 링크 (꼬리표성 링크)
- `components/validation/CategorySidebar.tsx:51` — `px-3 py-2` 버튼(높이 ~36px), 데스크톱 사이드바라 영향 제한적이나 44pt 미달
- `text-[10px]` 본문 다수(thesis/new, market-pulse-v2, BriefCardSummary 등) — 클릭 요소는 아니나 **줌 차단(BLOCKER ①)과 결합 시 저시력 가독성 악화**

---

## 네비게이션

### 🔴 BLOCKER — ② 모바일에서 핵심 메뉴 4종 도달 경로 없음
구조:
- `app/layout.tsx` → `<Header />` + `<MobileNav />` 전역 배치.
- `Header` 데스크톱 nav: `hidden md:flex` (모바일 비표시).
- `Header` 햄버거 버튼: **`className="hidden ..."`** — 의도적으로 영구 숨김 (주석: "MobileNav가 모바일 네비 단일 소스").
- 따라서 모바일 네비게이션의 **유일한 소스 = `MobileNav` 하단 탭 5개**.

`components/layout/MobileNav.tsx:11-17` 하단 탭 항목:
```
홈(/) · 종목(/stocks) · 뉴스(/news) · 포트폴리오(/portfolio) · 내정보(/mypage)
```

➡️ **데스크톱 Header에는 있으나 MobileNav에는 없는 메뉴**:
| 메뉴 | 데스크톱 Header | MobileNav | 모바일 도달 |
|------|:---:|:---:|:---:|
| Chain Sight (`/chainsight`) | ✅ | ❌ | **직접 URL만** |
| Thesis Control (`/thesis`) | ✅ | ❌ | **직접 URL만** |
| Market Pulse (`/market-pulse`) | ✅ | ❌ | **직접 URL만** |
| 스크리너 (`/screener`) | ✅ | ❌ | **직접 URL만** |

→ 햄버거가 `hidden`이고 하단 탭에도 없으므로, **모바일 사용자는 이 4개 핵심 기능에 UI상 진입 불가**. Chain Sight·Thesis는 이 서비스의 시그니처 기능인데 모바일에서 사실상 봉인됨. 더불어 `/stocks` 탭은 종목 목록 라우트가 존재하는지 확인 필요(MobileNav만의 진입점).

**해결 방향**(택1): 햄버거의 `hidden` 제거(Header 모바일 드로어 부활, 코드는 이미 161~257행에 완비) **또는** MobileNav를 "더보기" 탭 + 시트로 확장.

### Bottom Navigation — 존재 ✅
`MobileNav`가 `fixed bottom-0 md:hidden z-50`으로 하단 고정 탭 제공. `aria-label`·active 상태 표시까지 구현. 단, **하단 고정 바와 페이지 하단 콘텐츠의 겹침 방지 패딩**(`pb-16` 등)이 각 페이지에 일관 적용됐는지는 페이지별 추가 검증 권장.

### 가상화 — 🟠 MAJOR ⑤ 전무
- `react-window` / `@tanstack/react-virtual` / `useVirtualizer` 등 **가상화 라이브러리 의존성 없음**(package.json 미존재, 코드 0건).
- 스크리너 종목 목록, 종목 테이블, 뉴스 목록 등 **수백 행 잠재 목록을 전량 DOM 렌더링**.
- 모바일 저사양 기기에서 스크롤 버벅임/메모리 압박 위험. 페이지네이션(`screener/Pagination`)으로 일부 완화되나, 무한 스크롤/긴 단일 목록 화면은 취약.

### 모바일 분기 카드 — 부분 적용
모바일 전용 카드 컴포넌트는 **2개 화면에만** 적용:
- `app/screener/page.tsx` → `MobileStockCard` (테이블↔카드 분기)
- `app/chainsight/[symbol]/page.tsx` → `MobileCardList`

➡️ 그 외 테이블 화면(포트폴리오/종목/admin/validation)은 `overflow-x-auto` 가로 스크롤에 의존. 가로 스크롤은 동작하나, **모바일에서 다열 재무 테이블은 카드 분기가 더 우수**.

---

## 차트/그래프

### ResponsiveContainer 사용 — 양호 ✅
Recharts 사용 14개 파일 **전부 `ResponsiveContainer width="100%"`로 래핑**:
StockPriceChart, StockChart, PortfolioChart, SentimentChart, YieldCurveChart, MetricBarChart, SectorHeatmap(Treemap), MLTrendChart, IndicatorRow, IndividualMiniCharts, market-pulse-v2 detail 4종.
➡️ **차트 가로 반응형은 모범적.** 고정 width 차트 없음.

### 🟠 MAJOR — ⑥ 차트 축 라벨 모바일 가독성
`components/thesis/dashboard/IndicatorRow.tsx:207,211,248,252`
```
<XAxis ... fontSize={9} />
<YAxis ... fontSize={10} width={55} />
```
- 축 눈금 **9~10px** — 375px 폭에서 가독성 한계. interval 샘플링으로 라벨 수는 줄였으나 글자 자체가 과소.
- 차트 높이는 `height={160}`/`140` 고정 → 모바일에서 적정하나 폭 좁아질수록 라벨 밀집.

### 🟡 MINOR — ⑨ 분기 스파크라인 막대 폭
`components/thesis/dashboard/QuarterlySparkline.tsx`
- `flex items-end gap-1 h-10` 막대 + `text-[11px]` 분기 라벨(Q1~Q4).
- 인라인 표시는 최근 4분기(`slice(-4)`)로 제한해 모바일에서 폭 확보 — 합리적.
- 다만 20분기 펼침 차트는 `ResponsiveContainer`(area chart)로 별도 처리되어 문제없음.
- 막대 자체는 `min-h-[44px]` 터치 래퍼로 감싸 터치는 양호. 시각적 막대 폭만 좁음(MINOR).

---

## 페이지별 상세

### 🔴 전역 (`app/layout.tsx`) — BLOCKER ①
```ts
viewport: {
  maximumScale: 1,
  userScalable: false,   // ← 핀치 줌 차단
  viewportFit: "cover",
}
```
- **WCAG 2.1 SC 1.4.4(Resize Text) 위반.** 사용자가 화면을 확대할 수 없음.
- 앱 전반에 `text-[10px]`/`text-[11px]` 소형 텍스트가 다수인데 **확대 수단까지 차단** → 저시력/노안 사용자 사실상 배제.
- PWA 풀스크린 느낌을 위한 설정으로 보이나, 투자 데이터(숫자) 정밀 확인 서비스에서 줌 차단은 치명적.
- **해결**: `userScalable` 제거(또는 `true`), `maximumScale: 5` 권장. 한 줄 수정.

### `/thesis/[thesisId]` (관제실) — MAJOR ③ / 차트 ⑥
- `IndicatorRow` 카드: 토글 본체(`py-3`)·스파크라인 터치는 양호.
- **기간선택 칩(1M/1Y/3Y/5Y) 터치 타겟 20px 미달** + 펼침 차트 축 라벨 9~10px.
- 2행 레이아웃 `min-w-[60px] + min-w-[120px] + max-w-[100px]`가 한 flex 행에 공존 → 375px에서 `gap-3 + pl-4` 포함 시 폭 압박(스파크라인 `flex-1`이 흡수해 overflow는 회피).

### `/screener` — 양호 + MINOR
- `MobileStockCard` 분기 ✅, `min-h-[44px]` Pagination ✅.
- `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`(855행)으로 단계적 반응형 ✅.
- `text-[10px]` 인덱스 뱃지(528행)는 비클릭 — 영향 적음.

### `/chainsight/[symbol]` — 양호
- `MobileCardList` 분기 ✅, force-graph `handleNodeClickMobile` 모바일 클릭 ✅.
- 그래프 캔버스 `h-[560px]` 고정 — 모바일 세로에서 화면 점유 크나 동작상 문제 없음.
- 노드 SVG 반경 8~28px이나 canvas 라이브러리가 탭 히트 영역을 자체 처리.

### `/market-pulse`, `/watchlist`, `/news` — MINOR ⑦
- 모바일 1열 정상. **태블릿 중간 브레이크포인트(`md:`) 누락**으로 768px대 공간 낭비.

### `/stocks/[symbol]` — 양호
- 재무 테이블 `overflow-x-auto` 2개소 래핑 ✅, 탭 바 `overflow-x-auto scrollbar-hide` ✅.
- `grid-cols-2 md:grid-cols-3 lg:grid-cols-4`(568행) 단계적 반응형 ✅.

### `/admin/*` — 양호(데스크톱 우선)
- 전 테이블 `overflow-x-auto` ✅. 관리자 화면이라 모바일 우선순위 낮음 — 현 상태 수용 가능.

### `/portfolio` — MAJOR ⑤ 연관
- `PortfolioTable` `overflow-x-auto` ✅, `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` ✅.
- 보유 종목 다수 시 가상화 부재 → 긴 목록 성능 우려.

---

## 우선순위 권고 (요약)

| 순위 | 이슈 | 파일 | 난이도 |
|------|------|------|--------|
| 1 | 🔴 뷰포트 줌 차단 해제 | `app/layout.tsx` viewport | 한 줄 |
| 2 | 🔴 MobileNav에 Chain Sight/Thesis/Market Pulse/Screener 노출(또는 햄버거 `hidden` 제거) | `MobileNav.tsx` / `Header.tsx` | 소 |
| 3 | 🟠 관제실 기간선택 칩 터치 타겟 ≥44pt | `IndicatorRow.tsx:179` | 소 |
| 4 | 🟠 EOD 시트 칩/링크 터치 타겟 | `SignalDetailSheet.tsx:188,197` | 소 |
| 5 | 🟠 차트 축 라벨 fontSize 상향(≥11) | `IndicatorRow.tsx` 외 | 소 |
| 6 | 🟠 긴 목록 가상화 도입 검토 | 스크리너/포트폴리오/뉴스 | 중 |
| 7 | 🟡 `md:` 중간 브레이크포인트 보강 | market-pulse/watchlist/news | 소 |

> 주: 본 보고서는 정적 코드 분석 기반이다. BLOCKER 2건은 코드만으로 확정 가능하나, 실제 기기/에뮬레이터 렌더링 검증(특히 하단 고정 바 겹침 패딩, 스크롤 성능)을 별도 권장한다.
