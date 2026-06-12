"""Tests for marketpulse.regime.classifier."""
from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta

import pytest

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime import classifier as cls
from apps.market_pulse.regime.inputs import RegimeInputs


def _bull():
    return RegimeInputs(
        return_1d_pct=0.5, vol_20d_pct=0.8, drawdown_pct=-2.0,
        nfci=-0.4, nfci_credit=-0.2, nfci_leverage=-0.3, nfci_risk=-0.5,
        hy_oas_pct=2.2, hy_ccc_oas_pct=5.0,
        t10y2y_pct=0.6, t10y3m_pct=1.2,
        vix=14.0, vix3m=15.0, move=80.0,
    )


class TestClassifyInputs:
    def test_bull_default(self):
        regime, fired = cls.classify_inputs(_bull())
        assert regime == RegimeSnapshot.Regime.BULL_EXPANSION
        assert fired == []

    def test_late_bull_vix(self):
        i = _bull(); i.vix = 22.0
        regime, _ = cls.classify_inputs(i)
        assert regime == RegimeSnapshot.Regime.LATE_BULL

    def test_transition_nfci(self):
        i = _bull(); i.nfci = 0.2
        regime, _ = cls.classify_inputs(i)
        assert regime == RegimeSnapshot.Regime.TRANSITION

    def test_bear_combined(self):
        i = _bull(); i.hy_oas_pct = 5.5; i.vix = 32.0
        regime, _ = cls.classify_inputs(i)
        assert regime == RegimeSnapshot.Regime.BEAR_CONTRACTION

    def test_crisis_vix_extreme(self):
        i = _bull(); i.vix = 45.0
        regime, _ = cls.classify_inputs(i)
        assert regime == RegimeSnapshot.Regime.CRISIS

    def test_crisis_priority_over_bear(self):
        i = _bull(); i.hy_oas_pct = 5.5; i.vix = 32.0; i.move = 160.0
        regime, _ = cls.classify_inputs(i)
        assert regime == RegimeSnapshot.Regime.CRISIS

    def test_yield_inversion_transition(self):
        i = _bull(); i.t10y2y_pct = -0.1
        regime, _ = cls.classify_inputs(i)
        assert regime == RegimeSnapshot.Regime.TRANSITION

    def test_drawdown_crisis(self):
        i = _bull(); i.drawdown_pct = -25.0
        regime, _ = cls.classify_inputs(i)
        assert regime == RegimeSnapshot.Regime.CRISIS

    def test_missing_inputs_default(self):
        regime, fired = cls.classify_inputs(RegimeInputs())
        assert regime == RegimeSnapshot.Regime.BULL_EXPANSION
        assert fired == []

    def test_stress_input_none_preserves_output(self):
        # Phase 1.5 인터페이스 스텁: stress_input 미지정 = 기존 동작 회귀
        baseline_regime, baseline_fired = cls.classify_inputs(_bull())
        hooked_regime, hooked_fired = cls.classify_inputs(_bull(), stress_input=None)
        assert hooked_regime == baseline_regime
        assert hooked_fired == baseline_fired

    def test_stress_input_dummy_accepted_without_behavior_change(self):
        # 비-None stress_input은 받아들여지되 분류 결과에 영향 없음 (행위보존)
        baseline_regime, baseline_fired = cls.classify_inputs(_bull())
        dummy = {"placeholder": "phase-1.5-payload"}
        hooked_regime, hooked_fired = cls.classify_inputs(_bull(), stress_input=dummy)
        assert hooked_regime == baseline_regime
        assert hooked_fired == baseline_fired


@pytest.mark.django_db
class TestHysteresis:
    def _snap(self, *, regime, prev_candidate='', streak=1, days_ago=1):
        return RegimeSnapshot.objects.create(
            date=date_cls(2026, 4, 27) - timedelta(days=days_ago),
            snapshot_time=date_cls(2026, 4, 27) - timedelta(days=days_ago),
            regime=regime, previous_regime=prev_candidate,
            hysteresis_streak=streak,
        )

    def test_no_previous(self):
        d = cls.apply_hysteresis(
            candidate_regime=RegimeSnapshot.Regime.BULL_EXPANSION,
            previous_snapshot=None,
        )
        assert d.final_regime == RegimeSnapshot.Regime.BULL_EXPANSION
        assert d.streak == 1
        assert d.transitioned is False

    def test_same_regime_increments(self):
        prev = self._snap(regime=RegimeSnapshot.Regime.BULL_EXPANSION, streak=3)
        d = cls.apply_hysteresis(
            candidate_regime=RegimeSnapshot.Regime.BULL_EXPANSION,
            previous_snapshot=prev,
        )
        assert d.streak == 4

    def test_first_different_holds(self):
        prev = self._snap(regime=RegimeSnapshot.Regime.BULL_EXPANSION)
        d = cls.apply_hysteresis(
            candidate_regime=RegimeSnapshot.Regime.LATE_BULL,
            previous_snapshot=prev,
        )
        assert d.final_regime == RegimeSnapshot.Regime.BULL_EXPANSION
        assert d.transitioned is False

    def test_two_consecutive_transition(self):
        prev = self._snap(
            regime=RegimeSnapshot.Regime.BULL_EXPANSION,
            prev_candidate=RegimeSnapshot.Regime.LATE_BULL,
        )
        d = cls.apply_hysteresis(
            candidate_regime=RegimeSnapshot.Regime.LATE_BULL,
            previous_snapshot=prev,
        )
        assert d.final_regime == RegimeSnapshot.Regime.LATE_BULL
        assert d.transitioned is True

    def test_crisis_immediate(self):
        prev = self._snap(regime=RegimeSnapshot.Regime.BULL_EXPANSION)
        d = cls.apply_hysteresis(
            candidate_regime=RegimeSnapshot.Regime.CRISIS,
            previous_snapshot=prev,
        )
        assert d.final_regime == RegimeSnapshot.Regime.CRISIS
        assert d.transitioned is True
