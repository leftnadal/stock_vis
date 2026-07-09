"""Monitor REST API 검증 (MON-P2-S3): 인증·user 스코프·평가 action."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.monitor.models import Monitor, MonitorIndicator

User = get_user_model()


@pytest.fixture
def aapl(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="AAPL", stock_name="Apple Inc.")


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password="pw12345")


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="bob", password="pw12345")


@pytest.fixture
def client_alice(alice):
    c = APIClient()
    c.force_authenticate(user=alice)
    return c


@pytest.mark.django_db
class TestMonitorAPIAuth:
    def test_unauthenticated_rejected(self):
        resp = APIClient().get("/api/v1/monitor/monitors/")
        assert resp.status_code in (401, 403)

    def test_create_normalizes_target(self, client_alice, aapl, alice):
        resp = client_alice.post(
            "/api/v1/monitor/monitors/",
            {"scope": "stock", "target_ref": "aapl", "name": "애플"},
            format="json",
        )
        assert resp.status_code == 201, resp.content
        assert resp.data["target_ref"] == "AAPL"  # 정규화
        assert Monitor.objects.get(id=resp.data["id"]).user_id == alice.id

    def test_create_invalid_symbol_400(self, client_alice, db):
        resp = client_alice.post(
            "/api/v1/monitor/monitors/",
            {"scope": "stock", "target_ref": "NOPE", "name": "x"},
            format="json",
        )
        assert resp.status_code == 400

    def test_create_unsupported_scope_400(self, client_alice, db):
        resp = client_alice.post(
            "/api/v1/monitor/monitors/",
            {"scope": "sector", "target_ref": "tech", "name": "x"},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestMonitorAPIScope:
    def test_list_scoped_to_user(self, client_alice, bob):
        Monitor.objects.create(
            user=bob, scope="stock", target_ref="MSFT", name="밥 것"
        )
        resp = client_alice.get("/api/v1/monitor/monitors/")
        assert resp.status_code == 200
        data = resp.data
        items = data["results"] if isinstance(data, dict) and "results" in data else data
        assert len(items) == 0  # 밥의 Monitor는 앨리스에게 안 보임

    def test_cannot_add_indicator_to_others_monitor(self, client_alice, bob):
        bob_mon = Monitor.objects.create(
            user=bob, scope="stock", target_ref="MSFT", name="밥 것"
        )
        resp = client_alice.post(
            "/api/v1/monitor/indicators/",
            {
                "monitor": str(bob_mon.id),
                "name": "침입",
                "indicator_type": "market_data",
            },
            format="json",
        )
        assert resp.status_code == 403
        assert MonitorIndicator.objects.count() == 0


@pytest.mark.django_db
class TestEvaluateAction:
    def test_evaluate_returns_result(self, client_alice, alice):
        mon = Monitor.objects.create(
            user=alice, scope="stock", target_ref="AAPL", name="애플"
        )
        resp = client_alice.post(f"/api/v1/monitor/monitors/{mon.id}/evaluate/")
        assert resp.status_code == 200, resp.content
        assert resp.data["monitor_id"] == str(mon.id)
        assert "overall_score" in resp.data
        assert "state" in resp.data

    def test_evaluate_others_monitor_404(self, client_alice, bob):
        bob_mon = Monitor.objects.create(
            user=bob, scope="stock", target_ref="MSFT", name="밥 것"
        )
        resp = client_alice.post(f"/api/v1/monitor/monitors/{bob_mon.id}/evaluate/")
        assert resp.status_code == 404  # user 스코프 → 존재하지 않음
