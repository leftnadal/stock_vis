# Alpha Vantage API 사용 현황 분석 보고서

**작성일**: 2025-12-08
**작성자**: QA-Architecture Agent
**목적**: FMP 마이그레이션을 위한 현행 시스템 분석

---

## 1. 시스템 개요

### 1.1 아키텍처 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                          │
│   - StockChart, FinancialTabs, PortfolioStockCard               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (Django REST)                         │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  stocks/views   │  │   users/views    │  │  stocks/tasks  │  │
│  │  views_search   │  │                  │  │    (Celery)    │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬────────┘  │
│           │                    │                     │           │
│           └────────────────────┴─────────────────────┘           │
│                                │                                 │
│                                ▼                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              API request/ (3계층 구조)                     │  │
│  │                                                            │  │
│  │  ┌──────────────────┐                                     │  │
│  │  │ alphavantage_    │  ← HTTP 클라이언트                   │  │
│  │  │ client.py        │    Rate limiting (12초)              │  │
│  │  └────────┬─────────┘                                     │  │
│  │           │                                                │  │
│  │  ┌────────▼─────────┐                                     │  │
│  │  │ alphavantage_    │  ← 데이터 변환/검증                   │  │
│  │  │ processor.py     │    camelCase → snake_case            │  │
│  │  └────────┬─────────┘                                     │  │
│  │           │                                                │  │
│  │  ┌────────▼─────────┐                                     │  │
│  │  │ alphavantage_    │  ← DB 저장, 트랜잭션 관리             │  │
│  │  │ service.py       │                                      │  │
│  │  └──────────────────┘                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │   Alpha Vantage API     │
              │   (외부 서비스)          │
              └─────────────────────────┘
```

---

## 2. Alpha Vantage API 호출 현황

### 2.1 사용 중인 엔드포인트

| Function | 파일 위치 | 메서드명 | 용도 | 호출 빈도 |
|----------|----------|---------|------|----------|
| `GLOBAL_QUOTE` | alphavantage_client.py:71 | `get_stock_quote()` | 실시간 주가 조회 | **높음** |
| `OVERVIEW` | alphavantage_client.py:121 | `get_company_overview()` | 회사 기본정보 | 중간 |
| `TIME_SERIES_DAILY` | alphavantage_client.py:87 | `get_daily_stock_data()` | 일별 시세 | 중간 |
| `TIME_SERIES_WEEKLY` | alphavantage_client.py:104 | `get_weekly_stock_data()` | 주간 시세 | 낮음 |
| `SYMBOL_SEARCH` | alphavantage_client.py:136 | `search_stocks()` | 종목 검색 | 중간 |
| `BALANCE_SHEET` | alphavantage_client.py:182 | `get_balance_sheet()` | 재무상태표 | 낮음 |
| `INCOME_STATEMENT` | alphavantage_client.py:165 | `get_income_statement()` | 손익계산서 | 낮음 |
| `CASH_FLOW` | alphavantage_client.py:199 | `get_cash_flow()` | 현금흐름표 | 낮음 |
| `SECTOR` | alphavantage_client.py:152 | `get_sector_performance()` | 섹터 성과 | 낮음 |

### 2.2 호출 지점별 상세 분석

#### 2.2.1 API request/ 디렉토리 (핵심 레이어)

| 파일 | 역할 | 의존 엔드포인트 |
|-----|------|----------------|
| `alphavantage_client.py` | HTTP 클라이언트, Rate limiting | 모든 엔드포인트 |
| `alphavantage_processor.py` | 데이터 변환/검증 | - (순수 변환 로직) |
| `alphavantage_service.py` | DB 저장, 비즈니스 로직 | Client 전체 메서드 사용 |

#### 2.2.2 stocks/ 앱

| 파일 | 함수명 | 호출 엔드포인트 | 용도 |
|-----|--------|---------------|------|
| `views_search.py:24` | `SymbolSearchView.get()` | SYMBOL_SEARCH | 종목 검색 자동완성 |
| `views_search.py:126` | `SymbolValidateView.get()` | GLOBAL_QUOTE | 심볼 유효성 검증 |
| `views_search.py:242` | `validate_and_create_stock()` | GLOBAL_QUOTE, OVERVIEW, SYMBOL_SEARCH | 새 종목 생성 |
| `tasks.py:17` | `update_realtime_prices()` | (Service 통해) | Celery 실시간 업데이트 |
| `tasks.py:89` | `update_daily_prices()` | (Service 통해) | Celery 일일 업데이트 |
| `tasks.py:159` | `update_weekly_prices()` | (Service 통해) | Celery 주간 업데이트 |
| `tasks.py:192` | `update_financial_statements()` | (Service 통해) | Celery 재무제표 업데이트 |
| `tasks.py:267` | `fetch_and_save_stock_data()` | (Service 전체) | 포트폴리오 추가 시 전체 수집 |

#### 2.2.3 users/ 앱

| 파일 | 함수명 | 호출 엔드포인트 | 용도 |
|-----|--------|---------------|------|
| `utils.py:12` | `get_alphavantage_service()` | - | Service 인스턴스 팩토리 |
| `utils.py:32` | `ensure_complete_stock_data()` | Service 전체 | 데이터 완전성 검사 |
| `utils.py:143` | `fetch_stock_data_sync()` | Service 전체 | 동기식 데이터 수집 |
| `utils.py:260` | `update_portfolio_stock_data()` | Service 전체 | 포트폴리오 일괄 업데이트 |
| `utils.py:307` | `fetch_stock_data_background()` | Service 전체 | 백그라운드 수집 |
| `utils.py:372` | `get_stock_data_status()` | - | 수집 상태 확인 |

---

## 3. 데이터 모델 매핑

### 3.1 Stock 모델 (기본 정보)

```python
# OVERVIEW API → Stock 모델 필드 매핑 (alphavantage_processor.py:45-123)

Stock 모델 필드                  | Alpha Vantage 응답 키
--------------------------------|------------------------
symbol                          | Symbol
stock_name                      | Name
description                     | Description
exchange                        | Exchange
currency                        | Currency
sector                          | Sector
industry                        | Industry
asset_type                      | AssetType
address                         | Address
official_site                   | OfficialSite
fiscal_year_end                 | FiscalYearEnd
latest_quarter                  | LatestQuarter
market_capitalization           | MarketCapitalization
ebitda                          | EBITDA
pe_ratio                        | PERatio
peg_ratio                       | PEGRatio
book_value                      | BookValue
dividend_per_share              | DividendPerShare
dividend_yield                  | DividendYield
eps                             | EPS
revenue_per_share_ttm           | RevenuePerShareTTM
profit_margin                   | ProfitMargin
operating_margin_ttm            | OperatingMarginTTM
return_on_assets_ttm            | ReturnOnAssetsTTM
return_on_equity_ttm            | ReturnOnEquityTTM
revenue_ttm                     | RevenueTTM
gross_profit_ttm                | GrossProfitTTM
diluted_eps_ttm                 | DilutedEPSTTM
quarterly_earnings_growth_yoy   | QuarterlyEarningsGrowthYOY
quarterly_revenue_growth_yoy    | QuarterlyRevenueGrowthYOY
analyst_target_price            | AnalystTargetPrice
analyst_rating_*                | AnalystRating*
trailing_pe                     | TrailingPE
forward_pe                      | ForwardPE
price_to_sales_ratio_ttm        | PriceToSalesRatioTTM
price_to_book_ratio             | PriceToBookRatio
ev_to_revenue                   | EVToRevenue
ev_to_ebitda                    | EVToEBITDA
beta                            | Beta
week_52_high                    | 52WeekHigh
week_52_low                     | 52WeekLow
day_50_moving_average           | 50DayMovingAverage
day_200_moving_average          | 200DayMovingAverage
shares_outstanding              | SharesOutstanding
dividend_date                   | DividendDate
ex_dividend_date                | ExDividendDate
```

### 3.2 실시간 가격 (GLOBAL_QUOTE)

```python
# GLOBAL_QUOTE API → Stock 모델 가격 필드 (alphavantage_processor.py:17-42)

Stock 모델 필드     | Alpha Vantage 응답 키
-------------------|------------------------
open_price         | 02. open
high_price         | 03. high
low_price          | 04. low
real_time_price    | 05. price
volume             | 06. volume
previous_close     | 08. previous close
change             | 09. change
change_percent     | 10. change percent
```

### 3.3 가격 히스토리

```python
# TIME_SERIES_DAILY/WEEKLY → DailyPrice/WeeklyPrice (alphavantage_processor.py:126-201)

모델 필드      | Alpha Vantage 응답 키
--------------|------------------------
open_price    | 1. open
high_price    | 2. high
low_price     | 3. low
close_price   | 4. close
volume        | 5. volume
date          | (시계열 키 파싱)
```

### 3.4 재무제표

#### Balance Sheet (alphavantage_processor.py:234-362)
- **연간 보고서**: `annualReports[]` → `period_type='annual'`
- **분기 보고서**: `quarterlyReports[]` → `period_type='quarter'`
- **주요 필드**: totalAssets, totalLiabilities, totalShareholderEquity, commonStock, retainedEarnings 등 30+ 필드

#### Income Statement (alphavantage_processor.py:364-466)
- **주요 필드**: totalRevenue, grossProfit, operatingIncome, netIncome, ebitda 등 24+ 필드

#### Cash Flow Statement (alphavantage_processor.py:468-577)
- **주요 필드**: operatingCashflow, cashflowFromInvestment, cashflowFromFinancing, capitalExpenditures 등 27+ 필드

---

## 4. Rate Limiting 현황

### 4.1 현재 구현

```python
# alphavantage_client.py:16-45
class AlphaVantageClient:
    def __init__(self, api_key, request_delay=12.0):
        self.request_delay = request_delay  # 12초 (5 calls/min 대응)
        self.last_request_time = 0

    def _make_request(self, params):
        # Rate limiting 구현
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
```

### 4.2 추가 Rate Limit 적용 지점

| 위치 | 대기 시간 | 설명 |
|-----|----------|------|
| `users/utils.py:80` | 12초 | 기본 정보 수집 후 |
| `users/utils.py:100` | 12초 | 가격 데이터 수집 후 |
| `stocks/views_search.py:300` | 12초 | 종목 검증 후 |
| `stocks/tasks.py:72` | 12초 | Celery 태스크 내 |
| `stocks/tasks.py:144` | 12초 | 배치 업데이트 내 |

---

## 5. 프론트엔드 의존성

### 5.1 직접 언급 파일

```typescript
// frontend/app/stocks/[symbol]/page.tsx:143
// 주석으로 Alpha Vantage GLOBAL_QUOTE 언급

{/* Left Side - Basic Info (Alpha Vantage GLOBAL_QUOTE) */}
```

### 5.2 간접 의존 (API 응답 형식)

- **차트 컴포넌트**: `StockChart.tsx` - 일별/주간 가격 데이터
- **재무제표 탭**: `FinancialTabs/` - 대차대조표, 손익계산서, 현금흐름표
- **포트폴리오 카드**: `PortfolioStockCard.tsx` - 실시간 가격 데이터

---

## 6. 캐싱 전략

### 6.1 현재 캐싱 구현

| 캐시 키 패턴 | TTL | 적용 위치 |
|-------------|-----|----------|
| `symbol_search_{keywords}` | 300초 (5분) | views_search.py:107 |
| `symbol_validate_{symbol}` | 600초 (10분) | views_search.py:195 |
| `stock_quote_{symbol}` | 60초 | stocks/views.py |
| `chart_{symbol}_{type}_{period}` | 60초 | stocks/views.py |
| `overview_{symbol}` | 600초 | stocks/views.py |

### 6.2 캐시 무효화 지점

```python
# stocks/tasks.py:67-69
cache.delete(f'stock_quote_{symbol}')
cache.delete(f'chart_{symbol}_daily_1d')

# stocks/tasks.py:341-343
cache.delete(f'stock_quote_{symbol}')
cache.delete(f'overview_{symbol}')
cache.delete(f'chart_{symbol}_daily_1d')
```

---

## 7. 의존성 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                        사용자 요청 진입점                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [종목 검색]           [포트폴리오]          [주식 상세 페이지]        │
│       │                    │                      │                 │
│       ▼                    ▼                      ▼                 │
│  SymbolSearchView    PortfolioViewSet      StockDetailView          │
│  SymbolValidateView       │                      │                 │
│       │                    │                      │                 │
│       │                    ▼                      │                 │
│       │           fetch_stock_data_              │                 │
│       │           background()                   │                 │
│       │                    │                      │                 │
│       └────────────────────┼──────────────────────┘                 │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AlphaVantageService (통합 진입점)                │   │
│  │                                                              │   │
│  │  update_stock_data()      ← OVERVIEW + GLOBAL_QUOTE          │   │
│  │  update_historical_prices() ← TIME_SERIES_DAILY/WEEKLY       │   │
│  │  update_financial_statements() ← BALANCE/INCOME/CASH_FLOW    │   │
│  │  update_previous_close()   ← TIME_SERIES_DAILY               │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AlphaVantageProcessor (데이터 변환)              │   │
│  │                                                              │   │
│  │  process_stock_quote()      → Stock (가격 필드)               │   │
│  │  process_company_overview() → Stock (기본 정보)               │   │
│  │  process_historical_prices() → DailyPrice/WeeklyPrice        │   │
│  │  process_balance_sheet()    → BalanceSheet                   │   │
│  │  process_income_statement() → IncomeStatement                │   │
│  │  process_cash_flow()        → CashFlowStatement              │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AlphaVantageClient (HTTP 클라이언트)             │   │
│  │                                                              │   │
│  │  _make_request() ← Rate limiting 12초                        │   │
│  │  get_stock_quote() → GLOBAL_QUOTE                            │   │
│  │  get_company_overview() → OVERVIEW                           │   │
│  │  get_daily_stock_data() → TIME_SERIES_DAILY                  │   │
│  │  get_weekly_stock_data() → TIME_SERIES_WEEKLY                │   │
│  │  search_stocks() → SYMBOL_SEARCH                             │   │
│  │  get_balance_sheet() → BALANCE_SHEET                         │   │
│  │  get_income_statement() → INCOME_STATEMENT                   │   │
│  │  get_cash_flow() → CASH_FLOW                                 │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Alpha Vantage API   │
                    │                       │
                    │  Rate Limit:          │
                    │  - 5 calls/min (무료) │
                    │  - 500 calls/day      │
                    └───────────────────────┘
```

---

## 8. 마이그레이션 영향도 분석

### 8.1 핵심 변경 대상 파일

| 우선순위 | 파일 | 변경 범위 | 비고 |
|---------|------|----------|------|
| **P0** | `API request/alphavantage_client.py` | 전체 재작성 → `fmp_client.py` | 새 클라이언트 필요 |
| **P0** | `API request/alphavantage_processor.py` | 필드 매핑 수정 → `fmp_processor.py` | 응답 형식 차이 |
| **P0** | `API request/alphavantage_service.py` | 인터페이스 유지, 내부 변경 → `fmp_service.py` | Provider 패턴 권장 |
| **P1** | `stocks/views_search.py` | 검색 로직 수정 | FMP 검색 API 차이 |
| **P1** | `stocks/tasks.py` | Service import 경로 변경 | 영향도 낮음 |
| **P1** | `users/utils.py` | Service import 경로 변경 | 영향도 낮음 |
| **P2** | `config/settings.py` | API 키 환경변수 추가 | `FMP_API_KEY` |
| **P2** | `stocks/models.py` | 필드 추가/수정 가능 | FMP 전용 필드 검토 |

### 8.2 변경 없이 유지되는 파일

- `stocks/views.py` - Service 레이어만 사용
- `frontend/` - API 응답 형식 동일 유지 시

### 8.3 예상 위험도

| 리스크 | 확률 | 영향 | 대응 방안 |
|--------|-----|------|----------|
| 필드 매핑 불일치 | 높음 | 중간 | Processor에서 변환 레이어 추가 |
| 검색 기능 차이 | 중간 | 낮음 | FMP 검색 API 테스트 필요 |
| Rate Limit 차이 (250/일) | 높음 | 높음 | 캐싱 강화, 호출 예산 관리 |
| 재무제표 필드 차이 | 중간 | 중간 | 필드 매핑 테이블 작성 필요 |

---

## 9. 권장 마이그레이션 전략

### 9.1 Provider 추상화 패턴

```python
# 권장 구조
API_request/
├── base_provider.py          # 추상 인터페이스
├── alphavantage/
│   ├── client.py
│   ├── processor.py
│   └── service.py
├── fmp/
│   ├── client.py
│   ├── processor.py
│   └── service.py
└── stock_data_provider.py    # Factory + Feature Flag
```

### 9.2 점진적 전환 전략

1. **Phase 1**: FMP 클라이언트/프로세서 구현 (Alpha Vantage 유지)
2. **Phase 2**: Feature Flag로 엔드포인트별 전환
3. **Phase 3**: 모니터링 및 검증
4. **Phase 4**: Alpha Vantage 코드 제거

---

## 10. 다음 단계

1. **FMP API 엔드포인트 매핑 테이블 작성** (Investment-Advisor)
2. **데이터 요구사항 상세 정의** (Investment-Advisor)
3. **API 호출 예산 계획 수립** (Investment-Advisor)
4. **Provider 추상화 아키텍처 설계** (QA-Architecture)
5. **테스트 전략 수립** (QA-Architecture)

---

*이 보고서는 QA-Architecture 에이전트에 의해 자동 생성되었습니다.*
