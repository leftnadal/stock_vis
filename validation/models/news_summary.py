from django.db import models


class ValidationNewsSummary(models.Model):
    """1차 검증용 뉴스 감성/이벤트 집계 캐시."""

    symbol = models.OneToOneField(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        primary_key=True,
        related_name="validation_news_summary",
    )

    event_count_30d = models.IntegerField(default=0)
    event_count_90d = models.IntegerField(default=0)

    avg_sentiment_30d = models.DecimalField(
        max_digits=4, decimal_places=3, null=True, blank=True
    )
    sentiment_trend = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("improving", "Improving"),
            ("stable", "Stable"),
            ("deteriorating", "Deteriorating"),
        ],
    )

    dominant_event_type = models.CharField(max_length=50, blank=True)
    high_importance_count = models.IntegerField(default=0)

    has_regulatory_risk = models.BooleanField(default=False)
    has_exec_change = models.BooleanField(default=False)
    has_guidance_cut = models.BooleanField(default=False)

    recent_highlights = models.JSONField(
        default=list,
        help_text='[{"title": "...", "sentiment": 0.7, "event_type": "earnings", "date": "..."}, ...]',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "validation_news_summary"

    def __str__(self):
        return f"{self.symbol_id}: {self.event_count_30d} events (30d)"
