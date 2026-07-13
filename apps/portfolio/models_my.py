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
    updated_at = models.DateTimeField(auto_now=True)

    objects = ScopedManager()

    def __str__(self):
        return f"Goal({self.user}: {self.target_return_pct}% / {self.horizon_months}mo)"
