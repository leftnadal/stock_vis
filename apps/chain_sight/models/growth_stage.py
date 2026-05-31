from django.db import models


class CompanyGrowthStage(models.Model):
    """기업 생애주기 위치. 같은 이벤트에 대한 반응이 스테이지에 따라 다름."""

    STAGE_CHOICES = [
        ("early_growth", "Early Growth"),
        ("accelerating", "Accelerating"),
        ("mature", "Mature"),
        ("cash_cow", "Cash Cow"),
        ("turnaround", "Turnaround"),
        ("declining", "Declining"),
    ]
    CONFIDENCE_CHOICES = [("high", "High"), ("medium", "Medium"), ("low", "Low")]

    symbol = models.OneToOneField(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        primary_key=True,
        related_name="growth_stage",
    )

    stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default="mature")

    revenue_cagr_3y = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    revenue_cagr_5y = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    revenue_acceleration = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )

    net_income_positive_years = models.IntegerField(default=0)
    net_income_turned_positive = models.BooleanField(default=False)

    fcf_trend = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("growing", "Growing"),
            ("stable", "Stable"),
            ("declining", "Declining"),
        ],
    )
    fcf_positive_years = models.IntegerField(default=0)

    dividend_started = models.BooleanField(default=False)
    dividend_years = models.IntegerField(default=0)

    confidence = models.CharField(
        max_length=10, default="medium", choices=CONFIDENCE_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chainsight_growth_stage"

    def __str__(self):
        return f"{self.symbol_id}: {self.stage} (confidence={self.confidence})"
