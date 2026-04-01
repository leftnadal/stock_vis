"""
관계 발견 모델 (로드맵 CS-2)

CoMentionEdge: 뉴스 동시출현 쌍 (DC-5에서 축적)
PriceCoMovement: 주가 동조 분석 (CS-2-3에서 계산)
RelationConfidence: 관계 신뢰도 종합 (CS-2-4에서 판정)
"""

from django.db import models


class CoMentionEdge(models.Model):
    """
    뉴스 동시출현 쌍.
    하나의 뉴스에 2개 이상 종목이 태깅되면 모든 쌍(pair)에 대해 카운트 증가.
    """
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
    """
    주가 동조 분석. 90일 rolling correlation.
    """
    PERIOD_CHOICES = [
        ('30d', '30일'),
        ('90d', '90일'),
        ('180d', '180일'),
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
    """
    관계 신뢰도 종합. 여러 소스의 교차 검증 결과.
    confirmed 관계만 Neo4j 엣지로 동기화됨 (CS-3-2).
    """
    RELATION_STATUS_CHOICES = [
        ('confirmed', '확인됨'),
        ('suggested', '제안됨'),
        ('weak', '약함'),
        ('rejected', '기각됨'),
    ]

    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)

    # 소스별 존재 여부 (교차 검증)
    has_peer_relation = models.BooleanField(default=False)
    has_same_industry = models.BooleanField(default=False)
    has_co_mention = models.BooleanField(default=False)
    has_price_correlation = models.BooleanField(default=False)
    has_supply_chain = models.BooleanField(default=False)
    has_etf_theme = models.BooleanField(default=False)

    source_count = models.IntegerField(default=0, help_text='True인 소스 개수')
    confidence_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.0,
        help_text='0.0~1.0 종합 신뢰도'
    )
    relation_status = models.CharField(
        max_length=20, choices=RELATION_STATUS_CHOICES, default='suggested',
    )

    # Neo4j 동기화
    synced_to_neo4j = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_relation_confidence'
        unique_together = ['symbol_a', 'symbol_b']
        indexes = [
            models.Index(fields=['symbol_a']),
            models.Index(fields=['relation_status']),
            models.Index(fields=['-confidence_score']),
        ]

    def __str__(self):
        return f"{self.symbol_a} ↔ {self.symbol_b}: {self.relation_status} ({self.source_count} sources)"
