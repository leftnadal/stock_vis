# 모바일 UX 감사 보고서

**감사일**: 2026-04-25
**대상**: `frontend/` 전체 (Next.js 16, Tailwind CSS)
**기준 뷰포트**: iPhone SE / 375px
**터치 타겟 기준**: Apple HIG 44×44pt
**감사 범위**: 코드 정적 분석 (수정 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 정의 |
|--------|------|------|
| **BLOCKER** | 6 | 모바일에서 사용 불가 또는 핵심 기능 누락 |
| **MAJOR** | 11 | 사용성 저하가 크지만 간신히 동작 |
| **MINOR** | 8 | 가독성/일관성 문제, 보조적 |
| **합계** | **25** | |

### Top 5 BLOCKER (먼저 수정해야 할 것)
1. **MobileNav가 콘텐츠를 가림** — 거의 모든 페이지에 `pb-20` 누락 (16개 페이지 중 4개만 적용)
2. **MobileNav 링크 깨짐** — `/profile` 라우트 미존재 (`/mypage`로 가야 함), Chain Sight·Thesis·Screener·Market Pulse 진입 경로 부재
3. **Pagination 터치 타겟 28×28px** — `frontend/components/screener/Pagination.tsx:100,141` 화살표 버튼 (44px 미만, 페이지 이동 핵심)
4. **Thesis IndicatorRow 차트 기간 선택** — `px-2.5 py-0.5 text-[10px]` (1M/1Y/3Y/5Y) 약 22×18px, 관제실 핵심 인터랙션
5. **Validation Peer Preset 탭 터치 타겟 26px** — `frontend/components/validation/PeerContextBar.tsx:40,54,85` (사용자가 명시적으로 지목한 영역)
6. **PortfolioTable 12 컬럼 가로 스크롤** — 375px에서 콘텐츠 ~1400px, 사실상 보이지 않음

---

## 반응형 누락

### 1.1 페이지 레벨 `pb-20` 누락 (BLOCKER)

`app/layout.tsx:63`이 `<MobileNav />`를 `fixed bottom-0 ... md:hidden`(높이 64px)로 렌더한다. 페이지가 하단 64px 패딩을 갖지 않으면 마지막 행/버튼/페이지네이션이 가려진다.

**적용된 페이지** (4개):
- `app/page.tsx:71` (`pb-20 md:pb-0`)
- `app/thesis/[thesisId]/page.tsx:31,41,62`
- `app/thesis/(list)/layout.tsx:7`

**누락된 페이지** (12개):
| 페이지 | 결과 |
|--------|------|
| `/portfolio` | 12-col 테이블 마지막 행 가려짐 |
| `/screener` | Pagination 가려짐 (`app/screener/page.tsx:880`) |
| `/watchlist` | 종목 카드 마지막 행 가려짐 |
| `/news` | 카드 그리드 하단 가려짐 |
| `/market-pulse` | grid 마지막 카드 가려짐 |
| `/stocks/[symbol]` | 차트/탭 콘텐츠 하단 잘림 |
| `/chainsight/page.tsx` | (h-screen 레이아웃으로 일부 회피) |
| `/admin` | 테이블 하단 가려짐 |
| `/dashboard` | 자체 nav만 있고 MobileNav 무시 |
| `/login`, `/signup` | submit 버튼 가려짐 가능 |
| `/mypage`, `/ai-analysis` | 액션 버튼 가려짐 |

### 1.2 `max-w-[1400px]` 사용 — InvestingHeader (MINOR)

`frontend/components/layout/InvestingHeader.tsx:32,55,99`에 `max-w-[1400px]`. **단, 이 컴포넌트는 `app/layout.tsx`에서 import되지 않음** (legacy 후보). 레이아웃은 `Header.tsx`만 사용. 데드 코드 정리 권장.

### 1.3 데스크톱 전용(반응형 미적용) 컴포넌트

| 파일 | 라인 | 내용 | 심각도 |
|------|------|------|--------|
| `app/chainsight/[symbol]/page.tsx:358` | 우측 NodeDetailPanel `hidden lg:block` | 의도적 (lg 미만 숨김), 모바일 분기로 대응 | OK |
| `app/stocks/[symbol]/page.tsx:1058` | 사이드바 `hidden lg:block` | OK (모바일에선 단일 컬럼) | OK |
| `components/market-pulse/MoverCard.tsx:138~189` | hover 툴팁 `group-hover/tooltip:block` | 터치 디바이스에서 호버 없음, 정보 도달 불가 | **MAJOR** |
| `components/market-pulse/MoverCardWithBatchKeywords.tsx:145~196` | 동일 | 동일 | **MAJOR** |

### 1.4 고정 폭 `min-w-[NNpx]` overflow 위험

총 26개 파일에서 `w-[Npx]` / `min-w-[Npx]` / `max-w-[Npx]` 사용. `min-w-` 중 모바일 overflow 위험:

| 파일 | 라인 | 클래스 | 위험 |
|------|------|--------|------|
| `components/thesis/dashboard/IndicatorRow.tsx` | 110, 115, 132 | `min-w-[60px]` + `min-w-[120px]` + `max-w-[100px]` (한 행) | 값+변동+스파크 = 280px+, 375px 뷰포트에서 좌측 dot+이름+날짜 영역 압박 — **MAJOR** |
| `components/common/DataSourceBadge.tsx` | 171 | 툴팁 `min-w-[200px]` | 우측 고정 시 화면 밖 가능 — **MINOR** |
| `components/admin/SystemTab.tsx` | 362 | `max-w-[240px] truncate` | OK (truncate) |
| `components/admin/shared/TaskLogViewer.tsx` | 218 | `max-w-[260px] truncate` | OK |
| `components/eod/SignalDetailSheet.tsx` | 97 | `md:w-[420px]` | OK (md+에만 적용) |
| `components/rag/ChatInterface.tsx` | 198 | `w-[52px] h-[52px]` 보내기 버튼 | OK (44px 충족) |

### 1.5 `sm:` 미적용 컴포넌트

브레이크포인트 사용 검증:
- `Header.tsx`: `hidden md:flex`, `md:hidden` — OK
- `MobileStockCard.tsx`: 단일 컬럼 그리드 `grid-cols-3`로 작동 — OK
- `app/dashboard/page.tsx`: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` — OK
- `app/portfolio/page.tsx:228`: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` — OK
- `components/admin/AdminTabNav.tsx:30`: `flex gap-1 overflow-x-auto` — OK

**문제 없음.**

---

## 터치 타겟

Apple HIG 44×44pt 기준. `text-xs` (12px) + `py-1` (8px) ≈ 28~30px 높이로 미달.

### 2.1 BLOCKER — 핵심 인터랙션

| 컴포넌트 | 라인 | 현재 클래스 | 추정 크기 | 영향 |
|----------|------|-------------|-----------|------|
| `screener/Pagination.tsx` | 100,141,151 | `p-1.5` + 16px 아이콘 | 28×28px | 페이지 이동 |
| `screener/Pagination.tsx` | 127 | `min-w-[32px] px-2 py-1.5 text-sm` | 32×32px | 페이지 번호 클릭 |
| `thesis/dashboard/IndicatorRow.tsx` | 182 | `px-2.5 py-0.5 text-[10px]` 1M/1Y/3Y/5Y | ~22×18px | 차트 기간 선택 (관제실 핵심) |
| `validation/PeerContextBar.tsx` | 40,54,85 | `px-3 py-1 text-xs` 프리셋 탭 | ~26×26px | Peer 그룹 전환 |
| `screener/PresetGallery.tsx` | 192~204 | 삭제 `p-1` + 14px 아이콘 | 22×22px | 사용자 프리셋 삭제 |
| `eod/SignalDetailSheet.tsx` | 137 | 닫기 `p-1.5` + 16px X | 28×28px | 시트 닫기 (모바일 주요) |

### 2.2 MAJOR — 자주 사용되지만 사이즈 부족

| 컴포넌트 | 라인 | 클래스 |
|----------|------|--------|
| `screener/PresetGallery.tsx` | 241 | `text-[10px]` "상세 설명" |
| `validation/PeerContextBar.tsx` | 119 | "peer 목록 보기" `text-xs` |
| `eod/SignalDetailSheet.tsx` | 213 | 정렬 메뉴 `px-3 py-1 text-xs` |
| `eod/SignalDetailSheet.tsx` | 221 | 정렬 옵션 `px-3 py-2 text-xs` |
| `eod/SignalFilterTabs.tsx` | 44 | 카테고리 칩 `px-3 py-1.5 text-sm` (~30px) |
| `chainsight/MobileCardList.tsx` | 86,98 | 탭 `px-3 py-1.5 text-sm` (~32px) |
| `chainsight/MobileCardList.tsx` | 167~170 | 카드 CTA `text-xs py-1.5` |
| `app/chainsight/[symbol]/page.tsx` | 211,217,223 | 모바일 시트 `text-xs py-2` |
| `thesis/IndicatorCard.tsx` | 35~45 | 체크박스 `w-5 h-5` (20×20px) |
| `thesis/IndicatorCard.tsx` | 60~67 | ChevronDown `p-1` + 16px = 24×24px |
| `app/chainsight/[symbol]/page.tsx` | 251,267,277 | depth/필터 `px-3 py-1.5 text-sm` (~32px) |

### 2.3 MINOR — 시각적 라벨/배지 (클릭 영역 아니지만 작은 글자)

`text-[10px]` 71곳, `text-[11px]` 16곳 발견. 대부분 비클릭 라벨이지만 다음은 모호:

| 파일 | 라인 | 비고 |
|------|------|------|
| `chainsight/MobileCardList.tsx` | 149,154,159 | 섹터/성장단계/자본DNA 태그 `text-[10px]` 비클릭 — 가독성만 문제 |
| `thesis/dashboard/RealValueIndicatorCard.tsx` | 38,76,83 | 비교 라벨/설명 `text-[10px]` |
| `market-pulse/MoverCard.tsx` | 107,138~189 | 데스크탑 호버 툴팁 (모바일 불가) |
| `app/thesis/new/page.tsx` | 1063 | 링크 `text-[10px]` 클릭 가능 |
| `screener/AdvancedFilterPanel.tsx` | 142 | `text-[10px]` 필터 설명 (비클릭 OK) |

---

## 네비게이션

### 3.1 MobileNav (BottomTabBar) — `components/layout/MobileNav.tsx`

✅ 존재 (`md:hidden z-50` 64px 높이, 5개 탭).
- 홈 → `/`, 종목 → `/stocks`, 뉴스 → `/news`, 포트폴리오 → `/portfolio`, 내정보 → `/profile`

#### 3.1.1 BLOCKER — 라우트/IA 이슈

| 문제 | 상세 |
|------|------|
| `/profile` 라우트 미존재 | `app/` 하위에 `profile/` 없음. 실제 마이페이지는 `/mypage`. 클릭 시 404. |
| 핵심 기능 진입 부재 | `/chainsight`, `/thesis`, `/screener`, `/market-pulse`가 BottomTabBar에 없음. Header 햄버거가 유일한 진입점인데 햄버거 버튼이 우상단에만 있고 mobile 메뉴 길어 스크롤 필요 |
| Header(8 항목) ↔ MobileNav(5 항목) IA 불일치 | 사용자가 모바일/데스크톱에서 다른 IA를 학습해야 함 |

### 3.2 Header (햄버거) — `components/layout/Header.tsx`

✅ 모바일 메뉴 정상 (`md:hidden` 햄버거, `Menu` 아이콘 `h-6 w-6` `p-2` ≈ 40×40px → 44px 미달, **MAJOR**)
- 모바일 메뉴 펼침 시 `block px-3 py-2 text-base` (32px 높이) 항목 — **MAJOR** (44px 미달)
- `Search` 인풋 모바일에서 hidden, 메뉴 펼친 후만 노출 — UX 단계 추가됨, **MINOR**

### 3.3 InvestingHeader — `components/layout/InvestingHeader.tsx`

⚠️ 데스크톱 전용. 햄버거 / 모바일 메뉴 / 반응형 폴백 없음. **단, layout.tsx에서 사용되지 않음** → dead code.

### 3.4 Dashboard 자체 nav — `app/dashboard/page.tsx:31~50`

⚠️ `<Header />` 무시하고 자체 nav 렌더 + `MobileNav` 작동. 듀얼 nav 표시 가능. 일관성 깨짐 (**MAJOR**).

### 3.5 가상화 (Virtualization)

`grep -r "virtualizer\|react-virtual\|VariableSizeList"` → **0건**.

영향:
- `/screener` 결과 100~500종목 동시 DOM 렌더 (`MobileStockCard` × N)
- `/watchlist` 카드 리스트
- `/news` 기사 카드
- `/portfolio` 12-col 테이블
- `chainsight MobileCardList` 노드 리스트

→ 모바일에서 스크롤 jank 가능. **MINOR** (현재 페이지당 100개 제한으로 임계 미달이지만 검색 결과 ≥100시 위험).

---

## 차트/그래프

### 4.1 ResponsiveContainer 사용 현황

`grep ResponsiveContainer` → **15곳 모두 적용**:

| 컴포넌트 | 사용 |
|----------|------|
| `validation/MetricBarChart.tsx:78` | ✅ `width="100%" height="100%"` |
| `macro/YieldCurveChart.tsx:93` | ✅ |
| `stock/StockChart.tsx:652,748` | ✅ 동적 height |
| `charts/StockPriceChart.tsx:272` | ✅ |
| `portfolio/PortfolioChart.tsx:77,97` | ✅ height=400 (모바일 OK) |
| `news/SentimentChart.tsx:80` | ✅ |
| `screener/SectorHeatmap.tsx:216` | ✅ height=400 (Treemap 라벨 가독성 우려) |
| `thesis/dashboard/IndicatorRow.tsx:197,235` | ✅ height=160/140 |
| `admin/news/MLTrendChart.tsx:90` | ✅ |
| `thesis/dashboard/IndividualMiniCharts.tsx:54` | ✅ height=100 |

→ **반응형 차트는 일관되게 적용됨.** 양호.

### 4.2 차트 가독성 (모바일 375px)

| 차트 | 이슈 | 심각도 |
|------|------|--------|
| `IndicatorRow.tsx:197~223` | 일간 차트 height=160px, X축 fontSize=9 / Y축 width=55 + fontSize=10 — 좁은 폭에서 Y축 라벨이 차트 폭을 35% 점유 | MAJOR |
| `IndicatorRow.tsx:235~264` | 분기 차트 height=140px, X축 라벨 `Q4 '24` 형식 — 8분기 이상에서 라벨 겹침 (`interval` 자동 계산은 OK) | MINOR |
| `screener/SectorHeatmap.tsx:216` | Treemap height=400 고정. 11개 섹터 × 5종목 = ~55 셀, 모바일에서 라벨 잘림 | MAJOR |
| `eod/MiniSparkline` | `width={64} height={24}` 고정 (`StockRow.tsx:62`) — 작지만 보조 정보라 OK | MINOR |
| `thesis/dashboard/QuarterlySparkline.tsx:59` | 호버 툴팁 `absolute bottom-full left-1/2` — 카드 모서리에서 화면 밖 잘림 위험 | MINOR |

### 4.3 IndicatorRow 가로 압박 (BLOCKER)

`components/thesis/dashboard/IndicatorRow.tsx:108~143` 메인 행:
```
[2px dot] [이름 truncate flex-1] [날짜 text-[11px] flex-shrink-0] [chevron]
[값 min-w-60] [변동률 min-w-120] [스파크 max-w-100] [지지/반박 ml-auto]
```

375px - `px-4`(32px) = 343px 가용. 하단 행 최소 = 60+12(gap)+120+12+100+12+24 ≈ **340px** → 거의 빈틈 없음. 변동률 텍스트가 `전분기대비 +12.5%` 형태로 **min-w-120 초과** → 줄바꿈 또는 truncate 발생. **사용자가 명시적으로 지목한 영역.**

---

## 페이지별 상세

### 5.1 `/` (메인 페이지)
- `pb-20 md:pb-0` ✅
- EOD Dashboard 그리드 (SignalCard) — 카드 자체는 모바일 OK
- SignalFilterTabs 칩 `px-3 py-1.5 text-sm` ~30px → **MAJOR**
- 심각도: **MAJOR (1건)**

### 5.2 `/dashboard` (레거시)
- 자체 nav + MobileNav 충돌 → **MAJOR**
- `pb-20` 없음 → 마지막 카드 가려짐 가능 → **BLOCKER**
- 심각도: **BLOCKER (1) + MAJOR (1)**

### 5.3 `/portfolio`
- `pb-20` 없음 → **BLOCKER**
- PortfolioTable 12 컬럼 (`종목/수량/평균/현재/전일/평가/손익/수익률/목표/손절/비중/관리`) `overflow-x-auto`만 적용 → 가로 스크롤 ~1400px → **BLOCKER**
- 모바일 카드뷰 폴백 없음 (스크리너는 있음)
- 심각도: **BLOCKER (2)**

### 5.4 `/screener`
- `pb-20` 없음 → 페이지네이션 가려짐 → **BLOCKER**
- 모바일 카드뷰 자동 전환 (`viewMode === 'card' ? 'sm:block' : 'sm:hidden'`) ✅
- AdvancedFilterPanel 그리드 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` ✅
- PresetGallery 카드 `text-[10px]` 부가 정보 — 가독성 **MINOR**
- Pagination 터치 타겟 미달 → **BLOCKER**
- AI 키워드/테제 버튼 라벨 `hidden sm:inline` ✅ 모바일에서 아이콘만
- 심각도: **BLOCKER (2) + MINOR (1)**

### 5.5 `/watchlist`
- `pb-20` 없음 → **BLOCKER**
- `overflow-x-auto` 테이블 (line 294) — 컬럼 수 미확인이지만 동일 패턴 → **MAJOR**
- 심각도: **BLOCKER (1) + MAJOR (1)**

### 5.6 `/news`
- `pb-20` 없음 → **BLOCKER**
- `grid-cols-1 lg:grid-cols-3` ✅ 1열로 자연 폴백
- KeywordDetailSheet `overflow-x-auto scrollbar-hide` 가로 스크롤 ✅
- 심각도: **BLOCKER (1)**

### 5.7 `/market-pulse`
- `pb-20` 없음 → **BLOCKER**
- 1열 그리드 폴백 ✅
- MoverCard 호버 툴팁이 모바일에서 작동 불가 → 키워드 설명 정보 손실 → **MAJOR**
- "동기화"/"새로고침" 텍스트 `hidden sm:inline` ✅ 아이콘만 보존
- 심각도: **BLOCKER (1) + MAJOR (1)**

### 5.8 `/thesis` (관제실 / 빌더 / 가설 목록)
- `pb-20` ✅ (`(list)/layout.tsx`, `[thesisId]/page.tsx`)
- `max-w-lg mx-auto` 모바일 우선 디자인 ✅
- IndicatorRow 차트 기간 버튼 `px-2.5 py-0.5 text-[10px]` → **BLOCKER**
- IndicatorRow 메인 행 가로 압박 (340px / 343px) → **BLOCKER**
- IndicatorCard 체크박스 20×20px → **MAJOR**
- 가설 빌더 SuggestionCard 그리드 `grid-cols-1 sm:grid-cols-2` ✅
- thesis/new 페이지 `pb-20` 미확인 — 챗 UI는 자체 스크롤 영역
- 심각도: **BLOCKER (2) + MAJOR (1)**

### 5.9 `/chainsight/[symbol]`
- 모바일 분기 (`isMobile = window.innerWidth < 768`) → MobileCardList 폴백 ✅
- 데스크톱 그래프 → 모바일에선 카드 리스트 자동 전환 ✅
- "그래프 보기" 오버레이 풀스크린 ✅
- 노드 상세 바텀시트 (`max-h-48 overflow-y-auto`) → 3-CTA 버튼 `text-xs py-2` ~36px → **MAJOR**
- MobileCardList 카드 CTA `text-xs py-1.5` → **MAJOR**
- 카테고리 탭 `px-3 py-1.5 text-sm` ~32px → **MAJOR**
- 심각도: **MAJOR (3)**

### 5.10 `/stocks/[symbol]`
- `pb-20` 없음 → 차트/탭 콘텐츠 가려짐 → **BLOCKER**
- 우측 사이드바 `hidden lg:block` ✅ (모바일 1열)
- 재무 테이블 `overflow-x-auto` (line 843) — Quarterly/Annual 다년 데이터 → 가로 스크롤 → **MAJOR**
- 탭바 `flex gap-2 overflow-x-auto pb-3 scrollbar-hide` (line 1030) ✅
- 심각도: **BLOCKER (1) + MAJOR (1)**

### 5.11 `/admin`
- `pb-20` 없음 → 테이블 하단 가려짐 → **MAJOR** (관리자만 사용)
- AdminTabNav `flex gap-1 overflow-x-auto` ✅
- 다수 테이블 `overflow-x-auto` ✅
- TaskLogViewer `max-w-[260px] truncate` ✅
- 심각도: **MAJOR (1)**

### 5.12 `/login`, `/signup`
- `pb-20` 없음 → submit 버튼 가려짐 가능 → **MAJOR**
- 카드 가운데 정렬 ✅
- 심각도: **MAJOR (1)**

### 5.13 Validation 영역 (stock detail 내 탭)
- PeerContextBar 프리셋 탭 `px-3 py-1 text-xs` → **BLOCKER** (사용자 명시 영역)
- 직접 설정 인풋 `text-xs` 키보드 작아짐 → **MAJOR**
- "peer 목록 보기" 토글 `text-xs` → **MAJOR**
- SignalSummaryCard 카드 `min-w-[72px]` × N → 가로 스크롤 ✅ (`overflow-x-auto`)
- LeaderComparisonSection `overflow-x-auto` ✅
- MetricBarChart `text-[10px]` 라벨 — 차트 내부 라벨이라 OK
- 심각도: **BLOCKER (1) + MAJOR (2)**

---

## 부록: 즉시 적용 가능한 수정 패턴

> **이 보고서는 코드 수정 없이 작성됨. 아래는 후속 작업 가이드.**

1. **`pb-20` 일괄 적용**: `app/layout.tsx`의 `<main className="min-h-screen">` → `<main className="min-h-screen pb-20 md:pb-0">` 한 줄로 12개 페이지 동시 해결.
2. **MobileNav 라우트 수정**: `/profile` → `/mypage`, 또는 핵심 기능 5개 재선정 (홈/스크리너/Thesis/포트폴리오/내정보 등).
3. **Pagination 터치 타겟**: `p-1.5` → `p-2.5` + `min-h-[44px]`. `px-2 py-1.5 min-w-[32px]` → `px-3 py-2.5 min-w-[44px]`.
4. **IndicatorRow 차트 기간 버튼**: `px-2.5 py-0.5 text-[10px]` → `px-3 py-1.5 text-xs min-h-[36px]` (44px는 디자인 충돌, 최소 36px).
5. **Validation 프리셋 탭**: `px-3 py-1 text-xs rounded-full` → `px-4 py-2 text-sm min-h-[40px]`.
6. **PortfolioTable**: 모바일 카드뷰 컴포넌트(`MobilePortfolioCard.tsx`) 신규 생성, 데스크톱은 테이블 유지.
7. **MoverCard 호버 툴팁**: `group-hover/tooltip` → 클릭 토글 + 외부 클릭 닫기로 변경.
8. **InvestingHeader 제거**: 미사용 컴포넌트 dead code 삭제.
9. **dashboard/page.tsx 자체 nav 제거**: `Header.tsx` + MobileNav 일관 적용.

---

## 데이터 출처

- 고정 폭 검색: `w-\[\d+px\]|min-w-\[\d+px\]|max-w-\[\d+px\]` 26개 파일
- 미세 글자: `text-\[1[0-1]px\]` 71+16곳
- 가로 스크롤: `overflow-x-auto` 30곳
- 브레이크포인트: `md:hidden|hidden md:|sm:hidden` 22곳
- 가상화: `virtualizer|react-virtual` **0건**
- 차트: `ResponsiveContainer` 15곳 모두 적용
