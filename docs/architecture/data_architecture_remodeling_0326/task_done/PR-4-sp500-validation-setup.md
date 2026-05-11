# PR-4: SP500Constituent 수정 + validation 앱 생성 — 완료 보고서

> 완료일: 2026-03-26

---

## 작업 요약

SP500Constituent에 3개 필드를 추가(유일한 기존 코드 수정)하고, validation/ 앱을 생성하여 CompanyMetricLatest + CompanyBenchmarkDelta 모델을 구현했습니다.

## 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | SP500Constituent 필드 3개 추가 (is_core_universe, universe_source, industry) | ✅ |
| 2 | SP500Constituent 마이그레이션 성공 (기존 503개 데이터 유지) | ✅ |
| 3 | validation/ 앱 생성 | ✅ |
| 4 | CompanyMetricLatest 모델 + 마이그레이션 | ✅ |
| 5 | CompanyBenchmarkDelta 모델 + 마이그레이션 | ✅ |
| 6 | admin 등록 | ✅ |
| 7 | INSTALLED_APPS에 'validation' 추가 | ✅ |

## 생성/수정된 파일

### 신규 생성
- `validation/__init__.py`, `validation/admin.py`, `validation/apps.py`
- `validation/models/__init__.py`
- `validation/models/metric_latest.py`
- `validation/models/benchmark_delta.py`
- `validation/models/category_score.py` (PR-5 placeholder)
- `validation/models/news_summary.py` (PR-5 placeholder)
- `validation/migrations/0001_initial.py`
- `stocks/migrations/0007_sp500constituent_industry_and_more.py`

### 수정
- `stocks/models.py` — SP500Constituent에 3개 필드 추가
- `config/settings.py` — INSTALLED_APPS에 `'validation'` 추가

## 검증 결과

### SP500Constituent 마이그레이션 (기존 데이터 안전)
```
기존 데이터 수: 503
  is_core_universe: True (default True)
  universe_source: sp500 (default sp500)
  industry: "" (default empty)
```

### unique_together 검증
```
CompanyMetricLatest: (symbol, metric_code)
CompanyBenchmarkDelta: (symbol, fiscal_year, metric_code)
```

## 모델 구조

### CompanyMetricLatest
- symbol (FK→Stock), metric_code (FK→MetricDefinition)
- latest_value, latest_fiscal_year
- 추세: trend_label, trend_slope, trend_years_used
- 신호등: signal (green/yellow/red), signal_reason
- 경고: warning_flag, warning_message
- unique_together: (symbol, metric_code)
- DB: `validation_company_metric_latest`

### CompanyBenchmarkDelta
- symbol (FK→Stock), fiscal_year, metric_code (FK→MetricDefinition)
- company_value, benchmark_type (peer/industry)
- benchmark_median, benchmark_p25, benchmark_p75, benchmark_confidence
- delta_vs_median, percentile_rank, relative_signal
- unique_together: (symbol, fiscal_year, metric_code)
- DB: `validation_company_benchmark_delta`

## 기존 코드 영향

- `stocks/models.py` SP500Constituent 필드 3개 추가 (전부 nullable/default, 기존 데이터 안전)
- `config/settings.py` INSTALLED_APPS 1줄 추가
