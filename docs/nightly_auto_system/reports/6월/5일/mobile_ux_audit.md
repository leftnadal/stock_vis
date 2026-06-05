# 모바일 UX 감사 보고서

> 감사일: 2026-06-05 · 범위: `frontend/` (페이지 30개, 컴포넌트 205개, 총 tsx 291개)
> 기준 뷰포트: **375px (iPhone SE/표준 모바일)** · 터치 타겟 기준: **Apple HIG 44×44pt**
> 성격: **읽기 전용 감사** — 코드 변경 없음. 모든 지적은 정적 분석(grep + 직접 판독) 기반.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 내용 |
|--------|------|-----------|
| 🔴 **BLOCKER** | **2** | ① 전역 bottom-nav 가림(28/30 페이지 하단패딩 부재) ② 관제실/차트 핵심 토글 터치 타겟 ~14px |
| 🟠 **MAJOR** | **5** | 작은 터치 타겟 다수, 데스크톱 전용 레이아웃 182건, 테이블 가로 스크롤 의존, coach 폼 grid-cols-12, 고정 차트 height |
| 🟡 **MINOR** | **4** | text-[11px] 가독성, 미니 SVG 미니맵, 툴팁 폭, 다크모드 외 |

**총평**: 네비게이션 골격(bottom nav + 데스크톱 헤더 분기)과 차트 인프라(Recharts 14/14 ResponsiveContainer), chainsight 모바일 대체뷰(MobileCardList) 등 **모바일 기반 설계는 양호**. 다만 **전역 레이아웃의 하단 패딩 누락**과 **반복되는 초소형 터치 타겟**이 실제 사용을 막는 수준이다. 고정 폭(`w-[NNpx]`) 남용은 거의 없어 overflow 리스크는 낮음.

---

## 반응형 누락

### 🔴 BLOCKER-1 · 전역 레이아웃에 bottom-nav 가림 방지 패딩 없음
- **위치**: `app/layout.tsx:60` — `<main className="min-h-screen">`
- **사실**: `MobileNav`는 `fixed bottom-0 ... h-16`(64px, `MobileNav.tsx:19,22`)로 화면 하단을 항상 점유. 그러나 `<main>`에는 `pb-16`/`pb-20` 등 **하단 여백이 없다**.
- **영향**: 페이지 콘텐츠의 **최하단 요소가 64px 가려진다**. 자체 하단 패딩을 가진 페이지는 **30개 중 단 2개**(`app/page.tsx`, `app/thesis/[thesisId]/page.tsx`)뿐 → 나머지 **28개 페이지에서 최하단 버튼/링크/입력이 bottom nav에 가려져 탭 불가** 가능. 최하단 요소가 "저장/제출" 같은 액션이면 기능 차단.
- **근거**: `grep -rlE 'pb-16|pb-20|pb-24|mb-16|mb-20' --include=page.tsx app` → 2개만 매치.
- **권고(보고용)**: `<main>`에 `pb-20 md:pb-0` 단일 적용으로 28개 페이지 일괄 해소 가능.

### 🟠 MAJOR-1 · 브레이크포인트 없는 컴포넌트 182개
- **사실**: `className`을 쓰면서 `sm:`/`md:`/`lg:`/`xl:`가 **전혀 없는** 컴포넌트가 **182개**(브레이크포인트 사용 72개). 
- **해석**: 다수는 부모가 반응형을 책임지는 leaf 컴포넌트라 즉시 문제는 아니나, **페이지·섹션 레벨에서 데스크톱 고정 레이아웃**이 섞여 있어 모바일에서 밀집/잘림 유발.
- **대표 사례**: `app/coach/e1~e6/page.tsx`의 폼/그리드(아래 MAJOR-4), validation 섹션 카드들.

### 🟢 양호 · 고정 폭(`w-[NNpx]`) overflow 리스크 낮음
- 고정 폭 사용 파일 23개를 전수 확인했으나, 375px overflow를 유발하는 큰 고정 폭은 사실상 없음:
  - `SignalDetailSheet.tsx:97` `w-[420px]` → **`md:w-[420px]`**, 모바일은 `w-full`. ✅
  - `MarketGraphCanvas.tsx:676` `w-[110px] min-h-[68px]` → 섹터 버튼, 화면폭 내. ✅
  - `ChatInterface.tsx:198` `h-[52px] w-[52px]` → 전송 버튼(>44px). ✅
  - `DataSourceBadge.tsx:171` `min-w-[200px]` → 툴팁, 375px 내 수용. ✅
  - 최다 빈도 고정 폭은 `min-w-[44px]`(터치 타겟 보장 목적, 3건), `min-w-[18px]`(배지) 등 소형.

### 🟢 양호 · 테이블 가로 스크롤 처리됨 (단, UX는 MAJOR-3 참조)
- `overflow-x-auto`/`overflow-auto` 적용 파일 **29개**. 주요 테이블 모두 래퍼로 감쌈:
  - `StockTable.tsx:34`, `PortfolioTable.tsx:259`, `ScreenerTable.tsx:128` 전부 `overflow-x-auto`. ✅

---

## 터치 타겟

### 🔴 BLOCKER-2 · 관제실/차트 기간 토글 등 ~14px 터치 타겟
- **위치**: `components/thesis/dashboard/IndicatorRow.tsx:179-189`
  - `className="px-2.5 py-0.5 text-[10px] rounded ..."` → 높이 ≈ **py-0.5(4px) + 10px ≈ 14px**, 44px 기준의 1/3.
- **영향**: thesis **관제실 지표 카드의 차트 기간(7/30/90일 등) 토글**이 모바일에서 정확히 탭 불가. 사용자가 명시 지목한 "관제실 지표 카드" 영역의 핵심 인터랙션.
- **확산도**: `text-[10px]`는 클릭 가능 요소 포함 컨텍스트에서 광범위 사용 — 파일별 상위:
  - `app/thesis/new/page.tsx`(7건), `MoverCard.tsx`/`MoverCardWithBatchKeywords.tsx`(각 6건), `PresetGallery.tsx`(4건), `KeywordList.tsx`(4건), `IndicatorRow`·`RecommendCard`·`AlertCard`·`MobileStockCard`·`ChainStoryFeed`·`MobileCardList` 등(각 3건).

### 🟠 MAJOR-2 · `py-0.5`/`py-1` 초소형 클릭 요소 패턴
- `onClick`을 가진 컴포넌트가 **156개**. 그 중 `px-2.5 py-0.5`·`px-3 py-1.5`(≈30px) 같은 44px 미달 클릭 요소가 chainsight 필터칩, 키워드 태그, 프리셋 갤러리, validation 커스텀 입력 버튼(`PeerContextBar.tsx:76 px-3 py-1.5`) 등에 분포.

### 🟢 양호 · 지목 컴포넌트 중 HIG 준수 사례
- **validation 프리셋 탭**: `PeerContextBar.tsx:37-61` 프리셋/커스텀 버튼 모두 **`min-h-[44px] px-4 py-2`** ✅ (사용자 지목 항목, 합격).
- **bottom nav 항목**: `MobileNav.tsx` 각 링크 `min-h-[44px]` + `h-16` 컨테이너 ✅.
- **분기 스파크라인 바**: `QuarterlySparkline.tsx:44` 각 바가 `min-h-[44px]` 버튼 ✅.
- **min-h-[44px]/min-w-[44px] 또는 h-11/h-12** 사용 확인 파일 38개 — 터치 타겟 인지가 코드베이스 전반에 일부 정착.

---

## 네비게이션

### 🟢 양호 · 모바일 네비게이션 골격 견고
- **Bottom navigation 존재**: `MobileNav.tsx` — `fixed bottom-0 ... md:hidden z-50`, 5개 탭(홈/종목/뉴스/포트폴리오/내정보), 아이콘+라벨, active 상태 표시, `aria-label`. `app/layout.tsx:63`에서 전역 렌더. ✅
- **데스크톱/모바일 분기**: `Header.tsx` — 데스크톱 nav는 `hidden md:flex`(42), 모바일은 햄버거(`Menu`, 162) → `isMenuOpen` 드로어(`md:hidden`, 168). 검색·유저 액션 모두 분기. ✅
- **단일 소스 정리**: 주석(`Header.tsx:155`)대로 모바일 네비는 MobileNav로 일원화, 헤더 햄버거 중복 제거 흔적 확인.

### 🟠 MAJOR-3 · 긴 목록 virtualization 부재 + 테이블 가로 스크롤 의존
- **virtualization**: `react-window`/`react-virtuoso` 등 가상화 라이브러리 사용 흔적 없음. 종목/스크리너/뉴스 등 **긴 목록을 전량 렌더** → 모바일 저사양 기기에서 스크롤 성능·메모리 부담.
- **가로 스크롤 UX**: 테이블은 `overflow-x-auto`로 잘리진 않으나, 375px에서 `PortfolioTable`(8+ 컬럼, 전부 `whitespace-nowrap` 33건)은 **가로 스크롤 강제** → 모바일 본질적 열람성 저하. 카드 뷰 대체는 `screener`(`MobileStockCard`)·`chainsight`(`MobileCardList`)만 존재, **portfolio/stocks 테이블은 모바일 카드 대체뷰 없음**.

---

## 차트/그래프

### 🟢 양호 · Recharts 반응형 100%
- Recharts import 14개 파일 **전부 `ResponsiveContainer` 사용**(`width="100%"`): market-pulse-v2 상세 4종, StockPriceChart, PortfolioChart, SentimentChart, YieldCurveChart, MetricBarChart, SectorHeatmap, IndividualMiniCharts, IndicatorRow, StockChart, MLTrendChart. ✅

### 🟢 양호 · chainsight 그래프 모바일 대체뷰
- `app/chainsight/[symbol]/page.tsx`: 우측 상세 `<aside>`는 `hidden lg:block`(358), 모바일은 **`MobileCardList`**(162)로 대체. ForceGraph 노드(`MarketGraphCanvas` 노드 크기 8~28px)는 터치 타겟이 작지만, 모바일에서 카드 리스트로 우회하는 설계라 실사용 차단은 회피. ✅

### 🟠 MAJOR-4 · coach 입력 폼 `grid-cols-12` 모바일 밀집
- `app/coach/e1~e6/page.tsx`(각 ~150~200행): 종목/비중 입력 행이 **`grid grid-cols-12`**(브레이크포인트 없음). `col-span-4` input들이 375px에서 빡빡하게 압축 — `placeholder="AAPL"`/숫자 입력이 좁아 오타·미스탭 유발. overflow는 아니나 입력 정확도 저하.

### 🟡 MINOR-1 · 고정 차트 height
- `PortfolioChart.tsx:77,97` `height={400}` 고정 → 모바일에서 세로 400px 점유 과다(스크롤 비용↑). `StockPriceChart`는 `height` prop으로 유연 ✅.

### 🟡 MINOR-2 · 미니 SVG 미니맵 가독성
- `MarketGraphCanvas.tsx:606` 미니맵 `width="160" height="120"` 고정 + `r="3"` 노드 → 375px에서 식별 어려움(부가 요소라 영향 낮음).

---

## 페이지별 상세

> 컴포넌트→페이지 매핑은 import 추적 및 디렉토리 규칙 기반 추정. 심각도는 해당 페이지에서 가장 높은 이슈 기준.

| 페이지 | 심각도 | 주요 이슈 |
|--------|--------|-----------|
| **전체(28개)** | 🔴 BLOCKER | `<main>` 하단패딩 부재 → 최하단 요소 bottom-nav 가림 (`app/page.tsx`·`thesis/[thesisId]` 제외) |
| `/thesis/[thesisId]` (관제실) | 🔴 BLOCKER | IndicatorRow 차트 기간 토글 `text-[10px] py-0.5`(~14px). 단 자체 하단패딩은 보유 |
| `/thesis/new` | 🟠 MAJOR | `text-[10px]` 7건 클릭 컨텍스트, 제안 카드 밀집 |
| `/coach/e1`~`/coach/e6` | 🟠 MAJOR | `grid-cols-12` 입력 폼 모바일 밀집, 브레이크포인트 부재 |
| `/portfolio` | 🟠 MAJOR | PortfolioTable 8+컬럼 가로 스크롤, 모바일 카드 대체뷰 없음, `height={400}` 차트 |
| `/screener` | 🟠 MAJOR | `MobileStockCard` 대체뷰 ✅이나 PresetGallery `text-[10px]` 4건, 필터 패널 밀집 |
| `/stocks/[symbol]` | 🟠 MAJOR | StockTable 가로 스크롤, validation 섹션(MetricCard/CategorySection) 브레이크포인트 부재 |
| `/chainsight`, `/chainsight/[symbol]` | 🟡 MINOR | 모바일 대체뷰(MobileCardList) ✅, 그래프 노드 터치 작음(우회됨), 필터칩 `py-0.5` |
| `/news` | 🟡 MINOR | RecommendationCard/AINewsBriefingCard `text-[10px]`, NewsList 가상화 부재 |
| `/market-pulse`, `/market-pulse-v2` | 🟡 MINOR | Recharts ResponsiveContainer ✅, MoverCard `text-[10px]` 6건 |
| `/validation`(stocks 내부) | 🟢 양호 | PeerContextBar 프리셋 탭 `min-h-[44px]` ✅, 일부 카드 `text-[11px]` |
| `/admin` | 🟡 MINOR | 데스크톱 운영 도구 성격, 테이블 다수 `overflow-x-auto` 처리됨 |
| `/ai-analysis`(RAG) | 🟢 양호 | ChatInterface 전송 버튼 `52px` ✅, SuggestionChips 확인 권장 |
| `/dashboard`, `/watchlist`, `/mypage`, `/login`, `/signup` | 🟠 MAJOR | 하단패딩 부재(BLOCKER-1 포함), 그 외 표준 폼 양호 |

---

## 부록 · 검증 명령(재현용)

```bash
# 하단패딩 보유 페이지 (2개만 매치 → BLOCKER-1 근거)
grep -rlE 'pb-16|pb-20|pb-24|mb-16|mb-20' --include='page.tsx' frontend/app

# 브레이크포인트 없는 컴포넌트 수 (182)
# className 있고 sm:/md:/lg:/xl: 없는 tsx 카운트

# text-[10px] 클릭 컨텍스트 분포
grep -rEc 'text-\[10px\]' --include='*.tsx' frontend | grep -v ':0' | sort -t: -k2 -rn

# Recharts ResponsiveContainer 커버리지 (14/14)
grep -rEl "from 'recharts'" --include='*.tsx' frontend
grep -rEl 'ResponsiveContainer' --include='*.tsx' frontend
```

---

### 우선순위 권고 (보고용 — 코드 변경 없음)

1. **BLOCKER-1** (1줄 수정으로 28페이지 해소): `app/layout.tsx`의 `<main>`에 `pb-20 md:pb-0`.
2. **BLOCKER-2** (관제실 핵심): IndicatorRow 차트 기간 토글을 `min-h-[44px]` + 최소 `text-xs`로.
3. **MAJOR-3**: portfolio/stocks 테이블에 모바일 카드 대체뷰 추가(screener/chainsight 패턴 재사용).
4. **MAJOR-1/2**: 클릭 요소 `text-[10px] py-0.5` 패턴을 디자인 토큰화하여 44px 하한 강제.

> 본 보고서는 정적 분석 기반이며, 실제 픽셀 렌더링·실기기 탭 정확도는 `/qa` 또는 browse 도구(375px viewport)로 추가 검증 권장.
