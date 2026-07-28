"""MP2-ANALOG Slice B — 매칭 엔진 결정론 회귀 (fixture 손계산).

계약: 가족가중 거리·②C 이웃선정(radius·K·10일분리·경보)·①C 팬(지평별 N·n_eff 확대)·선도수익 우변절단.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.market_pulse.regime import analog

pytestmark = [pytest.mark.unit]


class TestWeights:
    def test_family_weights_sum_to_effective_axes(self):
        w = analog.component_weights()
        assert w["vix"] == pytest.approx(1 / 3)  # FAM1(3)
        assert w["nfci"] == pytest.approx(1 / 9)  # FAM2(9)
        assert w["return_1d_pct"] == 1.0  # 단독
        assert sum(w.values()) == pytest.approx(4.0)  # 유효 축 4


class TestDistance:
    def test_weighted_distance_sq_hand(self):
        w = analog.component_weights()
        z_a = {"vix": 1.0, "nfci": 0.0}
        z_b = {"vix": 0.0, "nfci": 3.0}
        # (1/3)(1)² + (1/9)(3)² = 0.3333 + 1.0 = 1.3333
        assert analog.distance_sq(z_a, z_b, w) == pytest.approx(1.0 / 3 + 1.0)

    def test_no_common_returns_none(self):
        w = analog.component_weights()
        assert analog.distance_sq({"vix": 1.0}, {"nfci": 1.0}, w) is None


class TestSelectNeighbors:
    def _pop(self, specs):
        # specs = [(date, vix_z)] — 단일 성분으로 거리 통제
        return [(d, {"vix": z}) for d, z in specs]

    def test_radius_and_k_cap(self):
        w = {"vix": 1.0}
        today = {"vix": 0.0}
        # 거리 = |vix_z| (w=1). radius 0.60 → z 0.6 이하만
        pop = self._pop([
            (date(2024, 1, 3), 0.1),   # dist 0.1
            (date(2024, 3, 3), 0.5),   # dist 0.5
            (date(2024, 6, 3), 0.9),   # dist 0.9 > radius
        ])
        picked, nearest = analog.select_neighbors(today, pop, w)
        assert nearest == pytest.approx(0.1)
        dists = [p["dist"] for p in picked]
        assert dists == [0.1, 0.5]  # 0.9 배제(radius)

    def test_min_separation_dedups_episode(self):
        w = {"vix": 1.0}
        today = {"vix": 0.0}
        # 같은 주 3일(거리 0.1/0.2/0.3) → 최근접만, 10영업일 분리 위반 배제
        pop = self._pop([
            (date(2024, 1, 3), 0.1),
            (date(2024, 1, 4), 0.2),
            (date(2024, 1, 5), 0.3),
            (date(2024, 3, 1), 0.4),  # 분리 OK
        ])
        picked, _ = analog.select_neighbors(today, pop, w)
        assert [p["date"] for p in picked] == [date(2024, 1, 3), date(2024, 3, 1)]

    def test_alert_when_nearest_beyond_tau(self):
        assert analog.is_alert(0.9) is True
        assert analog.is_alert(0.5) is False
        assert analog.is_alert(None) is True


class TestForwardReturns:
    def test_positional_and_right_censor(self):
        dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(10)]
        idx = {d: i for i, d in enumerate(dates)}
        closes = [100.0 + i for i in range(10)]  # 100..109
        # ref=위치0, +5 → close[5]/close[0]-1 = 105/100-1 = 0.05
        r = analog.forward_returns(dates[0], idx, closes, horizons=(5, 20))
        assert r[5] == pytest.approx(0.05)
        assert r[20] is None  # 우변 절단(위치 0+20 >= 10)

    def test_missing_ref_date(self):
        r = analog.forward_returns(date(2099, 1, 1), {}, [], horizons=(5,))
        assert r[5] is None


class TestBuildFan:
    def test_per_horizon_n_and_median(self):
        nb = [
            {"date": date(2024, 1, 3), "fwd": {5: 0.01, 20: 0.02}},
            {"date": date(2024, 6, 3), "fwd": {5: 0.03, 20: None}},  # 20d 미실현
            {"date": date(2024, 11, 3), "fwd": {5: 0.05, 20: 0.06}},
        ]
        fan = analog.build_fan(nb, horizons=(5, 20), k=3)
        f5 = next(f for f in fan if f["horizon"] == 5)
        f20 = next(f for f in fan if f["horizon"] == 20)
        assert f5["n"] == 3 and f5["median"] == pytest.approx(0.03)
        assert f20["n"] == 2  # 정직 N(하나 미실현)

    def test_clustering_widens_band(self):
        # 같은 에피소드(60일 내) 3 이웃 → n_eff=1 → 밴드 √(3/1) 확대
        clustered = [
            {"date": date(2024, 1, 1), "fwd": {5: 0.0}},
            {"date": date(2024, 1, 15), "fwd": {5: 0.02}},
            {"date": date(2024, 2, 1), "fwd": {5: 0.04}},
        ]
        fan_c = analog.build_fan(clustered, horizons=(5,), k=3)[0]
        assert fan_c["n_eff"] == 1
        # 분산 이웃(각 6개월 이상) → n_eff=3 → 확대 없음
        spread = [
            {"date": date(2023, 1, 1), "fwd": {5: 0.0}},
            {"date": date(2023, 9, 1), "fwd": {5: 0.02}},
            {"date": date(2024, 6, 1), "fwd": {5: 0.04}},
        ]
        fan_s = analog.build_fan(spread, horizons=(5,), k=3)[0]
        assert fan_s["n_eff"] == 3
        # 같은 값 분포라도 clustered 밴드 폭 ≥ spread 밴드 폭
        width_c = fan_c["hi"] - fan_c["lo"]
        width_s = fan_s["hi"] - fan_s["lo"]
        assert width_c > width_s
