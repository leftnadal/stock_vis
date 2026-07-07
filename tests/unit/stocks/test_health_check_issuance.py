"""health_check 발행 로그 신선도 항목 자기검증 — D-HC-ISSUANCE.

check_issuance_log_freshness의 3분기 회귀:
  - 빈 이력 → OK-skip(노이즈 0, bake 미실행 환경).
  - 최근 거래일 행 존재 → OK.
  - 이력은 있으나 stale(임계 초과) → WARN(#46 재발 신호).
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from scripts.health_check import (
    ISSUANCE_STALE_DAYS,
    OK,
    WARN,
    check_issuance_log_freshness,
)

pytestmark = pytest.mark.unit


def _make_issuance(signal_date):
    from packages.shared.stocks.models import IssuanceLog, Stock

    stock, _ = Stock.objects.get_or_create(
        symbol="AAA", defaults={"stock_name": "Alpha"}
    )
    IssuanceLog.objects.create(
        stock=stock,
        signal_date=signal_date,
        signal_tag="V1",
        confidence="high",
        composite_score=0.5,
        conf_ver=1,
        rank=1,
        published_at=datetime.now(timezone.utc),
        user_id=None,
    )


@pytest.mark.django_db
def test_issuance_freshness_ok_when_no_history():
    result = check_issuance_log_freshness()
    assert result.status == OK
    assert "이력 없음" in result.detail


@pytest.mark.django_db
def test_issuance_freshness_ok_when_recent():
    _make_issuance(date.today())
    result = check_issuance_log_freshness()
    assert result.status == OK


@pytest.mark.django_db
def test_issuance_freshness_warns_when_stale():
    _make_issuance(date.today() - timedelta(days=ISSUANCE_STALE_DAYS + 3))
    result = check_issuance_log_freshness()
    assert result.status == WARN
    assert "stale" in result.detail.lower()
