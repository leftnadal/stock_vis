"""SFI-I-2 Part 1 — AnalystSignalSnapshot 조회 API (read-only) 테스트.

GET 최신 1건(4신호 + grades_historical + captured_at). 미수집=null 계약(available:false, 200).
append 테이블에서 latest 판별. 인증 필수.
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from packages.shared.stocks.models import AnalystSignalSnapshot

User = get_user_model()
URL = "/api/v1/stocks/api/analyst-signals/{}/"


@pytest.fixture
def auth_client(db):
    u = User.objects.create_user(username="i2-user")
    c = APIClient()
    c.force_authenticate(u)
    return c


def _snap(symbol, consensus="100", **kw):
    defaults = dict(
        symbol=symbol, source="fmp",
        target_consensus=Decimal(consensus), target_high=Decimal("120"),
        target_low=Decimal("80"), target_median=Decimal("105"),
        grade_strong_buy=1, grade_buy=70, grade_hold=32, grade_sell=8,
        grade_strong_sell=0, grade_consensus="Buy",
        grades_historical=[{"date": "2026-08-01", "analystRatingsBuy": 22,
                            "analystRatingsStrongBuy": 6, "analystRatingsHold": 14,
                            "analystRatingsSell": 2, "analystRatingsStrongSell": 2}],
        rating="B", overall_score=3,
    )
    defaults.update(kw)
    return AnalystSignalSnapshot.objects.create(**defaults)


@pytest.mark.django_db
class TestAnalystSignalsAPI:
    def test_present_returns_full_signal(self, auth_client):
        _snap("AAPL", consensus="341.11")
        r = auth_client.get(URL.format("aapl"))  # 소문자 → upper
        assert r.status_code == 200
        d = r.json()
        assert d["available"] is True
        assert d["symbol"] == "AAPL"
        assert d["target"]["consensus"] == "341.1100"  # Decimal→str
        assert d["target"]["high"] == "120.0000"
        assert d["grades"]["buy"] == 70
        assert d["grades"]["consensus"] == "Buy"
        assert d["rating"] == "B" and d["overall_score"] == 3
        assert isinstance(d["grades_historical"], list) and d["grades_historical"]
        assert d["captured_at"]

    def test_absent_null_contract(self, auth_client):
        r = auth_client.get(URL.format("NOPE"))
        assert r.status_code == 200
        d = r.json()
        assert d["available"] is False
        assert d["symbol"] == "NOPE"

    def test_latest_row_selected(self, auth_client):
        _snap("TSLA", consensus="431.09")   # 먼저(older)
        _snap("TSLA", consensus="436.08")   # 나중(newer)
        r = auth_client.get(URL.format("TSLA"))
        assert r.json()["target"]["consensus"] == "436.0800"  # 최신

    def test_requires_auth(self):
        r = APIClient().get(URL.format("AAPL"))
        assert r.status_code in (401, 403)
