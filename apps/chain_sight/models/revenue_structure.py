from django.db import models


class CompanyRevenueStructure(models.Model):
    """매출 구조 (Revenue DNA). SEC 10-K 파싱 + LLM 보조."""

    EXTRACTION_METHOD_CHOICES = [
        ("fmp_api", "FMP API"),
        ("10k_llm", "10-K LLM Parsing"),
        ("manual", "Manual"),
    ]
    BUSINESS_MODEL_CHOICES = [
        ("b2b", "B2B"),
        ("b2c", "B2C"),
        ("mixed", "Mixed"),
        ("unknown", "Unknown"),
    ]
    CONCENTRATION_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    symbol = models.OneToOneField(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        primary_key=True,
        related_name="revenue_structure",
    )

    # 사업 부문별 매출
    segments = models.JSONField(
        default=list,
        help_text='[{"name":"iPhone","revenue_pct":52,"trend":"stable"}, ...]',
    )

    # 지역별 매출
    geographic_revenue = models.JSONField(
        default=list, help_text='[{"region":"Americas","pct":42}, ...]'
    )

    # 고객 집중도 (10-K 공시)
    major_customers = models.JSONField(
        default=list, help_text='[{"customer":"Apple","revenue_pct":22}, ...]'
    )
    customer_concentration_risk = models.CharField(
        max_length=10, blank=True, choices=CONCENTRATION_CHOICES
    )

    # B2B vs B2C
    business_model_type = models.CharField(
        max_length=20, blank=True, choices=BUSINESS_MODEL_CHOICES
    )

    # 원자재 의존도
    commodity_exposures = models.JSONField(
        default=list,
        help_text='[{"commodity":"lithium","exposure":"high","context":"battery"}, ...]',
    )

    # 파싱 메타
    source_filing = models.CharField(max_length=100, blank=True)
    extraction_method = models.CharField(
        max_length=20, blank=True, choices=EXTRACTION_METHOD_CHOICES
    )
    extraction_confidence = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True, help_text="0.0 ~ 1.0"
    )
    last_parsed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chainsight_revenue_structure"

    def __str__(self):
        return f"{self.symbol_id}: {len(self.segments)} segments"
