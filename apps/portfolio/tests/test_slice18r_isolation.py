"""
Slice 18-R — 교차 사용자 누수-0 격리 테스트 (DECISIONS SLICE18R D3').

- 신규 스코프 모델(USER_SCOPE_LOOKUP 보유)을 introspection으로 자동 수집 →
  파라미터라이즈드 누수-0 테스트.
- 등록 가드: 스코프 모델 집합이 기대와 다르면 실패(새 모델 누락 방지).
- 재사용 자산(WalletHolding·WatchlistItem) 스모크 격리(기존 정의 무접촉, 테스트만 가산).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import models

import apps.portfolio.models_my as models_my
from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.models_my import CashBalance, UserGoal
from packages.shared.stocks.models import Stock
from packages.shared.users.models import Watchlist, WatchlistItem

User = get_user_model()


# ---- introspection: USER_SCOPE_LOOKUP 보유 스코프 모델 자동 수집 ----
SCOPED_MODELS = [
    m
    for m in vars(models_my).values()
    if isinstance(m, type)
    and issubclass(m, models.Model)
    and not m._meta.abstract
    and hasattr(m, "USER_SCOPE_LOOKUP")
]


def _make(model, user):
    """스코프 모델별 A-소유 인스턴스 팩토리.

    신규 스코프 모델은 여기에 등록해야 한다 — 미등록 시 NotImplementedError로
    파라미터라이즈드 테스트가 실패(등록 가드의 실행부).
    """
    if model is UserGoal:
        return model.objects.create(
            user=user, target_return_pct=Decimal("10"), horizon_months=12
        )
    if model is CashBalance:
        wallet = Wallet.objects.create(user=user)
        return model.objects.create(wallet=wallet, amount=Decimal("100"))
    raise NotImplementedError(
        f"스코프 모델 {model.__name__}의 격리 팩토리 미등록 — _make()에 추가할 것."
    )


@pytest.fixture
def user_a(db):
    return User.objects.create_user(username="alice_s18r", password="x")


@pytest.fixture
def user_b(db):
    return User.objects.create_user(username="bob_s18r", password="x")


@pytest.fixture
def stock(db):
    return Stock.objects.create(symbol="TSTX")


# ============================================================
# 신규 2종 — 파라미터라이즈드 누수-0
# ============================================================


@pytest.mark.django_db
@pytest.mark.parametrize("model", SCOPED_MODELS, ids=lambda m: m.__name__)
def test_scoped_model_no_cross_user_leak(model, user_a, user_b):
    inst_a = _make(model, user_a)

    # A는 자기 데이터를 본다
    assert model.objects.for_user(user_a).filter(pk=inst_a.pk).exists()
    # B의 스코프 조회에는 A의 데이터가 없다 (누수-0)
    assert not model.objects.for_user(user_b).filter(pk=inst_a.pk).exists()
    assert model.objects.for_user(user_b).count() == 0


# ============================================================
# 등록 가드 — 새 스코프 모델이 생겼는데 커버 누락되면 실패
# ============================================================


@pytest.mark.django_db
def test_scoped_model_registry_guard():
    names = {m.__name__ for m in SCOPED_MODELS}
    assert names == {"CashBalance", "UserGoal"}, (
        f"USER_SCOPE_LOOKUP 스코프 모델 집합이 바뀜: {names}. "
        "신규 스코프 모델은 _make() 팩토리에 등록하고 이 기대집합을 갱신할 것 "
        "(D3' 등록 가드)."
    )
    # 각 모델이 실제로 for_user를 제공하는지 (ScopedManager 계승)
    for m in SCOPED_MODELS:
        assert hasattr(m.objects, "for_user"), f"{m.__name__}에 for_user 매니저 없음"


# ============================================================
# 재사용 자산 스모크 격리 (WalletHolding·WatchlistItem, 기존 정의 무접촉)
# ============================================================


@pytest.mark.django_db
def test_reused_wallet_holding_scope_smoke(user_a, user_b, stock):
    wallet_a = Wallet.objects.create(user=user_a)
    WalletHolding.objects.create(
        wallet=wallet_a,
        stock=stock,
        shares=Decimal("1"),
        avg_cost=Decimal("100"),
        first_bought_at=date(2026, 1, 1),
    )
    assert WalletHolding.objects.filter(wallet__user=user_a).count() == 1
    assert WalletHolding.objects.filter(wallet__user=user_b).count() == 0


@pytest.mark.django_db
def test_reused_watchlist_item_scope_smoke(user_a, user_b, stock):
    wl_a = Watchlist.objects.create(user=user_a, name="wl-a")
    WatchlistItem.objects.create(watchlist=wl_a, stock=stock)
    assert WatchlistItem.objects.filter(watchlist__user=user_a).count() == 1
    assert WatchlistItem.objects.filter(watchlist__user=user_b).count() == 0
