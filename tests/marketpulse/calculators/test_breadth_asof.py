"""A-1(HUB-V02-S1): Breadth 직전 거래일 폴백 — 결측일에도 실데이터 산출, 명시 기준일은 IDENTICAL."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.market_pulse.calculators import breadth as bmod
from packages.shared.stocks.models import DailyPrice, SP500Constituent, Stock

pytestmark = pytest.mark.django_db


def _mk(sym: str):
    Stock.objects.create(symbol=sym)
    SP500Constituent.objects.create(symbol=sym, is_active=True)


def _price(sym: str, d, close):
    DailyPrice.objects.create(
        stock_id=sym,
        date=d,
        open_price=Decimal("1"),
        high_price=Decimal("1"),
        low_price=Decimal("1"),
        close_price=Decimal(str(close)),
        volume=1,
    )


def _seed(d_recent, d_prev):
    # AAA 상승 / BBB 하락 / CCC 보합
    for s in ("AAA", "BBB", "CCC"):
        _mk(s)
    _price("AAA", d_prev, 10)
    _price("AAA", d_recent, 11)
    _price("BBB", d_prev, 10)
    _price("BBB", d_recent, 9)
    _price("CCC", d_prev, 10)
    _price("CCC", d_recent, 10)


def test_resolve_as_of_date_latest_trading_day():
    today = timezone.localdate()
    d_recent, d_prev = today - timedelta(days=1), today - timedelta(days=2)
    _seed(d_recent, d_prev)
    assert bmod.resolve_as_of_date("SPY") == d_recent  # 오늘 데이터 없음 → 직전 거래일


def test_compute_none_uses_latest_not_today():
    today = timezone.localdate()
    d_recent, d_prev = today - timedelta(days=1), today - timedelta(days=2)
    _seed(d_recent, d_prev)
    m = bmod.compute_breadth(universe="SPY")  # target 미지정 → 직전 거래일 해석
    assert (m.advance_count, m.decline_count, m.unchanged_count, m.total_count) == (1, 1, 1, 3)


def test_explicit_today_is_identical_zero():
    # 명시 target_date=today(데이터 없음) → 종전과 IDENTICAL(total 0). 행위보존.
    today = timezone.localdate()
    d_recent, d_prev = today - timedelta(days=1), today - timedelta(days=2)
    _seed(d_recent, d_prev)
    m = bmod.compute_breadth(universe="SPY", target_date=today)
    assert m.total_count == 0 and m.advance_count == 0


def test_explicit_recent_matches_none_default():
    today = timezone.localdate()
    d_recent, d_prev = today - timedelta(days=1), today - timedelta(days=2)
    _seed(d_recent, d_prev)
    m_explicit = bmod.compute_breadth(universe="SPY", target_date=d_recent)
    m_none = bmod.compute_breadth(universe="SPY")
    assert (m_explicit.advance_count, m_explicit.decline_count, m_explicit.total_count) == (
        m_none.advance_count,
        m_none.decline_count,
        m_none.total_count,
    )


def test_no_price_data_falls_back_to_today_zero():
    # DailyPrice 전무 → resolve None → localdate 폴백 → total 0(진짜 데이터 없음).
    for s in ("AAA", "BBB"):
        _mk(s)
    assert bmod.resolve_as_of_date("SPY") is None
    m = bmod.compute_breadth(universe="SPY")
    assert m.total_count == 0


def test_calculate_stores_under_data_date():
    # calculate()는 compute·store 기준일을 일원화 → 스냅샷이 데이터 날짜로 저장(오늘 아님).
    today = timezone.localdate()
    d_recent, d_prev = today - timedelta(days=1), today - timedelta(days=2)
    _seed(d_recent, d_prev)
    snap = bmod.calculate(universe="SPY")
    assert snap.date == d_recent and snap.total_count == 3
