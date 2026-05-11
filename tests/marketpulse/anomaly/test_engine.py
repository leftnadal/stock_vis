"""Tests for marketpulse.anomaly.engine."""
from __future__ import annotations

import pytest

from marketpulse.anomaly import engine as eng
from marketpulse.models.anomaly import AnomalySignalLog


def _ctx(**overrides):
    base = dict(top10_weight=0.3, vix_change_pct=5.0,
                max_abs_sector_z=1.5, cross_dispersion=0.5)
    base.update(overrides)
    return eng.AnomalyContext(**base)


class TestEvaluate:
    def test_no_rules_default(self):
        assert eng.evaluate(_ctx()) == []

    def test_r02_concentration(self):
        fired = eng.evaluate(_ctx(top10_weight=0.45))
        assert any(f.rule_id == 'R02' for f in fired)

    def test_r04_vix_spike(self):
        fired = eng.evaluate(_ctx(vix_change_pct=22.0))
        assert any(f.rule_id == 'R04' for f in fired)

    def test_r09_sector_z(self):
        fired = eng.evaluate(_ctx(max_abs_sector_z=3.5))
        assert any(f.rule_id == 'R09' for f in fired)

    def test_r12_dispersion(self):
        fired = eng.evaluate(_ctx(cross_dispersion=2.0))
        assert any(f.rule_id == 'R12' for f in fired)

    def test_multiple(self):
        fired = eng.evaluate(_ctx(top10_weight=0.5, vix_change_pct=25.0))
        ids = {f.rule_id for f in fired}
        assert ids >= {'R02', 'R04'}

    def test_missing_input_skips(self):
        fired = eng.evaluate(_ctx(top10_weight=None, vix_change_pct=None,
                                   max_abs_sector_z=None, cross_dispersion=None))
        assert fired == []


class TestSelectMode:
    def test_calm(self):
        assert eng.select_mode([]) == AnomalySignalLog.Mode.CALM

    def test_hybrid(self):
        f = eng.FiredRule('R02', 'x', {}, 0.5)
        assert eng.select_mode([f]) == AnomalySignalLog.Mode.HYBRID

    def test_anomaly(self):
        fs = [eng.FiredRule('R02', 'x', {}, 0.5),
              eng.FiredRule('R04', 'y', {}, 25)]
        assert eng.select_mode(fs) == AnomalySignalLog.Mode.ANOMALY
