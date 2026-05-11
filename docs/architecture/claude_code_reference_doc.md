# Stock-Vis 데이터 아키텍처 마스터 참고 문서

> **이 문서는 Claude Code가 각 PR 작업 시 참고하는 문서입니다.**
> **이 문서를 직접 수정하지 마세요.**

---

## 1. 프로젝트 컨텍스트

- Django REST Framework 백엔드, PostgreSQL DB
- 기존 앱: stocks/, users/, macro/, thesis/, graph/, rag_analysis/
- 신규 앱 3개 추가: metrics/, validation/, chainsight/
- 기존 코드 수정 최소화 원칙 (SP500Constituent 마이그레이션 1건만)

## 2. 4-Layer 아키텍처

```
Layer 1: Source of Truth (기존 — 수정 안 함)
  stocks.Stock, DailyPrice, WeeklyPrice
  stocks.BalanceSheet, IncomeStatement, CashFlowStatement
  stocks.StockNews, SP500Constituent, PipelineLog
  macro.EconomicIndicator, IndicatorValue, MarketIndex 등

Layer 2: Shared Derived (신규 metrics/)
  MetricDefinition, CompanyMetricSnapshot
  PeerListCache, IndustryMetricBenchmark, PeerMetricBenchmark
  BatchJobRun

Layer 3a: 1차 검증 (신규 validation/)
  CompanyMetricLatest, CompanyBenchmarkDelta
  CategoryScore, ValidationNewsSummary

Layer 3b: Chain Sight (신규 chainsight/)
  CompanySensitivityProfile, CompanyGrowthStage, CompanyCapitalDNA
  CompanyInsiderSignal, CompanyRevenueStructure, CompanyNarrativeTag
  CompanyEventReaction, CompanyChainProfile, ChainNewsEvent

Layer 4: Graph Layer (PostgreSQL + AGE, backend-swappable via GraphRepository)
  CompanyChainProfile → 그래프 노드 속성 투영 (AGE MVP, 추후 Neo4j 전환 가능)
```

## 3. 공통 컨벤션

- 모든 모델은 `created_at = models.DateTimeField(auto_now_add=True)` 포함
- 갱신 가능 모델은 `updated_at = models.DateTimeField(auto_now=True)` 추가
- 배치 계산 모델은 `calculated_at = models.DateTimeField(auto_now=True)` 사용 (auto_now_add 아님 — 재계산 시 갱신 필요)
- FK는 `to_field='symbol'` 사용 (Stock PK가 symbol CharField)
- JSONB는 `models.JSONField(default=dict)` 또는 `default=list` 사용
- **문자열 배열은 `ArrayField(models.CharField(max_length=N), default=list)` 사용** (JSONField가 아닌 PostgreSQL ArrayField로 통일 — `__overlap`, `__contains` 네이티브 쿼리 지원)
- db*table 네이밍: `{앱명}*{모델\_snake_case}`(예:`metrics_metric_definition`)
- 인덱스는 실제 쿼리 패턴 기반으로 최소한만
- symbol 참조는 `models.ForeignKey('stocks.Stock', on_delete=models.CASCADE, to_field='symbol')`
- metric_code 참조는 `models.ForeignKey('metrics.MetricDefinition', on_delete=models.CASCADE)`
- 모든 모델 파일은 `from django.db import models` import 포함 (ArrayField 사용 시 `from django.contrib.postgres.fields import ArrayField` 추가)

## 4. 기존 모델 주요 참조 정보

### stocks.Stock (PK = symbol CharField)

- symbol, stock_name, exchange, sector, industry
- market_capitalization, beta, pe_ratio, shares_outstanding
- 실시간 가격: real_time_price, change, change_percent, volume

### stocks.BalanceSheet (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)

- total_assets, total_current_assets, cash_and_cash_equivalents_at_carrying_value
- inventory, current_net_receivables
- total_liabilities, total_current_liabilities, short_term_debt, long_term_debt
- total_shareholder_equity, common_stock_shares_outstanding, treasury_stock

### stocks.IncomeStatement (같은 unique 구조)

- total_revenue, gross_profit, cost_of_revenue, operating_income
- selling_general_and_administrative, research_and_development
- interest_expense, net_income, ebitda
- depreciation_and_amortization

### stocks.CashFlowStatement (같은 unique 구조)

- operating_cashflow, capital_expenditures
- payments_for_repurchase_of_common_stock, dividend_payout
- proceeds_from_issuance_of_common_stock
- change_in_receivables, change_in_inventory
- net_income (현금흐름표 내 순이익)

### stocks.SP500Constituent

- symbol (unique), company_name, sector, sub_sector
- is_active, created_at, updated_at

### stocks.StockNews

- stock (FK), symbol, headline, summary, source, url, published_at
- sector, industry, sentiment

---

## 5. MetricDefinition 전체 지표 사전 (34개)

### profitability (5개)

| metric_code      | display_name   | display_name_en            | unit  | higher_is_better | formula                   |
| ---------------- | -------------- | -------------------------- | ----- | ---------------- | ------------------------- |
| gross_margin     | 매출총이익률   | Gross Margin               | ratio | true             | grossProfit / revenue     |
| operating_margin | 영업이익률     | Operating Margin           | ratio | true             | operatingIncome / revenue |
| net_margin       | 순이익률       | Net Margin                 | ratio | true             | netIncome / revenue       |
| roe              | 자기자본이익률 | Return on Equity           | ratio | true             | netIncome / equity        |
| roic             | 투하자본이익률 | Return on Invested Capital | ratio | true             | NOPAT / investedCapital   |

### growth (4개)

| metric_code             | display_name      | display_name_en            | unit  | higher_is_better | formula                          |
| ----------------------- | ----------------- | -------------------------- | ----- | ---------------- | -------------------------------- |
| revenue_growth_yoy      | 매출 성장률 (YoY) | Revenue Growth YoY         | ratio | true             | (rev_t - rev_t1) / abs(rev_t1)   |
| operating_income_growth | 영업이익 성장률   | Operating Income Growth    | ratio | true             | (op_t - op_t1) / abs(op_t1)      |
| fcf_growth_yoy          | FCF 성장률        | FCF Growth YoY             | ratio | true             | (fcf_t - fcf_t1) / abs(fcf_t1)   |
| rev_growth_vs_industry  | 매출성장 vs 업종  | Revenue Growth vs Industry | ratio | true             | company_growth - industry_median |

### financial_structure (6개)

| metric_code         | display_name   | display_name_en    | unit  | higher_is_better | formula                                 |
| ------------------- | -------------- | ------------------ | ----- | ---------------- | --------------------------------------- |
| debt_to_equity      | 부채비율       | Debt to Equity     | ratio | false            | totalDebt / equity                      |
| current_ratio       | 유동비율       | Current Ratio      | ratio | true             | currentAssets / currentLiabilities      |
| interest_coverage   | 이자보상배율   | Interest Coverage  | ratio | true             | operatingIncome / interestExpense       |
| net_debt_to_ebitda  | 순부채/EBITDA  | Net Debt to EBITDA | ratio | false            | (totalDebt - cash) / EBITDA             |
| cash_runway_years   | 현금 소진 연수 | Cash Runway        | years | true             | cash / abs(annualCashBurn), 흑자면 null |
| short_term_debt_pct | 단기부채 비중  | Short Term Debt %  | pct   | false            | shortTermDebt / totalDebt               |

### cash_flow_quality (6개)

| metric_code         | display_name      | display_name_en   | unit  | higher_is_better | formula                                 |
| ------------------- | ----------------- | ----------------- | ----- | ---------------- | --------------------------------------- |
| fcf_margin          | 잉여현금흐름 마진 | FCF Margin        | ratio | true             | FCF / revenue                           |
| ocf_to_net_income   | 영업CF/순이익     | OCF to Net Income | ratio | true             | operatingCF / netIncome                 |
| capex_to_ocf        | Capex/영업CF      | Capex to OCF      | ratio | false            | capex / operatingCF                     |
| accruals_ratio      | 발생액 비율       | Accruals Ratio    | ratio | false            | (netIncome - operatingCF) / totalAssets |
| fcf_conversion      | FCF 전환율        | FCF Conversion    | ratio | true             | FCF / netIncome                         |
| cash_from_ops_trend | 영업CF 추세 (3년) | OCF 3Y Trend      | ratio | true             | 3년 영업CF CAGR                         |

### operational_efficiency (6개)

| metric_code               | display_name         | display_name_en           | unit  | higher_is_better | formula                         |
| ------------------------- | -------------------- | ------------------------- | ----- | ---------------- | ------------------------------- |
| dso                       | 매출채권 회전일수    | Days Sales Outstanding    | days  | false            | (AR / revenue) × 365            |
| ar_to_revenue             | AR/매출 비율         | AR to Revenue             | ratio | false            | accountsReceivable / revenue    |
| inventory_turnover_days   | 재고자산 회전일수    | Inventory Turnover Days   | days  | false            | (inventory / COGS) × 365        |
| inventory_vs_sales_growth | 재고증가 vs 매출증가 | Inventory vs Sales Growth | ratio | false            | inventoryGrowth - revenueGrowth |
| sga_to_revenue            | 판관비/매출          | SGA to Revenue            | ratio | false            | SGA / revenue                   |
| asset_turnover            | 총자산회전율         | Asset Turnover            | ratio | true             | revenue / totalAssets           |

### dilution_shareholder (4개)

| metric_code           | display_name      | display_name_en        | unit  | higher_is_better | formula                                        |
| --------------------- | ----------------- | ---------------------- | ----- | ---------------- | ---------------------------------------------- |
| dilution_3y_cum       | 3년 누적 희석률   | 3Y Cumulative Dilution | pct   | false            | (shares_now - shares_3y_ago) / shares_3y_ago   |
| sbc_to_revenue        | 주식보상비/매출   | SBC to Revenue         | ratio | false            | stockBasedComp / revenue                       |
| buyback_offsets_sbc   | 자사주매입 vs SBC | Buyback Offsets SBC    | flag  | true             | buybackAmount >= SBC (boolean)                 |
| net_shareholder_yield | 순주주수익률      | Net Shareholder Yield  | ratio | true             | (dividend + buyback - newIssuance) / marketCap |

### valuation (3개, 보조)

| metric_code  | display_name | display_name_en   | unit  | higher_is_better | is_core_mvp | formula                  |
| ------------ | ------------ | ----------------- | ----- | ---------------- | ----------- | ------------------------ |
| pe_ratio     | PER          | Price to Earnings | ratio | false            | false       | price / EPS              |
| ev_to_ebitda | EV/EBITDA    | EV to EBITDA      | ratio | false            | false       | enterpriseValue / EBITDA |
| fcf_yield    | FCF 수익률   | FCF Yield         | ratio | true             | false       | FCF / marketCap          |

---

## 6. CompanyMetricSnapshot 필드 계산 소스 매핑

각 지표가 어떤 기존 모델의 어떤 필드에서 계산되는지:

```python
METRIC_SOURCE_MAP = {
    # profitability
    'gross_margin': {
        'apis': ['income-statement'],
        'fields': ['gross_profit', 'total_revenue'],
        'formula': 'IncomeStatement.gross_profit / IncomeStatement.total_revenue',
    },
    'operating_margin': {
        'apis': ['income-statement'],
        'fields': ['operating_income', 'total_revenue'],
        'formula': 'IncomeStatement.operating_income / IncomeStatement.total_revenue',
    },
    'net_margin': {
        'apis': ['income-statement'],
        'fields': ['net_income', 'total_revenue'],
        'formula': 'IncomeStatement.net_income / IncomeStatement.total_revenue',
    },
    'roe': {
        'apis': ['income-statement', 'balance-sheet'],
        'fields': ['net_income', 'total_shareholder_equity'],
        'formula': 'IncomeStatement.net_income / BalanceSheet.total_shareholder_equity',
    },
    'roic': {
        'apis': ['income-statement', 'balance-sheet'],
        'fields': ['operating_income', 'income_tax_expense', 'total_shareholder_equity', 'long_term_debt'],
        'formula': '(operating_income * (1 - tax_rate)) / (equity + long_term_debt)',
    },

    # growth (전년도 데이터 필요)
    'revenue_growth_yoy': {
        'apis': ['income-statement'],
        'fields': ['total_revenue'],
        'formula': '(rev_t - rev_t1) / abs(rev_t1)',
        'requires_prior_year': True,
    },
    'operating_income_growth': {
        'apis': ['income-statement'],
        'fields': ['operating_income'],
        'formula': '(op_t - op_t1) / abs(op_t1)',
        'requires_prior_year': True,
    },
    'fcf_growth_yoy': {
        'apis': ['cash-flow-statement'],
        'fields': ['operating_cashflow', 'capital_expenditures'],
        'formula': '(fcf_t - fcf_t1) / abs(fcf_t1)',
        'requires_prior_year': True,
    },
    'rev_growth_vs_industry': {
        'apis': ['income-statement'],
        'fields': ['total_revenue'],
        'formula': 'company_revenue_growth - industry_median_revenue_growth',
        'requires_benchmark': True,
    },

    # financial_structure
    'debt_to_equity': {
        'apis': ['balance-sheet'],
        'fields': ['short_longterm_debt_total', 'total_shareholder_equity'],
        'formula': 'BalanceSheet.short_longterm_debt_total / BalanceSheet.total_shareholder_equity',
        'fallback': '(long_term_debt + short_term_debt) / total_shareholder_equity',
    },
    'current_ratio': {
        'apis': ['balance-sheet'],
        'fields': ['total_current_assets', 'total_current_liabilities'],
        'formula': 'BalanceSheet.total_current_assets / BalanceSheet.total_current_liabilities',
    },
    'interest_coverage': {
        'apis': ['income-statement'],
        'fields': ['operating_income', 'interest_expense'],
        'formula': 'IncomeStatement.operating_income / IncomeStatement.interest_expense',
    },
    'net_debt_to_ebitda': {
        'apis': ['balance-sheet', 'income-statement'],
        'fields': ['short_longterm_debt_total', 'cash_and_cash_equivalents_at_carrying_value', 'ebitda'],
        'formula': '(total_debt - cash) / ebitda',
    },
    'cash_runway_years': {
        'apis': ['balance-sheet', 'cash-flow-statement'],
        'fields': ['cash_and_cash_equivalents_at_carrying_value', 'operating_cashflow'],
        'formula': 'cash / abs(operating_cashflow) if operating_cashflow < 0 else null',
    },
    'short_term_debt_pct': {
        'apis': ['balance-sheet'],
        'fields': ['short_term_debt', 'short_longterm_debt_total'],
        'formula': 'short_term_debt / total_debt',
    },

    # cash_flow_quality
    'fcf_margin': {
        'apis': ['cash-flow-statement', 'income-statement'],
        'fields': ['operating_cashflow', 'capital_expenditures', 'total_revenue'],
        'formula': '(operating_cashflow - capital_expenditures) / total_revenue',
    },
    'ocf_to_net_income': {
        'apis': ['cash-flow-statement', 'income-statement'],
        'fields': ['operating_cashflow', 'net_income'],
        'formula': 'operating_cashflow / net_income',
    },
    'capex_to_ocf': {
        'apis': ['cash-flow-statement'],
        'fields': ['capital_expenditures', 'operating_cashflow'],
        'formula': 'abs(capital_expenditures) / operating_cashflow',
    },
    'accruals_ratio': {
        'apis': ['income-statement', 'cash-flow-statement', 'balance-sheet'],
        'fields': ['net_income', 'operating_cashflow', 'total_assets'],
        'formula': '(net_income - operating_cashflow) / total_assets',
    },
    'fcf_conversion': {
        'apis': ['cash-flow-statement', 'income-statement'],
        'fields': ['operating_cashflow', 'capital_expenditures', 'net_income'],
        'formula': 'FCF / net_income',
    },
    'cash_from_ops_trend': {
        'apis': ['cash-flow-statement'],
        'fields': ['operating_cashflow'],
        'formula': '3Y CAGR of operating_cashflow',
        'requires_multi_year': True,
    },

    # operational_efficiency
    'dso': {
        'apis': ['balance-sheet', 'income-statement'],
        'fields': ['current_net_receivables', 'total_revenue'],
        'formula': '(current_net_receivables / total_revenue) * 365',
    },
    'ar_to_revenue': {
        'apis': ['balance-sheet', 'income-statement'],
        'fields': ['current_net_receivables', 'total_revenue'],
        'formula': 'current_net_receivables / total_revenue',
    },
    'inventory_turnover_days': {
        'apis': ['balance-sheet', 'income-statement'],
        'fields': ['inventory', 'cost_of_revenue'],
        'formula': '(inventory / cost_of_revenue) * 365',
    },
    'inventory_vs_sales_growth': {
        'apis': ['balance-sheet', 'income-statement'],
        'fields': ['inventory', 'total_revenue'],
        'formula': 'inventory_growth_rate - revenue_growth_rate',
        'requires_prior_year': True,
    },
    'sga_to_revenue': {
        'apis': ['income-statement'],
        'fields': ['selling_general_and_administrative', 'total_revenue'],
        'formula': 'SGA / total_revenue',
    },
    'asset_turnover': {
        'apis': ['income-statement', 'balance-sheet'],
        'fields': ['total_revenue', 'total_assets'],
        'formula': 'total_revenue / total_assets',
    },

    # dilution_shareholder
    'dilution_3y_cum': {
        'apis': ['balance-sheet'],
        'fields': ['common_stock_shares_outstanding'],
        'formula': '(shares_now - shares_3y_ago) / shares_3y_ago',
        'requires_multi_year': True,
    },
    'sbc_to_revenue': {
        'apis': ['cash-flow-statement', 'income-statement'],
        'fields': ['stock_based_compensation', 'total_revenue'],
        'formula': 'stock_based_compensation / total_revenue',
        'note': '현재 CashFlowStatement에 SBC 전용 필드 없음. FMP key-metrics 전환 시 추가 가능. 그전까지는 null 처리.',
        'nullable_until_fmp': True,
    },
    'buyback_offsets_sbc': {
        'apis': ['cash-flow-statement'],
        'fields': ['payments_for_repurchase_of_common_stock'],
        'formula': 'abs(buyback) >= SBC → true/false. SBC 없으면 null.',
        'note': 'sbc_to_revenue와 동일 제약.',
    },
    'net_shareholder_yield': {
        'apis': ['cash-flow-statement', 'stocks.Stock'],
        'fields': ['dividend_payout', 'payments_for_repurchase_of_common_stock', 'proceeds_from_issuance_of_common_stock', 'market_capitalization'],
        'formula': '(dividend + buyback - issuance) / market_cap',
    },

    # valuation (보조)
    'pe_ratio': {
        'apis': ['stocks.Stock'],
        'fields': ['pe_ratio'],
        'formula': 'Stock.pe_ratio (이미 계산된 값 사용)',
        'note': '직접 계산하지 않고 Stock 또는 FMP key-metrics에서 가져옴.',
    },
    'ev_to_ebitda': {
        'apis': ['stocks.Stock'],
        'fields': ['ev_to_ebitda'],
        'formula': 'Stock.ev_to_ebitda (이미 계산된 값 사용)',
    },
    'fcf_yield': {
        'apis': ['cash-flow-statement', 'stocks.Stock'],
        'fields': ['operating_cashflow', 'capital_expenditures', 'market_capitalization'],
        'formula': 'FCF / market_cap',
    },
}
```

---

## 7. Chain Sight 기업 데이터 정의 체계

### CompanySensitivityProfile 필드

```
symbol (PK, FK→Stock)
debt_to_equity: NUMERIC — 부채비율 (금리 민감도)
net_debt: BIGINT — 순부채
interest_coverage: NUMERIC — 이자보상배율
debt_maturity_risk: VARCHAR(10) — "high"/"medium"/"low"
rate_sensitivity: VARCHAR(10) — 종합 금리 민감도 ("high"/"medium"/"low")
foreign_revenue_pct: NUMERIC — 해외매출비중(%)
primary_currency_exposure: VARCHAR(10) — 주요 노출 통화
forex_sensitivity: VARCHAR(10) — 종합 환율 민감도 ("high"/"medium"/"low")
beta: NUMERIC — 시장 베타
beta_sector_adj: NUMERIC — 섹터 조정 베타
sector: VARCHAR(100)
industry: VARCHAR(100)
is_regulated_industry: BOOLEAN
regulation_type: VARCHAR(50) — "fda"/"financial"/"environmental"/"telecom"/"none"
commodity_sensitivity: VARCHAR(10) — 종합 원자재 민감도 ("high"/"medium"/"low")
data_source: JSONB
calculated_at: TIMESTAMP
```

### CompanyGrowthStage 필드

```
symbol (PK, FK→Stock)
stage: VARCHAR(30) — "early_growth"/"accelerating"/"mature"/"cash_cow"/"turnaround"/"declining"
revenue_cagr_3y: NUMERIC
revenue_cagr_5y: NUMERIC
revenue_acceleration: NUMERIC
net_income_positive_years: INTEGER
net_income_turned_positive: BOOLEAN
fcf_trend: VARCHAR(20)
fcf_positive_years: INTEGER
dividend_started: BOOLEAN
dividend_years: INTEGER
confidence: VARCHAR(10)
calculated_at: TIMESTAMP
```

### CompanyCapitalDNA 필드

```
symbol (PK, FK→Stock)
rd_to_revenue: NUMERIC
rd_trend: VARCHAR(20)
capex_to_revenue: NUMERIC
capex_trend: VARCHAR(20)
dividend_payout: NUMERIC
buyback_yield: NUMERIC
total_shareholder_return_pct: NUMERIC
net_cash_position: BIGINT
cash_to_market_cap: NUMERIC
capital_type: VARCHAR(30) — "heavy_investor"/"balanced"/"shareholder_first"/"cash_hoarder"/"aggressive_growth"
calculated_at: TIMESTAMP
```

### CompanyInsiderSignal 필드

```
symbol (PK, FK→Stock)
insider_buy_count_90d: INTEGER
insider_sell_count_90d: INTEGER
insider_net_amount_90d: BIGINT
insider_signal: VARCHAR(20) — "strong_buy"/"buy"/"neutral"/"sell"/"strong_sell"
institutional_ownership_pct: NUMERIC
institutional_change_qoq: NUMERIC
top_holder_action: VARCHAR(20)
short_interest_pct: NUMERIC
short_interest_change: VARCHAR(20)
days_to_cover: NUMERIC
smart_money_signal: VARCHAR(20) — "bullish"/"neutral"/"bearish"
data_freshness: DATE
calculated_at: TIMESTAMP
```

### CompanyRevenueStructure 필드

```
symbol (PK, FK→Stock)
segments: JSONB — [{"name":"iPhone","revenue_pct":52,"trend":"stable"},...]
geographic_revenue: JSONB — [{"region":"Americas","pct":42},...]
major_customers: JSONB — [{"customer":"Apple","revenue_pct":22},...]
customer_concentration_risk: VARCHAR(10)
business_model_type: VARCHAR(20) — "b2b"/"b2c"/"mixed"/"unknown"
commodity_exposures: JSONB — [{"commodity":"lithium","exposure":"high"},...]
source_filing: VARCHAR(100)
extraction_method: VARCHAR(20)
extraction_confidence: NUMERIC
last_parsed_at: TIMESTAMP
```

### CompanyNarrativeTag 필드

```
symbol (PK, FK→Stock)
primary_narrative: VARCHAR(100)
secondary_narrative: VARCHAR(100)
narrative_strength: VARCHAR(10)
narrative_sentiment: VARCHAR(10)
theme_tags: TEXT[]
avg_sentiment_30d: NUMERIC
sentiment_trend: VARCHAR(20)
news_frequency_30d: INTEGER
analyst_consensus: VARCHAR(20)
analyst_target_vs_price: NUMERIC
analyst_revision_trend: VARCHAR(20)
generated_by: VARCHAR(20)
generated_at: TIMESTAMP
```

### CompanyEventReaction 필드

```
id (PK, BIGSERIAL)
symbol (FK→Stock)
event_type: VARCHAR(50) — "rate_hike"/"china_tariff" 등
sample_count: INTEGER
avg_return_1d: NUMERIC
avg_return_5d: NUMERIC
hit_rate_negative: NUMERIC
avg_abnormal_return: NUMERIC
reaction_grade: VARCHAR(10)
confidence: VARCHAR(10)
calculated_at: TIMESTAMP
UNIQUE(symbol, event_type)
```

### CompanyChainProfile 필드 (집약 → 그래프 DB 투영)

```
symbol (PK, FK→Stock)
rate_sensitivity: VARCHAR(10)
forex_sensitivity: VARCHAR(10)
commodity_sensitivity: VARCHAR(10)
regulation_type: VARCHAR(50)
beta: NUMERIC
growth_stage: VARCHAR(30)
revenue_cagr_3y: NUMERIC
capital_type: VARCHAR(30)
net_cash_position: BIGINT
smart_money_signal: VARCHAR(20)
top_segment: VARCHAR(100)
top_segment_pct: NUMERIC
china_revenue_pct: NUMERIC
customer_concentration_risk: VARCHAR(10)
business_model_type: VARCHAR(20)
primary_narrative: VARCHAR(100)
theme_tags: TEXT[]
narrative_sentiment: VARCHAR(10)
score_profitability: NUMERIC
score_growth: NUMERIC
score_financial_structure: NUMERIC
overall_grade: VARCHAR(5)
profile_completeness: NUMERIC
last_updated: TIMESTAMP
```

### ChainNewsEvent 필드

```
id (PK, BIGSERIAL)
symbol (FK→Stock, on_delete=PROTECT)
source: VARCHAR(20) — "marketaux"/"finnhub"/"eodhd"
source_id: VARCHAR(255) — 중복 방지
title: TEXT
summary: TEXT
url: TEXT
published_at: TIMESTAMP
sentiment_score: NUMERIC(4,3)
sentiment_label: VARCHAR(10)
event_type: VARCHAR(50)
event_importance: VARCHAR(10)
co_mentioned_symbols: TEXT[] — 동시출현 종목
is_duplicate: BOOLEAN
duplicate_of_id: BIGINT (self FK)
created_at: TIMESTAMP
UNIQUE(source, source_id)
```

### ChainNewsEvent 감성 소스 매핑

| source    | sentiment_score                            | sentiment_label    | 비고                               |
| --------- | ------------------------------------------ | ------------------ | ---------------------------------- |
| marketaux | API 직접 제공 (entities[].sentiment_score) | score 기반 변환    | 가장 신뢰도 높음                   |
| finnhub   | null (제공 안 함)                          | null               | 추후 Gemini Flash 배치로 보강 가능 |
| eodhd     | API 직접 제공 (sentiment.polarity)         | polarity 기반 변환 | marketaux 보조                     |
