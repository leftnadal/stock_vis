from django.db import models


class MetricDefinition(models.Model):
    """
    지표 메타데이터 사전.
    모든 CompanyMetricSnapshot의 metric_code가 이 테이블을 FK 참조.
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

    UNIT_CHOICES = [
        ('ratio', 'Ratio'),
        ('days', 'Days'),
        ('pct', 'Percentage'),
        ('years', 'Years'),
        ('flag', 'Boolean Flag'),
    ]

    metric_code = models.CharField(max_length=50, primary_key=True)
    display_name = models.CharField(max_length=100)
    display_name_en = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    higher_is_better = models.BooleanField()
    is_core_mvp = models.BooleanField(default=True)
    is_benchmarkable = models.BooleanField(default=True)

    # 계산 정보
    formula_description = models.TextField(blank=True)
    source_apis = models.JSONField(default=list)
    source_fields = models.JSONField(default=list)
    fallback_formula = models.TextField(blank=True)

    # 신호등 임계값
    green_threshold = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    red_threshold = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    threshold_direction = models.CharField(
        max_length=10, default='above',
        choices=[('above', 'Above'), ('below', 'Below')]
    )

    # 관리
    sort_order = models.IntegerField(default=0)
    formula_version = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'metrics_metric_definition'
        ordering = ['category', 'sort_order']

    def __str__(self):
        return f"{self.metric_code}: {self.display_name}"
