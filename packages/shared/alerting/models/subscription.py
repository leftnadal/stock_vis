"""AlertSubscription — 알림 구독(누가·어떤 이벤트·어느 채널·어디로).

user는 user_id 스코프 이음새(방향 B) — null 허용(시스템/운영 구독은 user 없이 destination만).
Slice 0에서는 seed_alert_subscription 커맨드로 email destination만 시드한다.
"""
from __future__ import annotations

from django.db import models


class AlertSubscription(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alert_subscriptions",
        help_text="user_id 스코프 이음새(방향 B). null이면 시스템/운영 구독.",
    )
    source_app = models.CharField(max_length=50, db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    channel = models.CharField(max_length=20, default="email")
    destination = models.CharField(max_length=254, help_text="채널별 목적지(이메일 주소 등)")
    enabled = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alerting_subscription"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source_app", "event_type", "enabled"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_app", "event_type", "channel", "destination"],
                name="uq_alerting_subscription_target",
            ),
        ]

    def __str__(self) -> str:
        status = "on" if self.enabled else "off"
        return f"[{status}] {self.source_app}:{self.event_type} → {self.channel}:{self.destination}"
