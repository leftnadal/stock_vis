from django.db import models


class CategoryScore(models.Model):
    """카테고리별 종합 점수. MVP에서는 signal card 중심, 점수는 optional."""
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
        related_name='category_scores',
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)

    # MVP 핵심: signal card
    signal = models.CharField(
        max_length=10, blank=True,
        choices=[('green', 'Green'), ('yellow', 'Yellow'), ('red', 'Red')]
    )
    signal_reason = models.CharField(max_length=200, blank=True)

    # Optional (Phase 2)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=5, blank=True)  # "A+", "A", "B+", ...
    rank_in_industry = models.IntegerField(null=True, blank=True)
    total_in_industry = models.IntegerField(null=True, blank=True)

    contributing_metrics = models.JSONField(
        default=list,
        help_text='[{"metric": "roe", "value": 0.25, "signal": "green"}, ...]'
    )

    score_1y_ago = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_change = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validation_category_score'
        unique_together = ['symbol', 'category']
        indexes = [
            models.Index(fields=['symbol']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.category}: [{self.signal}] {self.score}"
