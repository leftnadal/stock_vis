"""evaluate_monitor 파이프라인 end-to-end 검증 (MON-P2-S3)."""
import pytest

from apps.monitor.models import Monitor, MonitorSnapshot
from apps.monitor.services.pipeline import evaluate_monitor, evaluate_monitors


@pytest.mark.django_db
class TestEvaluateMonitor:
    def test_creates_snapshot_and_sets_state(self, make_indicator, add_readings):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)])
        monitor = ind.monitor

        result = evaluate_monitor(monitor)

        assert result["snapshot_id"]
        assert MonitorSnapshot.objects.filter(monitor=monitor).count() == 1
        snap = MonitorSnapshot.objects.get(monitor=monitor)
        assert snap.overall_score == result["overall_score"]
        # 신규 Monitor(days_active=0) → warming_up
        monitor.refresh_from_db()
        assert monitor.current_state == Monitor.State.WARMING_UP
        assert result["data_coverage"] == 1.0

    def test_no_indicators_zero_score(self, monitor):
        result = evaluate_monitor(monitor)
        assert result["overall_score"] == 0.0
        assert result["data_coverage"] == 0.0
        assert MonitorSnapshot.objects.filter(monitor=monitor).count() == 1

    def test_idempotent_upsert_same_day(self, make_indicator, add_readings):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)])
        monitor = ind.monitor
        evaluate_monitor(monitor)
        evaluate_monitor(monitor)  # 같은 asof → update_or_create
        assert MonitorSnapshot.objects.filter(monitor=monitor).count() == 1

    def test_paused_indicator_excluded_from_coverage(self, make_indicator, add_readings):
        good = make_indicator(name="good", window=10)
        add_readings(good, [float(i) for i in range(10)])
        make_indicator(name="paused", is_paused=True)
        result = evaluate_monitor(good.monitor)
        assert result["data_coverage"] == 1.0  # paused 제외

    def test_batch_isolation(self, monitor):
        results = evaluate_monitors(Monitor.objects.filter(id=monitor.id))
        assert len(results) == 1
