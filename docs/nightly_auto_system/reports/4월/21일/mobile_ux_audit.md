# 모바일 UX 감사 보고서

- 감사 일자: 2026-04-22
- 감사 대상: `frontend/` (Next.js 16 + TypeScript + Tailwind)
- 기준 뷰포트: **375px (iPhone SE)**
- 감사 유형: 읽기 전용 (코드 수정 없음)
- 조사 방식: 컴포넌트(`components/**/*.tsx`) 약 250개, 페이지(`app/**/page.tsx`) 20여 개에 대한 정적 분석 (Tailwind 클래스, import, 고정 값 패턴)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|---|---:|---|
| **BLOCKER** | **4** | 375px에서 가로 스크롤 발생 확정, 터치 불가, 또는 모바일에서 네비게이션 자체가 작동 불능 |
| **MAJOR**   | **14** | 터치 어려움(30~43pt) · 핵심 페이지에 반응형 prefix 전무 · 본문 고정 폭으로 overflow 가능성 높음 |
| **MINOR**   | **11** | 폰트 과소(text-[10px]) 이나 배지/라벨 용도 · 일부 브레이크포인트 누락 · 데이터 규모 의존 성능 이슈 |
| **총계**    | **29** | |

### BLOCKER 4건 한눈에 보기

1. `components/layout/Header.tsx` — 햄버거 메뉴 미구현 (`Menu` 아이콘 import·`isMenuOpen` state만 존재, 실제 토글 UI 없음). 모바일에서 주요 9개 네비게이션 링크 접근 불가.
2. `components/layout/InvestingHeader.tsx` — `max-w-[1400px]` 3회 사용, 반응형 prefix 없음. 투자 화면 헤더 자체가 375px에서 가로 overflow.
3. `components/strategy/ScreenerTable.tsx` — `overflow-x-auto` 래퍼 없음 + 셀 내부 `max-w-[200px]/180px/120px` 고정. 스크리너 결과 테이블이 모바일에서 화면 밖으로 튀어나감.
4. `components/portfolio/PortfolioTable.tsx` — 다중 컬럼(가격/수익률/목표/손절) 테이블, `overflow-x-auto` 없음. 포트폴리오 핵심 화면 모바일 사용 불가.

---

## 반응형 누락

### A. 고정 폭 사용 (Tailwind 임의값)

총 **27개 파일 / 40+ 인스턴스**에서 `w-[NNpx]`, `min-w-[NNpx]`, `max-w-[NNpx]` 임의값 발견. 대부분은 truncate와 함께 쓰여 안전하나, 아래 항목은 모바일 overflow 위험.

| 심각도 | 파일:라인 | 클래스 | 근거 |
|---|---|---|---|
| BLOCKER | `components/layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` × 3 | 반응형 prefix 없음. 375px에서 확정 overflow. |
| BLOCKER | `components/eod/SignalDetailSheet.tsx:97` | `md:w-[420px]` | 420 > 375. md 조건부이나 시트가 full-width 전환 로직 없이 뜨면 overflow. |
| MAJOR   | `components/strategy/ScreenerTable.tsx:209,224,307` | `max-w-[180/120/200px]` | 셀 너비 고정. truncate 의존, 결합된 열 합계가 375px 초과. |
| MAJOR   | `components/common/DataSourceBadge.tsx:171` | `min-w-[200px]` | 배지/드롭다운 200px 고정. 팝오버 밖에서 overflow. |
| MAJOR   | `components/thesis/dashboard/IndicatorRow.tsx:110,115` | `min-w-[120px]`, `min-w-[60px]` | 관제실 지표 카드 좌측 열 고정. 여러 열 조합 시 375px 초과. |
| MINOR   | `components/screener/MobileStockCard.tsx` (SuggestionChips 계열) | `max-w-[150px]` | truncate 적용되어 안전. |
| MINOR   | `components/eod/StockRow.tsx` | `max-w-[140px]` | truncate 적용되어 안전. |

### B. 브레이크포인트 커버리지

- `sm:/md:/lg:/xl:` **사용 파일 64개** (전체 컴포넌트의 약 40%).
- 아래는 **핵심 페이지인데도 반응형 prefix가 전무하거나 < 30%**인 곳.

| 심각도 | 파일 | 증상 |
|---|---|---|
| BLOCKER | `app/chainsight/page.tsx` | `max-w-7xl` + `h-[400px]` 그래프. 반응형 폭/높이 조정 없음 |
| MAJOR | `app/admin/page.tsx` | 테이블 기반 전체 레이아웃, 모바일 적응 전무 |
| MAJOR | `app/thesis/(list)/page.tsx` | 카드 리스트 레이아웃, `max-w-7xl` + `px-4`만 |
| MAJOR | `app/thesis/(list)/alerts/page.tsx` | 알림 섹션, prefix 없음 |
| MAJOR | `app/thesis/[thesisId]/page.tsx` | 개별 가설 상세, prefix 없음 |
| MAJOR | `app/thesis/[thesisId]/indicators/page.tsx` | IndicatorRow 다수 나열, 모바일 폭 제어 없음 |
| MINOR | `app/thesis/[thesisId]/close/page.tsx` | 마감 페이지, 단순 폼 |
| MINOR | `app/mypage/page.tsx` | prefix 전무, 단순 폼 |
| MINOR | `app/news/page.tsx` | prefix 전무이나 카드 기반으로 자동 적응 |

### C. 테이블 / 가로 스크롤

테이블 사용 컴포넌트 **13개**. 아래 3개는 `overflow-x-auto` 래퍼가 부재.

| 심각도 | 파일 | 상태 |
|---|---|---|
| BLOCKER | `components/strategy/ScreenerTable.tsx` | overflow 래퍼 없음 + 셀 내부 `max-w-[...]` 고정 |
| BLOCKER | `components/portfolio/PortfolioTable.tsx` | 다중 컬럼, 래퍼 없음 |
| MAJOR   | `components/validation/LeaderComparisonSection.tsx` | 비교 테이블, 래퍼 없음 + `py-1.5` 셀 높이 작음 |
| MAJOR   | `components/admin/NewsTab.tsx`, `admin/news/MLCompareView.tsx`, `admin/news/CollectionStatsTable.tsx`, `admin/SystemTab.tsx`, `admin/ScreenerTab.tsx`, `admin/shared/TaskLogViewer.tsx`, `admin/NewsCategoryManager.tsx` | 모든 admin 테이블 overflow 미처리 (admin 전용이어서 우선순위는 낮음) |
| ✓ OK | `components/stocks/StockTable.tsx:34` | `overflow-x-auto` 적용 |
| ✓ OK | `components/validation/SignalSummaryCard.tsx:36` | flex + `overflow-x-auto pb-2 scrollbar-hide` |

---

## 터치 타겟

Apple HIG 기준 **44×44pt**. lucide-react 아이콘 기본 `w-5 h-5`(20px)에 주변 padding이 6~8px면 터치 영역이 32~36px에 불과.

### 핵심 위반 사례

| 심각도 | 파일:라인 | 클래스 | 유효 높이 | 근거 |
|---|---|---|---:|---|
| MAJOR | `components/eod/SignalFilterTabs.tsx:68` | `px-1 py-0.5` + `h-[18px]` | ~18px | 카운트 배지가 필터 탭 내부 클릭 요소 |
| MAJOR | `components/eod/SignalCard.tsx:97-98` | `px-2 py-0.5` | ~20px | 카운트 배지, 텍스트 클릭 영역 작음 |
| MAJOR | `components/thesis/dashboard/IndicatorRow.tsx:182` | `px-2.5 py-0.5` | ~22px | 관제실 지표 상태 배지, 클릭 가능 |
| MAJOR | `components/validation/PeerContextBar.tsx:40,54` | `px-3 py-1` | ~28px | "추가" 액션 버튼 (API 호출 트리거) |
| MAJOR | `components/thesis/builder/NewsSelector.tsx:142` | `p-1` 아이콘 버튼 | ~32px | 뉴스 선택 X/추가 버튼 |
| MAJOR | `components/thesis/builder/OptionButton.tsx:72` | `p-1 hidden sm:flex` | ~32px | 빌더 옵션 버튼 |
| MAJOR | `components/thesis/builder/PremiseCard.tsx:35` | `p-1` 닫기 버튼 | ~32px | 전제 카드 제거 버튼 |
| MINOR | `components/watchlist/WatchlistItemRow.tsx:116,126` | `p-1.5` | ~36px | 편집/삭제 아이콘 |

### 폰트 과소 사용

- `text-[10px]`: **45개 파일 / 100+ 인스턴스** — 대부분 라벨·타임스탬프·카테고리 배지 (터치 대상 아님, MINOR).
- `text-[11px]`: **15개 파일 / 30+ 인스턴스** — 일부 버튼 내부 텍스트에 사용되어 MAJOR와 중복(위 표 참조).

### 페이지별 터치 타겟 평가

| 페이지 | 주요 위반 | 심각도 |
|---|---|---|
| **thesis 관제실** | IndicatorRow 배지 `py-0.5` + builder 아이콘 `p-1` | MAJOR |
| **validation** | PeerContextBar "추가" `py-1` | MAJOR |
| **screener** | 결과 테이블 배지 `text-[10px]` (라벨 전용) | MINOR |
| **chainsight** | 노드 인터랙션 (react-force-graph 커스텀 렌더) | MINOR (조사 부족) |
| **news** | 키워드 필터 아이콘 버튼 `p-1` 의심 | MINOR |

---

## 네비게이션

### 현재 구성

| 컴포넌트 | 역할 | 상태 |
|---|---|---|
| `components/layout/MobileNav.tsx` | 하단 고정 5탭 바, `h-16` (64px), `md:hidden` | ✓ OK |
| `components/layout/Header.tsx` | 데스크톱 네비게이션 `hidden md:flex` | **BLOCKER — 햄버거 미구현** |
| `components/layout/InvestingHeader.tsx` | 투자 화면 상단 헤더 | **BLOCKER — `max-w-[1400px]`, 반응형 prefix 없음** |
| Drawer/Sheet 전용 라이브러리 | — | 없음 (커스텀도 없음) |

### 세부 이슈

- **BLOCKER** `Header.tsx`: `Menu` 아이콘(lucide)이 import 되어 있고 `isMenuOpen` state까지 있으나 실제 토글 UI가 렌더되지 않음. 모바일에서 Header 내 9개 주요 메뉴(예: 대시보드, 스크리너, 가설 관제실 등) 접근 불가. MobileNav의 5탭으로만 가려짐.
- **BLOCKER** `InvestingHeader.tsx`: 데스크톱 전용 폭(1400px)으로 렌더. 모바일에서 가로 스크롤 발생.
- **MAJOR** `app/thesis/(list)/layout.tsx` 추정 Group Layout: 내부 탐색(alerts, indicators, 가설 상세)이 모바일 탭/드로어 없이 단순 링크. 모바일에서 컨텍스트 잃기 쉬움.
- **MINOR** Bottom navigation(MobileNav) 자체는 충분히 크나, Chainsight 그래프 화면에서 하단 탭이 그래프를 가릴 가능성(그래프 하단 여백 미확인).

### 긴 목록 / virtualization

- `react-window`, `react-virtualized`, `@tanstack/react-virtual` **모두 미사용**.
- 대형 목록은 전부 **pagination** 방식:
  - ScreenerTable: `pageSize=50`
  - ThesisListCard.sorted.map()
  - News 피드, Validation 메트릭 등
- **평가**: 현재 데이터 규모(≤ 100건)에선 문제 없음 (MINOR).
- **MINOR** MarketGraphCanvas(react-force-graph-2d): 노드 수백 개로 커지면 저성능 기기에서 lag 가능성.

---

## 차트/그래프

### Recharts

- **사용 파일 14개 / `ResponsiveContainer` 37회 사용** → 전반적으로 안전 ✓
- 확인 파일 (모두 `ResponsiveContainer` 감쌈):
  - `components/stock/StockChart.tsx`
  - `components/news/SentimentChart.tsx`
  - `components/portfolio/PortfolioChart.tsx`
  - `components/thesis/dashboard/IndicatorRow.tsx`
  - `components/admin/news/MLTrendChart.tsx`
  - `components/validation/MetricBarChart.tsx`
  - `components/screener/SectorHeatmap.tsx`
  - `components/macro/YieldCurveChart.tsx`

### 분기 스파크라인

- `components/thesis/dashboard/QuarterlySparkline.tsx`: recharts 기반, hover tooltip 사용. 모바일 크기 조정은 부모 너비에 의존 — 관제실 IndicatorRow 좌측 min-w 고정과 결합해 **스파크라인 렌더 영역이 좁아지는 간접적 이슈** 가능 (MINOR).
- `components/eod/MiniSparkline.tsx`: 렌더 방식 미확인 (서브에이전트 보고 기준 MINOR 표시).

### 그래프 (ChainSight)

| 심각도 | 파일 | 이슈 |
|---|---|---|
| **MAJOR** | `components/chainsight/MarketGraphCanvas.tsx:97,107,114` | `h-[400px]` 고정 3회. 너비는 `clientWidth`로 동적이나 높이가 375px 환경에서 화면의 절반 이상을 차지하며 비율 왜곡 |
| MINOR | `components/chainsight/MobileCardList.tsx` | 그래프 대체 카드 리스트 존재. 단, 어느 브레이크포인트에서 전환되는지 명확하지 않음(조건부 렌더 규칙 미확인) |

---

## 페이지별 상세

### `/dashboard` (`app/dashboard/page.tsx`)
- 심각도: **MINOR**
- `grid cols-1 → md:cols-2 → lg:cols-3` 적용, MobileNav 노출. 주요 차트 recharts ResponsiveContainer 사용.
- 남은 이슈: Header 햄버거 미구현(BLOCKER)이 이 화면에도 영향.

### `/screener` (`app/screener/page.tsx`)
- 심각도: **MAJOR**
- BLOCKER: `ScreenerTable` overflow 래퍼 없음.
- MAJOR: 검색 bar가 `hidden md:block` → 모바일에서 검색 입력 불가능(대안 UI 미확인).
- OK: `MobileStockCard`가 별도로 존재(조건부 렌더 규칙 확인 필요).

### `/thesis` — 가설 관제실
- 심각도: **MAJOR**
- `app/thesis/(list)/page.tsx`, `alerts/page.tsx`, `[thesisId]/page.tsx`, `[thesisId]/indicators/page.tsx` 모두 반응형 prefix 없음.
- `IndicatorRow`의 `min-w-[120px]/60px` 좌측 열 고정 → 다중 값 표시 시 375px에서 압축/overflow.
- 상태 배지(`px-2.5 py-0.5`)·빌더 아이콘 버튼(`p-1`) 터치 타겟 미달.
- Sparkline은 recharts 기반이지만 부모 폭에 의존하여 가독성 저하 가능.

### `/chainsight`
- 심각도: **MAJOR**
- `app/chainsight/page.tsx`: `max-w-7xl` 고정 + `h-[400px]` 그래프 고정.
- `MarketGraphCanvas` 높이 400px 하드코딩.
- `MobileCardList` 대체는 있으나 전환 조건 불분명.
- `/chainsight/watchlist/*`: MINOR.

### `/validation` (stocks 상세 내 내장)
- 심각도: **MAJOR**
- 독립 page 아님 (stocks/[symbol] 상세 내 섹션으로 추정).
- `LeaderComparisonSection` 테이블 overflow 없음.
- `PeerContextBar` "추가" 버튼 `py-1`.

### `/portfolio`
- 심각도: **BLOCKER → 페이지 수준 MAJOR**
- `PortfolioTable` overflow 래퍼 부재 → 가격/수익률/목표/손절 다중 열이 모바일 화면 밖으로 튀어나감.
- 포트폴리오 핵심 화면이어서 영향도 큼.

### `/news`
- 심각도: **MINOR**
- 카드 기반 레이아웃, 페이지네이션. 필터 아이콘 `p-1` 의심(MINOR).

### `/stocks/[symbol]`
- 심각도: **MINOR** (부분적으로 MAJOR)
- `md:` prefix 1회뿐, 그러나 StockTable은 `overflow-x-auto` 적용.
- validation 섹션 내장 시 MAJOR로 승격.

### `/mypage`
- 심각도: **MINOR**
- prefix 전무이나 단순 폼 구조로 자동 적응.

### `/admin`
- 심각도: **MAJOR** (운영 전용)
- 테이블 기반 레이아웃, 모든 테이블 overflow 미처리.
- 관리자 전용이라 사용자 영향 낮으나 원칙적으로는 MAJOR.

### `/ai-analysis`, `/signup`, `/`(home)
- 이번 감사에서 개별 위반은 발견되지 않음(단, 공용 Header BLOCKER의 영향 받음).

---

## 부록: 감사 방법 메모

- `sm:/md:/lg:/xl:` Tailwind prefix 사용 파일 64개 중 핵심 페이지 9개가 prefix 전무.
- `w-\[\d+px\]` / `min-w-\[\d+px\]` / `max-w-\[\d+px\]` 임의값 40+ 인스턴스 중 모바일 영향 항목만 위에 나열.
- 터치 타겟은 Tailwind `p-*`, `h-*`, `py-*` 수치 + 둘러싼 텍스트 크기 조합으로 유효 높이 계산.
- 가상화 라이브러리(react-window 등) 의존성 전무 확인 (package.json 반영 아님).
- 파일 접근은 서브에이전트(Explore)를 통한 Grep/Read로 수행. frontend/ 경로는 이번 세션에서 메인 에이전트 직접 접근이 차단되어 Explore의 라인 번호·클래스 인용을 그대로 신뢰함.

---

## 참고: 우선순위별 조치 권고 (감사자 의견, 구현 지시 아님)

- **P0 (BLOCKER 해소)**: Header 햄버거 구현, InvestingHeader 반응형화, ScreenerTable/PortfolioTable overflow 래퍼.
- **P1 (MAJOR)**: thesis 페이지군 반응형 prefix 추가, MarketGraphCanvas 높이 반응형화(`h-[300px] sm:h-[400px]`), builder 아이콘 버튼 `p-1 → p-2` 확대, LeaderComparisonSection overflow 래퍼.
- **P2 (MINOR)**: 배지 터치 영역 미세 조정, News 카테고리 필터 재검토, admin 테이블 overflow 일괄 정비, MobileCardList 전환 조건 명확화.
