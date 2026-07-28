"""
Slice 20b-f1 — 매수일 선택화 + "입력일부터 추적" 폴백 (DECISIONS D-20BF1-*).

- 매수일(first_bought_at) 미입력 허용(serializer optional + 모델 null).
- 미입력 시 acquisition_fx_rate = 입력일 spot(최신 close) 캡처 → "입력일부터 KRW 추적".
- 매수일 입력 보유는 기존 경로 완전 불변(소급 재계산·spot 캡처 없음).
- 폴백 표지 = first_bought_at == None 자체(별도 필드 없음).
- spot 부재 시 근사 발명 금지(방어적 강등, 크래시 없음).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.services import advisory_engine as eng
from packages.shared.fx.models import ExchangeRate
from packages.shared.stocks.models import DailyPrice, Stock

User = get_user_model()

URL = "/api/v1/wallet/holdings/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="bf1user", password="x")


@pytest.fixture
def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def fx_rates(db):
    """백필 창: 최신(2024-12-15)=spot=1400."""
    ExchangeRate.objects.create(pair="USDKRW", date=date(2024, 1, 15), close=Decimal("1300"))
    ExchangeRate.objects.create(pair="USDKRW", date=date(2024, 12, 15), close=Decimal("1400"))


def _stock(symbol, currency="USD", price="100"):
    s = Stock.objects.create(symbol=symbol, currency=currency)
    p = Decimal(price)
    DailyPrice.objects.create(
        stock=s, date=date(2026, 7, 10),
        open_price=p, high_price=p, low_price=p, close_price=p, volume=1000,
    )
    return s


# ── serializer optional 경계 ──


@pytest.mark.django_db
def test_serializer_first_bought_at_optional():
    from apps.portfolio.api.wallet import HoldingCreateSerializer

    ser = HoldingCreateSerializer(data={"symbol": "AAA", "shares": "10", "avg_cost": "100"})
    assert ser.is_valid(), ser.errors
    assert ser.validated_data.get("first_bought_at") is None


# ── 미입력 생성 → 입력일 spot 캡처 ──


@pytest.mark.django_db
def test_create_without_first_bought_at_captures_spot(api, user, fx_rates):
    _stock("AAA", "USD", "100")
    resp = api.post(URL, {"symbol": "AAA", "shares": "10", "avg_cost": "100"}, format="json")
    assert resp.status_code == 201, resp.content
    h = WalletHolding.objects.get(wallet__user=user, stock_id="AAA")
    assert h.first_bought_at is None                  # 폴백 표지
    assert h.acquisition_fx_rate == Decimal("1400")   # 입력일 spot(최신 close)


@pytest.mark.django_db
def test_cost_basis_null_first_bought_at_captured_spot_is_exact(api, user, fx_rates):
    _stock("BBB", "USD", "100")
    api.post(URL, {"symbol": "BBB", "shares": "10", "avg_cost": "100"}, format="json")
    h = WalletHolding.objects.get(wallet__user=user, stock_id="BBB")
    cost, label = eng.krw_cost_basis(h)
    assert label == "exact"
    assert cost == Decimal("10") * Decimal("100") * Decimal("1400")  # 입력일부터 추적


# ── 매수일 입력 보유 = 기존 경로 불변 (invariance guard) ──


@pytest.mark.django_db
def test_create_with_first_bought_at_unchanged(api, user, fx_rates):
    _stock("CCC", "USD", "100")
    resp = api.post(
        URL,
        {"symbol": "CCC", "shares": "10", "avg_cost": "100", "first_bought_at": "2024-06-20"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    h = WalletHolding.objects.get(wallet__user=user, stock_id="CCC")
    assert h.first_bought_at == date(2024, 6, 20)
    assert h.acquisition_fx_rate is None              # 미전달 → None 유지(기존 경로)
    _, label = eng.krw_cost_basis(h)
    assert label == "approx_first_buy"                # 매수일 환율 조회(spot 캡처 안 함)


# ── KRW 종목 미입력 → spot 캡처 안 함 ──


@pytest.mark.django_db
def test_krw_stock_without_first_bought_at_no_capture(api, user, fx_rates):
    _stock("035420", "KRW", "50000")
    api.post(URL, {"symbol": "035420", "shares": "10", "avg_cost": "50000"}, format="json")
    h = WalletHolding.objects.get(wallet__user=user, stock_id="035420")
    assert h.first_bought_at is None
    assert h.acquisition_fx_rate is None              # KRW는 FX 무의미 → 캡처 안 함
    _, label = eng.krw_cost_basis(h)
    assert label == "native_krw"


# ── 방어: 미입력 + spot 전무 → 크래시 없이 강등 ──


@pytest.mark.django_db
def test_cost_basis_null_first_bought_at_no_fx_degrades(user):
    w = Wallet.objects.create(user=user)
    s = _stock("DDD", "USD", "100")
    h = WalletHolding.objects.create(
        wallet=w, stock=s, shares=Decimal("10"), avg_cost=Decimal("100"),
        first_bought_at=None, acquisition_fx_rate=None,
    )
    cost, label = eng.krw_cost_basis(h)               # get_rate_on(None) 미도달(가드)
    assert label == "approx_low_confidence"
    assert cost == Decimal("10") * Decimal("100")     # 환율 전무 → 원가 통화 그대로
