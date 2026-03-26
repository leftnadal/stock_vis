# PR-6: chainsight 앱 생성 — SensitivityProfile + GrowthStage + CapitalDNA — 완료 보고서

> 완료일: 2026-03-27

---

## 작업 요약

chainsight/ 앱을 생성하고 Tier A(정량, 재무제표 기반) 모델 3개를 구현했습니다.

## 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | chainsight/ 앱 생성 (models/ 패키지 구조) | ✅ |
| 2 | CompanySensitivityProfile 모델 + 마이그레이션 | ✅ |
| 3 | CompanyGrowthStage 모델 + 마이그레이션 | ✅ |
| 4 | CompanyCapitalDNA 모델 + 마이그레이션 | ✅ |
| 5 | admin 등록 (3개 모델) | ✅ |
| 6 | INSTALLED_APPS에 'chainsight' 추가 | ✅ |
| 7 | 기존 코드 영향 없음 | ✅ |

## 생성/수정된 파일

### 신규 생성
- `chainsight/__init__.py`, `chainsight/admin.py`, `chainsight/apps.py`
- `chainsight/models/__init__.py`
- `chainsight/models/sensitivity.py`
- `chainsight/models/growth_stage.py`
- `chainsight/models/capital_dna.py`
- `chainsight/migrations/0001_initial.py`

### 수정
- `config/settings.py` — INSTALLED_APPS에 `'chainsight'` 추가

## 검증 결과

```
CompanySensitivityProfile: PK=symbol, table=chainsight_sensitivity_profile
CompanyGrowthStage: PK=symbol, table=chainsight_growth_stage
CompanyCapitalDNA: PK=symbol, table=chainsight_capital_dna
```

## 모델 구조

### CompanySensitivityProfile (PK: symbol OneToOne→Stock)
- 금리: debt_to_equity, net_debt, interest_coverage, debt_maturity_risk, rate_sensitivity
- 환율: foreign_revenue_pct, primary_currency_exposure, forex_sensitivity
- 시장: beta, beta_sector_adj
- 원자재: commodity_sensitivity
- 규제: sector, industry, is_regulated_industry, regulation_type

### CompanyGrowthStage (PK: symbol OneToOne→Stock)
- stage (6단계), revenue_cagr_3y/5y, revenue_acceleration
- net_income_positive_years, net_income_turned_positive
- fcf_trend, fcf_positive_years, dividend_started/years, confidence

### CompanyCapitalDNA (PK: symbol OneToOne→Stock)
- rd_to_revenue, rd_trend, capex_to_revenue, capex_trend
- dividend_payout, buyback_yield, total_shareholder_return_pct
- net_cash_position, cash_to_market_cap, capital_type (6종)

## 기존 코드 영향

없음. config/settings.py INSTALLED_APPS 1줄 추가만.
