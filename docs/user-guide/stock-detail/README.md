# Stock Detail (종목 상세)

> 개별 종목 심층 분석 및 차트 시각화

## 📋 상태

**개발 중 (In Progress)**

이 페이지는 현재 개발 진행 중입니다. 완성되면 다음 내용이 포함될 예정입니다:

---

## 현재 구현된 기능

### 1. 차트 데이터

- **OHLCV 차트**: 일봉/주봉 데이터
- **기술적 지표**:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - 이동평균선 (MA)

**API 엔드포인트:**
```bash
GET /api/v1/stocks/api/chart/<symbol>/        # 차트 데이터
GET /api/v1/stocks/api/indicators/<symbol>/   # 기술적 지표
```

### 2. 기업 개요

- **회사 정보**: 섹터, 산업, 시가총액
- **주요 지표**: P/E, P/B, EPS, 배당수익률

**API 엔드포인트:**
```bash
GET /api/v1/stocks/api/overview/<symbol>/     # 기업 개요
```

### 3. 재무제표

- **대차대조표** (Balance Sheet)
- **손익계산서** (Income Statement)
- **현금흐름표** (Cash Flow Statement)
- **분기별/연간** 데이터 제공

**API 엔드포인트:**
```bash
GET /api/v1/stocks/api/balance-sheet/<symbol>/    # 재무상태표
GET /api/v1/stocks/api/income-statement/<symbol>/ # 손익계산서
GET /api/v1/stocks/api/cashflow/<symbol>/         # 현금흐름표
```

### 코드 위치

- **Backend**:
  - Models: `stocks/models.py`
  - Views: `stocks/views.py`
  - Services: `stocks/services/alpha_vantage_client.py`
- **Frontend**:
  - Page: `frontend/app/stocks/[symbol]/page.tsx`
  - Components: `frontend/components/stock/`
  - Hooks: `frontend/hooks/useStockData.ts`

---

## 데이터베이스 스키마

### stocks 앱

**Stock (종목 기본 정보)**
```python
class Stock(models.Model):
    symbol = models.CharField(max_length=10, primary_key=True, db_index=True)
    name = models.CharField(max_length=255)
    exchange = models.CharField(max_length=50, null=True)  # NYSE, NASDAQ 등
    sector = models.CharField(max_length=100, null=True)
    industry = models.CharField(max_length=100, null=True)
    market_cap = models.BigIntegerField(null=True)
    description = models.TextField(blank=True)

    # 주요 지표
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    pb_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    eps = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    dividend_yield = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**DailyPrice (일봉 데이터)**
```python
class DailyPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='daily_prices')
    date = models.DateField(db_index=True)
    open = models.DecimalField(max_digits=12, decimal_places=4)
    high = models.DecimalField(max_digits=12, decimal_places=4)
    low = models.DecimalField(max_digits=12, decimal_places=4)
    close = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField()
    adjusted_close = models.DecimalField(max_digits=12, decimal_places=4, null=True)

    class Meta:
        unique_together = [['stock', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['stock', '-date']),  # 종목별 최신순 조회
        ]
```

**WeeklyPrice (주봉 데이터)**
```python
class WeeklyPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='weekly_prices')
    date = models.DateField(db_index=True)
    open = models.DecimalField(max_digits=12, decimal_places=4)
    high = models.DecimalField(max_digits=12, decimal_places=4)
    low = models.DecimalField(max_digits=12, decimal_places=4)
    close = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField()
    adjusted_close = models.DecimalField(max_digits=12, decimal_places=4, null=True)

    class Meta:
        unique_together = [['stock', 'date']]
        ordering = ['-date']
```

**BalanceSheet (재무상태표)**
```python
class BalanceSheet(models.Model):
    PERIOD_TYPES = [
        ('annual', 'Annual'),
        ('quarterly', 'Quarterly'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='balance_sheets')
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    fiscal_year = models.IntegerField()
    fiscal_quarter = models.IntegerField(null=True)  # 분기 (1-4)

    # 자산
    total_assets = models.BigIntegerField(null=True)
    current_assets = models.BigIntegerField(null=True)
    cash_and_equivalents = models.BigIntegerField(null=True)
    inventory = models.BigIntegerField(null=True)

    # 부채
    total_liabilities = models.BigIntegerField(null=True)
    current_liabilities = models.BigIntegerField(null=True)
    long_term_debt = models.BigIntegerField(null=True)

    # 자본
    total_equity = models.BigIntegerField(null=True)
    retained_earnings = models.BigIntegerField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['stock', 'period_type', 'fiscal_year', 'fiscal_quarter']]
        ordering = ['-fiscal_year', '-fiscal_quarter']
```

**IncomeStatement (손익계산서)**
```python
class IncomeStatement(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='income_statements')
    period_type = models.CharField(max_length=10, choices=BalanceSheet.PERIOD_TYPES)
    fiscal_year = models.IntegerField()
    fiscal_quarter = models.IntegerField(null=True)

    # 매출
    revenue = models.BigIntegerField(null=True)
    cost_of_revenue = models.BigIntegerField(null=True)
    gross_profit = models.BigIntegerField(null=True)

    # 영업
    operating_expenses = models.BigIntegerField(null=True)
    operating_income = models.BigIntegerField(null=True)

    # 순이익
    net_income = models.BigIntegerField(null=True)
    eps = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ebitda = models.BigIntegerField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['stock', 'period_type', 'fiscal_year', 'fiscal_quarter']]
        ordering = ['-fiscal_year', '-fiscal_quarter']
```

**CashFlowStatement (현금흐름표)**
```python
class CashFlowStatement(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='cash_flows')
    period_type = models.CharField(max_length=10, choices=BalanceSheet.PERIOD_TYPES)
    fiscal_year = models.IntegerField()
    fiscal_quarter = models.IntegerField(null=True)

    # 영업활동
    operating_cash_flow = models.BigIntegerField(null=True)
    capital_expenditures = models.BigIntegerField(null=True)
    free_cash_flow = models.BigIntegerField(null=True)  # OCF - CapEx

    # 투자활동
    investing_cash_flow = models.BigIntegerField(null=True)

    # 재무활동
    financing_cash_flow = models.BigIntegerField(null=True)
    dividends_paid = models.BigIntegerField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['stock', 'period_type', 'fiscal_year', 'fiscal_quarter']]
        ordering = ['-fiscal_year', '-fiscal_quarter']
```

### 모델 관계

```
Stock (PK: symbol)
  │
  ├─── (1:N) DailyPrice
  │          └─ unique_together: (stock, date)
  │
  ├─── (1:N) WeeklyPrice
  │          └─ unique_together: (stock, date)
  │
  ├─── (1:N) BalanceSheet
  │          └─ unique_together: (stock, period_type, fiscal_year, fiscal_quarter)
  │
  ├─── (1:N) IncomeStatement
  │          └─ unique_together: (stock, period_type, fiscal_year, fiscal_quarter)
  │
  └─── (1:N) CashFlowStatement
             └─ unique_together: (stock, period_type, fiscal_year, fiscal_quarter)
```

### 인덱스 전략

1. **종목 조회** (가장 빈번):
   - `Stock`: `symbol` PK (자동 인덱스)

2. **차트 데이터 조회**:
   - `DailyPrice`: `(stock, -date)` 복합 인덱스 (최신순)
   - 예: `DailyPrice.objects.filter(stock='AAPL').order_by('-date')[:100]`

3. **재무제표 조회**:
   - `BalanceSheet`, `IncomeStatement`, `CashFlowStatement`
   - `stock` 외래키 자동 인덱스
   - `unique_together` 제약으로 중복 방지

4. **기간별 조회**:
   - `DailyPrice`, `WeeklyPrice`: `date` 인덱스

---

## 투자 지식

### 기술적 지표 해석

**RSI (Relative Strength Index)**
- **범위**: 0~100
- **70 이상**: 과매수 (매도 고려)
- **30 이하**: 과매도 (매수 고려)

**MACD**
- **골든 크로스**: MACD선이 시그널선 상향 돌파 → 매수 신호
- **데드 크로스**: MACD선이 시그널선 하향 돌파 → 매도 신호

**Bollinger Bands**
- **상단 밴드 돌파**: 강한 상승 모멘텀 (단, 과매수 주의)
- **하단 밴드 접촉**: 과매도 구간 (반등 기회)

### 재무제표 분석

**핵심 지표**:
- **ROE** (자기자본이익률): 15% 이상 우수
- **부채비율**: 업종별 차이 있으나 100% 이하 안정
- **영업현금흐름**: 당기순이익보다 높으면 양호

---

## 개발 예정 기능

- [ ] **실시간 차트**: WebSocket 기반 실시간 가격 업데이트
- [ ] **뉴스 통합**: 종목 관련 최신 뉴스
- [ ] **공매도 데이터**: 공매도 잔고 추이
- [ ] **기관/외국인 수급**: 주체별 매매 동향
- [ ] **유사 종목 추천**: 섹터 내 유사 기업 비교

자세한 내용은 추후 업데이트됩니다.
