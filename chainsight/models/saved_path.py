"""
SavedPath / PathAction — CS-6-1 (v1.4 확정 스키마)

사용자가 탐색한 경로를 저장하고 액션을 기록하는 모델.
"""

import uuid

from django.conf import settings
from django.db import models


class SavedPath(models.Model):
    class Status(models.TextChoices):
        WATCHING = "watching", "Watching"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="saved_paths",
    )
    # MVP: 단일 사용자 가정 — user nullable

    path_nodes = models.JSONField(help_text='ticker 배열. 예: ["NVDA", "TSM", "ASML"]')
    summary_path = models.JSONField(
        blank=True, null=True, help_text="landmark ticker 배열"
    )
    path_signature = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        help_text='경로 성격 태그: "공급망 중심 · 반도체 장비"',
    )
    edge_snapshot = models.JSONField(
        blank=True, null=True, help_text="저장 시점 관계 스냅샷"
    )
    why_now_snapshot = models.JSONField(blank=True, null=True)

    source_center = models.CharField(max_length=10, blank=True, null=True)
    source_slot = models.CharField(max_length=40, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WATCHING,
        db_index=True,
    )
    recheck_count = models.PositiveIntegerField(
        default=0,
        help_text="Recheck 횟수. 2회 이상 + 24h → watching→active",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "chainsight_saved_path"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["status", "-updated_at"]),
        ]

    def __str__(self):
        nodes = self.path_nodes or []
        path_str = " → ".join(nodes[:4])
        if len(nodes) > 4:
            path_str += f" … ({len(nodes)})"
        return f"[{self.status}] {path_str}"


class PathAction(models.Model):
    class ActionType(models.TextChoices):
        WATCH = "watch", "Watch"
        EXPAND = "expand", "Expand"
        ALTERNATIVES = "alternatives", "Alternatives"
        RECHECK = "recheck", "Recheck"
        ARCHIVE = "archive", "Archive"
        RESOLVE = "resolve", "Resolve"

    saved_path = models.ForeignKey(
        SavedPath,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "chainsight_path_action"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["saved_path", "-created_at"]),
            models.Index(fields=["action_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.action_type} @ {self.created_at}"
