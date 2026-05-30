"""
Thesis Control System - Full Cycle Integration Tests

Tests the complete lifecycle:
  가설 생성 -> 스코어링 -> 스냅샷 -> 마감 -> ValidityRecord + InvestorDNA
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from thesis.models import (
    IndicatorReading,
    Thesis,
    ThesisIndicator,
    ThesisPremise,
    ThesisSnapshot,
)
from thesis.models.learning import HypothesisEvent, InvestorDNA, ValidityRecord
from thesis.models.monitoring import ThesisAlert
from thesis.services.indicator_scorer import score_indicator_from_model
from thesis.services.snapshot_builder import build_snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_thesis(user, **kwargs):
    defaults = dict(
        title='테스트 가설',
        direction='bearish',
        target='KOSPI',
        target_type='index',
        thesis_type='trend',
        entry_source='free_input',
        status='active',
        current_state='warming_up',
    )
    defaults.update(kwargs)
    return Thesis.objects.create(user=user, **defaults)


def _create_indicator_with_readings(thesis, premise, n=10):
    indicator = ThesisIndicator.objects.create(
        thesis=thesis,
        premise=premise,
        name='미국 기준금리',
        indicator_type='macro',
        data_source='fred',
        support_direction='positive',
        data_params={'series_id': 'FEDFUNDS'},
    )
    for i in range(n):
        IndicatorReading.objects.create(
            indicator=indicator,
            value=4.0 + i * 0.1,
            raw_value=4.0 + i * 0.1,
            asof=timezone.now() - timedelta(days=n - i),
            validation_status='ok',
        )
    return indicator


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestThesisFullCycle:

    def test_full_cycle(self, user):
        # Step 1: Create Thesis via ORM
        thesis = _create_thesis(user)

        # Step 2: Create ThesisPremise
        premise = ThesisPremise.objects.create(
            thesis=thesis,
            content='금리 인상으로 주가 하락',
            category='macro',
            weight=1.0,
        )

        # Step 3: Create ThesisIndicator with 10 IndicatorReadings
        indicator = _create_indicator_with_readings(thesis, premise, n=10)

        # Step 4: Call build_snapshot()
        snapshot, scoring_result, prev_snapshot = build_snapshot(
            thesis, as_of_date=date.today()
        )

        assert snapshot is not None
        assert snapshot.overall_score is not None
        assert snapshot.asof_date == date.today()
        assert ThesisSnapshot.objects.filter(thesis=thesis).exists()

        # Step 5: Close thesis via API
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            f'/api/v1/thesis/{thesis.id}/close/',
            {'outcome': 'correct'},
        )

        assert response.status_code == 200

        # Step 6: Verify ValidityRecord — one per active indicator
        assert ValidityRecord.objects.filter(thesis=thesis).count() == 1

        # Step 7: Verify InvestorDNA
        dna = InvestorDNA.objects.get(user=user)
        assert dna.correct_count >= 1
        assert dna.closed_theses >= 1

        # Step 8: Verify HypothesisEvents
        events = HypothesisEvent.objects.filter(thesis=thesis)
        event_types = set(events.values_list('event_type', flat=True))
        assert 'thesis_closed' in event_types
        assert 'outcome_correct' in event_types

    def test_duplicate_close_returns_400(self, user):
        # Create a thesis that is already closed
        thesis = Thesis.objects.create(
            user=user,
            title='이미 마감됨',
            direction='bullish',
            target='SPY',
            target_type='stock',
            thesis_type='trend',
            entry_source='free_input',
            status='closed',
            outcome='correct',
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            f'/api/v1/thesis/{thesis.id}/close/',
            {'outcome': 'correct'},
        )

        assert response.status_code == 400

    def test_eod_pipeline_tasks_run_without_error(self, user):
        from thesis.tasks.eod_pipeline import (
            calculate_scores,
            create_snapshots_and_alerts,
        )

        # Create active thesis with premise and indicator readings
        thesis = _create_thesis(user)
        premise = ThesisPremise.objects.create(
            thesis=thesis,
            content='금리 인상으로 주가 하락',
            category='macro',
            weight=1.0,
        )
        _create_indicator_with_readings(thesis, premise, n=10)

        # Task 2: calculate_scores — runs score computation on active theses
        result2 = calculate_scores()
        assert result2['ind_count'] >= 1

        # Task 3: create_snapshots_and_alerts — builds snapshots + alerts
        result3 = create_snapshots_and_alerts()
        assert result3['snap_count'] >= 1
        assert ThesisSnapshot.objects.filter(thesis=thesis).exists()
