# 모바일 UX 감사 보고서

- **감사일**: 2026-05-22
- **대상**: `frontend/` 전체 (컴포넌트 195개, 페이지 24개)
- **기준 뷰포트**: iPhone SE 375px
- **터치 타겟 기준**: Apple HIG 44×44pt
- **모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 핵심 이슈 |
|--------|------|----------|
| **BLOCKER** | 3 | AlertCard `text-[10px]` 버튼, AdvancedFilterPanel 20×20px 아이콘 버튼, SignalSummaryCard 가로 스크롤 |
| **MAJOR** | 8 | 데스크톱 전용 grid 레이아웃 4건, virtualization 미적용 3건, IndicatorRow 고정 폭 |
| **MINOR** | 6 | BottomSheet `max-w-2xl` 제약, ChainSight 노드 라벨 폭, ScreenerTable truncate 등 |
| **양호** | — | Recharts ResponsiveContainer 14/14 적용, MobileNav 별도 구성, MobileStockCard 분기 존재 |

**총 17건** (BLOCKER 3, MAJOR 8, MINOR 6)

---

## 반응형 누락

### BLOCKER

**1. `frontend/components/validation/SignalSummaryCard.tsx:41`** — `min-w-[72px]` 7개 카테고리 버튼이 `overflow-x-auto` 컨테이너 내부에 배치되어 모바일에서 강제 가로 스크롤 발생.
```tsx
<div className="overflow-x-auto">
  <button className="min-w-[72px] ..." />  // 7개 × 72px = 504px > 375px
```
**페이지 영향**: `/validation` (1차 검증 페이지)

### MAJOR

**2. `frontend/app/stocks/[symbol]/page.tsx:329`** — Key Metrics 섹션 `grid grid-cols-2 gap-4`, `sm:` 분기 없음. 폭이 좁은 모바일에서 압축됨.

**3. `frontend/app/market-pulse-v2/cards/FlowCardSummary.tsx:13`** — `grid grid-cols-3 gap-2` (Concentration metrics), 모바일 분기 누락.

**4. `frontend/app/market-pulse-v2/details/BreadthDetail.tsx:29`** — `grid grid-cols-3 gap-2`, sm: prefix 없음.

**5. `frontend/app/market-pulse-v2/details/FlowDetail.tsx:34`** — 동일 패턴, `grid grid-cols-3`.

**6. `frontend/components/thesis/dashboard/IndicatorRow.tsx:110, 115, 132`** — `min-w-[60px]`, `min-w-[120px]`, `max-w-[100px]` 다단 폭이 sm: 분기 없이 적용. 관제실 지표 카드가 모바일에서 비좁게 압축됨.

### MINOR

**7. `frontend/components/chainsight/MarketGraphCanvas.tsx:676`** — `w-[110px] min-h-[68px]` 노드 라벨. 캔버스 컨텍스트라 overflow는 없지만 작은 화면에서 라벨 겹침 가능.

**8. `frontend/components/strategy/ScreenerTable.tsx:209, 224, 307`** — `max-w-[180px]/120px/200px` truncate 패턴은 모바일에서 시각적 압축이 심함 (truncate라 overflow 없음).

### 양호

- `frontend/app/screener/page.tsx:741`: `flex flex-col sm:flex-row` 패턴 정상.
- `frontend/components/eod/DataFreshnessBadge.tsx:64`: `flex-col sm:flex-row`.
- `frontend/app/thesis/new/page.tsx:672, 715`: `grid-cols-1 gap-2 sm:grid-cols-2`.
- `frontend/components/eod/SignalDetailSheet.tsx:97`: `md:w-[420px]` 모바일에서는 fullwidth.
- 대부분의 테이블(`StockTable.tsx:34`, `ScreenerTable` 등)이 `overflow-x-auto` 래퍼를 가짐.

---

## 터치 타겟

### BLOCKER

**1. `frontend/components/thesis/alerts/AlertCard.tsx:57-59`** — "읽음" 버튼이 `text-[10px] px-2 py-1` 단독. 추정 터치 영역 **약 40×16px** (HIG 44pt의 36% 수준). 관제실 알림에서 가장 자주 누르는 액션.
```tsx
<button className="text-[10px] px-2 py-1 ...">읽음</button>
```

**2. `frontend/components/screener/AdvancedFilterPanel.tsx:137`** — 필터 클리어 X 아이콘이 `p-1`, 아이콘 `h-3.5 w-3.5`. 실제 터치 영역 **약 20×20px** (HIG 45%).

### MAJOR

**3. `frontend/components/screener/PresetDetailPopover.tsx:86`** — 데스크톱 닫기 버튼 `p-0.5` + `w-4 h-4` X 아이콘 → **약 20×20px**. 모바일 분기(L55, `p-1`)는 32×32px로 마진 부족.

**4. `frontend/components/screener/Pagination.tsx:97, 107, 144, 154`** — 페이지네이션 화살표 버튼 `p-1.5` + `h-4 w-4` 아이콘 → **약 24×24px**. 인접 페이지 번호와 간격도 좁아 오탭 위험.

### MINOR

**5. `frontend/components/thesis/alerts/AlertCard.tsx:28, 32`** — Severity 배지·타임스탬프가 `text-[10px]`. 클릭 비대상이지만 인접 "읽음" 버튼과 시각적 혼동 유발.

### 양호

- `frontend/components/layout/Header.tsx:160`: 모바일 햄버거 트리거가 `min-h-[44px] min-w-[44px]` 명시.
- `frontend/components/validation/CategorySidebar.tsx`: 카테고리 버튼 `px-3 py-2 text-sm` (충분).
- `frontend/components/layout/MobileNav.tsx`: 하단 탭 5개 모두 `min-h-[44px]` 보장.

---

## 네비게이션

### 양호

**1. Bottom Tab Bar 존재** — `frontend/components/layout/MobileNav.tsx`
- `fixed bottom-0`, 5탭 (Home, Stocks, News, Portfolio, Profile), `h-16` 컨테이너에 `min-h-[44px]` 탭.
- 라벨 `text-xs` + 아이콘 `h-5 w-5`.
- ⚠️ 코멘트(L10)에 라우트 수정 메모: `/profile` → `/mypage` (현재 일치 여부 후속 확인 필요).

**2. Desktop Header + Mobile Hamburger** — `frontend/components/layout/Header.tsx`
- 데스크톱 nav: `hidden md:flex` (L157 등).
- 모바일 햄버거 메뉴: L167-257 expanded panel, `px-3 py-2` 충분한 패딩.

**3. InvestingHeader** — `frontend/components/layout/InvestingHeader.tsx`
- Top bar(h-10) + main nav(h-14), `max-w-[1400px]` 컨테이너 (모바일에서는 자연 축소).

### MAJOR — Virtualization 누락

**4. 긴 목록 virtualization 전무**
- `react-window` / `@tanstack/react-virtual` 등 import 전무.
- 영향 컴포넌트:
  - `frontend/components/news/NewsList.tsx` — `.map()` 평탄 렌더링 (뉴스 50+건 가능).
  - `frontend/components/chainsight/MobileCardList.tsx:100+` — `displayNodes.map()` (Chain Sight 노드 100+ 시 성능 저하).
  - `frontend/components/screener/ScreenerDashboard.tsx` — PresetGallery 무제한 map.
- 모바일 저사양 디바이스에서 스크롤 jank 우려.

### MINOR

**5. `frontend/components/thesis/common/BottomSheet.tsx:38`** — `max-w-2xl mx-auto`가 모바일에서도 적용되어 작은 화면에서는 좌우 마진 발생.

---

## 차트/그래프

### 양호 (전부)

**Recharts ResponsiveContainer 14/14 적용 확인**:
- `frontend/components/charts/StockPriceChart.tsx:272` ✓
- `frontend/components/thesis/dashboard/IndividualMiniCharts.tsx:54` ✓
- 분기 스파크라인, 메인 차트 모두 `<ResponsiveContainer width="100%" height={...}>` 패턴.
- 고정 width 차트 없음.

**Chain Sight 그래프 캔버스**:
- `frontend/components/chainsight/MarketGraphCanvas.tsx` — 캔버스 자체는 반응형이나 노드 라벨 `w-[110px]`(L676) 고정. 노드 밀도 높을 때 모바일 가독성 저하.

---

## 페이지별 상세

### `/validation` (1차 검증)
- **BLOCKER**: `SignalSummaryCard:41` 가로 스크롤.
- 양호: `CategorySidebar` 터치 영역 충분.

### `/thesis` (가설 관제실 / 알림 / 빌더)
- **BLOCKER**: `AlertCard:57` "읽음" 버튼 텍스트 10px.
- **MAJOR**: `IndicatorRow:110,115,132` 다단 고정 폭.
- **MINOR**: `BottomSheet:38` `max-w-2xl` 모바일 잉여 마진.
- 양호: `thesis/new/page.tsx` grid 분기, 차트 ResponsiveContainer.

### `/stocks/[symbol]` (종목 상세)
- **MAJOR**: `page.tsx:329` Key Metrics `grid-cols-2` 분기 누락.
- 양호: 가격 차트 ResponsiveContainer, StockTable overflow-x-auto.

### `/market-pulse-v2` (Market Pulse)
- **MAJOR**: `FlowCardSummary:13`, `BreadthDetail:29`, `FlowDetail:34` 모두 `grid-cols-3` 분기 누락 (3건).

### `/screener` (스크리너)
- **BLOCKER**: `AdvancedFilterPanel:137` 20×20px X 버튼.
- **MAJOR**: `Pagination` 화살표 24×24px, `PresetDetailPopover:86` 닫기 20×20px.
- 양호: `MobileStockCard.tsx` 모바일 전용 카드 존재, `page.tsx:741` flex 분기.

### `/news` (뉴스)
- **MAJOR**: `NewsList` virtualization 없음.

### `/chainsight` (Chain Sight)
- **MAJOR**: `MobileCardList` virtualization 없음 (100+ 노드 시).
- **MINOR**: `MarketGraphCanvas:676` 노드 라벨 폭 110px.

### `/dashboard`, `/portfolio`, `/mypage`
- 별도 BLOCKER/MAJOR 발견 없음.
- 차트는 모두 ResponsiveContainer.

---

## 우선순위 권고 (수정 시)

1. **즉시 (BLOCKER)**:
   - `AlertCard.tsx:57` "읽음" → `text-xs px-3 py-2` 또는 `min-h-[44px]` 추가
   - `AdvancedFilterPanel.tsx:137` → `p-2` + `h-4 w-4` (32×32px 이상)
   - `SignalSummaryCard.tsx:41` → `flex flex-wrap` 또는 `grid grid-cols-3 sm:grid-cols-7`

2. **단기 (MAJOR)**:
   - `market-pulse-v2`의 3건 `grid-cols-3` → `grid-cols-1 sm:grid-cols-3`
   - `stocks/[symbol]:329` → `grid-cols-1 sm:grid-cols-2`
   - `IndicatorRow` 고정 폭에 `sm:` prefix
   - `NewsList`, `MobileCardList`에 `@tanstack/react-virtual` 도입 (50+ 항목 시)

3. **중기 (MINOR)**:
   - `BottomSheet:38` → `max-w-full sm:max-w-2xl`
   - `Pagination` 터치 영역 확장 `p-2.5`
   - `MarketGraphCanvas` 노드 라벨 줌 레벨 연동

---

## 종합 평가

- **모바일 기반은 갖춰져 있음**: 별도 `MobileNav`, `MobileStockCard`, `MobileCardList`, `BottomSheet` 등 모바일 전용 컴포넌트 존재.
- **Recharts 차트 ResponsiveContainer 100% 적용** — 차트 영역은 우수.
- **약점**: 일관성 부족 — 일부 페이지(`market-pulse-v2`, `stocks/[symbol]`)는 sm: 분기 누락. 터치 영역 기준이 컴포넌트별 들쭉날쭉(특히 알림·필터·페이지네이션).
- **성능**: 100+ 항목 목록의 virtualization 부재가 모바일 스크롤 경험의 가장 큰 잠재 부채.
