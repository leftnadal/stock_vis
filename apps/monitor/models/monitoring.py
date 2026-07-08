"""Monitor 스냅샷 모델 (MON-P2-S2).

MonitorSnapshot = 특정 시점의 Monitor 종합 점수·상태 스냅샷(구 ThesisSnapshot).
상태기(state machine)의 score_history·추세 판정 입력이 된다.
"""
import uuid

from django.db import models

from apps.monitor.models.monitor import Monitor


class MonitorSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(
        Monitor, on_delete=models.CASCADE, related_name="snapshots"
    )
    asof_date = models.DateField()
    overall_score = models.FloatField()
    state = models.CharField(max_length=20, choices=Monitor.State.choices)
    # 유효 지표 비율(0~1) — 상태기 data_coverage 입력
    data_coverage = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-asof_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["monitor", "asof_date"], name="uniq_snapshot_monitor_asof"
            )
        ]

    def __str__(self):
        return f"{self.monitor_id} snapshot @ {self.asof_date} ({self.overall_score})"
