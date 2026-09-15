"""as_of_week() 규칙 검증 — 관측일 → 대상일(as_of) 매핑 (DSS-ASOF-1 STEP 1).

주간 마감 = 금요일 16:00 ET. 관측 시각 기준 '가장 최근에 완료된 주간 마감'을 돌려준다.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from packages.shared.market_week import as_of_week

ET = ZoneInfo("America/New_York")


@pytest.mark.parametrize(
    "label, observed, expected",
    [
        # ① 정상 발화: 금 16:30 ET (beat Fri 16:30) → 그 금요일
        ("정상 금 16:30", datetime(2026, 9, 4, 16, 30, tzinfo=ET), date(2026, 9, 4)),
        # ② 토요일 catch-up (2026-09-12 실사례) → 직전 금요일
        ("토요일 catch-up", datetime(2026, 9, 12, 15, 3, tzinfo=ET), date(2026, 9, 11)),
        # ③ 일요일 → 직전 금요일
        ("일요일", datetime(2026, 9, 13, 9, 0, tzinfo=ET), date(2026, 9, 11)),
        # ④ 월요일 catch-up (2026-07-27 실사례) → 직전 금요일
        ("월요일 catch-up", datetime(2026, 7, 27, 22, 48, tzinfo=ET), date(2026, 7, 24)),
        # ⑤ 금요일 장중 15:59 ET — 그 주 마감 미완료 → 직전 금요일
        ("금요일 장중", datetime(2026, 9, 11, 15, 59, tzinfo=ET), date(2026, 9, 4)),
    ],
)
def test_as_of_week_rules(label, observed, expected):
    assert as_of_week(observed) == expected, label


def test_friday_close_boundary_is_inclusive():
    """정확히 16:00:00 ET = 마감 완료로 본다 (경계 포함)."""
    assert as_of_week(datetime(2026, 9, 11, 16, 0, tzinfo=ET)) == date(2026, 9, 11)
    assert as_of_week(datetime(2026, 9, 11, 15, 59, 59, tzinfo=ET)) == date(2026, 9, 4)


def test_utc_input_is_converted_to_et():
    """tz-aware 입력은 ET로 변환된다. 09-12 19:03 UTC = 09-12 15:03 ET → 09-11."""
    utc = ZoneInfo("UTC")
    assert as_of_week(datetime(2026, 9, 12, 19, 3, tzinfo=utc)) == date(2026, 9, 11)


def test_naive_input_treated_as_et():
    assert as_of_week(datetime(2026, 9, 12, 15, 3)) == date(2026, 9, 11)


def test_date_input_rejected():
    with pytest.raises(TypeError):
        as_of_week(date(2026, 9, 12))
