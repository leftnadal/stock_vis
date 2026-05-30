"""
Snapshot Builder 테스트

thesis/services/snapshot_builder.py의 build_snapshot() 함수를 검증합니다.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from thesis.models import (
    IndicatorReading,
    Thesis,
    ThesisIndicator,
    ThesisPremise,
    ThesisSnapshot,
)
from thesis.services.snapshot_builder import build_snapshot


def make_thesis(user, **kwargs):
    """Thesis 인스턴스 생성 헬퍼."""
    defaults = dict(
        user=user,
        title='Snapshot Test Thesis',
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


def make_indicator(thesis, name='Test Indicator', **kwargs):
    """ThesisIndicator 인스턴스 생성 헬퍼."""
    defaults = dict(
        thesis=thesis,
        name=name,
        indicator_type='market_data',
        data_source='manual',
        support_direction='positive',
        weight=1.0,
        is_active=True,
    )
    defaults.update(kwargs)
    return ThesisIndicator.objects.create(**defaults)


def add_readings(indicator, count=5, base_value=100.0):
    """지표에 유효한 IndicatorReading 추가 헬퍼.

    score_indicator_from_model()이 점수를 계산하려면 validation_status='ok'인
    readings가 최소 5개 필요합니다 (effective_window >= 5).
    각 reading은 72시간 이내여야 stale_data 처리를 피합니다.
    """
    now = timezone.now()
    for i in range(count):
        asof = now - timedelta(hours=i * 2)
        IndicatorReading.objects.get_or_create(
            indicator=indicator,
            asof=asof,
            defaults=dict(
                value=base_value + i * 0.5,
                raw_value=base_value + i * 0.5,
                validation_status='ok',
            ),
        )


class TestSnapshotBuilder:

    @pytest.mark.django_db
    def test_snapshot_universe_preserves_dimension(self, user):
        """indicator_universe_ids가 이미 설정된 경우 새 지표를 추가해도
        스냅샷은 원래 universe만 사용해야 합니다."""
        thesis = make_thesis(user)

        # 최초 3개 지표 생성 및 readings 추가
        ind1 = make_indicator(thesis, name='Indicator 1')
        ind2 = make_indicator(thesis, name='Indicator 2')
        ind3 = make_indicator(thesis, name='Indicator 3')
        for ind in [ind1, ind2, ind3]:
            add_readings(ind)

        # Universe를 ind1, ind2, ind3으로 고정
        thesis.indicator_universe_ids = [str(ind1.id), str(ind2.id), str(ind3.id)]
        thesis.save(update_fields=['indicator_universe_ids'])

        # 이후 추가된 ind4는 universe에 포함되지 않아야 함
        ind4 = make_indicator(thesis, name='Indicator 4 (added later)')
        add_readings(ind4)

        snapshot, scoring_result, _ = build_snapshot(thesis, as_of_date=date.today())

        # universe_snapshot 키셋이 원래 3개여야 함
        assert set(snapshot.universe_snapshot.keys()) == {
            str(ind1.id), str(ind2.id), str(ind3.id)
        }
        assert str(ind4.id) not in snapshot.universe_snapshot

    @pytest.mark.django_db
    def test_snapshot_inactive_is_none(self, user):
        """비활성(is_active=False) 지표의 score는 universe_snapshot에서 None이어야 합니다."""
        thesis = make_thesis(user)

        ind_active = make_indicator(thesis, name='Active Indicator')
        ind_inactive = make_indicator(thesis, name='Inactive Indicator', is_active=False)
        add_readings(ind_active)
        add_readings(ind_inactive)

        thesis.indicator_universe_ids = [str(ind_active.id), str(ind_inactive.id)]
        thesis.save(update_fields=['indicator_universe_ids'])

        snapshot, _, _ = build_snapshot(thesis, as_of_date=date.today())

        # 비활성 지표는 None이어야 함
        assert snapshot.universe_snapshot[str(ind_inactive.id)] is None

    @pytest.mark.django_db
    def test_snapshot_asof_date_not_created_at(self, user):
        """as_of_date를 명시적으로 전달하면 스냅샷의 asof_date가 오늘이 아닌
        해당 날짜여야 합니다."""
        thesis = make_thesis(user)
        ind = make_indicator(thesis, name='Date Test Indicator')
        add_readings(ind, count=5)

        target_date = date(2026, 3, 1)

        snapshot, _, _ = build_snapshot(thesis, as_of_date=target_date)

        assert snapshot.asof_date == target_date
        assert snapshot.asof_date != date.today()

    @pytest.mark.django_db
    def test_snapshot_data_coverage_below_06_blocks_state_change(self, user):
        """data_coverage가 0.6 미만이면 thesis.current_state가 변경되지 않아야 합니다.

        3개 지표 중 2개가 비활성(inactive)이므로 data_coverage = 1/3 ≈ 0.33 < 0.6.
        """
        thesis = make_thesis(user, current_state='active')

        ind_active = make_indicator(thesis, name='Active Only')
        ind_inactive1 = make_indicator(thesis, name='Inactive 1', is_active=False)
        ind_inactive2 = make_indicator(thesis, name='Inactive 2', is_active=False)
        add_readings(ind_active)

        thesis.indicator_universe_ids = [
            str(ind_active.id),
            str(ind_inactive1.id),
            str(ind_inactive2.id),
        ]
        thesis.save(update_fields=['indicator_universe_ids'])

        original_state = thesis.current_state

        build_snapshot(thesis, as_of_date=date.today())

        # DB에서 다시 조회하여 상태가 변경되지 않았는지 확인
        thesis.refresh_from_db()
        assert thesis.current_state == original_state
