# Stock-Vis 화면-데이터 구조 문서

> 각 페이지별 컴포넌트, API 엔드포인트, 데이터베이스 연결 정보

---

## 목차

1. [홈 페이지 (/)](#1-홈-페이지-)
2. [로그인 (/login)](#2-로그인-login)
3. [회원가입 (/signup)](#3-회원가입-signup)
4. [대시보드 (/dashboard)](#4-대시보드-dashboard)
5. [포트폴리오 (/portfolio)](#5-포트폴리오-portfolio)
6. [종목 상세 (/stocks/[symbol])](#6-종목-상세-stockssymbol)
7. [관심종목 (/watchlist)](#7-관심종목-watchlist)
8. [Market Pulse (/market-pulse)](#8-market-pulse-market-pulse)
9. [마이페이지 (/mypage)](#9-마이페이지-mypage)
10. [Backend URL 요약](#10-backend-url-요약)
11. [데이터베이스 모델 관계도](#11-데이터베이스-모델-관계도)

---

## 데이터베이스 모델 범례

```
┌─────────────────────────────────────────────────────────────┐
│  📊 stocks 앱: Stock, DailyPrice, WeeklyPrice,             │
│               BalanceSheet, IncomeStatement, CashFlowStatement │
│                                                             │
│  👤 users 앱: User, Portfolio, Watchlist, WatchlistItem    │
│                                                             │
│  📰 news 앱: NewsArticle, NewsEntity, EntityHighlight,     │
│             SentimentHistory                                │
│                                                             │
│  📈 analysis 앱: EconomicIndicator                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. 홈 페이지 (/)

### 파일 위치
```
frontend/app/page.tsx
```

### 인증
불필요 (Public)

### 컴포넌트 구조
```
page.tsx
├── PortfolioSummary (샘플 데이터)
└── PortfolioStockCard[] (샘플 데이터)
```

### API 호출
현재 샘플 데이터 사용 (실제 API 미연결)

### 데이터베이스 연결
현재 없음 (향후 Stock 모델 연동 예정)

### 데이터 타입
```typescript
interface PortfolioStock {
  symbol: string
  name: string
  shares: number
  avgPrice: number
  currentPrice: number
  value: number
  gain: number
  gainPercent: number
}
```

---

## 2. 로그인 (/login)

### 파일 위치
```
frontend/app/login/page.tsx
```

### 인증
불필요

### 컴포넌트 구조
```
page.tsx
└── Form (username, password)
```

### API 호출
| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/v1/users/jwt/login/` | 로그인 |

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  API: POST /api/v1/users/jwt/login/                        │
│                                                             │
│  Django Model: users.User                                   │
│  ├── 테이블명: users_user                                   │
│  ├── PK: id (AutoField)                                    │
│  └── 인증 필드:                                             │
│      ├── username (CharField, unique)                      │
│      ├── password (암호화 저장)                             │
│      └── is_active (BooleanField)                          │
│                                                             │
│  인증 방식: JWT (Simple JWT)                                │
│  └── 토큰 생성: access + refresh token                      │
└─────────────────────────────────────────────────────────────┘
```

### 서비스
```typescript
// contexts/AuthContext.tsx
const { login } = useAuth()
await login(username, password)
```

### Request/Response
```typescript
// Request
{ username: string, password: string }

// Response
{
  access: string,   // JWT access token
  refresh: string,  // JWT refresh token
  user: User
}
```

---

## 3. 회원가입 (/signup)

### 파일 위치
```
frontend/app/signup/page.tsx
```

### 인증
불필요

### API 호출
| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/v1/users/jwt/signup/` | 회원가입 |

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  API: POST /api/v1/users/jwt/signup/                       │
│                                                             │
│  Django Model: users.User                                   │
│  ├── 테이블명: users_user                                   │
│  └── 생성되는 필드:                                         │
│      ├── username (CharField, unique, max_length=150)      │
│      ├── email (EmailField, unique)                        │
│      ├── nick_name (CharField, max_length=50)              │
│      ├── password (암호화 저장 - make_password)            │
│      ├── date_joined (DateTimeField, auto_now_add)         │
│      ├── is_active (BooleanField, default=True)            │
│      ├── is_staff (BooleanField, default=False)            │
│      └── is_superuser (BooleanField, default=False)        │
│                                                             │
│  제약조건:                                                   │
│  ├── username UNIQUE                                        │
│  └── email UNIQUE                                           │
└─────────────────────────────────────────────────────────────┘
```

### 서비스
```typescript
// contexts/AuthContext.tsx
const { signup } = useAuth()
await signup(username, email, password, password2, nick_name)
```

### Request/Response
```typescript
// Request
{
  username: string,
  email: string,
  password: string,
  password2: string,
  nick_name: string
}

// Response
{ user: User }
```

---

## 4. 대시보드 (/dashboard)

### 파일 위치
```
frontend/app/dashboard/page.tsx
```

### 인증
필수 (Protected)

### 컴포넌트 구조
```
page.tsx
├── 사용자 정보 표시
├── 포트폴리오 링크
├── 주식 검색 링크
└── 관심 종목 링크
```

### API 호출
없음 (AuthContext에서 User 정보 사용)

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  AuthContext에서 JWT 토큰 기반 사용자 정보 사용             │
│                                                             │
│  Django Model: users.User                                   │
│  └── JWT 토큰에서 user_id 추출 후 User 조회                │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 포트폴리오 (/portfolio)

### 파일 위치
```
frontend/app/portfolio/page.tsx
frontend/components/portfolio/
├── PortfolioSummary.tsx
├── PortfolioChart.tsx
├── PortfolioStockCard.tsx
├── PortfolioTable.tsx
└── PortfolioModal.tsx
```

### 인증
필수

### 컴포넌트 구조
```
page.tsx
├── PortfolioSummary ─────── GET /portfolio/summary/
├── PortfolioChart
├── ViewToggle (Grid/Table)
├── PortfolioStockCard[] ─── GET /portfolio/
│   └── Link → /stocks/[symbol]
├── PortfolioTable ───────── GET /portfolio/
└── PortfolioModal ───────── POST /portfolio/
                             PUT /portfolio/{id}/
                             DELETE /portfolio/{id}/
```

### API 호출
| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/v1/users/portfolio/` | 포트폴리오 목록 |
| GET | `/api/v1/users/portfolio/summary/` | 요약 정보 |
| POST | `/api/v1/users/portfolio/` | 종목 추가 |
| PUT | `/api/v1/users/portfolio/{id}/` | 종목 수정 |
| DELETE | `/api/v1/users/portfolio/{id}/` | 종목 삭제 |
| GET | `/api/v1/users/portfolio/symbol/{symbol}/` | 심볼로 조회 |
| GET | `/api/v1/users/portfolio/symbol/{symbol}/status/` | 데이터 수집 상태 |

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  API: GET/POST /api/v1/users/portfolio/                    │
│                                                             │
│  주요 Model: users.Portfolio                                │
│  ├── 테이블명: users_portfolio                              │
│  ├── PK: id (AutoField)                                    │
│  ├── FK: user → users.User (on_delete=CASCADE)             │
│  ├── FK: stock → stocks.Stock (to_field='symbol')          │
│  └── 필드:                                                  │
│      ├── quantity (DecimalField, max_digits=18, decimal=8) │
│      ├── average_price (DecimalField)                      │
│      ├── notes (TextField, optional)                       │
│      ├── created_at (DateTimeField, auto_now_add)          │
│      └── updated_at (DateTimeField, auto_now)              │
│                                                             │
│  제약조건:                                                   │
│  └── unique_together = ['user', 'stock']                   │
│                                                             │
│  연관 Model: stocks.Stock                                   │
│  ├── 테이블명: stocks_stock                                 │
│  ├── PK: symbol (CharField, max_length=10)                 │
│  └── 사용되는 필드:                                         │
│      ├── stock_name (CharField, max_length=200)            │
│      ├── real_time_price (DecimalField)                    │
│      ├── previous_close (DecimalField)                     │
│      ├── open_price (DecimalField)                         │
│      └── volume (BigIntegerField)                          │
│                                                             │
│  계산 필드 (Python @property):                              │
│  ├── total_value = quantity × real_time_price              │
│  ├── total_cost = quantity × average_price                 │
│  ├── profit_loss = total_value - total_cost                │
│  └── profit_loss_percentage = (profit_loss/cost) × 100     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  API: GET /portfolio/symbol/{symbol}/status/               │
│                                                             │
│  데이터 수집 상태 확인 - 여러 모델 조회:                    │
│  ├── stocks.Stock         → stock_exists                   │
│  ├── stocks.DailyPrice    → has_prices, daily_prices count │
│  ├── stocks.WeeklyPrice   → weekly_prices count            │
│  ├── stocks.BalanceSheet  → has_financial                  │
│  ├── stocks.IncomeStatement → income_statements count      │
│  └── stocks.CashFlowStatement → cash_flows count           │
│                                                             │
│  응답 예시:                                                  │
│  {                                                          │
│    "is_complete": true 조건:                                │
│    - stock_exists && has_prices && has_financial           │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

### 서비스
```typescript
// services/portfolio.ts
portfolioService.getPortfolios()
portfolioService.getPortfolioSummary()
portfolioService.createPortfolio(data)
portfolioService.updatePortfolio(id, data)
portfolioService.deletePortfolio(id)
portfolioService.getStockDataStatus(symbol)
```

### 데이터 타입
```typescript
interface Portfolio {
  id: number
  stock_symbol: string
  stock_name: string
  quantity: string
  average_price: string
  current_price: string
  total_value: number
  total_cost: number
  profit_loss: number
  profit_loss_percentage: number
  is_profitable: boolean
  notes?: string
  created_at: string
  updated_at: string
}

interface PortfolioSummary {
  total_stocks: number
  total_value: number
  total_cost: number
  total_profit_loss: number
  total_profit_loss_percentage: number
  is_profitable: boolean
}

interface StockDataStatus {
  symbol: string
  stock_exists: boolean
  has_overview: boolean
  has_prices: boolean
  has_financial: boolean
  is_complete: boolean
  details: {
    daily_prices: number
    weekly_prices: number
    balance_sheets: number
    income_statements: number
    cash_flows: number
  }
}
```

---

## 6. 종목 상세 (/stocks/[symbol])

### 파일 위치
```
frontend/app/stocks/[symbol]/page.tsx
frontend/components/stock/
├── StockChart.tsx
├── OverviewTab.tsx
├── FinancialTab.tsx
└── NewsTab.tsx
```

### 인증
불필요

### 컴포넌트 구조
```
page.tsx
├── StockHeader ──────────── GET /overview/{symbol}/
├── StockChart ───────────── GET /chart/{symbol}/?type=daily&period=1m
├── Tabs
│   ├── OverviewTab ──────── GET /overview/{symbol}/
│   ├── FinancialTab
│   │   ├── BalanceSheet ─── GET /balance-sheet/{symbol}/
│   │   ├── IncomeStatement  GET /income-statement/{symbol}/
│   │   └── CashFlow ─────── GET /cashflow/{symbol}/
│   └── NewsTab ──────────── (뉴스 API)
└── PortfolioNavigation (보유 종목간 이동)
```

### API 호출
| Method | URL | 쿼리 파라미터 | 설명 |
|--------|-----|-------------|------|
| GET | `/api/v1/stocks/api/overview/{symbol}/` | - | 기업 개요 + 실시간 가격 |
| GET | `/api/v1/stocks/api/chart/{symbol}/` | type, period, days | 차트 데이터 |
| GET | `/api/v1/stocks/api/balance-sheet/{symbol}/` | period, limit | 대차대조표 |
| GET | `/api/v1/stocks/api/income-statement/{symbol}/` | period, limit | 손익계산서 |
| GET | `/api/v1/stocks/api/cashflow/{symbol}/` | period, limit | 현금흐름표 |
| GET | `/api/v1/stocks/api/indicators/{symbol}/` | - | 기술적 지표 |

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  API: GET /api/v1/stocks/api/overview/{symbol}/            │
│                                                             │
│  Django Model: stocks.Stock                                 │
│  ├── 테이블명: stocks_stock                                 │
│  ├── PK: symbol (CharField, max_length=10)                 │
│  └── 주요 필드 (60개+):                                     │
│      ├── 기본 정보:                                         │
│      │   ├── stock_name (CharField, 200)                   │
│      │   ├── asset_type (CharField, 50)                    │
│      │   ├── exchange (CharField, 50)                      │
│      │   ├── currency (CharField, 10)                      │
│      │   └── country (CharField, 50)                       │
│      ├── 실시간 가격:                                       │
│      │   ├── real_time_price (DecimalField)                │
│      │   ├── open_price (DecimalField)                     │
│      │   ├── high_price (DecimalField)                     │
│      │   ├── low_price (DecimalField)                      │
│      │   ├── previous_close (DecimalField)                 │
│      │   ├── change (DecimalField)                         │
│      │   └── change_percent (DecimalField)                 │
│      ├── 기업 정보:                                         │
│      │   ├── description (TextField)                       │
│      │   ├── sector (CharField, 100)                       │
│      │   ├── industry (CharField, 100)                     │
│      │   └── full_time_employees (IntegerField)            │
│      └── 재무 비율:                                         │
│          ├── market_capitalization (BigIntegerField)       │
│          ├── pe_ratio (DecimalField)                       │
│          ├── peg_ratio (DecimalField)                      │
│          ├── book_value (DecimalField)                     │
│          ├── dividend_yield (DecimalField)                 │
│          ├── eps (DecimalField)                            │
│          ├── revenue_ttm (BigIntegerField)                 │
│          └── profit_margin (DecimalField)                  │
│                                                             │
│  캐싱: 600초 (overview_cache_key)                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  API: GET /api/v1/stocks/api/chart/{symbol}/               │
│                                                             │
│  Django Model: stocks.DailyPrice / stocks.WeeklyPrice      │
│  ├── 공통 상속: BasePriceData (Abstract Model)             │
│  ├── 테이블명: stocks_dailyprice / stocks_weeklyprice      │
│  └── 필드:                                                  │
│      ├── stock (FK → Stock, to_field='symbol')             │
│      ├── date (DateField)                                  │
│      ├── open_price (DecimalField, max_digits=20, decimal=4)│
│      ├── high_price (DecimalField)                         │
│      ├── low_price (DecimalField)                          │
│      ├── close_price (DecimalField)                        │
│      ├── adjusted_close (DecimalField)                     │
│      ├── volume (BigIntegerField)                          │
│      └── dividend_amount (DecimalField, default=0)         │
│                                                             │
│  제약조건:                                                   │
│  └── unique_together = ['stock', 'date']                   │
│                                                             │
│  인덱스:                                                     │
│  ├── stock_id (FK 인덱스)                                   │
│  └── date (기간 조회 최적화)                                │
│                                                             │
│  쿼리 예시 (period별):                                       │
│  ├── 1d/5d: DailyPrice.filter(date__gte=start_date)        │
│  ├── 1m~1y: DailyPrice.filter(date__gte=start_date)        │
│  └── max: DailyPrice.all() (전체 데이터)                   │
│                                                             │
│  캐싱: 60초 (실시간성 중요)                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  API: GET /api/v1/stocks/api/balance-sheet/{symbol}/       │
│                                                             │
│  Django Model: stocks.BalanceSheet                          │
│  ├── 테이블명: stocks_balancesheet                          │
│  └── 필드:                                                  │
│      ├── stock (FK → Stock, to_field='symbol')             │
│      ├── fiscal_date_ending (DateField)                    │
│      ├── fiscal_year (IntegerField)                        │
│      ├── fiscal_quarter (IntegerField, nullable)           │
│      ├── period_type (CharField: 'annual'|'quarterly')     │
│      ├── reported_currency (CharField, 10)                 │
│      └── 재무 항목 (50개+):                                 │
│          ├── total_assets (DecimalField, 22자리)           │
│          ├── total_current_assets                          │
│          ├── cash_and_equivalents                          │
│          ├── inventory                                     │
│          ├── total_liabilities                             │
│          ├── total_current_liabilities                     │
│          ├── long_term_debt                                │
│          ├── total_shareholder_equity                      │
│          └── ... 기타 항목들                               │
│                                                             │
│  제약조건:                                                   │
│  └── unique_together = ['stock', 'period_type',            │
│                         'fiscal_year', 'fiscal_quarter']   │
│                                                             │
│  캐싱: 3600초 (분기/연간 업데이트)                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  API: GET /api/v1/stocks/api/income-statement/{symbol}/    │
│                                                             │
│  Django Model: stocks.IncomeStatement                       │
│  ├── 테이블명: stocks_incomestatement                       │
│  └── 필드:                                                  │
│      ├── stock (FK → Stock, to_field='symbol')             │
│      ├── fiscal_date_ending, fiscal_year, fiscal_quarter   │
│      ├── period_type ('annual'|'quarterly')                │
│      └── 손익 항목:                                         │
│          ├── total_revenue (DecimalField)                  │
│          ├── gross_profit                                  │
│          ├── operating_income                              │
│          ├── operating_expenses                            │
│          ├── net_income                                    │
│          ├── ebitda                                        │
│          └── ... 기타 항목들                               │
│                                                             │
│  제약조건: unique_together (위와 동일)                      │
│  캐싱: 3600초                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  API: GET /api/v1/stocks/api/cashflow/{symbol}/            │
│                                                             │
│  Django Model: stocks.CashFlowStatement                     │
│  ├── 테이블명: stocks_cashflowstatement                     │
│  └── 필드:                                                  │
│      ├── stock (FK → Stock, to_field='symbol')             │
│      ├── fiscal_date_ending, fiscal_year, fiscal_quarter   │
│      └── 현금흐름 항목:                                     │
│          ├── operating_cashflow                            │
│          ├── payments_for_operating_activities             │
│          ├── capital_expenditures                          │
│          ├── investing_activity                            │
│          ├── financing_activity                            │
│          ├── dividend_payout                               │
│          └── ... 기타 항목들                               │
│                                                             │
│  제약조건: unique_together (위와 동일)                      │
│  캐싱: 3600초                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  API: GET /api/v1/stocks/api/indicators/{symbol}/          │
│                                                             │
│  실시간 계산 (DB 저장 없음):                                │
│  ├── 입력: stocks.DailyPrice (최근 데이터)                 │
│  └── 출력: 기술적 지표 계산 결과                            │
│      ├── RSI (Relative Strength Index)                     │
│      ├── MACD (Moving Average Convergence Divergence)      │
│      ├── Bollinger Bands                                   │
│      ├── SMA (Simple Moving Average)                       │
│      ├── EMA (Exponential Moving Average)                  │
│      ├── Stochastic                                        │
│      ├── OBV (On-Balance Volume)                           │
│      └── ATR (Average True Range)                          │
└─────────────────────────────────────────────────────────────┘
```

### 서비스
```typescript
// services/stock.ts
stockService.getStockQuote(symbol)
stockService.getStockOverview(symbol)
stockService.getChartData(symbol, type, period)
stockService.getBalanceSheet(symbol, period, limit)
stockService.getIncomeStatement(symbol, period, limit)
stockService.getCashFlow(symbol, period, limit)
```

### 데이터 타입
```typescript
interface StockQuote {
  symbol: string
  stock_name: string
  real_time_price: number
  high_price: number
  low_price: number
  open_price: number
  previous_close: number
  volume: number
  change: number
  change_percent: string
  market_capitalization?: number
  pe_ratio?: number
  dividend_yield?: number
  week_52_high?: number
  week_52_low?: number
}

interface ChartData {
  date: string
  open_price: number
  high_price: number
  low_price: number
  close_price: number
  volume: number
}

interface FinancialStatement {
  fiscal_date_ending: string
  fiscal_year: number
  fiscal_quarter?: number
  period_type: 'annual' | 'quarterly'
  // 각 항목별 금액 필드...
}
```

### 차트 기간 옵션
| period | 설명 |
|--------|------|
| 1d | 1일 |
| 5d | 5일 |
| 1m | 1개월 |
| 3m | 3개월 |
| 6m | 6개월 |
| 1y | 1년 |
| 2y | 2년 |
| 5y | 5년 |
| max | 전체 |

---

## 7. 관심종목 (/watchlist)

### 파일 위치
```
frontend/app/watchlist/page.tsx
frontend/components/watchlist/
├── WatchlistCard.tsx
├── WatchlistItemRow.tsx
├── WatchlistModal.tsx
├── AddStockModal.tsx
└── WatchlistErrorBoundary.tsx
```

### 인증
필수

### 컴포넌트 구조
```
page.tsx
├── WatchlistErrorBoundary
│   └── WatchlistPageContent
│       ├── Header + 리스트 생성 버튼
│       ├── WatchlistCard[] ──────── GET /watchlist/
│       │   └── WatchlistItemRow[] ─ GET /watchlist/{id}/stocks/
│       │       └── Link → /stocks/[symbol]
│       ├── WatchlistModal ───────── POST /watchlist/
│       │                            PATCH /watchlist/{id}/
│       │                            DELETE /watchlist/{id}/
│       └── AddStockModal ────────── POST /watchlist/{id}/add-stock/
│                                    PATCH /watchlist/{id}/stocks/{symbol}/
│                                    DELETE /watchlist/{id}/stocks/{symbol}/remove/
```

### API 호출
| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/v1/users/watchlist/` | 리스트 목록 |
| POST | `/api/v1/users/watchlist/` | 리스트 생성 |
| GET | `/api/v1/users/watchlist/{id}/` | 리스트 상세 |
| PATCH | `/api/v1/users/watchlist/{id}/` | 리스트 수정 |
| DELETE | `/api/v1/users/watchlist/{id}/` | 리스트 삭제 |
| GET | `/api/v1/users/watchlist/{id}/stocks/` | 종목 목록 (실시간 가격) |
| POST | `/api/v1/users/watchlist/{id}/add-stock/` | 종목 추가 |
| PATCH | `/api/v1/users/watchlist/{id}/stocks/{symbol}/` | 종목 설정 수정 |
| DELETE | `/api/v1/users/watchlist/{id}/stocks/{symbol}/remove/` | 종목 제거 |
| POST | `/api/v1/users/watchlist/{id}/bulk-add/` | 벌크 추가 |
| POST | `/api/v1/users/watchlist/{id}/bulk-remove/` | 벌크 삭제 |

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  API: GET/POST /api/v1/users/watchlist/                    │
│                                                             │
│  Django Model: users.Watchlist                              │
│  ├── 테이블명: users_watchlist                              │
│  ├── PK: id (AutoField)                                    │
│  ├── FK: user → users.User (on_delete=CASCADE)             │
│  └── 필드:                                                  │
│      ├── name (CharField, max_length=100)                  │
│      ├── description (TextField, blank=True)               │
│      ├── created_at (DateTimeField, auto_now_add)          │
│      └── updated_at (DateTimeField, auto_now)              │
│                                                             │
│  제약조건:                                                   │
│  └── unique_together = ['user', 'name']                    │
│                                                             │
│  계산 필드 (@property):                                     │
│  └── stock_count = watchlist_items.count()                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  API: GET /watchlist/{id}/stocks/                          │
│       POST /watchlist/{id}/add-stock/                      │
│                                                             │
│  Django Model: users.WatchlistItem                          │
│  ├── 테이블명: users_watchlistitem                          │
│  ├── PK: id (AutoField)                                    │
│  ├── FK: watchlist → users.Watchlist (on_delete=CASCADE)   │
│  ├── FK: stock → stocks.Stock (to_field='symbol')          │
│  └── 필드:                                                  │
│      ├── target_entry_price (DecimalField, nullable)       │
│      ├── notes (TextField, blank=True)                     │
│      ├── position_order (IntegerField, default=0)          │
│      └── added_at (DateTimeField, auto_now_add)            │
│                                                             │
│  제약조건:                                                   │
│  └── unique_together = ['watchlist', 'stock']              │
│                                                             │
│  연관 Model: stocks.Stock                                   │
│  └── 실시간 가격 정보 JOIN:                                 │
│      ├── stock_name                                        │
│      ├── real_time_price → current_price                   │
│      ├── change                                            │
│      ├── change_percent                                    │
│      └── previous_close                                    │
│                                                             │
│  계산 필드 (View에서 계산):                                  │
│  ├── distance_from_entry = current - target_entry          │
│  └── is_below_target = current < target_entry              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  트랜잭션 보호 (transaction.atomic):                        │
│  ├── 종목 추가 시 select_for_update() 사용                 │
│  └── 벌크 작업 시 전체 트랜잭션 보장                        │
│                                                             │
│  Rate Limiting:                                              │
│  └── UserRateThrottle: 100 requests/hour                   │
│                                                             │
│  캐싱 (WatchlistCache):                                     │
│  ├── 리스트 목록: 60초                                      │
│  ├── 종목 목록: 30초 (실시간 가격 포함)                     │
│  └── 캐시 무효화: 수정/삭제 시 자동                         │
└─────────────────────────────────────────────────────────────┘
```

### 서비스
```typescript
// services/watchlistService.ts
watchlistService.getWatchlists()
watchlistService.createWatchlist(data)
watchlistService.getWatchlist(id)
watchlistService.updateWatchlist(id, data)
watchlistService.deleteWatchlist(id)
watchlistService.getWatchlistStocks(id)
watchlistService.addStock(id, data)
watchlistService.updateStockSettings(id, symbol, data)
watchlistService.removeStock(id, symbol)
```

### 데이터 타입
```typescript
// types/watchlist.ts

interface Watchlist {
  id: number
  name: string
  description: string
  stock_count: number
  created_at: string
  updated_at: string
}

interface WatchlistItem {
  id: number
  stock_symbol: string
  stock_name: string
  current_price: string
  change: string
  change_percent: string
  previous_close: string
  target_entry_price: string | null
  distance_from_entry: number | null
  is_below_target: boolean | null
  notes: string
  position_order: number
  added_at: string
}

interface AddStockToWatchlistData {
  stock: string  // 종목 심볼
  target_entry_price?: number | null
  notes?: string
}

interface UpdateWatchlistItemData {
  target_entry_price?: number | null
  notes?: string
  position_order?: number
}
```

---

## 8. Market Pulse (/market-pulse)

### 파일 위치
```
frontend/app/market-pulse/page.tsx
frontend/components/market-pulse/
├── FearGreedGauge.tsx
├── YieldCurveChart.tsx
├── EconomicIndicators.tsx
└── GlobalMarketsCard.tsx
```

### 인증
불필요

### 컴포넌트 구조
```
page.tsx
├── SyncButton ───────────── POST /macro/sync/
│                            GET /macro/sync/status/
├── FearGreedGauge ───────── GET /macro/fear-greed/
├── YieldCurveChart ──────── GET /macro/interest-rates/
├── EconomicIndicators ───── GET /macro/inflation/
├── GlobalMarketsCard ────── GET /macro/global-markets/
└── EconomicCalendar ─────── GET /macro/calendar/
```

### API 호출
| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/v1/macro/pulse/` | 전체 대시보드 (통합) |
| GET | `/api/v1/macro/fear-greed/` | 공포/탐욕 지수 |
| GET | `/api/v1/macro/interest-rates/` | 금리/수익률 곡선 |
| GET | `/api/v1/macro/inflation/` | 경제 지표 |
| GET | `/api/v1/macro/global-markets/` | 글로벌 시장 |
| GET | `/api/v1/macro/calendar/?days=7` | 경제 캘린더 |
| POST | `/api/v1/macro/sync/` | 데이터 동기화 시작 |
| GET | `/api/v1/macro/sync/status/` | 동기화 상태 |

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  API: GET /api/v1/macro/*                                  │
│                                                             │
│  Django Model: analysis.EconomicIndicator                   │
│  ├── 테이블명: analysis_economicindicator                   │
│  ├── PK: id (AutoField)                                    │
│  └── 필드:                                                  │
│      ├── indicator_type (CharField, max_length=50)         │
│      │   예: 'GDP', 'CPI', 'UNEMPLOYMENT', 'FED_RATE',     │
│      │       'TREASURY_10Y', 'FEAR_GREED'                  │
│      ├── value (DecimalField, max_digits=20, decimal=4)    │
│      ├── previous_value (DecimalField, nullable)           │
│      ├── change (DecimalField, nullable)                   │
│      ├── change_percent (DecimalField, nullable)           │
│      ├── date (DateField)                                  │
│      ├── source (CharField, max_length=100)                │
│      ├── notes (TextField, blank=True)                     │
│      └── updated_at (DateTimeField, auto_now)              │
│                                                             │
│  제약조건:                                                   │
│  └── unique_together = ['indicator_type', 'date']          │
│                                                             │
│  인덱스:                                                     │
│  ├── indicator_type (타입별 조회)                           │
│  └── date (날짜별 조회)                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  데이터 소스 (Alpha Vantage API):                           │
│  ├── TREASURY_YIELD → 수익률 곡선                          │
│  ├── FEDERAL_FUNDS_RATE → 연준 금리                        │
│  ├── CPI → 소비자물가지수                                  │
│  ├── INFLATION → 인플레이션                                │
│  ├── GDP → 국내총생산                                      │
│  └── UNEMPLOYMENT → 실업률                                 │
│                                                             │
│  Fear & Greed Index:                                        │
│  └── 외부 API 또는 계산 기반 (CNN Money 참조)              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  글로벌 시장 데이터 (stocks.Stock 활용):                    │
│  ├── 주요 지수:                                             │
│  │   ├── SPY (S&P 500 ETF)                                 │
│  │   ├── QQQ (NASDAQ 100 ETF)                              │
│  │   ├── DIA (Dow Jones ETF)                               │
│  │   └── IWM (Russell 2000 ETF)                            │
│  ├── 섹터 ETF:                                              │
│  │   ├── XLK (Technology)                                  │
│  │   ├── XLF (Financials)                                  │
│  │   └── XLE (Energy)                                      │
│  └── 원자재:                                                │
│      ├── GLD (Gold)                                        │
│      ├── USO (Oil)                                         │
│      └── UNG (Natural Gas)                                 │
└─────────────────────────────────────────────────────────────┘
```

### 서비스
```typescript
// services/macroService.ts
macroService.getMarketPulse()
macroService.getFearGreedIndex()
macroService.getInterestRates()
macroService.getInflation()
macroService.getGlobalMarkets()
macroService.getEconomicCalendar(days)
macroService.syncData()
macroService.getSyncStatus()
```

### 데이터 타입
```typescript
// types/macro.ts

interface MarketPulseDashboard {
  fear_greed: FearGreedIndex
  interest_rates: InterestRatesDashboard
  economy: InflationDashboard
  global_markets: GlobalMarketsDashboard
  calendar: EconomicCalendar
  last_updated: string
}

interface FearGreedIndex {
  value: number           // 0-100
  label: string           // "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
  previous_close: number
  change: number
  indicators: FearGreedIndicator[]
}

interface InterestRatesDashboard {
  federal_funds_rate: number
  treasury_yields: TreasuryYield[]
  yield_curve: YieldCurvePoint[]
  is_inverted: boolean
}

interface GlobalMarketsDashboard {
  indices: MarketIndex[]
  sectors: SectorPerformance[]
  commodities: Commodity[]
  forex: ForexRate[]
}
```

---

## 9. 마이페이지 (/mypage)

### 파일 위치
```
frontend/app/mypage/page.tsx
```

### 인증
필수

### 컴포넌트 구조
```
page.tsx
├── 프로필 정보 표시
├── 프로필 수정 폼 ────── PATCH /users/me/
├── 비밀번호 변경 (미구현)
└── 계정 삭제 (미구현)
```

### API 호출
| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/v1/users/me/` | 프로필 조회 |
| PATCH | `/api/v1/users/me/` | 프로필 수정 |

### 데이터베이스 연결
```
┌─────────────────────────────────────────────────────────────┐
│  API: GET/PATCH /api/v1/users/me/                          │
│                                                             │
│  Django Model: users.User                                   │
│  ├── 테이블명: users_user                                   │
│  ├── JWT 토큰에서 user_id 추출                             │
│  └── 조회/수정 가능 필드:                                   │
│      ├── username (읽기 전용)                               │
│      ├── nick_name (수정 가능)                              │
│      ├── email (수정 가능)                                  │
│      ├── date_joined (읽기 전용)                            │
│      ├── is_superuser (읽기 전용)                           │
│      └── is_staff (읽기 전용)                               │
└─────────────────────────────────────────────────────────────┘
```

### 데이터 타입
```typescript
interface User {
  id: number
  user_name: string
  nick_name: string
  email: string
  date_joined: string
  is_superuser: boolean
  is_staff: boolean
}
```

---

## 10. Backend URL 요약

### 인증 API (`/api/v1/users/jwt/`)
```
POST   /signup/           회원가입
POST   /login/            로그인
POST   /logout/           로그아웃
POST   /refresh/          토큰 갱신
GET    /verify/           토큰 검증
POST   /change-password/  비밀번호 변경
PATCH  /profile/          프로필 수정
```

### 사용자 API (`/api/v1/users/`)
```
GET    /me/               내 정보 조회
PATCH  /me/               내 정보 수정
```

### 포트폴리오 API (`/api/v1/users/portfolio/`)
```
GET    /                  목록 조회
POST   /                  생성
GET    /summary/          요약 정보
GET    /{id}/             상세 조회
PUT    /{id}/             수정
DELETE /{id}/             삭제
GET    /symbol/{symbol}/  심볼로 조회
GET    /symbol/{symbol}/status/  데이터 상태
```

### 관심종목 API (`/api/v1/users/watchlist/`)
```
GET    /                  리스트 목록
POST   /                  리스트 생성
GET    /{id}/             리스트 상세
PATCH  /{id}/             리스트 수정
DELETE /{id}/             리스트 삭제
GET    /{id}/stocks/      종목 목록
POST   /{id}/add-stock/   종목 추가
PATCH  /{id}/stocks/{symbol}/         종목 수정
DELETE /{id}/stocks/{symbol}/remove/  종목 제거
POST   /{id}/bulk-add/    벌크 추가
POST   /{id}/bulk-remove/ 벌크 삭제
```

### 주식 API (`/api/v1/stocks/api/`)
```
GET    /overview/{symbol}/         기업 개요
GET    /chart/{symbol}/            차트 데이터
GET    /balance-sheet/{symbol}/    대차대조표
GET    /income-statement/{symbol}/ 손익계산서
GET    /cashflow/{symbol}/         현금흐름표
GET    /indicators/{symbol}/       기술적 지표
GET    /signal/{symbol}/           매매 신호
GET    /search/symbols/            종목 검색
GET    /search/validate/{symbol}/  심볼 검증
GET    /search/popular/            인기 종목
```

### 거시경제 API (`/api/v1/macro/`)
```
GET    /pulse/            전체 대시보드
GET    /fear-greed/       공포/탐욕 지수
GET    /interest-rates/   금리/수익률
GET    /inflation/        경제 지표
GET    /global-markets/   글로벌 시장
GET    /calendar/         경제 캘린더
POST   /sync/             데이터 동기화
GET    /sync/status/      동기화 상태
```

---

## 11. 데이터베이스 모델 관계도

### 전체 모델 ERD
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        STOCKS 앱 (핵심 데이터)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────┐                       │
│  │              Stock (PK: symbol)              │                       │
│  │  ─────────────────────────────────────────  │                       │
│  │  symbol: CharField(10) [PK]                 │                       │
│  │  stock_name: CharField(200)                 │                       │
│  │  asset_type: CharField(50)                  │                       │
│  │  exchange: CharField(50)                    │                       │
│  │  currency: CharField(10)                    │                       │
│  │  country: CharField(50)                     │                       │
│  │  real_time_price: DecimalField              │                       │
│  │  open_price, high_price, low_price          │                       │
│  │  previous_close: DecimalField               │                       │
│  │  change, change_percent: DecimalField       │                       │
│  │  volume: BigIntegerField                    │                       │
│  │  market_capitalization: BigIntegerField     │                       │
│  │  pe_ratio, peg_ratio, eps: DecimalField     │                       │
│  │  sector, industry: CharField                │                       │
│  │  description: TextField                     │                       │
│  │  ... (60개+ 필드)                           │                       │
│  └───────────────────┬─────────────────────────┘                       │
│                      │                                                  │
│         ┌────────────┼────────────┬────────────┐                       │
│         │            │            │            │                       │
│         ▼            ▼            ▼            ▼                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │ DailyPrice  │ │ WeeklyPrice │ │BalanceSheet │ │IncomeStmt   │      │
│  │─────────────│ │─────────────│ │─────────────│ │─────────────│      │
│  │stock(FK)    │ │stock(FK)    │ │stock(FK)    │ │stock(FK)    │      │
│  │date: Date   │ │date: Date   │ │fiscal_date  │ │fiscal_date  │      │
│  │open_price   │ │open_price   │ │fiscal_year  │ │fiscal_year  │      │
│  │high_price   │ │high_price   │ │period_type  │ │period_type  │      │
│  │low_price    │ │low_price    │ │total_assets │ │total_revenue│      │
│  │close_price  │ │close_price  │ │total_liab   │ │gross_profit │      │
│  │volume       │ │volume       │ │shareholder  │ │net_income   │      │
│  │             │ │             │ │equity       │ │ebitda       │      │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘      │
│         │                                │                             │
│         │  ┌─────────────┐              │                             │
│         │  │CashFlowStmt │              │                             │
│         │  │─────────────│              │                             │
│         │  │stock(FK)    │              │                             │
│         └──│fiscal_date  │──────────────┘                             │
│            │operating_cf │                                             │
│            │investing_cf │                                             │
│            │financing_cf │                                             │
│            │dividend_pay │                                             │
│            └─────────────┘                                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        USERS 앱 (사용자 데이터)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────┐                       │
│  │                 User (PK: id)                │                       │
│  │  ─────────────────────────────────────────  │                       │
│  │  id: AutoField [PK]                         │                       │
│  │  username: CharField(150) [UNIQUE]          │                       │
│  │  email: EmailField [UNIQUE]                 │                       │
│  │  nick_name: CharField(50)                   │                       │
│  │  password: CharField (암호화)               │                       │
│  │  date_joined: DateTimeField                 │                       │
│  │  is_active, is_staff, is_superuser          │                       │
│  └───────────────────┬─────────────────────────┘                       │
│                      │                                                  │
│         ┌────────────┴────────────┐                                    │
│         │                         │                                    │
│         ▼                         ▼                                    │
│  ┌─────────────────────┐   ┌─────────────────────┐                     │
│  │     Portfolio       │   │     Watchlist       │                     │
│  │─────────────────────│   │─────────────────────│                     │
│  │id: AutoField [PK]   │   │id: AutoField [PK]   │                     │
│  │user(FK) → User      │   │user(FK) → User      │                     │
│  │stock(FK) → Stock    │   │name: CharField(100) │                     │
│  │quantity: Decimal    │   │description: Text    │                     │
│  │average_price: Dec   │   │created_at, updated  │                     │
│  │notes: TextField     │   │                     │                     │
│  │created_at, updated  │   │ unique_together:    │                     │
│  │                     │   │ (user, name)        │                     │
│  │ unique_together:    │   └──────────┬──────────┘                     │
│  │ (user, stock)       │              │                                │
│  └─────────────────────┘              │                                │
│                                       ▼                                │
│                            ┌─────────────────────┐                     │
│                            │   WatchlistItem     │                     │
│                            │─────────────────────│                     │
│                            │id: AutoField [PK]   │                     │
│                            │watchlist(FK)        │                     │
│                            │stock(FK) → Stock    │                     │
│                            │target_entry_price   │                     │
│                            │notes: TextField     │                     │
│                            │position_order: Int  │                     │
│                            │added_at: DateTime   │                     │
│                            │                     │                     │
│                            │ unique_together:    │                     │
│                            │ (watchlist, stock)  │                     │
│                            └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       ANALYSIS 앱 (분석 데이터)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────┐                       │
│  │          EconomicIndicator (PK: id)          │                       │
│  │  ─────────────────────────────────────────  │                       │
│  │  id: AutoField [PK]                         │                       │
│  │  indicator_type: CharField(50)              │                       │
│  │    - 'GDP', 'CPI', 'UNEMPLOYMENT'           │                       │
│  │    - 'FED_RATE', 'TREASURY_10Y'             │                       │
│  │    - 'FEAR_GREED'                           │                       │
│  │  value: DecimalField(20,4)                  │                       │
│  │  previous_value: DecimalField (nullable)    │                       │
│  │  change, change_percent: DecimalField       │                       │
│  │  date: DateField                            │                       │
│  │  source: CharField(100)                     │                       │
│  │  notes: TextField                           │                       │
│  │  updated_at: DateTimeField                  │                       │
│  │                                             │                       │
│  │  unique_together: (indicator_type, date)    │                       │
│  │  인덱스: indicator_type, date               │                       │
│  └─────────────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         NEWS 앱 (뉴스 데이터)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────┐                       │
│  │            NewsArticle (PK: id)              │                       │
│  │  ─────────────────────────────────────────  │                       │
│  │  id: AutoField [PK]                         │                       │
│  │  title: CharField(500)                      │                       │
│  │  summary: TextField                         │                       │
│  │  content: TextField (optional)              │                       │
│  │  url: URLField [UNIQUE]                     │                       │
│  │  source: CharField(200)                     │                       │
│  │  published_at: DateTimeField                │                       │
│  │  sentiment_score: DecimalField(-1 to 1)     │                       │
│  │  sentiment_label: CharField                 │                       │
│  │    - 'POSITIVE', 'NEGATIVE', 'NEUTRAL'      │                       │
│  │  topics: JSONField                          │                       │
│  │  related_stocks: M2M → Stock                │                       │
│  └───────────────────┬─────────────────────────┘                       │
│                      │                                                  │
│         ┌────────────┴────────────┐                                    │
│         │                         │                                    │
│         ▼                         ▼                                    │
│  ┌─────────────────────┐   ┌─────────────────────┐                     │
│  │    NewsEntity       │   │  SentimentHistory   │                     │
│  │─────────────────────│   │─────────────────────│                     │
│  │id: AutoField [PK]   │   │id: AutoField [PK]   │                     │
│  │article(FK)          │   │stock(FK) → Stock    │                     │
│  │entity_type: Char    │   │date: DateField      │                     │
│  │entity_value: Char   │   │avg_sentiment: Dec   │                     │
│  │start_pos, end_pos   │   │article_count: Int   │                     │
│  │relevance_score: Dec │   │positive/neutral/neg │                     │
│  └─────────────────────┘   └─────────────────────┘                     │
│                                                                         │
│  ┌─────────────────────────────────────────────┐                       │
│  │          EntityHighlight (PK: id)            │                       │
│  │  ─────────────────────────────────────────  │                       │
│  │  entity(FK) → NewsEntity                    │                       │
│  │  highlight_text: CharField                  │                       │
│  │  sentiment_contribution: DecimalField       │                       │
│  └─────────────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 모델 간 관계 요약
```
┌──────────────────────────────────────────────────────────────┐
│                     모델 관계 요약                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Stock (중심 모델)                                           │
│  ├── 1:N → DailyPrice                                        │
│  ├── 1:N → WeeklyPrice                                       │
│  ├── 1:N → BalanceSheet                                      │
│  ├── 1:N → IncomeStatement                                   │
│  ├── 1:N → CashFlowStatement                                 │
│  ├── 1:N → Portfolio                                         │
│  ├── 1:N → WatchlistItem                                     │
│  ├── 1:N → SentimentHistory                                  │
│  └── M:N → NewsArticle (related_stocks)                      │
│                                                              │
│  User (사용자 모델)                                          │
│  ├── 1:N → Portfolio                                         │
│  └── 1:N → Watchlist                                         │
│                                                              │
│  Watchlist                                                   │
│  └── 1:N → WatchlistItem                                     │
│                                                              │
│  NewsArticle                                                 │
│  ├── 1:N → NewsEntity                                        │
│  │         └── 1:N → EntityHighlight                         │
│  └── M:N → Stock                                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 인덱스 전략
```
┌──────────────────────────────────────────────────────────────┐
│                    인덱스 설정 가이드                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  시계열 데이터 (DailyPrice, WeeklyPrice):                   │
│  ├── stock_id + date (복합 인덱스, 기간 조회용)             │
│  └── date (단일 인덱스, 날짜 필터용)                        │
│                                                              │
│  재무제표 (BalanceSheet, IncomeStatement, CashFlow):        │
│  ├── stock_id + period_type + fiscal_year (복합)           │
│  └── fiscal_date_ending (날짜 정렬용)                       │
│                                                              │
│  사용자 데이터 (Portfolio, Watchlist):                       │
│  ├── user_id (사용자별 조회)                                │
│  └── stock_id (종목별 조회)                                 │
│                                                              │
│  뉴스 데이터 (NewsArticle):                                  │
│  ├── published_at (최신순 정렬)                             │
│  └── sentiment_score (감성 분석 필터)                       │
│                                                              │
│  경제 지표 (EconomicIndicator):                              │
│  ├── indicator_type (지표 타입별)                           │
│  └── date (날짜별 조회)                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 서비스 파일 매핑

| 서비스 파일 | 담당 도메인 | 타입 파일 | DB 모델 |
|------------|-----------|----------|--------|
| `services/portfolio.ts` | 포트폴리오 | (inline) | Portfolio, Stock |
| `services/watchlistService.ts` | 관심종목 | `types/watchlist.ts` | Watchlist, WatchlistItem, Stock |
| `services/stock.ts` | 주식 데이터 | (inline) | Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement |
| `services/macroService.ts` | 거시경제 | `types/macro.ts` | EconomicIndicator, Stock |
| `services/newsService.ts` | 뉴스 | `types/news.ts` | NewsArticle, NewsEntity, SentimentHistory |
| `contexts/AuthContext.tsx` | 인증 | (inline) | User |

---

## 데이터 흐름 다이어그램

### 포트폴리오 추가 흐름
```
[PortfolioModal]
       │
       ▼ portfolioService.createPortfolio()
[POST /api/v1/users/portfolio/]
       │
       ▼ Django View
┌──────────────────────────────────────────────────────┐
│ 1. User 인증 확인 (JWT)                              │
│ 2. Stock 존재 확인 또는 생성                         │
│    └── Stock.objects.get_or_create(symbol=symbol)   │
│ 3. Portfolio 생성                                    │
│    └── Portfolio.objects.create(user, stock, ...)   │
│ 4. 백그라운드 데이터 수집 시작 (threading)           │
│    └── Alpha Vantage API 호출                       │
│        ├── DailyPrice 저장                          │
│        ├── WeeklyPrice 저장                         │
│        └── Financial Statements 저장               │
└──────────────────────────────────────────────────────┘
       │
       ▼ Response: Portfolio (즉시 반환)
[Response: Portfolio]
       │
       ▼ 10초 간격 폴링
[GET /api/v1/users/portfolio/symbol/{symbol}/status/]
       │
       ▼ is_complete === true
[UI 업데이트]
```

### 종목 상세 조회 흐름
```
[/stocks/[symbol] 접속]
       │
       ▼ 병렬 호출
┌──────┴──────┐
▼             ▼
[overview]  [chart]
       │
       ▼ Django View
┌──────────────────────────────────────────────────────┐
│ Overview:                                            │
│ └── Stock.objects.get(symbol=symbol.upper())        │
│                                                      │
│ Chart:                                               │
│ └── DailyPrice.objects.filter(                      │
│         stock__symbol=symbol,                        │
│         date__gte=start_date                         │
│     ).order_by('date')                              │
└──────────────────────────────────────────────────────┘
       │
       ▼
[기본 정보 표시]
       │
       ▼ 탭 선택 시
[재무제표 API 호출]
       │
       ▼ Django View
┌──────────────────────────────────────────────────────┐
│ BalanceSheet.objects.filter(                         │
│     stock__symbol=symbol,                            │
│     period_type=period  # 'annual' or 'quarterly'   │
│ ).order_by('-fiscal_date_ending')[:limit]           │
└──────────────────────────────────────────────────────┘
```

### 관심종목 추가 흐름
```
[AddStockModal]
       │
       ▼ watchlistService.addStock()
[POST /api/v1/users/watchlist/{id}/add-stock/]
       │
       ▼ Django View (transaction.atomic)
┌──────────────────────────────────────────────────────┐
│ 1. Watchlist 조회 (select_for_update - 락)          │
│    └── Watchlist.objects.select_for_update()        │
│           .get(id=id, user=request.user)            │
│                                                      │
│ 2. Stock 존재 확인                                   │
│    └── Stock.objects.get(symbol=symbol.upper())     │
│                                                      │
│ 3. 중복 체크                                         │
│    └── WatchlistItem.objects.filter(                │
│            watchlist=watchlist, stock=stock         │
│        ).exists()                                    │
│                                                      │
│ 4. WatchlistItem 생성                                │
│    └── WatchlistItem.objects.create(                │
│            watchlist, stock, target_entry_price,    │
│            notes, position_order                     │
│        )                                             │
│                                                      │
│ 5. 캐시 무효화                                       │
│    └── WatchlistCache.invalidate_stocks(id)         │
└──────────────────────────────────────────────────────┘
       │
       ▼ Response: WatchlistItem
[UI 업데이트 - Optimistic Update 적용]
```

---

*최종 업데이트: 2025-12-10*
