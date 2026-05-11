from django.db import models


class CompanyInsiderSignal(models.Model):
    """내부자/기관 행동 신호. Finnhub Form 4 + 13F 기반."""

    INSIDER_SIGNAL_CHOICES = [
        ('strong_buy', 'Strong Buy'), ('buy', 'Buy'),
        ('neutral', 'Neutral'),
        ('sell', 'Sell'), ('strong_sell', 'Strong Sell'),
    ]
    HOLDER_ACTION_CHOICES = [
        ('accumulating', 'Accumulating'),
        ('stable', 'Stable'),
        ('distributing', 'Distributing'),
    ]
    CHANGE_CHOICES = [
        ('increasing', 'Increasing'),
        ('stable', 'Stable'),
        ('decreasing', 'Decreasing'),
    ]
    SMART_MONEY_CHOICES = [
        ('bullish', 'Bullish'), ('neutral', 'Neutral'), ('bearish', 'Bearish'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='insider_signal',
    )

    # 내부자 매매
    insider_buy_count_90d = models.IntegerField(default=0)
    insider_sell_count_90d = models.IntegerField(default=0)
    insider_net_amount_90d = models.BigIntegerField(null=True, blank=True)
    insider_signal = models.CharField(max_length=20, blank=True, choices=INSIDER_SIGNAL_CHOICES)

    # 기관
    institutional_ownership_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    institutional_change_qoq = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    top_holder_action = models.CharField(max_length=20, blank=True, choices=HOLDER_ACTION_CHOICES)

    # 공매도
    short_interest_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    short_interest_change = models.CharField(max_length=20, blank=True, choices=CHANGE_CHOICES)
    days_to_cover = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # 종합
    smart_money_signal = models.CharField(max_length=20, blank=True, choices=SMART_MONEY_CHOICES)

    data_freshness = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_insider_signal'

    def __str__(self):
        return f"{self.symbol_id}: smart_money={self.smart_money_signal}"
