from django.db import models


class CompanyCapitalDNA(models.Model):
    """자본 배분 성향. 경영진이 돈을 어떻게 쓰는가."""

    CAPITAL_TYPE_CHOICES = [
        ('heavy_investor', 'Heavy Investor'),
        ('balanced', 'Balanced'),
        ('shareholder_first', 'Shareholder First'),
        ('cash_hoarder', 'Cash Hoarder'),
        ('aggressive_growth', 'Aggressive Growth'),
        ('unknown', 'Unknown'),
    ]
    TREND_CHOICES = [
        ('increasing', 'Increasing'),
        ('stable', 'Stable'),
        ('decreasing', 'Decreasing'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='capital_dna',
    )

    rd_to_revenue = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    rd_trend = models.CharField(max_length=20, blank=True, choices=TREND_CHOICES)

    capex_to_revenue = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    capex_trend = models.CharField(
        max_length=20, blank=True,
        choices=[('expanding', 'Expanding'), ('stable', 'Stable'), ('harvesting', 'Harvesting')]
    )

    dividend_payout = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    buyback_yield = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    total_shareholder_return_pct = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    net_cash_position = models.BigIntegerField(null=True, blank=True)
    cash_to_market_cap = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    capital_type = models.CharField(max_length=30, blank=True, choices=CAPITAL_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_capital_dna'

    def __str__(self):
        return f"{self.symbol_id}: {self.capital_type}"
