import uuid

from django.conf import settings
from django.db import models


class Thesis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='theses',
    )

    # 가설 내용
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    direction = models.CharField(
        max_length=10,
        choices=[
            ('bearish', 'Bearish'),
            ('bullish', 'Bullish'),
            ('neutral', 'Neutral'),
        ],
    )
    target = models.CharField(max_length=100)
    target_type = models.CharField(
        max_length=20,
        choices=[
            ('index', 'Index'),
            ('stock', 'Stock'),
            ('sector', 'Sector'),
            ('macro', 'Macro'),
        ],
    )

    # 시점/강도
    expected_timeframe = models.CharField(max_length=50, blank=True)
    expected_magnitude = models.CharField(max_length=50, blank=True)
    target_date_start = models.DateField(null=True, blank=True)
    target_date_end = models.DateField(null=True, blank=True)

    # 가설 유형
    thesis_type = models.CharField(
        max_length=20,
        choices=[
            ('event', 'Event-driven'),
            ('trend', 'Trend'),
            ('comparison', 'Comparison'),
            ('divergence', 'Divergence'),
            ('custom', 'Custom'),
        ],
    )

    # 진입 경로
    entry_source = models.CharField(
        max_length=20,
        choices=[
            ('news', 'Today Issue'),
            ('free_input', 'Free Input'),
            ('popular', 'Popular Thesis'),
            ('template', 'Template'),
            ('chainsight', 'Chain Sight'),
        ],
    )
    source_news = models.ForeignKey(
        'news.NewsArticle',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='thesis_sources',
    )
    copied_from = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='copies',
    )

    # 상태
    status = models.CharField(
        max_length=20,
        default='setting_up',
        choices=[
            ('setting_up', 'Setting Up'),
            ('active', 'Active'),
            ('closed', 'Closed'),
            ('paused', 'Paused'),
        ],
    )
    current_state = models.CharField(
        max_length=20,
        default='warming_up',
        choices=[
            ('warming_up', 'Warming Up'),
            ('active', 'Active'),
            ('strengthening', 'Strengthening'),
            ('weakening', 'Weakening'),
            ('critical', 'Critical'),
            ('expired', 'Expired'),
            ('needs_review', 'Needs Review'),
            ('paused', 'Paused'),
        ],
    )
    current_score = models.FloatField(null=True, blank=True)

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # 마감 결과
    outcome = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[
            ('correct', 'Correct'),
            ('incorrect', 'Incorrect'),
            ('neutral', 'Neutral'),
        ],
    )
    outcome_note = models.TextField(blank=True)

    # v2.3.2 추가 필드 (수학 모델 Section 9)
    premise_universe_ids = models.JSONField(default=list)
    indicator_universe_ids = models.JSONField(default=list)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_direction_display()}] {self.title}"


class ThesisPremise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thesis = models.ForeignKey(
        Thesis,
        on_delete=models.CASCADE,
        related_name='premises',
    )

    content = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=[
            ('macro', 'Macro'),
            ('sector', 'Sector'),
            ('company', 'Company'),
            ('technical', 'Technical'),
            ('sentiment', 'Sentiment'),
            ('custom', 'Custom'),
        ],
    )
    weight = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # v2.3.2 추가 필드
    is_paused = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['thesis', 'is_active']),
        ]

    def __str__(self):
        return f"{self.thesis.title} - {self.content[:50]}"
