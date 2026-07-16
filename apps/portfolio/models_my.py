"""
Slice 18-R — 사용자 상태 그릇 신규 모델 (ADDITIVE)
==================================================

DECISIONS.md `SLICE18R` 참조. 원안 4모델 중 2종은 재사용, 신규는 2종만.

신규 (이 파일):
  - CashBalance : 지갑 현금 잔고. house 컨테이너 경유 스코핑(`wallet__user`).
                  한 지갑 = 보유(WalletHolding) + 현금(CashBalance). USD 고정(다통화 YAGNI).
  - UserGoal    : 사용자 투자 목표. 사용자 전역 → `user` 직접 스코핑.

재사용 (생성 안 함 — 참조만):
  - WalletHolding : apps/portfolio.models (실보유, `wallet__user`)
  - WatchlistItem : packages/shared/users.models (관심 후보, `watchlist__user`)

D2' 이음새 — 추상 모델 베이스는 강제하지 않는다(YAGNI: 두 모델이 상이한 스코프 가지).
대신 **공통 매니저 `ScopedManager` + 모델별 `USER_SCOPE_LOOKUP`** 으로 "user로 좁혀지는
표준 조회 경로"를 한 곳에 모은다. 격리 테스트 등록 가드(D3')도 이 속성으로 introspect.

19a 결선 (목표-대비 권유 엔진):
  UserGoal(목표) vs WalletHolding(실보유)+CashBalance(현금) → 갭 → WatchlistItem(후보) 매칭.
  → 신규 2종 필드는 19a 비교 연산 '최소'로 잡는다(과설계 금지).
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.portfolio.models import Wallet


class ScopedManager(models.Manager):
    """user 스코프 조회를 쿼리 계층 기본값으로 노출.

    각 모델의 클래스 속성 `USER_SCOPE_LOOKUP`(예: "user", "wallet__user")을 사용해
    직접 FK / 컨테이너 경유 양쪽을 동일 인터페이스(`for_user`)로 흡수한다.
    """

    def for_user(self, user):
        return self.filter(**{self.model.USER_SCOPE_LOOKUP: user})


# ============================================================
# CashBalance — 지갑 현금 (D2': Wallet 컨테이너 경유 스코핑)
# ============================================================


class CashBalance(models.Model):
    """
    Wallet의 통화별 현금 잔고. 지갑당 통화별 1행(SLICE19A: FK + unique(wallet, currency)).
    스코핑: `CashBalance.objects.for_user(user)` → `wallet__user`.
    다통화(KRW+USD) — 19a 제품의도 확정. 환전 없음(통화별 매수여력 분리, 교차환전은 19b).
    """

    USER_SCOPE_LOOKUP = "wallet__user"

    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("KRW", "KRW"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="cash_balances",
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD",
        help_text="통화 (USD/KRW). 지갑당 통화별 1행.",
    )
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0"),
        help_text="현금 잔고 (해당 통화 단위).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = ScopedManager()

    class Meta:
        indexes = [models.Index(fields=["wallet"])]
        unique_together = [("wallet", "currency")]

    def __str__(self):
        return f"{self.amount} {self.currency} in {self.wallet.name}"


# ============================================================
# UserGoal — 투자 목표 (D2': 사용자 전역 → user 직접 스코핑)
# ============================================================


class UserGoal(models.Model):
    """
    사용자의 투자 목표. 사용자당 1개(OneToOne) — 지갑이 아니라 사용자 속성.
    스코핑: `UserGoal.objects.for_user(user)` → `user`.
    단일 현재값(실행 시점 스냅샷 이력은 19a PredictionRecord 소관 — 이력 테이블 아님).
    """

    USER_SCOPE_LOOKUP = "user"

    RISK_CHOICES = [
        ("conservative", "Conservative"),
        ("moderate", "Moderate"),
        ("aggressive", "Aggressive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_goal",
    )
    target_return_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="목표 수익률 (%). 예: 12.00 = 연 12%.",
    )
    horizon_months = models.PositiveIntegerField(
        help_text="투자 기간 (개월).",
    )
    risk_tolerance = models.CharField(
        max_length=20,
        choices=RISK_CHOICES,
        default="moderate",
    )
    exclusions = models.JSONField(
        default=dict,
        blank=True,
        help_text='제외 대상. 예: {"sectors": ["Energy"], "tickers": ["XOM"]}. 19a 후보 필터용.',
    )

    # ---- 성향 손잡이 5종 (SLICE19C — 사용자 주권, 전부 기본=보수값) ----
    # 엔진은 이 값들을 자동 조정하지 않는다. 자동 반응은 dd(측정 사실) 하나뿐.
    aggressiveness_offset = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(7)],
        help_text="A: 상시 여력 오프셋 (%p, 0~7). 다이얼 a에 상시 가산.",
    )
    growth_boost = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(7)],
        help_text="G: 성장 부스트 (%p, 0~7). **신고점 국면에서만** a에 가산.",
    )
    diversification_weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("0.20"))],
        help_text="w: 코어 랭킹 분산 성분 가중 (0~0.20). 신뢰도 지배 불변식 상한.",
    )
    concentration_limit = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(15), MaxValueValidator(100)],
        help_text="L: 집중도 한도 (%, 15~100). 자격+TRIM 기준. 100=무제한(TRIM 소멸).",
    )
    exploration_ratio = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        help_text="E: 여력 중 탐험 레인 배정 (%, 0~30). 젊은 후보 전용.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    objects = ScopedManager()

    # 손잡이 범위 (저장 거부용 단일 소스 — 검증기 선언과 일치)
    KNOB_RANGES = {
        "aggressiveness_offset": (0, 7),
        "growth_boost": (0, 7),
        "diversification_weight": (Decimal("0"), Decimal("0.20")),
        "concentration_limit": (15, 100),
        "exploration_ratio": (0, 30),
    }

    def clean(self):
        """손잡이 5종 범위 밖 = 거부 (SLICE19C — full_clean/save 경유)."""
        super().clean()
        errors = {}
        for field, (lo, hi) in self.KNOB_RANGES.items():
            v = getattr(self, field)
            if v is None or v < lo or v > hi:
                errors[field] = f"{field}는 {lo}~{hi} 범위여야 합니다 (입력: {v})."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # 손잡이 범위 밖 저장 거부(§0-2 검증기). 기본값(보수)은 전부 범위 내 → 기존 save 무영향.
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Goal({self.user}: {self.target_return_pct}% / {self.horizon_months}mo)"


# ============================================================
# PortfolioSnapshot — 일일 자산 평가 스냅샷 (SLICE19C 원장 1/2)
# ============================================================


class PortfolioSnapshot(models.Model):
    """
    사용자 포트폴리오의 특정 일자 KRW 평가 스냅샷 (SLICE19C).

    용도: 드로다운 dd 계산의 시계열 + flow 분해(가격효과/플로우효과) + 사후분석.
    기록: nightly Celery 태스크 + 엔진 실행 시 upsert (이중 기록, unique(user, date)).

    ⚠️ 기존 `WalletSnapshot`(wallet 스코프·이벤트 트리거·비-일일·비-FX)과 별개 —
       user 스코프·date-unique·일일·KRW/FX 상세 요구를 충족(§2f 중복 아님).
    """

    USER_SCOPE_LOOKUP = "user"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_snapshots",
    )
    date = models.DateField(
        db_index=True,
        help_text="스냅샷 일자 (실행/배치 시점 date). unique(user, date).",
    )
    total_krw = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="총자산 KRW (보유 평가 + 현금, 전부 현재 환율 KRW 환산).",
    )
    by_currency = models.JSONField(
        default=dict,
        blank=True,
        help_text='통화별 소계. {"USD": {"holdings_krw", "cash_krw"}, "KRW": {...}}.',
    )
    holdings_detail = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "종목별 상세(flow 분해 재료). "
            "[{symbol, currency, shares, price, fx_rate, value_krw}, ...]."
        ),
    )
    net_flow_krw = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="이 일자 순입금 KRW(입금−출금·수동수정 잔차). dd flow 조정용.",
    )
    price_as_of = models.DateField(
        null=True,
        blank=True,
        help_text="보유 종목 가격 기준일(최신 DailyPrice.date). 신선도 판별용.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ScopedManager()

    class Meta:
        ordering = ["-date"]
        unique_together = [("user", "date")]
        indexes = [models.Index(fields=["user", "-date"])]

    def __str__(self):
        return f"Snapshot({self.user}: {self.date} = {self.total_krw} KRW)"


# ============================================================
# AdvisoryRun — 권유 엔진 실행 기록 (SLICE19C 원장 2/2)
# ============================================================


class AdvisoryRun(models.Model):
    """
    배치 엔진 1회 실행 기록 (SLICE19C).

    용도: 사후분석(예측·성향 검증)의 토대 — 산출 전문 + 당시 손잡이 5종 스냅 + 레인 구분.
    19d 재보정은 이 라벨 축적 후. (기존 `AnalysisRun`=preset 지표 도메인과 무관.)
    """

    USER_SCOPE_LOOKUP = "user"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="advisory_runs",
    )
    snapshot = models.ForeignKey(
        PortfolioSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="advisory_runs",
        help_text="이 실행이 근거한 자산 스냅샷.",
    )
    run_at = models.DateTimeField(auto_now_add=True, db_index=True)

    TRIGGER_CHOICES = [
        ("auto", "Auto (nightly)"),
        ("manual", "Manual (화면 진단)"),
    ]
    trigger = models.CharField(
        max_length=10,
        choices=TRIGGER_CHOICES,
        default="manual",
        db_index=True,
        help_text=(
            "실행 트리거 (SLICE20A). auto=nightly 자동 기록(원장 시계열), "
            "manual=화면 수동 진단. **사후분석은 auto만 표본으로 사용**(수동 오염 배제)."
        ),
    )
    output = models.JSONField(
        default=dict,
        help_text="산출 전문(계약 v3). recommendations는 lane(core/exploration) 라벨 포함.",
    )
    knobs_snapshot = models.JSONField(
        default=dict,
        help_text=(
            "실행 당시 손잡이 5종 값. "
            '{"A", "G", "w", "L", "E"} + 파생(dd, buffer, headroom).'
        ),
    )

    objects = ScopedManager()

    class Meta:
        ordering = ["-run_at"]
        indexes = [models.Index(fields=["user", "-run_at"])]

    def __str__(self):
        return f"AdvisoryRun({self.user}: {self.run_at:%Y-%m-%d %H:%M})"
