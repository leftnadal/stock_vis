from django.db import models


class CategorySignal(models.Model):
    """
    카테고리별 종합 신호.
    score는 내부 계산용으로 유지, UI에서는 signal만 표시.
    """
    CATEGORY_CHOICES = [
        ('profitability', 'Profitability'),
        ('growth', 'Growth'),
        ('financial_structure', 'Financial Structure'),
        ('cash_flow_quality', 'Cash Flow Quality'),
        ('operational_efficiency', 'Operational Efficiency'),
        ('dilution_shareholder', 'Dilution & Shareholder'),
        ('valuation', 'Valuation'),
    ]

    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', db_column='symbol',
        related_name='category_signals',
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    fiscal_year = models.IntegerField(default=0)

    # 핵심: signal
    signal = models.CharField(
        max_length=10, blank=True,
        choices=[
            ('green', '양호'),
            ('yellow', '주의'),
            ('red', '경고'),
            ('gray', '해석 제한'),
        ]
    )
    signal_reason = models.CharField(max_length=200, blank=True)

    # 내부 계산용 score (UI 미노출)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # 지표 수 추적
    metric_count = models.IntegerField(default=0, help_text="이 카테고리의 총 지표 수")
    valid_metric_count = models.IntegerField(default=0, help_text="score 계산에 사용된 지표 수")

    contributing_metrics = models.JSONField(
        default=list,
        help_text='[{"metric": "roe", "value": 0.25, "signal": "green"}, ...]'
    )

    preset_key = models.CharField(max_length=30, default='default', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validation_category_signal'
        unique_together = ['symbol', 'category', 'fiscal_year', 'preset_key']
        indexes = [
            models.Index(fields=['symbol']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.category} {self.fiscal_year}: [{self.signal}]"
