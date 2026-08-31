"""홈 이벤트 스트립 BFF 테스트 (EVT-IMPL-4 STEP 2-3).

인증 필수 · 응답 shape · 관심 어닝 티저 상한 2 · 실패 격리.
"""
import datetime as _dt
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.dashboard.services.event_strip_service import build_event_strip
from apps.monitor.models.monitor import Monitor
from packages.shared.stocks.models import CalendarEvent

User = get_user_model()
_ET = ZoneInfo("America/New_York")
URL = "/api/dashboard/event-strip/"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="strip_u", password="pw")


def test_requires_auth(db):
    assert APIClient().get(URL).status_code in (401, 403)


def test_shape(user):
    c = APIClient()
    c.force_authenticate(user=user)
    resp = c.get(URL)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"as_of", "window_days", "items"}
    assert body["window_days"] == 45
    assert isinstance(body["items"], list)


def test_teaser_cap_two(user):
    et_today = _dt.datetime.now(tz=_ET).date()
    for i, sym in enumerate(["A1", "A2", "A3"], start=1):
        Monitor.objects.create(user=user, scope=Monitor.Scope.STOCK, target_ref=sym, name=sym)
        CalendarEvent.objects.create(
            event_type=CalendarEvent.EventType.EARNINGS, symbol=sym,
            event_date=et_today + _dt.timedelta(days=i), eps_estimated="1.0",
        )
    data = build_event_strip(user)
    teasers = [it for it in data["items"] if it["kind"] == "earnings"]
    assert len(teasers) <= 2  # 티저 상한 2


def test_failure_isolation_returns_empty(user, monkeypatch):
    # build_event_strip 은 함수 내부에서 monitor 서비스를 import → 모듈 속성 패치로 예외 주입.
    import apps.monitor.services.event_feed as feed

    def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(feed, "build_event_feed", _boom)
    data = build_event_strip(user)
    assert data["items"] == []
