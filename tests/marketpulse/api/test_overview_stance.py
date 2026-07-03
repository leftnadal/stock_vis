"""MP2-SURFACE — 국면별 판단 카피(stance) 부착 테스트.

- resolve_regime_stance 유닛(5 국면 + status 분기)
- _regime_card / overview 계약에 stance_copy·stance_ok 부착(additive, 기존 필드 불변)
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone as django_timezone
from rest_framework.test import APIClient

from apps.market_pulse.i18n.labels import (
    REGIME_STANCE,
    REGIME_STANCE_FALLBACK,
    resolve_regime_stance,
)
from apps.market_pulse.models.regime import RegimeSnapshot

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='st', email='st@e.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class TestResolveRegimeStance:
    @pytest.mark.parametrize('regime', list(REGIME_STANCE.keys()))
    def test_ok_returns_mapped_copy(self, regime):
        copy, ok = resolve_regime_stance(regime, 'OK')
        assert ok is True
        assert copy == REGIME_STANCE[regime]
        assert copy != REGIME_STANCE_FALLBACK

    def test_five_regimes_covered(self):
        assert set(REGIME_STANCE.keys()) == {
            'BULL_EXPANSION', 'LATE_BULL', 'TRANSITION',
            'BEAR_CONTRACTION', 'CRISIS',
        }

    @pytest.mark.parametrize('status', ['INSUFFICIENT_DATA', 'STALE', 'FAILED'])
    def test_non_ok_status_falls_back(self, status):
        copy, ok = resolve_regime_stance('LATE_BULL', status)
        assert ok is False
        assert copy == REGIME_STANCE_FALLBACK

    def test_unknown_regime_falls_back(self):
        copy, ok = resolve_regime_stance('NOPE', 'OK')
        assert ok is False
        assert copy == REGIME_STANCE_FALLBACK


@pytest.mark.django_db
class TestOverviewStanceContract:
    def _make(self, regime, status):
        today = django_timezone.localdate()
        RegimeSnapshot.objects.create(
            date=today, snapshot_time=django_timezone.now(),
            regime=regime, status=status,
            coverage=0.9, headline='h', fired_rules=[],
            previous_regime='', hysteresis_streak=1,
        )

    def test_regime_card_has_stance_ok(self, auth_client):
        self._make(RegimeSnapshot.Regime.LATE_BULL, RegimeSnapshot.Status.OK)
        r = auth_client.get(reverse('marketpulse_api_v2:overview'))
        regime = r.json()['cards']['regime']
        assert regime is not None
        assert regime['stance_ok'] is True
        assert regime['stance_copy'] == REGIME_STANCE['LATE_BULL']
        # 기존 계약 필드 불변(additive 확인)
        for k in ('regime', 'status', 'coverage', 'headline', 'fired_rules', 'transitioned'):
            assert k in regime

    def test_regime_card_stance_fallback_when_stale(self, auth_client):
        self._make(RegimeSnapshot.Regime.CRISIS, RegimeSnapshot.Status.STALE)
        r = auth_client.get(reverse('marketpulse_api_v2:overview'))
        regime = r.json()['cards']['regime']
        assert regime['stance_ok'] is False
        assert regime['stance_copy'] == REGIME_STANCE_FALLBACK
