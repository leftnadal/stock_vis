"""AGENT-S1 — 미국장 거래일 판정."""
from datetime import date

import pytest

from auto_agent_system.dogfood.market_calendar import (
    holiday_name,
    is_trading_day,
    previous_trading_day,
    target_session_date,
    trading_days_between,
)


@pytest.mark.parametrize(
    "day,name",
    [
        (date(2026, 1, 1), "New Year's Day"),
        (date(2026, 1, 19), "Martin Luther King Jr. Day"),
        (date(2026, 2, 16), "Washington's Birthday"),
        (date(2026, 4, 3), "Good Friday"),
        (date(2026, 5, 25), "Memorial Day"),
        (date(2026, 6, 19), "Juneteenth"),
        (date(2026, 9, 7), "Labor Day"),
        (date(2026, 11, 26), "Thanksgiving Day"),
        (date(2026, 12, 25), "Christmas Day"),
    ],
)
def test_nyse_holidays_2026(day, name):
    assert holiday_name(day) == name
    assert is_trading_day(day) is False


def test_observed_shift_when_holiday_falls_on_weekend():
    # 2026-07-04는 토요일 → 직전 금요일(07-03)로 이동
    assert date(2026, 7, 4).weekday() == 5
    assert holiday_name(date(2026, 7, 3)) == "Independence Day"
    assert holiday_name(date(2026, 7, 4)) == "Weekend"


def test_weekend_is_not_a_trading_day():
    assert holiday_name(date(2026, 8, 29)) == "Weekend"  # 토
    assert holiday_name(date(2026, 8, 30)) == "Weekend"  # 일
    assert is_trading_day(date(2026, 8, 28)) is True     # 금


def test_previous_trading_day_skips_weekend_and_holiday():
    # 월요일 직전 거래일 = 금요일
    assert previous_trading_day(date(2026, 8, 31)) == date(2026, 8, 28)
    # 추수감사절 다음날(금)의 직전 거래일 = 수요일(목요일 휴장)
    assert previous_trading_day(date(2026, 11, 27)) == date(2026, 11, 25)


def test_target_session_is_previous_trading_day():
    """05:20 KST 실행은 '전날 미국 세션'을 점검 대상으로 삼는다."""
    assert target_session_date(date(2026, 8, 27)) == date(2026, 8, 26)
    # 월요일 새벽 실행 → 금요일 세션
    assert target_session_date(date(2026, 8, 31)) == date(2026, 8, 28)


@pytest.mark.parametrize(
    "start,end,expected",
    [
        (date(2026, 8, 25), date(2026, 8, 26), 1),   # 화→수 평일 연속
        (date(2026, 8, 28), date(2026, 8, 31), 1),   # 금→월 (주말 낌)
        (date(2026, 9, 4), date(2026, 9, 8), 1),     # 금→화 (주말+Labor Day) = 09-09 재현
        (date(2026, 11, 25), date(2026, 11, 27), 1), # 수→금 (추수감사절 목 휴장)
        (date(2026, 8, 26), date(2026, 8, 26), 0),   # 동일일
        (date(2026, 8, 26), date(2026, 8, 20), 0),   # end < start
        (date(2026, 8, 25), date(2026, 8, 27), 2),   # 2 거래일 뒤처짐
    ],
)
def test_trading_days_between_counts_sessions_not_calendar_days(start, end, expected):
    """start(미포함)~end(포함) 사이의 거래일 수. 주말·휴장은 세지 않는다."""
    assert trading_days_between(start, end) == expected
