"""
DailyPrice 3년 백필 겹침 대조 게이트 테스트 (TH-9, 결정14=A).

커버: no_data / 미등록 종목 / 겹침 일치→쓰기 / 겹침 불일치→정지(DB 무접촉) / 멱등.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from packages.shared.stocks.models import DailyPrice, Stock
from packages.shared.stocks.services.daily_price_backfill import backfill_daily_prices

FROM, TO = date(2023, 1, 1), date(2026, 1, 1)


def _client(bars):
    c = MagicMock()
    c.get_historical_price.return_value = bars
    return c


def _existing(st, d, close):
    DailyPrice.objects.create(
        stock=st, currency="USD", date=d,
        open_price=Decimal("1"), high_price=Decimal("1"), low_price=Decimal("1"),
        close_price=Decimal(str(close)), volume=1000,
    )


@pytest.mark.django_db
class TestBackfillGate:
    def test_stock_not_registered(self):
        r = backfill_daily_prices(_client([{"date": "2025-01-02", "close": 100}]), ["ZZZ"], FROM, TO)
        assert r["errors"]["ZZZ"] == "stock_not_registered"

    def test_no_data(self):
        Stock.objects.create(symbol="AAA")
        r = backfill_daily_prices(_client([]), ["AAA"], FROM, TO)
        assert r["errors"]["AAA"] == "no_data" and r["written"] == 0

    def test_overlap_match_writes(self):
        st = Stock.objects.create(symbol="AAA")
        _existing(st, date(2025, 1, 2), 100)
        bars = [
            {"date": "2025-01-02", "open": 100, "high": 100, "low": 100, "close": 100.2, "volume": 1000},
            {"date": "2025-01-03", "open": 101, "high": 101, "low": 101, "close": 101, "volume": 1000},
        ]
        r = backfill_daily_prices(_client(bars), ["AAA"], FROM, TO)  # 오차 0.2% < 0.5%
        assert not r["halted"] and r["written"] == 2
        assert DailyPrice.objects.filter(stock=st).count() == 2

    def test_overlap_mismatch_halts_no_write(self):
        st = Stock.objects.create(symbol="AAA")
        _existing(st, date(2025, 1, 2), 100)
        bars = [{"date": "2025-01-02", "open": 150, "high": 150, "low": 150, "close": 150, "volume": 1000}]
        r = backfill_daily_prices(_client(bars), ["AAA"], FROM, TO)  # 50% 오차 → 정지
        assert r["halted"] and r["halted"][0][0] == "AAA"
        assert DailyPrice.objects.filter(stock=st).count() == 1  # 기존만, 쓰기 없음
        assert r["overlap_max_err"] >= 0.5

    def test_idempotent(self):
        st = Stock.objects.create(symbol="AAA")
        bars = [{"date": "2025-01-02", "open": 100, "high": 100, "low": 100, "close": 100, "volume": 1000}]
        backfill_daily_prices(_client(bars), ["AAA"], FROM, TO)
        backfill_daily_prices(_client(bars), ["AAA"], FROM, TO)
        assert DailyPrice.objects.filter(stock=st).count() == 1  # 멱등 upsert
