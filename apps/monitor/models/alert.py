"""AlertEvent 모델 (MON-P3-ALERT).

상태 전이(from_state→to_state)를 이벤트로 기록한다. refresh_monitors_task의 evaluate
직후 같은 태스크 내부에서 감지·기록(신규 beat 없음). `(monitor, from_state, to_state, asof)`
unique → 재실행 멱등. 쿨다운 억제는 `is_suppressed`로 표기(기록은 하되 배지·다이제스트
개별 행에서 숨김).
"""
import uuid

from django.db import models

from apps.monitor.models.monitor import Monitor


class AlertEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(
        Monitor, on_delete=models.CASCADE, related_name="alerts"
    )
    from_state = models.CharField(max_length=20, choices=Monitor.State.choices)
    to_state = models.CharField(max_length=20, choices=Monitor.State.choices)
    asof = models.DateField()
    score = models.FloatField()
    # 악화 여부(상태 심각도 랭크 하락) — 인앱 배지는 악화만 카운트(결정 1-C)
    is_deterioration = models.BooleanField()
    # 쿨다운 억제: 동일 방향 직전 알림 후 3거래일 내 재발 → 기록하되 배지·다이제스트 숨김
    is_suppressed = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-asof", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["monitor", "from_state", "to_state", "asof"],
                name="uniq_alert_monitor_transition_asof",
            )
        ]
        indexes = [
            models.Index(fields=["monitor", "-asof"]),
            models.Index(fields=["is_deterioration", "read"]),
        ]

    def __str__(self):
        return f"{self.monitor_id}: {self.from_state}→{self.to_state} @ {self.asof}"
