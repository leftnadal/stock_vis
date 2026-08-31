"""이벤트 캘린더 API 테스트 (EVT-IMPL-4 STEP 2-3).

인증 필수 · 파라미터 검증(scope/kind/span/date) · EventFeed shape.
"""
import datetime as _dt
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.monitor.models.monitor import Monitor
from packages.shared.stocks.models import CalendarEvent

User = get_user_model()
_ET = ZoneInfo("America/New_York")
URL = "/api/v1/monitor/calendar/"
FEED_KEYS = {"as_of", "start", "end", "scope", "symbols", "counts", "items"}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="cal_api_u", password="pw")


@pytest.fixture
def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


class TestCalendarApi:
    def test_requires_auth(self, db):
        resp = APIClient().get(URL)
        assert resp.status_code in (401, 403)

    def test_feed_shape(self, auth_client):
        resp = auth_client.get(URL)
        assert resp.status_code == 200
        assert set(resp.json().keys()) == FEED_KEYS
        assert resp.json()["scope"] == "monitor"
        assert isinstance(resp.json()["items"], list)

    def test_bad_scope_400(self, auth_client):
        assert auth_client.get(URL, {"scope": "nope"}).status_code == 400

    def test_bad_kind_400(self, auth_client):
        assert auth_client.get(URL, {"kinds": "earnings,bogus"}).status_code == 400

    def test_bad_date_400(self, auth_client):
        assert auth_client.get(URL, {"from": "2026/09/01"}).status_code == 400

    def test_span_cap_400(self, auth_client):
        assert auth_client.get(URL, {"from": "2026-01-01", "to": "2026-12-31"}).status_code == 400

    def test_bad_importance_400(self, auth_client):
        assert auth_client.get(URL, {"macro_min_importance": "huge"}).status_code == 400

    def test_scope_filters_symbols(self, auth_client, user):
        Monitor.objects.create(user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="a")
        et_today = _dt.datetime.now(tz=_ET).date()
        CalendarEvent.objects.create(
            event_type=CalendarEvent.EventType.EARNINGS, symbol="AAPL",
            event_date=et_today + _dt.timedelta(days=3), eps_estimated="1.0",
        )
        resp = auth_client.get(URL, {"scope": "monitor", "kinds": "earnings"})
        assert resp.status_code == 200
        syms = {it["symbol"] for it in resp.json()["items"]}
        assert syms == {"AAPL"}
