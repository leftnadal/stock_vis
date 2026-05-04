# 모바일 UX 감사 보고서

**작성일**: 2026-05-05
**대상**: `frontend/` 전체 (Next.js 16 + Tailwind)
**기준 뷰포트**: 모바일 375 × 667 (iPhone SE), 768 (sm), 1024 (lg)
**기준 터치 타겟**: Apple HIG 44 × 44pt (= Tailwind `min-h-11 / min-w-11`)
**모드**: read-only — 코드 수정 없음

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|------|----|----|
| BLOCKER | 9 | 모바일에서 핵심 기능 접근/조작 불가 |
| MAJOR | 14 | 모바일에서 사용 가능하나 가독성·터치 정확도 저하 |
| MINOR | 11 | 시각적 개선 여지, 기능 영향 없음 |
| **합계** | **34** | |

---

## 반응형 누락

### BLOCKER

#### 1. `InvestingHeader.tsx` — 모바일 대응 0건
- 위치: `frontend/components/layout/InvestingHeader.tsx:1-119`
- 증거:
  - L32, L55, L99: `max-w-[1400px]` 고정 컨테이너 3중 적용
  - L33: 상단바 `flex items-center justify-between h-10 text-xs` → 6개 텍스트 칩 (날짜, S&P/나스닥/다우 변동률, 한국어, 로그인) 한 줄 유지
  - L66: 검색바 `flex-1 max-w-xl mx-8` → 모바일 8px 마진 차감 후 320px도 안 됨
  - L98–117: 네비 8개 항목 `flex items-center h-10` 한 줄 → 375px에서 가로 overflow
  - sm:/md:/lg: prefix 단 1건도 없음
- 영향: 컴포넌트 자체가 사용되면 모바일 가로 스크롤 발생. (현재 `app/layout.tsx`는 `Header.tsx`만 사용 — InvestingHeader는 미사용 dead component일 가능성 높음. 사용 추적 필요.)

#### 2. 헤더 + 바텀 네비게이션 라우팅 불일치
- 위치:
  - `frontend/app/layout.tsx:59-64` — `<Header />` + `<MobileNav />` 둘 다 항상 렌더
  - `frontend/components/layout/MobileNav.tsx:10-16`
- 증거:
  - MobileNav 5개 항목: `홈 / 종목 / 뉴스 / 포트폴리오 / 내정보` (`/`, `/stocks`, `/news`, `/portfolio`, `/profile`)
  - **`/profile` 경로 미존재** (실제 마이페이지는 `/mypage`) → 모바일 사용자 broken link
  - **누락된 핵심 메뉴**: `/chainsight`, `/thesis`, `/market-pulse`, `/screener`, `/ai-analysis`, `/watchlist`
  - Header.tsx `md:hidden` hamburger menu(L156-161) 모바일에서 모든 메뉴 접근 가능하지만, 동시에 화면 하단 64px 바텀 네비도 표시 → 중복 + 충돌
- 영향: 모바일 사용자가 `/thesis`, `/screener` 등 서비스 핵심 메뉴에 접근할 때 햄버거 메뉴 의존, 바텀 탭은 잘못된 5개 메뉴만 노출. `/profile` 클릭 시 404.

#### 3. 포트폴리오 페이지 헤더 — 모바일 wrap 누락
- 위치: `frontend/app/portfolio/page.tsx:97-119`
- 증거:
  - L97: `flex justify-between items-center mb-8`
  - L99: `text-3xl font-bold` 한국어 "내 포트폴리오"
  - L102: `flex space-x-3` 안에 두 버튼 ("새로고침", "종목 추가")
  - sm: 분기점 없음
- 영향: 375px에서 제목 폭 + 버튼 2개 폭 합산이 자주 overflow. 제목이 줄어들거나 버튼이 잘림.

### MAJOR

#### 4. ScreenerTable — 모바일 카드 뷰 강제 미적용
- 위치: `frontend/app/screener/page.tsx:752-855`, `frontend/components/strategy/ScreenerTable.tsx:127-336`
- 증거:
  - 페이지 L845: `<div className="${viewMode === 'table' ? 'hidden sm:block' : 'hidden'}">` → sm 미만 강제 카드뷰
  - 그러나 `ScreenerTable.tsx`는 12개 컬럼 (종목/거래소/섹터/가격/변동률/시가총액/거래량/배당률/베타/유형/AI키워드/액션) — `overflow-x-auto`(L128)로 가로 스크롤 처리
  - 모바일 토글(L752 `hidden sm:flex`) 없으므로 사용자가 강제로 테이블을 볼 수 없음
- 영향: 정렬 기능(`onClick={handleSort}`)이 모바일에서 사용 불가 (카드 뷰에는 정렬 토글 없음).

#### 5. PortfolioTable — 카드 뷰 없음, 12 컬럼
- 위치: `frontend/components/portfolio/PortfolioTable.tsx:259-300`
- 증거:
  - L259: `overflow-x-auto`로 처리
  - L262-298: 12 컬럼 (종목/보유수량/평균매수가/현재가/전일대비/평가금액/손익/수익률/목표가/손절가/비중/관리)
  - 페이지(`portfolio/page.tsx`)에서 viewMode='table' 선택 시 카드 폴백 없음
- 영향: 모바일 사용자가 페이지당 가로 스크롤 12회 — 비중/관리 컬럼 도달까지 1200px 스크롤.

#### 6. StockTable.tsx — overflow-x-auto만 있고 모바일 카드 미존재
- 위치: `frontend/components/stocks/StockTable.tsx:34-46`
- 증거: 7 컬럼 (종목명/현재가/변동/변동%/시가총액/섹터/차트)
- 영향: 4 → 모바일에서 스크롤 안 하면 변동% 까지만 보임.

#### 7. Header (`Header.tsx`) — 검색바 모바일에서 햄버거 펼침 시에만
- 위치: `frontend/components/layout/Header.tsx:111-123, 242-253`
- 증거:
  - 데스크톱 검색: `hidden md:block flex-1 max-w-md mx-4` (L112)
  - 모바일 검색: 메뉴 펼친 상태에서만 노출 (L242-253) — 항상 보이지 않음
- 영향: 모바일에서 검색하려면 햄버거 → 메뉴 펼치기 → 검색 (3단계). MobileNav에 검색 진입점 없음.

#### 8. AdminTabNav — 6개 탭 가로 스크롤
- 위치: `frontend/components/admin/AdminTabNav.tsx:30-48`
- 증거: `flex gap-1 overflow-x-auto`, `whitespace-nowrap` — 이론상 모바일에서 작동
- 그러나 `frontend/app/admin/page.tsx`는 데스크톱 전용 화면 (StocksTab, ScreenerTab, NewsTab 등 광범위 데이터 테이블) → 모바일에서 의미 있게 사용 불가
- 영향: 관리자 페이지 모바일 접근 시 가로 스크롤 + 잘린 통계 테이블.

### MINOR

#### 9. `chainsight/[symbol]` 데스크톱 3-panel — 우측 패널 lg 미만 숨김
- 위치: `frontend/app/chainsight/[symbol]/page.tsx:298, 358`
- 증거:
  - 좌측 AIGuidePanel `w-60` (L298) — 항상 표시 (768~1023px도 표시)
  - 우측 NodeDetailPanel `w-72 ... hidden lg:block` (L358) → 768~1023px 태블릿에서는 사라짐
  - 모바일은 별도 분기(`isMobile && !graphOverlay`, L152-170)로 잘 처리
- 영향: 태블릿(768~1023)에서 노드 클릭 시 상세를 볼 수 없음.

#### 10. `app/thesis/[thesisId]/page.tsx` — `max-w-lg mx-auto`
- 위치: `frontend/app/thesis/[thesisId]/page.tsx:31, 41, 62`
- 증거: `max-w-lg`(512px) 고정. 데스크톱에서도 가운데 좁게 표시 (모바일 우선 디자인이 의도)
- 영향: 데스크톱에서 좌우 공백 과다, 차트 영역 협소. 모바일에는 적절.

---

## 터치 타겟

> Apple HIG: 44 × 44pt 권장. Material Design: 48dp. 아래는 모두 그 이하.

### BLOCKER

#### 11. SignalCard / StockRow의 Chain Sight `<Network>` 링크
- 위치:
  - `frontend/components/eod/SignalCard.tsx:175` → `<Network className="w-2.5 h-2.5" />` (10 × 10px)
  - `frontend/components/eod/StockRow.tsx:50` → `<Network className="w-3 h-3" />` (12 × 12px)
- 증거: `<Link>` 자체에 패딩 없음, 아이콘 바운딩 박스만 클릭 영역
- 영향: 메인 페이지 EOD 카드의 Chain Sight 진입이 사실상 정확 탭 불가.

#### 12. PresetGallery 삭제 버튼 — opacity-0 group-hover
- 위치: `frontend/components/screener/PresetGallery.tsx:191-204`
- 증거:
  - `opacity-0 group-hover:opacity-100` (L197) → 모바일은 hover 이벤트 없음 → **영구 숨김**
  - `p-1` + `<svg className="w-3.5 h-3.5">` → 22 × 22pt
- 영향: 모바일 사용자는 사용자 정의 프리셋을 삭제할 방법이 없음.

#### 13. IndicatorRow 차트 기간 토글 (1M/1Y/3Y/5Y)
- 위치: `frontend/components/thesis/dashboard/IndicatorRow.tsx:178-189`
- 증거: `px-2.5 py-0.5 text-[10px]` → 약 32 × 16pt
- 영향: 가설 관제실에서 차트 기간 변경 정확 탭 어려움.

### MAJOR

#### 14. AlertBell — 36 × 36pt
- 위치: `frontend/components/thesis/common/AlertBell.tsx:11-23`
- 증거: `p-2 -mr-2` + `<Bell size={20} />` → 36pt 정사각형
- 권장 44pt 미만.

#### 15. AlertBadge — 36 × 36pt
- 위치: `frontend/components/admin/news/AlertBadge.tsx:21-33`
- 증거: `w-9 h-9` (36 × 36)

#### 16. Pagination 화살표 4개
- 위치: `frontend/components/screener/Pagination.tsx:97, 107, 144, 152`
- 증거: `p-1.5` + `w-4 h-4` → 28 × 28pt (BLOCKER 직전 수준)
- 페이지 번호 버튼은 `min-w-[32px] px-2 py-1.5` → 약 32 × 32pt — 미만.

#### 17. CategorySidebar 항목 (validation)
- 위치: `frontend/components/validation/CategorySidebar.tsx:48-60`
- 증거: `px-3 py-2 text-sm` → 약 36pt 높이
- 사용 컨텍스트는 데스크톱 sticky sidebar(`hidden lg:block`)이므로 모바일 영향 낮음.

#### 18. SignalFilterTabs 카운트 배지
- 위치: `frontend/components/eod/SignalFilterTabs.tsx:67-77`
- 증거: 부모 버튼 `px-3 py-1.5` (32~34pt) — 카운트 자체는 비클릭. 부모 버튼이 클릭 영역인 점은 OK.

#### 19. SignalCard HelpCircle (교육 팁 토글)
- 위치: `frontend/components/eod/SignalCard.tsx:102-114`
- 증거: `p-1` + `w-3.5 h-3.5` → 22 × 22pt

#### 20. PresetGallery info 버튼
- 위치: `frontend/components/screener/PresetGallery.tsx:235-249`
- 증거: 버튼 패딩 없음, `text-[10px]`, `w-3 h-3` 아이콘 → 약 12pt 높이

#### 21. SignalDetailSheet 닫기 버튼
- 위치: `frontend/components/eod/SignalDetailSheet.tsx:136-141`
- 증거: `p-1.5` + `w-4 h-4` → 28pt

### MINOR

#### 22. KeywordTag 칩
- 위치: `frontend/components/keywords/KeywordTag.tsx:42`
- 증거: `px-2 py-0.5 text-[10px]` (sm 사이즈)
- 클릭 영역으로도 사용되므로 모바일에서 정밀 탭 어려움. 다만 전제 칩 성격 상 영향 작음.

#### 23. ThesisListCard 등 Link 카드는 충분
- 위치: `frontend/app/thesis/(list)/page.tsx` (ThesisListCard 사용)
- 증거: 카드 단위 Link로 wrap → 큰 터치 영역. **양호.**

---

## 네비게이션

### BLOCKER

#### 24. MobileNav 라우팅 깨짐 (위 #2와 동일 — 재집계 안 함)
- `/profile` 미존재, `/thesis` 등 핵심 메뉴 미수록.

#### 25. Bottom navigation + sticky 하단 CTA 충돌
- 위치:
  - `frontend/app/thesis/[thesisId]/indicators/page.tsx:293-311` → `border-t bg-gray-950 px-4 py-4 space-y-2` 하단 고정 CTA "관제 시작하기"
  - `frontend/app/thesis/[thesisId]/close/page.tsx:131` → 동일 패턴
  - `frontend/app/thesis/new/page.tsx:636` → `flex flex-col h-[calc(100dvh-env(safe-area-inset-top))]`
  - `frontend/app/layout.tsx`의 MobileNav (md:hidden, fixed bottom-0, h-16)
- 증거: thesis 하위 페이지들은 `100dvh - safe-area-inset-top`만 차감, **하단 MobileNav 64px는 고려 안 됨**
- 영향: 가설 마감/지표 추가 페이지에서 "관제 시작하기" 같은 핵심 CTA가 바텀 네비 뒤에 가려질 수 있음.

### MAJOR

#### 26. 메인 페이지 `pb-20 md:pb-0` 패턴 일관성 부족
- 위치: `frontend/app/page.tsx:71` (`min-h-screen pb-20 md:pb-0`)
- 동일 패턴 사용 페이지: 1개 (홈)만 확인됨
- 미적용 페이지 예: `/portfolio`, `/news`, `/screener`, `/market-pulse`, `/stocks/[symbol]` 등
- 영향: 페이지 마지막 콘텐츠가 64px 바텀 네비 뒤에 가림.

#### 27. Virtualization 부재
- 검색 결과: `react-window` / `react-virtual` / `virtuoso` / `@tanstack/react-virtual` **0건** (frontend 전체)
- 영향:
  - 스크리너 결과 (S&P 500: 500종목, FMP 검색 시 5,000+종목) 한 번에 DOM 생성
  - 알림 리스트, 관제 지표 리스트, 뉴스 카드 무한스크롤 모두 비가상화
  - 모바일 저사양 기기에서 스크롤 jank 위험

### MINOR

#### 28. ChainSight 좌측 토글 문구
- 위치: `frontend/app/chainsight/[symbol]/page.tsx:276-281` "패널 닫기 / AI 가이드"
- 모바일 분기 별도 OK, 데스크톱 토글 자체는 문제 없음.

#### 29. 사이드바(stocks/[symbol]) `w-48 hidden lg:block`
- 위치: `frontend/app/stocks/[symbol]/page.tsx:1058`
- 증거: 모바일은 카테고리 가로 스크롤 칩으로 대체(L1037-1043) → **양호.**

---

## 차트 / 그래프

### MAJOR

#### 30. Recharts axis font-size 8~10px
- 위치 (대표):
  - `frontend/components/thesis/dashboard/IndicatorRow.tsx:207, 211, 248, 252` → `fontSize={9}` X축, `fontSize={10}` Y축
  - `frontend/components/thesis/dashboard/QuarterlySparkline.tsx:54` → `text-[8px]` 분기 라벨
  - `frontend/components/validation/MetricBarChart.tsx:46` → `fontSize={9}` 라벨, X/Y `fontSize: 11`
- 영향: 모바일 retina 화면에서도 Q1/Q2/Q3 분기 라벨이 거의 판독 불가.

#### 31. PortfolioChart 고정 height 400
- 위치: `frontend/components/portfolio/PortfolioChart.tsx:77, 134`
- 증거: `<ResponsiveContainer width="100%" height={400}>` 모든 분기에서 고정
- 영향: 모바일 세로(667px)에서 차트 단독 60% 차지 → 토글/데이터 확인 동시 표시 어려움.

#### 32. StockPriceChart 기본 height={400}
- 위치: `frontend/components/charts/StockPriceChart.tsx:40, 272`
- 동일 이슈.

#### 33. MetricBarChart `h-48` 컨테이너 + `right: 50`
- 위치: `frontend/components/validation/MetricBarChart.tsx:72, 79`
- 증거: 우측 마진 50px (last-point label 공간) → 375px 화면에서 차트 실제 폭은 ~280px
- 영향: 모바일에서 5개년 라인이 짧게 압축.

### MINOR

#### 34. ResponsiveContainer 적용 현황 (양호)
- 11개 차트 컴포넌트에서 `ResponsiveContainer` 사용 확인:
  - `IndicatorRow.tsx`, `IndividualMiniCharts.tsx`, `MetricBarChart.tsx`, `MLTrendChart.tsx`, `SectorHeatmap.tsx`, `StockChart.tsx`, `SentimentChart.tsx`, `YieldCurveChart.tsx`, `PortfolioChart.tsx`, `StockPriceChart.tsx`, `IndicatorRow.test.tsx`
- 누락: `QuarterlySparkline.tsx` (gap 기반 flex-1 → 자체 반응형, 양호)
- 결론: 너비 반응성은 잘 갖춰짐. 폰트/높이가 약점.

---

## 페이지별 상세

### `/` (EOD Dashboard) — `frontend/app/page.tsx`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `pb-20 md:pb-0`로 바텀 네비 회피 | OK | 다른 페이지 미적용 — 비일관 |
| SignalCard `<Network w-2.5>` Chain Sight 링크 | BLOCKER | #11 |
| StockRow `max-w-[140px]` 회사명 truncate | OK | 모바일 의도된 처리 |
| SignalFilterTabs `overflow-x-auto scrollbar-hide` | OK | 가로 스크롤 정상 |
| MarketSummaryBar `text-[10px]` 비율 | MINOR | 가독성 |

### `/portfolio`

| 항목 | 심각도 | 비고 |
|----|----|----|
| 헤더 `flex justify-between` wrap 미적용 | BLOCKER | #3 |
| PortfolioTable 12 컬럼 카드 폴백 부재 | MAJOR | #5 |
| 그리드 `grid-cols-1 md:2 lg:3` | OK | 카드뷰는 적절 |
| PortfolioChart height={400} | MAJOR | #31 |
| 바텀 네비 padding 미적용 | MAJOR | #26 |

### `/news`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `grid-cols-1 lg:grid-cols-3 gap-4` | OK | |
| NewsCard 썸네일 `w-32 h-24` 고정 | MINOR | 375px에서 텍스트 영역 ~190px |
| StockInsightCard `max-h-[360px]` 드롭다운 | OK | |
| 바텀 네비 padding 미적용 | MAJOR | #26 |

### `/stocks/[symbol]`

| 항목 | 심각도 | 비고 |
|----|----|----|
| 사이드바 `w-48 hidden lg:block` + 모바일 카테고리 칩 | OK | 양호한 분기 |
| `grid grid-cols-2 md:3 lg:4` 통계 그리드 | OK | |
| 1차 검증 모바일 카테고리 탭 (L1037) | OK | |
| LeaderComparisonSection 차트 폰트 9px | MINOR | #30 |

### `/screener`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `grid-cols-1 lg:grid-cols-3` (Breadth + Heatmap) | OK | |
| 모바일 viewMode 토글 숨김 | MAJOR | #4 |
| AI 키워드/테제 텍스트 `hidden sm:inline` | OK | 의도된 압축 |
| PresetGallery 삭제 버튼 hover 의존 | BLOCKER | #12 |
| PresetGallery 활성 배지 `-top-2 -left-2` | MINOR | 화면 가장자리 카드에서 잘림 가능 |
| AdvancedFilterPanel `text-[10px] descriptionKo` | MINOR | 가독성 |

### `/thesis/(list)`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `space-y-8` 섹션 구성 | OK | |
| ThesisListCard Link wrap | OK | 충분한 터치 영역 |
| AlertBell `p-2` 36pt | MAJOR | #14 |

### `/thesis/[thesisId]` (관제실)

| 항목 | 심각도 | 비고 |
|----|----|----|
| `max-w-lg mx-auto px-4 pt-4 pb-20` | OK | 모바일 우선 디자인 |
| IndicatorRow 토글 탭 `text-[10px]` | BLOCKER | #13 (1M/1Y/3Y/5Y) |
| QuarterlySparkline 분기 라벨 `text-[8px]` | MAJOR | #30 |
| Recharts `fontSize={9}` X축 | MAJOR | #30 |
| description/recommendation_reason `text-[11px]` | MINOR | |

### `/thesis/new` (가설 빌더)

| 항목 | 심각도 | 비고 |
|----|----|----|
| `h-[calc(100dvh-env(safe-area-inset-top))]` 사용 | OK | safe area 처리 |
| 바텀 네비 64px 미차감 | BLOCKER | #25 |
| OptionButton `min-h-[52px]/[56px]` | OK | 터치 타겟 양호 |
| ChatBubble `min-h-[44px]` | OK | |
| 추천 카드 `text-[10px]` 라벨 | MINOR | |

### `/thesis/[thesisId]/indicators`

| 항목 | 심각도 | 비고 |
|----|----|----|
| 하단 CTA "관제 시작하기" 바텀 네비와 충돌 가능 | BLOCKER | #25 |
| `py-4 text-sm font-medium rounded-xl` 메인 CTA | OK | 44pt 이상 |
| AddIndicatorSheet `text-[9px]/[10px]` 메타 | MINOR | |

### `/chainsight/[symbol]`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `isMobile` 훅으로 카드 리스트 분기 | OK | 양호 |
| 그래프 오버레이 `flex-1 text-xs py-2` 액션 3개 | OK | 약 36pt — 경계선 |
| 데스크톱 우측 패널 `hidden lg:block` (태블릿 누락) | MINOR | #9 |
| GraphCanvas 터치 인터랙션 | 검증 불가 | force-graph-2d 라이브러리 의존 |

### `/market-pulse`

| 항목 | 심각도 | 비고 |
|----|----|----|
| 헤더 액션 텍스트 `hidden sm:inline` | OK | |
| `grid-cols-1 lg:grid-cols-3` Fear&Greed + Yield | OK | |
| GlobalMarketsCard `grid-cols-1 md:2 lg:4` | OK | |
| 바텀 네비 padding 미적용 | MAJOR | #26 |

### `/admin`

| 항목 | 심각도 | 비고 |
|----|----|----|
| AdminTabNav `overflow-x-auto whitespace-nowrap` | OK | |
| 콘텐츠 자체가 모바일 부적합 (시스템 테이블 등) | MAJOR | #8 |
| TaskLogViewer `max-w-[260px] truncate` 메타 | OK | |

### `/login`, `/signup`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `grid-cols-2 gap-3` 소셜 로그인 | OK | |
| 폼 입력 필드 height 표준 (`py-2`) | MINOR | 44pt 이하 — 다만 양호 |

### `/watchlist`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `grid-cols-1 lg:grid-cols-3` | OK | |
| 바텀 네비 padding 미적용 | MAJOR | #26 |

### `/ai-analysis`

| 항목 | 심각도 | 비고 |
|----|----|----|
| `relative flex h-screen flex-col` | OK | |
| 바텀 네비 64px 차감 누락 — `h-screen`은 100dvh 미고려 | MAJOR | iOS Safari 주소창 점프 |
| ChatInterface `h-[52px] w-[52px]` 전송 버튼 | OK | 52pt 양호 |

---

## 부록: 검색 통계

| 패턴 | 매칭 | 비고 |
|----|----|----|
| `w-[Npx]` / `min-w-[Npx]` / `max-w-[Npx]` | 32건 | 대부분 `max-w-[120~260px] truncate` 패턴 |
| `text-[10px]` / `text-[11px]` | 110+건 | 클릭 가능 요소 다수 |
| `ResponsiveContainer` | 11개 파일 | 양호 |
| `overflow-x-auto` | 25개 파일 | 테이블 가로 스크롤 표준 |
| `sm:` / `md:` / `lg:` / `xl:` | 174건 / 64개 파일 | 적용 분포 고르나 일부 컴포넌트 누락 |
| `react-window` / `react-virtual` / `virtuoso` | 0건 | virtualization 미사용 |
| `md:hidden` / `hidden md:` | 30건 | Header & 일부 컴포넌트 분기 처리 |

---

## 감사 종료

본 보고서는 정적 코드 분석에 기반하며, 실제 디바이스 측정·캡처는 포함하지 않습니다. 시각적 검증은 별도 디바이스/에뮬레이터 테스트가 필요합니다.
