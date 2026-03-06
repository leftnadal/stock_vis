import uuid

from django.db import models


class ThesisIndicator(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thesis = models.ForeignKey(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        related_name='indicators',
    )
    premise = models.ForeignKey(
        'thesis.ThesisPremise',
        on_delete=models.CASCADE,
        related_name='indicators',
        null=True,
        blank=True,
    )

    # 지표 정의
    name = models.CharField(max_length=100)
    indicator_type = models.CharField(
        max_length=30,
        choices=[
            ('market_data', 'Market Data'),
            ('macro', 'Macro Economic'),
            ('sentiment', 'News Sentiment'),
            ('technical', 'Technical'),
            ('fundamental', 'Fundamental'),
            ('custom', 'Custom'),
        ],
    )

    # 데이터 소스
    data_source = models.CharField(
        max_length=50,
        choices=[
            ('fmp', 'FMP'),
            ('fred', 'FRED'),
            ('news_sentiment', 'News Sentiment'),
            ('manual', 'Manual'),
            ('custom', 'Custom'),
        ],
    )
    data_params = models.JSONField(default=dict)

    # 방향 정의
    support_direction = models.CharField(
        max_length=10,
        choices=[
            ('positive', 'Positive'),
            ('negative', 'Negative'),
        ],
    )

    # 가중치/활성
    weight = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)

    # 현재 상태
    current_score = models.FloatField(null=True, blank=True)
    current_degree = models.FloatField(null=True, blank=True)
    current_color = models.CharField(max_length=10, blank=True)
    current_label = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # v2.3.2 추가 필드 (수학 모델 Section 9)
    epsilon = models.FloatField(default=0.0001)
    window = models.IntegerField(default=60)
    decay = models.FloatField(default=0.95)
    min_valid_value = models.FloatField(null=True, blank=True)
    max_valid_value = models.FloatField(null=True, blank=True)
    max_change_pct = models.FloatField(null=True, blank=True)
    allow_extreme_jump = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)
    override_score = models.FloatField(null=True, blank=True)

    @property
    def latest_validated_value(self):
        """마지막으로 validation 통과한 reading의 value (수학 모델 Section 2.2)"""
        reading = self.readings.filter(
            validation_status__in=['ok', 'extreme_jump_allowed']
        ).order_by('-asof').first()
        return reading.value if reading else None

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thesis', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_indicator_type_display()})"


class IndicatorReading(models.Model):
    VALIDATION_STATUS_CHOICES = [
        ('ok', 'OK'),
        ('null_value', 'Null Value'),
        ('non_finite', 'Non-Finite'),
        ('below_minimum', 'Below Minimum'),
        ('above_maximum', 'Above Maximum'),
        ('stale_data', 'Stale Data'),
        ('extreme_jump', 'Extreme Jump'),
        ('extreme_jump_allowed', 'Extreme Jump Allowed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    indicator = models.ForeignKey(
        ThesisIndicator,
        on_delete=models.CASCADE,
        related_name='readings',
    )

    value = models.FloatField()
    raw_value = models.FloatField()
    asof = models.DateTimeField()

    # v2.3.2 추가 필드
    validation_status = models.CharField(
        max_length=25,
        default='ok',
        choices=VALIDATION_STATUS_CHOICES,
    )
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['indicator', 'asof']
        ordering = ['-asof']
        indexes = [
            models.Index(fields=['indicator', '-asof']),
            models.Index(fields=['indicator', 'validation_status', '-asof']),
        ]

    def __str__(self):
        return f"{self.indicator.name} @ {self.asof}: {self.value}"
