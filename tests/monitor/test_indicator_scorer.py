"""indicator_scorer 이식 검증 (MON-P2-S2)."""
from datetime import date, timedelta

import pytest

from apps.monitor.services.indicator_scorer import (
    check_extreme_volatility,
    score_indicator,
    score_indicator_from_model,
)


class TestScoreIndicatorPure:
    def _dates(self, n):
        base = date(2026, 1, 1)
        return [base + timedelta(days=i) for i in range(n)]

    def test_insufficient_readings(self):
        r = score_indicator([1, 2, 3], self._dates(3), "positive")
        assert r["is_sufficient"] is False
        assert r["score"] == 0.0

    def test_constant_readings_neutral_mad(self):
        vals = [5.0] * 10
        r = score_indicator(vals, self._dates(10), "positive")
        assert r["is_neutral_mad"] is True
        assert r["score"] == 0.0

    def test_rising_series_positive_score(self):
        vals = [float(i) for i in range(10)]
        r = score_indicator(vals, self._dates(10), "positive", window=10)
        assert r["score"] > 0
        assert r["is_sufficient"] is True

    def test_support_direction_negative_flips(self):
        vals = [float(i) for i in range(10)]
        pos = score_indicator(vals, self._dates(10), "positive", window=10)
        neg = score_indicator(vals, self._dates(10), "negative", window=10)
        assert neg["score"] == pytest.approx(-pos["score"])

    def test_check_extreme_volatility(self):
        class _Ind:
            id = "x"
            name = "급변 지표"

        assert check_extreme_volatility(6.0, _Ind()) is not None
        assert check_extreme_volatility(1.0, _Ind()) is None


@pytest.mark.django_db
class TestScoreFromModel:
    def test_paused_returns_neutral(self, make_indicator):
        ind = make_indicator(is_paused=True)
        r = score_indicator_from_model(ind)
        assert r["score"] == 0.0
        assert r.get("is_paused") is True

    def test_override_score_used(self, make_indicator):
        ind = make_indicator(override_score=0.7)
        r = score_indicator_from_model(ind)
        assert r["score"] == 0.7
        assert r.get("is_override") is True

    def test_reads_from_model_readings(self, make_indicator, add_readings):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)])
        r = score_indicator_from_model(ind)
        assert r["is_sufficient"] is True
        assert r["score"] > 0

    def test_rejected_readings_excluded(self, make_indicator, add_readings):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)], status="rejected")
        r = score_indicator_from_model(ind)
        assert r["is_sufficient"] is False  # 유효 판독 0
