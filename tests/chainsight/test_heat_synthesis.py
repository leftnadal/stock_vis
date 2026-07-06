"""
Heat 합성기 테스트 (TH-3, 설계서 §3 + §2).

검증:
- 가중치 합 1.00 (상수 모듈)
- 시그모이드 + 밴드 임계 (70/40)
- 8성분 정상 합성 (z=0 전건 → 50/warning)
- 결측 비례 재분배 (1~2 결측은 산출, 점수 정규화)
- 결측 ≥3 → not_computed
- evidence |z| 상위 2
"""

import pytest

from apps.chain_sight.services import heat_synthesis as hs


def _comp(z, missing=None):
    return {"z": z, "raw": None, "missing_reason": missing}


def _all(z):
    return {k: _comp(z) for k in hs.HEAT_WEIGHTS}


class TestWeights:
    def test_sum_is_one(self):
        assert round(sum(hs.HEAT_WEIGHTS.values()), 6) == 1.0

    def test_eight_components(self):
        assert set(hs.HEAT_WEIGHTS) == {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"}


class TestSigmoidBand:
    def test_sigmoid_zero(self):
        assert hs.sigmoid(0) == 0.5

    def test_sigmoid_extremes(self):
        assert hs.sigmoid(20) == pytest.approx(1.0, abs=1e-6)
        assert hs.sigmoid(-20) == pytest.approx(0.0, abs=1e-6)

    def test_band_thresholds(self):
        assert hs.heat_band(70) == "overheated"
        assert hs.heat_band(69) == "warning"
        assert hs.heat_band(40) == "warning"
        assert hs.heat_band(39) == "cool"


class TestSynthesis:
    def test_all_zero_is_50_warning(self):
        r = hs.synthesize_heat(_all(0.0))
        assert r["score"] == 50 and r["status"] == "warning"
        assert r["missing_count"] == 0

    def test_all_high_overheated(self):
        r = hs.synthesize_heat(_all(10.0))
        assert r["score"] == 100 and r["status"] == "overheated"

    def test_all_low_cool(self):
        r = hs.synthesize_heat(_all(-10.0))
        assert r["score"] == 0 and r["status"] == "cool"

    def test_s_annotated(self):
        r = hs.synthesize_heat(_all(0.0))
        assert r["components"]["C1"]["s"] == 0.5


class TestMissingRedistribution:
    def test_one_missing_still_computed_normalized(self):
        comps = _all(0.0)
        comps["C8"] = _comp(None, missing="no_estimate")
        r = hs.synthesize_heat(comps)
        # 결측 1: 나머지 재분배 → 전건 0.5 이므로 점수 불변 50
        assert r["missing_count"] == 1
        assert r["score"] == 50 and r["status"] == "warning"

    def test_two_missing_ok(self):
        comps = _all(0.0)
        comps["C7"] = _comp(None, missing="x")
        comps["C8"] = _comp(None, missing="y")
        r = hs.synthesize_heat(comps)
        assert r["missing_count"] == 2 and r["score"] == 50

    def test_three_missing_not_computed(self):
        comps = _all(0.0)
        for k in ("C6", "C7", "C8"):
            comps[k] = _comp(None, missing="x")
        r = hs.synthesize_heat(comps)
        assert r["status"] == "not_computed" and r["score"] is None
        assert r["missing_count"] == 3

    def test_missing_reason_excludes_even_with_z(self):
        """missing_reason 있으면 z 있어도 제외."""
        comps = _all(0.0)
        comps["C8"] = {"z": 5.0, "missing_reason": "stale"}
        r = hs.synthesize_heat(comps)
        assert r["missing_count"] == 1


class TestEvidence:
    def test_top2_by_abs_z(self):
        comps = _all(0.1)
        comps["C1"] = _comp(2.0)
        comps["C2"] = _comp(-3.0)
        r = hs.synthesize_heat(comps)
        keys = [e["component"] for e in r["evidence"]]
        assert keys == ["C2", "C1"]  # |−3| > |2| > 나머지
