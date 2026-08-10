"""AdvisorNote — ADVISOR 브리핑 동결 기록 (MON-P4-LA, D-MON-P4-LA).

브리핑은 '생성 시점 사실의 동결 기록'이다. 점수는 MonitorSnapshot 정본을 인용만 하며
(재계산 금지), (monitor, asof, surface) 유일 — 존재 시 스킵(update 없음). L-A(정기
브리핑)만 이번 트랙 구현, L-B/L-C는 surface 소켓만 예약.
"""
import uuid

from django.db import models

from .monitor import Monitor


class AdvisorNote(models.Model):
    class Surface(models.TextChoices):
        L_A = "L-A", "정기 브리핑"
        L_B = "L-B", "예약(L-B)"
        L_C = "L-C", "예약(L-C)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(
        Monitor, on_delete=models.CASCADE, related_name="advisor_notes"
    )
    # 브리핑이 근거로 삼은 MonitorSnapshot의 asof(동결 시점 인용)
    asof = models.DateField()
    surface = models.CharField(
        max_length=8, choices=Surface.choices, default=Surface.L_A
    )

    headline = models.CharField(max_length=120)
    body = models.TextField()

    # 커버리지 문면 인용(불변식): n = source_n 충분 지표 수, total = 등록 지표 총수
    coverage_n = models.SmallIntegerField()
    coverage_total = models.SmallIntegerField()

    model_id = models.CharField(max_length=64)
    prompt_version = models.CharField(max_length=16)
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)

    # 2축 채점 예약 필드 — 이번 트랙 기록 로직 없음(D-MONITOR-HORIZON-ADVISOR)
    market_score = models.FloatField(null=True, blank=True)
    close_score = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-asof", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["monitor", "asof", "surface"],
                name="uniq_advisor_note_monitor_asof_surface",
            )
        ]

    def __str__(self):
        return f"{self.monitor_id} advisor[{self.surface}] @ {self.asof}"
