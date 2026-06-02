# 모바일 UX 감사 보고서

> 감사일: 2026-06-02 · 대상: `frontend/` (components 205개, app pages 30개) · 기준 뷰포트: **375px (iPhone SE/standard)**
> 방식: **읽기 전용 정적 분석** (코드 수정 없음). 실기기/브라우저 렌더링 미검증 — Tailwind 클래스·레이아웃 구조 기반 추론.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| **BLOCKER** | **1** | 뷰포트 `userScalable: false` → 핀치 줌 전면 차단 (WCAG 1.4.4 위반) |
| **MAJOR** | **6** | ① 하단 고정 네비 콘텐츠 가림(약 10개 페이지) ② thesis 차트 기간 버튼 터치 타겟 ~18px ③ KeywordTag 터치 타겟 + hover-only 툴팁 ④ 리스트 가상화 전무 ⑤ 밀집 카드 `text-[10px/11px]` 가독성 ⑥ stocks/[symbol] 데스크톱 전용 `p-8` |
| **MINOR** | **6** | InvestingHeader 비반응형(미사용) · `/stocks` 깨진 네비 링크 · `text-[9px]` 신뢰도 배지 · 차트 축 `fontSize 9` · Header 도달 불가 드로어 잔존 · 차트 축 라벨 밀집 |

**총평**: 전반적으로 **모바일 대응의 토대는 갖춰져 있다.** 전역 레이아웃이 `Header`(데스크톱) + `MobileNav`(하단 탭)로 분리돼 있고, screener/chainsight/thesis/EOD는 모바일 전용 분기(MobileStockCard, MobileCardList, dvh+safe-area, bottom sheet)를 이미 구현했다. 과거 감사 흔적(`audit P0 #12/#13` 주석)으로 터치 타겟 44pt가 다수 적용됨. 그러나 **(1) 줌 차단이라는 단일 치명 결함**과 **(2) 하단 네비 여백 누락이 페이지마다 산발적**이라는 두 가지 구조적 문제가 남아 있다.

---

## 1. 반응형 누락

### 1-1. 고정 폭 사용 현황 (66건 / 42파일)
`w-[Npx]` / `min-w-[Npx]` / `max-w-[Npx]` 패턴 전수 조사 결과, **대부분은 375px에서 안전**하다:

| 분류 | 대표 예시 | 375px 영향 | 판정 |
|------|----------|-----------|------|
| `max-w-[Npx]` + `truncate` | ScreenerTable `max-w-[180px/120px/200px]`, StockRow `max-w-[140px]`, NodeTooltip `max-w-[130px]` | 너비 상한 + 말줄임 → overflow 없음 | ✅ 안전 |
| 작은 고정 버튼/배지 | rag/ChatInterface `w-[52px]`, AlertBell `min-w-[18px]`, SignalFilterTabs `min-w-[18px]` | 화면 대비 충분히 작음 | ✅ 안전 |
| 반응형 처리됨 | eod/SignalDetailSheet `w-full md:w-[420px]` | 모바일은 `w-full` | ✅ 안전 |
| 카드 고정 폭 | chainsight/MarketGraphCanvas 인기섹터 `w-[110px]` (flex-wrap 내부) | 줄바꿈됨 | ✅ 안전 |
| **데스크톱 전용 컨테이너** | InvestingHeader `max-w-[1400px]` ×3 | 좌우 패딩만 적용, 내부 nav 비반응형 | ⚠️ MINOR (아래 1-4) |

→ **고정 폭 자체로 인한 BLOCKER급 overflow는 발견되지 않음.** 위험 케이스는 모두 truncate·flex-wrap·반응형 분기로 방어돼 있다.

### 1-2. 테이블 가로 스크롤 처리 — ✅ 양호
- **ScreenerTable** (12컬럼 밀집 표): `<div className="overflow-x-auto">`로 래핑(`ScreenerTable.tsx:128`). 추가로 **screener 페이지가 `MobileStockCard` + viewMode 토글** 제공 — 모바일에서 테이블은 `hidden sm:block`, 카드 뷰가 기본. 모범 사례.
- StockTable / PortfolioTable 등도 overflow 래핑 또는 차트 컨테이너 사용 확인.

### 1-3. Recharts 차트 — ✅ 양호 (4번 항목 참조)
- 고정 폭 차트(`<BarChart width={...}>` 등) **0건**. 전부 `ResponsiveContainer width="100%"` 사용 (44개 파일).

### 1-4. 데스크톱 전용 컴포넌트
| 컴포넌트 | 문제 | 판정 |
|----------|------|------|
| **InvestingHeader.tsx** | 상단바·메인 nav·8개 메뉴 전부 `flex` 가로 배치, 브레이크포인트 0개, `max-w-[1400px]`. 375px에서 메뉴 8개 가로 overflow 확정. | **MINOR** — `<InvestingHeader`가 **어디에도 import되지 않음**(미사용 컴포넌트). 현시점 영향 없으나 부활 시 BLOCKER. 삭제 또는 반응형화 권장. |
| **app/stocks/[symbol]/page.tsx** | 최상위 컨테이너 `p-8`(32px×2) — 375px에서 콘텐츠 폭 ~311px로 압박. 모바일 패딩 미분기. | **MAJOR** — `p-4 sm:p-8` 권장. 종목 상세는 핵심 동선이라 격상. |

### 1-5. 하단 고정 네비 콘텐츠 가림 — **MAJOR (구조적)**
`MobileNav`는 `fixed bottom-0 ... h-16`(64px). 하단 콘텐츠가 가려지지 않으려면 페이지가 하단 패딩(`pb-16~20`)을 가져야 한다.

**여백을 가진 페이지** (✅): `app/page.tsx`(`pb-20 md:pb-0`), thesis 전 페이지(`pb-20` / dvh+safe-area), EODSkeleton.

**여백이 없는 페이지** (⚠️ 하단 콘텐츠/CTA가 64px 네비에 가림):
`dashboard`, `portfolio`, `news`, `watchlist`, `market-pulse`, `market-pulse-v2`, `screener`, `stocks/[symbol]`, `mypage`, `ai-analysis`, `chainsight`, `login`, `signup` — 대부분 `min-h-screen` 뒤 패딩 없음.

→ 마지막 행·푸터·하단 sticky 버튼이 모바일에서 탭바에 가려짐. **루트 `<main>`에 `pb-16 md:pb-0` 일괄 적용**(`layout.tsx:60`)으로 한 번에 해결 가능. 현재 페이지별로 산발 적용돼 누락이 발생.

---

## 2. 터치 타겟 (Apple HIG 44×44pt)

### 2-1. ✅ 44pt 준수 (과거 감사로 적용됨)
| 컴포넌트 | 처리 |
|----------|------|
| MobileNav 탭 | `min-h-[44px]` + `h-16` 컨테이너 (`audit P0 #13` 주석) |
| ScreenerTable 바구니 버튼 | `min-h-[44px] min-w-[44px]` (`:323`) |
| PeerContextBar 프리셋 탭 + 직접설정 | `min-h-[44px] px-4 py-2` (`:40,:54`) |
| QuarterlySparkline 막대 | `min-h-[44px]` + `onTouchStart` (`:44,:47`) |
| Pagination | `min-w-[44px]` (`:127`) |
| MobileCardList CTA(가설/탐색/검증) | `min-h-[44px]` (`:169,:175,:181`) |
| Header 햄버거 | `min-h-[44px] min-w-[44px]` (단 `hidden`으로 비활성 — 2-4 참조) |

### 2-2. ⚠️ 위반 — thesis 관제실 지표 카드 (사용자 지목 영역) — **MAJOR**
`IndicatorRow.tsx`:
- **차트 기간 선택 버튼 (1M/1Y/3Y/5Y)**: `px-2.5 py-0.5 text-[10px]` (`:182`) → 실측 높이 **약 18px**. 44pt 한참 미달. 펼침 영역의 핵심 조작 요소라 모바일 오터치 빈발 예상.
- 메인 행 자체는 `w-full ... px-4 py-3` 큰 버튼이라 양호하나, 행 내부 정보가 `text-[11px]` 다수(이름 truncate, 날짜, 비교라벨, 전제) → 가독성 저하(3번/아래 5번 참조).

### 2-3. ⚠️ 위반 — KeywordTag (screener 테이블·Market Movers 전반) — **MAJOR**
`KeywordTag.tsx`:
- 클릭 가능 `<span onClick>` 크기 `px-2 py-0.5 text-[10px]`(`sm`, `:42`) → 높이 **약 18px**. `onClick` 핸들러 있는데 터치 타겟 미달.
- **hover 전용 툴팁**(`onMouseEnter`/`onMouseLeave`, `:55-56`) → **모바일에 호버 없음 → 설명 툴팁 접근 불가**. 키워드 설명이 모바일에서 사실상 사라짐.
- `text-[9px]` 신뢰도 배지(`:77`) → 판독 불가 수준(MINOR).

### 2-4. validation 프리셋 탭 — ✅ 양호
`PeerContextBar` 프리셋/직접설정 탭 모두 `min-h-[44px]`. 사용자 우려 지점이나 이미 해결됨.

### 2-5. chainsight 노드 — 부분 양호
- 모바일 진입 시 `MobileCardList`로 분기 → 노드가 카드(`p-4`)로 표시, CTA 44pt. ✅
- 그래프 오버레이(SVG canvas)는 노드가 작은 `<circle>` — 핀치/탭 조작이 줌 차단(BLOCKER 1)과 맞물려 정밀 터치 어려움.

### 2-6. 작은 텍스트 클릭 요소 분포
`text-[10px]`/`text-[11px]` **133건 / 57파일**. 다수는 비클릭 라벨(안전)이나, 클릭 요소에 붙은 경우가 위 2-2/2-3. 밀집 카드(thesis builder SuggestionCard 5건, eod SignalCard 3건, market-pulse MoverCard 6건)에 집중.

---

## 3. 네비게이션

### 3-1. 구조 — ✅ 대체로 양호
- 전역 `layout.tsx`: `<Header />`(상단, 데스크톱 nav는 `hidden md:flex`) + `<MobileNav />`(하단 탭, `md:hidden`). 데스크톱/모바일 네비 분리 정상.
- **MobileNav = 하단 고정 탭 5개**(홈/종목/뉴스/포트폴리오/내정보), `fixed bottom-0`, 44pt, `aria-label` 부여. 모범적.

### 3-2. ⚠️ 깨진 네비 링크 — **MINOR**
- MobileNav `종목` → `href="/stocks"` (`MobileNav.tsx:13`). 그러나 `app/stocks/`에는 `[symbol]/page.tsx`만 존재, **`/stocks` 인덱스 페이지 없음** → 404 가능. Header의 데스크톱 nav에는 `/stocks` 링크 자체가 없어 불일치.

### 3-3. ⚠️ 도달 불가 드로어 잔존 — **MINOR**
- `Header.tsx`: 모바일 햄버거 버튼이 `className="hidden ..."`로 **영구 비표시**(`:160`, `audit P0 #12` 주석 — 이중 네비 제거 의도). 그 결과 `isMenuOpen` 드로어 JSX(`:166-257`, 약 90줄)가 **렌더 불가능한 죽은 코드**. `searchQuery`/`handleSearch`도 미동작(`console.log`만). 정리 권장.

### 3-4. Bottom navigation — ✅ 존재 (MobileNav)
### 3-5. ⚠️ 가상화(virtualization) 전무 — **MAJOR (성능)**
- `react-window`/`react-virtual`/`@tanstack/react-virtual` **미설치, 사용 0건**.
- 긴 목록(screener 결과, watchlist, news 피드, chainsight 노드, thesis 지표 리스트)이 전체 DOM 노드를 렌더 → 저사양 모바일에서 스크롤 버벅임·메모리 압박 우려.
- **완화 요인**: screener는 `Pagination`으로 페이지 분할(부담 경감). 그러나 watchlist/news 무한스크롤 계열은 가상화 부재가 직접 노출.
- 데이터 규모에 따라 MAJOR↔MINOR. 현 시드 규모에서는 즉각 장애 아니나 확장 시 리스크.

---

## 4. 차트 / 그래프 모바일 대응

### 4-1. ResponsiveContainer — ✅ 우수
- 고정 폭 Recharts 0건. 모든 차트 `ResponsiveContainer width="100%"`(44파일). 가로 폭은 모바일에서 자동 축소.
- 단, **높이는 고정**(`height={140~160}`) — 모바일에서도 동일 높이라 비율 양호.

### 4-2. ⚠️ 축 라벨 가독성 — **MINOR**
- `IndicatorRow` 차트 `XAxis fontSize={9}`, `YAxis fontSize={10}`(`:207,:211,:248,:252`) → 375px에서 축 눈금 판독 어려움. `interval`로 라벨 솎아내기는 적용됨(밀집 완화).

### 4-3. 분기 스파크라인 — ✅ 양호
- `QuarterlySparkline`: 커스텀 flex 막대, `onTouchStart` 터치 토글 + `min-h-[44px]` + `aria-label`. 모바일 친화적.
- 단 인라인 버전은 `max-w-[100px]`에 최근 4분기(`IndicatorRow.tsx:132`) → 막대 폭 ~25px, `Q1~Q4` 라벨 `text-[11px]`로 다소 빽빽하나 판독 가능.

### 4-4. chainsight 그래프 캔버스
- SVG 기반 관계 그래프. 모바일은 `MobileCardList`가 기본, 그래프는 오버레이 옵션(`isMobile && graphOverlay`). 정밀 노드 터치는 줌 차단(BLOCKER 1)과 함께 개선 여지.

---

## 5. 페이지별 상세

| 페이지 | 모바일 대응 수준 | 주요 이슈 | 심각도 |
|--------|----------------|----------|--------|
| **`app/layout.tsx`** (전역) | — | 뷰포트 `userScalable:false` 줌 차단 / `<main>` 하단 네비 여백 일괄 누락 | **BLOCKER** + MAJOR |
| `app/page.tsx` (홈/EOD) | 우수 | `pb-20 md:pb-0` 적용됨. EOD SignalDetailSheet 모바일 바텀시트(`md:hidden` 드래그핸들) | ✅ |
| `screener` | 우수 | MobileStockCard + viewMode 토글 + 테이블 overflow-x-auto. 단 페이지 하단 여백 없음 / 카드 내 `text-[10px]` 다수 | MAJOR(여백)/MINOR |
| `chainsight/[symbol]` | 우수 | isMobile 분기 + MobileCardList + 그래프 오버레이. 하단 여백 없음 | MAJOR(여백) |
| `thesis/*` | 우수 | dvh + `env(safe-area-inset)` + `pb-20` + `max-w-lg` 모바일 우선 설계 | ✅ (단 IndicatorRow 기간버튼 터치 2-2) |
| **`stocks/[symbol]`** | 미흡 | `p-8` 데스크톱 전용 패딩 / 하단 여백 없음 | **MAJOR** |
| `dashboard` | 미확인-약 | `min-h-screen flex items-center` — 하단 여백 없음, 모바일 분기 불명확 | MAJOR(여백) |
| `portfolio` | 약 | 하단 여백 없음. 차트 ResponsiveContainer는 적용 | MAJOR(여백) |
| `watchlist` | 약 | 하단 여백 없음 / 긴 목록 가상화 없음 | MAJOR(여백)+MAJOR(가상화) |
| `news` | 약 | 하단 여백 없음 / 무한 피드 가상화 없음 / KeywordTag hover 툴팁 | MAJOR ×2 |
| `market-pulse` / `-v2` | 중 | `hidden sm:*`로 일부 라벨 숨김 처리됨(✅). 하단 여백 없음 / MoverCard `text-[10px]` 6건 | MAJOR(여백)/MINOR |
| `ai-analysis` | 중 | `max-w-5xl`, `hidden sm:inline` 라벨. 하단 여백 없음 | MAJOR(여백) |
| `mypage` / `login` / `signup` | 약 | 하단 여백 없음(폼 페이지라 영향 적음) | MINOR~MAJOR |
| `admin/*` | 데스크톱 전용 | 관리자 화면 — 모바일 우선순위 낮음(테이블/차트 다수) | (범위 외) |
| (미사용) `InvestingHeader` | 비반응형 | 어디서도 import 안 됨. 부활 시 BLOCKER | MINOR |

---

## 권장 조치 우선순위

1. **[BLOCKER]** `layout.tsx` 뷰포트에서 `maximumScale:1, userScalable:false` 제거 → 줌 허용 (WCAG 1.4.4). 금융 앱 특성상 숫자·차트 확대 필수.
2. **[MAJOR·1줄 수정]** `layout.tsx`의 `<main className="min-h-screen">` → `min-h-screen pb-16 md:pb-0` 일괄 적용 → 페이지별 하단 네비 가림 한 번에 해소(페이지별 산발 `pb-20`은 제거 정리).
3. **[MAJOR]** `IndicatorRow` 차트 기간 버튼, `KeywordTag` 클릭 span → `min-h-[44px]` + 터치 패딩 확대.
4. **[MAJOR]** `KeywordTag` 툴팁 hover 의존 제거 → 탭(`onClick`/`onTouchStart`) 토글 추가, 모바일 설명 접근성 회복.
5. **[MAJOR]** `stocks/[symbol]` `p-8` → `p-4 sm:p-8`.
6. **[MAJOR]** 긴 목록(watchlist/news) 가상화 도입 검토(`@tanstack/react-virtual`).
7. **[MINOR]** 죽은 코드 정리: `Header` 모바일 드로어, 미사용 `InvestingHeader`, `/stocks` 인덱스 라우트 추가 또는 MobileNav 링크 수정.

---

> 본 보고서는 정적 코드 분석 기반 추론이며, 실제 디바이스/브라우저 렌더링으로 BLOCKER(줌)·하단 여백 가림은 재현 검증을 권장한다. (예: `/browse` 또는 `/qa-only` 375px 뷰포트)
