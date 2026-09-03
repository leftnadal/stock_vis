"""관계망 이벤트 피드 API 테스트 (EVT-CHAIN-1 STEP 2).

인증 필수 · symbol 파라미터 검증 · 빈 응답 shape · 데이터 응답.
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.chain_sight.models.relation_discovery import RelationConfidence
from apps.monitor.services.chain_feed import _ET
from packages.shared.stocks.models import CalendarEvent

User = get_user_model()
URL = "/api/v1/monitor/calendar/chain/"
CHAIN_KEYS = {
    "seed", "as_of", "seed_events", "seed_next_event",
    "neighbors", "items", "after_count", "params",
}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="chain_api_u", password="pw")


@pytest.fixture
def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


class TestChainApi:
    def test_requires_auth(self, db):
        resp = APIClient().get(URL, {"symbol": "IREN"})
        assert resp.status_code in (401, 403)

    def test_missing_symbol_400(self, auth_client):
        assert auth_client.get(URL).status_code == 400

    def test_bad_symbol_format_400(self, auth_client):
        assert auth_client.get(URL, {"symbol": "not a symbol!"}).status_code == 400

    def test_unknown_symbol_empty_not_404(self, auth_client):
        resp = auth_client.get(URL, {"symbol": "ZZZZ"})
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == CHAIN_KEYS
        assert body["seed"] == "ZZZZ"
        assert body["neighbors"] == []
        assert body["items"] == []

    def test_data_response_shape(self, auth_client):
        seed = "IREN"
        RelationConfidence.objects.create(
            symbol_a=seed, symbol_b="NBR", relation_type="SUPPLIES_TO",
            relation_status="confirmed", truth_score=0.90,
        )
        t = timezone.now().astimezone(_ET).date()
        CalendarEvent.objects.create(
            event_type=CalendarEvent.EventType.EARNINGS, symbol=seed,
            event_date=t + timedelta(days=30), status=CalendarEvent.Status.SCHEDULED,
            eps_estimated="-0.2",
        )
        CalendarEvent.objects.create(
            event_type=CalendarEvent.EventType.EARNINGS, symbol="NBR",
            event_date=t + timedelta(days=10), status=CalendarEvent.Status.SCHEDULED,
            eps_estimated="1.0",
        )
        resp = auth_client.get(URL, {"symbol": "iren"})  # 소문자 → 정규화
        assert resp.status_code == 200
        body = resp.json()
        assert body["seed"] == "IREN"
        assert len(body["neighbors"]) == 1
        assert body["neighbors"][0]["symbol"] == "NBR"
        assert len(body["items"]) == 1
        assert body["items"][0]["relation"]["type"] == "SUPPLIES_TO"
