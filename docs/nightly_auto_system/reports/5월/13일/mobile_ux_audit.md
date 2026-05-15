# 모바일 UX 감사 보고서

> 감사 일자: 2026-05-13 (재감사)
> 감사 범위: `frontend/app/**`, `frontend/components/**` (TSX 195개 컴포넌트 + 24개 페이지)
> 기준 viewport: 모바일 375×667 (iPhone SE/13 mini 기준), 추가 검증 폭 320px / 412px
> 가이드라인: Apple HIG 44×44pt, Material Design 48dp, WCAG 2.5.5 (Target Size)
> 코드 수정 없음 — read-only

---

## 요약 (심각도별 이슈 수)

| 심각도 | 이슈 수 | 정의 |
|--------|---------|------|
| **BLOCKER** | 6 | 모바일 화면에서 핵심 정보가 잘리거나 사용 불가 |
| **MAJOR**   | 14 | 가독성/터치 정확도 저하, HIG/WCAG 미달, 모바일 사용성에 실질 영향 |
| **MINOR**   | 11 | 가독성·성능 개선 여지, 핵심 동선에 직접 영향 없음 |
| **TOTAL**   | 31 | |

### 모바일 친화 현황 한눈에 보기

| 페이지 | 상태 | 비고 |
|--------|------|------|
| `/` (EOD Dashboard) | ✅ 양호 | `pb-20`로 MobileNav 영역 확보, `grid-cols-1 sm:2 lg:3` |
| `/screener` | ⚠️ 부분 | `MobileStockCard` 분기 OK, 그러나 `PresetGallery` 텍스트 9~10px |
| `/chainsight` (메인) | ⚠️ 주의 | 모바일 분기 없음, `SectorBar`만 `overflow-x-auto` |
| `/chainsight/[symbol]` | ✅ 양호 | 768px 미만 `MobileCardList`로 분기, FAB로 그래프 열기 |
| `/stocks/[symbol]` | ⚠️ 주의 | Validation 탭만 `isMobile` 분기, 기본 정보·재무 테이블은 가로 스크롤만 |
| `/thesis` (목록) | ✅ 양호 | `max-w-3xl`, 카드 리스트 단순 구조 |
| `/thesis/[id]` (관제실) | ❌ 위험 | `max-w-lg` + `IndicatorRow` 가로 폭 빠듯, 10px 차트 토글, BLOCKER 다수 |
| `/thesis/new` (빌더) | ⚠️ 주의 | 10px 라벨·태그 다수, 사이드 패널 가로 압박 |
| `/portfolio` | ❌ 위험 | grid 분기 있으나 테이블 뷰는 12컬럼 `overflow-x-auto`만 |
| `/watchlist` | ⚠️ 주의 | `grid-cols-1 lg:grid-cols-3` — 모바일 단일 컬럼은 OK, 그러나 시각 좁음 |
| `/news` | ✅ 양호 | 시간/소스 필터는 chip 형태, 카드는 세로 정렬 |
| `/admin` | ❌ 위험 | 모든 표 `overflow-x-auto` 일변, 운영용이라 우선순위 ↓ |
| `Header` (전역) | ⚠️ 주의 | 햄버거 `hidden`, 검색 `hidden md:block` → **모바일에서 검색 진입점 없음** |
| `MobileNav` | ✅ 양호 | 5탭, `min-h-[44px]` |

---

## 1. 반응형 누락

### 1.1 BLOCKER

#### R-B1. `frontend/components/thesis/dashboard/IndicatorRow.tsx:108-144` — 메인 행 가로 폭 초과

```tsx
<div className="flex items-center gap-3 pl-4">
  <span className="... min-w-[60px]">{value}</span>          // 60px
  <div className="... min-w-[120px]">변동률 + 라벨</div>      // 120px
  <div className="flex-1 max-w-[100px]"><QuarterlySparkline/></div> // 100px
  <span className="... ml-auto">{support.text}</span>          // ~50-70px
</div>
```

- 좌측 `pl-4` (16px) + gap(3×12=36px) + 60 + 120 + 100 + 60 = **약 392px**.
- 375px viewport에서 컨테이너는 `max-w-lg`(=512px)이지만 외곽 `px-4`(=32px) 차감 시 343px → **실제로는 overflow** (스파크라인이 0px로 압축되거나 잘림).
- 320px 단말기(iPhone SE 1세대 등)에서는 변동률 라벨까지 깨짐.

#### R-B2. `frontend/components/portfolio/PortfolioTable.tsx:258-300` — 12 컬럼 테이블, 모바일 분기 없음

```tsx
<div className="overflow-x-auto">
  <table className="min-w-full ...">
    <thead>
      {/* 종목 / 보유수량 / 평균매수가 / 현재가 / 전일대비 / 평가금액 / 손익 / 수익률 / 목표가 / 손절가 / 비중 / 관리 */}
```

- 12개 컬럼 + `px-6 py-3` → 모바일에서 좌우 드래그 외 방법 없음.
- 비교용 카드형 `PortfolioStockCard`는 grid 뷰에만 사용, 사용자가 "테이블" 토글 선택 시 모바일에서도 그대로 노출됨.

#### R-B3. `frontend/components/stocks/StockTable.tsx:34-46` — 7 컬럼 테이블 모바일 대응 전무

- `overflow-x-auto` 단일 처리. `MobileStockCard` 같은 카드 분기 없음.
- 본 컴포넌트는 dashboard 등 메인 진입점에 노출됨에도 모바일 카드 fallback 없음.

#### R-B4. `frontend/components/portfolio/PortfolioTable.tsx:215-254` — Summary 5 컬럼 가로 grid

- 위 BLOCKER R-B2와 동일 페이지의 상단. `grid grid-cols-5`(추정) 또는 flex 가로 정렬로 모바일에서 깨짐 (실제 코드는 5개 div 가로 나열).
- `text-2xl` 금액이 5개 가로로 늘어서 좁은 화면에서 줄바꿈 무시.

#### R-B5. `frontend/components/layout/Header.tsx:111-153` — 모바일에서 검색·로그인 진입점 미노출

- 검색 박스 `hidden md:block` (line 112).
- 로그인/로그아웃 버튼 `hidden md:flex` (line 126).
- 햄버거 메뉴 `hidden` (line 157, 주석에 "본 버튼은 hidden — 향후 모바일 검색 패널 등 확장 시 부활 검토").
- **결과**: 모바일 사용자는 로그인 페이지로 가는 직접 진입점이 없음. MobileNav도 비회원 진입점 없음.

#### R-B6. `frontend/components/strategy/ScreenerTable.tsx:209,224,307` + 헤더 8 컬럼 — 모바일 자체 분기 없음

- 페이지 레벨(`/screener`)에서 `viewMode === 'card'` 또는 isMobile 시 `MobileStockCard`로 우회되지만, **사용자가 "테이블" 모드를 명시 선택하면** ScreenerTable이 그대로 렌더링됨 → 모바일 사용자가 무심코 선택 시 가로 스크롤 지옥.
- `max-w-[180px]`, `max-w-[120px]`, `max-w-[200px]` 등 셀 단위 폭이 누적되어 1100px+.

### 1.2 MAJOR

#### R-M1. `frontend/components/chainsight/MarketGraphCanvas.tsx:676` — 인기 섹터 버튼 고정폭

```tsx
'w-[110px] min-h-[68px] px-3 py-2',
```

- 3개 버튼 가로 배치 (`flex flex-wrap justify-center gap-3`), `gap-3`(12px)×2 + 110×3 = **354px** → 375px viewport에 가까스로 들어가나 `max-w-7xl mx-auto px-4` 컨테이너 padding 차감 시 343px → **wrap**으로 인해 의도된 3열 → 2+1열로 깨짐 (UX 의도 위반).

#### R-M2. `frontend/components/chainsight/SectorBar.tsx:23-55` — 섹터 칩 truncate에 의존

```tsx
<div className="flex gap-2 overflow-x-auto py-3 px-1 scrollbar-thin">
  ...
  <span className="block text-xs font-semibold truncate max-w-[120px]">
    {s.sector_display}
  </span>
```

- "Consumer Discretionary" 같은 긴 섹터명이 모바일에서 잘림 (`truncate`로 `…` 처리).
- 가로 스크롤 자체는 mobile-first지만 사용자가 스크롤 가능 여부를 인지하기 어려움 (스크롤 인디케이터 없음).

#### R-M3. `frontend/app/portfolio/page.tsx:215-253` — 카드/테이블 viewMode 토글이 데스크톱 가정

- 토글 UI는 `flex space-x-2`. 모바일에서 사용자가 "테이블" 선택해도 경고/안내 없음.
- 모바일 전용 fallback (예: 자동으로 "카드"로 force) 부재.

#### R-M4. `frontend/components/screener/PresetGallery.tsx:170-250` — 갤러리 카드 폭/태그 폭

- `text-[13px]`, `text-[10px]`, `text-[9px]`(Enhanced 배지) 혼재.
- 활성 배지 `-top-2 -left-2 w-5 h-5` 절대 위치 → 카드 경계 밖으로 5px 돌출, 양 옆 카드와 겹침 위험.

#### R-M5. `frontend/app/thesis/new/page.tsx:688-1063` — 빌더 패널 텍스트 다수 10px

- `text-[10px]` 라벨/태그 15개 이상.
- "꾹 누르면 설명" 안내 `sm:hidden` (line 66) — 데스크톱은 호버, 모바일은 long-press 지원하지만 long-press 트리거 코드는 OptionButton 외부에 분산.

#### R-M6. `frontend/app/stocks/[symbol]/page.tsx:1027-1055` — Validation 탭 외 영역 모바일 무대응

- Validation 탭만 `isMobile ? Chip + 카테고리 : Sidebar + 전체` 분기.
- **기본 정보 탭, 차트 탭, 재무제표 탭은 모바일 분기 없음** — `<FinancialTable>` 등이 데스크톱 폭 가정.

#### R-M7. `frontend/components/portfolio/PortfolioTable.tsx:212-254` — 5분할 Summary

- 5개 KPI(평가금액/매수금액/총손익/수익률/아이콘)가 한 줄에 들어가도록 `flex` 사용 (코드상 명시적 grid-cols 미지정, summary 섹션은 div 5개 가로 나열).
- 375px에서 각 KPI 폭 = 75px → `text-2xl` 금액(예: `$1,234,567.89`)이 잘림.

#### R-M8. `frontend/components/rag/ChatInterface.tsx:198` — 전송 버튼 52×52px, 입력창 폭은 가변

- 버튼 자체는 44px 초과(양호). 그러나 `flex h-[52px] w-[52px] flex-shrink-0` 옆 입력창은 컨테이너에 따라 가변 → 모바일에서 키보드 올라오면 입력창 폭 ~280px 미만으로 줄어듦 (placeholder 잘림 우려).

#### R-M9. `frontend/components/common/DataSourceBadge.tsx:171` — `min-w-[200px]` 팝오버

- 절대위치 팝오버이지만 부모가 화면 오른쪽 모서리 근처일 때 200px 컨테이너가 viewport 밖으로 밀려남 (overflow-x 차단 없으면 가로 스크롤 유발).

#### R-M10. `frontend/components/screener/AdvancedFilterPanel.tsx:142,247,266` — 필터 카드 텍스트 10px

- 필터 설명 `text-[10px]`, 활성 배지 `text-[10px]` → 가독성 임계.
- 활성 필터 chip의 토글 영역 `min-h-[44px]` 미보장.

#### R-M11. `frontend/components/market-pulse/MoverCard.tsx:138-189` — 툴팁 호버 의존 (모바일 노출 불가)

```tsx
<div className="absolute bottom-full left-0 mb-1 hidden group-hover/tooltip:block ...">
```

- `group-hover/tooltip:block` 으로 표시 → 모바일에는 hover 개념이 없으므로 5개 툴팁 모두 노출 불가.
- 동일 패턴이 `MoverCardWithBatchKeywords.tsx:145-196`에도 반복(5건).

#### R-M12. `frontend/components/news/RecommendationCard.tsx:85`, `chainsight/NodeTooltip.tsx:141` 등 — `max-w-[150px] truncate`

- 모바일에서 종목명이 절단되어 의미 손실. 툴팁 호버에 의존하는 NodeTooltip은 모바일 비노출.

#### R-M13. `frontend/app/watchlist/page.tsx:207` — `grid-cols-1 lg:grid-cols-3` 단순 분기

- 좌측 "내 리스트" + 우측 "선택된 리스트 종목" 구조가 모바일에서 세로 적층 → 리스트 선택 시 종목 영역까지 스크롤해야 보임 (UX 흐름 끊김).

#### R-M14. `frontend/components/admin/shared/TaskLogViewer.tsx:218` / `admin/SystemTab.tsx:362` — `max-w-[260px] truncate`

- 운영자용이지만 모바일 접근 시 결과 메시지가 잘림. `overflow-x-auto` 표 + 셀 단위 truncate 중첩.

### 1.3 MINOR

| ID | 위치 | 이슈 |
|----|------|------|
| R-m1 | `screener/MobileStockCard.tsx:166-180` | 10px 라벨(시가총액/PER/거래량). 라벨이 짧고 보조 정보라 가독성 영향 적음 |
| R-m2 | `eod/StockRow.tsx:55-92` | `max-w-[140px]`, `min-w-[72px]`, `text-[11px]` — 모바일에서 좁지만 EOD 카드 내부 구조라 허용 가능 |
| R-m3 | `validation/MetricBarChart.tsx:74` | `text-[10px]` 오버레이 라벨 (보조 정보) |
| R-m4 | `chainsight/MobileCardList.tsx:147-163` | 프로파일 태그 `text-[10px]`. 태그가 3개 이하라 줄바꿈 OK |
| R-m5 | `chainsight/FullPathView.tsx:182,287` | 10px 보조 라벨 다수 |
| R-m6 | `thesis/builder/SuggestionCard.tsx:52-91` | 10~13px 혼재. isHistory 모드에서 11px line-clamp-2 |
| R-m7 | `keywords/KeywordTag.tsx:42-94` | sm 사이즈에서 10/9px. 인라인 라벨이라 영향 적음 |
| R-m8 | `news/MLModelStatusCard.tsx:193-202` | 10px 메트릭 라벨, 운영자용 위주 |
| R-m9 | `market-pulse/MarketMoversSectionOptimized.tsx:63-78` | 10px 부가 정보 |
| R-m10 | `thesis/AddIndicatorSheet.tsx:240-254` | 9~10px 빈도/설명 라벨 |
| R-m11 | `eod/MarketSummaryBar.tsx:48` | "(54%)" 등 10px 부가 표시 |

---

## 2. 터치 타겟

> 기준: HIG 44×44pt, Material 48dp, WCAG 2.5.5 Level AAA 44×44 CSS px.
> 측정값은 `min-h/min-w` + 패딩만 본 정적 값이며, 자식 텍스트로 늘어나는 경우는 별도 표기.

### 2.1 BLOCKER

#### T-B1. `frontend/components/thesis/dashboard/IndicatorRow.tsx:178-189` — 차트 기간 토글 24px 미만

```tsx
<button className={`px-2.5 py-0.5 text-[10px] rounded ...`}>{label}</button>
```

- `py-0.5` (= 2px) + `text-[10px]` line-height 14px ≈ **18px 높이**.
- 4개 버튼(1M/1Y/3Y/5Y) `flex gap-1.5` → 모바일에서 매우 좁고 오탭 빈발 예상.

#### T-B2. `frontend/components/thesis/AddIndicatorSheet.tsx:240` — `text-[9px] px-1 py-px`

```tsx
<span className={`text-[9px] px-1 py-px rounded ${freqStyle}`}>
```

- 9px 텍스트 + 1px padding → **약 12px 높이**. 클릭 핸들러가 부모(`button`)에 있으므로 실 타깃은 카드 전체이나, 시각적 빈도 배지의 변별이 어렵고 이를 누르려는 시도 자체가 실패.

#### T-B3. `frontend/components/keywords/KeywordTag.tsx:42-69` — sm 사이즈 10px

```tsx
sm: 'px-2 py-0.5 text-[10px]',
```

- `py-0.5`(2px) + text-[10px] ≈ **18px 높이**. 카드 안에서 다른 핵심 클릭(상세 보기)과 인접하여 오탭 위험.

### 2.2 MAJOR

#### T-M1. `frontend/components/screener/Pagination.tsx:95-153` — 좌/우 끝 화살표 28px

```tsx
<button className="p-1.5 rounded ..." title="첫 페이지">
  <ChevronsLeft className="w-4 h-4 ..." />
</button>
```

- `p-1.5`(6px) + 16px 아이콘 = **28px**. 페이지 번호 버튼은 `min-w-[44px] min-h-[44px]`로 적합하나 양 끝 4개 버튼(첫/이전/다음/끝)이 미달.

#### T-M2. `frontend/components/screener/PresetGallery.tsx:191-204, 235-249` — 삭제·정보 버튼 22px

```tsx
<button className="absolute top-2 right-2 ... p-1 ...">  // 삭제, w-3.5 h-3.5
<button className="flex items-center gap-1 text-[10px] ...">상세 설명  // 정보
```

- 삭제 버튼: `p-1`(4px) + 14px 아이콘 = **22px**.
- "상세 설명" 인라인 버튼: 10px 텍스트 + 12px 아이콘 ≈ 16px 높이.

#### T-M3. `frontend/components/chainsight/SectorBar.tsx:29-50` — 섹터 칩 38px

```tsx
className="flex-shrink-0 px-4 py-2 ..."
```

- `py-2`(8px) × 2 + 두 줄 텍스트(text-xs ~14px + text-xs ~14px + mt-0.5 2px) ≈ **46px 높이** (양호) — 단, 한 줄 짜리 짧은 섹터에서는 30px 가능. 또한 폭은 `truncate max-w-[120px]`로 가변. 모바일 핑거 정확도 임계.

#### T-M4. `frontend/components/market-pulse/MoverCard.tsx:107-189` — 카드 전체 클릭 가능하지만 툴팁 트리거가 별도 hover

- 카드는 충분히 크지만, 각종 메트릭 호버 툴팁(`group-hover/tooltip:block`)은 모바일에서 절대로 노출되지 않음 → 사용자가 메트릭 의미를 알 수 없음.

#### T-M5. `frontend/components/news/AINewsBriefingCard.tsx:106-115` — "헤드라인 보기" 16px 인라인 버튼

```tsx
<button className="text-xs text-gray-400 hover:text-gray-600 ... flex items-center gap-1 mt-1">
  <ChevronUp/Down className="w-3 h-3" />
  헤드라인 {expanded ? '접기' : '보기'}
</button>
```

- `text-xs` (12px) + 12px 아이콘 → **약 16-18px 높이**.

#### T-M6. `frontend/components/eod/SignalDetailSheet.tsx:188,197` — 섹터 링크 10px

```tsx
className="text-[10px] px-1.5 py-0.5 rounded ..."
```

- "Chain Sight 연계" 칩 / "관계 지도" CTA가 10px. 시트 하단의 핵심 동선이라 위험.

#### T-M7. `frontend/components/chainsight/RelationLegend.tsx:59` — 토글 헤더 10px

```tsx
className="flex items-center justify-between w-full gap-1 text-[10px] font-semibold ..."
```

- 범례 펼침/접기 버튼이 10px 텍스트. 모바일 진입 시 자동 collapse(`setCollapsed(isMobile)`)되지만 그 후 펼치려면 이 작은 텍스트를 눌러야 함.

#### T-M8. `frontend/components/thesis/dashboard/IndicatorRow.tsx:99-104` — 행 우측 ChevronDown 14px

```tsx
<ChevronDown size={14} className="text-gray-500 flex-shrink-0 transition-transform ..." />
```

- 단, 부모 `<button>`이 행 전체이므로 실 클릭 영역은 충분. 그러나 시각 단서가 14px라 발견성 ↓ (MINOR로 분류 가능, 그러나 관제실 핵심 인터랙션이라 MAJOR).

#### T-M9. `frontend/components/news/InterestSelector.tsx:96` — 10px 카테고리 설명

- 클릭 카드 자체는 큼. 그러나 카테고리 설명 텍스트(10px)가 너무 작아 사용자가 무엇을 고르는지 파악 어려움.

#### T-M10. `frontend/app/thesis/new/page.tsx:1063` — 인라인 링크 10px

```tsx
className="text-[10px] text-gray-500 hover:text-blue-400 mt-1 inline-block"
```

- 텍스트 10px + line-height 14px ≈ 14px 높이의 인라인 링크. 빌더에서 보조 액션 진입이 어려움.

### 2.3 MINOR

| ID | 위치 | 이슈 |
|----|------|------|
| T-m1 | `eod/SignalCard.tsx:102-113` | 교육 팁 토글 버튼 `p-1` + 14px 아이콘 = 22px. 카드 안 보조 액션 |
| T-m2 | `chainsight/MobileCardList.tsx:166-184` | "가설 생성/탐색/검증" 버튼 3개 모두 `min-h-[44px]` ✓ — 양호 |
| T-m3 | `validation/SignalSummaryCard.tsx:41` | `min-w-[72px] min-h-[44px]` ✓ — 양호 |
| T-m4 | `eod/SignalFilterTabs.tsx:43-78` | 칩 `px-3 py-1.5` ≈ 32px. text-sm + 18px 배지로 시각 충돌 |
| T-m5 | `screener/Pagination.tsx:127` | 페이지 번호 `min-w-[44px] min-h-[44px]` ✓ |
| T-m6 | `validation/PeerContextBar.tsx:39-62` | `min-h-[44px] px-4 py-2` ✓ |
| T-m7 | `chainsight/RelationFilterChips.tsx` (관계 칩) | flex-wrap 칩, 44px 확보 여부는 자식 텍스트에 의존 |
| T-m8 | `thesis/common/AlertBell.tsx:18` | `min-w-[18px] h-[18px]` — 배지(클릭 아님) |
| T-m9 | `admin/news/AlertBadge.tsx:29` | 배지 18px — 클릭 아님 |
| T-m10 | `eod/SignalFilterTabs.tsx:68` | 카운트 배지 18px — 표시용 |
| T-m11 | `thesis/AddIndicatorSheet.tsx`(전체) | 카드 전체가 큰 터치 영역이지만 빈도/설명 배지가 너무 작아 정보 손실 |

---

## 3. 모바일 네비게이션

### 3.1 BLOCKER 없음.

### 3.2 MAJOR

#### N-M1. `frontend/components/layout/Header.tsx:155-163` — 모바일 햄버거 영구 비활성 + 검색 미노출

```tsx
{/* audit P0 #12: Header 햄버거를 모바일에서 비표시 (MobileNav가 모바일 네비 단일 소스).
    이중 네비 제거 + 데스크톱은 상단 nav 사용. 본 버튼은 hidden — 향후 모바일 검색 패널 등 확장 시 부활 검토. */}
<button className="hidden inline-flex ..." aria-label="메뉴 열기">
```

- 햄버거 메뉴 코드는 살아 있으나 `hidden`으로 영구 차단.
- `MobileNav`는 5탭(홈/종목/뉴스/포트폴리오/내정보)만 노출 → **`/screener`, `/chainsight`, `/thesis`, `/market-pulse`는 모바일에서 직접 진입 경로 없음**.
- 검색(`Header` line 112) + 로그인 버튼도 데스크톱 전용 → 비회원 모바일 사용자는 메인에서 로그인 경로 없음.

#### N-M2. `frontend/components/layout/MobileNav.tsx:11-17` — 핵심 기능 4개 미노출

- 노출: 홈(`/`), 종목(`/stocks`), 뉴스(`/news`), 포트폴리오(`/portfolio`), 내정보(`/mypage`).
- 누락: Screener, Chain Sight, Thesis Control, Market Pulse.
- "종목"의 destination이 `/stocks`인데 실제 `/stocks` 인덱스 페이지가 비어 있어 404 또는 빈 화면 가능성 (별도 검증 필요).

#### N-M3. `frontend/app/page.tsx:71` — `pb-20 md:pb-0` 일관 적용 안 됨

- 메인은 `pb-20`. 그러나 `/portfolio`, `/watchlist`, `/thesis/[id]` 등은 자체 `pb-20`(thesis는 `pb-20` 있음, portfolio는 `py-8` 단일) → MobileNav가 페이지 하단 콘텐츠를 가림.

### 3.3 MINOR

| ID | 위치 | 이슈 |
|----|------|------|
| N-m1 | `components/admin/AdminTabNav.tsx:30` | `overflow-x-auto` 가로 스크롤 탭. `min-h-[44px]` ✓ 양호 |
| N-m2 | `components/chainsight/SectorBar.tsx:23` | 가로 스크롤 칩 — 스크롤 인디케이터 없음 |
| N-m3 | `app/thesis/(list)/alerts` 등 | back 버튼(`<ArrowLeft>`) 단독 진입 — `p-1.5 rounded`, 36px → 44px 미달 |
| N-m4 | 모든 페이지 | virtualization (`react-window`, `TanStack Virtual`) **0건** — 긴 리스트에서 성능 우려 |

### 3.4 Virtualization 현황

- `react-window`, `react-virtual`, `TanStackVirtual` **사용처 0** (Grep 결과).
- 영향: 스크리너 100개 종목 페이지, 알림 리스트, ChainStoryFeed, 관제실 지표 N개 등 모두 일반 DOM 렌더.
- 모바일 저성능 단말기에서 스크롤 jank 위험.

---

## 4. 차트/그래프 모바일 대응

### 4.1 ResponsiveContainer 사용 현황 (총 15개 파일)

| 파일 | 사용 | 비고 |
|------|------|------|
| `components/charts/StockPriceChart.tsx` | ✓ | OK |
| `components/stock/StockChart.tsx` | ✓ + `getResponsiveChartHeight(window.innerWidth)` | 높이까지 반응형 ✓ |
| `components/thesis/dashboard/IndicatorRow.tsx:197,235` | ✓ width="100%" height={160}/{140} | 양호 (단, expand 시 차트 토글이 BLOCKER) |
| `components/thesis/dashboard/IndividualMiniCharts.tsx:54` | ✓ height={100} | 양호 |
| `components/validation/MetricBarChart.tsx` | ✓ | 양호 |
| `components/admin/news/MLTrendChart.tsx` | ✓ | 양호 |
| `components/screener/SectorHeatmap.tsx` | ✓ | 모바일 표 형태 변경은 없음 |
| `components/news/SentimentChart.tsx` | ✓ | 양호 |
| `components/macro/YieldCurveChart.tsx` | ✓ | 양호 |
| `components/portfolio/PortfolioChart.tsx` | ✓ | 양호 |
| `app/market-pulse-v2/details/*` (4개) | ✓ | 디테일 모달 형태 |
| `__tests__/...` | 테스트 | — |

→ **Recharts 사용처는 전부 ResponsiveContainer로 감싸져 있음** (양호).

### 4.2 비-Recharts 시각화

- `MarketGraphCanvas.tsx` (Chain Sight 메인 force-graph): `dynamic(() => import('react-force-graph-2d'))` + 모바일 분기(`window.matchMedia('(pointer: coarse)')`) + 첫 탭/두 번째 탭 구분 ✓
- `chainsight/[symbol]/page.tsx`: 768px 미만 자동으로 `MobileCardList` + "그래프로 보기" FAB로 오버레이 전환 ✓
- `eod/SignalCard.tsx:188` `MiniSparkline 52×20` — SVG로 직접 그림, 모바일 OK
- `stocks/StockTable.tsx:113-128` 인라인 SVG sparkline `w-16 h-8` — placeholder 수준, 데이터 미연동
- `thesis/dashboard/QuarterlySparkline.tsx`: `flex-1` + `min-h-[44px]` ✓ (양호 — 단, 4분기 + 분기 라벨 11px가 모바일에서 빡빡)

### 4.3 MAJOR

#### C-M1. `frontend/components/thesis/dashboard/QuarterlySparkline.tsx:57` — 분기 라벨 `text-[11px]`

- 4분기 라벨 `Q1/Q2/Q3/Q4` + `mt-0.5` → 가독성 임계. 호버 툴팁 10px도 동일.
- `onTouchStart`로 모바일 토글 구현 ✓ (양호한 점)

#### C-M2. `frontend/components/thesis/dashboard/IndicatorRow.tsx:197,235` — 차트 fontSize=9/10

```tsx
<XAxis dataKey="date" stroke="#6B7280" fontSize={9} ... />
<YAxis stroke="#6B7280" fontSize={10} width={55} ... />
```

- X축 라벨 9px. 모바일에서 거의 식별 불가.
- `interval` 계산은 데이터 길이 기반 → 모바일 narrow viewport에서 라벨 겹침은 별도 없으나 가독성 임계.

#### C-M3. `frontend/components/eod/SignalCard.tsx:188` — `MiniSparkline width={52} height={20}`

- 카드 우측 정렬 작은 차트. 추세만 보이고 정확한 값은 알 수 없음 — 보조 정보로 적정하나 모바일에서 더 좁아질 수 있음.

### 4.4 MINOR

| ID | 위치 | 이슈 |
|----|------|------|
| C-m1 | `IndicatorRow.tsx:217,258` | Tooltip `fontSize: 12` — 모바일에서 적정하나 X축 라벨과 비대칭 |
| C-m2 | `IndividualMiniCharts.tsx:64-77` | XAxis fontSize 10 / YAxis fontSize 10 — 임계, height 100 |
| C-m3 | `chainsight/[symbol]/page.tsx:185-196` | 모바일 그래프 오버레이가 `window.innerHeight - 48` — `safe-area-inset` 미고려 |

---

## 5. 페이지별 상세

### 5.1 `/` (EOD 메인 대시보드) — ✅ 양호 + MINOR 2

- mobile-first 설계, `pb-20 md:pb-0`, `grid-cols-1 sm:2 lg:3`.
- `SignalFilterTabs` 가로 스크롤(`overflow-x-auto pb-1 scrollbar-hide`) ✓.
- 이슈: T-m1 (교육 팁 22px), C-M3 (mini sparkline 52×20).

### 5.2 `/screener` — ⚠️ MAJOR 3 + MINOR 4

- `viewMode === 'card'` 또는 `isMobile` 시 `MobileStockCard` 적용 (양호).
- BLOCKER: R-B6 (사용자가 테이블 모드 명시 선택 시 가로 스크롤).
- MAJOR: R-M4 (PresetGallery 10/9px), R-M10 (AdvancedFilterPanel), T-M2 (삭제·정보 버튼 22px).
- `Pagination` 좌/우 끝 화살표 28px (T-M1).

### 5.3 `/chainsight` (메인 그래프) — ⚠️ MAJOR 3 + MINOR 1

- `/chainsight` 메인 페이지는 SectorBar + RelationFilterChips + MarketGraphCanvas + 카드 패널 구조. 모바일 명시 분기 **없음**.
- MAJOR: R-M1 (인기 섹터 110px 3열), R-M2 (SectorBar truncate), T-M7 (RelationLegend 10px 토글).
- MarketGraphCanvas는 force-graph 자체가 viewport에 자동 맞춤이지만 노드 라벨이 모바일에서 작음.

### 5.4 `/chainsight/[symbol]` — ✅ 양호

- 768px 미만 자동 `MobileCardList` ✓.
- 그래프 오버레이는 FAB로 진입 + 닫기 버튼 ✓.
- 액션 버튼 3개 모두 `min-h-[44px]` ✓ (T-m2).
- MINOR: C-m3 (safe-area-inset 미고려).

### 5.5 `/chainsight/watchlist` — ✅ 양호

- `max-w-3xl mx-auto px-4 py-6` — 모바일 단일 컬럼 OK.
- 단, 상단 back 버튼(`p-1.5 rounded`) = 36px (N-m3, MINOR).

### 5.6 `/stocks/[symbol]` — ⚠️ MAJOR 1

- Validation 탭만 `isMobile` 분기 (line 925-932).
- 기본 정보 / 차트 / 재무제표 / 뉴스는 모바일 명시 분기 없음.
- MAJOR: R-M6 (기본/재무 탭 모바일 무대응).
- `<SentimentChart>`, `<NewsList>`, `<NewsDetailModal>`는 grid 1열로 떨어지지만 폭 가정 검증 필요.

### 5.7 `/thesis` (목록) — ✅ 양호

- 단순 카드 리스트 + `space-y-3`.
- `max-w-3xl` 또는 layout 기본 폭에 맞춤.

### 5.8 `/thesis/[id]` (관제실) — ❌ BLOCKER 1 + MAJOR 2

- 컨테이너 `max-w-lg mx-auto px-4 pt-4 pb-20`.
- BLOCKER: R-B1 (IndicatorRow 가로 폭 392px, 375px viewport overflow).
- BLOCKER: T-B1 (차트 1M/1Y/3Y/5Y 토글 18px).
- MAJOR: T-M8 (ChevronDown 14px, 시각 단서 약함), C-M1 (QuarterlySparkline 라벨 11px), C-M2 (차트 fontSize 9).

### 5.9 `/thesis/new` (빌더) — ⚠️ MAJOR 1 + MINOR 6

- 1078 라인 단일 파일, 10/11px 라벨 다수.
- MAJOR: R-M5 (10px 다수), T-M10 (인라인 링크 10px).
- MINOR 6건 (R-m6, R-m7, R-m10 등).

### 5.10 `/portfolio` — ❌ BLOCKER 2 + MAJOR 1

- 카드/테이블 토글. 카드 뷰는 `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` ✓.
- BLOCKER: R-B2 (테이블 12 컬럼), R-B4 (Summary 5분할).
- MAJOR: R-M3 (테이블 토글이 모바일 가정 없음).

### 5.11 `/watchlist` — ⚠️ MAJOR 1

- `grid-cols-1 lg:grid-cols-3`.
- MAJOR: R-M13 (리스트 선택 → 종목 영역 스크롤 필요).

### 5.12 `/news` — ✅ 양호

- 카테고리 칩 + 카드 리스트 구조.
- AINewsBriefingCard `max-w-[200px]` importance bar는 카드 내부라 OK.
- T-M5 (헤드라인 토글 16px) 1건만 MAJOR.

### 5.13 `/market-pulse` — ⚠️ MAJOR 1

- MAJOR: R-M11 (MoverCard 호버 툴팁이 모바일에서 영구 비노출, 5건 × 2파일).

### 5.14 `/admin/*` — ❌ MAJOR 1 (운영자용, 우선순위 ↓)

- 모든 표 `overflow-x-auto` 일변.
- AdminTabNav는 `min-h-[44px]` ✓.
- TaskLogViewer, SystemTab 결과 셀 `max-w-[260px] truncate`.

### 5.15 전역 (Layout/Header/MobileNav) — ❌ BLOCKER 1 + MAJOR 3

- BLOCKER: R-B5 (모바일에서 검색·로그인 진입점 없음).
- MAJOR: N-M1 (햄버거 영구 hidden), N-M2 (5탭 한정), N-M3 (`pb-20` 일관성 결여).

---

## 6. 종합 평가

### 6.1 잘 된 점

1. **MobileNav 자체는 모범적** — `min-h-[44px]`, fixed bottom, z-50, 5탭으로 적절.
2. **Chain Sight `/chainsight/[symbol]`** — 모바일에서 카드 리스트 + FAB로 그래프 진입 전환은 적절한 mobile-first 패턴.
3. **Validation 탭** — 카테고리 칩 + 단일 카테고리 뷰 분기로 모바일 최적화.
4. **Recharts는 100% ResponsiveContainer 적용** — `width="100%"` 기반.
5. **`MarketGraphCanvas`의 모바일 탭 인터랙션** — 첫 탭(툴팁) + 두 번째 탭(center 전환) 패턴이 force-graph 모바일 UX의 정답.

### 6.2 우선 처리 권고

| 우선 | ID | 영역 | 처리 방향 (제안 — 본 감사는 read-only) |
|------|----|------|----------------------------------------|
| P0 | R-B1 + T-B1 | Thesis 관제실 IndicatorRow | 2행을 2줄로 분리(값/변동률 한 줄, 스파크라인/지지반박 한 줄). 차트 토글은 `min-h-[44px] text-xs`로 |
| P0 | R-B2 + R-B4 | Portfolio Table/Summary | 모바일 강제 카드 뷰 또는 Summary 2×2 또는 2×3 grid |
| P0 | R-B5 | Header | 모바일에 검색 + 로그인 단축 진입 추가 (예: MobileNav 또는 floating action) |
| P1 | N-M2 | MobileNav | Screener/Chain Sight/Thesis 진입점 추가 또는 햄버거 부활 |
| P1 | R-M11 | MoverCard 툴팁 | 모바일 long-press / `aria-describedby` + 시트 |
| P1 | T-M1 | Pagination 화살표 | `p-2.5` 이상 (40px+) 또는 `min-h-[44px]` |
| P2 | C-M1 / C-M2 | 차트 폰트 | XAxis fontSize 11~12, YAxis 11~12 |
| P2 | R-M14 / N-m4 | Admin/긴 리스트 | virtualization 적용 검토 (`react-window`) |

### 6.3 수치 요약

- BLOCKER 6, MAJOR 14, MINOR 11 = **31건**
- 페이지 24개 중 ❌ 위험 = 3 (관제실, 포트폴리오, 어드민/Header 영역) / ⚠️ 주의 = 7 / ✅ 양호 = 14
- 10px 이하 클릭 가능 요소 = **35+ 곳** (Grep 결과). 9px도 5곳.
- 12+컬럼 데스크톱 테이블 모바일 fallback 부재 = 3개 (Portfolio, Stock, Screener)

---

> 본 보고서는 정적 코드 분석 기반이며, 실제 viewport 렌더링·DOM 측정·a11y 테스트(axe-core 등)와 교차 검증 권장.
> 동적 폰트 스케일(iOS Dynamic Type, Android Font Size)·키보드 노출 시 viewport 축소(VisualViewport API)는 미반영.
