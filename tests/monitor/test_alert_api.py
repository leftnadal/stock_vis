"""알림 REST + 스파크라인 + E2E 검증 (MON-P3-ALERT §7-4·§7-5)."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.monitor.models import AlertEvent, Monitor, MonitorIndicator

User = get_user_model()


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice_a", password="pw12345")


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="bob_a", password="pw12345")


@pytest.fixture
def client_alice(alice):
    c = APIClient()
    c.force_authenticate(user=alice)
    return c


@pytest.fixture
def alice_monitor(alice):
    return Monitor.objects.create(
        user=alice, scope="stock", target_ref="AAPL", name="애플", current_state="active"
    )


def _alert(monitor, to="weakening", det=True, asof=date(2026, 7, 9), suppressed=False, read=False):
    return AlertEvent.objects.create(
        monitor=monitor, from_state="active", to_state=to, asof=asof,
        score=-0.3 if det else 0.3, is_deterioration=det, is_suppressed=suppressed, read=read,
    )


@pytest.mark.django_db
class TestAlertAPI:
    def test_unauthenticated_rejected(self):
        assert APIClient().get("/api/v1/monitor/alerts/").status_code in (401, 403)

    def test_list_user_scoped(self, client_alice, alice_monitor, bob):
        _alert(alice_monitor)
        bob_m = Monitor.objects.create(user=bob, scope="stock", target_ref="MSFT", name="b")
        _alert(bob_m)
        resp = client_alice.get("/api/v1/monitor/alerts/")
        assert resp.status_code == 200
        ids = [r["monitor"] for r in resp.data["results"]] if isinstance(resp.data, dict) and "results" in resp.data else [r["monitor"] for r in resp.data]
        assert all(str(alice_monitor.id) == str(i) for i in ids)

    def test_suppressed_excluded(self, client_alice, alice_monitor):
        _alert(alice_monitor, asof=date(2026, 7, 8))
        _alert(alice_monitor, to="critical", asof=date(2026, 7, 9), suppressed=True)
        resp = client_alice.get("/api/v1/monitor/alerts/")
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        assert all(a["is_suppressed"] is False for a in data)
        assert len(data) == 1

    def test_summary_counts_unread_deterioration_only(self, client_alice, alice_monitor):
        _alert(alice_monitor, det=True, read=False, asof=date(2026, 7, 9))
        _alert(alice_monitor, to="strengthening", det=False, read=False, asof=date(2026, 7, 8))
        _alert(alice_monitor, to="critical", det=True, read=True, asof=date(2026, 7, 7))
        resp = client_alice.get("/api/v1/monitor/alerts/summary/")
        assert resp.status_code == 200
        assert resp.data["unread_deterioration_count"] == 1

    def test_mark_read(self, client_alice, alice_monitor):
        a = _alert(alice_monitor)
        resp = client_alice.post(f"/api/v1/monitor/alerts/{a.id}/read/")
        assert resp.status_code == 200
        a.refresh_from_db()
        assert a.read is True

    def test_read_all(self, client_alice, alice_monitor):
        _alert(alice_monitor, asof=date(2026, 7, 9))
        _alert(alice_monitor, to="critical", asof=date(2026, 7, 8))
        resp = client_alice.post("/api/v1/monitor/alerts/read_all/")
        assert resp.data["marked_read"] == 2
        assert AlertEvent.objects.filter(monitor=alice_monitor, read=False).count() == 0

    def test_read_other_user_alert_404(self, client_alice, bob):
        bob_m = Monitor.objects.create(user=bob, scope="stock", target_ref="MSFT", name="b")
        a = _alert(bob_m)
        resp = client_alice.post(f"/api/v1/monitor/alerts/{a.id}/read/")
        assert resp.status_code == 404  # user 스코프 격리(IDOR 방지)


# ── 스파크라인 (§7-5: 실 AAPL 시계열 렌더 데이터) ──────────────────────────


@pytest.fixture
def aapl_with_readings(alice):
    """AAPL 모니터 + 지표 + 38 거래일 readings(실 데이터 형태)."""
    from packages.shared.stocks.models import EODSignal, Stock

    stock = Stock.objects.create(symbol="AAPL", stock_name="Apple Inc.")
    m = Monitor.objects.create(
        user=alice, scope="stock", target_ref="AAPL", name="애플", current_state="active"
    )
    ind = m.indicators.create(
        name="EOD 종합 신호", indicator_type="market_data", source_key="eod_composite",
    )
    # 38 거래일치 reading (asof 역순으로 생성, 값은 상승 추세)
    base = date(2026, 7, 7)
    n = 38
    for i in range(n):
        d = base - timedelta(days=(n - 1 - i))
        ind.readings.create(
            value=round(-0.5 + i / n, 4), asof=d, validation_status="ok"
        )
    return m, ind


@pytest.mark.django_db
class TestSparklineAPI:
    def test_sparkline_returns_series_and_bands(self, client_alice, aapl_with_readings):
        m, _ = aapl_with_readings
        resp = client_alice.get(f"/api/v1/monitor/monitors/{m.id}/sparkline/")
        assert resp.status_code == 200
        data = resp.data
        assert len(data["series"]) == 30  # window 기본 30
        assert all("asof" in p and "score" in p for p in data["series"])
        assert len(data["bands"]) == 5  # 달 위상 5밴드
        assert data["bands"][0]["phase"] == "full_moon"
        # Δ5d 계산됨(표시는 회전 맵 트랙)
        assert "delta_5d" in data

    def test_sparkline_window_param(self, client_alice, aapl_with_readings):
        m, _ = aapl_with_readings
        resp = client_alice.get(f"/api/v1/monitor/monitors/{m.id}/sparkline/?window=10")
        assert len(resp.data["series"]) == 10

    def test_sparkline_user_scoped(self, aapl_with_readings, bob):
        m, _ = aapl_with_readings
        c = APIClient()
        c.force_authenticate(user=bob)
        assert c.get(f"/api/v1/monitor/monitors/{m.id}/sparkline/").status_code == 404


# ── E2E (§7-4): 전이 강제 → AlertEvent 생성 → API → 다이제스트 HTML ─────────


@pytest.mark.django_db
class TestAlertE2E:
    def test_forced_transition_end_to_end(self, client_alice, aapl_with_readings, settings):
        from apps.monitor.services.alerts import build_digest, detect_and_record_alert, render_digest_html

        m, _ = aapl_with_readings
        asof = date(2026, 7, 7)

        # 전이 강제: active → critical (악화)
        eval_res = {
            "prev_state": "active", "state": "critical", "asof_date": asof.isoformat(),
            "state_changed": True, "overall_score": -0.72,
        }
        res = detect_and_record_alert(m, eval_res)
        assert res["created"] is True and res["is_deterioration"] is True

        # API 응답 확인
        resp = client_alice.get("/api/v1/monitor/alerts/")
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        assert len(data) == 1
        assert data[0]["to_state"] == "critical"
        assert data[0]["is_deterioration"] is True

        # 배지 카운트
        summ = client_alice.get("/api/v1/monitor/alerts/summary/")
        assert summ.data["unread_deterioration_count"] == 1

        # 다이제스트 HTML 렌더
        digest = build_digest(asof)
        html = render_digest_html(digest)
        assert "critical" in (data[0]["to_state"],)  # sanity
        assert m.name in html and "악화 전이" in html
