"""P2a-1c — NYSE 거래일 캘린더 (is/next/previous_trading_day · 커버리지 예외 · 경보)."""
import logging
from datetime import date

import pytest

from apps.credit_signals.trading_calendar import (
    CalendarCoverageError,
    COVERAGE_MAX,
    is_trading_day,
    next_trading_day,
    previous_trading_day,
    warn_if_coverage_expiring,
)


class TestIsTradingDay:
    def test_weekday_is_trading(self):
        assert is_trading_day(date(2026, 8, 5)) is True  # 수요일

    def test_weekend_not_trading(self):
        assert is_trading_day(date(2026, 8, 1)) is False  # 토
        assert is_trading_day(date(2026, 8, 2)) is False  # 일

    def test_holiday_not_trading(self):
        assert is_trading_day(date(2026, 1, 19)) is False  # MLK
        assert is_trading_day(date(2026, 12, 25)) is False  # Christmas

    def test_coverage_out_of_range_raises(self):
        with pytest.raises(CalendarCoverageError):
            is_trading_day(date(2029, 1, 2))  # 커버리지 밖 → 명시적 예외


class TestPreviousTradingDay:
    def test_normal_weekday(self):
        assert previous_trading_day(date(2026, 8, 6)) == date(2026, 8, 5)

    def test_over_weekend(self):
        # 월 08-03 → 금 07-31 (토·일 skip)
        assert previous_trading_day(date(2026, 8, 3)) == date(2026, 7, 31)

    def test_over_holiday(self):
        # 화 01-20 → 금 01-16 (01-19 월 MLK + 주말 skip)
        assert previous_trading_day(date(2026, 1, 20)) == date(2026, 1, 16)


class TestNextTradingDay:
    def test_normal(self):
        assert next_trading_day(date(2026, 8, 5)) == date(2026, 8, 6)

    def test_over_weekend(self):
        # 금 07-31 → 월 08-03
        assert next_trading_day(date(2026, 7, 31)) == date(2026, 8, 3)


class TestCoverageWarning:
    def test_warns_when_current_year_reaches_max(self, caplog):
        with caplog.at_level(logging.WARNING):
            warn_if_coverage_expiring(date(COVERAGE_MAX, 6, 1))
        assert any("커버리지 만료 임박" in r.message for r in caplog.records)

    def test_no_warn_before_max(self, caplog):
        with caplog.at_level(logging.WARNING):
            warn_if_coverage_expiring(date(2026, 6, 1))
        assert not any("커버리지 만료 임박" in r.message for r in caplog.records)
