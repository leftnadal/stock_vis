# 모바일 UX 감사 보고서

> **생성일**: 2026-05-20
> **대상**: Stock-Vis Frontend (`/frontend/`)
> **기준 뷰포트**: iPhone SE / 13 mini 기준 **375px** width
> **터치 타겟 기준**: Apple HIG **44×44pt**
> **모드**: 읽기 전용 감사 (코드 수정 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|--------|------|------|
| **BLOCKER** | **4** | 375px에서 핵심 기능 사용 불가 / 페이지 도달 자체가 막힘 |
| **MAJOR** | **9** | 사용 가능하나 사용성 크게 저하 (가로 스크롤 강제, 텍스트 잘림, 메뉴 누락) |
| **MINOR** | **7** | 시각적 불편 / 가독성 저하 (기능은 정상) |
| **합계** | **20** | |

### 한 줄 결론

> 헤더·MobileNav·MobileStockCard·ResponsiveContainer 등 **모바일 기본기는 잡혀 있으나**, ① **MobileNav 메뉴에 Chainsight·Thesis·MarketPulse·Screener 4개 핵심 페이지가 빠져 있고**, ② **비로그인 사용자의 모바일 로그인 진입점이 사라지며**, ③ **재무제표·관제실 지표 카드 등 핵심 데이터 UI에서 < 32px 터치 타겟과 가로 스크롤 강제가 빈발**한다. 4개의 BLOCKER가 모두 모바일 신규 사용자의 첫 인상을 망치는 지점에 몰려 있다.

---

## 1. 반응형 누락

### 1-1. 재무제표 테이블 (BLOCKER)
- **파일**: `app/stocks/[symbol]/page.tsx:843-844`
- **현상**: `<div className="overflow-x-auto">` + `<table className="min-w-full">` 구조. 항목 컬럼 + 6~8개 분기 컬럼 = **약 900px 최소 폭**. 375px에서 사용자는 가로 스크롤로 모든 컬럼을 훑어야 함.
- **모바일 카드 대안 없음**. Screener에는 `MobileStockCard`가 있는데 재무제표에는 동등한 모바일 뷰가 없음.
- **심각도**: **BLOCKER** (개인 투자자의 핵심 기능)

### 1-2. ScreenerTable 가로 스크롤 (MAJOR)
- **파일**: `components/strategy/ScreenerTable.tsx:128`, `app/screener/page.tsx:845-846`
- **현상**: 11개 이상 컬럼, 컬럼당 80~100px → 총 900px+. 데스크톱 뷰는 `hidden sm:block`으로 안전하게 숨겨지지만, **sm 브레이크포인트는 640px**라서 ~640px에서 ~768px 사이 작은 태블릿 가로 / 큰 폰 가로에서는 어색하게 노출됨.
- **MobileStockCard**가 카드 대안으로 잘 구현되어 있음 (긍정).

### 1-3. L2 탭 네비게이션 (MINOR)
- **파일**: `app/stocks/[symbol]/page.tsx:403`
- **현상**: `<nav className="flex space-x-6">` 탭 라벨이 모바일에서 줄바꿈/스크롤 처리 없이 잘릴 수 있음.

### 1-4. 메트릭 그리드 - 우측 (MINOR)
- **파일**: `app/stocks/[symbol]/page.tsx:329`
- **현상**: `grid grid-cols-2 gap-4` — 모든 화면 폭에서 2열 고정. 메트릭 라벨 길어지면 잘림 발생, `truncate` 미적용.

### 1-5. FearGreedGauge 고정 폭 (MAJOR)
- **파일**: `components/macro/FearGreedGauge.tsx:54`
- **현상**: `relative w-48 h-24` (192×96px). 320px 이하 단말기에서 좌우 패딩 합치면 오버플로우 위험. `max-w-full` 누락.

### 1-6. PortfolioChart / SectorHeatmap 고정 높이 (MINOR)
- **파일**: `components/portfolio/PortfolioChart.tsx:77,97`, `components/screener/SectorHeatmap.tsx:216`
- **현상**: `height={400}` 고정. 폭은 ResponsiveContainer로 안전하지만, 모바일 작은 폰의 세로 절반 이상을 차지. 핀치 줌 없이는 라벨 식별 어려움.

### 1-7. 우수 사례 (참고)
- `MobileStockCard.tsx`: `flex-1 min-w-0` + `truncate` + `grid-cols-3 gap-2` — 모범 사례.
- `app/thesis/new/page.tsx:672,715`: `grid-cols-1 gap-3 sm:grid-cols-2` — 적절한 모바일 우선 그리드.
- `components/chainsight/SectorBar.tsx:24,41`: `flex gap-2 overflow-x-auto` + `max-w-[120px]` 트렁케이션 — 올바른 가로 스크롤 패턴.

---

## 2. 터치 타겟

### 2-1. 관제실 지표 카드 토글/삭제 버튼 (BLOCKER)
- **파일**: `components/thesis/indicators/IndicatorSetupCard.tsx:49-68`
- **현상**: Power / Trash2 아이콘 버튼이 `p-2` + `size={16}` ≈ **32×32px**. 삭제는 파괴적 작업이므로 44pt 미만은 오탭 리스크.
- **심각도**: **BLOCKER** — 잘못 누르면 지표 손실.

### 2-2. 알림 "읽음" 버튼 (BLOCKER)
- **파일**: `components/thesis/alerts/AlertCard.tsx:57-63`
- **현상**: `text-[10px] px-2 py-1` ≈ **세로 18~20px**. 10px 폰트 + 좁은 패딩.
- **심각도**: **BLOCKER** — 알림 목록 핵심 액션인데 정밀 탭 필요.

### 2-3. 차트 기간 선택자 1M/1Y/3Y/5Y (MAJOR)
- **파일**: `components/thesis/dashboard/IndicatorRow.tsx:178-190`
- **현상**: `px-2.5 py-0.5 text-[10px]` ≈ **20px 높이**, `gap-1.5`로 4개 버튼이 밀집. 인접 오탭 빈발 예상.

### 2-4. 알림 필터 탭 (MAJOR)
- **파일**: `components/thesis/alerts/AlertFilterTabs.tsx:21-31`
- **현상**: `px-3 py-1.5 text-xs` ≈ **24px 높이**. 전체/안읽음/읽음 3개 탭이 좁음.

### 2-5. 대시보드 헤더 아이콘 버튼 (MAJOR)
- **파일**: `components/thesis/dashboard/DashboardPageHeader.tsx:19-39`
- **현상**: 뒤로가기(ArrowLeft) / 새로고침(RefreshCw) `p-1` + `size={20/16}` ≈ **24~28px**. 뒤로가기는 좌상단 엄지 도달 어려움 + 작은 타겟의 이중고.

### 2-6. Screener Pagination (MINOR-MAJOR)
- **파일**: `components/screener/Pagination.tsx:94-158`
- **현상**: `p-1.5` + 아이콘 16~20px ≈ **28~32px**. 페이지 이동 컨트롤은 44pt 권장.

### 2-7. IndicatorSetupCard 타입/방향 뱃지 (MINOR)
- **파일**: `components/thesis/indicators/IndicatorSetupCard.tsx:36-44`
- **현상**: 비인터랙티브 뱃지지만 활성 버튼과 시각적으로 인접해 오탭 유발.

---

## 3. 네비게이션

### 3-1. MobileNav 메뉴 항목 누락 (MAJOR)
- **파일**: `components/layout/MobileNav.tsx`, `components/layout/Header.tsx:42`
- **현상**: 데스크톱 헤더에는 있고 모바일 하단 nav에서 **누락된 페이지**:
  - **Chain Sight** ✗
  - **Thesis Control** ✗
  - **Market Pulse** ✗
  - **Screener** ✗
- 모바일 사용자는 핵심 기능 4개에 **딥링크 외에는 접근할 방법이 없음**.
- 추가로 MobileNav에는 `/stocks` 진입점이 있는데 **`/stocks` 루트 페이지 자체가 존재하지 않음** (`app/stocks/[symbol]`만 있음) → 404 또는 빈 화면 위험.

### 3-2. 비로그인 사용자 모바일 로그인 버튼 부재 (BLOCKER)
- **파일**: `components/layout/Header.tsx:125-153,160`
- **현상**: 로그인/회원가입 링크가 `hidden md:flex` 안에만 있음. 모바일 햄버거는 `hidden` (P0 감사 fix 주석 라인 155-156). MobileNav는 인증된 사용자 가정 항목만 노출 → **모바일에서 비로그인 신규 방문자가 로그인 페이지로 가는 명시적 진입점이 없음**.
- **심각도**: **BLOCKER** — 신규 가입 깔때기 자체가 차단됨.

### 3-3. List Virtualization 부재 (MAJOR)
- **파일**: `frontend/package.json`, `components/strategy/ScreenerTable.tsx:54-93`, `app/screener/page.tsx:162`, `app/thesis/(list)/page.tsx:36-44`
- **현상**: `react-window` / `@tanstack/react-virtual` / `react-virtual` 모두 **의존성 없음**. Screener는 전체 stocks 배열을 메모리 정렬 후 페이지네이션 (페이지 단위 렌더는 OK). Thesis 목록은 가상화 없이 전체 렌더. 500~1000개 종목이 페이지당 들어가는 시나리오에서 모바일 스크롤 jank 가능.

### 3-4. Bottom Navigation 자체는 모범 (PASS)
- **파일**: `components/layout/MobileNav.tsx:20-34`
- `fixed bottom-0 left-0 right-0 ... md:hidden z-50`, `h-16` (64px), 항목별 `min-h-[44px]` 보장. 콘텐츠는 `pb-20 md:pb-0`로 안전한 여백 확보.

---

## 4. 차트/그래프

### 4-1. Chainsight Force-Graph 풀스크린 강제 (MAJOR)
- **파일**: `app/chainsight/[symbol]/page.tsx:117,173-196`, `components/chainsight/GraphMiniView.tsx:30-33,110-115`
- **현상**: `window.innerWidth < 768` 감지 후 모바일에서는 그래프가 **풀스크린 오버레이**로만 열림. 다른 본문 정보와 동시에 보기 불가 → 연쇄 발견(Chain Sight DNA) UX의 핵심인 "맥락 비교"가 모바일에서 망가짐. 또한 `height=360` 고정.

### 4-2. FearGreedGauge 모바일 오버플로우 (MAJOR)
- (반응형 누락 1-5와 동일 이슈)

### 4-3. Recharts ResponsiveContainer는 전반적 양호 (PASS)
- `StockChart.tsx:177-187`: 윈도우 폭 기반 동적 높이 계산 — 모범.
- `SentimentChart.tsx:79-80` (h-80), `YieldCurveChart.tsx:92` (h-64), `MetricBarChart.tsx:72` (w-full h-48): 모두 ResponsiveContainer 사용.
- `MiniSparkline.tsx:9-62`: 순수 SVG 80×24, 의도된 비인터랙티브.

### 4-4. 차트 터치 인터랙션 미검증 (MINOR)
- Recharts Tooltip은 hover 기반 — 터치 디바이스에서는 long-press 또는 첫 탭만 유지되는 등 비일관적. 코드에서 별도 터치 핸들러 없음. 정확한 행동은 실기기 테스트 필요.

---

## 페이지별 상세

### `/` (`app/page.tsx`)
- **MINOR**: 비로그인 사용자가 첫 화면에서 MobileNav만 보면 로그인 진입점이 막힘 → 3-2 BLOCKER로 연결.
- **PASS**: `pb-20 md:pb-0`로 bottom nav 회피 여백 안전.

### `/dashboard` (`app/dashboard/page.tsx`)
- **MAJOR**: EOD Dashboard에 14개 시그널 카드. 각 카드의 IndicatorRow에서 기간 선택자 20px 높이 (2-3 참조).
- **MINOR**: MiniSparkline 80×24, 의도된 디자인.

### `/stocks/[symbol]` (`app/stocks/[symbol]/page.tsx`)
- **BLOCKER**: 1-1 재무제표 테이블 가로 스크롤 + 모바일 대안 없음.
- **MINOR**: 1-3 L2 탭, 1-4 메트릭 그리드, 4-4 차트 툴팁 터치.

### `/screener`
- **MAJOR**: 1-2 sm 브레이크포인트 경계 (640~768px) 어색함, 2-6 Pagination 작은 버튼, 3-3 가상화 없음.
- **PASS**: MobileStockCard 모범 구현.

### `/thesis/*` (가설 통제실)
- **BLOCKER**: 2-1 지표 토글/삭제 버튼 32px, 2-2 알림 읽음 버튼 18~20px.
- **MAJOR**: 2-3 기간 선택자, 2-4 알림 필터 탭, 2-5 헤더 아이콘.
- **MAJOR**: 3-1 MobileNav에서 진입 불가.

### `/chainsight/*`
- **MAJOR**: 4-1 풀스크린 강제로 연쇄 발견 UX 손상, 3-1 MobileNav에서 진입 불가.
- **PASS**: SectorBar 가로 스크롤 + 트렁케이션.

### `/market-pulse`, `/market-pulse-v2`
- **MAJOR**: 3-1 MobileNav 누락. FearGreedGauge 1-5/4-2 오버플로우.
- **MINOR**: YieldCurveChart h-64는 양호.

### `/news`
- **PASS**: MobileNav에 있음. SentimentChart ResponsiveContainer 사용.

### `/portfolio`, `/watchlist`, `/mypage`
- **MINOR**: PortfolioChart h-400 고정으로 작은 폰에서 세로 공간 압박.

### `/login`, `/signup`
- **BLOCKER 연결**: 3-2 — 모바일에서 이 페이지로 가는 진입점 자체가 없음.

### `/admin`
- 데스크톱 전용 가정으로 분류 (관리자 페이지) — 본 감사 범위 외.

---

## 권장 우선순위 (참고용, 코드 변경은 별도 PR)

1. **MobileNav 메뉴 확장** + 비로그인 로그인 버튼 노출 (BLOCKER 1건 + MAJOR 1건 해소)
2. **재무제표 모바일 카드 뷰** 추가 (BLOCKER 해소, MobileStockCard 패턴 재활용)
3. **관제실 지표/알림 터치 타겟 44pt 이상** 일괄 상향 (BLOCKER 2건 해소)
4. **Chainsight 모바일 그래프**를 풀스크린 → 하단 슬라이드업 시트로 (연쇄 발견 UX 보존)
5. **FearGreedGauge `max-w-full`** 1줄 fix
6. (장기) Screener / Thesis 목록에 `@tanstack/react-virtual` 도입 검토

---

## 부록 — 감사 방법

- 4개 영역 (반응형, 터치, 네비, 차트) 병렬 read-only 탐색
- Tailwind 임의값 (`w-[NNpx]`, `min-w-`, `text-[NNpx]`), 브레이크포인트 prefix (`sm:`/`md:`/`lg:`), Recharts `ResponsiveContainer` 사용 여부를 grep
- 파일 경로:라인 수준에서 추적 (실기기/스크린샷 검증은 본 감사 범위 외)
- 코드는 일절 수정하지 않음
