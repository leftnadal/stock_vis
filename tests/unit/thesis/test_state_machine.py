"""
Thesis State Machine 테스트

thesis/services/thesis_state_machine.py의 determine_state() 함수를 검증합니다.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from thesis.models import Thesis
from thesis.services.thesis_state_machine import determine_state


def make_thesis(user, **kwargs):
    """Thesis 인스턴스 생성 헬퍼."""
    defaults = dict(
        user=user,
        title='Test Thesis',
        direction='bullish',
        target='AAPL',
        target_type='stock',
        thesis_type='trend',
        entry_source='free_input',
        status='active',
        current_state='active',
        target_date_end=None,
    )
    defaults.update(kwargs)
    return Thesis.objects.create(**defaults)


class TestDetermineState:

    @pytest.mark.django_db
    def test_warming_up_under_5_days(self, user):
        """days_active=3이면 'warming_up' 반환."""
        thesis = make_thesis(user)

        result = determine_state(
            thesis=thesis,
            overall_score=0.3,
            prev_score=None,
            data_coverage=0.9,
            days_active=3,
            score_history=[0.3],
        )

        assert result['state'] == 'warming_up'
        assert result['state_changed'] is True

    @pytest.mark.django_db
    def test_critical_on_daily_change_03(self, user):
        """마지막 두 스냅샷 간 score 변화가 0.4 (>0.3)이면 'critical' 반환."""
        thesis = make_thesis(user)

        # history[-1] - history[-2] = 0.5 - 0.1 = 0.4, which is > DAILY_CHANGE_CRITICAL(0.3)
        score_history = [0.1, 0.1, 0.1, 0.1, 0.5]

        result = determine_state(
            thesis=thesis,
            overall_score=0.5,
            prev_score=0.1,
            data_coverage=1.0,
            days_active=20,
            score_history=score_history,
        )

        assert result['state'] == 'critical'
        assert result['state_changed'] is True

    @pytest.mark.django_db
    def test_strengthening_on_5day_trend(self, user):
        """5일 trend = history[-1] - history[0] = 0.3 - 0.1 = 0.2 > 0.15이면 'strengthening' 반환."""
        thesis = make_thesis(user)

        # trend = 0.3 - 0.1 = 0.2, which is > TREND_THRESHOLD(0.15)
        score_history = [0.1, 0.15, 0.2, 0.25, 0.3]

        result = determine_state(
            thesis=thesis,
            overall_score=0.3,
            prev_score=0.25,
            data_coverage=1.0,
            days_active=20,
            score_history=score_history,
        )

        assert result['state'] == 'strengthening'
        assert result['state_changed'] is True

    @pytest.mark.django_db
    def test_needs_review_at_90_days(self, user):
        """days_active=90이고 target_date_end가 없으면 'needs_review' 반환."""
        thesis = make_thesis(user, target_date_end=None)

        result = determine_state(
            thesis=thesis,
            overall_score=0.1,
            prev_score=0.1,
            data_coverage=1.0,
            days_active=90,
            score_history=[0.08, 0.09, 0.1, 0.09, 0.1],
        )

        assert result['state'] == 'needs_review'
        assert result['state_changed'] is True
        assert result['reminder_needed'] is True
