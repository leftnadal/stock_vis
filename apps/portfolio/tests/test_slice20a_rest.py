"""Slice 20a — REST 표면 테스트 (Part C): user 스코프·trigger·빈 상태."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.models_my import AdvisoryRun, UserGoal
from apps.portfolio.services import my_container as mc
from packages.shared.stocks.models import Stock

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="s20a_rest", password="x")


@pytest.fixture
def other(db):
    return User.objects.create_user(username="s20a_other", password="x")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _setup(user):
    wallet = Wallet.objects.create(user=user)
    stock = Stock.objects.create(symbol="R20A", currency="USD", real_time_price=Decimal("100"))
    WalletHolding.objects.create(
        wallet=wallet, stock=stock, shares=Decimal("1"),
        avg_cost=Decimal("100"), first_bought_at=date(2026, 1, 1),
    )
    mc.upsert_cash_for_wallet(wallet, Decimal("900"), currency="USD")
    UserGoal.objects.create(user=user, target_return_pct=Decimal("10"), horizon_months=12, aggressiveness_offset=2)


# ---- 인증 ----


@pytest.mark.django_db
def test_endpoints_require_auth():
    anon = APIClient()
    for name in ["advisory_latest", "advisory_summary", "advisory_knobs"]:
        r = anon.get(reverse(f"portfolio_api:{name}"))
        assert r.status_code in (401, 403)
    assert anon.post(reverse("portfolio_api:advisory_run")).status_code in (401, 403)


# ---- 빈 상태 ----


@pytest.mark.django_db
def test_latest_empty_available_false(client):
    r = client.get(reverse("portfolio_api:advisory_latest"))
    assert r.status_code == 200
    assert r.json()["available"] is False


@pytest.mark.django_db
def test_summary_empty_available_false(client):
    r = client.get(reverse("portfolio_api:advisory_summary"))
    assert r.status_code == 200
    assert r.json()["available"] is False


@pytest.mark.django_db
def test_knobs_empty_available_false(client):
    r = client.get(reverse("portfolio_api:advisory_knobs"))
    assert r.json()["available"] is False


# ---- POST 수동 진단 (trigger=manual) ----


@pytest.mark.django_db
def test_manual_run_records_manual_and_returns(client, user):
    _setup(user)
    r = client.post(reverse("portfolio_api:advisory_run"))
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["trigger"] == "manual"
    assert body["output"]["mode"] in ("BUY", "DEFEND")
    assert AdvisoryRun.objects.filter(user=user, trigger="manual").count() == 1


# ---- GET 계약 형태 ----


@pytest.mark.django_db
def test_latest_after_run_contract_shape(client, user):
    _setup(user)
    client.post(reverse("portfolio_api:advisory_run"))
    r = client.get(reverse("portfolio_api:advisory_latest"))
    out = r.json()["output"]
    assert {"mode", "summary", "recommendations", "disclaimer"} <= set(out)
    assert {"dial", "knobs", "max_concentration", "notes"} <= set(out["summary"])
    for rec in out["recommendations"]:
        assert rec["lane"] in ("core", "exploration")


@pytest.mark.django_db
def test_summary_shape(client, user):
    _setup(user)
    client.post(reverse("portfolio_api:advisory_run"))  # 스냅샷 생성
    r = client.get(reverse("portfolio_api:advisory_summary"))
    body = r.json()
    assert body["available"] is True
    assert "total_krw" in body and "progress_gap" in body and "mode" in body


@pytest.mark.django_db
def test_knobs_read_only_values(client, user):
    _setup(user)
    r = client.get(reverse("portfolio_api:advisory_knobs"))
    body = r.json()
    assert body["aggressiveness_offset"] == 2
    assert body["concentration_limit"] == 30  # 기본


# ---- user 스코프 (타인 데이터 미노출) ----


@pytest.mark.django_db
def test_user_scope_isolation(client, user, other):
    """user의 권유는 자기 것만 — other가 만든 run은 user에 안 보인다."""
    _setup(other)
    from apps.portfolio.services.advisory_engine import run_advisory

    run_advisory(other, trigger="manual")  # other의 run
    r = client.get(reverse("portfolio_api:advisory_latest"))  # user(=client)로 조회
    assert r.json()["available"] is False  # user 본인 run 없음 → other 것 안 보임
    assert AdvisoryRun.objects.filter(user=other).count() == 1  # other엔 존재
