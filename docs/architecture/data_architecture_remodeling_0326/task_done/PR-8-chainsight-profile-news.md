# PR-8: RevenueStructure + ChainProfile + ChainNewsEvent — 완료 보고서

> 완료일: 2026-03-27

---

## 작업 요약

chainsight 앱에 마지막 3개 모델을 추가하여 총 9개 모델을 완성했습니다. 전체 데이터 아키텍처 리모델링 완료.

## 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | CompanyRevenueStructure 모델 + 마이그레이션 | ✅ |
| 2 | CompanyChainProfile 모델 + 마이그레이션 | ✅ |
| 3 | ChainNewsEvent 모델 + 마이그레이션 (self FK, ArrayField) | ✅ |
| 4 | admin 등록 (3개) | ✅ |
| 5 | chainsight/models/__init__.py에 9개 모델 전체 export | ✅ |
| 6 | 기존 stocks.StockNews 수정 없음 | ✅ |

## 생성/수정된 파일

### 신규 생성
- `chainsight/models/revenue_structure.py`
- `chainsight/models/chain_profile.py`
- `chainsight/models/news_event.py`
- `chainsight/migrations/0003_companychainprofile_companyrevenuestructure_and_more.py`

### 수정
- `chainsight/models/__init__.py` — 9개 모델 전체 export
- `chainsight/admin.py` — 3개 모델 admin 등록 추가 (총 9개)

## 검증 결과

```
CompanyRevenueStructure: PK=symbol (OneToOne→Stock)
CompanyChainProfile: PK=symbol (OneToOne→Stock)
ChainNewsEvent: unique_together=(source, source_id), FK→Stock (PROTECT)
  duplicate_of: self FK, on_delete=SET_NULL
  co_mentioned_symbols: ArrayField
  theme_tags: ArrayField
chainsight __all__: 9개 모델
```

## 모델 구조

### CompanyRevenueStructure (PK: symbol OneToOne→Stock)
- segments, geographic_revenue, major_customers (JSONField)
- customer_concentration_risk, business_model_type
- commodity_exposures (JSONField)
- source_filing, extraction_method, extraction_confidence, last_parsed_at

### CompanyChainProfile (PK: symbol OneToOne→Stock)
- 전체 chainsight 모델 요약 집약 테이블
- sensitivity/growth/capital/insider/revenue/narrative 요약 필드
- validation score 요약 (profitability, growth, financial_structure, overall_grade)
- profile_completeness (0.0~1.0)

### ChainNewsEvent (FK→Stock PROTECT, unique: source+source_id)
- source, source_id, title, summary, url, published_at
- sentiment_score/label, event_type/importance
- co_mentioned_symbols (ArrayField)
- duplicate_of (self FK, SET_NULL)

## 전체 PR-1~8 아키텍처 요약

| 앱 | 모델 수 | PR |
|----|---------|-----|
| metrics | 6 | PR-1~3 |
| validation | 4 | PR-4~5 |
| chainsight | 9 | PR-6~8 |
| stocks (수정) | 1 | PR-4 |
| **총계** | **19 신규 + 1 수정** | |
