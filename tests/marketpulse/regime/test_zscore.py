"""MP2-TREND S4 — zscore baseline/z/downsample 순수 함수 회귀.

계약: 표본 std(n−1), 결측 제외, σ=0·n<30 가드, z null 전파, 다운샘플 경계.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta

import pytest

from apps.market_pulse.regime import zscore

pytestmark = [pytest.mark.unit]


class TestComputeBaseline:
    def test_sample_std_and_mean(self):
        rows = [{"vix": float(v)} for v in range(1, 41)]  # n=40
        base = zscore.compute_baseline(rows, ["vix"])["vix"]
        vals = list(range(1, 41))
        assert base["insufficient"] is False
        assert base["n"] == 40
        assert base["mean"] == pytest.approx(statistics.fmean(vals))
        assert base["std"] == pytest.approx(statistics.stdev(vals))  # n−1

    def test_missing_excluded_from_n(self):
        rows = [{"vix": 1.0}, {"vix": None}, {"other": 5.0}, {}] + [
            {"vix": float(v)} for v in range(50)
        ]
        base = zscore.compute_baseline(rows, ["vix"])["vix"]
        assert base["n"] == 51  # None/결측 3행 제외

    def test_n_below_min_insufficient(self):
        rows = [{"vix": float(v)} for v in range(10)]  # n=10 < 30
        base = zscore.compute_baseline(rows, ["vix"])["vix"]
        assert base["insufficient"] is True
        assert base["mean"] is None and base["std"] is None
        assert base["n"] == 10

    def test_zero_std_insufficient(self):
        rows = [{"vix": 20.0} for _ in range(40)]  # σ=0
        base = zscore.compute_baseline(rows, ["vix"])["vix"]
        assert base["insufficient"] is True
        assert base["std"] == 0.0


class TestZOf:
    def test_basic(self):
        base = {"mean": 10.0, "std": 2.0, "n": 40, "insufficient": False}
        assert zscore.z_of(14.0, base) == pytest.approx(2.0)

    def test_null_value(self):
        base = {"mean": 10.0, "std": 2.0, "n": 40, "insufficient": False}
        assert zscore.z_of(None, base) is None

    def test_insufficient_base(self):
        assert zscore.z_of(14.0, {"insufficient": True, "mean": None, "std": None}) is None
        assert zscore.z_of(14.0, None) is None


class TestDownsample:
    def _rows(self, n):
        d0 = date(2023, 1, 2)  # 월요일
        out, d = [], d0
        while len(out) < n:
            if d.weekday() < 5:
                out.append((d, {"vix": 1.0}))
            d += timedelta(days=1)
        return out

    def test_below_recent_unchanged(self):
        rows = self._rows(50)
        assert zscore.downsample(rows, recent_daily=90) == rows

    def test_recent_daily_preserved_older_weekly(self):
        rows = self._rows(200)
        ds = zscore.downsample(rows, recent_daily=90)
        # 최근 90행은 그대로 꼬리에 유지
        assert ds[-90:] == rows[-90:]
        # 그 이전 구간은 주당 1점(ISO 주 유일)
        older = ds[:-90]
        weeks = [d.isocalendar()[:2] for d, _ in older]
        assert len(weeks) == len(set(weeks))  # 주별 유일
        # 축소됐음
        assert len(ds) < len(rows)
