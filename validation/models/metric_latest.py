from django.db import models


class CompanyMetricLatest(models.Model):
    """종목별 지표 최신값 + 추세 + 신호등. API 응답용 캐시."""

    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        db_column="symbol",
        related_name="metric_latest",
    )
    metric_code = models.ForeignKey(
        "metrics.MetricDefinition",
        on_delete=models.CASCADE,
        db_column="metric_code",
    )

    latest_value = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    latest_fiscal_year = models.IntegerField(null=True, blank=True)

    # 추세
    trend_label = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("improving", "Improving"),
            ("flat", "Flat"),
            ("deteriorating", "Deteriorating"),
        ],
    )
    trend_slope = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    trend_years_used = models.IntegerField(null=True, blank=True)

    # 신호등
    signal = models.CharField(
        max_length=10,
        blank=True,
        choices=[("green", "Green"), ("yellow", "Yellow"), ("red", "Red")],
    )
    signal_reason = models.CharField(max_length=200, blank=True)

    # 경고
    warning_flag = models.BooleanField(default=False)
    warning_message = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "validation_company_metric_latest"
        unique_together = ["symbol", "metric_code"]
        indexes = [
            models.Index(fields=["symbol"]),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.metric_code_id}: {self.latest_value} [{self.signal}]"
