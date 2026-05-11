# PR-2: CompanyMetricSnapshot + PeerListCache — 완료 보고서

> 완료일: 2026-03-26

---

## 작업 요약

metrics 앱에 CompanyMetricSnapshot(종목×연도×지표 계산값)과 PeerListCache(peer 목록 캐시) 모델을 추가했습니다.

## 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | CompanyMetricSnapshot 모델 생성 | ✅ |
| 2 | PeerListCache 모델 생성 | ✅ |
| 3 | FK 관계 정상 (Stock, MetricDefinition) | ✅ |
| 4 | unique_together (symbol, fiscal_year, metric_code) 확인 | ✅ |
| 5 | admin 등록 | ✅ |
| 6 | 기존 코드 영향 없음 | ✅ |

## 생성/수정된 파일

### 신규 생성
- `metrics/models/metric_snapshot.py`
- `metrics/models/benchmark.py`
- `metrics/migrations/0002_peerlistcache_companymetricsnapshot.py`

### 수정
- `metrics/models/__init__.py` — 새 모델 export 추가
- `metrics/admin.py` — CompanyMetricSnapshot, PeerListCache admin 등록

## 검증 결과

### 마이그레이션
```
Applying metrics.0002_peerlistcache_companymetricsnapshot... OK
```

### FK 관계 검증
```
CompanyMetricSnapshot:
  FK: symbol -> Stock
  FK: metric_code -> MetricDefinition

PeerListCache:
  PK: symbol (OneToOneField -> Stock)
```

### unique_together 검증
```
CompanyMetricSnapshot unique_together: (('symbol', 'fiscal_year', 'metric_code'),)
```

## 모델 구조

### CompanyMetricSnapshot
- symbol (FK→Stock, PROTECT), fiscal_year, metric_code (FK→MetricDefinition)
- metric_value (Decimal 20,6)
- 데이터 품질: is_fallback_used, fallback_reason, quality_flag
- 원천 추적: source_detail (JSONField)
- unique_together: (symbol, fiscal_year, metric_code)
- DB: `metrics_company_metric_snapshot`

### PeerListCache
- symbol (PK, OneToOne→Stock)
- peer_symbols (ArrayField), peer_count
- use_industry_fallback, fallback_reason, source
- DB: `metrics_peer_list_cache`

## 기존 코드 영향

없음. metrics 앱 내부 파일만 추가/수정.
