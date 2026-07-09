"""Monitor 허브 핵심 모델 (D-MONITOR-REBUILD, P2).

Monitor{scope} = 개인화 모니터링 대상 (내가 등록한 대상 + 내 규칙 + 상태 기억).
Claim = Monitor에 부착되는 주장·마감 (구 thesis 개념의 재정의).
"""
import uuid

from django.conf import settings
from django.db import models


class Monitor(models.Model):
    """사용자가 등록한 모니터링 대상. scope에 따라 종목/섹터/테마/펀드/시장을 가리킨다."""

    class Scope(models.TextChoices):
        MARKET = "market", "Market"
        SECTOR = "sector", "Sector"
        THEME = "theme", "Theme"
        FUND = "fund", "Fund"
        STOCK = "stock", "Stock"

    class Status(models.TextChoices):
        SETTING_UP = "setting_up", "Setting Up"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    class State(models.TextChoices):
        """상태기(state machine) 판정값 — status(사용자 의도)와 별개의 자동 판정."""

        WARMING_UP = "warming_up", "데이터 수집 중"
        ACTIVE = "active", "활성 관제 중"
        STRENGTHENING = "strengthening", "강화 추세"
        WEAKENING = "weakening", "약화 추세"
        CRITICAL = "critical", "주의 필요"
        NEEDS_REVIEW = "needs_review", "점검 필요"
        EXPIRED = "expired", "기간 만료"
        PAUSED = "paused", "일시정지"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="monitors"
    )
    scope = models.CharField(max_length=16, choices=Scope.choices)
    # 정규화된 대상 참조: stock=심볼(대문자), sector=섹터키, theme=바스켓 id, fund=ETF 심볼, market=지수키
    target_ref = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.SETTING_UP
    )
    # 상태기 자동 판정 (thesis_state_machine 이식)
    current_state = models.CharField(
        max_length=20, choices=State.choices, default=State.WARMING_UP
    )
    # 관제 종료 목표일 (없으면 무기한 — 90일+ 시 needs_review)
    target_date_end = models.DateField(null=True, blank=True)
    # 마감 제안 (MON-P3-ALERT): danger(critical) 연속 거래일 카운터 + 10일↑ 제안 플래그.
    # 제안만 — 마감은 사용자 수동 확정(결정 3-B). 배지 UI는 CLOSE 트랙 몫.
    danger_streak = models.IntegerField(default=0)
    close_suggested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "scope", "target_ref"],
                name="uniq_monitor_user_scope_target",
            )
        ]
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self):
        return f"{self.name} [{self.scope}:{self.target_ref}]"


class Claim(models.Model):
    """Monitor에 부착되는 주장 + 마감. 검증 결과(outcome)로 회고를 남긴다."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLVED = "resolved", "Resolved"

    class Outcome(models.TextChoices):
        PENDING = "pending", "Pending"
        VALIDATED = "validated", "Validated"
        INVALIDATED = "invalidated", "Invalidated"
        INCONCLUSIVE = "inconclusive", "Inconclusive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(
        Monitor, on_delete=models.CASCADE, related_name="claims"
    )
    assertion = models.TextField(help_text="주장")
    deadline = models.DateField(null=True, blank=True, help_text="마감")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    outcome = models.CharField(
        max_length=16, choices=Outcome.choices, default=Outcome.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Claim({self.assertion[:30]}) @ {self.monitor_id}"
