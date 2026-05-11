# 모바일 UX 감사 보고서

- 감사 일자: 2026-04-23 (야간 자동 감사 — 대상 코드 스냅샷: 2026-04-22 기준)
- 감사 대상: `frontend/` (Next.js 16 + TypeScript + Tailwind 4)
- 기준 뷰포트: **375 × 667 (iPhone SE / Safari iOS)**
- 감사 유형: 읽기 전용 정적 분석 (코드 수정 없음)
- 조사 방식: `components/**/*.tsx` 192개, `app/**/page.tsx` 23개, layout 다수에 대한 Tailwind 클래스 · import · 고정 수치 패턴 검사
- 검증 방식: 주요 BLOCKER 후보는 실제 파일을 열어 조건부 렌더 로직(`isMobile`, `hidden/block` 계층, `md:` prefix)과 overflow 래퍼 실제 존재 여부까지 교차 확인
- **주의**: 2026-04-22 보고서(`4월/21일/mobile_ux_audit.md`)에 4건의 BLOCKER가 실제 코드와 일치하지 않았음 — 본 보고서의 "이전 감사 보정" 항목 참고

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|---|---:|---|
| **BLOCKER** | **1** | 375px에서 가로 overflow 확정 또는 핵심 UI가 조작 불가능 |
| **MAJOR**   | **9** | 터치 타겟 44pt 미만 핵심 버튼 · 모바일 전용 렌더 미제공으로 UX 저하 확정 |
| **MINOR**   | **13** | 배지·라벨 등 비상호작용 요소의 시인성 저하, 규모 의존 잠재 성능 이슈 |
| **총계**    | **23** | |

### BLOCKER 1건 한눈에 보기

1. `app/chainsight/page.tsx` (메인 탐색 화면) — `MarketGraphCanvas`가 `h-[400px]` + `containerRef.clientWidth` 기반으로 렌더되는데, 이 페이지에는 `/chainsight/[symbol]` 같은 `isMobile` 분기 대체 뷰가 **없음**. 375px 화면에서 force-graph 조작(노드 드래그/탭)이 사실상 불가능하며 페이지 전체 콘텐츠(섹터 바, 탐색 트레일, 관계 카드)가 400px 고정 캔버스에 가려짐.

> **지난 감사(4월 21일) BLOCKER 4건 중 3건은 실제로는 잘못된 진단이었음** — 아래 "이전 감사 보정" 섹션 참고. 실제 BLOCKER 남은 것은 위 1건.

---

## 반응형 누락

### A. 고정 폭 사용 (Tailwind 임의값)

전체 frontend에서 `w-[NNpx]` / `min-w-[NNpx]` / `max-w-[NNpx]` 임의값 **27개 파일 / 40+ 인스턴스** 발견. 대부분 truncate 보조용. 아래는 모바일 영향 가능성이 있는 항목만.

| 심각도 | 파일:라인 | 클래스 | 실제 영향 |
|---|---|---|---|
| MAJOR | `components/thesis/dashboard/IndicatorRow.tsx:110,115` | `min-w-[60px]`, `min-w-[120px]` | 값(60) + 변동률 라벨(120) + 스파크라인(100) + 지지/반박 텍스트 합이 375px에서 매우 빡빡함. `flex-1 truncate`로 이름은 줄어드나 숫자 블록은 압축 불가 |
| MAJOR | `components/chainsight/MarketGraphCanvas.tsx:97,107,114,119` | `h-[400px]` × 3 + `height={400}` 프롭 | 세로 고정. 375×667 뷰포트에서 화면의 60% 이상 점유. 터치 조작이 사실상 불가능한 force-graph 렌더 |
| MINOR | `components/strategy/ScreenerTable.tsx:209,224,307` | `max-w-[180/120/200px]` | 셀 내부 truncate. 테이블 바깥(`ScreenerTable.tsx:128`)에 `overflow-x-auto` 래퍼 존재하여 overflow 없음 |
| MINOR | `components/common/DataSourceBadge.tsx:171` | `min-w-[200px]` | 호버 팝오버 내부. 화면 우측 끝 앵커 시에만 잘림 가능성 |
| MINOR | `components/eod/SignalDetailSheet.tsx:97` | `md:w-[420px]` | md(768px) 이상에서만 적용. 모바일은 `w-full` — 무영향 |
| MINOR | `components/layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` × 3 | **어디에서도 import 되지 않은 데드 코드** — 실제 마운트 안 됨 |
| MINOR | `components/rag/ChatInterface.tsx:198` | `h-[52px] w-[52px]` | 전송 버튼. 52×52 ≥ 44 HIG 충족 ✓ |

### B. 브레이크포인트 커버리지

- `sm:/md:/lg:/xl:` **사용 파일 수**: `components/` 48개 + `app/` 14개 = 총 62개
- **아래 페이지는 반응형 prefix가 없지만 영향은 케이스별로 다름**:

| 파일 | prefix 유무 | 실제 영향 |
|---|---|---|
| `app/thesis/(list)/layout.tsx:7` | `max-w-lg` 사용 | mobile-first 512px 캡 — 오히려 모바일 최적화됨 ✓ |
| `app/thesis/(list)/page.tsx` | 없음 | layout이 폭 제어. 카드 기반이라 자동 적응 ✓ |
| `app/thesis/(list)/alerts/page.tsx` | 없음 | 알림 목록, 단일 열 카드 기반 ✓ |
| `app/thesis/[thesisId]/page.tsx:31,41,62` | `max-w-lg` | 대시보드 — 폭 적합. 내부 `IndicatorRow`가 MAJOR |
| `app/thesis/[thesisId]/indicators/page.tsx` | 없음 | `IndicatorRow` 다수 나열 — MAJOR로 전파 |
| `app/thesis/[thesisId]/close/page.tsx` | 없음 | 단순 폼, MINOR |
| `app/chainsight/page.tsx` | `max-w-7xl` + prefix 없음 | **BLOCKER** — `h-[400px]` 그래프 캔버스 + 모바일 분기 없음 |
| `app/chainsight/watchlist/page.tsx:22` | `max-w-3xl` | 768px 캡, 모바일 적합 ✓ |
| `app/chainsight/watchlist/[id]/page.tsx:13,21` | `max-w-3xl` | 동일 ✓ |
| `app/admin/page.tsx` | 없음 | 관리자 전용, 우선순위 낮음 |
| `app/layout.tsx` | 없음 | 루트 레이아웃, Header/MobileNav 포함 ✓ |

### C. 테이블 / 가로 스크롤

테이블 사용 컴포넌트 **11개 전수 검사** → **모두 `overflow-x-auto` 래퍼 존재** ✓

| 파일 | overflow-x-auto 위치 |
|---|---|
| `components/strategy/ScreenerTable.tsx` | line 128 ✓ |
| `components/portfolio/PortfolioTable.tsx` | line 259 ✓ |
| `components/stocks/StockTable.tsx` | 래퍼 존재 ✓ |
| `components/validation/LeaderComparisonSection.tsx` | line 47 ✓ |
| `components/admin/NewsCategoryManager.tsx` | line 299 ✓ |
| `components/admin/NewsTab.tsx` | line 81, 124 ✓ |
| `components/admin/shared/TaskLogViewer.tsx` | line 123 ✓ |
| `components/admin/news/CollectionStatsTable.tsx` | line 40 ✓ |
| `components/admin/news/MLCompareView.tsx` | line 26 ✓ |
| `components/admin/ScreenerTab.tsx` | line 56, 111 ✓ |
| `components/admin/SystemTab.tsx` | line 72, 144, 288 ✓ |

→ **결론: 테이블 영역 BLOCKER 없음**. 다만 `ScreenerTable`은 다수 컬럼을 포함하고 있어 375px에서 좌우 스크롤 동작이 UX상 필수이므로 `MobileStockCard` 경로(아래 D) 유도가 핵심.

### D. 모바일 전용 대체 렌더 (조건부 분기)

| 화면 | 대체 뷰 | 전환 조건 | 결과 |
|---|---|---|---|
| `/screener` | `MobileStockCard` (카드 그리드) | `viewMode === 'card'` + `sm:hidden`/`sm:block` 결합 (line 845, 854) | 모바일에서 `ScreenerTable` 미렌더, 카드 그리드 노출 ✓ |
| `/chainsight/[symbol]` | `MobileCardList` + 그래프 오버레이 | `isMobile` 상태 (useState + useEffect matchMedia 추정) | 모바일 전용 풀스크린 리스트 뷰 ✓ (line 152-170) |
| `/chainsight` (메인) | — | 대체 없음 | **BLOCKER** — 유일하게 MarketGraphCanvas가 모바일에 그대로 노출 |
| `/portfolio` | `viewMode === 'grid'` + `PortfolioStockCard` | 사용자 토글 | 기본값 'grid'로 카드 노출. 단, `PortfolioTable` 자체 overflow-x-auto도 대비됨 ✓ |

---

## 터치 타겟

Apple HIG 기준 **44×44pt**. 아래는 클릭 가능한 요소이면서 유효 터치 높이가 44pt 미만인 사례 (실측: `p-*`, `py-*`, `h-*` 수치 + 내부 요소 합산).

### 핵심 위반 사례

| 심각도 | 파일:라인 | 클래스 | 유효 높이 | 근거 |
|---|---|---|---:|---|
| MAJOR | `components/thesis/builder/NewsSelector.tsx:142` | `p-1` on `<button>` 아이콘 | ~32px | 뒤로가기 버튼. p-1(4px) + 아이콘 ≈ 24px |
| MAJOR | `components/thesis/builder/PremiseCard.tsx:35` | `p-1` + `size={14}` | ~22px | 근거 카드 X(삭제) 버튼. 14 + 4×2 = 22px. 매우 작음 |
| MAJOR | `components/thesis/builder/OptionButton.tsx:72` | `hidden sm:flex p-1` | ~32px | `sm:` 이상에서만 노출되므로 모바일(375px = sm 미만) 무영향 ✓ — 실제 MINOR |
| MAJOR | `components/validation/PeerContextBar.tsx:40,54` | `px-3 py-1` | ~28px | 프리셋 탭 · "직접 설정" 토글. 피어 그룹 전환 트리거 |
| MAJOR | `components/thesis/dashboard/IndicatorRow.tsx:181-189` | `px-2.5 py-0.5` | ~22px | 차트 기간 선택 버튼 (1M/1Y/3Y/5Y). 패널 내부 4개 연속 배치 — 오터치 위험 |
| MAJOR | `components/eod/SignalFilterTabs.tsx:68` | `min-w-[18px] h-[18px] px-1` | 18px | 카운트 배지. 배지 자체가 클릭 영역은 아니고 부모 탭에 포함되나 시각적 겹침 |
| MAJOR | `components/eod/SignalCard.tsx` 카운트/태그 배지 | `px-2 py-0.5` | ~20px | 카드 내부 배지가 별도 클릭 핸들러 보유 시 위반 |
| MAJOR | `components/watchlist/WatchlistItemRow.tsx:116,126` | `p-1.5` | ~36px | 편집/삭제 아이콘. 목표 44px에 8px 부족 |
| MAJOR | `components/eod/SignalDetailSheet.tsx:188` | `text-[10px] px-1.5 py-0.5 cursor-pointer` | ~18px | **키워드 칩이 클릭 가능** (`cursor-pointer` 명시). 10px 폰트 + 14px 높이 — BLOCKER에 근접하나 부차 상호작용이라 MAJOR |
| MINOR | `components/thesis/common/AlertBell.tsx:18` | `min-w-[18px] h-[18px]` | 18px | 헤더 알림 배지, 부모 버튼에 포함되어 실질 영향 없음 |
| MINOR | `components/thesis/builder/OptionButton.tsx:52` | `min-h-[52px]` / `min-h-[56px]` | 52/56px | 빌더 메인 옵션 ≥ 44 HIG 충족 ✓ |

### 폰트 과소 사용

- `text-[10px]` / `text-[11px]`: **113 인스턴스** 전체 검색
  - 대부분 라벨/타임스탬프/배지(비상호작용) — MINOR
  - **상호작용 요소인 경우는 1건만 확인**: `SignalDetailSheet.tsx:188` (키워드 칩, `cursor-pointer` 명시) — 위 표 MAJOR로 반영

### 페이지별 터치 타겟 평가

| 페이지 | 주요 위반 | 심각도 |
|---|---|---|
| **thesis 관제실** (`/thesis/[thesisId]`) | IndicatorRow 차트 기간 버튼 `py-0.5` | MAJOR |
| **thesis 빌더** (`/thesis/new`) | PremiseCard 삭제 `p-1 size-14`, NewsSelector 뒤로 `p-1` | MAJOR |
| **validation** (stocks 상세 내장) | PeerContextBar 프리셋/직접 설정 `py-1` | MAJOR |
| **EOD Dashboard** | SignalDetailSheet 키워드 칩 클릭 10px | MAJOR |
| **screener** | `sm:hidden` 카드 경로로 우회. MobileStockCard 터치 영역 확인 필요(미조사) | MINOR |
| **chainsight** | force-graph 노드 터치 (react-force-graph-2d) — 커스텀 hit area `nodePointerAreaPaint` 있음 | MINOR |
| **news** | 카테고리 필터 아이콘 `p-1` 의심(미확인) | MINOR |

---

## 네비게이션

### 현재 구성

| 컴포넌트 | 역할 | 상태 |
|---|---|---|
| `components/layout/MobileNav.tsx` | 하단 고정 5탭 바, `h-16` (64px), `md:hidden`, `z-50` | ✓ OK — 터치 영역 64px, fixed bottom-0 |
| `components/layout/Header.tsx` | 데스크톱 네비 `hidden md:flex` + **모바일 햄버거 메뉴 구현됨** (line 156-255) | ✓ OK |
| `components/layout/InvestingHeader.tsx` | 투자 데스크톱 헤더 | **데드 코드** — 어디에도 import 안 됨, 실제 마운트되지 않음 |

### 세부 이슈

- **Header.tsx 햄버거는 완전 구현되어 있음** (line 156: 토글 버튼, line 165-255: 펼쳐지는 모바일 패널 + 9개 네비 링크 + 로그인/로그아웃 + 검색 입력). 2026-04-22 보고서의 "햄버거 미구현 BLOCKER"는 **오진**이었다.
- **MobileNav의 5개 탭이 Header의 9개 네비게이션과 부분적으로만 겹침** — MobileNav에는 Chain Sight, Thesis, Market Pulse, 스크리너가 없고 `/stocks`(HOME 대체), `/profile` 링크가 있음. `/profile`은 실제 존재하지 않는 경로(→ `/mypage`)로 보여 MAJOR 링크 오류 가능성. 실제 로딩 확인 필요.
- **MobileNav `md:hidden` 조건 + `z-50` + `bottom-0`**: Chain Sight force-graph 위에 항상 떠 있으나, `fixed` 포지션이라 그래프 하단을 가림. `/chainsight/[symbol]` 모바일 오버레이가 `z-50 fixed inset-0`이므로 그래프 모드에선 MobileNav가 가려짐 ✓.
- **BottomSheet 패턴 도입됨**: `components/thesis/common/BottomSheet.tsx`, `components/thesis/builder/BottomSheet.tsx` — 가설 빌더 옵션 선택/뉴스 선택에서 활용 (MINOR — 개별 구현 품질 미조사).

### 긴 목록 / virtualization

- `react-window` / `react-virtualized` / `@tanstack/react-virtual` **미사용** (node_modules에는 recharts가 내부 참조로만 사용).
- 대형 목록은 전부 pagination:
  - `ScreenerTable` — 페이지네이션
  - 뉴스, 알림, 가설 목록 — 서버 페이지네이션
- **현 규모(≤ 100건)에서는 문제 없음** (MINOR).
- `MarketGraphCanvas`(react-force-graph-2d): 수백 노드 구간에서 저성능 기기 랙 가능성 (MINOR).

---

## 차트/그래프

### Recharts

- **recharts 사용 컴포넌트 10개 전수 검사**: 모두 `ResponsiveContainer` 사용 ✓
  - `components/stock/StockChart.tsx`
  - `components/news/SentimentChart.tsx`
  - `components/portfolio/PortfolioChart.tsx`
  - `components/thesis/dashboard/IndicatorRow.tsx` (line 197, 235)
  - `components/thesis/dashboard/IndividualMiniCharts.tsx`
  - `components/admin/news/MLTrendChart.tsx`
  - `components/validation/MetricBarChart.tsx`
  - `components/screener/SectorHeatmap.tsx`
  - `components/macro/YieldCurveChart.tsx`
  - `components/charts/StockPriceChart.tsx`

### 분기 스파크라인

- `components/thesis/dashboard/QuarterlySparkline.tsx`: IndicatorRow 인라인에서 `flex-1 max-w-[100px]`로 렌더 (line 132).
  - 다른 인접 요소: `min-w-[60px]` 값 + `min-w-[120px]` 변동률 = 180px + 100px spark + 지지/반박 텍스트 → 370-380px에 근접.
  - 375px 화면에서 **margin 가시 영역이 2-3px로 줄어들 가능성** → 스파크라인 렌더 실패는 없으나 **각 tick이 ~25px 간격**이라 4분기 추이 판독이 어려움 (MINOR, UX 저하).

### Chain Sight 그래프

| 심각도 | 파일 | 이슈 |
|---|---|---|
| **BLOCKER** | `app/chainsight/page.tsx` + `components/chainsight/MarketGraphCanvas.tsx:114-145` | 메인 Chain Sight 페이지에서 `h-[400px] height={400}` 고정, 모바일 대체 뷰 없음 |
| MINOR | `components/chainsight/MobileCardList.tsx` | `/chainsight/[symbol]`에서만 `isMobile && !graphOverlay` 조건으로 렌더. 메인 페이지에선 사용 불가 |
| MINOR | `MarketGraphCanvas.tsx:118` | `width={containerRef.current?.clientWidth || 800}` — 초기 렌더 시 800 fallback이 잠시 사용되어 flash 가능 |

---

## 페이지별 상세

### `/` (홈, `app/page.tsx`)
- 심각도: 미확인 (이 감사에서 개별 분석 생략). Header + MobileNav 영향 받음.

### `/dashboard` (`app/dashboard/page.tsx`)
- 심각도: **MINOR**
- `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` + `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 적용 ✓.
- 내부 차트 ResponsiveContainer 사용 ✓.

### `/screener` (`app/screener/page.tsx`)
- 심각도: **MINOR**
- 표 뷰와 카드 뷰 `viewMode` 토글 + `sm:block`/`sm:hidden` 조합으로 모바일에서 자동으로 카드 뷰 노출 (line 845, 854) ✓.
- 검색/필터 bar의 모바일 대응은 개별 검사 필요 (미조사).

### `/portfolio` (`app/portfolio/page.tsx`)
- 심각도: **MINOR**
- `max-w-7xl` + `sm:px-6 lg:px-8` ✓.
- `PortfolioTable`은 `overflow-x-auto` 적용 ✓.
- 요약 카드 `grid-cols-2 md:grid-cols-3 lg:grid-cols-6` ✓.
- 모바일은 `viewMode='grid'` 기본으로 `PortfolioStockCard`가 우선 노출됨.

### `/chainsight` (메인)
- 심각도: **BLOCKER**
- `max-w-7xl mx-auto px-4 py-4 space-y-4`.
- `MarketGraphCanvas` `h-[400px]` 고정, `isMobile` 분기 없음.
- 하위 컴포넌트: `SectorBar`, `MarketGraphCanvas`, `ExplorationTrail`, `RelationCardPanel`, `ChainStoryFeed` — 모두 모바일 테스트 미흡 추정.

### `/chainsight/[symbol]` (`app/chainsight/[symbol]/page.tsx`)
- 심각도: **MINOR**
- `isMobile` 상태로 모바일에선 `MobileCardList`(카드 리스트) 전체 화면 노출 ✓.
- 그래프 확인 시 `graphOverlay` 토글로 `fixed inset-0 z-50` 풀스크린 오버레이로 렌더 ✓.
- 데스크톱에선 SplitPane (별도 레이아웃, 미조사).

### `/chainsight/watchlist`, `/chainsight/watchlist/[id]`
- 심각도: **MINOR**
- `max-w-3xl mx-auto px-4 py-6` — 768px 이하 캡, 모바일 적합 ✓.

### `/thesis` (가설 관제실 전체)
- 심각도: **MAJOR** (개별 페이지 합산)

| 하위 | 이슈 | 심각도 |
|---|---|---|
| `/thesis` (list) | `max-w-lg` layout — 모바일 최적 ✓ | MINOR |
| `/thesis/alerts` | 카드 기반, 무이슈 | MINOR |
| `/thesis/new` (빌더) | PremiseCard/NewsSelector 터치 타겟 22-32px | MAJOR |
| `/thesis/[thesisId]` (대시보드) | `max-w-lg` ✓, IndicatorRow 내 `min-w-[60/120px]` 조합 + 기간 버튼 22px | MAJOR |
| `/thesis/[thesisId]/indicators` | IndicatorRow 다수 나열 — 위 이슈 전파 | MAJOR |
| `/thesis/[thesisId]/close` | 단순 폼 | MINOR |

### `/validation` (stocks 상세 내장 섹션)
- 심각도: **MAJOR**
- 독립 페이지 아님 (`/stocks/[symbol]` 내 렌더).
- `PeerContextBar.tsx`의 프리셋 탭(`px-3 py-1`, line 40) + "직접 설정" 버튼(`px-3 py-1`, line 54): Peer 그룹 전환 API 트리거인데 높이 28px.
- `LeaderComparisonSection`: `overflow-x-auto` 적용 ✓.
- `SignalSummaryCard:40`: `min-w-[72px]` 각 시그널 — 72 × N이 375 초과 시 `overflow-x-auto pb-2 scrollbar-hide` 래퍼로 대응 ✓.

### `/stocks/[symbol]`
- 심각도: **MAJOR**
- `max-w-7xl` + `sm:px-6 lg:px-8` + `grid grid-cols-1 lg:grid-cols-2` ✓.
- `overflow-x-auto` 래퍼 다수 (line 843, 1030) ✓.
- validation/PeerContextBar 내장으로 터치 타겟 MAJOR 영향 받음.

### `/news`
- 심각도: **MINOR**
- 카드 기반, 카테고리 필터 아이콘 버튼 검사 부족.

### `/market-pulse`
- 심각도: 미확인 (이 감사에서 개별 분석 생략).

### `/mypage`
- 심각도: **MINOR** — prefix 전무이나 단순 폼.

### `/admin/*`
- 심각도: **MINOR** (관리자 전용)
- 모든 테이블에 `overflow-x-auto` 래퍼 확인 ✓ (8개 admin 파일 전수 조사).

### `/ai-analysis`, `/signup`, `/login`
- 심각도: 미확인, 단순 폼/상세 화면으로 추정.

### `/watchlist`
- 심각도: **MAJOR**
- `WatchlistItemRow.tsx:116,126`의 편집/삭제 아이콘 `p-1.5` (36px) — 44px 미달.

---

## 이전 감사 보정 (2026-04-22 보고서 오진 정정)

| 이전 BLOCKER 주장 | 실제 검증 결과 |
|---|---|
| `Header.tsx` 햄버거 미구현 | **오진** — line 156-255에 완전 구현됨 (토글 버튼 + 펼침 패널 + 9개 링크 + 검색) |
| `InvestingHeader.tsx` max-w-[1400px] 모바일 overflow | **부분 오진** — 해당 컴포넌트는 어디에도 import되지 않는 **데드 코드**. 실제 마운트되지 않음. 또한 `max-w`는 최대값 캡이므로 375px 뷰포트에서 overflow 원인이 아님 |
| `ScreenerTable.tsx` overflow 래퍼 없음 | **오진** — line 128에 `<div className="overflow-x-auto">` 명확히 존재 |
| `PortfolioTable.tsx` overflow 래퍼 없음 | **오진** — line 259에 `<div className="overflow-x-auto">` 존재 |
| `SignalDetailSheet.tsx:97` `md:w-[420px]` 모바일 overflow | **오진** — 같은 라인에 `w-full md:w-[420px]`로 모바일은 `w-full` 적용. 420px는 `md:` 이상에서만. 무영향 |
| admin/validation 테이블 overflow 미처리 7건 | **오진** — 8개 admin 파일과 validation `LeaderComparisonSection` 모두 `overflow-x-auto` 래퍼 존재 |
| `MobileCardList` 전환 조건 불분명 | **보정** — `app/chainsight/[symbol]/page.tsx:152`에서 `isMobile && !graphOverlay` 조건으로 명확히 분기 |

---

## 부록: 감사 방법 메모

- Grep: `w-\[\d+px\]`, `min-w-\[\d+px\]`, `max-w-\[\d+px\]`, `text-\[10px\]`, `text-\[11px\]`, `overflow-x-auto`, `ResponsiveContainer`, `sm:/md:/lg:/xl:`, `isMobile`, `md:hidden`, `hidden md:`.
- 주요 BLOCKER 후보는 실제 파일을 `Read`로 직접 열어 조건부 렌더 로직·래퍼 존재·dead code 여부까지 검증.
- 터치 타겟은 Tailwind `p-*`/`py-*`/`px-*`/`h-*` + 내부 아이콘 크기(`size={N}` 또는 `h-[Npx] w-[Npx]`) 합산 실측.
- 이전 감사(2026-04-22) 보고서의 BLOCKER 4건 중 3건이 **코드와 불일치**하여 오늘 보고서는 1차적으로 **정정**에 집중. 신규 이슈는 Chain Sight 메인 페이지 1건.

---

## 참고: 우선순위별 조치 권고 (감사자 의견, 구현 지시 아님)

- **P0 (BLOCKER 해소)**
  1. `app/chainsight/page.tsx` — `/chainsight/[symbol]`의 `isMobile` 분기 패턴을 메인 페이지에도 적용 (모바일에선 SectorBar + 카드형 관계 피드 + 그래프 오버레이 버튼으로).
- **P1 (MAJOR)**
  2. `components/thesis/builder/PremiseCard.tsx:35` — 삭제 버튼 `p-1 size={14}` → `p-2 size={18}` 검토 (22→40px).
  3. `components/thesis/builder/NewsSelector.tsx:142` — 뒤로가기 `p-1` → `p-2` (32→40px).
  4. `components/thesis/dashboard/IndicatorRow.tsx:181-189` — 기간 버튼 `py-0.5` → `py-1.5` (22→32px) + 간격 확대.
  5. `components/validation/PeerContextBar.tsx:40,54` — `py-1` → `py-2` (28→40px).
  6. `components/watchlist/WatchlistItemRow.tsx:116,126` — `p-1.5` → `p-2.5` (36→44px, HIG 충족).
  7. `components/eod/SignalDetailSheet.tsx:188` — 키워드 칩 `text-[10px] py-0.5` → `text-xs py-1` + 최소 폭 지정.
  8. `components/thesis/dashboard/IndicatorRow.tsx` 메인 행 레이아웃 — `min-w-[120px]`/`min-w-[60px]` 결합 재고 (모바일에서 줄 바꿈 허용 또는 스파크라인 접기).
  9. MobileNav `/profile` 링크가 유효한지 실측 필요 (`/mypage`로 교정해야 할 수 있음).
- **P2 (MINOR)**
  10. `MarketGraphCanvas` `h-[400px]` → `h-[60vh] sm:h-[400px]` 또는 모바일에서 `h-[50vh]` 대응.
  11. `InvestingHeader.tsx` 데드 코드 제거 (컴파일 부피·혼란 감소).
  12. 상호작용 요소의 `text-[10px]` 전수 재조사 (본 감사에서 `grep -E "button|onClick|cursor-pointer"`로 1건만 포착).
  13. `QuarterlySparkline`이 렌더되는 IndicatorRow 메인 행의 폭 예산(~100px)이 375px 환경에서 여유가 없음 — 분기 수 4 → 3 축약 또는 펼친 상태에서만 표시 고려.
