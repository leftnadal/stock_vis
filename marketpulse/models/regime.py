"""Market Pulse v2 Regime Snapshot 모델 (PR-A2)"""
from django.db import models


class RegimeSnapshot(models.Model):
    class Regime(models.TextChoices):
        BULL_EXPANSION = 'BULL_EXPANSION', '강세 확장'
        LATE_BULL = 'LATE_BULL', '상승 후반 경계'
        TRANSITION = 'TRANSITION', '전환'
        BEAR_CONTRACTION = 'BEAR_CONTRACTION', '약세 수축'
        CRISIS = 'CRISIS', '위기'

    class Status(models.TextChoices):
        OK = 'OK', 'OK'
        INSUFFICIENT_DATA = 'INSUFFICIENT_DATA', 'Insufficient Data'
        STALE = 'STALE', 'Stale'
        FAILED = 'FAILED', 'Failed'

    date = models.DateField(db_index=True)
    snapshot_time = models.DateTimeField(db_index=True)

    regime = models.CharField(max_length=20, choices=Regime.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OK)

    inputs = models.JSONField(default=dict)
    coverage = models.FloatField(default=0.0)
    fired_rules = models.JSONField(default=list)

    previous_regime = models.CharField(
        max_length=20, choices=Regime.choices, blank=True, default='',
    )
    hysteresis_streak = models.PositiveSmallIntegerField(default=0)

    headline = models.CharField(max_length=300, blank=True, default='')
    summary = models.TextField(blank=True, default='')

    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mp_regime_snapshot'
        verbose_name = 'Regime Snapshot'
        verbose_name_plural = 'Regime Snapshots'
        ordering = ['-snapshot_time']
        indexes = [
            models.Index(fields=['date', 'is_finalized'], name='mp_regime_date_fin_idx'),
        ]
        unique_together = [('date',)]

    def __str__(self) -> str:
        return f'{self.date} {self.regime} (cov={self.coverage:.2f})'
