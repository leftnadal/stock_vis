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

    benchmark_basis = models.CharField(
        max_length=20, default='industry_size',
        choices=[
            ('industry_size', '업종+규모'),
            ('industry', '업종 전체'),
            ('sector', '섹터 전체'),
        ],
    )
    benchmark_confidence = models.CharField(
        max_length=10, default='low',
        choices=[
            ('high', 'High'), ('medium', 'Medium'),
            ('low', 'Low'), ('limited', 'Limited'),
        ],
        help_text='high: peer>=15+industry_size, medium: 8~14, low: <8, limited: <4'
    )

    delta_vs_median = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    percentile_rank = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)
    total = models.IntegerField(null=True, blank=True)

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
