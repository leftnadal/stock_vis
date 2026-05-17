# 모바일 UX 감사 보고서

- **감사일**: 2026-05-17 (보고일: 2026-05-18)
- **감사 대상**: `frontend/` (Next.js 16, 195개 컴포넌트 + 24개 page.tsx)
- **방법**: 정적 코드 분석 (코드 수정 없음, 읽기 전용)
- **기준 뷰포트**: 375px (iPhone SE/12 mini 기준)
- **터치 타겟 기준**: Apple HIG 44×44pt

---

## 요약 (심각도별 이슈 수)

| 심각도 | 반응형 | 터치 타겟 | 네비 | 차트 | 합계 |
|--------|--------|-----------|------|------|------|
| **BLOCKER** | 0 | 5 | 0 | 0 | **5** |
| **MAJOR** | 4 | 12 | 2 | 1 | **19** |
| **MINOR** | 2 | 8 | 1 | 0 | **11** |
| **합계** | 6 | 25 | 3 | 1 | **35** |

**핵심 결론**:
1. **차트(Recharts)는 양호** — `ResponsiveContainer` 일관 사용 + 반응형 높이 함수 구현.
2. **반응형 레이아웃은 대체로 안전** — `grid-cols-1` 기본값 + `md:`/`lg:` 브레이크포인트 패턴이 일관됨. 다만 Market Pulse v2 일부 카드가 `sm:` 누락.
3. **터치 타겟이 가장 큰 문제** — 알림/카운트 배지, 작은 아이콘 버튼이 18~28px 수준. `text-[10px]` 클릭 요소 다수.
4. **모바일 네비게이션 불완전** — 하단 고정 탭바(`MobileNav`)는 존재하지만 5개 라우트만 노출. `/thesis`, `/chainsight`, `/market-pulse-v2`, `/screener` 누락 → 햄버거 없이는 탭 전환 불가.
5. **Virtualization 미적용** — 50+ 뉴스/스크리너 목록에서 모바일 스크롤 성능 위험.

---

## 반응형 누락

### MAJOR

#### `app/market-pulse-v2/details/BreadthDetail.tsx:29`
- `grid grid-cols-3 gap-2` — `sm:` 브레이크포인트 없음.
- 375px에서 3분할 시 메트릭 라벨/숫자가 찌그러짐.
- 권장: `grid-cols-2 sm:grid-cols-3`.

#### `app/market-pulse-v2/details/FlowDetail.tsx:34`
- 동일 패턴 `grid grid-cols-3 gap-2`.
- "top5", "top10", "HHI" 메트릭이 모바일에서 겹침.

#### `app/market-pulse-v2/cards/FlowCardSummary.tsx:13`
- `grid grid-cols-3 gap-2` — 카드 요약 영역이 모바일에서 너무 좁음.

#### `app/portfolio/page.tsx:210`
- `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4`.
- 모바일 2열은 안전하지만 `lg:grid-cols-6`이 과함 — 6개 요약 카드가 데스크톱에서 매우 좁아짐(반응형 자체는 동작하므로 MAJOR로 둠).

### MINOR

#### `components/screener/MobileStockCard.tsx:164`
- `grid grid-cols-3 gap-2`.
- 모바일 카드용 컴포넌트이므로 의도된 설계지만, 375px에서 "123.4M" 같은 숫자가 빠듯함.

#### `components/thesis/dashboard/IndicatorRow.tsx`
- `min-w-[60px]`, `min-w-[120px]` 사용. flex 컨테이너에서 `flex-1` 또는 width 제약과 함께 쓰이지 않으면 overflow 위험 — 현 시점에는 동작하나 추후 카드 폭 변경 시 회귀 위험.

### 양호한 패턴 (참고)

- `app/dashboard/page.tsx:54` — `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6` ✓
- `app/stocks/[symbol]/page.tsx:843-888` — 재무제표 `<table>`을 `overflow-x-auto` 래퍼로 감쌈 ✓
- `app/stocks/[symbol]/page.tsx:1058` — 사이드바 `w-48 flex-shrink-0 hidden lg:block` ✓
- `app/chainsight/[symbol]/page.tsx:358` — `w-72 ... hidden lg:block` ✓
- `components/strategy/ScreenerTable.tsx:128` — `<div className="overflow-x-auto">` 래퍼 ✓
- `components/strategy/ScreenerTable.tsx:209,224,307,323` — `max-w-[Xpx]` + `truncate` 페어링 ✓

---

## 터치 타겟

### BLOCKER (30px 미만, 실제 손가락 터치 곤란)

#### `components/thesis/common/AlertBell.tsx:17-22`
- 알림 카운트 배지: `min-w-[18px] h-[18px] px-1`, 약 **26×18px**.
- 빨간 배지 자체가 카운트 표시이자 클릭 영역 — 44px 미달.

#### `components/eod/SignalFilterTabs.tsx:66-76`
- 시그널 카운트 배지: `min-w-[18px] h-[18px] px-1 text-[11px]`.
- 인접 탭과의 간격이 좁아 오터치 위험.

#### `components/admin/news/AlertBadge.tsx:29`
- 미해결 알림 배지: `min-w-[18px] h-[18px] px-1 text-[10px]`.
- **약 20×18px**, 10px 텍스트.

#### `components/screener/PresetGallery.tsx:197`
- 프리셋 삭제 버튼: `p-1` + `w-3.5 h-3.5` 아이콘 → 약 **20×20px**.

#### `components/screener/PresetGallery.tsx:241-245`
- "상세 설명" 버튼: `text-[10px]` + `w-3 h-3` 아이콘.
- 텍스트 10px + 12px 아이콘 → 클릭 영역 너무 작음.

### MAJOR (30~43px, HIG 미달)

| # | 위치 | 클래스/크기 | 메모 |
|---|------|-------------|------|
| 1 | `components/thesis/IndicatorCard.tsx:52` | `text-[10px] px-1.5 py-0.5` 배지 | '선행/동행/후행' 약 30×18px |
| 2 | `components/thesis/IndicatorCard.tsx:59-67` | `p-1` + `ChevronUp/Down size={16}` | 토글 약 24×24px |
| 3 | `components/thesis/builder/PremiseCard.tsx:28` | `text-[10px] px-2 py-0.5` 카테고리 배지 | 약 20px 높이 |
| 4 | `components/thesis/indicators/IndicatorSetupCard.tsx:48-58` | `p-2` + `size={16}` Power/Trash | 약 32×32px |
| 5 | `components/chainsight/RelationFilterChips.tsx:150` | `h-8` (32px) | 칩 텍스트 `text-xs` + 아이콘 14 |
| 6 | `components/validation/PeerContextBar.tsx:40-49` | `min-h-[44px] px-4 py-2 text-xs` | 높이는 OK, 폰트 12px로 가독성 부족 |
| 7 | `components/eod/SignalCard.tsx:113` | `p-1` + `w-3.5 h-3.5` 교육팁 | 약 24×24px |
| 8 | `components/thesis/dashboard/IndicatorRow.tsx:95-104` | `text-[11px]` 날짜 + `size={14}` 토글 | 행 자체 `py-3`은 OK, 하위 요소 구분 어려움 |
| 9 | `components/thesis/alerts/AlertFilterTabs.tsx:24-28` | `px-3 py-1.5 text-xs` | 약 32px |
| 10 | `components/screener/Pagination.tsx:97-100,104-110,141-148,151-157` | `p-1.5` + `w-4 h-4` 아이콘 | 약 28×28px (4종 페이지 버튼 모두) |
| 11 | `components/thesis/dashboard/PeriodSelector.tsx:18-22` | `px-3 py-1.5 text-xs` | 기간 버튼 약 32px |
| 12 | `components/thesis/dashboard/IndicatorRow.tsx:177-190` | `flex gap-1.5` 4개 기간 버튼 | 인접 6px, 모바일 구분 곤란 |

### MINOR

| # | 위치 | 메모 |
|---|------|------|
| 1 | `components/thesis/builder/OptionButton.tsx:52,72` | 옵션 본체 `min-h-[52~56px]`은 OK, 우측 Info 버튼 `p-1` + `size={14}` → 약 22×22px |
| 2 | `components/screener/PresetDetailPopover.tsx:85-89` | 닫기 X 버튼 `p-1`(모바일 20×20), `p-0.5`(데스크톱 16×16) |
| 3 | `components/chainsight/RelationLegend.tsx:59` | 범례 토글 `text-[10px]` 라벨 + ▲ 문자 |
| 4 | `components/news/KeywordBadge.tsx:41-46` | `sm` 사이즈: `px-2 py-1 text-xs` 약 28px |
| 5 | `components/eod/ConfidenceBadge.tsx:19-28` | 각 dot `w-2 h-2` (8×8) — 정보 표시지만 점이 너무 작음 |
| 6 | `components/eod/SignalDetailSheet.tsx:203` | 정렬 버튼들 작음 (상세 미확인) |
| 7 | `components/screener/Pagination.tsx:92` | 페이지 버튼 그룹 `gap-1` (4px) |
| 8 | `components/admin/news/AlertBadge.tsx` | 어드민 한정이라 우선순위 낮음 |

---

## 네비게이션

### 헤더

- **[양호]** `components/layout/Header.tsx:30` — 헤더 높이 `h-16`(64px), 모바일에서 적정.
- **[양호]** `components/layout/Header.tsx:42-109` — 데스크톱 네비를 `hidden md:flex`로 처리.
- **[양호]** `components/layout/Header.tsx:155-163` — 헤더 햄버거 메뉴 버튼이 `hidden` 처리, MobileNav가 단일 모바일 네비 소스.

### 모바일 메뉴 (MobileNav)

#### `components/layout/MobileNav.tsx:7-47`
- 하단 고정 탭바(`position: fixed bottom-0`, `md:hidden`) 구현.
- `min-h-[44px]` 보장 (HIG 충족).

#### [MAJOR] `components/layout/MobileNav.tsx:11-17` — 라우트 누락
```
navItems = [/, /stocks, /news, /portfolio, /mypage]   ← MobileNav
Header   = [/, /portfolio, /chainsight, /thesis,
            /market-pulse, /news, /screener]          ← Header
```
모바일에서 **`/thesis`, `/chainsight`, `/market-pulse-v2`, `/screener`** 4개 핵심 라우트로 직접 이동 불가. 이들 페이지에 진입한 사용자는 다른 섹션으로 이동하려면 페이지 상단 스크롤 + 햄버거(현재 hidden) 또는 직접 URL 입력 필요.

### Bottom Navigation

- **[양호]** 존재함 (MobileNav). Apple/Material 패턴 준수.

### Virtualization

#### [MAJOR] 라이브러리 미사용
- `package.json`에 `react-window`, `virtua`, `react-virtualized` 부재.
- `components/news/NewsList.tsx:228-242` — `.map()` 직렬 렌더링, 뉴스 30~100개 시 모바일 프레임 드롭 위험.
- `components/screener/ScreenerDashboard.tsx` — 스크리너 결과 100개 이상이면 동일 위험. `MobileStockCard`가 비교적 가볍지만 DOM 노드 수 증가는 동일.

### 기타

- **[양호]** `app/layout.tsx:60` `min-h-screen` 사용 (`100vh` 미사용 → 모바일 주소창 문제 회피).
- **[MINOR]** MobileNav `fixed bottom-0` + 가상 키보드 충돌은 현재 검색 입력이 헤더에 한정되어 즉시 문제 없음. 모바일 검색/대화형 빌더(`/thesis/new`) 입력 영역과의 상호작용은 실기기 테스트 필요.

---

## 차트/그래프

### Recharts `ResponsiveContainer`

| 컴포넌트 | 위치 | 상태 |
|----------|------|------|
| PieChart / BarChart | `components/portfolio/PortfolioChart.tsx:77,97` | `width="100%"` ✓ |
| ComposedChart (캔들+거래량) | `components/stock/StockChart.tsx:652,748` | `width="100%" height={chartHeight.*}` ✓ |
| LineChart (수익률 곡선) | `components/macro/YieldCurveChart.tsx:93` | `width="100%" height="100%"` ✓ |
| Treemap (섹터 히트맵) | `components/screener/SectorHeatmap.tsx:216` | `width="100%" height={400}` ✓ |

**모든 Recharts 차트가 `ResponsiveContainer`로 감싸짐 — BLOCKER/MAJOR 없음.**

### 반응형 차트 높이

#### [양호] `components/stock/StockChart.tsx:177-187`
```tsx
function getResponsiveChartHeight(windowWidth: number) {
  if (windowWidth < 640)  return { price: 280, volume: 70 };
  if (windowWidth < 1024) return { price: 320, volume: 80 };
  return { price: 350, volume: 90 };
}
```
모바일/태블릿/데스크톱별 적절히 축소됨.

### 분기 스파크라인

- `components/thesis/dashboard/IndicatorRow.tsx`의 행 구성은 양호하나, **스파크라인 자체 컴포넌트의 ResponsiveContainer 사용 여부는 상세 확인 미완료** — 후속 점검 권장.

### Chainsight 그래프 (force-graph)

- **[양호]** `components/chainsight/MarketGraphCanvas.tsx:17` — `dynamic(() => import('react-force-graph-2d'), { ssr: false })`로 SSR 회피.
- **[양호]** `components/chainsight/MobileCardList.tsx` — 모바일 fallback 구현 (카테고리 탭 + 카드 리스트). Canvas 그래프 대신 텍스트 기반 대안 제공.

### [MAJOR] 분기 스파크라인 폭 가독성

- IndicatorRow에서 스파크라인이 행 우측 작은 영역에 들어가며, `min-w-[120px]` 등 폭 제약이 있는 경우 모바일에서 화면 잘림이나 정보 시인성 부족 가능성. 실기기 검증 필요.

---

## 페이지별 상세

### `app/page.tsx` (메인)
- 데이터 부족 (메인 페이지는 라우터 디스패치 위주). 별도 BLOCKER/MAJOR 없음.

### `app/dashboard/page.tsx` (EOD Dashboard)
- [양호] `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6` 반응형 OK.
- [BLOCKER × 1] SignalFilterTabs 카운트 배지 18×18px.
- [MAJOR × 1] SignalCard 교육팁 아이콘 24×24px.

### `app/thesis/(list)/page.tsx` 외 thesis 전체
- [양호] 본문 레이아웃 모바일 친화적 (세로 스택).
- [BLOCKER × 1] AlertBell 배지 26×18px.
- [MAJOR × 6] IndicatorCard 배지/토글, PremiseCard 카테고리 배지, IndicatorSetupCard Power/Trash, IndicatorRow 라벨, AlertFilterTabs, PeriodSelector.
- [MINOR × 2] OptionButton Info 버튼, IndicatorRow 기간 버튼 그룹 gap.
- **관제실 지표 카드(IndicatorCard)는 사용자 지정 BLOCKER 검토 대상이었으며, 토글/배지 모두 30px 안팎 — MAJOR 분류.**

### `app/screener/page.tsx`
- [양호] `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` 패턴.
- [BLOCKER × 2] PresetGallery 삭제 버튼 20×20, 상세설명 버튼 10px 텍스트.
- [MAJOR × 1] Pagination 4종 아이콘 버튼 28×28px.
- [MINOR × 2] PresetDetailPopover 닫기 X, Pagination gap.
- **프리셋 탭은 `PeerContextBar`(validation)와 별개. PresetGallery 자체는 카드형이며 클릭 영역은 카드 전체로 OK이나 보조 버튼(삭제·상세설명)이 문제.**

### `app/chainsight/page.tsx`, `[symbol]/page.tsx`
- [양호] 사이드바 `w-72 ... hidden lg:block`.
- [양호] 모바일에서 force-graph 대신 `MobileCardList` 카드 리스트 fallback.
- [MAJOR × 1] RelationFilterChips `h-8` (32px) 칩.
- [MINOR × 1] RelationLegend 토글 10px 텍스트.
- **chainsight 노드는 force-graph 캔버스 노드라 픽셀 단위 터치 영역 측정 불가 — MobileCardList fallback에 의존 (양호).**

### `app/news/page.tsx`
- [양호] `grid-cols-1 lg:grid-cols-3` 패턴.
- [MAJOR × 1] NewsList virtualization 미적용, 30~100건 시 성능 우려.
- [MINOR × 1] KeywordBadge `sm` 사이즈 28px.

### `app/market-pulse-v2/page.tsx`
- [MAJOR × 3] BreadthDetail, FlowDetail, FlowCardSummary 모두 `grid-cols-3` (sm: 없음).
- [양호] EconomicIndicators 반응형 적절.

### `app/portfolio/page.tsx`
- [양호] 재무 테이블 `overflow-x-auto` 래퍼.
- [MAJOR × 1] 요약 카드 `lg:grid-cols-6` 과다 분할 (반응형 자체는 동작).
- [양호] PortfolioChart Recharts ResponsiveContainer OK.

### `app/stocks/[symbol]/page.tsx`
- [양호] 메트릭 그리드 반응형, 재무 테이블 가로 스크롤, 사이드바 `hidden lg:block` 모두 OK.
- 차트 ResponsiveContainer + 반응형 높이 OK.

### `app/validation/...` (PeerContextBar 등)
- [MAJOR × 1] PeerContextBar 프리셋 탭 `min-h-[44px]`은 OK지만 `text-xs`(12px) 가독성 부족.

### `app/admin/...`
- [BLOCKER × 1] AlertBadge 18×18 / 10px.
- 어드민 한정 UI라 일반 사용자 영향 적음.

---

## 권장 조치 우선순위 (코드 변경은 별도 PR로)

1. **[BLOCKER 5건]** 카운트/알림 배지 래퍼에 `min-h-[44px] min-w-[44px] flex items-center justify-center` 적용 또는 부모 클릭 영역 확장.
2. **[MAJOR 네비 1건]** `MobileNav.navItems`에 `/thesis`, `/chainsight`, `/market-pulse-v2`, `/screener` 추가 또는 7→5개 선별 정책 명문화.
3. **[MAJOR 반응형 3건]** Market Pulse v2 `grid-cols-3` → `grid-cols-2 sm:grid-cols-3`.
4. **[MAJOR 터치 12건]** 작은 아이콘 버튼 `p-1` → `p-2.5` 또는 `min-w/h-[44px]` 명시. `text-[10px]` 제거 또는 클릭 비활성화.
5. **[MAJOR 성능 1건]** NewsList / ScreenerDashboard에 `react-window` 등 virtualization 도입 (50건 초과 시).
6. **[MAJOR 분기 스파크라인]** 폭 제약 컴포넌트의 실기기 검증.
7. **[MINOR 11건]** 인접 버튼 `gap-1` → `gap-2`, 보조 버튼 폰트 12px 이상.

---

## 검증 미완료 / 후속 확인 권장

- 분기 스파크라인(`components/thesis/dashboard/QuarterlySparkline.tsx` 또는 IndicatorRow 내부)의 ResponsiveContainer 사용 여부 — 상세 확인 미완.
- `app/thesis/new/page.tsx` 대화형 빌더의 입력 폼과 가상 키보드 + MobileNav 고정 탭바 간 충돌 — 실기기 테스트 필요.
- chainsight force-graph 캔버스의 모바일 터치 제스처(핀치 줌, 더블탭) 작동 여부 — 코드만으로는 판단 불가.
- `app/thesis/[thesisId]/page.tsx` 관제실 지표 카드의 실제 렌더링된 픽셀 폭(컨테이너 폭 의존) — DOM 검사 필요.

---

**보고서 끝.** 본 감사는 정적 분석 기반으로, 35건의 이슈 중 BLOCKER 5건과 MAJOR 19건은 코드 단편으로 확인됨. 실기기 검증 항목 4건은 별도 QA 세션 권장.
