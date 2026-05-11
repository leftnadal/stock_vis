# PR-4: SP500Constituent 수정 + validation 앱 생성

## 참고 문서

- `docs/architecture/claude-code-reference-doc.md` — 섹션 4(기존 모델), 섹션 5(지표 사전)
- PR-1~3 완료 전제

## 작업 범위

1. SP500Constituent에 필드 3개 추가 (유일한 기존 코드 수정)
2. validation/ Django 앱 생성
3. CompanyMetricLatest 모델 생성
4. CompanyBenchmarkDelta 모델 생성
5. admin 등록

## 주의사항

- SP500Constituent 추가 필드는 전부 nullable/default 있어서 마이그레이션 안전
- validation/ 모델은 metrics/ 모델을 참조 (FK: MetricDefinition)

---

## 1. SP500Constituent 필드 추가

`stocks/models.py`의 SP500Constituent에 아래 3개 필드 추가:

```python
is_core_universe = models.BooleanField(
    default=True, db_index=True,
    help_text="핵심 커버리지 여부"
)
universe_source = models.CharField(
    max_length=50, default='sp500',
    choices=[
        ('sp500', 'S&P 500 Index'),
        ('manual', 'Manual Addition'),
        ('screener', 'Screener Result'),
    ]
)
industry = models.CharField(
    max_length=100, blank=True, default='',
    help_text="세부 산업 (FMP Profile industry)"
)
```

기존 필드, 기존 Meta, 기존 **str**은 수정하지 않는다.

## 2. validation/ 앱 생성

```
validation/
├── __init__.py
├── admin.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── metric_latest.py
│   ├── benchmark_delta.py
│   ├── category_score.py
│   └── news_summary.py
└── migrations/
```

settings.py INSTALLED_APPS에 `validation` 추가.

## 3. CompanyMetricLatest 모델

API 응답용 최신값 캐시. CompanyMetricSnapshot에서 집계.

```python
# validation/models/metric_latest.py

from django.db import models


class CompanyMetricLatest(models.Model):
    """종목별 지표 최신값 + 추세 + 신호등. API 응답용 캐시."""
    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', db_column='symbol',
        related_name='metric_latest',
    )
    metric_code = models.ForeignKey(
        'metrics.MetricDefinition', on_delete=models.CASCADE,
        db_column='metric_code',
    )

    latest_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    latest_fiscal_year = models.IntegerField(null=True, blank=True)

    # 추세
    trend_label = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('improving', 'Improving'),
            ('flat', 'Flat'),
            ('deteriorating', 'Deteriorating'),
        ]
    )
    trend_slope = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    trend_years_used = models.IntegerField(null=True, blank=True)

    # 신호등
    signal = models.CharField(
        max_length=10, blank=True,
        choices=[('green', 'Green'), ('yellow', 'Yellow'), ('red', 'Red')]
    )
    signal_reason = models.CharField(max_length=200, blank=True)

    # 경고
    warning_flag = models.BooleanField(default=False)
    warning_message = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validation_company_metric_latest'
        unique_together = ['symbol', 'metric_code']
        indexes = [
            models.Index(fields=['symbol']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.metric_code_id}: {self.latest_value} [{self.signal}]"
```

## 4. CompanyBenchmarkDelta 모델

종목 vs benchmark 비교 결과.

```python
# validation/models/benchmark_delta.py

from django.db import models


class CompanyBenchmarkDelta(models.Model):
    """종목 vs peer/industry 비교 결과. 프론트엔드 직접 사용."""
    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', db_column='symbol',
    )
    fiscal_year = models.IntegerField()
    metric_code = models.ForeignKey(
        'metrics.MetricDefinition', on_delete=models.CASCADE,
        db_column='metric_code',
    )

    company_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    benchmark_type = models.CharField(
        max_length=20,
        choices=[('peer', 'Peer'), ('industry', 'Industry')]
    )
    benchmark_median = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    benchmark_p25 = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    benchmark_p75 = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    benchmark_confidence = models.CharField(
        max_length=10, default='low',
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        help_text='high: peer>=8, medium: 3-7, low: <3'
    )

    delta_vs_median = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    percentile_rank = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    relative_signal = models.CharField(
        max_length=10, blank=True,
        choices=[('above', 'Above'), ('inline', 'Inline'), ('below', 'Below')]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validation_company_benchmark_delta'
        unique_together = ['symbol', 'fiscal_year', 'metric_code']
        indexes = [
            models.Index(fields=['symbol', 'fiscal_year']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.fiscal_year} {self.metric_code_id}: {self.relative_signal}"
```

## 완료 기준

- [ ] SP500Constituent 마이그레이션 성공 (기존 데이터 유지)
- [ ] validation 앱 생성 완료
- [ ] CompanyMetricLatest 모델 + 마이그레이션
- [ ] CompanyBenchmarkDelta 모델 + 마이그레이션
- [ ] admin 등록
- [ ] 기존 코드 영향 없음 (SP500Constituent 필드 추가만)
