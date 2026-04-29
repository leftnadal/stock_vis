"""Tests for thesis.tasks.summary.generate_thesis_summaries (audit P0 #15)."""
from __future__ import annotations

from datetime import date as date_cls
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from thesis.models import Thesis, ThesisSnapshot
from thesis.tasks.summary import generate_thesis_summaries


User = get_user_model()


@pytest.fixture
def thesis_with_snapshot(db):
    user = User.objects.create_user(username='ts', email='t@e.com', password='pw')
    thesis = Thesis.objects.create(
        user=user, title='Apple Q4 outlook',
        direction='up', target='AAPL', target_type='stock',
        thesis_type='direction', status='active',
    )
    snap = ThesisSnapshot.objects.create(
        thesis=thesis,
        asof_date=date_cls(2026, 4, 29),
        data_coverage=0.85,
        overall_score=0.62,
        state='watching',
        ai_summary='',
        notable_changes=[
            {'label': 'iPhone sales', 'delta': 0.12},
        ],
    )
    return thesis, snap


@pytest.mark.django_db
class TestGenerateThesisSummaries:
    def test_fills_empty_summary(self, thesis_with_snapshot):
        _, snap = thesis_with_snapshot
        with patch(
            'thesis.tasks.summary._generate_via_gemini',
            return_value='Apple은 watching 상태이며 iPhone sales 모멘텀이 약하게 양호.',
        ):
            result = generate_thesis_summaries.apply(
                kwargs={'target_date': '2026-04-29'},
            ).get()

        assert result['updated'] == 1
        assert result['skipped'] == 0
        assert result['failed'] == 0
        snap.refresh_from_db()
        assert 'Apple' in snap.ai_summary

    def test_skips_existing(self, thesis_with_snapshot):
        _, snap = thesis_with_snapshot
        snap.ai_summary = '기존 요약'
        snap.save(update_fields=['ai_summary'])

        called = {'n': 0}

        def fake_gen(prompt):
            called['n'] += 1
            return 'should not run'

        with patch('thesis.tasks.summary._generate_via_gemini', side_effect=fake_gen):
            result = generate_thesis_summaries.apply(
                kwargs={'target_date': '2026-04-29'},
            ).get()

        assert result['skipped'] == 1
        assert result['updated'] == 0
        assert called['n'] == 0

    def test_force_regenerates(self, thesis_with_snapshot):
        _, snap = thesis_with_snapshot
        snap.ai_summary = '기존 요약'
        snap.save(update_fields=['ai_summary'])

        with patch(
            'thesis.tasks.summary._generate_via_gemini',
            return_value='새 요약',
        ):
            result = generate_thesis_summaries.apply(
                kwargs={'target_date': '2026-04-29', 'force': True},
            ).get()

        snap.refresh_from_db()
        assert snap.ai_summary == '새 요약'
        assert result['updated'] == 1

    def test_failed_generation_counts_as_failed(self, thesis_with_snapshot):
        _, snap = thesis_with_snapshot
        with patch('thesis.tasks.summary._generate_via_gemini', return_value=''):
            result = generate_thesis_summaries.apply(
                kwargs={'target_date': '2026-04-29'},
            ).get()
        assert result['failed'] == 1
        snap.refresh_from_db()
        assert snap.ai_summary == ''

    def test_no_snapshots_returns_zero(self, db):
        result = generate_thesis_summaries.apply(
            kwargs={'target_date': '2026-04-29'},
        ).get()
        assert result == {
            'updated': 0, 'skipped': 0, 'failed': 0,
            'date': '2026-04-29', 'force': False,
        }
