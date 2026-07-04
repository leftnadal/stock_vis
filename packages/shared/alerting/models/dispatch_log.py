"""AlertDispatchLog — 이벤트 1건당 발송 기록(dedup 단위).

dedup_key unique — 같은 이벤트(예: 같은 날 같은 국면 전환)가 15분 주기로 재트리거돼도
행 1개만 유지(row 스팸 방지). status=sent면 재발송 억제, failed면 다음 사이클 재시도.
클래스명 AlertDispatchLog = services/news의 기존 AlertLog(ops 인시던트, 도메인 직교)와 충돌 회피(D-ALERTS-NAMING).
"""
from __future__ import annotations

from django.db import models


class AlertDispatchLog(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    dedup_key = models.CharField(max_length=255, unique=True)
    source_app = models.CharField(max_length=50, db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    payload = models.JSONField(default=dict)
    subscription = models.ForeignKey(
        "alerting.AlertSubscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_logs",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.FAILED, db_index=True
    )
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerting_dispatch_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["source_app", "event_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.dedup_key}"
