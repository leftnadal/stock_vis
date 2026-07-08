"""§8.7 strip API — 응답 스키마 + 쿼리 수 상한 + 인증."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.credit_signals.models import CreditSignalState, MacroSeriesHistory

STRIP_URL = "/api/credit-signals/strip/"


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(username="cs_tester", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _seed_signal(signal_key, series_id, n_spark=35):
    start = date(2026, 6, 1)
    for i in range(n_spark):
        MacroSeriesHistory.objects.create(
            series_id=series_id, date=start + timedelta(days=i),
            value=Decimal("3.50") + Decimal(str(i)) / 100,
        )
    CreditSignalState.objects.create(
        signal_key=signal_key, as_of=start + timedelta(days=n_spark - 1),
        value=Decimal("3.85"), z_score=Decimal("0.4000"), grade="gray", detail={},
    )


@pytest.mark.django_db
class TestStripApi:
    def test_requires_auth(self):
        resp = APIClient().get(STRIP_URL)
        assert resp.status_code in (401, 403)  # 파생 자산 — 인증 필요

    def test_schema(self, auth_client):
        _seed_signal("HY_OAS", "BAMLH0A0HYM2")
        _seed_signal("VIX", "VIXCLS")
        resp = auth_client.get(STRIP_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"as_of", "signals"}
        assert data["as_of"] is not None
        assert len(data["signals"]) == 2
        sig = next(s for s in data["signals"] if s["key"] == "HY_OAS")
        assert set(sig.keys()) == {"key", "name", "value", "z", "grade", "spark"}
        assert sig["name"] == "US HY OAS"
        assert sig["grade"] == "gray"
        assert sig["z"] == 0.4
        # spark = 최근 30 관측치 (35개 시드 → 30으로 제한)
        assert len(sig["spark"]) == 30
        assert set(sig["spark"][0].keys()) == {"date", "value"}
        # 오름차순 (오래된 → 최신)
        dates = [p["date"] for p in sig["spark"]]
        assert dates == sorted(dates)

    def test_empty_state_returns_empty_signals(self, auth_client):
        resp = auth_client.get(STRIP_URL)
        assert resp.status_code == 200
        assert resp.json() == {"as_of": None, "signals": []}

    def test_query_count_bounded(self, auth_client, django_assert_max_num_queries):
        """N+1 금지: 상태 1쿼리 + 시리즈별 spark 단일 쿼리 (6종 기준 상한 고정)."""
        for key, sid in [
            ("HY_OAS", "BAMLH0A0HYM2"), ("IG_OAS", "BAMLC0A0CM"),
            ("BBB_OAS", "BAMLC0A4CBBB"), ("CCC_OAS", "BAMLH0A3HYC"),
            ("CURVE_10Y2Y", "T10Y2Y"), ("VIX", "VIXCLS"),
        ]:
            _seed_signal(key, sid, n_spark=35)
        # 1(states) + 6(spark) = 7. 인증 오버헤드 여유 포함 상한 10.
        with django_assert_max_num_queries(10):
            resp = auth_client.get(STRIP_URL)
        assert resp.status_code == 200
        assert len(resp.json()["signals"]) == 6
