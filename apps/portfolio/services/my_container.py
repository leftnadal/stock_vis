"""
Slice 18-R — 사용자 상태 그릇 신규 모델 CRUD 경로 (user 스코프).

DECISIONS `SLICE18R` D2'. 조회는 반드시 `ScopedManager.for_user()` 경유 —
전역 조회로 사용자 경계를 넘지 않는다. 19a(목표-대비 권유)가 부를 표준 진입점.

- UserGoal    : 사용자 전역(`user` 직접 스코프). 사용자당 1개(OneToOne).
- CashBalance : 지갑 현금(`wallet__user` 컨테이너 스코프). 지갑당 1개(OneToOne).
"""

from __future__ import annotations

from decimal import Decimal

from apps.portfolio.models_my import CashBalance, UserGoal


# ============================================================
# UserGoal — user 직접 스코프
# ============================================================


def get_goal_for_user(user):
    """사용자의 투자 목표(단일). 없으면 None. 조회는 for_user 경유."""
    return UserGoal.objects.for_user(user).first()


def upsert_goal_for_user(
    user,
    *,
    target_return_pct,
    horizon_months,
    risk_tolerance="moderate",
    exclusions=None,
):
    """사용자 목표 생성 또는 수정(사용자당 1개 = update_or_create)."""
    goal, _created = UserGoal.objects.update_or_create(
        user=user,
        defaults={
            "target_return_pct": target_return_pct,
            "horizon_months": horizon_months,
            "risk_tolerance": risk_tolerance,
            "exclusions": exclusions if exclusions is not None else {},
        },
    )
    return goal


def delete_goal_for_user(user):
    """사용자 목표 삭제. 스코프 경로 경유(타 user 미접근)."""
    return UserGoal.objects.for_user(user).delete()


# ============================================================
# CashBalance — wallet__user 컨테이너 스코프
# ============================================================


def get_cash_for_user(user):
    """사용자의 현금 잔고 전체(지갑 경유 스코프, 통화별 다행). QuerySet 반환."""
    return CashBalance.objects.for_user(user)


def upsert_cash_for_wallet(wallet, amount, currency="USD"):
    """지갑 현금 잔고 생성 또는 수정(지갑당 통화별 1행 = unique(wallet, currency))."""
    cash, _created = CashBalance.objects.update_or_create(
        wallet=wallet,
        currency=currency,
        defaults={"amount": Decimal(str(amount))},
    )
    return cash


def delete_cash_for_wallet(wallet, currency=None):
    """지갑 현금 잔고 삭제. currency 지정 시 해당 통화만, 없으면 전체."""
    qs = CashBalance.objects.filter(wallet=wallet)
    if currency is not None:
        qs = qs.filter(currency=currency)
    return qs.delete()
