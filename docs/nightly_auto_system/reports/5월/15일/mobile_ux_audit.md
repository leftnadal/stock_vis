# 모바일 UX 감사 보고서

- **대상**: `/Users/byeongjinjeong/Desktop/stock_vis/frontend`
- **기준 뷰포트**: iPhone 12/13/14 표준 폭 375px (모바일), 768px (태블릿 sm)
- **터치 타겟 기준**: Apple HIG 44×44pt, Material Design 48×48dp
- **감사 방식**: 정적 코드 분석 (실 브라우저 측정 X) — Tailwind 클래스 기반 추정
- **수정 여부**: 읽기 전용, 코드 수정 없음

---

## 요약

| 심각도 | 개수 | 정의 |
|---|---|---|
| **BLOCKER** | 8 | 모바일 사용 불가 또는 핵심 기능 차단 |
| **MAJOR** | 17 | 사용 가능하나 UX/접근성 심각하게 저하 |
| **MINOR** | 12 | 가독성·정밀도 손실, 대안 동작 존재 |
| **PASS** | 4 | 양호 (참고) |
| **합계** | **41** | |

**최우선 처리 권장 (BLOCKER)**
1. `MarketGraphCanvas` 고정 높이 `h-[560px]` (chainsight) — 모바일 첫 화면 점유율 70% 초과
2. `IndicatorRow` 2행 압축 레이아웃 — 한 행 300px+ 콘텐츠가 375px에서 overflow
3. `ScreenerTable` 12컬럼 모바일 미대응 — sticky 좌측 컬럼 없는 horizontal scroll
4. 분기 `QuarterlySparkline` `max-w-[100px]` 4-bar — 각 바 20-25px (터치 불가)
5. `BreadthDetail` 차트 `fontSize: 10` — WCAG AA 위반 (12px 미만)
6. `/stocks/[symbol]` 카테고리 탭 — 가로 강제 스크롤, 시각적 단서 부재
7. 인기 섹터 quick CTA `w-[110px]` × 3 — 모바일에서 wrapping/잘림
8. `Header.tsx` 의 모바일 햄버거 메뉴 자체가 `hidden` 처리됨 — `MobileNav.tsx` (Bottom Nav)가 단일 소스이나, 모바일에서 5개 핵심 라우트만 노출. **Thesis / Chain Sight / Market Pulse / Screener는 모바일에서 접근 경로 없음**

---

## 반응형 누락

### BLOCKER

- **frontend/components/chainsight/MarketGraphCanvas.tsx:760** — `h-[560px]` 고정. 모바일 812px 화면에서 헤더+섹터바+칩바 합치면 단일 페이지 진입 시 그래프 외 정보 모두 스크롤 영역으로. (BLOCKER)
- **frontend/components/chainsight/MarketGraphCanvas.tsx:676** — `'w-[110px] min-h-[68px] px-3 py-2'` 인기 섹터 버튼. 3개 가로 배치 시 330px + gap-3(24px) = 354px → 좌우 패딩 포함 시 375px 임계. 4번째 섹터 추가 시 wrap 강제. (BLOCKER)
- **frontend/components/thesis/dashboard/IndicatorRow.tsx:108-144** — 한 행에 값 `min-w-[60px]` + 비교라벨 `min-w-[120px]` + 스파크라인 `max-w-[100px]` + 지지/반박 텍스트. 최소 280px + gap-3 = 320px+. 가설 이름(text-sm)이 길면 truncate 적용. (BLOCKER)
- **frontend/components/strategy/ScreenerTable.tsx:128-336** — 12개 컬럼 테이블. `overflow-x-auto`(L128)만 존재, sticky 좌측 종목명 컬럼 없음. 모바일 가로 스크롤 시 종목 식별 불가. (BLOCKER)

### MAJOR

- **frontend/components/strategy/ScreenerTable.tsx:209,224** — `max-w-[180px] truncate`(회사명), `max-w-[120px] truncate`(섹터). title hover는 모바일 불가. (MAJOR)
- **frontend/components/validation/MetricCard.tsx:108** — `grid grid-cols-2 sm:grid-cols-4`. sm 브레이크포인트(640px) 이전 375-639px 구간 2열 유지로 셀 내부 텍스트 wrap. (MAJOR)
- **frontend/app/thesis/new/page.tsx:811-822** — suggestion cards `grid-cols-1 sm:grid-cols-2`. sm까지 1열 유지로 다단계 폼이 모바일에서 매우 긴 세로 스크롤. (MAJOR)
- **frontend/components/admin/AdminTabNav.tsx:30** — 6개 탭 `whitespace-nowrap overflow-x-auto`. 모바일에서 가로 스크롤 강제이나 sticky 부재 + 페이드 인디케이터 없음. (MAJOR)
- **frontend/app/admin/page.tsx** — 전체 어드민이 데이터 테이블 중심. 모바일 분기 없음. (MAJOR, 의도적 데스크톱 전용일 가능성 — 명시 라벨 필요)
- **frontend/app/chainsight/[symbol]/page.tsx:234-368** — `w-60`(좌측) + `w-72`(우측 `hidden lg:block`) + flex-1(중앙). 모바일에서 별도 `MobileCardList`로 분기되어 `/chainsight` 메인과 UI 일관성 깨짐. (MAJOR)
- **frontend/components/validation/SignalSummaryCard.tsx:36-41** — 7개 신호등이 `min-w-[72px]` × 7 = 504px → `overflow-x-auto`로 가로 스크롤 강제. 시각적 스크롤 단서 없음. (MAJOR)

### MINOR

- **frontend/components/layout/InvestingHeader.tsx:32,55,99** — `max-w-[1400px] mx-auto px-4`. 안전(컨테이너 max-w + auto margin) (MINOR — overflow 없음, 단 두 개 헤더 구현이 공존하는 점은 별도 검토 필요)
- **frontend/components/eod/SignalDetailSheet.tsx:97** — `w-full md:w-[420px] md:h-full`. 모바일 풀폭, 데스크톱 고정. 잘 분기됨 (PASS)
- **frontend/components/news/RecommendationCard.tsx:85** — `max-w-[150px] truncate`. (MINOR)
- **frontend/components/common/DataSourceBadge.tsx:171** — 툴팁 `min-w-[200px]`. 375px 화면에서 양옆 절단 가능. (MINOR)
- **frontend/components/eod/StockRow.tsx:66** — `min-w-[72px]`. 우측 가격 영역. (MINOR — 정렬 유지 목적, overflow 없음)

---

## 터치 타겟

### BLOCKER

- **frontend/components/thesis/dashboard/IndicatorRow.tsx:177-190** — 기간 선택 버튼 `px-2.5 py-0.5 text-[10px]`. 계산상 약 18-20px 높이로 44pt 한참 미달. 1M/1Y/3Y/5Y 4버튼이 모바일 핵심 인터랙션. (BLOCKER)
- **frontend/components/thesis/dashboard/QuarterlySparkline.tsx:41-49** — `flex-1 min-h-[44px]`. 부모 컨테이너가 `max-w-[100px]`(IndicatorRow:132)이라 4-bar 시 각 버튼 폭 약 22px → 44×44 미달. `min-h-[44px]`는 높이만 보장. (BLOCKER)
- **frontend/app/stocks/[symbol]/page.tsx:1030-1044** — 카테고리 탭 `px-3 py-1.5 text-xs`. py-1.5 = 6px+6px+text-xs(16px line-height) ≈ 28-30px 높이로 44pt 미달. (BLOCKER, IndicatorRow 기간 버튼과 같은 유형)

### MAJOR

- **frontend/components/chainsight/MarketGraphCanvas.tsx:854** — 노드 반지름 `NODE_SIZE_MAP = { xl: 20, lg: 17, md: 14, sm: 10 }` → 지름 20-40px. sm/md 노드는 44pt 미달. `nodePointerAreaPaint`(788-793)에서 동일 반지름 사용 → hit-area 확대 없음. (MAJOR)
- **frontend/components/chainsight/NodeTooltip.tsx:124-126** — 절대 위치 `position.left/top` + 4px 경계 보정만. 375px 화면에서 노드 우측 탭 시 200px 폭 tooltip이 화면 밖. (MAJOR)
- **frontend/components/chainsight/RelationFilterChips.tsx:229-230** — `overflow-x-auto` + 우측 페이드 그라디언트(w-12). 그라디언트가 pointer-events 차단 시 마지막 "전체 끄기" 버튼 클릭 불가. (MAJOR)
- **frontend/components/screener/Pagination.tsx:97,104,144,154** — `p-1.5`(6px) + `w-4 h-4`(16px) = 약 28px 시작/끝/이전/다음 버튼. 페이지 번호 버튼만 `min-w-[44px] min-h-[44px]`(L127) 적용. **불일치**. (MAJOR)
- **frontend/components/admin/news/AlertBadge.tsx:29** — 배지 자체 `min-w-[18px] h-[18px]`. 알림 인디케이터로 클릭 요소면 미달, 표시 전용이면 PASS. **클릭 가능성 확인 필요** (MAJOR)
- **frontend/components/eod/SignalFilterTabs.tsx:68** — `min-w-[18px] h-[18px] px-1 rounded-full text-[11px]` 카운트 배지. 표시 전용. (MAJOR if clickable)
- **frontend/components/thesis/common/AlertBell.tsx:18** — `min-w-[18px] h-[18px]` 알림 배지. 표시 전용. (MINOR)

### MINOR — 작은 텍스트 (text-[10px], text-[11px])

> 클릭 가능 요소에 한해 가독성 저하. 총 60건 이상 발견. 대표 위치만 기재.

- **frontend/app/thesis/new/page.tsx:688,752,753,765,831,843,1063** — 카드 라벨, 카테고리 배지, 보조 설명에 `text-[10px]` 광범위 사용. (MINOR)
- **frontend/app/market-pulse-v2/page.tsx:77** — `text-[10px]` 푸터 (모델 버전 표시). (MINOR)
- **frontend/components/thesis/dashboard/IndicatorRow.tsx:95,118,148,161,167,182,232** — 날짜 라벨, 비교 라벨, 전제명, 차트 기간 버튼 등 8건. 일부는 클릭 요소 → MAJOR (L182 기간 버튼은 BLOCKER로 별도 기재)
- **frontend/components/chainsight/MarketGraphCanvas.tsx:690,698** — 섹터 칩 변동률(`text-[11px]`), 시드 수(`text-[10px]`). (MINOR)
- **frontend/components/validation/MetricBarChart.tsx:74** — 랭크 배지 `text-[10px]`. 표시 전용. (MINOR)

---

## 네비게이션

### 모바일 진입 가능 라우트 누락 — BLOCKER

- **frontend/components/layout/MobileNav.tsx:11-17** — 5개 라우트만 노출: `/`, `/stocks`, `/news`, `/portfolio`, `/mypage`.
  - **누락된 핵심 라우트**: `/thesis`, `/chainsight`, `/market-pulse`, `/screener`, `/validation`, `/dashboard`, `/ai-analysis`, `/admin`, `/watchlist`
- **frontend/components/layout/Header.tsx:157-163** — 햄버거 버튼 `className="hidden ..."`. 의도적 비활성화 (L155-156 주석 "이중 네비 제거"). 결과: **모바일 사용자는 위 9개 라우트에 직접 접근 경로 없음** (BLOCKER)

### 햄버거 메뉴 / 사이드바 — MAJOR

- **frontend/components/layout/Header.tsx:42-109** — 데스크톱 nav 7개 라우트가 `hidden md:flex`로 모바일에서 완전 숨김. MobileNav가 5개만 노출하므로 2개 라우트(`/screener`, `/market-pulse`, `/chainsight`, `/thesis`) 손실. (MAJOR, 위 BLOCKER와 동일 원인)
- **frontend/components/layout/Header.tsx:167-256** — 햄버거 분기 로직(`isMenuOpen`)은 코드상 존재하나 버튼이 hidden이라 트리거 불가. **죽은 코드** (MAJOR, 정리 또는 활성화 결정 필요)
- **frontend/components/layout/InvestingHeader.tsx** — 별도 헤더 컴포넌트, 모바일 분기 전무. 데스크톱 가정 (`max-w-[1400px]`). 어디서 사용되는지 별도 확인 필요. (MAJOR)

### Bottom Nav — PASS

- **frontend/components/layout/MobileNav.tsx:22-45** — `h-16 min-h-[44px] py-2 flex-1` — 터치 타겟 양호, 아이콘+라벨, active 상태 색상 변경. (PASS)

### Virtualization — MINOR

- 검색 결과: 코드베이스 전반에 `react-window`/`react-virtual` 등 라이브러리 import 없음 (별도 grep 필요 시 확장 가능). 긴 목록(`StocksTab`, `NewsTab`, `screener` 결과 100건 이상)에서 모바일 메모리/스크롤 성능 저하 우려. (MINOR — 측정 미실시)

### View Mode 토글 모바일 숨김 — MAJOR

- **frontend/app/screener/page.tsx:752** — `hidden sm:flex` 뷰 모드 토글. 모바일에서 카드만 강제. 단일 경로 OK이나 사용자 선택권 박탈. 또한 L72 초기값 `'table'`인데 모바일에서는 카드 표시 → 상태 불일치. (MAJOR)

---

## 차트/그래프

### Recharts ResponsiveContainer 적용 — 대체로 PASS

| 파일 | ResponsiveContainer | 높이 처리 | 평가 |
|---|---|---|---|
| `components/charts/StockPriceChart.tsx:272` | O | `height={400}` 고정 | MINOR |
| `components/stock/StockChart.tsx:652,748` | O | `getResponsiveChartHeight()` 동적 (L177-187) | **PASS (모범)** |
| `components/portfolio/PortfolioChart.tsx:77,97` | O | `height={400}` 고정 | MAJOR |
| `components/news/SentimentChart.tsx:80` | O | `height="100%"` | PASS |
| `components/macro/YieldCurveChart.tsx:93` | O | `h-64` Tailwind | MINOR |
| `components/validation/MetricBarChart.tsx:78` | O | `h-48` 부모, `height="100%"` | MAJOR (모바일 비율 깨짐) |
| `components/thesis/dashboard/IndicatorRow.tsx:197,235` | O | `height={160/140}` 고정 | MAJOR |
| `components/admin/news/MLTrendChart.tsx` | O | — | MAJOR (fontSize 11) |
| `app/market-pulse-v2/details/BreadthDetail.tsx:45,46` | O | — | **BLOCKER (fontSize 10)** |

### BLOCKER

- **frontend/app/market-pulse-v2/details/BreadthDetail.tsx:45-46** — XAxis/YAxis `fontSize={10}`. WCAG AA 미달 + 모바일 화면에서 사실상 판독 불가. (BLOCKER)

### MAJOR

- **frontend/components/thesis/dashboard/IndicatorRow.tsx:207,211,248,252** — `fontSize={9}` (XAxis), `fontSize={10}` (YAxis). 분기/일간 차트 양쪽. (MAJOR — 9px는 BLOCKER 수준이나 차트 보조 라벨이라 MAJOR 처리)
- **frontend/components/stock/StockChart.tsx:657,667** — `fontSize: 11`. (MAJOR)
- **frontend/components/validation/MetricBarChart.tsx:83,87** — `fontSize: 11`. (MAJOR)
- **frontend/components/admin/news/MLTrendChart.tsx:95,99** — `fontSize: 11`. (MAJOR)
- **frontend/components/portfolio/PortfolioChart.tsx:104-107** — `angle={-45} height={100}`. 모바일 240-280px 너비에 회전 X축 라벨이 컨테이너 초과. (MAJOR)
- **Recharts `<Tooltip />` 전반** — 모바일 터치 이벤트 미지원. `cursor`/`active` 명시 핸들러 없는 차트는 모바일에서 툴팁 호출 불가. (MAJOR — 차트 7개 영향)

### 분기 스파크라인 모바일 가독성 — BLOCKER (재기재)

- **frontend/components/thesis/dashboard/IndicatorRow.tsx:131-138** + **frontend/components/thesis/dashboard/QuarterlySparkline.tsx:33-69** — `max-w-[100px]` 부모 + 4 bars + `text-[11px]` Q라벨. 각 bar 약 22px, 라벨 충돌 가능. 호버 툴팁 `text-[10px]`(L62)은 터치 후 화면 밖 가능. (BLOCKER)

---

## 페이지별 상세

### `/` (홈, `app/page.tsx`)
- **컨테이너**: `max-w-6xl mx-auto px-4` (안전)
- **그리드**: `grid-cols-1` 기본 (PASS)
- **이슈**: 없음

### `/dashboard`
- **그리드**: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` (PASS)
- **이슈**: 차트 카드 내부 ResponsiveContainer 고정 높이 (MINOR — 위 차트 섹션 참조)

### `/thesis`, `/thesis/[thesisId]`, `/thesis/new`
- **BLOCKER**: `IndicatorRow` 2행 압축 + 분기 스파크라인 + 기간 버튼 터치 미달
- **MAJOR**: `/thesis/new` 폼이 `grid-cols-1 sm:grid-cols-2` (모바일 1열로 매우 긴 스크롤)
- **MAJOR**: `OptionButton` `min-h-[52px]/[56px]` 혼합, 정렬 불일치
- **MINOR**: 카테고리 배지 `text-[10px]` 광범위
- **종합**: thesis 관제실은 모바일 우선 재설계 필요. 단일 모바일 진입 경로 없음(BottomNav 누락)

### `/chainsight`, `/chainsight/[symbol]`, `/chainsight/watchlist`
- **BLOCKER**: `MarketGraphCanvas` `h-[560px]` + `w-[110px]` 인기 섹터 CTA
- **MAJOR**: `NodeTooltip` 경계 오버플로우, `RelationFilterChips` 마지막 칩 페이드 차단
- **MAJOR**: 노드 hit-area 44pt 미달, `/chainsight/[symbol]`의 좌/우 패널 모바일 동작이 메인과 분기 일관성 결여
- **MINOR**: `SectorBar` 칩 `max-w-[120px]` 텍스트 잘림
- **종합**: SVG 그래프 자체 pan/zoom 핵심 인터랙션 검증 필요. BottomNav 진입 경로 없음

### `/screener`
- **BLOCKER**: `ScreenerTable` 12컬럼 모바일 미대응
- **MAJOR**: `viewMode` 토글 모바일에서 숨김(L752), 사용자 선택권 없음
- **MAJOR**: AI 키워드/테제 버튼 `text-xs px-3 py-1.5` 터치 미달
- **PASS**: `MobileStockCard`(L854-875) 카드 뷰 잘 설계됨 — 3컬럼 메트릭 그리드, 전폭 액션 버튼
- **PASS**: `Pagination.tsx` 페이지 번호 버튼 44pt 만족
- **종합**: `MobileStockCard`는 모범. 다만 토글 비노출 정책 재검토 필요

### `/validation`
- **MAJOR**: `SignalSummaryCard` 7개 신호등 504px → 가로 스크롤 강제
- **MAJOR**: `MetricCard` `grid-cols-2 sm:grid-cols-4` — sm 미만 2열 압축
- **MAJOR**: `MetricBarChart` `h-48` 부모 + 모바일 비율 깨짐 + fontSize 11
- **MINOR**: 비교 테이블(`LeaderComparisonSection`) 헤더 min-w 부재

### `/stocks/[symbol]`
- **BLOCKER**: 카테고리 탭 가로 스크롤 강제(L1030-1044)
- **PASS**: 검증 탭 사이드바 모바일 시 stack 폴백

### `/admin`
- **MAJOR**: 전 탭(Stocks/News/MarketPulse/System 등) 데이터 테이블 중심, 모바일 분기 전무
- **MAJOR**: `AdminTabNav` 6탭 `whitespace-nowrap overflow-x-auto`, sticky/페이드 없음
- **MAJOR**: 어드민 진입 자체 BottomNav 누락
- **종합**: "데스크톱 전용" 명시 라벨 또는 모바일 단순화 결정 필요

### `/market-pulse`, `/market-pulse-v2`
- **BLOCKER**: `BreadthDetail` 차트 fontSize 10
- **MAJOR**: BottomNav에 진입 경로 없음
- **MINOR**: 푸터 `text-[10px]` 모델 버전 표시 — 표시 전용 (MINOR)

### `/news`
- **MINOR**: `AINewsBriefingCard` 차트 `max-w-[200px]` 인디케이터 바 (안전)
- **MINOR**: `RecommendationCard` 종목명 `max-w-[150px] truncate`
- **종합**: 비교적 모바일 친화적

### `/portfolio`
- **MAJOR**: `PortfolioChart` X축 `angle={-45}` 모바일 폭 초과
- **MAJOR**: 차트 `height={400}` 고정으로 모바일에서 비대
- **그리드**: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` (PASS)

### `/mypage`, `/login`, `/signup`
- 별도 분석 미실시 (일반 폼 페이지로 추정)

### `/rag` (ChatInterface)
- **MINOR**: `frontend/components/rag/ChatInterface.tsx:198` — `h-[52px] w-[52px]` 전송 버튼 (PASS, 44pt 초과)
- **MINOR**: `SuggestionChips.tsx:40` — `max-w-[150px] truncate` (MINOR)

---

## 부록: 데스크톱 전용 컴포넌트 후보 (sm:/md:/lg: 브레이크포인트 미사용)

> `frontend/components/validation`에서 `MetricCard.tsx`만 브레이크포인트 사용. 나머지 9개 파일은 미사용 또는 grep miss. **개별 검증 필요**.

해당 파일들:
- `frontend/components/validation/SignalSummaryCard.tsx`
- `frontend/components/validation/MetricBarChart.tsx`
- `frontend/components/validation/LeaderComparisonSection.tsx`
- `frontend/components/validation/PeerContextBar.tsx`
- (외 5개)

---

## 권장 조치 우선순위

| 순위 | 작업 | 영향 |
|---|---|---|
| P0 | BottomNav에 `/screener`, `/thesis`, `/chainsight`, `/market-pulse` 추가 또는 햄버거 메뉴 활성화 | 모바일에서 4개 핵심 라우트 도달 불가 해결 |
| P0 | `IndicatorRow`를 모바일에서 3행 stacked로 분리 (값 / 변동률 / 스파크라인) | thesis 관제실 모바일 사용 가능화 |
| P0 | `MarketGraphCanvas` 높이 반응형 `h-96 md:h-[560px]` + 인기 섹터 `w-24 md:w-[110px]` | chainsight 모바일 첫 화면 복구 |
| P0 | `ScreenerTable` 모바일 sticky 좌측 컬럼 또는 카드 뷰 강제 + 명시 안내 | 스크리너 모바일 사용성 |
| P1 | 모든 차트 `fontSize` 12 이상으로 통일 (특히 BreadthDetail 10 → 12) | WCAG AA 준수 |
| P1 | `IndicatorRow` 기간 버튼 + `/stocks/[symbol]` 카테고리 탭 `py-2.5` 이상 + `min-h-[44px]` | 핵심 인터랙션 터치 타겟 |
| P1 | `Pagination` 시작/끝/이전/다음 버튼 `min-w-[44px] min-h-[44px]` 통일 | 페이지네이션 일관성 |
| P2 | Recharts Tooltip 모바일 터치 핸들러 추가 (`cursor={false}` + onTouch) | 차트 인터랙션 |
| P2 | `text-[10px]`/`text-[11px]` 클릭 요소 → 최소 12px 상향 | 가독성·접근성 |
| P2 | `Admin` 페이지 "데스크톱 권장" 명시 라벨 또는 모바일 단순화 결정 | 사용자 기대 정렬 |

---

**감사 종료**. 본 보고서는 정적 코드 분석 기반이며, 실 디바이스 검증(브라우저 DevTools, 실 iPhone/Android 측정)으로 보강 권장.
