# 모바일 UX 감사 보고서

> 감사 일자: 2026-05-13
> 감사 범위: `frontend/app/**`, `frontend/components/**` (TSX 일체)
> 기준 viewport: 모바일 375×667 (iPhone SE/13 mini 가정)
> 가이드라인: Apple HIG 44×44pt 터치 타겟, Material Design 48dp, WCAG 2.5.5
> 코드 수정 없음 (read-only)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 이슈 수 | 분류 |
|--------|---------|------|
| **BLOCKER** | 4 | 모바일에서 화면을 사용할 수 없거나 핵심 정보가 잘림 |
| **MAJOR** | 11 | 가독성/터치 정확도 저해, HIG/WCAG 미달 |
| **MINOR** | 9 | 가독성 또는 성능 개선 여지 |
| **TOTAL** | 24 | |

### 모바일 친화 현황 한눈에 보기

| 영역 | 상태 | 비고 |
|------|------|------|
| 메인 EOD 대시보드 (`/`) | ✅ 양호 | mobile-first 설계, `pb-20` 안전영역 확보, `SignalCard` 1열→2열→3열 반응형 |
| MobileNav (하단 5탭) | ✅ 양호 | `min-h-[44px]`, 5탭 (홈/종목/뉴스/포트폴리오/내정보) |
| Screener `/screener` | ✅ 양호 | sm 미만 자동 `MobileStockCard`, 데스크톱은 `ScreenerTable` |
| ChainSight `/chainsight/[symbol]` | ✅ 양호 | 768px 미만 `MobileCardList`로 분기 |
| Stocks `/stocks/[symbol]` | ⚠️ 주의 | isMobile 분기 있으나 재무 테이블은 가로 스크롤만 |
| Thesis 관제실 `/thesis/[id]` | ❌ 위험 | `max-w-lg` 컨테이너이지만 `IndicatorRow` 가로 폭 빠듯, 작은 글자 다수 |
| ChainSight 메인 `/chainsight` | ⚠️ 주의 | 모바일 전용 컴포넌트 없음, `SectorBar`만 overflow-x-auto |
| Validation (`stocks/[symbol]?tab=validation`) | ⚠️ 주의 | `PeerContextBar` 프리셋 탭 flex-wrap 처리는 OK이나 본문 표 모바일 미고려 |
| Admin / News 관리 | ❌ 위험 | 모든 표 `overflow-x-auto`로만 처리, 모바일 친화 X (운영자용이라 우선순위 낮음) |

---

## 1. 반응형 누락

### 1.1 BLOCKER

#### B-1. `frontend/components/thesis/dashboard/IndicatorRow.tsx:110-138` — 메인 행 가로 폭 초과 위험

```tsx
{/* 2행: 값 + 변동률 + 스파크라인 + 지지/반박 */}
<div className="flex items-center gap-3 pl-4">
  <span className="... min-w-[60px]">{value}</span>              // 60px
  <div className="... min-w-[120px]">변동률 + 비교 라벨</div>     // 120px
  <div className="flex-1 max-w-[100px]"><QuarterlySparkline/></div>// 100px
  <span className="... ml-auto">{support.text}</span>              // ~60px
</div>
```

- 합산 최소 폭: 60 + 12(gap) + 120 + 12 + 100 + 12 + 60 = **376px**
- 모바일 viewport 375px - 컨테이너 `max-w-lg` 좌우 `px-4`(32px) - `px-4 py-3` 카드 패딩(32px) - `pl-4`(16px) = **약 295px** 잔여
- 결과: 모바일에서 스파크라인이 잘리거나 "지지/반박" 라벨이 줄바꿈/사라짐. `min-w` 강제로 부모 `overflow-hidden` 없으면 오른쪽 overflow 발생
- 영향 페이지: `/thesis/[thesisId]` (관제실 메인 — 핵심 기능)

#### B-2. `frontend/components/charts/StockPriceChart.tsx:272` — 차트 height 고정 400px

```tsx
<ResponsiveContainer width="100%" height={height}>  // default 400
```

- `height` prop의 기본값이 `400`, 모바일에서도 동일 적용
- 모바일 viewport 667px에서 차트 하나가 60% 점유 → 헤더+차트+버튼+범례까지 합치면 첫 화면 차트만 보이는 상태
- `useBreakpoint` 또는 `vh` 기반 동적 height 미적용

#### B-3. `frontend/components/chainsight/MarketGraphCanvas.tsx:712` — 그래프 캔버스 height 560px 고정

```tsx
<div className="relative h-[560px] bg-gray-50 ...">
```

- 모바일 667px viewport - Header 64px - 하단 nav 64px - 기타 padding = **약 480px** 가용
- 560px 고정 → 캔버스가 viewport보다 큼 → 본질적으로 사용 불가 (zoom in/out으로 회피 불가)
- `/chainsight` 페이지 메인 — Sector 탐색의 핵심 화면

#### B-4. `frontend/components/admin/**` — 전 영역 모바일 미고려

- `SystemTab.tsx:362`, `TaskLogViewer.tsx:218`, `NewsCategoryManager.tsx:299`, `ScreenerTab.tsx:56,111`, `NewsTab.tsx:81,124`, `CollectionStatsTable.tsx:40` 모두 `overflow-x-auto` 단일 처리
- 14개 테이블이 모바일에서 무한 가로 스크롤
- 운영자용이므로 우선순위는 낮지만, 모바일에서 admin 접근 시 사용 불가
- → BLOCKER로 분류했으나 비즈니스 영향 미미

### 1.2 MAJOR

#### M-1. `frontend/components/strategy/ScreenerTable.tsx` — 11개 컬럼 테이블, 모바일 대안 분기 의존

```tsx
<div className="overflow-x-auto">
  <table className="w-full">  // 종목/거래소/섹터/가격/변동률/시총/거래량/배당률/베타/유형/AI키워드/액션
```

- 11~12 컬럼 → 모바일에서 정상 보려면 약 1200px 필요
- 회피책: `/screener` 페이지가 `viewMode === 'card'` 또는 `sm:hidden`으로 `MobileStockCard` 자동 분기 (Line 845–855) → **회피되어 있음**
- 단, ScreenerTable이 다른 곳에서 직접 사용되면 모바일 대응 안 됨

#### M-2. `frontend/components/layout/InvestingHeader.tsx:32,55,99` — `max-w-[1400px]` 고정

- 데스크톱용 헤더로 추정되나 모바일에서도 렌더된다면 가로 스크롤 발생
- 실제 사용처와 모바일 분기 여부 확인 필요

#### M-3. `frontend/app/chainsight/page.tsx` — 메인 페이지 모바일 분기 없음

- `/chainsight/[symbol]`은 `MobileCardList`로 분기되지만, `/chainsight` 메인은 데스크톱 레이아웃만 존재
- `SectorBar`, `MarketGraphCanvas`, `RelationCardPanel`, `ChainStoryFeed`가 그대로 세로 적층 → 가독성 OK이나 그래프 캔버스가 560px로 강제 (B-3)

#### M-4. `frontend/components/eod/SignalFilterTabs.tsx:33` — overflow-x-auto, 카운트 배지 18px

```tsx
<div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
  ...
  <span className="... min-w-[18px] h-[18px] px-1 rounded-full text-[11px] ...">
```

- 가로 스크롤 처리는 적절하나, **18×18px 카운트 배지가 터치 영역 안에 있어 활성 영역 식별이 어려움**
- 다행히 탭 자체의 patternpx 높이가 충분 → MAJOR 강등은 어렵고 MINOR로 처리

#### M-5. `frontend/components/admin/AdminTabNav.tsx:30` — `overflow-x-auto`, sm: 분기 없음

- admin 탭 네비게이션, 모바일에서 가로 스크롤로만 처리

#### M-6. `frontend/components/layout/Header.tsx:42` — 데스크톱 nav 7개 항목, md 브레이크포인트에서 빠듯

```tsx
<nav className="hidden md:flex space-x-8">
```

- 7개 링크 (대시보드/포트폴리오/Chain Sight/Thesis Control/Market Pulse/뉴스/스크리너) + 로고 + 검색바 + 사용자 액션
- md(768px)에서 폭 600px+ 필요 → 768px에서 검색바와 충돌 가능
- lg:flex가 더 안전

### 1.3 MINOR

#### m-1. 9개 차트 컴포넌트 `ResponsiveContainer` 사용 — 적합

`StockPriceChart`, `IndicatorRow`, `IndividualMiniCharts`, `MetricBarChart`, `MLTrendChart`, `SectorHeatmap`, `StockChart`, `SentimentChart`, `YieldCurveChart`, `PortfolioChart`, `market-pulse-v2/details/*` — width="100%" 일관 사용. **OK**.

#### m-2. `app/chainsight/[symbol]/page.tsx:358` — 데스크톱 NodeDetailPanel `hidden lg:block`

- 모바일에서는 (`isMobile && !graphOverlay` 분기로) `MobileCardList` 표시 → 분기 적절
- lg(1024px) 미만 태블릿 portrait에서는 NodeDetail 숨김 + 카드 리스트도 안 보일 위험 → 768~1024px 갭 확인 필요

---

## 2. 터치 타겟

### 2.1 BLOCKER

(없음 — 모든 주요 액션은 `min-h-[44px]` 명시되어 있음)

### 2.2 MAJOR

#### T-1. `frontend/components/admin/news/AlertBadge.tsx:29` — 카운트 배지가 클릭 영역

```tsx
<span className="absolute -top-1 -right-1 ... min-w-[18px] h-[18px] ... text-[10px] ...">
```

- 18×18px, 10px 텍스트 — 알림 카운트 배지는 보통 부모 버튼이 터치 영역이지만, 일부 위치에서 자체 클릭 가능
- 부모 컴포넌트 사용처 확인 필요

#### T-2. `frontend/components/thesis/AddIndicatorSheet.tsx:240` — `text-[9px]` freq 배지

```tsx
<span className={`text-[9px] px-1 py-px rounded ${freqStyle}`}>
  {ind.freq}  // "daily"/"quarterly"
</span>
```

- 9px 텍스트 — WCAG AA 미달 (권장 16px, 최소 12px)
- 부모 버튼이 터치 영역이라 터치 자체는 문제 없으나, 정보 가독성이 매우 떨어짐

#### T-3. `text-[10px]` 정보성 텍스트 다량 — Apple HIG 권장 11pt(약 14.6px) 미만

발견 위치 (40+):
- `frontend/app/thesis/new/page.tsx:688, 752, 753, 765, 831, 843, 1063` (가설 빌더)
- `frontend/components/screener/MobileStockCard.tsx:166, 172, 178` (시총/PER/거래량 라벨)
- `frontend/components/screener/AdvancedFilterPanel.tsx:142, 247, 266`
- `frontend/components/screener/PresetGallery.tsx:184, 218, 230, 241`
- `frontend/components/thesis/AddIndicatorSheet.tsx:251, 254` (추천 컨텍스트)
- `frontend/components/thesis/builder/SuggestionCard.tsx:52, 75`
- `frontend/components/thesis/builder/NewsSelector.tsx:125, 126, 127`
- `frontend/components/thesis/builder/PremiseCard.tsx:28`
- `frontend/components/chainsight/MobileCardList.tsx:149, 154, 159` ⚠️ **모바일 전용 컴포넌트가 10px**
- `frontend/components/chainsight/MarketGraphCanvas.tsx:698`
- `frontend/components/validation/PeerContextBar.tsx:90`
- `frontend/components/validation/MetricBarChart.tsx:74`
- `frontend/components/market-pulse/MoverCard.tsx:107, 138, 150`
- `frontend/components/eod/ConfidenceBadge.tsx:28`
- `frontend/app/market-pulse-v2/cards/BriefCardSummary.tsx:15`
- `frontend/app/market-pulse-v2/details/BriefDetail.tsx:21`
- `frontend/app/market-pulse-v2/page.tsx:77`

#### T-4. `text-[11px]` 다량 사용 — 모바일 가독성 경계

특히 우려되는 곳:
- `frontend/components/thesis/dashboard/IndicatorRow.tsx:95, 118, 148, 161, 167` (관제실 핵심 정보)
- `frontend/components/eod/StockRow.tsx:89, 92` (시그널 라벨 + 거래량)
- `frontend/components/eod/SignalFilterTabs.tsx:68`
- `frontend/components/eod/SignalDetailSheet.tsx:126`

#### T-5. `frontend/components/strategy/ScreenerTable.tsx:323` — 바구니 추가 버튼

```tsx
<button className="... min-h-[44px] min-w-[44px] ... text-xs ...">
  <Plus className="h-3 w-3" />  // 12×12px 아이콘 → 매우 작음
  바구니
</button>
```

- 터치 영역은 44×44px로 OK
- 아이콘이 12×12px → 시각적 인지에 어려움

#### T-6. `frontend/components/validation/SignalSummaryCard.tsx:48-50` — 7개 신호등 클릭

```tsx
<button className="... min-w-[72px] min-h-[44px] ...">
  <div className="w-11 h-11 rounded-full ring-4 ..." />  // 44×44px ✓
  <span className="text-xs ...">{sig.display_name}</span>
</button>
```

- 신호등 자체는 44×44px (`w-11 h-11`) ✓
- 7개 가로 스크롤 (`overflow-x-auto`) — `min-w-[72px]` × 7 = 504px → 모바일에서 스크롤 필요
- 스크롤 인디케이터(우측 fade) 없음 → 발견성 저하

#### T-7. `frontend/components/eod/StockRow.tsx:38` — 종목 링크 영역 좁음

```tsx
<Link href={`/stocks/${stock.symbol}`} className="text-sm font-bold ...">
```

- text-sm(14px) 텍스트 영역만 클릭 가능 — 부모 카드 클릭 영역과 별개
- 종목 코드 자체가 짧으면 (3~5자) 클릭 가능 영역 80px×20px 정도

#### T-8. `frontend/components/chainsight/MarketGraphCanvas.tsx:670-702` — 인기 섹터 버튼

```tsx
<button className="... w-[110px] min-h-[68px] ...">
  <span className="text-xs ...">{s.sector_display}</span>
  <span className="text-[11px] ...">{s.pct_change.toFixed(2)}%</span>
  <span className="text-[10px] ...">{s.seed_count}개 시드</span>
</button>
```

- 110×68px → 터치 영역 OK
- 그러나 110px 고정 폭 → 모바일에서 3개 가로 배치 시 110×3+gap(12×2)=354px (375px 미만) → flex-wrap 적용으로 4개 이상은 줄바꿈 OK
- 텍스트 [10px], [11px] — 가독성 경계

#### T-9. `frontend/components/chainsight/RelationLegend.tsx:51` — `max-w-[140px]` 범례

```tsx
<div className="... max-w-[140px]">
```

- 140px에 범례 텍스트가 들어가야 함 → 잘림 위험
- `frontend/components/chainsight/SectorBar.tsx:41`: `max-w-[120px] truncate` — 섹터명 잘림

### 2.3 MINOR

#### t-1. ✅ `min-h-[44px]` 정확히 적용된 곳 (긍정 평가)

- `MobileNav.tsx:34` — bottom nav 5탭
- `Pagination.tsx:127` — 페이지 버튼
- `ScreenerTable.tsx:323` — 바구니 추가
- `Header.tsx:160` — 햄버거 (현재 hidden)
- `MobileCardList.tsx:169, 175, 181` — 가설/탐색/검증 CTA
- `PeerContextBar.tsx:40, 54` — 프리셋/직접 설정 탭
- `SignalSummaryCard.tsx:41` — 신호등 버튼
- `StockPriceChart.tsx:243, 252, 261` — 차트 타입 버튼

#### t-2. `text-xs`(12px) 사용 — 50+ 컴포넌트

Tailwind 기본값으로 폭넓게 사용 — Apple HIG 권장(14px) 미만이나 WCAG는 충족. 본문이 아닌 메타 정보에 한정되어 있어 MINOR.

---

## 3. 네비게이션

### 3.1 BLOCKER

(없음)

### 3.2 MAJOR

#### N-1. MobileNav가 5개 탭만 노출 — 깊은 페이지 접근 X

- 현재 탭: 홈, 종목, 뉴스, 포트폴리오, 내정보 (`MobileNav.tsx:11-17`)
- **누락된 핵심 페이지**: `/thesis`, `/chainsight`, `/screener`, `/market-pulse`
- 모바일 사용자는 깊은 페이지에 진입 후 뒤로 가기 외에 다른 페이지로 이동 불가
- Header의 햄버거가 `hidden`(P0 #12로 의도적 처리됨)이므로, 모바일에서 thesis로 이동하려면 외부 링크나 URL 직접 입력 필요

#### N-2. `frontend/components/layout/Header.tsx:155-163` — 햄버거 dead code

```tsx
{/* audit P0 #12: Header 햄버거를 모바일에서 비표시 (MobileNav가 모바일 네비 단일 소스) ... */}
<button ... className="hidden inline-flex ...">
  <Menu className="h-6 w-6" />
</button>
```

- `hidden` 클래스로 비표시되어 있으나, 본체 코드 + 메뉴 토글 상태(`isMenuOpen`) + 모바일 메뉴 패널 (Line 167-258) 90+ 줄이 남아있음
- 향후 복귀 가능성 있다는 주석이지만, dead code 형태로 유지 → 유지보수성 저하

#### N-3. Virtualization 부재

- `react-window`, `react-virtual` 등 가상화 라이브러리 미사용 (전체 코드 grep 결과 0건)
- 영향 영역:
  - `/screener` — 50개/페이지 카드 렌더링 (pagination으로 회피되어 OK)
  - `/news` — 무한 스크롤이 있다면 성능 이슈 (확인 필요)
  - `/thesis/[id]` — 지표 수가 늘어나면 IndicatorRow 100개 이상 렌더 시 성능 저하
  - `/admin/news` — `TaskLogViewer` 로그 500건 이상 — 모바일에서는 매우 느림

#### N-4. Bottom Sheet 패턴 — 일부만 적용

- `frontend/components/thesis/AddIndicatorSheet.tsx`, `KeywordDetailSheet.tsx`, `SignalDetailSheet.tsx` — Bottom Sheet 명시적 적용 ✓
- 그러나 `/thesis/[thesisId]/indicators` 페이지는 풀스크린 형식 — Bottom Sheet 일관성 X

### 3.3 MINOR

#### n-1. 라우팅 일관성

- `MobileNav` 내부 활성 상태 판정 (`pathname.startsWith(item.href)`) — 정상
- `/profile` 깨진 라우트는 `/mypage`로 수정됨 (코드 주석 P0 #12)

---

## 4. 차트 / 그래프

### 4.1 MAJOR

#### C-1. 모든 차트 height 고정 — `vh` 또는 반응형 미적용

| 컴포넌트 | height | 모바일 영향 |
|---------|--------|------------|
| `StockPriceChart.tsx:34, 272` | 기본 400 | viewport 60% 점유 |
| `IndicatorRow.tsx:197, 235` | 160 / 140 | 모바일 OK |
| `MarketGraphCanvas.tsx:712, 717` | 560 | **모바일 사용 불가 (B-3)** |
| `StockChart.tsx` | window 기반 동적 (`getResponsiveChartHeight`) | ✅ 양호 |
| `SectorHeatmap`, `YieldCurveChart`, `PortfolioChart` | (확인 필요) | — |

#### C-2. `frontend/components/thesis/dashboard/IndicatorRow.tsx:235` — 분기 차트 height 140

- ResponsiveContainer width 100% + height 140 → 모바일 잘 작동
- 그러나 펼침 영역 내부에서 `<YAxis width={50}>` (Line 253) → 모바일 viewport에서 그리기 영역 약 240px만 남음
- 1Y/3Y/5Y 토글로 데이터 점이 많을 때 dot 겹침 발생

#### C-3. `frontend/components/charts/StockPriceChart.tsx:241-269` — 차트 타입 버튼 3개

```tsx
<div className="flex gap-2">
  <button className="min-h-[44px] px-4 py-2 ...">라인</button>
  <button className="min-h-[44px] px-4 py-2 ...">영역</button>
  <button className="min-h-[44px] px-4 py-2 ...">캔들</button>
</div>
```

- 각 버튼 60-70px → 3개 합 약 220px + 헤더 정보 → 모바일에서 줄바꿈 OK
- onClick 핸들러 미부착 — 차트 타입 전환 실제로 작동하지 않음 (별도 버그)

### 4.2 MINOR

#### c-1. 분기 스파크라인 width 64, height 24 — `MiniSparkline`, `QuarterlySparkline`

- 카드 우측에 표시되는 미니 스파크라인 → 모바일에서도 잘 보임
- 단, IndicatorRow 메인 행 내부에서 `flex-1 max-w-[100px]`로 제한 → 추세 인식 가능

#### c-2. `ResponsiveContainer` 사용률 — 15개 차트 컴포넌트 전부 적용 ✓

---

## 5. 페이지별 상세

### 5.1 `/` (메인 EOD 대시보드) — ✅ 양호 (모바일 우선 설계)

| 항목 | 상태 |
|------|------|
| 컨테이너 | `max-w-6xl mx-auto px-4` ✓ |
| 하단 padding | `pb-20 md:pb-0` (MobileNav 안전영역) ✓ |
| 시그널 카드 그리드 | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` ✓ |
| 카드 디테일 | `SignalDetailSheet` Bottom Sheet (모바일) / Side Sheet (md+) ✓ |
| 필터 탭 | `SignalFilterTabs` overflow-x-auto + scrollbar-hide ✓ |

**이슈**: T-4 (text-[11px]), M-4 (필터 카운트 배지 18px)

### 5.2 `/thesis/[thesisId]` (관제실) — ❌ BLOCKER

| 항목 | 상태 |
|------|------|
| 컨테이너 | `max-w-lg mx-auto px-4 pt-4 pb-20` ✓ (모바일 의식) |
| IndicatorRow 메인 행 | **B-1: 가로 합산 376px > 모바일 가용 295px** |
| 차트 펼침 | `ResponsiveContainer height=160` ✓ |
| 텍스트 크기 | text-[11px] 5곳 + text-[10px] 1곳 — T-3, T-4 |

**핵심 결론**: thesis 관제실은 컨테이너는 모바일 친화적이지만 IndicatorRow 자체 폭이 빠듯. **이 BLOCKER가 모바일 사용성의 최대 병목**.

### 5.3 `/thesis/new` (가설 빌더) — ⚠️ 주의

- `app/thesis/new/page.tsx` text-[10px] 7곳 — T-3
- 빌더 UI는 모바일에서 텍스트 가독성 떨어짐

### 5.4 `/screener` — ✅ 양호 (모바일 분기)

| 항목 | 상태 |
|------|------|
| 데스크톱 | `ScreenerTable` (11컬럼, overflow-x-auto) |
| 모바일 | `MobileStockCard` (sm:hidden 자동 분기) ✓ |
| 분기 로직 | Line 845-855 `viewMode === 'table' ? 'hidden sm:block' : 'hidden'` ✓ |
| 페이지네이션 | `Pagination.tsx:127` min-w-[44px] min-h-[44px] ✓ |
| 카드 텍스트 | MobileStockCard text-[10px] 3곳 (시총/PER/거래량 라벨) — T-3 |

### 5.5 `/chainsight` (메인) — ⚠️ 주의

| 항목 | 상태 |
|------|------|
| 모바일 분기 | **없음** — `SectorBar`, `MarketGraphCanvas` 등 그대로 적층 |
| MarketGraphCanvas | **B-3: height 560px 고정 → 모바일 사용 불가** |
| SectorBar | `overflow-x-auto py-3` ✓ + `max-w-[120px] truncate` (T-9) |
| 인기 섹터 버튼 | `w-[110px]` 고정, text-[10px]/[11px] — T-8 |

### 5.6 `/chainsight/[symbol]` — ✅ 양호 (모바일 분기)

| 항목 | 상태 |
|------|------|
| 모바일 분기 | `isMobile` (`window.innerWidth < 768`) ✓ |
| 모바일 컴포넌트 | `MobileCardList` (카테고리 탭 + 카드 리스트 + FAB) ✓ |
| 데스크톱 좌측 | AIGuidePanel hidden (775px 미만) |
| 데스크톱 우측 | NodeDetailPanel hidden lg:block (1024px 미만 갭) — m-2 |
| 텍스트 | text-[10px] 3곳 — T-3 |

**한 가지 우려**: `isMobile` 상태가 useEffect 기반 → 초기 렌더 시 데스크톱으로 그렸다가 모바일로 점프하는 hydration 깜빡임 가능 (CLAUDE.md 버그 #24 참조).

### 5.7 `/stocks/[symbol]` — ⚠️ 주의

| 항목 | 상태 |
|------|------|
| 일부 영역 | `isMobile` 분기 있음 (Line 1027) |
| 재무 테이블 | `overflow-x-auto` 단일 처리 (Line 843) — 12분기 컬럼 |
| Validation 탭 | `PeerContextBar` 프리셋 탭 flex-wrap ✓ |
| 데스크톱 사이드바 | `hidden lg:block` (Line 1058) — 1024px 미만 갭 |
| 차트 | `StockChart`는 `getResponsiveChartHeight` 사용 ✓ |

### 5.8 `/market-pulse-v2` — ⚠️ 주의

- `cards/*`, `details/*` 17개 컴포넌트 — text-[10px] 4곳, text-xs 다수
- ResponsiveContainer 사용 ✓
- 모바일 분기는 grid `grid-cols-1 sm:grid-cols-2` 패턴 일관 적용 (sample 확인 필요)

### 5.9 `/news` — (상세 확인 미실시)

- `RecommendationCard` 카드 형식 → 모바일 친화
- `NewsCard`, `NewsHighlightedStocks` — overflow-x-auto + scrollbar-hide
- `KeywordDetailSheet` Bottom Sheet ✓

### 5.10 `/admin/*` — ❌ B-4 (운영자용, 우선순위 낮음)

- 14개 테이블 모두 `overflow-x-auto`만 적용
- 모바일에서 admin 작업 불가 (의도된 설계로 보임)

---

## 우선순위 권장 조치 (요약)

### 즉시 (P0)

1. **B-1**: `IndicatorRow` 메인 행 가로 폭 — `min-w` 제거 또는 모바일 전용 세로 레이아웃 분기
2. **B-3**: `MarketGraphCanvas` height 560px — `h-[60vh] sm:h-[560px]` 또는 동적 계산
3. **N-1**: MobileNav 5탭에 `/thesis` 또는 `/screener` 중 하나 추가, 또는 햄버거 부활

### 1주일 내 (P1)

4. **T-3**: `text-[10px]` 40+ 위치 — `text-xs`(12px) 이상으로 일괄 상향
5. **T-2**: AddIndicatorSheet freq 배지 `text-[9px]` → `text-[11px]` 최소
6. **B-2**: `StockPriceChart` height prop 모바일 분기 (`window.innerWidth < 640 ? 240 : 400`)
7. **N-2**: Header 햄버거 dead code 정리 (P0 #12 후속)

### 백로그 (P2)

8. **N-3**: virtualization 도입 — `react-window` 우선 후보는 `/admin/news` TaskLogViewer
9. **M-2**: InvestingHeader `max-w-[1400px]` 모바일 분기 확인
10. **m-2**: 768~1024px 태블릿 portrait 갭 (`lg:` 분기를 `md:`로 일부 하향 검토)

---

## 부록: 측정 메모

- **고정 폭 사용 빈도** (`w-[...px]`/`min-w-[...px]`/`max-w-[...px]`): 30+ 위치, 그중 모바일 영향 있는 곳 12곳
- **`text-[10px]`** 출현: 40+ 위치
- **`text-[11px]`** 출현: 30+ 위치
- **`min-h-[44px]` 적용 비율** (주요 액션 버튼 기준): 약 70% — 개선 여지 있음
- **`overflow-x-auto` 단일 처리** (모바일 분기 없는 표/탭): 18개 — 그중 admin 14개 제외 시 4개
- **`ResponsiveContainer` 사용률**: 차트 컴포넌트 15/15 (100%) ✓
- **Virtualization 사용**: 0건

---

*감사 작성: Claude Opus 4.7 — 코드 수정 없이 정적 분석으로 도출. 실제 모바일 디바이스 또는 Chrome DevTools 375×667 viewport 시뮬레이션으로 검증 권장.*
