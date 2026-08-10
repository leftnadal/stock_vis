"""
미국(NYSE) 거래일 캘린더 — P2a-1c C″ 전일 귀속용.

NYSE 휴일 테이블 + is/next/previous_trading_day. numpy busday(주말만)로는
D-1 귀속에서 휴일 경계(월요일 게시 → 금요일 귀속 등)를 못 잡으므로 휴일 테이블이
필요하다. 캘린더 라이브러리(pandas_market_calendars 등)는 미설치 → 자체 테이블.

MIRROR of services/news/services/ml_label_collector.py ALL_NYSE_HOLIDAYS
— 2025~2026은 그 원본을 그대로 복제한다(원본 갱신 시 본 테이블도 동기화).
  ⚠️ 원본은 Juneteenth(6/19)를 누락하고 있어 2025~2026은 원본과 동일하게 제외했다.
  2027~2028은 본 파일에서 신규 추가하며 NYSE 표준(Juneteenth 포함)을 따른다.
  news 측 파일은 무접촉(읽기 참조만, import 금지 — 크로스트랙 경계 규약).
[보류 큐] 캘린더 유틸 shared 통합(밴드 메타데이터 공용화·미러 철거와 동일 시점 재검토).
"""
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# ── 2025~2026: news ALL_NYSE_HOLIDAYS 미러 (원본 그대로) ──
NYSE_HOLIDAYS_2025 = {
    date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 4, 18),
    date(2025, 5, 26), date(2025, 7, 4), date(2025, 9, 1), date(2025, 11, 27),
    date(2025, 12, 25),
}
NYSE_HOLIDAYS_2026 = {
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3),
    date(2026, 5, 25), date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26),
    date(2026, 12, 25),
}
# ── 2027~2028: 본 파일 신규 (NYSE 표준, Juneteenth 포함) ──
NYSE_HOLIDAYS_2027 = {
    date(2027, 1, 1),    # New Year's Day
    date(2027, 1, 18),   # MLK Jr. Day
    date(2027, 2, 15),   # Presidents' Day
    date(2027, 3, 26),   # Good Friday
    date(2027, 5, 31),   # Memorial Day
    date(2027, 6, 18),   # Juneteenth (observed, 6/19 Sat)
    date(2027, 7, 5),    # Independence Day (observed, 7/4 Sun)
    date(2027, 9, 6),    # Labor Day
    date(2027, 11, 25),  # Thanksgiving
    date(2027, 12, 24),  # Christmas (observed, 12/25 Sat)
}
NYSE_HOLIDAYS_2028 = {
    date(2028, 1, 17),   # MLK Jr. Day (New Year 1/1 Sat — no makeup)
    date(2028, 2, 21),   # Presidents' Day
    date(2028, 4, 14),   # Good Friday
    date(2028, 5, 29),   # Memorial Day
    date(2028, 6, 19),   # Juneteenth
    date(2028, 7, 4),    # Independence Day
    date(2028, 9, 4),    # Labor Day
    date(2028, 11, 23),  # Thanksgiving
    date(2028, 12, 25),  # Christmas
}

ALL_NYSE_HOLIDAYS = (
    NYSE_HOLIDAYS_2025 | NYSE_HOLIDAYS_2026 | NYSE_HOLIDAYS_2027 | NYSE_HOLIDAYS_2028
)
COVERAGE_YEARS = frozenset({2025, 2026, 2027, 2028})
COVERAGE_MIN, COVERAGE_MAX = min(COVERAGE_YEARS), max(COVERAGE_YEARS)


class CalendarCoverageError(ValueError):
    """휴일 테이블 커버리지 밖 날짜 — 조용한 오판정 방지(명시적 실패)."""


def _check_coverage(d: date) -> None:
    if d.year not in COVERAGE_YEARS:
        raise CalendarCoverageError(
            f"{d} 는 NYSE 휴일 테이블 커버리지({COVERAGE_MIN}~{COVERAGE_MAX}) 밖 — "
            f"trading_calendar 연도 확장 필요(조용한 거래일 오판정 금지)."
        )


def warn_if_coverage_expiring(today: date) -> None:
    """캘린더 마지막 연도 == 현재 연도이면 만료 임박 경보(테이블 확장 리마인더)."""
    if today.year >= COVERAGE_MAX:
        logger.warning(
            "NYSE 휴일 테이블 커버리지 만료 임박: 현재 연도 %d ≥ 마지막 커버 연도 %d "
            "— trading_calendar 테이블을 다음 연도로 확장하라.",
            today.year, COVERAGE_MAX,
        )


def is_trading_day(d: date) -> bool:
    """NYSE 거래일 여부(주말·휴일 제외). 커버리지 밖이면 CalendarCoverageError."""
    _check_coverage(d)
    if d.weekday() >= 5:  # Sat=5, Sun=6
        return False
    return d not in ALL_NYSE_HOLIDAYS


def next_trading_day(d: date) -> date:
    """d 이후 첫 거래일."""
    c = d + timedelta(days=1)
    while not is_trading_day(c):
        c += timedelta(days=1)
    return c


def previous_trading_day(d: date) -> date:
    """d 이전 첫 거래일 (D-1 귀속의 핵심)."""
    c = d - timedelta(days=1)
    while not is_trading_day(c):
        c -= timedelta(days=1)
    return c
