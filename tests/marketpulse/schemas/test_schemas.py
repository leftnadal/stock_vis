"""Pydantic v2 schemas 검증 테스트 (PR-A2 §5.5 T21~T26)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

# ───────── News ─────────

class TestNewsEntities:
    def test_t21_default_empty_lists(self):
        from apps.market_pulse.schemas import NewsEntities
        e = NewsEntities()
        assert e.tickers == []
        assert e.sectors == []
        assert e.topics == []

    def test_round_trip(self):
        from apps.market_pulse.schemas import NewsEntities
        e = NewsEntities(tickers=['AAPL', 'MSFT'], sectors=['XLK'], topics=['Fed'])
        parsed = NewsEntities(**e.model_dump())
        assert parsed == e


# ───────── Anomaly Evidence ─────────

class TestAnomalyEvidence:
    def test_t22_r02_missing_required(self):
        from apps.market_pulse.schemas import R02Evidence
        with pytest.raises(ValidationError):
            R02Evidence(universe='SPY')  # top5_contrib 등 필수 누락

    def test_t23_r04_full_valid(self):
        from apps.market_pulse.schemas import R04Evidence
        ev = R04Evidence(
            vix_today=32.4, vix_yesterday=18.2,
            pct_change=0.78, vix_pct_1y=0.92,
            threshold_abs=30.0, threshold_pct=0.80,
        )
        assert ev.vix_today == 32.4
        assert ev.threshold_abs == 30.0

    def test_t24_r09_direction_literal(self):
        from apps.market_pulse.schemas import R09Evidence
        with pytest.raises(ValidationError):
            R09Evidence(
                sector_etf='XLK',
                z_score_temporal=2.7,
                z_score_cross=2.5,
                direction='sideways',  # invalid
            )

    def test_r12_threshold_pct_range(self):
        from apps.market_pulse.schemas import R12Evidence
        with pytest.raises(ValidationError):
            R12Evidence(dispersion_today=0.5, dispersion_pct_1y=1.5)  # >1


# ───────── Regime ─────────

class TestRegimeSchemas:
    def test_t25_coverage_ratio_range(self):
        from apps.market_pulse.schemas import IndicatorsSnapshot
        with pytest.raises(ValidationError):
            IndicatorsSnapshot(indicators=[], coverage_ratio=1.5)
        with pytest.raises(ValidationError):
            IndicatorsSnapshot(indicators=[], coverage_ratio=-0.1)

    def test_indicator_value_null(self):
        from apps.market_pulse.schemas import IndicatorValue
        iv = IndicatorValue(name='nfci', value=None, source='FRED:NFCI', fetched_at='2026-04-30T00:00:00Z')
        assert iv.value is None

    def test_matched_condition_status_literal(self):
        from apps.market_pulse.schemas import MatchedCondition
        with pytest.raises(ValidationError):
            MatchedCondition(
                indicator='vix', threshold_expr='< 30',
                actual_value=32.0, status='unknown',  # invalid
            )

    def test_pending_transition_days_non_negative(self):
        from apps.market_pulse.schemas import PendingTransition
        with pytest.raises(ValidationError):
            PendingTransition(target='CRISIS', candidate_since='2026-04-25', days_pending=-1)


# ───────── Briefing ─────────

class TestBriefingSection:
    def test_t26_section_literal(self):
        from apps.market_pulse.schemas import BriefingSection
        with pytest.raises(ValidationError):
            BriefingSection(section='other', title='t', text='x')

    def test_section_valid(self):
        from apps.market_pulse.schemas import BriefingSection
        s = BriefingSection(section='regime', title='Regime', text='Bull expansion confirmed')
        assert s.section == 'regime'

    def test_title_text_min_length(self):
        from apps.market_pulse.schemas import BriefingSection
        with pytest.raises(ValidationError):
            BriefingSection(section='flow', title='', text='ok')


# ───────── 통합 ─────────

class TestSchemasReexport:
    def test_all_imports_from_package(self):
        from apps.market_pulse.schemas import (
            BriefingSection,
            IndicatorsSnapshot,
            IndicatorValue,
            MatchedCondition,
            NewsEntities,
            PendingTransition,
            R02Evidence,
            R04Evidence,
            R09Evidence,
            R12Evidence,
        )
        # 모두 import 가능
        assert all([
            BriefingSection, IndicatorValue, IndicatorsSnapshot, MatchedCondition,
            NewsEntities, PendingTransition,
            R02Evidence, R04Evidence, R09Evidence, R12Evidence,
        ])
