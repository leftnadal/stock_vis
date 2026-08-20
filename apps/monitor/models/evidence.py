"""ClaimEvidence — Claim 근거 (RECON-SWAP-0813 PART 1, v0).

Claim(구 thesis 주장)의 assertion은 자유텍스트라 근거 구조가 없었다. ClaimEvidence는
Claim 1건에 N개 부착되는 근거로, 자동형(kind=auto, 지표 z 임계 대조)과 수동형
(kind=manual, 서술+재확인 주기) 2종을 단일 테이블에 kind로 구분해 담는다(과설계 금지).

additive 신규 테이블 — 기존 Claim 모델·데이터 무접촉.
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.monitor.models.indicator import MonitorIndicator
from apps.monitor.models.monitor import Claim


class ClaimEvidence(models.Model):
    class Kind(models.TextChoices):
        AUTO = "auto", "자동(지표)"
        MANUAL = "manual", "수동(서술)"

    class Operator(models.TextChoices):
        GTE = "gte", ">="
        LTE = "lte", "<="
        GT = "gt", ">"
        LT = "lt", "<"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="evidences")
    kind = models.CharField(max_length=8, choices=Kind.choices)

    # 자동형(kind=auto) — 지표 z 임계 대조. 예: "12-1 모멘텀 z ≥ +0.3, 유예 10거래일".
    # indicator=SET_NULL(Claim.resolved_by와 동일 관례) — 지표 삭제 후에도 근거 행 보존.
    indicator = models.ForeignKey(
        MonitorIndicator,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claim_evidences",
        help_text="자동형 대상 지표",
    )
    operator = models.CharField(
        max_length=4, choices=Operator.choices, null=True, blank=True,
        help_text="자동형 비교 연산자(raw_z 대상)",
    )
    threshold = models.FloatField(
        null=True, blank=True, help_text="자동형 임계값(raw_z 대상)"
    )
    grace_days = models.PositiveIntegerField(
        default=5, help_text="자동형 유예 거래일 수(연속 위반 허용 한도)"
    )

    # 수동형(kind=manual) — 서술 + 재확인 주기. 예: "AI 인프라 테마 열기 지속".
    description = models.TextField(blank=True, default="", help_text="수동형 서술")
    recheck_period_days = models.PositiveIntegerField(
        default=90, help_text="수동형 재확인 주기(일)"
    )
    last_confirmed_at = models.DateField(
        null=True, blank=True, help_text="수동형 마지막 확인일"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"evidence({self.kind}) @ {self.claim_id}"

    def clean(self):
        errors = {}
        if self.kind == self.Kind.AUTO:
            if self.indicator_id is None:
                errors["indicator"] = "자동형 근거는 indicator가 필요합니다."
            if not self.operator:
                errors["operator"] = "자동형 근거는 operator가 필요합니다."
            if self.threshold is None:
                errors["threshold"] = "자동형 근거는 threshold가 필요합니다."
        elif self.kind == self.Kind.MANUAL:
            if not self.description:
                errors["description"] = "수동형 근거는 description이 필요합니다."
        if errors:
            raise ValidationError(errors)
