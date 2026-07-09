"""Monitor 지표 + 판독 모델 (MON-P2-S2).

MonitorIndicator = Monitor에 부착된 관측 지표(구 ThesisIndicator).
IndicatorReading = 지표의 시계열 판독값(구 IndicatorReading).
엔진(indicator_scorer)이 소비하는 필드 계약을 그대로 승계.
"""
import uuid

from django.db import models

from apps.monitor.models.monitor import Monitor


class MonitorIndicator(models.Model):
    class IndicatorType(models.TextChoices):
        MARKET_DATA = "market_data", "시장 데이터"
        MACRO = "macro", "거시경제"
        SENTIMENT = "sentiment", "뉴스 심리"
        TECHNICAL = "technical", "기술적 분석"
        CUSTOM = "custom", "사용자 정의"

    class SupportDirection(models.TextChoices):
        POSITIVE = "positive", "정방향(값↑ = 지지)"
        NEGATIVE = "negative", "역방향(값↓ = 지지)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(
        Monitor, on_delete=models.CASCADE, related_name="indicators"
    )
    name = models.CharField(max_length=200)
    indicator_type = models.CharField(max_length=16, choices=IndicatorType.choices)
    support_direction = models.CharField(
        max_length=8, choices=SupportDirection.choices, default=SupportDirection.POSITIVE
    )
    weight = models.FloatField(default=1.0)
    # 카탈로그 소스 키 (예: 'eod_composite'). None = 사용자 정의(수동 판독). 이식 태스크가 이 키로 EODSignal→IndicatorReading 채움.
    source_key = models.CharField(max_length=40, blank=True, default="")

    # 스코어링 파라미터 (None → indicator_scorer 기본값)
    epsilon = models.FloatField(null=True, blank=True)
    window = models.IntegerField(null=True, blank=True)
    decay = models.FloatField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    override_score = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["monitor", "is_active"])]

    def __str__(self):
        return f"{self.name} [{self.indicator_type}] @ {self.monitor_id}"


class IndicatorReading(models.Model):
    class ValidationStatus(models.TextChoices):
        OK = "ok", "정상"
        EXTREME_JUMP_ALLOWED = "extreme_jump_allowed", "극단 점프 허용"
        REJECTED = "rejected", "기각"
        PENDING = "pending", "대기"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    indicator = models.ForeignKey(
        MonitorIndicator, on_delete=models.CASCADE, related_name="readings"
    )
    value = models.FloatField(null=True, blank=True)
    asof = models.DateTimeField()
    validation_status = models.CharField(
        max_length=24, choices=ValidationStatus.choices, default=ValidationStatus.OK
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["asof"]
        indexes = [models.Index(fields=["indicator", "asof"])]
        constraints = [
            # 멱등 ingest: (지표, 판독시점) 1행 — 재실행 시 upsert(update_or_create).
            models.UniqueConstraint(
                fields=["indicator", "asof"], name="uniq_reading_indicator_asof"
            )
        ]

    def __str__(self):
        return f"{self.indicator_id} = {self.value} @ {self.asof:%Y-%m-%d}"
