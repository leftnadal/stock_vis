# 모바일 UX 감사 보고서

> **대상**: Stock-Vis 프론트엔드 (Next.js 16 / Tailwind CSS)
> **기준 뷰포트**: 모바일 375px (iPhone SE/12 mini 기준)
> **방식**: 읽기 전용 정적 코드 감사 (코드 수정 없음). 205개 컴포넌트 + 30개 페이지 대상 패턴 스캔 + 핵심 영역 심층 분석.
> **작성일**: 2026-06-16
> **심각도 기준**:
> - **BLOCKER**: 375px에서 콘텐츠 사용 불가 / 가로 overflow / 핵심 기능 조작 불가
> - **MAJOR**: HIG 44pt 터치 타겟 미달, 가독성 심각 저하, 반응형 부재로 인한 레이아웃 깨짐
> - **MINOR**: 폰트 약간 작음, 패딩 불일관, 개선 여지

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 핵심 이슈 |
|--------|------|----------|
| **BLOCKER** | 6 | Chainsight 그래프 캔버스 모바일 미대응, `AddIndicatorSheet` grid-cols-2 고정, `MarketGraphCanvas` 인기섹터 버튼 overflow, `ScreenerTable` 단독 미대응, `StockRow` 회사명 절단, MoverCard hover 툴팁 터치 미작동 |
| **MAJOR** | 18 | 44pt 미달 아이콘 버튼 다수, `text-[10px]`/`text-[11px]` 정보 텍스트 범람, 차트 고정 height, 가상화 전무, thesis 지표카드 indent overflow |
| **MINOR** | 12 | 패딩 불일관(px-2 vs px-4), 작은 폰트 푸터/배지, admin 탭 가로 스크롤 |

**총 36건** (BLOCKER 6 / MAJOR 18 / MINOR 12)

### 종합 진단
- **기반 인프라는 양호**: `viewport` 메타 설정 정상, `MobileNav`(하단 탭) 존재, Recharts 전 컴포넌트 `ResponsiveContainer` 폭 반응형 적용, 주요 페이지 컨테이너 `grid-cols-1` 모바일 기본값 + 반응형 패딩 사용.
- **결정적 약점 3가지**:
  1. **Chain Sight 그래프 화면** — 데스크톱 3-panel 전제로 설계되어 모바일에서 그래프/카드 전환 시 상태 소실, 노드 터치 타겟 미달.
  2. **아이콘 버튼 터치 타겟** — `p-1`/`p-1.5` + 14~16px 아이콘 패턴이 EOD/watchlist/thesis 전반에 산재 (실제 22~32px, 44pt 미달).
  3. **소형 폰트 정보 밀도** — `text-[10px]`/`text-[11px]`가 57개 파일 128곳에서 사용. 다수가 핵심 정보(신호 라벨, 배지, 변동률)를 전달.
- **공통 패턴**: 정보를 좁은 공간에 욱여넣는 "데스크톱 밀도" 설계가 모바일로 그대로 이식됨.

---

## 반응형 누락

### BLOCKER

| 파일:라인 | 이슈 |
|-----------|------|
| `chainsight/MarketGraphCanvas.tsx:676` | 인기 섹터 빠른 접근 버튼 `w-[110px]` × 3개를 `flex flex-wrap justify-center gap-3`(668)로 가로 배치 → 3×110+gap = 360px+ > 343px 유효폭. 375px에서 줄바꿈/overflow |
| `strategy/ScreenerTable.tsx:128-129` | `overflow-x-auto` + `w-full` 테이블. 모바일→`MobileStockCard` 전환 분기가 **`screener/page.tsx:845,854`에만** 존재. ScreenerTable 단독 사용 시 모바일 미대응(데스크톱 다열 테이블 가로 스크롤 강제) |

### MAJOR

| 파일:라인 | 이슈 |
|-----------|------|
| `chainsight/MarketGraphCanvas.tsx:760` | 그래프 캔버스 `h-[560px]` 고정 + sm/md 브레이크포인트 없음. 375px에서 화면 ~90% 점유, 하단 컨텐츠 접근 곤란 |
| `chainsight/MarketGraphCanvas.tsx:104,152-156` | `containerWidth` 초기값 800px 하드코딩 후 ResizeObserver로 갱신 → 모바일 초기 렌더 시 폭 불일치 깜빡임 |
| `thesis/dashboard/IndicatorRow.tsx:110,115` | `min-w-[60px]`(값) + `min-w-[120px]`(변동)을 `gap-3` + `pl-4` 와 조합 → 375px에서 가로 overflow |
| `thesis/IndicatorCard.tsx:73` | 상세 영역 `ml-8`(32px) indent + `p-3` 컨테이너에서 텍스트 줄바꿈 시 horizontal overflow |
| `portfolio/PortfolioChart.tsx:77,97` | `ResponsiveContainer height={400}` 고정. 모바일 반응형 height 미적용 → 과도한 세로 점유 |
| `screener/SectorHeatmap.tsx:216` | `height={400}` 고정. 다른 모바일 차트(280px)와 불일치 |
| `eod/StockRow.tsx:65-84` | 우측 가격 영역 `min-w-[72px]` 고정폭 (반응형 미고려) |
| `app/coach/e1/page.tsx:150` | `grid grid-cols-12`(브레이크포인트 없음). 12열 그리드 375px에서 각 셀 과소 |

### MINOR

| 파일:라인 | 이슈 |
|-----------|------|
| `app/market-pulse-v2/page.tsx:58` | `px-2`(8px)만 사용 → 다른 페이지(px-4)와 불일관, 375px에서 콘텐츠가 가장자리에 붙음 |
| `chainsight/RelationLegend.tsx:51` | `max-w-[140px]` 좌하단 오버레이, 모바일에서 캔버스 콘텐츠 가림 가능 |
| `chainsight/SectorBar.tsx:41` | `max-w-[120px]` truncate (overflow-x-auto는 있음) — 긴 섹터명 시각 손실 |
| `screener/PresetGallery.tsx:355,380,405,430` | `grid-cols-2 md:...` → 375px/2=187px 좁은 카드, 텍스트 많으면 overflow 가능. grid-cols-1 고려 |
| `stock/StockChart.tsx:586` | 설정 패널 `absolute right-0` — 부모 relative 미보장 시 375px에서 우측 튀어나옴 위험 |
| `news/SentimentChart.tsx:79` | `h-80`(320px) 고정 — 동적 높이 미적용 |

**참고(양호)**: `dashboard/page.tsx:54`, `portfolio/page.tsx:96`, `watchlist/page.tsx:173`, `stocks/[symbol]/page.tsx:259`, `screener/AdvancedFilterPanel.tsx:276`, `screener/Pagination.tsx:78`는 `grid-cols-1` 모바일 기본 + 반응형 패딩을 올바르게 적용.

---

## 터치 타겟

> Apple HIG 권장 최소 44×44pt. 아래는 실제 렌더 크기가 미달하는 클릭 요소.

### BLOCKER

| 파일:라인 | 이슈 |
|-----------|------|
| `market-pulse/MoverCard.tsx:132-189` | 지표 설명이 **`group-hover/tooltip`** 기반(hover 전용). 터치 디바이스에는 hover 이벤트가 없어 **모바일에서 지표 설명 자체에 접근 불가**. 툴팁 내용도 `text-[10px]`. `MoverCardWithBatchKeywords.tsx`도 동일 패턴 |

### MAJOR

| 파일:라인 | 실제 크기 | 이슈 |
|-----------|-----------|------|
| `eod/SignalCard.tsx:102-114` | ~22×22px | `p-1` + `w-3.5 h-3.5`(14px) 교육 팁 토글 버튼 |
| `eod/SignalDetailSheet.tsx:136-141` | ~28×28px | `p-1.5` + `w-4 h-4` 닫기 버튼 |
| `eod/SignalDetailSheet.tsx:213-219` | ~20px 높이 | `px-3 py-1` 정렬 메뉴 버튼 |
| `watchlist/WatchlistItemRow.tsx:110-130` | ~28×28px | `p-1.5` + `h-4 w-4` 수정/삭제 액션 버튼 |
| `thesis/indicators/RecommendCard.tsx:52` | 40×40px | `p-2.5` + 16px 아이콘 추가/체크 버튼 (44pt 미달) |
| `thesis/indicators/IndicatorSetupCard.tsx:58,68` | 32×32px | `p-2` + 16px 아이콘 전원/삭제 버튼 |
| `thesis/dashboard/QuarterlySparkline.tsx:44,54` | 가변(<44px) | `min-h-[44px]`를 flex 컨테이너에 줬으나 실제 클릭 대상 바 높이는 `${heightPct}%`(h-10 기준 4~40px) |
| `chainsight/MarketGraphCanvas.tsx:789-792` | 20px 지름 | 2차 이웃 노드 `nodePointerAreaPaint` 반지름 sm=10 → 지름 20px 터치 타겟 미달 (center 56px·1차 28~40px은 양호) |

### MINOR (가독성 — 작은 정보 텍스트)

> `text-[10px]`(7.5pt)·`text-[11px]`(8.25pt)는 WCAG/모바일 권장 최소(12px) 미만. 클릭 요소는 아니나 핵심 정보를 전달하는 경우 가독성 저하.

| 영역 | 대표 위치 |
|------|-----------|
| EOD 신호 라벨 | `eod/StockRow.tsx:89`(`text-[11px]`), `eod/SignalCard.tsx:178`(`text-[10px]`), `eod/NewsContextBadge.tsx:67`(`text-[11px]`) |
| Thesis 지표 카드 | `thesis/dashboard/IndicatorRow.tsx:182`(기간 선택 버튼 `text-[10px]`), `RealValueIndicatorCard.tsx:76,83`(설명 `text-[10px] truncate`), `IndicatorCard.tsx:52,78`(배지/상세) |
| Chainsight | `MobileCardList.tsx:149,154,159`(프로파일 태그), `RelationCardPanel.tsx:273,289`(배지), `ExplorationTrail.tsx:46,48`(엣지 라벨), `ChainStoryFeed.tsx:108,111,122`(카드 배지) |
| Validation | `PeerContextBar.tsx:40,54`(프리셋 탭 `text-xs`+`min-h-[44px]`은 타겟OK·폰트 작음), `:90`(안내문 `text-[10px]`) |
| Market Pulse | `MoverCard.tsx:107`(회사명 `text-[10px] truncate`), `market-pulse-v2/page.tsx:77`(푸터 `text-[10px]`) |
| Screener | `MobileStockCard.tsx:166`(메트릭 레이블 `text-[10px]`) |

> **규모**: `text-[10px]`/`text-[11px]`/`text-[12px]` 패턴은 **57개 파일 128곳**에서 검출됨. 위는 사용자 노출 빈도가 높은 대표 사례.

---

## 네비게이션

### 양호
- **하단 탭 네비게이션 존재** — `components/layout/MobileNav.tsx`: 5개 탭(홈/종목/뉴스/포트폴리오/내정보), `md:hidden`, `fixed bottom-0`, `h-16`(64px) + 각 링크 `min-h-[44px]` 명시. 터치 타겟·`aria-label` 모두 준수. (주석상 audit P0 #12/#13에서 이미 1차 교정됨)
- **헤더 모바일 처리** — `components/layout/Header.tsx`: 데스크톱 nav `hidden md:flex`(42), 검색바/유저액션 `hidden md:block`(112,126). 햄버거 버튼은 `hidden`(157~163)으로 비활성화하고 MobileNav를 모바일 단일 네비 소스로 사용 (이중 네비 제거 의도, 주석 명시).
- **Admin 탭** — `components/admin/AdminTabNav.tsx:30`: `overflow-x-auto` + `whitespace-nowrap` + `min-h-[44px]`. 가로 스크롤 가능.

### MAJOR

| 파일:라인 | 이슈 |
|-----------|------|
| (전역) 가상화 전무 | `react-window`/`react-virtual`/`FixedSizeList` import **0건**. 긴 목록 전체 DOM 렌더 |
| `app/news/page.tsx:52` | 뉴스 최대 100건(`limit:100`) 풀 로드, 카테고리 4섹션 × N → 모바일 스크롤 시 프레임 드롭 위험 |
| `app/watchlist/page.tsx:294-331` | 데스크톱 테이블 레이아웃 + `overflow-x-auto`이나 `px-6` 패딩으로 375px에서 넘침, 무제한 행 |
| `app/stocks/[symbol]/page.tsx`(FinancialTable) | 재무제표 테이블 무제한 행×다열, 모바일 가로 스크롤 + 불필요 DOM |

### MINOR

| 파일:라인 | 이슈 |
|-----------|------|
| `components/admin/AdminTabNav.tsx:30` | 6개 탭이 375px에서 2~3개만 노출 → 스크롤 필수. 세그먼트 컨트롤/드롭다운 등 모바일 최적 UI 부재 |
| `app/chainsight/[symbol]/page.tsx:356-358` | 우측 패널 `hidden lg:block`(w-72) — 모바일 숨김은 의도적이나 3-panel 전제 설계 흔적 |

> **참고**: `InvestingHeader.tsx`는 완전 데스크톱 전용(max-w-[1400px] 다단 nav, 하드코딩 지수값)이나 `layout.tsx`에 미연결(`Header`만 사용)되어 실제 라우트 영향 없음. 다만 데드/레거시 코드로 잔존.

---

## 차트/그래프

### Recharts ResponsiveContainer 적용 현황 — **양호**
스캔된 15개 Recharts 사용 컴포넌트 전부 `ResponsiveContainer width="100%"` 적용 → **가로 폭 반응형은 전반적으로 정상**. 문제는 **높이(height)** 고정과 **Chainsight force-graph 캔버스**.

| 파일 | width 반응형 | height | 판정 |
|------|:---:|--------|------|
| `charts/StockPriceChart.tsx:272` | ✅ | prop | 양호 (버튼 `min-h-[44px]`) |
| `stock/StockChart.tsx:652,748` | ✅ | `getResponsiveChartHeight()` 모바일 280px | **모범 사례** |
| `thesis/dashboard/IndividualMiniCharts.tsx:54` | ✅ | 100(미니) | 양호 |
| `macro/YieldCurveChart.tsx:93` | ✅ | h-64 | 양호 |
| `admin/news/MLTrendChart.tsx:90` | ✅ | h-[200px] | 양호(관리자) |
| `portfolio/PortfolioChart.tsx:77` | ✅ | **400 고정** | MAJOR |
| `screener/SectorHeatmap.tsx:216` | ✅ | **400 고정** | MAJOR |
| `news/SentimentChart.tsx:80` | ✅ | **h-80 고정** | MINOR |

### 분기 스파크라인 모바일 가독성

| 파일:라인 | 이슈 | 심각도 |
|-----------|------|--------|
| `thesis/dashboard/IndicatorRow.tsx:132` | 스파크라인 `max-w-[100px]` 제약 + `:212` YAxis `width={55}` 고정 → 375px 차트 영역에서 Y축이 ~15% 점유, 실데이터 영역 협소 | MAJOR |
| `thesis/dashboard/QuarterlySparkline.tsx:57-59` | 분기 라벨 `text-[11px]`를 짧은 막대 위 h-10 공간에 4~5개 압축 → 가독성 저하 + 막대 터치 타겟 미달(위 터치 섹션 참조) | MAJOR |

### Chainsight 그래프 캔버스 (force-graph) — **BLOCKER 집중 영역**

| 파일:라인 | 이슈 | 심각도 |
|-----------|------|--------|
| `app/chainsight/[symbol]/page.tsx:152-231` | 모바일(<768px) 기본은 `MobileCardList`, 그래프는 `fixed inset-0` 전체화면 오버레이로만 표시. 오버레이 닫기(`:182`) 시 **그래프 상태(중심/탐색 경로) 보존 안 됨** | BLOCKER |
| `app/chainsight/[symbol]/page.tsx:200` | 그래프 오버레이 하단 시트 `max-h-48`(192px) 고정 → header 48px 제외 시 그래프 실효 공간 ~135px, 조작 사실상 불가 | MAJOR |
| `chainsight/MarketGraphCanvas.tsx:121,814-821` | 모바일 노드 클릭 `(pointer: coarse)` 분기·더블탭(500ms) 구현은 있으나, **롱프레스 미구현**(`longPressTimerRef` 선언만, 미사용), **터치 줌/팬 미지원**(react-force-graph 기본 동작 의존) | MAJOR |
| `chainsight/NodeTooltip.tsx:131-132` | 툴팁 `maxWidth:220` — 375px에서 화면 점유율 과다, 노드 가림 | MINOR |
| `chainsight/RelationFilterChips.tsx:229` / `SectorBar.tsx:24` | 필터 칩 바 `overflow-x-auto` (6개 칩 ~440px) → 가로 스크롤 필연 (페이드아웃 그라디언트 보완은 있음) | MINOR |

---

## 페이지별 상세

### 🟢 홈 `/` (`app/page.tsx`)
- `max-w-6xl mx-auto px-4`(72) — 컨테이너 안전. 큰 이슈 없음.

### 🟢 대시보드 `/dashboard`
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`(54) — 모바일 기본 1열 정상.

### 🟡 포트폴리오 `/portfolio`
- 컨테이너 반응형 양호(96). **MAJOR**: `PortfolioChart` height=400 고정.

### 🟡 뉴스 `/news`
- 컨테이너 `px-4 sm:px-6`(199) 양호. **MAJOR**: 100건 풀 로드 + 가상화 없음.

### 🟠 워치리스트 `/watchlist`
- **MAJOR**: 데스크톱 테이블 레이아웃(294-331) `px-6`로 375px 넘침 + 액션버튼(110-130) 28px 터치 타겟 미달 + 가상화 없음. 모바일 카드 레이아웃 전환 필요.

### 🟠 종목 상세 `/stocks/[symbol]`
- 컨테이너 반응형 양호(259). **MAJOR**: 재무제표 테이블 무제한 행×다열 가로 스크롤 + 가상화 없음. `StockChart`는 모범적(반응형 height).

### 🔴 Chain Sight `/chainsight`, `/chainsight/[symbol]` — **최우선 개선 대상**
- **BLOCKER**: 그래프 화면 모바일 상태 소실(152-231) + `MarketGraphCanvas` 인기섹터 버튼 overflow(676).
- **MAJOR**: 캔버스 h-560 고정, 2차 노드 터치 타겟 20px, 롱프레스/줌·팬 미구현.
- **MAJOR/MINOR**: 배지·태그·엣지 라벨 `text-[10px]` 범람(MobileCardList/RelationCardPanel/ExplorationTrail/ChainStoryFeed).
- 데스크톱 3-panel 전제 설계가 모바일에 부분 이식된 상태.

### 🔴 Thesis Control `/thesis/*` — **정보 밀도 과다**
- **BLOCKER**: `AddIndicatorSheet.tsx:274,292` `grid-cols-2` 고정(브레이크포인트 없음) — 긴 지표명("미국 기준금리(Fed Funds Rate)" 등) 187px 셀에서 overflow/truncate. `:265` `max-h-[60vh]` 과도 스크롤.
- **MAJOR**: `IndicatorRow` min-w overflow(110,115) + 스파크라인 협소(132,212), `IndicatorCard` ml-8 indent overflow(73), `RecommendCard`/`IndicatorSetupCard` 아이콘 버튼 44pt 미달.
- **MINOR**: 기간 선택/배지/설명 `text-[10px]` 다수.
- 페이지 컨테이너 자체(`max-w-lg mx-auto px-4`)는 양호.

### 🟡 Validation (1차 검증, chainsight/screener 내 임베드)
- **MAJOR**: `SignalSummaryCard.tsx:41` 신호등 인지 크기(원 w-11 h-11≈44px 경계), `PeerContextBar` 프리셋 탭 타겟은 `min-h-[44px]` OK이나 `text-xs` 가독성.
- **MINOR**: 안내문 `text-[10px]`.

### 🟠 스크리너 `/screener`
- 페이지 레벨은 양호: `hidden sm:block`로 테이블/카드 전환(845,854), `AdvancedFilterPanel` grid-cols-1 분기, `Pagination` flex-col + 44pt 버튼.
- **BLOCKER**: `ScreenerTable` 컴포넌트 자체는 모바일 미대응(페이지 분기에만 의존).
- **MINOR**: `PresetGallery` grid-cols-2 좁은 카드, `MobileStockCard` 레이블 `text-[10px]`.

### 🟡 Market Pulse `/market-pulse`, `/market-pulse-v2`
- **BLOCKER**: `MoverCard` 지표 설명이 hover 툴팁(132-189) → 터치 미작동.
- **MINOR**: `market-pulse-v2/page.tsx:58` `px-2` 패딩 불일관, 푸터 `text-[10px]`, 회사명 `text-[10px] truncate`.

### 🟡 Coach `/coach/e1~e6`
- `e1/page.tsx:94` `max-w-4xl px-4` 양호, `:111` grid 반응형 정상.
- **MAJOR 후보**: `e1/page.tsx:150` `grid-cols-12`(브레이크포인트 없음) — 12열을 375px에서 사용, 셀 과소 가능. (e2~e6 동일 패턴 여부 추가 점검 권장)

### 🟡 Admin `/admin`
- 컨테이너 `max-w-7xl px-4`(47) 양호, `AdminTabNav` overflow-x-auto + 44pt.
- **MINOR**: 6개 탭 가로 스크롤만 제공, 모바일 최적 UI 부재. 관리자 화면이라 우선순위 낮음.

---

## 권장 조치 (우선순위)

### P0 — BLOCKER (사용 불가/접근 차단)
1. **MoverCard hover 툴팁 → 탭/클릭 토글 전환** (`MoverCard.tsx`, `MoverCardWithBatchKeywords.tsx`). 터치 디바이스에서 지표 설명 접근 복구.
2. **Chain Sight 그래프 모바일 재설계** — 그래프↔카드 전환 시 상태 보존, 하단 시트 높이 동적화, 캔버스 반응형 height. (`app/chainsight/[symbol]/page.tsx`, `MarketGraphCanvas.tsx`)
3. **`AddIndicatorSheet` grid-cols-2 → grid-cols-1 + sm:grid-cols-2** (긴 지표명 overflow 해소).
4. **`MarketGraphCanvas` 인기섹터 버튼** `w-[110px]` 고정 제거 → flex-basis/반응형.
5. **`ScreenerTable` 자체 모바일 대응** 또는 단독 사용 금지 명문화.
6. **`StockRow` 회사명** `max-w-[140px]` → 반응형(`max-w-[60%]`/flex-1).

### P1 — MAJOR (터치 타겟 / 반응형)
7. **아이콘 버튼 일괄 `min-h-[44px] min-w-[44px]` 적용** — EOD(SignalCard/SignalDetailSheet), watchlist(액션), thesis(Recommend/Setup), chainsight 2차 노드.
8. **차트 height 반응형화** — `PortfolioChart`/`SectorHeatmap`/`SentimentChart`를 `StockChart.getResponsiveChartHeight()` 패턴으로 통일.
9. **긴 목록 가상화 도입** — news/watchlist/재무제표 테이블에 `react-window` 등.
10. **thesis `IndicatorRow`/`IndicatorCard` overflow 교정** — min-w/ml-8 모바일 조정.

### P2 — MINOR (가독성/일관성)
11. **`text-[10px]`/`text-[11px]` → 최소 `text-xs`(12px) 상향** (정보 전달 텍스트 우선). 128곳 중 사용자 노출 핵심부터.
12. **패딩 표준화** — `market-pulse-v2` `px-2`→`px-4`.
13. **admin 탭** 세그먼트 컨트롤/드롭다운 검토(우선순위 낮음).

---

## 부록: 스캔 메타데이터

- **고정 폭 패턴**(`w-[Npx]`/`min-w-[Npx]`/`max-w-[Npx]`/`h-[Npx]`): 42개 파일 66곳
- **소형 폰트 패턴**(`text-[10/11/12px]`): 57개 파일 128곳
- **Recharts 사용**: 15개 파일 (전부 ResponsiveContainer)
- **차트/그래프 컴포넌트**: 30개 파일
- **가상화 라이브러리**: 0건 (미도입)
- **분석 방식**: 패턴 grep + thesis/chainsight/validation/charts/screener/페이지·네비 5개 영역 병렬 심층 리딩 + layout/Header/MobileNav/MoverCard/coach 직접 확인
- **한계**: 정적 코드 분석이므로 실제 디바이스 렌더 측정·동적 콘텐츠 길이는 미반영. overflow 판정은 Tailwind 클래스 + 375px 유효폭(343px, px-4 기준) 산술 추정.
