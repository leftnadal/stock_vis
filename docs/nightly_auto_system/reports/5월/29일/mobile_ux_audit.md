# 모바일 UX 감사 보고서

> **범위**: `frontend/` (205 컴포넌트, 30 페이지) 정적 코드 감사
> **기준 뷰포트**: 375px (iPhone SE/mini), Apple HIG 44×44pt 터치 타겟
> **방식**: 읽기 전용 정적 분석 (코드 미수정)
> **일자**: 2026-05-29
> **참고**: 코드 내 `audit P0 #12/#13` 주석으로 보아 이전 1차 모바일 감사가 일부 수행됨 — 본 보고서는 그 후속 정밀 감사

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 |
|--------|------|------|
| 🔴 **BLOCKER** | **3** | `/stocks` 라우트 404, 하단 nav 콘텐츠 가림(폼 CTA), 모바일 글로벌 네비 데드코드 |
| 🟠 **MAJOR** | **5** | 모바일 네비 도달 불가 8개 섹션, pinch-zoom 차단(a11y), coach 12-col 입력행, market 그래프 모바일 대안 부재, 작은 터치 타겟(차트 기간 선택) |
| 🟡 **MINOR** | **4** | text-[10px]/[11px] 가독성, min-w 고정폭 행 압착, 일부 버튼 py-0.5/py-1.5, JS 기반 isMobile 분기 깜빡임 |

**총평**: 차트(Recharts ResponsiveContainer 14/14)·테이블 가로스크롤·일부 핵심 화면(chainsight 상세, screener)의 모바일 분기는 **양호**하다. 그러나 **전역 레이아웃 수준의 구조적 결함 3건**(라우트 404 / 하단 nav 가림 / 모바일 네비 데드코드)이 모바일 사용성의 근간을 흔든다. 개별 컴포넌트보다 `app/layout.tsx`·`Header.tsx`·`MobileNav.tsx` 트리오의 정합성 문제가 우선순위 1순위.

---

## 1. 반응형 누락

### 고정 폭 사용 현황 (31건)
대부분 `max-w-[NNpx]`(상한선 — overflow 유발 안 함)이라 **안전**. 위험한 `min-w`/`w-` 고정폭만 분석:

| 파일 | 클래스 | 375px 영향 | 심각도 |
|------|--------|-----------|--------|
| `thesis/dashboard/IndicatorRow.tsx:110,115` | `min-w-[60px]` + `min-w-[120px]` | 값+변동률+스파크라인(max-100)+지지/반박이 한 행(`pl-4`, 부모 `px-4`). 가용 ~311px 중 고정분 180px+gap. 스파크라인 `flex-1`로 흡수되나 **타이트** | 🟡 MINOR |
| `chainsight/MarketGraphCanvas.tsx:676` | `w-[110px] min-h-[68px]` | 인기 섹터 버튼 3개 `flex-wrap` → 375px에서 자동 래핑, overflow 없음 | ✅ 안전 |
| `common/DataSourceBadge.tsx:171` | `min-w-[200px]` 팝오버 | 절대위치 툴팁 — 화면 가장자리서 잘릴 수 있음 | 🟡 MINOR |
| `eod/SignalDetailSheet.tsx:97` | `w-full md:w-[420px]` | 모바일 full-width, 데스크톱만 고정 → **모범 사례** | ✅ 안전 |
| `layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` | 컨테이너 상한, 안전 (단 InvestingHeader는 미사용 추정 — 글로벌은 Header.tsx) | ✅ 안전 |

→ **고정폭으로 인한 실제 overflow 위험은 낮음.** 대부분 `max-w`+`truncate` 또는 `flex-wrap`으로 방어됨.

### 브레이크포인트 분포
- 전체 사용: `sm:` 115회, `md:` 65회, `lg:` 68회, `xl:` 7회
- **브레이크포인트 0개 페이지** (CSS 미디어쿼리 없음): admin, chainsight(4개), coach/e4, thesis(5개) 등 10개
- **단, 상당수는 "의도된 모바일 우선 단일 컬럼"**:
  - `thesis/[thesisId]/page.tsx`: `max-w-lg mx-auto px-4 pt-4 pb-20` → 512px 고정 단일 컬럼 = 모바일 우선 설계 (브레이크포인트 불필요)
  - `chainsight/*`: CSS 대신 **JS `isMobile` 분기**로 전혀 다른 레이아웃 렌더 (아래 §1-3)

### JS 기반 반응형 (`isMobile`/`useMediaQuery`) — 7개 파일
`chainsight/[symbol]/page.tsx`, `stocks/[symbol]/page.tsx`, `MarketGraphCanvas.tsx`, `screener/PresetGallery.tsx`, `validation/CategorySection.tsx` 등.
- **장점**: 모바일/데스크톱 완전 분리 레이아웃 가능 (chainsight 상세가 대표적 우수 사례)
- **단점**: SSR 시 `isMobile=false`(또는 초기값)로 렌더 → 클라이언트 hydration 후 레이아웃 점프(깜빡임) 발생 가능. CSS 미디어쿼리와 달리 FOUC 위험. → 🟡 MINOR

### 테이블 가로 스크롤 — **양호**
`overflow-x-auto`가 29개 파일에 적용. 핵심 테이블 전부 래핑됨:
- `strategy/ScreenerTable.tsx:128` ✅
- `stocks/StockTable.tsx` ✅ / `portfolio/PortfolioTable.tsx` ✅
- 스크리너는 한 단계 더: **`hidden sm:block` 데스크톱 테이블 + 모바일 `MobileStockCard` 카드 분기** (screener/page.tsx:845-857) → **모범 사례**

### 가상화(virtualization) — **전무**
`react-window`/`@tanstack/react-virtual` 등 **사용 0건**. 긴 목록(뉴스, peer 종목, 그래프 노드 리스트, 스크리너 결과)이 전건 DOM 렌더. 모바일 저사양 기기에서 수백 행 시 스크롤 버벅임 가능. → 데이터량 적으면 무방, 대량 목록 화면은 🟡 MINOR(향후 부채).

---

## 2. 터치 타겟 (Apple HIG 44×44pt)

### ✅ 44px 보장된 컴포넌트 (이전 감사 반영분)
`min-h-[44px]`/`min-w-[44px]` 명시 13개 파일 — MobileNav, Header(숨김 버튼), `validation/PeerContextBar`(프리셋 탭), `screener/Pagination`, `admin/AdminTabNav`, `strategy/ScreenerTable`(링크), `chainsight/MobileCardList`, `thesis/builder/*` 등. **프리셋 탭·페이지네이션·스크리너 등 사용자가 명시 지목한 영역은 이미 44px 충족.**

### 🟠 / 🟡 미달 터치 타겟

| 위치 | 클래스 | 추정 높이 | 심각도 |
|------|--------|----------|--------|
| `thesis/dashboard/IndicatorRow.tsx:182` 차트 기간 선택(1M/1Y/3Y/5Y) | `px-2.5 py-0.5 text-[10px]` | ~18–20px | 🟠 MAJOR (지표 카드 핵심 인터랙션) |
| `chainsight/[symbol]/page.tsx:254,268,278` Depth/필터/패널 버튼 | `px-3 py-1.5` | ~30px | 🟡 MINOR (데스크톱 헤더, 모바일선 isMobile 분기로 미노출) |
| `chainsight/[symbol]/page.tsx:211-223` 모바일 바텀시트 탐색/가설/검증 | `py-2 text-xs` | ~32px | 🟡 MINOR (flex-1로 폭은 충분, 높이만 부족) |
| `validation/PeerContextBar.tsx:85` "적용" 버튼, 커스텀 입력 | `py-1.5 text-xs` | ~28px | 🟡 MINOR |
| `coach/e1~e6` 종목 입력행 `+`/삭제, 인풋 | `px-2 py-1.5 text-sm` | ~30px | 🟠 MAJOR (§5 참조) |

> **사용자 지목 3개소 점검 결과**:
> - **thesis 관제실 지표 카드** → 행 전체가 `<button>`(큰 타겟)이라 토글은 양호하나, **펼친 후 기간 선택 버튼이 18px로 심각하게 작음** 🟠
> - **validation 프리셋 탭** → `min-h-[44px]` + `flex-wrap` 적용 완료 ✅
> - **chainsight 노드** → 그래프 노드는 force-graph 캔버스(터치 픽 반경 별도), 바텀시트 액션은 32px 🟡

### 작은 텍스트
- `text-[10px]`/`text-[11px]`: thesis IndicatorRow(날짜·변동률 라벨·전제·차트축·기간버튼), chainsight(섹터 시드수·툴팁), PeerContextBar 안내문 등 다수
- `text-xs`(12px): 42+건 (클릭 요소 라벨에 광범위 사용)
- **§3의 pinch-zoom 차단과 결합 시** 저시력·고령 사용자 가독성 저하 → 🟡 MINOR (단독), 🟠 (zoom 차단과 복합)

---

## 3. 모바일 네비게이션

### 🔴 BLOCKER A — `/stocks` 인덱스 라우트 404
`MobileNav.tsx:13`의 "종목" 탭이 `/stocks`로 링크하나 **`app/stocks/page.tsx`가 존재하지 않음** (`app/stocks/[symbol]/`만 존재). 모바일 하단 nav 5개 중 1개(종목)가 **탭 시 404**.
→ 즉시 수정 필요: `app/stocks/page.tsx` 생성 또는 nav href를 실존 라우트(`/screener` 등)로 변경.

### 🔴 BLOCKER B — 고정 하단 nav가 콘텐츠 가림
`app/layout.tsx`: `<main className="min-h-screen">` (하단 패딩 없음) + `<MobileNav>` (`fixed bottom-0 h-16 md:hidden z-50`, 64px).
- **30개 페이지 중 `pb-*`로 nav 높이를 확보한 페이지는 단 2개** (`app/page.tsx`, `thesis/[thesisId]/page.tsx` — `pb-20`).
- **나머지 26개 페이지**: 콘텐츠 하단 64px가 고정 nav에 영구히 가려짐.
- **치명적 사례**: 페이지 최하단에 CTA가 오는 폼 — `login`, `signup`, `thesis/new`, `coach/e1~e6` 제출 버튼, `mypage` 등이 **하단 nav에 가려 탭 불가** → 핵심 플로우 차단.
→ 수정: `<main>`에 `pb-16 md:pb-0` 추가(전역 일괄 해결) 또는 각 페이지 `pb-20`.

### 🔴 BLOCKER C — Header 모바일 네비 데드코드
`Header.tsx`:
- 데스크톱 nav(`hidden md:flex`), 검색바(`hidden md:block`), 유저 액션(`hidden md:flex`) → 모바일에서 전부 숨김.
- 햄버거 버튼이 `className="hidden inline-flex …"` (157-163행) → **영구 `hidden`**. 따라서 `isMenuOpen` 토글 불가.
- 결과: **모바일 드롭다운 메뉴(167-257행, ~90줄)는 절대 열리지 않는 데드코드.** 모바일에서 Header는 **로고만** 표시.
→ 주석(155행)은 "MobileNav가 단일 소스"라며 의도적이라 설명하나, MobileNav가 5개 섹션만 커버하므로 아래 MAJOR D 문제를 유발.

### 🟠 MAJOR D — 모바일에서 8개 섹션 글로벌 도달 불가
모바일 네비(하단 MobileNav)는 **홈/종목/뉴스/포트폴리오/내정보 5개만** 노출. Header 데스크톱 nav가 가진 다음 섹션은 모바일 글로벌 네비에서 **도달 경로 없음**:
- **chainsight, thesis(Thesis Control), market-pulse, screener** (Header 데스크톱엔 있음)
- **ai-analysis, coach(E1~E6), watchlist, admin** (어느 글로벌 nav에도 없음)
→ 인-콘텐츠 링크나 직접 URL로만 접근 가능. 신규 모바일 사용자는 핵심 기능(스크리너·가설·체인사이트) 발견 불가. → BLOCKER C의 데드코드를 살리거나 MobileNav에 "더보기" 메뉴 추가 필요.

### Bottom navigation 존재 여부
✅ **존재** (`MobileNav`, 하단 고정, 44px 타겟, `aria-label`, active 상태). 구조 자체는 우수 — 라우트(BLOCKER A)와 커버리지(MAJOR D)만 문제.

---

## 4. 차트/그래프 모바일 대응

### Recharts ResponsiveContainer — **14/14 전건 사용 ✅**
`StockPriceChart`, `StockChart`, `PortfolioChart`, `SentimentChart`, `YieldCurveChart`, `MLTrendChart`, `SectorHeatmap`, `MetricBarChart`, `thesis/IndividualMiniCharts`, `thesis/IndicatorRow`, market-pulse-v2 detail 4종 — **모두 `width="100%"`**. 가로 반응형 완비.
- 높이는 고정값(`height={140~560}`)이나 모바일에서 허용 범위.
- 축 폰트 `fontSize={9~10}` — 375px에서 빽빽하나 `interval` 동적 샘플링(IndicatorRow:208,249)으로 라벨 겹침 방어. ✅

### 분기 스파크라인 모바일 가독성
- `thesis/dashboard/QuarterlySparkline.tsx`: `min-h-[44px]` 적용, 인라인은 최근 4분기만(`slice(-4)`) → 좁은 폭 대응. ✅
- 펼침 시 전체 분기 AreaChart는 ResponsiveContainer 100%. ✅

### Market 관계 그래프 (force-graph) — 🟠 MAJOR
- `MarketGraphCanvas.tsx`: `width={containerWidth}`(`el.clientWidth` 측정, 반응형 ✅) + `height={560}`.
- **chainsight 인덱스 페이지(`app/chainsight/page.tsx`)는 모바일에서도 동일 force-graph를 그대로 렌더** — 375px 폭에 수십 노드 표시 시 노드 라벨 판독·터치 픽 난이도 높음. (상세 페이지 `[symbol]`은 `MobileCardList`+오버레이로 잘 분기되나, **인덱스 시장 그래프엔 모바일 카드 대안 없음**.)
→ 인덱스 그래프에도 상세 페이지처럼 모바일 카드/리스트 폴백 권장.

---

## 5. 페이지별 상세

| 페이지 | 모바일 대응 | 주요 이슈 | 심각도 |
|--------|------------|----------|--------|
| `app/layout.tsx` (전역) | — | **main에 pb 없음 → 하단 nav가 26개 페이지 콘텐츠 가림** / viewport `userScalable=false, maximumScale=1` (pinch-zoom 차단, WCAG 1.4.4 위반) | 🔴 / 🟠 |
| `Header.tsx` | 로고만 노출 | 햄버거 영구 hidden → 모바일 메뉴 데드코드, 검색 비기능(`TODO`, console.log) | 🔴 |
| `MobileNav.tsx` | 하단 고정 ✅ | `/stocks` 404, 5개 섹션만 커버 | 🔴 / 🟠 |
| `app/page.tsx` (홈) | `pb-20` ✅ | 양호 | ✅ |
| `app/thesis/[thesisId]` (관제실) | `max-w-lg` 모바일우선 + `pb-20` ✅ | 차트 기간 선택 버튼 18px, text-[11px] 다수 | 🟠 / 🟡 |
| `app/thesis/(list)`, `/new`, `/close`, `/indicators` | 단일 컬럼 | **pb 없음 → 폼 CTA 가림 위험** | 🔴(B) |
| `app/chainsight/[symbol]` (상세) | **isMobile 분기 + MobileCardList + 그래프 오버레이 + 바텀시트** | 모범 사례 ✅ / 바텀시트 버튼 32px / pb 없음 | ✅ / 🟡 |
| `app/chainsight` (인덱스) | force-graph 그대로 | 모바일 카드 폴백 없음, 그래프 375px 빽빽 | 🟠 |
| `app/screener` | **테이블 hidden sm:block + MobileStockCard 카드 분기** ✅ | 뷰 토글이 `hidden sm:flex`(모바일 강제 카드, 동작은 정상) / pb 없음 | ✅ / 🔴(B) |
| `app/stocks/[symbol]` | isMobile + validation 탭 | overflow-x ✅ / pb 없음 | 🔴(B) |
| `app/coach/e1~e6` | `max-w-4xl` | **종목 입력행 `grid-cols-12` 비반응형** (col-span-3/2/2/2/2 인풋이 375px서 ~60px로 압착·overflow) / 인풋 py-1.5(~30px) / pb 없음 | 🟠 / 🔴(B) |
| `app/portfolio` | PortfolioTable overflow-x ✅ | pb 없음 | 🔴(B) |
| `app/news` | — | 모바일 테이블 분기 미확인, pb 없음 | 🔴(B) |
| `app/login`, `/signup` | 폼 | **제출 버튼 하단 nav 가림 위험**, pb 없음 | 🔴(B) |
| `app/mypage`, `/watchlist`, `/dashboard`, `/market-pulse(-v2)`, `/ai-analysis`, `/admin` | 부분적 | pb 없음 공통 / admin은 브레이크포인트 0(데스크톱 전용 성격) | 🔴(B) / 🟠 |

---

## 권장 수정 우선순위

1. **🔴 [전역, 1줄] `app/layout.tsx`의 `<main>`에 `pb-16 md:pb-0`** → 26개 페이지 하단 가림 + 폼 CTA 차단 일괄 해결 (BLOCKER B). *가장 높은 ROI.*
2. **🔴 `MobileNav` "종목" href 수정 또는 `app/stocks/page.tsx` 생성** → 404 제거 (BLOCKER A).
3. **🔴/🟠 Header 햄버거 `hidden` 해제 + 드롭다운 부활**(또는 MobileNav "더보기" 추가) → 8개 섹션 도달성 복구 (BLOCKER C / MAJOR D).
4. **🟠 `layout.tsx` viewport `userScalable: true`, `maximumScale` 제거** → 접근성(WCAG 1.4.4) + 데이터 밀집 화면 확대 허용.
5. **🟠 thesis IndicatorRow 기간 버튼 / coach 입력행** 터치 타겟·반응형 보강 (`py-0.5`→`min-h-[40px]`, `grid-cols-12`→`grid-cols-1 sm:grid-cols-12`).
6. **🟠 chainsight 인덱스 그래프** 모바일 카드 폴백 추가 (상세 페이지 패턴 재사용).
7. **🟡** text-[10px]/[11px] 가독성, JS isMobile FOUC, 대량 목록 가상화는 후속 부채로 관리.

---

## 부록 — 감사 방법론 (재현용)

```bash
# 고정폭
grep -rnE "w-\[[0-9]+px\]|min-w-\[[0-9]+px\]|max-w-\[[0-9]+px\]" frontend/{components,app} --include='*.tsx'
# 작은 텍스트
grep -rnE "text-\[1[01]px\]" frontend/{components,app} --include='*.tsx'
# Recharts 반응형
grep -rln "recharts" … ; grep -rln "ResponsiveContainer" …
# 페이지별 브레이크포인트/하단패딩
for f in $(find frontend/app -name 'page.tsx'); do grep -cE "(sm|md|lg):" "$f"; grep -oE "pb-(16|20)" "$f"; done
# 터치 타겟
grep -rln "min-h-\[44px\]|min-w-\[44px\]" … ; grep -rnE "<button[^>]*py-(0\.5|1)\b" …
# 가상화
grep -rln "react-window|useVirtual|@tanstack/react-virtual" …   # → 0건
```

*본 감사는 정적 코드 분석 기반이며, 실기기 렌더링 검증(브라우저 375px 뷰포트)으로 overflow·가림 현상을 최종 확인할 것을 권장.*
