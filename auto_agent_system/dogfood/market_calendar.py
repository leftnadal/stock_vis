"""미국 주식시장(NYSE/NASDAQ) 거래일 판정 — 표준 라이브러리만 사용.

야간 도그푸딩 에이전트(AGENT-S1)가 "미국장 휴장이면 스킵"을 판정하는 데 쓴다.
외부 캘린더 패키지(pandas_market_calendars 등)는 이 repo에 설치돼 있지 않아
NYSE 정규 휴장 규칙을 직접 구현한다. 조기폐장(반일)은 거래일이므로 다루지 않는다.

규칙 출처 = NYSE 정규 휴장 9종 + Juneteenth(2022~). 토·일은 항상 휴장.
휴장일이 토요일이면 직전 금요일, 일요일이면 다음 월요일로 이동(observed).
"""

from __future__ import annotations

from datetime import date, timedelta

__all__ = ["is_trading_day", "previous_trading_day", "target_session_date", "holiday_name"]


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """그 달의 n번째 <weekday>(월=0). n=-1이면 마지막."""
    if n > 0:
        d = date(year, month, 1)
        offset = (weekday - d.weekday()) % 7
        return d + timedelta(days=offset + 7 * (n - 1))
    d = date(year, month, 28)
    while (d + timedelta(days=7)).month == month:
        d += timedelta(days=7)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _easter(year: int) -> date:
    """그레고리력 부활절(Anonymous Gregorian algorithm). Good Friday 계산용."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month, day = divmod(h + ell - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _observed(d: date) -> date:
    """고정일 휴장의 observed 이동 — 토→직전 금, 일→다음 월."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _holidays(year: int) -> dict[date, str]:
    h: dict[date, str] = {
        _observed(date(year, 1, 1)): "New Year's Day",
        _nth_weekday(year, 1, 0, 3): "Martin Luther King Jr. Day",
        _nth_weekday(year, 2, 0, 3): "Washington's Birthday",
        _easter(year) - timedelta(days=2): "Good Friday",
        _nth_weekday(year, 5, 0, -1): "Memorial Day",
        _observed(date(year, 7, 4)): "Independence Day",
        _nth_weekday(year, 9, 0, 1): "Labor Day",
        _nth_weekday(year, 11, 3, 4): "Thanksgiving Day",
        _observed(date(year, 12, 25)): "Christmas Day",
    }
    if year >= 2022:
        h[_observed(date(year, 6, 19))] = "Juneteenth"
    return h


def holiday_name(d: date) -> str | None:
    """휴장 사유. 거래일이면 None."""
    if d.weekday() >= 5:
        return "Weekend"
    return _holidays(d.year).get(d)


def is_trading_day(d: date) -> bool:
    return holiday_name(d) is None


def previous_trading_day(d: date) -> date:
    """d 직전(미포함)의 거래일."""
    cur = d - timedelta(days=1)
    while not is_trading_day(cur):
        cur -= timedelta(days=1)
    return cur


def target_session_date(run_date_kst: date) -> date:
    """05:20 KST 실행이 점검 대상으로 삼는 미국 세션 날짜.

    한국 05:20은 미국 동부 기준 전날 오후(장 마감 직후)다. 따라서 대상 세션 =
    실행일(KST)의 **전날**이며, 그날이 휴장이면 그 이전 거래일로 거슬러 올라간다.
    """
    return previous_trading_day(run_date_kst)
