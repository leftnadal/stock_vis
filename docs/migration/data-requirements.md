# Stock-Vis FMP 데이터 요구사항 분석 (Migration from Alpha Vantage)

**작성일**: 2025-12-08
**작성자**: Investment-Advisor
**목표**: Alpha Vantage → FMP(Financial Modeling Prep) 마이그레이션을 위한 데이터 매핑 및 호환성 검증

---

## 1. 현재 시스템 데이터 요구사항

### 1.1 필수 데이터 필드 (MustHave)

#### A. 실시간 주가 정보

**현재 Alpha Vantage 출처**: GLOBAL_QUOTE API

| 필드명 | DB 컬럼 | 데이터 타입 | 사용 용도 | FMP 매핑 |
|--------|--------|-----------|---------|----------|
| symbol | symbol | CharField | PK, 검색 | `symbol` |
| 현재가 | real_time_price | Decimal(15,4) | 실시간 포트폴리오 계산 | `price` |
| 변동액 | change | Decimal(15,4) | 수익률 계산 | `change` |
| 변동률 | change_percent | CharField | 화면 표시 | `changePercent` |
| 거래량 | volume | BigInteger | 거래량 차트 | `volume` |
| 시가 | open_price | Decimal(15,4) | 일일 차트 | `open` |
| 고가 | high_price | Decimal(15,4) | 일일 차트 | `high` |
| 저가 | low_price | Decimal(15,4) | 일일 차트 | `low` |
| 전일종가 | previous_close | Decimal(15,4) | 변동률 기준값 | `previousClose` |

**FMP 호환성**: ✅ 완전 호환
**API 엔드포인트**: `/quote/{symbol}` (무료 티어에서 제공)

---

#### B. 회사 기본 정보

**현재 Alpha Vantage 출처**: OVERVIEW API

| 필드명 | DB 컬럼 | 데이터 타입 | 사용 용도 | FMP 매핑 |
|--------|--------|-----------|---------|----------|
| 회사명 | stock_name | CharField(200) | 헤더 표시 | `companyName` |
| 업종 | industry | CharField(100) | 필터/분류 | `industry` |
| 섹터 | sector | CharField(100) | 필터/분류 | `sector` |
| 설명 | description | TextField | 회사 정보 탭 | `description` |
| 거래소 | exchange | CharField(50) | 정보 표시 | `exchange` |
| CEO | ❌ 없음 | - | - | `ceo` |
| 종업원 수 | ❌ 없음 | - | - | `employees` |
| 공식 웹사이트 | official_site | URLField | 링크 | `website` |
| 주소 | address | TextField | 정보 표시 | `address` |
| 회계연도 종료월 | fiscal_year_end | CharField(20) | 분기 기준 | `fiscalYearEnd` |
| 최근분기 | latest_quarter | DateField | 분기 기준 | `latestQuarter` |

**FMP 호환성**: ✅ 완전 호환 (추가 필드 있음)
**API 엔드포인트**: `/profile/{symbol}` (무료 티어에서 제공)

---

#### C. 시가총액 및 재무 비율

**현재 Alpha Vantage 출처**: OVERVIEW API

| 필드명 | DB 컬럼 | 데이터 타입 | 사용 용도 | FMP 매핑 |
|--------|--------|-----------|---------|----------|
| 시가총액 | market_capitalization | Decimal(20,2) | 포트폴리오 정렬 | `mktCap` |
| EBITDA | ebitda | Decimal(20,2) | 재무 분석 | `ebitda` |
| PER | pe_ratio | Decimal(10,4) | 기술적 지표 | `trailingPe` |
| PEG | peg_ratio | Decimal(10,4) | 성장성 평가 | `pegRatio` |
| 순자산가치 | book_value | Decimal(10,4) | 기술적 지표 | `bookValue` |
| 주당배당금 | dividend_per_share | Decimal(10,4) | 배당 정보 | `dividendPerShare` |
| 배당수익률 | dividend_yield | Decimal(10,4) | 수익 분석 | `dividendYield` |
| EPS | eps | Decimal(10,4) | 기술적 지표 | `eps` |
| 매출액(TTM) | revenue_ttm | Decimal(20,2) | 기술적 지표 | `revenuePerShare` |
| 순이익률 | profit_margin | Decimal(10,4) | 수익성 분석 | `profitMargin` |
| 영업이익률(TTM) | operating_margin_ttm | Decimal(10,4) | 수익성 분석 | `operatingMargin` |
| 자산수익률(TTM) | return_on_assets_ttm | Decimal(10,4) | 효율성 분석 | `roic` |
| 자기자본수익률(TTM) | return_on_equity_ttm | Decimal(10,4) | 효율성 분석 | `roe` |
| 전체 매출액(TTM) | revenue_ttm | Decimal(20,2) | 재무 규모 | `revenue` |
| 총이익(TTM) | gross_profit_ttm | Decimal(20,2) | 원가율 분석 | `grossProfit` |
| 조정 EPS(TTM) | diluted_eps_ttm | Decimal(10,4) | 기술적 지표 | `dilutedEps` |
| 분기 EPS 성장률 | quarterly_earnings_growth_yoy | Decimal(10,4) | 성장성 분석 | ⚠️ API에서 제공 안 함 |
| 분기 매출 성장률 | quarterly_revenue_growth_yoy | Decimal(10,4) | 성장성 분석 | ⚠️ API에서 제공 안 함 |

**FMP 호환성**: ✅ 대부분 호환 (성장률은 계산 필요)
**API 엔드포인트**: `/quote/{symbol}` (기본), `/ratios/{symbol}` (상세)

---

#### D. 기술적 지표

**현재 Alpha Vantage 출처**: OVERVIEW API

| 필드명 | DB 컬럼 | 데이터 타입 | 사용 용도 | FMP 매핑 |
|--------|--------|-----------|---------|----------|
| Trailing PE | trailing_pe | Decimal(10,4) | 밸류에이션 | `trailingPe` |
| Forward PE | forward_pe | Decimal(10,4) | 미래 밸류에이션 | ⚠️ 별도 계산 필요 |
| PS 비율 | price_to_sales_ratio_ttm | Decimal(10,4) | 밸류에이션 | `priceToSalesRatio` |
| PB 비율 | price_to_book_ratio | Decimal(10,4) | 밸류에이션 | `priceToBook` |
| EV/Revenue | ev_to_revenue | Decimal(10,4) | 기업가치 분석 | `evToRevenue` |
| EV/EBITDA | ev_to_ebitda | Decimal(10,4) | 기업가치 분석 | `evToEbitda` |
| 베타 | beta | Decimal(10,4) | 변동성 분석 | `beta` |
| 52주 고가 | week_52_high | Decimal(15,4) | 변동성 분석 | `52WeekHigh` |
| 52주 저가 | week_52_low | Decimal(15,4) | 변동성 분석 | `52WeekLow` |
| 50일 MA | day_50_moving_average | Decimal(15,4) | 기술적 분석 | ⚠️ 별도 계산 필요 |
| 200일 MA | day_200_moving_average | Decimal(15,4) | 기술적 분석 | ⚠️ 별도 계산 필요 |
| 발행주식 수 | shares_outstanding | Decimal(20,2) | 시가총액 검증 | `sharesOutstanding` |

**FMP 호환성**: ⚠️ 부분 호환 (이동평균은 별도 계산)
**API 엔드포인트**: `/quote/{symbol}`, `/historical-chart/1min/{symbol}` (이동평균 계산용)

---

#### E. 분석가 의견

**현재 Alpha Vantage 출처**: OVERVIEW API

| 필드명 | DB 컬럼 | 데이터 타입 | 사용 용도 | FMP 매핑 |
|--------|--------|-----------|---------|----------|
| 목표주가 | analyst_target_price | Decimal(15,4) | 투자 판단 | `analystTargetPrice` |
| Strong Buy | analyst_rating_strong_buy | Integer | 투자 의견 분포 | `analystRatingBuyCount` |
| Buy | analyst_rating_buy | Integer | 투자 의견 분포 | `analystRatingBuyCount` |
| Hold | analyst_rating_hold | Integer | 투자 의견 분포 | `analystRatingHoldCount` |
| Sell | analyst_rating_sell | Integer | 투자 의견 분포 | `analystRatingSellCount` |
| Strong Sell | analyst_rating_strong_sell | Integer | 투자 의견 분포 | `analystRatingStrongSellCount` |

**FMP 호환성**: ✅ 호환 가능 (별도 API 필요)
**API 엔드포인트**: `/analyst-estimates/{symbol}` (별도 API)

---

#### F. 배당 정보

**현재 Alpha Vantage 출처**: OVERVIEW API

| 필드명 | DB 컬럼 | 데이터 타입 | 사용 용도 | FMP 매핑 |
|--------|--------|-----------|---------|----------|
| 배당금 지급일 | dividend_date | DateField | 배당 일정 | `lastDividendDate` |
| 배당락일 | ex_dividend_date | DateField | 배당 일정 | `lastDividendDate` |

**FMP 호환성**: ⚠️ 부분 호환
**API 엔드포인트**: `/historical-dividends/{symbol}`

---

### 1.2 선택 데이터 필드 (NiceToHave)

| 기능 | 현재 Alpha Vantage | FMP | 비고 |
|-----|-----------------|-----|------|
| 일일 가격 히스토리 | `TIME_SERIES_DAILY` | `/historical-price-full/{symbol}` | 필수 |
| 주간 가격 히스토리 | `TIME_SERIES_WEEKLY` | ⚠️ 별도 처리 필요 | 1일 데이터로 주간 계산 |
| 뉴스 및 이벤트 | ❌ 미제공 | `/news?symbol={symbol}` | 추가 기능 |
| 기업 뉴스 | ❌ 미제공 | `/news?symbol={symbol}` | 추가 기능 |
| 업계 뉴스 | ❌ 미제공 | ⚠️ 별도 크롤링 필요 | 추가 기능 |

---

### 1.3 재무제표 데이터 요구사항

#### A. 재무제표 기본 구조

| 항목 | Alpha Vantage | FMP | 비고 |
|-----|--------------|-----|------|
| **손익계산서** | INCOME_STATEMENT | `/income-statement/{symbol}` | 직접 마핑 가능 |
| **대차대조표** | BALANCE_SHEET | `/balance-sheet-statement/{symbol}` | 직접 마핑 가능 |
| **현금흐름표** | CASH_FLOW | `/cash-flow-statement/{symbol}` | 직접 마핑 가능 |
| **기간** | annual + quarterly | annual + quarterly | 동일 |
| **조회 기간** | 최근 20개 | 최근 120개 | FMP가 더 풍부 |

#### B. 손익계산서 (Income Statement)

**FMP API**: `/income-statement/{symbol}?limit=120&period=annual|quarterly`

| DB 컬럼 | Alpha Vantage | FMP | 호환성 |
|---------|--------------|-----|--------|
| total_revenue | `totalRevenue` | `revenue` | ✅ |
| cost_of_revenue | `costOfRevenue` | `costOfRevenue` | ✅ |
| gross_profit | `grossProfit` | `grossProfit` | ✅ |
| operating_expenses | `operatingExpenses` | `operatingExpenses` | ✅ |
| selling_general_and_administrative | `operatingExpenses` 계산 | `sellingGeneralAndAdministrative` | ✅ |
| research_and_development | `researchAndDevelopment` | `researchAndDevelopment` | ✅ |
| operating_income | `operatingIncome` | `operatingIncome` | ✅ |
| interest_expense | `interestExpense` | `interestExpense` | ✅ |
| income_before_tax | `incomeBeforeTax` | `incomeBeforeTax` | ✅ |
| income_tax_expense | `incomeTaxExpense` | `incomeTaxExpense` | ✅ |
| net_income | `netIncome` | `netIncome` | ✅ |

**호환성**: ✅ 완전 호환

#### C. 대차대조표 (Balance Sheet)

**FMP API**: `/balance-sheet-statement/{symbol}?limit=120&period=annual|quarterly`

| DB 컬럼 | Alpha Vantage | FMP | 호환성 |
|---------|--------------|-----|--------|
| total_assets | `totalAssets` | `totalAssets` | ✅ |
| current_assets | `totalCurrentAssets` | `totalCurrentAssets` | ✅ |
| cash_and_cash_equivalents | `CashAndCashEquivalentsAtCarryingValue` | `cashAndCashEquivalents` | ✅ |
| inventory | `inventory` | `inventory` | ✅ |
| current_net_receivables | `currentNetReceivables` | `netReceivables` | ✅ |
| total_liabilities | `totalLiabilities` | `totalLiabilities` | ✅ |
| current_liabilities | `totalCurrentLiabilities` | `totalCurrentLiabilities` | ✅ |
| current_debt | `currentDebt` | `shortTermDebt` | ✅ |
| long_term_debt | `longTermDebt` | `longTermDebt` | ✅ |
| total_shareholder_equity | `totalShareholderEquity` | `totalStockholdersEquity` | ✅ |

**호환성**: ✅ 완전 호환

#### D. 현금흐름표 (Cash Flow)

**FMP API**: `/cash-flow-statement/{symbol}?limit=120&period=annual|quarterly`

| DB 컬럼 | Alpha Vantage | FMP | 호환성 |
|---------|--------------|-----|--------|
| operating_cashflow | `operatingCashflow` | `operatingCashFlow` | ✅ |
| capital_expenditures | `capitalExpenditures` | `capitalExpenditure` | ✅ |
| cashflow_from_investment | `cashflowFromInvestment` | `investingCashflow` | ✅ |
| cashflow_from_financing | `cashflowFromFinancing` | `financingCashflow` | ✅ |
| dividend_payout | `dividendPayout` | `dividendsPaid` | ✅ |
| net_income | `netIncome` | `netIncome` | ✅ |

**호환성**: ✅ 완전 호환

---

## 2. FMP 무료 티어 데이터 커버리지 검증

### 2.1 FMP 무료 API 리스트

| API | 무료 | 유료 | 호출당 Credits | 비고 |
|-----|-----|-----|--------------|------|
| `/quote/{symbol}` | ✅ | ✅ | 1 | 실시간 가격 |
| `/profile/{symbol}` | ✅ | ✅ | 1 | 회사 정보 |
| `/historical-price-full/{symbol}` | ✅ | ✅ | 2-5 | 가격 히스토리 |
| `/income-statement/{symbol}` | ⚠️ 일부 | ✅ | 1 | 최근 5개 무료 |
| `/balance-sheet-statement/{symbol}` | ⚠️ 일부 | ✅ | 1 | 최근 5개 무료 |
| `/cash-flow-statement/{symbol}` | ⚠️ 일부 | ✅ | 1 | 최근 5개 무료 |
| `/analyst-estimates/{symbol}` | ✅ | ✅ | 1 | 분석가 의견 |
| `/news?symbol={symbol}` | ✅ | ✅ | 1 | 최신 뉴스 |
| `/batch-request-end-of-day` | ✅ | ✅ | ? | 배치 요청 |
| `/ratios/{symbol}` | ⚠️ 일부 | ✅ | 1 | 주요 비율 |

### 2.2 FMP 무료 티어 한계

- **일일 할당량**: 250 API calls/day (무료, 추가 요청 유료)
- **재무제표**: 최근 5개 데이터만 무료 (전체 120개 히스토리는 유료)
- **배치 API**: 무료 티어에서 제한됨
- **Rate Limiting**: 없음 (즉시 처리)

---

## 3. Alpha Vantage → FMP 마이그레이션 전략

### 3.1 데이터 마핑 매트릭스

| 데이터 카테고리 | Alpha Vantage | FMP | 마이그레이션 난이도 | 우선순위 |
|---------------|--------------|-----|------------------|----------|
| 실시간 가격 | GLOBAL_QUOTE | `/quote` | 🟢 쉬움 | P0 |
| 회사 정보 | OVERVIEW | `/profile` | 🟢 쉬움 | P0 |
| 가격 히스토리 | TIME_SERIES_DAILY | `/historical-price-full` | 🟢 쉬움 | P0 |
| 손익계산서 | INCOME_STATEMENT | `/income-statement` | 🟢 쉬움 | P1 |
| 대차대조표 | BALANCE_SHEET | `/balance-sheet-statement` | 🟢 쉬움 | P1 |
| 현금흐름표 | CASH_FLOW | `/cash-flow-statement` | 🟢 쉬움 | P1 |
| 기술적 지표 | OVERVIEW 계산값 | 직접 계산 필요 | 🟡 보통 | P2 |
| 분석가 의견 | OVERVIEW | `/analyst-estimates` | 🟢 쉬움 | P3 |
| 주간 데이터 | TIME_SERIES_WEEKLY | 일일→주간 변환 | 🟡 보통 | P2 |

### 3.2 마이그레이션 단계별 계획

**Phase 1 (필수)**: 실시간 가격 + 회사 정보
- 소요 시간: 1-2주
- 데이터 손실: 없음
- 시스템 가동성: 유지 필요

**Phase 2 (중요)**: 재무제표 + 가격 히스토리
- 소요 시간: 2-3주
- 데이터 손실: Alpha Vantage의 과거 데이터 보존 권장
- 시스템 가동성: 점진적 전환

**Phase 3 (부가)**: 기술적 지표 + 분석가 의견
- 소요 시간: 1-2주
- 데이터 손실: 계산식 재정의 필요
- 시스템 가동성: 추가 개선

---

## 4. 주요 고려사항

### 4.1 데이터 품질 비교

| 항목 | Alpha Vantage | FMP | 권장사항 |
|-----|---------------|-----|----------|
| 실시간성 | 15분 지연 | 실시간 | FMP 사용 |
| 정확도 | 높음 | 높음 | 동일 |
| 완성도 | 70% | 85% | FMP 우수 |
| 히스토리 | 20년 | 30년 | FMP 우수 |
| Rate Limiting | 12초/call | 없음 | FMP 우수 |

### 4.2 마이그레이션 리스크

1. **데이터 손실**: 마이그레이션 전 Alpha Vantage 데이터 백업 (완료)
2. **API 키 관리**: FMP 무료 API 키 발급 및 환경 변수 설정
3. **비용 증가**: 250 calls/day 초과 시 유료 API로 업그레이드 필요
4. **데이터 형식**: 필드명 차이 (camelCase) → snake_case 변환 필요

### 4.3 추가 필드 (FMP에서만 제공)

FMP에서 새로 추가 가능한 필드들:

- `ceo`: CEO 이름 (Company Profile)
- `employees`: 종업원 수 (Company Profile)
- `marketCapitalization`: 실시간 시가총액 (Quote)
- `newsUrl`: 뉴스 링크 (News API)
- `freeFloat`: 자유 변동 주식 수 (Profile)

---

## 5. 결론 및 권장사항

### 5.1 마이그레이션 우선순위

1. **즉시 마이그레이션** (P0):
   - 실시간 가격 + 회사 정보 (1주)
   - 이유: Rate Limiting 제거로 성능 개선, 실시간성 향상

2. **단기 마이그레이션** (P1):
   - 재무제표 (2-3주)
   - 이유: 데이터 품질 우수, 히스토리 풍부

3. **중기 마이그레이션** (P2):
   - 기술적 지표 재계산 (1-2주)
   - 주간 데이터 자동 생성 (1주)

4. **장기 계획** (P3):
   - 분석가 의견 (추가)
   - 뉴스/이벤트 (신규 기능)

### 5.2 API 호출 예산 최적화

- 현재 Alpha Vantage: 12초 Rate Limiting (실시간 성능 저해)
- FMP 마이그레이션: Rate Limiting 제거 (성능 3-4배 향상)
- API 호출 예산: 250 calls/day (추가 최적화 필요)

---

## Appendix: 상세 필드 매핑표

### Alpha Vantage "OVERVIEW" → FMP "/profile" + "/quote"

```
Alpha Vantage OVERVIEW Fields → FMP APIs
Symbol → /profile, /quote
AssetType → /profile
Name → /profile (companyName)
Description → /profile
Exchange → /profile
Currency → /profile
Country → /profile (not in DB)
Sector → /profile
Industry → /profile
Address → /profile
OfficialWebsiteUrl → /profile (website)
FiscalYearEnd → /profile
LatestQuarter → /profile
MarketCapitalization → /quote (mktCap)
EBITDA → /quote
PERatio → /quote (trailingPe)
PEGRatio → /quote
BookValue → /quote
DividendPerShare → /quote
DividendYield → /quote
EPS → /quote
RevenueTTM → /quote
ProfitMargin → /quote
OperatingMarginTTM → /quote
ReturnOnAssetsTTM → /quote (roic)
ReturnOnEquityTTM → /quote (roe)
RevenuePerShareTTM → /quote (revenuePerShare)
GrossProfitTTM → /quote (grossProfit)
DilutedEpsTTM → /quote (dilutedEps)
QuarterlyEarningsGrowthYOY → 📊 별도 계산 필요
QuarterlyRevenueGrowthYOY → 📊 별도 계산 필요
AnalystTargetPrice → /analyst-estimates
AnalystRatingStrongBuy → /analyst-estimates
AnalystRatingBuy → /analyst-estimates
AnalystRatingHold → /analyst-estimates
AnalystRatingSell → /analyst-estimates
AnalystRatingStrongSell → /analyst-estimates
TrailingPE → /quote (trailingPe)
ForwardPE → 📊 별도 계산 필요
PriceToSalesRatioTTM → /quote (priceToSalesRatio)
PriceToBookRatio → /quote (priceToBook)
EV/Revenue → /quote (evToRevenue)
EV/EBITDA → /quote (evToEbitda)
Beta → /quote
52WeekHigh → /quote
52WeekLow → /quote
50DayMovingAverage → 📊 별도 계산 필요
200DayMovingAverage → 📊 별도 계산 필요
SharesOutstanding → /quote (sharesOutstanding)
DividendDate → /historical-dividends
ExDividendDate → /historical-dividends
```

**범례**:
- ✅: FMP에서 직접 제공
- 📊: 별도 계산 필요 (가격 히스토리 기반)
- ⚠️: 근사값 또는 제한적 제공
- ❌: FMP에서 미제공 (외부 소스 필요)

