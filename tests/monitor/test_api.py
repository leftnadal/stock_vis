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


def _items(resp):
    data = resp.data
    return data["results"] if isinstance(data, dict) and "results" in data else data


@pytest.mark.django_db
class TestMonitorListOrderingFilter:
    """서버측 트리아지 정렬·필터 (MON-P3-S1 소보강): 위험→약화→관찰→유지."""

    def _mk(self, alice, ref, name, state):
        return Monitor.objects.create(
            user=alice, scope="stock", target_ref=ref, name=name, current_state=state
        )

    def test_severity_ordering(self, client_alice, alice):
        self._mk(alice, "A", "keep", "strengthening")
        self._mk(alice, "B", "risk", "critical")
        self._mk(alice, "C", "watch", "active")
        self._mk(alice, "D", "weak", "weakening")
        names = [m["name"] for m in _items(client_alice.get("/api/v1/monitor/monitors/"))]
        assert names.index("risk") < names.index("weak") < names.index("watch") < names.index("keep")

    def test_scope_filter(self, client_alice, alice):
        self._mk(alice, "A", "s1", "active")
        Monitor.objects.create(
            user=alice, scope="fund", target_ref="XLK", name="f1", current_state="active"
        )
        items = _items(client_alice.get("/api/v1/monitor/monitors/?scope=fund"))
        assert len(items) == 1
        assert items[0]["name"] == "f1"

    def test_has_claim_filter(self, client_alice, alice):
        from apps.monitor.models import Claim

        with_claim = self._mk(alice, "A", "wc", "active")
        self._mk(alice, "B", "nc", "active")
        Claim.objects.create(monitor=with_claim, assertion="주장")
        items = _items(client_alice.get("/api/v1/monitor/monitors/?has_claim=true"))
        assert [m["name"] for m in items] == ["wc"]

    def test_card_annotations_present(self, client_alice, alice):
        from datetime import date, timedelta

        from apps.monitor.models import Claim, MonitorIndicator, MonitorSnapshot

        m = self._mk(alice, "A", "card", "active")
        MonitorIndicator.objects.create(
            monitor=m, name="i", indicator_type="market_data"
        )
        MonitorSnapshot.objects.create(
            monitor=m, asof_date=date(2026, 7, 1), overall_score=0.42, state="active"
        )
        Claim.objects.create(
            monitor=m, assertion="a", deadline=date.today() + timedelta(days=5)
        )
        item = _items(client_alice.get("/api/v1/monitor/monitors/"))[0]
        assert item["latest_score"] == 0.42
        assert item["indicator_count"] == 1
        assert item["next_deadline"] is not None
        # display = BE 엔진 파생값(FE 재계산 제거). score 양수 → 각도 < 90
        assert item["display"] is not None
        assert item["display"]["degree"] < 90
        assert "color" in item["display"] and "phase_label" in item["display"]

    def test_display_null_without_snapshot(self, client_alice, alice):
        self._mk(alice, "Z", "no-snap", "warming_up")
        item = _items(client_alice.get("/api/v1/monitor/monitors/"))[0]
        assert item["latest_score"] is None
        assert item["display"] is None

    def test_create_response_has_null_card_fields(self, client_alice, aapl):
        # 생성 응답은 annotation 없음 → None (AttributeError 없이)
        resp = client_alice.post(
            "/api/v1/monitor/monitors/",
            {"scope": "stock", "target_ref": "AAPL", "name": "새"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["latest_score"] is None
        assert resp.data["indicator_count"] is None
