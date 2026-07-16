"""Slice 20b — REST 표면 테스트 (Part B).

knobs PATCH 검증기 경계값(서버측 강제) + wallet/cash CRUD + user 스코프 격리 +
저장 ≠ 진단 실행(D2). 모델 무변경 — 신규 마이그레이션 0.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.models_my import AdvisoryRun, CashBalance, UserGoal
from packages.shared.stocks.models import Stock

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="s20b", password="x")


@pytest.fixture
def other(db):
    return User.objects.create_user(username="s20b_other", password="x")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def goal(user):
    return UserGoal.objects.create(
        user=user, target_return_pct=Decimal("10"), horizon_months=12
    )


@pytest.fixture
def stock(db):
    return Stock.objects.create(symbol="S20B", currency="USD", real_time_price=Decimal("50"))


# ============================================================
# knobs PATCH — 인증 · 검증기 경계값 · 저장≠진단
# ============================================================


@pytest.mark.django_db
def test_knobs_patch_requires_auth():
    anon = APIClient()
    r = anon.patch(reverse("portfolio_api:advisory_knobs"), {"aggressiveness_offset": 3})
    assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_knobs_patch_no_goal_400(client):
    r = client.patch(reverse("portfolio_api:advisory_knobs"), {"aggressiveness_offset": 3})
    assert r.status_code == 400
    assert r.json()["available"] is False


@pytest.mark.django_db
def test_knobs_patch_empty_body_400(client, goal):
    r = client.patch(reverse("portfolio_api:advisory_knobs"), {})
    assert r.status_code == 400


@pytest.mark.django_db
def test_knobs_patch_valid_updates_and_reflects(client, goal):
    r = client.patch(
        reverse("portfolio_api:advisory_knobs"),
        {
            "target_return_pct": "15.50",
            "aggressiveness_offset": 5,
            "growth_boost": 3,
            "diversification_weight": "0.15",
            "concentration_limit": 40,
            "exploration_ratio": 20,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["aggressiveness_offset"] == 5
    assert body["concentration_limit"] == 40
    assert body["exploration_ratio"] == 20
    assert Decimal(body["diversification_weight"]) == Decimal("0.15")
    assert Decimal(body["target_return_pct"]) == Decimal("15.50")
    goal.refresh_from_db()
    assert goal.aggressiveness_offset == 5
    assert goal.concentration_limit == 40


@pytest.mark.django_db
def test_knobs_patch_partial_only_provided(client, goal):
    """부분 수정 — 제공한 필드만 변경, 나머지 불변."""
    r = client.patch(reverse("portfolio_api:advisory_knobs"), {"growth_boost": 4})
    assert r.status_code == 200
    goal.refresh_from_db()
    assert goal.growth_boost == 4
    assert goal.concentration_limit == 30  # 기본값 불변
    assert goal.target_return_pct == Decimal("10")


# --- 경계값: 손잡이별 min / max 통과, 초과·미달 400 (서버측 검증기 강제) ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,ok_min,ok_max,too_low,too_high",
    [
        ("aggressiveness_offset", 0, 7, -1, 8),
        ("growth_boost", 0, 7, -1, 8),
        ("concentration_limit", 15, 100, 14, 101),
        ("exploration_ratio", 0, 30, -1, 31),
    ],
)
def test_knobs_patch_int_boundaries(client, goal, field, ok_min, ok_max, too_low, too_high):
    url = reverse("portfolio_api:advisory_knobs")
    assert client.patch(url, {field: ok_min}).status_code == 200
    assert client.patch(url, {field: ok_max}).status_code == 200
    assert client.patch(url, {field: too_low}).status_code == 400
    assert client.patch(url, {field: too_high}).status_code == 400


@pytest.mark.django_db
def test_knobs_patch_diversification_weight_boundaries(client, goal):
    url = reverse("portfolio_api:advisory_knobs")
    assert client.patch(url, {"diversification_weight": "0"}).status_code == 200
    assert client.patch(url, {"diversification_weight": "0.20"}).status_code == 200
    r = client.patch(url, {"diversification_weight": "0.21"})
    assert r.status_code == 400
    assert "diversification_weight" in r.json()["errors"]


@pytest.mark.django_db
def test_knobs_patch_non_numeric_400(client, goal):
    r = client.patch(reverse("portfolio_api:advisory_knobs"), {"aggressiveness_offset": "abc"})
    assert r.status_code == 400
    assert "aggressiveness_offset" in r.json()["errors"]


@pytest.mark.django_db
def test_knobs_patch_does_not_run_advisory(client, goal, user):
    """저장 ≠ 진단 실행(D2) — PATCH가 AdvisoryRun을 만들지 않는다."""
    client.patch(reverse("portfolio_api:advisory_knobs"), {"aggressiveness_offset": 3})
    assert AdvisoryRun.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_knobs_patch_over_range_does_not_persist(client, goal):
    """검증기 우회 불가 — 범위 밖은 저장조차 안 됨."""
    client.patch(reverse("portfolio_api:advisory_knobs"), {"concentration_limit": 200})
    goal.refresh_from_db()
    assert goal.concentration_limit == 30  # 불변


@pytest.mark.django_db
def test_knobs_patch_user_scope(client, goal, other):
    """다른 user의 goal은 건드리지 않는다."""
    other_goal = UserGoal.objects.create(
        user=other, target_return_pct=Decimal("8"), horizon_months=24, aggressiveness_offset=1
    )
    client.patch(reverse("portfolio_api:advisory_knobs"), {"aggressiveness_offset": 6})
    other_goal.refresh_from_db()
    assert other_goal.aggressiveness_offset == 1  # 불변


@pytest.mark.django_db
def test_knobs_get_includes_target_return(client, goal):
    r = client.get(reverse("portfolio_api:advisory_knobs"))
    assert r.status_code == 200
    assert Decimal(r.json()["target_return_pct"]) == Decimal("10")


# ============================================================
# wallet holdings CRUD
# ============================================================


@pytest.mark.django_db
def test_holdings_require_auth():
    anon = APIClient()
    assert anon.get(reverse("portfolio_api:wallet_holdings")).status_code in (401, 403)


@pytest.mark.django_db
def test_holdings_list_empty(client):
    r = client.get(reverse("portfolio_api:wallet_holdings"))
    assert r.status_code == 200
    assert r.json()["holdings"] == []


@pytest.mark.django_db
def test_holdings_create_and_list(client, stock):
    r = client.post(
        reverse("portfolio_api:wallet_holdings"),
        {
            "symbol": "s20b",  # 소문자 → 대문자 정규화
            "shares": "10",
            "avg_cost": "45.00",
            "first_bought_at": "2026-01-15",
            "investment_thesis": "성장 테제",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["symbol"] == "S20B"
    assert body["currency"] == "USD"
    assert body["investment_thesis"] == "성장 테제"

    lst = client.get(reverse("portfolio_api:wallet_holdings")).json()["holdings"]
    assert len(lst) == 1
    assert lst[0]["symbol"] == "S20B"


@pytest.mark.django_db
def test_holdings_create_unknown_stock_400(client):
    r = client.post(
        reverse("portfolio_api:wallet_holdings"),
        {"symbol": "NOPE", "shares": "1", "avg_cost": "1", "first_bought_at": "2026-01-01"},
    )
    assert r.status_code == 400
    assert "symbol" in r.json()["errors"]


@pytest.mark.django_db
def test_holdings_create_duplicate_400(client, stock):
    payload = {"symbol": "S20B", "shares": "1", "avg_cost": "1", "first_bought_at": "2026-01-01"}
    assert client.post(reverse("portfolio_api:wallet_holdings"), payload).status_code == 201
    r = client.post(reverse("portfolio_api:wallet_holdings"), payload)
    assert r.status_code == 400


@pytest.mark.django_db
def test_holdings_patch_update(client, stock):
    created = client.post(
        reverse("portfolio_api:wallet_holdings"),
        {"symbol": "S20B", "shares": "1", "avg_cost": "1", "first_bought_at": "2026-01-01"},
    ).json()
    hid = created["id"]
    r = client.patch(
        reverse("portfolio_api:wallet_holding_detail", args=[hid]),
        {"shares": "25", "investment_thesis": "수정된 테제"},
    )
    assert r.status_code == 200
    body = r.json()
    assert Decimal(body["shares"]) == Decimal("25")
    assert body["investment_thesis"] == "수정된 테제"


@pytest.mark.django_db
def test_holdings_delete(client, stock):
    created = client.post(
        reverse("portfolio_api:wallet_holdings"),
        {"symbol": "S20B", "shares": "1", "avg_cost": "1", "first_bought_at": "2026-01-01"},
    ).json()
    r = client.delete(reverse("portfolio_api:wallet_holding_detail", args=[created["id"]]))
    assert r.status_code == 204
    assert client.get(reverse("portfolio_api:wallet_holdings")).json()["holdings"] == []


@pytest.mark.django_db
def test_holdings_scope_isolation(client, other, stock):
    """other의 보유는 user에게 안 보이고, user가 수정/삭제 불가(404)."""
    ow = Wallet.objects.create(user=other)
    oh = WalletHolding.objects.create(
        wallet=ow, stock=stock, shares=Decimal("5"), avg_cost=Decimal("10"),
        first_bought_at=date(2026, 1, 1),
    )
    assert client.get(reverse("portfolio_api:wallet_holdings")).json()["holdings"] == []
    assert client.patch(
        reverse("portfolio_api:wallet_holding_detail", args=[oh.id]), {"shares": "99"}
    ).status_code == 404
    assert client.delete(
        reverse("portfolio_api:wallet_holding_detail", args=[oh.id])
    ).status_code == 404


# ============================================================
# wallet cash CRUD
# ============================================================


@pytest.mark.django_db
def test_cash_list_empty(client):
    r = client.get(reverse("portfolio_api:wallet_cash"))
    assert r.status_code == 200
    assert r.json()["cash"] == []


@pytest.mark.django_db
def test_cash_upsert_and_update(client):
    url = reverse("portfolio_api:wallet_cash")
    r = client.put(url, {"currency": "USD", "amount": "1000.00"})
    assert r.status_code == 200
    assert Decimal(r.json()["amount"]) == Decimal("1000.00")
    # 같은 통화 재-upsert = 갱신 (중복 행 아님)
    client.put(url, {"currency": "USD", "amount": "2000.00"})
    cash = client.get(url).json()["cash"]
    assert len(cash) == 1
    assert Decimal(cash[0]["amount"]) == Decimal("2000.00")


@pytest.mark.django_db
def test_cash_multi_currency(client):
    url = reverse("portfolio_api:wallet_cash")
    client.put(url, {"currency": "USD", "amount": "500"})
    client.put(url, {"currency": "KRW", "amount": "700000"})
    cash = {c["currency"]: c["amount"] for c in client.get(url).json()["cash"]}
    assert set(cash) == {"USD", "KRW"}


@pytest.mark.django_db
def test_cash_negative_400(client):
    r = client.put(reverse("portfolio_api:wallet_cash"), {"currency": "USD", "amount": "-5"})
    assert r.status_code == 400


@pytest.mark.django_db
def test_cash_delete(client):
    url = reverse("portfolio_api:wallet_cash")
    client.put(url, {"currency": "USD", "amount": "100"})
    r = client.delete(url + "?currency=USD")
    assert r.status_code == 204
    assert client.get(url).json()["cash"] == []


@pytest.mark.django_db
def test_cash_scope_isolation(client, other):
    """other의 현금은 user에게 안 보인다."""
    ow = Wallet.objects.create(user=other)
    CashBalance.objects.create(wallet=ow, currency="USD", amount=Decimal("999"))
    assert client.get(reverse("portfolio_api:wallet_cash")).json()["cash"] == []
