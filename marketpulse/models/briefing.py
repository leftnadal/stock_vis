"""Market Pulse v2 LLM 브리핑 모델 (PR-A2)"""
from django.db import models


class BriefingLog(models.Model):
    class Status(models.TextChoices):
        OK = 'OK', 'OK'
        INSUFFICIENT_DATA = 'INSUFFICIENT_DATA', 'Insufficient Data'
        REFUSED = 'REFUSED', 'LLM Refused'
        FAILED = 'FAILED', 'Failed'

    date = models.DateField(db_index=True)
    model_version = models.CharField(max_length=50, default='gemini-2.5-flash')

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OK)

    headline = models.CharField(max_length=300, blank=True, default='')
    content = models.TextField(blank=True, default='')

    inputs_summary = models.JSONField(default=dict, blank=True)

    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mp_briefing_log'
        verbose_name = 'Briefing Log'
        verbose_name_plural = 'Briefing Logs'
        unique_together = [('date', 'model_version')]
        ordering = ['-date']

    def __str__(self) -> str:
        return f'{self.date} ({self.model_version}) — {self.status}'
