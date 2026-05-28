# 모바일 UX 감사 보고서

- 감사일: 2026-05-28
- 대상: `frontend/` (Next.js 16.2.6, components 205개 / pages 30개)
- 기준 뷰포트: iPhone SE 375px × 667pt
- 기준선: Apple HIG 44×44pt 터치 타겟, WCAG 본문 가독성, Tailwind `sm`(640px) 이하 = 모바일

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 설명 |
|--------|------|------|
| BLOCKER | 3 | 모바일에서 콘텐츠 접근/사용이 사실상 불가능 |
| MAJOR | 7 | 사용 가능하나 가독성·터치 정확도·성능 명백히 저하 |
| MINOR | 9 | 폴리시·일관성 이슈, 기능에는 영향 없음 |
| 합계 | 19 |  |

**잘 된 점 (참고용 베이스라인)**:
- 하단 고정 `MobileNav` (홈/종목/뉴스/포트폴리오/내정보) 5개 탭이 `md:hidden`으로 정확히 모바일에만 노출, `min-h-[44px]` 보장 (`components/layout/MobileNav.tsx:20-44`)
- Recharts 사용 14개 파일 전수에서 `ResponsiveContainer` 사용 — `width="100%"` 가 일관됨 (예: `IndicatorRow.tsx:197,235`)
- Screener 결과는 `viewMode + hidden sm:block / sm:hidden`으로 모바일=카드/데스크톱=테이블 분기 (`app/screener/page.tsx:845-855`)
- ChainSight `/chainsight/[symbol]`는 `window.innerWidth < 768` 감지 후 `MobileCardList`로 완전 분기 (`app/chainsight/[symbol]/page.tsx:117, 151-232`)
- Thesis 대시보드 (`/thesis/[thesisId]`)는 `max-w-lg mx-auto` 모바일 우선 설계 (`app/thesis/[thesisId]/page.tsx:62`)

---

## 1. 반응형 누락

### BLOCKER

**[B-1] `/dashboard` 페이지 자체 헤더에 모바일 네비게이션 없음 — `app/dashboard/page.tsx:31-50`**
- 자체 `<nav>` 안에 "로그아웃" 버튼과 "안녕하세요, {nickname}님" 텍스트가 `flex justify-between` 한 줄에 강제 배치. 모바일 브레이크포인트 없음 (`hidden md:` 없음).
- 닉네임이 6글자 이상이면 374px 가로폭에서 로그아웃 버튼이 오른쪽으로 밀려 잘리거나 자체 nav가 2줄로 깨짐.
- 글로벌 `Header`(`components/layout/Header.tsx`)와 별개의 페이지 내장 nav라서 햄버거 토글이 아예 없음.
- 결정적: 이 페이지에서 `MobileNav` 하단바와 자체 nav가 동시 노출되어 이중 네비 — `CLAUDE.md`의 "이중 네비 제거" 주석(`Header.tsx:155-156`)에 위배.

**[B-2] `/stocks/[symbol]` L2 탭 네비게이션이 모바일에서 잘림 — `app/stocks/[symbol]/page.tsx:401-419`**
- L1 탭: `flex space-x-2` (4개 pill, `min-h-[44px]` 적용됨 — 양호)
- **L2 탭**: `flex space-x-6` (`px-6 mt-2`) — overflow 처리 없이 한 줄 강제. activeL1에 따라 5~7개의 L2 탭이 노출되며 (예: 재무제표 4개 탭 + 펀더멘탈 + ...), 375px 폭에서 마지막 2~3개 탭이 화면 밖으로 잘리고 가로 스크롤도 안 됨.
- 같은 위치의 `Pill`은 `min-h-[44px]`인데 underline 탭은 `pb-3` 만으로 → 터치 영역도 작음.

**[B-3] `components/stocks/StockTable.tsx` (`/` 메인의 "주요 종목" 등) 7컬럼 테이블, 모바일 대안 없음 — `StockTable.tsx:34-136`**
- `overflow-x-auto`로 가로 스크롤은 가능하나, `MobileStockCard`와 같은 모바일 분기 컴포넌트가 호출부에 연결되어 있지 않음 (`MobileStockCard`는 `screener`에서만 사용).
- 스파크라인 SVG가 `w-16 h-8` 고정 → 작은 화면에서 셀 폭 압박.
- 행 클릭 영역 전체가 링크처럼 동작하나 `cursor-pointer`만 적용, 명시적 터치 인디케이터 없음.

### MAJOR

**[M-1] `ScreenerTable` 12컬럼 테이블 — `components/strategy/ScreenerTable.tsx:127-336`**
- `overflow-x-auto`로 모바일에서도 노출 가능 (screener에서는 `hidden sm:block`로 차단되어 영향 없음). 그러나 `ScreenerTable`이 다른 페이지에서 import될 경우(현재는 screener 단일 호출이지만 재사용 가능성) 모바일에서 `max-w-[180px] truncate` 등으로 종목명 잘림 + 12 컬럼이 가로 스크롤로만 노출됨 → MAJOR.
- 헤더의 정렬 클릭(`<th>`)은 터치 영역이 `px-4 py-3` 즉 약 24pt 높이로 44pt 미만.

**[M-2] `RAG ChatInterface` 전송 버튼 고정 `w-[52px] h-[52px]` — `components/rag/ChatInterface.tsx:198`**
- 픽셀 고정으로 모바일에서도 줄어들지 않음 (44pt 이상이라 OK)이지만, 입력창과 같은 행에 있을 때 좁은 화면에서 input의 가용폭을 갉아먹음. 360~375px 폭 + 한글 placeholder 길이에서 input이 너무 좁아짐.

**[M-3] `app/coach/e4/page.tsx:135` 채팅 컨테이너 `max-h-[60vh] min-h-[300px]`**
- 60vh 고정으로 모바일 키보드가 올라오면 60vh가 시각적 30vh로 축소 → 스크롤이 답답하고 가장 최근 메시지가 키보드 뒤로 숨음. iOS Safari `visualViewport` 미사용.

**[M-4] `app/market-pulse-v2/details/BreadthDetail.tsx:29` `grid-cols-3` 기본값**
- `header className="grid grid-cols-3 gap-2 text-center"` — 모바일에서도 3열 유지. 각 셀에 숫자+라벨이 들어가 셀 폭이 ~120px 미만이 되며 라벨 줄바꿈 발생.
- `FlowDetail.tsx:34`도 동일 구조.

### MINOR

**[m-1]** `components/layout/InvestingHeader.tsx:32,55,99`: `max-w-[1400px]`는 컨테이너 상한이라 무해하나 px 픽셀 단위 — `mx-auto px-4` 동반이라 모바일 영향 없음. 일관성 차원에서 Tailwind 스케일(`max-w-screen-2xl`)이 권장.
**[m-2]** `eod/SignalDetailSheet.tsx:97` `w-full md:w-[420px]` — 모바일은 full, 데스크톱은 420px 사이드시트. 잘 됨, 픽셀 사용은 의도적.
**[m-3]** `chainsight/MarketGraphCanvas.tsx:603,712,760` `h-[560px]` 고정 — 모바일에서 화면 거의 다 차지. 모바일은 `MobileCardList`로 분기되어 영향 없음.
**[m-4]** `app/coach/e4/page.tsx:213` 글자수 카운트 `text-[11px]` — 보조 정보로 허용 범위.

---

## 2. 터치 타겟

기준: Apple HIG `44pt × 44pt`. Tailwind 기준 `h-11 w-11` (44px) 또는 `min-h-[44px] min-w-[44px]`.

### MAJOR

**[T-1] Thesis `IndicatorCard` 추천 카드 액션 영역 미보장 — `components/thesis/IndicatorCard.tsx:52,78-87`**
- 카드 내부의 `text-[10px]` 뱃지 + `px-1.5 py-0.5` 클릭 가능성 있는 라벨들이 명시적 `min-h-[44px]` 없음. 카드 전체가 클릭이라면 그나마 OK, 그러나 카드 내 개별 액션이 분기되면 위험.

**[T-2] `app/thesis/new/page.tsx`(가설 빌더) 옵션/뱃지 다수 `text-[10px]` + `py-0.5` — 688, 752-753, 765, 831, 843, 1063 라인**
- 가설 빌더는 가설 생성의 가장 중요한 화면. 라벨 클릭 가능 여부가 시각적으로 모호하고 터치 영역이 ~20~24pt에 그침. 옵션 버튼 자체는 `min-h-[52px]` 보장(`OptionButton.tsx:52`)이라 안전하나, 보조 액션(`reset`, `back`, `1063 inline-block` 등)은 미보장.

**[T-3] `RelationFilterChips.tsx:229` 가로 스크롤 칩, `OptionButton.tsx:66` "꾹 누르면 설명" — 모바일 특수 인터랙션**
- 모바일 사용자는 long-press 친화적이지만 시각 힌트가 `text-[10px]`로 작음. `sm:hidden`로 모바일에만 노출. 학습성 낮음.

**[T-4] `app/stocks/[symbol]/page.tsx:401-419` L2 underline 탭 `pb-3` 만 — 약 24pt**
- B-2와 중복이나 터치 관점에서 별도 카운트. underline 탭은 명시적 `min-h-[44px]` 없음.

**[T-5] `components/eod/SignalFilterTabs.tsx:33-68` 가로 스크롤 탭 — `min-w-[18px] h-[18px]` 카운터 뱃지**
- 18×18px 뱃지는 카운터 표시용이라 OK이지만, 탭 버튼 자체의 `min-h` 명시 없음 (코드에서 직접 확인 필요). 가로 스크롤 칩에서 자주 발생하는 패턴.

### MINOR

**[t-1]** `validation/SignalSummaryCard.tsx:41` `min-w-[72px] min-h-[44px]` — 신호등 7개가 가로 스크롤. 44pt 보장. OK.
**[t-2]** `validation/PeerContextBar.tsx:40,54` 프리셋 탭 `min-h-[44px] px-4 py-2` — OK.
**[t-3]** `chainsight/MobileCardList.tsx:169,175,181` 3분할 CTA "가설 생성/탐색/검증" — `flex-1 min-h-[44px]` 각각. OK.
**[t-4]** `screener/Pagination.tsx:127` `min-w-[44px] min-h-[44px]` — OK.
**[t-5]** `components/thesis/builder/OptionButton.tsx:52` `min-h-[52px]/[56px]` — OK.
**[t-6]** Header 햄버거(`Header.tsx:160`)는 `hidden`이지만 코드 잔존 — 향후 부활 시 `min-h-[44px] min-w-[44px]` 이미 적용.

---

## 3. 모바일 네비게이션

### BLOCKER

**[N-1] `Header.tsx` 모바일 검색 진입점 없음 — `Header.tsx:111-123, 244-256`**
- 데스크톱 헤더 검색 input은 `hidden md:block`. 모바일에서는 햄버거 메뉴(`isMenuOpen`)가 열려야 검색이 보이는데, 햄버거 버튼 자체가 `Header.tsx:157` `className="hidden ..."`로 영구 숨김 처리됨 (audit P0 #12 주석 참조 — MobileNav로 단일화 의도).
- 결과: `Header`의 검색 폼(`244-256`)은 도달 불가능한 죽은 코드. 모바일에서 종목 검색 동선이 끊김. `MobileNav`에는 검색 항목 없음.
- 글로벌 검색 동선 부재는 BLOCKER급 UX 결함.

### MAJOR

**[N-2] `MobileNav`에 핵심 기능 누락 — `MobileNav.tsx:11-17`**
- 5개 탭: 홈/종목/뉴스/포트폴리오/내정보.
- **누락**: Chain Sight, Thesis Control, Market Pulse, Screener — 모두 `Header`의 데스크톱 nav에는 있는 1급 메뉴. 모바일 사용자는 URL 직타 또는 다른 페이지 인링크로만 진입 가능.
- "종목" 탭이 `/stocks` 인덱스로 라우팅되지만 `app/stocks/page.tsx`는 부재 (있다면 `[symbol]` 동적 라우트만). 깨진 라우트 가능성.

**[N-3] 긴 목록 virtualization 전무 — `grep` 결과 0건**
- `react-window` / `@tanstack/react-virtual` / `react-virtuoso` 모두 미사용.
- 영향 받는 화면 (모바일 우선): 
  - `screener` 결과 (500개 종목 페이지네이션, 1페이지 50개 — 페이지네이션으로 우회 중)
  - `watchlist`, `news` 카드 리스트
  - `chainsight/MobileCardList`: `displayNodes.map` 전체 렌더 (200+ 노드 가능)
  - `thesis` 지표 리스트: 보통 5~20개라 무해
- 모바일 GPU/메모리 한계에서 200+ DOM 노드 + 차트가 동시 렌더되면 스크롤 jank.

### MINOR

**[n-1]** `chainsight/MarketGraphCanvas`는 빈 상태/로딩에서 모바일 친화적 SVG와 인기 섹터 칩 제공. OK.
**[n-2]** `AdminTabNav.tsx:30,37`: `flex gap-1 overflow-x-auto` + `min-h-[44px]` — 가로 스크롤 OK.
**[n-3]** `MobileNav.tsx` 활성 상태 표시는 텍스트 색만 변경 (`text-blue-600`) — 시각적 강조 약함. 상단 인디케이터 막대 또는 배경 옅은 색이 권장.

---

## 4. 차트/그래프 모바일 대응

### MAJOR

**[C-1] `IndicatorRow` 확장 영역 차트 X축 라벨 가독성 — `components/thesis/dashboard/IndicatorRow.tsx:206-209, 247-249`**
- `fontSize={9}` 폰트로 X축 표시. 화면 폭 100% 안에서 `interval={Math.floor(chartData.length / 6) - 1}`로 6 라벨만 노출 시도, 그러나 5Y(1825일) 데이터의 경우 `sampleInterval=40`으로 ~46개 포인트 → 6 라벨로 다이어트되어도 라벨 간 간격이 잡혀 X축이 비어 보임.
- Y축 `width={55}` 고정 → 360px 화면에서 차트 실폭 ~280px, 5Y 데이터 패턴 분간 어려움.

**[C-2] `QuarterlySparkline` 분기 스파크라인 — `components/thesis/dashboard/IndicatorRow.tsx:131-138`**
- 인라인 스파크라인이 `max-w-[100px]`로 제한, 4분기 표시. 작은 폭에서 점/막대 변별력 낮음.
- `min-h-[44px]`로 터치 영역 보장 (`QuarterlySparkline.tsx:44`) — 그러나 분기 수가 8개 이상이면 한 점에 ~12px → 손가락 hit 정확도 ↓.

### MINOR

**[c-1]** 모든 Recharts 컴포넌트가 `ResponsiveContainer width="100%"` 적용 (14/14). OK.
**[c-2]** `IndividualMiniCharts.tsx`도 Recharts + ResponsiveContainer. OK.
**[c-3]** Recharts tooltip `fontSize:12` 고정 — 모바일 long-press 후 손가락 가림 가능. 위치 조정 미적용.
**[c-4]** `MarketGraphCanvas` ForceGraph2D는 모바일에서 `MobileCardList`로 분기 처리되어 비노출 → OK.

---

## 5. 페이지별 상세

### `/dashboard` (로그인 후 기본 진입) — **BLOCKER**

- B-1 (자체 nav 모바일 분기 없음 + 이중 네비)
- 카드 `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 잘 됨 (54줄)
- 계정 정보 `sm:grid sm:grid-cols-3 sm:gap-4` — 모바일에서는 dt/dd 세로 나열, OK
- 결론: nav 헤더만 수정하면 본문은 OK

### `/stocks/[symbol]` — **BLOCKER + MAJOR**

- L1 pill 탭: `min-h-[44px]` OK
- **L2 underline 탭**: B-2 (가로 잘림 + 터치 영역 작음)
- "기업 정보" 그리드 `grid-cols-2 md:grid-cols-3 lg:grid-cols-4` — 모바일 2열 OK (568줄)
- "관련 종목" 그리드 `grid-cols-1 lg:grid-cols-2` — OK (897줄)
- `overflow-x-auto` 가로 탭 칩 (1030줄) — 스크롤 OK

### `/screener` — **MINOR (잘 됨)**

- ScreenerDashboard: `grid-cols-1 lg:grid-cols-2/3` — OK
- PresetGallery: `grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6` — 모바일 2열 OK
- 결과 리스트: `viewMode` + `hidden sm:block / sm:hidden` 모바일 카드뷰 자동 분기 → 모범 사례
- 카드 `MobileStockCard`는 `text-[10px]` 사용하지만 라벨용으로 격 맞음

### `/thesis` 가설 통제실 — **MAJOR**

- `/thesis/(list)`: 목록 모바일 우선 OK
- `/thesis/[thesisId]`: `max-w-lg mx-auto` 모바일 우선 — 모범
- `/thesis/[thesisId]/indicators`: 지표 설정 — `RecommendCard.tsx` 등 `text-[10px]` 다수, 카드 클릭은 OK
- `/thesis/new`: 가설 빌더 — **T-2** (`text-[10px]` 보조 라벨 다수, 1063줄 inline 액션) + 큰 화면 가정으로 디자인된 흔적
- `IndicatorRow` 확장 시 차트 가독성: **C-1**
- `QuarterlySparkline`: **C-2**

### `/chainsight/[symbol]` — **MINOR (잘 됨)**

- `window.innerWidth < 768` 감지 후 `MobileCardList`로 완전 분기
- 모바일 카드 CTA 3분할 `min-h-[44px]` 보장
- 그래프 오버레이 시 노드 상세 바텀시트 `max-h-48 overflow-y-auto` OK
- 데스크톱 3-panel은 모바일에서 노출되지 않으므로 무관

### `/news` — **MINOR**

- 카테고리 그리드 `grid-cols-1 lg:grid-cols-2/3` — OK
- 키워드 가로 스크롤 (`KeywordDetailSheet.tsx:125`) `scrollbar-hide` OK
- `text-[10px]` 메타 정보 다수 — 격 맞음

### `/portfolio` — **MINOR**

- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` OK
- `PortfolioTable`은 `overflow-x-auto` (`PortfolioTable.tsx:259`) — 카드 분기 없음, viewMode 토글로만 우회. 모바일 기본을 카드로 강제하지 않음 → MINOR

### `/watchlist` — **MAJOR**

- `grid-cols-1 lg:grid-cols-3` OK
- `overflow-x-auto`로 테이블 노출 (`watchlist/page.tsx:294`) — 모바일 카드 분기 없음. StockTable과 유사 패턴.

### `/market-pulse-v2/details/*` — **MAJOR**

- `grid-cols-3` (Breadth, Flow) — **M-4**
- `SectorDetail`, `RegimeDetail`도 동일 구조 가능성 (Read 미수행 — 추정)

### `/coach/e1~e6` — **MAJOR**

- `e4`: 채팅 컨테이너 60vh 고정 — **M-3**
- 다른 e1/e2/e3/e5/e6: `grid-cols-1 gap-4 md:grid-cols-2/3` — 모바일 우선 OK
- `grid-cols-12 items-center gap-2` (e1:150, e2:164, e3:178, e5:201, e6:181) — 12열을 모바일에서도 강제. 행 안의 컬럼 분배가 좁아짐. 검토 필요

### `/admin/*` — **MINOR**

- 데스크톱 우선 의도 명확 (Admin)
- `overflow-x-auto`로 테이블 노출 — 모바일에서 사용 가능하나 권장 아님

---

## 권장 우선순위 (의사결정 보조용)

1. **B-1, B-2, N-1 즉시 수정** — 사용자 동선이 끊기는 BLOCKER
2. **N-2** — `MobileNav`에 Screener/Thesis/Chain Sight 진입점 추가 (햄버거 부활 또는 "더보기" 탭)
3. **B-3, M-1, M-4** — 테이블 다수 화면을 모바일에서 카드뷰 자동 분기로 전환 (`MobileStockCard` 패턴 확장)
4. **T-2, T-4, C-1** — 가설 빌더 및 지표 차트의 모바일 터치/가독성 폴리시
5. **N-3** — 200+ 항목 잠재 화면에 virtualization 도입 (chainsight `MobileCardList` 우선)
6. **나머지 MINOR** — 디자인 시스템 정합화 시 일괄 처리

## 부록: 데이터 출처

- 고정 폭 grep: `w-[NNpx]|min-w-[NNpx]|max-w-[NNpx]|h-[NNpx]|min-h-[NNpx]` — 100+ 매치 중 상위 패턴 분류
- 작은 글자 grep: `text-\[(10|11)px\]` — 100+ 매치
- 차트 grep: `from 'recharts'` 14파일 / `ResponsiveContainer` 15파일(테스트 1 포함) — 누락 0
- 가로 스크롤 grep: `overflow-x-(auto|scroll)` — 30+ 매치, 대부분 의도적 (admin 테이블, 칩 리스트, 가로 탭)
- 모바일 분기 grep: `hidden md:|md:hidden|hidden sm:|sm:hidden` — 12 파일, 의도적 분기 명확
- virtualization grep: `virtualiz|react-window|react-virtual|TanStack.*Virtual` — 0건
