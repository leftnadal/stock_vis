"""SFI-I-1b — _coach_universe() UserGoal 스코프 교정 테스트.

D-I1b-1: 유니버스 = UserGoal 보유 유저의 WalletHolding ∪ WatchlistItem(advisory 동일 좌표).
글로벌 무필터(결함)는 목표 무보유 유저 자산까지 흡수했음.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.models_my import UserGoal
from apps.portfolio.tasks import _coach_universe
from packages.shared.stocks.models import Stock
from packages.shared.users.models import Watchlist, WatchlistItem

User = get_user_model()


def _stock(sym):
    return Stock.objects.get_or_create(symbol=sym, defaults={"currency": "USD"})[0]


def _goal_user(name):
    u = User.objects.create_user(username=name)
    UserGoal.objects.create(user=u, target_return_pct=Decimal("10"), horizon_months=12)
    return u


def _hold(user, sym):
    w = Wallet.objects.create(user=user)
    WalletHolding.objects.create(
        wallet=w, stock=_stock(sym), shares=Decimal("1"),
        avg_cost=Decimal("1"), first_bought_at=date(2026, 1, 1),
    )


def _watch(user, sym):
    wl = Watchlist.objects.get_or_create(user=user, name="wl")[0]
    WatchlistItem.objects.create(watchlist=wl, stock=_stock(sym))


@pytest.mark.django_db
class TestCoachUniverseScope:
    def test_goalless_user_holdings_and_watchlist_excluded(self):
        gu = _goal_user("goaluser")
        _hold(gu, "AAA")
        _watch(gu, "BBB")
        # 목표 무보유 유저: 보유·관심 있어도 제외돼야
        nu = User.objects.create_user(username="nogoal")
        _hold(nu, "ZZZ")
        _watch(nu, "WWW")
        assert _coach_universe() == ["AAA", "BBB"]

    def test_two_goal_users_union_dedup(self):
        u1 = _goal_user("g1")
        u2 = _goal_user("g2")
        _hold(u1, "AAA")
        _watch(u1, "SHARED")
        _hold(u2, "BBB")
        _watch(u2, "SHARED")  # 두 유저 공통 → dedup
        assert _coach_universe() == ["AAA", "BBB", "SHARED"]

    def test_no_goal_users_empty_universe(self):
        nu = User.objects.create_user(username="nogoal2")
        _hold(nu, "ZZZ")
        _watch(nu, "WWW")
        assert _coach_universe() == []
