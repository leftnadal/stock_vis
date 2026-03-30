from django.db import models
from django.contrib.postgres.fields import ArrayField


class PeerListCache(models.Model):
    """
    종목별 peer 목록 캐시.
    FMP stock-peers API 결과 저장.
    """
    symbol = models.OneToOneField(
        'stocks.Stock',
        on_delete=models.CASCADE,
        to_field='symbol',
        primary_key=True,
        related_name='peer_cache',
    )
    peer_symbols = ArrayField(
        models.CharField(max_length=10),
        default=list, blank=True,
        help_text='["MSFT", "GOOGL", "META"]'
    )
    peer_count = models.IntegerField(default=0)

    use_industry_fallback = models.BooleanField(default=False)
    fallback_reason = models.CharField(max_length=200, blank=True)

    source = models.CharField(max_length=20, default='fmp_peers')

    # peer 선정 기준 (설계서 섹션 3.2)
    benchmark_basis = models.CharField(
        max_length=20, default='industry_size',
        choices=[
            ('industry_size', '업종+규모'),
            ('industry', '업종 전체'),
            ('sector', '섹터 전체'),
        ],
    )
    size_bucket = models.CharField(
        max_length=10, blank=True, default='',
        choices=[('mega', 'Mega'), ('large', 'Large'), ('mid', 'Mid'), ('small', 'Small')],
    )
    peer_tier = models.CharField(
        max_length=20, blank=True, default='',
        help_text="Phase 2: Chain Sight 연계 시 strict/broad/industry. Phase 1에서는 빈 문자열."
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metrics_peer_list_cache'

    def __str__(self):
        return f"{self.symbol_id}: {self.peer_count} peers"


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
