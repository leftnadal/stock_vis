from django.db import models


class CompanyEventReaction(models.Model):
    """이벤트 유형별 주가 반응 통계. 뉴스 + 주가 교차분석."""

    REACTION_GRADE_CHOICES = [
        ("high_negative", "High Negative"),
        ("moderate_negative", "Moderate Negative"),
        ("neutral", "Neutral"),
        ("moderate_positive", "Moderate Positive"),
        ("high_positive", "High Positive"),
    ]
    CONFIDENCE_CHOICES = [("high", "High"), ("medium", "Medium"), ("low", "Low")]

    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        db_column="symbol",
        related_name="event_reactions",
    )
    event_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text='"rate_hike", "china_tariff", "tech_selloff" 등',
    )

    sample_count = models.IntegerField(default=0)
    avg_return_1d = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    avg_return_5d = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    hit_rate_negative = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    avg_abnormal_return = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )

    reaction_grade = models.CharField(
        max_length=20, blank=True, choices=REACTION_GRADE_CHOICES
    )
    confidence = models.CharField(
        max_length=10, default="low", choices=CONFIDENCE_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chainsight_event_reaction"
        unique_together = ["symbol", "event_type"]
        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["symbol"]),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.event_type}: {self.reaction_grade}"
