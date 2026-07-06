"""MP2-DELTA 슬라이스 2 — anomaly 신규/소멸/해소 델타 + 무발동일 표시.

유닛(compute_anomaly_delta): fired(신규/소멸/최초/동일) · quiet(lookback 초과/이내) · no_history.
계약(overview): anomaly_delta additive 존재 + S1(sector_deltas) 포함 기존 필드 전부 불변.

R3 실측: AnomalySignalLog는 발동 행만 적재(run-marker 부재) → 5c-ii 폴백(무발동일 항상 quiet).
  resolving은 BE에서 미발생하므로 유닛 테스트는 "갭≤7이어도 quiet"로 폴백 동작을 검증(§7).
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone as django_timezone
from rest_framework.test import APIClient

from apps.market_pulse.models.anomaly import AnomalySignalLog
from apps.market_pulse.services.anomaly_delta import (
    ANOMALY_RESOLVE_LOOKBACK_DAYS,
    compute_anomaly_delta,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='ad', email='ad@e.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _fire(d: date_cls, rule_id: str, mode: str = AnomalySignalLog.Mode.HYBRID):
    """발동일 d에 rule_id 1건 적재. triggered_at은 로컬 정오(날짜 경계 안전)."""
    aware = django_timezone.make_aware(datetime.combine(d, time(12, 0)))
    AnomalySignalLog.objects.create(
        rule_id=rule_id, triggered_at=aware, inputs={}, threshold={},
        mode=mode, headline=f'{rule_id} 발동', body='b',
    )


@pytest.mark.django_db
class TestComputeAnomalyDelta:
    def test_fired_vs_prev_fired_date_new_and_gone(self):
        """E1 확장 — 오늘 발동, 직전 발동일 대비 신규+소멸 동시."""
        today = date_cls(2026, 7, 1)
        prev = date_cls(2026, 6, 16)  # 직전 '발동일'(calendar -1 아님)
        _fire(prev, 'R04'); _fire(prev, 'R12')      # 직전: {R04, R12}
        _fire(today, 'R04'); _fire(today, 'R02')    # 오늘: {R04, R02}
        out = compute_anomaly_delta(today)
        assert out['state'] == 'fired'
        assert out['last_fired_date'] == '2026-07-01'
        assert out['vs_fired_date'] == '2026-06-16'
        assert out['new_rules'] == ['R02']          # 오늘 새로
        assert out['gone_rules'] == ['R12']          # 직전엔 있었으나 오늘 없음

    def test_fired_first_ever_all_new_no_prev(self):
        """E2 — 사상 첫 발동: vs_fired_date null, 전부 new_rules, gone 없음."""
        today = date_cls(2026, 7, 1)
        _fire(today, 'R04'); _fire(today, 'R09')
        out = compute_anomaly_delta(today)
        assert out['state'] == 'fired'
        assert out['vs_fired_date'] is None
        assert out['new_rules'] == ['R04', 'R09']
        assert out['gone_rules'] == []

    def test_fired_same_rules_both_days_empty_deltas(self):
        """엣지 — 직전 발동일과 룰 동일: new/gone 모두 빈 배열, vs_date는 노출."""
        today = date_cls(2026, 7, 1)
        prev = date_cls(2026, 6, 30)
        _fire(prev, 'R04'); _fire(today, 'R04')
        out = compute_anomaly_delta(today)
        assert out['state'] == 'fired'
        assert out['vs_fired_date'] == '2026-06-30'
        assert out['new_rules'] == [] and out['gone_rules'] == []

    def test_quiet_lookback_exceeded(self):
        """E4 — 오늘 무발동, 마지막 발동이 lookback 초과: quiet + 마지막 발동일."""
        last = date_cls(2026, 6, 16)
        today = last + timedelta(days=ANOMALY_RESOLVE_LOOKBACK_DAYS + 3)  # 갭 10 > 7
        _fire(last, 'R04')
        out = compute_anomaly_delta(today)
        assert out['state'] == 'quiet'
        assert out['last_fired_date'] == '2026-06-16'
        assert out['resolved_rules'] == []

    def test_quiet_within_lookback_fallback_no_resolving(self):
        """E4'(폴백, E5 대체) — 갭≤7이어도 5c-ii 폴백에서는 resolving 아닌 quiet."""
        last = date_cls(2026, 6, 16)
        today = last + timedelta(days=2)  # 갭 2 ≤ 7
        _fire(last, 'R04')
        out = compute_anomaly_delta(today)
        assert out['state'] == 'quiet'       # R3 판별 불가 → resolving 미발생
        assert out['state'] != 'resolving'
        assert out['last_fired_date'] == '2026-06-16'

    def test_no_history(self):
        """E6 — 발동 이력 0 + 오늘도 무발동: no_history."""
        out = compute_anomaly_delta(date_cls(2026, 7, 1))
        assert out['state'] == 'no_history'
        assert out['last_fired_date'] is None


@pytest.mark.django_db
class TestAnomalyDeltaContract:
    def test_anomaly_delta_additive_and_s1_fields_unchanged(self, auth_client):
        """계약 회귀 — anomaly_delta additive 존재 + S1(sector_deltas)·기존 봉투 전부 불변."""
        _fire(django_timezone.localdate(), 'R04')
        data = auth_client.get(reverse('marketpulse_api_v2:overview')).json()
        # 신규 additive
        assert 'anomaly_delta' in data
        ad = data['anomaly_delta']
        assert ad['state'] == 'fired'
        for k in ('state', 'as_of', 'last_fired_date', 'vs_fired_date',
                  'new_rules', 'gone_rules', 'resolved_rules'):
            assert k in ad
        # S1 필드 + 기존 봉투 불변
        assert 'sector_deltas' in data
        for k in ('_meta', 'ticker_bar', 'news', 'anomaly', 'cards', 'translations'):
            assert k in data
