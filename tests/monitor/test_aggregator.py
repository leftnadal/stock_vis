"""monitor_aggregator 이식 검증 (MON-P2-S2, premise 평탄화)."""
import pytest

from apps.monitor.services.monitor_aggregator import aggregate_monitor


@pytest.mark.django_db
class TestAggregateMonitor:
    def test_no_indicators_none(self, monitor):
        # MON-P2A T2: 유효 지표 0 → overall_score=None(구 0.0에서 변경).
        r = aggregate_monitor(monitor, {})
        assert r["overall_score"] is None
        assert r["weakest_link"] is None

    def test_weighted_average(self, make_indicator):
        a = make_indicator(name="A", weight=1.0)
        b = make_indicator(name="B", weight=3.0)
        scores = {str(a.id): 1.0, str(b.id): -1.0}
        r = aggregate_monitor(a.monitor, scores)
        # (1*1 + 3*-1) / 4 = -0.5
        assert r["overall_score"] == pytest.approx(-0.5)

    def test_missing_indicator_excluded_renormalized(self, make_indicator):
        # MON-P2A T2: 누락/불충분 지표는 0.0 희석이 아니라 분모에서 제외(재정규화).
        a = make_indicator(name="A", weight=1.0)
        make_indicator(name="B", weight=1.0)
        r = aggregate_monitor(a.monitor, {str(a.id): 1.0})  # b 누락(None) → 제외
        assert r["overall_score"] == pytest.approx(1.0)  # 구 0.5(희석)에서 변경

    def test_insufficient_excluded_via_contract(self, make_indicator):
        # {score, is_sufficient} 계약: is_sufficient=False는 제외, 재정규화.
        a = make_indicator(name="A", weight=1.0)
        b = make_indicator(name="B", weight=3.0)
        scores = {
            str(a.id): {"score": 0.4, "is_sufficient": True},
            str(b.id): {"score": -0.9, "is_sufficient": False},  # 무데이터 → 제외
        }
        r = aggregate_monitor(a.monitor, scores)
        assert r["overall_score"] == pytest.approx(0.4)  # b 제외 → a만

    def test_all_insufficient_none(self, make_indicator):
        a = make_indicator(name="A", weight=1.0)
        scores = {str(a.id): {"score": 0.0, "is_sufficient": False}}
        r = aggregate_monitor(a.monitor, scores)
        assert r["overall_score"] is None

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
