"""
Alert Engine 테스트

thesis/services/alert_engine.py의 주요 함수를 검증합니다:
- create_alert_if_needed(): throttling(cooldown) 로직
- check_and_create_alerts(): state_change 알림의 push 여부
"""

import pytest

from thesis.models import Thesis, ThesisAlert
from thesis.services.alert_engine import create_alert_if_needed, check_and_create_alerts


def make_thesis(user, **kwargs):
    """Thesis 인스턴스 생성 헬퍼."""
    defaults = dict(
        user=user,
        title='Alert Engine Test Thesis',
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


def make_base_scoring_result(state='active', state_changed=False):
    """alert_engine이 기대하는 scoring_result dict 생성 헬퍼."""
    return {
        'indicator_scores': {},
        'indicator_names': {},
        'indicator_degrees': {},
        'extreme_vol_indicators': [],
        'premise_scores': {},
        'overall_score': 0.0,
        'weakest_link': None,
        'divergence_count': 0,
        'thesis_bias_warning': None,
        'state_result': {
            'state': state,
            'state_changed': state_changed,
            'reminder_needed': False,
        },
        'data_coverage': 1.0,
    }


class TestAlertEngine:

    @pytest.mark.django_db
    def test_alert_throttling_blocks_duplicate(self, user):
        """동일한 alert_type과 target_id로 첫 번째 알림은 생성되지만,
        cooldown 내 두 번째 호출은 None을 반환해야 합니다."""
        thesis = make_thesis(user)

        # 첫 번째 호출 - 알림 생성 성공
        first_alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='sharp_move',
            title='Sharp Move Alert',
            message='Score changed sharply.',
            target_id='indicator-abc-123',
        )

        assert first_alert is not None
        assert isinstance(first_alert, ThesisAlert)

        # 두 번째 호출 - cooldown(24h) 내 동일 type+target_id → 차단
        second_alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='sharp_move',
            title='Sharp Move Alert (duplicate)',
            message='Score changed sharply again.',
            target_id='indicator-abc-123',
        )

        assert second_alert is None
        # DB에는 알림이 하나만 있어야 함
        assert ThesisAlert.objects.filter(thesis=thesis, alert_type='sharp_move').count() == 1

    @pytest.mark.django_db
    def test_alert_state_change_only_push_for_critical(self, user):
        """state_change 알림은 'strengthening' 상태에서는 is_pushed=False,
        'critical' 상태에서는 is_pushed=True여야 합니다 (push_override 적용).

        PUSH_WORTHY_STATES = {'critical', 'expired', 'needs_review'}
        """
        thesis_strengthening = make_thesis(
            user,
            title='Strengthening Thesis',
            current_state='active',
        )
        thesis_critical = make_thesis(
            user,
            title='Critical Thesis',
            current_state='active',
        )

        # 1. 'strengthening' 상태 변경 → is_pushed=False 기대
        scoring_result_strengthening = make_base_scoring_result(
            state='strengthening',
            state_changed=True,
        )
        alerts_strengthening = check_and_create_alerts(
            thesis=thesis_strengthening,
            scoring_result=scoring_result_strengthening,
            prev_snapshot=None,
        )

        state_change_alerts_strengthening = [
            a for a in alerts_strengthening if a.alert_type == 'state_change'
        ]
        assert len(state_change_alerts_strengthening) == 1
        assert state_change_alerts_strengthening[0].is_pushed is False

        # 2. 'critical' 상태 변경 → is_pushed=True 기대 (push_override)
        scoring_result_critical = make_base_scoring_result(
            state='critical',
            state_changed=True,
        )
        alerts_critical = check_and_create_alerts(
            thesis=thesis_critical,
            scoring_result=scoring_result_critical,
            prev_snapshot=None,
        )

        state_change_alerts_critical = [
            a for a in alerts_critical if a.alert_type == 'state_change'
        ]
        assert len(state_change_alerts_critical) == 1
        assert state_change_alerts_critical[0].is_pushed is True
