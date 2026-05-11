# PR-3: IndustryMetricBenchmark + PeerMetricBenchmark 모델

## 참고 문서

- `docs/architecture/claude-code-reference-doc.md` — 섹션 3(컨벤션)
- PR-2 완료 전제: CompanyMetricSnapshot, PeerListCache 존재

## 작업 범위

1. IndustryMetricBenchmark 모델 생성 (metrics/models/benchmark.py에 추가)
2. PeerMetricBenchmark 모델 생성 (같은 파일에 추가)
3. admin 등록

---

## 1. IndustryMetricBenchmark

산업별 연도별 지표 분포 (p25/median/p75). benchmark_confidence 포함.

```python
# metrics/models/benchmark.py 에 추가

from django.db import models


class IndustryMetricBenchmark(models.Model):
    """산업별 연도별 지표 분포. 차트 밴드 데이터."""
    industry = models.CharField(max_length=100, db_index=True)
    fiscal_year = models.IntegerField()
    metric_code = models.ForeignKey(
        'metrics.MetricDefinition',
        on_delete=models.CASCADE,
        db_column='metric_code',
    )

    p25_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    median_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    p75_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    mean_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    sample_count = models.IntegerField(default=0)
    benchmark_confidence = models.CharField(
        max_length=10, default='high',
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        help_text='high: sample>=10, medium: 5-9, low: <5 → sector fallback'
    )

    is_sector_fallback = models.BooleanField(default=False)
    sector = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'metrics_industry_metric_benchmark'
        unique_together = ['industry', 'fiscal_year', 'metric_code']
        indexes = [
            models.Index(fields=['industry', 'fiscal_year']),
        ]

    def __str__(self):
        return f"{self.industry} {self.fiscal_year} {self.metric_code_id}: median={self.median_value}"
```

## 2. PeerMetricBenchmark

종목별 peer 연도별 분포.

```python
from django.db import models
from django.contrib.postgres.fields import ArrayField


class PeerMetricBenchmark(models.Model):
    """종목별 peer 연도별 분포. 차트 핵심 데이터."""
    symbol = models.ForeignKey(
        'stocks.Stock',
        on_delete=models.CASCADE,
        to_field='symbol',
        db_column='symbol',
    )
    fiscal_year = models.IntegerField()
    metric_code = models.ForeignKey(
        'metrics.MetricDefinition',
        on_delete=models.CASCADE,
        db_column='metric_code',
    )

    p25_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    median_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    p75_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    peer_count = models.IntegerField(default=0)
    peer_symbols_used = ArrayField(
        models.CharField(max_length=10),
        default=list, blank=True,
    )

    benchmark_confidence = models.CharField(
        max_length=10, default='high',
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        help_text='high: peer>=8, medium: 3-7, low: <3'
    )

    use_minmax = models.BooleanField(default=False)
    min_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    max_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'metrics_peer_metric_benchmark'
        unique_together = ['symbol', 'fiscal_year', 'metric_code']
        indexes = [
            models.Index(fields=['symbol', 'fiscal_year']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.fiscal_year} {self.metric_code_id}: median={self.median_value}"
```

## 3. **init**.py 업데이트

IndustryMetricBenchmark, PeerMetricBenchmark 추가.

## 완료 기준

- [ ] IndustryMetricBenchmark 모델 + 마이그레이션
- [ ] PeerMetricBenchmark 모델 + 마이그레이션
- [ ] benchmark_confidence 필드 포함 확인
- [ ] admin 등록
