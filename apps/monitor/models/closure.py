"""마감 회고·동결 모델 (MON-CLOSE-UI Phase 1).

- ClaimIndicatorResult: 가설 마감 시 전제(=지표)별 hit/miss 결과 (①의 핵심, 조인 모델).
  전제 계층은 D-MONITOR-REBUILD에서 제거됨 → 지표로 피벗. categorical + FK라 후속
  전제별 승률·캘리브레이션 학습 루프가 붙을 수 있다.
- ClosureSnapshot: 마감 시점 종합점수·지표값·달위상을 불변 박제 (④ 동결). 주기·가변
  MonitorSnapshot과 별개 슬롯 — update 경로 미제공(생성만).
"""
import uuid

from django.db import models

from apps.monitor.models.indicator import MonitorIndicator
from apps.monitor.models.monitor import Claim


class ClaimIndicatorResult(models.Model):
    class Result(models.TextChoices):
        HIT = "hit", "Hit"
        PARTIAL = "partial", "Partial"
        MISS = "miss", "Miss"
        NA = "na", "N/A"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(
        Claim, on_delete=models.CASCADE, related_name="indicator_results"
    )
    indicator = models.ForeignKey(MonitorIndicator, on_delete=models.CASCADE)
    result = models.CharField(max_length=8, choices=Result.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "indicator"], name="uniq_claim_indicator_result"
            )
        ]

    def __str__(self):
        return f"{self.claim_id}·{self.indicator_id}={self.result}"


class ClosureSnapshot(models.Model):
    """마감 1회/가설의 불변 동결 슬롯. 생성만 — update 경로 미제공."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.OneToOneField(
        Claim, on_delete=models.CASCADE, related_name="closure_snapshot"
    )
    overall_score = models.FloatField(help_text="마감 시점 [-1,1] 종합점수(동결)")
    payload = models.JSONField(
        default=dict, help_text="지표별 최종값·달위상·스파크라인 시리즈 동결"
    )
    frozen_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"closure({self.claim_id}) @ {self.overall_score}"
