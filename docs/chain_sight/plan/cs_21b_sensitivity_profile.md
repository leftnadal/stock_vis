# CS-2-1b: SensitivityProfile 계산

> **작업 번호**: CS-2-1b
> **목표**: FMP Revenue Segmentation + Stock DB + BalanceSheet 기반 SensitivityProfile 자동 계산
> **예상 소요**: 3~5시간
> **선행 조건**: CS-2-1 완료 (GrowthStage, CapitalDNA 적재), FMP Revenue Segmentation API 200 확인 (decisions/003)
> **산출물**: `chainsight/tasks/sensitivity_tasks.py`, CompanySensitivityProfile ~500건 적재

---

## 데이터 원천

| 필드 | 원천 | API/테이블 |
|------|------|-----------|
| debt_to_equity | BalanceSheet | `total_shareholder_equity`, `long_term_debt`, `short_term_debt` |
| net_debt | BalanceSheet | `long_term_debt + short_term_debt - cash_and_cash_equivalents` |
| interest_coverage | IncomeStatement | `ebit / interest_expense` |
| debt_maturity_risk | 계산 | debt_to_equity + interest_coverage 기반 |
| rate_sensitivity | 계산 | debt_maturity_risk 종합 |
| foreign_revenue_pct | **FMP Revenue Geo Segmentation** | `/stable/revenue-geographic-segmentation?symbol=AAPL` |
| primary_currency_exposure | FMP Revenue Geo | 최대 지역 기반 추론 |
| forex_sensitivity | 계산 | foreign_revenue_pct 기반 |
| beta | Stock 모델 | `stock.beta` |
| beta_sector_adj | 계산 | `beta - sector_avg_beta` |
| sector, industry | Stock 모델 | `stock.sector`, `stock.industry` |
| is_regulated_industry | 규칙 | sector/industry 기반 매핑 |
| regulation_type | 규칙 | Healthcare→fda, Finance→financial 등 |

## 데이터 흐름

```
FMP Revenue Geo Segmentation API
  ↓
foreign_revenue_pct 계산 (US 외 매출 비중)
  ↓
BalanceSheet + IncomeStatement
  ↓
금리 민감도 계산 (D/E, interest coverage)
  ↓
Stock.beta + Sector 평균
  ↓
규제 민감도 매핑
  ↓
CompanySensitivityProfile (PostgreSQL)
```

## FMP API 사용

### Revenue Geographic Segmentation
```
GET https://financialmodelingprep.com/stable/revenue-geographic-segmentation?symbol=AAPL&apikey={key}
```

응답 예시:
```json
[
  {"date": "2025-09-27", "Americas": 169658000000, "Europe": 101328000000, "Greater China": 67024000000, ...}
]
```

### Revenue Product Segmentation (보조)
```
GET https://financialmodelingprep.com/stable/revenue-product-segmentation?symbol=AAPL&apikey={key}
```

⚠️ **Rate Limit**: FMP Starter 300 calls/min. S&P 500 전체 = 503 × 2 calls = ~1,006 calls (4분). 0.2초 딜레이 적용.
⚠️ **Geographic API 404 시**: foreign_revenue_pct = None, forex_sensitivity = '' (데이터 없음 허용)

## 민감도 계산 규칙

### 금리 민감도 (rate_sensitivity)
```
debt_to_equity > 2.0 AND interest_coverage < 3.0 → 'high'
debt_to_equity > 1.0 OR interest_coverage < 5.0  → 'medium'
else → 'low'
```

### 환율 민감도 (forex_sensitivity)
```
foreign_revenue_pct > 50% → 'high'
foreign_revenue_pct > 25% → 'medium'
foreign_revenue_pct <= 25% OR None → 'low'
```

### 규제 민감도 매핑
```python
REGULATION_MAP = {
    'Healthcare': 'fda',
    'Biotechnology': 'fda',
    'Pharmaceuticals': 'fda',
    'Financial Services': 'financial',
    'Banks': 'financial',
    'Insurance': 'financial',
    'Utilities': 'environmental',
    'Oil & Gas': 'environmental',
    'Telecommunications': 'telecom',
}
```

## 구현

```python
# chainsight/tasks/sensitivity_tasks.py

@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_sensitivity_profiles(self):
    """S&P 500 전체 SensitivityProfile 계산."""
    # 1. Stock DB에서 beta, sector, industry 가져오기
    # 2. BalanceSheet에서 D/E, interest_coverage 계산
    # 3. FMP Revenue Geo Segmentation에서 foreign_revenue_pct 계산
    # 4. 규칙 기반 민감도 분류
    # 5. CompanySensitivityProfile update_or_create
```

⚠️ FMP API 호출은 Celery task 내에서 **동기 requests** 사용 (CLAUDE.md 규칙: Celery에서 async 금지).
⚠️ `_clamp_decimal()` 패턴 재사용 (Decimal overflow 방지).
⚠️ 계산 실패 시 해당 종목 skip + logger.error (전체 중단 금지).

## 완료 기준

```
□ CompanySensitivityProfile ~480건+ 적재
□ rate_sensitivity 분포 확인 (high/medium/low)
□ forex_sensitivity 분포 확인
□ FMP API 호출 에러율 < 10%
□ calculate_all_profiles 통합 task에 추가
□ task_done 기록 작성
```

→ **다음**: cs_21c_insider_signal.md

**END OF DOCUMENT**
