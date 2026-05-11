# 모바일 UX 감사 보고서

> **감사 대상**: `frontend/app/**`, `frontend/components/**` (총 236 컴포넌트 + 24 page.tsx)
> **감사 일자**: 2026-05-11
> **기준**: iPhone SE 375px 폭 / Apple HIG 44×44pt 터치 타겟 / WCAG 2.5.5
> **모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 정의 |
|--------|------|------|
| **BLOCKER** | 4 | 모바일에서 라우트/기능 자체가 작동 불능 |
| **MAJOR** | 13 | 사용은 가능하나 핵심 기능에서 터치/판독 실패 빈발 |
| **MINOR** | 9 | 스타일·가독성 저하 (사용은 가능) |
| **합계** | **26** | |

### 한눈에 보는 결론
- 모바일 메인 동선의 단일 진입점은 **MobileNav.tsx** (Bottom Tab Bar) **5 항목**뿐 — 데스크톱 헤더 8개 라우트 중 **Chain Sight / Thesis / Market Pulse / Screener 4개가 모바일 네비에서 누락**.
- MobileNav의 `종목` 탭은 **존재하지 않는 `/stocks` 라우트**를 가리킴 → 404.
- Portfolio 페이지는 12-column 테이블 단일 뷰 + 16×16px 액션 아이콘으로 **모바일 실사용 불가**.
- Thesis 관제실 IndicatorRow, Validation 프리셋 탭, ChainSight 노드 등 핵심 클릭 요소가 `text-[10px]`/`text-[11px]`로 도배 — 정보 표시는 풍부하나 **터치 신뢰도 낮음**.
- 26개 컴포넌트가 `text-[10-11px]`를 클릭 가능 요소(button/Link/포함 셀)에 사용.
- 차트는 대체로 `ResponsiveContainer` 사용 양호. 단 일부 컨테이너 height는 px 고정.

---

## 반응형 누락

### BLOCKER

#### 1. `/stocks` 라우트 자체가 없음 → 모바일 홈 → 종목 탭 클릭 시 404
- `frontend/components/layout/MobileNav.tsx:13` 에서 `{ name: '종목', href: '/stocks', icon: TrendingUp }`로 링크
- 실제 파일: `frontend/app/stocks/[symbol]/page.tsx`만 존재. `frontend/app/stocks/page.tsx` **없음** (Glob 확인)
- **영향**: 모바일에서 Bottom Nav 5개 중 1개가 즉시 404 — 첫인상 치명적

#### 2. Header 햄버거 비활성화 + MobileNav 불충분 → 4개 라우트 접근 불가
- `frontend/components/layout/Header.tsx:160` 의 햄버거 버튼은 `className="hidden ..."` 으로 **항상 숨김** (주석: "audit P0 #12: MobileNav 단일 소스")
- MobileNav가 노출하는 라우트: `/`, `/stocks`, `/news`, `/portfolio`, `/mypage` (5개)
- **모바일에서 접근 불가한 라우트**: `/chainsight`, `/thesis`, `/market-pulse`, `/screener` (URL 직타이핑 외에는 진입 경로 없음)
- 의도가 "단일 소스"라면 MobileNav를 누락 라우트만큼 확장하거나, 데스크톱 라우트 중 일부를 의도적 제외해야 함

### MAJOR

#### 3. Portfolio 페이지 — 12-column 테이블, 모바일 카드 없음
- `frontend/components/portfolio/PortfolioTable.tsx:258-494`
- 컬럼: 종목 / 보유수량 / 평균매수가 / 현재가 / 전일대비 / 평가금액 / 손익 / 수익률 / 목표가 / 손절가 / 비중 / 관리
- 각 셀이 `px-6 py-4` → 1열 평균 ~120px → 전체 폭 ≥ 1400px. 375px에서는 한 화면에 **2열도 안 보임**.
- `overflow-x-auto`만 적용. 모바일 카드 대안 컴포넌트(`MobileStockCard` 같은 것) **없음**.
- **권장 영향도**: 포트폴리오 사용자가 모바일에서 사실상 보유 종목 한 줄 보려면 좌우 다섯 번 스크롤.

#### 4. ScreenerTable에 sm:hidden 가드가 페이지 단에만 있음
- `frontend/app/screener/page.tsx:845-875` 는 `viewMode==='table'` + `hidden sm:block` 으로 데스크톱 전용 표시 + 모바일은 `MobileStockCard` grid로 폴백 ✓ 잘 됨.
- 그러나 `frontend/components/strategy/ScreenerTable.tsx` 자체가 다른 곳(예: future 기능)에서 단독 사용될 경우 동일 보호망이 없음. 컴포넌트 자체가 `overflow-x-auto`만으로는 모바일 대응 미흡 (max-w-[180px]/[120px]/[200px] 셀이 다수).

#### 5. Stock Detail 페이지 L1/L2 탭 가로 스크롤 미적용
- `frontend/app/stocks/[symbol]/page.tsx:381-419`
- L1 nav: `nav className="flex space-x-2"` — `overflow-x-auto` 없음. 탭 수가 늘면 모바일에서 짤림
- L2 nav: `nav className="flex space-x-6"` — 위와 동일. `px-6` padding까지 더해져 375px에서 4개 이상 탭이면 horizontal overflow → body 스크롤 유발

#### 6. ChainSight MarketGraphCanvas 컨테이너 `h-[560px]` 고정
- `frontend/components/chainsight/MarketGraphCanvas.tsx:760`
- 모바일 세로 위주 화면(예: 375×667)에서 헤더+탭+카드 후 차트에 560px 할당하면 viewport 초과
- `min-h-screen` + flex layout 이 아니라 컨테이너 자체가 `h-[560px]` 고정 → 모바일 ChainSight 진입 시 그래프가 화면을 거의 채움
- 다행히 `frontend/app/chainsight/[symbol]/page.tsx:152-170` 에서 isMobile일 때 `MobileCardList`로 분기 — **개선 사례**. 그래프 모드 진입 시에만 풀스크린 overlay(`fixed inset-0`).
- 그러나 `frontend/app/chainsight/page.tsx` 진입(섹터 그래프)에서 동일한 분기 처리가 확인되지 않음 — 위 컴포넌트가 그대로 노출되면 모바일에서 답답

### MINOR

#### 7. InvestingHeader `max-w-[1400px]` (3곳)
- `frontend/components/layout/InvestingHeader.tsx:32,55,99` — 데스크톱 최대 폭 제약. 모바일 overflow 유발은 아님. 정보 제공용.

#### 8. AINewsBriefingCard 진행바 `max-w-[200px]`
- `frontend/components/news/AINewsBriefingCard.tsx:70` — 정보 표시용이므로 잘림 위험 낮음.

#### 9. RAG ChatInterface 전송 버튼 `h-[52px] w-[52px]`
- `frontend/components/rag/ChatInterface.tsx:198` — 44pt 이상 ✓ 양호 사례.

---

## 터치 타겟

### Apple HIG 44×44pt 기준. text-[10px]/[11px] 클릭 요소는 폰트 자체로는 미달은 아니나 hit area가 좁아지는 주범.

### MAJOR

#### 10. Validation PeerContextBar 프리셋 탭 (`px-3 py-1 text-xs`)
- `frontend/components/validation/PeerContextBar.tsx:36-62`
- 계산: `py-1` = 4+4 = 8px, `text-xs`(12px line-height tight) ≈ **24~28px 높이** → **44pt 미달**
- "직접 설정" 토글 버튼, 프리셋 탭, custom 적용 버튼 모두 동일
- 사용자가 자주 전환하는 핵심 컨트롤 (CLAUDE.md common-bugs #26에 명시된 영역)

#### 11. AdminTabNav 6개 탭 (`px-4 py-2.5`)
- `frontend/components/admin/AdminTabNav.tsx:37` — `py-2.5` = 10+10 = 20px + text-sm(14px) ≈ **38px 높이** → 44pt 미달
- `overflow-x-auto` 적용은 양호 ✓

#### 12. Stock Detail L1 탭 (`px-5 py-2 text-sm`)
- `frontend/app/stocks/[symbol]/page.tsx:388` — py-2 = 8+8 = 16 + 14 ≈ **32-36px** → 미달

#### 13. PortfolioTable 편집 아이콘 Save/Cancel/Edit (`h-4 w-4`)
- `frontend/components/portfolio/PortfolioTable.tsx:470, 477, 486`
- Lucide 아이콘 16×16, 부모 button에 padding 없음 → 실질 hit area 16×16
- 목표가/손절가 수정이라는 중요 액션이 거의 누를 수 없음

#### 14. SignalSummaryCard 신호등 (`w-10 h-10` + onMouseEnter only)
- `frontend/components/validation/SignalSummaryCard.tsx:40-58`
- 40×40 → 44pt 미달, 게다가 **gray 신호의 사유 툴팁이 `onMouseEnter`만 처리** → 터치 환경에서 영구히 접근 불가

#### 15. QuarterlySparkline 분기 막대 (`text-[8px]` + hover-only tooltip)
- `frontend/components/thesis/dashboard/QuarterlySparkline.tsx:54, 58-62`
- 분기 라벨 `text-[8px]` (8px) — Apple 권장 최소 11pt 미달
- 호버 툴팁이 `setHoveredIdx`로만 표시 — onTouchStart 등 모바일 보조 핸들러 **없음** → 터치 무용

#### 16. MobileCardList CTA 3버튼 (`py-1.5 text-xs`)
- `frontend/components/chainsight/MobileCardList.tsx:169, 175, 181` (가설 생성 / 탐색 / 검증)
- py-1.5 + text-xs ≈ **28-32px** → 44pt 미달. 모바일 전용 컴포넌트인데 모바일 기준 미달
- `flex-1`로 가로는 충분하나 세로 부족

#### 17. ScreenerTable 액션 버튼 (`px-2 py-1 text-xs`)
- `frontend/components/strategy/ScreenerTable.tsx:321-328` — 바구니 추가 버튼, 28px 미만

#### 18. RelationLegend 카테고리 토글 (`text-[10px] font-semibold`)
- `frontend/components/chainsight/RelationLegend.tsx:59, 94` — 칩 토글 UX에서 작은 폰트가 hit miss 유발

### MINOR

#### 19. EOD SignalFilterTabs (`px-3 py-1.5 text-sm` + 카운트 배지 18px)
- `frontend/components/eod/SignalFilterTabs.tsx:48, 68` — 약 36px, 거의 도달
- 카운트 배지 `min-w-[18px] h-[18px]`는 비클릭 요소이므로 OK

#### 20. EOD ConfidenceBadge, NewsContextBadge — 표시용, 클릭 아님

#### 21. SuggestionChips `max-w-[150px] text-xs`
- `frontend/components/rag/SuggestionChips.tsx:40` — RAG 채팅 제안 칩, truncate 적용 → 누락 정보 의심

#### 22. PresetGallery 보조 칩 `text-[10px]`
- `frontend/components/screener/PresetGallery.tsx:184, 218, 230, 241` — 색상/순서 배지. 일부는 absolute로 별도 카드 위에 떠 있음 → 시각적 정보 전달만 담당

#### 23. Pagination 페이지 번호 (`min-w-[32px] px-2 py-1.5`)
- `frontend/components/screener/Pagination.tsx:127` — 32×30 정도 → 44pt 미달, 그러나 충분히 누를 수 있는 크기

---

## 네비게이션

### BLOCKER

#### 24. MobileNav 라우트 누락 (Item #2 와 중복 — 분류 차원에서 재기재)
| 라우트 | 데스크톱 Header | MobileNav | 비고 |
|--------|----------------|-----------|------|
| `/` | ✓ | ✓ | |
| `/portfolio` | ✓ | ✓ | |
| `/chainsight` | ✓ | **✗** | 모바일 접근 불가 |
| `/thesis` | ✓ | **✗** | Thesis Control — 핵심 기능 누락 |
| `/market-pulse` | ✓ | **✗** | |
| `/news` | ✓ | ✓ | |
| `/screener` | ✓ | **✗** | |
| `/mypage` | ✓ (user) | ✓ | `내정보` |
| `/stocks` | (Link 없음) | **✗ (라우트 부재)** | 4xx |

### MAJOR

#### 25. 검색 기능 모바일 부재
- `frontend/components/layout/Header.tsx:111` 검색바 — `hidden md:block` 으로 데스크톱 전용
- 모바일에서는 햄버거를 통해서만 접근 가능했으나 햄버거가 `hidden` 처리됨 → **모바일 사용자는 종목 검색 자체가 불가능**
- 데스크톱의 검색조차 `console.log` 호출만 — 미구현 (별개 이슈)

#### 26. 긴 목록 가상화(virtualization) 0건
- `grep`: `react-window` / `react-virtual` / `virtuoso` / `FixedSizeList` 모두 검색 결과 없음
- Portfolio 보유 종목, ScreenerTable 종목 리스트, Thesis IndicatorRow 다수, ChainSight MobileCardList 등 잠재적 100+ 행 목록이 모두 일반 `.map()` 렌더링
- 모바일 저성능 기기에서 200개 이상 행 표시 시 스크롤 jank 발생 가능

### MINOR

#### 27. ChainSight 모바일 분기 처리 양호 사례 ✓
- `frontend/app/chainsight/[symbol]/page.tsx:152-170` 에서 `useIsMobile` hook으로 `MobileCardList` ↔ 그래프 overlay 분기 — **모범 사례**

#### 28. Screener 페이지 viewMode 토글 양호 사례 ✓
- `hidden sm:block` / `sm:hidden` 으로 테이블/카드 자동 전환 — **모범 사례**

---

## 차트/그래프

### MAJOR

#### 29. StockPriceChart 컨테이너 height 고정 (`height={400}` default)
- `frontend/components/charts/StockPriceChart.tsx:272` — `ResponsiveContainer width="100%" height={height}` 사용 ✓
- 단 `height` prop default 400px. 호출처에서 모바일 대응 height 분기 없으면 작은 화면에서 차트가 viewport의 절반 이상 차지
- 차트 타입 버튼 `px-3 py-1 text-sm` (라인/영역/캔들) — 28px 높이, 44pt 미달

#### 30. SentimentChart `<div className="w-full h-80">` (320px 고정)
- `frontend/components/news/SentimentChart.tsx:79` — ResponsiveContainer 내부 컨테이너가 px 고정
- left/right 듀얼 Y축으로 모바일 가로 폭 압박 심함. label "감성 점수"/"뉴스 수" 세로 라벨이 차트 본체 잠식

#### 31. YieldCurveChart 모바일 대응 미흡 추정
- `frontend/components/macro/YieldCurveChart.tsx` ResponsiveContainer 사용 ✓ — 본문 미확인이나 X축 만기 표시(3M/2Y/5Y/10Y/30Y) 5+ 포인트 → 모바일에서 X 라벨 겹침 우려

#### 32. QuarterlySparkline 모바일 가독성 결손
- `frontend/components/thesis/dashboard/QuarterlySparkline.tsx`
- div 막대로 직접 구현 (Recharts 미사용) — flex-1 균등 분할로 가로 반응 ✓
- 그러나 `text-[8px]` 분기 라벨 → 가독성 임계 이하
- 호버 툴팁만 제공 → 모바일 터치로는 분기별 정확 값 확인 불가

#### 33. IndicatorRow 확장 차트 `height={160}` / `height={140}` 고정
- `frontend/components/thesis/dashboard/IndicatorRow.tsx:197, 235` — ResponsiveContainer width="100%" height={px} 패턴
- 모바일에서는 16:9 같은 비율 기반 height 필요. 현재 160px 고정이라 좁은 폭에서는 차트가 납작해지고 X축 라벨 회전/생략 처리 미흡

### MINOR

#### 34. MarketGraphCanvas ForceGraph2D
- `frontend/components/chainsight/MarketGraphCanvas.tsx:761-822`
- `width={containerWidth}` 동적 측정 ✓, height=560 고정 — 모바일에서 그래프 노드 28-20px 반지름 / 1차 이웃 20-14px → 노드 자체는 클릭 가능하나 밀집 시 정확도 저하
- 모바일 더블탭 지원 명시 ✓ (`handleNodeClickMobile`, line 481-517) — **모범 사례**

#### 35. SectorHeatmap 작은 타일 텍스트 생략
- `frontend/components/screener/SectorHeatmap.tsx:31-46` — `width < 60 || height < 40` 시 텍스트 미표시 ✓
- 모바일에서는 거의 모든 타일이 그 임계에 걸릴 가능성 → 정보 빈 사각형만 보임. fallback 표시 부재

---

## 페이지별 상세

### `/` (메인 / EOD Dashboard) — page.tsx
| 이슈 | 심각도 |
|------|--------|
| StockRow `text-[11px]` 시그널 라벨 + 거래량 (line 89, 92) | MINOR |
| MarketSummaryBar `text-[10px]` 부가 정보 (line 48) | MINOR |
| SignalFilterTabs 36px 높이 칩 | MINOR |
| SignalDetailSheet `w-full md:w-[420px]` 사이드시트 ✓ | OK |

### `/portfolio`
| 이슈 | 심각도 |
|------|--------|
| **12-column 테이블 + 모바일 카드 없음** (#3) | **BLOCKER** |
| 16×16 Save/Cancel/Edit 아이콘 (#13) | MAJOR |
| 입력 `<input className="w-24 ... py-1 text-sm">` (line 379, 417) — 96px 폭 + 24px 높이 | MAJOR |
| 헤더 그리드 `grid-cols-2 md:grid-cols-3 lg:grid-cols-6` 양호 ✓ | OK |

### `/chainsight` (섹터 뷰)
| 이슈 | 심각도 |
|------|--------|
| `h-[560px]` 고정 컨테이너 (#6) | MAJOR |
| 인기 섹터 버튼 `w-[110px] min-h-[68px]` ✓ (line 676) | OK |
| RelationLegend 칩 `text-[10px]` (#18) | MAJOR |
| **모바일 라우트 자체 진입 불가** (#2 누락 라우트) | BLOCKER |

### `/chainsight/[symbol]` (종목 뷰)
| 이슈 | 심각도 |
|------|--------|
| 모바일 카드 리스트 분기 처리 ✓ (line 152-170) | **모범 사례** |
| MobileCardList CTA `py-1.5 text-xs` (#16) | MAJOR |
| `w-10 h-10 ... text-xs` 종목 이니셜 원 — 클릭 아님 OK | OK |

### `/thesis`, `/thesis/[id]`, `/thesis/new`
| 이슈 | 심각도 |
|------|--------|
| **모바일 라우트 진입 불가** (#2) | BLOCKER |
| IndicatorRow `text-[11px]` 본문 + 다수 `min-w-[60-120px]` (#33) | MAJOR |
| QuarterlySparkline `text-[8px]` + hover-only (#15, #32) | MAJOR |
| `thesis/new/page.tsx:672,715` `grid-cols-1 ... sm:grid-cols-2` ✓ | OK |
| OptionButton `text-[10px] sm:hidden` 힌트 (line 66) | MINOR |
| BottomSheet 패턴 사용 (다수) | OK |

### `/screener`
| 이슈 | 심각도 |
|------|--------|
| **모바일 라우트 진입 불가** (#2) | BLOCKER |
| 테이블/카드 자동 전환 분기 ✓ (page.tsx:845-875) | **모범 사례** |
| PresetGallery `grid-cols-2 md:grid-cols-3 ...` ✓ | OK |
| AdvancedFilterPanel `text-[10px]` 설명 (line 142) | MINOR |
| ScreenerTable 자체 단독 사용 시 모바일 대응 미흡 (#4) | MAJOR |

### `/market-pulse`, `/market-pulse-v2`
| 이슈 | 심각도 |
|------|--------|
| **모바일 라우트 진입 불가** (#2) | BLOCKER |
| BriefCardSummary/BriefDetail `text-[10px]` 모델 버전 | MINOR |
| v2 details 4개 (Sector/Regime/Flow/Breadth) 모두 ResponsiveContainer ✓ | OK |
| `text-[10px]` footer (page.tsx:77) | MINOR |

### `/news`
| 이슈 | 심각도 |
|------|--------|
| RecommendationCard `truncate max-w-[150px]` (line 85) | MINOR |
| AINewsBriefingCard `text-[10px]` LLM 모델 라벨 | MINOR |
| MLModelStatusCard `text-[10px] w-20 truncate` | MINOR |
| `grid-cols-1 lg:grid-cols-2` ✓ | OK |
| SentimentChart 듀얼 Y축 `h-80` 고정 (#30) | MAJOR |

### `/stocks/[symbol]`
| 이슈 | 심각도 |
|------|--------|
| L1/L2 탭 가로 스크롤 미적용 (#5) | MAJOR |
| L1 탭 `px-5 py-2 text-sm` 36px (#12) | MAJOR |
| StockPriceChart 차트 타입 버튼 28px (#29) | MAJOR |
| `grid-cols-1 lg:grid-cols-2` 헤더 + `grid-cols-2 md:grid-cols-3 lg:grid-cols-4` ✓ | OK |
| `useIsMobile` 사용 흔적 있음 — 부분 대응 | OK |

### `/admin`
| 이슈 | 심각도 |
|------|--------|
| AdminTabNav 6개 탭 38px (#11) | MAJOR |
| `overflow-x-auto` 적용 ✓ | OK |
| SystemTab/TaskLogViewer `max-w-[260px] truncate` 결과 셀 | MINOR |

### `/mypage`, `/watchlist`, `/dashboard`, `/login`, `/signup`, `/ai-analysis`
| 이슈 | 심각도 |
|------|--------|
| watchlist/page.tsx `overflow-x-auto` 있음 — 양호 | OK |
| dashboard/page.tsx `sm:grid-cols-3` 적용 ✓ | OK |
| login/signup — 표준 form 컴포넌트, 모바일 무관 | OK |

---

## 부록 A — 검출 통계

### `w-[NNpx]` / `min-w-[NNpx]` 사용 파일 (23개)
대부분 `max-w-[NNNpx] truncate` 형태로 텍스트 컷오프 용도. 모바일 overflow 직접 유발 사례:
- `MarketGraphCanvas.tsx:676` `w-[110px]` — 인기 섹터 버튼 (3개 fixed grid)
- `SignalDetailSheet.tsx:97` `md:w-[420px]` — md 이상에서만 적용 ✓
- `ChatInterface.tsx:198` `h-[52px] w-[52px]` — ✓

### `text-[10px]` / `text-[11px]` 사용 파일 (52개)
이 중 button/Link/clickable 부모 내부 사용 (터치 hit area 위협):
- Thesis (12): IndicatorRow, IndicatorCard, AlertCard, RecommendCard, IndicatorSetupCard, SuggestionCard, PremiseCard, OptionButton, NewsSelector, AISummarySection, AddIndicatorSheet, NotableChangesSection
- ChainSight (8): RelationLegend, FullPathView, ExplorationTrail, ChainStoryFeed, RelationCardPanel, MobileCardList, MarketGraphCanvas, TracePathView
- EOD (7): StockRow, SignalCard, NewsContextBadge, ConfidenceBadge, MarketSummaryBar, SignalDetailSheet, SignalFilterTabs
- Screener (5): PresetGallery, MobileStockCard, AdvancedFilterPanel, PresetDetailPopover, Pagination
- 기타 (다수)

### `ResponsiveContainer` 사용 (14개)
모두 적용 ✓: StockPriceChart, SentimentChart, YieldCurveChart, PortfolioChart, IndicatorRow, IndividualMiniCharts, MetricBarChart, MLTrendChart, SectorHeatmap, StockChart, market-pulse-v2/details/*

### `overflow-x-auto` 사용 (28개)
주요: PortfolioTable, ScreenerTable, AdminTabNav, SignalFilterTabs, MobileCardList 탭 바, AdvancedFilterPanel, RelationFilterChips. 패턴은 정착되어 있음. 단 Stock Detail L1/L2 탭에는 미적용 (#5).

---

## 부록 B — 권장 우선순위 (참고용 / 본 보고서는 수정 불가)

| 순위 | 항목 | 근거 |
|------|------|------|
| P0-1 | MobileNav `/stocks` 라우트 수정 또는 `/stocks/page.tsx` 생성 | BLOCKER #1 |
| P0-2 | MobileNav에 thesis/chainsight/market-pulse/screener 추가 또는 햄버거 복원 | BLOCKER #2 |
| P0-3 | PortfolioTable 모바일 카드 뷰 추가 (ScreenerTable 패턴 답습) | BLOCKER #3 |
| P0-4 | PortfolioTable Save/Cancel/Edit 버튼에 `p-2 min-w-[44px] min-h-[44px]` 적용 | MAJOR #13 |
| P1-1 | Validation PeerContextBar 프리셋 탭 `py-2` 이상으로 확장 | MAJOR #10 |
| P1-2 | QuarterlySparkline 분기 막대에 `onTouchStart` 추가, 라벨 `text-[10px]`로 확대 | MAJOR #15 |
| P1-3 | SignalSummaryCard gray 신호등 클릭 시 모달/하단시트 — 호버 의존 제거 | MAJOR #14 |
| P1-4 | Stock Detail L1/L2 nav `overflow-x-auto` 적용 | MAJOR #5 |
| P1-5 | Stock Detail/Screener/Thesis 차트 컨테이너 height를 `aspect-video` 등 비율로 | MAJOR #29-#33 |
| P2 | 검색바 모바일 노출 (햄버거 복원 시 함께) | MAJOR #25 |
| P2 | 100+ 행 리스트(특히 Portfolio, Thesis 가설 목록)에 react-window 도입 검토 | MAJOR #26 |

---

## 부록 C — 모범 사례 (확산 권장)

1. `frontend/app/chainsight/[symbol]/page.tsx:152-170` — `useIsMobile` 분기로 카드 리스트 ↔ 그래프 오버레이 전환
2. `frontend/app/screener/page.tsx:845-875` — `hidden sm:block` / `sm:hidden` 으로 같은 데이터의 테이블/카드 자동 전환
3. `frontend/components/chainsight/MarketGraphCanvas.tsx:481-517` — 모바일 더블탭 패턴 (`handleNodeClickMobile`)
4. `frontend/components/layout/MobileNav.tsx:34` — 각 Tab에 `min-h-[44px]` 보장 + `aria-label`
5. `frontend/components/eod/SignalDetailSheet.tsx:97` — `w-full md:w-[420px] md:h-full` 모바일 풀스크린/데스크톱 사이드시트
6. `frontend/components/rag/ChatInterface.tsx:198` — `h-[52px] w-[52px]` 전송 버튼 (44pt 초과)

---

**감사 종료**
