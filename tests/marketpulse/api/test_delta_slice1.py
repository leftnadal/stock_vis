"""MP2-DELTA 슬라이스 1 — regime transition_from + sector rank 델타.

유닛(compute_sector_deltas): 정상·주말갭·1날짜·어제없던섹터.
계약(overview): transition_from(true/false) + sector_deltas additive + 기존 필드 불변.
"""
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone as django_timezone
from rest_framework.test import APIClient

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import SectorFlowSnapshot
from apps.market_pulse.services.sector_delta import compute_sector_deltas
from macro.models.indicators import MarketIndex

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='dl', email='dl@e.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _idx(sym):
    obj, _ = MarketIndex.objects.update_or_create(
        symbol=sym, defaults={'name': sym, 'sector_group': 'SECTOR', 'category': 'sector'}
    )
    return obj


def _snap(d, sym, rank):
    SectorFlowSnapshot.objects.create(
        date=d, snapshot_time=django_timezone.now(), market_index=_idx(sym),
        rel_strength=Decimal('0.1'), momentum_1d=Decimal('0'),
        cross_dispersion=Decimal('0.3'), rotation_index=Decimal('1.1'),
        rank_in_universe=rank,
    )


@pytest.mark.django_db
class TestComputeSectorDeltas:
    def test_normal_two_dates_values_sign_sort(self):
        d1, d0 = date_cls(2026, 7, 3), date_cls(2026, 7, 2)
        # 어제 rank → 오늘 rank
        _snap(d0, 'XLK', 5); _snap(d1, 'XLK', 2)   # +3 상승
        _snap(d0, 'XLE', 3); _snap(d1, 'XLE', 5)   # -2 하락
        _snap(d0, 'XLF', 1); _snap(d1, 'XLF', 1)   # 0
        out = compute_sector_deltas(d1)
        assert [o['sector'] for o in out] == ['XLK', 'XLE', 'XLF']  # |delta| desc
        xlk = next(o for o in out if o['sector'] == 'XLK')
        assert xlk['rank_delta'] == 3 and xlk['prev_rank'] == 5 and xlk['rank'] == 2
        assert xlk['as_of'] == '2026-07-03' and xlk['vs_date'] == '2026-07-02'
        assert next(o for o in out if o['sector'] == 'XLE')['rank_delta'] == -2

    def test_weekend_gap_prev_is_last_distinct(self):
        # today=06-29(월), 직전 distinct = 06-27(금) — calendar -1(06-28) 아님
        mon, fri = date_cls(2026, 6, 29), date_cls(2026, 6, 27)
        _snap(fri, 'XLK', 4); _snap(mon, 'XLK', 1)
        out = compute_sector_deltas(mon)
        assert out and out[0]['vs_date'] == '2026-06-27'
        assert out[0]['rank_delta'] == 3

    def test_single_date_returns_empty(self):
        _snap(date_cls(2026, 7, 3), 'XLK', 1)
        assert compute_sector_deltas(date_cls(2026, 7, 3)) == []

    def test_sector_absent_yesterday_excluded(self):
        d1, d0 = date_cls(2026, 7, 3), date_cls(2026, 7, 2)
        _snap(d0, 'XLK', 2); _snap(d1, 'XLK', 1)
        _snap(d1, 'XLNEW', 3)  # 오늘만 존재 → 제외
        out = compute_sector_deltas(d1)
        assert {o['sector'] for o in out} == {'XLK'}


@pytest.mark.django_db
class TestDeltaContract:
    def _regime(self, regime, prev):
        RegimeSnapshot.objects.create(
            date=django_timezone.localdate(), snapshot_time=django_timezone.now(),
            regime=regime, status=RegimeSnapshot.Status.OK,
            coverage=0.9, headline='h', fired_rules=[], inputs={},
            previous_regime=prev, hysteresis_streak=1,
        )

    def test_transition_from_when_transitioned(self, auth_client):
        self._regime(RegimeSnapshot.Regime.LATE_BULL, RegimeSnapshot.Regime.TRANSITION)
        data = auth_client.get(reverse('marketpulse_api_v2:overview')).json()
        assert data['cards']['regime']['transition_from'] == 'TRANSITION'
        assert 'sector_deltas' in data  # additive 존재

    def test_transition_from_none_when_not_transitioned(self, auth_client):
        self._regime(RegimeSnapshot.Regime.LATE_BULL, '')
        data = auth_client.get(reverse('marketpulse_api_v2:overview')).json()
        assert data['cards']['regime']['transition_from'] is None

    def test_existing_contract_fields_unchanged(self, auth_client):
        self._regime(RegimeSnapshot.Regime.LATE_BULL, '')
        data = auth_client.get(reverse('marketpulse_api_v2:overview')).json()
        for k in ('_meta', 'ticker_bar', 'news', 'anomaly', 'cards', 'translations'):
            assert k in data
        for k in ('regime', 'status', 'coverage', 'headline', 'transitioned',
                  'stance_copy', 'stance_ok', 'next_stage'):
            assert k in data['cards']['regime']
