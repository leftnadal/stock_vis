"""arrow_calculator + state_machine 이식 검증 (MON-P2-S2)."""
import pytest

from apps.monitor.services.arrow_calculator import (
    calculate_indicator_arrow,
    degree_to_color,
    degree_to_label,
    score_to_degree,
)
from apps.monitor.services.state_machine import determine_state, score_to_phase


class TestArrowPure:
    def test_score_to_degree(self):
        assert score_to_degree(1.0) == 0
        assert score_to_degree(0.0) == 90
        assert score_to_degree(-1.0) == 180

    def test_degree_to_color_bands(self):
        assert degree_to_color(10) == "#2563EB"  # 강한 지지
        assert degree_to_color(90) == "#9CA3AF"  # 중립
        assert degree_to_color(180) == "#DC2626"  # 강한 반박

    def test_degree_to_label(self):
        assert degree_to_label(10) == "강하게 지지"
        assert degree_to_label(90) == "중립"


@pytest.mark.django_db
class TestArrowFromModel:
    def test_paused_label(self, make_indicator):
        ind = make_indicator(is_paused=True)
        r = calculate_indicator_arrow(ind)
        assert r["label"] == "일시정지됨"

    def test_insufficient_label(self, make_indicator):
        ind = make_indicator()  # 판독 없음
        r = calculate_indicator_arrow(ind)
        assert r["label"] == "데이터 부족"


class TestScoreToPhase:
    def test_phases(self):
        assert score_to_phase(0.8)["phase"] == "full_moon"
        assert score_to_phase(0.4)["phase"] == "waxing"
        assert score_to_phase(0.0)["phase"] == "half_moon"
        assert score_to_phase(-0.4)["phase"] == "waning"
        assert score_to_phase(-0.8)["phase"] == "new_moon"


@pytest.mark.django_db
class TestDetermineState:
    def test_archived_no_change(self, monitor):
        monitor.status = "archived"
        monitor.current_state = "active"
        r = determine_state(monitor, 0.5, 0.4, 1.0, 100, [0.4, 0.5])
        assert r["state"] == "active"
        assert r["state_changed"] is False

    def test_low_coverage_holds(self, monitor):
        monitor.current_state = "active"
        r = determine_state(monitor, 0.5, 0.4, 0.3, 100, [0.4, 0.5, 0.5])
        assert r["state_changed"] is False

    def test_warming_up(self, monitor):
        r = determine_state(monitor, 0.5, None, 1.0, 2, [])
        assert r["state"] == "warming_up"

    def test_strengthening_trend(self, monitor):
        monitor.current_state = "active"
        r = determine_state(monitor, 0.6, 0.5, 1.0, 30, [0.1, 0.3, 0.5, 0.6])
        assert r["state"] == "strengthening"

    def test_needs_review_after_90d(self, monitor):
        monitor.target_date_end = None
        r = determine_state(monitor, 0.2, 0.2, 1.0, 95, [0.2, 0.2, 0.2])
        assert r["state"] == "needs_review"
        assert r["reminder_needed"] is True
