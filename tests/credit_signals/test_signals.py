"""§8.2 z-score(MAD) · §8.3 콜드스타트 · §8.4 grade 경계."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.credit_signals.models import CreditSignalState, MacroSeriesHistory
from apps.credit_signals.services.signal_service import (
    compute_derived_signal,
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


@pytest.mark.django_db
class TestComputeDerivedSignal:
    """P2-0 파생 스프레드 (compute-on-read, inner-join, red 미발화, 원장 미적재)."""

    CCC = "BAMLH0A3HYC"   # CCC_MINUS_BB 피감
    BB = "BAMLH0A1HYBB"   # CCC_MINUS_BB 감수

    def _seed(self, series_id, start, values):
        MacroSeriesHistory.objects.bulk_create([
            MacroSeriesHistory(series_id=series_id, date=start + timedelta(days=i),
                               value=Decimal(str(v)))
            for i, v in enumerate(values)
        ])

    def test_spread_arithmetic(self):
        """스프레드 = 피감 − 감수, value = 마지막 정합일 스프레드."""
        start = date(2026, 1, 1)
        self._seed(self.CCC, start, [9.0] * 60)
        self._seed(self.BB, start, [2.0] * 60)
        state = compute_derived_signal("CCC_MINUS_BB")
        assert state is not None
        assert state.value == Decimal("7.0000")  # 9 − 2
        assert state.detail["derived"] is True
        assert state.detail["minuend"] == self.CCC
        assert state.detail["subtrahend"] == self.BB
        assert state.detail["n_aligned"] == 60
        assert state.detail["n_dropped"] == 0

    def test_inner_join_drops_unaligned_dates(self):
        """한쪽에만 있는 날짜는 drop — 정합 날짜만 스프레드."""
        start = date(2026, 1, 1)
        self._seed(self.CCC, start, [9.0] * 65)  # day 0..64
        self._seed(self.BB, start, [2.0] * 60)   # day 0..59
        state = compute_derived_signal("CCC_MINUS_BB")
        assert state.detail["n_aligned"] == 60
        assert state.detail["n_dropped"] == 5
        assert state.as_of == start + timedelta(days=59)  # 마지막 정합일

    def test_cold_start_gray_z_null(self):
        """정합 관측 <60 → z=null, grade=gray."""
        start = date(2026, 1, 1)
        self._seed(self.CCC, start, [9.0] * 20)
        self._seed(self.BB, start, [2.0] * 20)
        state = compute_derived_signal("CCC_MINUS_BB")
        assert state.grade == "gray"
        assert state.z_score is None
        assert state.detail["cold_start"] is True

    def test_derived_never_red_even_when_orange_and_large(self):
        """파생키는 orange(z≥2)·절대값 큼에도 red 미발화 (red=HY_OAS 한정)."""
        start = date(2026, 1, 1)
        # 분포에 변동(MAD>0) + 마지막 급등 → z≥2 orange, 스프레드 20.0(>8).
        #   spread med=11, MAD=1, current=20 → z≈6.07
        self._seed(self.CCC, start, [10.0] * 30 + [12.0] * 29 + [20.0])
        self._seed(self.BB, start, [0.0] * 60)
        state = compute_derived_signal("CCC_MINUS_BB")
        assert state.z_score is not None and float(state.z_score) >= 2.0
        assert float(state.value) >= 8.0  # 절대값은 크지만
        assert state.grade == "orange"    # red 승격 없음 (파생키)

    def test_ledger_not_written(self):
        """★ 파생 계산은 MacroSeriesHistory(원장)에 아무 것도 쓰지 않는다."""
        start = date(2026, 1, 1)
        self._seed(self.CCC, start, [9.0] * 60)
        self._seed(self.BB, start, [2.0] * 60)
        before = MacroSeriesHistory.objects.count()
        compute_derived_signal("CCC_MINUS_BB")
        assert MacroSeriesHistory.objects.count() == before == 120  # 원장 불변
        assert not MacroSeriesHistory.objects.filter(series_id="CCC_MINUS_BB").exists()

    def test_no_source_data_returns_none(self):
        assert compute_derived_signal("CCC_MINUS_BB") is None
        assert CreditSignalState.objects.filter(signal_key="CCC_MINUS_BB").count() == 0
