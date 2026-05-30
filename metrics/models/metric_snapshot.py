from django.db import models


class CompanyMetricSnapshot(models.Model):
    """
    종목별 연도별 지표 계산값.
    기존 BalanceSheet + IncomeStatement + CashFlowStatement에서 파생.
    """

    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.PROTECT,
        to_field="symbol",
        db_column="symbol",
        related_name="metric_snapshots",
    )
    fiscal_year = models.IntegerField(db_index=True)
    metric_code = models.ForeignKey(
        "metrics.MetricDefinition",
        on_delete=models.CASCADE,
        db_column="metric_code",
        related_name="snapshots",
    )

    metric_value = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )

    # 데이터 품질
    is_fallback_used = models.BooleanField(default=False)
    fallback_reason = models.CharField(max_length=200, blank=True)
    quality_flag = models.CharField(
        max_length=20,
        default="ok",
        choices=[
            ("ok", "OK"),
            ("insufficient_data", "Insufficient Data"),
            ("null_denominator", "Null Denominator"),
            ("stale", "Stale Data"),
            ("fallback", "Fallback Used"),
        ],
    )

    # 값 상태 판정 (배치에서 판정, 프론트에서 표시 분기 기준)
    value_status = models.CharField(
        max_length=20,
        default="normal",
        choices=[
            ("normal", "정상"),
            ("missing", "데이터 누락"),
            ("not_applicable", "해당 없음"),
            ("unstable", "값 불안정"),
            ("low_confidence", "신뢰도 낮음"),
        ],
    )
    exclusion_reason = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="not_applicable/unstable일 때 사유. e.g. '흑자 기업', '값 변동 과대'",
    )

    # 원천 추적
    source_detail = models.JSONField(
        default=dict, help_text='{"apis": [...], "fields": [...], "formula_version": 1}'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "metrics_company_metric_snapshot"
        unique_together = ["symbol", "fiscal_year", "metric_code"]
        indexes = [
            models.Index(fields=["symbol", "metric_code"]),
            models.Index(fields=["symbol", "fiscal_year"]),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.fiscal_year} {self.metric_code_id}: {self.metric_value}"
