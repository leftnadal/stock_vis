"""
관계 발견 모델 (로드맵 CS-2)

CoMentionEdge: 뉴스 동시출현 쌍 (DC-5에서 축적)
PriceCoMovement: 주가 동조 분석 (CS-2-3에서 계산)
RelationConfidence v2.1: 관계 신뢰도 종합 (CS-2-4에서 판정)
"""

from django.db import models


class CoMentionEdge(models.Model):
    """뉴스 동시출현 쌍."""
    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)
    co_mention_count = models.IntegerField(default=0)
    last_co_mention_date = models.DateField(null=True, blank=True)
    first_co_mention_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_co_mention_edge'
        unique_together = ['symbol_a', 'symbol_b']
        indexes = [
            models.Index(fields=['symbol_a']),
            models.Index(fields=['symbol_b']),
            models.Index(fields=['-co_mention_count']),
        ]

    def __str__(self):
        return f"{self.symbol_a} ↔ {self.symbol_b}: {self.co_mention_count}회"


class PriceCoMovement(models.Model):
    """주가 동조 분석. 90일 rolling correlation."""
    PERIOD_CHOICES = [
        ('30d', '30일'), ('90d', '90일'), ('180d', '180일'),
    ]

    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)
    correlation = models.DecimalField(max_digits=5, decimal_places=4)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='90d')
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chainsight_price_co_movement'
        unique_together = ['symbol_a', 'symbol_b', 'period']
        indexes = [
            models.Index(fields=['symbol_a']),
            models.Index(fields=['-correlation']),
        ]

    def __str__(self):
        return f"{self.symbol_a} ↔ {self.symbol_b}: {self.correlation} ({self.period})"


class RelationConfidence(models.Model):
    """관계 신뢰도 종합 v2.1. confirmed 관계만 Neo4j 엣지로 동기화 (CS-3-2)."""

    RELATION_TYPE_CHOICES = [
        ('PEER_OF', 'Peer'),
        ('SUPPLIES_TO', 'Supplies To'),
        ('CO_MENTIONED', 'Co-mentioned'),
        ('PRICE_CORRELATED', 'Price Correlated'),
        ('HAS_THEME', 'Has Theme'),
        ('COMPETES_WITH', 'Competes With'),
        ('HELD_BY_SAME_FUND', 'Held by Same Fund'),
    ]
    RELATION_CATEGORY_CHOICES = [
        ('truth', 'Truth'), ('market', 'Market'),
    ]
    DIRECTION_CHOICES = [
        ('a→b', 'A to B'), ('b→a', 'B to A'), ('both', 'Undirected'),
    ]
    RELATION_STATUS_CHOICES = [
        ('hidden', 'Hidden'), ('weak', 'Weak'), ('probable', 'Probable'),
        ('confirmed', 'Confirmed'), ('stale', 'Stale'),
    ]

    # 식별
    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)
    relation_type = models.CharField(max_length=30, choices=RELATION_TYPE_CHOICES)
    relation_category = models.CharField(max_length=10, choices=RELATION_CATEGORY_CHOICES, default='truth')
    canonical_direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES, default='both')

    # 상태 (5단계)
    relation_status = models.CharField(max_length=12, choices=RELATION_STATUS_CHOICES, default='hidden')

    # 점수 (3단)
    truth_score = models.FloatField(default=0)
    market_score = models.FloatField(null=True, blank=True)
    investment_relevance = models.FloatField(null=True, blank=True)

    # 증거
    evidence_tier_best = models.IntegerField(default=3)
    evidence_count_total = models.IntegerField(default=0)
    evidence_count_independent = models.IntegerField(default=0)
    evidence_sources = models.JSONField(default=dict, blank=True)

    # 빠른 필터용 bool 7개
    has_peer_source = models.BooleanField(default=False)
    has_industry_source = models.BooleanField(default=False)
    has_supply_chain_source = models.BooleanField(default=False)
    has_news_source = models.BooleanField(default=False)
    has_price_source = models.BooleanField(default=False)
    has_etf_source = models.BooleanField(default=False)
    has_llm_source = models.BooleanField(default=False)

    # 설명
    relation_basis_summary = models.TextField(blank=True, default='')

    # 시간
    first_observed_at = models.DateTimeField(auto_now_add=True)
    last_observed_at = models.DateTimeField(auto_now=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    stale_threshold_days = models.IntegerField(default=90)

    # 상태 전이 추적 (시드 선정용)
    previous_status = models.CharField(
        max_length=12, choices=RELATION_STATUS_CHOICES,
        blank=True, default='',
        help_text='직전 상태. 시드 선정 시 relation_upgrade/downgrade 판단용.',
    )

    # 동기화 (audit P0 #9 — neo4j_dirty 단일 소스. synced_to_neo4j 제거 2026-04-29)
    neo4j_dirty = models.BooleanField(
        default=True, db_index=True,
        help_text='True이면 Neo4j 동기화 필요. save() 시 자동 True.',
    )
    neo4j_synced_at = models.DateTimeField(null=True, blank=True)
    score_version = models.CharField(max_length=10, default='2.1')

    class Meta:
        db_table = 'chainsight_relation_confidence'
        unique_together = ['symbol_a', 'symbol_b', 'relation_type']
        indexes = [
            models.Index(fields=['relation_status']),
            models.Index(fields=['relation_type']),
            models.Index(fields=['neo4j_dirty']),
        ]

    def save(self, *args, **kwargs):
        # 상태 전이 추적: DB에서 기존 상태 읽어서 previous_status에 보존
        if self.pk:
            try:
                old = RelationConfidence.objects.filter(pk=self.pk).values_list(
                    'relation_status', flat=True
                ).first()
                if old and old != self.relation_status:
                    self.previous_status = old
            except Exception:
                pass
        # neo4j_dirty 자동 세팅 (bulk_update에서는 save() 미호출되므로 수동 관리 필요)
        self.neo4j_dirty = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.symbol_a} → {self.symbol_b} [{self.relation_type}]: {self.relation_status}"
