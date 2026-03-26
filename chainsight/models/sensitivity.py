from django.db import models


class CompanySensitivityProfile(models.Model):
    """이벤트(금리, 환율, 규제)에 대한 기업별 민감도 프로파일."""

    RISK_LEVEL_CHOICES = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    REGULATION_CHOICES = [
        ('fda', 'FDA/Healthcare'),
        ('financial', 'Financial'),
        ('environmental', 'Environmental'),
        ('telecom', 'Telecom'),
        ('none', 'None'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='sensitivity_profile',
    )

    # 금리 민감도
    debt_to_equity = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    net_debt = models.BigIntegerField(null=True, blank=True)
    interest_coverage = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    debt_maturity_risk = models.CharField(max_length=10, blank=True, choices=RISK_LEVEL_CHOICES)
    rate_sensitivity = models.CharField(
        max_length=10, blank=True, choices=RISK_LEVEL_CHOICES,
        help_text='종합 금리 민감도 (debt_to_equity + interest_coverage + maturity 기반)'
    )

    # 환율 민감도
    foreign_revenue_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    primary_currency_exposure = models.CharField(max_length=10, blank=True)
    forex_sensitivity = models.CharField(
        max_length=10, blank=True, choices=RISK_LEVEL_CHOICES,
        help_text='종합 환율 민감도 (foreign_revenue_pct 기반)'
    )

    # 시장 민감도
    beta = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    beta_sector_adj = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    # 원자재 민감도 (Tier B에서 채움, 초기에는 blank)
    commodity_sensitivity = models.CharField(
        max_length=10, blank=True, choices=RISK_LEVEL_CHOICES,
        help_text='종합 원자재 민감도 (revenue_structure.commodity_exposures 기반)'
    )

    # 규제 민감도
    sector = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    is_regulated_industry = models.BooleanField(default=False)
    regulation_type = models.CharField(max_length=50, blank=True, choices=REGULATION_CHOICES)

    data_source = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_sensitivity_profile'

    def __str__(self):
        return f"{self.symbol_id}: rate={self.debt_maturity_risk} beta={self.beta}"
