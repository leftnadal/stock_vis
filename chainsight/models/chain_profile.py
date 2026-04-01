from django.db import models
from django.contrib.postgres.fields import ArrayField


class CompanyChainProfile(models.Model):
    """
    Chain Sight 기업 프로파일 집약.
    모든 chainsight 테이블 + validation.CategoryScore에서 요약.
    그래프 DB 노드 속성으로 투영되는 원천 (AGE MVP, 추후 backend-swappable).
    """
    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='chain_profile',
    )

    # sensitivity 요약
    rate_sensitivity = models.CharField(max_length=10, blank=True)
    forex_sensitivity = models.CharField(max_length=10, blank=True)
    commodity_sensitivity = models.CharField(max_length=10, blank=True)
    regulation_type = models.CharField(max_length=50, blank=True)
    beta = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    # growth_stage 요약
    growth_stage = models.CharField(max_length=30, blank=True)
    revenue_cagr_3y = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # capital_dna 요약
    capital_type = models.CharField(max_length=30, blank=True)
    net_cash_position = models.BigIntegerField(null=True, blank=True)

    # insider_signal 요약
    smart_money_signal = models.CharField(max_length=20, blank=True)

    # revenue_structure 요약
    top_segment = models.CharField(max_length=100, blank=True)
    top_segment_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    china_revenue_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    customer_concentration_risk = models.CharField(max_length=10, blank=True)
    business_model_type = models.CharField(max_length=20, blank=True)

    # narrative 요약
    primary_narrative = models.CharField(max_length=100, blank=True)
    theme_tags = ArrayField(
        models.CharField(max_length=50),
        default=list, blank=True,
    )
    narrative_sentiment = models.CharField(max_length=10, blank=True)

    # validation score 요약
    score_profitability = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_growth = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_financial_structure = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overall_grade = models.CharField(max_length=5, blank=True)

    # 메타
    profile_completeness = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        help_text='0.0~1.0 채워진 필드 비율'
    )
    last_updated = models.DateTimeField(auto_now=True)

    # Neo4j 동기화 (CS-3-1)
    neo4j_synced = models.BooleanField(default=False, db_index=True)
    neo4j_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'chainsight_chain_profile'

    def __str__(self):
        return f"{self.symbol_id}: {self.growth_stage} / {self.overall_grade}"
