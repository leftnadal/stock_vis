# 모바일 UX 감사 보고서

- **감사일**: 2026-05-06
- **대상**: `frontend/` (Next.js 16, Tailwind CSS)
- **기준 뷰포트**: 모바일 375 px (iPhone SE/13 mini), 터치 타겟 Apple HIG 44×44 pt
- **방식**: 정적 코드 검사 (실행/렌더링 검증 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 비고 |
|--------|------|------|
| **BLOCKER** | 5 | 사용자가 핵심 기능에 접근 불가 또는 접근성 위반 |
| **MAJOR** | 12 | 사용성 크게 저해 (가독성·터치 정확도·네비 일관성) |
| **MINOR** | 9 | 사소한 폴리싱 (작은 폰트, 마진 등) |
| **합계** | **26** | |

### TL;DR
1. **루트 layout이 `userScalable: false`, `maximumScale: 1`** — WCAG 1.4.4 위반(접근성 BLOCKER).
2. **포트폴리오·스크리너 핵심 테이블이 모바일 미대응** — 9컬럼 테이블을 `overflow-x-auto`만으로 가로 스크롤 처리. `MobileStockCard`는 만들어져 있으나 호출되지 않음.
3. **네비게이션 이중화** — 햄버거 메뉴(Header)와 Bottom Nav(MobileNav)가 동시 노출되는데 메뉴 항목이 서로 다르고, BottomNav에 핵심 기능 5개(Chain Sight/Thesis/Market Pulse/Screener/Watchlist) 누락.
4. **터치 타겟 미달** — `text-[10px]`/`text-[11px]` 클릭 요소가 79개 파일에서 사용. 페이지네이션 버튼·차트 기간 버튼·프리셋 탭 모두 24×18 ~ 32×32 px로 44 pt 미달.
5. **가상화 미사용** — 긴 목록(스크리너 결과, 알림 목록 등) 어디에도 `react-window`/`react-virtual` 없음.

---

## 반응형 누락

### BLOCKER

#### B1. 뷰포트 확대 차단 — `frontend/app/layout.tsx:29-35`
```ts
viewport: { width: "device-width", initialScale: 1, maximumScale: 1, userScalable: false }
```
- `text-[10px]`이 다수 존재하는 화면에서 사용자가 핀치 줌으로 확대할 수 없음.
- WCAG 2.1 SC 1.4.4 (Resize Text) 위반.
- iOS Safari에서는 강제 무시되지만 Android Chrome에서는 차단됨.
- **조치**: `maximumScale: 5, userScalable: true`로 수정.

#### B2. 포트폴리오 테이블 모바일 미대응 — `frontend/components/portfolio/PortfolioTable.tsx:258-260`
- 9컬럼(`종목/수량/평균가/현재가/전일대비/평가금액/손익/수익률/목표가`) 테이블을 `overflow-x-auto`만으로 처리. `whitespace-nowrap`이 모든 셀에 걸려 있어 375 px 화면에서 가로 스크롤 ~600 px 발생.
- 인라인 편집 버튼(`Edit2`, `Save`, `X`) 또한 가로 스크롤 끝에 위치 → 발견조차 어려움.
- 모바일 카드 뷰가 별도로 없음(요약 카드만 `grid-cols-2 md:grid-cols-3 lg:grid-cols-6`로 분기됨).

#### B3. 스크리너 결과 — `MobileStockCard`는 만들어졌으나 호출 안 됨 — `frontend/components/strategy/ScreenerTable.tsx`
- `screener/MobileStockCard.tsx` (240줄짜리 모바일 카드)가 `index.ts:9`에 export 되어 있지만 실제 사용처가 코드베이스에 없음(`Grep`으로 0회). `frontend/components/strategy/ScreenerTable.tsx`만 사용 중인데 데스크톱 테이블 전용.
- `ScreenerTable.tsx:209-307`에 `max-w-[180px]`/`max-w-[120px]`/`max-w-[200px]` 셀 + 다컬럼 → 모바일에서 가로 스크롤만으로는 사용성 한계.

### MAJOR

#### M1. InvestingHeader 1400 px 고정 — `frontend/components/layout/InvestingHeader.tsx:32, 55, 99`
- `max-w-[1400px] mx-auto px-4` 3회 반복. `px-4`만 모바일 안전마진이라 좋지만, 내부 nav가 가로 스크롤될 가능성 있음. Header(다른 컴포넌트) 사용 시와 일관성 없음.

#### M2. RAG 채팅 입력 버튼 고정 52×52 — `frontend/components/rag/ChatInterface.tsx:198`
- `h-[52px] w-[52px]` → 데스크톱 OK이나 모바일에서 가로 폭의 14% 차지. 좋은 터치 타겟이지만 인접 입력창 폭 압박. 검토 필요.

#### M3. 사이드 시트 패턴은 잘 처리 — `frontend/components/eod/SignalDetailSheet.tsx:97`
- `w-full md:w-[420px] md:h-full` + `rounded-t-2xl md:rounded-none` + `md:hidden` 드래그 핸들 → 모바일에서 바텀시트, 데스크톱에서 사이드시트. **이 패턴이 다른 시트(`AddIndicatorSheet`, `KeywordDetailSheet`)에도 일관되게 적용되어야 함**(현재 부분적).

#### M4. SignalSummaryCard 고정 폭 72 px — `frontend/components/validation/SignalSummaryCard.tsx:40`
- `min-w-[72px]`이 가로로 N개 나열 → 6개 이상이면 모바일에서 줄바꿈 필요한데 `flex-wrap` 없음.

#### M5. ScreenerTable 한 줄 셀 폭 고정 — `frontend/components/strategy/ScreenerTable.tsx:209, 224, 307`
- `max-w-[180px]`/`max-w-[120px]`/`max-w-[200px]` truncate. 데스크톱에서는 OK이지만 모바일에서 종목명/섹터가 4~6자에서 잘림.

#### M6. Admin 테이블 `max-w-[240/260px] truncate` — `SystemTab.tsx:362`, `TaskLogViewer.tsx:218`
- 결과 셀 잘림. 모바일에서 핵심 정보 손실.

### MINOR

#### m1. PortfolioTable 요약 — `grid-cols-2 md:grid-cols-3 lg:grid-cols-6`로 분기됨 ✓
#### m2. RecommendationCard 회사명 — `max-w-[150px] truncate` (`news/RecommendationCard.tsx:85`). 모바일에서 잘림 가능.
#### m3. AINewsBriefingCard 진행바 `max-w-[200px]` (`news/AINewsBriefingCard.tsx:70`) — 모바일 폭 50% 정도라 OK이지만 불필요한 고정폭.

### 브레이크포인트 사용 분포
- `frontend/components/` 내 sm/md/lg/xl 사용: **104회 / 48파일** (전체 컴포넌트 ~200개 대비 24%)
- `frontend/app/` 페이지 14개 중 명시적 모바일 분기 사용: **14개 모두 일부 사용** (대부분 `grid-cols-1 md:grid-cols-2` 수준)
- 명시적 `hidden md:` / `md:hidden`(레이아웃 분기) 사용: **단 5개 파일** (Header, MobileNav, OptionButton, SignalDetailSheet, NewsEventTimeline) → 데스크톱과 모바일이 다른 컴포넌트 트리를 가져야 하는 케이스가 거의 처리되지 않음.

---

## 터치 타겟

### BLOCKER

#### B4. 페이지네이션 버튼 32×32 px — `frontend/components/screener/Pagination.tsx:127`
```tsx
className="min-w-[32px] px-2 py-1.5 rounded text-sm font-medium ..."
```
- 페이지 번호 버튼 `min-w-[32px] py-1.5` → 약 32×30 px. Apple HIG 44 pt 미달.
- 좌우 화살표(`p-1.5` + 아이콘 `w-4 h-4`) → 약 28×28 px. 더 심각.
- 페이지네이션은 스크리너 핵심 동작이므로 BLOCKER.

#### B5. Chain Sight 그래프 노드 터치 — `frontend/components/chainsight/MarketGraphCanvas.tsx:181-227`
- Canvas ForceGraph2D 노드 반지름: `xl=14, lg=11, md=8, sm=6` px → **md/sm 노드는 16×16 px 이하**.
- 노드 라벨 폰트 `${r > 10 ? 10 : 8}px` (Canvas) → 모바일 가독성 한계.
- `nodePointerAreaPaint`로 적중 영역을 노드 반지름과 동일하게 설정 → 작은 노드(8/6 px)는 **사실상 터치 불가능**.
- 그래프가 컴포넌트의 핵심 인터랙션이므로 BLOCKER.

### MAJOR

#### M7. 차트 기간 버튼 24×18 px — `frontend/components/thesis/dashboard/IndicatorRow.tsx:182`
```tsx
className="px-2.5 py-0.5 text-[10px] rounded ..."
```
- 1M/1Y/3Y/5Y 버튼 → 약 24×18 px. 4개가 `gap-1.5`로 붙어 있어 오터치율 높음.

#### M8. 프리셋 탭 70×24 px — `frontend/components/validation/PeerContextBar.tsx:40-49`
- `px-3 py-1 text-xs` → 약 70×24 px. **높이 24 px**가 44 pt 미달. 핵심 비교 기준 전환 UI라 영향 큼.
- `Pagination`과 동일 문제. 검증 화면 진입 후 첫 액션이라 사용자가 가장 자주 누름.

#### M9. AlertCard 해제 버튼 — `frontend/components/thesis/alerts/AlertCard.tsx:57`
- `text-[10px]` 텍스트 버튼 → 모바일에서 정확한 탭 어려움.

#### M10. SuggestionCard 카테고리 칩 `text-[10px]` (`thesis/builder/SuggestionCard.tsx:52`) — 클릭 가능한 영역인지 확인 필요. 이력 모드에서 `text-[11px] line-clamp-2`로 매우 작음.

#### M11. ChainSight 관계 카드 색상 칩 `px-1.5 py-0.5 text-[10px]` (`chainsight/RelationCardPanel.tsx:273, 289`) — 클릭 가능 시 24 pt 미달.

#### M12. ScreenerTable 정렬 헤더 — 셀 자체가 `<th>`로 클릭 가능 (`ScreenerTable.tsx:96-135`)이지만 실제 클릭 영역은 텍스트 + 화살표 아이콘만(`text-xs` 추정). 헤더 셀 전체가 트리거되도록 명시되지 않음.

### MINOR

#### m4. AlertBell/AlertBadge 카운터 `min-w-[18px] h-[18px] text-[10px]` — 표시 전용이라 탭 타겟 아님(OK).
#### m5. KeywordTag `sm` 크기 `px-2 py-0.5 text-[10px]` — 클릭 가능, 모바일에서는 `md` 이상 사용 권장.
#### m6. SignalFilterTabs 카운터 배지 `min-w-[18px] h-[18px] text-[11px]` — 표시 전용 OK.
#### m7. PresetGallery 순서 배지 `w-5 h-5 text-[10px]` — 표시 전용 OK.
#### m8. ConfidenceBadge `text-[10px]` — 표시 전용 OK.
#### m9. ExplorationTrail 구분자 `text-[10px]` — 비클릭, OK.

### 핵심 통계
- `text-[10px]` 사용: **38회 / 27파일**. 그중 클릭 가능 요소(button/Link/onClick) 추정: **~12 곳**.
- `text-[11px]` 사용: **15회 / 11파일**. 클릭 가능 추정: **~5 곳**.
- `min-h`/`min-w` 44 px 이상 명시한 클릭 요소: **0회** (전체 검색 결과).

---

## 네비게이션

### BLOCKER

#### B6. Header 햄버거 메뉴 + MobileNav 동시 노출 — `frontend/app/layout.tsx:59-63`
```tsx
<Header />
<main className="min-h-screen">{children}</main>
<MobileNav />
```
- 모바일에서 `Header.tsx:155-161` 햄버거 + `MobileNav.tsx:19` Bottom Nav가 **동시 표시**.
- 햄버거 메뉴 항목: `대시보드, 포트폴리오, Chain Sight, Thesis Control, Market Pulse, 뉴스, 스크리너, 마이페이지` (8개)
- BottomNav 항목: `홈(/), 종목(/stocks), 뉴스(/news), 포트폴리오(/portfolio), 내정보(/profile)` (5개)
- **불일치 항목**:
  - BottomNav에 Chain Sight, Thesis, Market Pulse, Screener, Watchlist 누락
  - BottomNav `종목` href=`/stocks` (해당 페이지 없음 — `/stocks/[symbol]`만 존재)
  - BottomNav `내정보` href=`/profile` (해당 페이지 없음 — 실제는 `/mypage`)
- 결과: 모바일에서 핵심 기능(Chain Sight/Thesis 등) 진입은 햄버거를 통해서만 가능, BottomNav는 **2개 깨진 링크 포함** → BLOCKER.

### MAJOR

#### M13. main 하단 패딩 누락 — `frontend/app/layout.tsx:60`
- `<main className="min-h-screen">`에 BottomNav 높이(64 px)만큼의 `pb-16 md:pb-0` 누락.
- 모든 페이지 하단 콘텐츠가 BottomNav에 가려질 수 있음(스크롤 끝에서 마지막 row가 안 보임).

#### M14. ChainSight 페이지 메인 컨테이너 — `frontend/app/chainsight/page.tsx:61`
- `max-w-7xl mx-auto px-4 py-4 space-y-4` → ChainSight는 그래프(400 px 고정 높이) + Section Bar + 4개 카드 구조. 모바일에서 그래프가 화면 절반 차지하면서 스크롤이 매우 길어짐.

### MINOR

#### m10. Header 검색바 `flex-1 max-w-md mx-4` (`Header.tsx:112`) — 모바일에서는 `hidden md:block`이라 OK. 모바일 메뉴 펼침 시(`244-253`) 별도 입력창 제공 ✓.

### 가상화 (Virtualization)
- **`react-window`/`react-virtual`/`tanstack-virtual` 사용처: 0건.**
- 잠재적 영향:
  - 스크리너 결과(페이지당 100개): `pageSize: 100`까지 가능하나 가상화 없이 렌더 → 모바일 저성능 기기에서 긴 스크롤 시 프레임 드롭 우려.
  - `thesis/(list)/alerts` 알림 목록: 알림이 50건 이상 쌓이면 동일 문제.
  - `news` 피드: 무한 스크롤이지만 모든 카드가 DOM에 머무는 구조 가능성 → 측정 필요.

---

## 차트/그래프

### Recharts ResponsiveContainer 사용 현황 (10개 파일)
| 파일 | 사용 여부 | 비고 |
|------|----------|------|
| `thesis/dashboard/IndicatorRow.tsx` | ✓ | `width="100%" height={160/140}` |
| `thesis/dashboard/IndividualMiniCharts.tsx` | ✓ | 미니차트 |
| `validation/MetricBarChart.tsx` | ✓ | — |
| `admin/news/MLTrendChart.tsx` | ✓ | — |
| `screener/SectorHeatmap.tsx` | ✓ | — |
| `stock/StockChart.tsx` | ✓ | — |
| `news/SentimentChart.tsx` | ✓ | — |
| `macro/YieldCurveChart.tsx` | ✓ | — |
| `portfolio/PortfolioChart.tsx` | ✓ | — |
| `charts/StockPriceChart.tsx` | ✓ | — |

→ Recharts 차트는 **전부 ResponsiveContainer로 감싸져 있음**.

### MAJOR

#### M15. ForceGraph2D 고정 height 400 px — `chainsight/MarketGraphCanvas.tsx:141-146`
- `containerRef`로 `containerWidth`만 동적, `height={400}`은 하드코딩.
- 모바일 세로 화면(예: 667 px)에서 그래프가 60% 차지 → 노드 라벨이 7-10 px로 그려져 가독성 매우 낮음(`paintNode:214` `${r > 10 ? 10 : 8}px sans-serif`).
- 모바일에서는 차라리 그래프 높이를 화면 비율(예: `vh * 0.5`)로 조정하고 라벨 폰트를 키우거나, **모바일 전용 리스트 뷰로 fallback** 필요.

#### M16. IndicatorRow 차트 X축 폰트 9 px — `thesis/dashboard/IndicatorRow.tsx:207, 248`
- `<XAxis fontSize={9}>` (월/연도 라벨). 모바일 가독성 미달.
- Y축은 10 px라 좀 더 나음. 차트 전체 높이 160/140 px라 라벨이 너무 작음.

#### M17. QuarterlySparkline 인라인 — `thesis/dashboard/IndicatorRow.tsx:131-138`
- 인라인 행 안에 `flex-1 max-w-[100px]`로 들어감. 모바일 한 줄 안에 *값(60px) + 변동률(120px) + 스파크라인(100px) + 지지반박(auto)* 4개가 `gap-3`로 → **375 px - 32(padding) - 16(들여쓰기) = 327 px**이라 공간 빠듯하지만 `flex-1`이 흡수. 가독성은 한계 직전.

### MINOR

#### m11. SectorHeatmap — Recharts지만 셀 폰트 사이즈 모바일 가독성 점검 필요 (코드 미상세 검토).
#### m12. StockChart — 잘못된 모바일 처리 시 X축 라벨 겹침 가능. ResponsiveContainer만으로 자동 해결되지 않음.

---

## 페이지별 상세

### 1. `/` (`app/page.tsx`) — EOD Dashboard
- **상태**: 검토 필요(코드 미열람). SignalCardGrid는 `sm:`/`md:` 분기 1회 사용. SignalDetailSheet는 모바일 바텀시트 ✓.
- **이슈**: M3(시트 ✓), M16(차트 폰트), B6(네비)가 영향.

### 2. `/portfolio` — 포트폴리오 (BLOCKER)
- **이슈**: B2(테이블), B6(네비), M13(하단 패딩).
- 9컬럼 테이블 + 인라인 편집 → 모바일에서 사실상 사용 불가.

### 3. `/screener` — 스크리너 (BLOCKER)
- **이슈**: B3(MobileStockCard 미사용), B4(페이지네이션), M5(셀 폭), M12(정렬 헤더), B6(네비).
- 핵심 페이지인데 데스크톱 테이블만 표시.

### 4. `/chainsight` — Chain Sight (BLOCKER)
- **이슈**: B5(노드 터치 6-14 px), M14(컨테이너), M15(그래프 높이), B6(네비).
- 그래프 인터랙션이 모바일에서 거의 불가능. `MobileCardList.tsx`는 존재(`text-[10px]` 칩 사용)하지만 그래프와 연결되어 있는지 검토 필요.

### 5. `/thesis` — Thesis Control (MAJOR)
- **이슈**: M7(차트 기간 버튼), M9(알림), M10(SuggestionCard), M16(축 폰트), M17(스파크라인 빠듯).
- IndicatorRow는 모바일 1xN 세로 나열 ✓ (사용자 피드백 반영). 펼치면 차트 표시 ✓.
- 단, 펼침 토글 버튼이 `<button>` 전체 행으로 되어 있어 터치 영역 자체는 OK ✓ — 단, 행 안의 작은 클릭 요소들(차트 기간 버튼)이 충돌 위험.

### 6. `/validation` — 1차 검증 (MAJOR)
- **이슈**: M4(SignalSummaryCard), M8(프리셋 탭 24 px), B6(네비).
- PeerContextBar의 프리셋 전환은 검증 진입 후 가장 빈번한 동작인데 24 px 높이.

### 7. `/news` — 뉴스 (MAJOR)
- **이슈**: M3 패턴은 일부 적용. RecommendationCard 회사명 `max-w-[150px]` (`m2`).
- MarketNewsSection, NewsEventTimeline에 `text-[10px]` 다수.

### 8. `/market-pulse` — Market Pulse (MAJOR)
- **이슈**: MoverCard 설명/툴팁 `text-[10px]` 5회 (`MoverCard.tsx:107~189`).
- 툴팁이 `group-hover/tooltip:block` — **모바일에 hover 없음**. 터치로 툴팁 표시 불가능 → 정보 접근성 손실.

### 9. `/stocks/[symbol]` — 종목 상세 (검토 필요)
- `overflow-x-auto` 사용 ✓. md:hidden/md:flex 분기 6회 등 다른 페이지보다 많음 → 비교적 모바일 대응 양호로 추정. 코드 상세 검토 필요.

### 10. `/admin/*` — 어드민 (영향 작음)
- 관리자용이라 모바일 우선순위 낮으나, `SystemTab/TaskLogViewer`의 `max-w-[240/260px] truncate`(M6)가 가독성 저해.

### 11. `/login`, `/signup` — 인증 (MINOR)
- `md:hidden/md:flex` 1회 → 단순 폼이라 큰 이슈 없을 것으로 추정. 직접 검토 필요.

### 12. `/dashboard` — Dashboard (검토 필요)
- `md:` 4회 사용. 카드 그리드는 일반적으로 `grid-cols-1 md:grid-cols-N`로 처리됨.

### 13. `/mypage` — 마이페이지
- BottomNav 링크가 `/profile`로 잘못되어 있음(B6). 이 페이지로 모바일 사용자가 BottomNav를 통해 접근 불가.

### 14. `/watchlist` — 관심종목
- 코드 `overflow-x-auto` 사용. 검토 필요.

---

## 권장 우선순위

| 순위 | 작업 | 영향 | 추정 작업량 |
|------|------|------|-------------|
| 1 | layout.tsx viewport `userScalable` 해제 (B1) | 접근성 BLOCKER | 5분 |
| 2 | MobileNav 5개 항목 재설계 + 깨진 링크 수정 + Header 햄버거와의 역할 분리 (B6) | 모든 모바일 사용자 | 2시간 |
| 3 | main에 `pb-16 md:pb-0` 추가 (M13) | 모든 페이지 콘텐츠 보존 | 5분 |
| 4 | ScreenerTable에 lg:이상에서만 표시 + lg 미만에서 MobileStockCard 호출하도록 분기 (B3) | 스크리너 사용자 | 1시간 |
| 5 | PortfolioTable 모바일 카드 뷰 추가 (B2) | 포트폴리오 사용자 | 4시간 |
| 6 | Pagination 버튼 min-h 44 px 적용 (B4) | 스크리너/리스트 전반 | 30분 |
| 7 | 검증 프리셋 탭 py-2.5 이상으로 확장 (M8) | 검증 사용자 | 10분 |
| 8 | Chain Sight 그래프 — 모바일 fallback 리스트 뷰 + 노드 최소 반지름 12 px (B5, M15) | Chain Sight 사용자 | 6시간 |
| 9 | MoverCard 툴팁 — 터치(`onClick`) 트리거 추가 (M2 영향) | Market Pulse 사용자 | 2시간 |
| 10 | 차트 기간 버튼(`text-[10px] py-0.5`) 모바일에서만 `min-h-[44px] text-xs`로 변환 (M7) | Thesis 사용자 | 30분 |

---

## 부록 — 검색 결과 raw 통계

| 패턴 | 건수 |
|------|------|
| `w-[NNpx]`/`min-w-[NNpx]`/`max-w-[NNpx]` (`*.tsx`) | 26회 / 22파일 |
| `text-[10px]` | 38회 / 27파일 |
| `text-[11px]` | 15회 / 11파일 |
| `overflow-x-auto`/`overflow-x-scroll` | 25파일 |
| `ResponsiveContainer` import | 10파일 (모두 사용 ✓) |
| `from 'recharts'` import | 10파일 (위와 일치) |
| `react-window`/`react-virtual`/`Virtualization` | 0건 |
| `hidden md:`/`md:hidden`/`hidden lg:`/`lg:hidden` 등 | 5파일만 사용 |
| 컴포넌트 내 sm/md/lg/xl 브레이크포인트 사용 | 104회 / 48파일 (전체의 24%) |

> 본 보고서는 코드 정적 분석 기준이며, 실제 모바일 디바이스 렌더링 검증(Chrome DevTools Device Mode, 실제 iPhone/Android Safari)은 수행하지 않았습니다. 우선순위 1~3 적용 후 디바이스 실측 권장.
