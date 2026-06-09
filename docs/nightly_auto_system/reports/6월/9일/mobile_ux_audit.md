# 모바일 UX 감사 보고서

> **작성일**: 2026-06-09
> **대상**: `frontend/` (Next.js 16 / Tailwind / 컴포넌트 205개 · 페이지 30개)
> **기준 뷰포트**: 모바일 375px (iPhone SE/mini), 터치 기준 Apple HIG 44×44pt
> **성격**: 읽기 전용 정적 감사 (코드 변경 없음). 실기기 렌더 측정이 아닌 소스 정적 분석 기반 → "추정" 표기 항목은 실기기 검증 필요.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 |
|--------|------|------|
| 🔴 **BLOCKER** | 2 | ① 모바일 하단 네비 `종목→/stocks` 라우트 부재(404 추정) ② Chain Sight·Thesis·Market Pulse·Screener 모바일 네비 진입점 전무 |
| 🟠 **MAJOR** | 6 | Chain Sight 메인 그래프 모바일 폴백 없음 / hover-only 툴팁 다수 / coach E1~E6 12컬럼 그리드 미붕괴 / 입력 높이 44pt 미만 / `text-[10px]` 정보 과다 / 분기 스파크라인 인라인 가독성 |
| 🟡 **MINOR** | 7 | 검증 카테고리 사이드바 버튼 높이 / SignalSummaryCard 가로 스크롤 / 고정폭 truncate 다수 / 노드 칩 / 푸터 미세 텍스트 등 |

**총평**: 반응형 인프라(테이블 `overflow-x-auto` 래핑, Recharts `ResponsiveContainer`, MobileStockCard·MobileCardList 폴백)는 **상당 부분 갖춰져 있음**. 그러나 **모바일 1차 동선(네비게이션)에 치명적 단절**이 있고, **터치 환경에서 동작하지 않는 hover-only 패턴**과 **44pt 미만 미세 텍스트/입력**이 광범위하게 분포한다. 데스크톱 우선으로 설계된 화면(coach, chainsight 메인, 검증)이 모바일 미대응 잔존.

---

## 반응형 누락

### 잘 처리된 것 (확인됨)
- **테이블 가로 스크롤**: 발견된 `<table>` 12곳 대부분 `overflow-x-auto` 래퍼 보유 — `ScreenerTable`(strategy), `StockTable`(stocks), `PortfolioTable`, `watchlist/page`, `stocks/[symbol]/page:843`, admin 계열(`SystemTab`/`NewsTab`/`ScreenerTab`/`NewsCategoryManager`/`TaskLogViewer`/`CollectionStatsTable`/`MLCompareView`), `LeaderComparisonSection`. → 모바일에서 테이블이 잘려도 가로 스크롤로 접근 가능.
- **차트**: `StockPriceChart`/`StockChart`/`PortfolioChart`/`SectorHeatmap`/`YieldCurveChart`/`SentimentChart` 등 15개 차트가 `ResponsiveContainer width="100%"` 사용 → 폭 반응형 확보.
- **반응형 폴백 컴포넌트 존재**: `screener/MobileStockCard`(스크리너), `chainsight/MobileCardList`(체인사이트 상세) — 모바일 전용 카드 뷰로 분기.

### 고정 폭 사용 컴포넌트 (overflow 위험 분석)

| 컴포넌트 | 고정폭 클래스 | 375px 영향 | 심각도 |
|----------|--------------|-----------|--------|
| `layout/InvestingHeader.tsx:32,55,99` | `max-w-[1400px]` | `mx-auto`로 컨테이너 상한일 뿐, overflow 없음 | OK |
| `chainsight/MarketGraphCanvas.tsx:712,760` | `h-[560px]` 고정 높이 캔버스 | 모바일 세로 화면 절반 점유, 노드 10~20px | 🟠 MAJOR |
| `chainsight/MarketGraphCanvas.tsx:676` | `w-[110px] min-h-[68px]` (섹터 칩) | flex-wrap 처리되어 줄바꿈 OK | OK |
| `thesis/dashboard/IndicatorRow.tsx:110,115,132` | `min-w-[60px]`+`min-w-[120px]`+`max-w-[100px]` 한 행 | 60+120+100+gap ≈ 300px+값/라벨 → 375px에서 **타이트, 스파크라인 압착** | 🟠 MAJOR |
| `validation/SignalSummaryCard.tsx:41` | `min-w-[72px]` × N개 가로 배열 | `overflow-x` 동반(41행 인접) → 가로 스크롤 발생 | 🟡 MINOR |
| `rag/ChatInterface.tsx:198` | `h-[52px] w-[52px]` 전송 버튼 | 고정이지만 44pt 초과라 적절 | OK |
| `eod/SignalDetailSheet.tsx:97` | `w-full md:w-[420px]` | 모바일 `w-full` 분기 처리됨 | OK |
| `common/DataSourceBadge.tsx:171` | `min-w-[200px]` 팝오버 | 375px 내 수용, 단 위치 오프셋 확인 필요 | 🟡 MINOR |
| `max-w-[NNpx] truncate` 다수 (`ScreenerTable` 180/120/200, `NodeTooltip` 130, `SectorBar` 120, `eod/StockRow` 140, `RecommendationCard` 150, `SuggestionChips` 150) | 텍스트 말줄임 | overflow는 없으나 모바일에서 정보 잘림 누적 | 🟡 MINOR |

### 브레이크포인트 없이 데스크톱 전용인 레이아웃
- **`coach/e1~e6/page.tsx`**: 입력 행이 `grid grid-cols-12`인데 `sm:`/`md:` 분기 없음 → 375px에서도 12분할 유지. ticker/비중/액션 입력이 한 줄에 압착됨. (e1:150, e2:164, e3:178, e5:201, e6:181) 🟠 MAJOR
- **`validation/CategorySidebar.tsx`**: `sticky top-24` 세로 사이드바 — 모바일에서 스택 시 본문 위 차지. 데스크톱 2열 가정 레이아웃 추정. 🟡 MINOR
- **`/chainsight` 메인 페이지**: `MarketGraphCanvas`만 렌더, 모바일 카드 폴백 분기 없음(상세 `[symbol]` 페이지와 대조). 🟠 MAJOR

### 테이블/차트 가로 스크롤 처리
- 테이블: 대부분 OK(위 참조). **예외 없음 확인** — 신규 테이블 추가 시 `overflow-x-auto` 래퍼 누락 주의.
- 차트: `ResponsiveContainer` 일관 사용으로 폭 OK. 단 내부 축 `width={55}`(StockChart:672,765) 고정 → 좁은 폭에서 플롯 영역 축소.

---

## 터치 타겟 (HIG 44×44pt)

### 양호 (의도적으로 44pt 보장한 흔적)
- `layout/MobileNav.tsx`: 하단 탭 `h-16`(64px) + `min-h-[44px]` — **모범 사례**.
- `screener/Pagination.tsx:127`: `min-w-[44px] min-h-[44px]`.
- `strategy/ScreenerTable.tsx:323`, `layout/Header.tsx:160`(단 hidden), `validation/SignalSummaryCard.tsx:41`: `min-h-[44px] min-w-[44px]` 명시.
- `chainsight/MarketGraphCanvas.tsx:676`: 섹터 칩 `min-h-[68px]`.

### 44pt 미만 터치 영역 / 미세 텍스트 클릭 요소

| 위치 | 문제 | 심각도 |
|------|------|--------|
| **`text-[10px]`/`text-[11px]` 클릭·정보 요소 광범위 분포** | grep 기준 **60+개소**. 특히 클릭 가능한 것: `IndicatorRow.tsx:182`(차트 기간 버튼 `px-2.5 py-0.5 text-[10px]` ≈ 높이 20px), `thesis/alerts/AlertCard.tsx:57`(닫기 버튼 `text-[10px]`), `chainsight/RelationLegend.tsx:59`(토글 `text-[10px]`), `chainsight/MobileCardList.tsx:149-159`(배지) | 🟠 MAJOR |
| **thesis 관제실 지표** — `IndicatorRow.tsx` | 행 전체가 `<button>`이라 탭 영역은 충분(행 높이 OK). 그러나 펼침 후 일간 기간 버튼(182행) `py-0.5`=2px 패딩 → 탭 높이 ≈20px. 사용자 지목 영역 중 **본체는 OK, 내부 컨트롤만 미달** | 🟠 MAJOR |
| **validation 프리셋/카테고리 탭** — `CategorySidebar.tsx:48` | 버튼 `px-3 py-2 text-sm` → 높이 ≈34~36px (44pt 미달). 사용자 지목 "프리셋 탭"에 해당하는 별도 프리셋 셀렉터는 미발견(프리셋 로직은 `PeerContextBar`/스크리너에 분산) | 🟡 MINOR |
| **chainsight 노드** — `MarketGraphCanvas.tsx:66` | `NODE_SIZE_MAP = {xl:20, lg:17, md:14, sm:10}` — 그래프 SVG 노드 10~20px. 487행에서 `pointer:coarse` 감지 분기는 있으나 노드 자체 히트박스가 작아 **터치 정밀 탭 어려움**. 상세 페이지는 `MobileCardList` 폴백으로 회피하나 메인 페이지는 그래프 직접 노출 | 🟠 MAJOR |
| `keywords/KeywordTag.tsx:42` | `sm` 사이즈 `px-2 py-0.5 text-[10px]` 클릭 태그 → 높이 ≈20px | 🟡 MINOR |
| `eod/SignalDetailSheet.tsx:188,197` | `text-[10px]` 클릭 가능한 관련 종목/링크 칩 | 🟡 MINOR |

---

## 네비게이션

### 🔴 BLOCKER ① — 하단 네비 `종목` 탭 라우트 부재
`MobileNav.tsx:13` → `{ name:'종목', href:'/stocks' }`. 그러나 `frontend/app/stocks/`에는 `[symbol]/page.tsx`만 존재하고 **`/stocks/page.tsx`가 없음** → `/stocks` 진입 시 **404 추정**. 모바일 1차 탭이 깨진 라우트를 가리킴.
> 비교: 같은 파일 주석에 과거 `/profile`→`/mypage` 수정 이력 있음(P0 #12). 동일 유형 잔존 버그.

### 🔴 BLOCKER ② — 모바일에서 주요 섹션 도달 불가
- `MobileNav`는 5개 탭만: **홈 / 종목 / 뉴스 / 포트폴리오 / 내정보**.
- `Header.tsx`의 데스크톱 nav에는 **Chain Sight / Thesis Control / Market Pulse / Screener**가 있으나 `hidden md:flex`로 모바일 숨김.
- `Header.tsx:157-163` 햄버거 버튼은 주석대로 **`hidden`(영구 비표시)** 처리됨 ("MobileNav가 단일 소스"). 그 결과 모바일 사용자는 **Chain Sight·Thesis·Market Pulse·Screener로 이동할 네비 수단이 전혀 없음**(딥링크/외부 진입만 가능).
> 이중 네비 제거 자체는 합리적이나, MobileNav 5탭에 누락 섹션이 빠지면서 **도달성(reachability) 회귀** 발생.

### 모바일 네비 구조 (확인)
- 하단 고정 탭바: `fixed bottom-0 ... md:hidden z-50` — 존재 ✅ (Bottom navigation 구현됨).
- 데스크톱: 상단 `Header` 인라인 nav.
- **이중 네비 충돌 없음**(햄버거 hidden) — 단 위 BLOCKER ②의 도달성 문제 상존.
- `aria-label` 부여됨(MobileNav Link, Header 검색/메뉴) — 접근성 기본 양호.

### Virtualization (긴 목록)
- `react-window`/`react-virtuoso` 등 가상화 라이브러리 **미발견**. 스크리너/뉴스/관제실 지표 등 장문 목록이 전체 DOM 렌더 추정 → 모바일 저사양 기기에서 스크롤 성능 저하 가능. (정량 측정 필요) 🟡 MINOR

---

## 차트/그래프

### Recharts ResponsiveContainer 사용 현황
- **사용 확인 15개 파일**: `charts/StockPriceChart`, `stock/StockChart`, `portfolio/PortfolioChart`, `screener/SectorHeatmap`, `macro/YieldCurveChart`, `news/SentimentChart`, `validation/MetricBarChart`, `thesis/dashboard/IndicatorRow`·`IndividualMiniCharts`, `admin/news/MLTrendChart`, `market-pulse-v2/details/*`(Breadth/Flow/Regime/Sector) 등.
- 모두 `width="100%"` → 폭 반응형 확보. **차트 폭 overflow 위험 낮음**.
- 다만 `height={400}`(PortfolioChart), `h-[560px]`(MarketGraphCanvas) 등 **고정 높이**는 모바일 세로에서 과점유. 🟡 MINOR

### 분기 스파크라인 모바일 가독성
- `thesis/dashboard/QuarterlySparkline.tsx`: 라벨 `text-[11px]`, 툴팁 `text-[10px]` + **hover-only 툴팁**(`group-hover` 의존, 62행) → **터치 기기에서 분기별 수치 확인 불가**. 🟠 MAJOR
- `IndicatorRow.tsx:132`: 인라인 스파크라인 `max-w-[100px]`로 압착 + 최근 4분기만 표시 → 모바일에서 추세 식별 어려움. 🟠 MAJOR

### Canvas 그래프 (Chain Sight)
- `MarketGraphCanvas`: `pointer:coarse` 감지(487행) 분기 존재하나, **고정 `h-[560px]` + 소형 노드 + 메인 페이지 카드 폴백 부재** 3중으로 모바일 부적합. 상세 페이지(`[symbol]`)는 `isMobile && window.innerWidth<768` → `MobileCardList`로 회피하나 **메인 `/chainsight`는 미적용**. 🟠 MAJOR

### Hover-only 패턴 (터치 미동작) — 횡단 이슈
터치 기기는 hover가 없어 아래 정보가 **노출 불가**:
- `market-pulse/MoverCard.tsx:138~189` + `MoverCardWithBatchKeywords.tsx:145~196`: `group-hover/tooltip:block` 설명 툴팁 5종.
- `keywords/KeywordTag.tsx:90`: 키워드 설명 hover 툴팁.
- `thesis/dashboard/QuarterlySparkline.tsx:62`: 분기 수치 hover 툴팁.
- `thesis/builder/OptionButton.tsx:66`: "꾹 누르면 설명"(long-press 안내 — 일부 대응) — sm:hidden으로 모바일 한정 안내, 그나마 양호.
> 권고(보고용): hover 의존 정보는 탭/long-press 토글 또는 상시 노출로 전환 필요.

---

## 페이지별 상세

### `/` (홈), `/dashboard`
- `dashboard/page.tsx`에 `md:hidden`/`hidden md:` 분기 존재 → 반응형 의식 설계. 차트 ResponsiveContainer 사용. 양호.

### `/stocks/[symbol]` (종목 상세)
- 재무 테이블 `overflow-x-auto` 래핑(843행) ✅. `StockChart` ResponsiveContainer ✅.
- `md:hidden`/`hidden md:` 분기 존재. 비교적 양호. (단 `/stocks` 인덱스 부재 → BLOCKER ① 참조)

### `/screener` (스크리너)
- **반응형 모범 사례**: 데스크톱 `ScreenerTable` + 모바일 `MobileStockCard` 분기(846/857행). MobileStockCard는 `grid-cols-3` 지표 + 44pt 미달 미세 라벨(`text-[10px]` 시총/PER/거래량) 존재하나 카드 자체는 탭 가능. 🟡 라벨만 MINOR.
- `AdvancedFilterPanel`: `text-[10px]` 설명/카운트 배지 다수 → 가독성 MINOR.
- `PresetGallery`: `grid-cols-2 md:grid-cols-3 ...` 반응형 ✅, 단 순번 배지 `w-5 h-5 text-[10px]`.

### `/chainsight` (메인)
- 🟠 그래프 캔버스 직접 노출, 모바일 카드 폴백 없음. h-[560px] 고정. 섹터 칩은 44pt+ 양호.

### `/chainsight/[symbol]` (관계 상세)
- ✅ `isMobile`(innerWidth<768) 감지 → `MobileCardList` 폴백(152행). 그래프 오버레이도 `width={window.innerWidth}` 대응(189행). **모범 사례**.

### `/thesis/[thesisId]` (관제실 대시보드)
- `IndicatorRow` 행 전체 탭 가능(양호). 단 한 행에 `min-w-[60px]+min-w-[120px]+max-w-[100px]` 압착 → 375px 타이트. 펼침 후 기간 버튼 `py-0.5`(≈20px) 44pt 미달.
- `text-[11px]`/`text-[10px]` 정보 밀집(설명/관계/전제). 모바일 가독성 🟠.
- 분기 스파크라인 hover 툴팁 터치 미동작 🟠.

### `/thesis/new` (대화형 빌더)
- `text-[10px]` 라벨/배지 다수(688~1063행). `SuggestionCard`/`OptionButton` 미세 텍스트. OptionButton은 long-press 안내 있어 부분 대응. 🟡~🟠.

### `/portfolio`
- `PortfolioTable` `overflow-x-auto` ✅, `grid-cols-2 md:grid-cols-3 lg:grid-cols-6` 반응형 ✅. `PortfolioChart` ResponsiveContainer ✅(높이 400 고정만 MINOR).

### `/validation` (1차 검증, stocks 상세 내 탭 추정)
- `CategorySidebar` 버튼 높이 ≈36px(44pt 미달) 🟡. `MetricBarChart` 라벨 `text-[10px]` 🟡. `SignalSummaryCard` `min-w-[72px]`+`overflow-x` 가로 스크롤 🟡. `PeerContextBar` `text-[10px]` 안내문.

### `/coach/e1~e6` (포트폴리오 코치)
- 🟠 입력 행 `grid grid-cols-12` 모바일 미붕괴(브레이크포인트 없음). ticker/비중 입력 `py-1.5`(≈32px) 44pt 미달. e4 입력 카운터 `text-[11px]`. 데스크톱 폼을 모바일에 그대로 노출.

### `/market-pulse`, `/market-pulse-v2`
- `MoverCard` 류 hover-only 툴팁 5종 → 터치 미동작 🟠. `TickerBar` `overflow-x` 사용(가로 스크롤 의도) ✅. footer `text-[10px]` 미세.

### `/news`
- `RecommendationCard`/`NewsHighlightedStocks`/`KeywordDetailSheet` `overflow-x` 사용. `text-[10px]` 메타데이터 다수. `AINewsBriefingCard` `max-w-[200px]` 바. 대체로 카드 기반이라 overflow 위험 낮음.

### `/admin`
- 다수 테이블(`SystemTab`/`NewsTab`/`ScreenerTab` 등) `overflow-x-auto` 래핑 ✅. `AdminTabNav` `overflow-x` 탭. `MLCompareView` `text-xs` 테이블. 관리자 화면이라 모바일 우선순위 낮음 — 현 상태 허용 가능.

---

## 우선 조치 권고 (보고용 — 코드 변경은 별도 승인 필요)

1. 🔴 **`/stocks` 인덱스 페이지 부재 해결 또는 MobileNav `href` 교체** (404 회귀 차단).
2. 🔴 **MobileNav에 Chain Sight·Thesis·Market Pulse·Screener 도달 경로 추가** (탭 확장 or "더보기" 시트).
3. 🟠 **hover-only 툴팁의 터치 대체** (MoverCard / KeywordTag / QuarterlySparkline) — 탭 토글 또는 상시 노출.
4. 🟠 **`/chainsight` 메인에도 모바일 카드 폴백 적용** ([symbol] 페이지 패턴 재사용).
5. 🟠 **coach E1~E6 그리드에 `sm:`/`md:` 분기 + 입력 `min-h-[44px]`**.
6. 🟠 **44pt 미만 클릭 컨트롤 정비** (IndicatorRow 기간 버튼, AlertCard 닫기, RelationLegend 토글 등).
7. 🟡 미세 텍스트(`text-[10px]`) 정보 밀도 점진적 완화 — 모바일 가독성.

> **측정 한계**: 본 감사는 정적 클래스 분석 기반. 실제 overflow/탭 정확도는 375px 실기기(또는 `/browse`·responsive 스냅샷)로 검증 권장. "404 추정"·"가상화 미발견" 등은 런타임 확인 필요.
