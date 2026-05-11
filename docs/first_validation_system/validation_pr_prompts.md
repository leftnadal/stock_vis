# 1차 검증 기능 — Claude Code PR 프롬프트

> 설계서: `validation_design_v1.4.md` 참조
> 모든 PR은 기존 코드 컨벤션/디렉토리 구조를 따를 것

---

## BE-PR-1: validation 앱 생성 + DB 모델 + 마이그레이션

```
validation Django 앱을 생성하고 1차 검증에 필요한 DB 모델을 구현해줘.

설계서 섹션 7 참조. 생성/수정할 모델:

1. MetricDefinition — 34개 지표 메타 (metric_code, display_name, display_name_en, category, unit, higher_is_better, sort_order, not_applicable_reason)
2. CompanyMetricSnapshot — 종목별 연도별 지표값 (symbol, fiscal_year, metric_code, value, value_status, exclusion_reason)
3. CompanyMetricLatest — 최신 연도 지표 (snapshot의 latest view)
4. PeerMetricBenchmark — peer 그룹 benchmark (symbol, fiscal_year, metric_code, median, p25, p75, peer_count)
5. IndustryMetricBenchmark — industry 전체 benchmark
6. CompanyBenchmarkDelta — 기업 vs benchmark 차이 (percentile_rank, rank, total, benchmark_basis, benchmark_confidence)
7. PeerListCache — peer 목록 캐시 (symbol, peers JSON, benchmark_basis, size_bucket, peer_tier nullable, confidence)
8. CategorySignal — 카테고리별 신호 (symbol, category, fiscal_year, signal green/yellow/red/gray, score nullable, signal_reason, metric_count, valid_metric_count)
9. BatchJobRun — 배치 실행 로그

기존 IndustryClassification 모델에 handling_mode (standard/special) CharField 추가.

unique_together, indexes, db_table명은 설계서 따를 것.
makemigrations + migrate 실행.
```

---

## BE-PR-2: 지표 시드 데이터 + handling_mode 시딩

```
validation 앱의 초기 시드 데이터를 Django management command로 구현해줘.

1. MetricDefinition 34개 지표 시딩:
   설계서 섹션 4 참조. 7개 카테고리 × 지표:
   - profitability (5): gross_margin, operating_margin, net_margin, roe, roic
   - growth (4): revenue_growth_yoy, operating_income_growth, fcf_growth_yoy, rev_growth_vs_industry
   - financial_structure (6): debt_to_equity, current_ratio, interest_coverage, net_debt_to_ebitda, cash_runway_years, short_term_debt_pct
   - cash_flow (6): fcf_margin, ocf_to_net_income, capex_to_ocf, accruals_ratio, fcf_conversion, ocf_trend_3y
   - operational_efficiency (6): dso, ar_to_revenue, inventory_turnover_days, inventory_vs_sales_growth, sga_to_revenue, asset_turnover
   - dilution_shareholder (4): dilution_3y_cum, sbc_to_revenue, buyback_yield, shareholder_yield
   - valuation (3): pe_ratio, ev_to_ebitda, fcf_yield

   각 지표에 unit(ratio/multiple/days/years/percent_point), higher_is_better, sort_order, category, 한글/영어 display_name 설정.
   not_applicable_reason: cash_runway_years="흑자 기업", inventory_turnover_days="서비스 기업 (재고 없음)", inventory_vs_sales_growth="서비스 기업 (재고 없음)", interest_coverage="무차입 기업"

2. IndustryClassification handling_mode 시딩:
   Banks, Insurance, REIT(Real Estate), Utilities 관련 industry를 handling_mode='special'로 업데이트.
   나머지는 'standard'.

management command: python manage.py seed_validation_data
idempotent하게 (update_or_create 사용).
```

---

## BE-PR-3: Celery Task 1-2 (FMP 수집 + 지표 계산 + value_status)

```
validation 배치 파이프라인의 Task 1, 2를 구현해줘.

설계서 섹션 6 참조.

Task 1: fetch_annual_financials(symbols)
- FMP API에서 종목별 income-statement, balance-sheet-statement, cash-flow-statement, key-metrics 수집 (annual, limit=5)
- company_metric_snapshot에 원값 저장
- 종목별 독립 실행 (한 종목 실패해도 나머지 계속, try-except per symbol)
- rate limit 대응: 요청 간 sleep, 429 시 exponential backoff 3회

Task 2: calculate_derived_metrics()
- snapshot 원값으로 33개 지표 계산 (rev_growth_vs_industry 제외 — Task 3.5에서)
- company_metric_latest 갱신
- value_status 판정 로직 (설계서 섹션 7.2):
  - cash_runway_years: 흑자 기업 → not_applicable
  - interest_coverage: total_debt==0 → not_applicable, interestExpense==0 → not_applicable, interestExpense is None → missing
  - inventory 관련: inventory==0 → not_applicable
  - 값 None → missing
  - interest_coverage 극단적 변동(부호 반전 + 10배) → unstable
  - 그 외 → normal

지표 계산 공식은 표준 재무 공식. 예:
- gross_margin = grossProfit / revenue
- roe = netIncome / totalStockholdersEquity
- fcf_margin = freeCashFlow / revenue
- debt_to_equity = totalDebt / totalStockholdersEquity
- dso = (netReceivables / revenue) * 365
분모 0인 경우 value=None, value_status='missing' 처리.
```

---

## BE-PR-4: Celery Task 3-3.5 (Peer 선정 + Benchmark 계산)

```
validation 배치 파이프라인의 Task 3, 3.5를 구현해줘.

설계서 섹션 3.2 (peer 선정) + 섹션 6 참조.

Task 3: calculate_benchmarks(symbols)

Step 1 — Peer 선정 (select_peers 함수):
- 같은 industry + 같은/인접 size bucket (±1) → benchmark_basis='industry_size'
- peer < 8이면 size 완화 → benchmark_basis='industry'
- peer < 5이면 sector fallback → benchmark_basis='sector'

Size bucket 분류:
- mega: market_cap >= $200B
- large: >= $10B
- mid: >= $2B
- small: < $2B

Step 2 — Benchmark 계산:
- peer_metric_benchmark: 각 metric_code별 median, p25, p75 계산 (연도별)
- industry_metric_benchmark: industry 전체 기준 동일 계산
- company_benchmark_delta: percentile_rank, rank, total 계산
  - benchmark_basis, benchmark_confidence 함께 저장
  - confidence: peer≥15 + industry_size → high, 8~14 → medium, <8 → low, <4 → limited

Step 3 — peer_list_cache 갱신:
- peers JSON, benchmark_basis, size_bucket, confidence 저장
- peer_tier는 null (Phase 2)

Task 3.5: calculate_relative_metrics()
- rev_growth_vs_industry = 자사 revenue_growth_yoy - industry_metric_benchmark의 revenue_growth_yoy median
- company_metric_snapshot + benchmark_delta 업데이트
- Task 3에서 해당 종목 실패했으면 gracefully 스킵
```

---

## BE-PR-5: Celery Task 4-6 (Category Signal + 오케스트레이터)

```
validation 배치 파이프라인의 Task 4, 5, 6과 오케스트레이터를 구현해줘.

설계서 섹션 3.1 (category_signal 계산) + 섹션 6 참조.

Task 4: calculate_category_signals()
- 카테고리별 소속 지표의 percentile_rank 균등 평균 계산
- value_status='normal'인 지표만 포함 (not_applicable, missing 등 제외)
- valid_metric_count == 0이면 signal='gray', reason='데이터 부족'
- handling_mode='special' 산업: 해당 카테고리 signal='gray', reason='금융업 특성상 일반 해석과 다를 수 있습니다' (재무구조 카테고리 등)
- 신호등: score>=65 → green, >=35 → yellow, <35 → red
- score는 내부 계산용으로 저장 (UI 미노출)
- signal_reason: rule-based (e.g. "5개 지표 중 4개 업종 상위 35%")
- CategorySignal 테이블에 upsert

Task 5: update_peer_list_caches() — Task 3에서 이미 peer_list_cache 갱신했으므로 여기서는 confidence 재검증 + 최종 저장만

Task 6: log_batch_run() — BatchJobRun에 실행 결과 기록 (universe, 처리 종목 수, 실패 종목 수, 소요 시간)

오케스트레이터: run_weekly_validation_batch(universe='sp500')
- Celery chain: Task1 → Task2 → Task3 → Task3.5 → Task4 → Task5 → Task6
- Celery Beat 등록: 일요일 새벽 2시

종목별 에러 tolerance: 각 Task 내에서 종목별 try-except, 실패 종목은 로그하고 나머지 계속 진행.
```

---

## BE-PR-6: API Views + Serializers

```
validation 앱의 REST API를 구현해줘.

설계서 섹션 5 참조. 3개 엔드포인트:

1. GET /api/v1/validation/{symbol}/summary/
응답: symbol, company_name, data_fiscal_year, data_freshness, category_signals[], summary_text(rule-based), summary_source='rule', peer_info{industry, peer_count, confidence, benchmark_basis, size_bucket, basis_description, top_peers[], industry_leader{}}, industry_position{ranks[]}
설계서 5.2 JSON 구조 참조.

2. GET /api/v1/validation/{symbol}/metrics/?category=profitability|growth|...|all
응답: categories[]{category, display_name, signal, description, metrics[]{metric_code, display_name, unit, higher_is_better, current{value, fiscal_year, value_status}, benchmark{basis, confidence, median, p25, p75, percentile_rank, rank, total}, history[]{fiscal_year, company_value, peer_median, peer_p25, peer_p75}, trend, interpretation(rule-based), interpretation_source='rule'}}
category=all이면 7개 전체, 개별이면 해당 카테고리만.

3. GET /api/v1/validation/{symbol}/leader-comparison/
응답: leader{symbol, name}, comparisons[]{metric_code, display_name, company_value, leader_value, gap, is_advantage}, summary(rule-based), growth_trend_comparison{}

rule-based 해석 함수 구현 (설계서 섹션 3.3의 generate_metric_interpretation, 3.1의 generate_summary_text, 3.5의 generate_leader_summary).

URL 설정: validation/api/urls.py + config/urls.py include.
```

---

## FE-PR-1: 네비게이션 재설계 (L1/L2 탭)

```
종목 상세 페이지의 네비게이션을 2-depth 구조로 재설계해줘.

설계서 섹션 1 참조.

L1 (Primary Tab): 기본정보 | 뉴스 | 분석 및 검증
- Pill 스타일, 선택 시 배경색 변경

L2 (Secondary Tab): L1 선택에 따라 다른 하위 탭
- 기본정보: Overview, Balance Sheet, Income Statement, Cash Flow, 기타 펀더멘탈
- 뉴스: 하위 탭 없음
- 분석 및 검증: 1차 검증 (재무 체질), Chain Sight (관계 탐색)
- Underline 스타일

라우팅: query param 방식 (?tab=validation, ?tab=chainsight 등)
기존 탭 내용은 그대로 유지, 위치만 이동.

컴포넌트:
- StockDetailLayout.tsx (전체 레이아웃 + 탭 상태 관리)
- PrimaryTabNav.tsx (L1)
- SecondaryTabNav.tsx (L2)

기존 탭 컴포넌트(OverviewTab, BalanceSheetTab 등)는 fundamentals/ 디렉토리로 이동.
분석 및 검증 하위에 ValidationTab.tsx (빈 껍데기), ChainSightTab.tsx (기존 이동) 배치.
```

---

## FE-PR-2: TypeScript 타입 + hooks + API client

```
1차 검증 프론트엔드의 타입 정의와 데이터 fetching 레이어를 구현해줘.

설계서 섹션 5.2 (API 응답 구조) + 섹션 9.2 참조.

1. types/validation.ts:
- ValidationSummary: categorySignals[], summaryText, peerInfo{}, industryPosition{}
- CategorySignal: category, displayName, signal('green'|'yellow'|'red'|'gray'), signalReason, metricCount
- ValidationMetricsResponse: categories[]
- MetricData: metricCode, displayName, unit, higherIsBetter, current{value, fiscalYear, valueStatus}, benchmark{basis, confidence, median, p25, p75, percentileRank, rank, total}, history[], trend, interpretation
- ChartDataPoint: fiscalYear, companyValue, peerMedian, peerP25, peerP75
- LeaderComparison: leader{}, comparisons[], summary, growthTrend{}
- PeerInfo: industry, peerCount, confidence, benchmarkBasis, sizeBucket, topPeers[], industryLeader{}

2. API client 함수: fetchValidationSummary, fetchValidationMetrics, fetchLeaderComparison

3. hooks/useValidation.ts:
- useValidationSummary(symbol) — staleTime 1시간, gcTime 24시간
- useValidationMetrics(symbol, category?) — 동일
- useLeaderComparison(symbol) — 동일

TanStack Query 사용. 기존 프로젝트 패턴 따를 것.
```

---

## FE-PR-3: SignalSummaryCard + PeerContextBar

```
1차 검증 페이지의 상단 2개 섹션을 구현해줘.

설계서 섹션 3.1, 3.2 참조.

1. SignalSummaryCard.tsx:
- 7개 카테고리 신호등 가로 나열 (green=🟢, yellow=🟡, red=🔴, gray=⚪)
- 각 신호등 아래 카테고리명 (한글)
- 하단에 한줄 요약 텍스트 (summary_text)
- gray 신호등에는 툴팁: "금융업 특화 지표는 고도화 예정입니다" 등 signal_reason 표시
- 모바일: 7개 신호등 가로 스크롤

2. PeerContextBar.tsx:
- "비교 기준: {industry} 업종 내 유사 규모 {peer_count}개"
- 비교 신뢰도 badge (high=🟢높음, medium=🟡보통, low=🔴낮음)
- 규모 기준: "{size_bucket} Cap"
- 데이터 기준: "{fiscal_year} FY"
- "과거 연도 차트도 현재 peer 기준으로 계산됩니다" 안내문
- 접기/펼치기: peer 목록 (top_peers 표시)

useValidationSummary hook 사용.
```

---

## FE-PR-4: MetricCard + MetricBarChart

```
개별 지표 카드와 차트 컴포넌트를 구현해줘.

설계서 섹션 3.3 + 9.3 참조.

1. MetricCard.tsx:
- value_status 분기 렌더링:
  - normal: 전체 표시 (현재값, 순위, percentile, 차트, 해석)
  - not_applicable: "해당 없음" + exclusion_reason, 차트 없음
  - missing: "데이터 누락" 표시
  - unstable: 전체 표시 + ⚠️ "값 변동이 크므로 해석 주의"
  - low_confidence: 전체 표시 + ⚠️ "비교 표본 부족"
- 상단: 신호등 + 지표명(한글) + 영어 병기
- 중단: 현재값, 업종 중앙값, 순위, 백분위, 비교 기준(benchmark_basis)
- 하단: 차트 + 해석 텍스트 + "(높을수록/낮을수록 좋은 지표)"

2. MetricBarChart.tsx:
- Recharts ComposedChart 사용
- Bar: 이 기업 값 (Cell로 연도별 색상 — getSignalColor 함수)
- Scatter (shape=dash): peer 중앙값 가로선
- ErrorBar on Scatter: peer p25~p75 범위
- XAxis: fiscal_year, YAxis: formatMetricValue(value, unit)
- Tooltip: 이 기업 값, median, p25, p75 표시
- Legend: 이 기업 / peer 중앙값 / peer p25~p75
- 설계서 9.3의 getSignalColor 함수 구현 (higher_is_better 반전 로직)
- history 배열 길이에 맞게 동적 렌더링 (3~5년)

3. MetricTooltip.tsx: hover 시 상세 수치 표시
```

---

## FE-PR-5: CategorySection + Sidebar + 모바일 Accordion

```
카테고리 섹션과 네비게이션 사이드바, 모바일 Accordion을 구현해줘.

설계서 섹션 2.1, 2.2, 3.4 참조.

1. CategorySection.tsx:
- 카테고리 헤더: 신호등 + 카테고리명 + 설명 텍스트 (설계서 섹션 4 각 카테고리 설명)
- 소속 MetricCard 나열
- 밸류에이션 카테고리: 접힘 기본 + "보조 지표" 표시, 색상 톤 다운

2. CategorySidebar.tsx (데스크톱):
- sticky position
- 7개 카테고리 목록: 신호등 + 카테고리명 + 지표 수
- 스크롤 위치에 따라 활성 카테고리 하이라이트 (IntersectionObserver)
- 클릭 시 해당 섹션으로 scrollTo

3. 모바일 분기:
- 사이드바 대신 카테고리 Chip 가로 스크롤 (상단 고정)
- 지표 카드 Accordion:
  - 접힌 상태 (기본): 신호등 + 지표명 + 현재값 + percentile 한줄
  - 펼친 상태 (탭): 차트 + benchmark 수치 + 해석
  - 한 번에 1개만 펼쳐짐
- 데스크톱: Accordion 없이 전체 펼침

4. ValidationTab.tsx:
- useValidationMetrics(symbol, category) 호출
- 데스크톱: category='all' 1회 호출 + CategorySidebar
- 모바일: 선택된 Chip 카테고리만 개별 호출

반응형 breakpoint: 기존 프로젝트 tailwind 설정 따를 것.
```

---

## FE-PR-6: IndustryPosition + LeaderComparison

```
산업 위치 요약과 대장주 비교 섹션을 구현해줘.

설계서 섹션 3.5 참조.

1. IndustryPosition.tsx:
- 핵심 지표 순위 가로 바 차트 (매출 성장률, 영업이익률, ROE, FCF 마진, 부채비율)
- 바 너비 = rank/total 비율
- "{rank}위/{total}" 텍스트

2. LeaderComparison.tsx:
- "업종 1위: {symbol} ({name})" 헤더
- 자기가 1위면: "업종 2위: {symbol}" 표시
- peer 2개 미만이면: 이 섹션 비표시
- 요약 6개 지표 (기본 노출): 영업이익률, 매출 성장률, 부채비율, FCF 마진, 총자산회전율, 주주수익률
- 상세 16개 (접기/펼치기): 설계서 3.5 참조
- 카테고리별 그룹핑
- 우위 ✅ 표시 (higher_is_better 방향 고려)
- 종합: "22개 중 N개 우위. 강점: ... 약점: ..."
- 성장 추세 비교: 자사 3년 vs 업종 median 3년 (가속/감속/유지)

useLeaderComparison(symbol) hook 사용.
```

---

## FE-PR-7: Empty States + 에러 처리 + 폴리시

```
1차 검증의 빈 데이터 처리, 에러 상태, 최종 폴리시를 구현해줘.

설계서 섹션 10 Phase 4 + Empty State UI 정의 참조.

1. Empty State 5가지 케이스:
- Case 1 (배치 미실행): "재무 분석 데이터 준비 중" + "기본정보 보기" 링크
- Case 2 (부분 데이터): 있는 카테고리만 표시 + "준비 중" 표시
- Case 3 (개별 지표 null): value_status 기반 분기 (MetricCard에서 이미 처리)
- Case 4 (S&P 500 외): "현재 S&P 500 종목 대상" 안내
- Case 5 (특수 산업): gray 신호 + "금융업 특성상..." 고지문 + 툴팁

2. 로딩 상태: skeleton UI (카드 형태 placeholder)

3. API 에러: "데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요." + retry 버튼

4. 성능 최적화:
- 카테고리별 lazy render (IntersectionObserver)
- TanStack Query 캐싱 (staleTime/gcTime 이미 설정됨)
- 모바일 Accordion으로 초기 차트 렌더 수 최소화

5. 데이터 기준일 표시: "데이터 기준: {data_fiscal_year} FY | 마지막 업데이트: {data_freshness}"

6. Chain Sight 탭 이동: 기존 chain_sight 탭을 "분석 및 검증" L2 하위로 이동 (FE-PR-1에서 이미 구조 잡았으면 여기서 확인/마무리)
```

---

## PR 실행 순서

```
BE-PR-1 → BE-PR-2 → BE-PR-3 → BE-PR-4 → BE-PR-5 → BE-PR-6
                                                         ↓
FE-PR-1 (네비게이션은 BE 없이 가능, 병렬 진행 가능)        ↓
FE-PR-2 (BE-PR-6 완료 후)                                 ↓
FE-PR-3 → FE-PR-4 → FE-PR-5 → FE-PR-6 → FE-PR-7
```

**병렬 가능:** FE-PR-1은 BE와 독립. BE-PR-1~6 진행 중에 FE-PR-1 먼저 완료 가능.
**의존성:** FE-PR-2부터는 BE-PR-6(API) 완료 필요.
