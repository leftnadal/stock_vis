# PR-3: IndustryMetricBenchmark + PeerMetricBenchmark — 완료 보고서

> 완료일: 2026-03-26

---

## 작업 요약

metrics/models/benchmark.py에 IndustryMetricBenchmark(산업별 지표 분포)와 PeerMetricBenchmark(peer별 지표 분포) 모델을 추가했습니다.

## 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | IndustryMetricBenchmark 모델 + 마이그레이션 | ✅ |
| 2 | PeerMetricBenchmark 모델 + 마이그레이션 | ✅ |
| 3 | benchmark_confidence 필드 포함 확인 | ✅ |
| 4 | admin 등록 | ✅ |
| 5 | 기존 코드 영향 없음 | ✅ |

## 생성/수정된 파일

### 신규 생성
- `metrics/migrations/0003_industrymetricbenchmark_peermetricbenchmark.py`

### 수정
- `metrics/models/benchmark.py` — IndustryMetricBenchmark, PeerMetricBenchmark 추가
- `metrics/models/__init__.py` — 새 모델 export 추가
- `metrics/admin.py` — 새 모델 admin 등록

## 검증 결과

### 마이그레이션
```
Applying metrics.0003_industrymetricbenchmark_peermetricbenchmark... OK
```

### unique_together 검증
```
IndustryMetricBenchmark: (industry, fiscal_year, metric_code)
PeerMetricBenchmark: (symbol, fiscal_year, metric_code)
```

### benchmark_confidence 필드
```
IndustryMetricBenchmark: [high, medium, low] — high: sample>=10, medium: 5-9, low: <5
PeerMetricBenchmark: [high, medium, low] — high: peer>=8, medium: 3-7, low: <3
```

## 모델 구조

### IndustryMetricBenchmark
- industry, fiscal_year, metric_code (FK→MetricDefinition)
- p25_value, median_value, p75_value, mean_value
- sample_count, benchmark_confidence
- is_sector_fallback, sector
- DB: `metrics_industry_metric_benchmark`

### PeerMetricBenchmark
- symbol (FK→Stock), fiscal_year, metric_code (FK→MetricDefinition)
- p25_value, median_value, p75_value
- peer_count, peer_symbols_used (ArrayField)
- benchmark_confidence, use_minmax, min_value, max_value
- DB: `metrics_peer_metric_benchmark`

## 기존 코드 영향

없음. metrics 앱 내부 파일만 수정.
