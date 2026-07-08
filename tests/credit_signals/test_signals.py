"""§8.2 z-score(MAD) · §8.3 콜드스타트 · §8.4 grade 경계."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.credit_signals.models import CreditSignalState, MacroSeriesHistory
from apps.credit_signals.services.signal_service import (
    compute_signal,
    grade_from_z,
    robust_z,
)


class TestRobustZ:
    def test_known_mad_z(self):
        """30×1.0 + 30×3.0 → median=2.0, MAD=1.0, current=3.0 → z=1/1.4826≈0.6745."""
        values = [1.0] * 30 + [3.0] * 30
        z = robust_z(values)
        assert z == pytest.approx(0.6745, abs=1e-3)

    def test_mad_floor_flat_series_returns_zero(self):
        """거의 안 움직이는 시리즈(MAD<floor) → z=0.0 (중립)."""
        values = [2.5] * 60
        assert robust_z(values) == 0.0

    def test_cold_start_below_min_returns_none(self):
        """관측 60개 미만 → None."""
        assert robust_z([1.0] * 59) is None
        assert robust_z([]) is None
        assert robust_z(None) is None


class TestGradeFromZ:
    def test_gray_below_one(self):
        assert grade_from_z(0.99, 3.0, "IG_OAS") == "gray"
        assert grade_from_z(0.0, 3.0, "IG_OAS") == "gray"

    def test_yellow_boundary_one(self):
        assert grade_from_z(1.0, 3.0, "IG_OAS") == "yellow"
        assert grade_from_z(1.99, 3.0, "IG_OAS") == "yellow"

    def test_orange_boundary_two(self):
        assert grade_from_z(2.0, 3.0, "IG_OAS") == "orange"
        assert grade_from_z(5.0, 3.0, "IG_OAS") == "orange"

    def test_none_z_is_gray(self):
        assert grade_from_z(None, 3.0, "HY_OAS") == "gray"

    def test_red_only_hy_with_crisis_bp(self):
        """red = orange(z≥2) + HY_OAS 절대값 ≥ 8.0 (800bp), HY_OAS 한정."""
        # HY, z≥2, value≥8.0 → red
        assert grade_from_z(2.0, 8.5, "HY_OAS") == "red"
        assert grade_from_z(2.5, 8.0, "HY_OAS") == "red"
        # HY, z≥2, value<8.0 → orange (절대값 미달)
        assert grade_from_z(2.0, 7.99, "HY_OAS") == "orange"
        # 비-HY는 value≥8.0이어도 red 아님
        assert grade_from_z(2.0, 9.0, "IG_OAS") == "orange"
        # HY, value≥8.0이지만 z<2 → red 아님 (orange 조건 미충족)
        assert grade_from_z(1.5, 9.0, "HY_OAS") == "yellow"


@pytest.mark.django_db
class TestComputeSignal:
    SID = "BAMLH0A0HYM2"  # HY_OAS

    def _seed(self, values):
        start = date(2026, 1, 1)
        rows = [
            MacroSeriesHistory(series_id=self.SID, date=start + timedelta(days=i),
                               value=Decimal(str(v)))
            for i, v in enumerate(values)
        ]
        MacroSeriesHistory.objects.bulk_create(rows)

    def test_cold_start_grade_gray_z_null(self):
        """원장 <60 관측 → CreditSignalState.grade=gray, z_score=null."""
        self._seed([3.5] * 20)
        state = compute_signal("HY_OAS")
        assert state is not None
        assert state.grade == "gray"
        assert state.z_score is None
        assert state.detail["cold_start"] is True
        assert state.as_of == date(2026, 1, 20)

    def test_no_data_returns_none(self):
        assert compute_signal("HY_OAS") is None
        assert CreditSignalState.objects.count() == 0

    def test_compute_upsert_is_idempotent(self):
        self._seed([1.0] * 30 + [3.0] * 30)
        s1 = compute_signal("HY_OAS")
        s2 = compute_signal("HY_OAS")
        assert s1.pk == s2.pk  # update_or_create — 단일 행
        assert CreditSignalState.objects.filter(signal_key="HY_OAS").count() == 1
        assert s2.z_score == pytest.approx(Decimal("0.6745"), abs=Decimal("0.001"))
