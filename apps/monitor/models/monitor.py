"""Monitor 허브 핵심 모델 (D-MONITOR-REBUILD, P2).

Monitor{scope} = 개인화 모니터링 대상 (내가 등록한 대상 + 내 규칙 + 상태 기억).
Claim = Monitor에 부착되는 주장·마감 (구 thesis 개념의 재정의).
"""
import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
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
        VALIDATED = "validated", "Validated"          # 적중
        PARTIAL = "partial", "Partial"                # 부분적중 (MON-CLOSE-UI ④)
        INVALIDATED = "invalidated", "Invalidated"    # 빗나감
        INCONCLUSIVE = "inconclusive", "Inconclusive" # 엣지(버튼 미노출)
        EXPIRED = "expired", "기한만료"                # 기한 경과·진입 미도달 (D-TIMING-DECISIONS-5 ④-B)

    class PriceZone(models.TextChoices):
        """가격 구간축 — Claim 가격 파라미터 대비 현재 종가의 위치 (D-TIMING-DECISIONS-5 ③-B).

        state_machine(신호축)과 별개의 가격축. 순수 파생값(price_zone.resolve_zone) — 저장은
        전이 감지용 직전값(last_price_zone)만. 라벨은 매수 타이밍 행동어.
        """

        EXITED = "exited", "이탈"           # close ≤ stop_price
        ENTRY = "entry", "진입 구간"         # stop < close ≤ entry
        APPROACH = "approach", "접근"        # entry < close ≤ entry×(1+버퍼)
        WAITING = "waiting", "관망"          # 버퍼 초과 ~ target 미만
        OVERHEATED = "overheated", "과열"    # close ≥ target

    class ProposedVerdict(models.TextChoices):
        """시스템 제안 판정 (마감 시점 종합점수 밴드 매핑). 최종=outcome, 델타=캘리브레이션."""

        VALIDATED = "validated", "Validated"
        PARTIAL = "partial", "Partial"
        INVALIDATED = "invalidated", "Invalidated"
        EXPIRED = "expired", "기한만료"  # 기한 경과·진입 미도달 (D-TIMING-DECISIONS-5 ④-B)

    class FactorTag(models.TextChoices):
        """회고 공통 요인 태그 (고정 enum — 자유문자열 금지)."""

        TIMING = "timing", "타이밍"
        EXT_SHOCK = "ext_shock", "외부 충격"
        INDICATOR_NOISE = "indicator_noise", "지표 노이즈"
        LUCK = "luck", "운"

    class ScenarioType(models.TextChoices):
        """시나리오 모드 (D-HOLD-DECISIONS 6). 저장 축 — 수익/손실/중립은 파생 상태(매입가 vs 종가).

        new_entry(미보유·매수 타이밍) / hold(보유 관리·매입가 앵커) / add_on(추가 매수·평단 백로그).
        """

        NEW_ENTRY = "new_entry", "신규 매수"
        HOLD = "hold", "보유 관리"
        ADD_ON = "add_on", "추가 매수"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(
        Monitor, on_delete=models.CASCADE, related_name="claims"
    )
    assertion = models.TextField(help_text="주장")
    deadline = models.DateField(null=True, blank=True, help_text="마감")

    # 시나리오 모드 (D-HOLD-DECISIONS) — 기존 10행 default=new_entry 무해 편입.
    scenario_type = models.CharField(
        max_length=16, choices=ScenarioType.choices, default=ScenarioType.NEW_ENTRY,
        help_text="시나리오 모드(신규 매수/보유 관리/추가 매수)",
    )
    # 보유 모드 확정 사실 (D-HOLD-DECISIONS 1·5) — entry_price(제안·미래)와 분리. hold zone 앵커.
    purchase_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, help_text="매입가(확정 사실)"
    )
    purchase_date = models.DateField(
        null=True, blank=True, help_text="매입일(보유 기간 원천)"
    )

    # 매수 시나리오 가격 파라미터 (D-TIMING-DECISIONS-5 ②-A, additive).
    # 전부 null=구 가설(가격 없는 Claim, 그대로 유효). 정밀도=리포 관례 shared stocks OHLC.
    entry_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, help_text="진입가"
    )
    target_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, help_text="목표가(익절)"
    )
    stop_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, help_text="손절가"
    )
    # 적정가 밴드 (⑤-A) — 수동 입력 기본, 가치평가 통로의 미래 착지점(스키마는 별도 결정).
    fair_value_low = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, help_text="적정가 하단"
    )
    fair_value_high = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, help_text="적정가 상단"
    )
    # 가격 구간축 상태 (③-B) — 전이 감지용 직전 구간 + 진입 최초 도달 시각(EXPIRED 판정·통계 원천).
    last_price_zone = models.CharField(
        max_length=16, choices=PriceZone.choices, null=True, blank=True,
        help_text="직전 가격 구간(전이 감지용)",
    )
    entry_reached_at = models.DateTimeField(
        null=True, blank=True, help_text="진입 구간 최초 도달 시각(1회 기록)"
    )

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    outcome = models.CharField(
        max_length=16, choices=Outcome.choices, default=Outcome.PENDING
    )
    # 마감 회고 (MON-CLOSE-UI Phase 1) — 전부 마감 액션(close)에서만 설정.
    proposed_verdict = models.CharField(
        max_length=16, choices=ProposedVerdict.choices, null=True, blank=True,
        help_text="시스템 제안 판정 (마감 전 없음)",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="resolved_claims",
        help_text="마감 주체",
    )
    factor_tags = ArrayField(
        models.CharField(max_length=20, choices=FactorTag.choices),
        default=list, blank=True, help_text="회고 요인 태그(고정 enum)",
    )
    retro_memo = models.TextField(blank=True, default="", help_text="회고 선택 한 줄")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Claim({self.assertion[:30]}) @ {self.monitor_id}"
