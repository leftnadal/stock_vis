"""Market Pulse v2 이상 신호 모델 (PR-A2)"""

from django.db import models


class AnomalySignalLog(models.Model):
    class RuleId(models.TextChoices):
        R02_CONCENTRATION = "R02", "Concentration Extreme"
        R04_VIX_SPIKE = "R04", "VIX Spike"
        R09_SECTOR_Z = "R09", "Sector Extreme Z-score"
        R12_DISPERSION = "R12", "Dispersion Spike"

    class Mode(models.TextChoices):
        ANOMALY = "ANOMALY", "Anomaly"
        HYBRID = "HYBRID", "Hybrid"
        CALM = "CALM", "Calm"

    rule_id = models.CharField(max_length=10, choices=RuleId.choices, db_index=True)
    triggered_at = models.DateTimeField(db_index=True)

    inputs = models.JSONField(default=dict)
    threshold = models.JSONField(default=dict)

    paired_news = models.ForeignKey(
        "marketpulse.MarketPulseNews",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paired_anomaly_signals",
    )

    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CALM)

    headline = models.CharField(max_length=300, blank=True, default="")
    body = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_anomaly_signal_log"
        verbose_name = "Anomaly Signal Log"
        verbose_name_plural = "Anomaly Signal Logs"
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(
                fields=["rule_id", "-triggered_at"], name="mp_anom_rule_trig_idx"
            ),
            models.Index(
                fields=["mode", "-triggered_at"], name="mp_anom_mode_trig_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.rule_id}] {self.mode} @ {self.triggered_at:%Y-%m-%d %H:%M}"
