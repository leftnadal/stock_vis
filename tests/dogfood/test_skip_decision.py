"""AGENT-CAL-1 — 야간 도그푸딩 휴장 스킵 판정은 '대상 세션(어제)' 기준이다.

05:20 KST에 도는 잡은 언제나 **어제 닫힌 세션**을 리뷰한다. 그래서 "오늘 장이
열리나"가 아니라 "어제 장이 열렸나"를 물어야 한다. 실행일 기준으로 물으면
토요일 발화가 Weekend로 스킵되어 **금요일 세션 리뷰가 토요일에 나가지 못한다**.

주의: 기준은 `target_session_date`(직전 **거래일**)가 아니라 **달력상 어제**다.
직전 거래일을 쓰면 일요일과 월요일이 모두 금요일 세션을 가리켜 같은 리뷰가
두 번 나간다(중복 발송).
"""
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from auto_agent_system.dogfood.market_calendar import holiday_name

RUN_DOGFOOD = Path(__file__).resolve().parents[2] / "auto_agent_system" / "dogfood" / "run_dogfood.sh"


def _skips(run_date: date) -> bool:
    """스크립트의 판정을 그대로 재현 — 어제가 휴장이면 스킵."""
    return holiday_name(run_date - timedelta(days=1)) is not None


# 실행일(KST), 스킵되는가, 대상 세션 설명
CASES = [
    (date(2026, 9, 19), False, "토 → 어제 금 09-18 = 거래일 → 실행(금요일 리뷰 복원)"),
    (date(2026, 9, 20), True,  "일 → 어제 토 09-19 = 주말 → 스킵"),
    (date(2026, 9, 21), True,  "월 → 어제 일 09-20 = 주말 → 스킵(행동 변화: 기존엔 실행)"),
    (date(2026, 9, 22), False, "화 → 어제 월 09-21 = 거래일 → 실행"),
    (date(2026, 9, 24), False, "목 → 어제 수 09-23 = 거래일 → 실행"),
    (date(2026, 11, 27), True, "금 → 어제 목 11-26 = Thanksgiving → 스킵"),
]


@pytest.mark.parametrize("run_date,expected_skip,why", CASES)
def test_skip_decision_uses_yesterday(run_date, expected_skip, why):
    assert _skips(run_date) is expected_skip, why


def test_saturday_runs_but_sunday_and_monday_skip():
    """이 수정의 실제 효과 — 금요일 리뷰가 월요일에서 토요일로 '이동'한다.

    리뷰가 없던 것이 생기는 게 아니라, 2일 늦게 오던 것이 제때 온다.
    그 대가로 월요일 발화는 스킵된다(그날 리뷰할 새 세션이 없다).
    """
    assert _skips(date(2026, 9, 19)) is False   # 토: 금요일 세션 리뷰 발송
    assert _skips(date(2026, 9, 20)) is True    # 일: 스킵
    assert _skips(date(2026, 9, 21)) is True    # 월: 스킵 ← 바뀐 지점


def test_no_duplicate_review_across_weekend():
    """달력상 어제를 쓰면 주말 동안 같은 세션을 두 번 리뷰하지 않는다.

    target_session_date(직전 거래일)를 썼다면 토·일·월 세 번 모두 금요일 세션을
    가리켰을 것이다. 이 테스트가 그 선택을 고정한다.
    """
    targets = [
        d - timedelta(days=1)
        for d in (date(2026, 9, 19), date(2026, 9, 20), date(2026, 9, 21))
        if not _skips(d)
    ]
    assert targets == [date(2026, 9, 18)]       # 금요일 세션, 정확히 한 번


def test_script_asks_about_yesterday_not_today():
    """회귀 차단 — 스크립트가 실행일로 되돌아가면 즉시 RED."""
    src = RUN_DOGFOOD.read_text()
    # 어제를 계산한다(변수로 뽑든 인라인이든 무관 — 로그에 날짜를 찍어야 해서 변수다).
    assert re.search(r"date\.today\(\)\s*-\s*timedelta\(days=1\)", src), (
        "run_dogfood.sh의 휴장 판정이 '어제' 기준이 아니다 — "
        "date.today() - timedelta(days=1)로 대상 세션을 구해야 한다"
    )
    # 실행일을 그대로 묻는 형태로 되돌아가면 RED.
    assert not re.search(r"holiday_name\(\s*date\.today\(\)\s*\)", src), (
        "run_dogfood.sh가 실행일(date.today()) 기준으로 휴장을 묻고 있다 — "
        "토요일 발화가 Weekend로 스킵되어 금요일 리뷰가 빠진다"
    )
