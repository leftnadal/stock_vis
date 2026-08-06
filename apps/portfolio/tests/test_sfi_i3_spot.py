"""SFI-I3 Part 1 — AnalystSignalSnapshot spot_at_capture 동봉 + 기존 수집 회귀."""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from packages.shared.stocks.models import AnalystSignalSnapshot, DailyPrice, Stock
from packages.shared.stocks.services.analyst_signal_writer import capture_symbol


def _fake_client():
    c = Mock()
    c.get_ratings_snapshot.return_value = {"rating": "A", "overallScore": 4}
    c.get_price_target_consensus.return_value = {
        "targetConsensus": "150", "targetHigh": "180", "targetLow": "120", "targetMedian": "150",
    }
    c.get_grades_consensus.return_value = {
        "strongBuy": 5, "buy": 10, "hold": 3, "sell": 1, "strongSell": 0, "consensus": "Buy",
    }
    c.get_grades_historical.return_value = [{"date": "2026-01-01", "analystRatingsBuy": 10}]
    return c


@pytest.mark.django_db
def test_spot_pinned_from_latest_daily_price():
    s = Stock.objects.create(symbol="SPT", currency="USD")
    DailyPrice.objects.create(
        stock=s, date=date(2026, 1, 5), open_price=100, high_price=102, low_price=99,
        close_price=Decimal("101.5000"), volume=1000,
    )
    # 더 최신 종가 → 이 값이 spot이 되어야 함
    DailyPrice.objects.create(
        stock=s, date=date(2026, 1, 6), open_price=101, high_price=103, low_price=100,
        close_price=Decimal("102.7500"), volume=1200,
    )
    res = capture_symbol(_fake_client(), "SPT")
    assert res["created"] == 1
    snap = AnalystSignalSnapshot.objects.get(symbol="SPT")
    assert snap.spot_at_capture == Decimal("102.7500")  # 최신 close 동봉
    assert snap.target_consensus == Decimal("150")


@pytest.mark.django_db
def test_spot_null_when_no_price_but_capture_still_succeeds():
    # DailyPrice 없음 → spot null 허용, 발화(append) 자체는 성공(회귀)
    res = capture_symbol(_fake_client(), "NOPX", mirror=False)
    assert res["created"] == 1
    snap = AnalystSignalSnapshot.objects.get(symbol="NOPX")
    assert snap.spot_at_capture is None
    assert snap.grade_consensus == "Buy"  # 기존 수집 경로 무손상


@pytest.mark.django_db
def test_capture_empty_signals_no_row():
    c = Mock()
    c.get_ratings_snapshot.return_value = {}
    c.get_price_target_consensus.return_value = {}
    c.get_grades_consensus.return_value = {}
    c.get_grades_historical.return_value = []
    res = capture_symbol(c, "EMPTY")
    assert res["created"] == 0
    assert not AnalystSignalSnapshot.objects.filter(symbol="EMPTY").exists()
