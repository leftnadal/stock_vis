"""
Slice 18-R — 신규 그릇 모델 CRUD 경로 + 제약/정밀도 (DECISIONS SLICE18R).

services/my_container.py의 user 스코프 CRUD 왕복 + Decimal 정밀도 + exclusions JSON 왕복
+ OneToOne 제약(사용자/지갑당 1개).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolio.models import Wallet
from apps.portfolio.models_my import CashBalance, UserGoal
from apps.portfolio.services import my_container as mc

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="crud_s18r", password="x")


# ---- UserGoal ----


@pytest.mark.django_db
def test_goal_crud_roundtrip_and_exclusions_json(user):
    # create
    goal = mc.upsert_goal_for_user(
        user,
        target_return_pct=Decimal("12.34"),
        horizon_months=24,
        risk_tolerance="aggressive",
        exclusions={"sectors": ["Energy"], "tickers": ["XOM", "CVX"]},
    )
    # read (for_user 경유)
    got = mc.get_goal_for_user(user)
    assert got is not None and got.pk == goal.pk
    assert got.target_return_pct == Decimal("12.34")  # Decimal 정밀도 보존
    assert got.horizon_months == 24
    assert got.exclusions == {"sectors": ["Energy"], "tickers": ["XOM", "CVX"]}  # JSON 왕복

    # update (동일 user upsert → 수정, 새 행 아님)
    mc.upsert_goal_for_user(user, target_return_pct=Decimal("8.00"), horizon_months=12)
    assert UserGoal.objects.for_user(user).count() == 1  # OneToOne 유지
    assert mc.get_goal_for_user(user).target_return_pct == Decimal("8.00")

    # delete
    mc.delete_goal_for_user(user)
    assert mc.get_goal_for_user(user) is None


@pytest.mark.django_db
def test_goal_one_per_user(user):
    mc.upsert_goal_for_user(user, target_return_pct=Decimal("10"), horizon_months=12)
    mc.upsert_goal_for_user(user, target_return_pct=Decimal("15"), horizon_months=6)
    assert UserGoal.objects.filter(user=user).count() == 1


# ---- CashBalance ----


@pytest.mark.django_db
def test_cash_crud_roundtrip_and_precision(user):
    wallet = Wallet.objects.create(user=user)

    cash = mc.upsert_cash_for_wallet(wallet, Decimal("1234.56"))
    assert cash.amount == Decimal("1234.56")  # Decimal 정밀도

    # read via for_user (wallet__user 컨테이너 스코프)
    qs = mc.get_cash_for_user(user)
    assert qs.count() == 1 and qs.first().amount == Decimal("1234.56")

    # update (동일 wallet → 수정)
    mc.upsert_cash_for_wallet(wallet, Decimal("999.99"))
    assert CashBalance.objects.filter(wallet=wallet).count() == 1  # OneToOne 유지
    assert mc.get_cash_for_user(user).first().amount == Decimal("999.99")

    # delete
    mc.delete_cash_for_wallet(wallet)
    assert mc.get_cash_for_user(user).count() == 0
