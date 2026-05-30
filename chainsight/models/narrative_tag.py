from django.contrib.postgres.fields import ArrayField
from django.db import models


class CompanyNarrativeTag(models.Model):
    """뉴스 기반 내러티브/테마 태그. LLM 배치 태깅 또는 rule-based."""

    STRENGTH_CHOICES = [('strong', 'Strong'), ('moderate', 'Moderate'), ('weak', 'Weak')]
    SENTIMENT_CHOICES = [('positive', 'Positive'), ('mixed', 'Mixed'), ('negative', 'Negative')]
    GENERATED_BY_CHOICES = [
        ('llm_batch', 'LLM Batch'), ('rule_based', 'Rule Based'), ('manual', 'Manual'),
    ]
    CONSENSUS_CHOICES = [
        ('strong_buy', 'Strong Buy'), ('buy', 'Buy'), ('hold', 'Hold'),
        ('sell', 'Sell'), ('strong_sell', 'Strong Sell'),
    ]
    REVISION_CHOICES = [
        ('upgrading', 'Upgrading'), ('stable', 'Stable'), ('downgrading', 'Downgrading'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='narrative_tag',
    )

    primary_narrative = models.CharField(max_length=100, blank=True)
    secondary_narrative = models.CharField(max_length=100, blank=True)
    narrative_strength = models.CharField(max_length=10, blank=True, choices=STRENGTH_CHOICES)
    narrative_sentiment = models.CharField(max_length=10, blank=True, choices=SENTIMENT_CHOICES)

    theme_tags = ArrayField(
        models.CharField(max_length=50),
        default=list, blank=True,
        help_text='["ai_infrastructure", "china_risk"]'
    )

    avg_sentiment_30d = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    sentiment_trend = models.CharField(
        max_length=20, blank=True,
        choices=[('improving', 'Improving'), ('stable', 'Stable'), ('deteriorating', 'Deteriorating')]
    )
    news_frequency_30d = models.IntegerField(default=0)

    analyst_consensus = models.CharField(max_length=20, blank=True, choices=CONSENSUS_CHOICES)
    analyst_target_vs_price = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    analyst_revision_trend = models.CharField(max_length=20, blank=True, choices=REVISION_CHOICES)

    generated_by = models.CharField(max_length=20, blank=True, choices=GENERATED_BY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_narrative_tag'

    def __str__(self):
        return f"{self.symbol_id}: {self.primary_narrative}"
