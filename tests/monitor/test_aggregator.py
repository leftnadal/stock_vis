"""monitor_aggregator 이식 검증 (MON-P2-S2, premise 평탄화)."""
import pytest

from apps.monitor.services.monitor_aggregator import aggregate_monitor


@pytest.mark.django_db
class TestAggregateMonitor:
    def test_no_indicators_zero(self, monitor):
        r = aggregate_monitor(monitor, {})
        assert r["overall_score"] == 0.0
        assert r["weakest_link"] is None

    def test_weighted_average(self, make_indicator):
        a = make_indicator(name="A", weight=1.0)
        b = make_indicator(name="B", weight=3.0)
        scores = {str(a.id): 1.0, str(b.id): -1.0}
        r = aggregate_monitor(a.monitor, scores)
        # (1*1 + 3*-1) / 4 = -0.5
        assert r["overall_score"] == pytest.approx(-0.5)

    def test_none_score_treated_zero(self, make_indicator):
        a = make_indicator(name="A", weight=1.0)
        b = make_indicator(name="B", weight=1.0)
        r = aggregate_monitor(a.monitor, {str(a.id): 1.0})  # b 누락 → 0.0
        assert r["overall_score"] == pytest.approx(0.5)

    def test_weakest_link_detected(self, make_indicator):
        a = make_indicator(name="A")
        b = make_indicator(name="B")
        r = aggregate_monitor(a.monitor, {str(a.id): 0.3, str(b.id): -0.8})
        assert r["weakest_link"]["indicator_name"] == "B"

    def test_divergence_flag(self, make_indicator):
        a = make_indicator(name="A")
        b = make_indicator(name="B")
        r = aggregate_monitor(a.monitor, {str(a.id): 0.8, str(b.id): -0.8})
        assert r["divergence"] is True

    def test_paused_excluded(self, make_indicator):
        a = make_indicator(name="A", weight=1.0)
        make_indicator(name="B", weight=1.0, is_paused=True)
        r = aggregate_monitor(a.monitor, {str(a.id): 1.0})
        assert r["overall_score"] == pytest.approx(1.0)  # b 제외

    def test_category_overlap(self, make_indicator):
        from apps.monitor.models import MonitorIndicator

        a = make_indicator(name="A", indicator_type=MonitorIndicator.IndicatorType.MACRO)
        make_indicator(name="B", indicator_type=MonitorIndicator.IndicatorType.MACRO)
        r = aggregate_monitor(a.monitor, {str(a.id): 0.1})
        assert r["category_overlap"] is not None
