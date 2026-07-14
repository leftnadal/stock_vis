"""
Slice 19b — KRW 교정 + 취득원가 우선순위 테스트 (DECISIONS SLICE19B).

게이트1 우선순위 3분기(exact/approx_first_buy/approx_low_confidence) + native_krw
+ 휴장일 fallback + 수동값 precedence + KRW 교정 실증(FX가 수익 구성요소).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.services import advisory_engine as eng
from apps.portfolio.services import my_container as mc
from packages.shared.fx.models import ExchangeRate
from packages.shared.stocks.models import DailyPrice, Stock

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="krw19b", password="x")


@pytest.fixture
def wallet(user):
    return Wallet.objects.create(user=user)


@pytest.fixture
def fx_rates(db):
    """백필 창 2024-01-15 ~ 2024-12-15 (최신 = spot)."""
    ExchangeRate.objects.create(pair="USDKRW", date=date(2024, 1, 15), close=Decimal("1300"))
    ExchangeRate.objects.create(pair="USDKRW", date=date(2024, 6, 15), close=Decimal("1350"))
    ExchangeRate.objects.create(pair="USDKRW", date=date(2024, 12, 15), close=Decimal("1400"))


def _stock(symbol, currency="USD", price="100"):
    s = Stock.objects.create(symbol=symbol, currency=currency)
    p = Decimal(price)
    DailyPrice.objects.create(
        stock=s, date=date(2026, 7, 10),
        open_price=p, high_price=p, low_price=p, close_price=p, volume=1000,
    )
    return s


def _hold(wallet, stock, shares="10", avg_cost="100", first="2026-01-01"):
    y, m, d = map(int, first.split("-"))
    return WalletHolding.objects.create(
        wallet=wallet, stock=stock,
        shares=Decimal(shares), avg_cost=Decimal(avg_cost),
        first_bought_at=date(y, m, d),
    )


# ---- 취득원가 우선순위 ----


@pytest.mark.django_db
def test_cost_basis_exact(user, wallet, fx_rates):
    h = _hold(wallet, _stock("AAA", "USD", "100"), shares="10", avg_cost="100")
    h.acquisition_fx_rate = Decimal("1250")
    h.save()
    cost, label = eng.krw_cost_basis(h)
    assert label == "exact"
    assert cost == Decimal("10") * Decimal("100") * Decimal("1250")  # 1,250,000


@pytest.mark.django_db
def test_cost_basis_approx_first_buy_holiday_fallback(user, wallet, fx_rates):
    # 매수일 2024-06-20(휴장 가정) → 직전 영업일 2024-06-15 rate 1350
    h = _hold(wallet, _stock("BBB", "USD", "100"), shares="10", avg_cost="100", first="2024-06-20")
    cost, label = eng.krw_cost_basis(h)
    assert label == "approx_first_buy"
    assert cost == Decimal("1000") * Decimal("1350")  # 직전 영업일 fallback


@pytest.mark.django_db
def test_cost_basis_approx_low_confidence(user, wallet, fx_rates):
    # 매수일 2020-01-01 = 백필 창(2024~) 밖 → 가장 오래된 rate 1300
    h = _hold(wallet, _stock("CCC", "USD", "100"), shares="10", avg_cost="100", first="2020-01-01")
    cost, label = eng.krw_cost_basis(h)
    assert label == "approx_low_confidence"
    assert cost == Decimal("1000") * Decimal("1300")  # oldest available


@pytest.mark.django_db
def test_cost_basis_native_krw(user, wallet, fx_rates):
    h = _hold(wallet, _stock("035420", "KRW", "50000"), shares="10", avg_cost="50000")
    cost, label = eng.krw_cost_basis(h)
    assert label == "native_krw"
    assert cost == Decimal("10") * Decimal("50000")  # 무환산


@pytest.mark.django_db
def test_cost_basis_precedence_manual_beats_approx(user, wallet, fx_rates):
    # first_bought_at이 창 안이어도 acquisition_fx_rate(수동)가 이긴다
    h = _hold(wallet, _stock("DDD", "USD", "100"), shares="10", avg_cost="100", first="2024-06-20")
    h.acquisition_fx_rate = Decimal("1111")
    h.save()
    cost, label = eng.krw_cost_basis(h)
    assert label == "exact"  # approx_first_buy 아님
    assert cost == Decimal("1000") * Decimal("1111")


# ---- KRW 교정 실증 (FX가 수익 구성요소) ----


@pytest.mark.django_db
def test_krw_correction_fx_is_return_component(user, wallet, fx_rates):
    h = _hold(wallet, _stock("EEE", "USD", "120"), shares="10", avg_cost="100")
    h.acquisition_fx_rate = Decimal("1300")  # 매수 환율
    h.save()
    goal = mc.upsert_goal_for_user(user, target_return_pct=Decimal("10"), horizon_months=12)

    gap = eng.compute_progress_gap(user, goal)
    # cost_krw = 10*100*1300 = 1,300,000 / value_krw = 10*120*spot(1400) = 1,680,000
    assert gap["cost_krw"] == Decimal("1300000")
    assert gap["value_krw"] == Decimal("1680000")
    # KRW 수익률 ≈ 29.2% > USD 수익률 20% — 환율 상승(1300→1400)이 수익에 기여(정직한 numéraire)
    assert gap["return_pct"] > Decimal("29") and gap["return_pct"] < Decimal("30")
    assert gap["cost_labels"]["exact"] == 1


@pytest.mark.django_db
def test_allocation_gap_krw_unified_multicurrency(user, wallet, fx_rates):
    # USD 현금 1000(→KRW 1,400,000) + KRW 현금 600,000 → 통합 유휴현금 비중
    mc.upsert_cash_for_wallet(wallet, Decimal("1000"), currency="USD")
    mc.upsert_cash_for_wallet(wallet, Decimal("600000"), currency="KRW")
    _hold(wallet, _stock("FFF", "KRW", "100000"), shares="10", avg_cost="100000")  # KRW 보유 1,000,000

    alloc = eng.compute_allocation_gap(user)
    # cash_krw = 1000*1400 + 600000 = 2,000,000 / hold_krw = 1,000,000 / total 3,000,000
    assert alloc["cash_krw"] == Decimal("2000000")
    assert alloc["holdings_value_krw"] == Decimal("1000000")
    assert alloc["idle_ratio"] == Decimal("2000000") / Decimal("3000000")
    assert set(alloc["by_currency"]) == {"USD", "KRW"}


# ---- FX 맥락 factor (역사적 백분위, 예측 아님) ----


@pytest.mark.django_db
def test_fx_context_percentile(user, fx_rates):
    # spot = 최신 1400 (3건 중 최고) → 100 백분위
    ctx = eng.fx_context("USDKRW")
    assert ctx["available"] is True
    assert ctx["spot"] == Decimal("1400")
    assert ctx["percentile"] == 100.0  # 1400 >= 1300,1350,1400 = 3/3
    assert ctx["sample_n"] == 3
    assert "예측 아님" in ctx["note"]


@pytest.mark.django_db
def test_fx_context_unavailable_no_data(db):
    # ExchangeRate 없음 → available False
    assert eng.fx_context("USDKRW") == {"available": False}


@pytest.mark.django_db
def test_recommend_v2_includes_fx_context_and_labels(user, wallet, fx_rates):
    h = _hold(wallet, _stock("GGG", "USD", "120"), shares="1", avg_cost="100")
    h.acquisition_fx_rate = Decimal("1300")
    h.save()
    mc.upsert_cash_for_wallet(wallet, Decimal("100"), currency="USD")
    mc.upsert_goal_for_user(user, target_return_pct=Decimal("50"), horizon_months=12)

    out = eng.recommend(user)
    assert out["summary"]["numeraire"] == "KRW"
    assert out["summary"]["fx_context"]["available"] is True
    assert "cost_basis_note" in out["summary"]
    assert "예측" in out["disclaimer"]
