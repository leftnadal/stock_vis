import uuid

from django.db import models


class ThesisSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thesis = models.ForeignKey(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        related_name='snapshots',
    )

    # v2.3.2 확정 필드
    asof_date = models.DateField()
    data_coverage = models.FloatField(default=1.0)
    universe_snapshot = models.JSONField(default=dict)
    ordered_indicator_ids = models.JSONField(default=list)

    # 기존 필드
    overall_score = models.FloatField()
    state = models.CharField(max_length=20)
    premise_scores = models.JSONField(default=dict)
    indicator_degrees = models.JSONField(default=dict)
    notable_changes = models.JSONField(default=list)
    ai_summary = models.TextField(blank=True)

    class Meta:
        unique_together = ['thesis', 'asof_date']
        ordering = ['-asof_date']

    def __str__(self):
        return f"{self.thesis.title} snapshot @ {self.asof_date}"


class ThesisAlert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('direction_flip', 'Direction Flip'),
        ('sharp_move', 'Sharp Move'),
        ('extreme_volatility', 'Extreme Volatility'),
        ('weakest_link', 'Weakest Link'),
        ('premise_divergence', 'Premise Divergence'),
        ('stale_data', 'Stale Data'),
        ('indicator_overlap', 'Indicator Overlap'),
        ('indicator_bias', 'Indicator Bias'),
        ('state_change', 'State Change'),
        ('milestone', 'Milestone'),
        ('needs_review', 'Needs Review'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thesis = models.ForeignKey(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    indicator = models.ForeignKey(
        'thesis.ThesisIndicator',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
    )

    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)

    # v2.3.2 추가 필드 (throttling)
    target_id = models.CharField(max_length=36, blank=True)
    cooldown_hours = models.IntegerField(default=24)

    # 기존 필드
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_pushed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['thesis', 'alert_type', 'target_id', '-created_at']),
            models.Index(fields=['thesis', 'is_read']),
        ]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"
