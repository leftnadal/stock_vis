"""Slice 20a — 백엔드: trigger 가산 + nightly 태스크 (Part B).

REST user 스코프·수동 실행 테스트는 test_slice20a_rest.py(Part C).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.models_my import AdvisoryRun, UserGoal
from apps.portfolio.services import my_container as mc
from apps.portfolio.services.advisory_engine import run_advisory
from packages.shared.stocks.models import Stock

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="s20a_user", password="x")


def _setup_portfolio(user):
    wallet = Wallet.objects.create(user=user)
    stock = Stock.objects.create(symbol="S20A", currency="USD", real_time_price=Decimal("100"))
    WalletHolding.objects.create(
        wallet=wallet, stock=stock, shares=Decimal("1"),
        avg_cost=Decimal("100"), first_bought_at=date(2026, 1, 1),
    )
    mc.upsert_cash_for_wallet(wallet, Decimal("900"), currency="USD")
    UserGoal.objects.create(user=user, target_return_pct=Decimal("10"), horizon_months=12)


# ---- trigger 기록 ----


@pytest.mark.django_db
def test_run_advisory_default_trigger_manual(user):
    _setup_portfolio(user)
    run_advisory(user)
    assert AdvisoryRun.objects.get(user=user).trigger == "manual"


@pytest.mark.django_db
def test_run_advisory_explicit_auto(user):
    _setup_portfolio(user)
    run_advisory(user, trigger="auto")
    assert AdvisoryRun.objects.get(user=user).trigger == "auto"


@pytest.mark.django_db
def test_trigger_default_value_on_field(user):
    """필드 default = manual (기존 행/미지정 안전값)."""
    _setup_portfolio(user)
    snap_run = AdvisoryRun.objects.create(user=user)  # trigger 미지정
    assert snap_run.trigger == "manual"


# ---- nightly 태스크 ----


@pytest.fixture
def _no_close(monkeypatch):
    """fork 안전용 connections.close_all()은 실워커 전용 — 테스트 트랜잭션 보존 위해 no-op."""
    from django.db import connections

    monkeypatch.setattr(connections, "close_all", lambda: None)


@pytest.mark.django_db
def test_advisory_all_users_records_auto(user, _no_close):
    """advisory_all_users nightly → 목표 보유 사용자에 trigger=auto 기록."""
    _setup_portfolio(user)
    # 목표 없는 사용자는 제외되는지도 확인
    User.objects.create_user(username="no_goal", password="x")

    from apps.portfolio.tasks import advisory_all_users

    result = advisory_all_users()
    assert result["ok"] == 1  # 목표 있는 사용자 1명만
    runs = AdvisoryRun.objects.filter(user=user)
    assert runs.count() == 1
    assert runs.first().trigger == "auto"


@pytest.mark.django_db
def test_advisory_all_users_sample_isolation(user, _no_close):
    """사후분석 표본 = auto만: 수동 실행이 auto 표본을 오염하지 않음(D2)."""
    _setup_portfolio(user)
    run_advisory(user, trigger="manual")  # 수동
    from apps.portfolio.tasks import advisory_all_users

    advisory_all_users()  # auto
    assert AdvisoryRun.objects.filter(user=user, trigger="auto").count() == 1
    assert AdvisoryRun.objects.filter(user=user, trigger="manual").count() == 1
